"""Common 60 m grid (src/dem/grid.py): a plane of known slope must keep that slope."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
pytest.importorskip("rasterio")
from pyproj import Transformer  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402

from dem.grid import metric_crs_for, reproject_dem  # noqa: E402
from dem.terrain import compute_terrain  # noqa: E402

RISE = 0.1                                   # 10 % grade
SLOPE = math.degrees(math.atan(RISE))        # 5.7106 deg
MOON_SPS = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"
MOON_LL = "+proj=longlat +R=1737400 +no_defs"


def _earth_plane(lat0, lon0, dlon_px, axis="x", n=540):
    """lon/lat DEM (1 arcsec rows, dlon_px arcsec columns) of a plane rising RISE m/m along
    UTM x (east) or y (north). Heights are exact in the UTM zone the grid will be put on."""
    res = 1 / 3600
    west, north = lon0 - n * dlon_px * res / 2, lat0 + n * res / 2
    tf = from_origin(west, north, dlon_px * res, res)
    cols, rows = np.meshgrid(np.arange(n) + 0.5, np.arange(n) + 0.5)
    lon, lat = tf * (cols, rows)
    x, y = Transformer.from_crs("EPSG:4326", metric_crs_for(lon0, lat0), always_xy=True).transform(lon, lat)
    v = x if axis == "x" else y
    return (RISE * (v - v.mean())).astype(np.float32), tf


def _interior(mg, px=3):
    from scipy import ndimage
    return ndimage.binary_erosion(np.isfinite(mg.dem), np.ones((2 * px + 1,) * 2), border_value=0)


@pytest.mark.parametrize("lat0,lon0,dlon_px", [(28.5, 84.5, 1), (75.4, -89.6, 2)])
@pytest.mark.parametrize("axis", ["x", "y"])
def test_earth_plane_keeps_slope_on_60m_utm_grid(lat0, lon0, dlon_px, axis):
    z, tf = _earth_plane(lat0, lon0, dlon_px, axis)
    mg = reproject_dem(z, tf, "EPSG:4326", res_m=60)
    assert mg.crs == metric_crs_for(lon0, lat0)
    assert mg.transform.a == pytest.approx(60) and -mg.transform.e == pytest.approx(60)
    t = compute_terrain(mg, relief_window_m=600)
    assert np.nanmedian(t.slope_deg) == pytest.approx(SLOPE, abs=0.05)   # measured bias <= 0.022 deg, cause not identified
    # >= 3 px from no-data and from the array border: every pixel within 0.15 deg.
    # (The outer 1-2 px of the reprojected footprint can be off by ~1 deg; the pipeline
    # reads every cell with a >= 2.5 km buffer, so cells never touch that edge.)
    assert np.abs(t.slope_deg - SLOPE)[_interior(mg)].max() < 0.15


def test_utm_zone_choice():
    assert metric_crs_for(84.5, 28.5) == "EPSG:32645"
    assert metric_crs_for(83.5, 28.5) == "EPSG:32644"
    assert metric_crs_for(-89.6, 75.4) == "EPSG:32616"


def test_lunar_5m_plane_resampled_to_60m_keeps_slope():
    """LOLA-like: already polar stereographic metres at 5 m -> stays in that CRS, 60 m pixels."""
    n, px = 1200, 5.0                                       # 6 km x 6 km, ~90 km from the south pole
    tf = from_origin(0.0, 90_000.0, px, px)
    x = (np.arange(n) + 0.5) * px
    z = np.tile(RISE * x, (n, 1)).astype(np.float32)
    mg = reproject_dem(z, tf, MOON_SPS, res_m=60)
    assert mg.crs == MOON_SPS and mg.transform.a == pytest.approx(60)
    assert mg.dem.shape == (100, 100)
    t = compute_terrain(mg, relief_window_m=600)
    assert np.nanmedian(t.slope_deg) == pytest.approx(SLOPE, abs=0.05)   # measured bias <= 0.022 deg, cause not identified
    assert np.abs(t.slope_deg - SLOPE)[_interior(mg)].max() < 0.15
    assert np.isfinite(t.aspect_deg).mean() > 0.9           # aspect works with the lunar CRS too


def test_lunar_lonlat_needs_explicit_target_crs():
    z = np.zeros((10, 10), np.float32)
    tf = from_origin(0, -85, 0.01, 0.01)
    with pytest.raises(ValueError, match="dst_crs"):
        reproject_dem(z, tf, MOON_LL)
    mg = reproject_dem(z, tf, MOON_LL, dst_crs=MOON_SPS, res_m=60)
    assert mg.crs == MOON_SPS


def test_missing_data_stays_nan_never_zero():
    z, tf = _earth_plane(28.5, 84.5, 1)
    z = z + 3000.0
    z[200:340, 200:340] = np.nan                           # hole in the middle
    mg = reproject_dem(z, tf, "EPSG:4326", res_m=60)
    r, c = (s // 2 for s in mg.dem.shape)
    assert np.isnan(mg.dem[r, c])
    assert np.nanmin(mg.dem) > 2000                        # nothing was filled with 0
    assert np.isnan(compute_terrain(mg, relief_window_m=600).slope_deg[r, c])
