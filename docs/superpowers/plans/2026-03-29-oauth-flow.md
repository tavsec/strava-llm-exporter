# OAuth Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `strava-export auth` command that opens a browser, spins up a local HTTP server to capture the Strava OAuth callback, exchanges the code for a refresh token, and writes it to `.env`.

**Architecture:** New `strava_exporter/oauth.py` contains pure OAuth logic (`_build_auth_url`, `_exchange_code`, `_save_refresh_token`, `run_oauth_flow`). `cli.py` is refactored into a `click.group` with `auth` and `export` subcommands; a new `_find_env_path()` helper is extracted for shared use. `pyproject.toml` entry point updated to point at the group.

**Tech Stack:** Python stdlib `http.server`, `webbrowser`, `urllib.parse`; `requests`; `click`; `pytest` + `unittest.mock`

---

## File Map

| File | Change |
|------|--------|
| `strava_exporter/oauth.py` | New — `_build_auth_url`, `_exchange_code`, `_save_refresh_token`, `_CallbackHandler`, `run_oauth_flow` |
| `strava_exporter/cli.py` | Refactor — extract `_find_env_path`, add `auth` command, convert `main` → `export` in a `cli` group, update `_load_credentials` error message |
| `pyproject.toml` | Change entry point from `strava_exporter.cli:main` to `strava_exporter.cli:cli` |
| `tests/test_oauth.py` | New — unit tests for all oauth helpers + `run_oauth_flow` |
| `tests/test_cli_auth.py` | New — tests for `auth` command and updated `_load_credentials` via `CliRunner` |

---

## Task 1: oauth.py — helper functions

**Files:**
- Create: `strava_exporter/oauth.py`
- Create: `tests/test_oauth.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_oauth.py`:

```python
import pytest
import requests
from pathlib import Path
from unittest.mock import patch, Mock
from strava_exporter.oauth import _build_auth_url, _exchange_code, _save_refresh_token


def test_build_auth_url_required_params():
    url = _build_auth_url("123", "http://localhost:8080/callback")
    assert "client_id=123" in url
    assert "response_type=code" in url
    assert "approval_prompt=force" in url
    assert "localhost%3A8080" in url or "localhost:8080" in url  # redirect_uri encoded


def test_build_auth_url_scope():
    url = _build_auth_url("123", "http://localhost:8080/callback")
    assert "activity" in url and "read_all" in url


def test_build_auth_url_base():
    url = _build_auth_url("123", "http://localhost:8080/callback")
    assert url.startswith("https://www.strava.com/oauth/authorize")


def test_exchange_code_returns_refresh_token():
    mock_resp = Mock()
    mock_resp.json.return_value = {"refresh_token": "rt_abc123", "access_token": "at_xyz"}
    mock_resp.raise_for_status = Mock()

    with patch("strava_exporter.oauth.requests.post", return_value=mock_resp) as mock_post:
        result = _exchange_code("123", "secret", "auth_code")

    assert result == "rt_abc123"
    mock_post.assert_called_once_with(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": "123",
            "client_secret": "secret",
            "code": "auth_code",
            "grant_type": "authorization_code",
        },
        timeout=10,
    )


def test_exchange_code_raises_on_http_error():
    mock_resp = Mock()
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401")

    with patch("strava_exporter.oauth.requests.post", return_value=mock_resp):
        with pytest.raises(requests.exceptions.HTTPError):
            _exchange_code("bad", "creds", "code")


def test_save_refresh_token_creates_new_file(tmp_path):
    env_path = tmp_path / ".env"
    _save_refresh_token("mytoken", env_path)
    assert env_path.read_text() == "REFRESH_TOKEN=mytoken\n"


def test_save_refresh_token_appends_to_existing(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("CLIENT_ID=123\nCLIENT_SECRET=secret\n")
    _save_refresh_token("mytoken", env_path)
    content = env_path.read_text()
    assert "CLIENT_ID=123" in content
    assert "CLIENT_SECRET=secret" in content
    assert "REFRESH_TOKEN=mytoken" in content


def test_save_refresh_token_replaces_existing(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("CLIENT_ID=123\nREFRESH_TOKEN=oldtoken\nCLIENT_SECRET=secret\n")
    _save_refresh_token("newtoken", env_path)
    content = env_path.read_text()
    assert "REFRESH_TOKEN=newtoken" in content
    assert "oldtoken" not in content
    assert "CLIENT_ID=123" in content
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/timotej/Documents/projects/strava-gpt-exporter
source venv/bin/activate && pytest tests/test_oauth.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'strava_exporter.oauth'`

