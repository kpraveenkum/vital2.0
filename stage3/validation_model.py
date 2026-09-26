"""
validation_model.py

STAGE 3
Model vs Observation Validation

Metrics:

    MAE
    RMSE
    Bias
    R2
    Correlation
    MAPE

The code compares:

    MODEL
        vs
    OBSERVATION

for:

    PM2.5
    PM10
    NO2
    O3
    NO
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class ValidationModel:

    def __init__(
        self,
        model_data,
        observation_data
    ):

        self.model = model_data.copy()

        self.observations = (
            observation_data.copy()
        )

        self.comparison = None

        self.model["time"] = (
            pd.to_datetime(
                self.model["time"]
            ).astype("datetime64[ns]")
        )

        self.observations["time"] = (
            pd.to_datetime(
                self.observations["time"]
            ).astype("datetime64[ns]")
        )

    # =========================================================
    # ALIGN DATA
    # =========================================================

    def align_data(
        self,
        tolerance_minutes=30
    ):

        print("\n")
        print("=" * 70)
        print("ALIGNING MODEL AND OBSERVATION DATA")
        print("=" * 70)

        model = (
            self.model
            .sort_values("time")
        )

        obs = (
            self.observations
            .sort_values("time")
        )

        tolerance = pd.Timedelta(
            minutes=tolerance_minutes
        )

        merged = pd.merge_asof(
            model,
            obs,
            on="time",
            direction="nearest",
            tolerance=tolerance,
            suffixes=(
                "_model",
                "_obs"
            )
        )

        self.comparison = merged

        print(
            f"\nModel records: "
            f"{len(model)}"
        )

        print(
            f"Observation records: "
            f"{len(obs)}"
        )

        print(
            f"Matched records: "
            f"{len(merged)}"
        )

        return merged

    # =========================================================
    # METRICS
    # =========================================================

    @staticmethod
    def calculate_metrics(
        observed,
        predicted
    ):

        observed = np.asarray(
            observed,
            dtype=float
        )

        predicted = np.asarray(
            predicted,
            dtype=float
        )

        valid = (
            np.isfinite(observed)
            &
            np.isfinite(predicted)
        )

        observed = observed[valid]
        predicted = predicted[valid]

        n = len(observed)

        if n == 0:

            return {

                "N": 0,
                "MAE": np.nan,
                "RMSE": np.nan,
                "Bias": np.nan,
                "R2": np.nan,
                "Correlation": np.nan,
                "MAPE_percent": np.nan
            }

        error = (
            predicted
            -
            observed
        )

        mae = np.mean(
            np.abs(error)
        )

        rmse = np.sqrt(
            np.mean(
                error ** 2
            )
        )

        bias = np.mean(
            error
        )

        # -----------------------------------------------------
        # R2
        # -----------------------------------------------------

        denominator = np.sum(
            (
                observed
                -
                np.mean(observed)
            ) ** 2
        )

        if denominator > 0:

            r2 = (
                1
                -
                np.sum(
                    error ** 2
                )
                /
                denominator
            )

        else:

            r2 = np.nan

        # -----------------------------------------------------
        # Correlation
        # -----------------------------------------------------

        if (
            np.std(observed) > 0
            and
            np.std(predicted) > 0
        ):

            correlation = np.corrcoef(
                observed,
                predicted
            )[0, 1]

        else:

            correlation = np.nan

        # -----------------------------------------------------
        # MAPE
        # -----------------------------------------------------

        nonzero = (
            np.abs(observed)
            > 1e-10
        )

        if np.any(nonzero):

            mape = (
                np.mean(
                    np.abs(
                        error[nonzero]
                        /
                        observed[nonzero]
                    )
                )
                * 100
            )

        else:

            mape = np.nan

        return {

            "N": n,
            "MAE": mae,
            "RMSE": rmse,
            "Bias": bias,
            "R2": r2,
            "Correlation": correlation,
            "MAPE_percent": mape
        }

    # =========================================================
    # ALL POLLUTANT METRICS
    # =========================================================

    def evaluate(
        self,
        pollutants=None
    ):

        if self.comparison is None:

            self.align_data()

        if pollutants is None:

            pollutants = [
                "PM25",
                "PM10",
                "NO2",
                "O3",
                "NO"
            ]

        results = []

        for pollutant in pollutants:

            model_column = (
                f"{pollutant}_model"
                if f"{pollutant}_model" in self.comparison.columns
                else pollutant
            )
            observation_column = (
                f"{pollutant}_obs"
                if f"{pollutant}_obs" in self.comparison.columns
                else pollutant
            )

            if (
                model_column
                not in self.comparison.columns
            ):

                print(
                    f"\nModel pollutant missing:"
                    f" {pollutant}"
                )

                continue

            if (
                observation_column
                not in self.comparison.columns
            ):

                print(
                    f"\nObservation pollutant "
                    f"missing: {pollutant}"
                )

                continue

            metrics = (
                self.calculate_metrics(
                    self.comparison[
                        observation_column
                    ],
                    self.comparison[
                        model_column
                    ]
                )
            )

            metrics[
                "Pollutant"
            ] = pollutant

            results.append(
                metrics
            )

        result = pd.DataFrame(
            results
        )

        if not result.empty:

            result = result[
                [
                    "Pollutant",
                    "N",
                    "MAE",
                    "RMSE",
                    "Bias",
                    "R2",
                    "Correlation",
                    "MAPE_percent"
                ]
            ]

        return result

    # =========================================================
    # TIME SERIES PLOT
    # =========================================================

    def plot_timeseries(
        self,
        pollutant,
        output_dir="outputs"
    ):

        if self.comparison is None:

            self.align_data()

        output_dir = Path(
            output_dir
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        model_col = f"{pollutant}_model" if f"{pollutant}_model" in self.comparison.columns else pollutant
        obs_col = f"{pollutant}_obs" if f"{pollutant}_obs" in self.comparison.columns else pollutant

        if model_col not in self.comparison.columns or obs_col not in self.comparison.columns:

            print(
                f"Missing model/observation data for: "
                f"{pollutant}"
            )

            return

        plt.figure(
            figsize=(14, 6)
        )

        plt.plot(
            self.comparison["time"],
            self.comparison[model_col],
            label="Model"
        )

        plt.plot(
            self.comparison["time"],
            self.comparison[obs_col],
            label="Observation"
        )

        plt.xlabel(
            "Time"
        )

        plt.ylabel(
            f"{pollutant} concentration"
        )

        plt.title(
            f"{pollutant}: Model vs Observation"
        )

        plt.legend()

        plt.grid(
            True,
            alpha=0.3
        )

        plt.tight_layout()

        filename = (
            output_dir
            /
            f"{pollutant}_timeseries.png"
        )

        plt.savefig(
            filename,
            dpi=200
        )

        plt.close()

    # =========================================================
    # SCATTER PLOT
    # =========================================================

    def plot_scatter(
        self,
        pollutant,
        output_dir="outputs"
    ):

        if self.comparison is None:

            self.align_data()

        output_dir = Path(
            output_dir
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        model_column = (
            f"{pollutant}_model"
            if f"{pollutant}_model" in self.comparison.columns
            else pollutant
        )

        obs_column = (
            f"{pollutant}_obs"
            if f"{pollutant}_obs" in self.comparison.columns
            else pollutant
        )

        if (
            model_column
            not in self.comparison.columns
            or
            obs_column
            not in self.comparison.columns
        ):

            print(
                f"Cannot plot {pollutant}: "
                "data unavailable."
            )

            return

        df = self.comparison[
            [
                model_column,
                obs_column
            ]
        ].dropna()

        if df.empty:

            print(
                f"No valid data for {pollutant}."
            )

            return

        x = df[obs_column].values
        y = df[model_column].values

        plt.figure(
            figsize=(7, 7)
        )

        plt.scatter(
            x,
            y,
            alpha=0.6
        )

        minimum = min(
            np.min(x),
            np.min(y)
        )

        maximum = max(
            np.max(x),
            np.max(y)
        )

        plt.plot(
            [minimum, maximum],
            [minimum, maximum],
            linestyle="--",
            label="1:1 line"
        )

        plt.xlabel(
            "Observed"
        )

        plt.ylabel(
            "Predicted"
        )

        plt.title(
            f"{pollutant}: Observed vs Predicted"
        )

        plt.legend()

        plt.grid(
            True,
            alpha=0.3
        )

        plt.tight_layout()

        filename = (
            output_dir
            /
            f"{pollutant}_scatter.png"
        )

        plt.savefig(
            filename,
            dpi=200
        )

        plt.close()

    # =========================================================
    # RESIDUAL PLOT
    # =========================================================

    def plot_residuals(
        self,
        pollutant,
        output_dir="outputs"
    ):

        if self.comparison is None:

            self.align_data()

        output_dir = Path(
            output_dir
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        model_column = (
            f"{pollutant}_model"
            if f"{pollutant}_model" in self.comparison.columns
            else pollutant
        )

        obs_column = (
            f"{pollutant}_obs"
            if f"{pollutant}_obs" in self.comparison.columns
            else pollutant
        )

        if (
            model_column
            not in self.comparison.columns
            or
            obs_column
            not in self.comparison.columns
        ):

            return

        df = self.comparison[
            [
                "time",
                model_column,
                obs_column
            ]
        ].dropna()

        if df.empty:

            return

        residual = (
            df[model_column]
            -
            df[obs_column]
        )

        plt.figure(
            figsize=(14, 5)
        )

        plt.axhline(
            0,
            linestyle="--"
        )

        plt.plot(
            df["time"],
            residual
        )

        plt.xlabel(
            "Time"
        )

        plt.ylabel(
            "Prediction Error"
        )

        plt.title(
            f"{pollutant}: Model Residual"
        )

        plt.grid(
            True,
            alpha=0.3
        )

        plt.tight_layout()

        filename = (
            output_dir
            /
            f"{pollutant}_residuals.png"
        )

        plt.savefig(
            filename,
            dpi=200
        )

        plt.close()

    # =========================================================
    # GENERATE ALL PLOTS
    # =========================================================

    def generate_plots(
        self,
        pollutants=None,
        output_dir="outputs"
    ):

        if pollutants is None:

            pollutants = [
                "PM25",
                "PM10",
                "NO2",
                "O3"
            ]

        for pollutant in pollutants:

            self.plot_timeseries(
                pollutant,
                output_dir
            )

            self.plot_scatter(
                pollutant,
                output_dir
            )

            self.plot_residuals(
                pollutant,
                output_dir
            )

    # =========================================================
    # SAVE COMPARISON
    # =========================================================

    def save_comparison(
        self,
        output_file
    ):

        if self.comparison is None:

            self.align_data()

        output_file = Path(
            output_file
        )

        output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.comparison.to_csv(
            output_file,
            index=False
        )

        print(
            f"\nComparison saved:"
            f"\n{output_file}"
        )
