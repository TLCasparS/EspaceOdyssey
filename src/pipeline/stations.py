"""Research stations near a place (criterion 29). Display only, NOT part of the Moon score.

stations.csv (built by src/build_stations.py) holds one row per station:
    name, operator, lat, lon, type, season, analog, source, dataset, status, year_established
`analog` is "yes" for planetary analog stations (hand-made list), "no" for all others.

nearest_station() gives the great-circle nearest station (same haversine and Earth radius as
pipeline.access). No data is None, never 0.

Sources, licences and limits: docs/ACCESS.md, section "Research stations".
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from pipeline.access import haversine_km

STATION_FIELDS = ["name", "operator", "lat", "lon", "type", "season", "analog", "source", "dataset",
                  "status", "year_established"]


def load_stations(csv_path) -> pd.DataFrame:
    """stations.csv -> rows with valid coordinates. keep_default_na=False keeps "NA"-like text as text."""
    df = pd.read_csv(csv_path, keep_default_na=False, dtype=str)
    missing = [c for c in ("name", "lat", "lon", "type", "analog") if c not in df.columns]
    if missing:
        raise ValueError(f"{csv_path}: missing columns {missing}")
    for c in ("lat", "lon"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[np.isfinite(df["lat"]) & np.isfinite(df["lon"])]
    df = df[df["lat"].between(-90, 90) & df["lon"].between(-180, 180)]
    return df.reset_index(drop=True)


def nearest_station(lon: float, lat: float, stations: pd.DataFrame, analog_only: bool = False) -> dict:
    """Nearest station by great-circle distance.

    analog_only=True looks only at rows with analog == "yes".
    Returns {"station_km", "station_name", "station_type", "station_dataset"}; all None if the table
    (after the analog filter) is empty or the point is invalid.
    """
    empty = {"station_km": None, "station_name": None, "station_type": None, "station_dataset": None}
    if lon is None or lat is None or not (math.isfinite(lon) and math.isfinite(lat)):
        return empty
    df = stations[stations["analog"].str.strip().str.lower() == "yes"] if analog_only else stations
    if len(df) == 0:
        return empty
    d = haversine_km(lon, lat, df["lon"].to_numpy(), df["lat"].to_numpy())
    i = int(np.argmin(d))
    row = df.iloc[i]
    return {"station_km": float(d[i]), "station_name": row["name"], "station_type": row["type"],
            "station_dataset": row.get("dataset", None) or None}
