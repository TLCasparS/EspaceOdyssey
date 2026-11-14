"""A1 prescreen on synthetic GLO-90 data: a round bowl passes, an elongated trench and a shallow dip do not."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

from pipeline.a1 import a1_tile, skip_reason  # noqa: E402
from pipeline.world import tile_cells  # noqa: E402

LIM = {"min_depth_m": 25.0, "min_width_m": 700.0, "max_elongation": 2.0}
LAT0 = 35.0


def _xy(lon, lat):
    return (lon * 111_320 * math.cos(math.radians(LAT0 + 0.5)), lat * 110_574)


def _tile():
    d = 1 / 1200
    tf = from_origin(-112.05, 36.05, d, d)
    cc, rr = np.meshgrid(np.arange(1320) + 0.5, np.arange(1320) + 0.5)
    lon, lat = tf * (cc, rr)
    z = np.full(lon.shape, 1000.0)
    # round bowl r 1.5 km, 120 m deep at 35.25 N 111.75 W
    x, y = _xy(lon + 111.75, lat - 35.25)
    r = np.hypot(x, y)
    z -= np.where(r < 1500, 120 * (1 - r ** 2 / 1500 ** 2), 0)
    # trench 8 km x 0.8 km, 80 m deep at 35.75 N 111.25 W (elongation ~ 3.5 -> rejected)
    x, y = _xy(lon + 111.25, lat - 35.75)
    q = np.hypot(x / 4000, y / 400)
    z -= np.where(q < 1, 80 * (1 - q ** 2), 0)
    # shallow dip r 2 km, 10 m deep at 35.25 N 111.25 W (too shallow)
    x, y = _xy(lon + 111.25, lat - 35.25)
    r = np.hypot(x, y)
    z -= np.where(r < 2000, 10 * (1 - r ** 2 / 2000 ** 2), 0)
    return z.astype(np.float32), tf


def test_a1_bowl_only():
    z, tf = _tile()
    cells = tile_cells(35, -112)
    hits = a1_tile(z, tf, cells, LIM)
    found = [(cid, d) for cid, v in hits.items() for d in v]
    assert len(found) == 1
    cid, d = found[0]
    c = next(c for c in cells if c["id"] == cid)
    assert c["west"] <= -111.75 < c["east"] and c["south"] <= 35.25 < c["north"]
    assert d["depth_m"] == pytest.approx(120, abs=15) and d["width_m"] == pytest.approx(3000, rel=0.15)
    assert d["elongation"] < 1.3
    assert "25 m deep" in skip_reason(LIM) and "GLO-90" in skip_reason(LIM)


def test_a1_lenient_limits_are_options():
    z, tf = _tile()
    cells = tile_cells(35, -112)
    loose = {**LIM, "min_depth_m": 5.0, "max_elongation": 5.0}       # now the dip and the trench pass too
    assert sum(len(v) for v in a1_tile(z, tf, cells, loose).values()) == 3
