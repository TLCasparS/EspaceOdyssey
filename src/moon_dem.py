"""
Step 1 (Moon targets): load the LOLA south-pole DEM, crop it around Shackleton,
resample it to the Earth grid size, and mark the rim and floor zones.

Input  : a LOLA LDEM GeoTIFF in south polar stereographic metres (PGDA products,
         5 m/px). Use the 87-90S mosaic (pgda.gsfc.nasa.gov/products/81) if you
         have it: it surely contains the whole crater. The "Site04 Shackleton rim"
         tile (products/78) may not include the floor -- the quicklook will show.
         Put the downloaded file in data/dem/moon/ (git-ignored, too large to commit).
Outputs: data/dem/moon/shackleton_dem_<res>m.tif    elevation (m), same CRS, <res> m pixels
         data/dem/moon/shackleton_zones_<res>m.tif  0 = other, 1 = floor, 2 = rim
         figures/moon/shackleton_quicklook.png      hillshade + zones + radial profile
         data/results/moon_dem_summary.json         numbers to check against sources

Usage (from the repo root):
         python src/moon_dem.py data/dem/moon/Site04_final_adj_5mpp_surf.tif
         python src/moon_dem.py https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF
           (whole south pole, 20 m, cloud-optimized: only the Shackleton window is downloaded)
         python src/moon_dem.py <dem.tif> --res 30 --half-width-km 18
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from rasterio.crs import CRS
from rasterio.warp import transform as warp_transform

# Shackleton crater centre (approximate; refined below from the DEM itself).
# Verify against the Gazetteer of Planetary Nomenclature before it goes on a slide.
SHACKLETON_LAT = -89.67
SHACKLETON_LON = 129.8

# Used only if the GeoTIFF has no CRS: LOLA polar products are stereographic,
# centred on the south pole, on a 1737.4 km sphere.
MOON_SPS = "+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R=1737400 +units=m +no_defs"


def lonlat_to_xy(crs: CRS, lon: float, lat: float) -> tuple[float, float]:
    """Project a lunar lon/lat into the DEM's own map coordinates."""
    moon_lonlat = CRS.from_proj4("+proj=longlat +R=1737400 +no_defs")
    xs, ys = warp_transform(moon_lonlat, crs, [lon], [lat])
    return xs[0], ys[0]


def load_crop(path: str, half_width_m: float, res_m: float):
    """Windowed read around Shackleton, averaged down to res_m pixels.

    Only the crop is read from disk, so this works on the multi-GB mosaic.
    """
    if path.startswith(("http://", "https://")):
        path = "/vsicurl/" + path  # reads only the bytes of the crop window
    with rasterio.open(path) as src:
        crs = src.crs if src.crs else CRS.from_proj4(MOON_SPS)
        native_res = abs(src.transform.a)
        print(f"file: {os.path.basename(path)}  native pixel: {native_res:.1f} m  size: {src.width}x{src.height}")
        print(f"file extent (m): x {src.bounds.left:.0f}..{src.bounds.right:.0f}, "
              f"y {src.bounds.bottom:.0f}..{src.bounds.top:.0f}")

        cx, cy = lonlat_to_xy(crs, SHACKLETON_LON, SHACKLETON_LAT)
        print(f"Shackleton centre guess in map coords: x={cx:.0f} m, y={cy:.0f} m")

        # Clip the requested box to what the file actually covers.
        left = max(cx - half_width_m, src.bounds.left)
        right = min(cx + half_width_m, src.bounds.right)
        bottom = max(cy - half_width_m, src.bounds.bottom)
        top = min(cy + half_width_m, src.bounds.top)
        if left >= right or bottom >= top:
            raise SystemExit("Shackleton is outside this file's extent - wrong tile?")
        if (right - left) < 2 * half_width_m * 0.95 or (top - bottom) < 2 * half_width_m * 0.95:
            print("WARNING: the file only partly covers the crop box; the floor or "
                  "part of the rim may be missing. Check the quicklook.")

        window = from_bounds(left, bottom, right, top, transform=src.transform)
        out_w = max(1, int(round((right - left) / res_m)))
        out_h = max(1, int(round((top - bottom) / res_m)))
        # Average resampling = the mean elevation of the 5 m pixels inside each
        # coarse pixel, which is how a 30 m Earth DEM pixel behaves too.
        dem = src.read(
            1, window=window, out_shape=(out_h, out_w),
            resampling=Resampling.average, masked=True,
        ).astype("float64")
        transform = rasterio.transform.from_bounds(left, bottom, right, top, out_w, out_h)

    dem = dem.filled(np.nan)
    # LOLA heights are relative to a 1737.4 km sphere; keep metres as-is.
    return dem, transform, crs, (cx, cy)


