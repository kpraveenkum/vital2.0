"""
air_quality_reader.py

STAGE 3
Real Air-Quality Observation Reader

Purpose:
    Read real air-quality monitoring observations.

Supported pollutants:
    PM2.5
    PM10
    NO2
    O3
    NO

The reader attempts to recognize common column names
automatically.

Example input:

    datetime, station, PM2.5, PM10, NO2, O3
    2026-01-01 00:00, Delhi, 180, 250, 65, 22
    2026-01-01 01:00, Delhi, 175, 245, 60, 24

IMPORTANT:
    The observations must come from a real monitoring
    dataset. Do not use synthetic values for actual
    validation.
"""

from pathlib import Path

import numpy as np
import pandas as pd


class AirQualityReader:

    def __init__(self, filepath):

        self.filepath = Path(filepath)

        if not self.filepath.exists():

            raise FileNotFoundError(
                f"\nAir-quality file not found:\n"
                f"{self.filepath}"
            )

        self.raw_data = None
        self.data = None

    # =========================================================
    # LOAD CSV
    # =========================================================

    def load(self):

        print("\n")
        print("=" * 70)
        print("LOADING AIR-QUALITY DATA")
        print("=" * 70)

        print(
            f"\nFile: {self.filepath}"
        )

        self.raw_data = pd.read_csv(
            self.filepath
        )

        print(
            f"\nRows: {len(self.raw_data)}"
        )

        print("\nColumns:")

        for column in self.raw_data.columns:

            print(
                f"  {column}"
            )

        return self.raw_data

    # =========================================================
    # FIND COLUMN
    # =========================================================

    def find_column(
        self,
        candidates,
        required=False
    ):

        if self.raw_data is None:

            self.load()

        columns = list(
            self.raw_data.columns
        )

        # Exact match
        for candidate in candidates:

            if candidate in columns:

                return candidate

        # Case-insensitive
        lower_map = {
            str(column).lower().strip(): column
            for column in columns
        }

        for candidate in candidates:

            key = (
                candidate
                .lower()
                .strip()
            )

            if key in lower_map:

                return lower_map[key]

        # Remove spaces and punctuation
        normalized = {}

        for column in columns:

            key = (
                str(column)
                .lower()
                .replace(" ", "")
                .replace("_", "")
                .replace("-", "")
                .replace(".", "")
            )

            normalized[key] = column

        for candidate in candidates:

            key = (
                candidate
                .lower()
                .replace(" ", "")
                .replace("_", "")
                .replace("-", "")
                .replace(".", "")
            )

            if key in normalized:

                return normalized[key]

        if required:

            raise ValueError(
                "\nRequired column not found.\n"
                f"Possible names: {candidates}\n\n"
                f"Available columns:\n{columns}"
            )

        return None

    # =========================================================
    # IDENTIFY COLUMNS
    # =========================================================

    def identify_columns(self):

        if self.raw_data is None:

            self.load()

        self.time_column = self.find_column(
            [
                "datetime",
                "date_time",
                "date time",
                "timestamp",
                "time",
                "Date",
                "DateTime"
            ],
            required=True
        )

        self.station_column = self.find_column(
            [
                "station",
                "station_name",
                "stationname",
                "site",
                "site_name",
                "location"
            ],
            required=False
        )

        self.pm25_column = self.find_column(
            [
                "PM2.5",
                "PM25",
                "PM_2_5",
                "pm2.5",
                "pm25",
                "PM2_5"
            ],
            required=False
        )

        self.pm10_column = self.find_column(
            [
                "PM10",
                "pm10",
                "PM_10"
            ],
            required=False
        )

        self.no2_column = self.find_column(
            [
                "NO2",
                "NO2 (ug/m3)",
                "NO2_ug_m3",
                "no2",
                "nitrogen_dioxide"
            ],
            required=False
        )

        self.o3_column = self.find_column(
            [
                "O3",
                "o3",
                "Ozone",
                "ozone"
            ],
            required=False
        )

        self.no_column = self.find_column(
            [
                "NO",
                "no",
                "Nitric Oxide",
                "nitric_oxide"
            ],
            required=False
        )

        print("\nColumn mapping:")

        print(
            f"  Time   : {self.time_column}"
        )

        print(
            f"  Station: {self.station_column}"
        )

        print(
            f"  PM2.5  : {self.pm25_column}"
        )

        print(
            f"  PM10   : {self.pm10_column}"
        )

        print(
            f"  NO2    : {self.no2_column}"
        )

        print(
            f"  O3     : {self.o3_column}"
        )

        print(
            f"  NO     : {self.no_column}"
        )

    # =========================================================
    # PREPROCESS
    # =========================================================

    def preprocess(self):

        if self.raw_data is None:

            self.load()

        self.identify_columns()

        df = pd.DataFrame()

        # -----------------------------------------------------
        # Time
        # -----------------------------------------------------

        df["time"] = pd.to_datetime(
            self.raw_data[
                self.time_column
            ],
            errors="coerce"
        )

        # -----------------------------------------------------
        # Station
        # -----------------------------------------------------

        if self.station_column is not None:

            df["station"] = (
                self.raw_data[
                    self.station_column
                ]
                .astype(str)
                .str.strip()
            )

        else:

            df["station"] = "Unknown"

        # -----------------------------------------------------
        # Pollutants
        # -----------------------------------------------------

        pollutant_mapping = {

            "PM25": self.pm25_column,

            "PM10": self.pm10_column,

            "NO2": self.no2_column,

            "O3": self.o3_column,

            "NO": self.no_column
        }

        for output_name, input_column in (
            pollutant_mapping.items()
        ):

            if input_column is not None:

                df[output_name] = pd.to_numeric(
                    self.raw_data[
                        input_column
                    ],
                    errors="coerce"
                )

            else:

                df[output_name] = np.nan

        # -----------------------------------------------------
        # Remove invalid timestamps
        # -----------------------------------------------------

        df = df.dropna(
            subset=["time"]
        )

        # -----------------------------------------------------
        # Sort
        # -----------------------------------------------------

        df = df.sort_values(
            "time"
        )

        df = df.reset_index(
            drop=True
        )

        # -----------------------------------------------------
        # Remove physically invalid values
        # -----------------------------------------------------

        pollutants = [
            "PM25",
            "PM10",
            "NO2",
            "O3",
            "NO"
        ]

        for pollutant in pollutants:

            df.loc[
                df[pollutant] < 0,
                pollutant
            ] = np.nan

        # -----------------------------------------------------
        # Extreme value protection
        #
        # These are conservative cleaning limits.
        # Adjust them according to the source dataset
        # documentation when appropriate.
        # -----------------------------------------------------

        limits = {

            "PM25": 2000,
            "PM10": 5000,
            "NO2": 2000,
            "O3": 1000,
            "NO": 2000
        }

        for pollutant, limit in limits.items():

            df.loc[
                df[pollutant] > limit,
                pollutant
            ] = np.nan

        self.data = df

        return df

    # =========================================================
    # SELECT STATIONS
    # =========================================================

    def select_stations(
        self,
        stations=None
    ):

        if self.data is None:

            self.preprocess()

        if stations is None:

            return self.data

        stations = [
            str(x).strip().lower()
            for x in stations
        ]

        mask = (
            self.data["station"]
            .str.lower()
            .isin(stations)
        )

        selected = (
            self.data[mask]
            .copy()
        )

        print(
            f"\nSelected stations: "
            f"{selected['station'].nunique()}"
        )

        return selected

    # =========================================================
    # AGGREGATE STATIONS
    # =========================================================

    def aggregate_stations(
        self,
        data=None
    ):

        if data is None:

            data = self.data

        if data is None:

            data = self.preprocess()

        pollutants = [
            "PM25",
            "PM10",
            "NO2",
            "O3",
            "NO"
        ]

        available = [
            p for p in pollutants
            if p in data.columns
        ]

        regional = (
            data
            .groupby("time")[available]
            .mean(
                skipna=True
            )
            .reset_index()
        )

        return regional

    # =========================================================
    # HOURLY RESAMPLING
    # =========================================================

    def hourly_average(
        self,
        data=None
    ):

        if data is None:

            data = self.data

        if data is None:

            data = self.preprocess()

        pollutants = [
            "PM25",
            "PM10",
            "NO2",
            "O3",
            "NO"
        ]

        available = [
            p for p in pollutants
            if p in data.columns
        ]

        result = (
            data
            .set_index("time")
            [available]
            .resample("1h")
            .mean()
            .reset_index()
        )

        return result

    # =========================================================
    # SAVE
    # =========================================================

    def save(
        self,
        output_file
    ):

        if self.data is None:

            self.preprocess()

        output_file = Path(
            output_file
        )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.data.to_csv(
            output_file,
            index=False
        )

        print(
            f"\nCleaned AQ data saved:"
            f"\n{output_file}"
        )


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    FILE = (
        Path(__file__).resolve().parent / "data" / "air_quality" / "delhi_air_quality.csv"
    )

    reader = AirQualityReader(
        FILE
    )

    reader.load()

    data = reader.preprocess()

    print("\nCleaned data:")
    print(
        data.head()
    )

    print("\nAvailable stations:")

    print(
        data["station"]
        .unique()
    )

    regional = (
        reader.aggregate_stations()
    )

    hourly = (
        reader.hourly_average()
    )

    print(
        "\nHourly regional observations:"
    )

    print(
        hourly.head()
    )

    reader.save(
        Path(__file__).resolve().parent / "data" / "air_quality" / "cleaned_air_quality.csv"
    )
