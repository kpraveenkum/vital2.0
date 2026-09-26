"""
main_stage5.py

STAGE 5
Delhi NCR Spatial Emission Inventory

Pipeline:

    Source data
        ↓
    Unit conversion
        ↓
    Unified inventory
        ↓
    Spatial gridding
        ↓
    Emission maps
        ↓
    Stage 4 atmospheric model

Test-data generation is included only for software testing.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from grid_model import (
    SpatialGrid,
    GridConfig
)

from emission_inventory import (
    EmissionInventory
)

from emission_gridding import (
    EmissionGridder
)


BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "emissions"

OUTPUT_DIR = BASE_DIR / "outputs"

TRAFFIC_FILE = (
    DATA_DIR / "traffic.csv"
)

INDUSTRY_FILE = (
    DATA_DIR / "industry.csv"
)

BIOMASS_FILE = (
    DATA_DIR / "biomass.csv"
)


def create_test_data():

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # Traffic
    # ---------------------------------------------------------

    traffic = pd.DataFrame([

        {
            "latitude": 28.61,
            "longitude": 77.21,
            "pollutant": "PM25",
            "emission": 100,
            "unit": "kg/day"
        },

        {
            "latitude": 28.62,
            "longitude": 77.24,
            "pollutant": "PM10",
            "emission": 180,
            "unit": "kg/day"
        },

        {
            "latitude": 28.59,
            "longitude": 77.18,
            "pollutant": "NOx",
            "emission": 500,
            "unit": "kg/day"
        },

        {
            "latitude": 28.65,
            "longitude": 77.25,
            "pollutant": "CO",
            "emission": 1000,
            "unit": "kg/day"
        }

    ])

    traffic.to_csv(
        TRAFFIC_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # Industry
    # ---------------------------------------------------------

    industry = pd.DataFrame([

        {
            "latitude": 28.50,
            "longitude": 77.30,
            "pollutant": "PM25",
            "emission": 200,
            "unit": "kg/day",
            "facility": "Industry_A"
        },

        {
            "latitude": 28.55,
            "longitude": 77.35,
            "pollutant": "PM10",
            "emission": 400,
            "unit": "kg/day",
            "facility": "Industry_B"
        },

        {
            "latitude": 28.52,
            "longitude": 77.28,
            "pollutant": "NOx",
            "emission": 600,
            "unit": "kg/day",
            "facility": "Industry_C"
        }

    ])

    industry.to_csv(
        INDUSTRY_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # Biomass
    # ---------------------------------------------------------

    biomass = pd.DataFrame([

        {
            "latitude": 29.00,
            "longitude": 76.90,
            "pollutant": "PM25",
            "emission": 300,
            "unit": "kg/day",
            "fire_id": "TEST_001"
        },

        {
            "latitude": 29.05,
            "longitude": 77.00,
            "pollutant": "PM10",
            "emission": 500,
            "unit": "kg/day",
            "fire_id": "TEST_002"
        },

        {
            "latitude": 28.90,
            "longitude": 77.10,
            "pollutant": "CO",
            "emission": 800,
            "unit": "kg/day",
            "fire_id": "TEST_003"
        }

    ])

    biomass.to_csv(
        BIOMASS_FILE,
        index=False
    )

    print(
        "\nTest emission datasets created."
    )


def plot_emission_map(
    grid,
    field,
    title,
    filename,
    unit="kg/s"
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.figure(
        figsize=(9, 7)
    )

    plt.imshow(
        field,
        origin="lower",
        extent=[
            grid.longitude.min(),
            grid.longitude.max(),
            grid.latitude.min(),
            grid.latitude.max()
        ],
        aspect="auto"
    )

    plt.colorbar(
        label=unit
    )

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")

    plt.title(title)

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / filename,
        dpi=200
    )

    plt.close()


def save_emission_grid(
    grid,
    emission_field,
    pollutant
):

    rows = []

    for j in range(grid.ny):

        for i in range(grid.nx):

            rows.append({

                "grid_y": j,

                "grid_x": i,

                "latitude":
                    grid.latitude[j, i],

                "longitude":
                    grid.longitude[j, i],

                "pollutant":
                    pollutant,

                "emission_kg_s":
                    emission_field[j, i]

            })

    return pd.DataFrame(rows)


def main():

    print("\n")
    print("=" * 70)
    print(
        "STAGE 5 - REAL SPATIAL EMISSION INVENTORY"
    )
    print("=" * 70)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # Create test data when input files are absent
    # ---------------------------------------------------------

    if not (
        TRAFFIC_FILE.exists()
        and
        INDUSTRY_FILE.exists()
        and
        BIOMASS_FILE.exists()
    ):

        print(
            "\nInput emission files not found."
        )

        print(
            "Creating TEST datasets."
        )

        create_test_data()

    # ---------------------------------------------------------
    # Grid
    # ---------------------------------------------------------

    grid_config = GridConfig(
        width_km=100,
        height_km=100,
        resolution_km=5,
        center_lat=28.6139,
        center_lon=77.2090
    )

    grid = SpatialGrid(
        grid_config
    )

    grid.summary()

    # ---------------------------------------------------------
    # Inventory
    # ---------------------------------------------------------

    inventory_model = EmissionInventory(
        traffic_file=TRAFFIC_FILE,
        industry_file=INDUSTRY_FILE,
        biomass_file=BIOMASS_FILE
    )

    inventory = (
        inventory_model.load_all()
    )

    inventory_model.summary(
        inventory
    )

    # ---------------------------------------------------------
    # Save unified inventory
    # ---------------------------------------------------------

    inventory.to_csv(
        OUTPUT_DIR /
        "combined_emission_inventory.csv",
        index=False
    )

    # ---------------------------------------------------------
    # Spatial gridding
    # ---------------------------------------------------------

    gridder = EmissionGridder(
        grid
    )

    gridded = gridder.grid_sources(
        inventory
    )

    # ---------------------------------------------------------
    # Create maps
    # ---------------------------------------------------------

    all_grid_records = []

    pollutant_names = [
        "PM25",
        "PM10",
        "NOx",
        "NO2",
        "NO",
        "CO",
        "VOC"
    ]

    for pollutant in pollutant_names:

        if pollutant not in gridded:
            continue

        field = gridded[pollutant]

        print(
            f"\n{pollutant}:"
        )

        print(
            f"Total emission = "
            f"{field.sum():.8e} kg/s"
        )

        print(
            f"Maximum cell = "
            f"{field.max():.8e} kg/s"
        )

        plot_emission_map(
            grid,
            field,
            f"Delhi NCR {pollutant} Emission",
            pollutant.lower() +
            "_emission_map.png"
        )

        grid_df = save_emission_grid(
            grid,
            field,
            pollutant
        )

        all_grid_records.append(
            grid_df
        )

    # ---------------------------------------------------------
    # Combined spatial inventory
    # ---------------------------------------------------------

    if all_grid_records:

        spatial_inventory = pd.concat(
            all_grid_records,
            ignore_index=True
        )

        spatial_inventory.to_csv(
            OUTPUT_DIR /
            "spatial_emission_inventory.csv",
            index=False
        )

    print("\n")
    print("=" * 70)
    print("STAGE 5 COMPLETED")
    print("=" * 70)

    print("\nOutputs:")
    print("  combined_emission_inventory.csv")
    print("  spatial_emission_inventory.csv")
    print("  pollutant emission maps")


if __name__ == "__main__":

    main()
