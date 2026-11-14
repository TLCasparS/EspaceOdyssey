"""Polar criteria (src/pipeline/polar.py) and scoring (src/pipeline/scoring.py) on synthetic DEMs."""
import copy
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

from dem.grid import MetricGrid  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.polar import evaluate_polar_cell, fill_depressions  # noqa: E402
from pipeline.scoring import apply_rank, percentile_ranks, rank_score, total_score  # noqa: E402

CFG = load_config()                                  # real config, incl. verified lunar targets
CFG["light"]["sun"] = False                          # terrain tests: no year of Sun (tests/test_light.py covers it)
CFG_RANK = copy.deepcopy(CFG)                        # same, with lunar targets switched off
for _c in CFG_RANK["polar"]["criteria"].values():
    _c["target"] = None
CFG_FALLBACK = copy.deepcopy(CFG)                    # bowl-less cells scored (require_depression: false)
CFG_FALLBACK["polar"]["require_depression"] = False
RES = 60.0
N = 400                        # 24 km window: 15 km cell + buffer
CRS = "EPSG:32645"             # near its central meridian (87E): grid north ~ true north


def _grid(z):
    tf = from_origin(500_000 - N * RES / 2, 3_160_000, RES, RES)
    return MetricGrid(z.astype(np.float32), tf, CRS, RES)


def _cell_mask(half_km=7.5):
    rr, cc = np.indices((N, N))
    h = half_km * 1000 / RES
    return (np.abs(rr - N / 2) < h) & (np.abs(cc - N / 2) < h)


def _xy():
    rr, cc = np.indices((N, N))
    return (cc - N / 2 + 0.5) * RES, -(rr - N / 2 + 0.5) * RES      # x east, y north (m)


def _bowl(radius=3000.0, depth=1000.0):
    """Paraboloid bowl of given depth in a flat plain at 0 m (rim = plain level)."""
    x, y = _xy()
    r = np.hypot(x, y)
    return np.where(r < radius, depth * (r ** 2 / radius ** 2 - 1), 0.0)


def test_fill_raises_closed_depression_to_spill_level():
    z = _bowl(radius=1500, depth=200)[150:250, 150:250] + 10.0
    f = fill_depressions(z)
    assert np.allclose(f, 10.0, atol=1e-6)                       # bowl filled to the plain
    ramp = np.tile(np.arange(50.0), (50, 1))                       # no depression
    assert np.array_equal(fill_depressions(ramp), ramp)


def test_bowl():
    r = evaluate_polar_cell(_grid(_bowl()), _cell_mask(), None, 28.5, CFG_RANK)
    assert r["anchor"] == "depression" and r["n_candidates"] == 1
    assert r["c7_depth_m"] == pytest.approx(1000, abs=10)
    assert r["c7_width_m"] == pytest.approx(6000, rel=0.03)
    assert r["c7_bowl"] == pytest.approx(1000 / 6000, rel=0.04)
    assert (r["low_row"], r["low_col"]) in [(199, 199), (199, 200), (200, 199), (200, 200)]
    assert r["c9_relief"] == pytest.approx(1000, abs=20)          # floor to plain within 5 km
    assert r["c10_flat_base"] == pytest.approx(0, abs=0.01)       # the plain outside
    assert r["s_c10_flat_base"] == pytest.approx(1, abs=0.01) and r["keep"]
    assert 0 < r["base_to_bowl_km"] <= 0.2                        # flat ties -> pad right at the rim
    # inner walls: ring 0.5-1.0 x bowl radius = 1.5-3 km; paraboloid slope atan(2 d r / R^2)
    assert r["wall_ring_km"] == pytest.approx([1.5, 3.0], abs=0.1)
    x, y = _xy()
    rad = np.hypot(x, y)
    ring = (rad >= 1500) & (rad <= 3000)
    expect = np.degrees(np.arctan(np.where(rad < 3000, 2 * 1000 * rad / 3000 ** 2, 0.0)))[ring].mean()
    assert r["c11_walls"] == pytest.approx(expect, abs=1.5)
    # symmetric bowl: steep pixels within 3 km face every direction -> ~ 90/360 face north
    assert r["c14_aspect"] == pytest.approx(0.25, abs=0.03)
    assert r["s_c7_bowl"] == 0.5             # single-cell use: ranked among its own 1 candidate (run ranks run-wide)
    assert r["c13_roughness"] is not None and r["s_c13_roughness"] is None   # no lunar target in CFG_RANK


