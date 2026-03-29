# Strava GPT Exporter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool (`strava-export`) that fetches Strava activities for a date range and sport filter, then exports them as LLM-ready Markdown or JSON.

**Architecture:** A pip-installable package (`strava_exporter`) with separate modules for auth, API client, filtering, and formatting. The CLI entry point (`cli.py`) wires them together via `click`. Data flows: credentials → access token → raw DetailedActivity dicts → filtered list → formatted string → stdout or file.

**Tech Stack:** Python 3.10+, `click`, `requests`, `python-dotenv`, `pytest`, `pytest-mock`

---

## File Map

| File | Responsibility |
|------|---------------|
| `pyproject.toml` | Package metadata, dependencies, `strava-export` entry point |
| `strava_exporter/__init__.py` | Empty package marker |
| `strava_exporter/auth.py` | Exchange refresh token → access token via Strava OAuth |
| `strava_exporter/client.py` | Paginated activity list + detail fetch + 429 retry logic |
| `strava_exporter/filters.py` | Filter activity list by sport type |
| `strava_exporter/formatters/__init__.py` | `extract_fields()` shared by both formatters |
| `strava_exporter/formatters/json_fmt.py` | Render activity list to JSON string |
| `strava_exporter/formatters/md_fmt.py` | Render activity list to Markdown string |
| `strava_exporter/cli.py` | `click` CLI — credentials, orchestration, output |
| `tests/test_auth.py` | Unit tests for auth module |
| `tests/test_client.py` | Unit tests for client module |
| `tests/test_filters.py` | Unit tests for filters module |
| `tests/test_formatters.py` | Unit tests for extract_fields + both formatters |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `strava_exporter/__init__.py`
- Create: `strava_exporter/formatters/__init__.py` (temporary empty, replaced in Task 6)
- Create: `tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "strava-gpt-exporter"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "requests>=2.28",
    "python-dotenv>=1.0",
]

[project.scripts]
strava-export = "strava_exporter.cli:main"

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-mock>=3.0",
]
```

- [ ] **Step 2: Create package init files**

`strava_exporter/__init__.py` — empty file.

`strava_exporter/formatters/__init__.py` — empty file (will be replaced in Task 6).

`tests/__init__.py` — empty file.

- [ ] **Step 3: Install the package in editable mode**

```bash
cd /home/timotej/Documents/projects/strava-gpt-exporter
pip install -e ".[dev]"
```

Expected output: `Successfully installed strava-gpt-exporter-0.1.0`

- [ ] **Step 4: Verify entry point exists**

```bash
which strava-export
```

Expected: a path like `/home/timotej/.local/bin/strava-export` or similar (not "not found").

- [ ] **Step 5: Commit**

```bash
cd /home/timotej/Documents/projects/strava-gpt-exporter
git add pyproject.toml strava_exporter/__init__.py strava_exporter/formatters/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding and package setup"
```

---

## Task 2: auth.py

**Files:**
- Create: `strava_exporter/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_auth.py`:

```python
import pytest
from unittest.mock import patch, Mock
from strava_exporter.auth import get_access_token


def test_get_access_token_returns_token():
    mock_resp = Mock()
    mock_resp.json.return_value = {"access_token": "abc123"}
    mock_resp.raise_for_status = Mock()

    with patch("strava_exporter.auth.requests.post", return_value=mock_resp) as mock_post:
        token = get_access_token("123", "secret", "refresh")

    assert token == "abc123"
    mock_post.assert_called_once_with(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": "123",
            "client_secret": "secret",
            "refresh_token": "refresh",
            "grant_type": "refresh_token",
        },
    )


def test_get_access_token_raises_on_http_error():
    mock_resp = Mock()
    mock_resp.raise_for_status.side_effect = Exception("401 Unauthorized")

    with patch("strava_exporter.auth.requests.post", return_value=mock_resp):
        with pytest.raises(Exception, match="401"):
            get_access_token("bad", "creds", "token")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/timotej/Documents/projects/strava-gpt-exporter
pytest tests/test_auth.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'strava_exporter.auth'`

- [ ] **Step 3: Implement auth.py**

Create `strava_exporter/auth.py`:

```python
import requests

STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"


def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    response = requests.post(
        STRAVA_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add strava_exporter/auth.py tests/test_auth.py
git commit -m "feat: auth module — exchange refresh token for access token"
```

