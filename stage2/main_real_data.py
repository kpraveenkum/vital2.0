"""
main_real_data.py

Stage 2:
Real meteorological data
        +
Dual-loop atmospheric model

This version focuses on:

    Temperature
    Wind
    PBL height
    Radiation
    Inversion
    Vertical mixing
    PM2.5
    PM10
    O3
    NO
    NO2

The chemistry is still simplified.

This is NOT WRF-Chem.
It is the bridge between the prototype
and the real numerical model.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from netcdf_reader import NetCDFMeteorologyReader


# =============================================================
# CONFIGURATION
# =============================================================

class Config:

    AREA = 1.0e8
    MIN_PBL = 50.0
    DT = 3600.0

    PM25_EXTINCTION = 0.0015
    PM10_EXTINCTION = 0.00015

    TEMPERATURE_SENSITIVITY = 0.003
    PBL_TEMPERATURE_SENSITIVITY = 12.0

    INVERSION_STRENGTH = 80.0
    BASE_KZ_FACTOR = 0.35

    O3_BACKGROUND_LOSS = 1.0e-5
    MAX_PHOTOLYSIS = 0.0015

    A = 1.0e-3
    EA = 3000.0
    R = 8.314

    MAX_PM = 10000.0
    MAX_GAS = 1000.0


# =============================================================
# INVERSION MODEL
# =============================================================

class InversionModel:

    def __init__(self, config):
        self.cfg = config

    def calculate(self, time, temperature_C):

        """
        Temporary inversion proxy.

        IMPORTANT:
        A real inversion calculation requires
        vertical temperature information.

        This proxy will be replaced in a later
        stage when vertical atmospheric profiles
        are available.
        """

        hour = time.hour

        if hour >= 20 or hour <= 8:

            if 3 <= hour <= 7:
                strength = 0.8
            else:
                strength = 0.4

        else:
            strength = 0.0

        return strength

    def calculate_kz(
        self,
        pbl_height,
        wind_speed,
        inversion_strength
    ):

        """
        Simplified turbulent mixing coefficient.

        Kz increases with:
            PBL height
            wind speed

        Kz decreases with:
            inversion strength
        """

        base_kz = (
            self.cfg.BASE_KZ_FACTOR
            * pbl_height
            * max(wind_speed, 0.1)
        )

        penalty = (
            1.0
            +
            self.cfg.INVERSION_STRENGTH
            * inversion_strength
        )

        kz = base_kz / penalty

        return max(kz, 0.1)


# =============================================================
# CHEMISTRY MODEL
# =============================================================

class ChemistryModel:

    def __init__(self, config):
        self.cfg = config

    def reaction_rate(self, temperature_K):

        return (
            self.cfg.A
            * np.exp(
                -self.cfg.EA
                /
                (
                    self.cfg.R
                    * temperature_K
                )
            )
        )

    def photolysis_rate(self, radiation):

        radiation = np.clip(
            radiation,
            0,
            700
        )

        return (
            self.cfg.MAX_PHOTOLYSIS
            * radiation
            / 700.0
        )

    def update_pm(
        self,
        pm25,
        pm10,
        temperature_K,
        wind_speed,
        pbl_height,
        kz,
        dt,
        emission_pm25,
        emission_pm10
    ):

        volume = (
            self.cfg.AREA
            * max(
                pbl_height,
                self.cfg.MIN_PBL
            )
        )

        source_pm25 = (
            emission_pm25
            / volume
            * 1.0e6
        )

        source_pm10 = (
            emission_pm10
            / volume
            * 1.0e6
        )

        wind_loss = (
            1.0e-5
            * wind_speed
        )

        mixing_loss = (
            1.0e-8
            * kz
        )

        k = self.reaction_rate(
            temperature_K
        )

        secondary_pm25 = (
            k
            * 100.0
        )

        dpm25 = (
            source_pm25
            + secondary_pm25
            - wind_loss * pm25
            - mixing_loss * pm25
        )

        dpm10 = (
            source_pm10
            + 0.3 * secondary_pm25
            - wind_loss * pm10
            - mixing_loss * pm10
        )

        pm25_new = (
            pm25
            + dt * dpm25
        )

        pm10_new = (
            pm10
            + dt * dpm10
        )

        pm25_new = np.clip(
            pm25_new,
            0,
            self.cfg.MAX_PM
        )

        pm10_new = np.clip(
            pm10_new,
            0,
            self.cfg.MAX_PM
        )

        return pm25_new, pm10_new

    def update_gases(
        self,
        no,
        no2,
        o3,
        temperature_K,
        radiation,
        wind_speed,
        dt,
        emission_no,
        emission_no2
    ):

        J = self.photolysis_rate(
            radiation
        )

        k = self.reaction_rate(
            temperature_K
        )

        no2_photolysis = (
            J * no2
        )

        o3_titration = (
            k * no * o3
        )

        o3_production = (
            0.5
            * no2_photolysis
        )

        dilution = (
            1.0e-5
            * wind_speed
        )

        d_no = (
            emission_no
            - no * dilution
            - no * k
            + no2_photolysis
        )

        d_no2 = (
            emission_no2
            + no * k
            - no2_photolysis
            - no2 * dilution
        )

        d_o3 = (
            o3_production
            - o3_titration
            - self.cfg.O3_BACKGROUND_LOSS * o3
        )

        no_new = np.clip(
            no + dt * d_no,
            0,
            self.cfg.MAX_GAS
        )

        no2_new = np.clip(
            no2 + dt * d_no2,
            0,
            self.cfg.MAX_GAS
        )

        o3_new = np.clip(
            o3 + dt * d_o3,
            0,
            self.cfg.MAX_GAS
        )

        return (
            no_new,
            no2_new,
            o3_new
        )


# =============================================================
# AEROSOL FEEDBACK
# =============================================================

class AerosolFeedback:

    def __init__(self, config):
        self.cfg = config

    def radiation_effect(
        self,
        pm25,
        pm10,
        radiation
    ):

        optical_depth = (
            self.cfg.PM25_EXTINCTION * pm25
            +
            self.cfg.PM10_EXTINCTION * pm10
        )

        new_radiation = (
            radiation
            * np.exp(-optical_depth)
        )

        return (
            new_radiation,
            optical_depth
        )

    def temperature_feedback(
        self,
        old_temperature,
        old_radiation,
        new_radiation
    ):

        delta_temperature = (
            self.cfg.TEMPERATURE_SENSITIVITY
            *
            (
                new_radiation
                -
                old_radiation
            )
        )

        return (
            old_temperature
            +
            delta_temperature
        )

    def pbl_feedback(
        self,
        old_pbl,
        temperature_K
    ):

        reference_temperature = 290.0

        delta_pbl = (
            self.cfg.PBL_TEMPERATURE_SENSITIVITY
            *
            (
                temperature_K
                -
                reference_temperature
            )
        )

        new_pbl = (
            old_pbl
            +
            delta_pbl
        )

        return max(
            new_pbl,
            self.cfg.MIN_PBL
        )


# =============================================================
# DUAL LOOP MODEL
# =============================================================

class RealDataDualLoop:

    def __init__(self):

        self.cfg = Config()

        self.inversion = InversionModel(
            self.cfg
        )

        self.chemistry = ChemistryModel(
            self.cfg
        )

        self.feedback = AerosolFeedback(
            self.cfg
        )

        self.pm25 = 80.0
        self.pm10 = 140.0

        self.no = 10.0
        self.no2 = 30.0
        self.o3 = 40.0

    def step(self, row):

        temperature_K = row["temperature_K"]
        temperature_C = row["temperature_C"]

        wind_speed = row["wind_speed"]
        pbl_height = row["pbl_height"]
        radiation = row["radiation"]

        # =====================================================
        # LOOP 1
        # METEOROLOGY → CHEMISTRY
        # =====================================================

        inversion_strength = (
            self.inversion.calculate(
                row["time"],
                temperature_C
            )
        )

        kz = (
            self.inversion.calculate_kz(
                pbl_height,
                wind_speed,
                inversion_strength
            )
        )

        # -----------------------------------------------------
        # TEMPORARY EMISSIONS
        #
        # These are NOT real Delhi emissions.
        # They will be replaced in the emissions stage.
        # -----------------------------------------------------

        hour = row["time"].hour

        traffic_factor = 1.0

        if 7 <= hour <= 10:
            traffic_factor = 2.0

        elif 18 <= hour <= 21:
            traffic_factor = 2.0

        emission_pm25 = 20.0 * traffic_factor
        emission_pm10 = 35.0 * traffic_factor

        emission_no = 5.0 * traffic_factor
        emission_no2 = 3.0 * traffic_factor

        # -----------------------------------------------------
        # Chemistry
        # -----------------------------------------------------

        (
            self.pm25,
            self.pm10
        ) = self.chemistry.update_pm(
            self.pm25,
            self.pm10,
            temperature_K,
            wind_speed,
            pbl_height,
            kz,
            self.cfg.DT,
            emission_pm25,
            emission_pm10
        )

        (
            self.no,
            self.no2,
            self.o3
        ) = self.chemistry.update_gases(
            self.no,
            self.no2,
            self.o3,
            temperature_K,
            radiation,
            wind_speed,
            self.cfg.DT,
            emission_no,
            emission_no2
        )

        # =====================================================
        # LOOP 2
        # CHEMISTRY → METEOROLOGY
        # =====================================================

        (
            new_radiation,
            optical_depth
        ) = self.feedback.radiation_effect(
            self.pm25,
            self.pm10,
            radiation
        )

        new_temperature = (
            self.feedback.temperature_feedback(
                temperature_K,
                radiation,
                new_radiation
            )
        )

        new_pbl = (
            self.feedback.pbl_feedback(
                pbl_height,
                new_temperature
            )
        )

        new_kz = (
            self.inversion.calculate_kz(
                new_pbl,
                wind_speed,
                inversion_strength
            )
        )

        return {

            "time": row["time"],

            "temperature_observed": temperature_K,
            "temperature_model": new_temperature,

            "wind_speed": wind_speed,

            "pbl_observed": pbl_height,
            "pbl_model": new_pbl,

            "radiation_observed": radiation,
            "radiation_model": new_radiation,

            "inversion_strength": inversion_strength,

            "Kz": new_kz,
            "optical_depth": optical_depth,

            "PM25": self.pm25,
            "PM10": self.pm10,

            "NO": self.no,
            "NO2": self.no2,
            "O3": self.o3
        }


# =============================================================
# RUN MODEL
# =============================================================

def run_model(weather_file):

    print("\n")
    print("=" * 70)
    print("REAL-DATA ATMOSPHERIC DUAL-LOOP MODEL")
    print("=" * 70)

    reader = NetCDFMeteorologyReader(
        weather_file
    )

    reader.open()

    weather = reader.to_timeseries()

    reader.summary()

    model = RealDataDualLoop()

    results = []

    print("\nRunning atmospheric model...")

    for index, row in weather.iterrows():

        try:

            result = model.step(row)

            results.append(result)

        except Exception as error:

            print(
                f"\nError at row {index}:"
            )

            print(error)

            continue

        if index % 10 == 0:

            print(
                f"Processed "
                f"{index + 1}/"
                f"{len(weather)}"
            )

    results = pd.DataFrame(
        results
    )

    return results


# =============================================================
# SAVE RESULTS
# =============================================================

def save_results(results, output_dir=None):

    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "outputs"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_dir
        /
        "real_data_dual_loop_results.csv"
    )

    results.to_csv(
        output_file,
        index=False
    )

    print(
        "\nResults saved to:"
    )

    print(
        output_file
    )


# =============================================================
# PLOT RESULTS
# =============================================================

def plot_results(results, output_dir=None):

    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "outputs"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------
    # PM
    # ---------------------------------------------------------

    plt.figure(
        figsize=(12, 5)
    )

    plt.plot(
        results["time"],
        results["PM25"],
        label="PM2.5"
    )

    plt.plot(
        results["time"],
        results["PM10"],
        label="PM10"
    )

    plt.xlabel("Time")
    plt.ylabel("Concentration")

    plt.title(
        "Predicted Particulate Matter"
    )

    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        output_dir /
        "PM_forecast_real_data.png",
        dpi=200
    )

    plt.close()

    # ---------------------------------------------------------
    # O3 / NOx
    # ---------------------------------------------------------

    plt.figure(
        figsize=(12, 5)
    )

    plt.plot(
        results["time"],
        results["O3"],
        label="O3"
    )

    plt.plot(
        results["time"],
        results["NO"],
        label="NO"
    )

    plt.plot(
        results["time"],
        results["NO2"],
        label="NO2"
    )

    plt.xlabel("Time")
    plt.ylabel("Concentration")

    plt.title(
        "Gas Chemistry"
    )

    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        output_dir /
        "gas_chemistry_real_data.png",
        dpi=200
    )

    plt.close()

    # ---------------------------------------------------------
    # Meteorology
    # ---------------------------------------------------------

    plt.figure(
        figsize=(12, 5)
    )

    plt.plot(
        results["time"],
        results["temperature_model"],
        label="Temperature"
    )

    plt.plot(
        results["time"],
        results["pbl_model"],
        label="PBL Height"
    )

    plt.xlabel("Time")
    plt.ylabel("Value")

    plt.title(
        "Meteorology After Aerosol Feedback"
    )

    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        output_dir /
        "meteorology_feedback.png",
        dpi=200
    )

    plt.close()

    # ---------------------------------------------------------
    # Radiation feedback
    # ---------------------------------------------------------

    plt.figure(
        figsize=(12, 5)
    )

    plt.plot(
        results["time"],
        results["radiation_observed"],
        label="Original Radiation"
    )

    plt.plot(
        results["time"],
        results["radiation_model"],
        label="Aerosol-Adjusted Radiation"
    )

    plt.xlabel("Time")
    plt.ylabel("Radiation W/m²")

    plt.title(
        "Aerosol → Radiation Feedback"
    )

    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        output_dir /
        "radiation_feedback.png",
        dpi=200
    )

    plt.close()

    # ---------------------------------------------------------
    # Inversion
    # ---------------------------------------------------------

    plt.figure(
        figsize=(12, 5)
    )

    plt.plot(
        results["time"],
        results["inversion_strength"],
        label="Inversion Strength"
    )

    plt.plot(
        results["time"],
        results["Kz"],
        label="Vertical Mixing Kz"
    )

    plt.xlabel("Time")
    plt.ylabel("Value")

    plt.title(
        "Atmospheric Inversion and Vertical Mixing"
    )

    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()

    plt.savefig(
        output_dir /
        "inversion_mixing.png",
        dpi=200
    )

    plt.close()

    print(
        f"\nPlots saved in {output_dir}/"
    )


# =============================================================
# MAIN
# =============================================================

if __name__ == "__main__":

    WEATHER_FILE = (
        Path(__file__).resolve().parent / "data" / "meteorology" / "weather.nc"
    )

    results = run_model(
        WEATHER_FILE
    )

    save_results(
        results
    )

    plot_results(
        results
    )

    print("\n")
    print("=" * 70)
    print("FINAL MODEL OUTPUT")
    print("=" * 70)

    print(
        results[
            [
                "time",
                "PM25",
                "PM10",
                "O3",
                "NO",
                "NO2",
                "pbl_model",
                "Kz"
            ]
        ].tail(10)
    )

    print("\nStage 2 completed.")
