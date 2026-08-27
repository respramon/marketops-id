"""The read-only dashboard.

The dashboard is a reader, never a trigger. These tests assert both that it
renders the last unattended run correctly and that it exposes no write path
that would undermine the "this runs without a human" claim.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from marketops.config import Settings
from marketops.models import RunMode
from marketops.pipeline import execute
from marketops.web import create_app


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def client_with_run(settings: Settings) -> Iterator[TestClient]:
    execute(settings=settings, mode=RunMode.FIXTURE, trigger="schedule", notify=False)
    with TestClient(create_app(settings)) as test_client:
        yield test_client


class TestEmptyState:
    def test_dashboard_explains_itself_before_any_run(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert "No run recorded yet" in response.text
        assert "marketops run --mode fixture" in response.text

    def test_latest_api_is_a_clean_404(self, client: TestClient) -> None:
        response = client.get("/api/latest")
        assert response.status_code == 404
        assert response.json()["error"] == "no run recorded yet"

    def test_health_works_with_no_data(self, client: TestClient) -> None:
        payload = client.get("/healthz").json()
        assert payload["status"] == "ok"
        assert payload["runs_recorded"] == 0


class TestDashboard:
    def test_renders_the_research_queue(self, client_with_run: TestClient) -> None:
        response = client_with_run.get("/")
        assert response.status_code == 200
        for ticker in ("FLMC.JK", "ANTM.JK", "MDKA.JK"):
            assert ticker in response.text

    def test_shows_the_unattended_run_metadata(self, client_with_run: TestClient) -> None:
        text = client_with_run.get("/").text
        assert "Last run" in text
        assert "Notifications sent" in text
        assert "API credits" in text
        assert "schedule" in text

    def test_shows_the_replay_banner_for_fixture_data(self, client_with_run: TestClient) -> None:
        assert "SANITIZED HISTORICAL REPLAY" in client_with_run.get("/").text

    def test_disclaimer_banner_is_present(self, client_with_run: TestClient) -> None:
        assert "does not provide investment recommendations" in client_with_run.get("/").text

    def test_score_breakdown_is_visible(self, client_with_run: TestClient) -> None:
        text = client_with_run.get("/").text
        assert "Why surfaced" in text
        assert "Insider or major-shareholder filing" in text

    def test_source_provenance_links_are_present(self, client_with_run: TestClient) -> None:
        assert "idx.co.id" in client_with_run.get("/").text

    def test_run_history_table(self, client_with_run: TestClient) -> None:
        assert "Unattended run history" in client_with_run.get("/").text

    def test_no_template_syntax_leaks(self, client_with_run: TestClient) -> None:
        text = client_with_run.get("/").text
        assert "{{" not in text
        assert "{%" not in text


class TestApi:
    def test_latest_returns_the_full_report(self, client_with_run: TestClient) -> None:
        payload = client_with_run.get("/api/latest").json()
        assert payload["mode"] == "fixture"
        assert payload["trigger"] == "schedule"
        assert payload["events_detected"] > 0
        symbols = [d["symbol"] for d in payload["dossiers"]]
        assert "FLMC" in symbols

    def test_runs_endpoint_lists_history(self, client_with_run: TestClient) -> None:
        payload = client_with_run.get("/api/runs").json()
        assert payload["total_runs"] == 1
        assert payload["total_events_known"] > 0
        assert payload["runs"][0]["trigger"] == "schedule"

    def test_runs_limit_is_clamped(self, client_with_run: TestClient) -> None:
        assert client_with_run.get("/api/runs?limit=99999").status_code == 200
        assert client_with_run.get("/api/runs?limit=0").status_code == 200

    def test_health_reports_counts(self, client_with_run: TestClient) -> None:
        payload = client_with_run.get("/healthz").json()
        assert payload["runs_recorded"] == 1
        assert "disclaimer" in payload

    def test_interactive_api_docs_are_disabled_by_default(
        self, client_with_run: TestClient
    ) -> None:
        assert client_with_run.get("/api/docs").status_code == 404

    def test_security_headers_are_applied(self, client_with_run: TestClient) -> None:
        headers = client_with_run.get("/").headers
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert "script-src 'none'" in headers["content-security-policy"]
        assert headers["referrer-policy"] == "no-referrer"

    def test_untrusted_host_is_rejected(self, client_with_run: TestClient) -> None:
        response = client_with_run.get("/", headers={"host": "attacker.example"})
        assert response.status_code == 400


class TestReadOnly:
    def test_no_route_accepts_a_write_method(self, client_with_run: TestClient) -> None:
        """The pipeline is triggered by the scheduler, never by a page visit."""
        for path in ("/", "/api/latest", "/api/runs", "/healthz"):
            for method in ("post", "put", "delete", "patch"):
                response = getattr(client_with_run, method)(path)
                assert response.status_code in (404, 405), f"{method.upper()} {path}"

    def test_static_assets_are_served(self, client_with_run: TestClient) -> None:
        response = client_with_run.get("/static/styles.css")
        assert response.status_code == 200
        assert "--ink-900" in response.text
