"""Candidate Polar lunar targets, one per Artemis III candidate region (NASA, 19 Aug 2022), computed
with the SAME code and method as the Shackleton target (src/compute_lunar_target.py). Night Task 5.

    python src/compute_polar_candidates.py --moon-dir ../EspaceOdyssey/data/moon
    python src/compute_polar_candidates.py --only Site01,Site07

Writes the "polar" entries of config/lunar_targets_candidates.json (all verified: false) and one preview
PNG per region in figures/moon/targets/. Never touches config/lunar_targets.json.

Region centre: centre of the extent of PGDA product 78's 5 m site DEM (<site>_final_adj_5mpp_surf.tif,
read from the GeoTIFF header over HTTP). Each site DEM covers one Artemis III candidate region
(names on the PGDA page match the NASA 2022 list). The tile centre is a proxy for the region centre,
not an official coordinate.

Method per region (as Shackleton):
  1. LOLA LDEM_80S_20MPP_ADJ.TIF window +-35 km around the region centre (src/fetch_lola_window.py,
     /vsicurl/ range reads; cached as <moon-dir>/targets/<site>_20m_window.tif), bilinear to 60 m.
  2. "cell" = cell_km (15 km) square centred on the region centre; candidates = closed depressions
     with low point in the cell (pipeline.polar.polar_candidates, body="moon", nothing masked).
  3. Chosen place = the VALID candidate (keep=True: base pad found, slope <= max_base_slope_deg) with
     the largest depth x width - the same rule that picked Shackleton. No valid candidate -> region
     skipped with the reason (not forced).
  4. Light c1-c4 from PGDA product 69 AVGVISIB_85S_060M_201608 / LPSR_85S_060M_201608 via
     pipeline.lunar_light.moon_light (same zones as Earth). Those maps stop at 85 S: outside -> null.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import sys
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
import rasterio.errors
from rasterio.env import Env

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compute_lunar_target import crater_zones, load_grid, to_lonlat, xy_grid  # noqa: E402
from fetch_lola_window import URL as LDEM_URL, read_window  # noqa: E402
from pipeline.config import load_config  # noqa: E402
from pipeline.lunar_light import AVGVISIB_SOURCE, moon_light, read_on_grid  # noqa: E402
from pipeline.polar import _Cell, find_depressions  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "config" / "lunar_targets_candidates.json"
FIG_DIR = ROOT / "figures" / "moon" / "targets"
HALF_KM = 35.0
SITE_URL = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/{s}/{s}_final_adj_5mpp_surf.tif"
PGDA78 = "https://pgda.gsfc.nasa.gov/products/78"
NASA_2022 = ("https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/"
             " (RELEASE22-089, 19 Aug 2022; 'each region is approximately 15 by 15 kilometers')")

# NASA 2022 region name -> PGDA product 78 site id (PGDA page labels in brackets)
REGIONS = [
    ("Connecting Ridge", "Site01", "Connecting ridge"),
    ("Peak Near Shackleton", "Site07", "Peak near Shackleton"),
    ("de Gerlache Rim 1", "Site11", "de Gerlache rim"),
    ("de Gerlache Rim 2", "SL2", "de Gerlache rim"),
    ("Malapert Massif", "Site23", "Malapert massif"),
    ("Nobile Rim 1", "Site06", "Nobile rim 1"),
    ("Nobile Rim 2", "DM2", "Nobile rim 2"),
    ("Connecting Ridge Extension", "SL3", "Connecting ridge extension"),
    ("de Gerlache-Kocher Massif", "Site42", "de Gerlache-Kocher massif"),
    ("Haworth", "Haworth", "Haworth"),
    ("Leibnitz Beta Plateau", "Site20", "Leibnitz beta plateau"),
    ("Amundsen Rim", "DM1", "Amundsen rim"),
    ("Faustini Rim A", "LM7", "Faustini Rim A"),
]
MAPPING_NOTE = {"Site11": "UNVERIFIED: PGDA labels both Site11 and SL2 'de Gerlache rim'; Rim 1 = Site11 and "
                          "Rim 2 = SL2 is our assumption (SL2 = later site list)",
                "SL2": "UNVERIFIED: see Site11"}
CRITERIA = ("c1_sunny_ridge", "c2_dark_floor", "c3_light_dark", "c4_grazing_sun", "c5_sky_view", "c7_bowl",
            "c9_relief", "c10_flat_base", "c11_walls", "c13_roughness", "c14_aspect")


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def site_centre(site: str):
    """Centre (x, y) m of the PGDA 5 m site DEM extent, from its header only."""
    with Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        with rasterio.open("/vsicurl/" + SITE_URL.format(s=site)) as d:
            b = d.bounds
            return (b.left + b.right) / 2, (b.bottom + b.top) / 2, (b.right - b.left) / 1e3


def window_file(moon_dir: Path, site: str, cx: float, cy: float) -> Path:
    f = moon_dir / "targets" / f"{site}_20m_window.tif"
    if f.exists():
        return f
    # PGDA sometimes returns 0 bytes for a tile (seen 14 Nov): retry, one HTTP range per request
    for attempt in range(4):
        try:
            with Env(GDAL_HTTP_MULTIRANGE="SINGLE", GDAL_HTTP_MULTIPLEX="NO", VSI_CACHE="TRUE"):
                z, tf, crs = read_window(HALF_KM, cx, cy)
            break
        except rasterio.errors.RasterioIOError as e:
            print(f"  window read failed ({e}); retry {attempt + 1}/3", flush=True)
            if attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))
    f.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(f, "w", driver="GTiff", height=z.shape[0], width=z.shape[1], count=1, dtype="float32",
                       crs=crs, transform=tf, nodata=np.nan, compress="deflate", tiled=True) as dst:
        dst.write(z, 1)
        dst.update_tags(source=LDEM_URL, read=f"+-{HALF_KM:g} km around ({cx:g}, {cy:g}) m, native, /vsicurl/")
    return f


def evaluate(name, site, label, moon_dir, cfg):
    p = cfg["polar"]
    cx, cy, tile_km = site_centre(site)
    win = window_file(moon_dir, site, cx, cy)
    mg = load_grid(win, cfg)
    X, Y = xy_grid(mg)
    clon, clat = to_lonlat(mg, cx, cy)
    rec = {"name": f"polar_{site.lower()}", "label": f"Polar · {name} (Artemis III 2022 region)",
           "base_type": "polar", "region": name, "pgda_site": site, "pgda_label": label,
           "region_centre_xy_m": [round(cx), round(cy)], "region_centre_lat_lon": [round(clat, 3), round(clon % 360, 2)],
           "region_centre_source": f"centre of the {tile_km:g} km extent of {SITE_URL.format(s=site)} ({PGDA78})",
           "region_list_source": NASA_2022}
    if site in MAPPING_NOTE:
        rec["mapping_note"] = MAPPING_NOTE[site]
    h = cfg["grid"]["cell_km"] * 500
    in_cell = (np.abs(X - cx) <= h) & (np.abs(Y - cy) <= h)
    cell = _Cell(mg, in_cell, np.ones_like(in_cell), clat, cfg, body="moon")
    deps = find_depressions(mg.dem, in_cell, mg.res_m, p)
    rec["n_depressions"] = len(deps)
    places = [(d, cell.place(d["low"], d)) for d in deps]
    valid = [(d, pl) for d, pl in places if pl["keep"]]
    rec["n_valid"] = len(valid)
    if not valid:
        why = ("no closed depression >= {:g} m deep, >= {:g} m wide, elongation <= {:g} with low point in the "
               "15 km region".format(p["min_depression_depth_m"], p["min_depression_width_m"], p["max_elongation"])
               if not deps else f"{len(deps)} depression(s), none valid: " +
               "; ".join(sorted({pl['reason'] for _, pl in places})))
        rec.update(skipped=True, skip_reason=why)
        figure(mg, X, Y, None, None, None, None, None, rec, cx, cy, h)
        return rec
    dep, place = max(valid, key=lambda t: t[0]["depth_m"] * t[0]["width_m"])
    low = dep["low"]
    lx, ly = float(X[low]), float(Y[low])
    lon, lat = to_lonlat(mg, lx, ly)
    base = (place["base_row"], place["base_col"])
    zones = crater_zones(mg, X, Y, dep, low, cell.t.slope_deg)

    light = None
    avg, lpsr = moon_dir / "AVGVISIB_85S_060M_201608.TIF", moon_dir / "LPSR_85S_060M_201608.TIF"
    if avg.exists():
        lit = read_on_grid(str(avg), mg)
        psr = read_on_grid(str(lpsr), mg, resampling="nearest") if lpsr.exists() else None
        if np.isfinite(lit).any():
            light = moon_light(mg, dep, low, cell.t.slope_deg, lat, cfg, lit, psr)
    light_note = None
    if light is None:
        light_note = "low point / window outside the PGDA 85S illumination map (stops at 85 S): c1-c3 null"
    elif light.get("reason"):
        light_note = light["reason"] + " (PGDA 85S map ends at 85 S)"

    today = date.today().isoformat()
    vals = {k: place.get(k) for k in CRITERIA}
    for k in ("c1_sunny_ridge", "c2_dark_floor", "c3_light_dark"):
        vals[k] = light.get(k) if light else None
    vals["c4_grazing_sun"] = light["c4_grazing_sun"] if light else None
    if vals["c4_grazing_sun"] is None:
        from pipeline.light import MOON_EQUATOR_TILT_DEG, max_sun_elevation_deg
        vals["c4_grazing_sun"] = max_sun_elevation_deg(lat, MOON_EQUATOR_TILT_DEG)
    src_dem = (f"LOLA LDEM_80S_20MPP_ADJ.TIF (Barker et al. 2023, PGDA product 90), +-{HALF_KM:g} km window around "
               f"the region centre read via /vsicurl/, bilinear to {cfg['grid']['res_m']} m")
    crit = {}
    for k, v in vals.items():
        src = AVGVISIB_SOURCE if k in ("c1_sunny_ridge", "c2_dark_floor", "c3_light_dark") else (
            "geometry: low-point latitude + light.MOON_EQUATOR_TILT_DEG" if k == "c4_grazing_sun" else src_dem)
        crit[k] = {"value": None if v is None else round(float(v), 4), "source": src, "date": today,
                   "verified": False}
    rec.update(skipped=False, criteria=crit, date=today, verified=False, light_note=light_note, place={
        "low_point_xy_m": [round(lx), round(ly)], "low_point_lat_lon": [round(lat, 3), round(lon % 360, 2)],
        "low_to_region_centre_km": round(float(np.hypot(lx - cx, ly - cy)) / 1e3, 2),
        "low_elev_m": place["low_elev_m"], "spill_depth_m": place["c7_depth_m"],
        "equiv_diameter_m": place["c7_width_m"], "elongation": place["c7_elongation"],
        "extends_outside_region": dep["extends_outside_cell"],
        "rim_crest_diameter_m": zones["rim_diam_m"], "rim_to_floor_depth_m": zones["rim_depth_m"],
        "inner_wall_mean_slope_deg": zones["wall_slope_deg"], "wall_ring_km": place["wall_ring_km"],
        "c11_ring_covered": place["c11_ring_covered"],
        "base_xy_m": [round(float(X[base])), round(float(Y[base]))], "base_to_bowl_km": place["base_to_bowl_km"],
        "c5_horizon_km": place.get("c5_horizon_km"),
        "window_edge_km": round(min(lx - X.min(), X.max() - lx, ly - Y.min(), Y.max() - ly) / 1e3, 1),
        "lpsr_share_of_floor": light.get("lpsr_share_of_floor") if light else None,
    })
    figure(mg, X, Y, dep, place, low, base, zones, rec, cx, cy, h)
    return rec


def figure(mg, X, Y, dep, place, low, base, zones, rec, cx, cy, h):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    z = mg.dem
    ext = [X.min() / 1e3, X.max() / 1e3, Y.min() / 1e3, Y.max() / 1e3]
    hs = LightSource(315, 35).hillshade(np.nan_to_num(z, nan=np.nanmin(z)), dx=mg.res_m, dy=mg.res_m)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(hs, extent=ext, cmap="gray")
    sq = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1], [-1, -1]]) * h
    ax.plot((cx + sq[:, 0]) / 1e3, (cy + sq[:, 1]) / 1e3, "g-", lw=1.5, label="15 km region (centre = PGDA site tile)")
    if dep is None:
        ax.set_title(f"{rec['region']} ({rec['pgda_site']}): SKIPPED\n{rec['skip_reason'][:110]}", fontsize=9)
    else:
        ov = np.zeros(z.shape + (4,))
        ov[zones["wall"]] = (1.0, 0.55, 0.0, 0.35)
        ov[zones["floor"]] = (0.1, 0.3, 1.0, 0.55)
        ax.imshow(ov, extent=ext)
        c = zones["crest_xy"] / 1e3
        ax.plot(np.r_[c[:, 0], c[:1, 0]], np.r_[c[:, 1], c[:1, 1]], "m-", lw=1.2,
                label=f"rim crest ~{zones['rim_diam_m'] / 1e3:.1f} km")
        ax.contour(X / 1e3, Y / 1e3, dep["mask"].astype(float), levels=[0.5], colors="cyan", linewidths=1.2)
        ax.plot([], [], "s", color=(0.1, 0.3, 1.0), label="floor (< 10 deg)")
        ax.plot([], [], "s", color=(1.0, 0.55, 0.0), label=f"inner wall, mean {zones['wall_slope_deg']} deg")
        ax.plot([], [], "c-", label="bowl (filled depression)")
        ax.plot(X[low] / 1e3, Y[low] / 1e3, "bv", ms=9, label=f"low point {place['low_elev_m']:.0f} m")
        ax.plot(X[base] / 1e3, Y[base] / 1e3, "r*", ms=14, label=f"base pad {place['c10_flat_base']:.1f} deg")
        ax.set_title(f"{rec['region']} ({rec['pgda_site']}), LOLA 20 m -> 60 m\nbowl depth {place['c7_depth_m']:.0f} m, "
                     f"diam {place['c7_width_m'] / 1e3:.1f} km, c7 {place['c7_bowl']:.3f}  [verified: false]", fontsize=9)
    if ext[0] <= 0 <= ext[1] and ext[2] <= 0 <= ext[3]:
        ax.plot(0, 0, "w+", ms=14, mew=2, label="south pole")
    ax.set(xlabel="x km (polar stereographic)", ylabel="y km")
    ax.legend(loc="lower left", fontsize=7)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    f = FIG_DIR / f"{rec['name']}.png"
    fig.savefig(f, dpi=90, bbox_inches="tight")
    plt.close(fig)
    rec["preview"] = str(f.relative_to(ROOT))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--moon-dir", type=Path, default=ROOT / "data" / "moon")
    ap.add_argument("--only", default="", help="comma-separated PGDA site ids")
    a = ap.parse_args()
    cfg = load_config()
    only = set(filter(None, a.only.split(",")))
    out = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {"targets": []}
    keep = [t for t in out["targets"] if t["base_type"] != "polar" or (only and t.get("pgda_site") not in only)]
    new = []
    for name, site, label in REGIONS:
        if only and site not in only:
            continue
        print(f"--- {name} ({site})", flush=True)
        rec = evaluate(name, site, label, a.moon_dir, cfg)
        rec["git_commit"] = git_commit()
        print("  skipped:", rec["skip_reason"]) if rec["skipped"] else print(
            "  " + ", ".join(f"{k}={v['value']}" for k, v in rec["criteria"].items()))
        new.append(rec)
    order = {s: i for i, (_, s, _) in enumerate(REGIONS)}
    polar = sorted([t for t in keep if t["base_type"] == "polar"] + new, key=lambda t: order[t["pgda_site"]])
    out["targets"] = polar + [t for t in keep if t["base_type"] != "polar"]
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("->", OUT_JSON)


if __name__ == "__main__":
    main()
