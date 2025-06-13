import os
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
from flask import Flask, render_template, jsonify, request, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from scraper import MeridianEnergyScraper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger('meridian_app')

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev_key')

# Initialize scraper
email = os.getenv("MERIDIAN_EMAIL")
password = os.getenv("MERIDIAN_PASSWORD")
headless = os.getenv("HEADLESS", "true").lower() == "true"

if not email or not password:
    logger.error("Meridian Energy credentials not found in environment variables")
    raise ValueError("Missing credentials. Please set MERIDIAN_EMAIL and MERIDIAN_PASSWORD in .env file")

scraper = MeridianEnergyScraper(email, password, headless=headless)

# Initialize scheduler
scheduler = BackgroundScheduler()
scrape_interval = int(os.getenv("SCRAPE_INTERVAL", "60"))  # Default to 60 minutes

# Data directory
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Home Assistant integration settings
hass_url = os.getenv("HASS_URL")
hass_token = os.getenv("HASS_TOKEN")


def scrape_data():
    """
    Scheduled function to scrape power usage data.
    """
    logger.info("Starting scheduled data scrape")
    try:
        data = scraper.run()
        if data:
            logger.info("Successfully scraped power usage data")
            
            # If Home Assistant integration is configured, send data
            if hass_url and hass_token:
                send_to_home_assistant(data)
        else:
            logger.error("Failed to scrape power usage data")
    except Exception as e:
        logger.error(f"Error during scheduled scrape: {e}")


def send_to_home_assistant(data):
    """
    Send power usage data to Home Assistant.
    This is a placeholder for future implementation.
    
    Args:
        data (dict): Power usage data to send
    """
    logger.info("Home Assistant integration not yet implemented")
    # TODO: Implement Home Assistant integration


# Set up scheduled job
scheduler.add_job(
    scrape_data, 
    'interval', 
    minutes=scrape_interval,
    next_run_time=datetime.now()  # Run immediately on startup
)


# Flask routes
@app.route('/')
def index():
    """
    Render the main dashboard page.
    """
    return render_template('index.html')


@app.route('/api/data/latest')
def get_latest_data():
    """
    API endpoint to get the latest power usage data.
    """
    data = scraper.get_latest_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({"error": "No data available"}), 404


@app.route('/api/data/history')
def get_historical_data():
    """
    API endpoint to get historical power usage data.
    """
    days = request.args.get('days', default=7, type=int)
    df = scraper.get_historical_data(days=days)
    
    if df.empty:
        return jsonify({"error": "No historical data available"}), 404
    
    # Convert DataFrame to JSON
    return jsonify(df.to_dict(orient='records'))


@app.route('/api/scrape/manual')
def manual_scrape():
    """
    API endpoint to manually trigger a data scrape.
    """
    try:
        data = scraper.run()
        if data:
            return jsonify({"status": "success", "message": "Successfully scraped data"})
        else:
            return jsonify({"status": "error", "message": "Failed to scrape data"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/data/<path:filename>')
def download_data(filename):
    """
    Endpoint to download data files.
    """
    return send_from_directory(data_dir, filename)


@app.route('/api/status')
def get_status():
    """
    API endpoint to get the status of the application.
    """
    # Get the timestamp of the latest data
    latest_filepath = os.path.join(data_dir, "latest_data.json")
    last_update = None
    
    if os.path.exists(latest_filepath):
        last_update = datetime.fromtimestamp(os.path.getmtime(latest_filepath)).isoformat()
    
    # Get the next scheduled run
    next_run = None
    for job in scheduler.get_jobs():
        next_run = job.next_run_time.isoformat()
        break
    
    # Count the number of data files
    data_files = [f for f in os.listdir(data_dir) if f.endswith('.json') and f != 'latest_data.json']
    
    return jsonify({
        "status": "running",
        "last_update": last_update,
        "next_scheduled_run": next_run,
        "data_files_count": len(data_files),
        "scrape_interval_minutes": scrape_interval,
        "home_assistant_integration": bool(hass_url and hass_token)
    })


if __name__ == "__main__":
    # Start the scheduler
    scheduler.start()
    logger.info("Scheduler started")
    
    # Start the Flask app
    port = int(os.getenv("WEB_PORT", "8080"))
    debug = os.getenv("DEBUG_MODE", "true").lower() == "true"
    
    logger.info(f"Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