def test_c9_is_rim_to_floor_depth_also_for_bowls_wider_than_5_km():
    big = evaluate_polar_cell(_grid(_bowl(radius=6000, depth=1500) + 200), _cell_mask(), None, 28.5, CFG)
    assert big["c9_relief"] == pytest.approx(1500, abs=25)        # old 5 km window gave ~260 m here
    rimmed = _bowl(radius=3000, depth=800) + np.where(
        (np.hypot(*_xy()) >= 3000) & (np.hypot(*_xy()) < 3600), 150.0, 0.0)   # 150 m raised rim
    assert evaluate_polar_cell(_grid(rimmed), _cell_mask(), None, 28.5, CFG)["c9_relief"] == pytest.approx(950, abs=25)
    x, y = _xy()
    plane = evaluate_polar_cell(_grid(-0.1 * y), _cell_mask(), None, 28.5, CFG_FALLBACK)
    assert plane["c9_relief"] == 0.0                              # no bowl: data exists, depth 0


def test_target_scoring_is_gaussian_similarity():
    from pipeline.scoring import method, score_direct
    c = {"direction": "higher", "scale": [0, 1], "target": 0.2, "tolerance": 0.05}
    assert method(c) == "target"                                   # target wins over scale
    assert score_direct(0.2, c) == pytest.approx(1.0)
    assert score_direct(0.25, c) == pytest.approx(math.exp(-1))
    assert score_direct(0.10, c) == pytest.approx(math.exp(-4))
    assert score_direct(None, c) is None
    r = evaluate_polar_cell(_grid(_bowl()), _cell_mask(), None, 28.5, CFG)   # real targets
    for name, cc in CFG["polar"]["criteria"].items():
        if cc["target"] is not None and r[name] is not None:
            assert r[f"s_{name}"] == pytest.approx(math.exp(-((r[name] - cc["target"]) / cc["tolerance"]) ** 2), abs=1e-3)


def test_plane_no_depression_and_base_spot_filter():
    x, y = _xy()
    gentle = evaluate_polar_cell(_grid(-0.1 * y), _cell_mask(), None, 28.5, CFG_FALLBACK)   # rises south -> faces north
    slope = math.degrees(math.atan(0.1))
    assert gentle["anchor"] == "lowest_point" and gentle["c7_bowl"] == 0      # no depression: fallback
    assert gentle["c10_flat_base"] == pytest.approx(slope, abs=0.05)
    assert gentle["c11_walls"] == pytest.approx(slope, abs=0.05)
    assert gentle["c14_aspect"] == 0 and gentle["c14_n_steep"] == 0                 # 5.7 deg is not steep
    assert gentle["keep"]

    steep = evaluate_polar_cell(_grid(-0.6 * y), _cell_mask(), None, 28.5, CFG_FALLBACK)     # 31 deg everywhere
    assert steep["c14_aspect"] == pytest.approx(1.0)                                # all face north
    assert not steep["keep"] and steep["reason"].startswith("base-spot slope")

    south = evaluate_polar_cell(_grid(-0.6 * y), _cell_mask(), None, -28.5, CFG_FALLBACK)    # southern hemisphere
    assert south["c14_aspect"] == pytest.approx(0.0)                                # faces away from S pole