---

## Task 3: client.py

**Files:**
- Create: `strava_exporter/client.py`
- Create: `tests/test_client.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_client.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_client.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'strava_exporter.client'`

- [ ] **Step 3: Implement client.py**

Create `strava_exporter/client.py`:

```python
import time
import requests
from datetime import datetime

STRAVA_API_BASE = "https://www.strava.com/api/v3"


def _get(url: str, access_token: str, params: dict | None = None) -> dict | list:
    headers = {"Authorization": f"Bearer {access_token}"}
    for attempt in range(5):
        resp = requests.get(url, headers=headers, params=params or {})
        if resp.status_code == 429:
            wait = 2 ** attempt * 15
            print(f"Rate limited. Waiting {wait}s...", flush=True)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError("Rate limit exceeded after 5 retries")


def list_activity_ids(access_token: str, after_ts: int, before_ts: int) -> list[int]:
    ids: list[int] = []
    page = 1
    while True:
        activities = _get(
            f"{STRAVA_API_BASE}/athlete/activities",
            access_token,
            {"after": after_ts, "before": before_ts, "per_page": 200, "page": page},
        )
        if not activities:
            break
        ids.extend(a["id"] for a in activities)
        page += 1
    return ids


def fetch_detail(access_token: str, activity_id: int) -> dict:
    return _get(f"{STRAVA_API_BASE}/activities/{activity_id}", access_token)


def fetch_activities(
    access_token: str, after: datetime, before: datetime
) -> list[dict]:
    after_ts = int(after.timestamp())
    before_ts = int(before.timestamp())
    ids = list_activity_ids(access_token, after_ts, before_ts)
    activities = []
    for i, aid in enumerate(ids, 1):
        print(f"Fetching activity {i}/{len(ids)}...", end="\r", flush=True)
        activities.append(fetch_detail(access_token, aid))
    if ids:
        print()
    return activities
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_client.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add strava_exporter/client.py tests/test_client.py
git commit -m "feat: client module — paginated list + detail fetch with 429 retry"
```

---

## Task 4: filters.py

**Files:**
- Create: `strava_exporter/filters.py`
- Create: `tests/test_filters.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_filters.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_filters.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'strava_exporter.filters'`

- [ ] **Step 3: Implement filters.py**

Create `strava_exporter/filters.py`:

```python
def filter_by_sport(
    activities: list[dict], sports: list[str] | None
) -> list[dict]:
    if not sports:
        return activities
    sports_lower = {s.lower() for s in sports}
    return [
        a for a in activities
        if a.get("sport_type", "").lower() in sports_lower
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_filters.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add strava_exporter/filters.py tests/test_filters.py
git commit -m "feat: filters module — sport type filtering, case-insensitive"
```

---

## Task 5: formatters/__init__.py — extract_fields

**Files:**
- Modify: `strava_exporter/formatters/__init__.py`
- Create: `tests/test_formatters.py` (partial — only extract_fields tests for now)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_formatters.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_formatters.py -v
```

Expected: FAIL — `ImportError: cannot import name 'extract_fields'`

- [ ] **Step 3: Implement formatters/__init__.py**

Replace `strava_exporter/formatters/__init__.py` with:

```python
OPTIONAL_FIELDS = [
    "elev_high",
    "elev_low",
    "average_heartrate",
    "max_heartrate",
    "suffer_score",
    "average_speed",
    "max_speed",
    "average_watts",
    "weighted_average_watts",
    "max_watts",
    "kilojoules",
    "average_cadence",
    "calories",
    "average_temp",
    "device_name",
    "workout_type",
]


def extract_fields(activity: dict) -> dict:
    result = {
        "id": activity.get("id"),
        "name": activity.get("name"),
        "sport_type": activity.get("sport_type"),
        "start_date_local": activity.get("start_date_local"),
        "distance_m": activity.get("distance"),
        "moving_time_s": activity.get("moving_time"),
        "elapsed_time_s": activity.get("elapsed_time"),
        "total_elevation_gain_m": activity.get("total_elevation_gain"),
    }

    for field in OPTIONAL_FIELDS:
        val = activity.get(field)
        if val is not None:
            result[field] = val

    gear = activity.get("gear")
    if gear:
        result["gear_name"] = gear.get("name")

    splits = activity.get("splits_metric")
    if splits:
        result["splits"] = [
            {
                "km": i + 1,
                "elapsed_time_s": s.get("elapsed_time"),
                "distance_m": s.get("distance"),
                "average_heartrate": s.get("average_heartrate"),
                "average_speed_ms": s.get("average_speed"),
            }
            for i, s in enumerate(splits)
        ]

    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_formatters.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add strava_exporter/formatters/__init__.py tests/test_formatters.py
