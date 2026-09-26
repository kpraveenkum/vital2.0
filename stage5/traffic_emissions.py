"""
traffic_emissions.py

Stage 5

Traffic emission processor.
"""

from pathlib import Path

import pandas as pd

from emission_units import (
    to_kg_per_second
)


class TrafficEmissionModel:

    def __init__(self, filename):

        self.filename = Path(filename)

    def load(self):

        if not self.filename.exists():

            raise FileNotFoundError(
                f"Traffic file not found: "
                f"{self.filename}"
            )

        df = pd.read_csv(
            self.filename
        )

        required = [
            "latitude",
            "longitude",
            "pollutant",
            "emission",
            "unit"
        ]

        missing = [
            col
            for col in required
            if col not in df.columns
        ]

        if missing:

            raise ValueError(
                "Missing traffic columns: "
                f"{missing}"
            )

        df["latitude"] = pd.to_numeric(
            df["latitude"],
            errors="coerce"
        )

        df["longitude"] = pd.to_numeric(
            df["longitude"],
            errors="coerce"
        )

        df["emission"] = pd.to_numeric(
            df["emission"],
            errors="coerce"
        )

        df = df.dropna(
            subset=[
                "latitude",
                "longitude",
                "emission"
            ]
        )

        df["emission_kg_s"] = df.apply(
            lambda row:
                to_kg_per_second(
                    row["emission"],
                    row["unit"]
                ),
            axis=1
        )

        df["source_type"] = "traffic"

        return df
