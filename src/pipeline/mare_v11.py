"""mare-v1.1 scoring (15 Nov 2026): mare-v1 + c30 small-crater density + fair Mare twins.

mare-v1 (config `mare:`, lunar_targets.json["mare"] c9/c10/c12/c13) stays frozen and is the reference. mare-v1.1
adds, from config `mare_v11:`:
  - c30_small_craters (pipeline.mare.small_crater_density): lunar value = median over the same 20 mare cells,
    tolerance = max(IQR, mare_v11.c30_tolerance_floor), weight mare_v11.c30_weight (0 = display only).
  - common_tolerance: every Mare lunar target (20-cell median "mare_20cells" + the 4 maria in
    config/lunar_targets_candidates.json) is scored with the 20-cell median's tolerance per criterion.
    Why: with each target's own IQR, the 20-cell target (c9 tolerance 163 m, spread across 4 maria) is far
    more forgiving than a single mare (Imbrium c9 tolerance 42 m), so BEST_TARGET mostly picked the target with
    the widest tolerance, not the closest one. One tolerance per criterion = closeness to the lunar value only.
The scoring rule itself (exp(-((earth - moon) / tolerance)^2), weighted mean, complete-or-no-data for target
scores) is pipeline.scoring / pipeline.multi_target, unchanged.

c30 lunar values are "computed by Claude Code, to be checked by Mateo" (lunar_targets.json, candidates file).
"""
from __future__ import annotations

import copy

from pipeline import multi_target as mt
from pipeline.mare import C30, MARE_CRITERIA

V11_CRITERIA = (*MARE_CRITERIA, C30)


def c30_lunar(cfg: dict) -> dict | None:
    """The c30 entry of lunar_targets.json["mare"]["criteria"], or None."""
    return cfg["lunar_targets"].get("mare", {}).get("criteria", {}).get(C30)


def v11_criteria(cfg: dict, c30_weight: float | None = None) -> dict:
    """mare-v1.1 criteria for pipeline.scoring: the four mare-v1 criteria exactly as load_config built them
    (target, tolerance = max(IQR, floor), weight) + c30. c30_weight overrides the config (what-ifs)."""
    v = cfg["mare_v11"]
    crit = copy.deepcopy(cfg["mare"]["criteria"])
    lt = c30_lunar(cfg) or {}
    ok = lt.get("value") is not None and lt.get("iqr") is not None
    crit[C30] = {"weight": v["c30_weight"] if c30_weight is None else c30_weight, "direction": "target",
                 "target": lt["value"] if ok else None,
                 "tolerance": max(lt["iqr"], v["c30_tolerance_floor"]) if ok else None}
    if crit[C30]["tolerance"] == 0:
        crit[C30]["target"] = None                     # no spread and no floor: cannot score
    return crit


def v11_targets(cfg: dict, candidates: list[dict] | None = None, c30_weight: float | None = None,
                common_tolerance: bool | None = None) -> list[dict]:
    """Mare targets for multi_target.score: built-in 20-cell median + the verified maria from the candidates
    file. With common_tolerance (default: config), every target uses the 20-cell median's tolerance per
    criterion; else each target's own max(IQR, floor) (the mare-v1 export rule). A mare's c30 is used if the
    candidates file has a c30 value for it (to be checked by Mateo, like the 20-cell c30)."""
    common = cfg["mare_v11"]["common_tolerance"] if common_tolerance is None else common_tolerance
    base = v11_criteria(cfg, c30_weight)
    floors = {**cfg["mare"]["tolerance_floor"], C30: cfg["mare_v11"]["c30_tolerance_floor"]}
    cands = mt.load_candidates() if candidates is None else candidates
    out = [{"name": mt.BUILTIN["mare"], "column": mt.column(mt.BUILTIN["mare"]), "label": mt.BUILTIN_LABEL["mare"],
            "base_type": "mare", "builtin": True, "criteria": base, "required": mt.required(base)}]
    for t in cands:
        if t.get("base_type") != "mare" or t.get("skipped") or t.get("verified") is not True:
            continue
        crit = {}
        for name, bc in base.items():
            lt = (t.get("criteria") or {}).get(name) or {}
            value = mt._num(lt.get("value"))
            usable = value is not None and (lt.get("verified") is True or name == C30)
            own = mt._num(lt.get("iqr")) if name == C30 else mt._num(lt.get("tolerance"))
            tol = bc["tolerance"] if common else (None if own is None else max(own, floors[name]))
            crit[name] = {**bc, "target": value if usable and tol else None, "tolerance": tol}
        out.append({"name": t["name"], "column": mt.column(t["name"]), "label": t.get("label") or t["name"],
                    "base_type": "mare", "builtin": False, "criteria": crit, "required": mt.required(base)})
    return out
