"""Mare lunar target inputs: cell picking (fixed seed, inside the mare) and SLDEM window reading."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fetch_sldem_window import MOON_LL, read_window, tile_name, to_metres  # noqa: E402
from mare_cells import local_crs, pick_cells  # noqa: E402


def test_tile_names_follow_the_archive():
    assert tile_name(8.3355, 33.222) == "SLDEM2015_512_00N_30N_000_045"       # Tranquillitatis pit
    assert tile_name(34.0, -15.0) == "SLDEM2015_512_30N_60N_315_360"           # Imbrium, 0-360 E
    assert tile_name(-5.0, 300.0) == "SLDEM2015_512_30S_00S_270_315"
    assert tile_name(-45.0, 10.0) == "SLDEM2015_512_60S_30S_000_045"
    with pytest.raises(ValueError):
        tile_name(70.0, 0.0)


def test_units_from_values():
    km = np.array([-2.1, -1.8, -2.5])
    assert to_metres(km)[0] == pytest.approx(km * 1000)
    m = np.array([-2100.0, -1800.0])
    assert to_metres(m)[0] == pytest.approx(m)
    with pytest.raises(ValueError):
        to_metres(np.array([50.0, 60.0]))


def _square_mare(lat0, lon0, half_deg):
    from shapely.geometry import box
    return box(lon0 - half_deg, lat0 - half_deg, lon0 + half_deg, lat0 + half_deg)


def test_cells_inside_with_margin_non_overlapping_and_reproducible():
    pytest.importorskip("geopandas")                         # not installed on every laptop
    pytest.importorskip("shapely")
    import geopandas as gpd
    from shapely.geometry import Point
    mare = _square_mare(10.0, 30.0, 4.0)                     # ~240 km half-width
    a = pick_cells(mare, cell_km=15, margin_km=10, n=15, seed=7)
    assert a == pick_cells(mare, cell_km=15, margin_km=10, n=15, seed=7) and len(a) == 15
    crs = local_crs(10.0, 30.0)
    g = gpd.GeoSeries([mare], crs=MOON_LL).to_crs(crs).iloc[0]
    pts = gpd.GeoSeries([Point(p) for p in a], crs=MOON_LL).to_crs(crs)
    half_diag = 7500 * np.sqrt(2)
    for p in pts:
        assert g.exterior.distance(p) >= half_diag + 10_000 - 50     # whole cell + margin inside (50 m: projection)
    d = [pts.iloc[i].distance(pts.iloc[j]) for i in range(15) for j in range(i)]
    assert min(d) >= 2 * half_diag - 50                        # no overlap
    assert pick_cells(mare, 15, 10, 15, seed=8) != a          # the seed matters


def test_mare_too_small_fails():
    pytest.importorskip("geopandas")                         # not installed on every laptop
    pytest.importorskip("shapely")
    with pytest.raises(ValueError):
        pick_cells(_square_mare(10.0, 30.0, 0.2), 15, 10, 1, seed=1)


def test_read_window_from_a_0_360_tile_in_km(tmp_path):
    import rasterio
    from rasterio.transform import from_origin
    ppd = 16                                                  # coarse stand-in for 512 ppd
    w, h = 45 * ppd, 30 * ppd
    p = tmp_path / "SLDEM2015_512_00N_30N_000_045.tif"
    with rasterio.open(p, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
                       crs=MOON_LL, transform=from_origin(0.0, 30.0, 1 / ppd, 1 / ppd)) as d:
        d.write(np.full((h, w), -2.0, np.float32), 1)        # km, like a mare
    out, otf, crs, note = read_window(str(p), lat=8.3355, lon=33.222, half_km=13)
    assert np.nanmean(out) == pytest.approx(-2000.0) and note.startswith("km")
    assert otf.c + out.shape[1] / 2 * otf.a == pytest.approx(33.222, abs=2 / ppd)
    with pytest.raises(ValueError):
        read_window(str(p), lat=8.0, lon=44.9, half_km=13)    # leaves the tile


def _write_window(path, lat, lon, crater=False, seed=0, half_km=13.0):
    """Synthetic SLDEM-like window (lon/lat, metres): gentle noise, optionally a 3 km / 300 m bowl."""
    import math
    import rasterio
    from rasterio.transform import from_origin
    ppd = 512
    dlat = math.degrees(half_km * 1000 / 1737400)
    dlon = dlat / math.cos(math.radians(lat))
    nx, ny = int(2 * dlon * ppd), int(2 * dlat * ppd)
    from scipy import ndimage
    rng = np.random.default_rng(seed)
    yy0, xx0 = np.indices((ny, nx))
    # gentle regional slope (0.5 m/km, so water leaves the window) + smooth 1-m bumps, like mare at 60 m
    z = -2000 + 0.5 * xx0 * 59.2 / 1000 + ndimage.gaussian_filter(rng.normal(0, 30, (ny, nx)), 8)
    if crater:
        yy, xx = np.indices(z.shape)
        r = np.hypot((yy - ny / 2) * 59.2, (xx - nx / 2) * 59.2 * math.cos(math.radians(lat)))
        z = z - 300 * np.clip(1 - (r / 1500) ** 2, 0, None)
    with rasterio.open(path, "w", driver="GTiff", height=ny, width=nx, count=1, dtype="float32", crs=MOON_LL,
                       transform=from_origin(lon - dlon, lat + dlat, 1 / ppd, 1 / ppd)) as d:
        d.write(z.astype("float32"), 1)


def test_evaluate_keeps_bowls_and_takes_first_n_in_order(tmp_path):
    from compute_mare_target import evaluate
    from pipeline.config import load_config
    from pipeline.mare import MARE_CRITERIA, target_from_cells
    cfg = load_config()
    cells = [{"id": "a_01", "mare": "A", "order": 1, "lat": 10.0, "lon": 30.0},
             {"id": "a_02", "mare": "A", "order": 2, "lat": 11.0, "lon": 30.0},
             {"id": "a_03", "mare": "A", "order": 3, "lat": 12.0, "lon": 30.0},
             {"id": "b_01", "mare": "B", "order": 1, "lat": 20.0, "lon": 50.0},
             {"id": "b_02", "mare": "B", "order": 2, "lat": 21.0, "lon": 50.0}]
    for i, c in enumerate(cells):
        _write_window(tmp_path / f"{c['id']}.tif", c["lat"], c["lon"], crater=c["id"] == "a_01", seed=i)
    spec = {"per_mare": 2, "seed": 1, "cells": cells,
            "named_site": {"apollo_11": {"lat": 0.67416, "lon": 23.47314}}}
    _write_window(tmp_path / "apollo_11.tif", 0.67416, 23.47314, seed=9)
    values, used, skipped, apollo = evaluate(spec, tmp_path, cfg)
    # no bowl exclusion (as on Earth): the first per_mare cells in order count; the bowl is recorded
    assert [c["id"] for c in used] == ["a_01", "a_02", "b_01", "b_02"] and not skipped
    assert [c["has_bowl"] for c in used] == [True, False, False, False]
    assert apollo and apollo["name"] == "apollo_11" and not apollo["has_bowl"]
    t = target_from_cells(values, cfg["mare"]["tolerance_floor"], [c["id"] for c in used], 1)
    for k in MARE_CRITERIA:
        assert t[k]["n_cells"] == 4 and t[k]["tolerance"] >= cfg["mare"]["tolerance_floor"][k]
    assert t["c12_drivable"]["value"] == pytest.approx(1.0)                  # gentle synthetic mare


def test_read_window_from_a_projected_mosaic_in_metres(tmp_path):
    """The USGS mosaic is equirectangular in METRES (not degrees): the window must be transformed."""
    import rasterio
    from rasterio.transform import from_origin
    eqc = "+proj=eqc +lat_ts=0 +lon_0=0 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"
    res = 59.2252938
    x0, y0 = 30.0 * np.pi / 180 * 1737400, 12.0 * np.pi / 180 * 1737400        # 30 E, 12 N corner
    w, h = 400, 400
    p = tmp_path / "mosaic.tif"
    with rasterio.open(p, "w", driver="GTiff", height=h, width=w, count=1, dtype="int16", crs=eqc,
                       transform=from_origin(x0, y0, res, res), nodata=-32768) as d:
        d.write(np.full((h, w), -2100, np.int16), 1)                           # metres
    lat_c = (y0 - h / 2 * res) / 1737400 * 180 / np.pi
    lon_c = (x0 + w / 2 * res) / 1737400 * 180 / np.pi
    out, otf, crs, note = read_window(str(p), lat=lat_c, lon=lon_c, half_km=5)
    assert out.shape[0] > 150 and out.shape[1] > 150                           # ~10 km / 59 m
    assert np.nanmean(out) == pytest.approx(-2100.0) and note.startswith("m as stored")
