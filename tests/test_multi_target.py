"""pipeline.multi_target + export_app multi-target columns (night Task 3), synthetic raw values only."""
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline import multi_target as mt  # noqa: E402

# today's (built-in) Polar target, as config["polar"]["criteria"] after load_config / radar axes
POLAR = {
    "c7_bowl": {"weight": 1.0, "direction": "higher", "tolerance": 0.05, "target": 0.20},
    "c11_walls": {"weight": 1.0, "direction": "higher", "tolerance": 5.0, "target": 27.0},
    "c10_flat_base": {"weight": 1.0, "direction": "lower", "scale": [0, 15], "tolerance": 3.0, "target": 0.7},
    "c9_relief": {"weight": 0.0, "direction": "higher", "tolerance": 1500, "target": 4000.0},   # display only
}
MARE = {c: {"weight": 1.0, "direction": "target", "target": v, "tolerance": t}
        for c, v, t in (("c9_relief", 150.0, 160.0), ("c10_flat_base", 0.24, 0.5),
                        ("c12_drivable", 0.99, 0.05), ("c13_roughness", 1.7, 1.0))}
FLOORS = {"mare": {"c9_relief": 20, "c10_flat_base": 0.5, "c12_drivable": 0.05, "c13_roughness": 1.0}}


def _crit(values, verified=True, tol=None):
    return {c: {"value": v, "verified": verified, "source": "fake", **({"tolerance": tol[c]} if tol else {})}
            for c, v in values.items()}


FAKE_OK = {"name": "fake_ok", "label": "Fake verified", "base_type": "polar", "verified": True,
           "criteria": _crit({"c7_bowl": 0.05, "c11_walls": 9.0, "c10_flat_base": 1.0, "c9_relief": 150.0})}
FAKE_DRAFT = {"name": "fake_draft", "label": "Fake unverified", "base_type": "polar", "verified": False,
              "criteria": _crit({"c7_bowl": 0.10, "c11_walls": 15.0, "c10_flat_base": 1.0}, verified=False)}
SKIPPED = {"name": "fake_skipped", "base_type": "polar", "skipped": True, "skip_reason": "no bowl"}


def g(raw, target, tol):
    return math.exp(-((raw - target) / tol) ** 2)


def test_column_names():
    assert mt.column("polar_site01") == "SCORE_POLAR_SITE01"
    assert mt.column("Mare Crisium") == "SCORE_MARE_CRISIUM"
    with pytest.raises(ValueError):
        mt.column("total")                                   # SCORE_TOTAL is taken


def test_only_verified_targets_unless_preview():
    t = mt.build_targets({"polar": POLAR}, [FAKE_OK, FAKE_DRAFT, SKIPPED])
    assert [x["name"] for x in t] == ["shackleton", "fake_ok"]
    assert t[0]["builtin"] and not t[0]["preview"] and not t[1]["preview"]
    p = mt.build_targets({"polar": POLAR}, [FAKE_OK, FAKE_DRAFT, SKIPPED], include_unverified=True)
    assert [x["name"] for x in p] == ["shackleton", "fake_ok", "fake_draft"]          # skipped never
    assert p[2]["preview"] and not p[1]["preview"]


def test_same_rule_weights_and_tolerances():
    t = {x["name"]: x for x in mt.build_targets({"polar": POLAR}, [FAKE_OK])}
    raw = {"c7_bowl": "0.1", "c11_walls": 20.0, "c10_flat_base": 2.0, "c9_relief": 300.0}  # strings as in a CSV
    # built-in = today's score; candidate: same tolerances (from config, Polar has no own), weight-0 c9 ignored
    exp_b = round((round(g(0.1, 0.2, 0.05), 4) + round(g(20, 27, 5), 4) + round(g(2, 0.7, 3), 4)) / 3, 4)
    exp_c = round((round(g(0.1, 0.05, 0.05), 4) + round(g(20, 9, 5), 4) + round(g(2, 1.0, 3), 4)) / 3, 4)
    assert mt.score(raw, t["shackleton"]) == exp_b
    assert mt.score(raw, t["fake_ok"]) == exp_c
    row = mt.score_row(raw, "polar", list(t.values()))
    assert row == {"SCORE_SHACKLETON": exp_b, "SCORE_FAKE_OK": exp_c,
                   "BEST_TARGET": "shackleton" if exp_b >= exp_c else "fake_ok", "BEST_SCORE": max(exp_b, exp_c)}


