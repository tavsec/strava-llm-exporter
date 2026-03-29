import pytest
import requests
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
        timeout=10,
    )


def test_get_access_token_raises_on_http_error():
    mock_resp = Mock()
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")

    with patch("strava_exporter.auth.requests.post", return_value=mock_resp):
        with pytest.raises(requests.exceptions.HTTPError, match="401"):
            get_access_token("bad", "creds", "token")