- [ ] **Step 3: Implement oauth.py helper functions**

Create `strava_exporter/oauth.py`:

```python
import webbrowser
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
REDIRECT_URI = "http://localhost:8080/callback"
CALLBACK_PORT = 8080


def _build_auth_url(client_id: str, redirect_uri: str) -> str:
    params = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "approval_prompt": "force",
        "scope": "activity:read_all",
    })
    return f"{STRAVA_AUTH_URL}?{params}"


def _exchange_code(client_id: str, client_secret: str, code: str) -> str:
    response = requests.post(
        STRAVA_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["refresh_token"]


def _save_refresh_token(refresh_token: str, env_path: Path) -> None:
    token_line = f"REFRESH_TOKEN={refresh_token}\n"
    if not env_path.exists():
        env_path.write_text(token_line)
        return
    content = env_path.read_text()
    lines = content.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("REFRESH_TOKEN="):
            lines[i] = token_line
            env_path.write_text("".join(lines))
            return
    # Not present — append
    if content and not content.endswith("\n"):
        token_line = "\n" + token_line
    env_path.write_text(content + token_line)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
source venv/bin/activate && pytest tests/test_oauth.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add strava_exporter/oauth.py tests/test_oauth.py
git commit -m "feat: oauth helpers — build_auth_url, exchange_code, save_refresh_token"
```

---

## Task 2: oauth.py — CallbackHandler and run_oauth_flow

**Files:**
- Modify: `strava_exporter/oauth.py` (append `_CallbackHandler` class and `run_oauth_flow` function)
- Modify: `tests/test_oauth.py` (append `run_oauth_flow` tests)

- [ ] **Step 1: Append failing tests to tests/test_oauth.py**

Add the following to the **end** of `tests/test_oauth.py`:

```python
from strava_exporter.oauth import run_oauth_flow, _CallbackHandler


def test_run_oauth_flow_success(tmp_path):
    env_path = tmp_path / ".env"

    def fake_handle_request():
        _CallbackHandler.code = "test_code_abc"
        _CallbackHandler.error = None

    with patch("strava_exporter.oauth.webbrowser.open", return_value=True):
        with patch("strava_exporter.oauth.HTTPServer") as mock_server_class:
            mock_server = Mock()
            mock_server.handle_request.side_effect = fake_handle_request
            mock_server_class.return_value = mock_server
            with patch("strava_exporter.oauth._exchange_code", return_value="rt_xyz") as mock_exchange:
                with patch("strava_exporter.oauth._save_refresh_token") as mock_save:
                    run_oauth_flow("cid", "csecret", env_path)

    mock_exchange.assert_called_once_with("cid", "csecret", "test_code_abc")
    mock_save.assert_called_once_with("rt_xyz", env_path)


def test_run_oauth_flow_opens_browser(tmp_path):
    env_path = tmp_path / ".env"

    def fake_handle_request():
        _CallbackHandler.code = "code"
        _CallbackHandler.error = None

    with patch("strava_exporter.oauth.webbrowser.open", return_value=True) as mock_browser:
        with patch("strava_exporter.oauth.HTTPServer") as mock_server_class:
            mock_server = Mock()
            mock_server.handle_request.side_effect = fake_handle_request
            mock_server_class.return_value = mock_server
            with patch("strava_exporter.oauth._exchange_code", return_value="rt"):
                with patch("strava_exporter.oauth._save_refresh_token"):
                    run_oauth_flow("123", "secret", env_path)

    mock_browser.assert_called_once()
    called_url = mock_browser.call_args[0][0]
    assert "client_id=123" in called_url
    assert "activity" in called_url


def test_run_oauth_flow_error_from_strava(tmp_path):
    env_path = tmp_path / ".env"

    def fake_handle_request():
        _CallbackHandler.code = None
        _CallbackHandler.error = "access_denied"

    with patch("strava_exporter.oauth.webbrowser.open", return_value=True):
        with patch("strava_exporter.oauth.HTTPServer") as mock_server_class:
            mock_server = Mock()
            mock_server.handle_request.side_effect = fake_handle_request
            mock_server_class.return_value = mock_server
            with pytest.raises(RuntimeError, match="access_denied"):
                run_oauth_flow("cid", "csecret", env_path)


def test_run_oauth_flow_port_in_use(tmp_path):
    env_path = tmp_path / ".env"

    with patch("strava_exporter.oauth.webbrowser.open", return_value=True):
        with patch("strava_exporter.oauth.HTTPServer", side_effect=OSError("address in use")):
            with pytest.raises(OSError):
                run_oauth_flow("cid", "csecret", env_path)
```

