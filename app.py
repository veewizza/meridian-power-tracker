from flask import Flask, jsonify, request, render_template, send_from_directory
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from scraper import MeridianEnergyScraper
from dotenv import load_dotenv
import os
import json
import logging

# Load environment variables
load_dotenv()
EMAIL = os.getenv("MERIDIAN_EMAIL")
PASSWORD = os.getenv("MERIDIAN_PASSWORD")
SCRAPE_INTERVAL = int(os.getenv("SCRAPE_INTERVAL", "60"))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Helper to get latest data
def get_latest_data():
    latest_path = os.path.join(DATA_DIR, "latest_data.json")
    if os.path.exists(latest_path):
        with open(latest_path) as f:
            return json.load(f)
    return {}

# Helper to get historical data
def get_historical_data(days=7):
    cutoff = datetime.now() - timedelta(days=days)
    data = []
    for fname in os.listdir(DATA_DIR):
        if fname.startswith("meridian_data_") and fname.endswith(".json"):
            try:
                ts = fname.split("_")[2].split(".")[0]
                dt = datetime.strptime(ts, "%Y%m%d")
                if dt >= cutoff:
                    with open(os.path.join(DATA_DIR, fname)) as f:
                        d = json.load(f)
                        # Try to extract readings if present
                        readings = d.get("raw_data", {}).get("readings")
                        if readings:
                            data.extend(readings)
            except Exception:
                continue
    return data

# Helper to list data files
def list_data_files():
    files = []
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".json") and fname.startswith("meridian_data_"):
            path = os.path.join(DATA_DIR, fname)
            stat = os.stat(path)
            files.append({
                "filename": fname,
                "date": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size
            })
    files.sort(key=lambda x: x["date"], reverse=True)
    return files

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    # Dummy values for now
    last_update = None
    next_run = None
    try:
        latest = get_latest_data()
        last_update = latest.get("timestamp")
    except Exception:
        pass
    return jsonify({
        "status": "running",
        "last_update": last_update,
        "next_scheduled_run": next_run,
        "data_files_count": len(list_data_files()),
        "scrape_interval_minutes": SCRAPE_INTERVAL,
        "home_assistant_integration": False
    })

@app.route("/api/data/latest")
def api_data_latest():
    data = get_latest_data()
    if not data:
        return jsonify({"error": "No data"}), 404
    readings = data.get("raw_data", {}).get("readings")
    if readings:
        return jsonify({"readings": readings})
    return jsonify(data.get("raw_data", {}))

@app.route("/api/scrape/manual")
def api_scrape_manual():
    try:
        scraper = MeridianEnergyScraper(EMAIL, PASSWORD)
        scraper.run()
        return jsonify({"message": "Scrape completed"}), 200
    except Exception as e:
        logger.error(f"Manual scrape failed: {e}")
        return jsonify({"message": str(e)}), 500

@app.route("/api/data/history")
def api_data_history():
    try:
        days = int(request.args.get("days", 7))
        data = get_historical_data(days)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return jsonify([])

@app.route("/api/files")
def api_files():
    return jsonify(list_data_files())

@app.route("/data/<path:filename>")
def download_file(filename):
    return send_from_directory(DATA_DIR, filename, as_attachment=True)

# Schedule scraping
def scheduled_scrape():
    try:
        scraper = MeridianEnergyScraper(EMAIL, PASSWORD)
        scraper.run()
        logger.info("Scheduled scrape completed")
    except Exception as e:
        logger.error(f"Scheduled scrape failed: {e}")

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_scrape, 'interval', minutes=SCRAPE_INTERVAL)
scheduler.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('WEB_PORT', 8080)), debug=os.getenv('DEBUG_MODE', 'false').lower() == 'true')
