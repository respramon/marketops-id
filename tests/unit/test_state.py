"""Persistent state and the deduplication contract.

The product promise is "we will not tell you the same thing twice". These tests
are that promise, written down.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from tests.conftest import filing_event, news_event, price_event, suspension_event

from marketops.models import (
    WIB,
    EventType,
    MarketEvent,
    Priority,
    RunMode,
    RunReport,
    RunStatus,
    ScoreBreakdown,
    ScoreComponent,
    TickerDossier,
)
from marketops.state import StateStore


def _dossier(symbol: str = "ANTM", score: int = 75) -> TickerDossier:
    return TickerDossier(
        symbol=symbol,
        events=[filing_event(symbol, pct=1.0, value=1.0)],
        score=ScoreBreakdown(
            total=score,
            priority=Priority.P1,
            components=[ScoreComponent(label="filing", points=score, evidence="test")],
        ),
    )


def _report(run_id: str = "run-test-1", **kw: object) -> RunReport:
    defaults: dict[str, object] = {
        "run_id": run_id,
        "mode": RunMode.FIXTURE,
        "status": RunStatus.OK,
        "started_at": datetime(2026, 8, 26, 7, 17, tzinfo=WIB),
        "finished_at": datetime(2026, 8, 26, 7, 17, 4, tzinfo=WIB),
        "trigger": "schedule",
    }
    defaults.update(kw)
    return RunReport(**defaults)  # type: ignore[arg-type]


class TestEventDeduplication:
    def test_a_fresh_store_knows_nothing(self, store: StateStore) -> None:
        assert store.known_event_ids(["a", "b"]) == set()

    def test_recorded_events_become_known(self, store: StateStore) -> None:
        events = [filing_event("ANTM", pct=1.0, value=1.0), price_event("MDKA", pct=8.0)]
        store.record_events(events, "run-1", datetime.now(tz=WIB))
        known = store.known_event_ids(e.event_id for e in events)
        assert known == {e.event_id for e in events}

    def test_partition_splits_new_from_seen(self, store: StateStore) -> None:
        first = filing_event("ANTM", pct=1.0, value=1.0)
        store.record_events([first], "run-1", datetime.now(tz=WIB))
        second = price_event("MDKA", pct=8.0)
        fresh, dupes = store.partition_events([first, second])
        assert [e.symbol for e in fresh] == ["MDKA"]
        assert [e.symbol for e in dupes] == ["ANTM"]

    def test_identical_replay_yields_zero_new_events(self, store: StateStore) -> None:
        """The headline dedup guarantee: replaying the same day is silent."""
        batch = [
            filing_event("ANTM", pct=1.85, value=412_000_000_000),
            suspension_event("FLMC"),
            news_event("MDKA"),
        ]
        first_new, first_dupes = store.partition_events(batch)
        store.record_events(first_new, "run-1", datetime.now(tz=WIB))
        assert len(first_new) == 3
        assert first_dupes == []

        second_new, second_dupes = store.partition_events(batch)
        assert second_new == []
        assert len(second_dupes) == 3

    def test_a_different_source_reference_is_a_different_event(self, store: StateStore) -> None:
        a = filing_event("ANTM", pct=1.0, value=1.0, source_ref="http://idx/a.pdf")
        b = filing_event("ANTM", pct=1.0, value=1.0, source_ref="http://idx/b.pdf")
        store.record_events([a], "run-1", datetime.now(tz=WIB))
        fresh, _ = store.partition_events([a, b])
        assert [e.event_id for e in fresh] == [b.event_id]

    def test_a_different_timestamp_is_a_different_event(self, store: StateStore) -> None:
        monday = filing_event("ANTM", pct=1.0, value=1.0, when=datetime(2026, 8, 24, tzinfo=WIB))
        tuesday = filing_event("ANTM", pct=1.0, value=1.0, when=datetime(2026, 8, 25, tzinfo=WIB))
        store.record_events([monday], "run-1", datetime.now(tz=WIB))
        fresh, _ = store.partition_events([monday, tuesday])
        assert len(fresh) == 1

    def test_recording_is_idempotent(self, store: StateStore) -> None:
        event = filing_event("ANTM", pct=1.0, value=1.0)
        inserted_first = store.record_events([event], "run-1", datetime.now(tz=WIB))
        inserted_again = store.record_events([event], "run-2", datetime.now(tz=WIB))
        assert inserted_first == 1
        assert inserted_again == 0
        assert store.event_count() == 1

    def test_atomic_claim_has_one_winner_across_store_instances(self, tmp_path: Path) -> None:
        """The insert, not a prior read, decides which concurrent run is fresh."""
        db = tmp_path / "shared.db"
        first = StateStore(db)
        second = StateStore(db)
        event = filing_event("ANTM", pct=1.0, value=1.0)
        try:
            claimed_first = first.claim_events([event], "run-1", datetime.now(tz=WIB))
            claimed_second = second.claim_events([event], "run-2", datetime.now(tz=WIB))
        finally:
            first.close()
            second.close()
        assert claimed_first == [event]
        assert claimed_second == []

    def test_first_seen_provenance_is_not_overwritten(self, store: StateStore) -> None:
        event = filing_event("ANTM", pct=1.0, value=1.0)
        store.record_events([event], "run-original", datetime.now(tz=WIB))
        store.record_events([event], "run-later", datetime.now(tz=WIB))
        row = store._conn.execute(
            "SELECT first_seen_run FROM events WHERE event_id = ?", (event.event_id,)
        ).fetchone()
        assert row["first_seen_run"] == "run-original"

    def test_empty_batches_are_safe(self, store: StateStore) -> None:
        assert store.record_events([], "run-1", datetime.now(tz=WIB)) == 0
        assert store.partition_events([]) == ([], [])

    def test_large_batches_exceed_no_sqlite_variable_limit(self, store: StateStore) -> None:
        """Chunking guard: a 90-day backfill must not blow the IN() limit."""
        events = [
            MarketEvent.build(
                event_type=EventType.NEWS,
                symbol="TEST",
                occurred_at=None,
                headline=f"story {i}",
                source_ref=f"ref-{i}",
            )
            for i in range(1500)
        ]
        store.record_events(events, "run-big", datetime.now(tz=WIB))
        assert len(store.known_event_ids(e.event_id for e in events)) == 1500


class TestRestartSurvival:
    def test_state_survives_a_process_restart(self, tmp_path: Path) -> None:
        db = tmp_path / "persist.db"
        event = filing_event("ANTM", pct=1.0, value=1.0)

        first = StateStore(db)
        first.record_events([event], "run-1", datetime.now(tz=WIB))
        first.close()

        second = StateStore(db)
        try:
            assert second.known_event_ids([event.event_id]) == {event.event_id}
            fresh, dupes = second.partition_events([event])
            assert fresh == []
            assert len(dupes) == 1
        finally:
            second.close()

    def test_run_history_survives_a_restart(self, tmp_path: Path) -> None:
        db = tmp_path / "persist.db"
        first = StateStore(db)
        first.record_run(_report("run-a", events_detected=16, new_events=16))
        first.close()

        second = StateStore(db)
        try:
            assert second.run_count() == 1
            report = second.latest_report()
            assert report is not None
            assert report.run_id == "run-a"
            assert report.events_detected == 16
        finally:
            second.close()

    def test_missing_parent_directory_is_created(self, tmp_path: Path) -> None:
        store = StateStore(tmp_path / "nested" / "deep" / "state.db")
        try:
            assert store.is_writable()
        finally:
            store.close()


class TestAlerts:
    def test_alerts_are_recorded_with_their_channel(self, store: StateStore) -> None:
        store.record_alert("run-1", _dossier(), "discord", datetime.now(tz=WIB))
        assert store.alert_count() == 1
        assert store.alert_count("ANTM") == 1
        assert store.alert_count("BBCA") == 0

    def test_alert_history_is_independent_of_event_history(self, store: StateStore) -> None:
        """Seeing an event and telling someone about it are different facts."""
        store.record_events([filing_event("ANTM", pct=1.0, value=1.0)], "r", datetime.now(tz=WIB))
        assert store.event_count() == 1
        assert store.alert_count() == 0


class TestRunRecords:
    def test_runs_are_stored_and_listed_newest_first(self, store: StateStore) -> None:
        store.record_run(_report("run-old", started_at=datetime(2026, 8, 24, 7, 17, tzinfo=WIB)))
        store.record_run(_report("run-new", started_at=datetime(2026, 8, 26, 7, 17, tzinfo=WIB)))
        rows = store.recent_runs()
        assert [r["run_id"] for r in rows] == ["run-new", "run-old"]

    def test_recording_the_same_run_twice_updates_it(self, store: StateStore) -> None:
        store.record_run(_report("run-1", status=RunStatus.OK, notifications_sent=0))
        store.record_run(_report("run-1", status=RunStatus.PARTIAL, notifications_sent=5))
        assert store.run_count() == 1
        rows = store.recent_runs()
        assert rows[0]["status"] == "PARTIAL"
        assert rows[0]["notifications_sent"] == 5

    def test_latest_report_round_trips_full_fidelity(self, store: StateStore) -> None:
        report = _report("run-1", dossiers=[_dossier()], warnings=["something degraded"])
        store.record_run(report)
        loaded = store.latest_report()
        assert loaded is not None
        assert loaded.warnings == ["something degraded"]
        assert loaded.dossiers[0].symbol == "ANTM"
        assert loaded.dossiers[0].score.total == 75

    def test_latest_report_of_an_empty_store(self, store: StateStore) -> None:
        assert store.latest_report() is None

    def test_corrupt_report_json_does_not_crash_the_dashboard(self, store: StateStore) -> None:
        store.record_run(_report("run-1"))
        store._conn.execute(
            "UPDATE runs SET report_json = ? WHERE run_id = ?", ("{not json", "run-1")
        )
        store._conn.commit()
        assert store.latest_report() is None

    def test_writability_probe(self, store: StateStore) -> None:
        assert store.is_writable() is True

    def test_context_manager_closes_cleanly(self, tmp_path: Path) -> None:
        with StateStore(tmp_path / "ctx.db") as state:
            assert state.run_count() == 0
        with pytest.raises(Exception, match="closed"):
            state.run_count()
