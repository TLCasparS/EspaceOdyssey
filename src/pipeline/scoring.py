"""Raw criterion values -> 0-1 scores -> one weighted score per cell. Rules come from the config.

Per criterion (config `polar.criteria.<name>`):
    scale [a, b]           "linear": direct, independent of other cells
    target set             "target": exp(-((raw - target) / tolerance)^2), checked first
    direction higher/lower "rank":   percentile rank among the surviving cells of this run;
                                     only comparable WITHIN one run
    direction target, no target -> None ("no data"), e.g. roughness until LOLA values exist
None never counts as 0: the weighted score uses only the criteria that have a score, with
their weights renormalised (interpreted from "missing data shows as no data, never 0").
"""
from __future__ import annotations

import numpy as np




def method(ccfg: dict) -> str:
    if ccfg.get("target") is not None:                # verified lunar value wins over scale / rank
        return "target"
    if ccfg.get("scale") is not None:
        return "linear"
    if ccfg.get("direction") in ("higher", "lower"):
        return "rank"
    return "none"


def score_direct(raw, ccfg: dict):
    """Score that needs no other cells; None for rank (filled by apply_rank) and for no data."""
    if raw is None:
        return None
    m = method(ccfg)
    if m == "linear":
        a, b = ccfg["scale"]
        s = (raw - a) / (b - a)
        s = 1 - s if ccfg["direction"] == "lower" else s
        return float(np.clip(s, 0.0, 1.0))
    if m == "target":
        # team choice 14 Nov 2026: Gaussian similarity, tolerance per criterion (pipeline.yaml);
        # 1 at the lunar value, 0.37 at one tolerance away, 0.02 at two
        return float(np.exp(-((raw - ccfg["target"]) / ccfg["tolerance"]) ** 2))
    return None


def scoring_note(criteria: dict) -> str:
    """One line for the outputs: which scoring the criteria of this run use."""
    ms = {name: method(c) for name, c in criteria.items()}
    parts = ["target = similarity to the lunar value, exp(-((earth - moon) / tolerance)^2), comparable across runs"
             if "target" in ms.values() else None,
             "rank = percentile among the candidate places of THIS run only" if "rank" in ms.values() else None,
             "linear = fixed scale" if "linear" in ms.values() else None,
             "none = no score yet (null = no data, not 0)" if "none" in ms.values() else None]
    in_total = [k for k, c in criteria.items() if ms[k] == "target" and c["weight"] > 0]
    return ("; ".join(x for x in parts if x)
            + f". TOTAL score (vs Moon) = weighted mean of target-scored criteria with weight > 0 only: {', '.join(in_total) or 'none'}"
            + ". rank_score (within run) is shown separately and never enters the total"
            + ". Methods: " + ", ".join(f"{k} {v} (w {criteria[k]['weight']:g})" for k, v in ms.items()))


def percentile_ranks(values: list[float]) -> list[float]:
    """0 = lowest, 1 = highest; ties share their average rank; a single value gets 0.5."""
    v = np.asarray(values, float)
    if v.size == 1:
        return [0.5]
    order = v.argsort(kind="mergesort")
    ranks = np.empty(v.size)
    ranks[order] = np.arange(v.size)
    for u in np.unique(v):                           # average ranks of ties
        tie = v == u
        ranks[tie] = ranks[tie].mean()
    return list(ranks / (v.size - 1))


def apply_rank(rows: list[dict], criteria: dict) -> None:
    """Fill s_<name> for rank-method criteria, over the rows that are kept and have a raw value."""
    for name, ccfg in criteria.items():
        if method(ccfg) != "rank":
            continue
        idx = [i for i, r in enumerate(rows) if r.get("keep") and r.get(name) is not None]
        if not idx:
            continue
        pr = percentile_ranks([rows[i][name] for i in idx])
        for i, p in zip(idx, pr):
            rows[i][f"s_{name}"] = round(p if ccfg["direction"] == "higher" else 1 - p, 4)


def weighted_score(row: dict, criteria: dict, methods=("target",)):
    """(score, n). Weighted mean of s_<name> over criteria whose method is in `methods`, weight > 0
    and a score present; weights renormalised over those. None if none qualify.

    The TOTAL score ("score vs Moon") uses methods=("target",) only (team decision 14 Nov 2026):
    rank scores depend on the other cells of the run (a run with 1 cell gives 0.5) and linear
    scales are not a lunar comparison, so neither may enter the total. Weight-0 criteria (display
    only: c5, c9, c14) never count, not even in n."""
    num = den = 0.0
    n = 0
    for name, ccfg in criteria.items():
        s = row.get(f"s_{name}")
        if s is None or ccfg["weight"] <= 0 or method(ccfg) not in methods:
            continue
        num += ccfg["weight"] * s
        den += ccfg["weight"]
        n += 1
    return (round(num / den, 4) if den > 0 else None), n


def total_score(row: dict, criteria: dict):
    """(score vs Moon, n): target-scored criteria only."""
    return weighted_score(row, criteria, ("target",))


def rank_score(row: dict, criteria: dict):
    """(rank score within run, n): rank-scored criteria only, shown separately, never in the total."""
    return weighted_score(row, criteria, ("rank",))
