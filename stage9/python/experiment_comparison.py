"""
experiment_comparison.py

Loads and compares surface meteorological and chemical variables between CONTROL and FEEDBACK NetCDF datasets.
"""

from pathlib import Path
import numpy as np
import xarray as xr


def load_dataset(file_path):
    return xr.open_dataset(file_path)


def find_variable(dataset, candidates):
    for candidate in candidates:
        if candidate in dataset.variables:
            return candidate
    return None


def load_surface_variables(file_path):
    ds = load_dataset(file_path)

    variable_map = {
        "T2": ["T2"],
        "U10": ["U10"],
        "V10": ["V10"],
        "PBLH": ["PBLH"],
        "SWDOWN": ["SWDOWN"],
        "O3": ["o3", "O3"],
        "NO2": ["no2", "NO2"],
        "CO": ["co", "CO"],
        "PM25": [
            "PM2_5_DRY",
            "PM25",
            "pm25",
        ],
    }

    result = {}
    for output_name, candidates in variable_map.items():
        actual = find_variable(ds, candidates)
        if actual is None:
            continue

        val = ds[actual].values
        # If 4D (Time, level, lat, lon), select surface level 0
        if val.ndim == 4:
            val = val[:, 0, :, :]
        result[output_name] = val

    ds.close()
    return result


def compare(control_file, feedback_file):
    control = load_surface_variables(control_file)
    feedback = load_surface_variables(feedback_file)

    common = sorted(set(control) & set(feedback))
    result = {}

    for variable in common:
        result[variable] = {
            "control": control[variable],
            "feedback": feedback[variable],
            "difference": feedback[variable] - control[variable],
        }

    return result
