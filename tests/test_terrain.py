"""Offline checks for src/dem, src/fetch_region.py, src/terrain.py shim, src/pipeline/cells.py (synthetic data only)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dem import local_relief, roughness, slope_deg, summarize, tiles_for_bbox, tri  # noqa: E402
from fetch_region import Region, _urls_aws, bbox_around  # noqa: E402
from terrain import compute_terrain, to_metric_grid  # noqa: E402

pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402


def _plane_region(lat0=75.383, lon0=-89.667, rise=0.1, n=600):
    """lon/lat DEM of a plane rising `rise` (m/m) towards the east."""
    res = 1 / 3600
    west, north = lon0 - 0.5, lat0 + 0.08
    tf = from_origin(west, north, 2 * res, res)
    cols = np.arange(n)[None, :].repeat(n, 0)
    lon = west + (cols + 0.5) * 2 * res
    z = ((lon - lon0) * 111320 * np.cos(np.radians(lat0)) * rise).astype(np.float32)
    bbox = (west, north - n * res, west + n * 2 * res, north)
    return Region(bbox, z, tf, np.full((n, n), 60, np.uint8), tf)


def test_metric_plane_slope_and_true_north_aspect():
    t = compute_terrain(to_metric_grid(_plane_region()), relief_window_m=900)
    assert np.nanmedian(t.slope_deg) == pytest.approx(np.degrees(np.arctan(0.1)), abs=0.1)
    # rises to the east -> faces true west, even though UTM grid north is ~2.6 deg off here
    assert np.nanmedian(t.aspect_deg) == pytest.approx(270, abs=0.5)
    assert np.isnan(t.relief_m[0, 0])            # truncated window at the edge -> NaN
    assert np.nanmedian(t.tri_m) > 0


def test_dem_package_metrics_on_known_surfaces():
    flat = np.full((50, 50), 100.0, np.float32)
    assert np.nanmax(slope_deg(flat, 30, 30)) == pytest.approx(0, abs=1e-9)
    assert np.nanmax(roughness(flat)) == pytest.approx(0, abs=1e-6) and np.nanmax(tri(flat)) == 0
    ramp = np.tile(np.arange(50, dtype=np.float32) * 3, (50, 1))   # 3 m per 30 m pixel
    assert np.nanmedian(slope_deg(ramp, 30, 30)) == pytest.approx(np.degrees(np.arctan(0.1)), abs=1e-3)
    assert local_relief(ramp, 11)[25, 25] == pytest.approx(30)      # 10 pixels x 3 m
    summary, layers = summarize(ramp, 30, 30)
    assert set(layers) == {"elevation", "slope_deg", "roughness_m", "relief_m", "tri_m"}


def test_tile_names_shared_by_both_fetchers():
    bbox = bbox_around(75.383, -89.667, 18.5)
    dem_urls, wc_urls = _urls_aws(bbox)
    assert dem_urls == tiles_for_bbox(*bbox)
    # +-18.5 km at 75.4 N spans -90.7..-88.6 deg, i.e. the W091 and W090 tiles
    assert [u.rsplit("/", 1)[-1] for u in dem_urls] == [
        "Copernicus_DSM_COG_10_N75_00_W091_00_DEM.tif", "Copernicus_DSM_COG_10_N75_00_W090_00_DEM.tif"]
    # WorldCover tiles are 3 deg wide: W093 covers -93..-90, W090 covers -90..-87
    assert [u.rsplit("/", 1)[-1] for u in wc_urls] == [
        "ESA_WorldCover_10m_2021_v200_N75W093_Map.tif", "ESA_WorldCover_10m_2021_v200_N75W090_Map.tif"]
    assert _urls_aws(bbox, 90)[0][0].startswith("s3://copernicus-dem-90m/")


def test_worldcover_tile_names():
    from dem import worldcover_url
    assert worldcover_url(28.9, 83.8).endswith("ESA_WorldCover_10m_2021_v200_N27E081_Map.tif")
    assert worldcover_url(75.4, -89.7).endswith("ESA_WorldCover_10m_2021_v200_N75W090_Map.tif")
    assert worldcover_url(-0.5, -0.5).endswith("ESA_WorldCover_10m_2021_v200_S03W003_Map.tif")


def test_filter_cells_grid_covers_bbox_without_gaps():
    from pipeline import cells as fc
    cells = fc.make_grid(82, 27, 86, 31, 15)
    total = sum(fc.cell_area_km2(c) for c in cells)
    bbox_area = fc.cell_area_km2({"west": 82, "south": 27, "east": 86, "north": 31})
    assert total == pytest.approx(bbox_area, rel=0.01)
    full = [c for c in cells if c["north"] < 31 and c["east"] < 86]
    assert all(fc.cell_area_km2(c) == pytest.approx(225, rel=0.01) for c in full)


def test_filter_cells_window_picks_right_pixels():
    from pipeline import cells as fc
    tf = from_origin(10, 20, 0.1, 0.1)              # 0.1 deg pixels, NW corner at (10E, 20N)
    rs, cs = fc.window_of({"west": 10.2, "south": 19.5, "east": 10.5, "north": 19.8}, tf, (100, 100))
    assert (rs.start, rs.stop, cs.start, cs.stop) == (2, 5, 2, 5)
