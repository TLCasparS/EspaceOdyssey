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
         python src/moon_dem.py data/dem/moon/ldem_87s_5mpp.tif
         python src/moon_dem.py <dem.tif> --res 30 --half-width-km 18
"""
import argparse
import json
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


def load_crop(path: Path, half_width_m: float, res_m: float):
    """Windowed read around Shackleton, averaged down to res_m pixels.

    Only the crop is read from disk, so this works on the multi-GB mosaic.
    """
    with rasterio.open(path) as src:
        crs = src.crs if src.crs else CRS.from_proj4(MOON_SPS)
        native_res = abs(src.transform.a)
        print(f"file: {path.name}  native pixel: {native_res:.1f} m  size: {src.width}x{src.height}")
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


def zone_crater(dem, transform, centre_xy, rim_band_m=1000.0):
    """Find the crater centre, rim radius and floor from the DEM itself.

    - centre: the lowest point within 5 km of the catalogue position
    - rim radius: the radius where the mean radial elevation peaks
    - rim zone: a ring of +/- rim_band_m around that radius
    - floor zone: inside 40% of the rim radius and within 300 m of the lowest point
    """
    h, w = dem.shape
    cols, rows = np.meshgrid(np.arange(w), np.arange(h))
    xs, ys = rasterio.transform.xy(transform, rows.ravel(), cols.ravel())
    xs = np.asarray(xs).reshape(h, w)
    ys = np.asarray(ys).reshape(h, w)

    cx, cy = centre_xy
    near = np.hypot(xs - cx, ys - cy) < 5000
    cand = np.where(near & np.isfinite(dem), dem, np.inf)
    i, j = np.unravel_index(np.argmin(cand), dem.shape)
    cx, cy = xs[i, j], ys[i, j]

    r = np.hypot(xs - cx, ys - cy)
    res = abs(transform.a)
    bins = np.arange(0, r.max(), max(res, 100.0))
    idx = np.digitize(r, bins)
    prof_r, prof_z = [], []
    for k in range(1, len(bins)):
        sel = (idx == k) & np.isfinite(dem)
        if sel.sum() > 10:
            prof_r.append(bins[k - 1] + (bins[1] - bins[0]) / 2)
            prof_z.append(np.nanmean(dem[sel]))
    prof_r, prof_z = np.array(prof_r), np.array(prof_z)

    # The rim is the first big peak of the profile; ignore the outermost ring
    # where the crop edge can create false maxima.
    usable = prof_r < 0.9 * min(r[h // 2, 0], r[h // 2, -1], r[0, w // 2], r[-1, w // 2])
    rim_r = prof_r[usable][np.argmax(prof_z[usable])]

    floor_min = np.nanmin(dem[r < 0.4 * rim_r])
    zones = np.zeros(dem.shape, dtype="uint8")
    zones[(r < 0.4 * rim_r) & (dem < floor_min + 300)] = 1
    zones[np.abs(r - rim_r) <= rim_band_m] = 2
    zones[~np.isfinite(dem)] = 0

    rim_elev = float(np.nanmedian(dem[zones == 2]))
    info = {
        "refined_centre_xy_m": [float(cx), float(cy)],
        "rim_radius_km": round(float(rim_r) / 1000, 2),
        "rim_diameter_km": round(2 * float(rim_r) / 1000, 2),
        "rim_median_elev_m": round(rim_elev, 1),
        "floor_min_elev_m": round(float(floor_min), 1),
        "depth_rim_to_floor_m": round(rim_elev - float(floor_min), 1),
        "depth_to_diameter": round((rim_elev - float(floor_min)) / (2 * float(rim_r)), 3),
        "floor_pixels": int((zones == 1).sum()),
        "rim_pixels": int((zones == 2).sum()),
    }
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
    ax[1].set_title(f"radial profile: D ≈ {info['rim_diameter_km']} km, "
                    f"depth ≈ {info['depth_rim_to_floor_m'] / 1000:.1f} km")
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
    ap.add_argument("dem", type=Path, help="LOLA LDEM GeoTIFF (south polar stereographic)")
    ap.add_argument("--res", type=float, default=30.0, help="output pixel size in m (match the Earth DEM)")
    ap.add_argument("--half-width-km", type=float, default=18.0, help="half-size of the crop box")
    ap.add_argument("--out-dir", type=Path, default=Path("."), help="repo root")
    args = ap.parse_args()

    dem, transform, crs, centre = load_crop(args.dem, args.half_width_km * 1000, args.res)
    nan_frac = float(np.isnan(dem).mean())
    print(f"crop: {dem.shape[1]}x{dem.shape[0]} px at {args.res:.0f} m, no-data fraction {nan_frac:.1%}")

    zones, info, profile = zone_crater(dem, transform, centre)
    info.update({
        "source_file": args.dem.name,
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
