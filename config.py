"""
Configuration file for Frankfurt Flight Tracker
Modify these settings to customize the application behavior.
"""

# Target coordinates for monitoring (latitude, longitude)
TARGET_COORDS = (49.949857, 8.635253)

# Monitoring radius in kilometers
RADIUS_KM = 2.0

# Maximum altitude in feet (only aircraft below this altitude will be tracked)
MAX_ALTITUDE_FT = 6000

# Frankfurt Airport coordinates (for departure filtering)
FRA_AIRPORT_COORDS = (50.0379, 8.5622)

# Data collection interval in seconds
DATA_COLLECTION_INTERVAL = 10

# API Configuration
OPENSKY_API_URL = "https://opensky-network.org/api/states/all"
OPENSKY_USER_AGENT = "FlightTracker/1.0"
OPENSKY_USERNAME = "nicklasmw"
OPENSKY_PASSWORD = "gezqiJ-kufpe4-gujdah"

# Database Configuration
DATABASE_PATH = "data/flights.db"

# Web Server Configuration
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 8080
FLASK_DEBUG = True

# Frontend Configuration
FRONTEND_AUTO_REFRESH_INTERVAL = 30000  # milliseconds (30 seconds)

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Flight Data Filtering
# Countries to consider as "departing from FRA" (simplified approach)
FRA_DEPARTURE_COUNTRIES = ["Germany"]

# Minimum data quality requirements
MIN_ALTITUDE_METERS = 500  # Minimum altitude to consider valid data
MIN_SPEED_KTS = 0  # Minimum speed to consider valid data
MIN_ALTITUDE_FT = 1500

# Database retention settings
MAX_FLIGHTS_PER_DAY = 1000  # Maximum flights to store per day
DAYS_TO_RETAIN = 30  # Number of days to keep flight data 