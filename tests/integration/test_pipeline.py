"""End-to-end pipeline behaviour.

Covers the two claims the product is judged on:

* the whole chain runs unattended and produces a correct, ranked queue, and
* it degrades honestly - a dead source yields PARTIAL with the gap named, never
  a silent all-clear.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from tests.conftest import FIXTURE_DIR, load_fixture

from marketops.config import Settings, load_scoring, load_watchlist
from marketops.models import WIB, Priority, RunMode, RunStatus, SourceName, SourceState
from marketops.pipeline import Pipeline, execute, make_run_id, source_summary
from marketops.sectors import FixtureSource, SectorsClient
from marketops.state import StateStore

BASE = "https://api.sectors.app"
CLOCK = datetime(2026, 8, 26, 7, 17, 0, tzinfo=WIB)
DELIVERY_HOOK = "https://hooks.example.test/marketops-delivery"

EXPECTED_QUEUE = [
    ("FLMC", 100, Priority.P1),
    ("ANTM", 75, Priority.P1),
    ("MDKA", 50, Priority.P2),
    ("ADRO", 35, Priority.P3),
    ("BBCA", 25, Priority.P3),
]


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("marketops.sectors.time.sleep", lambda _s: None)


def build_pipeline(
    settings: Settings,
    store: StateStore,
    *,
    source: Any = None,
    mode: RunMode = RunMode.FIXTURE,
    trigger: str = "schedule",
) -> Pipeline:
    return Pipeline(
        settings=settings,
        source=source or FixtureSource(FIXTURE_DIR, budget=settings.max_api_credits_per_run),
        store=store,
        scoring=load_scoring(settings.scoring_path),
        watchlist=load_watchlist(settings.watchlist_path),
        mode=mode,
        trigger=trigger,
        clock=lambda: CLOCK,
    )


def delivery_settings(settings: Settings) -> Settings:
    """A test-only configured sink: real dispatch path, mocked transport."""
    from pydantic import SecretStr

    return settings.model_copy(update={"generic_webhook_url": SecretStr(DELIVERY_HOOK)})


class BrokenSource(FixtureSource):
    """A fixture source with named endpoints sabotaged, to prove fail-soft."""

    def __init__(self, fixture_dir: Path, *, broken: set[str], budget: int = 25) -> None:
        super().__init__(fixture_dir, budget=budget)
        self.broken = broken

    def _guard(self, name: str) -> None:
        if name in self.broken:
            raise httpx.ConnectError(f"{name} is down")

    def fetch_filings(self, start: date, end: date, limit: int = 30) -> list[dict[str, Any]]:
        self._guard("filings")
        return super().fetch_filings(start, end, limit)

    def fetch_suspensions(self, start: date, end: date, limit: int = 30) -> list[dict[str, Any]]:
        self._guard("suspensions")
        return super().fetch_suspensions(start, end, limit)

    def fetch_top_changes(self, periods: Any = ("1d",), n_stock: int = 10) -> dict[str, Any]:
        self._guard("movers")
        return super().fetch_top_changes(periods, n_stock)

    def fetch_news(
        self, symbols: Any, start: date, end: date, limit: int = 30
    ) -> list[dict[str, Any]]:
        self._guard("news")
        return super().fetch_news(symbols, start, end, limit)

    def fetch_foreign_flow(self, symbol: str, start: date, end: date) -> dict[str, Any]:
        self._guard("foreign_flow")
        return super().fetch_foreign_flow(symbol, start, end)

    def fetch_corporate_actions(self, symbol: str) -> dict[str, Any]:
        self._guard("corporate_actions")
        return super().fetch_corporate_actions(symbol)


# ---------------------------------------------------------------------------
class TestFixtureRun:
    def test_produces_the_expected_ranked_queue(
        self, settings: Settings, store: StateStore
    ) -> None:
        report = build_pipeline(settings, store).run(notify=False)
        actual = [(d.symbol, d.score.total, d.score.priority) for d in report.queue]
        assert actual == EXPECTED_QUEUE

    def test_status_is_clean(self, settings: Settings, store: StateStore) -> None:
        report = build_pipeline(settings, store).run(notify=False)
        assert report.status is RunStatus.OK
        assert all(s.state in (SourceState.OK, SourceState.SKIPPED) for s in report.sources)

    def test_every_source_contributed(self, settings: Settings, store: StateStore) -> None:
        report = build_pipeline(settings, store).run(notify=False)
        summary = source_summary(report)
        for name in (
            "filings",
            "suspensions",
            "movers",
            "news",
            "foreign_flow",
            "corporate_actions",
        ):
            assert summary[name]["state"] == "ok", name
            assert summary[name]["records"] >= 0

    def test_all_six_sectors_capabilities_are_represented_in_evidence(
        self, settings: Settings, store: StateStore
    ) -> None:
        """Sectors is the core data source, not one decorative call."""
        report = build_pipeline(settings, store).run(notify=False)
        seen = {e.event_type.value for d in report.dossiers for e in d.events}
        assert seen == {
            "filing",
            "suspension",
            "price_move",
            "news",
            "foreign_flow",
            "corporate_action",
        }

    def test_below_threshold_tickers_are_filtered_from_the_queue(
        self, settings: Settings, store: StateStore
    ) -> None:
        report = build_pipeline(settings, store).run(notify=False)
        queued = {d.symbol for d in report.queue}
        assert "INDF" not in queued
        assert "ASII" not in queued

    def test_credit_spend_stays_inside_the_budget(
        self, settings: Settings, store: StateStore
    ) -> None:
        report = build_pipeline(settings, store).run(notify=False)
        assert 0 < report.estimated_api_credits <= report.credit_budget

    def test_suspended_ticker_is_not_enriched(self, settings: Settings, store: StateStore) -> None:
        """A pinned 100 cannot move, so paying to enrich it is waste."""
        report = build_pipeline(settings, store).run(notify=False)
        flmc = next(d for d in report.queue if d.symbol == "FLMC")
        assert flmc.enriched is False

    def test_malformed_source_record_is_reported_not_hidden(
        self, settings: Settings, store: StateStore
    ) -> None:
        report = build_pipeline(settings, store).run(notify=False)
        assert any("malformed" in w for w in report.warnings)

    def test_run_is_reproducible(self, settings: Settings, tmp_path: Path) -> None:
        """Two runs against separate state must score identically."""
        results = []
        for name in ("a", "b"):
            state = StateStore(tmp_path / f"{name}.db")
            try:
                report = build_pipeline(settings, state).run(notify=False)
                results.append([(d.symbol, d.score.total) for d in report.queue])
            finally:
                state.close()
        assert results[0] == results[1]

    def test_fixture_replay_is_anchored_to_its_historical_date(
        self, settings: Settings, store: StateStore
    ) -> None:
        """Date-relative logic must not rot as the wall clock moves on."""
        pipeline = build_pipeline(settings, store)
        assert pipeline._today == date(2026, 8, 25)
        report = pipeline.run(notify=False)
        bbca = next(d for d in report.queue if d.symbol == "BBCA")
        assert any(e.event_type.value == "corporate_action" for e in bbca.events)


class TestDeduplicationAcrossRuns:
    @respx.mock
    def test_second_identical_run_notifies_nobody(
        self, settings: Settings, store: StateStore
    ) -> None:
        """The core Track 2 promise, end to end."""
        route = respx.post(DELIVERY_HOOK).mock(return_value=httpx.Response(204))
        configured = delivery_settings(settings)
        first = build_pipeline(configured, store).run()
        assert first.new_events > 0
        assert first.duplicate_events_suppressed == 0
        assert first.notifications_sent > 0

        second = build_pipeline(configured, store).run()
        assert second.new_events == 0
        assert second.duplicate_events_suppressed == first.events_detected
        assert second.notifications_sent == 0
        assert route.call_count == 1

    def test_the_queue_itself_is_unchanged_on_replay(
        self, settings: Settings, store: StateStore
    ) -> None:
        """Dedup suppresses the alert, not the analysis - the dashboard must
        still show today's queue."""
        first = build_pipeline(settings, store).run(notify=False)
        second = build_pipeline(settings, store).run(notify=False)
        assert [(d.symbol, d.score.total) for d in second.queue] == [
            (d.symbol, d.score.total) for d in first.queue
        ]

    @respx.mock
    def test_state_persists_across_a_restart(self, settings: Settings, tmp_path: Path) -> None:
        db = tmp_path / "persist.db"
        respx.post(DELIVERY_HOOK).mock(return_value=httpx.Response(204))
        configured = delivery_settings(settings)
        first_store = StateStore(db)
        try:
            first = build_pipeline(configured, first_store).run()
        finally:
            first_store.close()

        second_store = StateStore(db)
        try:
            second = build_pipeline(configured, second_store).run()
        finally:
            second_store.close()

        assert first.notifications_sent > 0
        assert second.notifications_sent == 0
        assert second.duplicate_events_suppressed > 0

    @respx.mock
    def test_new_evidence_reopens_notification(self, settings: Settings, store: StateStore) -> None:
        """Dedup must not become a permanent mute."""
        route = respx.post(DELIVERY_HOOK).mock(return_value=httpx.Response(204))
        configured = delivery_settings(settings)
        build_pipeline(configured, store).run()
        quiet = build_pipeline(configured, store).run()
        assert quiet.notifications_sent == 0

        from tests.conftest import suspension_event

        fresh = suspension_event("NEWX", reason="Fresh halt")
        pipeline = build_pipeline(configured, store)
        original = pipeline.discover

        def discover_with_extra() -> Any:
            events, reports = original()
            return [*events, fresh], reports

        pipeline.discover = discover_with_extra  # type: ignore[method-assign]
        loud = pipeline.run(dry_notify=True)
        assert loud.new_events == 1
        assert loud.notifications_sent == 0
        assert loud.notification_previews == 1
        assert route.call_count == 1


