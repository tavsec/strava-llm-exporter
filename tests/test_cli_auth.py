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
