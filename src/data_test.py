"""Data test: plot one elevation cross-section from any raster file.
Usage: python data_test.py <file> <x1> <y1> <x2> <y2>
"""
import sys
import numpy as np
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1]
x1, y1, x2, y2 = map(float, sys.argv[2:6])

with rasterio.open(path) as src:
    print("size:", src.width, "x", src.height, "| coordinate system:", src.crs)
    xs = np.linspace(x1, x2, 500)
    ys = np.linspace(y1, y2, 500)
    heights = np.array([v[0] for v in src.sample(zip(xs, ys))], dtype=float)

print("min %.0f m, max %.0f m, relief %.0f m" % (heights.min(), heights.max(), np.ptp(heights)))
plt.plot(heights)
plt.xlabel("sample along the line")
plt.ylabel("elevation (m)")
plt.title(path)
plt.savefig("profile.png", dpi=120)
print("saved profile.png")
