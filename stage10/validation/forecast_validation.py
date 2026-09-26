"""
forecast_validation.py

Statistical evaluation and horizon-based validation (24h, 48h, 72h lead times)
for air quality forecast predictions against ground observations.
"""

import numpy as np
import pandas as pd


def mae(prediction, observation):
    prediction = np.asarray(prediction, dtype=float)
    observation = np.asarray(observation, dtype=float)
    mask = np.isfinite(prediction) & np.isfinite(observation)
    if mask.sum() == 0:
        return np.nan
    return float(np.mean(np.abs(prediction[mask] - observation[mask])))


def rmse(prediction, observation):
    prediction = np.asarray(prediction, dtype=float)
    observation = np.asarray(observation, dtype=float)
    mask = np.isfinite(prediction) & np.isfinite(observation)
    if mask.sum() == 0:
        return np.nan
    return float(np.sqrt(np.mean((prediction[mask] - observation[mask]) ** 2)))


def bias(prediction, observation):
    prediction = np.asarray(prediction, dtype=float)
    observation = np.asarray(observation, dtype=float)
    mask = np.isfinite(prediction) & np.isfinite(observation)
    if mask.sum() == 0:
        return np.nan
    return float(np.mean(prediction[mask] - observation[mask]))


def correlation(prediction, observation):
    prediction = np.asarray(prediction, dtype=float)
    observation = np.asarray(observation, dtype=float)
    mask = np.isfinite(prediction) & np.isfinite(observation)
    if mask.sum() < 2:
        return np.nan
    return float(np.corrcoef(prediction[mask], observation[mask])[0, 1])


def calculate_metrics(prediction, observation):
    return {
        "MAE": mae(prediction, observation),
        "RMSE": rmse(prediction, observation),
        "Bias": bias(prediction, observation),
        "Correlation": correlation(prediction, observation),
    }


def align_forecast_observations(forecast, observations, tolerance_minutes=60):
    forecast = forecast.copy()
    observations = observations.copy()

    forecast["datetime"] = pd.to_datetime(forecast["datetime"])
    observations["datetime"] = pd.to_datetime(observations["datetime"])

    forecast = forecast.sort_values("datetime")
    observations = observations.sort_values("datetime")

    merged = pd.merge_asof(
        forecast,
        observations,
        on="datetime",
        direction="nearest",
        tolerance=pd.Timedelta(minutes=tolerance_minutes),
        suffixes=("_forecast", "_observation"),
    )

    return merged


def validate_by_horizon(comparison, start_time, pollutant):
    start_time = pd.Timestamp(start_time)
    comparison = comparison.copy()

    comparison["datetime"] = pd.to_datetime(comparison["datetime"])
    comparison["forecast_hour"] = (
        comparison["datetime"] - start_time
    ).dt.total_seconds() / 3600.0

    results = []
    horizons = [
        (0, 24, "24h"),
        (24, 48, "48h"),
        (48, 72, "72h"),
    ]

    for lower, upper, label in horizons:
        subset = comparison[
            (comparison["forecast_hour"] >= lower) & (comparison["forecast_hour"] <= upper)
        ]

        if subset.empty:
            continue

        prediction_column = None
        observation_column = None

        for pred_col in [f"{pollutant}_forecast", f"{pollutant}_model", pollutant]:
            if pred_col in subset.columns:
                prediction_column = pred_col
                break

        for obs_col in [f"{pollutant}_observation", f"{pollutant}_obs"]:
            if obs_col in subset.columns:
                observation_column = obs_col
                break

        if prediction_column is None or observation_column is None:
            continue

        m = calculate_metrics(
            subset[prediction_column],
            subset[observation_column],
        )
        if not np.isnan(m["MAE"]):
            m["horizon"] = label
            m["pollutant"] = pollutant
            results.append(m)

    return pd.DataFrame(results)
