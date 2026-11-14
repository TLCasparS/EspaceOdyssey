"""Guards for config/lunar_targets.json: no lunar number without a source (rule: never invent numbers)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline.config import TARGETS_PATH  # noqa: E402

TARGETS = json.loads(Path(TARGETS_PATH).read_text(encoding="utf-8"))


def _entries(obj, path="root"):
    """Every dict in the file that carries a 'value' or a 'verified' field, with its path."""
    if isinstance(obj, dict):
        if "value" in obj or "verified" in obj:
            yield path, obj
        for k, v in obj.items():
            yield from _entries(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _entries(v, f"{path}[{i}]")


def _has_source(e):
    return isinstance(e.get("source"), str) and e["source"].strip() != ""


def test_verified_values_have_a_source():
    bad = [p for p, e in _entries(TARGETS) if e.get("verified") is True and not _has_source(e)]
    assert not bad, f"verified=true but no source: {bad}"


def test_every_number_has_a_source():
    bad = [p for p, e in _entries(TARGETS) if e.get("value") is not None and not _has_source(e)]
    assert not bad, f"value without source (set it to null or name the LOLA/LROC source): {bad}"


def test_guard_catches_a_missing_source():
    fake = {"polar": {"criteria": {"x": {"value": 1.0, "verified": True, "source": ""}}}}
    assert [p for p, e in _entries(fake) if e.get("verified") is True and not _has_source(e)] == \
        ["root.polar.criteria.x"]
