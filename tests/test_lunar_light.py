"""lunar_light: Moon side of the light criteria, on a synthetic bowl with known answers."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dem.grid import MetricGrid  # noqa: E402
from pipeline.light import MOON_EQUATOR_TILT_DEG, flat_lit_fraction, max_sun_elevation_deg  # noqa: E402
from pipeline.light import rim_zone  # noqa: E402
from pipeline.lunar_light import as_fraction, light_criteria, moon_light, read_on_grid  # noqa: E402

MOON_SPS = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"
RES, N, R_BOWL = 60.0, 201, 3000.0      # 12 km square, bowl radius 3 km
C = N // 2


@pytest.fixture
def scene():
    from rasterio.transform import from_origin
    mg = MetricGrid(np.zeros((N, N), np.float32), from_origin(-N * RES / 2, N * RES / 2, RES, RES), MOON_SPS, RES)
    rr, cc = np.indices((N, N))
    d = np.hypot(rr - C, cc - C) * RES
    bowl = d <= R_BOWL
    floor = d <= 1000
    rim, _ = rim_zone(bowl, (C, C), R_BOWL, RES, 1.0, 1.3)   # ring 0-1 km outside (1.3 r = edge + 0.9 km)
    lit = np.full((N, N), 0.5, np.float32)               # flat land everywhere ...
    lit[bowl] = 0.2                                       # ... shaded walls
    lit[floor] = 0.0                                      # ... dark floor
    sunny = (C, C + int(R_BOWL / RES) + 3)                # one bright rim pixel, due east
    lit[sunny] = 0.9
    return mg, lit, bowl, floor, rim, sunny


def test_rim_zone_is_outside_the_bowl_within_the_distance(scene):
    mg, lit, bowl, floor, rim, _ = scene
    assert not (rim & bowl).any()
    rr, cc = np.nonzero(rim)
    d = np.hypot(rr - C, cc - C) * RES
    assert d.min() > R_BOWL and d.max() <= R_BOWL + 1000 + RES


def test_criteria_known_values(scene):
    mg, lit, bowl, floor, rim, sunny = scene
    out = light_criteria(lit, floor, rim, flat_lit=0.5, r_m=R_BOWL, res_m=RES, psr=floor.astype(float))
    assert out["c1_sunny_ridge"] == pytest.approx(0.9 / 0.5)
    assert out["c2_dark_floor"] == pytest.approx(1.0)
    assert out["near_permanent_shadow_share"] == pytest.approx(1.0)
    assert out["near_permanent_vs_lpsr_iou"] == pytest.approx(1.0)
    # closest darkest floor pixel to the sunny pixel: the floor edge (1 km) on the same row
    expected_m = (sunny[1] - C) * RES - 1000
    assert out["light_dark_distance_m"] == pytest.approx(expected_m, abs=RES)
    assert out["c3_light_dark"] == pytest.approx(expected_m / R_BOWL, abs=RES / R_BOWL)
    assert tuple(out["sunniest_rim_px"]) == sunny


def test_c2_not_clipped_like_earth(scene):
    """A floor lit longer than flat land gives negative shadow; Earth does not clip, nor do we."""
    mg, lit, bowl, floor, rim, _ = scene
    lit = lit.copy()
    lit[floor] = 0.6
    out = light_criteria(lit, floor, rim, flat_lit=0.5, r_m=R_BOWL, res_m=RES)
    assert out["c2_dark_floor"] == pytest.approx(1 - 0.6 / 0.5)


def test_missing_zone_gives_none_not_zero(scene):
    mg, lit, bowl, floor, rim, _ = scene
    lit = lit.copy()
    lit[floor] = np.nan
    out = light_criteria(lit, floor, rim, flat_lit=0.5, r_m=R_BOWL, res_m=RES)
    assert out["c2_dark_floor"] is None and out["c1_sunny_ridge"] is None and "floor" in out["reason"]


def test_moon_light_uses_the_shared_functions(scene):
    mg, lit, bowl, floor, rim, _ = scene
    cfg = {"light": {"floor_max_slope_deg": 10, "near_permanent_shadow": 0.9},
           "polar": {"max_base_to_bowl_km": 1.0, "rim_zone_rel": 1.3}}
    slope = np.where(np.hypot(*(np.indices((N, N)) - C)) * RES <= 1000, 2.0, 25.0)   # flat floor, steep walls
    dep = {"mask": bowl, "width_m": 2 * R_BOWL}
    out = moon_light(mg, dep, (C, C), slope, -89.624, cfg, lit)
    flat = flat_lit_fraction(-89.624, MOON_EQUATOR_TILT_DEG)
    assert flat == pytest.approx(0.5, abs=1e-3)
    assert out["flat_lit_fraction"] == pytest.approx(flat, abs=1e-4)
    assert out["c4_grazing_sun"] == pytest.approx(max_sun_elevation_deg(-89.624, MOON_EQUATOR_TILT_DEG))
    assert out["floor_px"] == int(floor.sum())
    assert out["c1_sunny_ridge"] == pytest.approx(0.9 / flat)


def test_scale_check():
    assert as_fraction(np.array([0.0, 0.7])).max() == pytest.approx(0.7)
    with pytest.raises(ValueError):
        as_fraction(np.array([0.0, 22111.0]))


def test_read_on_grid_applies_the_files_scale(tmp_path, scene):
    """PGDA stores int16 + scale (AVGVISIB x 4e-5): the reader must return 0-1."""
    import rasterio
    from rasterio.transform import from_origin
    mg = scene[0]
    n = N + 10
    p = tmp_path / "avgvisib.tif"
    with rasterio.open(p, "w", driver="GTiff", height=n, width=n, count=1, dtype="int16", nodata=-32768,
                       crs=MOON_SPS, transform=from_origin(-n * 30.0, n * 30.0, 60.0, 60.0)) as dst:
        dst.write(np.full((n, n), 22111, np.int16), 1)
        dst.scales, dst.offsets = (4e-5,), (0.0,)
    out = read_on_grid(str(p), mg)
    assert out.shape == mg.dem.shape and np.nanmax(out) == pytest.approx(22111 * 4e-5, rel=1e-4)
