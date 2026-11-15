"""mare-v1.1: c30 small-crater density (pipeline.mare.small_crater_density) and fair Mare twins
(pipeline.mare_v11) on synthetic plains."""
import copy
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline import multi_target as mt  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.mare import C30, small_crater_density  # noqa: E402
from pipeline.mare_v11 import v11_criteria, v11_targets  # noqa: E402
from pipeline.scoring import score_direct, total_score  # noqa: E402

CFG = load_config()
P = CFG["mare_v11"]["c30"]
RES, N = 60.0, 301
BASE = (N // 2, N // 2)
DISC_KM2 = None                                      # data-covered disc area, filled below


def _plain(seed=0):
    """Flat mare-like plain: 0.1 % regional tilt + spatially smooth 0.3 m noise (white noise would make the
    fill of a pit spill into countless one-pixel hollows, which real DEMs do not show)."""
    from scipy import ndimage
    rng = np.random.default_rng(seed)
    noise = ndimage.gaussian_filter(rng.normal(0, 1, (N, N)), 3)
    _, cc = np.indices((N, N))
    return 0.001 * cc * RES + 0.3 * noise / noise.std()


def _pit(z, dx_km, dy_km, depth=20.0, diam_m=600.0):
    """Bowl-shaped pit (cosine profile) centred dx, dy km from the base spot."""
    rr, cc = np.indices(z.shape)
    d = np.hypot((cc - BASE[1]) * RES - dx_km * 1000, (rr - BASE[0]) * RES - dy_km * 1000)
    r = diam_m / 2
    return z - np.where(d < r, depth * 0.5 * (1 + np.cos(np.pi * d / r)), 0.0)


def _area_km2():
    rr, cc = np.indices((N, N))
    return float((np.hypot(rr - BASE[0], cc - BASE[1]) * RES <= P["radius_km"] * 1000).sum() * RES ** 2 / 1e6)


def test_plain_without_pits_is_zero():
    assert small_crater_density(_plain(), BASE, RES, P) == 0


def test_plain_with_pits_counts_them_per_km2():
    z = _plain()
    for dx, dy in [(0, 2), (2, 0), (-3, -1), (1.5, -3.5)]:
        z = _pit(z, dx, dy)
    assert small_crater_density(z, BASE, RES, P) == pytest.approx(4 / _area_km2(), rel=1e-3)


def test_size_shape_and_distance_limits():
    z = _plain()
    z = _pit(z, 0, 2)                                   # counts
    z = _pit(z, 6.0, 0)                                 # low point outside 5 km: not counted
    z = _pit(z, -2, 0, depth=5.0)                       # too shallow (< 10 m)
    z = _pit(z, 0, -2, diam_m=200.0)                    # too narrow (< 300 m)
    rr, cc = np.indices(z.shape)                        # elongated trench, 2.4 km x 0.36 km: not a crater
    x, y = (cc - BASE[1]) * RES, (rr - BASE[0]) * RES
    trench = (np.abs(x - 3000) < 180) & (np.abs(y - 2500) < 1200)
    z = np.where(trench, z - 20 * np.cos(np.pi * (x - 3000) / 360) ** 2, z)
    assert small_crater_density(z, BASE, RES, P) == pytest.approx(1 / _area_km2(), rel=1e-3)


def test_missing_data_is_none_never_zero():
    z = _plain()
    z[:, : N // 2 + 10] = np.nan                       # more than half of the 5 km disc without data
    assert small_crater_density(z, BASE, RES, P) is None


def test_density_uses_covered_area_only():
    z = _pit(_plain(), 0, 2)
    z2 = z.copy()
    z2[: N // 2 - 40, :] = np.nan                       # remove part of the disc away from the pit
    full, part = small_crater_density(z, BASE, RES, P), small_crater_density(z2, BASE, RES, P)
    assert part is not None and part > full            # same single pit, smaller covered area


def test_independent_of_base_position_in_window():
    """Same terrain around the base spot, base spot near a window edge -> same density (window cut to
    radius + margin around the base spot)."""
    z = _pit(_pit(_plain(), 1, 1), -2, 3)
    big = np.pad(z, ((0, 0), (0, 150)), constant_values=0.0)
    assert small_crater_density(big, BASE, RES, P) == small_crater_density(z, BASE, RES, P)


# --- fair Mare twins -----------------------------------------------------------------------------------------

def _cfg_with_c30(weight=1.0, floor=0.01):
    cfg = copy.deepcopy(CFG)
    cfg["mare_v11"].update(c30_weight=weight, c30_tolerance_floor=floor)
    cfg["lunar_targets"]["mare"]["criteria"][C30] = {"value": 0.05, "iqr": 0.02, "verified": False}
    return cfg


def _cands():
    crit = {"c9_relief": {"value": 120.0, "tolerance": 42.0, "verified": True},
            "c10_flat_base": {"value": 0.23, "tolerance": 0.5, "verified": True},
            "c12_drivable": {"value": 0.998, "tolerance": 0.05, "verified": True},
            "c13_roughness": {"value": 1.7, "tolerance": 1.0, "verified": True},
            C30: {"value": 0.04, "iqr": 0.01, "verified": False}}
    return [{"name": "mare_x", "base_type": "mare", "verified": True, "criteria": crit}]


def test_common_tolerance_uses_the_20_cell_tolerance_for_every_target():
    cfg = _cfg_with_c30()
    base, x = v11_targets(cfg, _cands())
    for k, cc in x["criteria"].items():
        assert cc["tolerance"] == base["criteria"][k]["tolerance"]
    _, own = v11_targets(cfg, _cands(), common_tolerance=False)
    assert own["criteria"]["c9_relief"]["tolerance"] == 42.0
    assert own["criteria"][C30]["tolerance"] == 0.01   # max(iqr 0.01, floor 0.01)


def test_common_tolerance_best_target_is_the_closest():
    """A place exactly at the narrow-tolerance target's values must have that target as BEST under the
    common tolerance."""
    cfg = _cfg_with_c30()
    tg = v11_targets(cfg, _cands())
    raw = {k: v["value"] for k, v in _cands()[0]["criteria"].items()}
    sc = {t["name"]: mt.score(raw, t) for t in tg}
    assert mt.best(sc)[0] == "mare_x" and sc["mare_x"] == pytest.approx(1.0)


def test_c30_weight_zero_keeps_the_mare_v1_total():
    cfg = _cfg_with_c30(weight=0.0)
    raw = {"c9_relief": 150.0, "c10_flat_base": 0.3, "c12_drivable": 0.99, "c13_roughness": 1.9, C30: 0.2}
    old, new = CFG["mare"]["criteria"], v11_criteria(cfg)
    so = total_score({f"s_{k}": score_direct(raw[k], old[k]) for k in old}, old)[0]
    sn = total_score({f"s_{k}": score_direct(raw[k], new[k]) for k in new}, new)[0]
    assert so == sn


def test_missing_c30_never_wins_best_target():
    cfg = _cfg_with_c30()
    tg = v11_targets(cfg, _cands())
    raw = {"c9_relief": 150.0, "c10_flat_base": 0.3, "c12_drivable": 0.99, "c13_roughness": 1.9, C30: None}
    assert all(mt.score(raw, t) is None for t in tg)
