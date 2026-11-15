"""Read SLDEM2015 (LOLA + Kaguya TC merge, 512 ppd = 59.2 m/px, 60 S - 60 N) windows around lunar
mare cells and save them as GeoTIFFs in metres. Resampling to the common 60 m grid happens later
(dem.grid.reproject_dem with a local metric CRS: mare_cells.local_crs).

Sources, tried in this order:
  1. --tiles-dir: downloaded SLDEM2015 512 ppd tiles (30 deg lat x 45 deg lon, 0-360 E), e.g.
       https://imbrium.mit.edu/EXTRAS/SLDEM2015/TILES/JP2/SLDEM2015_512_00N_30N_000_045.JP2 (~165 MB)
     with its _JP2.LBL and _AUX.XML next to it (the _AUX.XML holds the georeference; it is copied to
     <tile>.JP2.aux.xml, the name GDAL reads)
  2. the USGS global mosaic, read by window over HTTP (22 GB, int16 metres, R = 1737.4 km):
       https://planetarymaps.usgs.gov/mosaic/LolaKaguya_Topo/Lunar_LRO_LOLAKaguya_DEMmerge_60N60S_512ppd.tif
     (not documented as cloud-optimised: if the remote read fails, use the tiles)

Units: SLDEM2015 tiles may store km; the mosaic stores m. Heights are converted to metres from the
values themselves (mare plains lie ~1-3 km below 1737.4 km): 99th percentile of |h| < 30 -> km,
> 100 -> m, anything else -> error. The file's own scale/offset is applied first.

    python src/fetch_sldem_window.py --cells config/mare_cells.json --first 5   # the cells used (+ Apollo 11)
    python src/fetch_sldem_window.py --cells config/mare_cells.json          # all candidates (spares too)
    python src/fetch_sldem_window.py --lat 0.67416 --lon 23.47314 --name apollo_11
    python src/fetch_sldem_window.py --cells config/mare_cells.json --tiles-dir <folder>

Tiles live OUTSIDE the repo (OneDrive must not sync ~800 MB): default --tiles-dir is
%LOCALAPPDATA%/espaceodyssey_data/sldem_tiles (DEFAULT_TILES_DIR) if that folder exists; --tiles-dir "" = mosaic.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline.config import load_config  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "moon" / "sldem"
DEFAULT_TILES_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "espaceodyssey_data" / "sldem_tiles"
USGS_MOSAIC = ("https://planetarymaps.usgs.gov/mosaic/LolaKaguya_Topo/"
               "Lunar_LRO_LOLAKaguya_DEMmerge_60N60S_512ppd.tif")
R_MOON = 1737400.0
MOON_LL = "+proj=longlat +R=1737400 +no_defs"


def tile_name(lat: float, lon: float) -> str:
    """SLDEM2015 512 ppd tile covering (lat, lon): 30 deg latitude bands, 45 deg longitude bands, 0-360 E."""
    if not -60 <= lat < 60:
        raise ValueError("SLDEM2015 covers 60 S - 60 N")
    lo = int(math.floor(lat / 30) * 30)
    hi = lo + 30
    lat_s = f"{lo:02d}N_{hi:02d}N" if lo >= 0 else f"{-lo:02d}S_{-hi:02d}S"   # archive: 30S_00S, 60S_30S
    lon360 = lon % 360
    l0 = int(lon360 // 45) * 45
    return f"SLDEM2015_512_{lat_s}_{l0:03d}_{l0 + 45:03d}"


def ensure_pam_sidecar(jp2: Path) -> None:
    """The MIT archive ships the georeference as <tile>_AUX.XML; GDAL only reads <file>.aux.xml.
    Copy it under the name GDAL expects (once)."""
    import shutil
    src = jp2.with_name(jp2.stem + "_AUX.XML")
    dst = jp2.with_name(jp2.name + ".aux.xml")
    if src.exists() and not dst.exists():
        shutil.copyfile(src, dst)


def to_metres(z: np.ndarray) -> tuple[np.ndarray, str]:
    """km or m, decided from the values; fails instead of guessing."""
    p = float(np.nanpercentile(np.abs(z), 99))
    if p < 30:
        return z * 1000.0, f"km -> m (p99 |h| = {p:.3g})"
    if p > 100:
        return z, f"m as stored (p99 |h| = {p:.4g})"
    raise ValueError(f"height units unclear (p99 |h| = {p}); read the product label")


def read_window(src: str, lat: float, lon: float, half_km: float):
    """(z in metres, transform, crs, note) for +-half_km around (lat, lon), at native resolution."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    path = "/vsicurl/" + src if src.startswith(("http://", "https://")) else src
    dlat = math.degrees(half_km * 1000 / R_MOON)
    dlon = dlat / math.cos(math.radians(lat))
    with rasterio.open(path) as s:
        crs = s.crs or CRS.from_proj4(MOON_LL)
        b = s.bounds
        if crs.is_geographic:                                    # SLDEM tiles: degrees, 0..360 or -180..180
            x = lon if b.left < 0 else lon % 360
            w, e, so, n = x - dlon, x + dlon, lat - dlat, lat + dlat
        else:                                                    # USGS mosaic: equirectangular in metres
            w, so, e, n = transform_bounds(CRS.from_proj4(MOON_LL), crs, lon - dlon, lat - dlat,
                                           lon + dlon, lat + dlat, densify_pts=21)
        if w < b.left or e > b.right or so < b.bottom or n > b.top:
            raise ValueError(f"window ({w:.6g}..{e:.6g}, {so:.6g}..{n:.6g}) leaves {os.path.basename(src)} "
                             f"({b.left:.6g}..{b.right:.6g}, {b.bottom:.6g}..{b.top:.6g})")
        win = from_bounds(w, so, e, n, transform=s.transform)
        z = s.read(1, window=win, masked=True).astype("float64").filled(np.nan)
        if z.size == 0 or not np.isfinite(z).any():
            raise ValueError(f"empty window {z.shape} or all no-data in {os.path.basename(src)} (crs {crs})")
        z = z * float(s.scales[0] or 1.0) + float(s.offsets[0] or 0.0)
        tf = s.window_transform(win)
    z, note = to_metres(z)
    return z.astype("float32"), tf, crs, note


