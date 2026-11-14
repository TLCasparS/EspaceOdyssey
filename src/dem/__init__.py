"""Copernicus DEM access and terrain metrics for EspaceOdyssey."""

from .fetch import tile_url, tiles_for_bbox, read_bbox
from .landcover import CLASSES, worldcover_url, worldcover_tiles, read_landcover
from .terrain import pixel_size_m, slope_deg, roughness, local_relief, tri, summarize, Terrain, compute_terrain
from .grid import MetricGrid, metric_crs_for, to_metric_grid, crop_center

__all__ = [
    "tile_url", "tiles_for_bbox", "read_bbox",
    "CLASSES", "worldcover_url", "worldcover_tiles", "read_landcover",
    "pixel_size_m", "slope_deg", "roughness", "local_relief", "tri", "summarize", "Terrain", "compute_terrain",
    "MetricGrid", "metric_crs_for", "to_metric_grid", "crop_center",
]
