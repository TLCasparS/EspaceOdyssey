"""Score stored raw values against SEVERAL lunar targets per base type ("closest lunar twin").

Night Task 3 (docs/AGENTS_NIGHT_GUIDE.md, docs/MULTI_TARGET.md). Reads only stored raw values (out/<run>/ranking.csv
or the night run's raw/<track>/*.jsonl records) plus targets; no DEM reads, no change to existing scoring:
the per-criterion rule and the total are pipeline.scoring.score_direct / total_score, unchanged.

Targets
    built-in   today's target per base type, exactly as the run was scored (config/lunar_targets.json via
               pipeline.yaml / radar.json): Polar "shackleton", Mare "mare_20cells".
    candidates config/lunar_targets_candidates.json (optional, written by Task 5):
               {"targets": [{"name", "label", "base_type", "verified", "skipped",
                             "criteria": {<criterion>: {"value", "verified", "tolerance"?, "source", "date"}}}]}
               Real scoring uses a candidate only if the TARGET has verified = true, and within it only criteria
               with verified = true. include_unverified=True (preview) uses every non-skipped target and every
               criterion with a value; outputs are then marked as preview.
Weights per base type are the run's / config's (same as today). Tolerance: the target's own if it has one
(Mare: max(own, mare.tolerance_floor), the same rule config.load_config applies to the built-in Mare target),
else the base type's tolerance from config (Polar). A Mare criterion without its own tolerance is not scored.
Missing values never score better than real ones (15 Nov 2026): a score against a target is only given when
EVERY counting criterion of the base type (weight > 0, scored against today's target) has both a usable lunar value
and an Earth value. Otherwise that score is None (no data, never 0), so a target with gaps, or a place with gaps,
can never win BEST_TARGET by being scored on fewer, easier criteria. (SCORE_TOTAL itself keeps the frozen
config-v1 / mare-v1 rule; with complete data the built-in score equals it.)

CLI (night run, after --score; or any ranking.csv):
    python src/pipeline/multi_target.py out/night_polar/ranking.csv out/night_mare/ranking.csv -o out/multi_target.csv
    python src/pipeline/multi_target.py --raw %LOCALAPPDATA%/espaceodyssey_night/raw/A --base polar -o out/mt_polar.csv
"""
from __future__ import annotations

import copy
import json
import math
import re
import sys
from pathlib import Path

if __name__ == "__main__":                             # run as a script: make `pipeline` importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pipeline.scoring import method, score_direct, total_score

CANDIDATES_PATH = Path(__file__).resolve().parents[2] / "config" / "lunar_targets_candidates.json"
BUILTIN = {"polar": "shackleton", "mare": "mare_20cells"}
BUILTIN_LABEL = {"polar": "Shackleton rim + floor (config/lunar_targets.json)",
                 "mare": "Mare median over 20 cells (config/lunar_targets.json)"}
RESERVED = {"TOTAL"}                                   # SCORE_TOTAL already exists in scores.csv / ranking.csv


def column(name: str) -> str:
    """Target name -> scores.csv column, e.g. polar_site01 -> SCORE_POLAR_SITE01."""
    key = re.sub(r"[^A-Z0-9]+", "_", str(name).upper()).strip("_")
    if not key or key in RESERVED:
        raise ValueError(f"target name {name!r} gives an invalid column SCORE_{key}")
    return f"SCORE_{key}"


