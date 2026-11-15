"""Nearest research station for every place in data/access/access_hours.csv (criterion 29, display only).

Uses the lon/lat already in access_hours.csv (Polar low point, Mare base spot) and adds or replaces:
    STATION_NAME, STATION_KM, STATION_TYPE        nearest station of any kind (stations.csv)
    ANALOG_STATION_NAME, ANALOG_STATION_KM        nearest planetary analog station (analog == yes)
Distances are great-circle km. Empty = no data (never 0). Changes no score and no export.

    python src/compute_stations.py
    python src/compute_stations.py --stations data/stations/stations.csv --access data/access/access_hours.csv

Sources and limits: docs/ACCESS.md, section "Research stations".
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.stations import load_stations, nearest_station  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATION_COLUMNS = ["STATION_NAME", "STATION_KM", "STATION_TYPE", "ANALOG_STATION_NAME", "ANALOG_STATION_KM"]


def station_values(lon, lat, stations: pd.DataFrame) -> dict:
    """The five display columns for one point; empty strings for no data."""
    try:
        lon, lat = float(lon), float(lat)
    except (TypeError, ValueError):
        lon = lat = None
    near = nearest_station(lon, lat, stations)
    ana = nearest_station(lon, lat, stations, analog_only=True)
    km = lambda v: "" if v is None else round(v, 1)  # noqa: E731
    return {"STATION_NAME": near["station_name"] or "", "STATION_KM": km(near["station_km"]),
            "STATION_TYPE": near["station_type"] or "",
            "ANALOG_STATION_NAME": ana["station_name"] or "", "ANALOG_STATION_KM": km(ana["station_km"])}


def add_station_columns(df: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    out = df.drop(columns=[c for c in STATION_COLUMNS if c in df.columns])
    vals = [station_values(r["lon"], r["lat"], stations) for _, r in out.iterrows()]
    return pd.concat([out.reset_index(drop=True), pd.DataFrame(vals, columns=STATION_COLUMNS)], axis=1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stations", default=str(ROOT / "data" / "stations" / "stations.csv"))
    ap.add_argument("--access", default=str(ROOT / "data" / "access" / "access_hours.csv"),
                    help="read and rewritten in place")
    a = ap.parse_args(argv)
    stations = load_stations(a.stations)
    print(f"stations: {len(stations)} ({(stations['analog'] == 'yes').sum()} analog)")
    df = pd.read_csv(a.access, keep_default_na=False, dtype=str)
    out = add_station_columns(df, stations)
    out.to_csv(a.access, index=False)
    print("wrote", a.access, len(out), "rows")


if __name__ == "__main__":
    main()
