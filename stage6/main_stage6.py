"""
main_stage6.py

STAGE 6
Satellite-Based Biomass / Stubble-Burning Emissions Pipeline
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from satellite_fire_reader import SatelliteFireReader
from fire_filter import FireFilter
from frp_model import FRPModel
from biomass_burned_model import BiomassBurnedModel
from biomass_emission_model import BiomassEmissionModel
from fire_gridding import FireGridder


# ============================================================
# Paths
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = (
    BASE_DIR
    / "data"
    / "satellite"
)

OUTPUT_DIR = (
    BASE_DIR
    / "outputs"
)

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

FIRE_FILE = (
    DATA_DIR
    / "fires.csv"
)


# ============================================================
# Create test data if no real satellite data exists
# ============================================================

def create_test_data():

    data = [
        [
            29.12,
            76.82,
            "2026-10-15",
            1030,
            35.4,
            "high",
            "TEST",
        ],

        [
            29.05,
            76.95,
            "2026-10-15",
            1040,
            62.1,
            "nominal",
            "TEST",
        ],

        [
            28.91,
            77.10,
            "2026-10-15",
            1050,
            18.5,
            "high",
            "TEST",
        ],

        [
            29.25,
            76.70,
            "2026-10-15",
            1110,
            48.2,
            "high",
            "TEST",
        ],

        [
            29.00,
            76.60,
            "2026-10-15",
            1130,
            25.7,
            "nominal",
            "TEST",
        ],
    ]

    columns = [
        "latitude",
        "longitude",
        "acq_date",
        "acq_time",
        "frp",
        "confidence",
        "satellite",
    ]

    df = pd.DataFrame(
        data,
        columns=columns,
    )

    df.to_csv(
        FIRE_FILE,
        index=False,
    )

    print(
        "Test satellite fire dataset created:"
    )

    print(FIRE_FILE)


# ============================================================
# Create Delhi NCR prototype grid
# ============================================================

def create_grid():

    center_lat = 28.6139
    center_lon = 77.2090

    grid_size_km = 100
    resolution_km = 5

    n = int(
        grid_size_km
        / resolution_km
    )

    # Approximate geographic conversion
    km_per_degree_lat = 111.0
    km_per_degree_lon = (
        111.0
        * np.cos(
            np.radians(center_lat)
        )
    )

    lat_range = (
        grid_size_km
        / 2
        / km_per_degree_lat
    )

    lon_range = (
        grid_size_km
        / 2
        / km_per_degree_lon
    )

    lat_values = np.linspace(
        center_lat - lat_range,
        center_lat + lat_range,
        n,
    )

    lon_values = np.linspace(
        center_lon - lon_range,
        center_lon + lon_range,
        n,
    )

    lon_grid, lat_grid = np.meshgrid(
        lon_values,
        lat_values,
    )

    return (
        lat_grid,
        lon_grid,
    )


# ============================================================
# Plot fire detections
# ============================================================

def plot_fire_locations(fires):

    plt.figure(figsize=(8, 6))

    scatter = plt.scatter(
        fires["longitude"],
        fires["latitude"],
        c=fires["frp"],
        s=60,
    )

    plt.colorbar(
        scatter,
        label="FRP"
    )

    plt.xlabel(
        "Longitude"
    )

    plt.ylabel(
        "Latitude"
    )

    plt.title(
        "Satellite Fire Detections"
    )

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        / "fire_detection_map.png",
        dpi=200,
    )

    plt.close()


# ============================================================
# Plot emission grid
# ============================================================

def plot_emission_map(
    lat_grid,
    lon_grid,
    emission_grid,
    pollutant,
):

    plt.figure(figsize=(8, 6))

    mesh = plt.pcolormesh(
        lon_grid,
        lat_grid,
        emission_grid,
        shading="auto",
    )

    plt.colorbar(
        mesh,
        label="kg/s/cell"
    )

    plt.xlabel(
        "Longitude"
    )

    plt.ylabel(
        "Latitude"
    )

    plt.title(
        f"Satellite Biomass Burning {pollutant} Emissions"
    )

    plt.grid(
        alpha=0.2
    )

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        / f"biomass_{pollutant.lower()}_map.png",
        dpi=200,
    )

    plt.close()


# ============================================================
# Main Stage 6 pipeline
# ============================================================

def main():

    print("\n====================================")
    print("STAGE 6 - SATELLITE FIRE EMISSIONS")
    print("====================================\n")

    # --------------------------------------------------------
    # 1. Input
    # --------------------------------------------------------

    if not FIRE_FILE.exists():

        create_test_data()

        print(
            "\nWARNING: Test satellite data are being used."
        )

        print(
            "Replace fires.csv with real satellite observations "
            "before scientific analysis.\n"
        )

    # --------------------------------------------------------
    # 2. Read satellite data
    # --------------------------------------------------------

    reader = SatelliteFireReader(
        FIRE_FILE
    )

    fires = reader.read()

    print(
        "Total satellite detections:",
        len(fires)
    )

    # --------------------------------------------------------
    # 3. Filter
    # --------------------------------------------------------

    fire_filter = FireFilter(
        min_frp=5.0,
        allowed_confidence=[
            "high",
            "nominal",
        ],
    )

    fires = fire_filter.apply(
        fires
    )

    print(
        "Detections after filtering:",
        len(fires)
    )

    if fires.empty:

        print(
            "No fires passed the filter."
        )

        return

    # --------------------------------------------------------
    # 4. FRP -> biomass burning rate
    # --------------------------------------------------------

    frp_model = FRPModel(
        frp_to_burn_rate=0.0005
    )

    fires = frp_model.apply(
        fires
    )

    # --------------------------------------------------------
    # 5. Burning rate -> total biomass burned
    # --------------------------------------------------------

    biomass_model = BiomassBurnedModel(
        active_duration_seconds=600
    )

    fires = biomass_model.apply(
        fires
    )

    # --------------------------------------------------------
    # 6. Biomass -> pollutant emissions
    # --------------------------------------------------------

    emission_model = (
        BiomassEmissionModel()
    )

    fires = emission_model.apply(
        fires
    )

    # --------------------------------------------------------
    # 7. Save individual-fire emissions
    # --------------------------------------------------------

    fire_output = (
        OUTPUT_DIR
        / "biomass_fire_emissions.csv"
    )

    fires.to_csv(
        fire_output,
        index=False,
    )

    # --------------------------------------------------------
    # 8. Create atmospheric grid
    # --------------------------------------------------------

    lat_grid, lon_grid = create_grid()

    gridder = FireGridder(
        lat_grid,
        lon_grid,
    )

    # --------------------------------------------------------
    # 9. Grid pollutants
    # --------------------------------------------------------

    pollutants = [
        "PM25",
        "PM10",
        "CO",
        "NOx",
        "VOC",
    ]

    spatial_records = []

    for pollutant in pollutants:

        emission_grid = (
            gridder.grid_pollutant(
                fires,
                pollutant,
            )
        )

        plot_emission_map(
            lat_grid,
            lon_grid,
            emission_grid,
            pollutant,
        )

        ny, nx = emission_grid.shape

        for y in range(ny):

            for x in range(nx):

                value = (
                    emission_grid[y, x]
                )

                if value > 0:

                    spatial_records.append(
                        {
                            "grid_y": y,
                            "grid_x": x,
                            "latitude":
                                lat_grid[y, x],
                            "longitude":
                                lon_grid[y, x],
                            "pollutant":
                                pollutant,
                            "emission_kg_s":
                                value,
                        }
                    )

    # --------------------------------------------------------
    # 10. Save spatial emissions
    # --------------------------------------------------------

    spatial_df = pd.DataFrame(
        spatial_records
    )

    spatial_output = (
        OUTPUT_DIR
        / "biomass_spatial_emissions.csv"
    )

    spatial_df.to_csv(
        spatial_output,
        index=False,
    )

    # --------------------------------------------------------
    # 11. Fire map
    # --------------------------------------------------------

    plot_fire_locations(
        fires
    )

    # --------------------------------------------------------
    # 12. Summary
    # --------------------------------------------------------

    print(
        "\nSatellite fire processing complete."
    )

    print(
        "\nOutputs:"
    )

    print(
        fire_output
    )

    print(
        spatial_output
    )

    print(
        OUTPUT_DIR
        / "fire_detection_map.png"
    )

    print(
        "\nPollutants:"
    )

    print(
        ", ".join(pollutants)
    )


if __name__ == "__main__":
    main()
