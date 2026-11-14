"""Export pipeline runs for Sofia's app (branch sofia/app, app/README.md): out/<run>/ -> outputs/.

    python src/export_app.py out/meteor_crater out/pinacate
    python src/export_app.py out/meteor_crater out/pinacate --sites-info app/sample/site_info.json \
        --sites-coords app/sample/scores.csv

Writes outputs/:
    scores.csv      SITE,LAT,LON + app columns (0-1 similarity to the Moon; empty = no data / no
                    similarity yet) + RUN,CELL,BASE_TYPE,SCORE_TOTAL,RANK
    raw_values.csv  same rows, raw values (units in targets.json) + a few display values
    targets.json    per base type: criteria, whether they count, weight, score_method
                    (target / rank / display / not computed), raw Moon value + unit + source
    heatmap.json    [{lat, lng, weight}] for all ranked cells, weight = SCORE_TOTAL
    README.md       what the files mean

Rules:
- A column in scores.csv holds a SIMILARITY score vs the Moon (exp(-((earth - moon)/tol)^2)) or is empty.
  Rank-scored criteria (no lunar value yet, e.g. c1-c4) are left EMPTY there: a rank within one run is
  not a similarity and the app would read it as one. Their raw values are in raw_values.csv.
- SCORE_TOTAL = the run's "score (vs Moon)" (target criteria with weight > 0 only), comparable across
  runs; RANK = rank of SCORE_TOTAL across all exported rows.
- LAT/LON = the cell's best place low point (crater centre, for the 3D view).
- SITE = name of a known site from site_info.json if its point (from --sites-coords, Sofia's approximate
  coordinates) lies inside the cell, else "<run> <cell>". No commas in names (the app splits on ",").
- All runs must use the same scoring config (methods, weights, lunar targets), else the script stops.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# pipeline criterion -> app column (agreed with Sofia's proposal in app.js CRITERIA)
APP_COLUMNS = {
    "c1_sunny_ridge": "SUNNY_RIDGE", "c2_dark_floor": "DARK_FLOOR", "c3_light_dark": "LIGHT_NEAR_DARK",
    "c4_grazing_sun": "GRAZING_SUN", "c5_sky_view": "SKY_VIEW", "c7_bowl": "BOWL_SHAPE",
    "c8_crater_size": "CRATER_SIZE", "c9_relief": "RELIEF", "c10_flat_base": "SLOPE_BASE",
    "c11_walls": "STEEP_WALLS", "c12_drivable": "DRIVABLE", "c13_roughness": "ROUGHNESS", "c14_aspect": "ASPECT",
}
UNITS = {
    "c1_sunny_ridge": "lit fraction / flat-land lit fraction", "c2_dark_floor": "terrain shadow fraction (p99 of floor)",
    "c3_light_dark": "distance / bowl radius", "c4_grazing_sun": "deg (max Sun elevation)",
    "c5_sky_view": "share of sky hemisphere", "c7_bowl": "depth / width", "c9_relief": "m (rim to floor)",
    "c10_flat_base": "deg (base pad slope)", "c11_walls": "deg (inner wall slope)",
    "c13_roughness": "m (elevation std, 3x3 px at 60 m)", "c14_aspect": "share of steep slopes facing the pole",
}
EXTRA_RAW = {"c7_depth_m": "DEPTH_SPILL_M", "c7_width_m": "DIAMETER_EQUIV_M", "low_elev_m": "LOW_ELEV_M",
             "base_lat": "BASE_LAT", "base_lon": "BASE_LON", "base_elev_m": "BASE_ELEV_M",
             "max_dark_days": "MAX_DARK_DAYS", "near_permanent_shadow_share": "NEAR_PERMANENT_SHADOW_SHARE",
             "rank_score": "RANK_SCORE_WITHIN_RUN"}


def _num(v):
    if v in (None, ""):
        return None
    x = float(v)
    return None if math.isnan(x) else x


def _fmt(v, nd=4):
    """Fixed decimals, trailing zeros dropped (no significant-digit cut: coordinates keep nd decimals)."""
    if v is None:
        return ""
    s = f"{round(v, nd):.{nd}f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def score_method(axis: dict) -> str:
    if axis["weight"] <= 0:
        return "display"
    return {"target": "target", "rank": "rank"}.get(axis["method"], axis["method"])


def load_run(path: Path):
    radar = json.loads((path / "radar.json").read_text(encoding="utf-8"))
    with open(path / "ranking.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return radar, rows


def known_sites(info_path: Path | None, coords_path: Path | None) -> list[tuple[str, float, float]]:
    if not info_path or not coords_path or not info_path.exists() or not coords_path.exists():
        return []
    names = {k for k in json.loads(info_path.read_text(encoding="utf-8")) if not k.startswith("_")}
    out = []
    with open(coords_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["SITE"] in names and r.get("LAT") and r.get("LON"):
                out.append((r["SITE"], float(r["LAT"]), float(r["LON"])))
    return out


def site_name(run: str, row: dict, sites) -> str:
    w, s, e, n = (float(row[k]) for k in ("west", "south", "east", "north"))
    inside = [name for name, lat, lon in sites if s <= lat <= n and w <= lon <= e]
    return inside[0] if inside else f"{run} {row['id']}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="+", type=Path, help="out/<run> folders (with radar.json + ranking.csv)")
    ap.add_argument("--out", type=Path, default=ROOT / "outputs")
    ap.add_argument("--sites-info", type=Path, default=ROOT / "app" / "sample" / "site_info.json")
    ap.add_argument("--sites-coords", type=Path, default=ROOT / "app" / "sample" / "scores.csv",
                    help="CSV with SITE,LAT,LON for the known sites (Sofia's approximate coordinates)")
    a = ap.parse_args()

    runs = [(p.name, *load_run(p)) for p in a.runs]
    ref_axes = {x["id"]: x for x in runs[0][1]["axes"]}
    for name, radar, _ in runs[1:]:
        axes = {x["id"]: x for x in radar["axes"]}
        diff = [k for k in set(ref_axes) | set(axes)
                if {f: (ref_axes.get(k) or {}).get(f) for f in ("method", "weight", "target", "tolerance")}
                != {f: (axes.get(k) or {}).get(f) for f in ("method", "weight", "target", "tolerance")}]
        if diff:
            raise SystemExit(f"run {name} was scored with a different config than {runs[0][0]} ({sorted(diff)}): rerun it")
    base_type = runs[0][1]["base_type"]
    lunar = runs[0][1]["lunar_target"]
    sites = known_sites(a.sites_info, a.sites_coords)
    if not sites:
        print("note: no known-site file found, every SITE is '<run> <cell>'")

    rows = []
    for name, radar, ranking in runs:
        for r in ranking:
            row = {"SITE": site_name(name, r, sites), "LAT": _num(r["low_lat"]), "LON": _num(r["low_lon"]),
                   "RUN": name, "CELL": r["id"], "BASE_TYPE": radar["base_type"], "SCORE_TOTAL": _num(r["score"]),
                   "_r": r, "_centre": (_num(r["lat"]), _num(r["lon"]))}
            for crit, col in APP_COLUMNS.items():
                ax = ref_axes.get(crit)
                ok = ax is not None and score_method(ax) in ("target", "display") and ax["method"] == "target"
                row[col] = _num(r.get(f"s_{crit}")) if ok else None       # similarity only; rank -> empty
            rows.append(row)
    rows.sort(key=lambda x: (x["SCORE_TOTAL"] is None, -(x["SCORE_TOTAL"] or 0.0)))
    for i, x in enumerate(rows, 1):
        x["RANK"] = i if x["SCORE_TOTAL"] is not None else None
    dup = {x["SITE"] for x in rows if sum(y["SITE"] == x["SITE"] for y in rows) > 1}
    for x in rows:                                         # app keys sites by SITE: keep names unique
        if x["SITE"] in dup:
            x["SITE"] = f"{x['SITE']} ({x['RUN']} {x['CELL']})"
    assert all("," not in x["SITE"] for x in rows), "site names must not contain commas"

    a.out.mkdir(parents=True, exist_ok=True)
    cols = ["SITE", "LAT", "LON", *APP_COLUMNS.values(), "RUN", "CELL", "BASE_TYPE", "SCORE_TOTAL", "RANK"]
    with open(a.out / "scores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for x in rows:
            w.writerow([x["SITE"], _fmt(x["LAT"], 5), _fmt(x["LON"], 5), *[_fmt(x[c]) for c in APP_COLUMNS.values()],
                        x["RUN"], x["CELL"], x["BASE_TYPE"], _fmt(x["SCORE_TOTAL"]), x["RANK"] or ""])

    raw_cols = ["SITE", "LAT", "LON", *APP_COLUMNS.values(), *EXTRA_RAW.values(), "RUN", "CELL"]
    with open(a.out / "raw_values.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(raw_cols)
        for x in rows:
            r = x["_r"]
            w.writerow([x["SITE"], _fmt(x["LAT"], 5), _fmt(x["LON"], 5),
                        *[_fmt(_num(r.get(c))) for c in APP_COLUMNS],
                        *[_fmt(_num(r.get(c))) for c in EXTRA_RAW], x["RUN"], x["CELL"]])

    crit_list = []
    for crit, col in APP_COLUMNS.items():
        ax = ref_axes.get(crit)
        lt = (lunar.get("criteria") or {}).get(crit, {})
        crit_list.append({
            "column": col, "criterion": crit, "label": ax["label"] if ax else None,
            "counts": bool(ax and ax.get("in_total")),
            "weight": ax["weight"] if ax else None,
            "score_method": score_method(ax) if ax else "not computed",
            "in_scores_csv": bool(ax and ax["method"] == "target"),
            "tolerance": ax.get("tolerance") if ax else None,
            "earth_unit": UNITS.get(crit),
            "moon": {"value": lt.get("value") if lt.get("verified") else None, "unit": lt.get("unit"),
                     "source": lt.get("source") if lt.get("verified") else None,
                     "zone": lt.get("zone"), "note": lt.get("note")} if lt else None,
        })
    targets = {
        "_note": ("Lunar reference per base type. The 0-1 values in scores.csv ARE the similarity to the Moon "
                  "(1 = equal to the Moon); there are no 0-1 target values. Moon values are raw, in earth_unit. "
                  "score_method: target = similarity, counts in SCORE_TOTAL if weight > 0; display = similarity "
                  "shown but weight 0; rank = no lunar value yet, rank within one run, NOT in scores.csv; "
                  "not computed = no pipeline value yet."),
        base_type: {"label": "Polar base · " + lunar.get("label", ""),
                    "total_rule": runs[0][1].get("score_label", "score vs Moon"),
                    "criteria": crit_list},
    }
    (a.out / "targets.json").write_text(json.dumps(targets, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    heat = [{"lat": x["_centre"][0], "lng": x["_centre"][1], "weight": round(x["SCORE_TOTAL"], 4)}
            for x in rows if x["SCORE_TOTAL"] is not None]
    (a.out / "heatmap.json").write_text(json.dumps(heat, indent=1) + "\n", encoding="utf-8")

    # every searched cell (ranked or not), so the app can draw the searched area; not part of the heatmap
    ranked_ids = {(x["RUN"], x["CELL"]): x for x in rows}
    cells = []
    for p in a.runs:
        gj = p / "cells.geojson"
        if not gj.exists():
            continue
        for f in json.loads(gj.read_text(encoding="utf-8"))["features"]:
            pr = f["properties"]
            ring = f["geometry"]["coordinates"][0]
            lons, lats = [c[0] for c in ring], [c[1] for c in ring]
            hit = ranked_ids.get((p.name, pr["id"]))
            fr, tr = pr.get("filter_reason") or "", pr.get("terrain_reason") or ""
            status = ("ranked" if hit else "filtered" if fr else "no_bowl" if tr.startswith("no depression")
                      else "dropped")
            cells.append({"run": p.name, "cell": pr["id"], "lat": pr.get("lat"), "lng": pr.get("lon"),
                          "bbox": [round(min(lons), 5), round(min(lats), 5), round(max(lons), 5), round(max(lats), 5)],
                          "status": status, "reason": fr or tr or "", "site": hit["SITE"] if hit else None,
                          "score_total": hit["SCORE_TOTAL"] if hit else None})
    (a.out / "cells.json").write_text(json.dumps(cells, indent=1) + "\n", encoding="utf-8")

    by = {m: [c["column"] for c in crit_list if c["score_method"] == m] for m in ("target", "display", "rank", "not computed")}
    counts = [c["column"] for c in crit_list if c["counts"]]
    readme = f"""# outputs/ for the app

