"""
forecast_24h.py

Filters and extracts 24-hour forecast window predictions.
"""

import pandas as pd


def extract_24h(forecast_df, start_time):
    start_time = pd.Timestamp(start_time)
    end_time = start_time + pd.Timedelta(hours=24)

    return forecast_df[
        (forecast_df["datetime"] >= start_time) & (forecast_df["datetime"] <= end_time)
    ].copy()
