"""Night run: many regions, two tracks, resumable. Raw values are stored, scoring is re-run separately.

    python src/night_run.py                       # all regions of config/night_regions.yaml, tracks A + B
    python src/night_run.py --only tibesti        # one region
    python src/night_run.py --score               # morning: rankings from the stored raw values -> out/night_*/
    python src/night_run.py --status              # progress summary

Tracks
    A  Polar crater (config-v1, frozen): pipeline.run.cell_candidates per kept cell -> all candidate places
       with raw values. Prefilter: the cell's buffered DEM window has less relief than
       polar.min_depression_depth_m -> no bowl possible, skipped (status no_bowl, reason "prefilter").
    B  Mare (pipeline.run_mare.cell_mare). Prefilter: cell relief above settings.mare_prefilter_relief_m.
    C  Polar light (separate heavier light pass): NOT built (time).
Stage 0 (shared by all tracks, per 1 deg tile): land-cover filter for the tile's cells (the cell grid is made
on the WHOLE region, cells are assigned to the tile holding their centre, so no cells are lost at tile edges),
DEM read once (buffer = max of both tracks' buffers + 1 km). Cached as .npz in the work directory.

Work directory (default %LOCALAPPDATA%/espaceodyssey_night, outside OneDrive):
    cache/<tile>/stage0.npz, rows.json     raw/<track>/<tile>.jsonl     progress.json     night.log
Resume: a tile/track listed as done in progress.json is skipped. Failures are retried with waits
(settings.retries / retry_wait_s); a tile that still fails is marked failed and the run goes on.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dem.fetch import read_bbox  # noqa: E402
from dem.landcover import read_landcover  # noqa: E402
from pipeline.cells import make_grid, window_of  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.filters import check_classes, evaluate_cell, padded_bbox, pixel_masks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
REGIONS = ROOT / "config" / "night_regions.yaml"
WORK = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "espaceodyssey_night"


class _NP(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return None if not math.isfinite(o) else float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
        return str(o)


class Night:
    def __init__(self, work: Path, regions_path: Path):
        self.work = work
        self.work.mkdir(parents=True, exist_ok=True)
        spec = yaml.safe_load(regions_path.read_text(encoding="utf-8"))
        self.regions = sorted(spec["regions"], key=lambda r: r["priority"])
        self.s = spec["settings"]
        self.cfg = load_config()
        self.prog_path = work / "progress.json"
        self.prog = json.loads(self.prog_path.read_text()) if self.prog_path.exists() else {"tiles": {}}
        self.logf = open(work / "night.log", "a", encoding="utf-8")

    # --- bookkeeping ----------------------------------------------------------------------------
    def log(self, msg):
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
        print(line, flush=True)
        self.logf.write(line + "\n")
        self.logf.flush()

    def save(self):
        tmp = self.prog_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.prog, indent=1))
        os.replace(tmp, self.prog_path)                           # atomic: a crash never leaves half a file

    def tiles(self, region):
        """[(tile_id, tile bbox, [cells])] with cells from the region-wide grid, assigned by centre."""
        w, s, e, n = region["bbox"]
        cells = make_grid(w, s, e, n, self.cfg["grid"]["cell_km"])
        for c in cells:
            c["id"] = f"{region['name']}_{c['id']}"
        d = self.s["tile_deg"]
        out = {}
        for c in cells:
            lon, lat = (c["west"] + c["east"]) / 2, (c["south"] + c["north"]) / 2
            tx, ty = math.floor((lon - w) / d), math.floor((lat - s) / d)
            tid = f"{region['name']}_t{ty:02d}_{tx:02d}"
            out.setdefault(tid, []).append(c)
        res = []
        for tid, cs in sorted(out.items()):
            bb = (min(c["west"] for c in cs), min(c["south"] for c in cs),
                  max(c["east"] for c in cs), max(c["north"] for c in cs))
            res.append((tid, bb, cs))
        return res

    def with_retries(self, what, fn):
        waits = list(self.s["retry_wait_s"])
        for attempt in range(1, self.s["retries"] + 1):
            try:
                return fn()
            except Exception as e:                                # network / S3 / GDAL errors
                self.log(f"  {what}: attempt {attempt} failed: {type(e).__name__}: {e}")
                if attempt == self.s["retries"]:
                    raise
                wait = waits[min(attempt - 1, len(waits) - 1)]
                self.log(f"  waiting {wait} s before retrying")
                time.sleep(wait)

    # --- stage 0 --------------------------------------------------------------------------------
    def stage0(self, tid, bb, cells):
        d = self.work / "cache" / tid
        if (d / "stage0.npz").exists() and (d / "rows.json").exists():
            z = np.load(d / "stage0.npz", allow_pickle=False)
            rows = json.loads((d / "rows.json").read_text())
            from rasterio import Affine
            if z["dem"].size:                                     # DEM cache may have been deleted after the tile
                return rows, z["lc"], Affine(*z["lc_tf"]), z["dem"], Affine(*z["dem_tf"])
        d.mkdir(parents=True, exist_ok=True)
        fcfg = self.cfg["filter"]
        check_classes(fcfg)
        pad = max(fcfg["built_up_buffer_m"], fcfg["water_buffer_m"])
        lc, lc_tf = read_landcover(*padded_bbox(*bb, pad), fcfg["landcover_res_m"])
        masks = pixel_masks(lc, lc_tf, fcfg)
        rows = [r for r in (evaluate_cell(c, lc, lc_tf, masks, fcfg, None, self.cfg["grid"]["cell_km"]) for c in cells) if r]
        buf = max(self.cfg["polar"]["buffer_m"], self.cfg["mare"]["radius_km"] * 1000 + 500) + 1000
        dem, prof = read_bbox(*padded_bbox(*bb, buf), res=self.res)
        np.savez_compressed(d / "stage0.npz", lc=lc, lc_tf=np.array(tuple(lc_tf)[:6]), dem=dem,
                            dem_tf=np.array(tuple(prof["transform"])[:6]))
        (d / "rows.json").write_text(json.dumps(rows, cls=_NP))
        return rows, lc, lc_tf, dem, prof["transform"]

    # --- tracks ---------------------------------------------------------------------------------
    def track_a(self, rows, lc, lc_tf, dem, dem_tf):
        from pipeline.run import cell_candidates
        p = self.cfg["polar"]
        masks = pixel_masks(lc, lc_tf, self.cfg["filter"])
        ice = np.isin(lc, p["ice_classes"])
        out = []
        for r in rows:
            rec = {"cell": r, "info": None, "cands": [], "prefilter": None}
            if r["keep"]:
                pw, ps, pe, pn = padded_bbox(r["west"], r["south"], r["east"], r["north"], p["buffer_m"])
                rs, cs = window_of({"west": pw, "south": ps, "east": pe, "north": pn}, dem_tf, dem.shape)
                win = dem[rs, cs]
                relief = float(np.nanmax(win) - np.nanmin(win)) if np.isfinite(win).any() else 0.0
                if relief < p["min_depression_depth_m"]:
                    rec["prefilter"] = f"prefilter: buffered window relief {relief:.0f} m < {p['min_depression_depth_m']:g} m"
                else:
                    info, cands = cell_candidates(r, dem, dem_tf, masks["usable"], lc_tf, self.cfg, ice=ice, lc=lc)
                    rec["info"], rec["cands"] = info, cands
            out.append(rec)
        return out

    def track_b(self, rows, lc, lc_tf, dem, dem_tf):
        from pipeline.run_mare import cell_mare
        masks = pixel_masks(lc, lc_tf, self.cfg["filter"])
        lim = self.s["mare_prefilter_relief_m"]
        out = []
        for r in rows:
            rec = {"cell": r, "res": None, "prefilter": None}
            if r["keep"]:
                rs, cs = window_of(r, dem_tf, dem.shape)
                win = dem[rs, cs]
                relief = float(np.nanmax(win) - np.nanmin(win)) if np.isfinite(win).any() else None
                if relief is None:
                    rec["prefilter"] = "prefilter: no DEM data in cell"
                elif relief > lim:
                    rec["prefilter"] = f"prefilter: cell relief {relief:.0f} m > {lim:g} m (not a plain)"
                else:
                    rec["res"] = cell_mare(r, dem, dem_tf, masks["usable"], lc_tf, self.cfg)
            out.append(rec)
        return out

    # --- main loop ------------------------------------------------------------------------------
    def run(self, only=None, tracks=("A", "B"), res=30):
        self.res = res
        todo = [(rg, t) for rg in self.regions if not only or rg["name"] in only for t in self.tiles(rg)]
        n_tiles = len(todo)
        self.log(f"night run: {n_tiles} tiles, tracks {','.join(tracks)}, DEM {res} m, work dir {self.work}")
        t_start, done_now = time.time(), 0
        for k, (rg, (tid, bb, cells)) in enumerate(todo, 1):
            st = self.prog["tiles"].setdefault(tid, {"region": rg["name"], "bbox": bb, "n_cells": len(cells)})
            if all(st.get(t) == "done" for t in tracks):
                continue
            t0 = time.time()
            try:
                rows, lc, lc_tf, dem, dem_tf = self.with_retries(f"{tid} stage 0", lambda: self.stage0(tid, bb, cells))
                st["stage0"] = "done"
                st["n_kept"] = sum(r["keep"] for r in rows)
                for t in tracks:
                    if st.get(t) == "done":
                        continue
                    t1 = time.time()
                    fn = self.track_a if t == "A" else self.track_b
                    recs = self.with_retries(f"{tid} track {t}", lambda: fn(rows, lc, lc_tf, dem, dem_tf))
                    path = self.work / "raw" / t / f"{tid}.jsonl"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp = path.with_suffix(".tmp")
                    with open(tmp, "w", encoding="utf-8") as f:
                        for rec in recs:
                            f.write(json.dumps(rec, cls=_NP) + "\n")
                    os.replace(tmp, path)
                    st[t] = "done"
                    st[f"{t}_s"] = round(time.time() - t1, 1)
                    self.save()
                if not self.s["keep_dem_cache"]:
                    z = np.load(self.work / "cache" / tid / "stage0.npz")
                    np.savez_compressed(self.work / "cache" / tid / "stage0.npz", lc=z["lc"], lc_tf=z["lc_tf"],
                                        dem=np.zeros((0, 0), np.float32), dem_tf=z["dem_tf"])
                    st["dem_cache"] = "deleted"
            except Exception as e:
                st["error"] = f"{type(e).__name__}: {e}"
                st["traceback"] = traceback.format_exc()[-1500:]
                for t in tracks:
                    st.setdefault(t, "failed")
                self.log(f"{tid}: FAILED after retries: {st['error']}")
            st["tile_s"] = round(time.time() - t0, 1)
            self.save()
            done_now += 1
            el = time.time() - t_start
            left = sum(1 for _, (t2, _, _) in todo[k:] if not all(self.prog["tiles"].get(t2, {}).get(x) == "done" for x in tracks))
            self.log(f"{tid} ({k}/{n_tiles}, {len(cells)} cells, kept {st.get('n_kept')}) in {st['tile_s']} s | "
                     f"A {st.get('A_s', '-')} s B {st.get('B_s', '-')} s | ETA ~{el / done_now * left / 60:.0f} min")
        self.log("night run finished")

    # --- morning: scoring from raw values -------------------------------------------------------
    def score(self, tracks=("A", "B"), out_root=ROOT / "out"):
        for t in tracks:
            recs = []
            for path in sorted((self.work / "raw" / t).glob("*.jsonl")):
                with open(path, encoding="utf-8") as f:
                    recs += [json.loads(line) for line in f]
            if not recs:
                self.log(f"score: no raw records for track {t}")
                continue
            bb = (min(r["cell"]["west"] for r in recs), min(r["cell"]["south"] for r in recs),
                  max(r["cell"]["east"] for r in recs), max(r["cell"]["north"] for r in recs))
            if t == "A":
                self._score_a(recs, bb, out_root / "night_polar")
            else:
                self._score_b(recs, bb, out_root / "night_mare")

    def _score_a(self, recs, bb, out_dir):
        from pipeline.polar import CRITERIA, best_of, select_best
        from pipeline.run import write_outputs
        from pipeline.scoring import method, score_direct
        crit = self.cfg["polar"]["criteria"]
        all_c = []
        for r in recs:
            for c in r["cands"]:
                for name in CRITERIA:                              # re-score from raw with the CURRENT config
                    sc = score_direct(c.get(name), crit[name])
                    c[f"s_{name}"] = None if sc is None else round(sc, 4)
                all_c.append(c)
        select_best(all_c, crit)
        out_rows = []
        for r in recs:
            row = {**r["cell"], "filter_reason": r["cell"]["reason"], "terrain_reason": ""}
            if r["prefilter"]:
                row.update(keep=False, terrain_reason=r["prefilter"], score=None)
            elif r["info"] is not None:
                info, cands = r["info"], r["cands"]
                best = best_of(cands)
                row.update({k: v for k, v in info.items() if k not in ("keep", "reason")})
                row["n_candidates"] = len(cands)
                if best is None:
                    reason = info["reason"] or "no valid candidate"
                    row.update({**(cands[0] if cands else {}), "keep": False, "reason": reason,
                                "terrain_reason": reason, "score": None, "rank_score": None})
                else:
                    row.update({k: v for k, v in best.items() if k != "cell_id"})
            for c in CRITERIA:
                row.setdefault(c, None)
                row.setdefault(f"s_{c}", None)
                row[f"method_{c}"] = method(crit[c])
            if not row.get("keep"):
                row["score"], row["n_scored"], row["rank_score"], row["n_ranked"] = None, 0, None, 0
            out_rows.append(row)
        ranked = sorted([r for r in out_rows if r.get("keep") and r.get("score") is not None], key=lambda r: -r["score"])
        for k, r in enumerate(ranked, 1):
            r["rank"] = k
        write_outputs(str(out_dir), bb, self.res, self.cfg, out_rows, ranked)
        self.log(f"score A: {len(recs)} cells, {len(ranked)} ranked -> {out_dir}")

    def _score_b(self, recs, bb, out_dir):
        from pipeline.mare import MARE_CRITERIA
        from pipeline.run_mare import write_mare_outputs
        from pipeline.scoring import method, score_direct, total_score
        crit = self.cfg["mare"]["criteria"]
        out_rows = []
        for r in recs:
            row = {**r["cell"], "filter_reason": r["cell"]["reason"], "terrain_reason": ""}
            if r["prefilter"]:
                row.update({c: None for c in MARE_CRITERIA}, keep=False, terrain_reason=r["prefilter"], score=None, n_scored=0)
            elif r["res"] is not None:
                res = r["res"]
                for name in MARE_CRITERIA:
                    sc = score_direct(res.get(name), crit[name])
                    res[f"s_{name}"] = None if sc is None else round(sc, 4)
                row.update(res)
                row["terrain_reason"] = res["reason"] if not res["keep"] else ""
                row["score"], row["n_scored"] = total_score(row, crit) if res["keep"] else (None, 0)
            else:
                row.update({c: None for c in MARE_CRITERIA}, score=None, n_scored=0)
            for c in MARE_CRITERIA:
                row[f"method_{c}"] = method(crit[c])
            row["lon"] = round((row["west"] + row["east"]) / 2, 5)
            row["lat"] = round((row["south"] + row["north"]) / 2, 5)
            out_rows.append(row)
        kept = write_mare_outputs(str(out_dir), bb, self.res, self.cfg, out_rows, len(out_rows))
        self.log(f"score B: {len(recs)} cells, {len(kept)} kept -> {out_dir}")

    def status(self):
        tiles = self.prog["tiles"]
        by = {}
        for st in tiles.values():
            key = (st["region"], st.get("A", "-"), st.get("B", "-"))
            by[key] = by.get(key, 0) + 1
        for k, v in sorted(by.items()):
            print(f"  {k[0]:16} A {k[1]:7} B {k[2]:7} : {v} tiles")
        fails = {t: st["error"] for t, st in tiles.items() if st.get("error")}
        if fails:
            print("  failed:", json.dumps(fails, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=WORK)
    ap.add_argument("--regions", type=Path, default=REGIONS)
    ap.add_argument("--only", nargs="*", help="region names")
    ap.add_argument("--tracks", default="A,B")
    ap.add_argument("--res", type=int, default=30, choices=[30, 90])
    ap.add_argument("--score", action="store_true", help="score the stored raw values (no downloads)")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    night = Night(a.work, a.regions)
    night.res = a.res
    tracks = tuple(a.tracks.split(","))
    if a.status:
        night.status()
    elif a.score:
        night.score(tracks)
    else:
        night.run(a.only, tracks, a.res)


if __name__ == "__main__":
    main()
