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
