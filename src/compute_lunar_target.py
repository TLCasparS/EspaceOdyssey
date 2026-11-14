"""Compute the Polar lunar target (Shackleton) with the SAME code as the Earth cells and write it
into config/lunar_targets.json, plus a preview figure.

    python src/fetch_lola_window.py          # once, --half-km 35: data/moon/shackleton_20m_window.tif (20 m, +-35 km)
    python src/compute_lunar_target.py       # -> config/lunar_targets.json, figures/shackleton_target.png

Sources per criterion:
    all criteria           LDEM_80S_20MPP_ADJ (window) - they need the whole crater
    (c13 came from the Site04 5 m tile until 14 Nov; now bowl + rim ring, same zone as on Earth)
Both resampled to the common 60 m grid (config grid.res_m / resampling) with dem.grid.reproject_dem.

The crater is found from the data, not from known coordinates: the qualifying closed depression
(config polar.min_depression_*) with the largest depth x width whose low point lies within
SEARCH_KM of the pole. The target "cell" is a cell_km square centred on that low point, so the
whole ~15 km Earth-cell logic applies unchanged; nothing on the Moon is masked as unusable.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dem.grid import reproject_dem  # noqa: E402
from pipeline.config import TARGETS_PATH, load_config  # noqa: E402
from pipeline.polar import _Cell, find_depressions  # noqa: E402
from pipeline.lunar_light import AVGVISIB_SOURCE, moon_light, read_on_grid  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WINDOW = ROOT / "data" / "moon" / "shackleton_20m_window.tif"
FIG = ROOT / "figures" / "shackleton_target.png"
# light c1-c4 (src/pipeline/lunar_light.py): PGDA product 69 maps, downloaded once (32 MB + 0.6 MB):
#   curl -L -o data/moon/AVGVISIB_85S_060M_201608.TIF https://pgda.gsfc.nasa.gov/data/MoonIllumination/AVGVISIB_85S_060M_201608.TIF
#   curl -L -o data/moon/LPSR_85S_060M_201608.TIF https://pgda.gsfc.nasa.gov/data/MoonIllumination/LPSR_85S_060M_201608.TIF
AVGVISIB = ROOT / "data" / "moon" / "AVGVISIB_85S_060M_201608.TIF"
LPSR = ROOT / "data" / "moon" / "LPSR_85S_060M_201608.TIF"
SEARCH_KM = 15
# pipeline definitions (same text the Earth side uses), refreshed on every run
DEFINITIONS = {
    "c9_relief": {"label": "9 Rim-to-floor depth", "definition":
                  "median over 1-deg azimuth sectors of the highest elevation within rim_search_rel x bowl radius "
                  "of the low point, minus the low point; no bowl -> 0"},
    "c10_flat_base": {"definition": "mean slope of the flattest ~200 m pad (3x3 px at 60 m) outside the bowl whose "
                                    "centre is at most max_base_to_bowl_km outside the bowl edge"},
    "c13_roughness": {"definition": "median std of elevation in 3x3 px windows over the bowl + rim ring (bowl "
                                    "plus everything within rim_search_rel x r of the low point)"},
    "c11_walls": {"definition": "mean slope in a ring of wall_ring_rel x r around the low point, r = equivalent "
                                "radius of the filled depression (inner walls only)"},
    "c14_aspect": {"definition": "share of steep pixels (> 20 deg) within the wall ring's outer radius facing the "
                                 "nearer pole (+-45 deg)"},
}
SRC_WINDOW = ("LOLA LDEM_80S_20MPP_ADJ.TIF (Barker et al. 2023, PGDA product 90), "
              "+-35 km window around the pole read via /vsicurl/ (widened from +-25 km on 14 Nov for c5)")


def load_grid(path, cfg):
    with rasterio.open(path) as s:
        return reproject_dem(s.read(1), s.transform, s.crs, res_m=cfg["grid"]["res_m"],
                             resampling=cfg["grid"]["resampling"])


def xy_grid(mg):
    rr, cc = np.indices(mg.dem.shape)
    return mg.transform * (cc + 0.5, rr + 0.5)


def to_lonlat(mg, x, y):
    from pyproj import CRS, Transformer
    crs = CRS.from_user_input(mg.crs)
    return Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True).transform(x, y)


def main():
    cfg = load_config()
    p = cfg["polar"]
    mg = load_grid(WINDOW, cfg)
    X, Y = xy_grid(mg)

    # 1. crater from the data
    deps = find_depressions(mg.dem, np.hypot(X, Y) <= SEARCH_KM * 1000, mg.res_m, p)
    if not deps:
        raise SystemExit("no qualifying depression near the pole")
    dep = max(deps, key=lambda d: d["depth_m"] * d["width_m"])
    low = dep["low"]
    lx, ly = float(X[low]), float(Y[low])
    lon, lat = to_lonlat(mg, lx, ly)

    # 2. target cell = cell_km square centred on the low point; same per-place code as Earth
    h = cfg["grid"]["cell_km"] * 500
    in_cell = (np.abs(X - lx) <= h) & (np.abs(Y - ly) <= h)
    usable = np.ones_like(in_cell)
    cell = _Cell(mg, in_cell, usable, lat, cfg, body="moon")   # Moon radius, no refraction for horizons
    place = cell.place(low, dep)
    base = (place["base_row"], place["base_col"])

    # distance from the low point to the nearest window edge (c5 look-out check)
    edge_km = min(lx - X.min(), X.max() - lx, ly - Y.min(), Y.max() - ly) / 1000

    # 3. display zones from the data: floor, walls, rim crest (not used in scoring)
    zones = crater_zones(mg, X, Y, dep, low, cell.t.slope_deg)

    # 4. light c1-c4: same zones and formulas as on Earth (light.place_light), lit map from PGDA
    light = None
    if AVGVISIB.exists():
        psr = read_on_grid(str(LPSR), mg, resampling="nearest") if LPSR.exists() else None
        light = moon_light(mg, dep, low, cell.t.slope_deg, lat, cfg, read_on_grid(str(AVGVISIB), mg), psr)
    else:
        print(f"WARNING: {AVGVISIB.relative_to(ROOT)} missing (download command at the top of this file): "
              "c1-c4 stay null")


    today = date.today().isoformat()
    grid_note = f"bilinear to {cfg['grid']['res_m']} m (dem.grid.reproject_dem)"
    win_dem = f"data/moon/shackleton_20m_window.tif, {grid_note}"
    ring = f"{place['wall_ring_km'][0]}-{place['wall_ring_km'][1]} km"
    # name: (value, DEM, zone, stat[, source]); source defaults to SRC_WINDOW
    lz = (f"floor = bowl pixels < {cfg['light']['floor_max_slope_deg']:g} deg connected to the low point; "
          f"rim = outside the bowl, at most {p['max_base_to_bowl_km']:g} km from its edge (criterion-10 zone)")
    lit_dem = f"{AVGVISIB.name} (60 m, own scale x 4e-5) on the 60 m grid; zones from {win_dem.split(',')[0]}"
    lv = (lambda k: light[k]) if light else (lambda k: None)
    flat_txt = f"flat-land lit fraction {lv('flat_lit_fraction')} (light.flat_lit_fraction, lunar tilt)"
    values = {
        "c1_sunny_ridge": (lv("c1_sunny_ridge"), lit_dem, lz, "max lit fraction in the rim zone / " + flat_txt,
                           AVGVISIB_SOURCE),
        "c2_dark_floor": (lv("c2_dark_floor"), lit_dem, lz,
                          "p99 over the floor zone of 1 - lit / flat_lit (not clipped); " + flat_txt, AVGVISIB_SOURCE),
        "c3_light_dark": (lv("c3_light_dark"), lit_dem, lz,
                          "distance darkest floor px -> sunniest rim px (closest pair) / bowl radius r",
                          AVGVISIB_SOURCE),
        "c4_grazing_sun": (lv("c4_grazing_sun"), "none (latitude only)", f"low point, latitude {lat:.3f}",
                           "light.max_sun_elevation_deg(lat, MOON_EQUATOR_TILT_DEG) = 90 - max(0, |lat| - tilt)",
                           "geometry: low-point latitude from the LOLA window + lunar equator tilt "
                           "(light.MOON_EQUATOR_TILT_DEG, NSSDC Moon Fact Sheet)"),
        "c5_sky_view": (place["c5_sky_view"], win_dem,
                        f"floor zone ({place['c5_floor_px']} px: bowl pixels < {cfg['light']['floor_max_slope_deg']:g} "
                        f"deg connected to the low point); horizons out to {place['c5_horizon_km']} km "
                        f"(= {cfg['light']['horizon_rel']:g} x r); nearest window edge {edge_km:.1f} km from the low point "
                        + ("(covers the full look-out distance)" if edge_km >= place["c5_horizon_km"] else
                           "(SHORTER than the look-out distance: terrain beyond counts as invisible, c5 may be high)"),
                        "median of 1 - mean_az sin(max(horizon, 0)), 72 azimuths, Moon radius, no refraction"),
        "c7_bowl": (place["c7_bowl"], win_dem, "whole crater = filled closed depression (cyan outline)",
                    "spill depth / equivalent diameter"),
        "c9_relief": (place["c9_relief"], win_dem,
                      f"whole bowl: rim crest within {p['rim_search_rel']:g} x bowl radius of the floor low point",
                      "median over 1-deg azimuth sectors of the highest elevation, minus the low point "
                      "(size-dependent: large tolerance)"),
        "c10_flat_base": (place["c10_flat_base"], win_dem,
                          f"rim: outside the bowl, pad centre at most {p['max_base_to_bowl_km']:g} km outside the bowl edge",
                          "minimum over 3x3 px (180 m) pads of the mean slope"),
        "c11_walls": (place["c11_walls"], win_dem,
                      f"inner wall: ring {ring} around the low point (= {p['wall_ring_rel'][0]}-"
                      f"{p['wall_ring_rel'][1]} x bowl radius, r = equivalent radius of the filled depression)",
                      "mean slope"),
        "c13_roughness": (place["c13_roughness"], win_dem,
                          f"bowl + rim ring: the bowl plus everything within {p['rim_search_rel']:g} x bowl radius "
                          "of the low point (same zone as on Earth)",
                          "median of the 3x3 px elevation std"),
        "c14_aspect": (place["c14_aspect"], win_dem,
                       f"within {place['wall_ring_km'][1]} km (ring outer radius) of the low point",
                       "share of pixels steeper than 20 deg whose downslope direction is within +-45 deg of the pole "
                       "direction. DISPLAY ONLY (weight 0, 14 Nov): Shackleton sits practically on the pole, so 'toward the pole' is a different direction for each part of the wall; not comparable with Earth"),
    }

    t = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))
    pol = t["polar"]
    pol["status"] = (f"computed {today} by src/compute_lunar_target.py with the Earth pipeline code "
                     "(pipeline.polar._Cell.place) on the 60 m grid")
    pol["grid"] = {"res_m": cfg["grid"]["res_m"], "crs": "lunar south polar stereographic (sphere R = 1737.4 km)",
                   "resampling": cfg["grid"]["resampling"]}
    pol["window"] = (f"{cfg['grid']['cell_km']} km square centred on the crater low point, found from the data "
                     f"(largest depth x width depression within {SEARCH_KM} km of the pole)")
    for name, (v, dem, zone, stat, *src_opt) in values.items():
        c = pol["criteria"][name]
        for k in ("why_not_verified", "note", "how", "computed"):
            c.pop(k, None)
        src = src_opt[0] if src_opt else SRC_WINDOW
        c.update(value=None if v is None else round(float(v), 4), source=src, dem=dem, zone=zone, stat=stat,
                 date=today, verified=v is not None)
        c.update(DEFINITIONS.get(name, {}))
    pol["place"] = {
        "_note": "display values, not scored (scale decision 14 Nov: size-dependent)",
        "low_point_xy_m": [round(lx), round(ly)], "low_point_lat_lon": [round(lat, 3), round(lon % 360, 1)],
        "low_elev_m": place["low_elev_m"], "spill_depth_m": place["c7_depth_m"],
        "equiv_diameter_m": place["c7_width_m"], "elongation": place["c7_elongation"],
        "rim_crest_median_elev_m": zones["rim_elev_m"], "rim_crest_diameter_m": zones["rim_diam_m"],
        "rim_to_floor_depth_m": zones["rim_depth_m"], "floor_equiv_diameter_m": zones["floor_diam_m"],
        "inner_wall_mean_slope_deg": zones["wall_slope_deg"],
        "wall_ring_km": place["wall_ring_km"], "c11_ring_covered": place["c11_ring_covered"],
        "base_xy_m": [round(float(X[base])), round(float(Y[base]))], "base_elev_m": place["base_elev_m"],
        "base_to_bowl_km": place["base_to_bowl_km"], "base_to_low_km": place["base_to_low_km"],
        "zones_how": "floor = bowl pixels < 10 deg connected to the low point; inner wall = bowl pixels between "
                     "floor and rim crest; rim crest = highest point within 1.3 x bowl radius per 1 deg azimuth",
    }
    if light:
        pol["place"]["light"] = {
            "_note": ("display values from src/pipeline/lunar_light.py. PGDA counts the visible fraction of the "
                      "solar disc, light.py (Earth) the Sun's centre; flat land gives 0.5 either way at the pole"),
            **{k: v for k, v in light.items() if not k.startswith(("_", "c1_", "c2_", "c3_", "c4_"))},
            "sunniest_rim_xy_m": [round(float(X[tuple(light["sunniest_rim_px"])])),
                                  round(float(Y[tuple(light["sunniest_rim_px"])]))],
            "darkest_floor_xy_m": [round(float(X[tuple(light["darkest_floor_px"])])),
                                   round(float(Y[tuple(light["darkest_floor_px"])]))],
        }
    Path(TARGETS_PATH).write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for name, (v, *_rest) in values.items():
        print(f"{name:14} {v}")
    print("place:", json.dumps(pol["place"]))
    figure(mg, X, Y, dep, place, low, base, zones)


def crater_zones(mg, X, Y, dep, low, slope):
    """Floor, inner wall and rim crest from the data (display only)."""
    from scipy import ndimage
    lx, ly = X[low], Y[low]
    d = np.hypot(X - lx, Y - ly)
    az = np.degrees(np.arctan2(Y - ly, X - lx)) % 360
    r_eq = dep["width_m"] / 2
    flat = dep["mask"] & (slope < 10)
    lab, _ = ndimage.label(flat)
    floor = lab == lab[low] if lab[low] else np.zeros_like(flat)
    crest_r, crest_z, crest_xy = [], [], []
    search = (d <= 1.3 * r_eq) & np.isfinite(mg.dem)
    for a in range(360):
        k = search & (az >= a) & (az < a + 1)
        if not k.any():
            continue
        i = np.argmax(np.where(k, mg.dem, -np.inf))
        crest_r.append(d.flat[i]); crest_z.append(mg.dem.flat[i]); crest_xy.append((X.flat[i], Y.flat[i]))
    crest_r, crest_z = np.array(crest_r), np.array(crest_z)
    rim_r = float(np.median(crest_r))
    wall = dep["mask"] & ~floor & (d <= rim_r)
    return {"floor": floor, "wall": wall, "crest_xy": np.array(crest_xy),
            "rim_elev_m": round(float(np.median(crest_z)), 0), "rim_diam_m": round(2 * rim_r, -1),
            "rim_depth_m": round(float(np.median(crest_z) - mg.dem[low]), 0),
            "floor_diam_m": round(2 * float(np.sqrt(floor.sum() * mg.res_m ** 2 / np.pi)), -1),
            "wall_slope_deg": round(float(np.nanmean(slope[wall])), 1)}


def figure(mg, X, Y, dep, place, low, base, zones):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    z = mg.dem
    ext = [X.min() / 1e3, X.max() / 1e3, Y.min() / 1e3, Y.max() / 1e3]
    hs = LightSource(315, 35).hillshade(np.nan_to_num(z, nan=np.nanmin(z)), dx=mg.res_m, dy=mg.res_m)
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(hs, extent=ext, cmap="gray")
    overlay = np.zeros(z.shape + (4,))
    overlay[zones["wall"]] = (1.0, 0.55, 0.0, 0.35)      # inner wall: orange
    overlay[zones["floor"]] = (0.1, 0.3, 1.0, 0.55)      # floor: blue
    ax.imshow(overlay, extent=ext)
    cx, cy = zones["crest_xy"][:, 0] / 1e3, zones["crest_xy"][:, 1] / 1e3
    ax.plot(np.r_[cx, cx[:1]], np.r_[cy, cy[:1]], "m-", lw=1.2)
    ax.plot([], [], "s", color=(0.1, 0.3, 1.0), label=f"floor (< 10 deg), ~{zones['floor_diam_m'] / 1e3:.1f} km")
    ax.plot([], [], "s", color=(1.0, 0.55, 0.0), label=f"inner wall, mean {zones['wall_slope_deg']} deg")
    ax.plot([], [], "m-", label=f"rim crest, median {zones['rim_elev_m']:.0f} m, ~{zones['rim_diam_m'] / 1e3:.1f} km")
    ax.contour(X / 1e3, Y / 1e3, dep["mask"].astype(float), levels=[0.5], colors="cyan", linewidths=1.2)
    lx, ly = X[low] / 1e3, Y[low] / 1e3
    th = np.linspace(0, 2 * np.pi, 200)
    for r in place["wall_ring_km"]:
        ax.plot(lx + r * np.cos(th), ly + r * np.sin(th), "y--", lw=1)
    ax.plot(lx, ly, "bv", ms=9, label=f"floor low point {place['low_elev_m']:.0f} m")
    ax.plot(X[base] / 1e3, Y[base] / 1e3, "r*", ms=14, label=f"base pad {place['c10_flat_base']:.1f} deg")
    ax.plot(0, 0, "w+", ms=14, mew=2, label="south pole")
    r13 = 1.3 * place["c7_width_m"] / 2 / 1e3
    ax.plot(lx + r13 * np.cos(th), ly + r13 * np.sin(th), "w:", lw=1, label=f"c13 zone edge (1.3 x r = {r13:.1f} km)")
    ax.plot([], [], "c-", label="bowl (filled depression)")
    ax.plot([], [], "y--", label=f"wall ring {place['wall_ring_km'][0]}-{place['wall_ring_km'][1]} km")
    ax.set(xlabel="x km (polar stereographic)", ylabel="y km",
           title=f"Shackleton from LOLA 20 m -> 60 m: depth {place['c7_depth_m']:.0f} m, "
                 f"diam {place['c7_width_m'] / 1e3:.1f} km")
    ax.legend(loc="lower left", fontsize=8)
    FIG.parent.mkdir(exist_ok=True)
    fig.savefig(FIG, dpi=110, bbox_inches="tight")
    print("figure ->", FIG)


if __name__ == "__main__":
    main()
