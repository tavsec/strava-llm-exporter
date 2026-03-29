# OAuth Flow — Design Spec

**Date:** 2026-03-29

## Overview

Add a `strava-export auth` command that guides the user through Strava's OAuth flow programmatically. It opens a browser, spins up a temporary local HTTP server to capture the callback, exchanges the code for a refresh token, and writes it to `.env` — so the user never has to manually generate a refresh token.

---

## CLI Changes

The CLI becomes a command group. The existing `main` command is renamed `export`:

```bash
# One-time setup
strava-export auth

# Export (all flags unchanged)
strava-export export --from 2025-01-01 --to 2025-03-01 --sport Run --format md
```

---

## New File: strava_exporter/oauth.py

Contains three functions:

### `run_oauth_flow(client_id: str, client_secret: str, env_path: Path) -> None`

Orchestrates the full flow:
1. Builds the Strava authorization URL with `scope=activity:read_all`, `redirect_uri=http://localhost:8080/callback`, `response_type=code`, `approval_prompt=force`
2. Attempts to open the URL in the default browser via `webbrowser.open()`; if it fails, prints the URL and asks the user to open it manually
3. Starts a temporary `http.server.HTTPServer` on `localhost:8080`
4. Waits for one request to `/callback?code=...`; extracts `code` (or raises if `error` param is present)
5. Shuts down the HTTP server
6. Calls `_exchange_code()` to get the refresh token
7. Calls `_save_refresh_token()` to write it to `.env`
8. Prints: `"Authorization complete. REFRESH_TOKEN saved to {env_path}"`

### `_exchange_code(client_id: str, client_secret: str, code: str) -> str`

POSTs to `https://www.strava.com/oauth/token` with:
```
client_id, client_secret, code, grant_type=authorization_code
```
Calls `raise_for_status()`, returns `response.json()["refresh_token"]`.

### `_save_refresh_token(refresh_token: str, env_path: Path) -> None`

- If `.env` exists: reads it, replaces existing `REFRESH_TOKEN=...` line or appends if not present
- If `.env` doesn't exist: creates it with `REFRESH_TOKEN=...`

---

## Changes to strava_exporter/cli.py

### Convert to command group

```python
@click.group()
def cli(): pass

cli.add_command(auth)
cli.add_command(export)
```

Entry point in `pyproject.toml` changes from `strava_exporter.cli:main` to `strava_exporter.cli:cli`.

### New `auth` command

```python
@click.command()
def auth():
    """Run Strava OAuth flow and save REFRESH_TOKEN to .env."""
```

Loads CLIENT_ID + CLIENT_SECRET from `.env` (only these two required — error if missing). The `env_path` used is whichever file CLIENT_ID was found in (`./.env` first, then `~/.strava-exporter/.env`). REFRESH_TOKEN is written back to that same file. Calls `run_oauth_flow(client_id, client_secret, env_path)`.

### Updated `_load_credentials()`

When REFRESH_TOKEN is missing, error message changes to:
```
"REFRESH_TOKEN not found. Run 'strava-export auth' to authorize."
```
(CLIENT_ID and CLIENT_SECRET still required with the original error message.)

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| CLIENT_ID or CLIENT_SECRET missing from `.env` | `ClickException`: "Set CLIENT_ID and CLIENT_SECRET in .env first" |
| Port 8080 already in use | `ClickException`: "Port 8080 is in use. Free it and try again." |
| Browser fails to open | Print URL, instruct user to open manually; continue waiting |
| Strava returns `error` param | `ClickException`: "Authorization denied: {error}" |
| Token exchange HTTP error | `ClickException`: "Token exchange failed: {status}" |
| `.env` doesn't exist | Create it with just the REFRESH_TOKEN line |

---

## OAuth Parameters

| Parameter | Value |
|---|---|
| Authorization URL | `https://www.strava.com/oauth/authorize` |
| Token URL | `https://www.strava.com/oauth/token` |
| Redirect URI | `http://localhost:8080/callback` |
| Scope | `activity:read_all` |
| Response type | `code` |
| Approval prompt | `force` (always show consent screen) |
| Grant type (exchange) | `authorization_code` |

---

## File Map

| File | Change |
|---|---|
| `strava_exporter/oauth.py` | New — `run_oauth_flow`, `_exchange_code`, `_save_refresh_token` |
| `strava_exporter/cli.py` | Convert to group, add `auth` command, update `_load_credentials` error msg, rename `main` → `export` |
| `pyproject.toml` | Update entry point: `strava_exporter.cli:cli` |
| `tests/test_oauth.py` | New — unit tests for all three oauth functions |
| `tests/test_cli_auth.py` | New — integration tests for `auth` command and updated `_load_credentials` |
