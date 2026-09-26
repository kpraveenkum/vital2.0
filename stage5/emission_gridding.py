"""
emission_gridding.py

Stage 5

Maps source emissions onto the atmospheric grid.

Input:
    latitude
    longitude
    pollutant
    emission_kg_s

Output:
    emission[pollutant][y, x]
"""

import numpy as np


class EmissionGridder:

    def __init__(self, grid):

        self.grid = grid

    def find_cell(
        self,
        latitude,
        longitude
    ):

        distance = (
            (
                self.grid.latitude -
                latitude
            ) ** 2
            +
            (
                self.grid.longitude -
                longitude
            ) ** 2
        )

        index = np.unravel_index(
            np.argmin(distance),
            distance.shape
        )

        return index

    def grid_sources(
        self,
        sources
    ):

        pollutants = sorted(
            sources["pollutant"].unique()
        )

        result = {}

        for pollutant in pollutants:

            result[pollutant] = np.zeros(
                (
                    self.grid.ny,
                    self.grid.nx
                ),
                dtype=float
            )

        for _, row in sources.iterrows():

            latitude = row["latitude"]
            longitude = row["longitude"]

            pollutant = row["pollutant"]

            emission = row[
                "emission_kg_s"
            ]

            j, i = self.find_cell(
                latitude,
                longitude
            )

            result[pollutant][j, i] += emission

        return result

    def total_pollutant(
        self,
        gridded_emissions,
        pollutant
    ):

        if pollutant not in gridded_emissions:

            return np.zeros(
                (
                    self.grid.ny,
                    self.grid.nx
                )
            )

        return gridded_emissions[pollutant]
