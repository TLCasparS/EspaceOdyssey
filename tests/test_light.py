"""Light criteria (src/pipeline/light.py) and the body-aware horizon (src/shadowsim/horizon.py)."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

from dem.grid import MetricGrid  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.light import floor_zone, sky_view_factor  # noqa: E402
from pipeline.polar import evaluate_polar_cell  # noqa: E402
from shadowsim.horizon import EARTH_RADIUS_M, MOON_RADIUS_M, horizon_angles  # noqa: E402

CFG = load_config()
EARTH = CFG["light"]["bodies"]["earth"]
MOON = CFG["light"]["bodies"]["moon"]
RES, N = 60.0, 400


def _xy(n=N):
    rr, cc = np.indices((n, n))
    return (cc - n / 2 + 0.5) * RES, -(rr - n / 2 + 0.5) * RES


def test_flat_plain_sees_the_whole_sky():
    z = np.zeros((101, 101))
    zone = np.zeros_like(z, bool)
    zone[45:56, 45:56] = True
    svf = sky_view_factor(z, zone, RES, 3000, EARTH)
    assert np.nanmin(svf[zone]) == pytest.approx(1.0, abs=1e-6)        # curvature only lowers far terrain


def test_cylindrical_pit_centre_matches_formula():
    x, y = _xy(201)
    R, D = 1200.0, 500.0
    z = np.where(np.hypot(x, y) < R, -D, 0.0)                           # vertical walls, flat floor
    zone = np.zeros_like(z, bool)
    zone[100, 100] = True
    svf = sky_view_factor(z, zone, RES, 3000, EARTH, n_azimuths=72)
    expect = 1 - math.sin(math.atan(D / R))                             # horizon atan(D/R) all round
    assert svf[100, 100] == pytest.approx(expect, abs=0.03)


def test_moon_curvature_lowers_distant_horizon_more_than_earth():
    z = np.zeros((1, 400))
    z[0, 350:] = 200.0                                                   # 200 m step ~15 km east
    kw = dict(n_azimuths=4, max_dist_m=21000)
    _, h_e = horizon_angles(z, (0, 1, 100, 101), RES, RES, radius_m=EARTH_RADIUS_M, refraction_k=0.13, **kw)
    _, h_m = horizon_angles(z, (0, 1, 100, 101), RES, RES, radius_m=MOON_RADIUS_M, refraction_k=0.0, **kw)
    east = 1                                                             # sectors 0, 90, 180, 270 deg
    d = 250 * RES
    exp_e = math.degrees(math.atan((200 - d ** 2 * 0.87 / (2 * EARTH_RADIUS_M)) / d))
    exp_m = math.degrees(math.atan((200 - d ** 2 / (2 * MOON_RADIUS_M)) / d))
    assert h_e[east, 0, 0] == pytest.approx(exp_e, abs=0.05)
    assert h_m[east, 0, 0] == pytest.approx(exp_m, abs=0.05)
    assert h_m[east, 0, 0] < h_e[east, 0, 0]


def test_floor_zone_is_flat_part_connected_to_low_point():
    x, y = _xy()
    r = np.hypot(x, y)
    mask = r < 3000
    slope = np.where(r < 800, 2.0, 25.0)
    slope[(r > 2000) & (r < 2200)] = 2.0                                 # a flat terrace, not connected
    zone = floor_zone(mask, slope, (200, 200), 10)
    assert zone[200, 200] and not zone[200, 200 + 35]                    # terrace at 2.1 km excluded
    assert zone.sum() == pytest.approx(math.pi * 800 ** 2 / RES ** 2, rel=0.1)


def test_c5_on_paraboloid_bowl_through_the_pipeline():
    x, y = _xy()
    R, D = 3000.0, 1000.0
    z = np.where(np.hypot(x, y) < R, D * (np.hypot(x, y) ** 2 / R ** 2 - 1), 0.0)
    tf = from_origin(500_000 - N * RES / 2, 3_160_000, RES, RES)
    rr, cc = np.indices((N, N))
    cell = (np.abs(rr - N / 2) < 125) & (np.abs(cc - N / 2) < 125)
    r = evaluate_polar_cell(MetricGrid(z.astype(np.float32), tf, "EPSG:32645", RES), cell, None, 28.5, CFG)
    # from the centre the rim (plain level) is the highest point on every ray: horizon atan(D/R)
    assert r["c5_svf_low_point"] == pytest.approx(1 - math.sin(math.atan(D / R)), abs=0.03)
    assert r["c5_sky_view"] == pytest.approx(r["c5_svf_low_point"], abs=0.03)  # floor ~ flat centre
    assert r["c5_horizon_km"] == pytest.approx(2 * R / 1000, rel=0.05)
