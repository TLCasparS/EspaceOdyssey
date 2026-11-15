"""Mare display additions on the night run's Mare shortlist (B2: the 500 places mare-v1 selected; NOT a new
global search).

Per B2 record (<work>/raw/B2/*.jsonl): the stored 60 m DEM crop (<work>/crops/B2/..., night_run.save_crop) and the
stored base spot (base_lon/base_lat -> pixel of the crop) -> pipeline.mare.small_crater_density = c30.
Missing crop / unreadable crop = no data (None), never 0. Check per place: the base-pad slope recomputed on the
crop must match the stored c10 (else the pixel is not the base spot) -> otherwise c30 = None + reason.

Then scores, before (mare-v1) and after (display additions; identical totals while c30 weight = 0):
  before: SCORE_TOTAL = mare-v1 (4 criteria, 20-cell target); BEST_TARGET with each target's own tolerance
          (the rule of the current export, multi_target.build_targets)
  after:  SCORE_TOTAL with c30 at weight mare_v11.c30_weight (0 = mare-v1); BEST_TARGET with the common tolerance
Outputs in out/mare_v11/ (git-ignored): places.csv, c30_earth.csv (cache), summary.json, and c30_<run>.csv
(RUN,CELL,C30_PER_KM2,C30_REASON; empty = no data) = the table for `export_app.py --mare-c30`.

    python src/mare_v11_rescore.py [--work %LOCALAPPDATA%/espaceodyssey_night] [--workers 8]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline import multi_target as mt  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.mare import C30, MARE_CRITERIA, small_crater_density  # noqa: E402
from pipeline.mare_v11 import V11_CRITERIA, v11_criteria, v11_targets  # noqa: E402
from pipeline.scoring import score_direct, total_score  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORK = Path(os.environ.get("LOCALAPPDATA", ".")) / "espaceodyssey_night"


def load_crop(path: Path):
    """(z float64 with NaN, affine 6-tuple, crs wkt, res_m) from a night_run crop npz."""
    d = np.load(path, allow_pickle=False)
    dm = d["z_dm"].astype(np.float64)
    z = np.where(d["z_dm"] == -32767, np.nan, float(d["z0_m"]) + dm / 10.0)
    return z, tuple(d["transform"]), str(d["crs_wkt"]), float(d["res_m"])


def base_pixel(lon, lat, tf, crs_wkt):
    from pyproj import Transformer
    x, y = Transformer.from_crs("EPSG:4326", crs_wkt, always_xy=True).transform(lon, lat)
    a, b, c, d, e, f = tf
    return int(np.floor((y - f) / e)), int(np.floor((x - c) / a))


def pad_slope(z, r, c, res_m, pad_m):
    """Mean slope (deg) of the k x k pad centred on (r, c), as pipeline.mare.base_pad (dem.terrain slope)."""
    from dem.grid import MetricGrid
    from dem.terrain import compute_terrain
    from rasterio.transform import Affine
    k = max(1, int(round(pad_m / res_m))) | 1
    h = k // 2 + 2
    sub = z[r - h - 1:r + h + 2, c - h - 1:c + h + 2]
    mg = MetricGrid(sub.astype(np.float32), Affine(res_m, 0, 0, 0, -res_m, 0), "EPSG:3857", res_m)
    s = compute_terrain(mg, relief_window_m=res_m * 3, roughness_window_px=3).slope_deg
    m = h + 1
    return float(np.nanmean(s[m - k // 2:m + k // 2 + 1, m - k // 2:m + k // 2 + 1]))


def c30_for(job):
    """job = (cell id, crop path or None, base lon, base lat, stored c10, c30 params, pad_m) -> dict."""
    cid, path, lon, lat, c10, p, pad_m = job
    out = {"id": cid, C30: None, "c30_reason": "", "c10_check": None}
    if not path or not Path(path).exists():
        out["c30_reason"] = "no crop (no data)"
        return out
    try:
        z, tf, wkt, res = load_crop(Path(path))
        r, c = base_pixel(lon, lat, tf, wkt)
        if not (0 <= r < z.shape[0] and 0 <= c < z.shape[1]):
            out["c30_reason"] = "base spot outside crop"
            return out
        chk = pad_slope(z, r, c, res, pad_m)
        out["c10_check"] = round(chk, 4)
        if c10 is not None and abs(chk - c10) > max(0.05, 0.2 * c10):
            out["c30_reason"] = f"base pad check failed (crop {chk:.3f} vs stored c10 {c10:.3f} deg)"
            return out
        out[C30] = small_crater_density(z, (r, c), res, p)
        if out[C30] is None:
            out["c30_reason"] = "5 km zone less than half covered (no data)"
    except Exception as e:                                   # unreadable crop -> no data, never 0
        out["c30_reason"] = f"crop error {type(e).__name__}: {e}"
    return out


def load_b2(work: Path) -> list[dict]:
    recs = []
    for path in sorted((work / "raw" / "B2").glob("*.jsonl")):
        with open(path, encoding="utf-8") as f:
            recs += [json.loads(line) for line in f if line.strip()]
    return recs


def earth_c30(recs, work: Path, cfg, cache: Path, workers: int) -> dict:
    if cache.exists():
        with open(cache, newline="", encoding="utf-8") as f:
            rows = {r["id"]: r for r in csv.DictReader(f)}
        for r in rows.values():
            r[C30] = float(r[C30]) if r[C30] not in ("", None) else None
        if len(rows) == len(recs):
            return rows
    p, pad_m = cfg["mare_v11"]["c30"], cfg["mare"]["pad_m"]
    jobs = []
    for rec in recs:
        res = rec.get("res") or {}
        crop = (rec.get("crop") or {}).get("path")
        jobs.append((rec["cell"]["id"], str(work / crop) if crop else None, res.get("base_lon"), res.get("base_lat"),
                     res.get("c10_flat_base"), p, pad_m))
    with ProcessPoolExecutor(workers) as ex:
        out = list(ex.map(c30_for, jobs, chunksize=4))
    cache.parent.mkdir(parents=True, exist_ok=True)
    with open(cache, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", C30, "c30_reason", "c10_check"])
        w.writeheader()
        for r in out:
            w.writerow({k: "" if v is None else v for k, v in r.items()})
    return {r["id"]: r for r in out}


def score_places(recs, c30: dict, cfg, c30_weight=None) -> list[dict]:
    """One row per kept B2 place with before / after scores."""
    old_crit = cfg["mare"]["criteria"]
    new_crit = v11_criteria(cfg, c30_weight)
    old_t = v11_targets(cfg, common_tolerance=False, c30_weight=0.0)       # 4 criteria, own tolerances
    old_t = [{**t, "criteria": {k: v for k, v in t["criteria"].items() if k != C30}} for t in old_t]
    new_t = v11_targets(cfg, c30_weight=c30_weight)
    rows = []
    for rec in recs:
        res = rec.get("res") or {}
        if not res.get("keep"):
            continue
        raw = {k: res.get(k) for k in MARE_CRITERIA}
        raw[C30] = (c30.get(rec["cell"]["id"]) or {}).get(C30)
        row = {"id": rec["cell"]["id"], "lat": rec["cell"].get("lat") or round((rec["cell"]["south"] + rec["cell"]["north"]) / 2, 5),
               "lon": rec["cell"].get("lon") or round((rec["cell"]["west"] + rec["cell"]["east"]) / 2, 5),
               "base_lat": res.get("base_lat"), "base_lon": res.get("base_lon"), **raw,
               "c30_reason": (c30.get(rec["cell"]["id"]) or {}).get("c30_reason", "")}
        for tag, crit in (("v1", old_crit), ("v11", new_crit)):
            s = {f"s_{k}": score_direct(raw.get(k), crit[k]) for k in crit}
            row[f"score_{tag}"] = total_score(s, crit)[0]
            if tag == "v11":
                row["s_c30"] = None if s[f"s_{C30}"] is None else round(s[f"s_{C30}"], 4)
        for tag, tg in (("v1", old_t), ("v11", new_t)):
            sc = {t["name"]: mt.score(raw, t) for t in tg}
            row[f"best_target_{tag}"], row[f"best_score_{tag}"] = mt.best(sc)
            for t in tg:
                row[f"{t['column']}_{tag}"] = sc[t["name"]]
        rows.append(row)
    return rows


def ranked(rows, key):
    s = sorted([r for r in rows if r.get(key) is not None], key=lambda r: -r[key])
    return {r["id"]: i + 1 for i, r in enumerate(s)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, default=DEFAULT_WORK)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "mare_v11")
    ap.add_argument("--whatif-weight", type=float, default=1.0, help="extra columns *_w: scores with this c30 weight")
    ap.add_argument("--run-name", default="night_mare", help="export run folder of the B2 records (RUN in the c30 table)")
    a = ap.parse_args()
    np.seterr(invalid="ignore")
    cfg = load_config()
    recs = load_b2(a.work)
    c30 = earth_c30(recs, a.work, cfg, a.out / "c30_earth.csv", a.workers)
    with open(a.out / f"c30_{a.run_name}.csv", "w", newline="", encoding="utf-8") as f:   # export_app --mare-c30
        w = csv.writer(f)
        w.writerow(["RUN", "CELL", "C30_PER_KM2", "C30_REASON"])
        for rec in recs:
            cid = rec["cell"]["id"]
            v = (c30.get(cid) or {}).get(C30)
            w.writerow([a.run_name, cid, "" if v is None else v, (c30.get(cid) or {}).get("c30_reason", "")])
    rows = score_places(recs, c30, cfg)
    wi = {r["id"]: r for r in score_places(recs, c30, cfg, c30_weight=a.whatif_weight)}
    for r in rows:
        w = wi[r["id"]]
        r["score_v11_w"], r["best_target_v11_w"], r["best_score_v11_w"] = (w["score_v11"], w["best_target_v11"],
                                                                         w["best_score_v11"])
    rk1, rk2, rk3 = ranked(rows, "score_v1"), ranked(rows, "score_v11"), ranked(rows, "score_v11_w")
    for r in rows:
        r["rank_v1"], r["rank_v11"], r["rank_v11_w"] = rk1.get(r["id"]), rk2.get(r["id"]), rk3.get(r["id"])
    rows.sort(key=lambda r: (r["rank_v11"] is None, r["rank_v11"] or 0))
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(a.out / "places.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: "" if r.get(k) is None else (round(r[k], 4) if isinstance(r[k], float) else r[k]) for k in cols})
    vals = [r[C30] for r in rows if r[C30] is not None]
    summ = {"n_records": len(recs), "n_kept": len(rows), "n_c30": len(vals),
            "n_c30_no_data": len(rows) - len(vals),
            "c30_earth": {"min": min(vals), "p25": float(np.percentile(vals, 25)), "median": float(np.median(vals)),
                          "p75": float(np.percentile(vals, 75)), "max": max(vals),
                          "share_zero": float(np.mean(np.array(vals) == 0))} if vals else None,
            "whatif_c30_weight": a.whatif_weight, "c30_weight": cfg["mare_v11"]["c30_weight"],
            "best_target_v1": {}, "best_target_v11": {}, "best_target_v11_w": {}}
    for tag in ("v1", "v11", "v11_w"):
        for r in rows:
            k = r[f"best_target_{tag}"] or "no data"
            summ[f"best_target_{tag}"][k] = summ[f"best_target_{tag}"].get(k, 0) + 1
    (a.out / "summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
