"""Fine-scale rock type at a point from Macrostrat geologic maps (macrostrat.org, CC BY 4.0).

DISPLAY ONLY: never in a score, rank or config.

    https://macrostrat.org/api/v2/geologic_units/map?lat=..&lng=..&scale=large
    no unit -> retry scale=medium, then scale=small; the scale that answered is recorded.

Per place:
    ROCK_SITE         unit name (name, else strat_name)
    ROCK_SITE_LITH    lithology text of the unit (lith, else the first sentence of descrip)
    ROCK_SITE_SOURCE  name of the source map (Macrostrat /defs/sources)
    ROCK_SITE_SCALE   large / medium / small
    BASALT_SITE       1 basalt / mafic volcanic, 0 clearly something else, None unknown or no answer
                      (never 0 for missing)

Several maps can overlap at one point (e.g. a surface map and a basement map). The unit used is the
YOUNGEST one (smallest top age, then smallest base age, then first in the response): the surface
geology is the youngest unit, a buried basement is older.

Every response is cached on disk (one JSON file per request), so a run can be stopped and resumed.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://macrostrat.org/api/v2"
SCALES = ("large", "medium", "small")
USER_AGENT = "espaceodyssey-rock-lookup (python urllib)"
CREDIT = "Macrostrat (macrostrat.org), CC BY 4.0"
COLUMNS = ["ROCK_SITE", "ROCK_SITE_LITH", "ROCK_SITE_SOURCE", "ROCK_SITE_SCALE", "BASALT_SITE"]

# --- basalt rule -------------------------------------------------------------------------------
# 1: a basalt / mafic-volcanic word in the unit's MAIN lithology
BASALT_RE = re.compile(
    r"(?<!meta)(?<!meta-)basalt|basanit|tholeiit|hawaiit|mugearit|picrit|nephelinit|"   # metabasalt = metamorphic
    r"\b(?:mafic|basic)[\s-]+(?:volcanic|lava|flow|extrusive)|"
    r"\bvolcanic[\s-]+rocks?[\s,;(-]+(?:mafic|basic)\b|\bmafic[\s-]+volcanics?\b", re.I)
# unknown: volcanic / igneous rock without a composition (could be basalt, could be rhyolite)
VAGUE_RE = re.compile(r"\b(?:volcanic|volcanics|volcanite|volcanoclastic|volcaniclastic|lavas?|igneous|extrusive|"
                      r"pyroclastic|scoria|cinder|tephra|tuff|undifferentiated|undivided|unknown|unmapped)\b", re.I)
# words that name a composition or rock that is clearly not basalt
OTHER_RE = re.compile(
    r"granit|gneiss|schist|sandstone|limestone|dolomit|dolostone|shale|mudstone|siltstone|conglomerat|"
    r"carbonate|evaporit|gypsum|salt\b|marble|quartzit|slate|phyllit|rhyolit|dacit|andesit|trachyt|"
    r"phonolit|ignimbrit|felsic|silicic|sediment|alluvi|colluvi|aeolian|eolian|dune|sand\b|gravel|clay|"
    r"loess|till\b|glacial|moraine|lacustrine|fluvial|marine|plutonic|intrusive|diorit|gabbro|syenit|"
    r"peridotit|ultramafic|serpentinit|metamorph|migmatit|amphibolit|chert|marl|coal|laterit|calcrete|"
    r"sabkha|playa|ice\b|water\b|siliciclastic|clastic|turbidit|flysch|molasse|greywacke|graywacke|"
    r"argillit|pelit|psammit|arenit|arkose|breccia|mylonit|ophiolit|melange|komatiit|dolerit|diabase|"
    r"tonalit|granodiorit|granitoid|chalk|mudrock|\bmud\b|\bsilt\b|rhythmit|deposits?\b|terrace|piedmont", re.I)
MAJOR_RE = re.compile(r"major\s*:?\s*\{([^}]*)\}", re.I)


def main_lith(lith: str) -> str:
    """'Major:{basalt}, Minor:{latite}' -> 'basalt'; any other text is returned unchanged."""
    m = MAJOR_RE.search(lith or "")
    return m.group(1).strip() if m else (lith or "").strip()


def basalt_flag(lith: str, name: str = "") -> int | None:
    """1 basalt / mafic volcanic, 0 clearly something else, None unknown.

    The lithology text decides first (only its Major part, if the map separates Major and Minor):
      basalt word -> 1; a clear non-basalt rock word -> 0.
    If the lithology is empty or names no composition (e.g. "volcanic rocks"), the unit NAME decides the
    same way. Nothing recognisable -> None. A unit that lists basalt together with other rocks counts as 1.
    """
    for text in (main_lith(lith), (name or "").strip()):
        if not text:
            continue
        if BASALT_RE.search(text):
            return 1
        if OTHER_RE.search(text):
            return 0
    return None


# --- parsing -----------------------------------------------------------------------------------

def units_of(response: dict) -> list[dict]:
    """Map units in one API response ([] if none or an error response)."""
    data = (response or {}).get("success", {}).get("data")
    return [u for u in data if isinstance(u, dict)] if isinstance(data, list) else []


def _age(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return float("inf")


def pick_unit(units: list[dict]) -> dict | None:
    """Youngest unit: smallest top age, then smallest base age, then first in the response."""
    if not units:
        return None
    return min(enumerate(units), key=lambda iu: (_age(iu[1].get("t_age")), _age(iu[1].get("b_age")), iu[0]))[1]


def first_sentence(text: str, limit: int = 160) -> str:
    s = re.split(r"(?<=[.;])\s", (text or "").strip(), maxsplit=1)[0].strip()
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + "…"


def source_name(response: dict, unit: dict, source_names: dict | None = None) -> str:
    """Map name from /defs/sources (source_names: {source_id: name}); else the reference in the response."""
    sid = unit.get("source_id")
    if source_names and source_names.get(str(sid)):
        return source_names[str(sid)]
    ref = (response.get("success", {}).get("refs") or {}).get(str(sid), "")
    return ref.strip()


def parse_place(responses: dict, source_names: dict | None = None) -> dict:
    """responses: {scale: API response} for the scales that were asked, in any order.

    Returns the COLUMNS for the first scale of SCALES that has a unit, plus n_units (at that scale)
    and source_id. No unit at any scale -> all None (BASALT_SITE None, never 0).
    """
    out = {c: None for c in COLUMNS} | {"n_units": 0, "source_id": None}
    for scale in SCALES:
        resp = responses.get(scale)
        units = units_of(resp) if resp else []
        if not units:
            continue
        u = pick_unit(units)
        name = (u.get("name") or u.get("strat_name") or "").strip()
        lith = (u.get("lith") or "").strip() or first_sentence(u.get("descrip") or "")
        out.update(ROCK_SITE=name or None, ROCK_SITE_LITH=lith or None,
                   ROCK_SITE_SOURCE=source_name(resp, u, source_names) or None, ROCK_SITE_SCALE=scale,
                   BASALT_SITE=basalt_flag(u.get("lith") or "", name), n_units=len(units),
                   source_id=u.get("source_id"))
        return out
    return out


# --- cached, rate-limited client ---------------------------------------------------------------

class Client:
    """GET with an on-disk cache, a request rate limit and retries with backoff.

    bytes_downloaded counts response bodies fetched from the network in this session (cache hits: 0).
    """

    def __init__(self, cache_dir, max_per_second: float = 3.0, retries: int = 6, timeout: float = 60.0,
                 opener=None, sleep=time.sleep):
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.min_gap = 1.0 / max_per_second
        self.retries, self.timeout = retries, timeout
        self._open = opener or self._urlopen
        self._sleep = sleep
        self._next = 0.0                                # earliest start time of the next request
        self._lock = threading.Lock()                   # the client may be shared by a few threads
        self.bytes_downloaded = 0
        self.n_requests = 0
        self.n_cached = 0

    def _urlopen(self, url: str) -> bytes:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return r.read()

    def _path(self, url: str) -> Path:
        return self.cache / (hashlib.sha1(url.encode()).hexdigest() + ".json")

    def get(self, url: str) -> dict:
        path = self._path(url)
        if path.exists():
            try:
                self.n_cached += 1
                return json.loads(path.read_text(encoding="utf-8"))["response"]
            except (ValueError, KeyError):
                self.n_cached -= 1                      # broken cache file: fetch again
        last = None
        for attempt in range(self.retries):
            with self._lock:                            # one global queue: never above max_per_second
                start = max(time.monotonic(), self._next)
                self._next = start + self.min_gap
            wait = start - time.monotonic()
            if wait > 0:
                self._sleep(wait)
            try:
                body = self._open(url)
                resp = json.loads(body)
                if "success" not in resp:
                    raise ValueError(f"no 'success' in response: {str(resp)[:200]}")
            except (urllib.error.URLError, TimeoutError, ConnectionError, ValueError, OSError) as e:
                last = e
                self._sleep(min(60.0, 2.0 ** attempt))
                continue
            with self._lock:
                self.n_requests += 1
                self.bytes_downloaded += len(body)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"url": url, "bytes": len(body), "response": resp}), encoding="utf-8")
            tmp.replace(path)
            return resp
        raise RuntimeError(f"Macrostrat request failed after {self.retries} tries: {url}: {last}")

    def cache_bytes(self) -> int:
        """Total size of all response bodies in the cache (all sessions)."""
        total = 0
        for p in self.cache.glob("*.json"):
            try:
                total += int(json.loads(p.read_text(encoding="utf-8")).get("bytes", 0))
            except ValueError:
                pass
        return total


def unit_url(lon: float, lat: float, scale: str) -> str:
    q = urllib.parse.urlencode({"lat": f"{lat:.5f}", "lng": f"{lon:.5f}", "scale": scale})
    return f"{API}/geologic_units/map?{q}"


def lookup(lon: float, lat: float, client: Client, source_names: dict | None = None) -> dict:
    """Ask large, then medium, then small until a unit comes back; parse it."""
    responses = {}
    for scale in SCALES:
        responses[scale] = client.get(unit_url(lon, lat, scale))
        if units_of(responses[scale]):
            break
    res = parse_place(responses, source_names)
    if res["source_id"] is not None and source_names is not None and str(res["source_id"]) not in source_names:
        src = client.get(f"{API}/defs/sources?source_id={res['source_id']}")
        rows = units_of(src)
        source_names[str(res["source_id"])] = (rows[0].get("name") or "").strip() if rows else ""
        res = parse_place(responses, source_names)
    return res


# --- export helpers (src/export_app.py --macrostrat, src/add_macrostrat_to_outputs.py) ----------

EXPORT_NOTE = "geological map unit at the site; resolution depends on the source map (ROCK_SITE_SCALE)"


def load_rock_site(path) -> dict:
    """data/macrostrat/rock_site.csv -> {(RUN, CELL): {column: text}} with RUN = 'night_<run>'.

    Values stay text exactly as in the file; empty = no data (BASALT_SITE empty is never turned into 0).
    """
    import csv
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[(f"night_{r['run']}", r["cell"])] = {c: (r.get(c) or "").strip() for c in COLUMNS}
    return out


def export_values(table: dict, run: str, cell: str) -> list[str]:
    """The COLUMNS for one export row, as text; a place without a row gets empty values."""
    row = table.get((run or "", cell or ""))
    return [row[c] if row else "" for c in COLUMNS]


def export_meta(table: dict) -> dict:
    """targets.json -> _rock_site: display only, with the note and the credit."""
    return {"source": CREDIT, "license": "CC BY 4.0", "url": "https://macrostrat.org",
            "score_method": "display", "counts": False, "weight": 0, "note": EXPORT_NOTE,
            "columns": [{"column": c, "score_method": "display", "counts": False, "weight": 0, "note": EXPORT_NOTE}
                        for c in COLUMNS],
            "basalt_rule": ("BASALT_SITE = 1 if the unit's main lithology (or, failing that, its name) names basalt "
                            "or a mafic volcanic rock; 0 if it clearly names another rock; empty = unknown or no "
                            "map unit (never 0 for missing). Where several maps overlap, the youngest unit is used."),
            "scales": "large, then medium, then small: the first scale with a map unit at the point",
            "point": "Mare base pad", "n_places": len(table),
            "details": "docs/MACROSTRAT_REPORT.md"}


def export_readme(table: dict) -> str:
    """Section for outputs/README.md."""
    n = {}
    for v in table.values():
        k = (v["ROCK_SITE_SCALE"] or "no answer", v["BASALT_SITE"] or "unknown")
        n[k] = n.get(k, 0) + 1
    order = {s: i for i, s in enumerate((*SCALES, "no answer"))}
    return f"""
## Rock at the site (Macrostrat, display only; never in a score)
`raw_values.csv` columns {', '.join(f'`{c}`' for c in COLUMNS)}, at the Mare base pad. Source: **{CREDIT}**.
- `ROCK_SITE` = name of the geological map unit under the point, `ROCK_SITE_LITH` = its lithology text,
  `ROCK_SITE_SOURCE` = the source map, `ROCK_SITE_SCALE` = `large` / `medium` / `small` (the first Macrostrat scale
  with a unit at the point). Note: {EXPORT_NOTE}.
- `BASALT_SITE` = 1 basalt / mafic volcanic, 0 clearly another rock, **empty = unknown or no map unit** (never 0 for
  missing). Rule and limits: docs/MACROSTRAT_REPORT.md. The GLiM columns above stay as the regional (0.5°) view.

| ROCK_SITE_SCALE | BASALT_SITE | places |
|---|---|---|
""" + "".join(f"| {s} | {b} | {c} |\n" for (s, b), c in sorted(n.items(), key=lambda kv: (order.get(kv[0][0], 9), kv[0][1])))
