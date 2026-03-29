from strava_exporter.formatters import extract_fields

SAMPLE_ACTIVITY = {
    "id": 1,
    "name": "Morning Run",
    "sport_type": "Run",
    "start_date_local": "2025-01-15T07:30:00Z",
    "distance": 10200.0,
    "moving_time": 3150,
    "elapsed_time": 3200,
    "total_elevation_gain": 120.0,
    "elev_high": 250.0,
    "elev_low": 130.0,
    "average_heartrate": 148.0,
    "max_heartrate": 172.0,
    "suffer_score": 54,
    "average_speed": 3.238,
    "max_speed": 4.5,
    "average_cadence": 178.0,
    "calories": 620,
    "average_temp": 8,
    "device_name": "Garmin Forerunner 955",
    "gear": {"name": "Nike Vaporfly 3"},
    "splits_metric": [
        {
            "elapsed_time": 312,
            "distance": 1000.0,
            "average_heartrate": 142.0,
            "average_speed": 3.205,
        },
        {
            "elapsed_time": 305,
            "distance": 1000.0,
            "average_heartrate": 149.0,
            "average_speed": 3.279,
        },
    ],
}


def test_extract_fields_required():
    f = extract_fields(SAMPLE_ACTIVITY)
    assert f["id"] == 1
    assert f["name"] == "Morning Run"
    assert f["sport_type"] == "Run"
    assert f["distance_m"] == 10200.0
    assert f["moving_time_s"] == 3150
    assert f["elapsed_time_s"] == 3200
    assert f["total_elevation_gain_m"] == 120.0


def test_extract_fields_optional_present():
    f = extract_fields(SAMPLE_ACTIVITY)
    assert f["average_heartrate"] == 148.0
    assert f["calories"] == 620
    assert f["gear_name"] == "Nike Vaporfly 3"
    assert f["elev_high"] == 250.0
    assert f["device_name"] == "Garmin Forerunner 955"


def test_extract_fields_omits_missing_optional():
    activity = {k: v for k, v in SAMPLE_ACTIVITY.items() if k != "average_heartrate"}
    f = extract_fields(activity)
    assert "average_heartrate" not in f


def test_extract_fields_splits_shape():
    f = extract_fields(SAMPLE_ACTIVITY)
    assert len(f["splits"]) == 2
    assert f["splits"][0] == {
        "km": 1,
        "elapsed_time_s": 312,
        "distance_m": 1000.0,
        "average_heartrate": 142.0,
        "average_speed_ms": 3.205,
    }
    assert f["splits"][1]["km"] == 2


def test_extract_fields_no_gear():
    activity = {**SAMPLE_ACTIVITY, "gear": None}
    f = extract_fields(activity)
    assert "gear_name" not in f


def test_extract_fields_no_splits():
    activity = {k: v for k, v in SAMPLE_ACTIVITY.items() if k != "splits_metric"}
    f = extract_fields(activity)
    assert "splits" not in f


import json
from strava_exporter.formatters.json_fmt import format_json


def test_format_json_valid():
    result = format_json([SAMPLE_ACTIVITY])
    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "Morning Run"
    assert parsed[0]["distance_m"] == 10200.0


def test_format_json_empty():
    result = format_json([])
    assert json.loads(result) == []


def test_format_json_omits_missing_fields():
    activity = {k: v for k, v in SAMPLE_ACTIVITY.items() if k != "average_heartrate"}
    result = format_json([activity])
    parsed = json.loads(result)
    assert "average_heartrate" not in parsed[0]


from strava_exporter.formatters.md_fmt import (
    format_markdown,
    _fmt_time,
    _fmt_pace,
    _fmt_distance,
)


def test_fmt_time_under_hour():
    assert _fmt_time(312) == "5:12"


def test_fmt_time_over_hour():
    assert _fmt_time(3661) == "1:01:01"


def test_fmt_time_none():
    assert _fmt_time(None) == "N/A"


def test_fmt_pace():
    # 3.238 m/s → 1000/3.238 = 308.8s/km → 5m 8s
    assert _fmt_pace(3.238) == "5:08/km"


def test_fmt_pace_none():
    assert _fmt_pace(None) == "N/A"


def test_fmt_distance():
    assert _fmt_distance(10200.0) == "10.20 km"


def test_fmt_distance_none():
    assert _fmt_distance(None) == "N/A"


def test_format_markdown_header_with_sports():
    result = format_markdown([SAMPLE_ACTIVITY], "2025-01-01", "2025-01-31", ["Run"])
    assert "# Strava Export: 2025-01-01 to 2025-01-31 | Run" in result


def test_format_markdown_header_all_sports():
    result = format_markdown([SAMPLE_ACTIVITY], "2025-01-01", "2025-01-31", None)
    assert "All sports" in result


def test_format_markdown_activity_heading():
    result = format_markdown([SAMPLE_ACTIVITY], "2025-01-01", "2025-01-31", None)
    assert "## 2025-01-15 — Morning Run (Run)" in result


def test_format_markdown_includes_distance_and_hr():
    result = format_markdown([SAMPLE_ACTIVITY], "2025-01-01", "2025-01-31", None)
    assert "10.20 km" in result
    assert "148" in result  # avg HR


def test_format_markdown_includes_splits_table():
    result = format_markdown([SAMPLE_ACTIVITY], "2025-01-01", "2025-01-31", None)
    assert "### Splits" in result
    assert "| km |" in result


def test_format_markdown_empty_activities():
    result = format_markdown([], "2025-01-01", "2025-01-31", None)
    assert "# Strava Export" in result


def test_format_markdown_multiple_sports_header():
    result = format_markdown([SAMPLE_ACTIVITY], "2025-01-01", "2025-01-31", ["Run", "Ride"])
    assert "Run, Ride" in result
