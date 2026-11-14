"""Rank candidate sites by how much they behave like the lunar south pole.

Usage (from the repo root):
    python src/run_shadow_sites.py                      # all sites in config/sites.csv
    python src/run_shadow_sites.py --only rjukan        # one site
    python src/run_shadow_sites.py --demo               # synthetic crater, no internet

Outputs: data/results/shadow_scores.csv and figures/shadow/<site>.png
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shadowsim import load_site, run_site, synthetic_crater  # noqa: E402


def plot_site(name, grid, res, out_png: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    r0, r1, c0, c1 = grid.window
    ext = [-(c1 - c0) * grid.dx_m / 2000, (c1 - c0) * grid.dx_m / 2000,
           -(r1 - r0) * grid.dy_m / 2000, (r1 - r0) * grid.dy_m / 2000]
    panels = [
        (grid.window_z, "Elevation (m)", "terrain"),
        (res.lit_fraction * 100, "Direct sun, % of year", "inferno"),
        (res.terrain_shadow_fraction * 100, "Terrain shadow, % of daylight", "Blues"),
        (res.max_dark_days, "Longest run without sun (days)", "Purples"),
    ]
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.6), constrained_layout=True)
    for ax, (data, title, cmap) in zip(axes, panels):
        im = ax.imshow(data, extent=ext, cmap=cmap)
        ax.set_title(title)
        ax.set_xlabel("km east")
        fig.colorbar(im, ax=ax, shrink=0.85)
    axes[0].set_ylabel("km north")
    fig.suptitle(f"{name}  ({grid.lat:.3f}, {grid.lon:.3f})")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sites", default="config/sites.csv")
    p.add_argument("--only", help="run just this site name")
    p.add_argument("--radius-km", type=float, default=5.0, help="half-width of analysis square")
    p.add_argument("--horizon-km", type=float, default=20.0, help="how far to look for blocking terrain")
    p.add_argument("--year", type=int, default=2026)
    p.add_argument("--step-min", type=int, default=60, help="time step in minutes")
    p.add_argument("--azimuths", type=int, default=72, help="horizon sectors (72 = every 5 deg)")
    p.add_argument("--out", default="data/results/shadow_scores.csv")
    p.add_argument("--fig-dir", default="figures/shadow")
    p.add_argument("--demo", action="store_true", help="synthetic 20 km crater at 75 N")
    a = p.parse_args()

    if a.demo:
        jobs = [("synthetic_crater_75N", lambda: synthetic_crater())]
    else:
        with open(a.sites, newline="") as f:
            rows = [r for r in csv.DictReader(f) if not a.only or r["name"] == a.only]
        jobs = [(r["name"], lambda r=r: load_site(float(r["lat"]), float(r["lon"]), a.radius_km,
                                                  a.horizon_km, name=r["name"])) for r in rows]

    results = []
    for name, loader in jobs:
        t0 = time.time()
        print(f"[{name}] loading DEM ...", flush=True)
        grid = loader()
        print(f"[{name}] {grid.window_z.shape} cells, pixel {grid.dx_m:.0f} x {grid.dy_m:.0f} m; simulating ...", flush=True)
        res, _, summary = run_site(grid, a.year, a.step_min, a.azimuths, a.horizon_km)
        plot_site(name, grid, res, Path(a.fig_dir) / f"{name}.png")
        results.append({"name": name, "lat": grid.lat, "lon": grid.lon, **summary})
        print(f"[{name}] done in {time.time() - t0:.0f} s: {summary}", flush=True)

    results.sort(key=lambda r: r["analog_score"], reverse=True)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    print(f"\nRanking written to {out}")
    for r in results:
        print(f"  {r['analog_score']:.3f}  {r['name']}")


if __name__ == "__main__":
    np.seterr(invalid="ignore")
    main()
