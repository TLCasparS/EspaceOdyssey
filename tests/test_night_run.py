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

sys.path.insert(0, str(ROOT / "tests"))

from night_fakes import fake_read_bbox, fake_read_glo90, fake_read_landcover, z_at as _z  # noqa: E402


@pytest.fixture
def patched(monkeypatch, tmp_path):
    import dem.glo90_cache
    import night_run
    import stage0_world as sw
    monkeypatch.setattr(night_run, "read_bbox", fake_read_bbox)
    monkeypatch.setattr(dem.glo90_cache, "read_glo90", fake_read_glo90)
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
    for r in with_bowl:                                             # A1 found it, A2 computed it, crop + provenance
        assert r["a1"]["depressions"] and r["a1"]["depressions"][0]["depth_m"] > 300
        assert r["prov"]["config_polar"] == "config-v1" and "GLO-30" in r["prov"]["dem"]
        crop = np.load(tmp / "night" / r["crop"]["path"])
        assert crop["z_dm"].dtype == np.int16 and crop["res_m"] == 60.0
        c = r["cands"][0]
        assert c["bowl_r_m"] and c["rim_zone_px"] and all(k in c for k in ("c1_sunny_ridge", "c2_dark_floor", "c3_light_dark", "c24_impact"))
    assert all("prov" in r for r in recs_a)
    recs_b1 = [json.loads(l) for l in open(tmp / "night" / "raw" / "B1" / "N35W112.jsonl")]
    assert sum(1 for r in recs_b1 if r["res"]) >= 40 and all(r["coarse_res"] == 90 for r in recs_b1)

    # resume: nothing left to do
    n2 = night_run.Night(tmp / "night", ROOT / "config" / "night_regions.yaml")
    n2.s["auto_b2"] = False                                         # B2 is tested explicitly below
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
    assert all(r["prov"]["config_mare"] and r["crop"]["shape"] for r in recs_b2)

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


def test_parallel_regions_mode_a1_skip_reasons(patched, monkeypatch):
    """2 tiles in regions mode with 2 spawned workers (fakes installed by the test hook): A1 runs on all kept
    cells, only the bowl cell(s) go to A2, the rest store the A1 skip reason; progress written by main only."""
    night_run, _, tmp = patched
    monkeypatch.setenv("NIGHT_RUN_TEST_HOOK", str(ROOT / "tests" / "night_fakes.py") + ":install")
    n = night_run.Night(tmp / "night", ROOT / "config" / "night_regions.yaml")
    n.regions = [{"name": "t", "bbox": [-112.0, 35.0, -110.0, 36.0], "priority": 1}]
    n.s["auto_b2"] = False
    n.run(tracks=("A",), res=30, workers=2)
    tiles = n.prog["tiles"]
    assert len(tiles) == 2 and all(st["A"] == "done" and not st.get("error") for st in tiles.values())
    recs = [json.loads(l) for p in sorted((tmp / "night" / "raw" / "A").glob("*.jsonl")) for l in open(p)]
    a2 = [r for r in recs if r["cands"]]
    skipped = [r for r in recs if r["prefilter"] and r["prefilter"].startswith("A1:")]
    assert 1 <= len(a2) <= 4 and len(skipped) >= 80
    assert sum(st["A2_cells"] for st in tiles.values()) == len(a2)
    assert all(r["prov"]["track"] == "A1+A2" for r in recs)
    assert not list((tmp / "night").glob("progress.json.tmp*"))
    # resume with workers: nothing to redo
    n2 = night_run.Night(tmp / "night", ROOT / "config" / "night_regions.yaml")
    n2.regions = n.regions
    n2.run(tracks=("A",), res=30, workers=2)
    assert "0 to do" in (tmp / "night" / "night.log").read_text(encoding="utf-8")
