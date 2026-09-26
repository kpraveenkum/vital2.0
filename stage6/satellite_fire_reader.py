"""
satellite_fire_reader.py

Stage 6
Satellite Fire Data Reader
"""

import pandas as pd


class SatelliteFireReader:
    """
    Reads and standardizes satellite fire observations.

    Required columns:
        latitude
        longitude
        acq_date
        acq_time
        frp

    Optional columns:
        confidence
        satellite
    """

    def __init__(self, file_path):
        self.file_path = file_path

    def read(self):
        df = pd.read_csv(self.file_path)

        required = [
            "latitude",
            "longitude",
            "acq_date",
            "acq_time",
            "frp",
        ]

        missing = [col for col in required if col not in df.columns]

        if missing:
            raise ValueError(
                f"Missing required satellite-fire columns: {missing}"
            )

        # Convert numeric columns
        for col in ["latitude", "longitude", "frp"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        # Parse acquisition date
        df["acq_date"] = pd.to_datetime(
            df["acq_date"],
            errors="coerce"
        )

        # Parse acquisition time in HHMM format
        def parse_hhmm(value):
            try:
                value = int(value)
                hours = value // 100
                minutes = value % 100

                if hours > 23 or minutes > 59:
                    return None

                return hours * 3600 + minutes * 60

            except Exception:
                return None

        df["acq_seconds"] = df["acq_time"].apply(parse_hhmm)

        # Create combined timestamp
        df["datetime"] = df.apply(
            lambda row: (
                row["acq_date"]
                + pd.to_timedelta(row["acq_seconds"], unit="s")
                if pd.notna(row["acq_date"])
                and pd.notna(row["acq_seconds"])
                else pd.NaT
            ),
            axis=1,
        )

        # Optional fields
        if "confidence" not in df.columns:
            df["confidence"] = "unknown"

        if "satellite" not in df.columns:
            df["satellite"] = "unknown"

        # Standardize confidence text
        df["confidence"] = (
            df["confidence"]
            .astype(str)
            .str.lower()
            .str.strip()
        )

        # Remove invalid values
        df = df.dropna(
            subset=[
                "latitude",
                "longitude",
                "datetime",
                "frp",
            ]
        )

        # FRP cannot be negative
        df = df[df["frp"] >= 0]

        df = df.sort_values("datetime").reset_index(drop=True)

        return df


if __name__ == "__main__":
    from pathlib import Path
    FILE = Path(__file__).resolve().parent / "data" / "satellite" / "fires.csv"
    reader = SatelliteFireReader(FILE)

    fires = reader.read()

    print(fires.head())
    print("\nNumber of fires:", len(fires))
