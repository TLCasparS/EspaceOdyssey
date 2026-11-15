"""What-if for the PROPOSED Mare criterion c23 basalt (mare-v1.1, post-run addition). Proposal only:
changes no config, no score, no export. Prints a Markdown table and writes data/material/mare_c23_whatif_<variant>_w<weight>_t<tol>.csv.

    c23 raw   = share of GLiM "vb" (basic volcanic rocks) within 5 km of the base spot (rock_classes.csv);
                no data if GLiM covers less than --min-covered of the 5 km disc (coastal grid cells are sea)
    Moon      = 1.0 (mare = basalt plain)
    s_c23     = exp(-((raw - 1.0) / tolerance)^2)       same rule as every target-scored criterion
    new score = (sum w_i s_i + w23 s_c23) / (sum w_i + w23); c23 no data -> left out (weights renormalised)
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MARE_AXES = ["c9_relief", "c10_flat_base", "c12_drivable", "c13_roughness"]   # all weight 1.0 in mare-v1


def new_scores(mare: pd.DataFrame, rock: pd.DataFrame, weight: float, tol: float, min_covered: float = 0.5) -> pd.DataFrame:
    rk = rock[rock.run == "mare"][["cell", "ROCK_CLASS", "covered_share", "share_vb"]].rename(columns={"cell": "id"})
    d = mare.merge(rk, on="id", how="left")
    d["share_vb"] = pd.to_numeric(d["share_vb"], errors="coerce")
    d.loc[pd.to_numeric(d.covered_share, errors="coerce").fillna(0) < min_covered, "share_vb"] = float("nan")
    d["s_c23"] = [None if pd.isna(v) else round(math.exp(-((v - 1.0) / tol) ** 2), 4) for v in d.share_vb]
    num = sum(d[f"s_{c}"].fillna(0) for c in MARE_AXES)
    den = sum(d[f"s_{c}"].notna().astype(float) for c in MARE_AXES)
    has = d.s_c23.notna()
    d["score_new"] = ((num + has * weight * d.s_c23.fillna(0).astype(float)) / (den + has * weight)).round(4)
    d["rank_new"] = d.score_new.rank(ascending=False, method="first").astype(int)
    return d.sort_values("rank_new")


def md_table(d: pd.DataFrame, n=20) -> str:
    lines = ["| new rank | old rank | cell | lon | lat | rock class | vb share 5 km | old score | s_c23 | new score |",
             "|---:|---:|---|---:|---:|---|---:|---:|---:|---:|"]
    for _, r in d.head(n).iterrows():
        vb = "no data" if pd.isna(r.share_vb) else f"{r.share_vb:.2f}"
        s23 = "no data" if pd.isna(r.s_c23) else f"{r.s_c23:.3f}"
        lines.append(f"| {r.rank_new} | {int(r['rank'])} | {r.id} | {r.lon:.3f} | {r.lat:.3f} | "
                     f"{r.ROCK_CLASS if isinstance(r.ROCK_CLASS, str) and r.ROCK_CLASS else 'no data'} | {vb} | "
                     f"{r.score:.4f} | {s23} | {r.score_new:.4f} |")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-root", default=str(ROOT / "out"))
    ap.add_argument("--rock", default=str(ROOT / "data" / "material" / "rock_classes.csv"))
    ap.add_argument("--weight", type=float, default=1.0)
    ap.add_argument("--tolerance", type=float, default=0.5)
    ap.add_argument("--min-covered", type=float, default=0.5)
    ap.add_argument("--only-with-c23", action="store_true",
                    help="variant B: rank only cells that have a c23 value (no-data cells listed apart)")
    a = ap.parse_args(argv)
    mare = pd.read_csv(Path(a.out_root) / "night_mare" / "ranking.csv")
    rock = pd.read_csv(a.rock, keep_default_na=False)
    d = new_scores(mare, rock, a.weight, a.tolerance, a.min_covered)
    old_rank = mare.set_index("id")["rank"]
    variant = "B (only cells with c23)" if a.only_with_c23 else "A (no data renormalised, current team rule)"
    if a.only_with_c23:
        d = d[d.s_c23.notna()].copy()
        d["rank_new"] = d.score_new.rank(ascending=False, method="first").astype(int)
        d = d.sort_values("rank_new")
        old20 = set(mare[mare.id.isin(d.id)].nsmallest(20, "rank").id)
    else:
        old20 = set(mare.nsmallest(20, "rank").id)
    new20 = set(d.head(20).id)
    print(f"## c23 what-if, variant {variant}: weight {a.weight:g}, tolerance {a.tolerance:g}, "
          f"min covered {a.min_covered:g}; {len(d)} cells ranked\n")
    print(md_table(d))
    print(f"\nno-data c23 cells in new top 20: {int(d.head(20).s_c23.isna().sum())}")
    print(f"old top 20 (of the ranked cells): stay {len(old20 & new20)}, leave {len(old20 - new20)}, "
          f"enter {len(new20 - old20)}")
    rn = d.set_index("id")["rank_new"]
    print("leave:", ", ".join(f"{i} (#{old_rank[i]} -> #{rn[i]})" for i in sorted(old20 - new20, key=old_rank.get)))
    tag = "B" if a.only_with_c23 else "A"
    dest = Path(a.rock).with_name(f"mare_c23_whatif_{tag}_w{a.weight:g}_t{a.tolerance:g}.csv")
    d[["rank_new", "rank", "id", "lon", "lat", "base_lon", "base_lat", "ROCK_CLASS", "covered_share", "share_vb",
       "score", "s_c23", "score_new"]].to_csv(dest, index=False)
    print("wrote", dest)


if __name__ == "__main__":
    main()
