import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from shadowsim import (flat_baseline, horizon_angles, run_site, simulate_year,  # noqa: E402
                       sun_position, synthetic_crater, year_times)


def test_sun_noon_elevation_barcelona():
    lat = 41.39
    for date, decl in [("2026-06-21", 23.44), ("2026-12-21", -23.44)]:
        t = np.arange(np.datetime64(f"{date}T00:00"), np.datetime64(f"{date}T23:59"),
                      np.timedelta64(1, "m")).astype("datetime64[s]")
        _, el = sun_position(lat, 2.17, t, refraction=False)
        assert abs(el.max() - (90 - lat + decl)) < 0.1


def test_sun_matches_pvlib():
    pvlib = pytest.importorskip("pvlib")
    import pandas as pd
    t = year_times(2026, 180)
    for lat, lon in [(59.88, 8.59), (75.38, -89.67), (28.63, 83.61)]:
        az, el = sun_position(lat, lon, t, refraction=False)
        ref = pvlib.solarposition.get_solarposition(pd.DatetimeIndex(t, tz="UTC"), lat, lon)
        assert np.abs(el - ref["elevation"].values).max() < 0.05
        up = el > 5
        daz = (az[up] - ref["azimuth"].values[up] + 180) % 360 - 180
        assert np.abs(daz).max() < 0.1


def test_flat_terrain_equals_baseline():
    z = np.zeros((101, 101), np.float32)
    az, hz = horizon_angles(z, (40, 61, 40, 61), 100, 100, n_azimuths=36, max_dist_m=4000)
    t = year_times(2026, 60)
    sa, se = sun_position(60.0, 0.0, t)
    res = simulate_year(hz, az, sa, se, 60)
    base = flat_baseline(sa, se, 60)
    # Earth curvature makes the flat horizon slightly negative -> a tiny bit more light
    assert np.allclose(res.lit_fraction, base.lit_fraction, atol=0.01)
    assert res.terrain_shadow_fraction.max() < 0.01


def test_polar_night_length():
    # at 75 N the Sun's centre stays below the horizon for roughly 3 months
    t = year_times(2026, 60)
    sa, se = sun_position(75.0, 0.0, t)
    base = flat_baseline(sa, se, 60)
    assert 85 <= int(base.max_dark_days.ravel()[0]) <= 105


def test_synthetic_crater_dark_floor_lit_rim():
    grid = synthetic_crater(lat=75.0, pixel_m=250, extent_km=60, radius_km=12)
    res, base, summary = run_site(grid, step_minutes=120, n_azimuths=36, horizon_km=20)
    n = res.lit_fraction.shape[0]
    c = n // 2
    floor_lit = res.lit_fraction[c, c]
    rim_lit = res.lit_fraction[c - int(10_000 / 250), c]  # north rim, faces the Sun
    # Earth's 23.4 deg tilt lets summer Sun reach even a deep crater floor at 75 N,
    # so we expect a clear contrast, not lunar-style permanent darkness.
    assert floor_lit < 0.7 * rim_lit
    assert res.terrain_shadow_fraction[c, c] > 0.3
    assert res.max_dark_days[c, c] > base.max_dark_days.ravel()[0] + 30  # terrain lengthens polar night
    assert abs(rim_lit - base.lit_fraction.ravel()[0]) < 0.02          # rim ~ as sunny as flat land
    assert summary["near_permanent_shadow_km2"] == 0                    # no true PSR on Earth
    assert summary["analog_score"] > 0.5
