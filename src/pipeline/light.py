"""Light criteria 1-5 (Polar), on the same 60 m MetricGrid and zones as the terrain criteria.

"Lit" always means: the CENTRE of the Sun is above the local horizon (point Sun, not the 0.5 deg disk).

Zones (same on Earth and Moon):
    floor zone  bowl pixels flatter than light.floor_max_slope_deg connected to the low point
                (the low point alone if it is steeper)
    rim zone    the criterion-10 zone: outside the bowl, at most polar.max_base_to_bowl_km from its edge
Horizons: shadowsim.horizon_angles out to light.horizon_rel x bowl radius r, with the body's radius and
refraction (light.bodies). Terrain outside the DEM counts as invisible.

Criteria (interface agreed with Mateo, 14 Nov 2026; his src/pipeline/lunar_light.py does the Moon side):
    c1_sunny_ridge  max lit fraction in the rim zone / flat-land lit fraction
    c2_dark_floor   p99 over the floor zone of the terrain shadow fraction = 1 - lit / flat_lit
                    (not clipped: a pixel with a horizon below 0 deg can be lit longer than flat land)
    c3_light_dark   distance from the darkest floor pixel to the sunniest rim pixel, divided by r
                    (ties: the closest pair among all darkest floor and all sunniest rim pixels)
    c4_grazing_sun  max Sun elevation over the cycle (deg), latitude only: max_sun_elevation_deg()
                    = 90 - max(0, |lat| - amplitude); mean apparent elevation over daylight as display.
                    Shared: at Shackleton's low point (-89.624) it gives 1.91 deg, at the pole 1.535 deg

flat_lit_fraction() bias (checked 14 Nov 2026 against shadowsim's simulated flat baseline, 2026, hourly):
the symmetric-sine declination ignores Earth's orbital eccentricity, so on Earth the analytic value is
0.4 % low at 28.6 N, 1.9 % low at 75 N and 1.8 % high at 75 S. Hence c1 on a flat Earth rim can be
slightly above 1. Far below the tolerances; kept so that Earth and Moon use the same function.
    c5_sky_view     median over the floor zone of 1 - mean_az sin(max(horizon, 0))
                    (Zaksek, Ostir & Kokalj 2011); needs no Sun
  display:
    max_dark_days               longest run of days without direct sun, max over the floor (Earth only)
    near_permanent_shadow_share share of floor pixels with terrain shadow fraction >= 0.9 (both sides)

flat_lit_fraction() is shared: Mateo imports it for the Moon. Earth c1/c2 use it too, with the
apparent horizon lowered by the refraction that shadowsim.sun adds, so numerator and denominator
treat refraction the same way.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from shadowsim.horizon import horizon_angles

# Declination amplitude of the Sun over one cycle:
EARTH_OBLIQUITY_DEG = 23.439     # J2000 obliquity, the value used in shadowsim/sun.py
# Moon: lunar equator vs ecliptic. Derived from the NSSDC Moon Fact Sheet
# (nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html, read 14 Nov 2026): obliquity to orbit
# 6.68 deg minus orbit inclination to ecliptic 5.145 deg (Cassini state) = 1.535 deg. Other
# references give 1.536-1.543 deg; the difference is irrelevant for the flat-land value.
MOON_EQUATOR_TILT_DEG = 1.535


# --- flat land ---------------------------------------------------------------------------------

def flat_lit_fraction(lat_deg: float, decl_amplitude_deg: float, apparent_horizon_deg: float = 0.0,
                      n_phase: int = 7200) -> float:
    """Long-term share of time the Sun's centre is above a flat horizon, Earth or Moon.

    Declination delta = amplitude x sin(phase), phase uniform over one cycle (Earth: year; Moon:
    the cycle of the Sun's latitude on the Moon). Hour angle uniform over one day (Earth: solar day;
    Moon: synodic month). Lit when the true elevation > apparent_horizon_deg, i.e. for each delta the
    lit share of the day is H0 / pi with cos H0 = (sin h0 - sin lat sin delta) / (cos lat cos delta).
    Ignores orbital eccentricity (the declination is not exactly sinusoidal on Earth).
    Earth with refraction: apparent_horizon_deg = earth_refraction_horizon_deg() (about -0.5 deg).
    """
    lat = np.radians(lat_deg)
    delta = np.radians(decl_amplitude_deg) * np.sin(2 * np.pi * (np.arange(n_phase) + 0.5) / n_phase)
    h0 = np.radians(apparent_horizon_deg)
    with np.errstate(divide="ignore", invalid="ignore"):
        cos_h0 = (np.sin(h0) - np.sin(lat) * np.sin(delta)) / (np.cos(lat) * np.cos(delta))
    cos_h0 = np.where(np.isfinite(cos_h0), cos_h0, np.where(np.sin(lat) * np.sin(delta) > np.sin(h0), -1.0, 1.0))
    return float(np.mean(np.arccos(np.clip(cos_h0, -1.0, 1.0)) / np.pi))


def max_sun_elevation_deg(lat_deg: float, decl_amplitude_deg: float) -> float:
    """Highest elevation of the Sun's centre over the cycle (geometric, no refraction):
    90 - max(0, |lat| - amplitude). Criterion 4; Earth and Moon (at the lunar pole = the tilt)."""
    return 90.0 - max(0.0, abs(lat_deg) - decl_amplitude_deg)


def earth_refraction_horizon_deg() -> float:
    """True elevation at which shadowsim.sun's apparent elevation (true + refraction) is 0."""
    from shadowsim.sun import _refraction_deg
    lo, hi = -1.0, 0.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if mid + float(_refraction_deg(np.array(mid))) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


