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
        self.cand, self._cur = {}, None                      # world mode: candidate cell ids per tile and track

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
    def stage0(self, tid, bb, cells, need_dem: bool = True):
        """(rows, lc, lc_tf, dem30, dem_tf). need_dem=False (only B1 on this tile): no 30 m DEM read (dem empty)."""
        d = self.work / "cache" / tid
        if (d / "stage0.npz").exists() and (d / "rows.json").exists():
            z = np.load(d / "stage0.npz", allow_pickle=False)
            rows = json.loads((d / "rows.json").read_text())
            from rasterio import Affine
            if z["dem"].size or not need_dem:                     # DEM cache may have been deleted after the tile
                return rows, z["lc"], Affine(*z["lc_tf"]), z["dem"], Affine(*z["dem_tf"])
        d.mkdir(parents=True, exist_ok=True)
        fcfg = self.cfg["filter"]
        check_classes(fcfg)
        pad = max(fcfg["built_up_buffer_m"], fcfg["water_buffer_m"])
        lc, lc_tf = read_landcover(*padded_bbox(*bb, pad), fcfg["landcover_res_m"])
        masks = pixel_masks(lc, lc_tf, fcfg)
        rows = [r for r in (evaluate_cell(c, lc, lc_tf, masks, fcfg, None, self.cfg["grid"]["cell_km"]) for c in cells) if r]
        if need_dem:
            buf = max(self.cfg["polar"]["buffer_m"], self.cfg["mare"]["radius_km"] * 1000 + 500) + 1000
            dem, prof = read_bbox(*padded_bbox(*bb, buf), res=self.res)
            dem_tf = prof["transform"]
        else:
            from rasterio import Affine
            dem, dem_tf = np.zeros((0, 0), np.float32), Affine.identity()
        np.savez_compressed(d / "stage0.npz", lc=lc, lc_tf=np.array(tuple(lc_tf)[:6]), dem=dem,
                            dem_tf=np.array(tuple(dem_tf)[:6]))
        (d / "rows.json").write_text(json.dumps(rows, cls=_NP))
        return rows, lc, lc_tf, dem, dem_tf

    def mare_buffer(self):
        return self.cfg["mare"]["radius_km"] * 1000 + 500 + 1000

    # --- tracks ---------------------------------------------------------------------------------
    def track_a(self, rows, lc, lc_tf, dem, dem_tf):
        from pipeline.run import cell_candidates
        p = self.cfg["polar"]
        masks = pixel_masks(lc, lc_tf, self.cfg["filter"])
        ice = np.isin(lc, p["ice_classes"])
        out = []
        for r in rows:
            rec = {"cell": r, "info": None, "cands": [], "prefilter": None}
            if r["keep"] and self._cur is not None and r["id"] not in self._cur["A"]:
                rec["prefilter"] = "prefilter: world stage 0, not an A candidate"
            elif r["keep"]:
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

    def track_b1(self, rows, lc, lc_tf, bb):
        """B1: coarse Mare raw values (GLO-90) for low-relief, bare cells. ONLY for selecting B2 candidates."""
        from pipeline.run_mare import cell_mare
        masks = pixel_masks(lc, lc_tf, self.cfg["filter"])
        dem, prof = read_bbox(*padded_bbox(*bb, self.mare_buffer()), res=self.s["coarse_res"])
        lim, bare_min = self.s["mare_prefilter_relief_m"], self.s["bare_min_share"]
        out = []
        for r in rows:
            rec = {"cell": r, "res": None, "prefilter": None, "coarse_res": self.s["coarse_res"]}
            if r["keep"] and self._cur is not None and r["id"] not in self._cur["B1"]:
                rec["prefilter"] = "prefilter: world stage 0, not a B candidate"
            elif r["keep"]:
                rs, cs = window_of(r, prof["transform"], dem.shape)
                win = dem[rs, cs]
                relief = float(np.nanmax(win) - np.nanmin(win)) if np.isfinite(win).any() else None
                bare = r.get("f_bare") or 0.0
                if relief is None:
                    rec["prefilter"] = "prefilter: no DEM data in cell"
                elif relief > lim:
                    rec["prefilter"] = f"prefilter: cell relief {relief:.0f} m > {lim:g} m (not a plain)"
                elif bare < bare_min:
                    rec["prefilter"] = f"prefilter: bare share {bare:.2f} < {bare_min:g}"
                else:
                    rec["res"] = cell_mare(r, dem, prof["transform"], masks["usable"], lc_tf, self.cfg)
            out.append(rec)
        return out

    # --- B2: select from B1 and run 30 m ----------------------------------------------------------
    def mare_ready(self) -> bool:
        """True if every counting Mare criterion has a verified lunar target (config loader set target)."""
        return all(c.get("target") is not None for c in self.cfg["mare"]["criteria"].values())

    def select_b2(self, n=None):
        from pipeline.mare import MARE_CRITERIA
        from pipeline.scoring import score_direct, total_score
        crit = self.cfg["mare"]["criteria"]
        n = n or self.s["b2_top_n"]
        cand = []
        for path in sorted((self.work / "raw" / "B1").glob("*.jsonl")):
            tid = path.stem
            with open(path, encoding="utf-8") as f:
                for line in f:
                    rec = json.loads(line)
                    res = rec["res"]
                    if not res or not res.get("keep"):
                        continue
                    for name in MARE_CRITERIA:
                        res[f"s_{name}"] = score_direct(res.get(name), crit[name])
                    sc, _ = total_score(res, crit)
                    if sc is not None:
                        cand.append((sc, tid, rec["cell"]["id"]))
        cand.sort(reverse=True)
        sel = cand[:n]
        out = {"n_requested": n, "n_coarse_scored": len(cand), "n_selected": len(sel),
               "coarse_score_cutoff": sel[-1][0] if sel else None,
               "targets": {k: (v["target"], v["tolerance"]) for k, v in crit.items()},
               "cells": [{"tile": t, "cell": c, "coarse_score": round(s, 4)} for s, t, c in sel]}
        (self.work / "b2_selection.json").write_text(json.dumps(out, indent=1))
        self.log(f"B2 selection: {len(sel)} of {len(cand)} coarse-scored cells (cutoff {out['coarse_score_cutoff']})")
        return out

    def run_b2(self):
        from pipeline.run_mare import cell_mare
        sel = json.loads((self.work / "b2_selection.json").read_text())
        by_tile = {}
        for c in sel["cells"]:
            by_tile.setdefault(c["tile"], set()).add(c["cell"])
        self.log(f"B2: 30 m Mare pass for {sel['n_selected']} cells in {len(by_tile)} tiles")
        for k, (tid, ids) in enumerate(sorted(by_tile.items()), 1):
            st = self.prog["tiles"].setdefault(tid, {})
            if st.get("B2") == "done":
                continue
            t0 = time.time()
            try:
                rows = [r for r in json.loads((self.work / "cache" / tid / "rows.json").read_text()) if r["id"] in ids]
                z = np.load(self.work / "cache" / tid / "stage0.npz")
                from rasterio import Affine
                lc, lc_tf = z["lc"], Affine(*z["lc_tf"])
                masks = pixel_masks(lc, lc_tf, self.cfg["filter"])
                bb = (min(r["west"] for r in rows), min(r["south"] for r in rows),
                      max(r["east"] for r in rows), max(r["north"] for r in rows))
                dem, prof = self.with_retries(f"{tid} B2 DEM", lambda: read_bbox(*padded_bbox(*bb, self.mare_buffer()), res=30))
                recs = [{"cell": r, "res": cell_mare(r, dem, prof["transform"], masks["usable"], lc_tf, self.cfg),
                         "prefilter": None} for r in rows]
                path = self.work / "raw" / "B2" / f"{tid}.jsonl"
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    for rec in recs:
                        f.write(json.dumps(rec, cls=_NP) + "\n")
                os.replace(tmp, path)
                st["B2"], st["B2_s"] = "done", round(time.time() - t0, 1)
            except Exception as e:
                st["B2"], st["B2_error"] = "failed", f"{type(e).__name__}: {e}"
                self.log(f"{tid} B2 FAILED: {st['B2_error']}")
            self.save()
            self.log(f"{tid} B2 ({k}/{len(by_tile)}, {len(ids)} cells) in {round(time.time() - t0, 1)} s")

    def auto_b2(self):
        if not self.mare_ready():
            self.log("B2 deferred: Mare lunar targets not verified in config/lunar_targets.json. Coarse B1 raw values "
                     "are stored; tomorrow: `python src/night_run.py --b2` (selects from B1, runs 30 m).")
            return
        self.select_b2()
        self.run_b2()

    # --- main loop ------------------------------------------------------------------------------
    def world_todo(self, world_dir: Path):
        """Tiles from stage 0 world (world_priority.json order), each with its A / B1 candidate cells only."""
        from pipeline.world import parse_tile, tile_cells
        prio = json.loads((world_dir / "world_priority.json").read_text())["tiles"]
        flags = {}
        for line in open(world_dir / "stage0_world.jsonl", encoding="utf-8"):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            flags[r["tile"]] = {"A": {c["id"] for c in r["cells"] if c["a"]}, "B1": {c["id"] for c in r["cells"] if c["b"]}}
        todo = []
        for t in prio:
            tid, cand = t["tile"], flags.get(t["tile"])
            if not cand:
                continue
            ids = cand["A"] | cand["B1"]
            cells = [c for c in tile_cells(*parse_tile(tid)) if c["id"] in ids]
            if not cells:
                continue
            bb = (min(c["west"] for c in cells), min(c["south"] for c in cells),
                  max(c["east"] for c in cells), max(c["north"] for c in cells))
            self.cand[tid] = cand
            todo.append(({"name": "world"}, (tid, bb, cells)))
        return todo

    def run(self, only=None, tracks=("A", "B1"), res=30, world_dir=None, max_hours=None):
        self.res = res
        self.cand = {}
        if world_dir:
            todo = self.world_todo(Path(world_dir))
        else:
            todo = [(rg, t) for rg in self.regions if not only or rg["name"] in only for t in self.tiles(rg)]
        n_tiles = len(todo)
        self.log(f"night run: {n_tiles} tiles ({'world stage 0 order' if world_dir else 'regions'}), tracks "
                 f"{','.join(tracks)}, DEM {res} m, work dir {self.work}"
                 + (f", stops after {max_hours:g} h" if max_hours else ""))
        t_start, done_now, stopped = time.time(), 0, False
        for k, (rg, (tid, bb, cells)) in enumerate(todo, 1):
            if max_hours and time.time() - t_start > max_hours * 3600:
                self.log(f"time limit {max_hours:g} h reached after {k - 1}/{n_tiles} tiles: stopping cleanly "
                         "(run the same command again to resume)")
                stopped = True
                break
            st = self.prog["tiles"].setdefault(tid, {"region": rg["name"], "bbox": bb, "n_cells": len(cells)})
            if all(st.get(t) == "done" for t in tracks):
                continue
            self._cur = self.cand.get(tid)                       # world mode: only candidate cells per track
            t0 = time.time()
            try:
                need = any(t in ("A", "B") for t in tracks if st.get(t) != "done")
                rows, lc, lc_tf, dem, dem_tf = self.with_retries(f"{tid} stage 0", lambda: self.stage0(tid, bb, cells, need))
                st["stage0"] = "done"
                st["n_kept"] = sum(r["keep"] for r in rows)
                for t in tracks:
                    if st.get(t) == "done":
                        continue
                    t1 = time.time()
                    if t == "B1":
                        recs = self.with_retries(f"{tid} track B1", lambda: self.track_b1(rows, lc, lc_tf, bb))
                    else:
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
        self.log("tile loop finished" if not stopped else "tile loop stopped by the time limit")
        if "B1" in tracks and self.s.get("auto_b2", True) and not stopped:
            self.auto_b2()
        elif stopped:
            self.log("B2 not started (B1 incomplete). After B1 is complete: `python src/night_run.py --b2`")
        self.log("night run finished")

    # --- morning: scoring from raw values -------------------------------------------------------
    FOLDERS = {"A": "night_polar", "B": "night_mare_all30", "B1": "night_mare_coarse", "B2": "night_mare"}

    def score(self, tracks=None, out_root=ROOT / "out"):
        """Rankings from stored raw values. B1 (coarse) goes to its own folder: selection only, never final."""
        tracks = tracks or tuple(t for t in self.FOLDERS if (self.work / "raw" / t).exists())
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
                self._score_a(recs, bb, out_root / self.FOLDERS[t])
            else:
                self._score_b(recs, bb, out_root / self.FOLDERS[t])

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
    ap.add_argument("--tracks", default="A,B1", help="A (Polar), B1 (Mare coarse); B2 runs after; legacy B = 30 m all")
    ap.add_argument("--res", type=int, default=30, choices=[30, 90])
    ap.add_argument("--score", action="store_true", help="score the stored raw values (no downloads)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--b2", action="store_true", help="select the top coarse Mare cells from B1 and run the 30 m pass")
    ap.add_argument("--world", type=Path, nargs="?", const=WORK / "world",
                    help="process the tiles of stage 0 world (default its work dir) instead of the regions file")
    ap.add_argument("--max-hours", type=float, help="stop cleanly after this many hours (resume later)")
    a = ap.parse_args()
    night = Night(a.work, a.regions)
    night.res = a.res
    tracks = tuple(a.tracks.split(","))
    if a.status:
        night.status()
    elif a.b2:
        if not night.mare_ready():
            raise SystemExit("Mare lunar targets are not verified in config/lunar_targets.json: B2 cannot select yet")
        night.select_b2()
        night.run_b2()
    elif a.score:
        night.score(tuple(a.tracks.split(",")) if a.tracks != "A,B1" else None)
    else:
        night.run(a.only, tracks, a.res, world_dir=a.world, max_hours=a.max_hours)


if __name__ == "__main__":
    main()
