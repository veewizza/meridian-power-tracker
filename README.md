# Meridian Energy Power Tracker

A Docker container that logs into Meridian Energy's website hourly to retrieve power usage data. It includes a web interface for monitoring and debugging during development, with future capability to send data to Home Assistant.

## Features

- **Automated Data Collection**: Logs into Meridian Energy's website and scrapes power usage data at configurable intervals
- **Web Dashboard**: Provides a user-friendly interface to view and analyze your power usage data
- **Data Visualization**: Displays your power usage in charts and tables
- **Historical Data**: Stores and allows you to view historical power usage data
- **Manual Scraping**: Trigger data collection manually when needed
- **Home Assistant Integration**: Prepared for future integration with Home Assistant

## Prerequisites

- Docker and Docker Compose installed on your system
- Meridian Energy account credentials
- Internet connection to access the Meridian Energy website

## Setup Instructions

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd meridian-power-tracker
   ```

2. **Configure environment variables**

   Copy the example environment file and edit it with your credentials:

   ```bash
   cp .env.example .env
   ```

   Edit the `.env` file and add your Meridian Energy login credentials:

   ```
   MERIDIAN_EMAIL=your_email@example.com
   MERIDIAN_PASSWORD=your_password
   ```

3. **Build and start the container**

   ```bash
   docker-compose up -d
   ```

   This will build the Docker image and start the container in the background.

4. **Access the web interface**

   Open your browser and navigate to:

   ```
   http://localhost:8080
   ```

## Configuration Options

The following environment variables can be configured in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `MERIDIAN_EMAIL` | Your Meridian Energy account email | (Required) |
| `MERIDIAN_PASSWORD` | Your Meridian Energy account password | (Required) |
| `SCRAPE_INTERVAL` | Interval between data scrapes in minutes | 60 |
| `WEB_PORT` | Port for the web interface | 8080 |
| `DEBUG_MODE` | Enable debug mode for more verbose logging | true |
| `DATA_RETENTION_DAYS` | Number of days to retain historical data | 30 |
| `HEADLESS` | Run browser in headless mode | true |
| `HASS_URL` | Home Assistant URL (for future integration) | http://homeassistant.local:8123 |
| `HASS_TOKEN` | Home Assistant long-lived access token | (Optional) |

## Usage

### Web Interface

The web interface provides several features:

- **System Status**: View the current status of the scraper, last update time, and next scheduled run
- **Manual Scrape**: Trigger a data scrape manually
- **Latest Data**: View the most recent power usage data in chart or table format
- **Historical Data**: View and analyze historical power usage data
- **Raw Data**: Access the raw JSON data for debugging

### Data Files

All scraped data is stored in the `data` directory, which is mounted as a volume in the Docker container. This ensures that your data persists even if the container is restarted or rebuilt.

## Home Assistant Integration

The system is designed to be integrated with Home Assistant in the future. Once implemented, it will send power usage data to Home Assistant, allowing you to:

- Create automations based on power usage
- Set up notifications for high usage periods
- Integrate power usage data with other smart home systems

To enable Home Assistant integration, set the `HASS_URL` and `HASS_TOKEN` environment variables in the `.env` file.

## Troubleshooting

### Common Issues

1. **Login Failures**:
   - Ensure your Meridian Energy credentials are correct
   - Check if Meridian Energy's website structure has changed, which might require an update to the scraper

2. **No Data Collected**:
   - Check the logs for any errors: `docker-compose logs`
   - Try running a manual scrape from the web interface
   - Verify your internet connection

3. **Container Not Starting**:
   - Ensure Docker and Docker Compose are installed correctly
   - Check if the required ports are available

### Viewing Logs

To view the container logs:

```bash
docker-compose logs -f
```

## Development

If you want to modify the code or contribute to the project:

1. Make your changes to the code
2. Rebuild the Docker image:

   ```bash
   docker-compose build
   ```

3. Restart the container:

   ```bash
   docker-compose up -d
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- This project uses [Playwright](https://playwright.dev/) for web automation
- Web interface built with [Flask](https://flask.palletsprojects.com/) and [Bootstrap](https://getbootstrap.com/)
- Charts created with [Chart.js](https://www.chartjs.org/)
