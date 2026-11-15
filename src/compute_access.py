"""Accessibility display values for every place of the night runs -> data/access/access_hours.csv.

Points: Polar = bowl low point (low_lon, low_lat), Mare = base spot (base_lon, base_lat).
Reads out/ only. Display data: changes no score and no export.

    python src/compute_access.py
    python src/compute_access.py --raster <travel_time.tif> --airports <airports.csv>

Columns: run, cell, lon, lat, ACCESS_HOURS, AIRPORT_KM, AIRPORT_NAME, AIRPORT_TYPE, AIRPORT_IDENT, and, when
data/stations/stations.csv exists, the station columns of src/compute_stations.py (criterion 29).
Empty = no data (never 0). Sources and limits: docs/ACCESS.md.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.access import AIRPORT_TYPES, TravelTimeRaster, load_airports, nearest_airport  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_HOME = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "espaceodyssey_data"
DEFAULT_RASTER = DATA_HOME / "access_weiss2018" / "201501_Global_Travel_Time_to_Cities_2015.tif"
DEFAULT_AIRPORTS = DATA_HOME / "ourairports" / "airports.csv"
RUNS = {"polar": ("night_polar", "low_lon", "low_lat"), "mare": ("night_mare", "base_lon", "base_lat")}
FIELDS = ["run", "cell", "lon", "lat", "ACCESS_HOURS", "AIRPORT_KM", "AIRPORT_NAME", "AIRPORT_TYPE",
          "AIRPORT_IDENT"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-root", default=str(ROOT / "out"), help="folder with night_polar/ and night_mare/")
    ap.add_argument("--raster", default=str(DEFAULT_RASTER), help="travel time to cities GeoTIFF (minutes)")
    ap.add_argument("--airports", default=str(DEFAULT_AIRPORTS), help="OurAirports airports.csv")
    ap.add_argument("--dest", default=str(ROOT / "data" / "access" / "access_hours.csv"))
    ap.add_argument("--stations", default=str(ROOT / "data" / "stations" / "stations.csv"),
                    help="stations.csv for the criterion 29 columns; skipped if the file is missing")
    a = ap.parse_args(argv)

    airports = load_airports(a.airports)
    print(f"airports: {len(airports)} of types {AIRPORT_TYPES}")

    rows = []
    with TravelTimeRaster(a.raster) as tt:
        print("raster:", a.raster, tt.ds.width, "x", tt.ds.height, "nodata", tt.nodata)
        for run, (folder, lon_col, lat_col) in RUNS.items():
            df = pd.read_csv(Path(a.out_root) / folder / "ranking.csv")
            n_nodata = 0
            for _, r in df.iterrows():
                if pd.isna(r[lon_col]) or pd.isna(r[lat_col]):
                    rows.append({"run": run, "cell": r["id"], "lon": "", "lat": "", "ACCESS_HOURS": "",
                                 "AIRPORT_KM": "", "AIRPORT_NAME": "", "AIRPORT_TYPE": "", "AIRPORT_IDENT": ""})
                    n_nodata += 1
                    continue
                lon, lat = float(r[lon_col]), float(r[lat_col])
                hours = tt.hours(lon, lat)
                n_nodata += hours is None
                air = nearest_airport(lon, lat, airports)
                rows.append({"run": run, "cell": r["id"], "lon": round(lon, 5), "lat": round(lat, 5),
                             "ACCESS_HOURS": "" if hours is None else round(hours, 2),
                             "AIRPORT_KM": "" if air["airport_km"] is None else round(air["airport_km"], 1),
                             "AIRPORT_NAME": air["airport_name"] or "",
                             "AIRPORT_TYPE": air["airport_type"] or "",
                             "AIRPORT_IDENT": air["airport_ident"] or ""})
            print(f"{run}: {len(df)} places, {n_nodata} without travel time (no data)")

    dest = Path(a.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("wrote", dest, len(rows), "rows")

    if Path(a.stations).exists():
        from compute_stations import main as add_stations
        add_stations(["--stations", a.stations, "--access", str(dest)])
    else:
        print("no", a.stations, "- station columns skipped (run src/build_stations.py)")


if __name__ == "__main__":
    main()
