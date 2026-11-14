"""Cut a bbox into ~square cells (default 15 km = Artemis III candidate region size)."""
from __future__ import annotations

import math


def make_grid(west, south, east, north, cell_km):
    """Roughly square cells of cell_km x cell_km, in degrees (lon width grows with latitude)."""
    dlat = cell_km / 110.574
    cells = []
    lat = south
    row = 0
    while lat < north - 1e-9:
        top = min(lat + dlat, north)
        mid = (lat + top) / 2
        dlon = cell_km / (111.320 * max(math.cos(math.radians(mid)), 0.01))
        lon = west
        col = 0
        while lon < east - 1e-9:
            right = min(lon + dlon, east)
            cells.append({"id": f"r{row:03d}c{col:03d}", "west": lon, "south": lat,
                          "east": right, "north": top})
            lon = right
            col += 1
        lat = top
        row += 1
    return cells


def cell_area_km2(c):
    mid = math.radians((c["south"] + c["north"]) / 2)
    return ((c["east"] - c["west"]) * 111.320 * math.cos(mid)) * ((c["north"] - c["south"]) * 110.574)


def window_of(c, transform, shape):
    """Row/col slice of a lat/lon raster covering cell c."""
    inv = ~transform
    c0, r0 = inv * (c["west"], c["north"])
    c1, r1 = inv * (c["east"], c["south"])
    r0, r1 = max(0, int(math.floor(r0))), min(shape[0], int(math.ceil(r1)))
    c0, c1 = max(0, int(math.floor(c0))), min(shape[1], int(math.ceil(c1)))
    return slice(r0, r1), slice(c0, c1)
