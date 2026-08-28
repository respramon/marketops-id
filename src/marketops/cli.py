"""Command-line interface.

    marketops doctor                        preflight every dependency
    marketops run --mode fixture            deterministic replay, zero credits
    marketops run --mode live               real Sectors data
    marketops run --mode live --dry-notify  live data, render but do not send
    marketops report                        re-print the last run
    marketops serve                         start the dashboard

``run`` is what the scheduler invokes. Everything else exists for humans.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import DISCLAIMER, __version__
from .config import get_settings, load_scoring, load_watchlist
from .models import RunMode, RunStatus
from .pipeline import execute
from .render import console_summary
from .security import configure_safe_logging, redact_text
from .state import StateStore

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help=(
        "MarketOps ID - autonomous IDX research triage. "
        "Research triage only: no investment recommendations, no trade execution."
    ),
)


def _configure_logging(
    level: str,
    json_logs: bool = False,
    *,
    secrets: tuple[str, ...] = (),
) -> None:
    """Structured, greppable logs. CI reads these as unattended-run evidence."""
    configure_safe_logging(level, json_logs=json_logs, secrets=secrets)


def _ok(message: str) -> None:
    typer.secho(f"  PASS   {message}", fg=typer.colors.GREEN)


def _warn(message: str) -> None:
    typer.secho(f"  WARN   {message}", fg=typer.colors.YELLOW)


def _fail(message: str) -> None:
    typer.secho(f"  FAIL   {message}", fg=typer.colors.RED)


@app.command()
def doctor(
    check_api: Annotated[
        bool,
        typer.Option("--check-api/--no-check-api", help="Spend 1 credit to verify the API key."),
    ] = False,
) -> None:
    """Preflight every dependency before trusting the scheduler with it.

    Never prints a secret - only whether one is present and whether it works.
    """
    typer.secho(f"\nMarketOps ID v{__version__} - doctor\n", bold=True)
    settings = get_settings()
    secrets = settings.secret_values_for_redaction
    _configure_logging(settings.log_level, secrets=secrets)
    failures = 0
    warnings = 0

    # --- configuration ----------------------------------------------------
    typer.secho("configuration", bold=True)
    try:
        scoring = load_scoring(settings.scoring_path)
        _ok(
            f"scoring.yml valid (P1>={scoring.priority.p1_min}, "
            f"P2>={scoring.priority.p2_min}, P3>={scoring.priority.p3_min}, "
            f"max={scoring.maximum_score})"
        )
    except (OSError, ValueError) as exc:
        _fail(redact_text(f"scoring.yml invalid: {exc}", secrets))
        failures += 1
    try:
        watchlist = load_watchlist(settings.watchlist_path)
        _ok(f"watchlist.yml valid ({len(watchlist.covered)} covered, {len(watchlist.muted)} muted)")
    except (OSError, ValueError) as exc:
        _fail(redact_text(f"watchlist.yml invalid: {exc}", secrets))
        failures += 1

    # --- directories ------------------------------------------------------
    typer.secho("\ndirectories", bold=True)
    for label, path in (
        ("artifact dir", settings.artifact_dir),
        ("fixture dir", settings.fixture_dir),
    ):
        target = Path(path)
        if label == "artifact dir":
            try:
                target.mkdir(parents=True, exist_ok=True)
                _ok(f"{label} writable: {target}")
            except OSError as exc:
                _fail(redact_text(f"{label} not writable: {exc}", secrets))
                failures += 1
        elif target.exists():
            count = len(list(target.glob("*.json")))
            _ok(f"{label} present: {target} ({count} fixture files)")
        else:
            _warn(f"{label} missing: {target} - fixture mode will fail")
            warnings += 1

    # --- database ---------------------------------------------------------
    typer.secho("\nstate database", bold=True)
    try:
        store = StateStore(settings.db_path)
        if store.is_writable():
            _ok(
                f"sqlite writable: {settings.db_path} "
                f"({store.run_count()} runs, {store.event_count()} known events)"
            )
        else:
            _fail(f"sqlite not writable: {settings.db_path}")
            failures += 1
        store.close()
    except Exception as exc:
        _fail(redact_text(f"sqlite unavailable: {type(exc).__name__}: {exc}", secrets))
        failures += 1

    # --- credentials ------------------------------------------------------
    typer.secho("\ncredentials", bold=True)
    if settings.has_api_key:
        _ok("SECTORS_API_KEY present (value never printed)")
    else:
        _warn("SECTORS_API_KEY not set - live mode unavailable, fixture mode still works")
        warnings += 1

    if settings.discord_webhook_url:
        _ok("DISCORD_WEBHOOK_URL present (value never printed)")
    elif settings.generic_webhook_url:
        _ok("GENERIC_WEBHOOK_URL present (value never printed)")
    else:
        _warn("no webhook configured - the queue will be written to disk but not delivered")
        warnings += 1

    # --- budget -----------------------------------------------------------
    typer.secho("\nAPI credit budget", bold=True)
    worst_case = 4 + 1 + (2 * settings.max_enrich_tickers)
    _ok(
        f"budget {settings.max_api_credits_per_run} credits/run; "
        f"worst case this config can spend {worst_case} "
        f"(4 discovery + 1 news + 2 x {settings.max_enrich_tickers} enrichment)"
    )
    if worst_case > settings.max_api_credits_per_run:
        _warn(
            "budget is lower than the worst case - enrichment will stop early "
            "and the run will be reported PARTIAL"
        )
        warnings += 1

    # --- optional live probe ----------------------------------------------
    if check_api:
        typer.secho("\nSectors API reachability", bold=True)
        if not settings.has_api_key:
            _fail("cannot probe: SECTORS_API_KEY not set")
            failures += 1
        else:
            try:
                from .sectors import SectorsClient

                with SectorsClient(settings) as client:
                    client.ping()
                _ok("authenticated against api.sectors.app/v2 (1 credit spent)")
            except Exception as exc:
                _fail(redact_text(f"{type(exc).__name__}: {exc}", secrets))
                failures += 1
    else:
        typer.secho("\nSectors API reachability", bold=True)
        _warn("skipped - pass --check-api to spend 1 credit and verify the key")

    typer.secho("\n" + "-" * 68)
    if failures:
        typer.secho(
            f"DOCTOR: {failures} failure(s), {warnings} warning(s)", fg=typer.colors.RED, bold=True
        )
        raise typer.Exit(code=1)
    typer.secho(
        f"DOCTOR: all checks passed ({warnings} warning(s))", fg=typer.colors.GREEN, bold=True
    )
    typer.echo(DISCLAIMER)


@app.command()
def run(
    mode: Annotated[
        RunMode, typer.Option("--mode", help="fixture = sanitized replay, live = Sectors API.")
    ] = RunMode.FIXTURE,
    dry_notify: Annotated[
        bool,
        typer.Option("--dry-notify", help="Render the notification payload without sending it."),
    ] = False,
    no_notify: Annotated[
        bool, typer.Option("--no-notify", help="Skip the notification stage entirely.")
    ] = False,
    trigger: Annotated[
        str, typer.Option("--trigger", help="How this run was started (schedule, manual, ...).")
    ] = "manual",
    artifact_dir: Annotated[
        Path | None, typer.Option("--artifact-dir", help="Override the artifact output directory.")
    ] = None,
    json_logs: Annotated[
        bool, typer.Option("--json-logs", help="Emit machine-readable JSON log lines.")
    ] = False,
    fail_on_partial: Annotated[
        bool,
        typer.Option("--fail-on-partial", help="Exit non-zero when the run degrades to PARTIAL."),
    ] = False,
) -> None:
    """Execute one full pipeline run. This is what the scheduler calls."""
    settings = get_settings()
    secrets = settings.secret_values_for_redaction
    _configure_logging(settings.log_level, json_logs, secrets=secrets)

    if mode is RunMode.LIVE and not settings.has_api_key:
        typer.secho(
            "SECTORS_API_KEY is not set. Live mode needs it in .env locally or in "
            "GitHub Secrets in CI. Use --mode fixture to run without credentials.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    report = execute(
        settings=settings,
        mode=mode,
        trigger=trigger,
        dry_notify=dry_notify,
        notify=not no_notify,
        artifact_dir=artifact_dir,
    )

    typer.echo("")
    typer.echo(redact_text(console_summary(report), secrets))

    if report.status is RunStatus.FAILED:
        raise typer.Exit(code=1)
    if fail_on_partial and report.status is RunStatus.PARTIAL:
        raise typer.Exit(code=3)


@app.command()
def report(
    limit: Annotated[int, typer.Option("--limit", help="How many past runs to list.")] = 10,
) -> None:
    """Re-print the most recent run and the unattended run history."""
    settings = get_settings()
    secrets = settings.secret_values_for_redaction
    _configure_logging(settings.log_level, secrets=secrets)
    store = StateStore(settings.db_path)
    try:
        latest = store.latest_report()
        if latest is None:
            typer.secho(
                "No run recorded yet. Try: marketops run --mode fixture",
                fg=typer.colors.YELLOW,
            )
            raise typer.Exit(code=1)
        typer.echo(redact_text(console_summary(latest), secrets))
        history = store.recent_runs(limit)
        if history:
            typer.echo("")
            typer.secho("UNATTENDED RUN HISTORY", bold=True)
            header = (
                f"  {'run id':<28} {'trigger':<10} {'mode':<8} {'status':<8} "
                f"{'evt':>4} {'new':>4} {'dup':>4} {'sent':>5} {'cr':>4}"
            )
            typer.echo(header)
            for row in history:
                typer.echo(
                    redact_text(
                        f"  {row['run_id']:<28} {row['trigger']:<10} {row['mode']:<8} "
                        f"{row['status']:<8} {row['events_detected']:>4} "
                        f"{row['new_events']:>4} {row['duplicate_events_suppressed']:>4} "
                        f"{row['notifications_sent']:>5} {row['estimated_api_credits']:>4}",
                        secrets,
                    )
                )
    finally:
        store.close()


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port")] = 8000,
) -> None:
    """Start the read-only dashboard."""
    import uvicorn

    settings = get_settings()
    _configure_logging(
        settings.log_level,
        secrets=settings.secret_values_for_redaction,
    )
    typer.secho(f"MarketOps ID dashboard on http://{host}:{port}", fg=typer.colors.GREEN)
    uvicorn.run("marketops.web:app", host=host, port=port, log_level=settings.log_level.lower())


@app.command()
def version() -> None:
    """Print the version and the standing disclaimer."""
    typer.echo(f"MarketOps ID v{__version__}")
    typer.echo(DISCLAIMER)


def main() -> None:  # pragma: no cover - console-script shim
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
