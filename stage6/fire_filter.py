"""
fire_filter.py

Stage 6
Satellite Fire Filtering Engine
"""

import pandas as pd


class FireFilter:
    """
    Filters satellite fire detections.

    The filters identify fires that are relevant to the
    study region and potentially relevant to biomass burning.

    NOTE:
    Passing these filters does NOT prove that a fire is
    agricultural/stubble burning.
    """

    def __init__(
        self,
        lat_min=27.0,
        lat_max=30.5,
        lon_min=75.5,
        lon_max=79.5,
        min_frp=5.0,
        allowed_confidence=None,
        start_month=None,
        end_month=None,
    ):

        self.lat_min = lat_min
        self.lat_max = lat_max
        self.lon_min = lon_min
        self.lon_max = lon_max
        self.min_frp = min_frp

        if allowed_confidence is None:
            allowed_confidence = ["high", "nominal"]

        self.allowed_confidence = [
            str(x).lower()
            for x in allowed_confidence
        ]

        self.start_month = start_month
        self.end_month = end_month

    def apply(self, fires):

        mask = (
            (fires["latitude"] >= self.lat_min)
            & (fires["latitude"] <= self.lat_max)
            & (fires["longitude"] >= self.lon_min)
            & (fires["longitude"] <= self.lon_max)
            & (fires["frp"] >= self.min_frp)
        )

        filtered = fires[mask].copy()

        # Confidence filter
        if self.allowed_confidence:
            filtered = filtered[
                filtered["confidence"].isin(
                    self.allowed_confidence
                )
            ]

        # Optional seasonal filter
        if self.start_month is not None:
            if self.end_month is not None:

                month = filtered["datetime"].dt.month

                if self.start_month <= self.end_month:
                    filtered = filtered[
                        (month >= self.start_month)
                        & (month <= self.end_month)
                    ]

                else:
                    # Handles periods such as November -> February
                    filtered = filtered[
                        (month >= self.start_month)
                        | (month <= self.end_month)
                    ]

        return filtered.reset_index(drop=True)


if __name__ == "__main__":
    from pathlib import Path
    FILE = Path(__file__).resolve().parent / "data" / "satellite" / "fires.csv"
    if FILE.exists():
        fires = pd.read_csv(FILE)
        fire_filter = FireFilter()
        print(fire_filter.apply(fires))