def test_ridge_aspect_half_and_steep_walls_never_masked():
    x, y = _xy()
    ridge = 2000 - 0.5 * np.abs(y)                                                   # E-W ridge, 26.6 deg flanks
    r = evaluate_polar_cell(_grid(ridge), _cell_mask(), None, 28.5, CFG_FALLBACK)
    # lowest pixel lies at the foot of one flank; all steep pixels within 3 km face one way
    assert r["c14_aspect"] in (pytest.approx(0.0, abs=0.02), pytest.approx(1.0, abs=0.02))
    assert r["c11_walls"] == pytest.approx(math.degrees(math.atan(0.5)), abs=1.0)   # steep pixels kept
    assert not r["keep"]                                                            # no flat pad anywhere


def test_base_spot_must_be_usable_and_on_the_rim():
    z = _bowl()
    usable = np.zeros((N, N), bool)
    usable[200 - 40:200 - 30, 195:205] = True       # only a strip on the bowl's north wall (inside the bowl)
    r = evaluate_polar_cell(_grid(z), _cell_mask(), usable, 28.5, CFG)
    assert not r["keep"] and r["c10_flat_base"] is None
    assert r["reason"].startswith("no usable base pad on the rim")
    usable[200 - 70:200 - 60, 195:205] = True       # plus a strip on the plain 3.6-4.2 km north (outside)
    r = evaluate_polar_cell(_grid(z), _cell_mask(), usable, 28.5, CFG)
    assert r["keep"] and usable[r["base_row"], r["base_col"]] and r["c10_flat_base"] == pytest.approx(0, abs=0.05)


def test_missing_dem_is_no_data_not_zero():
    z = _bowl()
    z[:, :] = np.nan
    r = evaluate_polar_cell(_grid(z), _cell_mask(), None, 28.5, CFG)
    assert not r["keep"] and all(r[c] is None for c in ("c7_bowl", "c9_relief", "c10_flat_base"))


def test_rank_scoring_direction_and_none_never_zero():
    crit = CFG_RANK["polar"]["criteria"]
    rows = [{"keep": True, "c7_bowl": v, "c9_relief": 100.0, "c11_walls": w,
             "s_c10_flat_base": 1.0, "s_c14_aspect": None, "s_c13_roughness": None}
            for v, w in [(0.0, 10.0), (0.1, 20.0), (0.2, 30.0)]]
    rows.append({"keep": False, "c7_bowl": 9.9, "c11_walls": 99.0})                # dropped: not ranked
    apply_rank(rows, crit)
    assert [r["s_c7_bowl"] for r in rows[:3]] == [0.0, 0.5, 1.0]                     # higher = better
    assert [r["s_c9_relief"] for r in rows[:3]] == [0.5, 0.5, 0.5]                   # ties
    assert "s_c7_bowl" not in rows[3]
    # no lunar targets in CFG_RANK: no total score; rank score = rank criteria with weight > 0 only
    assert total_score(rows[2], crit) == (None, 0)
    rs, n = rank_score(rows[2], crit)
    assert crit["c9_relief"]["weight"] == 0                                         # c9 display only: not counted
    assert crit["c10_flat_base"].get("scale") and n == 2 and rs == pytest.approx(1.0)  # c7, c11 (c10 is linear)
    assert rank_score({}, crit) == (None, 0)


def test_percentile_ranks():
    assert percentile_ranks([5.0]) == [0.5]
    assert percentile_ranks([3.0, 1.0, 2.0]) == [1.0, 0.0, 0.5]


