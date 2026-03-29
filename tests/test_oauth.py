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
    assert "scope=activity%3Aread_all" in url


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
