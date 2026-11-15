"""Accessibility display values (src/pipeline/access.py) on a small synthetic raster and airport list."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

from pipeline.access import (TravelTimeRaster, haversine_km, load_airports,  # noqa: E402
                             nearest_airport, travel_time_hours)

NODATA = -9999.0
RES = 0.5   # degrees


@pytest.fixture()
def raster(tmp_path):
    """0.5 deg grid, lon -180..180, lat 85..-60 (like the real map), value = minutes.

    Everything is 120 min, except: one 0-minute pixel (inside a city), one 90-minute pixel,
    one no-data pixel (sea) and one NaN pixel.
    """
    width, height = int(360 / RES), int(145 / RES)
    data = np.full((height, width), 120.0, dtype="float32")
    transform = from_origin(-180.0, 85.0, RES, RES)

    def px(lon, lat):
        return int((85.0 - lat) / RES), int((lon + 180.0) / RES)

    data[px(10.25, 50.25)] = 0.0       # city pixel: a real 0, not "no data"
    data[px(20.25, 40.25)] = 90.0
    data[px(-30.25, 0.25)] = NODATA    # sea
    data[px(-40.25, 0.25)] = np.nan
    path = tmp_path / "travel_time.tif"
    with rasterio.open(path, "w", driver="GTiff", width=width, height=height, count=1, dtype="float32",
                       crs="EPSG:4326", transform=transform, nodata=NODATA) as dst:
        dst.write(data, 1)
    return path


def test_minutes_become_hours(raster):
    with TravelTimeRaster(raster) as tt:
        assert tt.hours(20.25, 40.25) == pytest.approx(1.5)
        assert tt.hours(100.0, 10.0) == pytest.approx(2.0)
        assert tt.minutes(20.25, 40.25) == pytest.approx(90.0)


def test_point_anywhere_in_the_pixel_gives_its_value(raster):
    with TravelTimeRaster(raster) as tt:
        for lon, lat in [(20.01, 40.49), (20.49, 40.01), (20.25, 40.25)]:
            assert tt.hours(lon, lat) == pytest.approx(1.5)
        assert tt.hours(20.51, 40.25) == pytest.approx(2.0)     # the neighbour pixel


def test_real_zero_stays_zero(raster):
    """A pixel inside a city is 0 h: a measured value, different from no data."""
    with TravelTimeRaster(raster) as tt:
        assert tt.hours(10.25, 50.25) == 0.0


def test_south_of_60s_is_no_data_not_zero(raster):
    with TravelTimeRaster(raster) as tt:
        assert tt.hours(0.0, -60.01) is None
        assert tt.hours(166.67, -77.85) is None      # McMurdo, Antarctica
        assert tt.hours(0.0, -59.9) == pytest.approx(2.0)


def test_north_of_85n_and_bad_input_are_no_data(raster):
    with TravelTimeRaster(raster) as tt:
        assert tt.hours(0.0, 85.5) is None
        assert tt.hours(0.0, 91.0) is None
        assert tt.hours(float("nan"), 10.0) is None
        assert tt.hours(None, 10.0) is None
        assert tt.hours(500.0, 10.0) is None


def test_nodata_and_nan_pixels_are_no_data(raster):
    with TravelTimeRaster(raster) as tt:
        assert tt.hours(-30.25, 0.25) is None
        assert tt.hours(-40.25, 0.25) is None


def test_longitude_0_to_360_is_accepted(raster):
    with TravelTimeRaster(raster) as tt:
        assert tt.hours(329.75, 0.25) is None                    # = -30.25, the sea pixel
        assert tt.hours(200.0, 10.0) == pytest.approx(2.0)       # = -160


def test_one_off_lookup(raster):
    assert travel_time_hours(20.25, 40.25, raster) == pytest.approx(1.5)
    assert travel_time_hours(0.0, -70.0, raster) is None


def test_other_crs_is_refused(tmp_path):
    path = tmp_path / "utm.tif"
    with rasterio.open(path, "w", driver="GTiff", width=2, height=2, count=1, dtype="float32",
                       crs="EPSG:32633", transform=from_origin(500000, 5000000, 1000, 1000)) as dst:
        dst.write(np.ones((2, 2), dtype="float32"), 1)
    with pytest.raises(ValueError):
        TravelTimeRaster(path)


# ---------------------------------------------------------------- airports

AIRPORTS_CSV = '''"id","ident","type","name","latitude_deg","longitude_deg","elevation_ft","continent","iso_country"
1,"AAAA","large_airport","Big Airport",0.0,10.0,10,"AF","NA"
2,"BBBB","medium_airport","Middle Airport",0.0,12.0,10,"AF","NA"
3,"CCCC","small_airport","Small Strip",0.0,11.0,10,"AF","NA"
4,"DDDD","heliport","Helipad",0.0,11.4,10,"AF","NA"
5,"EEEE","closed","Closed Field",0.0,11.4,10,"AF","NA"
6,"FFFF","medium_airport","No Coordinates",,,10,"AF","NA"
7,"GGGG","medium_airport","Date Line Airport",0.0,-179.5,10,"OC","FJ"
'''


@pytest.fixture()
def airports(tmp_path):
    path = tmp_path / "airports.csv"
    path.write_text(AIRPORTS_CSV, encoding="utf-8")
    return load_airports(path)


def test_only_medium_and_large_airports_with_coordinates(airports):
    assert sorted(airports["ident"]) == ["AAAA", "BBBB", "GGGG"]
    assert set(airports["type"]) == {"medium_airport", "large_airport"}
    assert set(airports["iso_country"]) == {"NA", "FJ"}      # "NA" (Namibia) is not read as missing


def test_haversine_one_degree_on_the_equator():
    assert float(haversine_km(0.0, 0.0, 1.0, 0.0)) == pytest.approx(111.195, abs=0.01)
    assert float(haversine_km(0.0, 0.0, 0.0, 90.0)) == pytest.approx(10007.56, abs=0.1)
    assert float(haversine_km(5.0, 5.0, 5.0, 5.0)) == 0.0


def test_nearest_airport_skips_small_and_keeps_type(airports):
    """At lon 11.4 the small strip, helipad and closed field are nearer, but only medium/large count."""
    res = nearest_airport(11.4, 0.0, airports)
    assert res["airport_name"] == "Middle Airport"
    assert res["airport_type"] == "medium_airport"
    assert res["airport_ident"] == "BBBB"
    assert res["airport_km"] == pytest.approx(0.6 * 111.195, abs=0.01)
    res = nearest_airport(10.2, 0.0, airports)
    assert (res["airport_name"], res["airport_type"]) == ("Big Airport", "large_airport")


def test_nearest_airport_across_the_date_line(airports):
    res = nearest_airport(179.5, 0.0, airports)
    assert res["airport_name"] == "Date Line Airport"
    assert res["airport_km"] == pytest.approx(111.195, abs=0.01)


def test_nearest_airport_without_data(airports):
    assert nearest_airport(float("nan"), 0.0, airports)["airport_km"] is None
    assert nearest_airport(0.0, 0.0, airports.iloc[0:0])["airport_name"] is None
