"""Hard filters per cell: land-cover blacklist, buffers around built-up and water, population.

No slope filter here: steep walls are what we look for. The slope limit applies only to the
flat base spot, later, in the criteria step.

Pixel level (whole bbox, so buffers reach across cell borders):
    usable = keep class  AND  > built_up_buffer_m from built-up  AND  > water_buffer_m from water/wetland
Cell level, dropped if any of:
    cell area < min_cell_frac of a full cell (partial cells at the bbox edge),
    land share < min_land (ocean / coast), usable share < min_usable,
    largest connected usable patch < min_patch_km2, population > max_pop_per_km2 (only with --pop).
Masked pixels are only excluded as base-spot locations; the DEM keeps all pixels.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from dem.landcover import CLASSES, read_landcover
from dem.terrain import pixel_size_m
from pipeline.cells import cell_area_km2, make_grid, window_of


def check_classes(fcfg: dict) -> None:
    """Every WorldCover class must be in exactly one of drop_classes / keep_classes."""
    drop, keep = set(fcfg["drop_classes"]), set(fcfg["keep_classes"])
    if drop & keep:
        raise ValueError(f"classes in both drop and keep: {sorted(drop & keep)}")
    missing = set(CLASSES) - drop - keep
    if missing:
        raise ValueError(f"classes in neither drop nor keep: {sorted(missing)}")


def _row_lat(transform, row: float) -> float:
    return transform.f + transform.e * row          # north-up lat/lon raster


def distance_m(mask: np.ndarray, transform, max_dist_m: float, band_deg: float = 0.5) -> np.ndarray:
    """Metric distance (m) from each pixel to the nearest True pixel of `mask` on a lat/lon grid.

    Exact up to max_dist_m (larger values may be overestimated; inf if no True pixel nearby).
    Processed in latitude bands so the east-west pixel size follows cos(lat).
    """
    out = np.full(mask.shape, np.inf, np.float32)
    if not mask.any():
        return out
    h = mask.shape[0]
    band = max(1, int(round(band_deg / abs(transform.e))))
    for r0 in range(0, h, band):
        r1 = min(h, r0 + band)
        dx, dy = pixel_size_m(transform, _row_lat(transform, (r0 + r1) / 2))
        pad = int(math.ceil(max_dist_m / dy)) + 1
        p0, p1 = max(0, r0 - pad), min(h, r1 + pad)
        sub = mask[p0:p1]
        if not sub.any():
            continue
        d = ndimage.distance_transform_edt(~sub, sampling=(dy, dx))
        out[r0:r1] = d[r0 - p0:r1 - p0]
    return out


def pixel_masks(lc: np.ndarray, transform, fcfg: dict) -> dict:
    """Boolean layers on the land-cover grid: usable, and what removed each pixel."""
    land = lc != 0
    keep_class = np.isin(lc, fcfg["keep_classes"])
    near_built = distance_m(np.isin(lc, fcfg["built_up_classes"]), transform,
                            fcfg["built_up_buffer_m"]) <= fcfg["built_up_buffer_m"]
    near_water = distance_m(np.isin(lc, fcfg["water_classes"]), transform,
                            fcfg["water_buffer_m"]) <= fcfg["water_buffer_m"]
    usable = keep_class & ~near_built & ~near_water
    return {"land": land, "keep_class": keep_class, "near_built": near_built,
            "near_water": near_water, "usable": usable}


def largest_patch_px(usable: np.ndarray, connectivity: int = 8) -> int:
    if not usable.any():
        return 0
    structure = np.ones((3, 3), bool) if connectivity == 8 else None
    labels, n = ndimage.label(usable, structure=structure)
    return int(np.bincount(labels.ravel())[1:].max())


class Population:
    """Population-count raster (EPSG:4326, people per pixel), e.g. GHS-POP WGS84 30 arcsec."""

    def __init__(self, path):
        import rasterio
        self.src = rasterio.open(path)
        if self.src.crs is None or self.src.crs.to_epsg() != 4326:
            raise SystemExit(f"--pop must be in WGS84 (EPSG:4326), got {self.src.crs}. "
                             "Download the 'WGS84 / 3 or 30 arcsec' version of GHS-POP.")

    def density(self, c) -> float:
        from rasterio.windows import from_bounds
        win = from_bounds(c["west"], c["south"], c["east"], c["north"], self.src.transform)
        win = win.round_offsets().round_lengths()
        a = self.src.read(1, window=win, boundless=True, fill_value=0).astype("float64")
        if self.src.nodata is not None:
            a[a == self.src.nodata] = 0
        a[a < 0] = 0
        return float(a.sum()) / max(cell_area_km2(c), 1e-9)


def evaluate_cell(c: dict, lc: np.ndarray, transform, masks: dict, fcfg: dict,
                  pop: Population | None = None, cell_km: float | None = None) -> dict:
    """One output row: land-cover shares, masking shares, largest patch, keep + reasons."""
    rs, cs = window_of(c, transform, lc.shape)
    block = lc[rs, cs]
    n = block.size
    if n == 0:
        return None
    m = {k: v[rs, cs] for k, v in masks.items()}
    share = lambda a: float(a.sum()) / n
    land, usable = share(m["land"]), share(m["usable"])
    # pixels of a kept class lost only to a buffer
    lost_built = share(m["keep_class"] & m["near_built"])
    lost_water = share(m["keep_class"] & m["near_water"] & ~m["near_built"])

    dx, dy = pixel_size_m(transform, (c["south"] + c["north"]) / 2)
    patch_km2 = largest_patch_px(m["usable"], fcfg["patch_connectivity"]) * dx * dy / 1e6
    density = pop.density(c) if pop else None

    reasons = []
    area_frac = cell_area_km2(c) / cell_km ** 2 if cell_km else 1.0
    if area_frac < fcfg["min_cell_frac"]:
        reasons.append(f"edge-cell {area_frac:.0%} of full size")
    if land < fcfg["min_land"]:
        reasons.append(f"ocean/no-data {1 - land:.0%}")
    if usable < fcfg["min_usable"]:
        reasons.append(f"usable {usable:.0%}<{fcfg['min_usable']:.0%}")
    if patch_km2 < fcfg["min_patch_km2"]:
        reasons.append(f"patch {patch_km2:.2f}km2<{fcfg['min_patch_km2']:g}")
    if density is not None and density > fcfg["max_pop_per_km2"]:
        reasons.append(f"pop {density:.1f}/km2")

    return {
        **{k: (round(v, 5) if isinstance(v, float) else v) for k, v in c.items()},
        "keep": not reasons, "reason": "; ".join(reasons),
        "area_km2": round(cell_area_km2(c), 1),
        "land": round(land, 4), "usable": round(usable, 4),
        "lost_to_built_buffer": round(lost_built, 4), "lost_to_water_buffer": round(lost_water, 4),
        "largest_patch_km2": round(patch_km2, 2),
        "pop_per_km2": None if density is None else round(density, 2),
        **{f"f_{name}": round(float((block == v).sum()) / n, 4) for v, name in CLASSES.items()},
    }


def padded_bbox(west, south, east, north, pad_m: float):
    """bbox grown by pad_m so buffers see built-up / water just outside the area."""
    dlat = pad_m / 110_574.0
    lat_max = min(max(abs(south), abs(north)) + dlat, 89.0)
    dlon = pad_m / (111_320.0 * math.cos(math.radians(lat_max)))
    return (max(west - dlon, -180), max(south - dlat, -90), min(east + dlon, 180), min(north + dlat, 90))


def run_filter(bbox, cfg: dict, pop_path: str | None = None, log=print):
    """bbox -> (rows for every cell, land cover, transform, pixel masks)."""
    fcfg = cfg["filter"]
    check_classes(fcfg)
    west, south, east, north = bbox
    cells = make_grid(west, south, east, north, cfg["grid"]["cell_km"])
    pad = max(fcfg["built_up_buffer_m"], fcfg["water_buffer_m"])
    log(f"{len(cells)} cells of ~{cfg['grid']['cell_km']} km. Reading WorldCover at "
        f"{fcfg['landcover_res_m']:.0f} m (bbox + {pad / 1000:g} km padding) ...")
    lc, transform = read_landcover(*padded_bbox(west, south, east, north, pad), fcfg["landcover_res_m"])
    masks = pixel_masks(lc, transform, fcfg)
    pop = Population(pop_path) if pop_path else None
    rows = [r for r in (evaluate_cell(c, lc, transform, masks, fcfg, pop, cfg["grid"]["cell_km"]) for c in cells) if r]
    return rows, lc, transform, masks
