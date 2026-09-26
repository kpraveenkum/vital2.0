"""
biomass_burned_model.py

Stage 6
Biomass Burned Mass Estimator
"""

import pandas as pd


class BiomassBurnedModel:
    """
    Estimates total biomass burned from the estimated
    biomass burning rate.

    The active duration is a prototype assumption and
    should be replaced by a documented fire-duration
    methodology.
    """

    def __init__(self, active_duration_seconds=600):
        self.active_duration_seconds = (
            active_duration_seconds
        )

    def calculate(self, burn_rate):
        return (
            burn_rate
            * self.active_duration_seconds
        )

    def apply(self, fires):
        fires = fires.copy()

        fires["biomass_burned_kg"] = (
            fires["biomass_burn_rate_kg_s"]
            .apply(self.calculate)
        )

        return fires


if __name__ == "__main__":
    from pathlib import Path
    FILE = Path(__file__).resolve().parent / "data" / "satellite" / "fires.csv"
    if FILE.exists():
        fires = pd.read_csv(FILE)
        fires["biomass_burn_rate_kg_s"] = fires["frp"] * 0.0005
        model = BiomassBurnedModel()
        result = model.apply(fires)
        print(result)
