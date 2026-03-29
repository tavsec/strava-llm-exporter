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
