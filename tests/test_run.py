"""Per-cell path of src/pipeline/run.py on a synthetic lon/lat DEM (offline)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
pytest.importorskip("rasterio")
from pyproj import Transformer  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402

from pipeline.cells import cell_area_km2, make_grid  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.run import evaluate_cell_terrain  # noqa: E402

CFG = load_config()


def test_cell_terrain_on_lonlat_bowl():
    """1 arcsec lon/lat DEM with a 1000 m deep, 3 km radius bowl in the middle of one 15 km cell."""
    lat0, lon0 = 28.6, 84.4
    cell = make_grid(lon0 - 0.0765, lat0 - 0.0678, lon0 + 0.0765, lat0 + 0.0678, 15)[0]
    res = 1 / 3600
    west, north = cell["west"] - 0.1, cell["north"] + 0.1
    n_r, n_c = int((cell["north"] - cell["south"] + 0.2) / res), int((cell["east"] - cell["west"] + 0.2) / res)
    tf = from_origin(west, north, res, res)
    cc, rr = np.meshgrid(np.arange(n_c) + 0.5, np.arange(n_r) + 0.5)
    lon, lat = tf * (cc, rr)
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32645", always_xy=True)
    x, y = to_utm.transform(lon, lat)
    xc, yc = to_utm.transform((cell["west"] + cell["east"]) / 2, (cell["south"] + cell["north"]) / 2)
    r = np.hypot(x - xc, y - yc)
    dem = (3000 + np.where(r < 3000, 1000 * (r ** 2 / 3000 ** 2 - 1), 0.0)).astype(np.float32)

    lc_tf = from_origin(west, north, 100 / 111_320, 100 / 111_320)
    usable = np.ones((int(0.4 * 1113.2), int(0.4 * 1113.2)), bool)
    t = evaluate_cell_terrain(cell, dem, tf, usable, lc_tf, CFG)

    assert t["keep"] and t["utm_crs"] == "EPSG:32645"
    assert t["c7_depth_m"] == pytest.approx(1000, abs=15)
    assert t["c7_bowl"] == pytest.approx(1 / 6, rel=0.05)
    assert t["low_lon"] == pytest.approx((cell["west"] + cell["east"]) / 2, abs=0.001)
    assert t["low_lat"] == pytest.approx((cell["south"] + cell["north"]) / 2, abs=0.001)
    assert t["low_elev_m"] == pytest.approx(2000, abs=15)
    assert t["c10_flat_base"] == pytest.approx(0, abs=0.05)
    assert cell["west"] <= t["base_lon"] <= cell["east"] and cell["south"] <= t["base_lat"] <= cell["north"]
    assert cell_area_km2(cell) == pytest.approx(225, rel=0.02)
