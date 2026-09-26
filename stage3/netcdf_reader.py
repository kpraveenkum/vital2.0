"""
netcdf_reader.py

Stage 2:
Read real meteorological data from a NetCDF file.

Expected atmospheric variables:
    Temperature
    U wind
    V wind
    PBL height
    Surface radiation

Common variable names supported:
    Temperature:
        T2, t2, temperature, temp, tas

    U wind:
        U10, u10, u10m, wind_u

    V wind:
        V10, v10, v10m, wind_v

    PBL height:
        PBLH, pblh, PBL_height,
        planetary_boundary_layer_height,
        boundary_layer_height

    Radiation:
        SWDOWN, swdown, shortwave_radiation,
        surface_solar_radiation, ssrd,
        solar_radiation

Output:
    pandas.DataFrame
"""

from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


class NetCDFMeteorologyReader:

    def __init__(self, filepath):
        self.filepath = Path(filepath)

        if not self.filepath.exists():
            raise FileNotFoundError(
                f"NetCDF file not found:\n{self.filepath}"
            )

        self.ds = None
        self.data = None

    # ---------------------------------------------------------
    # OPEN DATASET
    # ---------------------------------------------------------

    def open(self):
        print("\nOpening NetCDF file...")
        print(f"File: {self.filepath}")

        self.ds = xr.open_dataset(self.filepath)

        print("\nDataset opened successfully.")

        print("\nDimensions:")
        for name, size in self.ds.sizes.items():
            print(f"  {name}: {size}")

        print("\nVariables:")
        for var in self.ds.data_vars:
            print(f"  {var}")

        return self.ds

    # ---------------------------------------------------------
    # FIND VARIABLE
    # ---------------------------------------------------------

    def find_variable(self, candidates, required=True):

        if self.ds is None:
            raise RuntimeError(
                "Dataset is not open. Call reader.open() first."
            )

        # Exact match
        for candidate in candidates:
            if candidate in self.ds.variables:
                return candidate

        # Case-insensitive match
        variable_map = {
            name.lower(): name
            for name in self.ds.variables
        }

        for candidate in candidates:
            if candidate.lower() in variable_map:
                return variable_map[candidate.lower()]

        # Partial match
        for name in self.ds.variables:

            name_lower = name.lower()

            for candidate in candidates:

                candidate_lower = candidate.lower()

                if candidate_lower in name_lower:
                    return name

        if required:
            raise ValueError(
                "\nCould not find required variable.\n"
                f"Possible names: {candidates}\n\n"
                f"Available variables:\n"
                f"{list(self.ds.variables)}"
            )

        return None

    # ---------------------------------------------------------
    # FIND TIME DIMENSION
    # ---------------------------------------------------------

    def find_time_coordinate(self):

        candidates = [
            "time",
            "Time",
            "datetime",
            "date",
            "valid_time"
        ]

        for name in candidates:

            if name in self.ds.coords:
                return name

            if name in self.ds.variables:
                return name

        # Search automatically
        for name in self.ds.coords:

            if "time" in name.lower():
                return name

        raise ValueError(
            "Could not identify time coordinate."
        )

    # ---------------------------------------------------------
    # CONVERT DATA TO TIME SERIES
    # ---------------------------------------------------------

    def to_timeseries(self):

        if self.ds is None:
            self.open()

        time_var = self.find_time_coordinate()

        print(f"\nTime coordinate: {time_var}")

        # -----------------------------------------------------
        # Identify variables
        # -----------------------------------------------------

        temperature_var = self.find_variable(
            [
                "T2",
                "t2",
                "temperature",
                "temp",
                "tas",
                "air_temperature"
            ]
        )

        u_var = self.find_variable(
            [
                "U10",
                "u10",
                "u10m",
                "wind_u",
                "u_wind"
            ]
        )

        v_var = self.find_variable(
            [
                "V10",
                "v10",
                "v10m",
                "wind_v",
                "v_wind"
            ]
        )

        pbl_var = self.find_variable(
            [
                "PBLH",
                "pblh",
                "PBL_height",
                "planetary_boundary_layer_height",
                "boundary_layer_height"
            ]
        )

        radiation_var = self.find_variable(
            [
                "SWDOWN",
                "swdown",
                "shortwave_radiation",
                "surface_solar_radiation",
                "ssrd",
                "solar_radiation"
            ]
        )

        print("\nVariables selected:")

        print(f"  Temperature : {temperature_var}")
        print(f"  U wind      : {u_var}")
        print(f"  V wind      : {v_var}")
        print(f"  PBL height  : {pbl_var}")
        print(f"  Radiation   : {radiation_var}")

        # -----------------------------------------------------
        # Extract data
        # -----------------------------------------------------

        T = self.ds[temperature_var]
        U = self.ds[u_var]
        V = self.ds[v_var]
        PBL = self.ds[pbl_var]
        RAD = self.ds[radiation_var]

        # -----------------------------------------------------
        # Spatial averaging
        # -----------------------------------------------------

        spatial_dims = []

        for dim in T.dims:

            if dim.lower() in [
                "lat",
                "latitude",
                "lon",
                "longitude",
                "x",
                "y"
            ]:

                spatial_dims.append(dim)

        if spatial_dims:

            print(
                "\nSpatial dimensions detected:"
            )

            for dim in spatial_dims:
                print(f"  {dim}")

            print(
                "\nCalculating spatial average..."
            )

            T = T.mean(dim=spatial_dims)
            U = U.mean(dim=spatial_dims)
            V = V.mean(dim=spatial_dims)
            PBL = PBL.mean(dim=spatial_dims)
            RAD = RAD.mean(dim=spatial_dims)

        # -----------------------------------------------------
        # Convert to pandas
        # -----------------------------------------------------

        df = pd.DataFrame(
            {
                "time": T[time_var].values,
                "temperature": T.values,
                "u_wind": U.values,
                "v_wind": V.values,
                "pbl_height": PBL.values,
                "radiation": RAD.values
            }
        )

        # -----------------------------------------------------
        # Remove extra dimensions if necessary
        # -----------------------------------------------------

        for column in [
            "temperature",
            "u_wind",
            "v_wind",
            "pbl_height",
            "radiation"
        ]:

            df[column] = np.asarray(
                df[column]
            ).squeeze()

        # -----------------------------------------------------
        # Temperature conversion
        # -----------------------------------------------------

        temperature_mean = np.nanmean(
            df["temperature"]
        )

        if temperature_mean > 150:

            print(
                "\nTemperature appears to be Kelvin."
            )

            df["temperature_K"] = (
                df["temperature"]
            )

            df["temperature_C"] = (
                df["temperature"] - 273.15
            )

        else:

            print(
                "\nTemperature appears to be Celsius."
            )

            df["temperature_C"] = (
                df["temperature"]
            )

            df["temperature_K"] = (
                df["temperature"] + 273.15
            )

        # -----------------------------------------------------
        # Wind speed
        # -----------------------------------------------------

        df["wind_speed"] = np.sqrt(
            df["u_wind"] ** 2 +
            df["v_wind"] ** 2
        )

        # -----------------------------------------------------
        # Wind direction
        # -----------------------------------------------------

        df["wind_direction"] = (
            np.degrees(
                np.arctan2(
                    -df["u_wind"],
                    -df["v_wind"]
                )
            ) + 360
        ) % 360

        # -----------------------------------------------------
        # PBL sanity check
        # -----------------------------------------------------

        df["pbl_height"] = (
            df["pbl_height"]
            .astype(float)
            .clip(lower=20)
        )

        # -----------------------------------------------------
        # Radiation sanity check
        # -----------------------------------------------------

        df["radiation"] = (
            df["radiation"]
            .astype(float)
            .clip(lower=0)
        )

        # -----------------------------------------------------
        # Sort by time
        # -----------------------------------------------------

        df["time"] = pd.to_datetime(
            df["time"]
        )

        df = df.sort_values(
            "time"
        )

        df = df.reset_index(
            drop=True
        )

        # -----------------------------------------------------
        # Interpolate missing values
        # -----------------------------------------------------

        numerical_columns = [
            "temperature_K",
            "temperature_C",
            "u_wind",
            "v_wind",
            "wind_speed",
            "wind_direction",
            "pbl_height",
            "radiation"
        ]

        for column in numerical_columns:

            df[column] = (
                df[column]
                .interpolate(
                    method="linear"
                )
                .ffill()
                .bfill()
            )

        self.data = df

        return df

    # ---------------------------------------------------------
    # SAVE PROCESSED DATA
    # ---------------------------------------------------------

    def save_csv(self, output_file):

        if self.data is None:
            self.to_timeseries()

        output_file = Path(output_file)

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.data.to_csv(
            output_file,
            index=False
        )

        print(
            f"\nProcessed data saved to:"
            f"\n{output_file}"
        )

    # ---------------------------------------------------------
    # SUMMARY
    # ---------------------------------------------------------

    def summary(self):

        if self.data is None:
            self.to_timeseries()

        print("\n" + "=" * 60)
        print("METEOROLOGICAL DATA SUMMARY")
        print("=" * 60)

        print(
            f"Start time : "
            f"{self.data['time'].min()}"
        )

        print(
            f"End time   : "
            f"{self.data['time'].max()}"
        )

        print(
            f"Records    : "
            f"{len(self.data)}"
        )

        print("\nTemperature:")
        print(
            f"  Min : "
            f"{self.data['temperature_C'].min():.2f} °C"
        )
        print(
            f"  Max : "
            f"{self.data['temperature_C'].max():.2f} °C"
        )

        print("\nWind:")
        print(
            f"  Min : "
            f"{self.data['wind_speed'].min():.2f} m/s"
        )
        print(
            f"  Max : "
            f"{self.data['wind_speed'].max():.2f} m/s"
        )

        print("\nPBL:")
        print(
            f"  Min : "
            f"{self.data['pbl_height'].min():.1f} m"
        )

        print(
            f"  Max : "
            f"{self.data['pbl_height'].max():.1f} m"
        )

        print("\nRadiation:")
        print(
            f"  Min : "
            f"{self.data['radiation'].min():.1f} W/m²"
        )

        print(
            f"  Max : "
            f"{self.data['radiation'].max():.1f} W/m²"
        )

        print("=" * 60)


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    FILE = Path(__file__).resolve().parent / "data" / "meteorology" / "weather.nc"

    reader = NetCDFMeteorologyReader(FILE)

    reader.open()

    df = reader.to_timeseries()

    reader.summary()

    reader.save_csv(
        Path(__file__).resolve().parent / "data" / "meteorology" / "processed_weather.csv"
    )

    print("\nFirst five records:")
    print(df.head())
