from strava_exporter.filters import filter_by_sport

ACTIVITIES = [
    {"id": 1, "sport_type": "Run"},
    {"id": 2, "sport_type": "Ride"},
    {"id": 3, "sport_type": "Swim"},
]


def test_filter_single_sport():
    result = filter_by_sport(ACTIVITIES, ["Run"])
    assert [a["id"] for a in result] == [1]


def test_filter_multiple_sports():
    result = filter_by_sport(ACTIVITIES, ["Run", "Ride"])
    assert [a["id"] for a in result] == [1, 2]


def test_filter_none_returns_all():
    result = filter_by_sport(ACTIVITIES, None)
    assert result == ACTIVITIES


def test_filter_empty_list_returns_all():
    result = filter_by_sport(ACTIVITIES, [])
    assert result == ACTIVITIES


def test_filter_case_insensitive():
    result = filter_by_sport(ACTIVITIES, ["run", "RIDE"])
    assert [a["id"] for a in result] == [1, 2]


def test_filter_no_matches():
    result = filter_by_sport(ACTIVITIES, ["WeightTraining"])
    assert result == []
