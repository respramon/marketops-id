"""Command-line surface.

``marketops run`` is what the scheduler invokes unattended, so its exit codes
are an operational contract: 0 means the queue is trustworthy, non-zero means a
human should look at the workflow log.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.conftest import FIXTURE_DIR
from typer.testing import CliRunner

from marketops.cli import app
from marketops.config import REPO_ROOT, get_settings

runner = CliRunner()


@pytest.fixture
def cli_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Point the CLI at a throwaway database and artifact directory.

    Any ambient credential is cleared so a developer's real key can never be
    picked up by a test run.
    """
    for secret in ("SECTORS_API_KEY", "DISCORD_WEBHOOK_URL", "GENERIC_WEBHOOK_URL"):
        monkeypatch.delenv(secret, raising=False)
    monkeypatch.setenv("MARKETOPS_DB_PATH", str(tmp_path / "state.db"))
    monkeypatch.setenv("MARKETOPS_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("MARKETOPS_FIXTURE_DIR", str(FIXTURE_DIR))
    monkeypatch.setenv("MARKETOPS_SCORING_PATH", str(REPO_ROOT / "config" / "scoring.yml"))
    monkeypatch.setenv("MARKETOPS_WATCHLIST_PATH", str(REPO_ROOT / "config" / "watchlist.yml"))
    monkeypatch.setenv("MARKETOPS_LOG_LEVEL", "WARNING")
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


class TestVersion:
    def test_prints_version_and_disclaimer(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "MarketOps ID v" in result.stdout
        assert "does not provide investment recommendations" in result.stdout


class TestDoctor:
    def test_passes_without_credentials(self, cli_env: Path) -> None:
        """Fixture mode must be fully usable with no secrets at all."""
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "all checks passed" in result.stdout

    def test_warns_about_the_missing_api_key(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "SECTORS_API_KEY not set" in result.stdout

    def test_never_prints_a_secret(self, cli_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECTORS_API_KEY", "sk-live-DO-NOT-LEAK-ME")
        monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/9/SECRETPART")
        get_settings.cache_clear()
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "DO-NOT-LEAK-ME" not in result.stdout
        assert "SECRETPART" not in result.stdout
        assert "value never printed" in result.stdout

    def test_reports_the_credit_budget_worst_case(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "worst case" in result.stdout

    def test_fails_on_invalid_scoring_config(
        self, cli_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        broken = cli_env / "broken.yml"
        broken.write_text("priority: {p1_min: 75}\n", encoding="utf-8")
        monkeypatch.setenv("MARKETOPS_SCORING_PATH", str(broken))
        get_settings.cache_clear()
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "scoring.yml invalid" in result.stdout

    def test_check_api_without_a_key_fails_clearly(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["doctor", "--check-api"])
        assert result.exit_code == 1
        assert "cannot probe" in result.stdout


class TestRun:
    def test_fixture_run_succeeds_and_prints_the_queue(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["run", "--mode", "fixture", "--no-notify"])
        assert result.exit_code == 0
        assert "RUN STATUS: OK" in result.stdout
        assert "RESEARCH QUEUE" in result.stdout
        assert "[P1] FLMC.JK" in result.stdout
        assert "100/100" in result.stdout

    def test_fixture_run_is_labelled_as_a_replay(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["run", "--mode", "fixture", "--no-notify"])
        assert "SANITIZED REPLAY - NOT LIVE DATA" in result.stdout

    def test_score_breakdown_is_printed(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["run", "--mode", "fixture", "--no-notify"])
        assert "Insider or major-shareholder filing" in result.stdout
        assert "Large one-day price move" in result.stdout

    def test_disclaimer_is_printed(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["run", "--mode", "fixture", "--no-notify"])
        assert "Research triage only" in result.stdout

    def test_artifacts_are_written(self, cli_env: Path) -> None:
        runner.invoke(app, ["run", "--mode", "fixture", "--no-notify"])
        artifacts = cli_env / "artifacts"
        assert (artifacts / "latest.json").exists()
        assert (artifacts / "latest.html").exists()
        assert list(artifacts.glob("*-summary.md"))

    def test_second_run_suppresses_duplicates(self, cli_env: Path) -> None:
        runner.invoke(app, ["run", "--mode", "fixture", "--dry-notify"])
        second = runner.invoke(app, ["run", "--mode", "fixture", "--dry-notify"])
        assert "new events        0" in second.stdout
        assert "notifications     0" in second.stdout

    def test_live_mode_without_a_key_exits_with_guidance(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["run", "--mode", "live"])
        assert result.exit_code == 2
        assert "SECTORS_API_KEY is not set" in result.stdout
        assert "--mode fixture" in result.stdout

    def test_trigger_label_is_recorded(self, cli_env: Path) -> None:
        result = runner.invoke(
            app, ["run", "--mode", "fixture", "--no-notify", "--trigger", "schedule"]
        )
        assert "trigger           schedule" in result.stdout

    def test_json_logs_flag_emits_structured_lines(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["run", "--mode", "fixture", "--no-notify", "--json-logs"])
        assert result.exit_code == 0

    def test_fail_on_partial_leaves_a_clean_run_alone(self, cli_env: Path) -> None:
        result = runner.invoke(
            app, ["run", "--mode", "fixture", "--no-notify", "--fail-on-partial"]
        )
        assert result.exit_code == 0

    def test_fail_on_partial_trips_when_a_source_is_degraded(
        self, cli_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A budget too small to finish enrichment must be visible to CI."""
        monkeypatch.setenv("MARKETOPS_MAX_API_CREDITS_PER_RUN", "6")
        get_settings.cache_clear()
        result = runner.invoke(
            app, ["run", "--mode", "fixture", "--no-notify", "--fail-on-partial"]
        )
        assert result.exit_code == 3
        assert "RUN STATUS: PARTIAL" in result.stdout

    def test_artifact_dir_override(self, cli_env: Path) -> None:
        target = cli_env / "elsewhere"
        result = runner.invoke(
            app,
            ["run", "--mode", "fixture", "--no-notify", "--artifact-dir", str(target)],
        )
        assert result.exit_code == 0
        assert (target / "latest.json").exists()


class TestReport:
    def test_reports_the_last_run(self, cli_env: Path) -> None:
        runner.invoke(app, ["run", "--mode", "fixture", "--no-notify"])
        result = runner.invoke(app, ["report"])
        assert result.exit_code == 0
        assert "RESEARCH QUEUE" in result.stdout
        assert "UNATTENDED RUN HISTORY" in result.stdout

    def test_history_lists_every_recorded_run(self, cli_env: Path) -> None:
        for _ in range(3):
            runner.invoke(app, ["run", "--mode", "fixture", "--no-notify"])
        result = runner.invoke(app, ["report"])
        assert result.stdout.count("run-2") >= 3

    def test_empty_state_is_a_helpful_failure(self, cli_env: Path) -> None:
        result = runner.invoke(app, ["report"])
        assert result.exit_code == 1
        assert "No run recorded yet" in result.stdout
