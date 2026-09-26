"""
spatial_feedback.py

STAGE 4
Spatial Aerosol-Radiation-Meteorology Feedback
"""

import numpy as np


class SpatialFeedback:

    def __init__(self):

        self.pm25_extinction = 0.0015
        self.pm10_extinction = 0.00015

        self.temperature_sensitivity = 0.003

        self.pbl_temperature_sensitivity = 12.0

        self.min_pbl = 50.0

    def aerosol_radiation(
        self,
        pm25,
        pm10,
        radiation
    ):

        optical_depth = (
            self.pm25_extinction * pm25
            +
            self.pm10_extinction * pm10
        )

        new_radiation = (
            radiation
            * np.exp(-optical_depth)
        )

        return new_radiation, optical_depth

    def radiation_temperature(
        self,
        temperature,
        old_radiation,
        new_radiation
    ):

        delta_temperature = (
            self.temperature_sensitivity
            * (
                new_radiation -
                old_radiation
            )
        )

        return temperature + delta_temperature

    def temperature_pbl(
        self,
        pbl,
        temperature
    ):

        reference_temperature = 290.0

        delta_pbl = (
            self.pbl_temperature_sensitivity
            * (
                temperature -
                reference_temperature
            )
        )

        return np.maximum(
            pbl + delta_pbl,
            self.min_pbl
        )

    def apply(
        self,
        pm25,
        pm10,
        temperature,
        radiation,
        pbl
    ):

        (
            new_radiation,
            optical_depth
        ) = self.aerosol_radiation(
            pm25, pm10, radiation
        )

        new_temperature = (
            self.radiation_temperature(
                temperature,
                radiation,
                new_radiation
            )
        )

        new_pbl = (
            self.temperature_pbl(
                pbl,
                new_temperature
            )
        )

        return {
            "radiation": new_radiation,
            "temperature": new_temperature,
            "pbl": new_pbl,
            "optical_depth": optical_depth,
        }
