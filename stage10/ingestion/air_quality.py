"""
air_quality.py

Ingests real-time ground-level air quality station observations for forecast evaluation & initialization.
"""

from pathlib import Path
import pandas as pd


class AirQualityReader:

    def __init__(self, file_path):
        self.file_path = Path(file_path)

    def read(self):
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")

        df = pd.read_csv(self.file_path)

        time_candidates = [
            "datetime",
            "timestamp",
            "DateTime",
            "date_time",
            "time",
            "date",
        ]

        time_column = None
        for column in time_candidates:
            if column in df.columns:
                time_column = column
                break

        if time_column is None:
            raise ValueError("No datetime column found.")

        df["datetime"] = pd.to_datetime(df[time_column], errors="coerce")

        pollutant_aliases = {
            "PM25": ["PM25", "PM2.5", "pm25", "pm2.5", "PM_2_5"],
            "PM10": ["PM10", "pm10", "PM_10"],
            "NO2": ["NO2", "no2", "Nitrogen Dioxide"],
            "O3": ["O3", "o3", "Ozone", "ozone"],
            "CO": ["CO", "co", "Carbon Monoxide"],
        }

        for standard, aliases in pollutant_aliases.items():
            for alias in aliases:
                if alias in df.columns:
                    df[standard] = pd.to_numeric(df[alias], errors="coerce")
                    break

        df = df.dropna(subset=["datetime"])

        for pollutant in pollutant_aliases:
            if pollutant in df.columns:
                df.loc[df[pollutant] < 0, pollutant] = float("nan")

        return df


def hourly_average(df):
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = (
        df.set_index("datetime")
        .resample("1h")
        .mean(numeric_only=True)
        .reset_index()
    )
    return df
