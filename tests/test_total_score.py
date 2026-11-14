"""Total score = score vs Moon: only target-scored criteria with weight > 0 (team decision 14 Nov 2026).
Rank scores (run-relative; a run with 1 cell gives 0.5) and display-only criteria never enter it."""
import copy
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

from dem.grid import MetricGrid  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.polar import best_of, polar_candidates, select_best  # noqa: E402
from pipeline.scoring import method, rank_score, total_score  # noqa: E402

CFG = load_config()
CRIT = CFG["polar"]["criteria"]
RES, N = 60.0, 400


def _one_cell_run():
    """One cell with one bowl, Sun on (coarse steps for speed) -> c1-c4 exist and are rank-scored."""
    cfg = copy.deepcopy(CFG)
    cfg["light"].update(sun=True, step_min=360, n_azimuths=36)
    rr, cc = np.indices((N, N))
    x, y = (cc - N / 2 + 0.5) * RES, -(rr - N / 2 + 0.5) * RES
    r = np.hypot(x, y)
    z = np.where(r < 1500, 600 * (r ** 2 / 1500 ** 2 - 1), 0.0).astype(np.float32)
    mg = MetricGrid(z, from_origin(500_000 - N * RES / 2, 3_160_000, RES, RES), "EPSG:32645", RES)
    cell = (np.abs(rr - N / 2) < 125) & (np.abs(cc - N / 2) < 125)
    _, cands = polar_candidates(mg, cell, None, 28.5, cfg)
    select_best(cands, cfg["polar"]["criteria"])        # what run.py does across the whole run
    return best_of(cands), cfg["polar"]["criteria"]


def test_display_only_criteria_have_weight_zero():
    for c in ("c5_sky_view", "c9_relief", "c14_aspect"):
        assert CRIT[c]["weight"] == 0, c


def test_one_cell_run_rank_scores_do_not_enter_the_total():
    best, crit = _one_cell_run()
    rank_crit = [c for c in crit if method(crit[c]) == "rank" and crit[c]["weight"] > 0]
    assert set(rank_crit) >= {"c1_sunny_ridge", "c2_dark_floor", "c3_light_dark", "c4_grazing_sun"}
    assert all(best[f"s_{c}"] == 0.5 for c in rank_crit)              # 1 cell -> middle value
    in_total = [c for c in crit if method(crit[c]) == "target" and crit[c]["weight"] > 0]
    expect = sum(crit[c]["weight"] * best[f"s_{c}"] for c in in_total) / sum(crit[c]["weight"] for c in in_total)
    assert best["score"] == pytest.approx(expect, abs=1e-4)             # only target criteria
    assert best["n_scored"] == len(in_total)
    assert best["rank_score"] == pytest.approx(0.5) and best["n_ranked"] == len(rank_crit)


def test_total_ignores_rank_and_display_scores():
    best, crit = _one_cell_run()
    base = total_score(best, crit)[0]
    changed = dict(best)
    for c in crit:
        if method(crit[c]) != "target" or crit[c]["weight"] <= 0:       # rank, linear, display-only
            changed[f"s_{c}"] = 0.0 if (best.get(f"s_{c}") or 0) > 0.5 else 1.0
    assert total_score(changed, crit)[0] == pytest.approx(base)
    assert rank_score(changed, crit)[0] != pytest.approx(best["rank_score"])
