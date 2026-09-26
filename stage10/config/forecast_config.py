"""
forecast_config.py

Configuration parameters, spatial domain definitions, pollutant lists,
and directory paths for Stage 10 24/48/72-hour air quality forecasting.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------
# Forecast configuration
# ------------------------------------------------------------
FORECAST_HOURS = [24, 48, 72]
OUTPUT_INTERVAL_HOURS = 1
TIME_ZONE = "Asia/Kolkata"

# ------------------------------------------------------------
# Delhi NCR approximate study domain
# ------------------------------------------------------------
DOMAIN = {
    "lat_min": 27.0,
    "lat_max": 30.5,
    "lon_min": 75.5,
    "lon_max": 79.5,
}

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------
DATA_DIR = BASE_DIR / "data"
MET_DIR = DATA_DIR / "meteorology"
OBS_DIR = DATA_DIR / "observations"
SATELLITE_DIR = DATA_DIR / "satellite"
EMISSION_DIR = DATA_DIR / "emissions"

OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------
# Pollutants & Thresholds
# ------------------------------------------------------------
POLLUTANTS = ["PM25", "PM10", "NO2", "O3", "CO"]
EPISODE_THRESHOLD_PM25 = 250.0


def print_config():
    print("Stage 10 Forecast Configuration")
    print("-------------------------------")
    print("Forecast hours:", FORECAST_HOURS)
    print("Time zone:     ", TIME_ZONE)
    print("Domain:        ", DOMAIN)
    print("Pollutants:    ", POLLUTANTS)