def _num(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def load_candidates(path: str | Path | None = None) -> list[dict]:
    """Entries of config/lunar_targets_candidates.json; [] if the file does not exist."""
    p = Path(path) if path else CANDIDATES_PATH
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return list(data.get("targets", []))


def required(base_ccfg: dict) -> list[str]:
    """Counting criteria of a base type: weight > 0 and scored against today's target (method 'target')."""
    return [c for c, cc in base_ccfg.items() if (cc.get("weight") or 0) > 0 and method(cc) == "target"]


def build_targets(base_criteria: dict, candidates: list[dict], include_unverified: bool = False,
                  tolerance_floor: dict | None = None) -> list[dict]:
    """Built-in + candidate targets for the base types in base_criteria.

    base_criteria: {base: {criterion: ccfg}}; ccfg as used by pipeline.scoring (weight, target, tolerance,
        direction / scale) for today's target, i.e. config["polar"]["criteria"] after load_config or the axes
        of a run's radar.json.
    tolerance_floor: {base: {criterion: floor}} (config mare.tolerance_floor), applied to targets' own tolerances.
    Returns [{name, column, label, base_type, builtin, verified, preview, criteria: {crit: ccfg}, required,
    complete, source}]; required = the base type's counting criteria, complete = the target has a usable value
    for all of them.
    """
    floors = tolerance_floor or {}
    out = []
    for base, crit in base_criteria.items():
        out.append({"name": BUILTIN[base], "column": column(BUILTIN[base]), "label": BUILTIN_LABEL[base],
                    "base_type": base, "builtin": True, "verified": True, "preview": False,
                    "criteria": copy.deepcopy(crit), "required": required(crit), "complete": True,
                    "source": "config/lunar_targets.json"})
    for t in candidates:
        base = t.get("base_type")
        if base not in base_criteria or t.get("skipped"):
            continue
        t_ok = t.get("verified") is True
        if not (t_ok or include_unverified):
            continue
        lunar = t.get("criteria") or {}
        crit = {}
        for name, base_ccfg in base_criteria[base].items():
            lt = lunar.get(name) or {}
            value = _num(lt.get("value"))
            usable = value is not None and (include_unverified or (t_ok and lt.get("verified") is True))
            own = _num(lt.get("tolerance"))
            if own is not None:
                tol = max(own, floors.get(base, {}).get(name, own))
            elif base == "mare":
                tol = None                              # Mare targets carry their own (IQR-based) tolerance
            else:
                tol = base_ccfg.get("tolerance")
            ccfg = dict(base_ccfg)
            ccfg["target"] = value if usable and tol else None
            ccfg["tolerance"] = tol
            crit[name] = ccfg
        out.append({"name": t["name"], "column": column(t["name"]), "label": t.get("label") or t["name"],
                    "base_type": base, "builtin": False, "verified": t_ok, "preview": not t_ok or any(
                        (lunar.get(c) or {}).get("verified") is not True and crit[c]["target"] is not None
                        for c in crit),
                    "criteria": crit, "required": required(base_criteria[base]),
                    "complete": all(method(crit[c]) == "target" for c in required(base_criteria[base])),
                    "source": "config/lunar_targets_candidates.json"})
    cols = [t["column"] for t in out]
    dup = sorted({c for c in cols if cols.count(c) > 1})
    if dup:
        raise ValueError(f"lunar target names collide in scores.csv columns: {dup}")
    return out


def common_tolerance(targets: list[dict], base: str) -> list[dict]:
    """Fair twins (team decision 15 Nov 2026, docs/MARE_V11.md): every non-built-in target of `base` is scored with
    the BUILT-IN target's tolerance per criterion (Mare: the 20-cell median's), so BEST_TARGET compares closeness to
    the lunar values, not tolerance width. Lunar values and the built-in target (= SCORE_TOTAL) are unchanged.
    In place; returns targets."""
    ref = next((t for t in targets if t["builtin"] and t["base_type"] == base), None)
    if ref is None:
        return targets
    for t in targets:
        if t["base_type"] != base or t["builtin"]:
            continue
        for name, cc in t["criteria"].items():
            tol = (ref["criteria"].get(name) or {}).get("tolerance")
            cc["tolerance"] = tol
            if not tol:
                cc["target"] = None
        t["complete"] = all(method(t["criteria"][c]) == "target" for c in t["required"])
        t["common_tolerance"] = True
    return targets


def score(raw: dict, target: dict) -> float | None:
    """Score vs Moon of one place's raw values against one target (same rule and rounding as the pipeline).

    None (no data) if any counting criterion (target["required"]) lacks a lunar value or an Earth value."""
    for name in target.get("required", ()):
        cc = target["criteria"].get(name)
        if cc is None or method(cc) != "target" or _num(raw.get(name)) is None:
            return None
    s = {}
    for name, ccfg in target["criteria"].items():
        if method(ccfg) != "target":
            continue
        v = score_direct(_num(raw.get(name)), ccfg)
        s[f"s_{name}"] = None if v is None else round(v, 4)
    return total_score(s, target["criteria"])[0]


def best(scores: dict[str, float | None]) -> tuple[str | None, float | None]:
    """(name, score) of the highest score; ties keep the first target (built-in first). (None, None) if none."""
    name, top = None, None
    for k, v in scores.items():
        if v is not None and (top is None or v > top):
            name, top = k, v
    return name, top


def score_row(raw: dict, base: str, targets: list[dict]) -> dict:
    """{SCORE_<X>: score for every target of this base type, BEST_TARGET: name, BEST_SCORE}."""
    mine = [t for t in targets if t["base_type"] == base]
    by_name = {t["name"]: score(raw, t) for t in mine}
    out = {t["column"]: by_name[t["name"]] for t in mine}
    out["BEST_TARGET"], out["BEST_SCORE"] = best(by_name)
    return out


def score_records(recs: list[dict], base: str, targets: list[dict]) -> list[dict]:
    """Night-run raw records (raw/<track>/*.jsonl) -> one row per cell with a scorable place.

    Polar: per target the BEST valid candidate place of the cell (a different target may prefer a different
    bowl in the same cell); PLACE_<X> = index of that candidate in rec["cands"]. Mare: the cell's one result."""
    mine = [t for t in targets if t["base_type"] == base]
    rows = []
    for r in recs:
        cell = r["cell"]
        row = {"id": cell["id"], "lat": _num(cell.get("lat")), "lon": _num(cell.get("lon"))}
        if base == "polar":
            cands = [(i, c) for i, c in enumerate(r.get("cands") or []) if c.get("keep")]
            if not cands:
                continue
            by_name = {}
            for t in mine:
                sc = [(score(c, t), i) for i, c in cands]
                sc = [x for x in sc if x[0] is not None]
                top = max(sc, key=lambda x: (x[0], -x[1])) if sc else (None, None)
                by_name[t["name"]] = top[0]
                row[t["column"]] = top[0]
                row["PLACE_" + t["column"][6:]] = top[1]
        else:
            res = r.get("res")
            if not res or not res.get("keep"):
                continue
            by_name = {t["name"]: score(res, t) for t in mine}
            row.update({t["column"]: by_name[t["name"]] for t in mine})
        row["BEST_TARGET"], row["BEST_SCORE"] = best(by_name)
        rows.append(row)
    return rows


def targets_summary(targets: list[dict]) -> list[dict]:
    """JSON-ready list for outputs/targets.json: per target its lunar values, tolerances and weights."""
    out = []
    for t in targets:
        out.append({"name": t["name"], "column": t["column"], "label": t["label"], "base_type": t["base_type"],
                    "builtin": t["builtin"], "verified": t["verified"], "preview": t["preview"], "source": t["source"],
                    "complete": t.get("complete", True),
                    "criteria": {c: {"value": cc.get("target"), "tolerance": cc.get("tolerance"),
                                     "weight": cc.get("weight")}
                                 for c, cc in t["criteria"].items()
                                 if method(cc) == "target" and cc.get("weight", 0) > 0}})
    return out


def main(argv=None):
    import argparse
    import csv
    from pipeline.config import load_config

    ap = argparse.ArgumentParser(description="Score stored raw values against several lunar targets.")
    ap.add_argument("ranking", nargs="*", type=Path, help="out/<run>/ranking.csv (base type from the radar.json next to it)")
    ap.add_argument("--raw", type=Path, help="night run raw/<track> folder with *.jsonl records")
    ap.add_argument("--base", choices=sorted(BUILTIN), help="base type of --raw records")
    ap.add_argument("--candidates", type=Path, default=CANDIDATES_PATH)
    ap.add_argument("--include-unverified", action="store_true", help="PREVIEW: also unverified targets / criteria")
    ap.add_argument("-o", "--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if bool(a.raw) != bool(a.base):
        ap.error("--raw needs --base")
    cfg = load_config()
    base_crit = {b: cfg[b]["criteria"] for b in BUILTIN if b in cfg}
    targets = build_targets(base_crit, load_candidates(a.candidates), a.include_unverified,
                            {"mare": cfg.get("mare", {}).get("tolerance_floor", {})})
    preview = any(t["preview"] for t in targets)
    rows = []
    for p in a.ranking:
        base = json.loads((p.parent / "radar.json").read_text(encoding="utf-8"))["base_type"]
        with open(p, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows.append({"run": p.parent.name, "id": r["id"], "base_type": base, "lat": r.get("lat"),
                             "lon": r.get("lon"), "score": r.get("score"), **score_row(r, base, targets)})
    if a.raw:
        recs = []
        for path in sorted(a.raw.glob("*.jsonl")):
            with open(path, encoding="utf-8") as f:
                recs += [json.loads(line) for line in f if line.strip()]
        rows += [{"run": a.raw.name, "base_type": a.base, **r} for r in score_records(recs, a.base, targets)]
    cols = ["run", "id", "base_type", "lat", "lon", "score", *[t["column"] for t in targets],
            *[k for k in dict.fromkeys(k for r in rows for k in r) if k.startswith("PLACE_")],
            "BEST_TARGET", "BEST_SCORE", "PREVIEW"]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({**{k: ("" if v is None else v) for k, v in r.items()}, "PREVIEW": 1 if preview else ""})
    print(f"{len(rows)} rows x {len(targets)} targets -> {a.out}" + ("  [PREVIEW: unverified targets]" if preview else ""))
    off = [r["id"] for r in rows if _num(r.get("score")) is not None and r.get(column(BUILTIN[r["base_type"]])) is not None
           and abs(_num(r["score"]) - r[column(BUILTIN[r["base_type"]])]) > 2e-4]
    if off:
        print(f"NOTE: {len(off)} rows: today's target re-scored with the CURRENT config != the stored score "
              f"(e.g. {off[:3]}); the run was scored with another config")


if __name__ == "__main__":
    main()
