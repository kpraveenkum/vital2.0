"""
meteorology.py

Identifies and opens WRF meteorological output files for forecast initialization and coupling.
"""

from pathlib import Path
import xarray as xr


def find_wrf_outputs(wrf_directory):
    directory = Path(wrf_directory)
    files = sorted(directory.glob("wrfout_d01_*"))

    if not files:
        raise FileNotFoundError(f"No WRF files found in {directory}")

    return files


def open_wrf(file_path):
    return xr.open_dataset(file_path)


def inspect_wrf(file_path):
    ds = open_wrf(file_path)
    information = {
        "file": str(file_path),
        "dimensions": dict(ds.sizes),
        "variables": list(ds.variables),
    }
    ds.close()
    return information


def combine_wrf_files(files):
    datasets = []
    for file_path in files:
        datasets.append(xr.open_dataset(file_path))

    combined = xr.concat(datasets, dim="Time")

    for ds in datasets:
        ds.close()

    return combined
