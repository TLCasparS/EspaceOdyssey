"""src/export_app.py on two tiny fake runs (offline)."""
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AXES = [  # as written by pipeline/run.py
    {"id": "c1_sunny_ridge", "label": "1 Sunny ridge", "method": "rank", "weight": 1.0, "target": None, "tolerance": 0.1, "in_total": False},
    {"id": "c5_sky_view", "label": "5 Sky-view factor", "method": "target", "weight": 0.0, "target": 0.63, "tolerance": 0.1, "in_total": False},
    {"id": "c7_bowl", "label": "7 Bowl shape", "method": "target", "weight": 1.0, "target": 0.197, "tolerance": 0.05, "in_total": True},
]
LUNAR = {"label": "Shackleton", "criteria": {
    "c7_bowl": {"value": 0.197, "unit": "depth/width", "source": "LOLA test", "verified": True},
    "c1_sunny_ridge": {"value": None, "unit": "lit/flat", "source": None, "verified": False}}}


def _run(tmp, name, rows, axes=AXES):
    d = tmp / name
    d.mkdir()
    (d / "radar.json").write_text(json.dumps({"base_type": "polar", "axes": axes, "lunar_target": LUNAR,
                                              "score_label": "score vs Moon"}))
    cols = ["id", "score", "rank_score", "lat", "lon", "low_lat", "low_lon", "west", "south", "east", "north",
            "c1_sunny_ridge", "s_c1_sunny_ridge", "c5_sky_view", "s_c5_sky_view", "c7_bowl", "s_c7_bowl"]
    with open(d / "ranking.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return d


def _row(cid, score, lat, lon, **kw):
    return {"id": cid, "score": score, "rank_score": 0.5, "lat": lat, "lon": lon, "low_lat": lat + 0.01,
            "low_lon": lon + 0.01, "west": lon - 0.1, "south": lat - 0.1, "east": lon + 0.1, "north": lat + 0.1,
            "c1_sunny_ridge": 1.02, "s_c1_sunny_ridge": 0.5, "c5_sky_view": 0.72, "s_c5_sky_view": 0.38,
            "c7_bowl": 0.13, "s_c7_bowl": 0.17, **kw}


def _export(tmp, runs, *extra, isolate=True):
    out = tmp / "outputs"
    iso = ["--regions", str(tmp / "none.yaml"), "--night-regions", str(tmp / "none.yaml"),
           "--missed", str(tmp / "none.yaml")] if isolate else []
    if "--sites-info" not in extra:
        iso += ["--sites-info", str(tmp / "none.json")]
    p = subprocess.run([sys.executable, str(ROOT / "src" / "export_app.py"), *map(str, runs), "--out", str(out),
                        *iso, *extra], capture_output=True, text=True)
    return p, out


def test_export_writes_app_files(tmp_path):
    a = _run(tmp_path, "runa", [_row("r001c001", 0.3, 35.0, -111.0)])
    b = _run(tmp_path, "runb", [_row("r000c000", 0.6, 31.8, -113.4)])
    info = tmp_path / "info.json"
    info.write_text(json.dumps({"_note": "x", "Test Crater": {"type": "known"}}))
    coords = tmp_path / "coords.csv"
    coords.write_text("SITE,LAT,LON\nTest Crater,35.02,-111.03\nElsewhere,0,0\n")
    p, out = _export(tmp_path, [a, b], "--sites-info", str(info), "--sites-coords", str(coords))
    assert p.returncode == 0, p.stderr
    rows = list(csv.DictReader(open(out / "scores.csv")))
    assert [r["SITE"] for r in rows] == ["runb r000c000", "Test Crater"]          # sorted by total, name matched
    assert [r["RANK"] for r in rows] == ["1", "2"]
    assert rows[1]["SUNNY_RIDGE"] == ""                                            # rank-scored: not a similarity
    assert rows[1]["BOWL_SHAPE"] == "0.17" and rows[1]["SKY_VIEW"] == "0.38"        # target / display similarity
    assert rows[1]["CRATER_SIZE"] == ""                                            # not computed: no data
    assert rows[1]["LAT"] == "35.01" and rows[1]["LON"] == "-110.99"               # low point, not cut
    raw = list(csv.DictReader(open(out / "raw_values.csv")))
    assert raw[1]["SUNNY_RIDGE"] == "1.02"                                         # raw value is kept
    t = json.loads((out / "targets.json").read_text(encoding="utf-8"))["polar"]["criteria"]
    by = {c["column"]: c for c in t}
    assert by["BOWL_SHAPE"]["counts"] and by["BOWL_SHAPE"]["moon"]["value"] == 0.197
    assert by["SUNNY_RIDGE"]["score_method"] == "rank" and by["SUNNY_RIDGE"]["moon"]["value"] is None
    assert by["SKY_VIEW"]["score_method"] == "display" and not by["SKY_VIEW"]["counts"]
    heat = json.loads((out / "heatmap.json").read_text())
    assert heat[0] == {"lat": 31.8, "lng": -113.4, "weight": 0.6, "base": "polar"}  # cell centre, weight = total
    assert (out / "README.md").exists()
    assert json.loads((out / "cells.json").read_text()) == []                       # fake runs: no cells.geojson


def test_export_refuses_runs_with_different_config(tmp_path):
    a = _run(tmp_path, "runa", [_row("r001c001", 0.3, 35.0, -111.0)])
    axes_b = [dict(x, weight=0.5) if x["id"] == "c5_sky_view" else x for x in AXES]
    b = _run(tmp_path, "runb", [_row("r000c000", 0.6, 31.8, -113.4)], axes=axes_b)
    p, _ = _export(tmp_path, [a, b])
    assert p.returncode != 0 and "different config" in (p.stderr + p.stdout)


def test_impact_match_radius():
    sys.path.insert(0, str(ROOT / "src"))
    from export_app import impact_match
    ims = [{"name": "Test", "lat": 35.0, "lon": -111.0, "diameter_km": 1.2, "source": "x"}]
    disp = {"impact_match_rel": 0.6, "impact_match_min_km": 1.0}
    assert impact_match(35.005, -111.0, ims, disp)["name"] == "Test"           # 0.55 km < max(0.72, 1) km
    assert impact_match(35.05, -111.0, ims, disp) is None                      # 5.5 km away


def _mare_run(tmp, name, rows):
    d = tmp / name
    d.mkdir()
    axes = [{"id": c, "label": c, "method": "none", "weight": 1.0, "target": None, "tolerance": None, "in_total": False}
            for c in ("c9_relief", "c10_flat_base", "c12_drivable", "c13_roughness")]
    (d / "radar.json").write_text(json.dumps({"base_type": "mare", "axes": axes, "display": {"c16_day_night_swing": "fact"},
                                              "lunar_target": {"label": "Mare · Apollo 11", "named_site": "Apollo 11",
                                                               "criteria": {}}}))
    cols = ["id", "score", "lat", "lon", "base_lat", "base_lon", "west", "south", "east", "north",
            "c9_relief", "s_c9_relief", "c10_flat_base", "s_c10_flat_base", "c12_drivable", "s_c12_drivable",
            "c13_roughness", "s_c13_roughness"]
    with open(d / "ranking.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return d


def test_export_v2_regions_missed_mare(tmp_path):
    a = _run(tmp_path, "zz_region", [_row("zz_region_r001c001", 0.3, 35.0, -111.0)])
    m = _mare_run(tmp_path, "zz_mare", [{"id": "zz_region_r002c002", "score": "", "lat": 20.0, "lon": 17.0,
                                          "base_lat": 20.01, "base_lon": 17.01, "west": 16.9, "south": 19.9,
                                          "east": 17.1, "north": 20.1, "c9_relief": 120.0, "c10_flat_base": 0.2,
                                          "c12_drivable": 0.98, "c13_roughness": 1.1}])
    reg = tmp_path / "regions.yaml"
    reg.write_text("regions:\n  - {name: zz_region, title: ZZ Land, bbox: [-112, 34, 18, 36], role: screening, country: Nowhere}\n")
    missed = tmp_path / "missed.yaml"
    missed.write_text("missed:\n  - {name: Lost crater, country: Nowhere, lat: 1.0, lon: 2.0, base_type: polar, reason: 'too shallow, 44 m'}\n")
    p, out = _export(tmp_path, [a, m], "--regions", str(reg), "--night-regions", str(tmp_path / "none.yaml"),
                     "--missed", str(missed), isolate=False)
    assert p.returncode == 0, p.stderr
    rows = list(csv.DictReader(open(out / "scores.csv", encoding="utf-8")))
    by = {r["BASE_TYPE"] + r["ROLE"]: r for r in rows}
    pol, mare, lost = by["polarscreening"], by["marescreening"], by["polarmissed"]
    assert pol["NAME"] == "ZZ Land r001c001" and pol["COUNTRY"] == "Nowhere" and pol["RANK"] == "1"
    assert pol["TERRAIN_SCORE"] == "0.17" and pol["LIGHT_SCORE"] == ""        # c7 counts; c1 rank, c5 display
    assert mare["SCORE_TOTAL"] == "" and mare["RELIEF"] == "" and mare["LAT"] == "20.01"   # no Mare target yet
    assert lost["NAME"] == "Lost crater" and lost["MISSED_REASON"] == "too shallow; 44 m" and lost["RANK"] == ""
    raw = {r["BASE_TYPE"] + r["SITE"]: r for r in csv.DictReader(open(out / "raw_values.csv", encoding="utf-8"))}
    assert raw["mare" + mare["SITE"]]["RELIEF"] == "120" and raw["mare" + mare["SITE"]]["DRIVABLE"] == "0.98"
    t = json.loads((out / "targets.json").read_text(encoding="utf-8"))
    assert set(t) >= {"polar", "mare"} and t["mare"]["named_site"] == "Apollo 11"
    assert {c["column"] for c in t["mare"]["criteria"] if c["column"]} == {"RELIEF", "SLOPE_BASE", "DRIVABLE", "ROUGHNESS"}
    regs = json.loads((out / "regions.json").read_text(encoding="utf-8"))
    assert regs[0]["role"] == "screening"
    assert isinstance(json.loads((out / "coverage.json").read_text()), list)