def fit_centre(dem, xs, ys, cx0, cy0, half_width_m, search_m=3000.0, step_m=250.0):
    """Centre that makes the rim crest sharpest.

    For each candidate centre within +/- search_m of the catalogue position,
    average the elevation in 200 m rings; the ring average peaks highest when
    the rings line up with the crest. The lowest floor point is not used: it
    can sit km away from the centre (it did for Shackleton).
    """
    sub = (slice(None, None, 3), slice(None, None, 3))   # 3x thinner grid, fast enough
    z, x, y = dem[sub], xs[sub], ys[sub]
    ok = np.isfinite(z)
    z, x, y = z[ok], x[ok], y[ok]
    rmax = 0.95 * half_width_m
    best = (-np.inf, cx0, cy0)
    for dx in np.arange(-search_m, search_m + 1, step_m):
        for dy in np.arange(-search_m, search_m + 1, step_m):
            r = np.hypot(x - (cx0 + dx), y - (cy0 + dy))
            m = r < rmax
            b = (r[m] // 200).astype(int)
            cnt = np.bincount(b)
            prof = np.bincount(b, weights=z[m]) / np.maximum(cnt, 1)
            prof = prof[cnt > 20]
            if prof.size and prof.max() > best[0]:
                best = (prof.max(), cx0 + dx, cy0 + dy)
    return best[1], best[2]


def zone_crater(dem, transform, centre_xy, half_width_m, rim_band_m=1000.0):
    """Find the rim radius and floor from the DEM, and say what the tile covers.

    - centre: the catalogue position, refined by fit_centre only when the data
      covers the whole 5 km disc around it (a partial tile would bias the fit)
    - rim radius: the radius where the mean elevation of each ring peaks, using
      only rings that the data covers well enough
    - rim zone: a ring of +/- rim_band_m around that radius (covered part only)
    - floor zone: inside 40% of the rim radius and within 300 m of the lowest
      point; left empty when the data covers less than half of that disc
    """
    h, w = dem.shape
    cols, rows = np.meshgrid(np.arange(w), np.arange(h))
    xs, ys = rasterio.transform.xy(transform, rows.ravel(), cols.ravel())
    xs = np.asarray(xs).reshape(h, w)
    ys = np.asarray(ys).reshape(h, w)
    res = abs(transform.a)
    valid = np.isfinite(dem)

    def coverage(mask_fn, area_m2):
        return float((mask_fn & valid).sum() * res * res / area_m2) if area_m2 > 0 else 0.0

    cx, cy = centre_xy
    r0 = np.hypot(xs - cx, ys - cy)
    disc5_cov = coverage(r0 < 5000, np.pi * 5000 ** 2)
    centre_refined = disc5_cov >= 0.9
    if centre_refined:
        cx, cy = fit_centre(dem, xs, ys, cx, cy, half_width_m)

    r = np.hypot(xs - cx, ys - cy)
    step = max(res, 100.0)
    bins = np.arange(0, half_width_m, step)
    idx = np.digitize(r, bins)
    prof_r, prof_z, prof_cov = [], [], []
    for k in range(1, len(bins)):
        sel = (idx == k) & valid
        ring_area = np.pi * (bins[k] ** 2 - bins[k - 1] ** 2) if k < len(bins) else 0
        if sel.sum() > 10:
            prof_r.append(bins[k - 1] + step / 2)
            prof_z.append(np.nanmean(dem[sel]))
            prof_cov.append(sel.sum() * res * res / ring_area if ring_area else 0)
    prof_r, prof_z, prof_cov = map(np.array, (prof_r, prof_z, prof_cov))

    # A ring needs >= 15 % coverage to count; stay away from the crop edge.
    usable = (prof_cov >= 0.15) & (prof_r < 0.95 * half_width_m)
    if not usable.any():
        raise SystemExit("No ring around the centre is covered well enough - wrong tile?")
    rim_r = float(prof_r[usable][np.argmax(prof_z[usable])])
    rim_cov = coverage(np.abs(r - rim_r) <= rim_band_m, np.pi * ((rim_r + rim_band_m) ** 2 - max(rim_r - rim_band_m, 0) ** 2))
    floor_cov = coverage(r < 0.4 * rim_r, np.pi * (0.4 * rim_r) ** 2)
    has_floor = floor_cov >= 0.5

    zones = np.zeros(dem.shape, dtype="uint8")
    zones[(np.abs(r - rim_r) <= rim_band_m) & valid] = 2
    rim_elev = float(np.nanmedian(dem[zones == 2]))
    inside_min = float(np.nanmin(np.where(r < rim_r, dem, np.nan)))
    if has_floor:
        floor_min = float(np.nanmin(dem[(r < 0.4 * rim_r) & valid]))
        zones[(r < 0.4 * rim_r) & (dem < floor_min + 300) & valid] = 1
        depth = rim_elev - floor_min
    else:
        floor_min, depth = None, None

    info = {
        "centre_xy_m": [round(float(cx), 1), round(float(cy), 1)],
        "centre_refined_from_dem": bool(centre_refined),
        "rim_radius_km": round(rim_r / 1000, 2),
        "rim_diameter_km": round(2 * rim_r / 1000, 2),
        "rim_median_elev_m": round(rim_elev, 1),
        "floor_min_elev_m": None if floor_min is None else round(floor_min, 1),
        "depth_rim_to_floor_m": None if depth is None else round(depth, 1),
        "depth_to_diameter": None if depth is None else round(depth / (2 * rim_r), 3),
        "lowest_point_inside_rim_m": round(inside_min, 1),
        "depth_lower_bound_m": round(rim_elev - inside_min, 1),
        "coverage": {"rim_ring": round(rim_cov, 2), "floor_disc": round(floor_cov, 2)},
        "floor_pixels": int((zones == 1).sum()),
        "rim_pixels": int((zones == 2).sum()),
    }
    if not has_floor:
        print(f"WARNING: the file covers only {floor_cov:.0%} of the crater floor, so no floor zone "
              "and no depth were written. 'depth_lower_bound_m' is rim minus the lowest point "
              "this file reaches; the real depth is larger.")
    if rim_cov < 0.5:
        print(f"NOTE: the file covers {rim_cov:.0%} of the rim ring; rim numbers describe that part only.")
    return zones, info, (prof_r, prof_z)


def hillshade(dem, res, az=315.0, alt=30.0):
    gy, gx = np.gradient(np.nan_to_num(dem, nan=np.nanmean(dem)), res)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    az, alt = np.radians(az), np.radians(alt)
    return np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect)


