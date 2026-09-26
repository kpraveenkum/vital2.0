"""
biomass_emission_model.py

Stage 6
Biomass Burning Emission Calculator
"""

import pandas as pd

from emission_factors import EmissionFactors


class BiomassEmissionModel:
    """
    Calculates pollutant emissions from estimated
    burned biomass.
    """

    def __init__(self, emission_factors=None):

        if emission_factors is None:
            emission_factors = EmissionFactors()

        self.emission_factors = emission_factors

    def calculate_fire_emissions(
        self,
        biomass_burned_kg,
        active_duration_seconds,
    ):

        pollutants = {}

        for pollutant in self.emission_factors.factors:

            mass = self.emission_factors.calculate(
                biomass_burned_kg,
                pollutant
            )

            rate = (
                mass
                / active_duration_seconds
            )

            pollutants[pollutant] = {
                "mass_kg": mass,
                "rate_kg_s": rate,
            }

        return pollutants

    def apply(self, fires):

        fires = fires.copy()

        duration = fires["biomass_burned_kg"] / (
            fires["biomass_burn_rate_kg_s"]
            .replace(0, float("nan"))
        )

        duration = duration.fillna(600)

        for pollutant in self.emission_factors.factors:

            ef = self.emission_factors.get(
                pollutant
            )

            fires[
                f"{pollutant}_emission_kg"
            ] = (
                fires["biomass_burned_kg"]
                * ef
            )

            fires[
                f"{pollutant}_emission_kg_s"
            ] = (
                fires[
                    f"{pollutant}_emission_kg"
                ]
                / duration
            )

        return fires


if __name__ == "__main__":
    from pathlib import Path
    FILE = Path(__file__).resolve().parent / "data" / "satellite" / "fires.csv"
    if FILE.exists():
        fires = pd.read_csv(FILE)
        from frp_model import FRPModel
        from biomass_burned_model import BiomassBurnedModel

        fires = FRPModel().apply(fires)
        fires = BiomassBurnedModel().apply(fires)

        model = BiomassEmissionModel()
        result = model.apply(fires)
        print(result)
