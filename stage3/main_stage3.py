"""
main_stage3.py

Stage 3 — Air Quality Observations + Model Validation

Handles two input formats:
  A) Time-series: datetime + PM25, PM10, NO2, O3, CO
  B) Station snapshot: name, lat, lon, pm25, pm10, no2, o3, co, aqi

For format B, synthesizes a "now" timestamp.
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
from datetime import datetime

STAGE3_DIR = Path(__file__).resolve().parent
BACKEND_DIR = STAGE3_DIR.parent

if str(STAGE3_DIR) not in sys.path:
    sys.path.insert(0, str(STAGE3_DIR))

AIR_QUALITY_FILE = BACKEND_DIR / "data" / "air_quality" / "delhi_air_quality.csv"
OBSERVATIONS_FILE = BACKEND_DIR / "data" / "observations" / "air_quality.csv"
OUTPUT_DIR = BACKEND_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_air_quality():
    candidates = [OBSERVATIONS_FILE, AIR_QUALITY_FILE]

    for path in candidates:
        if not path.exists():
            continue

        print(f"✅ Using: {path}")
        try:
            df = pd.read_csv(path)
        except Exception as e:
            print(f"⚠️  Cannot read: {e}")
            continue

        print(f"   Columns: {list(df.columns)}")
        print(f"   Rows: {len(df)}")

        has_time = any(
            c.lower() in ("datetime", "time", "timestamp", "date", "date_time")
            for c in df.columns
        )

        if has_time:
            print("   Format: time-series")
            return normalize_timeseries(df)

        print("   Format: station snapshot (no time column)")
        return normalize_snapshot(df)

    raise FileNotFoundError(
        f"No air quality file found.\n"
        f"Looked in: {candidates}\n"
        f"Run POST /api/sync-from-s3 or wait for ingest-sensors Lambda."
    )


def normalize_timeseries(df):
    rename = {}
    for c in df.columns:
        low = c.lower().strip()
        if low in ("datetime", "time", "timestamp", "date", "date_time"):
            rename[c] = "time"
        elif low in ("pm25", "pm2.5", "pm_2_5"):
            rename[c] = "PM25"
        elif low in ("pm10", "pm_10"):
            rename[c] = "PM10"
        elif low in ("no2", "nitrogen_dioxide"):
            rename[c] = "NO2"
        elif low in ("o3", "ozone"):
            rename[c] = "O3"
        elif low in ("co", "carbon_monoxide"):
            rename[c] = "CO"

    df = df.rename(columns=rename)
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"])

    cols = ["time"] + [c for c in ["PM25", "PM10", "NO2", "O3", "CO"] if c in df.columns]
    return df[cols]


def normalize_snapshot(df):
    rename = {}
    for c in df.columns:
        low = c.lower().strip()
        if low in ("pm25", "pm2.5", "pm_2_5"):
            rename[c] = "PM25"
        elif low in ("pm10", "pm_10"):
            rename[c] = "PM10"
        elif low in ("no2", "nitrogen_dioxide"):
            rename[c] = "NO2"
        elif low in ("o3", "ozone"):
            rename[c] = "O3"
        elif low in ("co", "carbon_monoxide"):
            rename[c] = "CO"
        elif low in ("name", "station", "site"):
            rename[c] = "station"

    df = df.rename(columns=rename)

    df["time"] = pd.Timestamp.utcnow().floor("h").tz_localize(None)

    cols = ["time"] + [c for c in ["PM25", "PM10", "NO2", "O3", "CO"] if c in df.columns]
    if "station" in df.columns:
        cols.append("station")

    result = df[cols].copy()

    if "PM25" in result.columns:
        result = result[(result["PM25"].isna()) | ((result["PM25"] >= 0) & (result["PM25"] <= 500))]
    if "PM10" in result.columns:
        result = result[(result["PM10"].isna()) | ((result["PM10"] >= 0) & (result["PM10"] <= 1000))]
    if "CO" in result.columns:
        result = result[(result["CO"].isna()) | ((result["CO"] >= 0) & (result["CO"] <= 50))]

    return result


def prepare_observations(df):
    numeric_cols = [c for c in ["PM25", "PM10", "NO2", "O3", "CO"] if c in df.columns]

    if not numeric_cols:
        raise ValueError("No pollutant columns in observations")

    regional = (
        df
        .set_index("time")[numeric_cols]
        .resample("1h")
        .mean()
        .reset_index()
    )

    print(f"\nRegional hourly: {len(regional)} rows")
    for c in numeric_cols:
        if regional[c].notna().any():
            print(f"   {c}: mean = {regional[c].mean():.2f}")

    return regional


def validate_forecast(forecast_df, observations):
    if forecast_df is None or forecast_df.empty:
        return None

    fc = forecast_df.copy()
    if "datetime" in fc.columns:
        fc = fc.rename(columns={"datetime": "time"})
    fc["time"] = pd.to_datetime(fc["time"])

    obs = observations.copy()
    obs["time"] = pd.to_datetime(obs["time"])

    comparison = pd.merge_asof(
        fc.sort_values("time"),
        obs.sort_values("time"),
        on="time",
        direction="nearest",
        tolerance=pd.Timedelta("2h"),
        suffixes=("_model", "_obs"),
    )

    print(f"Comparison rows: {len(comparison)}")

    metrics = []
    for pollutant in ["PM25", "PM10", "NO2", "O3", "CO"]:
        model_col = pollutant
        obs_col = f"{pollutant}_obs"

        if model_col not in comparison.columns:
            continue
        if obs_col not in comparison.columns:
            continue

        m = comparison[model_col].values
        o = comparison[obs_col].values
        mask = np.isfinite(m) & np.isfinite(o)
        m, o = m[mask], o[mask]

        if len(m) < 2:
            continue

        err = m - o
        metrics.append({
            "pollutant": pollutant,
            "N": len(m),
            "MAE": round(float(np.mean(np.abs(err))), 2),
            "RMSE": round(float(np.sqrt(np.mean(err ** 2))), 2),
            "Bias": round(float(np.mean(err)), 2),
            "Correlation": round(
                float(np.corrcoef(o, m)[0, 1]) if np.std(o) > 0 and np.std(m) > 0 else float("nan"),
                3,
            ),
        })

    return pd.DataFrame(metrics) if metrics else None


def main():
    print("=" * 60)
    print("STAGE 3 — AIR QUALITY VALIDATION")
    print("=" * 60)

    df = load_air_quality()
    observations = prepare_observations(df)

    clean_path = OUTPUT_DIR / "cleaned_air_quality.csv"
    observations.to_csv(clean_path, index=False)
    print(f"✅ Saved: {clean_path}")

    forecast_path = OUTPUT_DIR / "regional_forecast.csv"
    if not forecast_path.exists():
        print(f"\n⚠️  No forecast found: {forecast_path}")
        print("   Run Stage 10 first.")
        return

    forecast_df = pd.read_csv(forecast_path)
    print(f"✅ Loaded forecast: {len(forecast_df)} rows")

    metrics = validate_forecast(forecast_df, observations)

    if metrics is not None and not metrics.empty:
        metrics_path = OUTPUT_DIR / "validation_metrics.csv"
        metrics.to_csv(metrics_path, index=False)
        print(f"\n✅ Saved: {metrics_path}")
        print("\n" + metrics.to_string(index=False))
    else:
        print("\n⚠️  No overlapping data for validation")

    print("\n" + "=" * 60)
    print("Stage 3 complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
