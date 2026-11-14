"""config-v1 freeze (14 Nov 2026): thresholds, weights, tolerances and lunar target values used for
scoring must not change after the git tag config-v1 (validation on Iceland and Devon Island runs on it).
If this test fails, do NOT update the snapshot silently: tell the team; a change means a new config
version (config-v2) and a new validation."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pipeline.config import load_config  # noqa: E402


def test_scoring_config_matches_config_v1():
    c = load_config()
    now = {
        "grid": c["grid"], "filter": c["filter"], "light": c["light"],
        "polar": {k: v for k, v in c["polar"].items() if k != "criteria"},
        "criteria": {k: {f: v.get(f) for f in ("weight", "direction", "scale", "tolerance", "target")}
                     for k, v in c["polar"]["criteria"].items()},
    }
    frozen = json.loads((ROOT / "tests" / "config_v1_snapshot.json").read_text(encoding="utf-8"))
    assert json.loads(json.dumps(now, sort_keys=True)) == frozen, "scoring config differs from config-v1"
