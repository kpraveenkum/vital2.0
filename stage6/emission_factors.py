"""
emission_factors.py

Stage 6
Emission Factors per Dry Biomass Burned
"""

class EmissionFactors:
    """
    TEST emission factors.

    Units:
        kg pollutant / kg dry biomass

    These are software demonstration parameters.
    Replace them with documented literature values
    before scientific analysis.
    """

    DEFAULT_FACTORS = {
        "PM25": 0.010,
        "PM10": 0.012,
        "CO": 0.060,
        "NOx": 0.003,
        "VOC": 0.008,
    }

    def __init__(self, factors=None):

        if factors is None:
            factors = self.DEFAULT_FACTORS.copy()

        self.factors = factors

    def get(self, pollutant):

        if pollutant not in self.factors:
            raise ValueError(
                f"No emission factor available for {pollutant}"
            )

        return self.factors[pollutant]

    def calculate(self, biomass_kg, pollutant):

        ef = self.get(pollutant)

        return biomass_kg * ef
