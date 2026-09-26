"""
satellite_fire.py

Ingests satellite-detected active fire products (VIIRS / MODIS / FIRMS) for forecast emission projection.
"""

from pathlib import Path
import pandas as pd


class SatelliteFireReader:

    def __init__(self, file_path):
        self.file_path = Path(file_path)

    def read(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        df = pd.read_csv(self.file_path)

        # Coordinate column resolution
        lat_col = "latitude" if "latitude" in df.columns else ("lat" if "lat" in df.columns else None)
        lon_col = "longitude" if "longitude" in df.columns else ("lon" if "lon" in df.columns else None)

        if lat_col is None or lon_col is None:
            raise ValueError("Missing latitude/longitude columns in fire data.")

        df["latitude"] = pd.to_numeric(df[lat_col], errors="coerce")
        df["longitude"] = pd.to_numeric(df[lon_col], errors="coerce")

        # Datetime column resolution
        time_col = None
        for candidate in ["datetime", "acq_date", "timestamp", "time", "date"]:
            if candidate in df.columns:
                time_col = candidate
                break

        if time_col is None:
            raise ValueError("Missing datetime column in fire data.")

        df["datetime"] = pd.to_datetime(df[time_col], errors="coerce")

        if "frp" in df.columns:
            df["frp"] = pd.to_numeric(df["frp"], errors="coerce")

        df = df.dropna(subset=["latitude", "longitude", "datetime"])
        return df


def fires_for_forecast(fires, start_time, end_time):
    start_time = pd.Timestamp(start_time)
    end_time = pd.Timestamp(end_time)

    return fires[
        (fires["datetime"] >= start_time) & (fires["datetime"] <= end_time)
    ].copy()
