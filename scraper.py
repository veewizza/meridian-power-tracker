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
                browser = playwright.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 800},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                
                # Enable request interception for API calls
                page = context.new_page()
                page.on("response", self._handle_response)
                
                # Navigate to the login page
                logger.info("Navigating to Meridian Energy dashboard")
                page.goto("https://nextgen.meridianenergy.co.nz/dashboard")
                
                # Wait for login form to appear
                logger.info("Waiting for login form")
                page.wait_for_selector('input[type="email"]')
                
                # Fill in login credentials
                logger.info("Filling in login credentials")
                page.fill('input[type="email"]', self.email)
                page.click('button[type="submit"]')
                
                # Wait for password field and fill it
                page.wait_for_selector('input[type="password"]')
                page.fill('input[type="password"]', self.password)
                page.click('button[type="submit"]')
                
                # Wait for dashboard to load
                logger.info("Waiting for dashboard to load")
                page.wait_for_selector('.dashboard-container', timeout=30000)
                
                # Wait for data to load (adjust selector based on actual page structure)
                logger.info("Waiting for power usage data to load")
                page.wait_for_selector('.usage-data', timeout=30000)
                
                # Wait a bit to ensure all API calls are completed
                time.sleep(5)
                
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
    
    def _handle_response(self, response):
        """
        Handle API responses to capture power usage data.
        
        Args:
            response: Playwright response object
        """
        # Check if this is the API response containing power usage data
        # You'll need to identify the correct API endpoint by observing network traffic
        if "api/usage/hourly" in response.url or "api/consumption" in response.url:
            try:
                data = response.json()
                logger.info(f"Captured power usage data from {response.url}")
                
                # Process and store the data
                self._process_data(data)
                
            except Exception as e:
                logger.error(f"Error processing API response: {e}")
    
    def _process_data(self, data):
        """
        Process and store the power usage data.
        
        Args:
            data (dict): The raw power usage data from the API
        """
        # Store the latest data
        self.latest_data = data
        
        # Save raw data to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"meridian_data_{timestamp}.json"
        filepath = os.path.join(self.data_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved raw data to {filepath}")
        
        # Also save the latest data to a fixed filename for easy access
        latest_filepath = os.path.join(self.data_dir, "latest_data.json")
        with open(latest_filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        # Convert to pandas DataFrame for analysis (structure depends on actual data format)
        try:
            # This is a placeholder - adjust based on actual data structure
            if 'readings' in data:
                df = pd.DataFrame(data['readings'])
                
                # Save to CSV
                csv_filepath = os.path.join(self.data_dir, f"meridian_data_{timestamp}.csv")
                df.to_csv(csv_filepath, index=False)
                logger.info(f"Saved processed data to {csv_filepath}")
                
                # Also save to latest CSV
                latest_csv = os.path.join(self.data_dir, "latest_data.csv")
                df.to_csv(latest_csv, index=False)
        except Exception as e:
            logger.error(f"Error converting data to DataFrame: {e}")
    
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
        # This is a placeholder - implement based on how you store historical data
        files = []
        for filename in os.listdir(self.data_dir):
            if filename.startswith("meridian_data_") and filename.endswith(".csv"):
                filepath = os.path.join(self.data_dir, filename)
                file_date = datetime.strptime(filename.split("_")[2].split(".")[0], "%Y%m%d")
                
                if file_date >= datetime.now() - timedelta(days=days):
                    files.append(filepath)
        
        if not files:
            return pd.DataFrame()
        
        # Combine all files into a single DataFrame
        dfs = [pd.read_csv(file) for file in files]
        return pd.concat(dfs).drop_duplicates()


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
    else:
        logger.error("Failed to scrape power usage data")
