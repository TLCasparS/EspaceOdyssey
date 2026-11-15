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
- Several lunar targets (night Task 3, docs/MULTI_TARGET.md, src/pipeline/multi_target.py): if
  config/lunar_targets_candidates.json (--candidates) has a target in use (verified: true, or any with
  --include-unverified = PREVIEW), scores.csv gets SCORE_<TARGET> per target (today's target included, e.g.
  SCORE_SHACKLETON = SCORE_TOTAL), BEST_TARGET, BEST_SCORE (+ MULTI_TARGET_PREVIEW = 1 in a preview), appended
  after the existing columns; targets.json gets targets[base].lunar_targets and _multi_target. With only
  today's targets nothing changes: all files are identical to before.

Optional (15 Nov 2026; without these flags nothing changes):
- --post-filters config/post_filters.yaml: config-v1.1 post-run filters (src/post_filters.py). An excluded
  Polar place keeps SCORE_TOTAL and raw values, gets EXCLUDED = reason(s), no RANK, no heatmap point; its cell
  gets status "excluded" in cells.json. Scores are never changed.
- --place-names DIR: offline NAME ("34 km SW of Balkhash") and per-cell COUNTRY (src/place_names.py).
- --anchors CSV (SITE,LAT,LON,MAX_KM): a row whose LAT/LON lies within MAX_KM of an anchor takes that SITE key,
  so the app's site_info.json cards (keyed by older "<run> <cell>" names) still find their place.
- --dedupe-km D: the same bowl found by two runs (low points within D km, same base type) is exported once;
  the row of a region run wins over a night (world-grid) run. Dropped rows are listed in the README.
- --glim PATH: GLiM rock class (Hartmann & Moosdorf 2012, PANGAEA 0.5 deg grid; src/pipeline/material.py) as
  DISPLAY columns in raw_values.csv: ROCK_CLASS, ROCK_CLASS_NAME, BASALT_SHARE_5KM, GLIM_COVERED_SHARE,
  BASALT_REGION (team decision 15 Nov 2026: BASALT_REGION = 1 if the class AT the point is vb, else 0; a point in a
  cell GLiM counts as sea, or GLiM "nd", = no data, nothing borrowed from neighbours). Never in a score.
- --mare-c30 PATH: out/mare_v11/c30_night_mare.csv (src/mare_v11_rescore.py; RUN,CELL,C30_PER_KM2): c30 small-crater
  density as ONE DISPLAY column SMALL_CRATERS_PER_KM2 at the very END of raw_values.csv for Mare rows (weight 0, never
  in a score; empty = no data, Polar rows empty) + targets.json "_mare_c30" (team decision 15 Nov 2026, docs/MARE_V11.md).
- --mare-common-tolerance: fair Mare twins (team decision 15 Nov 2026): every Mare lunar target is scored with the
  20-cell target's tolerance per criterion (multi_target.common_tolerance). Changes only BEST_TARGET / BEST_SCORE /
  SCORE_<mare target>; SCORE_TOTAL and RANK unchanged.
- --macrostrat PATH: data/macrostrat/rock_site.csv (src/compute_macrostrat.py; Macrostrat, CC BY 4.0) as DISPLAY
  columns at the END of raw_values.csv: ROCK_SITE, ROCK_SITE_LITH, ROCK_SITE_SOURCE, ROCK_SITE_SCALE, BASALT_SITE
  (joined on RUN + CELL; empty = no data). targets.json -> _rock_site. Never in a score; no other column changes.
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
    "c9_relief": "RELIEF", "c10_flat_base": "SLOPE_BASE",
    "c11_walls": "STEEP_WALLS", "c13_roughness": "ROUGHNESS", "c14_aspect": "ASPECT",
}
# DISPLAY-only columns (weight 0, never in SCORE_TOTAL; parameters in config/display.yaml, outside the freeze).
# column: (criterion, raw field for scores.csv or None, kind, unit / meaning)
DISPLAY_COLUMNS = {
    "DRIVABLE": ("c12_drivable", "drivable_share_5km", "more is better",
                 "share of pixels flatter than display.drivable_slope_deg within display.drivable_radius_km of the base pad"),
    "BARE": ("c19_bare", "bare_share", "more is better", "share of WorldCover bare/sparse (class 60) in floor + rim zone"),
    "GROUND_ICE": ("c18_ground_ice", "ice_floor_share", "more is better", "share of WorldCover snow & ice in the floor zone"),
    "IMPACT_CRATER": ("c24_impact_crater", "impact_match", "fact",
                      "1 = low point lies within max(0.6 x diameter, 1 km) of a confirmed impact structure in "
                      "data/impact/impact_structures.csv (Wikipedia list, incomplete), 0 = not in that list"),
    "CRATER_SIZE": ("c8_crater_size", None, "raw only",
                    "size-dependent: diameter and depth in raw_values.csv (CRATER_DIAMETER_EQUIV_M, CRATER_RIM_TO_FLOOR_M); "
                    "no 0-1 value"),
}
DISPLAY_RAW = {"drivable_share_rim": "DRIVABLE_RIM_SHARE", "drivable_share_5km": "DRIVABLE_5KM_SHARE",
               "bare_share": "BARE_SHARE", "c7_width_m": "CRATER_DIAMETER_EQUIV_M", "c9_relief": "CRATER_RIM_TO_FLOOR_M"}
UNITS = {
    "c1_sunny_ridge": "lit fraction / flat-land lit fraction", "c2_dark_floor": "terrain shadow fraction (p99 of floor)",
    "c3_light_dark": "distance / bowl radius", "c4_grazing_sun": "deg (max Sun elevation)",
    "c5_sky_view": "share of sky hemisphere", "c7_bowl": "depth / width", "c9_relief": "m (rim to floor)",
    "c10_flat_base": "deg (base pad slope)", "c11_walls": "deg (inner wall slope)",
    "c13_roughness": "m (elevation std, 3x3 px at 60 m)", "c14_aspect": "share of steep slopes facing the pole",
}
# known limitation (team decision 14 Nov 2026, option a): accepted and shown with the value
DISC_VS_CENTRE = ("Known limitation: on the Moon 'lit' is the visible fraction of the solar DISC (PGDA AVGVISIB, "
                  "extended Sun); on Earth it is the Sun's CENTRE above the horizon (point Sun). Both give 0.5 on "
                  "flat land at the pole; on terrain they can differ where the Sun stays partly hidden for long "
                  "stretches (disc fraction > 0 while the centre is already below the horizon).")
LIMITATIONS = {"c1_sunny_ridge": DISC_VS_CENTRE, "c2_dark_floor": DISC_VS_CENTRE, "c3_light_dark": DISC_VS_CENTRE}
# facts for the pitch: criteria where no place on Earth can match the Moon
FACTS = {"c4_grazing_sun": ("No Earth analog possible: the Sun's highest elevation is purely a matter of latitude. "
                            "On Earth it is at least 23.4 deg (at the poles, from the axial tilt); at Shackleton it is "
                            "1.9 deg (1.5 deg at the lunar pole). Shown for information, weight 0.")}
