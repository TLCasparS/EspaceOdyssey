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
from pipeline.light import (EARTH_OBLIQUITY_DEG, MOON_EQUATOR_TILT_DEG, earth_refraction_horizon_deg,  # noqa: E402
                            flat_lit_fraction, floor_zone, max_sun_elevation_deg, sky_view_factor,
                            true_north_in_grid_deg)
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


# --- step 2: Sun ---------------------------------------------------------------------------------

def test_flat_lit_fraction_is_half_without_refraction_on_earth_and_moon():
    for lat in (-89.6, -45, 0, 28.6, 75, 89.9):
        assert flat_lit_fraction(lat, EARTH_OBLIQUITY_DEG) == pytest.approx(0.5, abs=1e-3)
        assert flat_lit_fraction(lat, MOON_EQUATOR_TILT_DEG) == pytest.approx(0.5, abs=1e-3)


def test_flat_lit_fraction_with_refraction_matches_shadowsim_baseline():
    from shadowsim import flat_baseline, sun_position, year_times
    h = earth_refraction_horizon_deg()
    assert h == pytest.approx(-0.57, abs=0.02)
    t = year_times(2026, 60)
    for lat, tol in ((28.6, 0.005), (-35, 0.005), (75, 0.02)):     # bias = orbital eccentricity (documented)
        az, el = sun_position(lat, 0.0, t)
        sim = float(flat_baseline(az, el, 60).lit_fraction.ravel()[0])
        assert flat_lit_fraction(lat, EARTH_OBLIQUITY_DEG, h) == pytest.approx(sim, abs=tol)


def test_max_sun_elevation():
    assert max_sun_elevation_deg(28.6, EARTH_OBLIQUITY_DEG) == pytest.approx(90 - 28.6 + 23.439)
    assert max_sun_elevation_deg(10, EARTH_OBLIQUITY_DEG) == 90.0                 # tropics: zenith
    assert max_sun_elevation_deg(-90, MOON_EQUATOR_TILT_DEG) == pytest.approx(1.535)


def test_true_north_conversion_matches_terrain_module():
    from dem.terrain import _grid_north_azimuth
    tf = from_origin(250_000, 3_200_000, RES, RES)                      # UTM 45N, ~3 deg west of 87 E
    mg = MetricGrid(np.zeros((50, 50), np.float32), tf, "EPSG:32645", RES)
    x, y = tf * (25.5, 25.5)
    g = true_north_in_grid_deg("EPSG:32645", x, y)
    assert abs(g) > 1.0                                                 # real convergence here
    assert g == pytest.approx(float(_grid_north_azimuth(mg)[25, 25]), abs=0.05)


def _bowl_cfg(step=120):
    import copy
    c = copy.deepcopy(CFG)
    c["light"].update(sun=True, step_min=step, n_azimuths=36)
    return c


def test_sun_criteria_on_a_bowl_through_the_pipeline():
    x, y = _xy()
    R, D = 1500.0, 600.0
    z = np.where(np.hypot(x, y) < R, D * (np.hypot(x, y) ** 2 / R ** 2 - 1), 0.0)
    tf = from_origin(500_000 - N * RES / 2, 3_160_000, RES, RES)
    rr, cc = np.indices((N, N))
    cell = (np.abs(rr - N / 2) < 125) & (np.abs(cc - N / 2) < 125)
    r = evaluate_polar_cell(MetricGrid(z.astype(np.float32), tf, "EPSG:32645", RES), cell, None, 28.5, _bowl_cfg())
    assert r["c1_sunny_ridge"] == pytest.approx(1.0, abs=0.03)          # flat rim sees the full sky
    assert 0.05 < r["c2_dark_floor"] < 1.0                              # floor loses some sun to the walls
    assert r["c3_light_dark"] > 0
    assert r["c4_grazing_sun"] == pytest.approx(90 - 28.5 + 23.439, abs=0.1)
    assert r["max_dark_days"] == 0 and r["near_permanent_shadow_share"] == 0.0     # 28.5 N: no polar night
    assert 0.5 < r["flat_lit_fraction"] < 0.51


def test_deep_pit_at_high_latitude_has_near_permanent_shadow():
    x, y = _xy()
    R, D = 1500.0, 1500.0                                               # walls far above winter sun at 75 N
    z = np.where(np.hypot(x, y) < R, -D * (1 - (np.hypot(x, y) / R) ** 8), 0.0)   # steep walls, flat floor
    tf = from_origin(500_000 - N * RES / 2, 8_330_000, RES, RES)          # UTM 45N near 75 N
    rr, cc = np.indices((N, N))
    cell = (np.abs(rr - N / 2) < 125) & (np.abs(cc - N / 2) < 125)
    r = evaluate_polar_cell(MetricGrid(z.astype(np.float32), tf, "EPSG:32645", RES), cell, None, 75.0, _bowl_cfg())
    assert r["c2_dark_floor"] > 0.6
    assert r["near_permanent_shadow_share"] > 0
    assert r["max_dark_days"] > 100                                     # polar night + walls


def test_moon_body_leaves_sun_criteria_to_lunar_light():
    import copy
    from pipeline.polar import _Cell, find_depressions
    x, y = _xy()
    z = np.where(np.hypot(x, y) < 3000, 1000 * (np.hypot(x, y) ** 2 / 9e6 - 1), 0.0).astype(np.float32)
    mg = MetricGrid(z, from_origin(-N * RES / 2, N * RES / 2, RES, RES),
                    "+proj=stere +lat_0=-90 +lon_0=0 +R=1737400 +units=m +no_defs", RES)
    allpx = np.ones((N, N), bool)
    dep = find_depressions(mg.dem, allpx, RES, CFG["polar"])[0]
    place = _Cell(mg, allpx, allpx, -89.9, _bowl_cfg(), body="moon").place(dep["low"], dep)
    assert all(place[k] is None for k in ("c1_sunny_ridge", "c2_dark_floor", "c3_light_dark", "c4_grazing_sun"))
    assert place["c5_sky_view"] == pytest.approx(1 - math.sin(math.atan(1000 / 3000)), abs=0.03)


def test_shared_rim_zone_reaches_max_of_edge_plus_1km_and_1p3_r():
    from pipeline.light import rim_zone
    n = 501
    rr, cc = np.indices((n, n))
    d = np.hypot(rr - 250, cc - 250) * RES
    for r_bowl, expect_outer in ((600.0, 600 + 1000), (9000.0, 1.3 * 9000)):   # small: edge + 1 km; big: 1.3 r
        bowl = d <= r_bowl
        zone, to_bowl = rim_zone(bowl, (250, 250), r_bowl, RES, 1.0, 1.3)
        assert not (zone & bowl).any() and (to_bowl[bowl] == 0).all()
        assert d[zone].max() == pytest.approx(expect_outer, abs=RES * 1.5)
