"""Stage 0 worldwide: a cheap coarse prescreen of every land tile -> candidate cells per track + priority.

    python src/stage0_world.py                              # all land tiles (resumes)
    python src/stage0_world.py --only N35W112 N20E017       # test on a few tiles
    python src/stage0_world.py --summary                    # counts + priority list from what is done

Per 1 x 1 deg land tile (Copernicus tileList.txt in data/tiles/): WorldCover at ~1 km (COG overview) and
GLO-90 at 300 x 300 px (its 4x overview). Per ~15 km world cell (pipeline.world): land share, bare share
(class 60), drop-class share (filter.drop_classes), coarse relief (max-min of the 300 px DEM).
    all:   land >= world_min_land, snow/ice <= world_max_snow (ice sheets out); DEM read only if land cover allows
    A candidate (Polar crater): drop <= world_max_drop, relief >= world_relief_min_a
    B candidate (Mare):         bare >= bare_min_share, relief <= mare_prefilter_relief_m
These are PRESCREEN thresholds only (config/night_regions.yaml settings, outside the config-v1 freeze); the night
run applies the real 100 m filter and the frozen criteria to the candidates. Coarse relief at ~300 m underestimates
small bowls, hence world_relief_min_a (30 m) below the real 50 m bowl minimum.

Output (work dir, default %LOCALAPPDATA%/espaceodyssey_night/world): stage0_world.jsonl (one line per tile,
appended, resume-safe), failures.jsonl, world_priority.json (tiles with candidates, most first).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline.cells import window_of  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.world import land_tiles, parse_tile, tile_cells, tile_id  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "espaceodyssey_night" / "world"
TILES = ROOT / "data" / "tiles" / "copdem90_tileList.txt"
SETTINGS = ROOT / "config" / "night_regions.yaml"


def read_dem_coarse(lat0: int, lon0: int, px: int):
    """GLO-90 tile at px x px (uses the file's overview). Returns (z, transform) or None if the tile is missing."""
    import rasterio
    from rasterio.transform import from_bounds
    from dem.fetch import open_tile, tile_url
    ds = open_tile(tile_url(lat0 + 0.5, lon0 + 0.5, 90))
    if ds is None:
        return None
    with ds:
        z = ds.read(1, out_shape=(px, px), masked=False).astype(np.float32)
        nod = ds.nodata
        b = ds.bounds
    if nod is not None:
        z[z == nod] = np.nan
    z[z < -1000] = np.nan
    return z, from_bounds(b.left, b.bottom, b.right, b.top, px, px)


class LCWorld:
    """WorldCover on one exact global grid (3 deg / N_PX per pixel). Each 3 deg WorldCover tile is read ONCE
    (lowest overview, nearest) and kept in memory; windows across tile edges are assembled from the cache.
    Avoids re-reading the same overview block for each of the 9 one-degree tiles inside it."""
    N_PX = 333                                       # 3 deg / 333 = 0.009009 deg (~1 km) per pixel

    def __init__(self):
        import threading
        self.cache, self.lock, self.reads = {}, threading.Lock(), 0

    def block(self, lat3: int, lon3: int) -> np.ndarray:
        key = (lat3, lon3)
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        from dem.fetch import open_tile
        from dem.landcover import worldcover_url
        ds = open_tile(worldcover_url(lat3 + 0.5, lon3 + 0.5))
        if ds is None:
            arr = np.zeros((self.N_PX, self.N_PX), np.uint8)       # no tile: open ocean
        else:
            with ds:
                arr = ds.read(1, out_shape=(self.N_PX, self.N_PX), masked=False).astype(np.uint8)
        with self.lock:
            self.cache[key] = arr
            self.reads += int(ds is not None)
            if len(self.cache) > 200:                               # tiles are processed block by block
                self.cache.pop(next(iter(self.cache)))
        return arr

    def window(self, west, south, east, north):
        """(classes, transform) on the global grid covering the bbox."""
        from rasterio.transform import from_origin
        d = 3.0 / self.N_PX
        c0, c1 = math.floor((west + 180) / d), math.ceil((east + 180) / d)
        r0, r1 = math.floor((90 - north) / d), math.ceil((90 - south) / d)
        out = np.zeros((r1 - r0, c1 - c0), np.uint8)
        for br in range(r0 // self.N_PX, (r1 - 1) // self.N_PX + 1):
            for bc in range(c0 // self.N_PX, (c1 - 1) // self.N_PX + 1):
                lat3, lon3 = 90 - 3 * (br + 1), -180 + 3 * (bc % (360 // 3))
                if lat3 < -90:
                    continue
                arr = self.block(lat3, lon3)
                rr0, cc0 = br * self.N_PX, bc * self.N_PX
                ys, ye = max(r0, rr0), min(r1, rr0 + self.N_PX)
                xs, xe = max(c0, cc0), min(c1, cc0 + self.N_PX)
                if ys < ye and xs < xe:
                    out[ys - r0:ye - r0, xs - c0:xe - c0] = arr[ys - rr0:ye - rr0, xs - cc0:xe - cc0]
        return out, from_origin(-180 + c0 * d, 90 - r0 * d, d, d)


LC = LCWorld()


def prescreen_tile(lat0: int, lon0: int, cfg: dict, s: dict, lc_only: bool = False) -> dict:
    cells = tile_cells(lat0, lon0)
    t0 = time.time()
    out = {"tile": tile_id(lat0, lon0), "lat": lat0, "lon": lon0, "n_cells": len(cells), "cells": []}
    if not cells:
        return out
    bb = (min(c["west"] for c in cells), min(c["south"] for c in cells),
          max(c["east"] for c in cells), max(c["north"] for c in cells))
    lc, lc_tf = LC.window(*bb)
    drop = cfg["filter"]["drop_classes"]
    # land cover first: the DEM overview is most of the download, so read it only if some cell can still qualify
    lc_ok = []
    for c in cells:
        rs, cs = window_of(c, lc_tf, lc.shape)
        w = lc[rs, cs]
        lc_ok.append(w.size > 0 and (w > 0).mean() >= s["world_min_land"] and (w == 70).mean() <= s["world_max_snow"]
                     and (np.isin(w, drop).mean() <= s["world_max_drop"] or (w == 60).mean() >= s["bare_min_share"]))
    out["dem_needed"] = any(lc_ok)
    if lc_only:                                         # cheap first pass: land cover only, no DEM
        out["lc_ok"] = int(sum(lc_ok))
        out["s"] = round(time.time() - t0, 2)
        return out
    dem = read_dem_coarse(lat0, lon0, s["world_dem_px"]) if any(lc_ok) else None
    out["dem_read"] = dem is not None
    for c in cells:
        rs, cs = window_of(c, lc_tf, lc.shape)
        w = lc[rs, cs]
        if w.size == 0:
            continue
        land = float((w > 0).mean())
        bare = float((w == 60).mean())
        dropf = float(np.isin(w, drop).mean())
        relief = None
        if dem is not None:
            zr, zc = window_of(c, dem[1], dem[0].shape)
            zw = dem[0][zr, zc]
            if np.isfinite(zw).any():
                relief = float(np.nanmax(zw) - np.nanmin(zw))
        snow = float((w == 70).mean())
        base_ok = land >= s["world_min_land"] and snow <= s["world_max_snow"] and relief is not None
        a = base_ok and dropf <= s["world_max_drop"] and relief >= s["world_relief_min_a"]
        b = base_ok and bare >= s["bare_min_share"] and relief <= s["mare_prefilter_relief_m"]
        out["cells"].append({"id": c["id"], "a": a, "b": b, "land": round(land, 3), "bare": round(bare, 3),
                             "snow": round(snow, 3),
                             "drop": round(dropf, 3), "relief": None if relief is None else round(relief, 1)})
    out["n_a"] = sum(x["a"] for x in out["cells"])
    out["n_b"] = sum(x["b"] for x in out["cells"])
    out["bare_mean"] = round(float(np.mean([x["bare"] for x in out["cells"]])), 3) if out["cells"] else 0.0
    out["s"] = round(time.time() - t0, 2)
    return out


def done_tiles(path: Path) -> set:
    done = set()
    if path.exists():
        for line in open(path, encoding="utf-8"):
            try:
                done.add(json.loads(line)["tile"])
            except (json.JSONDecodeError, KeyError):
                pass                                       # a half-written last line after a crash
    return done


DEM_MB_PER_TILE = 0.3     # measured 14 Nov on 4 real tiles: ~0.4-0.5 MB per tile incl. land cover (adapter upper bound)


def summary_lc(work: Path):
    rows = [json.loads(l) for l in open(work / "stage0_lc.jsonl", encoding="utf-8") if l.strip().endswith("}")]
    need = sum(r.get("dem_needed", False) for r in rows)
    print(f"stage 0 LC-only: {len(rows)} tiles, {need} need a DEM read -> full stage 0 adds ~{need * DEM_MB_PER_TILE / 1000:.1f} GB "
          f"(estimate: {DEM_MB_PER_TILE} MB per GLO-90 overview); WorldCover blocks read: {LC.reads}")


def summary(work: Path):
    rows = []
    for line in open(work / "stage0_world.jsonl", encoding="utf-8"):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    pr = sorted([r for r in rows if r.get("n_a", 0) + r.get("n_b", 0) > 0],
                key=lambda r: (-(r["n_a"] + r["n_b"]), -r.get("bare_mean", 0)))
    out = {"n_tiles_done": len(rows), "n_cells": sum(r["n_cells"] for r in rows),
           "n_a": sum(r.get("n_a", 0) for r in rows), "n_b": sum(r.get("n_b", 0) for r in rows),
           "tiles": [{"tile": r["tile"], "n_a": r["n_a"], "n_b": r["n_b"], "bare_mean": r["bare_mean"]} for r in pr]}
    (work / "world_priority.json").write_text(json.dumps(out, indent=1))
    print(f"stage 0 world: {out['n_tiles_done']} tiles, {out['n_cells']} cells, A candidates {out['n_a']}, "
          f"B candidates {out['n_b']}, {len(pr)} tiles with candidates -> {work / 'world_priority.json'}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--work", type=Path, default=WORK)
    ap.add_argument("--tiles", type=Path, default=TILES)
    ap.add_argument("--only", nargs="*", help="tile ids like N35W112")
    ap.add_argument("--limit", type=int, help="at most this many tiles (testing)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--lc-only", action="store_true",
                    help="first pass: land cover only (~0.3-0.5 GB worldwide); reports how many tiles need a DEM read")
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    if a.summary:
        summary(a.work)
        return
    cfg = load_config()
    s = yaml.safe_load(SETTINGS.read_text(encoding="utf-8"))["settings"]
    tiles = [parse_tile(t) for t in a.only] if a.only else land_tiles(a.tiles)
    tiles.sort(key=lambda t: (math.floor(t[0] / 3), math.floor(t[1] / 3), t))   # WorldCover 3 deg blocks together
    out_path = a.work / ("stage0_lc.jsonl" if a.lc_only else "stage0_world.jsonl")
    fail_path = a.work / "failures.jsonl"
    done = done_tiles(out_path)
    todo = [t for t in tiles if tile_id(*t) not in done][: a.limit]
    print(f"stage 0 world: {len(tiles)} land tiles, {len(done)} already done, {len(todo)} to do, {a.workers} workers",
          flush=True)
    t_start, n = time.time(), 0

    def job(t):
        last = None
        for attempt in range(1, s["retries"] + 1):
            try:
                return prescreen_tile(t[0], t[1], cfg, s, a.lc_only), None
            except Exception as e:                         # network hiccup: wait and retry
                last = f"{type(e).__name__}: {e}"
                time.sleep(s["retry_wait_s"][min(attempt - 1, len(s["retry_wait_s"]) - 1)] if attempt < s["retries"] else 0)
        return None, last

    with ThreadPoolExecutor(max_workers=a.workers) as ex, open(out_path, "a", encoding="utf-8") as fo, \
            open(fail_path, "a", encoding="utf-8") as ff:
        futs = {ex.submit(job, t): t for t in todo}
        for fut in as_completed(futs):
            t = futs[fut]
            res, err = fut.result()
            n += 1
            if res is not None:
                fo.write(json.dumps(res) + "\n")
                fo.flush()
            else:
                ff.write(json.dumps({"tile": tile_id(*t), "error": err, "time": time.strftime("%H:%M:%S")}) + "\n")
                ff.flush()
            if n % 50 == 0 or n == len(todo):
                el = time.time() - t_start
                print(f"  {n}/{len(todo)} tiles, {el / 60:.1f} min, ETA {el / n * (len(todo) - n) / 60:.0f} min", flush=True)
    summary_lc(a.work) if a.lc_only else summary(a.work)


if __name__ == "__main__":
    main()
