"""config-v1.1 post-run filters for Polar places (config/post_filters.yaml).

config-v1 stays frozen: these filters never change a score. They only mark a place as excluded, with a reason:
    mine      low point inside a mining polygon (Maus et al. 2022, v2)
    dry_bowl  BARE_SHARE < bare_min, or ICE_FLOOR_SHARE > ice_floor_max, or ICE_RIM_SHARE > ice_rim_max
A share without data is not tested (no data is never 0). Used by src/export_app.py --post-filters.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "config" / "post_filters.yaml"


def expand(p: str) -> Path:
    """${LOCALAPPDATA}/... -> real path (falls back to the home folder like src/night_run.py)."""
    env = dict(os.environ)
    env.setdefault("LOCALAPPDATA", str(Path.home()))
    out = str(p)
    for k in ("LOCALAPPDATA", "USERPROFILE", "HOME"):
        if k in env:
            out = out.replace("${" + k + "}", env[k]).replace("%" + k + "%", env[k])
    return Path(out)


def load(path: Path | str = DEFAULT) -> dict:
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _f(v):
    if v in (None, ""):
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def dry_bowl_fails(rec: dict, cfg: dict) -> list[str]:
    """Which dry-bowl tests fail, e.g. ['BARE_SHARE 0.16 < 0.3', 'ICE_RIM_SHARE 0.41 > 0.2']; [] = passes."""
    out = []
    bare, ice_f, ice_r = _f(rec.get("bare_share")), _f(rec.get("ice_floor_share")), _f(rec.get("ice_rim_share"))
    if bare is not None and bare < cfg["bare_min"]:
        out.append(f"BARE_SHARE {bare:.2f} < {cfg['bare_min']:g}")
    if ice_f is not None and ice_f > cfg["ice_floor_max"]:
        out.append(f"ICE_FLOOR_SHARE {ice_f:.2f} > {cfg['ice_floor_max']:g}")
    if ice_r is not None and ice_r > cfg["ice_rim_max"]:
        out.append(f"ICE_RIM_SHARE {ice_r:.2f} > {cfg['ice_rim_max']:g}")
    return out


class MineMask:
    """Mining polygons (EPSG:4326) with a spatial index. hit(): point inside; dist_km(): distance to the
    nearest polygon edge in km (local equirectangular metres, fine at < ~20 km)."""

    def __init__(self, path: Path | str):
        import pyogrio
        import shapely
        df = pyogrio.read_dataframe(str(path), columns=["ISO3_CODE", "COUNTRY_NAME", "AREA"])
        self.geoms = shapely.make_valid(df.geometry.to_numpy())
        self.tree = shapely.STRtree(self.geoms)
        self.n = len(self.geoms)
        self.area_km2 = df["AREA"].to_numpy()
        self.country = df["COUNTRY_NAME"].to_numpy()

    def hit(self, lat: float, lon: float) -> int | None:
        """Index of a polygon that contains the point (boundary counts), else None."""
        import shapely
        idx = self.tree.query(shapely.points(lon, lat), predicate="intersects")
        return int(idx[0]) if len(idx) else None

    def dist_km(self, lat: float, lon: float, max_km: float = 5.0) -> float | None:
        """Distance to the nearest polygon within max_km (0 = inside), else None."""
        import shapely
        k = math.cos(math.radians(lat))
        dlat, dlon = max_km / 110.6, max_km / (111.3 * max(k, 0.05))
        idx = self.tree.query(shapely.box(lon - dlon, lat - dlat, lon + dlon, lat + dlat))
        if not len(idx):
            return None

        def to_km(a):
            out = a.copy()
            out[:, 0] = (a[:, 0] - lon) * 111.3 * k
            out[:, 1] = (a[:, 1] - lat) * 110.6
            return out
        origin = shapely.points(0.0, 0.0)
        best = None
        for i in idx:
            d = float(shapely.distance(shapely.transform(self.geoms[i], to_km), origin))
            best = d if best is None else min(best, d)
        return None if best is None or best > max_km else round(best, 3)


class PostFilters:
    """config-v1.1 for one export: evaluate(row) -> list of reasons ([] = keeps its rank)."""

    def __init__(self, cfg: dict, mines: MineMask | None = None, mines_missing: str | None = None):
        self.cfg = cfg
        self.mines = mines
        self.mines_missing = mines_missing                   # why the mine filter could not run (or None)
        self.base_types = set(cfg.get("base_types") or ["polar"])

    @classmethod
    def from_file(cls, path: Path | str = DEFAULT) -> "PostFilters":
        cfg = load(path)
        mp = expand(cfg["mine"]["path"]) if cfg.get("mine") else None
        if mp is None:
            return cls(cfg, None, "no mine section")
        if not mp.exists():
            return cls(cfg, None, f"mining polygons not found at {mp}")
        return cls(cfg, MineMask(mp))

    def evaluate(self, base: str, lat, lon, rec: dict) -> dict:
        """{'reasons': [...], 'details': [...], 'mine_idx': i | None, 'mine_dist_km': d | None}."""
        out = {"reasons": [], "details": [], "mine_idx": None, "mine_dist_km": None}
        if base not in self.base_types:
            return out
        lat, lon = _f(lat), _f(lon)
        if self.mines is not None and lat is not None and lon is not None:
            i = self.mines.hit(lat, lon)
            out["mine_idx"] = i
            near = self.cfg["mine"].get("near_km", 1.0)
            out["mine_dist_km"] = 0.0 if i is not None else self.mines.dist_km(lat, lon, max(near, 5.0))
            if i is not None:
                out["reasons"].append(self.cfg["mine"]["reason"])
                out["details"].append(f"inside a mapped mining area of {self.mines.area_km2[i]:.1f} km2 "
                                      f"in {self.mines.country[i]} (Maus et al. 2022 v2 polygon {i})")
        if self.cfg.get("dry_bowl"):
            fails = dry_bowl_fails(rec, self.cfg["dry_bowl"])
            if fails:
                out["reasons"].append(self.cfg["dry_bowl"]["reason"])
                out["details"].extend(fails)
        return out