# --- zones and horizons -------------------------------------------------------------------------

def floor_zone(dep_mask: np.ndarray, slope_deg: np.ndarray, low, max_slope_deg: float) -> np.ndarray:
    """Bowl pixels flatter than max_slope_deg that are connected to the low point."""
    flat = dep_mask & np.isfinite(slope_deg) & (slope_deg < max_slope_deg)
    lab, _ = ndimage.label(flat, structure=np.ones((3, 3), bool))
    zone = np.zeros_like(dep_mask, dtype=bool)
    if lab[low]:
        zone = lab == lab[low]
    else:
        zone[low] = True                                  # V-shaped floor: the low point alone
    return zone


def _bbox(mask):
    rows, cols = np.nonzero(mask)
    return rows.min(), rows.max() + 1, cols.min(), cols.max() + 1


def zone_horizons(z, zone, res_m, max_dist_m, body: dict, n_azimuths=72):
    """(azimuths, horizon [n_az, h, w], bbox) for the bounding box of `zone` (grid-up azimuths)."""
    box = _bbox(zone)
    az, hz = horizon_angles(z, box, res_m, res_m, n_azimuths=n_azimuths, max_dist_m=max_dist_m,
                            radius_m=body["radius_m"], refraction_k=body["refraction_k"])
    return az, hz, box


def _svf(hz):
    return 1.0 - np.sin(np.radians(np.clip(hz, 0.0, 90.0))).mean(axis=0)


def sky_view_factor(z, zone, res_m, max_dist_m, body: dict, n_azimuths=72) -> np.ndarray:
    """SVF for the pixels of `zone` (NaN elsewhere)."""
    _, hz, (r0, r1, c0, c1) = zone_horizons(z, zone, res_m, max_dist_m, body, n_azimuths)
    out = np.full(z.shape, np.nan)
    sub = zone[r0:r1, c0:c1]
    out[r0:r1, c0:c1][sub] = _svf(hz)[sub]
    return out


def true_north_in_grid_deg(crs, x: float, y: float) -> float:
    """Azimuth of true north, clockwise from grid up, at map point (x, y) (as dem.terrain does per pixel).
    A Sun at true azimuth A has grid azimuth A + this value."""
    from pyproj import CRS, Transformer
    c = CRS.from_user_input(crs)
    to_ll = Transformer.from_crs(c, c.geodetic_crs, always_xy=True)
    to_xy = Transformer.from_crs(c.geodetic_crs, c, always_xy=True)
    lon, lat = to_ll.transform(x, y)
    x2, y2 = to_xy.transform(lon, lat + 0.001)
    return float(np.degrees(np.arctan2(x2 - x, y2 - y)))


# --- per place ----------------------------------------------------------------------------------

LIGHT_KEYS = ("c1_sunny_ridge", "c2_dark_floor", "c3_light_dark", "c4_grazing_sun", "c5_sky_view")


