"""Light criteria 1-5 (Polar), on the same 60 m MetricGrid and zones as the terrain criteria.

Build step 1 (14 Nov 2026): criterion 5, sky-view factor of the bowl floor. Needs only the horizon,
no Sun, so the SAME function runs on Earth cells and on the lunar window (body = earth / moon).

    sky-view factor (SVF) = share of the sky hemisphere that is visible
                          = 1 - mean over azimuths of sin(max(horizon angle, 0))
    (Zaksek, Ostir & Kokalj 2011, "Sky-view factor as a relief visualization technique").
    1 = open sky (flat plain), lower = more enclosed. Horizons below 0 deg count as 0 (a point on a
    hill does not see "more than a hemisphere" here).

Zone: the floor = bowl pixels flatter than light.floor_max_slope_deg connected to the low point
(the low point alone if it is steeper). Value = median SVF over the floor.
Look-out distance: light.horizon_rel x bowl radius r (relative, like the other zones), so the value
does not depend on crater size. Terrain outside the DEM counts as invisible (shadowsim rule):
if the buffer is shorter than the look-out distance, the SVF is slightly too high.

Still to come (step 2+): Sun time series for criteria 1, 2, 4 with a grid-north -> true-north
conversion of the azimuths (not needed for the SVF, which averages over all azimuths).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage

from shadowsim.horizon import horizon_angles


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


def sky_view_factor(z: np.ndarray, zone: np.ndarray, res_m: float, max_dist_m: float,
                    body: dict, n_azimuths: int = 72) -> np.ndarray:
    """SVF for the pixels of `zone` (NaN elsewhere). Horizons only on the zone's bounding box."""
    rows, cols = np.nonzero(zone)
    r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    _, hz = horizon_angles(z, (r0, r1, c0, c1), res_m, res_m, n_azimuths=n_azimuths,
                           max_dist_m=max_dist_m, radius_m=body["radius_m"], refraction_k=body["refraction_k"])
    svf_box = 1.0 - np.sin(np.radians(np.clip(hz, 0.0, 90.0))).mean(axis=0)
    out = np.full(z.shape, np.nan)
    box = out[r0:r1, c0:c1]
    sub = zone[r0:r1, c0:c1]
    box[sub] = svf_box[sub]
    return out


def c5_sky_view(z, dep, low, slope_deg, res_m, lcfg: dict, body: str, fallback_dist_m: float):
    """(median floor SVF or None, info). dep = depression dict (mask, width_m) or None (no bowl)."""
    b = lcfg["bodies"][body]
    if dep is not None:
        zone = floor_zone(dep["mask"], slope_deg, low, lcfg["floor_max_slope_deg"])
        dist = lcfg["horizon_rel"] * dep["width_m"] / 2
    else:
        zone = np.zeros(z.shape, bool)
        zone[low] = True
        dist = fallback_dist_m
    if not np.isfinite(z[low]):
        return None, {}
    svf = sky_view_factor(z, zone, res_m, dist, b, lcfg["n_azimuths"])
    v = svf[zone]
    v = v[np.isfinite(v)]
    info = {"c5_floor_px": int(zone.sum()), "c5_horizon_km": round(dist / 1000, 2),
            "c5_svf_low_point": None if not np.isfinite(svf[low]) else round(float(svf[low]), 4)}
    return (float(np.median(v)) if v.size else None), info