def test_built_in_matches_pipeline_total_score():
    from pipeline.scoring import score_direct, total_score
    raw = {"c7_bowl": 0.13, "c11_walls": 18.2, "c10_flat_base": 1.4, "c9_relief": 200.0}
    s = {f"s_{c}": round(score_direct(raw[c], cc), 4) for c, cc in POLAR.items()}
    t = mt.build_targets({"polar": POLAR}, [])
    assert mt.score(raw, t[0]) == total_score(s, POLAR)[0]


def test_unverified_criterion_of_verified_target_is_left_out():
    cand = json.loads(json.dumps(FAKE_OK))
    cand["criteria"]["c11_walls"]["verified"] = False
    t = mt.build_targets({"polar": POLAR}, [cand])[1]
    assert t["criteria"]["c11_walls"]["target"] is None
    raw = {"c7_bowl": 0.05, "c11_walls": 50.0, "c10_flat_base": 1.0}
    # 15 Nov 2026: a target missing a counting criterion gives no score (not a renormalised 1.0, not 0)
    assert not t["complete"] and mt.score(raw, t) is None
    assert mt.build_targets({"polar": POLAR}, [cand], include_unverified=True)[1]["criteria"]["c11_walls"]["target"] == 9.0


def test_missing_values_never_score_better_than_real_ones():
    """A target with a gap would score 1.0 on the remaining criteria (renormalised); it must not win BEST."""
    gap = json.loads(json.dumps(FAKE_OK))
    gap["name"] = "fake_gap"
    del gap["criteria"]["c11_walls"]
    t = mt.build_targets({"polar": POLAR}, [FAKE_OK, gap])
    raw = {"c7_bowl": 0.05, "c11_walls": 20.0, "c10_flat_base": 1.0}       # perfect on c7 / c10, off on c11
    row = mt.score_row(raw, "polar", t)
    assert row["SCORE_FAKE_GAP"] is None and row["SCORE_FAKE_OK"] < 1.0
    assert row["BEST_TARGET"] == "fake_ok"
    # Earth side: a place without a counting value gets no score against any target (no data, never better)
    row = mt.score_row({"c7_bowl": 0.05, "c10_flat_base": 1.0}, "polar", t)
    assert row == {"SCORE_SHACKLETON": None, "SCORE_FAKE_OK": None, "SCORE_FAKE_GAP": None,
                   "BEST_TARGET": None, "BEST_SCORE": None}
    # display-only (weight 0) criteria are never required
    assert mt.score({"c7_bowl": 0.05, "c11_walls": 9.0, "c10_flat_base": 1.0}, t[1]) == 1.0


def test_verified_targets_in_repo_are_complete():
    """The verified candidates in config/ cover every counting criterion of their base type."""
    from pipeline.config import load_config
    cfg = load_config()
    base = {b: cfg[b]["criteria"] for b in mt.BUILTIN if b in cfg}
    t = mt.build_targets(base, mt.load_candidates(), tolerance_floor={"mare": cfg["mare"].get("tolerance_floor", {})})
    cands = [x for x in t if not x["builtin"]]
    assert cands and all(x["complete"] for x in cands), [x["name"] for x in cands if not x["complete"]]


def test_missing_value_is_no_data():
    t = mt.build_targets({"polar": POLAR}, [FAKE_OK])
    assert mt.score({"c7_bowl": None}, t[1]) is None
    assert mt.score_row({}, "polar", t) == {"SCORE_SHACKLETON": None, "SCORE_FAKE_OK": None,
                                            "BEST_TARGET": None, "BEST_SCORE": None}


def test_mare_own_tolerance_with_floor():
    own = {"c9_relief": 40.0, "c10_flat_base": 0.05, "c12_drivable": 0.01, "c13_roughness": 0.3}
    cand = {"name": "mare_fake", "base_type": "mare", "verified": True,
            "criteria": _crit({"c9_relief": 120.0, "c10_flat_base": 0.23, "c12_drivable": 0.998,
                               "c13_roughness": 1.3}, tol=own)}
    no_tol = {"name": "mare_notol", "base_type": "mare", "verified": True, "criteria": _crit({"c9_relief": 120.0})}
    t = {x["name"]: x for x in mt.build_targets({"mare": MARE}, [cand, no_tol], tolerance_floor=FLOORS)}
    c = t["mare_fake"]["criteria"]
    assert c["c9_relief"]["tolerance"] == 40.0 and c["c10_flat_base"]["tolerance"] == 0.5     # max(own, floor)
    assert c["c12_drivable"]["tolerance"] == 0.05 and c["c13_roughness"]["tolerance"] == 1.0
    assert t["mare_notol"]["criteria"]["c9_relief"]["target"] is None                         # Mare needs own tolerance
    assert mt.score({"c9_relief": 120.0}, t["mare_notol"]) is None


