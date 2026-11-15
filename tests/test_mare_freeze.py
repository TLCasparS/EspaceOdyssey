"""mare-v1 freeze (14 Nov 2026): the Mare config section and the Mare lunar targets used for scoring must not
change after the git tag mare-v1 (night run and Mare validation run on it). If this fails, do NOT update the
snapshot silently: tell the team; a change means mare-v2 and a new validation.

Display additions (15 Nov 2026, no mare-v1.1) ADD c30_small_craters to lunar_targets.json["mare"]["criteria"] and a separate
`mare_v11:` config section; both are outside this guard. The four mare-v1 criteria stay fully guarded here."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pipeline.config import TARGETS_PATH, load_config  # noqa: E402
from pipeline.mare import C30, MARE_CRITERIA  # noqa: E402


def test_mare_config_and_targets_match_mare_v1():
    c = load_config()
    t = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))["mare"]
    now = {"mare": {k: v for k, v in c["mare"].items() if k != "criteria"},
           "criteria": {k: {f: v.get(f) for f in ("weight", "direction", "target", "tolerance")}
                        for k, v in c["mare"]["criteria"].items()},
           "lunar": {"seed": t.get("seed"), "n_cells": len(t.get("cells") or []),
                     "criteria": {k: {f: v.get(f) for f in ("value", "tolerance", "iqr", "n_cells", "verified")}
                                  for k, v in t["criteria"].items() if k in MARE_CRITERIA}}}
    frozen = json.loads((ROOT / "tests" / "mare_v1_snapshot.json").read_text(encoding="utf-8"))
    assert json.loads(json.dumps(now, sort_keys=True)) == frozen, "Mare config or lunar targets differ from mare-v1"


def test_mare_v11_c30_is_additive_and_marked_unchecked():
    t = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))["mare"]["criteria"]
    assert set(t) == set(MARE_CRITERIA) | {C30}
    assert t[C30]["verified"] is False and "to be checked by Mateo" in t[C30]["check"]
    assert C30 not in load_config()["mare"]["criteria"]             # never in the mare-v1 score
