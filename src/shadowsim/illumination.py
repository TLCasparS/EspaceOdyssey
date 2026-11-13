"""Simulate one year of direct sunlight for every cell, using precomputed horizons."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class IlluminationResult:
    lit_fraction: np.ndarray            # share of all time steps with direct sun
    terrain_shadow_fraction: np.ndarray  # share of "sun above horizon" steps blocked by terrain
    dark_days: np.ndarray               # days of the year without any direct sun
    max_dark_days: np.ndarray           # longest run of consecutive days without direct sun (cyclic)
    max_lit_hours: np.ndarray           # longest continuous period of direct sun, hours (cyclic)


def _horizon_at(horizon: np.ndarray, azimuths: np.ndarray, sun_az: float) -> np.ndarray:
    """Linear interpolation of the horizon between the two nearest azimuth sectors."""
    n = len(azimuths)
    step = 360.0 / n
    x = (sun_az % 360.0) / step
    i0 = int(np.floor(x)) % n
    i1 = (i0 + 1) % n
    w = x - np.floor(x)
    return (1 - w) * horizon[i0] + w * horizon[i1]


def simulate_year(horizon: np.ndarray, azimuths: np.ndarray, sun_az: np.ndarray,
                  sun_el: np.ndarray, step_minutes: int) -> IlluminationResult:
    """horizon: [n_az, rows, cols]; sun_az/sun_el: one value per time step (UTC, full days)."""
    shape = horizon.shape[1:]
    steps_per_day = int(round(24 * 60 / step_minutes))
    n_days = len(sun_el) // steps_per_day
    hz_min = horizon.min()

    lit_steps = np.zeros(shape, np.int32)
    above_steps = 0
    blocked_steps = np.zeros(shape, np.int32)
    dark_days = np.zeros(shape, np.int32)

    # run-length counters; "head" = run at the start of the year (for cyclic wrap)
    dark_run = np.zeros(shape, np.int32); dark_max = np.zeros(shape, np.int32)
    dark_head = np.zeros(shape, np.int32); dark_in_head = np.ones(shape, bool)
    lit_run = np.zeros(shape, np.int32); lit_max = np.zeros(shape, np.int32)
    lit_head = np.zeros(shape, np.int32); lit_in_head = np.ones(shape, bool)

    for d in range(n_days):
        lit_today = np.zeros(shape, bool)
        for s in range(d * steps_per_day, (d + 1) * steps_per_day):
            el = sun_el[s]
            if el <= hz_min:
                lit = np.zeros(shape, bool)
            else:
                lit = el > _horizon_at(horizon, azimuths, sun_az[s])
            if el > 0:
                above_steps += 1
                blocked_steps += ~lit
            lit_steps += lit
            lit_today |= lit
            lit_run = np.where(lit, lit_run + 1, 0)
            np.maximum(lit_max, lit_run, out=lit_max)
            lit_head += lit_in_head & lit
            lit_in_head &= lit
        dark = ~lit_today
        dark_days += dark
        dark_run = np.where(dark, dark_run + 1, 0)
        np.maximum(dark_max, dark_run, out=dark_max)
        dark_head += dark_in_head & dark
        dark_in_head &= dark

    total_steps = n_days * steps_per_day
    # wrap-around: a run at the end of December continues into January
    dark_max = np.where(dark_in_head, n_days, np.maximum(dark_max, np.minimum(dark_head + dark_run, n_days)))
    lit_max = np.where(lit_in_head, total_steps, np.maximum(lit_max, np.minimum(lit_head + lit_run, total_steps)))

    return IlluminationResult(
        lit_fraction=lit_steps / total_steps,
        terrain_shadow_fraction=blocked_steps / max(above_steps, 1),
        dark_days=dark_days,
        max_dark_days=dark_max,
        max_lit_hours=lit_max * step_minutes / 60.0,
    )


def flat_baseline(sun_az: np.ndarray, sun_el: np.ndarray, step_minutes: int) -> IlluminationResult:
    """Same metrics for a perfectly flat horizon (0 deg) at the same latitude."""
    flat = np.zeros((4, 1, 1), np.float32)
    return simulate_year(flat, np.arange(4) * 90.0, sun_az, sun_el, step_minutes)
