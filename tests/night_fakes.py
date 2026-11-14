"""Synthetic S3 readers for the night-run tests (also installed in spawned worker processes via
NIGHT_RUN_TEST_HOOK=<this file>:install). Plain at 1000 m with one bowl (r 3 km, 400 m deep) at 35.5 N 111.5 W."""
import math
import sys
from pathlib import Path

import numpy as np
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
LAT_C, LON_C = 35.5, -111.5


def z_at(lon, lat):
    dx = (lon - LON_C) * 111_320 * math.cos(math.radians(LAT_C))
    dy = (lat - LAT_C) * 110_574
    r = np.hypot(dx, dy)
    return np.where(r < 3000, 400 * (r ** 2 / 3000 ** 2 - 1), 0.0) + 1000.0


def fake_read_bbox(west, south, east, north, res=30):
    d = res / 111_320
    w, h = int(math.ceil((east - west) / d)), int(math.ceil((north - south) / d))
    tf = from_origin(west, north, d, d)
    cc, rr = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    lon, lat = tf * (cc, rr)
    return z_at(lon, lat).astype(np.float32), {"transform": tf, "crs": "EPSG:4326"}


def fake_read_glo90(west, south, east, north, cache):
    return fake_read_bbox(west, south, east, north, res=90)


def fake_read_landcover(west, south, east, north, res_m=100.0):
    d = res_m / 111_320
    w, h = max(1, round((east - west) / d)), max(1, round((north - south) / d))
    return np.full((h, w), 60, np.uint8), from_origin(west, north, (east - west) / w, (north - south) / h)


def fast_config(cfg):
    cfg["light"].update(step_min=360, n_azimuths=36)                 # fast Sun simulation
    return cfg


def install():
    """Patch the readers (and a fast light setting) in the CURRENT process (worker initializer hook)."""
    import dem.glo90_cache
    import night_run
    night_run.read_bbox = fake_read_bbox
    night_run.read_landcover = fake_read_landcover
    dem.glo90_cache.read_glo90 = fake_read_glo90
    orig = night_run.load_config
    night_run.load_config = lambda *a, **k: fast_config(orig(*a, **k))
