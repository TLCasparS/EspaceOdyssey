"""Rock class at lon/lat points from GLiM (Hartmann & Moosdorf 2012), first level only.

For each point:
    rock_class        first-level GLiM code of the polygon under the point (None = no data: sea, or GLiM "nd")
    share_<code>      area share of each class within `radius_km` of the point, relative to the
                      COVERED part of the disc (sea / no polygon is left out, not counted as 0)
    covered_share     part of the disc that has any GLiM polygon (0..1)
If nothing within the disc is covered, all shares are None ("no data, never 0").

Sources (same algorithm for all, only the loader differs):
    GridSource        PANGAEA 0.5 deg raster (doi:10.1594/PANGAEA.788537, CC-BY 3.0): each grid cell is
                      turned into a square polygon carrying its DOMINANT class. Shares are then only the
                      overlap of the disc with ~55 km cells, not the real rock mix within 5 km.
    PolygonFileSource full GLiM polygons (e.g. "LiMW_GIS 2015.gdb", not downloaded, see docs/MATERIAL.md);
                      read per 2 deg tile with a bbox filter, so only the needed area is loaded.
    FrameSource       any GeoDataFrame in EPSG:4326 (used by the tests).

Areas are measured in a local azimuthal equidistant projection centred on each point, so the 5 km disc
is a true circle at every latitude.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import shapely
from pyproj import CRS, Transformer
from shapely.geometry import Point, box

# First-level GLiM classes (Hartmann & Moosdorf 2012, G3 13 Q12004, table 2)
CLASSES = {
    "su": "unconsolidated sediments",
    "ss": "siliciclastic sedimentary rocks",
    "sm": "mixed sedimentary rocks",
    "sc": "carbonate sedimentary rocks",
    "py": "pyroclastics",
    "ev": "evaporites",
    "mt": "metamorphics",
    "pa": "acid plutonic rocks",
    "pi": "intermediate plutonic rocks",
    "pb": "basic plutonic rocks",
    "va": "acid volcanic rocks",
    "vi": "intermediate volcanic rocks",
    "vb": "basic volcanic rocks",
    "ig": "ice and glaciers",
    "wb": "water bodies",
    "nd": "no data",
}
CODES = [c for c in CLASSES if c != "nd"]   # "nd" = GLiM no data: treated like sea, never a share
KM_PER_DEG = 111.32


def first_level(value) -> str | None:
    """'vb', 'VB', 'vbpy' (three-level code) -> 'vb'; unknown or empty -> None."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    code = str(value).strip().lower()[:2]
    return code if code in CLASSES else None


def disc_bbox(lon: float, lat: float, radius_km: float) -> tuple[float, float, float, float]:
    """Lon/lat box that contains the disc (slightly generous)."""
    dlat = radius_km / KM_PER_DEG * 1.05
    c = math.cos(math.radians(min(abs(lat) + dlat, 89.9)))
    dlon = min(180.0, radius_km / (KM_PER_DEG * c) * 1.05)
    return lon - dlon, max(-90.0, lat - dlat), lon + dlon, min(90.0, lat + dlat)


class FrameSource:
    """GeoDataFrame (EPSG:4326) with a class column; spatial index from geopandas."""

    def __init__(self, gdf, class_field: str = "xx"):
        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(4326)
        self.geoms = np.asarray(gdf.geometry.values, dtype=object)
        self.codes = np.array([first_level(v) for v in gdf[class_field]], dtype=object)
        self.tree = shapely.STRtree(self.geoms)

    def features(self, bbox):
        idx = self.tree.query(box(*bbox))
        return self.geoms[idx], self.codes[idx]


class GridSource:
    """GLiM ESRI ASCII grid (dominant class per cell) + Classnames.txt (Value_ -> xx code)."""

    def __init__(self, asc_path, classnames_path=None):
        asc_path = Path(asc_path)
        header = {}
        with open(asc_path) as f:
            for _ in range(6):
                k, v = f.readline().split()
                header[k.lower()] = float(v)
        self.ncols, self.nrows = int(header["ncols"]), int(header["nrows"])
        self.x0, self.y0 = header["xllcorner"], header["yllcorner"]
        self.cell = header["cellsize"]
        self.nodata = header["nodata_value"]
        self.data = np.loadtxt(asc_path, skiprows=6).reshape(self.nrows, self.ncols)
        self.lut = self._read_classnames(classnames_path or asc_path.with_name("Classnames.txt"))

    @staticmethod
    def _read_classnames(path) -> dict[int, str]:
        lut = {}
        for line in Path(path).read_text().splitlines()[1:]:
            parts = [p.strip().strip('"') for p in line.split(";")]
            if len(parts) >= 4 and first_level(parts[3]):
                lut[int(float(parts[1]))] = first_level(parts[3])
        return lut

    def features(self, bbox):
        w, s, e, n = bbox
        geoms, codes = [], []
        top = self.y0 + self.nrows * self.cell
        r0 = max(0, int(math.floor((top - n) / self.cell)))
        r1 = min(self.nrows - 1, int(math.floor((top - s) / self.cell)))
        for lon_shift in (-360.0, 0.0, 360.0):        # wrap boxes that cross the antimeridian
            ww, ee = w + lon_shift, e + lon_shift
            if ee < self.x0 or ww > self.x0 + self.ncols * self.cell:
                continue
            c0 = max(0, int(math.floor((ww - self.x0) / self.cell)))
            c1 = min(self.ncols - 1, int(math.floor((ee - self.x0) / self.cell)))
            for r in range(r0, r1 + 1):
                for c in range(c0, c1 + 1):
                    v = self.data[r, c]
                    if v == self.nodata:
                        continue
                    xw = self.x0 + c * self.cell - lon_shift
                    yn = top - r * self.cell
                    geoms.append(box(xw, yn - self.cell, xw + self.cell, yn))
                    codes.append(self.lut.get(int(v)))
        return np.array(geoms, dtype=object), np.array(codes, dtype=object)


