"""GLiM rock class display columns in src/export_app.py (--glim), synthetic grid, offline."""
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import export_app  # noqa: E402

MCFG = {"radius_km": 5}


@pytest.fixture
def grid(tmp_path):
    # 4 x 2 grid of 1-deg cells from lon 8, lat -1 (row 0 = north): sea | vb | sc | sc
    d = tmp_path / "glim" / "extracted"
    d.mkdir(parents=True)
    (d / export_app.GLIM_GRID).write_text("ncols 4\nnrows 2\nxllcorner 8\nyllcorner -1\ncellsize 1\nNODATA_value -9999\n"
                                          "-9999 2 6 6\n-9999 2 6 6\n")
    (d / "Classnames.txt").write_text('"OBJECTID";"Value_";"Count_";"xx"\n1;2;1.0;"vb"\n2;6;1.0;"sc"\n')
    return tmp_path / "glim"


def test_rock_values_basalt_other_and_sea(grid):
    g = export_app.load_glim(grid, MCFG)                      # folder: finds the .asc inside
    vb = export_app.rock_values(0.5, 9.5, g)
    assert vb["ROCK_CLASS"] == "vb" and vb["ROCK_CLASS_NAME"] == "basic volcanic rocks"
    assert vb["BASALT_SHARE_5KM"] == 1.0 and vb["BASALT_REGION"] == 1.0 and vb["GLIM_COVERED_SHARE"] == 1.0
    sc = export_app.rock_values(0.5, 10.5, g)
    assert sc["ROCK_CLASS"] == "sc" and sc["BASALT_SHARE_5KM"] == 0.0 and sc["BASALT_REGION"] == 0.0
    # coast: point in the sea cell, 2 km from the vb cell -> no data, nothing borrowed from the vb cell, never 0
    coast = export_app.rock_values(0.5, 8.982, g)
    assert coast["ROCK_CLASS"] == "" and coast["GLIM_COVERED_SHARE"] > 0
    assert coast["BASALT_SHARE_5KM"] is None and coast["BASALT_REGION"] is None
    # team rule: the flag is the class AT the point, not the share around it
    corner = export_app.rock_values(0.998, 9.002, g)         # vb cell corner, sea west + north: little coverage
    assert corner["ROCK_CLASS"] == "vb" and corner["GLIM_COVERED_SHARE"] < 0.5 and corner["BASALT_REGION"] == 1.0
    edge = export_app.rock_values(0.5, 10.002, g)            # 200 m into sc next to vb: share_vb just under 0.5
    assert edge["ROCK_CLASS"] == "sc" and edge["BASALT_REGION"] == 0.0 and 0.3 < edge["BASALT_SHARE_5KM"] < 0.5
    sea = export_app.rock_values(0.5, 8.3, g)                  # open sea: nothing covered
    assert sea["ROCK_CLASS"] == "" and sea["BASALT_REGION"] is None and sea["GLIM_COVERED_SHARE"] == 0.0
    assert export_app.rock_values(None, None, g)["BASALT_REGION"] is None


def test_display_config_has_material_block():
    import yaml
    m = yaml.safe_load((ROOT / "config" / "display.yaml").read_text(encoding="utf-8"))["material"]
    assert m == MCFG


AXES = [{"id": "c7_bowl", "label": "7 Bowl shape", "method": "target", "weight": 1.0, "target": 0.197,
         "tolerance": 0.05, "in_total": True}]
COLS = ["id", "score", "lat", "lon", "low_lat", "low_lon", "west", "south", "east", "north", "c7_bowl", "s_c7_bowl"]


def test_export_glim_columns_are_display_only(tmp_path, grid):
    run = tmp_path / "runa"
    run.mkdir()
    (run / "radar.json").write_text(json.dumps({"base_type": "polar", "axes": AXES, "score_label": "score vs Moon",
                                                "lunar_target": {"label": "Shackleton", "criteria": {}}}))
    with open(run / "ranking.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for cid, score, lat, lon in (("r001c001", 0.6, 0.5, 10.5), ("r001c002", 0.5, 0.5, 9.5), ("r001c003", 0.4, 0.5, 8.3)):
            w.writerow({"id": cid, "score": score, "lat": lat, "lon": lon, "low_lat": lat, "low_lon": lon,
                        "west": lon - 0.05, "south": lat - 0.05, "east": lon + 0.05, "north": lat + 0.05,
                        "c7_bowl": 0.13, "s_c7_bowl": score})
    none = str(tmp_path / "none.yaml")
    args = [sys.executable, str(ROOT / "src" / "export_app.py"), str(run), "--regions", none, "--night-regions", none,
            "--missed", none, "--sites-info", str(tmp_path / "none.json"), "--candidates", str(tmp_path / "none.json")]
    p0 = subprocess.run(args + ["--out", str(tmp_path / "plain")], capture_output=True, text=True)
    p1 = subprocess.run(args + ["--out", str(tmp_path / "glim_out"), "--glim", str(grid)], capture_output=True, text=True)
    assert p0.returncode == 0 and p1.returncode == 0, p0.stderr + p1.stderr
    # scores.csv is the same with and without --glim: rock class never changes a score or a rank
    assert (tmp_path / "plain" / "scores.csv").read_text() == (tmp_path / "glim_out" / "scores.csv").read_text()
    raw = {r["CELL"]: r for r in csv.DictReader(open(tmp_path / "glim_out" / "raw_values.csv", encoding="utf-8"))}
    assert raw["r001c002"]["ROCK_CLASS"] == "vb" and raw["r001c002"]["BASALT_REGION"] == "1"
    assert raw["r001c001"]["ROCK_CLASS"] == "sc" and raw["r001c001"]["BASALT_REGION"] == "0"
    assert raw["r001c003"]["ROCK_CLASS"] == "" and raw["r001c003"]["BASALT_REGION"] == ""      # sea: no data
    plain_raw = next(csv.reader(open(tmp_path / "plain" / "raw_values.csv", encoding="utf-8")))
    assert "ROCK_CLASS" not in plain_raw
    t = json.loads((tmp_path / "glim_out" / "targets.json").read_text(encoding="utf-8"))
    assert "PANGAEA.788537" in t["_material"]["source"] and t["_material"]["classes"]["vb"] == "basic volcanic rocks"
    assert t["_material"]["caveat"] == "0.5° grid, regional, not site-level"
    assert "| polar | no data | 1 |" in (tmp_path / "glim_out" / "README.md").read_text(encoding="utf-8")
