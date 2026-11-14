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


def _export(tmp, runs, *extra):
    out = tmp / "outputs"
    p = subprocess.run([sys.executable, str(ROOT / "src" / "export_app.py"), *map(str, runs), "--out", str(out), *extra],
                       capture_output=True, text=True)
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
    assert heat[0] == {"lat": 31.8, "lng": -113.4, "weight": 0.6}                  # cell centre, weight = total
    assert (out / "README.md").exists()


def test_export_refuses_runs_with_different_config(tmp_path):
    a = _run(tmp_path, "runa", [_row("r001c001", 0.3, 35.0, -111.0)])
    axes_b = [dict(x, weight=0.5) if x["id"] == "c5_sky_view" else x for x in AXES]
    b = _run(tmp_path, "runb", [_row("r000c000", 0.6, 31.8, -113.4)], axes=axes_b)
    p, _ = _export(tmp_path, [a, b])
    assert p.returncode != 0 and "different config" in (p.stderr + p.stdout)
