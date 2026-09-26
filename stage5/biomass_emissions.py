"""
biomass_emissions.py

Stage 5

Biomass-burning emission processor.

Future input sources can include:

    VIIRS
    MODIS
    FIRMS
    FRP-derived fire products
"""

from pathlib import Path

import pandas as pd

from emission_units import (
    to_kg_per_second
)


class BiomassEmissionModel:

    def __init__(self, filename):

        self.filename = Path(filename)

    def load(self):

        if not self.filename.exists():

            raise FileNotFoundError(
                f"Biomass file not found: "
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
                "Missing biomass columns: "
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

        df["source_type"] = (
            "biomass_burning"
        )

        return df
