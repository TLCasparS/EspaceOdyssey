"""Shadow simulation: which places on Earth behave like the lunar south pole?

Pipeline: DEM -> horizon angles -> one year of Sun positions -> per-cell light metrics -> site score.
"""
from .dem import DemGrid, load_site, synthetic_crater
from .horizon import horizon_angles
from .illumination import IlluminationResult, flat_baseline, simulate_year
from .score import summarise
from .sun import sun_position, year_times


def run_site(grid: DemGrid, year: int = 2026, step_minutes: int = 60, n_azimuths: int = 72,
             horizon_km: float = 20.0):
    """Full pipeline for one site. Returns (result maps, flat baseline, summary dict)."""
    az, hz = horizon_angles(grid.z, grid.window, grid.dx_m, grid.dy_m,
                            n_azimuths=n_azimuths, max_dist_m=horizon_km * 1000)
    times = year_times(year, step_minutes)
    sun_az, sun_el = sun_position(grid.lat, grid.lon, times)
    res = simulate_year(hz, az, sun_az, sun_el, step_minutes)
    base = flat_baseline(sun_az, sun_el, step_minutes)
    summary = summarise(res, base, grid.dx_m * grid.dy_m / 1e6)
    return res, base, summary


__all__ = ["DemGrid", "load_site", "synthetic_crater", "horizon_angles", "simulate_year",
           "flat_baseline", "IlluminationResult", "summarise", "sun_position", "year_times", "run_site"]