def place_light(mg, dep, low, slope_deg, rim_zone, lcfg: dict, body: str, fallback_dist_m: float):
    """Raw light criteria + display values for one place. Sun criteria only for body 'earth' with
    light.sun true (the Moon side comes from lunar_light.py); otherwise they are None."""
    z, res = mg.dem, mg.res_m
    raw = {k: None for k in LIGHT_KEYS}
    info = {"c5_floor_px": None, "c5_horizon_km": None, "c5_svf_low_point": None,
            "max_dark_days": None, "near_permanent_shadow_share": None, "flat_lit_fraction": None,
            "mean_sun_elev_deg": None}
    if not np.isfinite(z[low]):
        return raw, info
    b = lcfg["bodies"][body]
    if dep is not None:
        floor = floor_zone(dep["mask"], slope_deg, low, lcfg["floor_max_slope_deg"])
        r = dep["width_m"] / 2
        dist = lcfg["horizon_rel"] * r
    else:
        floor = np.zeros(z.shape, bool)
        floor[low] = True
        r, dist = None, fallback_dist_m
    sun_on = body == "earth" and lcfg.get("sun", True)
    use_sun = sun_on and dep is not None and rim_zone is not None and bool(rim_zone.any())
    zone = floor | rim_zone if use_sun else floor
    az, hz, (r0, r1, c0, c1) = zone_horizons(z, zone, res, dist, b, lcfg["n_azimuths"])
    fl = floor[r0:r1, c0:c1]

    svf = _svf(hz)
    v = svf[fl]
    v = v[np.isfinite(v)]
    raw["c5_sky_view"] = float(np.median(v)) if v.size else None
    info.update(c5_floor_px=int(floor.sum()), c5_horizon_km=round(dist / 1000, 2),
                c5_svf_low_point=round(float(svf[low[0] - r0, low[1] - c0]), 4))
    if not sun_on:
        return raw, info

    # Earth year: Sun at the low point (apparent elevation incl. refraction, as in shadowsim)
    from shadowsim.illumination import simulate_year
    from shadowsim.sun import sun_position, year_times
    from pyproj import CRS, Transformer
    x, y = mg.transform * (low[1] + 0.5, low[0] + 0.5)
    crs = CRS.from_user_input(mg.crs)
    lon, lat = Transformer.from_crs(crs, crs.geodetic_crs, always_xy=True).transform(x, y)
    times = year_times(lcfg["year"], lcfg["step_min"])
    sun_az, sun_el = sun_position(lat, lon, times)
    # 4: grazing sun, latitude only: exact max Sun elevation (shared function; hourly samples miss noon);
    # mean apparent elevation over the daylight samples as display
    raw["c4_grazing_sun"] = max_sun_elevation_deg(lat, EARTH_OBLIQUITY_DEG)
    info["mean_sun_elev_deg"] = round(float(sun_el[sun_el > 0].mean()), 2) if (sun_el > 0).any() else None
    if not use_sun:
        return raw, info
    # azimuths turned into the grid frame (horizons are measured from grid up)
    sun_az_grid = (sun_az + true_north_in_grid_deg(mg.crs, x, y)) % 360.0
    res_y = simulate_year(hz, az, sun_az_grid, sun_el, lcfg["step_min"])
    flat = flat_lit_fraction(lat, EARTH_OBLIQUITY_DEG, earth_refraction_horizon_deg())

    lit = res_y.lit_fraction
    shadow = 1.0 - lit / flat
    rm = rim_zone[r0:r1, c0:c1]
    raw["c1_sunny_ridge"] = float(lit[rm].max() / flat)
    raw["c2_dark_floor"] = float(np.percentile(shadow[fl], 99))
    dark = fl & (shadow >= shadow[fl].max() - 1e-9)
    sunny = rm & (lit >= lit[rm].max() - 1e-9)
    d_px = ndimage.distance_transform_edt(~sunny)          # distance to the nearest sunniest rim pixel
    raw["c3_light_dark"] = float(d_px[dark].min() * res / r)
    info.update(max_dark_days=int(res_y.max_dark_days[fl].max()),
                near_permanent_shadow_share=round(float((shadow[fl] >= lcfg["near_permanent_shadow"]).mean()), 4),
                flat_lit_fraction=round(flat, 4))
    return raw, info
