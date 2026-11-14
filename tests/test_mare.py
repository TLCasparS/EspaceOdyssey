"""Mare criteria (src/pipeline/mare.py) on synthetic DEMs, Earth and Moon grids."""
import copy
import json
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
from pipeline.mare import MARE_CRITERIA, base_pad, has_bowl, mare_cell, target_from_cells  # noqa: E402

CFG = load_config()
RES, N = 60.0, 433                                    # 15 km cell + 2 x 5.5 km buffer
MOON = "+proj=stere +lat_0=-90 +lon_0=0 +R=1737400 +units=m +no_defs"


def _xy():
    rr, cc = np.indices((N, N))
    return (cc - N / 2 + 0.5) * RES, -(rr - N / 2 + 0.5) * RES


def _grid(z, crs="EPSG:32645"):
    return MetricGrid(z.astype(np.float32), from_origin(500_000 - N * RES / 2, 3_170_000, RES, RES), crs, RES)


def _cell():
    x, y = _xy()
    return (np.abs(x) < 7500) & (np.abs(y) < 7500)


def test_flat_plain():
    r = mare_cell(_grid(np.zeros((N, N))), _cell(), None, CFG)
    assert r["keep"] and r["c10_flat_base"] == pytest.approx(0, abs=1e-6)
    assert r["c9_relief"] == pytest.approx(0, abs=1e-6) and r["c12_drivable"] == pytest.approx(1.0)
    assert r["c13_roughness"] == pytest.approx(0, abs=1e-3)
    assert (r["base_row"], r["base_col"]) in [(216, 216), (216, 217), (217, 216), (217, 217)]   # ties -> centre


def test_tilted_plane_relief_and_slope():
    x, y = _xy()
    r = mare_cell(_grid(0.05 * x), _cell(), None, CFG)                   # 2.86 deg everywhere
    assert r["c10_flat_base"] == pytest.approx(math.degrees(math.atan(0.05)), abs=0.05)
    assert r["c9_relief"] == pytest.approx(0.05 * 10_000, rel=0.03)      # 10 km across the 5 km circle
    assert r["c12_drivable"] == pytest.approx(1.0)


def test_steep_terrain_dropped_and_drivable_share():
    x, y = _xy()
    r = mare_cell(_grid(0.4 * x), _cell(), None, CFG)                    # 21.8 deg
    assert not r["keep"] and r["reason"].startswith("base-spot slope")
    assert r["c12_drivable"] == pytest.approx(0.0)


def test_base_pad_must_be_usable():
    x, y = _xy()
    z = np.where(x < 0, 0.0, 0.3 * x)                                    # flat west half, 16.7 deg east half
    usable = x > 0
    r, c, s = base_pad(np.full((N, N), 0.0), _cell(), usable, RES, 200)
    assert usable[r, c]
    res = mare_cell(_grid(z), _cell(), usable, CFG)
    assert res["base_col"] > N / 2 and not res["keep"]                   # only the steep half is usable


def test_moon_grid_works_and_bowl_detector():
    x, y = _xy()
    rad = np.hypot(x, y)
    bowl = np.where(rad < 3000, 1000 * (rad ** 2 / 9e6 - 1), 0.0)
    assert has_bowl(_grid(bowl, MOON), _cell(), CFG)
    assert not has_bowl(_grid(np.zeros((N, N)), MOON), _cell(), CFG)
    r = mare_cell(_grid(np.zeros((N, N)), MOON), _cell(), None, CFG)
    assert r["keep"] and r["c12_drivable"] == pytest.approx(1.0)


def test_target_from_cells_median_iqr_floor():
    floors = CFG["mare"]["tolerance_floor"]
    vals = {"c9_relief": [10, 20, 30, 40, 50, None], "c10_flat_base": [0.1, 0.1, 0.1, 0.1]}
    t = target_from_cells(vals, floors, cells=["a", "b"], seed=42)
    assert t["c9_relief"]["value"] == 30 and t["c9_relief"]["iqr"] == 20 and t["c9_relief"]["n_cells"] == 5
    assert t["c9_relief"]["tolerance"] == max(20, floors["c9_relief"])
    assert t["c10_flat_base"]["iqr"] == 0 and t["c10_flat_base"]["tolerance"] == floors["c10_flat_base"]   # floor
    assert t["c9_relief"]["seed"] == 42 and t["c9_relief"]["cells"] == ["a", "b"]


def test_config_loader_uses_verified_mare_targets(tmp_path):
    from pipeline.config import TARGETS_PATH
    targets = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))
    assert set(targets["mare"]["criteria"]) == set(MARE_CRITERIA) == set(CFG["mare"]["criteria"])
    # the loader passes a value through only when verified (independent of what the file holds today)
    for c in MARE_CRITERIA:
        targets["mare"]["criteria"][c]["verified"] = False
    p0 = tmp_path / "unverified.json"
    p0.write_text(json.dumps(targets), encoding="utf-8")
    assert all(load_config(targets_path=p0)["mare"]["criteria"][c]["target"] is None for c in MARE_CRITERIA)
    targets["mare"]["criteria"]["c10_flat_base"].update(value=0.8, tolerance=0.1, verified=True, source="test")
    p = tmp_path / "t.json"
    p.write_text(json.dumps(targets), encoding="utf-8")
    c10 = load_config(targets_path=p)["mare"]["criteria"]["c10_flat_base"]
    assert c10["target"] == 0.8 and c10["tolerance"] == CFG["mare"]["tolerance_floor"]["c10_flat_base"]   # floor wins
