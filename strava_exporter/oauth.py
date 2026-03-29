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
        env_path.write_text(token_line, encoding="utf-8")
        return
    content = env_path.read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("REFRESH_TOKEN="):
            lines[i] = token_line
            env_path.write_text("".join(lines), encoding="utf-8")
            return
    # Not present — append
    if content and not content.endswith("\n"):
        token_line = "\n" + token_line
    env_path.write_text(content + token_line, encoding="utf-8")


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