class TestFailSoft:
    @pytest.mark.parametrize("broken", ["news", "foreign_flow", "corporate_actions"])
    def test_one_dead_enrichment_source_still_yields_a_queue(
        self, settings: Settings, store: StateStore, broken: str
    ) -> None:
        source = BrokenSource(FIXTURE_DIR, broken={broken}, budget=25)
        report = build_pipeline(settings, store, source=source).run(notify=False)
        assert report.status is RunStatus.PARTIAL
        assert report.queue, "a dead enrichment source must not empty the queue"
        assert any(broken in w for w in report.warnings)

    def test_a_dead_discovery_source_degrades_but_does_not_stop(
        self, settings: Settings, store: StateStore
    ) -> None:
        source = BrokenSource(FIXTURE_DIR, broken={"filings"}, budget=25)
        report = build_pipeline(settings, store, source=source).run(notify=False)
        assert report.status is RunStatus.PARTIAL
        assert any(d.symbol == "FLMC" for d in report.queue)
        assert not any(d.symbol == "ADRO" for d in report.queue)

    def test_total_discovery_failure_is_never_an_all_clear(
        self, settings: Settings, store: StateStore
    ) -> None:
        source = BrokenSource(FIXTURE_DIR, broken={"filings", "suspensions", "movers"}, budget=25)
        report = build_pipeline(settings, store, source=source).run(notify=False)
        assert report.status is RunStatus.FAILED
        assert report.queue == []
        assert any("NOT an all-clear" in w for w in report.warnings)

    def test_failed_source_names_itself_in_the_report(
        self, settings: Settings, store: StateStore
    ) -> None:
        source = BrokenSource(FIXTURE_DIR, broken={"foreign_flow"}, budget=25)
        report = build_pipeline(settings, store, source=source).run(notify=False)
        flow = next(s for s in report.sources if s.name is SourceName.FOREIGN_FLOW)
        assert flow.state is SourceState.FAILED
        assert flow.error

    def test_one_bad_ticker_does_not_stop_the_others(
        self, settings: Settings, store: StateStore
    ) -> None:
        class OneBadTicker(FixtureSource):
            def fetch_foreign_flow(self, symbol: str, start: date, end: date) -> dict[str, Any]:
                if symbol == "ANTM":
                    raise httpx.ConnectError("just this one")
                return super().fetch_foreign_flow(symbol, start, end)

        source = OneBadTicker(FIXTURE_DIR, budget=25)
        report = build_pipeline(settings, store, source=source).run(notify=False)
        flow = next(s for s in report.sources if s.name is SourceName.FOREIGN_FLOW)
        assert flow.state is SourceState.OK
        assert flow.error is not None and "ANTM" in flow.error
        assert any(d.symbol == "MDKA" and d.score.total == 50 for d in report.queue)