def test_lunar_targets_match_pipeline_and_unverified_values_are_unused(tmp_path):
    import json
    from pipeline.config import TARGETS_PATH
    from pipeline.scoring import method
    targets = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))
    assert set(targets["polar"]["criteria"]) == set(CFG["polar"]["criteria"])
    for name, c in CFG["polar"]["criteria"].items():              # verified -> used, with a tolerance
        t = targets["polar"]["criteria"][name]
        assert (c["target"] is not None) == bool(t["verified"] and t["value"] is not None)
        assert c["target"] is None or (method(c) == "target" and c["tolerance"] > 0 and t["source"] and t["dem"])

    targets["polar"]["criteria"]["c9_relief"].update(value=1234.0, verified=False)
    p = tmp_path / "t.json"
    p.write_text(json.dumps(targets), encoding="utf-8")
    assert load_config(targets_path=p)["polar"]["criteria"]["c9_relief"]["target"] is None
    targets["polar"]["criteria"]["c9_relief"]["verified"] = True
    p.write_text(json.dumps(targets), encoding="utf-8")
    c9 = load_config(targets_path=p)["polar"]["criteria"]["c9_relief"]
    assert c9["target"] == 1234.0 and method(c9) == "target"


def _bowl_at(x0, y0, radius, depth):
    x, y = _xy()
    r = np.hypot(x - x0, y - y0)
    return np.where(r < radius, depth * (r ** 2 / radius ** 2 - 1), 0.0)


def test_depressions_below_minimums_are_ignored():
    shallow = evaluate_polar_cell(_grid(_bowl_at(0, 0, 2000, 40)), _cell_mask(), None, 28.5, CFG_FALLBACK)   # 40 m < 50
    narrow = evaluate_polar_cell(_grid(_bowl_at(0, 0, 400, 300)), _cell_mask(), None, 28.5, CFG_FALLBACK)    # 800 m < 1000
    for r in (shallow, narrow):
        assert r["n_depressions"] == 0 and r["anchor"] == "lowest_point" and r["c7_bowl"] == 0


def test_best_of_several_depressions_is_one_coherent_place():
    z = (_bowl_at(-4000, 0, 2500, 600)          # A: big, deep
         + _bowl_at(4500, 0, 1000, 120)         # B: qualifies, smaller
         + _bowl_at(0, 5000, 1000, 30)          # too shallow
         + _bowl_at(0, -5000, 300, 200))        # too narrow
    r = evaluate_polar_cell(_grid(z), _cell_mask(), None, 28.5, CFG)
    assert r["n_depressions"] == 2 and r["n_candidates"] == 2
    lx, ly = (r["low_col"] - N / 2 + 0.5) * RES, -(r["low_row"] - N / 2 + 0.5) * RES
    assert abs(lx + 4000) < 120 and abs(ly) < 120                    # A chosen
    assert r["c7_depth_m"] == pytest.approx(600, abs=10)
    assert 0 < r["base_to_bowl_km"] <= CFG["polar"]["max_base_to_bowl_km"]  # base on this bowl's rim


def test_depression_crossing_cell_edge_counted_once_by_its_low_point():
    inside = evaluate_polar_cell(_grid(_bowl_at(6500, 0, 2000, 300)), _cell_mask(), None, 28.5, CFG)
    assert inside["anchor"] == "depression"
    assert inside["depression_extends_outside_cell"]
    assert inside["c7_width_m"] == pytest.approx(4000, rel=0.03)   # found whole, not cut at the edge
    outside = evaluate_polar_cell(_grid(_bowl_at(8500, 0, 2000, 300)), _cell_mask(), None, 28.5, CFG_FALLBACK)
    assert outside["n_depressions"] == 0 and outside["anchor"] == "lowest_point"   # belongs to the neighbour


