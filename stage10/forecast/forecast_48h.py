"""
forecast_48h.py

Filters and extracts 48-hour forecast window predictions.
"""

import pandas as pd


def extract_48h(forecast_df, start_time):
    start_time = pd.Timestamp(start_time)
    end_time = start_time + pd.Timedelta(hours=48)

    return forecast_df[
        (forecast_df["datetime"] >= start_time) & (forecast_df["datetime"] <= end_time)
    ].copy()