class TestCreditBudgetEnforcement:
    def test_a_tight_budget_stops_enrichment_and_reports_it(
        self, settings: Settings, store: StateStore
    ) -> None:
        tight = settings.model_copy(update={"max_api_credits_per_run": 6})
        source = FixtureSource(FIXTURE_DIR, budget=6)
        report = build_pipeline(tight, store, source=source).run(notify=False)
        assert report.estimated_api_credits <= 6
        assert report.status is RunStatus.PARTIAL
        assert any(s.state is SourceState.BUDGET_EXHAUSTED for s in report.sources)
        assert any("budget" in w.lower() for w in report.warnings)

    def test_discovery_still_completes_under_a_tight_budget(
        self, settings: Settings, store: StateStore
    ) -> None:
        """Discovery is what finds the suspension; it must never be starved."""
        tight = settings.model_copy(update={"max_api_credits_per_run": 5})
        source = FixtureSource(FIXTURE_DIR, budget=5)
        report = build_pipeline(tight, store, source=source).run(notify=False)
        assert any(d.symbol == "FLMC" and d.score.total == 100 for d in report.queue)

    def test_no_usable_discovery_is_failed_not_an_all_clear(
        self, settings: Settings, store: StateStore
    ) -> None:
        source = FixtureSource(FIXTURE_DIR, budget=1)
        source.ledger.charge("prior-work", 1)
        tight = settings.model_copy(update={"max_api_credits_per_run": 1})
        report = build_pipeline(tight, store, source=source).run(notify=False)
        assert report.status is RunStatus.FAILED
        assert report.queue == []
        assert any("NOT an all-clear" in warning for warning in report.warnings)

    def test_zero_enrichment_tickers_skips_paid_enrichment(
        self, settings: Settings, store: StateStore
    ) -> None:
        frugal = settings.model_copy(update={"max_enrich_tickers": 0})
        report = build_pipeline(frugal, store).run(notify=False)
        flow = next(s for s in report.sources if s.name is SourceName.FOREIGN_FLOW)
        assert flow.state is SourceState.SKIPPED
        assert report.enriched_tickers == 0


