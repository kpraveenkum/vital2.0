"""
frp_model.py

Stage 6
FRP to Biomass Burn Rate Conversion
"""

import pandas as pd


class FRPModel:
    """
    Converts satellite FRP into an estimated biomass
    burning rate.

    IMPORTANT:
    The default coefficient is a software TEST value.
    It is not a universal physical constant.
    """

    def __init__(self, frp_to_burn_rate=0.0005):
        self.frp_to_burn_rate = frp_to_burn_rate

    def calculate_burn_rate(self, frp):
        return self.frp_to_burn_rate * frp

    def apply(self, fires):
        fires = fires.copy()

        fires["biomass_burn_rate_kg_s"] = (
            fires["frp"]
            .apply(self.calculate_burn_rate)
        )

        return fires


if __name__ == "__main__":
    from pathlib import Path
    FILE = Path(__file__).resolve().parent / "data" / "satellite" / "fires.csv"
    if FILE.exists():
        fires = pd.read_csv(FILE)
        model = FRPModel()
        result = model.apply(fires)
        print(result)
