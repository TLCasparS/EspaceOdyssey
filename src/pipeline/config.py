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
    display = CONFIG_DIR / "display.yaml"                     # display-only parameters, outside the freeze
    cfg["display"] = yaml.safe_load(display.read_text(encoding="utf-8")) if display.exists() else {}
    if "polar" in cfg:
        crit, lunar = cfg["polar"]["criteria"], targets["polar"]["criteria"]
        if set(crit) != set(lunar):
            raise ValueError(f"criteria in pipeline.yaml {sorted(crit)} != lunar_targets.json {sorted(lunar)}")
        for name, ccfg in crit.items():
            t = lunar[name]
            # only values someone computed from the named source and marked verified are used
            ccfg["target"] = t["value"] if t.get("verified") and t.get("value") is not None else None
            if ccfg["target"] is not None and not ccfg.get("tolerance"):
                raise ValueError(f"{name}: verified lunar target but no tolerance in pipeline.yaml")
    if "mare" in cfg:                                         # Mare: target = median, tolerance from the IQR
        lm = targets.get("mare", {}).get("criteria", {})
        for name, ccfg in cfg["mare"]["criteria"].items():
            t = lm.get(name, {})
            ok = t.get("verified") and t.get("value") is not None and t.get("tolerance") is not None
            ccfg["target"] = t["value"] if ok else None
            ccfg["tolerance"] = max(t["tolerance"], cfg["mare"]["tolerance_floor"][name]) if ok else None
    return cfg