def test_base_spot_must_be_within_max_distance_of_bowl_edge():
    z = _bowl_at(0, 0, 3000, 1000)                     # bowl edge at 3 km; limit max_base_to_bowl_km = 1
    assert CFG["polar"]["max_base_to_bowl_km"] == 1
    usable = np.zeros((N, N), bool)
    usable[195:205, 200 + 70:200 + 80] = True          # plain 4.2-4.8 km east = 1.2-1.8 km from the edge: too far
    r = evaluate_polar_cell(_grid(z), _cell_mask(), usable, 28.5, CFG)
    assert not r["keep"] and r["reason"].startswith("no usable base pad on the rim")
    usable[195:205, 200 + 53:200 + 63] = True          # 3.2-3.8 km east = 0.2-0.8 km from the edge: allowed
    r = evaluate_polar_cell(_grid(z), _cell_mask(), usable, 28.5, CFG)
    assert r["keep"] and 0 < r["base_to_bowl_km"] <= 1 and r["c10_flat_base"] == pytest.approx(0, abs=0.05)


def test_c13_roughness_is_bowl_plus_rim_ring_not_whole_cell():
    x, y = _xy()
    rough_far = np.where(np.abs(x) > 6000, 30 * np.sin(x / 90.0) * np.sin(y / 90.0), 0.0)   # rough terrain far away
    r_smooth = evaluate_polar_cell(_grid(_bowl()), _cell_mask(), None, 28.5, CFG_RANK)
    r_far = evaluate_polar_cell(_grid(_bowl() + rough_far), _cell_mask(), None, 28.5, CFG_RANK)
    assert r_far["c13_roughness"] == pytest.approx(r_smooth["c13_roughness"], abs=0.5)   # outside 1.3 r: ignored


def test_no_bowl_fallback_keeps_fixed_ring_and_low_point_radius():
    x, y = _xy()
    r = evaluate_polar_cell(_grid(-0.1 * y), _cell_mask(), None, 28.5, CFG_FALLBACK)
    assert r["anchor"] == "lowest_point" and r["wall_ring_km"] == [0.5, 3.0]
    assert r["base_to_bowl_km"] is None and r["base_to_low_km"] <= CFG["polar"]["max_base_to_low_km"]


def test_require_depression_drops_bowl_less_cells():
    x, y = _xy()
    assert CFG["polar"]["require_depression"] is True
    r = evaluate_polar_cell(_grid(-0.1 * y), _cell_mask(), None, 28.5, CFG)
    assert not r["keep"] and r["reason"].startswith("no depression")


def test_elongated_valley_is_not_a_bowl():
    x, y = _xy()
    trench = np.where((np.abs(y) < 600) & (np.abs(x) < 6000), -300 * (1 - (y / 600) ** 2), 0.0)   # 12 x 1.2 km
    r = evaluate_polar_cell(_grid(trench), _cell_mask(), None, 28.5, CFG_FALLBACK)
    assert r["n_depressions"] == 0 and r["anchor"] == "lowest_point"
    bowl = evaluate_polar_cell(_grid(_bowl()), _cell_mask(), None, 28.5, CFG)
    assert bowl["c7_elongation"] == pytest.approx(1.0, abs=0.08)                   # circle ~ 1


def test_ice_floor_excludes_place_and_ice_shares_are_shown():
    from pipeline.polar import best_of, polar_candidates, select_best
    z = _bowl()                                                          # bowl r = 3 km
    x, y = _xy()
    r = np.hypot(x, y)
    for ice, expect_keep in ((r < 1500, False), ((r > 3000) & (r < 3500), True)):   # icy floor / icy rim ring
        info, cands = polar_candidates(_grid(z), _cell_mask(), None, 28.5, CFG, ice=ice)
        c = cands[0]
        assert c["ice_floor_share"] is not None and c["ice_rim_share"] is not None
        assert c["keep"] is expect_keep
        if not expect_keep:
            assert c["ice_floor_share"] > CFG["polar"]["max_floor_ice_share"]
            assert c["reason"].startswith("ice floor, DEM measures ice surface")
        else:
            assert c["ice_floor_share"] == 0 and c["ice_rim_share"] > 0
    info, cands = polar_candidates(_grid(z), _cell_mask(), None, 28.5, CFG)   # no ice data -> shares None
    assert cands[0]["ice_floor_share"] is None and cands[0]["keep"]
