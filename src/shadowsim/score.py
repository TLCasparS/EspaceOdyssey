"""Turn per-cell maps into one row of numbers per site.

The idea (Shackleton analogue): a good site has BOTH
  - spots that the terrain keeps in shadow most of the time (crater floor / PSR), and
  - nearby ridges that get almost as much sun as is possible at that latitude (rim).
Thresholds and the combined score are team choices, not established values:
change them in one place here.
"""
from __future__ import annotations

import numpy as np

from .illumination import IlluminationResult

NEAR_PERMANENT_SHADOW = 0.9   # terrain blocks the Sun >= 90 % of the time it is up


def summarise(res: IlluminationResult, base: IlluminationResult, cell_area_km2: float) -> dict:
    base_lit = float(base.lit_fraction.ravel()[0])
    base_dark = int(base.max_dark_days.ravel()[0])
    shadow = res.terrain_shadow_fraction
    lit_rel = res.lit_fraction / base_lit if base_lit > 0 else np.zeros_like(res.lit_fraction)
    extra_dark = res.max_dark_days - base_dark

    dark_p99 = float(np.percentile(shadow, 99))
    light_p99 = float(np.percentile(lit_rel, 99))
    return {
        "flat_lit_fraction": round(base_lit, 3),
        "flat_max_dark_days": base_dark,                       # polar night without terrain
        "darkest_terrain_shadow_p99": round(dark_p99, 3),
        "near_permanent_shadow_km2": round(float((shadow >= NEAR_PERMANENT_SHADOW).sum() * cell_area_km2), 3),
        "max_extra_dark_days": int(extra_dark.max()),          # dark days caused by terrain
        "sunniest_lit_vs_flat_p99": round(light_p99, 3),
        "max_continuous_sun_h": float(res.max_lit_hours.max()),
        "analog_score": round(float(np.sqrt(max(dark_p99, 0) * max(min(light_p99, 1), 0))), 3),
    }
