"""Macrostrat rock at the site (src/pipeline/macrostrat.py): parser and basalt rule on saved API responses.

tests/fixtures/macrostrat/*.json are real responses saved on 15 Nov 2026 (Macrostrat, CC BY 4.0). No network.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline import macrostrat as ms  # noqa: E402
from add_macrostrat_to_outputs import add_columns  # noqa: E402

FIX = Path(__file__).parent / "fixtures" / "macrostrat"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


EMPTY, IDAHO, TUAREG, SOURCE = (load(n) for n in ("empty_large.json", "idaho_medium.json", "tuareg_small.json",
                                                  "source_546.json"))


# ---------------------------------------------------------------- basalt rule

@pytest.mark.parametrize("lith, name, want", [
    ("basalt, latite", "", 1),
    ("Major:{basalt}, Minor:{latite}", "", 1),
    ("Major:{rhyolite}, Minor:{basalt}", "", 0),            # basalt only as a minor rock
    ("mafic volcanic rocks", "", 1),
    ("Basic volcanics", "", 1),                             # basic = mafic
    ("volcanic rocks, mafic", "", 1),
    ("alkali basalt and basanite flows", "", 1),
    ("tholeiitic lava", "", 1),
    ("gneiss, granite", "", 0),
    ("with ediacaran metamorphism (tuareg shield)", "", 0),
    ("sandstone, shale", "Basalt Creek Formation", 0),      # the lithology decides before the name
    ("rhyolite", "", 0),
    ("andesite, basalt", "", 1),                            # basalt listed with other rocks counts as 1
    ("pelitic gneiss/schist, marble, metabasalt, gabbro", "", 0),   # metabasalt is metamorphic, not a lava plain
    ("Major:{chalk}, Minor{marl,limestone}", "", 0),
    ("", "Floodplain deposits of the Rio Grande", 0),
    ("gabbro", "", 0),                                      # mafic but intrusive: not a lava plain
    ("volcanic rocks", "", None),                           # could be basalt or rhyolite: unknown
    ("volcanic rocks", "Columbia River Basalt Group", 1),   # vague lithology: the name decides
    ("", "Quaternary basalt flows", 1),
    ("", "Dune sand", 0),
    ("", "Quaternary volcanics", None),
    ("", "", None),
    (None, None, None),
])
def test_basalt_rule(lith, name, want):
    assert ms.basalt_flag(lith, name) == want


def test_main_lith_takes_the_major_part():
    assert ms.main_lith("Major:{basalt}, Minor:{latite}") == "basalt"
    assert ms.main_lith("basalt, latite") == "basalt, latite"
    assert ms.main_lith("") == ""


# ---------------------------------------------------------------- parser

def test_units_of_handles_empty_and_broken_responses():
    assert ms.units_of(EMPTY) == []
    assert ms.units_of({}) == []
    assert ms.units_of({"error": {"message": "x"}}) == []
    assert len(ms.units_of(IDAHO)) == 3


def test_youngest_unit_is_picked_not_the_basement():
    """Idaho: two Quaternary basalt maps and an Archean basement map overlap; the basement must not win."""
    u = ms.pick_unit(ms.units_of(IDAHO))
    assert u["name"] == "Basalt (Quaternary)"
    assert u["t_age"] == 0 and u["b_age"] == 0.126
    assert ms.pick_unit([]) is None
    same_age = [{"name": "a", "t_age": 1, "b_age": 2}, {"name": "b", "t_age": 1, "b_age": 2}]
    assert ms.pick_unit(same_age)["name"] == "a"            # tie: first in the response
    assert ms.pick_unit([{"name": "no age"}, {"name": "aged", "t_age": 5, "b_age": 9}])["name"] == "aged"


def test_parse_place_uses_the_first_scale_with_a_unit():
    res = ms.parse_place({"large": EMPTY, "medium": IDAHO})
    assert res["ROCK_SITE_SCALE"] == "medium"
    assert res["ROCK_SITE"] == "Basalt (Quaternary)"
    assert res["ROCK_SITE_LITH"] == "Major:{basalt}, Minor:{latite}"
    assert res["ROCK_SITE_SOURCE"].startswith("Horton, J.D.")          # no source table: the reference text
    assert res["BASALT_SITE"] == 1
    assert res["n_units"] == 3 and res["source_id"] == 133


def test_parse_place_small_scale_free_text_lithology():
    res = ms.parse_place({"large": EMPTY, "medium": EMPTY, "small": TUAREG}, {"190": "Geological map of Africa"})
    assert res["ROCK_SITE_SCALE"] == "small"
    assert res["ROCK_SITE"] is None                                    # the unit has no name
    assert res["ROCK_SITE_LITH"] == "with ediacaran metamorphism (tuareg shield)"
    assert res["ROCK_SITE_SOURCE"] == "Geological map of Africa"
    assert res["BASALT_SITE"] == 0


def test_no_answer_is_empty_never_zero():
    res = ms.parse_place({"large": EMPTY, "medium": EMPTY, "small": EMPTY})
    assert all(res[c] is None for c in ms.COLUMNS)
    assert res["BASALT_SITE"] is None and res["n_units"] == 0


def test_lith_falls_back_to_the_description():
    resp = {"success": {"data": [{"name": "Qv", "lith": "", "descrip": "Young lava flows. More text here.",
                                  "source_id": 1, "t_age": 0, "b_age": 1}], "refs": {}}}
    res = ms.parse_place({"large": resp})
    assert res["ROCK_SITE_LITH"] == "Young lava flows."
    assert res["BASALT_SITE"] is None            # the description never decides the flag; "Qv" says nothing


# ---------------------------------------------------------------- client: cache, retry, fallback

class FakeNet:
    """Answers by scale; can fail the first n calls. Counts calls."""

    def __init__(self, by_scale, fail_first=0):
        self.by_scale, self.fail, self.urls = by_scale, fail_first, []

    def __call__(self, url):
        self.urls.append(url)
        if self.fail > 0:
            self.fail -= 1
            raise ConnectionError("dropped")
        if "defs/sources" in url:
            return json.dumps(SOURCE).encode()
        scale = url.rsplit("scale=", 1)[1]
        return json.dumps(self.by_scale[scale]).encode()


def client(tmp_path, net):
    return ms.Client(tmp_path / "cache", max_per_second=1000, opener=net, sleep=lambda s: None)


def test_lookup_falls_back_large_medium_and_names_the_source(tmp_path):
    net = FakeNet({"large": EMPTY, "medium": IDAHO, "small": TUAREG})
    names = {}
    res = ms.lookup(-113.55, 43.42, client(tmp_path, net), names)
    assert [u.rsplit("scale=", 1)[1] for u in net.urls if "scale=" in u] == ["large", "medium"]   # small not asked
    assert res["ROCK_SITE_SCALE"] == "medium" and res["BASALT_SITE"] == 1
    assert res["ROCK_SITE_SOURCE"] == "Geologic map of Idaho: Idaho Geological Survey"   # fake net: source 546 text
    assert "lat=43.42000" in net.urls[0] and "lng=-113.55000" in net.urls[0]


def test_cache_makes_the_run_resumable(tmp_path):
    net = FakeNet({"large": EMPTY, "medium": EMPTY, "small": TUAREG})
    c1 = client(tmp_path, net)
    ms.lookup(6.15605, 24.06448, c1, {})
    n_first, bytes_first = len(net.urls), c1.bytes_downloaded
    assert n_first == 4 and bytes_first > 0                 # 3 scales + 1 source name
    c2 = client(tmp_path, net)                              # "restart": same cache folder
    res = ms.lookup(6.15605, 24.06448, c2, {})
    assert len(net.urls) == n_first                         # nothing asked again
    assert c2.bytes_downloaded == 0 and c2.n_cached == 4
    assert c2.cache_bytes() == bytes_first
    assert res["ROCK_SITE_SCALE"] == "small"


def test_retry_after_dropped_connection(tmp_path):
    net = FakeNet({"large": IDAHO}, fail_first=2)
    c = client(tmp_path, net)
    assert ms.units_of(c.get(ms.unit_url(-113.55, 43.42, "large")))
    assert len(net.urls) == 3 and c.n_requests == 1


def test_gives_up_after_all_retries_and_caches_nothing(tmp_path):
    net = FakeNet({"large": IDAHO}, fail_first=99)
    c = ms.Client(tmp_path / "cache", max_per_second=1000, retries=3, opener=net, sleep=lambda s: None)
    with pytest.raises(RuntimeError):
        c.get(ms.unit_url(0, 0, "large"))
    assert list((tmp_path / "cache").glob("*.json")) == []


# ---------------------------------------------------------------- export helpers

ROCK_CSV = ("run,cell,lon,lat,ROCK_SITE,ROCK_SITE_LITH,ROCK_SITE_SOURCE,ROCK_SITE_SCALE,BASALT_SITE,N_UNITS,SOURCE_ID\n"
            'mare,c1,1,2,Basalt,"basalt, latite","Map, with comma",medium,1,3,546\n'
            "mare,c2,1,2,,,,,,,\n")


@pytest.fixture()
def table(tmp_path):
    p = tmp_path / "rock_site.csv"
    p.write_text(ROCK_CSV, encoding="utf-8")
    return ms.load_rock_site(p)


def test_export_values_join_on_run_and_cell(table):
    assert ms.export_values(table, "night_mare", "c1") == ["Basalt", "basalt, latite", "Map, with comma", "medium", "1"]
    assert ms.export_values(table, "night_mare", "c2") == ["", "", "", "", ""]      # no answer: empty, not 0
    assert ms.export_values(table, "night_polar", "c1") == [""] * 5
    assert ms.export_values(table, "", "") == [""] * 5                              # missed known site


def test_export_meta_is_display_only(table):
    m = ms.export_meta(table)
    assert m["score_method"] == "display" and m["weight"] == 0 and m["counts"] is False
    assert m["note"] == "geological map unit at the site; resolution depends on the source map (ROCK_SITE_SCALE)"
    assert [c["column"] for c in m["columns"]] == ms.COLUMNS
    assert "CC BY 4.0" in m["source"] and "Macrostrat" in m["source"]
    assert "Macrostrat (macrostrat.org), CC BY 4.0" in ms.export_readme(table)


@pytest.mark.parametrize("nl", ["\n", "\r\n"])
def test_add_columns_keeps_every_existing_byte(table, nl):
    old = nl.join(["SITE,LAT,RUN,CELL,NOTE", 'A,1.5,night_mare,c1,"x, y"', "B,2,night_mare,c2,", "C,3,,,",
                   "D,4,night_polar,c1,z"]) + nl
    new = add_columns(old.encode(), table).decode()
    old_lines, new_lines = old.split(nl)[:-1], new.split(nl)[:-1]
    assert len(new_lines) == len(old_lines) and new.endswith(nl)
    assert all(n.startswith(o + ",") for o, n in zip(old_lines, new_lines))
    assert new_lines[0].endswith(",ROCK_SITE,ROCK_SITE_LITH,ROCK_SITE_SOURCE,ROCK_SITE_SCALE,BASALT_SITE")
    assert new_lines[1].endswith(',Basalt,"basalt, latite","Map, with comma",medium,1')
    assert new_lines[2].endswith("night_mare,c2,,,,,,")
    assert new_lines[4].endswith(",z,,,,,")
    with pytest.raises(SystemExit):
        add_columns(new.encode(), table)                    # columns already there
