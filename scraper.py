import asyncio
from playwright.async_api import async_playwright
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
MERIDIAN_EMAIL = os.getenv('MERIDIAN_EMAIL')
MERIDIAN_PASSWORD = os.getenv('MERIDIAN_PASSWORD')
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'

# Define the scraper function
async def scrape_data():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to Meridian Energy login page
            logger.info("Navigating to Meridian Energy secure login")
            await page.goto('https://nextgen.meridianenergy.co.nz/login')

            # Fill in email
            logger.info("Looking for email input field")
            await page.fill('input[type="email"]', MERIDIAN_EMAIL)
            logger.info("Found email field, filling it")

            # Click submit button
            logger.info("Clicking submit button: input[type='submit']")
            await page.click('input[type="submit"]')

            # Fill in password
            logger.info("Looking for password input field")
            await page.fill('input[type="password"]', MERIDIAN_PASSWORD)
            logger.info("Found password field, filling it")

            # Click login button
            logger.info("Clicking login button: input[type='submit']")
            await page.click('input[type="submit"]')

            # Wait for login to complete
            logger.info("Waiting for login to complete")
            await page.wait_for_selector('.dashboard', timeout=60000)

            # Make API request to fetch usage data
            logger.info("Fetching usage data from API")
            response = await page.request.get(
                'https://nextgen.meridianenergy.co.nz/api/v1/usage/me?startDate=2025-06-12&endDate=2025-06-13&returnAllU'
            )
            data = await response.json()

            # Save the data to a JSON file
            os.makedirs('data', exist_ok=True)
            with open('data/usage_data.json', 'w') as f:
                json.dump(data, f, indent=4)
            logger.info("Usage data saved to data/usage_data.json")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")

        finally:
            await browser.close()

# Run the scraper function
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(scrape_data())