- [ ] **Step 2: Run new tests to verify they fail**

```bash
source venv/bin/activate && pytest tests/test_oauth.py -k "run_oauth_flow or CallbackHandler" -v
```

Expected: FAIL — `ImportError: cannot import name 'run_oauth_flow'`

- [ ] **Step 3: Append _CallbackHandler and run_oauth_flow to oauth.py**

Add to the **end** of `strava_exporter/oauth.py`:

```python


class _CallbackHandler(BaseHTTPRequestHandler):
    code: str | None = None
    error: str | None = None

    def do_GET(self) -> None:
        params = parse_qs(urlparse(self.path).query)
        _CallbackHandler.error = params.get("error", [None])[0]
        _CallbackHandler.code = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Authorization complete! You can close this tab.</h1></body></html>"
        )

    def log_message(self, format: str, *args: object) -> None:
        pass  # suppress server logs


def run_oauth_flow(client_id: str, client_secret: str, env_path: Path) -> None:
    auth_url = _build_auth_url(client_id, REDIRECT_URI)

    print("Opening browser for Strava authorization...")
    opened = webbrowser.open(auth_url)
    if not opened:
        print(f"Could not open browser automatically. Please visit:\n{auth_url}")

    _CallbackHandler.code = None
    _CallbackHandler.error = None

    server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    print(f"Waiting for authorization on port {CALLBACK_PORT}...")
    server.handle_request()
    server.server_close()

    if _CallbackHandler.error:
        raise RuntimeError(f"Authorization denied: {_CallbackHandler.error}")
    if not _CallbackHandler.code:
        raise RuntimeError("No authorization code received.")

    refresh_token = _exchange_code(client_id, client_secret, _CallbackHandler.code)
    _save_refresh_token(refresh_token, env_path)
    print(f"Authorization complete. REFRESH_TOKEN saved to {env_path}")
```

- [ ] **Step 4: Run all oauth tests to verify they pass**

```bash
source venv/bin/activate && pytest tests/test_oauth.py -v
```

Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add strava_exporter/oauth.py tests/test_oauth.py
git commit -m "feat: run_oauth_flow — local HTTP server OAuth callback handler"
```

---

## Task 3: cli.py — group refactor, auth command, _find_env_path

**Files:**
- Modify: `strava_exporter/cli.py` (full replacement)
- Create: `tests/test_cli_auth.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_auth.py`:

```python
import pytest
from click.testing import CliRunner
from unittest.mock import patch
from strava_exporter.cli import cli


def _clear_cred_env(monkeypatch):
    for var in ("CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN"):
        monkeypatch.delenv(var, raising=False)


def test_cli_group_shows_auth_and_export():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "auth" in result.output
    assert "export" in result.output


def test_export_command_help_unchanged():
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--help"])
    assert result.exit_code == 0
    assert "--from" in result.output
    assert "--to" in result.output
    assert "--sport" in result.output
    assert "--format" in result.output
    assert "--output" in result.output


def test_auth_command_success(tmp_path, monkeypatch):
    _clear_cred_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env"
    env_file.write_text("CLIENT_ID=123\nCLIENT_SECRET=secret\n")

    with patch("strava_exporter.cli.run_oauth_flow") as mock_flow:
        runner = CliRunner()
        result = runner.invoke(cli, ["auth"])

    assert result.exit_code == 0, result.output
    mock_flow.assert_called_once()
    args = mock_flow.call_args[0]
    assert args[0] == "123"        # client_id
    assert args[1] == "secret"     # client_secret
    assert args[2].name == ".env"  # env_path points to .env file


