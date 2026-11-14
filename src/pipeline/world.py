"""World cell grid shared by stage0_world.py and night_run.py --world.

Cells are the same ~15 km cells as everywhere (pipeline.cells.make_grid), built on latitude BANDS that span
the full 360 deg and hold a whole number of cell rows (BAND_ROWS), so no partial rows appear at band edges.
A cell belongs to the 1 x 1 deg tile that holds its centre (tile id "N35W112" style, as Copernicus DEM).
Cell id: "<band>_r<row>c<col>", e.g. "b056_r003c01234" (unique worldwide).
"""
from __future__ import annotations

import math
from functools import lru_cache

from pipeline.cells import make_grid

CELL_KM = 15.0
DLAT = CELL_KM / 110.574             # as make_grid
BAND_ROWS = 8
BAND_H = BAND_ROWS * DLAT
LAT0, LAT1 = -60.0, 84.0             # Antarctica excluded; WorldCover / UTM range


def tile_id(lat0: int, lon0: int) -> str:
    return f"{'N' if lat0 >= 0 else 'S'}{abs(lat0):02d}{'E' if lon0 >= 0 else 'W'}{abs(lon0):03d}"


def parse_tile(tid: str) -> tuple[int, int]:
    lat = int(tid[1:3]) * (1 if tid[0] == "N" else -1)
    lon = int(tid[4:7]) * (1 if tid[3] == "E" else -1)
    return lat, lon


def bands_for_lat(lat_s: float, lat_n: float) -> range:
    k0 = max(0, math.floor((lat_s - LAT0) / BAND_H))
    k1 = math.floor((min(lat_n, LAT1) - 1e-9 - LAT0) / BAND_H)
    return range(k0, k1 + 1)


@lru_cache(maxsize=64)
def band_cells(k: int) -> tuple:
    s = LAT0 + k * BAND_H
    n = min(s + BAND_H, LAT1)
    cells = make_grid(-180.0, s, 180.0, n, CELL_KM)
    for c in cells:
        c["id"] = f"b{k:03d}_{c['id']}"
    return tuple(cells)


@lru_cache(maxsize=64)
def band_index(k: int) -> dict:
    """{(lat0, lon0): [cells]} for band k, by cell centre (built once per band)."""
    idx = {}
    for c in band_cells(k):
        la, lo = (c["south"] + c["north"]) / 2, (c["west"] + c["east"]) / 2
        idx.setdefault((math.floor(la), math.floor(lo)), []).append(c)
    return idx


def tile_cells(lat0: int, lon0: int) -> list[dict]:
    """Cells whose centre lies in the 1 deg tile [lat0, lat0+1) x [lon0, lon0+1)."""
    out = []
    for k in bands_for_lat(lat0, lat0 + 1):
        out += [dict(c) for c in band_index(k).get((lat0, lon0), [])]
    return out


def land_tiles(tile_list_path, lat_min=LAT0, lat_max=LAT1) -> list[tuple[int, int]]:
    """1 deg tiles that have a Copernicus DEM tile (= land), from the bucket's tileList.txt."""
    import re
    out = []
    for line in open(tile_list_path, encoding="utf-8"):
        m = re.search(r"_([NS])(\d\d)_00_([EW])(\d{3})_00_DEM", line)
        if not m:
            continue
        lat = int(m.group(2)) * (1 if m.group(1) == "N" else -1)
        lon = int(m.group(4)) * (1 if m.group(3) == "E" else -1)
        if lat_min <= lat < lat_max:
            out.append((lat, lon))
    return sorted(set(out))
