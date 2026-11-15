"""Accessibility display values (criterion 26). NOT part of the Moon score.

ACCESS_HOURS   travel time to the nearest city in hours, read at one lon/lat point from the global
               "travel time to cities 2015" raster (Weiss et al. 2018, Nature 553, doi:10.1038/nature25181;
               Malaria Atlas Project). The raster stores minutes on a 30 arcsec (~1 km) grid, 85 N to 60 S.
AIRPORT_KM     great-circle distance to the nearest medium or large airport (OurAirports airports.csv),
AIRPORT_NAME   its name, AIRPORT_TYPE its OurAirports type.

No data is None, never 0 (team rule of 14 Nov 2026): outside the raster (south of 60 S, north of 85 N),
on a no-data pixel (sea), or a non-finite / negative value.

See docs/ACCESS.md for source, licence and limits.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window

EARTH_RADIUS_KM = 6371.0088          # IUGG mean radius
AIRPORT_TYPES = ("medium_airport", "large_airport")


class TravelTimeRaster:
    """Point lookup in the travel-time raster (EPSG:4326, values in minutes).

        with TravelTimeRaster(path) as tt:
            hours = tt.hours(lon, lat)     # float, or None = no data
    """

    def __init__(self, path, units_per_hour: float = 60.0):
        self.path = Path(path)
        self.ds = rasterio.open(self.path)
        if self.ds.crs is not None and self.ds.crs.to_epsg() != 4326:
            raise ValueError(f"{self.path}: expected EPSG:4326, got {self.ds.crs}")
        self.units_per_hour = float(units_per_hour)
        self.nodata = self.ds.nodata

    def close(self):
        self.ds.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def minutes(self, lon: float, lat: float) -> float | None:
        """Raw raster value (minutes) of the pixel that contains the point; None = no data."""
        if lon is None or lat is None or not (math.isfinite(lon) and math.isfinite(lat)):
            return None
        b = self.ds.bounds
        lon = float(lon)
        if b.right <= lon <= 360.0 and lon - 360.0 >= b.left:      # accept 0..360 longitudes
            lon -= 360.0
        if not (b.left <= lon < b.right and b.bottom < lat <= b.top):
            return None
        row, col = self.ds.index(lon, lat)
        if not (0 <= row < self.ds.height and 0 <= col < self.ds.width):
            return None
        value = float(self.ds.read(1, window=Window(col, row, 1, 1))[0, 0])
        if not math.isfinite(value) or value < 0:
            return None
        if self.nodata is not None and value == self.nodata:
            return None
        return value

    def hours(self, lon: float, lat: float) -> float | None:
        """Travel time to the nearest city in hours; None = no data (never 0 for missing data)."""
        m = self.minutes(lon, lat)
        return None if m is None else m / self.units_per_hour


def travel_time_hours(lon: float, lat: float, raster_path) -> float | None:
    """One-off lookup. For many points keep one TravelTimeRaster open instead."""
    with TravelTimeRaster(raster_path) as tt:
        return tt.hours(lon, lat)


# ---------------------------------------------------------------- airports (OurAirports)

def load_airports(csv_path, types=AIRPORT_TYPES) -> pd.DataFrame:
    """OurAirports airports.csv -> rows of the given types with valid coordinates.

    Columns kept: ident, type, name, latitude_deg, longitude_deg, iso_country. keep_default_na=False
    so that the country code "NA" (Namibia) is not read as missing.
    """
    cols = ["ident", "type", "name", "latitude_deg", "longitude_deg", "iso_country"]
    df = pd.read_csv(csv_path, usecols=cols, keep_default_na=False, dtype=str)
    df = df[df["type"].isin(types)].copy()
    for c in ("latitude_deg", "longitude_deg"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[np.isfinite(df["latitude_deg"]) & np.isfinite(df["longitude_deg"])]
    df = df[df["latitude_deg"].between(-90, 90) & df["longitude_deg"].between(-180, 180)]
    return df[cols].reset_index(drop=True)


def haversine_km(lon1, lat1, lon2, lat2):
    """Great-circle distance in km on a sphere of mean Earth radius (numpy broadcasting)."""
    lon1, lat1, lon2, lat2 = (np.radians(np.asarray(v, dtype=float)) for v in (lon1, lat1, lon2, lat2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def nearest_airport(lon: float, lat: float, airports: pd.DataFrame) -> dict:
    """Nearest airport of `airports` (from load_airports) by great-circle distance.

    Returns {"airport_km", "airport_name", "airport_type", "airport_ident"}; all None if there is
    no airport in the table or the point is invalid.
    """
    empty = {"airport_km": None, "airport_name": None, "airport_type": None, "airport_ident": None}
    if len(airports) == 0 or lon is None or lat is None or not (math.isfinite(lon) and math.isfinite(lat)):
        return empty
    d = haversine_km(lon, lat, airports["longitude_deg"].to_numpy(), airports["latitude_deg"].to_numpy())
    i = int(np.argmin(d))
    row = airports.iloc[i]
    return {"airport_km": float(d[i]), "airport_name": row["name"], "airport_type": row["type"],
            "airport_ident": row["ident"]}
