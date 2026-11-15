"""Research station display values (criterion 29): pipeline.stations, build_stations, compute_stations."""
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
pytest.importorskip("rasterio")      # pipeline.access (haversine) imports rasterio

import build_stations  # noqa: E402
from compute_stations import STATION_COLUMNS, add_station_columns, station_values  # noqa: E402
from pipeline.stations import STATION_FIELDS, load_stations, nearest_station  # noqa: E402


@pytest.fixture()
def stations(tmp_path):
    rows = [
        {"name": "North Station", "lat": 70.0, "lon": 20.0, "type": "research station", "analog": "no"},
        {"name": "South Base", "lat": -70.0, "lon": 20.0, "type": "Station", "analog": "no"},
        {"name": "Desert Habitat", "lat": 38.0, "lon": -110.0, "type": "habitat", "analog": "yes"},
        {"name": "Bad Row", "lat": "", "lon": 5.0, "type": "x", "analog": "no"},
    ]
    p = tmp_path / "stations.csv"
    pd.DataFrame(rows).reindex(columns=STATION_FIELDS).to_csv(p, index=False)
    return load_stations(p)


def test_rows_without_coordinates_are_dropped(stations):
    assert list(stations["name"]) == ["North Station", "South Base", "Desert Habitat"]


def test_nearest_any_and_nearest_analog(stations):
    near = nearest_station(21.0, 70.0, stations)
    assert near["station_name"] == "North Station"
    assert 30 < near["station_km"] < 45            # 1 deg lon at 70 N ~ 38 km
    ana = nearest_station(21.0, 70.0, stations, analog_only=True)
    assert ana["station_name"] == "Desert Habitat" and ana["station_km"] > 5000


def test_on_the_station_is_a_real_zero(stations):
    assert nearest_station(20.0, 70.0, stations)["station_km"] == pytest.approx(0.0, abs=1e-6)


def test_no_analog_rows_and_bad_points_are_no_data(stations):
    no_analog = stations[stations["analog"] == "no"]
    assert nearest_station(0.0, 0.0, no_analog, analog_only=True)["station_km"] is None
    assert nearest_station(float("nan"), 0.0, stations)["station_name"] is None
    v = station_values("", "", stations)
    assert v["STATION_KM"] == "" and v["ANALOG_STATION_KM"] == ""          # empty, never 0


def test_add_columns_keeps_old_columns_and_replaces_station_columns(stations):
    df = pd.DataFrame({"run": ["polar", "mare"], "cell": ["a", "b"], "lon": ["21.0", ""], "lat": ["70.0", ""],
                       "ACCESS_HOURS": ["1.5", ""], "STATION_KM": ["999", "999"]})
    out = add_station_columns(df, stations)
    assert list(out.columns) == ["run", "cell", "lon", "lat", "ACCESS_HOURS"] + STATION_COLUMNS
    assert out.loc[0, "STATION_NAME"] == "North Station" and out.loc[1, "STATION_KM"] == ""
    assert list(out["ACCESS_HOURS"]) == ["1.5", ""]


def test_build_from_small_sources(tmp_path):
    interact = tmp_path / "interact_stationlist.json"
    interact.write_text(json.dumps([
        {"StationName": "Arctic Station", "Latitude": 69.25, "Longitude": -53.5, "OperatingCountry": "Denmark",
         "OperatingPeriod": "year-round", "StationType": 0, "StationStatus": 0, "Hidden": False, "OpeningYear": 1906,
         "Email": "private@example.org"},
        {"StationName": "Hidden One", "Latitude": 60.0, "Longitude": 60.0, "Hidden": True},
        {"StationName": "Antarctic Base", "Latitude": -72.01, "Longitude": 362.5, "StationType": 0,
         "StationStatus": 0, "Hidden": False},                                  # 0..360 lon -> 2.5
    ]), encoding="utf-8")
    manual = tmp_path / "manual.csv"
    pd.DataFrame([{"name": "Hab", "operator": "X", "lat": 38.4, "lon": -110.8, "type": "habitat", "season": "",
                   "analog": "yes", "source": "https://example.org", "note": ""}]).to_csv(manual, index=False)
    dest = tmp_path / "stations.csv"
    build_stations.main(["--src-dir", str(tmp_path), "--manual", str(manual), "--dest", str(dest)])
    out = pd.read_csv(dest, keep_default_na=False, dtype=str)
    assert list(out.columns) == STATION_FIELDS
    assert list(out["name"]) == ["Arctic Station", "Antarctic Base", "Hab"]
    assert out.loc[0, "season"] == "Year-Round" and "private" not in dest.read_text()
    assert float(out.loc[1, "lon"]) == pytest.approx(2.5)
    assert list(out["analog"]) == ["no", "no", "yes"]
