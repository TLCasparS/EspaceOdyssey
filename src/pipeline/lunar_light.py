"""Lunar light criteria c1-c4 for the Polar target (Shackleton): the Moon side of light.place_light.
Same zones, same formulas and the same shared functions as the Earth side; only the lit-fraction
map differs (Earth: shadowsim year; Moon: PGDA illumination map). Called by
src/compute_lunar_target.py, which stays the only script that writes config/lunar_targets.json.

    c1_sunny_ridge  max lit fraction in the rim zone / flat-land lit fraction
    c2_dark_floor   p99 over the floor zone of terrain shadow = 1 - lit / flat_lit (not clipped)
    c3_light_dark   distance darkest floor pixel -> sunniest rim pixel, / r
                    (ties: the closest pair among all darkest floor and all sunniest rim pixels)
    c4_grazing_sun  light.max_sun_elevation_deg(lat, MOON_EQUATOR_TILT_DEG)
  display: near_permanent_shadow_share (floor share with shadow >= light.near_permanent_shadow),
           its agreement with the LPSR permanent-shadow map, flat_lit_fraction

Zones exactly as on Earth: floor = light.floor_zone(bowl, slope, low, light.floor_max_slope_deg);
rim = light.rim_zone (shared with polar._Cell.place, criterion 10): outside the bowl, out to
max(edge + polar.max_base_to_bowl_km, polar.rim_zone_rel x r). (Own copy removed 14 Nov 2026.)

Lit fraction: PGDA product 69, AVGVISIB_85S_060M_201608 (modelled from LOLA, 60 m, hourly over
18.6 years, shadows from distant terrain included). The GeoTIFF stores int16 with a scale in the
file (x 4e-5); read_on_grid applies it. NOTE: PGDA counts the VISIBLE FRACTION OF THE SOLAR DISC
(extended Sun, limb darkening; Barker et al. 2020, following Mazarico et al. 2011); light.py counts
the Sun's CENTRE. Flat land gives 0.5 either way at the pole (the Sun swings symmetrically about
the horizon); on terrain the two can differ where the Sun is partly hidden for long stretches.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from pipeline.light import MOON_EQUATOR_TILT_DEG, floor_zone, flat_lit_fraction, max_sun_elevation_deg, rim_zone

PGDA_AVGVISIB_60M = "https://pgda.gsfc.nasa.gov/data/MoonIllumination/AVGVISIB_85S_060M_201608.TIF"
PGDA_LPSR_60M = "https://pgda.gsfc.nasa.gov/data/MoonIllumination/LPSR_85S_060M_201608.TIF"
AVGVISIB_SOURCE = ("PGDA product 69 AVGVISIB_85S_060M_201608.TIF (Mazarico et al. 2011, LOLA-modelled, "
                   "60 m, hourly over 18.6 yr; visible solar-disc fraction)")


def read_on_grid(src: str, mg, resampling: str = "bilinear") -> np.ndarray:
    """The part of a raster (path or https URL) that covers mg, on mg's grid, with the file's own
    scale/offset applied (PGDA: AVGVISIB x 4e-5; LPSR x 2.5e-5 + 0.5). NaN = no data.
    The _COG.TIF links on the PGDA page could not be opened remotely on 14 Nov: download the .TIF."""
    import rasterio
    from rasterio.transform import array_bounds
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    from dem.grid import onto_grid

    path = "/vsicurl/" + src if src.startswith(("http://", "https://")) else src
    h, w = mg.dem.shape
    with rasterio.open(path) as s:
        b = transform_bounds(mg.crs, s.crs, *array_bounds(h, w, mg.transform))
        pad = 2 * abs(s.transform.a)
        win = from_bounds(b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad, transform=s.transform)
        a = s.read(1, window=win, boundless=True, masked=True).astype("float32").filled(np.nan)
        a = a * float(s.scales[0] or 1.0) + float(s.offsets[0] or 0.0)
        return onto_grid(a, s.window_transform(win), s.crs, mg, nodata=np.nan, resampling=resampling)


def as_fraction(lit: np.ndarray) -> np.ndarray:
    """Check that a lit map is a 0-1 fraction. Fails loudly instead of guessing a scale."""
    lo, hi = float(np.nanmin(lit)), float(np.nanmax(lit))
    if lo < -1e-6 or hi > 1.0 + 1e-6:
        raise ValueError(f"lit map range {lo:.4g}..{hi:.4g} is not 0-1: check the file's scale/offset")
    return lit


def light_criteria(lit: np.ndarray, floor: np.ndarray, rim: np.ndarray, flat_lit: float, r_m: float,
                   res_m: float, near_permanent: float = 0.9, psr: np.ndarray | None = None) -> dict:
    """c1-c3 + display values from a 0-1 lit map; the formulas of light.place_light."""
    out = {"c1_sunny_ridge": None, "c2_dark_floor": None, "c3_light_dark": None,
           "flat_lit_fraction": round(float(flat_lit), 4)}
    fl = floor & np.isfinite(lit)
    rm = rim & np.isfinite(lit)
    if not fl.any() or not rm.any():
        out["reason"] = f"no lit data in the {'floor' if not fl.any() else 'rim'} zone"
        return out
    shadow = 1.0 - lit / flat_lit
    out["c1_sunny_ridge"] = float(lit[rm].max() / flat_lit)
    out["c2_dark_floor"] = float(np.percentile(shadow[fl], 99))
    dark = fl & (shadow >= shadow[fl].max() - 1e-9)
    sunny = rm & (lit >= lit[rm].max() - 1e-9)
    d_px, (ir, ic) = ndimage.distance_transform_edt(~sunny, return_indices=True)
    out["c3_light_dark"] = float(d_px[dark].min() * res_m / r_m)

    k = np.argmin(np.where(dark, d_px, np.inf))                 # the closest pair, for figures
    dr, dc = np.unravel_index(k, lit.shape)
    out.update(rim_max_lit=round(float(lit[rm].max()), 4),
               floor_lit_median=round(float(np.median(lit[fl])), 4),
               light_dark_distance_m=round(float(d_px[dr, dc] * res_m), 0),
               darkest_floor_px=[int(dr), int(dc)], sunniest_rim_px=[int(ir[dr, dc]), int(ic[dr, dc])],
               near_permanent_shadow_share=round(float((shadow[fl] >= near_permanent).mean()), 4))
    if psr is not None:
        p = (psr > 0.5) & fl                                    # LPSR after scaling: 1 = permanent shadow
        s = (shadow >= near_permanent) & fl
        union = int((p | s).sum())
        out["lpsr_share_of_floor"] = round(float(p.sum() / fl.sum()), 4)
        out["near_permanent_vs_lpsr_iou"] = round(float((p & s).sum() / union), 4) if union else None
    return out


def moon_light(mg, dep: dict, low, slope_deg: np.ndarray, lat_deg: float, cfg: dict,
               lit: np.ndarray, psr: np.ndarray | None = None) -> dict:
    """c1-c4 + display values for the lunar place, zones and flat land as on Earth."""
    lcfg, p = cfg["light"], cfg["polar"]
    floor = floor_zone(dep["mask"], slope_deg, low, lcfg["floor_max_slope_deg"])
    rim, _ = rim_zone(dep["mask"], low, dep["width_m"] / 2, mg.res_m, p["max_base_to_bowl_km"], p["rim_zone_rel"])
    flat = flat_lit_fraction(lat_deg, MOON_EQUATOR_TILT_DEG)       # no atmosphere: horizon 0 deg
    out = light_criteria(as_fraction(lit), floor, rim, flat, dep["width_m"] / 2, mg.res_m,
                         lcfg["near_permanent_shadow"], psr)
    out["c4_grazing_sun"] = max_sun_elevation_deg(lat_deg, MOON_EQUATOR_TILT_DEG)
    out["floor_px"], out["rim_px"] = int(floor.sum()), int(rim.sum())
    out["_zones"] = {"floor": floor, "rim": rim}
    return out