def quicklook(dem, zones, transform, profile, info, out_png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    res = abs(transform.a)
    left, top = transform.c, transform.f
    h, w = dem.shape
    ext = [left / 1000, (left + w * res) / 1000, (top - h * res) / 1000, top / 1000]

    fig, ax = plt.subplots(1, 2, figsize=(12, 5.5))
    ax[0].imshow(hillshade(dem, res), cmap="gray", extent=ext)
    over = np.ma.masked_where(zones == 0, zones)
    ax[0].imshow(over, cmap="cool", alpha=0.45, extent=ext, vmin=1, vmax=2)
    ax[0].set_title("Shackleton: hillshade, floor (blue) and rim (pink)")
    ax[0].set_xlabel("x (km, polar stereographic)")
    ax[0].set_ylabel("y (km)")

    pr, pz = profile
    ax[1].plot(pr / 1000, pz, color="black")
    ax[1].axvline(info["rim_radius_km"], ls="--", color="tab:red", label="rim radius")
    ax[1].set_xlabel("distance from crater centre (km)")
    ax[1].set_ylabel("mean elevation (m)")
    depth_txt = (f"depth ≈ {info['depth_rim_to_floor_m'] / 1000:.1f} km"
                 if info["depth_rim_to_floor_m"] is not None
                 else f"depth > {info['depth_lower_bound_m'] / 1000:.1f} km (floor not in file)")
    ax[1].set_title(f"radial profile: D ≈ {info['rim_diameter_km']} km, {depth_txt}")
    ax[1].legend()
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=130)
    plt.close(fig)


def write_tif(path, arr, transform, crs, dtype, nodata):
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1],
        count=1, dtype=dtype, crs=crs, transform=transform, nodata=nodata,
        compress="deflate",
    ) as dst:
        dst.write(arr.astype(dtype), 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dem", help="LOLA LDEM GeoTIFF path, or an https:// URL of a cloud-optimized one")
    ap.add_argument("--res", type=float, default=30.0, help="output pixel size in m (match the Earth DEM)")
    ap.add_argument("--half-width-km", type=float, default=18.0, help="half-size of the crop box")
    ap.add_argument("--out-dir", type=Path, default=Path("."), help="repo root")
    args = ap.parse_args()

    dem, transform, crs, centre = load_crop(args.dem, args.half_width_km * 1000, args.res)
    nan_frac = float(np.isnan(dem).mean())
    print(f"crop: {dem.shape[1]}x{dem.shape[0]} px at {args.res:.0f} m, no-data fraction {nan_frac:.1%}")

    zones, info, profile = zone_crater(dem, transform, centre, args.half_width_km * 1000)
    info.update({
        "source_file": os.path.basename(args.dem),
        "output_pixel_m": args.res,
        "crop_half_width_km": args.half_width_km,
        "nodata_fraction": round(nan_frac, 4),
        "elevation_reference": "height above 1737.4 km sphere (LOLA convention)",
    })

    tag = f"{int(args.res)}m"
    root = args.out_dir
    write_tif(root / f"data/dem/moon/shackleton_dem_{tag}.tif", np.nan_to_num(dem, nan=-9999), transform, crs, "float32", -9999)
    write_tif(root / f"data/dem/moon/shackleton_zones_{tag}.tif", zones, transform, crs, "uint8", None)
    quicklook(dem, zones, transform, profile, info, root / "figures/moon/shackleton_quicklook.png")
    (root / "data/results").mkdir(parents=True, exist_ok=True)
    (root / "data/results/moon_dem_summary.json").write_text(json.dumps(info, indent=2))

    print(json.dumps(info, indent=2))
    print("Check: Shackleton is usually quoted at ~21 km across. If rim_diameter_km is far off, "
          "or the quicklook shows a cut-off crater, use the 87S mosaic or widen --half-width-km.")


if __name__ == "__main__":
    main()
