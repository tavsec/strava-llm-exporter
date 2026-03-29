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

A quick way: use the Strava OAuth authorize URL below — replace `YOUR_CLIENT_ID`, authorize, copy the `code` from the redirect URL, then exchange it:

```
https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all
```

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
