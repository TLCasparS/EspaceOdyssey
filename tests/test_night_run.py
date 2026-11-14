"""Offline end-to-end test of stage0_world.py + night_run.py (all S3 readers replaced by synthetic data).
One 1 x 1 deg tile N35W112: bare plain (WorldCover 60) with one bowl (r 3 km, 400 m deep) in the middle."""
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

LAT_C, LON_C = 35.5, -111.5


def _z(lon, lat):
    dx = (lon - LON_C) * 111_320 * math.cos(math.radians(LAT_C))
    dy = (lat - LAT_C) * 110_574
    r = np.hypot(dx, dy)
    return np.where(r < 3000, 400 * (r ** 2 / 3000 ** 2 - 1), 0.0) + 1000.0


def fake_read_bbox(west, south, east, north, res=30):
    d = res / 111_320
    w, h = int(math.ceil((east - west) / d)), int(math.ceil((north - south) / d))
    tf = from_origin(west, north, d, d)
    cc, rr = np.meshgrid(np.arange(w) + 0.5, np.arange(h) + 0.5)
    lon, lat = tf * (cc, rr)
    return _z(lon, lat).astype(np.float32), {"transform": tf, "crs": "EPSG:4326"}


def fake_read_landcover(west, south, east, north, res_m=100.0):
    d = res_m / 111_320
    w, h = max(1, round((east - west) / d)), max(1, round((north - south) / d))
    return np.full((h, w), 60, np.uint8), from_origin(west, north, (east - west) / w, (north - south) / h)


@pytest.fixture
def patched(monkeypatch, tmp_path):
    import night_run
    import stage0_world as sw
    monkeypatch.setattr(night_run, "read_bbox", fake_read_bbox)
    monkeypatch.setattr(night_run, "read_landcover", fake_read_landcover)
    monkeypatch.setattr(sw.LC, "block", lambda lat3, lon3: np.full((333, 333), 60, np.uint8))

    def fake_dem_coarse(lat0, lon0, px):
        d = 1.0 / px
        tf = from_origin(lon0, lat0 + 1, d, d)
        cc, rr = np.meshgrid(np.arange(px) + 0.5, np.arange(px) + 0.5)
        lon, lat = tf * (cc, rr)
        return _z(lon, lat).astype(np.float32), tf
    monkeypatch.setattr(sw, "read_dem_coarse", fake_dem_coarse)
    return night_run, sw, tmp_path


def _stage0(sw, work):
    import yaml
    from pipeline.config import load_config
    s = yaml.safe_load((ROOT / "config" / "night_regions.yaml").read_text(encoding="utf-8"))["settings"]
    res = sw.prescreen_tile(35, -112, load_config(), s)
    work.mkdir(parents=True, exist_ok=True)
    (work / "stage0_world.jsonl").write_text(json.dumps(res) + "\n")
    return res, sw.summary(work)


def test_stage0_world_prescreen(patched):
    _, sw, tmp = patched
    res, summ = _stage0(sw, tmp / "world")
    assert res["n_cells"] == 49 and res["dem_read"]
    bowl = [c for c in res["cells"] if c["relief"] and c["relief"] > 100]
    assert bowl and all(c["a"] for c in bowl)                       # the bowl cell(s): A candidates
    assert sum(c["b"] for c in res["cells"]) >= 40                  # bare, flat: B candidates
    assert summ["tiles"][0]["tile"] == "N35W112"


def test_night_run_world_A_B1_defer_B2_resume_score(patched):
    night_run, sw, tmp = patched
    _stage0(sw, tmp / "world")
    n = night_run.Night(tmp / "night", ROOT / "config" / "night_regions.yaml")
    n.cfg["light"].update(step_min=360, n_azimuths=36)               # fast Sun simulation
    for c in n.cfg["mare"]["criteria"].values():                    # no lunar Mare target yet
        c["target"] = c["tolerance"] = None
    n.run(tracks=("A", "B1"), res=30, world_dir=tmp / "world")
    st = n.prog["tiles"]["N35W112"]
    assert st["A"] == "done" and st["B1"] == "done" and not st.get("error")
    log = (tmp / "night" / "night.log").read_text(encoding="utf-8")
    assert "B2 deferred" in log                                     # fallback: coarse only, B2 tomorrow
    recs_a = [json.loads(l) for l in open(tmp / "night" / "raw" / "A" / "N35W112.jsonl")]
    with_bowl = [r for r in recs_a if r["cands"]]
    assert len(with_bowl) >= 1
    assert any(r["prefilter"] and "world stage 0" in r["prefilter"] for r in recs_a)   # flat cells: not A candidates
    recs_b1 = [json.loads(l) for l in open(tmp / "night" / "raw" / "B1" / "N35W112.jsonl")]
    assert sum(1 for r in recs_b1 if r["res"]) >= 40 and all(r["coarse_res"] == 90 for r in recs_b1)

    # resume: nothing left to do
    n2 = night_run.Night(tmp / "night", ROOT / "config" / "night_regions.yaml")
    n2.run(tracks=("A", "B1"), res=30, world_dir=tmp / "world")
    assert "N35W112" in n2.prog["tiles"] and n2.prog["tiles"]["N35W112"]["A"] == "done"

    # Mare target arrives -> select + 30 m pass
    for name, (tgt, tol) in {"c9_relief": (5.0, 20), "c10_flat_base": (0.2, 0.5), "c12_drivable": (1.0, 0.05),
                             "c13_roughness": (0.5, 1.0)}.items():
        n2.cfg["mare"]["criteria"][name].update(target=tgt, tolerance=tol)
    assert n2.mare_ready()
    sel = n2.select_b2(10)
    assert sel["n_selected"] == 10 and sel["coarse_score_cutoff"] is not None
    n2.run_b2()
    recs_b2 = [json.loads(l) for l in open(tmp / "night" / "raw" / "B2" / "N35W112.jsonl")]
    assert len(recs_b2) == 10 and all(r["res"]["c10_flat_base"] is not None for r in recs_b2)

    # morning: scoring from raw values only
    n2.res = 30
    n2.score(out_root=tmp / "out")
    pol = list(csv.DictReader(open(tmp / "out" / "night_polar" / "ranking.csv")))
    assert len(pol) >= 1 and float(pol[0]["c7_depth_m"]) == pytest.approx(400, abs=40)
    mare = list(csv.DictReader(open(tmp / "out" / "night_mare" / "ranking.csv")))
    assert len(mare) == 10 and mare[0]["score"] != ""                # B2 scored for real
    assert (tmp / "out" / "night_mare_coarse" / "ranking.csv").exists()


def test_max_hours_stops_cleanly(patched):
    night_run, sw, tmp = patched
    _stage0(sw, tmp / "world")
    n = night_run.Night(tmp / "night", ROOT / "config" / "night_regions.yaml")
    n.run(tracks=("A", "B1"), res=30, world_dir=tmp / "world", max_hours=-1)   # limit already reached
    log = (tmp / "night" / "night.log").read_text(encoding="utf-8")
    assert "time limit" in log and "B2 not started" in log
    assert "N35W112" not in n.prog["tiles"]