def test_targets_of_other_base_type_are_ignored():
    t = mt.build_targets({"polar": POLAR, "mare": MARE}, [FAKE_OK], tolerance_floor=FLOORS)
    assert [x["name"] for x in t] == ["shackleton", "mare_20cells", "fake_ok"]
    row = mt.score_row({"c9_relief": 150.0, "c10_flat_base": 0.24, "c12_drivable": 0.99, "c13_roughness": 1.7},
                       "mare", t)
    assert row == {"SCORE_MARE_20CELLS": 1.0, "BEST_TARGET": "mare_20cells", "BEST_SCORE": 1.0}


def test_score_records_picks_best_place_per_target():
    t = mt.build_targets({"polar": POLAR}, [FAKE_OK])
    like_shackleton = {"keep": True, "c7_bowl": 0.2, "c11_walls": 27.0, "c10_flat_base": 0.7}
    like_fake = {"keep": True, "c7_bowl": 0.05, "c11_walls": 9.0, "c10_flat_base": 1.0}
    dropped = {"keep": False, "c7_bowl": 0.2, "c11_walls": 27.0, "c10_flat_base": 0.7}
    recs = [{"cell": {"id": "b001_r1c1", "lat": 1, "lon": 2}, "cands": [like_fake, like_shackleton]},
            {"cell": {"id": "b001_r1c2", "lat": 1, "lon": 3}, "cands": [dropped]},
            {"cell": {"id": "b001_r1c3", "lat": 1, "lon": 4}, "cands": [], "prefilter": "x"}]
    rows = mt.score_records(recs, "polar", t)
    assert len(rows) == 1
    r = rows[0]
    assert r["SCORE_SHACKLETON"] == 1.0 and r["PLACE_SHACKLETON"] == 1
    assert r["SCORE_FAKE_OK"] == 1.0 and r["PLACE_FAKE_OK"] == 0
    assert r["BEST_TARGET"] == "shackleton"                  # tie: built-in first


def test_task5_file_format_loads():
    """The real candidates file (if present on this branch) parses; all its targets are unverified tonight."""
    p = ROOT / "config" / "lunar_targets_candidates.json"
    if not p.exists():
        pytest.skip("config/lunar_targets_candidates.json not on this branch (Task 5)")
    from pipeline.config import load_config
    cfg = load_config()
    base = {"polar": cfg["polar"]["criteria"], "mare": cfg["mare"]["criteria"]}
    floors = {"mare": cfg["mare"]["tolerance_floor"]}
    cands = mt.load_candidates(p)
    real = mt.build_targets(base, cands, False, floors)
    prev = mt.build_targets(base, cands, True, floors)
    assert {t["name"] for t in real if not t["builtin"]} == {c["name"] for c in cands if c.get("verified") is True}
    assert len(prev) >= len(real)


# --- export_app ---------------------------------------------------------------------------------

AXES = [{"id": c, "label": c, "method": "target" if cc["weight"] > 0 or c == "c9_relief" else "rank",
         "weight": cc["weight"], "target": cc["target"], "tolerance": cc["tolerance"],
         "in_total": cc["weight"] > 0} for c, cc in POLAR.items()]


def _place(cid, lat, lon, bowl, walls, base, relief=200.0):
    raw = {"c7_bowl": bowl, "c11_walls": walls, "c10_flat_base": base, "c9_relief": relief}
    s = {c: round(g(raw[c], POLAR[c]["target"], POLAR[c]["tolerance"]), 4) for c in raw}
    score = round((s["c7_bowl"] + s["c11_walls"] + s["c10_flat_base"]) / 3, 4)
    return {"id": cid, "score": score, "rank_score": "", "lat": lat, "lon": lon, "low_lat": lat, "low_lon": lon,
            "west": lon - 0.1, "south": lat - 0.1, "east": lon + 0.1, "north": lat + 0.1,
            **raw, **{f"s_{c}": v for c, v in s.items()}}


