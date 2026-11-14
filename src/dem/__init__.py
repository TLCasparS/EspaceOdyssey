"""Copernicus DEM access and terrain metrics for EspaceOdyssey."""

from .fetch import tile_url, tiles_for_bbox, read_bbox
from .landcover import CLASSES, worldcover_url, worldcover_tiles, read_landcover
from .terrain import pixel_size_m, slope_deg, roughness, local_relief, tri, summarize

__all__ = [
    "tile_url", "tiles_for_bbox", "read_bbox",
    "CLASSES", "worldcover_url", "worldcover_tiles", "read_landcover",
    "pixel_size_m", "slope_deg", "roughness", "local_relief", "tri", "summarize",
]
