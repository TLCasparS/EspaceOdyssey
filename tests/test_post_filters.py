"""config-v1.1 post-run filters (src/post_filters.py) and their use in src/export_app.py, offline, synthetic data."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from post_filters import PostFilters, dry_bowl_fails, load  # noqa: E402

DRY = {"bare_min": 0.3, "ice_floor_max": 0.2, "ice_rim_max": 0.2}


def test_config_v1_1_values():
    c = load(ROOT / "config" / "post_filters.yaml")
    assert c["version"] == "config-v1.1" and c["based_on"] == "config-v1" and c["base_types"] == ["polar"]
    assert c["dry_bowl"]["bare_min"] == 0.3 and c["dry_bowl"]["ice_floor_max"] == 0.2 and c["dry_bowl"]["ice_rim_max"] == 0.2
    assert c["mine"]["reason"] == "excluded: mine"


def test_dry_bowl_rules():
    assert dry_bowl_fails({"bare_share": 0.9, "ice_floor_share": 0.0, "ice_rim_share": 0.1}, DRY) == []
    assert dry_bowl_fails({"bare_share": 0.3, "ice_floor_share": 0.2, "ice_rim_share": 0.2}, DRY) == []   # limits pass
    assert len(dry_bowl_fails({"bare_share": 0.16, "ice_floor_share": 0.3, "ice_rim_share": 0.41}, DRY)) == 3
    assert dry_bowl_fails({"bare_share": 0.9, "ice_rim_share": "0.25"}, DRY) == ["ICE_RIM_SHARE 0.25 > 0.2"]
    assert dry_bowl_fails({"bare_share": None, "ice_floor_share": "", "ice_rim_share": float("nan")}, DRY) == []  # no data


@pytest.fixture
def mines(tmp_path):
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box
    p = tmp_path / "mines.gpkg"
    gpd.GeoDataFrame({"ISO3_CODE": ["USA"], "COUNTRY_NAME": ["Testland"], "AREA": [4.9]},
                     geometry=[box(-111.01, 34.99, -110.99, 35.01)], crs="EPSG:4326").to_file(p, layer="mining_polygons")
    return p


def _cfg(tmp_path, mines_path):
    cfg = tmp_path / "post.yaml"
    cfg.write_text(f"""version: config-v1.1
