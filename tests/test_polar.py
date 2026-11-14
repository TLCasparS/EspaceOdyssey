"""Polar criteria (src/pipeline/polar.py) and scoring (src/pipeline/scoring.py) on synthetic DEMs."""
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
from pipeline.scoring import apply_rank, percentile_ranks, weighted_score  # noqa: E402

CFG = load_config()
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
    r = evaluate_polar_cell(_grid(_bowl()), _cell_mask(), None, 28.5, CFG)
    assert r["has_depression"]
    assert r["c7_depth_m"] == pytest.approx(1000, abs=10)
    assert r["c7_width_m"] == pytest.approx(6000, rel=0.03)
    assert r["c7_bowl"] == pytest.approx(1000 / 6000, rel=0.04)
    assert (r["low_row"], r["low_col"]) in [(199, 199), (199, 200), (200, 199), (200, 200)]
    assert r["c9_relief"] == pytest.approx(1000, abs=20)          # floor to plain within 5 km
    assert r["c10_flat_base"] == pytest.approx(0, abs=0.01)       # the plain outside
    assert r["s_c10_flat_base"] == pytest.approx(1, abs=0.01) and r["keep"]
    # paraboloid wall slope at radius r: atan(2 d r / R^2); ring 500-3000 m is mostly inside the bowl
    assert 15 < r["c11_walls"] < 30
    # symmetric bowl: steep pixels face every direction -> ~ 90/360 face north
    assert r["c14_aspect"] == pytest.approx(0.25, abs=0.03)
    assert r["s_c7_bowl"] is None                                  # rank: filled later across cells
    assert r["c13_roughness"] is not None and r["s_c13_roughness"] is None   # no lunar target yet


def test_plane_no_depression_and_base_spot_filter():
    x, y = _xy()
    gentle = evaluate_polar_cell(_grid(-0.1 * y), _cell_mask(), None, 28.5, CFG)   # rises south -> faces north
    slope = math.degrees(math.atan(0.1))
    assert not gentle["has_depression"] and gentle["c7_bowl"] == 0
    assert gentle["c10_flat_base"] == pytest.approx(slope, abs=0.05)
    assert gentle["c11_walls"] == pytest.approx(slope, abs=0.05)
    assert gentle["c14_aspect"] == 0 and gentle["c14_n_steep"] == 0                 # 5.7 deg is not steep
    assert gentle["keep"]

    steep = evaluate_polar_cell(_grid(-0.6 * y), _cell_mask(), None, 28.5, CFG)     # 31 deg everywhere
    assert steep["c14_aspect"] == pytest.approx(1.0)                                # all face north
    assert not steep["keep"] and steep["reason"].startswith("base-spot slope")

    south = evaluate_polar_cell(_grid(-0.6 * y), _cell_mask(), None, -28.5, CFG)    # southern hemisphere
    assert south["c14_aspect"] == pytest.approx(0.0)                                # faces away from S pole


def test_ridge_aspect_half_and_steep_walls_never_masked():
    x, y = _xy()
    ridge = 2000 - 0.5 * np.abs(y)                                                   # E-W ridge, 26.6 deg flanks
    r = evaluate_polar_cell(_grid(ridge), _cell_mask(), None, 28.5, CFG)
    assert r["c14_aspect"] == pytest.approx(0.5, abs=0.02)
    assert r["c11_walls"] == pytest.approx(math.degrees(math.atan(0.5)), abs=1.0)   # steep pixels kept
    assert not r["keep"]                                                            # no flat pad anywhere


def test_base_spot_must_be_usable():
    z = _bowl()
    usable = np.zeros((N, N), bool)
    usable[200 - 40:200 - 30, 195:205] = True       # only a strip on the bowl's north wall
    r = evaluate_polar_cell(_grid(z), _cell_mask(), usable, 28.5, CFG)
    assert usable[r["base_row"], r["base_col"]]
    assert r["c10_flat_base"] > 5                    # the flat plain is not usable
    none = evaluate_polar_cell(_grid(z), _cell_mask(), np.zeros((N, N), bool), 28.5, CFG)
    assert none["c10_flat_base"] is None and none["reason"] == "no usable base pad"


def test_missing_dem_is_no_data_not_zero():
    z = _bowl()
    z[:, :] = np.nan
    r = evaluate_polar_cell(_grid(z), _cell_mask(), None, 28.5, CFG)
    assert not r["keep"] and all(r[c] is None for c in ("c7_bowl", "c9_relief", "c10_flat_base"))


def test_rank_scoring_direction_and_none_never_zero():
    crit = CFG["polar"]["criteria"]
    rows = [{"keep": True, "c7_bowl": v, "c9_relief": 100.0, "c11_walls": w,
             "s_c10_flat_base": 1.0, "s_c14_aspect": None, "s_c13_roughness": None}
            for v, w in [(0.0, 10.0), (0.1, 20.0), (0.2, 30.0)]]
    rows.append({"keep": False, "c7_bowl": 9.9, "c11_walls": 99.0})                # dropped: not ranked
    apply_rank(rows, crit)
    assert [r["s_c7_bowl"] for r in rows[:3]] == [0.0, 0.5, 1.0]                     # higher = better
    assert [r["s_c9_relief"] for r in rows[:3]] == [0.5, 0.5, 0.5]                   # ties
    assert "s_c7_bowl" not in rows[3]
    score, n = weighted_score(rows[2], crit)
    assert n == 4 and score == pytest.approx((1.0 + 0.5 + 1.0 + 1.0) / 4)          # None (13, 14) skipped, not 0
    assert weighted_score({}, crit) == (None, 0)


def test_percentile_ranks():
    assert percentile_ranks([5.0]) == [0.5]
    assert percentile_ranks([3.0, 1.0, 2.0]) == [1.0, 0.0, 0.5]


def test_lunar_targets_match_pipeline_and_unverified_values_are_unused(tmp_path):
    import json
    from pipeline.config import TARGETS_PATH
    from pipeline.scoring import method
    targets = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))
    assert set(targets["polar"]["criteria"]) == set(CFG["polar"]["criteria"])
    assert all(c["target"] is None for c in CFG["polar"]["criteria"].values())   # nothing verified yet

    targets["polar"]["criteria"]["c9_relief"].update(value=1234.0, verified=False)
    p = tmp_path / "t.json"
    p.write_text(json.dumps(targets), encoding="utf-8")
    assert load_config(targets_path=p)["polar"]["criteria"]["c9_relief"]["target"] is None
    targets["polar"]["criteria"]["c9_relief"]["verified"] = True
    p.write_text(json.dumps(targets), encoding="utf-8")
    c9 = load_config(targets_path=p)["polar"]["criteria"]["c9_relief"]
    assert c9["target"] == 1234.0 and method(c9) == "target"