class TestLiveMode:
    @staticmethod
    def _mock_all() -> None:
        respx.get(f"{BASE}/v2/filings/").mock(
            return_value=httpx.Response(200, json=load_fixture("filings"))
        )
        respx.get(f"{BASE}/v2/suspensions/").mock(
            return_value=httpx.Response(200, json=load_fixture("suspensions"))
        )
        respx.get(f"{BASE}/v2/companies/top-changes/").mock(
            return_value=httpx.Response(200, json=load_fixture("movers"))
        )
        respx.get(f"{BASE}/v2/news/").mock(
            return_value=httpx.Response(200, json=load_fixture("news"))
        )
        flows = load_fixture("foreign_flow")
        actions = load_fixture("corporate_actions")
        for symbol, payload in flows.items():
            if symbol.startswith("_"):
                continue
            respx.get(f"{BASE}/v2/foreign-flow/{symbol}/").mock(
                return_value=httpx.Response(200, json=payload)
            )
        for symbol, payload in actions.items():
            if symbol.startswith("_"):
                continue
            respx.get(f"{BASE}/v2/company/corporate-actions/{symbol}/").mock(
                return_value=httpx.Response(200, json=payload)
            )

    @respx.mock
    def test_live_run_over_http_produces_the_same_queue(
        self, settings: Settings, store: StateStore
    ) -> None:
        self._mock_all()
        client = SectorsClient(settings)
        try:
            report = build_pipeline(settings, store, source=client, mode=RunMode.LIVE).run(
                notify=False
            )
        finally:
            client.close()
        assert report.status is RunStatus.OK
        assert [(d.symbol, d.score.total) for d in report.queue] == [
            (s, v) for s, v, _ in EXPECTED_QUEUE
        ]

    @respx.mock
    def test_live_run_credit_arithmetic(self, settings: Settings, store: StateStore) -> None:
        """4 discovery (1 filings + 1 suspensions + 2 movers) + 1 news
        + 2 per enriched ticker."""
        self._mock_all()
        client = SectorsClient(settings)
        try:
            report = build_pipeline(settings, store, source=client, mode=RunMode.LIVE).run(
                notify=False
            )
        finally:
            client.close()
        assert report.estimated_api_credits == 5 + (2 * 5)

    @respx.mock
    def test_live_run_survives_a_flapping_endpoint(
        self, settings: Settings, store: StateStore
    ) -> None:
        self._mock_all()
        respx.get(f"{BASE}/v2/filings/").mock(
            side_effect=[
                httpx.Response(429),
                httpx.Response(200, json=load_fixture("filings")),
            ]
        )
        client = SectorsClient(settings)
        try:
            report = build_pipeline(settings, store, source=client, mode=RunMode.LIVE).run(
                notify=False
            )
        finally:
            client.close()
        assert report.status is RunStatus.OK
        assert any(d.symbol == "ANTM" for d in report.queue)

    @respx.mock
    def test_live_run_marks_a_dead_endpoint_partial(
        self, settings: Settings, store: StateStore
    ) -> None:
        self._mock_all()
        respx.get(f"{BASE}/v2/foreign-flow/MDKA/").mock(return_value=httpx.Response(500))
        client = SectorsClient(settings)
        try:
            report = build_pipeline(settings, store, source=client, mode=RunMode.LIVE).run(
                notify=False
            )
        finally:
            client.close()
        assert report.status is RunStatus.PARTIAL
        mdka = next(d for d in report.queue if d.symbol == "MDKA")
        assert mdka.score.total == 30  # 50 minus the 20-point flow anomaly


