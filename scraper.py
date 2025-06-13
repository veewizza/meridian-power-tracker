import os
import json
import logging
import time
from datetime import datetime, timedelta
import pandas as pd
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log')
    ]
)
logger = logging.getLogger('meridian_scraper')

class MeridianEnergyScraper:
    """
    A class to scrape power usage data from Meridian Energy's website.
    """
    
    def __init__(self, email, password, headless=True):
        """
        Initialize the scraper with login credentials.
        
        Args:
            email (str): Meridian Energy account email
            password (str): Meridian Energy account password
            headless (bool): Whether to run the browser in headless mode
        """
        self.email = email
        self.password = password
        self.headless = headless
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        self.latest_data = None
        self.captured_requests = []
        
        # Create data directory if it doesn't exist
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def run(self):
        """
        Run the scraper to fetch the latest power usage data.
        
        Returns:
            dict: The latest power usage data or None if scraping failed
        """
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    java_script_enabled=True,
                    accept_downloads=True,
                    ignore_https_errors=True
                )
                
                page = context.new_page()
                
                # Set up response monitoring for API calls
                page.on("response", self._handle_response)
                page.on("request", self._handle_request)
                
                # Navigate to the secure login page
                logger.info("Navigating to Meridian Energy secure login")
                page.goto("https://secure.meridianenergy.co.nz/", wait_until='networkidle', timeout=60000)
                
                # Take screenshot for debugging
                if not self.headless:
                    page.screenshot(path="login_page.png")
                
                # Wait for and fill email field
                logger.info("Looking for email input field")
                email_selector = 'input[type="email"], input[name="email"], input[id*="email"], input[placeholder*="email" i]'
                
                try:
                    page.wait_for_selector(email_selector, timeout=10000)
                    logger.info("Found email field, filling it")
                    page.fill(email_selector, self.email)
                    
                    # Look for and click submit/next button
                    submit_selectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Next")',
                        'button:has-text("Continue")',
                        'button:has-text("Sign in")',
                        'button:has-text("Log in")'
                    ]
                    
                    submit_clicked = False
                    for selector in submit_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                logger.info(f"Clicking submit button: {selector}")
                                page.click(selector)
                                submit_clicked = True
                                break
                        except:
                            continue
                    
                    if not submit_clicked:
                        # Try pressing Enter on the email field
                        logger.info("No submit button found, trying Enter key")
                        page.press(email_selector, 'Enter')
                    
                    # Wait for password field
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error with email field: {e}")
                    page.screenshot(path="error_email.png")
                    return None
                
                # Wait for and fill password field
                logger.info("Looking for password input field")
                password_selector = 'input[type="password"], input[name="password"], input[id*="password"]'
                
                try:
                    page.wait_for_selector(password_selector, timeout=15000)
                    logger.info("Found password field, filling it")
                    page.fill(password_selector, self.password)
                    
                    # Look for and click login button
                    login_selectors = [
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button:has-text("Sign in")',
                        'button:has-text("Log in")',
                        'button:has-text("Login")',
                        'button:has-text("Continue")'
                    ]
                    
                    login_clicked = False
                    for selector in login_selectors:
                        try:
                            if page.locator(selector).count() > 0:
                                logger.info(f"Clicking login button: {selector}")
                                page.click(selector)
                                login_clicked = True
                                break
                        except:
                            continue
                    
                    if not login_clicked:
                        # Try pressing Enter on the password field
                        logger.info("No login button found, trying Enter key")
                        page.press(password_selector, 'Enter')
                    
                except Exception as e:
                    logger.error(f"Error with password field: {e}")
                    page.screenshot(path="error_password.png")
                    return None
                
                # Wait for successful login and dashboard
                logger.info("Waiting for login to complete")
                time.sleep(5)
                
                # Check if we're successfully logged in by looking for dashboard elements
                # This will vary based on Meridian's actual dashboard structure
                dashboard_selectors = [
                    '[class*="dashboard"]',
                    '[class*="account"]',
                    '[class*="usage"]',
                    '[class*="consumption"]',
                    'main',
                    '.main-content'
                ]
                
                dashboard_found = False
                for selector in dashboard_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=5000)
                        logger.info(f"Dashboard found using selector: {selector}")
                        dashboard_found = True
                        break
                    except:
                        continue
                
                if not dashboard_found:
                    logger.warning("Dashboard not found with common selectors, continuing anyway")
                
                # Take screenshot after login
                if not self.headless:
                    page.screenshot(path="after_login.png")
                
                # Look for usage/consumption data or navigate to usage page
                logger.info("Looking for power usage data")
                
                # Try to find and click on usage/consumption links
                usage_links = [
                    'a:has-text("Usage")',
                    'a:has-text("Consumption")',
                    'a:has-text("My Usage")',
                    'a:has-text("Energy Usage")',
                    '[href*="usage"]',
                    '[href*="consumption"]'
                ]
                
                for link_selector in usage_links:
                    try:
                        if page.locator(link_selector).count() > 0:
                            logger.info(f"Found usage link: {link_selector}")
                            page.click(link_selector)
                            time.sleep(3)
                            break
                    except:
                        continue
                
                # Wait for any data to load and capture API responses
                logger.info("Waiting for data to load...")
                time.sleep(10)
                
                # Try to trigger data loading by interacting with the page
                try:
                    # Look for date pickers, dropdowns, or buttons that might trigger data loading
                    interactive_elements = [
                        'select',
                        'button:has-text("Load")',
                        'button:has-text("Refresh")',
                        'button:has-text("Update")',
                        '[class*="date-picker"]',
                        '[class*="dropdown"]'
                    ]
                    
                    for element in interactive_elements:
                        try:
                            if page.locator(element).count() > 0:
                                logger.info(f"Interacting with element: {element}")
                                page.click(element, timeout=2000)
                                time.sleep(2)
                        except:
                            continue
                            
                except Exception as e:
                    logger.info(f"Error interacting with page elements: {e}")
                
                # Wait additional time for any API calls
                time.sleep(5)
                
                # If no API data was captured, try to scrape visible data
                if not self.latest_data:
                    logger.info("No API data captured, trying to scrape visible data")
                    self._scrape_visible_data(page)
                
                # Close browser
                browser.close()
                
                # Return the latest data
                return self.latest_data
                
        except PlaywrightTimeoutError as e:
            logger.error(f"Timeout error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return None
    
    def _handle_request(self, request):
        """
        Handle outgoing requests to log API calls.
        """
        if any(keyword in request.url.lower() for keyword in ['api', 'usage', 'consumption', 'data', 'meter']):
            logger.info(f"API Request: {request.method} {request.url}")
            self.captured_requests.append({
                'url': request.url,
                'method': request.method,
                'timestamp': datetime.now().isoformat()
            })
    
    def _handle_response(self, response):
        """
        Handle API responses to capture power usage data.
        
        Args:
            response: Playwright response object
        """
        # Check if this is an API response containing power usage data
        api_keywords = ['usage', 'consumption', 'meter', 'reading', 'data', 'energy', 'power']
        
        if (response.status == 200 and 
            any(keyword in response.url.lower() for keyword in api_keywords) and
            'json' in response.headers.get('content-type', '').lower()):
            
            try:
                data = response.json()
                logger.info(f"Captured API response from {response.url}")
                logger.info(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                
                # Process and store the data
                self._process_data(data, response.url)
                
            except Exception as e:
                logger.error(f"Error processing API response from {response.url}: {e}")
    
    def _scrape_visible_data(self, page):
        """
        Fallback method to scrape visible data from the page if API capture fails.
        """
        try:
            logger.info("Attempting to scrape visible data from page")
            
            # Common selectors for usage data
            data_selectors = [
                '[class*="usage"]',
                '[class*="consumption"]',
                '[class*="reading"]',
                '[class*="meter"]',
                '[class*="kwh"]',
                'table',
                '.data-table',
                '.usage-chart',
                '.consumption-chart'
            ]
            
            scraped_data = {
                'timestamp': datetime.now().isoformat(),
                'source': 'visual_scrape',
                'data': {}
            }
            
            for selector in data_selectors:
                try:
                    elements = page.locator(selector)
                    count = elements.count()
                    
                    if count > 0:
                        logger.info(f"Found {count} elements with selector: {selector}")
                        
                        for i in range(min(count, 5)):  # Limit to first 5 elements
                            element = elements.nth(i)
                            text = element.inner_text()
                            
                            if text and len(text.strip()) > 0:
                                scraped_data['data'][f'{selector}_{i}'] = text.strip()
                
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
            
            if scraped_data['data']:
                logger.info("Found some visible data")
                self._process_data(scraped_data)
            else:
                logger.warning("No visible data found to scrape")
                
        except Exception as e:
            logger.error(f"Error scraping visible data: {e}")
    
    def _process_data(self, data, source_url=None):
        """
        Process and store the power usage data.
        
        Args:
            data (dict): The power usage data
            source_url (str): The URL where data was captured from
        """
        # Add metadata
        processed_data = {
            'timestamp': datetime.now().isoformat(),
            'source_url': source_url,
            'raw_data': data
        }
        
        # Store the latest data
        self.latest_data = processed_data
        
        # Save raw data to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meridian_data_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(processed_data, f, indent=2)
        
        logger.info(f"Saved raw data to {filepath}")
        
        # Also save the latest data to a fixed filename for easy access
        latest_filepath = os.path.join(self.data_dir, "latest_data.json")
        with open(latest_filepath, 'w') as f:
            json.dump(processed_data, f, indent=2)
        
        # Save request log
        if self.captured_requests:
            requests_filepath = os.path.join(self.data_dir, f"requests_{timestamp}.json")
            with open(requests_filepath, 'w') as f:
                json.dump(self.captured_requests, f, indent=2)
        
        # Try to convert to pandas DataFrame for analysis
        try:
            self._convert_to_dataframe(processed_data, timestamp)
        except Exception as e:
            logger.error(f"Error converting data to DataFrame: {e}")
    
    def _convert_to_dataframe(self, data, timestamp):
        """
        Convert the data to pandas DataFrame format.
        """
        # This will need to be customized based on actual data structure
        raw_data = data.get('raw_data', {})
        
        # Try different common data structures
        df_candidates = []
        
        # Check if data is a list
        if isinstance(raw_data, list):
            df_candidates.append(pd.DataFrame(raw_data))
        
        # Check for common nested structures
        for key in ['readings', 'usage', 'consumption', 'data', 'results', 'items']:
            if key in raw_data and isinstance(raw_data[key], list):
                df_candidates.append(pd.DataFrame(raw_data[key]))
        
        # If we found data to convert
        if df_candidates:
            df = df_candidates[0]  # Use the first valid DataFrame
            
            # Save to CSV
            csv_filepath = os.path.join(self.data_dir, f"meridian_data_{timestamp}.csv")
            df.to_csv(csv_filepath, index=False)
            logger.info(f"Saved processed data to {csv_filepath}")
            
            # Also save to latest CSV
            latest_csv = os.path.join(self.data_dir, "latest_data.csv")
            df.to_csv(latest_csv, index=False)
    
    def get_latest_data(self):
        """
        Get the latest stored power usage data.
        
        Returns:
            dict: The latest power usage data or None if no data is available
        """
        latest_filepath = os.path.join(self.data_dir, "latest_data.json")
        if os.path.exists(latest_filepath):
            with open(latest_filepath, 'r') as f:
                return json.load(f)
        return None
    
    def get_historical_data(self, days=7):
        """
        Get historical power usage data for the specified number of days.
        
        Args:
            days (int): Number of days of historical data to retrieve
            
        Returns:
            pd.DataFrame: Historical power usage data
        """
        files = []
        for filename in os.listdir(self.data_dir):
            if filename.startswith("meridian_data_") and filename.endswith(".csv"):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    # Extract date from filename
                    date_str = filename.split("_")[2].split(".")[0]
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    
                    if file_date >= datetime.now() - timedelta(days=days):
                        files.append(filepath)
                except ValueError:
                    # Skip files with invalid date format
                    continue
        
        if not files:
            return pd.DataFrame()
        
        # Combine all files into a single DataFrame
        dfs = []
        for file in files:
            try:
                df = pd.read_csv(file)
                dfs.append(df)
            except Exception as e:
                logger.error(f"Error reading {file}: {e}")
                continue
        
        if dfs:
            return pd.concat(dfs).drop_duplicates()
        else:
            return pd.DataFrame()


# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    email = os.getenv("MERIDIAN_EMAIL")
    password = os.getenv("MERIDIAN_PASSWORD")
    
    if not email or not password:
        logger.error("Meridian Energy credentials not found in environment variables")
        exit(1)
    
    scraper = MeridianEnergyScraper(email, password, headless=False)
    data = scraper.run()
    
    if data:
        logger.info("Successfully scraped power usage data")
        print(json.dumps(data, indent=2))
    else:
        logger.error("Failed to scrape power usage data")
