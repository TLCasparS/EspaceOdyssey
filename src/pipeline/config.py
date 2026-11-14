"""Load config/pipeline.yaml (thresholds, weights) and config/lunar_targets.json (lunar reference values)."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
DEFAULT_PATH = CONFIG_DIR / "pipeline.yaml"
TARGETS_PATH = CONFIG_DIR / "lunar_targets.json"


def load_config(path: str | Path | None = None, targets_path: str | Path | None = None) -> dict:
    with open(path or DEFAULT_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    with open(targets_path or TARGETS_PATH, encoding="utf-8") as f:
        targets = json.load(f)
    cfg["lunar_targets"] = targets
    if "polar" in cfg:
        crit, lunar = cfg["polar"]["criteria"], targets["polar"]["criteria"]
        if set(crit) != set(lunar):
            raise ValueError(f"criteria in pipeline.yaml {sorted(crit)} != lunar_targets.json {sorted(lunar)}")
        for name, ccfg in crit.items():
            t = lunar[name]
            # only values someone computed from the named source and marked verified are used
            ccfg["target"] = t["value"] if t.get("verified") and t.get("value") is not None else None
    return cfg
