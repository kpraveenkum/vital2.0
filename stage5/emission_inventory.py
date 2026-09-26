"""
emission_inventory.py

Stage 5

Combines traffic, industry and biomass emissions
into one unified inventory.
"""

import pandas as pd

from traffic_emissions import (
    TrafficEmissionModel
)

from industrial_emissions import (
    IndustrialEmissionModel
)

from biomass_emissions import (
    BiomassEmissionModel
)


class EmissionInventory:

    def __init__(
        self,
        traffic_file=None,
        industry_file=None,
        biomass_file=None
    ):

        self.traffic_file = traffic_file
        self.industry_file = industry_file
        self.biomass_file = biomass_file

    def load_all(self):

        datasets = []

        if self.traffic_file is not None:

            traffic = (
                TrafficEmissionModel(
                    self.traffic_file
                ).load()
            )

            datasets.append(traffic)

        if self.industry_file is not None:

            industry = (
                IndustrialEmissionModel(
                    self.industry_file
                ).load()
            )

            datasets.append(industry)

        if self.biomass_file is not None:

            biomass = (
                BiomassEmissionModel(
                    self.biomass_file
                ).load()
            )

            datasets.append(biomass)

        if not datasets:

            raise ValueError(
                "No emission datasets were provided."
            )

        return pd.concat(
            datasets,
            ignore_index=True
        )

    def summary(self, inventory):

        print("\n")
        print("=" * 70)
        print("EMISSION INVENTORY SUMMARY")
        print("=" * 70)

        print(
            f"\nTotal records: "
            f"{len(inventory)}"
        )

        print("\nBy source:")

        print(
            inventory[
                "source_type"
            ].value_counts()
        )

        print("\nBy pollutant:")

        pollutant_summary = (
            inventory
            .groupby("pollutant")[
                "emission_kg_s"
            ]
            .sum()
            .sort_values(
                ascending=False
            )
        )

        print(pollutant_summary)

        print("=" * 70)
