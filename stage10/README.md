# Stage 10 — 24/48/72-Hour Delhi NCR Air-Quality Forecasting

## Overview
Automated operational 24/48/72-hour air quality forecasting pipeline with satellite fire emission decay forecasting, 72-hour concentration prediction, SQLite database storage (`forecast.db`), and horizon-based validation (24h, 48h, 72h lead times).

## Subdirectories & Files
- [`config/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage10/config): `forecast_config.py`
- [`ingestion/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage10/ingestion): `meteorology.py`, `air_quality.py`, `satellite_fire.py`
- [`emissions/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage10/emissions): `forecast_emissions.py`
- [`forecast/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage10/forecast): `forecast_24h.py`, `forecast_48h.py`, `forecast_72h.py`, `extract_forecast.py`
- [`wrfchem/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage10/wrfchem): `run_forecast.sh`
- [`validation/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage10/validation): `forecast_validation.py`
- [`database/`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage10/database): `forecast_storage.py`
- [`main_stage10.py`](file:///c:/Users/yashr/OneDrive/Desktop/SIH_VITAL_AIR/Backend/stage10/main_stage10.py)

## How to Run
```bash
py -3 main_stage10.py
```
