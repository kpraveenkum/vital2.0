"""
grid_model.py

STAGE 4
Spatial Grid Model for Delhi NCR (100km x 100km, 5km resolution)
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class GridConfig:
    width_km: float = 100.0
    height_km: float = 100.0
    resolution_km: float = 5.0
    center_lat: float = 28.6139
    center_lon: float = 77.2090


class SpatialGrid:

    def __init__(self, config=None):

        if config is None:
            config = GridConfig()

        self.config = config

        self.nx = int(
            config.width_km / config.resolution_km
        )

        self.ny = int(
            config.height_km / config.resolution_km
        )

        if self.nx < 2 or self.ny < 2:
            raise ValueError(
                "Grid requires at least 2 cells in each direction."
            )

        self.dx = config.resolution_km * 1000.0
        self.dy = config.resolution_km * 1000.0

        self.x = np.arange(self.nx) * self.dx + self.dx / 2
        self.y = np.arange(self.ny) * self.dy + self.dy / 2

        self.X, self.Y = np.meshgrid(self.x, self.y)

        lat_degree = config.height_km / 111.0

        lon_degree = (
            config.width_km
            / (
                111.0
                * np.cos(np.radians(config.center_lat))
            )
        )

        self.latitude = (
            config.center_lat
            + (
                self.Y - config.height_km * 1000 / 2
            )
            / (config.height_km * 1000)
            * lat_degree
        )

        self.longitude = (
            config.center_lon
            + (
                self.X - config.width_km * 1000 / 2
            )
            / (config.width_km * 1000)
            * lon_degree
        )

    def summary(self):

        print("\n" + "=" * 70)
        print("SPATIAL GRID")
        print("=" * 70)

        print(f"Domain width : {self.config.width_km} km")
        print(f"Domain height: {self.config.height_km} km")
        print(f"Resolution   : {self.config.resolution_km} km")
        print(f"Grid cells X : {self.nx}")
        print(f"Grid cells Y : {self.ny}")
        print(f"Total cells  : {self.nx * self.ny}")

        print(
            f"Latitude range : "
            f"{self.latitude.min():.3f} to "
            f"{self.latitude.max():.3f}"
        )

        print(
            f"Longitude range: "
            f"{self.longitude.min():.3f} to "
            f"{self.longitude.max():.3f}"
        )

        print("=" * 70)


if __name__ == "__main__":

    grid = SpatialGrid()
    grid.summary()
    print("\nGrid shape:", grid.X.shape)
