from unittest.mock import patch, Mock
from datetime import datetime
from strava_exporter.client import list_activity_ids, fetch_detail, fetch_activities


def _resp(json_data, status_code=200):
    resp = Mock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status = Mock()
    return resp


def test_list_activity_ids_single_page():
    with patch("strava_exporter.client.requests.get", side_effect=[
        _resp([{"id": 1}, {"id": 2}]),
        _resp([]),
    ]):
        result = list_activity_ids("token", 1000, 2000)
    assert result == [1, 2]


def test_list_activity_ids_empty():
    with patch("strava_exporter.client.requests.get", return_value=_resp([])):
        result = list_activity_ids("token", 1000, 2000)
    assert result == []


def test_list_activity_ids_multiple_pages():
    with patch("strava_exporter.client.requests.get", side_effect=[
        _resp([{"id": i} for i in range(1, 201)]),   # 200 results → another page
        _resp([{"id": 201}]),
        _resp([]),
    ]):
        result = list_activity_ids("token", 1000, 2000)
    assert len(result) == 201
    assert result[-1] == 201


def test_fetch_detail_returns_dict():
    detail = {"id": 42, "name": "Morning Run", "sport_type": "Run"}
    with patch("strava_exporter.client.requests.get", return_value=_resp(detail)):
        result = fetch_detail("token", 42)
    assert result == detail


def test_fetch_detail_retries_on_429():
    rate_limited = _resp({}, status_code=429)
    success = _resp({"id": 1, "name": "Run"})

    with patch("strava_exporter.client.requests.get", side_effect=[rate_limited, success]):
        with patch("strava_exporter.client.time.sleep") as mock_sleep:
            result = fetch_detail("token", 1)

    mock_sleep.assert_called_once()
    assert result == {"id": 1, "name": "Run"}


def test_fetch_activities_combines_list_and_detail():
    with patch("strava_exporter.client.requests.get", side_effect=[
        _resp([{"id": 10}, {"id": 20}]),
        _resp([]),
        _resp({"id": 10, "name": "Run A", "sport_type": "Run"}),
        _resp({"id": 20, "name": "Ride B", "sport_type": "Ride"}),
    ]):
        result = fetch_activities("token", datetime(2025, 1, 1), datetime(2025, 1, 31))

    assert len(result) == 2
    assert result[0]["id"] == 10
    assert result[1]["id"] == 20