def test_auth_command_missing_client_id(tmp_path, monkeypatch):
    _clear_cred_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env"
    env_file.write_text("CLIENT_SECRET=secret\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["auth"])

    assert result.exit_code != 0
    assert "CLIENT_ID" in result.output or "CLIENT_SECRET" in result.output


def test_auth_command_no_env_file(tmp_path, monkeypatch):
    _clear_cred_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    # No .env file exists, no env vars set

    runner = CliRunner()
    result = runner.invoke(cli, ["auth"])

    assert result.exit_code != 0


def test_export_missing_refresh_token_suggests_auth(tmp_path, monkeypatch):
    _clear_cred_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    env_file = tmp_path / ".env"
    env_file.write_text("CLIENT_ID=123\nCLIENT_SECRET=secret\n")

    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--from", "2025-01-01", "--to", "2025-01-31"])

    assert result.exit_code != 0
    assert "strava-export auth" in result.output


def test_export_missing_client_credentials(tmp_path, monkeypatch):
    _clear_cred_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    # No .env at all

    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--from", "2025-01-01", "--to", "2025-01-31"])

    assert result.exit_code != 0
    assert "CLIENT_ID" in result.output or "CLIENT_SECRET" in result.output or "Missing" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
source venv/bin/activate && pytest tests/test_cli_auth.py -v
```

Expected: multiple failures — `cli` is not a group yet, `auth` command doesn't exist.

- [ ] **Step 3: Replace cli.py**

Replace the full contents of `strava_exporter/cli.py` with:

```python
import os
from datetime import datetime, time as dt_time
from pathlib import Path

import click
from dotenv import load_dotenv

from strava_exporter.auth import get_access_token
from strava_exporter.client import fetch_activities
from strava_exporter.filters import filter_by_sport
from strava_exporter.formatters.json_fmt import format_json
from strava_exporter.formatters.md_fmt import format_markdown
from strava_exporter.oauth import run_oauth_flow


def _find_env_path() -> Path | None:
    for path in [Path(".env"), Path.home() / ".strava-exporter" / ".env"]:
        if path.exists():
            return path
    return None


def _load_credentials() -> tuple[str, str, str]:
    env_path = _find_env_path()
    if env_path:
        load_dotenv(env_path)

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    refresh_token = os.getenv("REFRESH_TOKEN")

    if not client_id or not client_secret:
        raise click.ClickException(
            "Missing credentials. Create a .env file with:\n"
            "  CLIENT_ID=<your_client_id>\n"
            "  CLIENT_SECRET=<your_client_secret>\n"
            "See README.md for setup instructions."
        )
    if not refresh_token:
        raise click.ClickException(
            "REFRESH_TOKEN not found. Run 'strava-export auth' to authorize."
        )
    return client_id, client_secret, refresh_token


@click.group()
def cli() -> None:
    """Strava activity exporter for LLM analysis."""


@cli.command()
def auth() -> None:
    """Run Strava OAuth flow and save REFRESH_TOKEN to .env."""
    env_path = _find_env_path()
    if env_path:
        load_dotenv(env_path)
    else:
        env_path = Path(".env")

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not client_id or not client_secret:
        raise click.ClickException("Set CLIENT_ID and CLIENT_SECRET in .env first.")

    try:
        run_oauth_flow(client_id, client_secret, env_path)
    except Exception as e:
        raise click.ClickException(str(e))


@cli.command("export")
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
def export(
    from_date: datetime,
    to_date: datetime,
    sport: str | None,
    fmt: str,
    output: str | None,
) -> None:
    """Export Strava activities to Markdown or JSON."""
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

- [ ] **Step 4: Run all tests to verify they pass**

```bash
source venv/bin/activate && pytest -v
```

Expected: all prior 37 tests pass + new 7 cli_auth tests = 44 passed

- [ ] **Step 5: Commit**

```bash
git add strava_exporter/cli.py tests/test_cli_auth.py
git commit -m "feat: cli group with auth command and updated credentials handling"
```

---

## Task 4: pyproject.toml — update entry point

**Files:**
- Modify: `pyproject.toml`

No new tests needed — verified via smoke test.

- [ ] **Step 1: Update the entry point in pyproject.toml**

In `pyproject.toml`, change line:

```toml
strava-export = "strava_exporter.cli:main"
```

to:

```toml
strava-export = "strava_exporter.cli:cli"
```

- [ ] **Step 2: Reinstall to register updated entry point**

```bash
source venv/bin/activate && pip install -e .
```

Expected: `Successfully installed strava-gpt-exporter-0.1.0`

- [ ] **Step 3: Smoke-test the group**

```bash
source venv/bin/activate && strava-export --help
```

Expected output contains both `auth` and `export`:

```
Usage: strava-export [OPTIONS] COMMAND [ARGS]...

  Strava activity exporter for LLM analysis.

Options:
  --help  Show this message and exit.

Commands:
  auth    Run Strava OAuth flow and save REFRESH_TOKEN to .env.
  export  Export Strava activities to Markdown or JSON.
```

- [ ] **Step 4: Smoke-test auth help**

```bash
source venv/bin/activate && strava-export auth --help
```

Expected: shows `auth` command description.

- [ ] **Step 5: Smoke-test export help**

```bash
source venv/bin/activate && strava-export export --help
```

Expected: shows all export flags (`--from`, `--to`, `--sport`, `--format`, `--output`).

- [ ] **Step 6: Run full test suite**

```bash
source venv/bin/activate && pytest -v
```

Expected: 44 passed, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml
git commit -m "chore: update entry point to cli group"
```
