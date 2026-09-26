"""
main_stage4.py

STAGE 4
Delhi NCR Spatial Air Quality Model Orchestrator
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from grid_model import SpatialGrid, GridConfig
from spatial_meteorology import SpatialMeteorology
from transport_model import TransportModel
from spatial_chemistry import SpatialChemistry
from spatial_feedback import SpatialFeedback
from netcdf_reader import NetCDFMeteorologyReader


BASE_DIR = Path(__file__).resolve().parent

WEATHER_FILE = (
    BASE_DIR / "data" / "meteorology" / "processed_weather.csv"
)

NETCDF_FILE = (
    BASE_DIR / "data" / "meteorology" / "weather.nc"
)

OUTPUT_DIR = BASE_DIR / "outputs"

TIME_STEP = 300.0


class SpatialEmissions:

    def __init__(self, grid):
        self.grid = grid

    def create(self, time):

        X = self.grid.X
        Y = self.grid.Y

        x = X / X.max()
        y = Y / Y.max()

        pm25 = np.ones_like(X) * 5.0
        pm10 = np.ones_like(X) * 8.0
        no = np.ones_like(X) * 1.0
        no2 = np.ones_like(X) * 0.5

        hour = time.hour

        traffic_factor = 1.0

        if 7 <= hour <= 10:
            traffic_factor = 3.0

        elif 18 <= hour <= 21:
            traffic_factor = 3.0

        traffic_corridor = np.exp(
            -((y - 0.5) ** 2) / 0.02
        )

        traffic = (
            traffic_factor *
            traffic_corridor
        )

        pm25 += 10.0 * traffic
        pm10 += 15.0 * traffic
        no += 8.0 * traffic
        no2 += 4.0 * traffic

        industrial = np.exp(
            -(
                (x - 0.75) ** 2
                +
                (y - 0.25) ** 2
            ) / 0.01
        )

        pm25 += 20.0 * industrial
        pm10 += 30.0 * industrial
        no += 10.0 * industrial
        no2 += 5.0 * industrial

        # Temporary biomass-burning proxy.
        # Replace with satellite fire/FRP emissions later.
        if 0 <= hour <= 8:

            biomass = np.exp(
                -(
                    (x - 0.15) ** 2
                    +
                    (y - 0.80) ** 2
                ) / 0.02
            )

            pm25 += 30.0 * biomass
            pm10 += 45.0 * biomass

        return {
            "PM25": pm25,
            "PM10": pm10,
            "NO": no,
            "NO2": no2,
        }


class SpatialAirQualityModel:

    def __init__(self, grid):

        self.grid = grid

        self.meteorology = SpatialMeteorology(grid)

        self.transport = TransportModel(
            grid,
            diffusion_coefficient=100.0
        )

        self.chemistry = SpatialChemistry(grid)

        self.feedback = SpatialFeedback()

        self.emissions = SpatialEmissions(grid)

        shape = (grid.ny, grid.nx)

        self.pm25 = np.ones(shape) * 80.0
        self.pm10 = np.ones(shape) * 140.0
        self.no = np.ones(shape) * 10.0
        self.no2 = np.ones(shape) * 30.0
        self.o3 = np.ones(shape) * 40.0

    def step(self, weather_row):

        met = self.meteorology.create_field(
            weather_row
        )

        emissions = self.emissions.create(
            weather_row["time"]
        )

        # Transport
        self.pm25 = self.transport.update(
            self.pm25,
            met["u_wind"],
            met["v_wind"],
            TIME_STEP
        )

        self.pm10 = self.transport.update(
            self.pm10,
            met["u_wind"],
            met["v_wind"],
            TIME_STEP
        )

        self.no = self.transport.update(
            self.no,
            met["u_wind"],
            met["v_wind"],
            TIME_STEP
        )

        self.no2 = self.transport.update(
            self.no2,
            met["u_wind"],
            met["v_wind"],
            TIME_STEP
        )

        self.o3 = self.transport.update(
            self.o3,
            met["u_wind"],
            met["v_wind"],
            TIME_STEP
        )

        # Chemistry
        (
            self.pm25,
            self.pm10
        ) = self.chemistry.update_pm(
            self.pm25,
            self.pm10,
            met["temperature"],
            met["pbl_height"],
            met["wind_speed"],
            TIME_STEP,
            emissions["PM25"],
            emissions["PM10"]
        )

        (
            self.no,
            self.no2,
            self.o3
        ) = self.chemistry.update_gases(
            self.no,
            self.no2,
            self.o3,
            met["temperature"],
            met["radiation"],
            met["wind_speed"],
            TIME_STEP,
            emissions["NO"],
            emissions["NO2"]
        )

        # Chemistry -> meteorology feedback
        feedback = self.feedback.apply(
            self.pm25,
            self.pm10,
            met["temperature"],
            met["radiation"],
            met["pbl_height"]
        )

        return {
            "meteorology": met,
            "feedback": feedback,
            "emissions": emissions,
            "PM25": self.pm25.copy(),
            "PM10": self.pm10.copy(),
            "NO": self.no.copy(),
            "NO2": self.no2.copy(),
            "O3": self.o3.copy(),
        }


def load_weather():

    print("\nLoading meteorological data...")

    if not WEATHER_FILE.exists():
        if not NETCDF_FILE.exists():
            print(f"Generating sample NetCDF weather file at {NETCDF_FILE}...")
            from generate_sample_weather_nc import create_sample_weather_nc
            NETCDF_FILE.parent.mkdir(parents=True, exist_ok=True)
            create_sample_weather_nc()

        print(f"Generating {WEATHER_FILE} from {NETCDF_FILE}...")
        reader = NetCDFMeteorologyReader(NETCDF_FILE)
        reader.save_csv(WEATHER_FILE)

    df = pd.read_csv(WEATHER_FILE)

    df["time"] = pd.to_datetime(df["time"])

    required = [
        "temperature_K",
        "u_wind",
        "v_wind",
        "pbl_height",
        "radiation"
    ]

    missing = [
        column for column in required
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing meteorological columns: {missing}"
        )

    return df


def plot_field(
    grid,
    field,
    title,
    filename,
    unit=""
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.figure(figsize=(9, 7))

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

    plt.colorbar(label=unit)

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title(title)

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / filename,
        dpi=200
    )

    plt.close()


def plot_wind(grid, u, v):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.figure(figsize=(9, 7))

    speed = np.sqrt(u ** 2 + v ** 2)

    plt.imshow(
        speed,
        origin="lower",
        extent=[
            grid.longitude.min(),
            grid.longitude.max(),
            grid.latitude.min(),
            grid.latitude.max()
        ],
        aspect="auto"
    )

    step = max(1, grid.nx // 8)

    plt.quiver(
        grid.longitude[::step, ::step],
        grid.latitude[::step, ::step],
        u[::step, ::step],
        v[::step, ::step]
    )

    plt.colorbar(label="Wind speed m/s")

    plt.xlabel("Longitude")
    plt.ylabel("Latitude")
    plt.title("Delhi NCR Spatial Wind Field")

    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR / "wind_field.png",
        dpi=200
    )

    plt.close()


def save_grid(grid, result, time):

    rows = []

    for j in range(grid.ny):

        for i in range(grid.nx):

            rows.append({
                "time": time,
                "grid_y": j,
                "grid_x": i,
                "latitude": grid.latitude[j, i],
                "longitude": grid.longitude[j, i],
                "PM25": result["PM25"][j, i],
                "PM10": result["PM10"][j, i],
                "NO": result["NO"][j, i],
                "NO2": result["NO2"][j, i],
                "O3": result["O3"][j, i],
                "temperature":
                    result["feedback"]["temperature"][j, i],
                "radiation":
                    result["feedback"]["radiation"][j, i],
                "PBL":
                    result["feedback"]["pbl"][j, i],
                "wind_speed":
                    result["meteorology"]["wind_speed"][j, i],
            })

    return pd.DataFrame(rows)


def main():

    print("\n" + "=" * 70)
    print("STAGE 4 - DELHI NCR SPATIAL AIR QUALITY MODEL")
    print("=" * 70)

    grid_config = GridConfig(
        width_km=100,
        height_km=100,
        resolution_km=5,
        center_lat=28.6139,
        center_lon=77.2090
    )

    grid = SpatialGrid(grid_config)
    grid.summary()

    weather = load_weather()

    print(f"\nWeather records: {len(weather)}")

    model = SpatialAirQualityModel(grid)

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    all_grid_results = []

    for index, row in weather.iterrows():

        print(
            f"\nTimestep {index + 1}/{len(weather)}"
        )

        print(f"Time: {row['time']}")

        result = model.step(row)

        grid_df = save_grid(
            grid,
            result,
            row["time"]
        )

        all_grid_results.append(grid_df)

        if index == len(weather) - 1:

            plot_field(
                grid,
                result["PM25"],
                "Delhi NCR PM2.5",
                "pm25_map.png",
                "PM2.5"
            )

            plot_field(
                grid,
                result["PM10"],
                "Delhi NCR PM10",
                "pm10_map.png",
                "PM10"
            )

            plot_field(
                grid,
                result["NO2"],
                "Delhi NCR NO2",
                "no2_map.png",
                "NO2"
            )

            plot_field(
                grid,
                result["O3"],
                "Delhi NCR O3",
                "o3_map.png",
                "O3"
            )

            plot_wind(
                grid,
                result["meteorology"]["u_wind"],
                result["meteorology"]["v_wind"]
            )

    if all_grid_results:

        final_grid = pd.concat(
            all_grid_results,
            ignore_index=True
        )

        final_grid.to_csv(
            OUTPUT_DIR / "spatial_model_results.csv",
            index=False
        )

    print("\n" + "=" * 70)
    print("STAGE 4 COMPLETED")
    print("=" * 70)

    print("\nOutputs:")
    print("  PM2.5 map")
    print("  PM10 map")
    print("  NO2 map")
    print("  O3 map")
    print("  Wind field")
    print("  Spatial CSV")


if __name__ == "__main__":
    main()