EXTRA_RAW = {"c7_depth_m": "DEPTH_SPILL_M", "c7_width_m": "DIAMETER_EQUIV_M", "low_elev_m": "LOW_ELEV_M",
             "base_lat": "BASE_LAT", "base_lon": "BASE_LON", "base_elev_m": "BASE_ELEV_M",
             "max_dark_days": "MAX_DARK_DAYS", "near_permanent_shadow_share": "NEAR_PERMANENT_SHADOW_SHARE",
             "rank_score": "RANK_SCORE_WITHIN_RUN", "ice_floor_share": "ICE_FLOOR_SHARE", "ice_rim_share": "ICE_RIM_SHARE"}


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


def impact_match(lat, lon, impacts: list[dict], disp: dict):
    """Nearest confirmed impact structure whose centre is within max(rel x diameter, min_km) of the point."""
    if lat is None or lon is None or not impacts:
        return None
    best = None
    for im in impacts:
        d = math.hypot((lat - im["lat"]) * 110.6, (lon - im["lon"]) * 111.3 * math.cos(math.radians(lat)))
        reach = max(disp.get("impact_match_rel", 0.6) * (im["diameter_km"] or 0.0), disp.get("impact_match_min_km", 1.0))
        if d <= reach and (best is None or d < best["dist_km"]):
            best = {**im, "dist_km": d}
    return best


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


MARE_COLUMNS = {"c9_relief": "RELIEF", "c10_flat_base": "SLOPE_BASE", "c12_drivable": "DRIVABLE",
                "c13_roughness": "ROUGHNESS"}
MARE_UNITS = {"c9_relief": "m (max - min within 5 km of the base pad)", "c10_flat_base": "deg (base pad slope)",
              "c12_drivable": "share of pixels < 15 deg within 5 km", "c13_roughness": "m (median 3x3 std within 5 km)"}
LIGHT_GROUP = {"c1_sunny_ridge", "c2_dark_floor", "c3_light_dark", "c4_grazing_sun", "c5_sky_view"}
EXTRA_COLS = ["RUN", "CELL", "BASE_TYPE", "SCORE_TOTAL", "RANK", "NAME", "COUNTRY", "ROLE",
              "TERRAIN_SCORE", "LIGHT_SCORE", "MISSED_REASON"]


ROCK_COLS = ["ROCK_CLASS", "ROCK_CLASS_NAME", "BASALT_SHARE_5KM", "GLIM_COVERED_SHARE", "BASALT_REGION"]
GLIM_GRID = "glim_wgs84_0point5deg.txt.asc"


def load_glim(path: Path, mcfg: dict) -> dict:
    """GLiM grid source + display parameters (config/display.yaml -> material). path = .asc file or a folder."""
    from pipeline.material import CLASSES, DISPLAY_CAVEAT, GridSource
    p = Path(path)
    if p.is_dir():
        hits = sorted(p.rglob(GLIM_GRID))
        if not hits:
            raise SystemExit(f"--glim: no {GLIM_GRID} under {p}")
        p = hits[0]
    meta = {"source": "Hartmann & Moosdorf (2012) GLiM v1.0 gridded to 0.5 deg, PANGAEA doi:10.1594/PANGAEA.788537 "
                      "(CC-BY 3.0); cite doi:10.1029/2012GC004370",
            "radius_km": float(mcfg.get("radius_km", 5)), "caveat": DISPLAY_CAVEAT,
            "classes": {k: v for k, v in CLASSES.items() if k != "nd"},
            "note": ("Display only, never in a score. Caveat: " + DISPLAY_CAVEAT + " (one dominant class per 0.5 deg "
                     "cell, ~55 km). BASALT_REGION = 1 if the class at the point is vb, 0 for any other class. A point "
                     "in a cell GLiM counts as sea (coasts, islands) or GLiM nd = no data: no class, no flag, no "
                     "shares borrowed from neighbouring cells. Point = Polar low point, Mare base pad. "
                     "docs/MATERIAL.md (team decisions 15 Nov 2026).")}
    return {"src": GridSource(p), "meta": meta}


def rock_values(lat, lon, glim: dict) -> dict:
    """ROCK_COLS for one point; None / "" = no data (never 0)."""
    from pipeline.material import CLASSES, classify_point
    out = {"ROCK_CLASS": "", "ROCK_CLASS_NAME": "", "BASALT_SHARE_5KM": None, "GLIM_COVERED_SHARE": None,
           "BASALT_REGION": None}
    if lat is None or lon is None:
        return out
    m = glim["meta"]
    res = classify_point(float(lon), float(lat), glim["src"], m["radius_km"])
    code = res["rock_class"] or ""
    out.update(ROCK_CLASS=code, ROCK_CLASS_NAME=CLASSES.get(code, "") if code else "",
               GLIM_COVERED_SHARE=res["covered_share"])
    if code:                                               # no class at the point = no data (team decision)
        out["BASALT_SHARE_5KM"] = res["share_vb"]
        out["BASALT_REGION"] = 1.0 if code == "vb" else 0.0
    return out


def _count_best(rows) -> dict:
    n = {}
    for x in rows:
        if x.get("BEST_TARGET"):
            k = (x["BASE_TYPE"], x["BEST_TARGET"])
            n[k] = n.get(k, 0) + 1
    return n


def group_score(r: dict, axes: dict, ids) -> float | None:
    """Weighted mean of the target-scored axes with weight > 0 among ids (TERRAIN_SCORE / LIGHT_SCORE)."""
    num = den = 0.0
    for c in ids:
        ax = axes.get(c)
        s = _num(r.get(f"s_{c}"))
        if ax is None or s is None or ax["weight"] <= 0 or ax["method"] != "target":
            continue
        num += ax["weight"] * s
        den += ax["weight"]
    return round(num / den, 4) if den > 0 else None


def load_regions(registry: Path, night: Path) -> list[dict]:
    import yaml
    regs = []
    if registry.exists():
        regs += yaml.safe_load(registry.read_text(encoding="utf-8"))["regions"]
    if night.exists():
        for r in yaml.safe_load(night.read_text(encoding="utf-8"))["regions"]:
            regs.append({"title": r["name"].replace("_", " ").title(), **r})
    return regs


WORLD_REGION = {"name": "world", "title": "World cell", "bbox": None, "role": "screening", "country": ""}


