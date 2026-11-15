"""Build data/stations/stations.csv from two sources (criterion 29, display only).

1. INTERACT GIS station list, JSON behind interact-gis.org/Home/Stations (https://interact-gis.org/api/StationList/).
   Only name, operating country, coordinates and operating period are kept: no contact names, e-mails or phones.
   Rows the site hides (Hidden = true) are dropped.
2. Hand-made list of planetary analog stations, data/stations/analog_stations_manual.csv (source link per row).

COMNAP Antarctic Facilities is NOT used (team decision 15 Nov 2026): its licence is educational / non-commercial
only, which clashes with the Space Apps rule on third-party material, and no night-run place had a COMNAP
station within 500 km. See docs/ACCESS.md.

    python src/build_stations.py --fetch          # download 1 into ~/espaceodyssey_data/stations/ first
    python src/build_stations.py                  # use files already downloaded

Columns: name, operator, lat, lon, type, season, analog, source, dataset, status, year_established.
Empty = no data. See docs/ACCESS.md.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.stations import STATION_FIELDS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_HOME = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "espaceodyssey_data" / "stations"
INTERACT_URL = "https://interact-gis.org/api/StationList/"
INTERACT_SOURCE = "https://interact-gis.org/Home/Stations"
USER_AGENT = "moon-analog-research-script"


def fetch(dest_dir: Path):
    dest_dir.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(INTERACT_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        (dest_dir / "interact_stationlist.json").write_bytes(r.read())
    print("downloaded into", dest_dir)


def _lon180(lon: float) -> float:
    return lon - 360.0 if lon > 180.0 else lon


def interact_rows(path) -> tuple[list[dict], list[str]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows, hidden = [], []
    for s in data:
        name = (s.get("StationName") or "").strip()
        if s.get("Hidden"):
            hidden.append(name)
            continue
        lat, lon = s.get("Latitude"), s.get("Longitude")
        if lat is None or lon is None:
            continue
        lon = _lon180(float(lon))
        period = (s.get("OperatingPeriod") or "").strip()
        season = "Year-Round" if period.lower().replace(" ", "-") == "year-round" else period
        rows.append({"name": name, "operator": (s.get("OperatingCountry") or "").strip(),
                     "lat": round(float(lat), 5), "lon": round(lon, 5),
                     "type": "research station" if s.get("StationType") == 0 else f"INTERACT type {s.get('StationType')}",
                     "season": season, "analog": "no", "source": INTERACT_SOURCE, "dataset": "INTERACT GIS",
                     "status": "open" if s.get("StationStatus") == 0 else f"INTERACT status {s.get('StationStatus')}",
                     "year_established": s.get("OpeningYear") or ""})
    return rows, hidden


def manual_rows(path) -> list[dict]:
    df = pd.read_csv(path, keep_default_na=False, dtype=str)
    return [{"name": r["name"], "operator": r["operator"], "lat": float(r["lat"]), "lon": float(r["lon"]),
             "type": r["type"], "season": r["season"], "analog": r["analog"], "source": r["source"],
             "dataset": "manual analog list", "status": "", "year_established": ""} for _, r in df.iterrows()]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fetch", action="store_true", help="download the INTERACT station list first")
    ap.add_argument("--src-dir", default=str(DATA_HOME))
    ap.add_argument("--manual", default=str(ROOT / "data" / "stations" / "analog_stations_manual.csv"))
    ap.add_argument("--dest", default=str(ROOT / "data" / "stations" / "stations.csv"))
    a = ap.parse_args(argv)
    src = Path(a.src_dir)
    if a.fetch:
        fetch(src)

    interact, hidden = interact_rows(src / "interact_stationlist.json")
    manual = manual_rows(a.manual)
    print(f"INTERACT {len(interact)} kept, {len(hidden)} hidden dropped | manual analog {len(manual)}")

    dest = Path(a.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=STATION_FIELDS)
        w.writeheader()
        w.writerows(interact + manual)
    print("wrote", dest, len(interact) + len(manual), "rows")


if __name__ == "__main__":
    main()
