"""
wrfchem_feedback_reader.py

NetCDF output reader class for two-way aerosol-meteorology feedback experiments.
"""

from pathlib import Path
import xarray as xr


class FeedbackReader:

    def __init__(self, file_path):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"File not found: {self.file_path}")
        self.ds = None

    def open(self):
        self.ds = xr.open_dataset(self.file_path)
        return self.ds

    def has_variable(self, name):
        if self.ds is None:
            self.open()
        return name in self.ds.variables

    def get(self, name):
        if self.ds is None:
            self.open()
        if name not in self.ds:
            raise KeyError(f"{name} not found in WRF-Chem output.")
        return self.ds[name]

    def variables(self):
        if self.ds is None:
            self.open()
        return list(self.ds.variables)

    def close(self):
        if self.ds is not None:
            self.ds.close()
