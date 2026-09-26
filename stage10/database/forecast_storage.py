"""
forecast_storage.py

SQLite storage manager for saving 24/48/72-hour air quality forecasts,
run metadata, and verification metrics into a persistent relational store.
"""

from pathlib import Path
import sqlite3
import pandas as pd


class ForecastDatabase:

    def __init__(self, database_file):
        self.database_file = Path(database_file)
        self.database_file.parent.mkdir(parents=True, exist_ok=True)

    def connect(self):
        return sqlite3.connect(self.database_file)

    def save_forecast(self, df, table="forecast"):
        df_to_save = df.copy()

        # Convert Timestamp object columns to string representation for SQLite compatibility
        for col in df_to_save.columns:
            if pd.api.types.is_datetime64_any_dtype(df_to_save[col]):
                df_to_save[col] = df_to_save[col].dt.strftime("%Y-%m-%d %H:%M:%S")

        with self.connect() as connection:
            df_to_save.to_sql(table, connection, if_exists="append", index=False)

    def read_forecast(self, table="forecast"):
        with self.connect() as connection:
            return pd.read_sql_query(f"SELECT * FROM {table}", connection)

    def clear_table(self, table="forecast"):
        with self.connect() as connection:
            connection.execute(f"DROP TABLE IF EXISTS {table}")