def region_of(run: str, cell_id: str, lat, lon, regions: list[dict]) -> dict | None:
    import re
    if re.match(r"^b\d{3}_r\d+c\d+$", cell_id):            # night run --world: world grid cells (screening)
        named = [rg for rg in regions if lat is not None and lon is not None and rg.get("bbox")
                 and rg["bbox"][1] <= lat <= rg["bbox"][3] and rg["bbox"][0] <= lon <= rg["bbox"][2]]
        return named[0] if named else WORLD_REGION
    for rg in regions:                                     # night runs: cell ids carry the region name
        if cell_id.startswith(rg["name"] + "_r"):
            return rg
    for rg in regions:                                     # single runs: run folder name = region name
        if run == rg["name"] or run.startswith(rg["name"] + "_"):
            return rg
    if lat is not None and lon is not None:
        for rg in regions:
            w, s, e, n = rg["bbox"]
            if s <= lat <= n and w <= lon <= e:
                return rg
    return None


def cell_status(pr: dict, scored: bool, base: str, override: str | None = None) -> str:
    fr, tr = pr.get("filter_reason") or "", pr.get("terrain_reason") or ""
    if override:                                           # config-v1.1 "excluded", or "duplicate"
        return override
    if scored:
        return "ranked" if base == "polar" else "kept"
    if fr:
        return "filtered"
    if tr.startswith("prefilter"):
        return "prefilter"
    if tr.startswith("no depression"):
        return "no_bowl"
    if "ice floor" in tr:
        return "ice_floor"
    return "dropped"


def _dist_km(lat1, lon1, lat2, lon2):
    return math.hypot((lat1 - lat2) * 110.6, (lon1 - lon2) * 111.3 * math.cos(math.radians(lat1)))


def _portable(v) -> str:
    """Path for the README re-create line: repo-relative (out/..., data/..., config/...); under %LOCALAPPDATA% ->
    $LOCALAPPDATA/...; anything else -> <data dir>/<name>. Never a local user path."""
    import os
    p = Path(v).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        pass
    la = os.environ.get("LOCALAPPDATA")
    if la:
        try:
            return "$LOCALAPPDATA/" + p.relative_to(Path(la).resolve()).as_posix()
        except ValueError:
            pass
    return f"<data dir>/{p.name}"


def recreate_line(ap, a) -> str:
    """The exact export command: the runs + EVERY option whose value differs from its default (store_true flags
    as bare flags), paths made portable (_portable)."""
    parts = ["python src/export_app.py", *(_portable(p) for p in a.runs)]
    for act in ap._actions:
        if not act.option_strings or act.dest in ("help",):
            continue
        v = getattr(a, act.dest)
        if v == act.default or v is None or v is False:
            continue
        flag = act.option_strings[-1]
        if v is True:
            parts.append(flag)
        elif isinstance(v, Path):
            parts.append(f"{flag} {_portable(v)}")
        elif isinstance(v, float):
            parts.append(f"{flag} {v:g}")
        else:
            parts.append(f"{flag} {v}")
    return " ".join(parts)


