#!/usr/bin/env python3
"""

Iden Challenge - Playwright Automation Script

"""

import json
import os
import signal
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

class IdenChallengeScraper:
    def __init__(self):
        self.base_url = "https://hiring.idenhq.com"
        self.session_file = "session.json"
        self.output_file = "product_data.json"
        self.temp_file = "temp_products.json"
        self.browser = None
        self.page = None
        self.all_products = []
        
        # Set up interrupt handler
        signal.signal(signal.SIGINT, self.handle_interrupt)
        
    def handle_interrupt(self, signum, frame):
        """Handle Ctrl+C interruption and save data"""
        print(f"\nInterruption detected! Saving {len(self.all_products)} products before exit...")
        self.save_final_data()
        print("Data saved successfully!")
        print(f"Total products saved: {len(self.all_products)}")
        
        try:
            if self.browser:
                self.browser.close()
        except:
            pass
            
        sys.exit(0)
    
    def save_continuous(self, products):
        """Save products immediately - called after every attempt (This creates regular progress backups)"""
        print(f"SAVING: Attempting to save {len(products)} products...")
        
        try:
            # Create the data structure
            temp_data = {
                'timestamp': time.time(),
                'products_count': len(products),
                'status': 'in_progress',
                'products': products
            }
            
            # Save to main temp file
            print(f"Writing to {self.temp_file}...")
            with open(self.temp_file, 'w', encoding='utf-8') as f:
                json.dump(temp_data, f, indent=2, ensure_ascii=False)
            print(f"SUCCESS: Saved to {self.temp_file}")
            
            # Save to numbered backup
            backup_name = f"progress_backup_{len(products)}.json"
            print(f"Writing to {backup_name}...")
            with open(backup_name, 'w', encoding='utf-8') as f:
                json.dump(temp_data, f, indent=2, ensure_ascii=False)
            print(f"SUCCESS: Saved to {backup_name}")
            
            # Verify files were created
            if os.path.exists(self.temp_file):
                size = os.path.getsize(self.temp_file)
                print(f"VERIFIED: {self.temp_file} exists, size: {size} bytes")
            else:
                print(f"ERROR: {self.temp_file} was not created!")
                
            if os.path.exists(backup_name):
                size = os.path.getsize(backup_name)
                print(f"VERIFIED: {backup_name} exists, size: {size} bytes")
            else:
                print(f"ERROR: {backup_name} was not created!")
                
        except Exception as e:
            print(f"SAVE ERROR: {e}")
            print(f"Error type: {type(e).__name__}")
            
            # Try emergency save
            try:
                emergency_name = f"emergency_save_{int(time.time())}.json"
                print(f"Attempting emergency save to {emergency_name}...")
                with open(emergency_name, 'w', encoding='utf-8') as f:
                    json.dump({'products': products, 'count': len(products)}, f, indent=2)
                print(f"EMERGENCY SAVE SUCCESS: {emergency_name}")
            except Exception as e2:
                print(f"EMERGENCY SAVE FAILED: {e2}")
    
    def save_final_data(self):
        """Save final data to main output file"""
        print(f"FINAL SAVE: Saving {len(self.all_products)} products to {self.output_file}")
        try:
            final_data = {
                'timestamp': time.time(),
                'total_products': len(self.all_products),
                'status': 'completed',
                'products': self.all_products
            }
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
                
            print(f"FINAL SAVE SUCCESS: Data saved to {self.output_file}")
            
        except Exception as e:
            print(f"FINAL SAVE ERROR: {e}")
            try:
                backup_final = f"final_backup_{int(time.time())}.json"
                with open(backup_final, 'w', encoding='utf-8') as f:
                    json.dump({'products': self.all_products}, f, indent=2)
                print(f"BACKUP FINAL SAVE SUCCESS: {backup_final}")
            except:
                print("ALL SAVES FAILED!")
    
    def load_previous_progress(self):
        """Load any previous progress from temp file, can resume after interrupt/CTRL+C"""
        if os.path.exists(self.temp_file):
            try:
                with open(self.temp_file, 'r', encoding='utf-8') as f:
                    temp_data = json.load(f)
                
                if temp_data.get('products'):
                    print(f"Found previous progress: {len(temp_data['products'])} products")
                    response = input("Do you want to continue from where you left off? (y/n): ")
                    if response.lower() == 'y':
                        self.all_products = temp_data['products']
                        return True
                        
            except Exception as e:
                print(f"Could not load previous progress: {e}")
        
        return False
        
    def save_session(self, context):
        """Save session cookies for future use - session management using session.json"""
        try:
            cookies = context.cookies()
            session_data = {
                'cookies': cookies,
                'timestamp': time.time()
            }
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            print(f"Session saved to {self.session_file}")
        except Exception as e:
            print(f"Failed to save session: {e}")
    
    def load_session(self, context):
        """Load existing session if available"""
        if not os.path.exists(self.session_file):
            print("No existing session found")
            return False
            
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            if time.time() - session_data.get('timestamp', 0) > 86400:
                print("Session expired, will create new one")
                return False
                
            context.add_cookies(session_data['cookies'])
            print("Existing session loaded successfully")
            return True
            
        except Exception as e:
            print(f"Failed to load session: {e}")
            return False
    
    def check_authentication(self):
        """Check if we're currently authenticated"""
        try:
            print("Checking if authenticated...")
            self.page.wait_for_load_state('networkidle')
            
            current_url = self.page.url
            print(f"Current URL: {current_url}")
            
            if '/instructions' in current_url:
                print("Successfully authenticated - at instructions page")
                return True
            
            if '/challenge' in current_url:
                print("Successfully authenticated - at challenge page")
                return True
            
            login_form_selectors = [
                'input[type="password"]', 'input[name="password"]', 
                'button:has-text("Login")', 'button:has-text("Sign In")',
                'input[type="email"]'
            ]
            
            for selector in login_form_selectors:
                try:
                    if self.page.wait_for_selector(selector, timeout=2000):
                        print("Login form still present, not authenticated")
                        return False
                except:
                    continue
            
            print("No login form found, assuming authenticated")
            return True
                
        except Exception as e:
            print(f"Error checking authentication: {e}")
            return True
    
    def authenticate(self):
        """Handle authentication process"""
        try:
            print("Looking for login interface...")
            self.page.wait_for_timeout(2000)
            
            if self.check_authentication():
                print("Already authenticated")
                return True
                
            print("Searching for login form elements...")
            
            username_selectors = [
                'input[type="email"]', 'input[name="email"]', 'input[id="email"]',
                'input[type="text"]', 'input[name="username"]', 'input[id="username"]',
                'input[placeholder*="email" i]', 'input[placeholder*="username" i]',
                'input[placeholder*="user" i]', 'input[data-testid*="email"]',
                'input[data-testid*="username"]'
            ]
            
            password_selectors = [
                'input[type="password"]', 'input[name="password"]', 'input[id="password"]',
                'input[placeholder*="password" i]', 'input[data-testid*="password"]'
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = self.page.wait_for_selector(selector, timeout=3000)
                    if username_field:
                        print(f"Found username field with selector: {selector}")
                        break
                except:
                    continue
                    
            if not username_field:
                print("Could not find username/email field")
                return False
                
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.page.wait_for_selector(selector, timeout=3000)
                    if password_field:
                        print(f"Found password field with selector: {selector}")
                        break
                except:
                    continue
                    
            if not password_field:
                print("Could not find password field")
                return False
            
            credentials = {
                'username': 'anirudh.cb13@gmail.com',  
                'password': 'V1tpV3MP'   
            }
            
            print("Filling in credentials...")
            username_field.click()
            username_field.press('Control+a')
            username_field.fill(credentials['username'])
            
            password_field.click()
            password_field.press('Control+a')
            password_field.fill(credentials['password'])
            
            submit_selectors = [
                'button[type="submit"]', 'input[type="submit"]', 
                'button:has-text("Login")', 'button:has-text("Sign In")',
                'button:has-text("Log In")', 'button:has-text("Submit")',
                '[role="button"]:has-text("Login")', '[role="button"]:has-text("Sign In")',
                'button[data-testid*="login"]', 'button[data-testid*="submit"]'
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    submit_button = self.page.wait_for_selector(selector, timeout=3000)
                    if submit_button:
                        print(f"Found submit button with selector: {selector}")
                        break
                except:
                    continue
                    
            if not submit_button:
                print("Could not find submit button")
                return False
            
            print("Clicking submit button...")
            submit_button.click()
            
            print("Waiting for login to process...")
            self.page.wait_for_load_state('networkidle')
            self.page.wait_for_timeout(3000)
                
            if self.check_authentication():
                print("Authentication successful!")
                return True
            else:
                print("Authentication may have failed, but continuing...")
                return False
                
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def launch_challenge(self):
        """Navigate from instructions page to challenge page"""
        try:
            current_url = self.page.url
            print(f"Current page: {current_url}")
            
            if '/instructions' not in current_url:
                instructions_url = f"{self.base_url}/instructions"
                print(f"Navigating to instructions page: {instructions_url}")
                self.page.goto(instructions_url)
                self.page.wait_for_load_state('networkidle')
                self.page.wait_for_timeout(2000)
            
            print("Looking for 'Launch Challenge' button...")
            
            launch_button_selectors = [
                'button:has-text("Launch Challenge")',
                'a:has-text("Launch Challenge")',
                'button:has-text("Launch")',
                'a:has-text("Launch")',
                'button:has-text("Start Challenge")',
                'a:has-text("Start Challenge")',
                'button:has-text("Begin")',
                'a:has-text("Begin")',
                '[data-testid*="launch"]',
                '[data-testid*="challenge"]'
            ]
            
            launch_button = None
            for selector in launch_button_selectors:
                try:
                    launch_button = self.page.wait_for_selector(selector, timeout=3000)
                    if launch_button:
                        print(f"Found launch button with selector: {selector}")
                        break
                except:
                    continue
            
            if not launch_button:
                print("Could not find Launch Challenge button")
                return False
            
            print("Clicking Launch Challenge button...")
            launch_button.click()
            
            print("Waiting for challenge page to load...")
            self.page.wait_for_load_state('networkidle')
            self.page.wait_for_timeout(3000)
            
            final_url = self.page.url
            print(f"Final URL: {final_url}")
            
            if '/challenge' in final_url:
                print("Successfully launched challenge!")
                return True
            else:
                print(f"Expected to be at /challenge, but at: {final_url}")
                return False
                
        except Exception as e:
            print(f"Error launching challenge: {e}")
            return False
    
    def find_product_table(self):
        """Check if current page contains a product table"""
        try:
            table_selectors = [
                'table', '.table', '[role="table"]', '.data-table',
                '.product-table', '.products-table'
            ]
            
            for selector in table_selectors:
                try:
                    table = self.page.wait_for_selector(selector, timeout=3000)
                    if table:
                        table_text = table.inner_text().lower()
                        product_keywords = ['product', 'name', 'price', 'id', 'sku', 'item']
                        
                        if any(keyword in table_text for keyword in product_keywords):
                            print("Found product table!")
                            return True
                except:
                    continue
                    
            return False
        except:
            return False
    
    def navigate_to_product_table(self):
        """Navigate through the hidden path to find the product table"""
        try:
            print("Searching for product table on challenge page...")
            
            current_url = self.page.url
            if '/challenge' not in current_url:
                print("Not on challenge page, something went wrong")
                return False
            
            self.page.wait_for_load_state('networkidle')
            self.page.wait_for_timeout(3000)
            
            print("Examining challenge page content...")
            
            buttons = self.page.query_selector_all('button')
            links = self.page.query_selector_all('a')
            
            print(f"Found {len(buttons)} buttons and {len(links)} links on challenge page")
            
            for i, button in enumerate(buttons[:10]):
                try:
                    text = button.inner_text().strip()
                    if text:
                        print(f"  Button {i+1}: '{text}'")
                except:
                    pass
            
            if self.find_product_table():
                print("Product table found immediately!")
                return True
            
            return False
            
        except Exception as e:
            print(f"Navigation error: {e}")
            return False
    
    def find_scrollable_table_container(self):
        """Find the scrollable table container efficiently"""
        container_selectors = [
            'div[style*="overflow"]',
            '.table-container',
            'div[style*="max-height"]',
            '.overflow-auto',
            '.overflow-y-auto',
            'tbody',
            'table'
        ]
        
        for selector in container_selectors:
            try:
                elements = self.page.query_selector_all(selector)
                for element in elements:
                    scroll_info = element.evaluate("""(el) => {
                        return {
                            hasVerticalScroll: el.scrollHeight > el.clientHeight,
                            scrollHeight: el.scrollHeight,
                            clientHeight: el.clientHeight
                        }
                    }""")
                    
                    if scroll_info['hasVerticalScroll']:
                        print(f"Found scrollable container: {selector}")
                        print(f"   ScrollHeight: {scroll_info['scrollHeight']}, ClientHeight: {scroll_info['clientHeight']}")
                        return element
                        
            except:
                continue
        
        return None
    
    def extract_current_page_data(self):
        """Extract product data from all currently visible products"""
        try:
            products = []
            
            table = self.page.wait_for_selector('table, .table, [role="table"]', timeout=3000)
            if not table:
                return products
            
            rows = self.page.query_selector_all('tbody tr, table tr:not(:first-child)')
            
            for i, row in enumerate(rows):
                try:
                    if not row.is_visible():
                        continue
                        
                    cells = row.query_selector_all('td')
                    
                    if len(cells) >= 8:
                        cell_data = []
                        for cell in cells[:9]:
                            try:
                                text = cell.inner_text().strip()
                                cell_data.append(text if text else None)
                            except:
                                cell_data.append(None)
                        
                        product = {
                            'id': cell_data[0],
                            'description': cell_data[1], 
                            'stock': cell_data[2],
                            'color': cell_data[3],
                            'price': cell_data[4],
                            'sku': cell_data[5],
                            'manufacturer': cell_data[6],
                            'item': cell_data[7],
                            'size': cell_data[8] if len(cell_data) > 8 else None
                        }
                        
                        if product.get('id') or product.get('sku'):
                            products.append(product)
                            
                except Exception as e:
                    continue
            
            return products
            
        except Exception as e:
            print(f"Error extracting current page data: {e}")
            return []
    
    def extract_product_data(self):
        """Extract all product data """
        try:
            #Scrolls directly to bottom of table container at each try, checks for 20 new products, keeps the waiting time constant
            
            # Check previous progress
            if not self.load_previous_progress():
                self.all_products = []
            
            consecutive_no_new_data = 0
            max_no_data_attempts = 5
            total_attempts = 0
            max_attempts = 100
            starting_count = len(self.all_products)
            
            print(f"Starting with {starting_count} products already extracted")
            
            table_container = self.find_scrollable_table_container()
            
            if not table_container:
                print("Could not find scrollable table container")
                return self.all_products
            
            # Initial extraction if starting fresh
            if starting_count == 0:
                print("Extracting initial products...")
                current_products = self.extract_current_page_data()
                self.all_products.extend(current_products)
                print(f"Initial extraction: {len(current_products)} products")
                
                # IMMEDIATE SAVE TEST
                print("TESTING IMMEDIATE SAVE...")
                self.save_continuous(self.all_products)
            
            
            # Cache for duplicate detection
            self._existing_ids_cache = {p.get('id') for p in self.all_products if p.get('id')}
            
            # Since table loads 20 products per scroll, we need many scrolls
            wait_time = 500  # Even shorter wait since we know it's 20 per batch
            
            while consecutive_no_new_data < max_no_data_attempts and total_attempts < max_attempts:
                total_attempts += 1
                
                print(f"Attempt {total_attempts}: Scrolling to trigger next batch of 20...")
                
                # Multiple rapid scrolls to trigger loading
                for i in range(3):  # Do 3 scrolls to ensure we trigger loading
                    table_container.evaluate("""(el) => {
                        el.scrollTop = el.scrollHeight;
                    }""")
                    self.page.wait_for_timeout(100)  # Brief pause between scrolls
                
                print(f"Waiting {wait_time}ms for new batch to load...")
                self.page.wait_for_timeout(wait_time)
                
                # Extract all currently visible products
                new_batch = self.extract_current_page_data()
                print(f"Found {len(new_batch)} total visible products in table")
                
                # Find new unique products
                new_unique_products = []
                for product in new_batch:
                    product_id = product.get('id', '')
                    
                    if product_id and product_id not in self._existing_ids_cache and any(product.values()):
                        new_unique_products.append(product)
                        self._existing_ids_cache.add(product_id)
                
                # Add new products
                self.all_products.extend(new_unique_products)
                current_count = len(self.all_products)
                new_count = len(new_unique_products)
                
                # Save every 5 attempts to reduce I/O overhead
                if total_attempts % 5 == 0 or new_count == 0:
                    print("SAVING PROGRESS...")
                    self.save_continuous(self.all_products)
                
                print(f"Total: {current_count} products (+{new_count} new)")
                
                # Track consecutive failures
                if new_count == 0:
                    consecutive_no_new_data += 1
                    print(f"No new products - consecutive failures: {consecutive_no_new_data}/{max_no_data_attempts}")
                else:
                    consecutive_no_new_data = 0  # Reset on any new products
                    
                    # If we're getting exactly 20 each time, we're making good progress
                    if new_count == 20:
                        print("Getting expected 20 products per batch - good progress")
                    elif new_count < 20:
                        print(f"Only {new_count} new products - may be nearing end")
                
                # Estimate progress if we're getting consistent batches
                if new_count > 0:
                    estimated_remaining = (3300 - current_count) / new_count if new_count > 0 else 0
                    if estimated_remaining > 0:
                        print(f"Estimated {estimated_remaining:.0f} more attempts needed to reach 3300")
                
                # Quick exit when we hit target
                if current_count >= 3300:
                    print("Reached target of 3300+ products!")
                    break
                
                # Check target
                if current_count >= 3300:
                    print("Reached expected product count (3300+)!")
                    
                    print("Final verification attempts...")
                    for final_attempt in range(2):
                        table_container.evaluate("""(el) => {
                            el.scrollTop = el.scrollHeight;
                        }""")
                        self.page.wait_for_timeout(3000)
                        
                        final_batch = self.extract_current_page_data()
                        final_new = 0
                        for product in final_batch:
                            product_id = product.get('id', '')
                            if product_id and product_id not in self._existing_ids_cache:
                                self.all_products.append(product)
                                self._existing_ids_cache.add(product_id)
                                final_new += 1
                        
                        print(f"Final attempt {final_attempt+1}: +{final_new} products")
                        
                        # Save after final attempts too
                        self.save_continuous(self.all_products)
                    
                    break
                
                # Progress reporting
                if current_count % 500 == 0 and current_count > 0:
                    percentage = (current_count / 3300) * 100
                    avg_per_attempt = current_count / total_attempts
                    print(f"MILESTONE: {current_count}/3300 ({percentage:.1f}%) | {total_attempts} attempts | {avg_per_attempt:.1f} products/attempt")
                
                # Recovery strategies when stuck
                if consecutive_no_new_data == 3:
                    print("STRATEGY CHANGE: Multiple bottom scrolls + longer wait...")
                    for i in range(5):
                        table_container.evaluate("""(el) => {
                            el.scrollTop = el.scrollHeight;
                        }""")
                        self.page.wait_for_timeout(200)
                    self.page.wait_for_timeout(2000)  # Longer wait after multiple scrolls
                    
                elif consecutive_no_new_data == 4:
                    print("LAST RESORT: Click table + scroll + longer wait...")
                    try:
                        table_container.click()
                        self.page.wait_for_timeout(500)
                        for i in range(3):
                            table_container.evaluate("""(el) => {
                                el.scrollTop = el.scrollHeight;
                            }""")
                            self.page.wait_for_timeout(300)
                        self.page.wait_for_timeout(3000)
                    except:
                        pass
            
            print(f"SCROLL-TO-BOTTOM extraction complete!")
            print(f"Total products: {len(self.all_products)}")
            print(f"Total attempts: {total_attempts}")
            
            if total_attempts > 0:
                avg_per_attempt = len(self.all_products) / total_attempts
                avg_time = wait_time / 1000  # Convert to seconds
                print(f"Efficiency: {avg_per_attempt:.1f} products/attempt | {avg_time:.1f}s avg wait")
            
            # Final save
            self.save_continuous(self.all_products)
            return self.all_products
            
        except Exception as e:
            print(f"Scroll-to-bottom extraction error: {e}")
            if hasattr(self, 'all_products') and self.all_products:
                print(f"Emergency save: {len(self.all_products)} products")
                self.save_continuous(self.all_products)
            return self.all_products if hasattr(self, 'all_products') else []
    
    def run(self):

        try:
            print("Starting Iden Challenge automation...")
            
            with sync_playwright() as p:
                self.browser = p.chromium.launch(headless=False)
                context = self.browser.new_context()
                self.page = context.new_page()
                
                session_loaded = self.load_session(context)
                
                print(f"Navigating to {self.base_url}")
                self.page.goto(self.base_url)
                
                print("Waiting for React app to load...")
                self.page.wait_for_load_state('networkidle')
                self.page.wait_for_timeout(3000)
                
                print(f"Page title: {self.page.title()}")
                print(f"Current URL: {self.page.url}")
                
                if not session_loaded or not self.check_authentication():
                    if not self.authenticate():
                        print("Authentication failed, exiting...")
                        return False
                    else:
                        self.save_session(context)
                
                if not self.launch_challenge():
                    print("Could not launch challenge, exiting...")
                    return False
                
                if not self.navigate_to_product_table():
                    print("Could not find product table, exiting...")
                    return False
                
                products = self.extract_product_data()
                
                if not products:
                    print("No product data extracted")
                    return False
                
                self.save_final_data()
                
                print("Challenge completed successfully!")
                return True
                
        except Exception as e:
            print(f"Fatal error: {e}")
            return False
        
        finally:
            if self.browser:
                try:
                    self.browser.close()
                except:
                    pass

def main():
    """Entry point"""
    scraper = IdenChallengeScraper()
    success = scraper.run()
    
    if success:
        print("\n Successful, check the product_data.json file for results.")
    else:
        print("\n Failed. Review logs")

if __name__ == "__main__":
    main()