class TestExecuteEntryPoint:
    def test_execute_writes_every_artifact(self, settings: Settings, tmp_path: Path) -> None:
        report = execute(
            settings=settings,
            mode=RunMode.FIXTURE,
            trigger="schedule",
            notify=False,
            clock=lambda: CLOCK,
        )
        artifacts = Path(settings.artifact_dir)
        assert (artifacts / f"{report.run_id}.json").exists()
        assert (artifacts / f"{report.run_id}.html").exists()
        assert (artifacts / f"{report.run_id}-summary.md").exists()
        assert (artifacts / "latest.json").exists()
        assert (artifacts / "latest.html").exists()
        assert (artifacts / "run-history.json").exists()

    def test_execute_records_the_run_in_state(self, settings: Settings) -> None:
        report = execute(settings=settings, mode=RunMode.FIXTURE, notify=False, clock=lambda: CLOCK)
        store = StateStore(settings.db_path)
        try:
            assert store.run_count() == 1
            loaded = store.latest_report()
            assert loaded is not None
            assert loaded.run_id == report.run_id
        finally:
            store.close()

    def test_dry_notify_writes_a_preview_without_sending(self, settings: Settings) -> None:
        report = execute(
            settings=settings, mode=RunMode.FIXTURE, dry_notify=True, clock=lambda: CLOCK
        )
        preview = Path(settings.artifact_dir) / f"{report.run_id}-notification-preview.json"
        assert preview.exists()
        assert report.notifications_sent == 0
        assert report.notification_previews == len(report.queue)


class TestRunIdentity:
    def test_run_ids_are_sortable_and_unique(self) -> None:
        first = make_run_id(CLOCK)
        second = make_run_id(CLOCK)
        assert first.startswith("run-20260826-071700-")
        assert first != second
