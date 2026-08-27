"""Artifact rendering.

An unattended run has to leave evidence a human can read later without a
server, and that evidence must never misrepresent a fixture replay as live
market data.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from tests.conftest import filing_event, price_event, suspension_event

from marketops.models import (
    WIB,
    Priority,
    RunMode,
    RunReport,
    RunStatus,
    ScoreBreakdown,
    ScoreComponent,
    SourceName,
    SourceReport,
    SourceState,
    TickerDossier,
)
from marketops.render import (
    console_summary,
    render_report_html,
    render_summary_markdown,
    report_context,
    write_artifacts,
)


def _dossier(symbol: str, score: int, priority: Priority) -> TickerDossier:
    return TickerDossier(
        symbol=symbol,
        company_name=f"PT {symbol} Tbk",
        events=[filing_event(symbol, pct=1.85, value=4.1e11), price_event(symbol, pct=8.42)],
        score=ScoreBreakdown(
            total=score,
            priority=priority,
            components=[
                ScoreComponent(label="Insider filing", points=25, evidence="Dana Nusantara"),
                ScoreComponent(label="Large one-day price move", points=20, evidence="8.42% move"),
            ],
        ),
    )


def _report(**kw: Any) -> RunReport:
    base: dict[str, Any] = {
        "run_id": "run-20260826-071700-abc123",
        "mode": RunMode.FIXTURE,
        "status": RunStatus.OK,
        "started_at": datetime(2026, 8, 26, 7, 17, tzinfo=WIB),
        "finished_at": datetime(2026, 8, 26, 7, 17, 4, tzinfo=WIB),
        "trigger": "schedule",
        "events_detected": 16,
        "new_events": 16,
        "duplicate_events_suppressed": 0,
        "candidates": 7,
        "notifications_sent": 5,
        "estimated_api_credits": 15,
        "credit_budget": 25,
        "dossiers": [
            _dossier("FLMC", 100, Priority.P1),
            _dossier("ANTM", 75, Priority.P1),
            _dossier("MDKA", 50, Priority.P2),
            _dossier("BBCA", 25, Priority.P3),
            _dossier("NOISE", 5, Priority.NONE),
        ],
        "sources": [
            SourceReport(
                name=SourceName.FILINGS, state=SourceState.OK, records=2, credits=1, calls=1
            ),
            SourceReport(
                name=SourceName.FOREIGN_FLOW, state=SourceState.FAILED, error="upstream 500"
            ),
        ],
    }
    base.update(kw)
    return RunReport(**base)


class TestHtmlReport:
    def test_renders_without_leaving_template_syntax(self) -> None:
        html = render_report_html(_report())
        assert not re.search(r"\{\{|\{%", html)

    def test_is_self_contained(self) -> None:
        """Must open offline from a downloaded CI artifact."""
        html = render_report_html(_report(), standalone=True)
        assert "<style>" in html
        assert "/static/styles.css" not in html
        assert "--ink-900" in html

    def test_served_variant_links_the_stylesheet(self) -> None:
        html = render_report_html(_report(), standalone=False)
        assert "/static/styles.css" in html

    def test_fixture_mode_shows_the_replay_banner(self) -> None:
        assert "SANITIZED HISTORICAL REPLAY" in render_report_html(_report())

    def test_live_mode_shows_no_replay_banner(self) -> None:
        html = render_report_html(_report(mode=RunMode.LIVE))
        assert "SANITIZED HISTORICAL REPLAY" not in html

    def test_disclaimer_is_always_present(self) -> None:
        html = render_report_html(_report())
        assert "does not provide investment recommendations" in html

    def test_every_priority_band_is_rendered(self) -> None:
        html = render_report_html(_report())
        for band in ("P1", "P2", "P3"):
            assert f'id="band-{band}"' in html

    def test_below_threshold_tickers_are_not_shown_in_a_band(self) -> None:
        html = render_report_html(_report())
        assert "NOISE.JK" not in html

    def test_score_breakdown_is_visible(self) -> None:
        html = render_report_html(_report())
        assert "Why surfaced" in html
        assert "Insider filing" in html
        assert "+25" in html

    def test_run_warnings_are_surfaced(self) -> None:
        html = render_report_html(_report(warnings=["foreign_flow unavailable"]))
        assert "foreign_flow unavailable" in html
        assert "not an all-clear" in html

    def test_source_health_table_shows_a_failure(self) -> None:
        html = render_report_html(_report())
        assert "upstream 500" in html
        assert "foreign_flow" in html

    def test_user_content_is_escaped(self) -> None:
        """Headlines come from a third party; the dashboard must not execute them."""
        evil = TickerDossier(
            symbol="EVIL",
            events=[
                suspension_event("EVIL", reason='<script>alert("xss")</script>'),
            ],
            score=ScoreBreakdown(
                total=100,
                priority=Priority.P1,
                components=[
                    ScoreComponent(
                        label="IDX suspension", points=100, evidence="<img src=x onerror=alert(1)>"
                    )
                ],
            ),
        )
        html = render_report_html(_report(dossiers=[evil]))
        # The payload must survive as inert *text*, never as a live tag. Assert
        # on tag formation, not on substrings: "onerror=alert" appearing inside
        # "&lt;img ... &gt;" is escaped content and is harmless.
        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "<img src=x" not in html
        assert "&lt;img src=x onerror=alert(1)&gt;" in html

    def test_source_links_are_rendered_with_safe_rel(self) -> None:
        html = render_report_html(_report())
        if 'target="_blank"' in html:
            assert 'rel="noopener noreferrer"' in html


class TestMarkdownSummary:
    def test_contains_the_unattended_run_evidence(self) -> None:
        md = render_summary_markdown(_report())
        assert "run-20260826-071700-abc123" in md
        assert "`schedule`" in md
        assert "| Estimated API credits | 15 / 25 |" in md

    def test_lists_the_research_queue(self) -> None:
        md = render_summary_markdown(_report())
        assert "## Research queue" in md
        assert "`FLMC.JK`" in md
        assert "100/100" in md

    def test_flags_a_fixture_replay(self) -> None:
        assert "SANITIZED HISTORICAL REPLAY" in render_summary_markdown(_report())

    def test_reports_source_health(self) -> None:
        md = render_summary_markdown(_report())
        assert "## Source health" in md
        assert "failed" in md

    def test_warnings_section(self) -> None:
        md = render_summary_markdown(_report(warnings=["news degraded"]))
        assert "## Warnings" in md
        assert "news degraded" in md

    def test_empty_queue_says_so_plainly(self) -> None:
        md = render_summary_markdown(_report(dossiers=[]))
        assert "Nothing crossed the P3 threshold" in md


class TestConsoleSummary:
    def test_includes_the_counters_ci_greps_for(self) -> None:
        text = console_summary(_report())
        assert "RUN STATUS: OK" in text
        assert "events detected   16" in text
        assert "notifications     5" in text
        assert "api credits       15 / 25" in text

    def test_marks_a_fixture_replay(self) -> None:
        assert "SANITIZED REPLAY" in console_summary(_report())

    def test_live_mode_is_not_marked(self) -> None:
        assert "SANITIZED REPLAY" not in console_summary(_report(mode=RunMode.LIVE))

    def test_empty_queue(self) -> None:
        assert "RESEARCH QUEUE: empty" in console_summary(_report(dossiers=[]))


class TestArtifacts:
    def test_writes_every_expected_file(self, tmp_path: Path) -> None:
        report = _report()
        written = write_artifacts(report, tmp_path)
        assert set(written) >= {"json", "latest_json", "html", "latest_html", "summary"}
        for path in written.values():
            assert path.exists()
            assert path.stat().st_size > 0

    def test_json_round_trips(self, tmp_path: Path) -> None:
        report = _report()
        write_artifacts(report, tmp_path)
        loaded = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
        assert loaded["run_id"] == report.run_id
        assert loaded["mode"] == "fixture"
        assert loaded["estimated_api_credits"] == 15

    def test_latest_mirrors_the_run_file(self, tmp_path: Path) -> None:
        report = _report()
        write_artifacts(report, tmp_path)
        assert (tmp_path / "latest.html").read_text(encoding="utf-8") == (
            tmp_path / f"{report.run_id}.html"
        ).read_text(encoding="utf-8")

    def test_creates_a_missing_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "deep" / "nested"
        write_artifacts(_report(), target)
        assert (target / "latest.json").exists()

    def test_history_is_written_when_a_store_is_supplied(self, tmp_path: Path) -> None:
        from marketops.state import StateStore

        store = StateStore(tmp_path / "state.db")
        try:
            store.record_run(_report())
            written = write_artifacts(_report(), tmp_path, store=store)
            assert "history" in written
            history = json.loads(written["history"].read_text(encoding="utf-8"))
            assert history[0]["run_id"] == "run-20260826-071700-abc123"
        finally:
            store.close()


class TestContext:
    def test_bands_cover_p1_p2_p3_only(self) -> None:
        context = report_context(_report())
        assert [b["priority"] for b in context["bands"]] == [
            Priority.P1,
            Priority.P2,
            Priority.P3,
        ]

    def test_status_class_maps_for_the_stylesheet(self) -> None:
        assert report_context(_report())["status_class"] == "ok"
        assert report_context(_report(status=RunStatus.PARTIAL))["status_class"] == "partial"
        assert report_context(_report(status=RunStatus.FAILED))["status_class"] == "failed"

    @pytest.mark.parametrize(
        ("value", "expected"),
        [(4.125e11, "IDR 412.50B"), (1.5e12, "IDR 1.50T"), (250_000, "IDR 250,000"), ("x", "-")],
    )
    def test_idr_filter(self, value: Any, expected: str) -> None:
        from marketops.render import _idr_filter

        assert _idr_filter(value) == expected
