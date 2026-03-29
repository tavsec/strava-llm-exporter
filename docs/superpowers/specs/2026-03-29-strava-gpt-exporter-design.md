# Strava GPT Exporter — Design Spec

**Date:** 2026-03-29

## Overview

A Python CLI tool that fetches Strava activities for a given date range and sport type filter, then exports them as Markdown or JSON optimized for pasting into an LLM (Claude, ChatGPT, etc.) for sports performance analysis.

---

## Project Structure

```
strava-gpt-exporter/
├── strava_exporter/
│   ├── __init__.py
│   ├── cli.py              # click CLI entry point
│   ├── auth.py             # token refresh via Strava OAuth
│   ├── client.py           # Strava API calls (list + detail fetch)
│   ├── filters.py          # date range + sport type filtering
│   ├── formatters/
│   │   ├── __init__.py
│   │   ├── json_fmt.py     # JSON output formatter
│   │   └── md_fmt.py       # Markdown output formatter
├── .env                    # CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN
├── pyproject.toml          # package definition + entry point: strava-export
└── README.md
```

---

## CLI Interface

```bash
strava-export \
  --from 2025-01-01 \
  --to   2025-03-01 \
  --sport Run,Ride \   # optional, defaults to all sports
  --format md \        # md or json, default: md
  --output report.md   # optional, defaults to stdout
```

### Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--from` | date (YYYY-MM-DD) | required | Start of date range (inclusive) |
| `--to` | date (YYYY-MM-DD) | required | End of date range (inclusive) |
| `--sport` | comma-separated string | all | One or more Strava sport types (e.g. `Run`, `Ride`, `Swim`) |
| `--format` | `md` or `json` | `md` | Output format |
| `--output` | file path | stdout | Write output to file instead of stdout |

### Credentials

Loaded from `.env` in the current directory, with `~/.strava-exporter/.env` as fallback. Required keys: `CLIENT_ID`, `CLIENT_SECRET`, `REFRESH_TOKEN`.

---

## Data Flow

1. **Auth** (`auth.py`): Exchange refresh token for access token via Strava OAuth endpoint.
2. **List** (`client.py`): Fetch paginated list of activities for the date range using `/athlete/activities?after=&before=`.
3. **Detail fetch** (`client.py`): For each activity in the list, fetch `GET /activities/{id}` to get the `DetailedActivity` object. Includes rate-limit handling (100 req/15 min, 1000/day).
4. **Filter** (`filters.py`): Apply sport type filter (if specified).
5. **Format** (`formatters/`): Render activities to Markdown or JSON.
6. **Output**: Print to stdout or write to file.

---

## Fields Exported

Sourced from the Strava `DetailedActivity` model:

| Category | Fields |
|----------|--------|
| Identity | `name`, `sport_type`, `start_date_local`, `id` |
| Volume | `distance`, `moving_time`, `elapsed_time`, `total_elevation_gain`, `elev_high`, `elev_low` |
| Intensity | `average_heartrate`, `max_heartrate`, `suffer_score`, `average_speed`, `max_speed` |
| Power | `average_watts`, `weighted_average_watts`, `max_watts`, `kilojoules` |
| Cadence | `average_cadence` |
| Context | `calories`, `average_temp`, `device_name`, `gear` (name only), `workout_type` |
| Splits | `splits_metric` — per-km: distance, elapsed time, pace, average HR |

Fields missing from an activity (e.g. no HR on a manual activity) are silently omitted from the output.

---

## Output Formats

### Markdown

One section per activity, ordered chronologically. Optimized for LLM readability.

```markdown
# Strava Export: 2025-01-01 to 2025-03-01 | Run, Ride

## 2025-01-15 — Morning Run (Run)
- **Distance:** 10.2 km | **Moving time:** 52:30 | **Elevation:** 120 m
- **Avg HR:** 148 bpm | **Max HR:** 172 bpm | **Suffer score:** 54
- **Avg pace:** 5:08/km | **Calories:** 620 kcal | **Cadence:** 178 spm
- **Gear:** Nike Vaporfly 3 | **Device:** Garmin Forerunner 955

### Splits
| km | Time  | Pace    | HR  |
|----|-------|---------|-----|
| 1  | 5:12  | 5:12/km | 142 |
| 2  | 5:05  | 5:05/km | 149 |
```

### JSON

Array of activity objects, each containing the same fields as above plus the raw `splits_metric` array. Suitable for programmatic use or structured LLM prompting.

---

## Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Rate limit (HTTP 429) | Exponential backoff, retry automatically, show progress to user |
| Missing optional field | Silently omit from output, do not fail |
| Invalid `--from`/`--to` date | Clear error message before any API calls |
| Invalid `--sport` value | Clear error message listing valid sport types |
| Missing `.env` / credentials | Clear error message with setup instructions |
| Network error | Fail with descriptive message |

---

## Dependencies

- `click` — CLI framework
- `requests` — HTTP client for Strava API
- `python-dotenv` — `.env` loading
- `tabulate` (optional) — Markdown table formatting

---

## Authentication Setup (for README)

Users must create a Strava API application and obtain:
- `CLIENT_ID`
- `CLIENT_SECRET`
- `REFRESH_TOKEN` (with `activity:read_all` scope)

The tool uses the refresh token grant to obtain a short-lived access token on each run. No OAuth browser flow required.
