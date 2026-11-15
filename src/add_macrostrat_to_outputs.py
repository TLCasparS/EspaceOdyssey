"""Add the Macrostrat display columns to an EXISTING export folder, without re-running the export.

Use when the inputs of the full export (region runs, mining polygons, place names, GLiM grid) are not on
this machine. It does exactly what `src/export_app.py --macrostrat` adds, with the same functions
(src/pipeline/macrostrat.py), and nothing else:

    raw_values.csv  five columns appended at the end of every line; the existing bytes of each line are kept
    targets.json    key "_rock_site" added
    README.md       section "Rock at the site (Macrostrat ...)" added (same place as in the full export)

    python src/add_macrostrat_to_outputs.py --macrostrat data/macrostrat/rock_site.csv --out outputs

Running it twice is refused (the columns are already there).
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline import macrostrat as ms  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
README_BEFORE = "\n## config-v1.1: post-run filters"       # the full export writes the section before this one


def _csv_fields(values: list[str], terminator: str) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator=terminator).writerow(values)
    return buf.getvalue()


def add_columns(raw_bytes: bytes, table: dict) -> bytes:
    """Append ms.COLUMNS to every line of raw_values.csv; every original line stays a byte-exact prefix."""
    text = raw_bytes.decode("utf-8")
    terminator = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(terminator)
    if lines and lines[-1] == "":
        lines.pop()
    header = next(csv.reader([lines[0]]))
    if any(c in header for c in ms.COLUMNS):
        raise SystemExit("raw_values.csv already has Macrostrat columns")
    i_run, i_cell = header.index("RUN"), header.index("CELL")
    out = [lines[0] + "," + _csv_fields(ms.COLUMNS, "")]
    for line in lines[1:]:
        row = next(csv.reader([line]))                      # no field of this file contains a line break
        if len(row) != len(header):
            raise SystemExit(f"raw_values.csv: unexpected number of fields in line: {line[:80]}")
        out.append(line + "," + _csv_fields(ms.export_values(table, row[i_run], row[i_cell]), ""))
    return (terminator.join(out) + terminator).encode("utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--macrostrat", type=Path, default=ROOT / "data" / "macrostrat" / "rock_site.csv")
    ap.add_argument("--out", type=Path, default=ROOT / "outputs")
    a = ap.parse_args(argv)
    table = ms.load_rock_site(a.macrostrat)

    raw_path = a.out / "raw_values.csv"
    old = raw_path.read_bytes()
    new = add_columns(old, table)
    raw_path.write_bytes(new)

    t_path = a.out / "targets.json"
    targets = json.loads(t_path.read_text(encoding="utf-8"))
    targets["_rock_site"] = ms.export_meta(table)
    t_path.write_bytes((json.dumps(targets, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))

    r_path = a.out / "README.md"
    readme = r_path.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in readme else "\n"
    section = ms.export_readme(table).replace("\n", nl)
    marker = README_BEFORE.replace("\n", nl)
    if "## Rock at the site (Macrostrat" not in readme:
        k = readme.find(marker)
        readme = readme + section if k < 0 else readme[:k] + section + readme[k:]
        r_path.write_bytes(readme.encode("utf-8"))

    n_old, n_new = old.count(b"\n"), new.count(b"\n")
    joined = sum(1 for k in table if k)
    print(f"raw_values.csv: {n_old} -> {n_new} lines, {len(ms.COLUMNS)} columns added; rock_site rows: {joined}")
    print("targets.json: _rock_site added; README.md: section added")


if __name__ == "__main__":
    main()