based_on: config-v1
base_types: [polar]
mine: {{path: "{mines_path.as_posix()}", reason: "excluded: mine", near_km: 1.0}}
dry_bowl: {{bare_min: 0.3, ice_floor_max: 0.2, ice_rim_max: 0.2, reason: "excluded: not a dry bowl (vegetation/ice/water)"}}
""")
    return cfg


def test_mine_mask_and_evaluate(tmp_path, mines):
    pf = PostFilters.from_file(_cfg(tmp_path, mines))
    assert pf.mines_missing is None
    inside = pf.evaluate("polar", 35.0, -111.0, {"bare_share": 0.9})
    assert inside["reasons"] == ["excluded: mine"] and inside["mine_dist_km"] == 0.0
    near = pf.evaluate("polar", 35.0, -110.98, {"bare_share": 0.9})          # ~0.9 km east of the polygon edge
    assert near["reasons"] == [] and 0.8 < near["mine_dist_km"] < 1.0
    both = pf.evaluate("polar", 35.0, -111.0, {"bare_share": 0.1})
    assert both["reasons"] == ["excluded: mine", "excluded: not a dry bowl (vegetation/ice/water)"]
    assert pf.evaluate("mare", 35.0, -111.0, {"bare_share": 0.1})["reasons"] == []   # Polar only


def test_missing_mine_file_is_reported(tmp_path):
    pf = PostFilters.from_file(_cfg(tmp_path, tmp_path / "nope.gpkg"))
    assert pf.mines is None and "not found" in pf.mines_missing
    assert pf.evaluate("polar", 35.0, -111.0, {"bare_share": 0.1})["reasons"] == ["excluded: not a dry bowl (vegetation/ice/water)"]


AXES = [{"id": "c7_bowl", "label": "7 Bowl shape", "method": "target", "weight": 1.0, "target": 0.197,
         "tolerance": 0.05, "in_total": True}]
COLS = ["id", "score", "lat", "lon", "low_lat", "low_lon", "west", "south", "east", "north", "c7_bowl", "s_c7_bowl",
        "bare_share", "ice_floor_share", "ice_rim_share"]


def _run(tmp, name, rows):
    d = tmp / name
    d.mkdir()
    (d / "radar.json").write_text(json.dumps({"base_type": "polar", "axes": AXES, "score_label": "score vs Moon",
                                              "lunar_target": {"label": "Shackleton", "criteria": {}}}))
    with open(d / "ranking.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    return d


def _row(cid, score, lat, lon, bare=0.9, ice_f=0.0, ice_r=0.0):
    return {"id": cid, "score": score, "lat": lat, "lon": lon, "low_lat": lat, "low_lon": lon, "west": lon - 0.05,
            "south": lat - 0.05, "east": lon + 0.05, "north": lat + 0.05, "c7_bowl": 0.13, "s_c7_bowl": score,
            "bare_share": bare, "ice_floor_share": ice_f, "ice_rim_share": ice_r}


def test_export_with_post_filters_dedupe_and_anchors(tmp_path, mines):
    night = _run(tmp_path, "night_polar", [
        _row("b001_r000c000", 0.7, 35.0, -111.0),                 # inside the mine -> excluded
        _row("b001_r000c001", 0.6, 20.0, 10.0, bare=0.1),          # vegetated -> excluded
        _row("b001_r000c002", 0.5, 22.9, 41.14),                   # ranked, anchor -> card key
        _row("b001_r000c003", 0.44, 31.0, -113.0),                 # same bowl as the region run -> dropped
    ])
    region = _run(tmp_path, "zz_region", [_row("r001c001", 0.46, 31.002, -113.001)])
    anchors = tmp_path / "anchors.csv"
    anchors.write_text("# comment line\nSITE,LAT,LON,MAX_KM\narid_test r001c001,22.9001,41.1401,1.5\n")
    info = tmp_path / "info.json"
    info.write_text(json.dumps({"arid_test r001c001": {"type": "candidate", "name": "Test crater"}}))
    out = tmp_path / "outputs"
    none = str(tmp_path / "none.yaml")
    p = subprocess.run([sys.executable, str(ROOT / "src" / "export_app.py"), str(night), str(region), "--out", str(out),
                        "--regions", none, "--night-regions", none, "--missed", none, "--sites-info", str(info),
                        "--post-filters", str(_cfg(tmp_path, mines)), "--anchors", str(anchors), "--dedupe-km", "1"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    rows = {r["CELL"]: r for r in csv.DictReader(open(out / "scores.csv", encoding="utf-8"))}
    assert set(rows) == {"b001_r000c000", "b001_r000c001", "b001_r000c002", "r001c001"}      # duplicate dropped
    assert rows["b001_r000c000"]["EXCLUDED"] == "excluded: mine" and rows["b001_r000c000"]["RANK"] == ""
    assert rows["b001_r000c000"]["SCORE_TOTAL"] == "0.7"                                      # score unchanged
    assert rows["b001_r000c001"]["EXCLUDED"].startswith("excluded: not a dry bowl") and rows["b001_r000c001"]["RANK"] == ""
    assert rows["b001_r000c002"]["RANK"] == "1" and rows["r001c001"]["RANK"] == "2"           # ranks close up
    assert rows["b001_r000c002"]["SITE"] == "arid_test r001c001" and rows["b001_r000c002"]["NAME"] == "Test crater"
    heat = json.loads((out / "heatmap.json").read_text())
    assert sorted(h["weight"] for h in heat) == [0.46, 0.5]                                   # excluded: no point
    raw = {r["CELL"]: r for r in csv.DictReader(open(out / "raw_values.csv", encoding="utf-8"))}
    assert "mining area" in raw["b001_r000c000"]["EXCLUDED_DETAIL"] and raw["b001_r000c000"]["MINE_DIST_KM"] == "0"
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "config-v1.1" in readme and "| excluded: mine | 1 |" in readme and "night_polar b001_r000c003" in readme


def test_export_without_new_flags_has_no_new_columns(tmp_path):
    run = _run(tmp_path, "runa", [_row("r001c001", 0.3, 35.0, -111.0, bare=0.0)])
    out = tmp_path / "outputs"
    none = str(tmp_path / "none.yaml")
    p = subprocess.run([sys.executable, str(ROOT / "src" / "export_app.py"), str(run), "--out", str(out),
                        "--regions", none, "--night-regions", none, "--missed", none,
                        "--sites-info", str(tmp_path / "none.json")], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    rows = list(csv.DictReader(open(out / "scores.csv", encoding="utf-8")))
    assert "EXCLUDED" not in rows[0] and rows[0]["RANK"] == "1"


def test_place_name_helpers():
    from place_names import _tidy, bearing_word, haversine_km
    assert bearing_word(0, 0, 1, 0) == "N" and bearing_word(0, 0, -1, -1) == "SW" and bearing_word(0, 0, 0, 1) == "E"
    assert abs(haversine_km(0, 0, 1, 0) - 111.2) < 0.2
    assert _tidy("SOUTHERN ALPS") == "Southern Alps" and _tidy("Hentiyn Mts.") == "Hentiyn Mountains"
