"""Persistent state: the reason MarketOps does not shout the same news twice.

A scheduled job that re-reads a rolling window of market data will see the
same filing on Monday, Tuesday and Wednesday. Without memory it would alert an
analyst three times, and they would mute it. This module is that memory.

Three tables, one SQLite file:

``events``
    Every fingerprint ever observed, with the run that first saw it. Presence
    here is what makes an event a duplicate.
``alerts``
    Which dossiers were actually notified, on which channel. Lets the audit
    trail answer "did we tell anyone about this?" independently of "did we see
    this?".
``runs``
    One row per pipeline execution with its counters and the full report JSON,
    so the dashboard and the unattended-run evidence pack read from the same
    source of truth the notifier used.

SQLite is chosen deliberately: the state must survive process restarts and be
committed-adjacent (a single file the CI job can cache and an operator can
inspect with any SQLite browser) without standing up a server for a job that
runs once a day.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Any, Self

from .models import MarketEvent, RunReport, TickerDossier

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    event_id        TEXT PRIMARY KEY,
    event_type      TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    occurred_at     TEXT,
    headline        TEXT NOT NULL,
    source_ref      TEXT,
    source_url      TEXT,
    payload         TEXT NOT NULL DEFAULT '{}',
    first_seen_run  TEXT NOT NULL,
    first_seen_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol);
CREATE INDEX IF NOT EXISTS idx_events_run    ON events(first_seen_run);

CREATE TABLE IF NOT EXISTS alerts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT NOT NULL,
    symbol     TEXT NOT NULL,
    priority   TEXT NOT NULL,
    score      INTEGER NOT NULL,
    channel    TEXT NOT NULL,
    event_ids  TEXT NOT NULL,
    sent_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_alerts_symbol ON alerts(symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_run    ON alerts(run_id);

CREATE TABLE IF NOT EXISTS runs (
    run_id                      TEXT PRIMARY KEY,
    mode                        TEXT NOT NULL,
    status                      TEXT NOT NULL,
    trigger                     TEXT NOT NULL DEFAULT 'manual',
    started_at                  TEXT NOT NULL,
    finished_at                 TEXT,
    events_detected             INTEGER NOT NULL DEFAULT 0,
    new_events                  INTEGER NOT NULL DEFAULT 0,
    duplicate_events_suppressed INTEGER NOT NULL DEFAULT 0,
    candidates                  INTEGER NOT NULL DEFAULT 0,
    notifications_sent          INTEGER NOT NULL DEFAULT 0,
    estimated_api_credits       INTEGER NOT NULL DEFAULT 0,
    report_json                 TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at DESC);
"""