git commit -m "feat: extract_fields — shared field extraction for formatters"
```

---

## Task 6: formatters/json_fmt.py

**Files:**
- Create: `strava_exporter/formatters/json_fmt.py`
- Modify: `tests/test_formatters.py` (append JSON formatter tests)

- [ ] **Step 1: Append failing tests to tests/test_formatters.py**

Add the following to the end of `tests/test_formatters.py`:

```python
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
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_formatters.py::test_format_json_valid tests/test_formatters.py::test_format_json_empty tests/test_formatters.py::test_format_json_omits_missing_fields -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'strava_exporter.formatters.json_fmt'`

- [ ] **Step 3: Implement json_fmt.py**

Create `strava_exporter/formatters/json_fmt.py`:

```python
import json
from strava_exporter.formatters import extract_fields


def format_json(activities: list[dict]) -> str:
    return json.dumps([extract_fields(a) for a in activities], indent=2)
```

- [ ] **Step 4: Run all formatter tests to verify they pass**

```bash
pytest tests/test_formatters.py -v
```

Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add strava_exporter/formatters/json_fmt.py tests/test_formatters.py
git commit -m "feat: JSON formatter"
```

---

## Task 7: formatters/md_fmt.py

**Files:**
- Create: `strava_exporter/formatters/md_fmt.py`
- Modify: `tests/test_formatters.py` (append Markdown formatter tests)

- [ ] **Step 1: Append failing tests to tests/test_formatters.py**

Add the following to the end of `tests/test_formatters.py`:

```python
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
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
pytest tests/test_formatters.py -k "md or fmt_time or fmt_pace or fmt_distance or format_markdown" -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'strava_exporter.formatters.md_fmt'`

- [ ] **Step 3: Implement md_fmt.py**

Create `strava_exporter/formatters/md_fmt.py`:

```python
from strava_exporter.formatters import extract_fields


def _fmt_time(seconds: int | None) -> str:
    if seconds is None:
        return "N/A"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _fmt_pace(speed_ms: float | None) -> str:
    if not speed_ms:
        return "N/A"
    secs_per_km = 1000 / speed_ms
    m, s = divmod(int(secs_per_km), 60)
    return f"{m}:{s:02d}/km"


def _fmt_distance(meters: float | None) -> str:
    if meters is None:
        return "N/A"
    return f"{meters / 1000:.2f} km"


def _activity_section(activity: dict) -> str:
    f = extract_fields(activity)
    date = (f.get("start_date_local") or "")[:10]
    name = f.get("name", "Untitled")
    sport = f.get("sport_type", "")

    lines = [f"## {date} — {name} ({sport})"]

    volume_parts = [
        f"**Distance:** {_fmt_distance(f.get('distance_m'))}",
        f"**Moving time:** {_fmt_time(f.get('moving_time_s'))}",
        f"**Elevation gain:** {f.get('total_elevation_gain_m', 'N/A')} m",
    ]
    if "elev_high" in f and "elev_low" in f:
        volume_parts.append(f"**Elev range:** {f['elev_low']}–{f['elev_high']} m")
    lines.append("- " + " | ".join(volume_parts))

    intensity_parts = []
    if "average_heartrate" in f:
        intensity_parts.append(f"**Avg HR:** {f['average_heartrate']:.0f} bpm")
    if "max_heartrate" in f:
        intensity_parts.append(f"**Max HR:** {f['max_heartrate']:.0f} bpm")
    if "suffer_score" in f:
        intensity_parts.append(f"**Suffer score:** {f['suffer_score']}")
    if "average_speed" in f:
        intensity_parts.append(f"**Avg pace:** {_fmt_pace(f['average_speed'])}")
    if "calories" in f:
        intensity_parts.append(f"**Calories:** {f['calories']} kcal")
    if "average_cadence" in f:
        intensity_parts.append(f"**Cadence:** {f['average_cadence']:.0f} spm")
    if intensity_parts:
        lines.append("- " + " | ".join(intensity_parts))

    power_parts = []
    if "average_watts" in f:
        power_parts.append(f"**Avg power:** {f['average_watts']:.0f} W")
    if "weighted_average_watts" in f:
        power_parts.append(f"**NP:** {f['weighted_average_watts']:.0f} W")
    if "max_watts" in f:
        power_parts.append(f"**Max power:** {f['max_watts']:.0f} W")
    if "kilojoules" in f:
        power_parts.append(f"**Work:** {f['kilojoules']:.0f} kJ")
    if power_parts:
        lines.append("- " + " | ".join(power_parts))

    context_parts = []
    if "gear_name" in f:
        context_parts.append(f"**Gear:** {f['gear_name']}")
    if "device_name" in f:
        context_parts.append(f"**Device:** {f['device_name']}")
    if "average_temp" in f:
        context_parts.append(f"**Temp:** {f['average_temp']}°C")
    if context_parts:
        lines.append("- " + " | ".join(context_parts))

    splits = f.get("splits")
    if splits:
        lines.append("\n### Splits")
        lines.append("| km | Time | Pace | HR |")
        lines.append("|----|------|------|----|")
        for s in splits:
            hr = f"{s['average_heartrate']:.0f}" if s.get("average_heartrate") else "—"
            lines.append(
                f"| {s['km']} "
                f"| {_fmt_time(s['elapsed_time_s'])} "
                f"| {_fmt_pace(s['average_speed_ms'])} "
                f"| {hr} |"
            )

    return "\n".join(lines)


def format_markdown(
    activities: list[dict],
    from_date: str,
    to_date: str,
    sports: list[str] | None,
) -> str:
    sport_label = ", ".join(sports) if sports else "All sports"
    header = f"# Strava Export: {from_date} to {to_date} | {sport_label}\n"
    sections = [_activity_section(a) for a in activities]
    return header + "\n\n".join(sections)
```

