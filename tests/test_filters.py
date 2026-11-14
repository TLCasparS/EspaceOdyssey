"""Offline checks for src/pipeline/filters.py (synthetic land cover and population only)."""
import copy
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

from dem.terrain import pixel_size_m  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.filters import (Population, check_classes, distance_m, evaluate_cell,  # noqa: E402
                              pixel_masks)

CFG = load_config()
F = CFG["filter"]
RES = 100 / 111_320.0          # ~100 m pixels, like read_landcover(res_m=100)
LAT0, LON0 = 28.6, 83.5


def _raster(n=160, fill=30):
    tf = from_origin(LON0, LAT0, RES, RES)    # NW corner
    return np.full((n, n), fill, np.uint8), tf


def _cell(tf, n):
    """Cell covering the whole n x n raster."""
    return {"id": "t", "west": tf.c, "north": tf.f, "east": tf.c + n * RES, "south": tf.f - n * RES}


def test_config_class_lists_cover_every_class_once():
    check_classes(F)
    bad = dict(F, keep_classes=[20, 30, 60, 70])          # 100 moss missing
    with pytest.raises(ValueError, match="neither"):
        check_classes(bad)
    with pytest.raises(ValueError, match="both"):
        check_classes(dict(F, keep_classes=F["keep_classes"] + [10]))


def test_built_up_buffer_reaches_2km_not_3km():
    lc, tf = _raster()
    c = 80
    lc[c, c] = 50                                          # one built-up pixel
    m = pixel_masks(lc, tf, F)
    dx, dy = pixel_size_m(tf, LAT0 - c * RES)
    k_in, k_out = math.floor(2000 / dy), math.floor(2000 / dy) + 1
    assert m["near_built"][c - k_in, c] and not m["usable"][c - k_in, c]          # < 2 km north
    assert m["usable"][c - k_out, c]                                              # just beyond 2 km
    j_in, j_out = math.floor(2000 / dx), math.floor(2000 / dx) + 1                # east: narrower pixels
    assert not m["usable"][c, c + j_in] and m["usable"][c, c + j_out]
    assert m["usable"][c - round(3000 / dy), c]                                   # 3 km: usable


def test_water_buffer_200m_and_kept_classes_survive():
    lc, tf = _raster()
    for k, cls in enumerate(F["keep_classes"]):            # stripes of every kept class
        lc[k * 10:(k + 1) * 10, :] = cls
    lc[120, 80] = 80                                        # one water pixel, far from the stripes
    m = pixel_masks(lc, tf, F)
    assert m["usable"][:50].all()                           # all kept classes usable
    dx, dy = pixel_size_m(tf, LAT0 - 120 * RES)
    assert not m["usable"][120 - math.floor(200 / dy), 80]
    assert m["usable"][120 - math.floor(200 / dy) - 1, 80]
    assert not m["usable"][120, 80]                         # the water pixel itself


def test_every_drop_class_is_unusable():
    lc, tf = _raster(n=20)
    for cls in F["drop_classes"]:
        lc[:] = cls
        assert not pixel_masks(lc, tf, F)["usable"].any(), cls


def test_cell_with_enough_usable_but_tiny_patches_is_dropped():
    n = 160
    lc, tf = _raster(n, fill=10)                            # trees everywhere ...
    for i in range(0, n, 4):                                # ... with 3x3 grass blocks, 1 px apart
        for j in range(0, n, 4):
            lc[i:i + 3, j:j + 3] = 30
    m = pixel_masks(lc, tf, F)
    row = evaluate_cell(_cell(tf, n), lc, tf, m, F)
    assert row["usable"] >= F["min_usable"]                 # 9/16 = 56 % usable ...
    assert not row["keep"] and row["reason"].startswith("patch")   # ... but no 2 km2 patch

    lc2, _ = _raster(n)                                     # control: all grass
    row2 = evaluate_cell(_cell(tf, n), lc2, tf, pixel_masks(lc2, tf, F), F)
    assert row2["keep"] and row2["reason"] == ""


def test_ocean_cell_is_dropped():
    lc, tf = _raster(fill=0)
    lc[:, :40] = 60
    row = evaluate_cell(_cell(tf, 160), lc, tf, pixel_masks(lc, tf, F), F)
    assert not row["keep"] and "ocean/no-data" in row["reason"]


def test_population_filter(tmp_path):
    lc, tf = _raster()
    cell = _cell(tf, 160)

    def pop_file(value):
        p = tmp_path / f"pop_{value}.tif"
        ptf = from_origin(LON0 - 1, LAT0 + 1, 0.01, 0.01)
        with rasterio.open(p, "w", driver="GTiff", height=300, width=300, count=1, dtype="float32",
                           crs="EPSG:4326", transform=ptf) as dst:
            dst.write(np.full((300, 300), value, np.float32), 1)
        return Population(p)

    m = pixel_masks(lc, tf, F)
    crowded = evaluate_cell(cell, lc, tf, m, F, pop_file(1000.0))   # ~1000 people per ~1 km2 pixel
    assert not crowded["keep"] and "pop" in crowded["reason"] and crowded["pop_per_km2"] > 10
    empty = evaluate_cell(cell, lc, tf, m, F, pop_file(0.0))
    assert empty["keep"] and empty["pop_per_km2"] == 0


def test_distance_without_targets_is_inf():
    _, tf = _raster(n=10)
    assert np.isinf(distance_m(np.zeros((10, 10), bool), tf, 2000)).all()


def test_partial_edge_cell_is_dropped():
    lc, tf = _raster()
    m = pixel_masks(lc, tf, F)
    full = _cell(tf, 160)                                    # ~16 km x 18 km of grass
    assert evaluate_cell(full, lc, tf, m, F, cell_km=15)["keep"]
    sliver = dict(full, east=full["west"] + 0.02)            # ~2 km wide
    row = evaluate_cell(sliver, lc, tf, m, F, cell_km=15)
    assert not row["keep"] and row["reason"].startswith("edge-cell")