class PolygonFileSource:
    """Full GLiM polygons from a file (FileGDB, GeoPackage, shapefile). Reads one 2 deg tile at a time
    with a bbox filter and keeps it in memory, so only the area around the points is loaded."""

    def __init__(self, path, layer=None, class_field: str = "xx", tile_deg: float = 2.0):
        self.path, self.layer, self.class_field, self.tile_deg = str(path), layer, class_field, tile_deg
        self._tiles: dict[tuple[int, int], FrameSource | None] = {}

    def _tile(self, key):
        if key not in self._tiles:
            import pyogrio
            t = self.tile_deg
            bb = (key[0] * t, key[1] * t, (key[0] + 1) * t, (key[1] + 1) * t)
            if not hasattr(self, "_crs"):
                self._crs = pyogrio.read_info(self.path, layer=self.layer).get("crs")
            if self._crs and CRS(self._crs).to_epsg() != 4326:
                # the bbox filter works in the layer CRS (the layer may be projected): transform it
                bb = Transformer.from_crs(4326, self._crs, always_xy=True).transform_bounds(*bb, densify_pts=21)
            gdf = pyogrio.read_dataframe(self.path, layer=self.layer, bbox=bb, columns=[self.class_field])
            self._tiles[key] = FrameSource(gdf, self.class_field) if len(gdf) else None
        return self._tiles[key]

    def features(self, bbox):
        t = self.tile_deg
        geoms, codes = [], []
        for i in range(int(math.floor(bbox[0] / t)), int(math.floor(bbox[2] / t)) + 1):
            for j in range(int(math.floor(bbox[1] / t)), int(math.floor(bbox[3] / t)) + 1):
                src = self._tile((i, j))
                if src is not None:
                    g, c = src.features(bbox)
                    geoms.extend(g)
                    codes.extend(c)
        # a polygon crossing a tile edge comes back from both tiles: drop exact duplicates
        seen, keep_g, keep_c = set(), [], []
        for g, c in zip(geoms, codes):
            k = (g.wkb, c)
            if k not in seen:
                seen.add(k)
                keep_g.append(g)
                keep_c.append(c)
        return np.array(keep_g, dtype=object), np.array(keep_c, dtype=object)


def _to_local(geom, tf: Transformer):
    return shapely.transform(geom, lambda xy: np.column_stack(tf.transform(xy[:, 0], xy[:, 1])))


def classify_point(lon: float, lat: float, source, radius_km: float = 5.0) -> dict:
    """Rock class at the point and class shares within radius_km (see module docstring)."""
    out = {"rock_class": None, "covered_share": 0.0, **{f"share_{c}": None for c in CODES}}
    bbox = disc_bbox(lon, lat, radius_km)
    geoms, codes = source.features(bbox)
    if len(geoms) == 0:
        return out
    tf = Transformer.from_crs("EPSG:4326",
                              f"+proj=aeqd +lat_0={lat} +lon_0={lon} +datum=WGS84 +units=m +no_defs",
                              always_xy=True)
    r = radius_km * 1000.0
    disc = Point(0.0, 0.0).buffer(r, quad_segs=64)
    disc_area = disc.area
    areas = dict.fromkeys(CODES, 0.0)
    best_at_point = None
    for g, code in zip(geoms, codes):
        if code is None or code == "nd":
            continue
        g = shapely.clip_by_rect(shapely.make_valid(g), *bbox)
        if g.is_empty:
            continue
        g = shapely.segmentize(g, 0.02)      # densify before projecting so long edges bend correctly
        gl = _to_local(g, tf)
        a = gl.intersection(disc).area
        areas[code] += a
        if gl.covers(Point(0.0, 0.0)) and (best_at_point is None or a > best_at_point[1]):
            best_at_point = (code, a)
    covered = sum(areas.values())
    out["covered_share"] = round(min(1.0, covered / disc_area), 4)
    out["rock_class"] = best_at_point[0] if best_at_point else None
    if covered > 0:
        for c in CODES:
            out[f"share_{c}"] = round(areas[c] / covered, 4)
    return out


def classify_points(lons, lats, source, radius_km: float = 5.0) -> list[dict]:
    """classify_point for many points; NaN coordinates give a no-data row."""
    rows = []
    for lon, lat in zip(lons, lats):
        if lon is None or lat is None or not (np.isfinite(lon) and np.isfinite(lat)):
            rows.append({"rock_class": None, "covered_share": 0.0, **{f"share_{c}": None for c in CODES}})
        else:
            rows.append(classify_point(float(lon), float(lat), source, radius_km))
    return rows
