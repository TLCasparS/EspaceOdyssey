"""Compatibility shim: the metric-grid code now lives in src/dem/grid.py and src/dem/terrain.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dem.grid import MetricGrid, crop_center, metric_crs_for, to_metric_grid  # noqa: E402,F401
from dem.terrain import Terrain, compute_terrain  # noqa: E402,F401
