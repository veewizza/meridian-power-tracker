from flask import Flask, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
import logging
import asyncio
from scraper import scrape_data

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load usage data from JSON file
def load_usage_data():
    try:
        with open('data/usage_data.json', 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        logger.error("Usage data file not found.")
        return {}

# Endpoint to get usage data
@app.route('/data', methods=['GET'])
def get_usage_data():
    data = load_usage_data()
    return jsonify(data)

# Endpoint to trigger scraping manually
@app.route('/scrape', methods=['POST'])
def trigger_scrape():
    try:
        asyncio.run(scrape_data())
        return jsonify({"message": "Scraping triggered successfully."}), 200
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        return jsonify({"message": "Error during scraping."}), 500

# Schedule scraping every hour
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: asyncio.run(scrape_data()), 'interval', hours=1)
scheduler.start()

# Start the Flask app
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('WEB_PORT', 8080)),
        debug=os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    )