- [ ] **Step 4: Run all formatter tests to verify they pass**

```bash
pytest tests/test_formatters.py -v
```

Expected: 23 passed

- [ ] **Step 5: Commit**

```bash
git add strava_exporter/formatters/md_fmt.py tests/test_formatters.py
git commit -m "feat: Markdown formatter with splits table and LLM-friendly layout"
```

---

## Task 8: cli.py

**Files:**
- Create: `strava_exporter/cli.py`

No unit tests for the CLI — it's a thin orchestration layer over already-tested modules. Verify manually.

- [ ] **Step 1: Implement cli.py**

Create `strava_exporter/cli.py`:

```python
import os
import sys
from datetime import datetime, time as dt_time
from pathlib import Path

import click
from dotenv import load_dotenv

from strava_exporter.auth import get_access_token
from strava_exporter.client import fetch_activities
from strava_exporter.filters import filter_by_sport
from strava_exporter.formatters.json_fmt import format_json
from strava_exporter.formatters.md_fmt import format_markdown


def _load_credentials() -> tuple[str, str, str]:
    for env_path in [Path(".env"), Path.home() / ".strava-exporter" / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        raise click.ClickException(
            "Missing credentials. Create a .env file with:\n"
            "  CLIENT_ID=<your_client_id>\n"
            "  CLIENT_SECRET=<your_client_secret>\n"
            "  REFRESH_TOKEN=<your_refresh_token>\n"
            "See README.md for setup instructions."
        )
    return client_id, client_secret, refresh_token


@click.command()
@click.option(
    "--from", "from_date",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date inclusive (YYYY-MM-DD)",
)
@click.option(
    "--to", "to_date",
    required=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date inclusive (YYYY-MM-DD)",
)
@click.option(
    "--sport",
    default=None,
    help="Comma-separated sport types, e.g. Run,Ride. Defaults to all.",
)
@click.option(
    "--format", "fmt",
    default="md",
    type=click.Choice(["md", "json"], case_sensitive=False),
    help="Output format: md or json (default: md)",
)
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Write output to file instead of stdout",
)
def main(from_date: datetime, to_date: datetime, sport: str | None, fmt: str, output: str | None) -> None:
    sports = [s.strip() for s in sport.split(",")] if sport else None

    from_dt = datetime.combine(from_date.date(), dt_time(0, 0, 0))
    to_dt = datetime.combine(to_date.date(), dt_time(23, 59, 59))

    if from_dt > to_dt:
        raise click.ClickException("--from date must be before --to date")

    client_id, client_secret, refresh_token = _load_credentials()

    try:
        access_token = get_access_token(client_id, client_secret, refresh_token)
    except Exception as e:
        raise click.ClickException(f"Authentication failed: {e}")

    try:
        activities = fetch_activities(access_token, from_dt, to_dt)
    except Exception as e:
        raise click.ClickException(f"Failed to fetch activities: {e}")

    activities = filter_by_sport(activities, sports)

    from_str = from_date.strftime("%Y-%m-%d")
    to_str = to_date.strftime("%Y-%m-%d")

    if fmt == "json":
        result = format_json(activities)
    else:
        result = format_markdown(activities, from_str, to_str, sports)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        click.echo(f"Written {len(activities)} activities to {output}", err=True)
    else:
        click.echo(result)
```

