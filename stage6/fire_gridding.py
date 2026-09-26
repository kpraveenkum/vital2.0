"""
fire_gridding.py

Stage 6
Satellite Fire Emission Spatial Gridder
"""

import numpy as np


class FireGridder:
    """
    Maps fire emissions to the nearest atmospheric-model
    grid cell.

    Output:
        pollutant[y, x] in kg/s/cell
    """

    def __init__(
        self,
        lat_grid,
        lon_grid,
    ):

        self.lat_grid = lat_grid
        self.lon_grid = lon_grid

    def nearest_index(self, latitude, longitude):

        distance = (
            (self.lat_grid - latitude) ** 2
            + (self.lon_grid - longitude) ** 2
        )

        index = np.unravel_index(
            np.argmin(distance),
            distance.shape,
        )

        return index

    def grid_pollutant(
        self,
        fires,
        pollutant,
    ):

        ny, nx = self.lat_grid.shape

        emission_grid = np.zeros(
            (ny, nx),
            dtype=float,
        )

        column = (
            f"{pollutant}_emission_kg_s"
        )

        if column not in fires.columns:
            return emission_grid

        for _, fire in fires.iterrows():

            y, x = self.nearest_index(
                fire["latitude"],
                fire["longitude"],
            )

            emission_grid[y, x] += (
                fire[column]
            )

        return emission_grid
