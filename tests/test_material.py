"""GLiM rock classes (src/pipeline/material.py) on a small synthetic polygon set."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
gpd = pytest.importorskip("geopandas")
from shapely.geometry import box  # noqa: E402

from pipeline.material import (CODES, FrameSource, GridSource, PolygonFileSource,  # noqa: E402
                               classify_point, classify_points, disc_bbox, first_level)

# Two half-planes split at lon 10.0: basalt (vb) west, carbonate (sc) east; nothing north of lat 1.0 (sea)
POLYS = gpd.GeoDataFrame({"xx": ["vb", "sc", "VBpy"]},
                         geometry=[box(9.0, -1.0, 10.0, 1.0), box(10.0, -1.0, 11.0, 1.0),
                                   box(9.0, -3.0, 11.0, -2.0)], crs=4326)
SRC = FrameSource(POLYS)
KM_LON = 111.32  # at the equator, km per degree


def test_first_level_codes():
    assert first_level("vb") == "vb"
    assert first_level("VBpy") == "vb"
    assert first_level("xx") is None
    assert first_level(None) is None
    assert first_level(float("nan")) is None


def test_point_inside_one_class():
    r = classify_point(9.5, 0.0, SRC, radius_km=5)
    assert r["rock_class"] == "vb"
    assert r["share_vb"] == pytest.approx(1.0)
    assert r["share_sc"] == pytest.approx(0.0)
    assert r["covered_share"] == pytest.approx(1.0, abs=1e-3)


def test_point_on_boundary_splits_half_half():
    r = classify_point(10.0, 0.0, SRC, radius_km=5)
    assert r["share_vb"] == pytest.approx(0.5, abs=0.01)
    assert r["share_sc"] == pytest.approx(0.5, abs=0.01)
    assert r["rock_class"] in ("vb", "sc")


def test_share_matches_circular_segment():
    # point 2.5 km east of the boundary: the vb part is a circular segment at distance d = 2.5 km
    d, R = 2.5, 5.0
    lon = 10.0 + d / KM_LON
    seg = R * R * math.acos(d / R) - d * math.sqrt(R * R - d * d)
    r = classify_point(lon, 0.0, SRC, radius_km=R)
    assert r["share_vb"] == pytest.approx(seg / (math.pi * R * R), abs=0.01)
    assert r["rock_class"] == "sc"


def test_sea_is_left_out_not_zero():
    # disc centred on the coast at lat 1.0: half covered, shares relative to the covered half
    r = classify_point(9.5, 1.0, SRC, radius_km=5)
    assert r["covered_share"] == pytest.approx(0.5, abs=0.01)
    assert r["share_vb"] == pytest.approx(1.0)


def test_open_sea_is_no_data():
    r = classify_point(9.5, 5.0, SRC, radius_km=5)
    assert r["rock_class"] is None
    assert r["covered_share"] == 0.0
    assert all(r[f"share_{c}"] is None for c in CODES)


def test_three_level_code_counts_as_first_level():
    r = classify_point(10.0, -2.5, SRC, radius_km=5)
    assert r["rock_class"] == "vb"
    assert r["share_vb"] == pytest.approx(1.0)


def test_high_latitude_disc_is_still_a_circle():
    hi = gpd.GeoDataFrame({"xx": ["ig", "mt"]}, geometry=[box(0, 79, 20, 81), box(20, 79, 40, 81)], crs=4326)
    r = classify_point(20.0, 80.0, FrameSource(hi), radius_km=5)
    assert r["share_ig"] == pytest.approx(0.5, abs=0.01)
    w, s, e, n = disc_bbox(20.0, 80.0, 5)
    assert (e - w) > 4 * (n - s)       # box much wider in lon than in lat at 80 deg


def test_nan_point_gives_no_data():
    rows = classify_points([9.5, float("nan")], [0.0, 0.0], SRC)
    assert rows[0]["rock_class"] == "vb"
    assert rows[1]["rock_class"] is None and rows[1]["share_vb"] is None


def test_polygon_file_source_projected_layer(tmp_path):
    # file in an equal-area projection (as GLiM is distributed): bbox read must still find the polygons
    path = tmp_path / "glim_test.gpkg"
    POLYS.to_crs("ESRI:54012").to_file(path, layer="glim")
    src = PolygonFileSource(path, layer="glim", class_field="xx", tile_deg=2.0)
    r = classify_point(10.0, 0.0, src, radius_km=5)
    assert r["share_vb"] == pytest.approx(0.5, abs=0.02)
    assert r["share_sc"] == pytest.approx(0.5, abs=0.02)
    assert classify_point(9.5, 5.0, src)["rock_class"] is None


def test_grid_source(tmp_path):
    # 4 x 2 grid of 1-deg cells from lon 8, lat -1; row 0 is the north row; -9999 = sea
    asc = tmp_path / "g.asc"
    asc.write_text("ncols 4\nnrows 2\nxllcorner 8\nyllcorner -1\ncellsize 1\nNODATA_value -9999\n"
                   "-9999 2 6 6\n-9999 2 6 6\n")
    (tmp_path / "Classnames.txt").write_text('"OBJECTID";"Value_";"Count_";"xx"\n'
                                              '1;2;1.0;"vb"\n2;6;1.0;"sc"\n')
    src = GridSource(asc)
    r = classify_point(10.0, 0.0, src, radius_km=5)      # on the vb|sc cell border
    assert r["share_vb"] == pytest.approx(0.5, abs=0.01)
    assert classify_point(9.5, 0.5, src)["rock_class"] == "vb"
    r = classify_point(9.0, 0.5, src, radius_km=5)       # sea|vb border: sea left out
    assert r["covered_share"] == pytest.approx(0.5, abs=0.01)
    assert r["share_vb"] == pytest.approx(1.0)


def test_glim_nd_class_is_no_data():
    nd = gpd.GeoDataFrame({"xx": ["nd", "vb"]}, geometry=[box(9, -1, 10, 1), box(10, -1, 11, 1)], crs=4326)
    r = classify_point(10.0, 0.0, FrameSource(nd), radius_km=5)
    assert r["covered_share"] == pytest.approx(0.5, abs=0.01)
    assert r["share_vb"] == pytest.approx(1.0)
    assert "share_nd" not in r
    assert classify_point(9.5, 0.0, FrameSource(nd))["rock_class"] is None
