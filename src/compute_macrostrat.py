"""Macrostrat rock type at the base spot of the night-run places -> data/macrostrat/rock_site.csv.

DISPLAY ONLY: changes no score, rank or config. Default: the 500 Mare places.

    python src/compute_macrostrat.py                    # Mare (base_lon / base_lat)
    python src/compute_macrostrat.py --runs mare polar  # Polar = bowl low point (low_lon / low_lat)

Responses are cached (default <LOCALAPPDATA or home>/espaceodyssey_data/macrostrat_cache), so the
script can be stopped and started again; it then only asks for what is missing.
Source: Macrostrat (macrostrat.org), CC BY 4.0. Rule and columns: src/pipeline/macrostrat.py.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.macrostrat import COLUMNS, Client, lookup  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_HOME = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "espaceodyssey_data"
RUNS = {"polar": ("night_polar", "low_lon", "low_lat"), "mare": ("night_mare", "base_lon", "base_lat")}
FIELDS = ["run", "cell", "lon", "lat", *COLUMNS, "N_UNITS", "SOURCE_ID"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", choices=list(RUNS), default=["mare"])
    ap.add_argument("--out-root", default=str(ROOT / "out"), help="folder with night_polar/ and night_mare/")
    ap.add_argument("--cache", default=str(DATA_HOME / "macrostrat_cache"))
    ap.add_argument("--rate", type=float, default=3.0, help="max requests per second")
    ap.add_argument("--workers", type=int, default=4, help="parallel requests (the rate limit is shared)")
    ap.add_argument("--limit", type=int, help="only the first N places per run (test)")
    ap.add_argument("--dest", default=str(ROOT / "data" / "macrostrat" / "rock_site.csv"))
    a = ap.parse_args(argv)

    client = Client(a.cache, max_per_second=a.rate)
    source_names: dict = {}
    rows, t0 = [], time.time()
    for run in a.runs:
        folder, lon_col, lat_col = RUNS[run]
        df = pd.read_csv(Path(a.out_root) / folder / "ranking.csv")
        if a.limit:
            df = df.head(a.limit)
        def one(r):
            lon, lat = getattr(r, lon_col), getattr(r, lat_col)
            row = {"run": run, "cell": r.id, "lon": "", "lat": "", **{c: "" for c in FIELDS[4:]}}
            if not (pd.isna(lon) or pd.isna(lat)):
                res = lookup(float(lon), float(lat), client, source_names)
                row.update(lon=round(float(lon), 5), lat=round(float(lat), 5),
                           **{c: ("" if res[c] is None else res[c]) for c in COLUMNS},
                           N_UNITS=res["n_units"] or "", SOURCE_ID="" if res["source_id"] is None else res["source_id"])
            return row

        with ThreadPoolExecutor(max_workers=a.workers) as pool:          # map keeps the ranking order
            for i, row in enumerate(pool.map(one, list(df.itertuples(index=False))), 1):
                rows.append(row)
                if i % 50 == 0 or i == len(df):
                    print(f"{run}: {i}/{len(df)}  requests {client.n_requests}  cached {client.n_cached}  "
                          f"{client.bytes_downloaded:,} bytes  {time.time() - t0:.0f} s", flush=True)

    dest = Path(a.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print("wrote", dest, len(rows), "rows")
    print(f"this session: {client.n_requests} requests, {client.bytes_downloaded:,} bytes downloaded, "
          f"{client.n_cached} cache hits")
    print(f"cache total (all sessions): {client.cache_bytes():,} bytes of response bodies in {a.cache}")


if __name__ == "__main__":
    main()