def read_window_tiles(tiles_dir: str, lat: float, lon: float, half_km: float):
    """Like read_window, but from all SLDEM tiles in tiles_dir, stitched when the window crosses a
    tile edge (e.g. a cell on 30 N). Tiles are lon/lat 0-360 E with a scale in the file."""
    import rasterio
    from rasterio.merge import merge
    tiles = sorted(Path(tiles_dir).glob("SLDEM2015_512_*.JP2"))
    for t in tiles:
        ensure_pam_sidecar(t)
    dlat = math.degrees(half_km * 1000 / R_MOON)
    dlon = dlat / math.cos(math.radians(lat))
    x = lon % 360
    w, e, so, n = x - dlon, x + dlon, lat - dlat, lat + dlat
    srcs = [rasterio.open(t) for t in tiles]
    try:
        hit = [s for s in srcs if s.bounds.left < e and s.bounds.right > w and s.bounds.bottom < n and s.bounds.top > so]
        if not hit:
            raise ValueError("no local tile overlaps the window")
        covered = (min(s.bounds.left for s in hit) <= w and max(s.bounds.right for s in hit) >= e and
                   min(s.bounds.bottom for s in hit) <= so and max(s.bounds.top for s in hit) >= n)
        if not covered:
            raise ValueError(f"local tiles do not cover the window ({w:.3f}..{e:.3f}, {so:.3f}..{n:.3f})")
        scale, offset = float(hit[0].scales[0] or 1.0), float(hit[0].offsets[0] or 0.0)
        if any(float(s.scales[0] or 1.0) != scale or float(s.offsets[0] or 0.0) != offset for s in hit):
            raise ValueError("tiles with different scale/offset")
        arr, tf = merge(hit, bounds=(w, so, e, n), nodata=hit[0].nodata)
        crs = hit[0].crs or MOON_LL
        z = arr[0].astype("float64")
        if hit[0].nodata is not None:
            z[arr[0] == hit[0].nodata] = np.nan
        z = z * scale + offset
        names = "+".join(Path(s.name).name for s in hit)
    finally:
        for s in srcs:
            s.close()
    if not np.isfinite(z).any():
        raise ValueError("all no-data")
    z, note = to_metres(z)
    return z.astype("float32"), tf, crs, note, names


