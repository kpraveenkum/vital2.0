"""
spatial_chemistry.py

STAGE 4
Spatial Chemical Kinetics and Mass Balance
"""

import numpy as np


class SpatialChemistry:

    def __init__(self, grid):

        self.grid = grid

        self.R = 8.314
        self.A = 1.0e-3
        self.EA = 3000.0

        self.max_pm = 10000.0
        self.max_gas = 1000.0

    def reaction_rate(self, temperature):

        return (
            self.A
            * np.exp(
                -self.EA
                / (self.R * temperature)
            )
        )

    def photolysis_rate(self, radiation):

        radiation = np.clip(
            radiation, 0.0, 700.0
        )

        return (
            0.0015
            * radiation
            / 700.0
        )

    def update_pm(
        self,
        pm25,
        pm10,
        temperature,
        pbl,
        wind_speed,
        dt,
        emission_pm25,
        emission_pm10
    ):

        volume_factor = (
            1.0 /
            np.maximum(pbl, 50.0)
        )

        k = self.reaction_rate(
            temperature
        )

        pm25_source = (
            emission_pm25 * volume_factor
        )

        pm10_source = (
            emission_pm10 * volume_factor
        )

        secondary = 100.0 * k

        wind_loss = 1.0e-5 * wind_speed
        mixing_loss = 1.0e-8 * pbl

        dpm25 = (
            pm25_source
            + secondary
            - wind_loss * pm25
            - mixing_loss * pm25
        )

        dpm10 = (
            pm10_source
            + 0.3 * secondary
            - wind_loss * pm10
            - mixing_loss * pm10
        )

        pm25_new = pm25 + dt * dpm25
        pm10_new = pm10 + dt * dpm10

        return (
            np.clip(
                pm25_new, 0.0, self.max_pm
            ),
            np.clip(
                pm10_new, 0.0, self.max_pm
            )
        )

    def update_gases(
        self,
        no,
        no2,
        o3,
        temperature,
        radiation,
        wind_speed,
        dt,
        emission_no,
        emission_no2
    ):

        k = self.reaction_rate(
            temperature
        )

        J = self.photolysis_rate(
            radiation
        )

        photolysis = J * no2

        titration = k * no * o3

        ozone_production = 0.5 * photolysis

        dilution = 1.0e-5 * wind_speed

        dno = (
            emission_no
            + photolysis
            - titration
            - dilution * no
        )

        dno2 = (
            emission_no2
            - photolysis
            + titration
            - dilution * no2
        )

        do3 = (
            ozone_production
            - titration
            - 1.0e-5 * o3
        )

        no_new = np.clip(
            no + dt * dno,
            0.0, self.max_gas
        )

        no2_new = np.clip(
            no2 + dt * dno2,
            0.0, self.max_gas
        )

        o3_new = np.clip(
            o3 + dt * do3,
            0.0, self.max_gas
        )

        return no_new, no2_new, o3_new
