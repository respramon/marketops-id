"""Notification delivery.

Three properties are non-negotiable:

* only genuinely new evidence is notified (the dedup promise),
* a webhook failure degrades the run, it never throws the queue away, and
* a webhook URL is a secret and never appears in a payload, log or error.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import respx
from tests.conftest import filing_event, price_event, suspension_event

from marketops.config import Settings
from marketops.models import (
    WIB,
    Priority,
    RunMode,
    RunReport,
    RunStatus,
    ScoreBreakdown,
    ScoreComponent,
    TickerDossier,
)
from marketops.notify import (
    build_discord_payload,
    build_generic_payload,
    dispatch,
    notifiable,
)

HOOK = "https://discord.com/api/webhooks/1234567890/super-secret-token-value"


def _dossier(
    symbol: str = "ANTM",
    score: int = 75,
    priority: Priority = Priority.P1,
    *,
    is_new: bool = True,
) -> TickerDossier:
    events = [filing_event(symbol, pct=1.85, value=412_000_000_000), price_event(symbol, pct=8.42)]
    event_ids = [event.event_id for event in events]
    return TickerDossier(
        symbol=symbol,
        company_name=f"PT {symbol} Tbk",
        events=events,
        score=ScoreBreakdown(
            total=score,
            priority=priority,
            components=[
                ScoreComponent(label="Insider filing", points=25, evidence="Dana Nusantara"),
                ScoreComponent(label="Large one-day price move", points=20, evidence="8.42%"),
            ],
        ),
        new_event_ids=event_ids if is_new else [],
        pending_alert_event_ids=event_ids if is_new else [],
    )


def _report(dossiers: list[TickerDossier], **kw: Any) -> RunReport:
    base: dict[str, Any] = {
        "run_id": "run-20260826-071700-abc123",
        "mode": RunMode.FIXTURE,
        "status": RunStatus.OK,
        "started_at": datetime(2026, 8, 26, 7, 17, tzinfo=WIB),
        "trigger": "schedule",
        "dossiers": dossiers,
        "events_detected": 16,
        "new_events": 16,
        "candidates": 7,
        "estimated_api_credits": 15,
        "credit_budget": 25,
    }
    base.update(kw)
    return RunReport(**base)


class TestNotifiableGate:
    def test_only_dossiers_with_pending_delivery_are_notified(self) -> None:
        report = _report(
            [_dossier("ANTM", is_new=True), _dossier("MDKA", 50, Priority.P2, is_new=False)]
        )
        assert [d.symbol for d in notifiable(report)] == ["ANTM"]

    def test_below_threshold_dossiers_are_never_notified(self) -> None:
        quiet = _dossier("NOISE", 5, Priority.NONE, is_new=True)
        assert notifiable(_report([quiet])) == []

    def test_nothing_pending_means_nothing_sent(self) -> None:
        report = _report([_dossier("ANTM", is_new=False)])
        assert notifiable(report) == []


class TestDiscordPayload:
    def test_one_embed_per_dossier(self) -> None:
        report = _report([_dossier("ANTM"), _dossier("MDKA", 50, Priority.P2)])
        payload = build_discord_payload(report, notifiable(report))
        assert len(payload["embeds"]) == 2

    def test_embed_carries_the_score_breakdown(self) -> None:
        report = _report([_dossier()])
        payload = build_discord_payload(report, notifiable(report))
        body = payload["embeds"][0]["description"]
        assert "75/100" in body
        assert "Why surfaced" in body
        assert "Insider filing" in body
        assert "+25" in body

    def test_priority_colour_is_semantic(self) -> None:
        p1 = build_discord_payload(_report([_dossier()]), [_dossier()])
        p3 = build_discord_payload(
            _report([_dossier("X", 25, Priority.P3)]), [_dossier("X", 25, Priority.P3)]
        )
        assert p1["embeds"][0]["color"] != p3["embeds"][0]["color"]

    def test_disclaimer_is_on_every_card(self) -> None:
        report = _report([_dossier()])
        payload = build_discord_payload(report, notifiable(report))
        assert (
            "does not provide investment recommendations" in payload["embeds"][0]["footer"]["text"]
        )

    def test_fixture_mode_is_flagged_in_the_message(self) -> None:
        payload = build_discord_payload(_report([_dossier()]), [_dossier()])
        assert "SANITIZED HISTORICAL REPLAY" in payload["content"]

    def test_live_mode_carries_no_replay_banner(self) -> None:
        report = _report([_dossier()], mode=RunMode.LIVE)
        payload = build_discord_payload(report, notifiable(report))
        assert "SANITIZED" not in payload["content"]

    def test_partial_run_warnings_reach_the_analyst(self) -> None:
        report = _report(
            [_dossier()], status=RunStatus.PARTIAL, warnings=["foreign_flow unavailable"]
        )
        payload = build_discord_payload(report, notifiable(report))
        assert "foreign_flow unavailable" in payload["content"]
        assert "PARTIAL" in payload["content"]

    def test_embed_count_never_exceeds_the_discord_limit(self) -> None:
        many = [_dossier(f"T{i:02d}") for i in range(25)]
        report = _report(many)
        payload = build_discord_payload(report, notifiable(report))
        assert len(payload["embeds"]) <= 10

    def test_overflow_tickers_are_still_named(self) -> None:
        many = [_dossier(f"T{i:02d}") for i in range(12)]
        report = _report(many)
        payload = build_discord_payload(report, notifiable(report))
        assert "Also in the queue" in payload["content"]

    def test_mentions_are_disabled(self) -> None:
        payload = build_discord_payload(_report([_dossier()]), [_dossier()])
        assert payload["allowed_mentions"] == {"parse": []}

    def test_content_stays_within_discord_limits(self) -> None:
        report = _report([_dossier(f"T{i:02d}") for i in range(12)])
        payload = build_discord_payload(report, notifiable(report))
        assert len(payload["content"]) <= 2000
        for embed in payload["embeds"]:
            assert len(embed["description"]) <= 4096
            assert len(embed["title"]) <= 256

    def test_suspension_override_reason_is_shown(self) -> None:
        events = [suspension_event("FLMC")]
        dossier = TickerDossier(
            symbol="FLMC",
            events=events,
            score=ScoreBreakdown(
                total=100,
                priority=Priority.P1,
                components=[ScoreComponent(label="IDX suspension", points=100, evidence="halt")],
                override_reason="Trading is halted.",
            ),
            new_event_ids=[events[0].event_id],
        )
        payload = build_discord_payload(_report([dossier]), [dossier])
        assert "Trading is halted." in payload["embeds"][0]["description"]


class TestGenericPayload:
    def test_shape_is_stable_and_documented(self) -> None:
        report = _report([_dossier()])
        payload = build_generic_payload(report, notifiable(report))
        assert set(payload) == {"product", "disclaimer", "run", "queue"}
        assert payload["run"]["run_id"] == "run-20260826-071700-abc123"
        entry = payload["queue"][0]
        assert entry["symbol"] == "ANTM"
        assert entry["display_symbol"] == "ANTM.JK"
        assert entry["score"] == 75
        assert entry["priority"] == "P1"
        assert entry["why_surfaced"]

    def test_events_carry_their_provenance(self) -> None:
        report = _report([_dossier()])
        payload = build_generic_payload(report, notifiable(report))
        event = payload["queue"][0]["events"][0]
        assert {"event_id", "type", "headline", "occurred_at", "source_url"} <= set(event)


class TestDispatch:
    @respx.mock
    def test_sends_to_discord_when_configured(self, settings: Settings) -> None:
        route = respx.post(HOOK).mock(return_value=httpx.Response(204))
        configured = settings.model_copy(update={"discord_webhook_url": _secret(HOOK)})
        report = _report([_dossier()])
        sent, channels, errors = dispatch(report, configured)
        assert sent == 1
        assert channels == ["discord"]
        assert errors == []
        assert route.call_count == 1

    @respx.mock
    def test_webhook_failure_is_reported_not_raised(self, settings: Settings) -> None:
        respx.post(HOOK).mock(return_value=httpx.Response(500))
        configured = settings.model_copy(update={"discord_webhook_url": _secret(HOOK)})
        sent, channels, errors = dispatch(_report([_dossier()]), configured)
        assert sent == 0
        assert channels == []
        assert errors and "500" in errors[0]

    @respx.mock
    def test_transport_failure_is_reported_not_raised(self, settings: Settings) -> None:
        respx.post(HOOK).mock(side_effect=httpx.ConnectError("no route"))
        configured = settings.model_copy(update={"discord_webhook_url": _secret(HOOK)})
        _sent, _channels, errors = dispatch(_report([_dossier()]), configured)
        assert errors and "transport" in errors[0]

    @respx.mock
    def test_the_secret_url_never_appears_in_an_error(self, settings: Settings) -> None:
        respx.post(HOOK).mock(return_value=httpx.Response(500))
        configured = settings.model_copy(update={"discord_webhook_url": _secret(HOOK)})
        _sent, _channels, errors = dispatch(_report([_dossier()]), configured)
        joined = " ".join(errors)
        assert "super-secret-token-value" not in joined
        assert "discord.com/api/webhooks" not in joined

    def test_no_webhook_configured_is_an_explicit_error(self, settings: Settings) -> None:
        sent, channels, errors = dispatch(_report([_dossier()]), settings)
        assert sent == 0
        assert channels == []
        assert errors and "no webhook configured" in errors[0]

    def test_nothing_new_sends_nothing_and_errors_nothing(self, settings: Settings) -> None:
        report = _report([_dossier(is_new=False)])
        sent, channels, errors = dispatch(report, settings)
        assert (sent, channels, errors) == (0, [], [])

    def test_dry_run_writes_a_preview_and_transmits_nothing(
        self, settings: Settings, tmp_path: Path
    ) -> None:
        with respx.mock:
            route = respx.post(HOOK)
            configured = settings.model_copy(update={"discord_webhook_url": _secret(HOOK)})
            report = _report([_dossier()])
            sent, channels, errors = dispatch(
                report, configured, dry_run=True, artifact_dir=tmp_path
            )
            assert route.call_count == 0
        assert sent == 0
        assert channels == ["dry-notify-preview"]
        assert errors == []
        preview = tmp_path / f"{report.run_id}-notification-preview.json"
        assert preview.exists()
        assert "discord" in preview.read_text(encoding="utf-8")

    def test_dry_run_does_not_preview_previously_seen_evidence(self, settings: Settings) -> None:
        report = _report([_dossier(is_new=False)])
        sent, channels, errors = dispatch(report, settings, dry_run=True)
        assert (sent, channels, errors) == (0, [], [])

    @respx.mock
    def test_generic_webhook_is_independent_of_discord(self, settings: Settings) -> None:
        generic = "https://n8n.example.test/webhook/marketops"
        respx.post(HOOK).mock(return_value=httpx.Response(500))
        route = respx.post(generic).mock(return_value=httpx.Response(200))
        configured = settings.model_copy(
            update={"discord_webhook_url": _secret(HOOK), "generic_webhook_url": _secret(generic)}
        )
        sent, channels, errors = dispatch(_report([_dossier()]), configured)
        assert route.call_count == 1
        assert channels == ["generic-webhook"]
        assert sent == 1
        assert len(errors) == 1


def _secret(value: str) -> Any:
    from pydantic import SecretStr

    return SecretStr(value)