def fetch(cell: dict, half_km: float, tiles_dir: str | None) -> Path:
    import rasterio
    lat, lon = cell["lat"], cell["lon"]
    z = None
    if tiles_dir:
        try:
            z, tf, crs, note, src = read_window_tiles(tiles_dir, lat, lon, half_km)
        except Exception as ex:
            print(f"  [{cell['id']}] local tiles failed: {str(ex)[:120]}; trying the USGS mosaic")
    if z is None:
        src = USGS_MOSAIC
        try:
            z, tf, crs, note = read_window(src, lat, lon, half_km)
        except Exception as ex:
            raise SystemExit(f"[{cell['id']}] no source worked: {ex}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{cell['id']}.tif"
    with rasterio.open(out, "w", driver="GTiff", height=z.shape[0], width=z.shape[1], count=1, dtype="float32",
                       crs=crs, transform=tf, nodata=np.nan, compress="deflate") as d:
        d.write(z, 1)
        d.update_tags(units="m", reference_radius_m=str(R_MOON), source=os.path.basename(src), units_check=note,
                      center_lat=str(lat), center_lon=str(lon))
    print(f"  [{cell['id']}] {z.shape[1]}x{z.shape[0]} px from {os.path.basename(src)}, {note}, "
          f"h {np.nanmin(z):.0f}..{np.nanmax(z):.0f} m -> {out.relative_to(ROOT)}")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cells", help="config/mare_cells.json: fetch every candidate + the named site")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    ap.add_argument("--name")
    ap.add_argument("--tiles-dir", default=str(DEFAULT_TILES_DIR) if DEFAULT_TILES_DIR.is_dir() else None,
                    help=f"folder with downloaded SLDEM2015 512 ppd tiles (default {DEFAULT_TILES_DIR} if it exists)")
    ap.add_argument("--half-km", type=float, help="default: grid.cell_km / 2 + polar.buffer_m")
    ap.add_argument("--first", type=int, help="only candidates with order <= N (+ the named site); "
                    "fetch spares later only if compute_mare_target.py skips cells")
    a = ap.parse_args()
    cfg = load_config()
    half = a.half_km or cfg["grid"]["cell_km"] / 2 + cfg["polar"]["buffer_m"] / 1000
    if a.cells:
        spec = json.loads(Path(a.cells).read_text(encoding="utf-8"))
        cand = [c for c in spec["cells"] if a.first is None or c["order"] <= a.first]
        cells = cand + [{"id": k, **v} for k, v in spec.get("named_site", {}).items()]
    elif a.lat is not None and a.lon is not None:
        cells = [{"id": a.name or f"cell_{a.lat:.3f}_{a.lon:.3f}", "lat": a.lat, "lon": a.lon}]
    else:
        ap.error("give --cells or --lat/--lon")
    print(f"{len(cells)} window(s) of +-{half:g} km")
    for c in cells:
        if (OUT_DIR / f"{c['id']}.tif").exists():
            print(f"  [{c['id']}] already there")
            continue
        fetch(c, half, a.tiles_dir)


if __name__ == "__main__":
    main()
