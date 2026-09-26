"""
forecast_emissions.py

Projects recent satellite fire activity forward over the 24/48/72-hour forecast window
using an exponential decay half-life persistence model.
"""

import numpy as np
import pandas as pd

POLLUTANT_COLUMNS = {
    "PM25": "PM25_emission_kg_s",
    "PM10": "PM10_emission_kg_s",
    "CO": "CO_emission_kg_s",
    "NOx": "NOx_emission_kg_s",
    "VOC": "VOC_emission_kg_s",
}


def recent_fire_activity(fires, forecast_start, lookback_hours=24):
    forecast_start = pd.Timestamp(forecast_start)
    lookback_start = forecast_start - pd.Timedelta(hours=lookback_hours)

    result = fires[
        (fires["datetime"] >= lookback_start) & (fires["datetime"] <= forecast_start)
    ].copy()

    return result


def apply_decay(emission, hours_since_detection, half_life_hours=6.0):
    decay = 0.5 ** (hours_since_detection / half_life_hours)
    return emission * decay


def generate_fire_forecast(fires, forecast_start, forecast_hours=72, interval_hours=1):
    forecast_start = pd.Timestamp(forecast_start)
    recent = recent_fire_activity(fires, forecast_start)

    if recent.empty:
        # If no recent subset matches, use all available fire detections
        recent = fires.copy()

    records = []
    for hour in range(0, forecast_hours, interval_hours):
        forecast_time = forecast_start + pd.Timedelta(hours=hour)

        for _, fire in recent.iterrows():
            hours_since_detection = (forecast_time - fire["datetime"]).total_seconds() / 3600.0
            if hours_since_detection < 0:
                hours_since_detection = hour

            record = {
                "datetime": forecast_time,
                "latitude": fire["latitude"],
                "longitude": fire["longitude"],
            }

            for pollutant, column in POLLUTANT_COLUMNS.items():
                if column in fire:
                    value = fire[column]
                elif f"{pollutant}_emission" in fire:
                    value = fire[f"{pollutant}_emission"]
                elif pollutant in fire:
                    value = fire[pollutant]
                else:
                    continue

                if pd.isna(value):
                    continue

                record[f"{pollutant}_emission_kg_s"] = apply_decay(
                    float(value), hours_since_detection
                )

            records.append(record)

    return pd.DataFrame(records)


def aggregate_forecast_emissions(df):
    if df.empty:
        return pd.DataFrame()

    numeric_columns = [c for c in df.columns if c.endswith("_emission_kg_s")]

    result = (
        df.groupby(
            ["datetime", "latitude", "longitude"],
            as_index=False,
        )[numeric_columns]
        .sum()
    )

    return result
