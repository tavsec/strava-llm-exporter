# strava-llm-exporter

Export your Strava activities to clean Markdown or JSON, ready to paste into an LLM (Claude, ChatGPT, Gemini, ...) for training analysis, pattern recognition, and performance insights.

> **Vibe coded.** This project was built entirely through conversational AI-assisted development — no traditional planning, no upfront architecture docs. Just prompts, iteration, and vibes. It works, it's tested, and the code is clean. Make of that what you will.

---

## What it does

`strava-llm-exporter` fetches your Strava activities for a given date range via the Strava API, filters by sport type if needed, and formats everything into a compact, token-efficient representation that LLMs parse well.

### How it works

1. You create a Strava API app and get your credentials
2. Run `strava-export auth` to do the OAuth dance — a local HTTP server catches the callback, exchanges the code, and saves your refresh token to `.env`
3. Run `strava-export export --from ... --to ...` to pull activities
4. Each activity fetches full detail (splits, power, HR, gear) from the Strava API
5. Activities are formatted and written to stdout or a file

```
Strava API ──► list activity IDs ──► fetch detail per activity
                                              │
                                              ▼
                                    filter by sport type
                                              │
                                    ┌─────────┴─────────┐
                                    ▼                   ▼
                              Markdown (.md)       JSON (.json)
                                    │
                                    ▼
                            paste into LLM
```

### Output it produces

**Markdown** (default, `--format md`) — structured, human-readable, optimised for LLM context windows:

```markdown
# Strava Export: 2025-03-01 to 2025-03-31 | Run

## 2025-03-28 — Morning Run (Run)
- **Distance:** 10.50 km | **Moving time:** 52:30 | **Elevation gain:** 120.0 m
- **Avg HR:** 158 bpm | **Max HR:** 175 bpm | **Avg pace:** 5:00/km | **Calories:** 650 kcal

### Splits
| km | Time | Pace | HR |
|----|------|------|----|
| 1  | 5:12 | 5:12/km | 145 |
| 2  | 5:05 | 5:04/km | 155 |
...
```

Fields included (when available from Strava):
- Distance, moving time, elapsed time, elevation gain/range
- Heart rate (avg + max), suffer score
- Pace, cadence, calories
- Power (avg, normalised, max, kilojoules) — for cycling or running power meters
- Gear name, device name, temperature
- Per-kilometre splits (time, pace, HR)

**JSON** (`--format json`) — structured data, useful for programmatic processing or when you want to feed activities to an LLM API directly.

---

## Installation

Requires Python 3.10+.

```bash
git clone https://github.com/tavsec/strava-llm-exporter
cd strava-llm-exporter
pip install -e .
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv pip install -e .
```

---

## Setup

### 1. Create a Strava API application

Go to [strava.com/settings/api](https://www.strava.com/settings/api) and create an app. Set the **Authorization Callback Domain** to `localhost`.

Note your **Client ID** and **Client Secret**.

### 2. Create a `.env` file

```
CLIENT_ID=123456
CLIENT_SECRET=your_client_secret_here
```

Place it in the directory where you'll run `strava-export`, or globally at `~/.strava-exporter/.env`.

### 3. Authorize

```bash
strava-export auth
```

This opens your browser to Strava's authorization page. After you approve, the local callback server catches the redirect, exchanges the code for tokens, and saves `REFRESH_TOKEN` to your `.env`.

---

## Usage

```bash
# Export March 2025 runs as Markdown (stdout)
strava-export export --from 2025-03-01 --to 2025-03-31 --sport Run

# Export runs and rides to a file
strava-export export --from 2025-01-01 --to 2025-03-31 --sport Run,Ride --output q1.md

# Export all sports as JSON
strava-export export --from 2025-01-01 --to 2025-01-31 --format json --output january.json

# All options
strava-export export --help
```

### Options

| Flag | Description |
|------|-------------|
| `--from` | Start date inclusive, `YYYY-MM-DD` |
| `--to` | End date inclusive, `YYYY-MM-DD` |
| `--sport` | Comma-separated sport types (e.g. `Run`, `Ride`, `TrailRun`). Defaults to all. |
| `--format` | `md` (default) or `json` |
| `--output` | Write to file instead of stdout |

### Paste into an LLM

Copy the output and start a prompt like:

> "Here are my Strava activities for Q1 2025. Analyse my training load, identify patterns, and suggest what I should focus on next month."

or

> "I'm training for a marathon in June. Based on these activities, am I building enough base mileage? Where are the gaps?"

---

## Rate limits

Strava allows 100 requests per 15 minutes and 1000 per day. The tool fetches one extra API request per activity for full detail (splits, power, gear). For typical exports (< 50 activities) you'll be well within limits. If you hit the rate limit, the tool backs off automatically and retries.

---

## Contributing

This was vibe coded, so the bar for contributions is: **does it work, is it simple, does it stay focused?**

- Bug fixes and edge case handling are welcome
- New output formats (CSV? YAML?) — open an issue first, discuss the use case
- Support for additional Strava fields — PRs welcome, keep the field extraction in `strava_exporter/formatters/__init__.py`
- Anything that adds significant complexity or dependencies — let's talk first

To get started:

```bash
git clone https://github.com/tavsec/strava-llm-exporter
cd strava-llm-exporter
pip install -e ".[dev]"
pytest
```

Tests live in `tests/`. The project uses no external test mocking beyond `pytest-mock`.

---

## Project structure

```
strava_exporter/
├── cli.py              # Click CLI — auth + export commands
├── auth.py             # Refresh token → access token exchange
├── oauth.py            # OAuth flow — local HTTP server callback
├── client.py           # Strava API client — paginated fetch + rate limit retry
├── filters.py          # Sport type filtering
└── formatters/
    ├── __init__.py     # Shared field extraction from raw Strava activity
    ├── md_fmt.py       # Markdown formatter
    └── json_fmt.py     # JSON formatter
```

---

## License

MIT