def main():
    import sys
    import yaml
    for stream in (sys.stdout, sys.stderr):                # Windows cp1252 console: place names like "ā" must not crash
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("runs", nargs="+", type=Path, help="out/<run> folders (radar.json + ranking.csv), Polar or Mare")
    ap.add_argument("--out", type=Path, default=ROOT / "outputs")
    ap.add_argument("--sites-info", type=Path, default=ROOT / "app" / "sample" / "site_info.json")
    ap.add_argument("--sites-coords", type=Path, default=ROOT / "app" / "sample" / "scores.csv",
                    help="CSV with SITE,LAT,LON for the known sites (Sofia's approximate coordinates)")
    ap.add_argument("--impacts", type=Path, default=ROOT / "data" / "impact" / "impact_structures.csv")
    ap.add_argument("--regions", type=Path, default=ROOT / "config" / "regions.yaml")
    ap.add_argument("--night-regions", type=Path, default=ROOT / "config" / "night_regions.yaml")
    ap.add_argument("--missed", type=Path, default=ROOT / "config" / "missed_sites.yaml")
    ap.add_argument("--cells-near-km", type=float, default=50.0,
                    help="cells.json: only cells within this distance of a ranked/kept place")
    ap.add_argument("--candidates", type=Path, default=ROOT / "config" / "lunar_targets_candidates.json",
                    help="extra lunar targets (Task 5 format, docs/MULTI_TARGET.md); only verified ones are used")
    ap.add_argument("--include-unverified", action="store_true",
                    help="PREVIEW: also score unverified candidate targets / criteria; outputs are marked as preview")
    ap.add_argument("--post-filters", type=Path, help="config-v1.1 post-run filters (config/post_filters.yaml)")
    ap.add_argument("--place-names", type=Path,
                    help="folder with Natural Earth + GeoNames data for offline NAME / COUNTRY (src/place_names.py)")
    ap.add_argument("--anchors", type=Path, help="CSV SITE,LAT,LON,MAX_KM: keep site_info keys for these places")
    ap.add_argument("--glim", type=Path,
                    help="GLiM 0.5 deg ASCII grid (.asc) or a folder containing it: rock class display columns")
    ap.add_argument("--mare-c30", type=Path,
                    help="out/mare_v11/c30_night_mare.csv: c30 small-crater density display column (Mare, weight 0)")
    ap.add_argument("--mare-common-tolerance", action="store_true",
                    help="fair Mare twins: all Mare lunar targets scored with the 20-cell tolerance (BEST_TARGET only)")
    ap.add_argument("--macrostrat", type=Path,
                    help="data/macrostrat/rock_site.csv: Macrostrat rock-at-site display columns in raw_values.csv")
    ap.add_argument("--dedupe-km", type=float, default=0.0,
                    help="same bowl in two runs (low points within this distance): export once, region run wins")
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT / "src"))
    from impact_list import load as load_impacts
    from pipeline.config import load_config
    from pipeline import multi_target as mt
    cfg = load_config()
    disp = cfg.get("display", {})
    impacts = load_impacts(a.impacts)
    regions = load_regions(a.regions, a.night_regions)
    sites = known_sites(a.sites_info, a.sites_coords)
    post = names = None
    if a.post_filters:
        from post_filters import PostFilters
        post = PostFilters.from_file(a.post_filters)
        if post.mines_missing:
            print(f"WARNING: mine filter NOT applied: {post.mines_missing}")
    if a.place_names:
        from place_names import PlaceNames
        names = PlaceNames(a.place_names)
    glim = load_glim(a.glim, disp.get("material", {})) if a.glim else None
    macro = None
    if a.macrostrat:
        from pipeline import macrostrat as ms
        macro = ms.load_rock_site(a.macrostrat)
    info_names = {}
    if a.sites_info and a.sites_info.exists():
        info_names = {k: (v.get("name") if isinstance(v, dict) else None) or k
                      for k, v in json.loads(a.sites_info.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    anchors_in = []
    if a.anchors and a.anchors.exists():
        with open(a.anchors, newline="", encoding="utf-8") as f:
            lines = [ln for ln in f if ln.strip() and not ln.startswith("#")]
        anchors_in = [(r["SITE"], float(r["LAT"]), float(r["LON"]), float(r.get("MAX_KM") or 1.5))
                      for r in csv.DictReader(lines)]

    runs = [(p, p.name, *load_run(p)) for p in a.runs]
    ref = {}                                               # base type -> (run name, axes, radar)
    keys = ("method", "weight", "target", "tolerance")
    for p, name, radar, _ in runs:
        base = radar["base_type"]
        axes = {x["id"]: x for x in radar["axes"]}
        if base not in ref:
            ref[base] = (name, axes, radar)
            continue
        r_axes = ref[base][1]
        diff = [k for k in set(r_axes) | set(axes)
                if {f: (r_axes.get(k) or {}).get(f) for f in keys} != {f: (axes.get(k) or {}).get(f) for f in keys}]
        if diff:
            raise SystemExit(f"{base} run {name} was scored with a different config than {ref[base][0]} "
                             f"({sorted(diff)}): rerun it")

    # several lunar targets: today's target = the run's axes (as scored); candidates from --candidates
    base_crit = {base: {x_id: {"weight": ax["weight"], "tolerance": ax.get("tolerance"),
                               "target": ax.get("target") if ax.get("method") == "target" else None}
                        for x_id, ax in axes.items()} for base, (_, axes, _) in ref.items() if base in mt.BUILTIN}
    lunar_targets = mt.build_targets(base_crit, mt.load_candidates(a.candidates), a.include_unverified,
                                     {"mare": cfg.get("mare", {}).get("tolerance_floor", {})})
    if a.mare_common_tolerance:
        mt.common_tolerance(lunar_targets, "mare")
    c30 = None
    if a.mare_c30:
        with open(a.mare_c30, newline="", encoding="utf-8") as f:
            c30 = {(r["RUN"], r["CELL"]): _num(r["C30_PER_KM2"]) for r in csv.DictReader(f)}
    multi = any(not t["builtin"] for t in lunar_targets)   # False: outputs exactly as before Task 3
    mt_preview = multi and any(t["preview"] for t in lunar_targets)
    mt_cols = ([t["column"] for t in lunar_targets] + ["BEST_TARGET", "BEST_SCORE"]
               + (["MULTI_TARGET_PREVIEW"] if mt_preview else [])) if multi else []

    rows = []
    for p, name, radar, ranking in runs:
        base = radar["base_type"]
        axes = ref[base][1]
        colmap = APP_COLUMNS if base == "polar" else MARE_COLUMNS
        for r in ranking:
            if base == "polar":
                lat, lon = _num(r.get("low_lat")), _num(r.get("low_lon"))
            else:
                lat, lon = _num(r.get("base_lat")), _num(r.get("base_lon"))
            rg = region_of(name, r["id"], lat, lon, regions)
            row = {c: None for c in list(APP_COLUMNS.values()) + list(DISPLAY_COLUMNS)}
            row.update(LAT=lat, LON=lon, RUN=name, CELL=r["id"], BASE_TYPE=base, SCORE_TOTAL=_num(r.get("score")),
                       _r=r, _centre=(_num(r["lat"]), _num(r["lon"])), ROLE=rg["role"] if rg else "",
                       COUNTRY=rg["country"] if rg else "", MISSED_REASON="")
            for crit, col in colmap.items():
                ax = axes.get(crit)
                row[col] = _num(r.get(f"s_{crit}")) if ax is not None and ax["method"] == "target" else None
            hit = None
            if base == "polar":
                hit = impact_match(lat, lon, impacts, disp)
                r["impact_match"] = None if not impacts else (1.0 if hit else 0.0)
                for col, (_, field, _, _) in DISPLAY_COLUMNS.items():
                    row[col] = _num(r.get(field)) if field else None
                row["TERRAIN_SCORE"] = group_score(r, axes, [c for c in APP_COLUMNS if c not in LIGHT_GROUP])
                row["LIGHT_SCORE"] = group_score(r, axes, [c for c in APP_COLUMNS if c in LIGHT_GROUP])
            else:
                row["TERRAIN_SCORE"] = group_score(r, axes, list(MARE_COLUMNS))
                row["LIGHT_SCORE"] = None
            row["_impact"] = hit
            w, s, e, n = (float(r[k]) for k in ("west", "south", "east", "north"))
            known = [nm for nm, la, lo in sites if s <= la <= n and w <= lo <= e]
            short = r["id"].split("_")[-1]
            label = None
            if names is not None and lat is not None and lon is not None:
                label = names.label(lat, lon)
                row["COUNTRY"] = names.country(lat, lon) or row["COUNTRY"]
            row["NAME"] = (known[0] if known else hit["name"] if hit else label if label
                           else f"{rg['title'] if rg else name} {short}")
            row["_anchor"] = None
            if lat is not None and lon is not None:
                near = [(_dist_km(lat, lon, la, lo), k) for k, la, lo, mx in anchors_in if _dist_km(lat, lon, la, lo) <= mx]
                if near:
                    row["_anchor"] = min(near)[1]
                    row["NAME"] = info_names.get(row["_anchor"], row["_anchor"])
            pf = post.evaluate(base, lat, lon, r) if post else None
            row["_pf"] = pf
            row["EXCLUDED"] = " + ".join(pf["reasons"]) if pf and pf["reasons"] else ""
            row["_rock"] = rock_values(lat, lon, glim) if glim else None
            if multi:
                row.update(mt.score_row(r, base, lunar_targets))
            rows.append(row)

    duplicates = []                                        # same bowl in two runs: keep one (region run wins)
    if a.dedupe_km > 0:
        kept = []
        for x in sorted(rows, key=lambda x: (x["RUN"].startswith("night_"), -(x["SCORE_TOTAL"] or -1))):
            twin = next((k for k in kept if k["BASE_TYPE"] == x["BASE_TYPE"] and k["RUN"] != x["RUN"]
                         and None not in (k["LAT"], x["LAT"])
                         and _dist_km(x["LAT"], x["LON"], k["LAT"], k["LON"]) <= a.dedupe_km), None)
            if twin is None:
                kept.append(x)
            else:
                duplicates.append((x, twin))
        drop = {id(x) for x, _ in duplicates}
        rows = [x for x in rows if id(x) not in drop]

    for base in ref:                                       # rank per base type (config-v1.1: excluded rows not)
        sub = sorted([x for x in rows if x["BASE_TYPE"] == base and x["SCORE_TOTAL"] is not None
                      and not x.get("EXCLUDED")], key=lambda x: -x["SCORE_TOTAL"])
        for i, x in enumerate(sub, 1):
            x["RANK"] = i
    for x in rows:
        x.setdefault("RANK", None)

    missed = yaml.safe_load(a.missed.read_text(encoding="utf-8"))["missed"] if a.missed.exists() else []
    for m in missed:
        row = {c: None for c in list(APP_COLUMNS.values()) + list(DISPLAY_COLUMNS)}
        row.update(LAT=m["lat"], LON=m["lon"], RUN="", CELL="", BASE_TYPE=m["base_type"], SCORE_TOTAL=None, RANK=None,
                   NAME=m["name"], COUNTRY=m["country"], ROLE="missed", TERRAIN_SCORE=None, LIGHT_SCORE=None,
                   MISSED_REASON=m["reason"], _r={}, _impact=None, _centre=(m["lat"], m["lon"]),
                   EXCLUDED="", _pf=None, _anchor=None)
        row["_rock"] = rock_values(m["lat"], m["lon"], glim) if glim else None
        rows.append(row)

    rows.sort(key=lambda x: (x["ROLE"] == "missed", x["BASE_TYPE"], x["RANK"] is None,
                             x["RANK"] or 0, -(x["SCORE_TOTAL"] or 0)))
    for x in rows:
        x["SITE"] = x.get("_anchor") or x["NAME"]
    count = {}
    for x in rows:
        count[x["SITE"]] = count.get(x["SITE"], 0) + 1
    for x in rows:                                         # app keys sites by SITE: keep names unique
        if count[x["SITE"]] > 1:
            x["SITE"] = f"{x['NAME']} ({x['BASE_TYPE']} {x['CELL'] or 'missed'})"
    for x in rows:
        for k in ("SITE", "NAME", "COUNTRY", "MISSED_REASON", "EXCLUDED"):
            x[k] = str(x.get(k) or "").replace(",", ";")   # the app splits on ","

    a.out.mkdir(parents=True, exist_ok=True)
    pf_cols = ["EXCLUDED"] if post else []
    cols = ["SITE", "LAT", "LON", *APP_COLUMNS.values(), *DISPLAY_COLUMNS, *EXTRA_COLS, *pf_cols, *mt_cols]
    if multi:                                              # today's target re-scored from raw must equal SCORE_TOTAL
        off = [x["SITE"] for x in rows for t in lunar_targets if t["builtin"] and t["base_type"] == x["BASE_TYPE"]
               and x["SCORE_TOTAL"] is not None and x.get(t["column"]) is not None
               and abs(x[t["column"]] - x["SCORE_TOTAL"]) > 2e-4]
        if off:
            print(f"WARNING: {len(off)} rows: built-in target re-scored from raw values != SCORE_TOTAL "
                  f"(e.g. {off[:3]}); check the run's radar.json")
    with open(a.out / "scores.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for x in rows:
            w.writerow([x["SITE"], _fmt(x["LAT"], 5), _fmt(x["LON"], 5), *[_fmt(x[c]) for c in APP_COLUMNS.values()],
                        *[_fmt(x[c]) for c in DISPLAY_COLUMNS], x["RUN"], x["CELL"], x["BASE_TYPE"],
                        _fmt(x["SCORE_TOTAL"]), x["RANK"] or "", x["NAME"], x["COUNTRY"], x["ROLE"],
                        _fmt(x["TERRAIN_SCORE"]), _fmt(x["LIGHT_SCORE"]), x["MISSED_REASON"],
                        *[x["EXCLUDED"] for _ in pf_cols],
                        *[x.get(c) or "" if c == "BEST_TARGET" else "1" if c == "MULTI_TARGET_PREVIEW"
                          else _fmt(x.get(c)) for c in mt_cols]])

    crit_cols = list(dict.fromkeys([*APP_COLUMNS.values(), *MARE_COLUMNS.values()]))   # Polar + Mare raw columns
    pf_raw = ["EXCLUDED", "EXCLUDED_DETAIL", "MINE_DIST_KM"] if post else []
    raw_cols = ["SITE", "LAT", "LON", *crit_cols, *EXTRA_RAW.values(), *DISPLAY_RAW.values(),
                "IMPACT_NAME", "IMPACT_DIAMETER_KM", "IMPACT_DIST_KM", "IMPACT_SOURCE", "RUN", "CELL", "BASE_TYPE",
                *pf_raw, *(ROCK_COLS if glim else []), *(ms.COLUMNS if macro is not None else []),
                *(["SMALL_CRATERS_PER_KM2"] if c30 is not None else [])]
    with open(a.out / "raw_values.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(raw_cols)
        for x in rows:
            r, hit, pf = x["_r"], x["_impact"], x.get("_pf")
            inv = {v: k for k, v in (APP_COLUMNS if x["BASE_TYPE"] == "polar" else MARE_COLUMNS).items()}
            w.writerow([x["SITE"], _fmt(x["LAT"], 5), _fmt(x["LON"], 5),
                        *[_fmt(_num(r.get(inv[col]))) if col in inv else "" for col in crit_cols],
                        *[_fmt(_num(r.get(c))) for c in EXTRA_RAW], *[_fmt(_num(r.get(c))) for c in DISPLAY_RAW],
                        hit["name"] if hit else "", _fmt(hit["diameter_km"]) if hit else "",
                        _fmt(hit["dist_km"], 2) if hit else "", hit["source"] if hit else "",
                        x["RUN"], x["CELL"], x["BASE_TYPE"],
                        *([x["EXCLUDED"], "; ".join(pf["details"]).replace(",", ";") if pf else "",
                           _fmt(pf["mine_dist_km"], 3) if pf else ""] if post else []),
                        *([x["_rock"][c] if c in ("ROCK_CLASS", "ROCK_CLASS_NAME") else _fmt(x["_rock"][c])
                           for c in ROCK_COLS] if glim else []),
                        *(ms.export_values(macro, x["RUN"], x["CELL"]) if macro is not None else []),
                        *([_fmt(c30.get((x["RUN"], x["CELL"]))) if x["BASE_TYPE"] == "mare" else ""]
                          if c30 is not None else [])])

    targets = {"_note": ("Lunar reference per base type. The 0-1 values in scores.csv ARE the similarity to the "
                         "Moon (1 = equal); no 0-1 target values. Moon values are raw, in earth_unit. score_method: "
                         "target = similarity, counts in SCORE_TOTAL if weight > 0; display = shown, weight 0; "
                         "rank = no lunar value yet; not computed = no pipeline value yet. A column can mean "
                         "different things per base type (e.g. DRIVABLE: Polar display share, Mare scored "
                         "similarity): always read it through targets[BASE_TYPE].")}
    for base, (_, axes, radar) in ref.items():
        lunar = radar.get("lunar_target", {})
        colmap, units = (APP_COLUMNS, UNITS) if base == "polar" else (MARE_COLUMNS, MARE_UNITS)
        crit_list = []
        for crit, col in colmap.items():
            ax = axes.get(crit)
            lt = (lunar.get("criteria") or {}).get(crit, {})
            ok = bool(lt.get("verified"))
            crit_list.append({
                "column": col, "criterion": crit, "label": ax["label"] if ax else None,
                "counts": bool(ax and ax.get("in_total")), "weight": ax["weight"] if ax else None,
                "score_method": score_method(ax) if ax else "not computed",
                "in_scores_csv": bool(ax and ax["method"] == "target"),
                "tolerance": ax.get("tolerance") if ax else None, "earth_unit": units.get(crit),
                "limitation": LIMITATIONS.get(crit) if base == "polar" else None,
                "fact": FACTS.get(crit) if base == "polar" else None,
                "moon": {"value": lt.get("value") if ok else None, "unit": lt.get("unit"),
                         "source": lt.get("source") if ok else None, "zone": lt.get("zone"),
                         "n_cells": lt.get("n_cells"), "note": lt.get("note")} if lt else None})
        if base == "polar":
            for col, (crit, field, kind, meaning) in DISPLAY_COLUMNS.items():
                crit_list.append({"column": col, "criterion": crit, "label": None, "counts": False, "weight": 0,
                                  "score_method": "display", "display_kind": kind, "in_scores_csv": field is not None,
                                  "tolerance": None, "earth_unit": meaning, "limitation": None, "fact": None,
                                  "moon": None, "note": "Display only, 'more is better', not a similarity to the Moon."})
        else:
            for crit, txt in radar.get("display", {}).items():
                crit_list.append({"column": None, "criterion": crit, "counts": False, "weight": 0,
                                  "score_method": "display", "fact": txt, "moon": None})
        targets[base] = {"label": lunar.get("label") or base, "named_site": lunar.get("named_site"),
                         "total_rule": radar.get("score_label", "score vs Moon"), "criteria": crit_list}
        if multi:
            targets[base]["lunar_targets"] = mt.targets_summary([t for t in lunar_targets if t["base_type"] == base])
    if multi:
        targets["_multi_target"] = {
            "preview": mt_preview,
            "note": ("scores.csv SCORE_<TARGET> = score vs Moon against that lunar target (same rule, weights and "
                     "tolerances as SCORE_TOTAL; a target's own tolerance wins, Mare: max(own, floor)); BEST_TARGET = "
                     "target with the highest score among the row's base type, BEST_SCORE = that score. "
                     "targets[base].lunar_targets lists each target (builtin = today's target, = SCORE_TOTAL). "
                     "A SCORE_<TARGET> is only given when every counting criterion has both a lunar and an Earth "
                     "value; otherwise it is empty (no data) and cannot be BEST_TARGET: missing values never score "
                     "better than real ones. RANK stays the rank of SCORE_TOTAL."
                     + (" PREVIEW: unverified targets or criteria are included (--include-unverified); "
                        "not for real results." if mt_preview else "")
                     + (" Mare COMMON TOLERANCE (--mare-common-tolerance, team decision 15 Nov 2026): every Mare "
                        "target is scored with the built-in 20-cell target's tolerance per criterion (not its own), "
                        "so BEST_TARGET compares closeness to the lunar values, not tolerance width; SCORE_TOTAL and "
                        "RANK unchanged." if a.mare_common_tolerance else ""))}
    if glim:
        targets["_material"] = glim["meta"]
    if macro is not None:
        targets["_rock_site"] = ms.export_meta(macro)
    if c30 is not None:
        lt = cfg["lunar_targets"].get("mare", {}).get("criteria", {}).get("c30_small_craters") or {}
        targets["_mare_c30"] = {
            "column": "SMALL_CRATERS_PER_KM2", "file": "raw_values.csv", "base_type": "mare", "criterion": "c30_small_craters",
            "score_method": "display", "weight": 0, "counts": False,
            "earth_unit": "closed depressions per km2 (>= 10 m deep, >= 300 m wide, elongation <= 2) within 5 km of the base pad",
            "moon": {"value": lt.get("value"), "iqr": lt.get("iqr"), "n_cells": lt.get("n_cells"), "source": lt.get("source"),
                     "verified": lt.get("verified"), "check": lt.get("check")},
            "note": ("Display only (team decision 15 Nov 2026), never in a score; empty = no data. Computed for the 500 "
                     "places of the night run's Mare shortlist, not a new search. On Earth most values are 0 and the "
                     "high ones lie in sand seas (dune hollows, not impact craters); docs/MARE_V11.md.")}
    (a.out / "targets.json").write_text(json.dumps(targets, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    heat = [{"lat": x["_centre"][0], "lng": x["_centre"][1], "weight": round(x["SCORE_TOTAL"], 4),
             "base": x["BASE_TYPE"]} for x in rows if x["SCORE_TOTAL"] is not None and not x.get("EXCLUDED")]
    (a.out / "heatmap.json").write_text(json.dumps(heat, indent=1) + "\n", encoding="utf-8")

    # every searched cell -> coverage per 1 deg tile + region counts; cells.json only near ranked/kept places
    # (config-v1.1: excluded places are not anchors, but their own cell is written with status "excluded")
    anchors = [x["_centre"] for x in rows if x["RUN"] and x["_centre"][0] is not None and not x.get("EXCLUDED")]
    by_id = {(x["RUN"], x["CELL"]): x for x in rows if x["RUN"]}
    dup_cells = {(x["RUN"], x["CELL"]) for x, _ in duplicates}
    buckets = {}                                           # 1 deg buckets: only nearby anchors are checked
    for la, lo in anchors:
        buckets.setdefault((math.floor(la), math.floor(lo)), []).append((la, lo))

    def near_anchor(lat, lon):
        dlat = int(math.ceil(a.cells_near_km / 110.6))
        dlon = int(math.ceil(a.cells_near_km / (111.3 * max(math.cos(math.radians(lat)), 0.02))))
        fy, fx = math.floor(lat), math.floor(lon)
        for y in range(fy - dlat, fy + dlat + 1):
            for x in range(fx - dlon, fx + dlon + 1):
                for la, lo in buckets.get((y, (x + 180) % 360 - 180), ()):
                    if _dist_km(lat, lon, la, lo) <= a.cells_near_km:
                        return True
        return False
    cells, cov, reg_count = [], {}, {}
    for p, name, radar, _ in runs:
        gj = p / "cells.geojson"
        if not gj.exists():
            continue
        base = radar["base_type"]
        for f in json.loads(gj.read_text(encoding="utf-8"))["features"]:
            pr = f["properties"]
            hit = by_id.get((name, pr["id"]))
            override = ("excluded" if hit is not None and hit.get("EXCLUDED") else
                        "duplicate" if (name, pr["id"]) in dup_cells else None)
            st = cell_status(pr, hit is not None and (hit["SCORE_TOTAL"] is not None or base == "mare"), base, override)
            lat, lon = pr.get("lat"), pr.get("lon")
            t = cov.setdefault(f"{math.floor(lat)}_{math.floor(lon)}", {"lat": math.floor(lat), "lon": math.floor(lon)})
            b = t.setdefault(base, {})
            b["searched"] = b.get("searched", 0) + 1
            b[st] = b.get(st, 0) + 1
            rg = region_of(name, pr["id"], lat, lon, regions)
            rk = rg["name"] if rg else name
            rc = reg_count.setdefault(rk, {}).setdefault(base, {})
            rc[st] = rc.get(st, 0) + 1
            if hit or near_anchor(lat, lon):
                ring = f["geometry"]["coordinates"][0]
                lons, lats = [c[0] for c in ring], [c[1] for c in ring]
                cells.append({"run": name, "cell": pr["id"], "base": base, "lat": lat, "lng": lon,
                              "bbox": [round(min(lons), 5), round(min(lats), 5), round(max(lons), 5), round(max(lats), 5)],
                              "status": st, "reason": (hit["EXCLUDED"] if st == "excluded" else
                                                       "same bowl as a region run" if st == "duplicate" else
                                                       pr.get("filter_reason") or pr.get("terrain_reason") or ""),
                              "site": hit["SITE"] if hit else None, "score_total": hit["SCORE_TOTAL"] if hit else None})
    (a.out / "cells.json").write_text(json.dumps(cells, indent=1) + "\n", encoding="utf-8")
    (a.out / "coverage.json").write_text(json.dumps(sorted(cov.values(), key=lambda t: (t["lat"], t["lon"])), indent=1)
                                         + "\n", encoding="utf-8")
    for x in rows:                                         # regions that only appear in the rows (no cells.geojson)
        if x["RUN"]:
            rg = region_of(x["RUN"], x["CELL"], x["LAT"], x["LON"], regions)
            if rg:
                reg_count.setdefault(rg["name"], {})
    reg_out = [{k: rg.get(k) for k in ("name", "title", "bbox", "role", "country")} | {"cells": reg_count[rg["name"]]}
               for rg in regions if rg["name"] in reg_count]
    known_names = {r["name"] for r in reg_out}
    reg_out += [{"name": rk, "title": rk, "bbox": None, "role": "", "country": "", "cells": c}
                for rk, c in reg_count.items() if rk not in known_names]
    (a.out / "regions.json").write_text(json.dumps(reg_out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    n_by = {b: sum(1 for x in rows if x["BASE_TYPE"] == b and x["ROLE"] != "missed") for b in ref}
    cmdline = recreate_line(ap, a)
    readme = f"""# outputs/ for the app

Written by `src/export_app.py` from {len(runs)} runs: {', '.join(n for _, n, _, _ in runs)}.
Base types: {', '.join(f"{b} ({n_by[b]} rows)" for b in ref)}; plus {len(missed)} missed known sites.

| File | What it is |
|---|---|
| `scores.csv` | one row per ranked (Polar) / kept (Mare) cell + missed known sites: `SITE,LAT,LON`, one 0–1 column per criterion, display columns, then `{','.join(EXTRA_COLS)}` |
| `raw_values.csv` | same rows, raw Earth values (units in `targets.json` → `earth_unit`), impact match, base pad |
| `targets.json` | per base type: each column's meaning, `counts`, `weight`, `score_method`, raw Moon value + unit + source |
| `heatmap.json` | `[{{lat, lng, weight, base}}]` per scored cell (cell centre), weight = `SCORE_TOTAL` |
| `cells.json` | cells within {a.cells_near_km:g} km of a ranked/kept place ({len(cells)}): `bbox`, `status`, `reason` |
| `coverage.json` | every searched cell counted per 1° tile and base type ({len(cov)} tiles): searched / filtered / prefilter / no_bowl / ice_floor / dropped / ranked (Polar) or kept (Mare) |
| `regions.json` | regions in this export: title, bbox, **role** (tuning / validation / screening), country, cell counts |

## Columns
- **0–1 criterion columns** = similarity to the Moon (1 = same). Empty = no data / no similarity yet. The meaning
  depends on `BASE_TYPE`: read it through `targets[BASE_TYPE]` (DRIVABLE is a display share for Polar and a scored
  similarity for Mare).
- **`SCORE_TOTAL`** = score vs Moon (counted criteria only); **`RANK`** = rank within the same `BASE_TYPE`.
- **`TERRAIN_SCORE` / `LIGHT_SCORE`** = the same weighted mean over the counted terrain / light criteria only.
- **`NAME`** = known site (site_info) or confirmed impact structure, else {"the nearest place (see Place names below)" if names else "`<region title> <cell>`"}. **`COUNTRY`** =
  {"per place, Natural Earth polygon (see Place names below)" if names else "region level (approximate, from the region registry, no per-cell lookup)"}.
- **`ROLE`** = tuning / validation / screening (from the region), or **missed** for known sites the pipeline does
  not rank; `MISSED_REASON` says why ({', '.join(m['name'] for m in missed)}).
- **`LAT`/`LON`** = Polar: the crater's low point; Mare: the base pad.
{"- **`EXCLUDED`** = config-v1.1 post-run filter reason(s); empty = not excluded (see below)." + chr(10) if post else ""}- {"Mare scores: similarity to the frozen mare-v1 lunar target (`targets.json` → mare)." if any(x["BASE_TYPE"] == "mare" and x["SCORE_TOTAL"] is not None for x in rows) else "Mare scores stay **empty** until the lunar Mare targets (Mateo) are verified; raw values are already there."}
{"" if not cmdline else chr(10) + "Re-create: `" + cmdline + "`" + chr(10)}
## Display-only columns (Polar, weight 0, never in SCORE_TOTAL)
{chr(10).join(f"- **{c}** ({v[2]}): {v[3]}" for c, v in DISPLAY_COLUMNS.items())}
- Impact list: {len(impacts)} confirmed structures (incomplete; "0" = not in this list).

## No Earth analog possible: GRAZING_SUN (Polar)
{FACTS["c4_grazing_sun"]}

## Known limitation: Sun disc vs Sun centre (SUNNY_RIDGE, DARK_FLOOR, LIGHT_NEAR_DARK)
{DISC_VS_CENTRE}
"""
    if multi:
        readme += (f"""
## Several lunar targets ("closest lunar twin"){" — PREVIEW, includes unverified targets" if mt_preview else ""}
Columns after `MISSED_REASON`: {', '.join(f'`{c}`' for c in mt_cols)}. `SCORE_<TARGET>` = score vs Moon against that
target (same rule, weights and tolerances as `SCORE_TOTAL`; today's target equals `SCORE_TOTAL`); `BEST_TARGET` /
`BEST_SCORE` = best-matching target of the row's base type. Targets: `targets[BASE_TYPE].lunar_targets`
(see docs/MULTI_TARGET.md). Targets used: {', '.join(t['name'] for t in lunar_targets)}.
**Missing values never score better than real ones:** a `SCORE_<TARGET>` is only given when every counting
criterion has both a lunar and an Earth value; otherwise it is empty and that target cannot be `BEST_TARGET`.
`RANK` stays the rank of `SCORE_TOTAL`. The place per cell is the bowl chosen against today's target (one place per
cell in `ranking.csv`); another target might prefer a different bowl in the same cell.

| base | BEST_TARGET | places (excluded included) |
|---|---|---|
""" + "".join(f"| {b} | {bt} | {n} |\n" for (b, bt), n in sorted(_count_best(rows).items())))
    if glim:
        mc = glim["meta"]
        n_rock = {}
        for x in rows:
            if x.get("_rock") is not None:
                v = x["_rock"]["BASALT_REGION"]
                k = (x["BASE_TYPE"], "no data" if v is None else str(int(v)))
                n_rock[k] = n_rock.get(k, 0) + 1
        readme += f"""
## Rock class (GLiM, display only; never in a score)
`raw_values.csv` columns {', '.join(f'`{c}`' for c in ROCK_COLS)}, at the Polar low point / Mare base pad (`LAT`/`LON`).
- `ROCK_CLASS` = first-level GLiM code of the grid cell under the point (`vb` = basic volcanic = basalt; names in
  `ROCK_CLASS_NAME` and `targets.json` -> `_material.classes`); empty = no data (sea or GLiM "nd").
- `BASALT_REGION` = 1 if `ROCK_CLASS` is `vb`, 0 for any other class (team decision 15 Nov 2026).
  `BASALT_SHARE_5KM` = share of `vb` within {mc['radius_km']:g} km, relative to the part of the disc that has GLiM data;
  `GLIM_COVERED_SHARE` = that part (0-1). A point in a grid cell GLiM counts as sea (coasts, islands) or GLiM "nd"
  is **no data**: class, flag and share empty, nothing borrowed from neighbouring cells, never 0.
- **Caveat: {mc['caveat']}.** Source = {mc['source']}. One dominant class per 0.5 deg cell (~55 km); small lava
  fields vanish. GLiM has no anorthosite class (c22 cannot be scored). Details: docs/MATERIAL.md.

| base | BASALT_REGION | places |
|---|---|---|
""" + "".join(f"| {b} | {v} | {n} |\n" for (b, v), n in sorted(n_rock.items()))
    if macro is not None:
        readme += ms.export_readme(macro)
    if post:
        pc = post.cfg
        pol = [x for x in rows if x["BASE_TYPE"] in post.base_types and x["RUN"]]
        mine_r, dry_r = pc["mine"]["reason"], pc["dry_bowl"]["reason"]
        n_mine = sum(1 for x in pol if mine_r in x["EXCLUDED"])
        n_dry = sum(1 for x in pol if dry_r in x["EXCLUDED"])
        n_both = sum(1 for x in pol if mine_r in x["EXCLUDED"] and dry_r in x["EXCLUDED"])
        n_ex = sum(1 for x in pol if x["EXCLUDED"])
        near = [x for x in pol if not x["EXCLUDED"] and x["_pf"] and x["_pf"]["mine_dist_km"] is not None
                and x["_pf"]["mine_dist_km"] <= pc["mine"].get("near_km", 1.0)]
        db = pc["dry_bowl"]
        readme += f"""
## config-v1.1: post-run filters (Polar only; config-v1 scoring unchanged)
Rules in `{a.post_filters.as_posix()}`, code `src/post_filters.py`. An excluded place keeps `SCORE_TOTAL` and its raw
values, gets **`EXCLUDED`** = reason(s) (`raw_values.csv` → `EXCLUDED_DETAIL`), has **no `RANK`** and **no heatmap point**;
its cell has status `excluded` in `cells.json`. Remaining places keep their scores; only their ranks move up.
- **`{mine_r}`**: low point inside a mining polygon of Maus et al. (2022), Global-scale mining polygons v2,
  PANGAEA https://doi.org/10.1594/PANGAEA.942325 (CC BY-SA 4.0). {"**NOT APPLIED: " + post.mines_missing + "**" if post.mines_missing else f"{post.mines.n} polygons."}
- **`{dry_r}`**: `BARE_SHARE` < {db['bare_min']:g} or `ICE_FLOOR_SHARE` > {db['ice_floor_max']:g} or `ICE_RIM_SHARE` > {db['ice_rim_max']:g}
  (WorldCover 2021 shares from config-v1; an empty share = no data = not tested).

| Polar places in this export | count |
|---|---|
| before the filters | {len(pol)} |
| {mine_r} | {n_mine} |
| {dry_r} | {n_dry} |
| both reasons | {n_both} |
| excluded in total | {n_ex} |
| ranked after the filters | {len(pol) - n_ex - sum(1 for x in pol if x["SCORE_TOTAL"] is None and not x["EXCLUDED"])} |

Not excluded but within {pc["mine"].get("near_km", 1.0):g} km of a mining polygon (`MINE_DIST_KM`, for a manual look): {len(near)}{" (ranks " + ", ".join(str(x["RANK"]) for x in sorted(near, key=lambda x: x["RANK"] or 1e9)[:15]) + (" ..." if len(near) > 15 else "") + ")" if near else ""}.
"""
    if names:
        readme += """
## Place names (offline)
`NAME` (when no known site or impact structure matches) = nearest populated place from GeoNames `cities1000`
(CC BY 4.0, https://www.geonames.org), "34 km SW of Balkhash"; among places within 1.5 × the nearest distance the
most populous is used. Beyond 60 km the Natural Earth geographic region is added, beyond 400 km only the region is
shown. `COUNTRY` = Natural Earth 1:10m Admin 0 polygon containing the point (public domain; de-facto borders as
Natural Earth draws them). Computed per place by `src/place_names.py`; no web lookup.
"""
    if duplicates:
        readme += f"""
## Same bowl in two runs ({len(duplicates)} rows dropped, `--dedupe-km {a.dedupe_km:g}`)
The region run's row is kept (tuning sites keep the values their docs quote); the night (world-grid) row is dropped,
its cell has status `duplicate` in `cells.json`. Scores differ slightly because the 60 m grid is laid on a different cell.

| dropped (run cell, score) | kept (run cell, score) |
|---|---|
""" + "".join(f"| {x['RUN']} {x['CELL']}, {_fmt(x['SCORE_TOTAL'])} | {k['RUN']} {k['CELL']}, {_fmt(k['SCORE_TOTAL'])} |\n"
              for x, k in duplicates)
    (a.out / "README.md").write_text(readme, encoding="utf-8")
    print(f"{len(rows)} rows ({', '.join(f'{b} {n_by[b]}' for b in ref)}, missed {len(missed)}) from {len(runs)} runs -> {a.out}")
    for x in rows[:12]:
        print(f"  {x['BASE_TYPE']} {x['RANK']}. {x['SITE']} [{x['ROLE']}; {x['COUNTRY']}] total {x['SCORE_TOTAL']} "
              f"terrain {x['TERRAIN_SCORE']} light {x['LIGHT_SCORE']}")


if __name__ == "__main__":
    main()
