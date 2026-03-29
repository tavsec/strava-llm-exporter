import json
from strava_exporter.formatters import extract_fields


def format_json(activities: list[dict]) -> str:
    return json.dumps([extract_fields(a) for a in activities], indent=2)
