"""Confirmed impact structures for criterion 24 (display only): Wikipedia "List of impact craters on Earth"
-> data/impact/impact_structures.csv (name, lat, lon, diameter_km, age, country, source).

    curl -L -o data/impact/wikipedia_list_of_impact_craters.html "https://en.wikipedia.org/wiki/List_of_impact_craters_on_Earth"
    python src/impact_list.py

The page lists confirmed structures (based on the Earth Impact Database) in age sections; it is NOT complete
(88 rows with coordinates on 14 Nov 2026; the criteria doc says the Earth Impact Database has ~190). A place
that is not matched is therefore "not in this list", not "proven not an impact crater".
Parsed with the standard library only (pandas is blocked on the team laptop).
"""
from __future__ import annotations

import csv
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "impact" / "wikipedia_list_of_impact_craters.html"
OUT = ROOT / "data" / "impact" / "impact_structures.csv"
PAGE = "https://en.wikipedia.org/wiki/List_of_impact_craters_on_Earth"


def _text(cell: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", cell))).strip()


def parse(page: str) -> list[dict]:
    rev = re.search(r'"wgRevisionId":(\d+)', page)
    source = f"{PAGE}?oldid={rev.group(1)}" if rev else PAGE
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        g = re.search(r'class="geo"[^>]*>([-\d.]+);\s*([-\d.]+)<', row)
        if not g:
            continue
        cells = [_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        # columns: name | region | country | diameter (km) | age (Ma); numbers may carry a zero-padded sort key
        diam = re.search(r"\d+(?:\.\d+)?", cells[3]) if len(cells) > 3 else None
        out.append({"name": cells[0], "lat": float(g.group(1)), "lon": float(g.group(2)),
                    "diameter_km": float(diam.group(0)) if diam else None,
                    "age": cells[4] if len(cells) > 4 else "", "country": cells[2] if len(cells) > 2 else "",
                    "source": source})
    return out


def load(path: Path = OUT) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return [{**r, "lat": float(r["lat"]), "lon": float(r["lon"]),
                 "diameter_km": float(r["diameter_km"]) if r["diameter_km"] else None} for r in csv.DictReader(f)]


def main():
    rows = parse(SRC.read_text(encoding="utf-8"))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["name", "lat", "lon", "diameter_km", "age", "country", "source"])
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} impact structures -> {OUT}")


if __name__ == "__main__":
    main()
