"""
spatial_meteorology.py

STAGE 4
Spatial Meteorology Field Creator
"""

import numpy as np


class SpatialMeteorology:

    def __init__(self, grid):
        self.grid = grid

    def create_field(self, regional_row):

        X = self.grid.X
        Y = self.grid.Y

        x_norm = X / X.max() - 0.5
        y_norm = Y / Y.max() - 0.5

        temperature = regional_row["temperature_K"]
        u_wind = regional_row["u_wind"]
        v_wind = regional_row["v_wind"]
        pbl = regional_row["pbl_height"]
        radiation = regional_row["radiation"]

        temperature_field = (
            temperature
            + 1.0 * x_norm
            + 0.5 * y_norm
        )

        u_field = u_wind * (1.0 + 0.10 * y_norm)
        v_field = v_wind * (1.0 + 0.10 * x_norm)

        pbl_field = pbl * (1.0 + 0.10 * y_norm)

        radiation_field = (
            radiation * (1.0 - 0.05 * x_norm)
        )

        wind_speed = np.sqrt(
            u_field ** 2 + v_field ** 2
        )

        return {
            "temperature": temperature_field,
            "u_wind": u_field,
            "v_wind": v_field,
            "wind_speed": wind_speed,
            "pbl_height": np.maximum(
                pbl_field, 50.0
            ),
            "radiation": np.maximum(
                radiation_field, 0.0
            ),
        }
