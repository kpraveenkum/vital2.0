"""
extract_forecast.py

Extracts regional surface pollutant and meteorological forecast timeseries
from WRF-Chem output NetCDF files across the 72-hour forecast horizon.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import xarray as xr

VARIABLES = {
    "temperature_C": ["T2"],
    "u_wind_m_s": ["U10"],
    "v_wind_m_s": ["V10"],
    "PBLH_m": ["PBLH"],
    "radiation_W_m2": ["SWDOWN"],
    "O3": ["o3", "O3"],
    "NO2": ["no2", "NO2"],
    "CO": ["co", "CO"],
    "PM25": [
        "PM2_5_DRY",
        "PM25",
        "pm25",
    ],
    "PM10": [
        "PM10",
        "pm10",
    ],
}


def find_variable(ds, candidates):
    for candidate in candidates:
        if candidate in ds.variables:
            return candidate
    return None


def extract_file(file_path):
    ds = xr.open_dataset(file_path)
    result = {}

    for output_name, candidates in VARIABLES.items():
        actual = find_variable(ds, candidates)
        if actual is None:
            continue

        values = ds[actual].values
        result[output_name] = values

    ds.close()
    return result


def safe_surface_average(values):
    values = np.asarray(values, dtype=float)

    # If 4D (Time, level, lat, lon), pick surface level 0
    if values.ndim == 4:
        values = values[:, 0, :, :]

    # Typical WRF surface variable: Time, south_north, west_east
    if values.ndim == 3:
        return np.nanmean(values, axis=(1, 2))

    if values.ndim == 2:
        return np.nanmean(values, axis=1)

    return values


def build_regional_forecast(wrf_files):
    records = []

    for file_path in wrf_files:
        ds = xr.open_dataset(file_path)

        if "XTIME" in ds.variables:
            times = ds["XTIME"].values
            times = [pd.Timestamp(t) for t in times]
        elif "Time" in ds.coords and pd.api.types.is_datetime64_any_dtype(ds.coords["Time"].values):
            times = [pd.Timestamp(t) for t in ds.coords["Time"].values]
        else:
            n_steps = ds.sizes.get("Time", 1)
            times = [pd.Timestamp("2026-10-15 00:00:00") + pd.Timedelta(hours=i) for i in range(n_steps)]

        extracted = {}
        for output_name, candidates in VARIABLES.items():
            actual = find_variable(ds, candidates)
            if actual is None:
                continue

            extracted[output_name] = safe_surface_average(ds[actual].values)

        n = max([len(values) for values in extracted.values()], default=len(times))

        for i in range(n):
            ts = times[i] if i < len(times) else times[-1]
            record = {
                "datetime": ts,
                "source_file": str(file_path),
                "time_index": i,
            }

            for variable, values in extracted.items():
                if i < len(values):
                    record[variable] = float(values[i])

            records.append(record)

        ds.close()

    return pd.DataFrame(records)


if __name__ == "__main__":
    directory = Path("WRF/run_forecast")
    files = sorted(directory.glob("wrfout_d01_*"))

    if files:
        result = build_regional_forecast(files)
        out_file = Path("outputs/regional_forecast.csv")
        out_file.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(out_file, index=False)
        print(result.head())
    else:
        print("No forecast files found in WRF/run_forecast.")