Written by `src/export_app.py` from: {', '.join(n for n, _, _ in runs)}. Base type: {base_type}.
Re-create with `python src/export_app.py {' '.join('out/' + n for n, _, _ in runs)}` (site names need
`--sites-info` / `--sites-coords`, default `app/sample/site_info.json` and `app/sample/scores.csv` from Sofia's app).
Known sites matched this time: {', '.join(sorted({x['SITE'] for x in rows if not x['SITE'].startswith(tuple(n + ' ' for n, _, _ in runs))})) or 'none'}.

| File | What it is |
|---|---|
| `scores.csv` | one row per ranked cell: `SITE,LAT,LON`, one 0–1 column per criterion, then `RUN,CELL,BASE_TYPE,SCORE_TOTAL,RANK` |
| `raw_values.csv` | same rows, raw Earth values (units in `targets.json` → `earth_unit`) plus depth, diameter, base pad, dark days |
| `targets.json` | per base type: each criterion's column, `counts`, `weight`, `score_method`, raw Moon value + unit + source |
| `heatmap.json` | `[{{lat, lng, weight}}]`, one point per ranked cell at the **cell centre**, weight = `SCORE_TOTAL` |
| `cells.json` | every searched cell of these runs ({len(cells)}): centre, `bbox` [W,S,E,N], `status` (ranked / no_bowl / filtered / dropped) + `reason`, for drawing the searched area |

**Why bowl-less cells are not in the heatmap with weight 0:** a weighted heatmap adds up the weights, so a
point with weight 0 adds nothing and would be invisible. To show where we searched and found nothing, draw
`cells.json` (e.g. faint outlines for `no_bowl` / `filtered`) under the heatmap instead.
Status counts here: {', '.join(f"{s} {sum(c['status'] == s for c in cells)}" for s in ('ranked', 'no_bowl', 'filtered', 'dropped'))}.

## How to read the numbers
- **A 0–1 value in `scores.csv` is already the similarity to the Moon**: exp(−((Earth − Moon) / tolerance)²),
  1 = same as the Moon. Do not compare it with a target again.
- **Empty = no data** or no similarity yet. Never 0.
- **`SCORE_TOTAL`** = score vs Moon: weighted mean of the criteria with `counts: true` only
  ({', '.join(counts)}). Comparable across runs. **`RANK`** = rank of `SCORE_TOTAL` over all rows in this file.
- **`LAT`/`LON`** = the crater's low point (centre of the bowl), for the 3D view. The base pad is in `raw_values.csv`.
- **`SITE`** = a known site from `site_info.json` when its (approximate) point lies inside the cell, else `<run> <cell>`.

## Which criteria count
- **Counted (target, weight > 0):** {', '.join(by['target']) or 'none'}
- **Display only (similarity shown, weight 0):** {', '.join(by['display']) or 'none'}
- **Rank-scored, no lunar value yet** (empty in `scores.csv`, raw value in `raw_values.csv`):
  {', '.join(by['rank']) or 'none'}. They get a similarity once the lunar light targets (Mateo) are in.
- **Not computed by the pipeline yet:** {', '.join(by['not computed']) or 'none'}
- Only the polar base type exists so far; `cave` and `mare` have no targets yet.
"""
    (a.out / "README.md").write_text(readme, encoding="utf-8")
    print(f"{len(rows)} rows from {len(runs)} runs -> {a.out}")
    for x in rows:
        print(f"  {x['RANK']}. {x['SITE']}  total {x['SCORE_TOTAL']}  ({x['LAT']}, {x['LON']})")


if __name__ == "__main__":
    main()