def _run(tmp, name, rows):
    d = tmp / name
    d.mkdir()
    (d / "radar.json").write_text(json.dumps({"base_type": "polar", "axes": AXES, "score_label": "score vs Moon",
                                              "lunar_target": {"label": "Shackleton", "criteria": {}}}))
    with open(d / "ranking.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return d


def _export(tmp, runs, out_name, cands, *extra):
    out = tmp / out_name
    none = tmp / "none.yaml"
    cpath = tmp / f"{out_name}_cands.json"
    if cands is not None:
        cpath.write_text(json.dumps({"targets": cands}))
    p = subprocess.run([sys.executable, str(ROOT / "src" / "export_app.py"), *map(str, runs), "--out", str(out),
                        "--regions", str(none), "--night-regions", str(none), "--missed", str(none),
                        "--sites-info", str(tmp / "none.json"), "--impacts", str(tmp / "none.csv"),
                        "--candidates", str(cpath), *extra], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr + p.stdout
    return out


@pytest.fixture
def runs(tmp_path):
    return [_run(tmp_path, "runa", [_place("r001c001", 35.0, -111.0, 0.19, 26.0, 0.8),
                                    _place("r001c002", 35.0, -110.5, 0.06, 10.0, 1.1)]),
            _run(tmp_path, "runb", [_place("r000c000", 31.8, -113.4, 0.12, 18.0, 1.5)])]


FILES = ("scores.csv", "raw_values.csv", "targets.json", "heatmap.json", "cells.json", "coverage.json",
         "regions.json", "README.md")


def test_export_regression_only_todays_targets(tmp_path, runs):
    """No candidates file, or only unverified candidates: every output file byte-identical."""
    a = _export(tmp_path, runs, "out_none", None)
    b = _export(tmp_path, runs, "out_draft", [FAKE_DRAFT, SKIPPED])
    for f in FILES:
        assert (a / f).read_bytes() == (b / f).read_bytes(), f
    head = next(csv.reader(open(a / "scores.csv")))
    assert not any(h.startswith("SCORE_") and h != "SCORE_TOTAL" for h in head) and "BEST_TARGET" not in head
    assert "lunar_targets" not in json.loads((a / "targets.json").read_text())["polar"]


def test_export_with_verified_candidate(tmp_path, runs):
    base = _export(tmp_path, runs, "out_none", None)
    out = _export(tmp_path, runs, "out_multi", [FAKE_OK, FAKE_DRAFT])
    old = list(csv.reader(open(base / "scores.csv")))
    new = list(csv.reader(open(out / "scores.csv")))
    n = len(old[0])
    assert new[0][n:] == ["SCORE_SHACKLETON", "SCORE_FAKE_OK", "BEST_TARGET", "BEST_SCORE"]   # appended
    assert [r[:n] for r in new] == old                                                        # old columns unchanged
    rows = list(csv.DictReader(open(out / "scores.csv")))
    for r in rows:
        assert r["SCORE_SHACKLETON"] == r["SCORE_TOTAL"]                                      # built-in = today
        s = {"shackleton": float(r["SCORE_SHACKLETON"]), "fake_ok": float(r["SCORE_FAKE_OK"])}
        assert r["BEST_TARGET"] == max(s, key=s.get) and float(r["BEST_SCORE"]) == max(s.values())
    by_cell = {r["CELL"]: r for r in rows}
    assert by_cell["r001c001"]["BEST_TARGET"] == "shackleton" and by_cell["r001c002"]["BEST_TARGET"] == "fake_ok"
    t = json.loads((out / "targets.json").read_text())
    assert [x["name"] for x in t["polar"]["lunar_targets"]] == ["shackleton", "fake_ok"]
    assert t["polar"]["lunar_targets"][1]["criteria"]["c7_bowl"] == {"value": 0.05, "tolerance": 0.05, "weight": 1.0}
    assert "c9_relief" not in t["polar"]["lunar_targets"][1]["criteria"]                       # weight 0: not listed
    assert t["_multi_target"]["preview"] is False
    for f in ("raw_values.csv", "heatmap.json"):
        assert (out / f).read_bytes() == (base / f).read_bytes(), f


def test_export_preview_is_marked(tmp_path, runs):
    out = _export(tmp_path, runs, "out_prev", [FAKE_OK, FAKE_DRAFT], "--include-unverified")
    rows = list(csv.DictReader(open(out / "scores.csv")))
    assert "SCORE_FAKE_DRAFT" in rows[0] and all(r["MULTI_TARGET_PREVIEW"] == "1" for r in rows)
    t = json.loads((out / "targets.json").read_text())
    assert t["_multi_target"]["preview"] is True and "PREVIEW" in t["_multi_target"]["note"]
    assert [x["preview"] for x in t["polar"]["lunar_targets"]] == [False, False, True]
    assert "PREVIEW" in (out / "README.md").read_text()