class StateStore:
    """SQLite-backed run state. Safe to open and close per run."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._migrate()

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _migrate(self) -> None:
        with self._tx() as conn:
            conn.executescript(_SCHEMA)
            conn.execute(
                "INSERT INTO schema_meta(key, value) VALUES('version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )

    # -- deduplication ------------------------------------------------------
    def known_event_ids(self, event_ids: Iterable[str]) -> set[str]:
        """Which of these fingerprints has this store already seen?"""
        ids = list(dict.fromkeys(event_ids))
        if not ids:
            return set()
        found: set[str] = set()
        # Chunked to stay clear of SQLite's variable limit on large windows.
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            placeholders = ",".join("?" * len(chunk))
            rows = self._conn.execute(
                f"SELECT event_id FROM events WHERE event_id IN ({placeholders})",  # noqa: S608
                chunk,
            ).fetchall()
            found.update(str(row["event_id"]) for row in rows)
        return found

    def partition_events(
        self, events: list[MarketEvent]
    ) -> tuple[list[MarketEvent], list[MarketEvent]]:
        """Split into (never-seen-before, already-known)."""
        known = self.known_event_ids(e.event_id for e in events)
        fresh = [e for e in events if e.event_id not in known]
        dupes = [e for e in events if e.event_id in known]
        return fresh, dupes

    def record_events(self, events: list[MarketEvent], run_id: str, seen_at: datetime) -> int:
        """Persist newly observed events. Returns the number actually inserted.

        ``INSERT OR IGNORE`` makes this idempotent: re-running the same batch
        cannot corrupt first-seen provenance, which is what the dashboard uses
        to say when an event entered the system.
        """
        return len(self.claim_events(events, run_id, seen_at))

    def claim_events(
        self, events: list[MarketEvent], run_id: str, seen_at: datetime
    ) -> list[MarketEvent]:
        """Atomically persist and return the evidence claimed by this run.

        A scheduler normally serializes runs, but the state layer must remain
        correct if an operator starts a manual run at the same time. Splitting
        the known-event read from insertion creates a race where both processes
        can classify one event as fresh. SQLite's unique index and this single
        transaction make the write itself the claim.
        """
        if not events:
            return []
        unique_events = list({event.event_id: event for event in events}.values())
        stamp = seen_at.isoformat()
        claimed: list[MarketEvent] = []
        with self._tx() as conn:
            for event in unique_events:
                cursor = conn.execute(
                    "INSERT OR IGNORE INTO events (event_id, event_type, symbol, occurred_at, "
                    "headline, source_ref, source_url, payload, first_seen_run, first_seen_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        event.event_id,
                        str(event.event_type),
                        event.symbol,
                        event.occurred_at.isoformat() if event.occurred_at else None,
                        event.headline,
                        event.source_ref,
                        event.source_url,
                        json.dumps(event.payload, default=str, sort_keys=True),
                        run_id,
                        stamp,
                    ),
                )
                if cursor.rowcount:
                    claimed.append(event)
        return claimed

    # -- alerts -------------------------------------------------------------
    def record_alert(
        self,
        run_id: str,
        dossier: TickerDossier,
        channel: str,
        sent_at: datetime,
    ) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO alerts (run_id, symbol, priority, score, channel, event_ids, sent_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    run_id,
                    dossier.symbol,
                    str(dossier.score.priority),
                    dossier.score.total,
                    channel,
                    json.dumps([e.event_id for e in dossier.events]),
                    sent_at.isoformat(),
                ),
            )

    def alert_count(self, symbol: str | None = None) -> int:
        if symbol:
            row = self._conn.execute(
                "SELECT COUNT(*) AS n FROM alerts WHERE symbol = ?", (symbol,)
            ).fetchone()
        else:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM alerts").fetchone()
        return int(row["n"]) if row else 0

    def alerted_event_ids(self, event_ids: Iterable[str]) -> set[str]:
        """Return event fingerprints that have reached at least one sink.

        ``alerts.event_ids`` is intentionally stored as a JSON array because
        one correlated card represents several source events.  The alert table
        stays tiny for a daily research workflow, so parsing those audit rows
        in Python is clearer and more portable than depending on SQLite's
        optional JSON1 extension.
        """
        wanted = set(event_ids)
        if not wanted:
            return set()
        delivered: set[str] = set()
        rows = self._conn.execute("SELECT event_ids FROM alerts").fetchall()
        for row in rows:
            try:
                recorded = json.loads(str(row["event_ids"]))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if isinstance(recorded, list):
                delivered.update(str(event_id) for event_id in recorded if event_id in wanted)
        return delivered

    # -- runs ---------------------------------------------------------------
    def record_run(self, report: RunReport) -> None:
        with self._tx() as conn:
            conn.execute(
                "INSERT INTO runs (run_id, mode, status, trigger, started_at, finished_at, "
                "events_detected, new_events, duplicate_events_suppressed, candidates, "
                "notifications_sent, estimated_api_credits, report_json) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(run_id) DO UPDATE SET "
                "status=excluded.status, finished_at=excluded.finished_at, "
                "events_detected=excluded.events_detected, new_events=excluded.new_events, "
                "duplicate_events_suppressed=excluded.duplicate_events_suppressed, "
                "candidates=excluded.candidates, "
                "notifications_sent=excluded.notifications_sent, "
                "estimated_api_credits=excluded.estimated_api_credits, "
                "report_json=excluded.report_json",
                (
                    report.run_id,
                    str(report.mode),
                    str(report.status),
                    report.trigger,
                    report.started_at.isoformat(),
                    report.finished_at.isoformat() if report.finished_at else None,
                    report.events_detected,
                    report.new_events,
                    report.duplicate_events_suppressed,
                    report.candidates,
                    report.notifications_sent,
                    report.estimated_api_credits,
                    report.model_dump_json(),
                ),
            )

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT run_id, mode, status, trigger, started_at, finished_at, events_detected, "
            "new_events, duplicate_events_suppressed, candidates, notifications_sent, "
            "estimated_api_credits FROM runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def latest_report(self) -> RunReport | None:
        """Rehydrate the most recent run's full report, if any."""
        row = self._conn.execute(
            "SELECT report_json FROM runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        if not row or not row["report_json"]:
            return None
        try:
            return RunReport.model_validate_json(str(row["report_json"]))
        except ValueError:
            return None

    def run_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()
        return int(row["n"]) if row else 0

    def event_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()
        return int(row["n"]) if row else 0

    def is_writable(self) -> bool:
        """Prove the database really accepts writes - used by ``doctor``."""
        try:
            with self._tx() as conn:
                conn.execute(
                    "INSERT INTO schema_meta(key, value) VALUES('healthcheck', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (datetime.now().astimezone().isoformat(),),
                )
            return True
        except sqlite3.Error:
            return False