- [ ] **Step 2: Run all tests to verify nothing is broken**

```bash
pytest -v
```

Expected: all previous tests pass (23+)

- [ ] **Step 3: Smoke-test the CLI help**

```bash
strava-export --help
```

Expected output:
```
Usage: strava-export [OPTIONS]

Options:
  --from TEXT    Start date inclusive (YYYY-MM-DD)  [required]
  --to TEXT      End date inclusive (YYYY-MM-DD)  [required]
  --sport TEXT   Comma-separated sport types, e.g. Run,Ride. Defaults to all.
  --format TEXT  Output format: md or json (default: md)
  --output TEXT  Write output to file instead of stdout
  --help         Show this message and exit.
```

- [ ] **Step 4: Commit**

```bash
git add strava_exporter/cli.py
git commit -m "feat: CLI entry point — strava-export command with all flags"
```

---

## Task 9: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

Create `README.md`:

```markdown
# strava-gpt-exporter

Export Strava activities to Markdown or JSON, optimized for pasting into an LLM (Claude, ChatGPT, etc.) for sports performance analysis.

## Installation

```bash
git clone <repo>
cd strava-gpt-exporter
pip install -e .
```

## Setup

### 1. Create a Strava API Application

Go to https://www.strava.com/settings/api and create an application.
Note your **Client ID** and **Client Secret**.

### 2. Get a Refresh Token with `activity:read_all` scope

Follow the [Strava OAuth guide](https://developers.strava.com/docs/getting-started/) to obtain a refresh token.
The token must have `activity:read_all` scope (not just the default read scope).

A quick way: use the [Strava OAuth Playground](https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all) — replace `YOUR_CLIENT_ID`, authorize, copy the `code` from the redirect URL, then exchange it:

```bash
curl -X POST https://www.strava.com/oauth/token \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d code=YOUR_CODE \
  -d grant_type=authorization_code
```

The response contains your `refresh_token`.

### 3. Create a .env file

In the directory where you run `strava-export`, create a `.env` file:

```
CLIENT_ID=123456
CLIENT_SECRET=your_client_secret_here
REFRESH_TOKEN=your_refresh_token_here
```

Alternatively, place the `.env` file at `~/.strava-exporter/.env` for global use.

## Usage

```bash
# Export last month's runs as Markdown (stdout)
strava-export --from 2025-02-01 --to 2025-02-28 --sport Run

# Export runs and rides as JSON to a file
strava-export --from 2025-01-01 --to 2025-03-01 --sport Run,Ride --format json --output activities.json

# Export all sports as Markdown to a file
strava-export --from 2025-01-01 --to 2025-01-31 --output january.md
```

## Pasting into an LLM

Copy the output and start your prompt with something like:

> "Here are my Strava activities for January 2025. Analyse my training load, identify patterns, and suggest improvements."

## Rate Limits

Strava allows 100 requests per 15 minutes and 1000 per day. The tool fetches one extra API call per activity (for detailed data). For exports of ~50 activities this is well within limits. If you hit the limit, the tool will automatically wait and retry.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with setup and usage instructions"
```

---

## Final Check

- [ ] **Run full test suite**

```bash
pytest -v
```

Expected: all tests pass, 0 failures.

- [ ] **Verify CLI is installed and working**

```bash
strava-export --help
strava-export --from 2025-01-01 --to 2025-01-01  # should fail with credentials error, not a crash
```

Expected for second command: `Error: Missing credentials. Create a .env file with: ...`
