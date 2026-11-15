"""Offline, readable place names for exported cells: "34 km SW of Balkhash" + country.

Data (not in the repo, data/ rule; default folder ${LOCALAPPDATA}/espaceodyssey_data):
    naturalearth/extracted/ne_10m_admin_0_countries.shp   Natural Earth 1:10m Admin 0 countries (public domain)
        https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_0_countries.zip
    geonames/extracted/cities1000.txt                     GeoNames populated places >= 1000 people (CC BY 4.0)
        https://download.geonames.org/export/dump/cities1000.zip
Country = Natural Earth polygon containing the point (de-facto borders as drawn by Natural Earth; nearest
polygon within 25 km for points on a coastline). Name = nearest GeoNames place, with distance and direction.
No network access at run time.
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _unit(lat, lon):
    la, lo = math.radians(lat), math.radians(lon)
    return (math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la))


def bearing_word(lat_from, lon_from, lat_to, lon_to) -> str:
    """8-point direction of 'to' as seen from 'from' (initial great-circle bearing)."""
    p1, p2 = math.radians(lat_from), math.radians(lat_to)
    dl = math.radians(lon_to - lon_from)
    b = math.degrees(math.atan2(math.sin(dl) * math.cos(p2),
                                math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)))
    return DIRS[int(((b + 360) % 360 + 22.5) // 45) % 8]


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(min(1.0, a)))


class PlaceNames:
    def __init__(self, data_dir: Path | str):
        import numpy as np
        import pyogrio
        import shapely
        from scipy.spatial import cKDTree
        d = Path(data_dir)
        shp = d / "naturalearth" / "extracted" / "ne_10m_admin_0_countries.shp"
        txt = d / "geonames" / "extracted" / "cities1000.txt"
        missing = [str(p) for p in (shp, txt) if not p.exists()]
        if missing:
            raise FileNotFoundError(f"place-name data missing: {missing}")
        df = pyogrio.read_dataframe(str(shp), columns=["NAME", "ADMIN"])
        self.c_names = [str(n or a or "") for n, a in zip(df["NAME"], df["ADMIN"])]
        self.c_geoms = shapely.make_valid(df.geometry.to_numpy())
        self.c_tree = shapely.STRtree(self.c_geoms)
        names, lats, lons, pops = [], [], [], []
        csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))
        with open(txt, encoding="utf-8", newline="") as f:
            for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
                if len(row) < 15:
                    continue
                names.append(row[1] or row[2])
                lats.append(float(row[4]))
                lons.append(float(row[5]))
                pops.append(int(row[14] or 0))
        self.p_names, self.p_lat, self.p_lon, self.p_pop = names, lats, lons, pops
        self.p_tree = cKDTree(np.array([_unit(a, b) for a, b in zip(lats, lons)]))
        self.n_places = len(names)
        geo = d / "naturalearth" / "extracted" / "ne_10m_geography_regions_polys.shp"
        self.r_names, self.r_geoms, self.r_tree = [], None, None
        if geo.exists():                                   # optional: names for remote places
            g = pyogrio.read_dataframe(str(geo), columns=["NAME", "NAME_EN", "FEATURECLA"])
            g = g[~g["FEATURECLA"].isin(["Continent", "Dragons-be-here"])]      # too coarse to name a place
            self.r_names = [_tidy(en or n) for n, en in zip(g["NAME"], g["NAME_EN"])]
            self.r_geoms = shapely.make_valid(g.geometry.to_numpy())
            self.r_area = shapely.area(self.r_geoms)
            self.r_tree = shapely.STRtree(self.r_geoms)

    def country(self, lat: float, lon: float) -> str:
        import shapely
        pt = shapely.points(lon, lat)
        idx = self.c_tree.query(pt, predicate="intersects")
        if len(idx):
            return self.c_names[int(idx[0])]
        i = self.c_tree.nearest(pt)                         # coast: nearest polygon within ~25 km
        if i is not None and float(shapely.distance(self.c_geoms[i], pt)) * 111.0 <= 25.0:
            return self.c_names[int(i)]
        return ""

    def nearest(self, lat: float, lon: float) -> tuple[str, float, str]:
        """(place name, distance km, direction of the point as seen from the place). Among the places within
        1.5 x the nearest distance the most populous wins: better known, and robust to single misplaced
        GeoNames entries (e.g. a duplicate 'LeChee' next to Winslow AZ)."""
        dist, idx = self.p_tree.query(_unit(lat, lon), k=12)
        cand = [(haversine_km(self.p_lat[i], self.p_lon[i], lat, lon), i) for i in idx if i < self.n_places]
        d0 = min(c[0] for c in cand)
        km, i = max((c for c in cand if c[0] <= max(1.5 * d0, d0 + 2.0)), key=lambda c: (self.p_pop[c[1]], -c[0]))
        return self.p_names[i], km, bearing_word(self.p_lat[i], self.p_lon[i], lat, lon)

    def region(self, lat: float, lon: float) -> str:
        """Smallest Natural Earth geographic region (desert, range, plateau, island, ...) containing the point."""
        if self.r_tree is None:
            return ""
        import shapely
        idx = self.r_tree.query(shapely.points(lon, lat), predicate="intersects")
        return self.r_names[int(min(idx, key=lambda i: self.r_area[i]))] if len(idx) else ""

    def label(self, lat: float, lon: float) -> str:
        """'34 km SW of Balkhash'; remote (> 60 km): 'Tibesti Mountains (85 km NE of Bardai)'; > 400 km: region
        or 'remote <country>'. No commas (the app splits on ',')."""
        name, km, d = self.nearest(lat, lon)
        town = name.replace(",", " ").strip()
        near = f"near {town}" if km < 2 else f"{km:.0f} km {d} of {town}"
        if km <= 60:
            return near
        reg = self.region(lat, lon).replace(",", " ")
        if km <= 400:
            return f"{reg} ({near})" if reg else near
        return reg or f"remote {self.country(lat, lon) or 'area'}".strip()


def _tidy(name) -> str:
    """'SOUTHERN ALPS' -> 'Southern Alps', 'Hentiyn Mts.' -> 'Hentiyn Mountains'."""
    s = str(name or "").strip()
    if s.isupper():
        s = s.title()
    for a, b in ((" Mts.", " Mountains"), (" Mts", " Mountains"), (" Mt.", " Mount"), (" I.", " Island"),
                 (" Is.", " Islands"), ("Pen. ", "Peninsula "), (" Pen.", " Peninsula")):
        s = s.replace(a, b)
    return s
