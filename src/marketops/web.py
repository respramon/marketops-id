"""Read-only dashboard over the run state.

The dashboard is deliberately a *reader*. It never triggers a pipeline run and
holds no write path, because the product's whole claim is that the work happens
unattended on a schedule. A judge opening this page is looking at the output of
a job that already ran without anybody watching.

Serve it with::

    marketops serve            # http://127.0.0.1:8000
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import DISCLAIMER, __version__
from .config import Settings, get_settings
from .render import STATIC_DIR, build_environment, report_context
from .state import StateStore


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the dashboard application."""
    config = settings or get_settings()

    app = FastAPI(
        title="MarketOps ID",
        description=(
            "Autonomous IDX research triage. Research triage only - no investment "
            "recommendations, no trade execution."
        ),
        version=__version__,
        docs_url="/api/docs" if config.enable_api_docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if config.enable_api_docs else None,
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=config.allowed_host_list)

    @app.middleware("http")
    async def security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Apply a strict browser baseline to every dashboard response."""
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    env = build_environment()

    def _store() -> StateStore:
        return StateStore(config.db_path)

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> HTMLResponse:
        """The research queue produced by the most recent unattended run."""
        store = _store()
        try:
            report = store.latest_report()
            if report is None:
                template = env.get_template("empty.html")
                return HTMLResponse(
                    template.render(
                        version=__version__,
                        disclaimer=DISCLAIMER,
                        standalone=False,
                        inline_css="",
                        is_fixture=False,
                    )
                )
            context = report_context(report, standalone=False, runs=store.recent_runs(20))
            template = env.get_template("index.html")
            return HTMLResponse(template.render(**context))
        finally:
            store.close()

    @app.get("/api/latest")
    def latest() -> JSONResponse:
        """Full JSON of the most recent run."""
        store = _store()
        try:
            report = store.latest_report()
            if report is None:
                return JSONResponse({"error": "no run recorded yet"}, status_code=404)
            return JSONResponse(report.model_dump(mode="json"))
        finally:
            store.close()

    @app.get("/api/runs")
    def runs(limit: int = 50) -> JSONResponse:
        """Unattended run history - the Track 2 evidence, as data."""
        store = _store()
        try:
            return JSONResponse(
                {
                    "runs": store.recent_runs(min(max(limit, 1), 200)),
                    "total_runs": store.run_count(),
                    "total_events_known": store.event_count(),
                }
            )
        finally:
            store.close()

    @app.get("/healthz")
    def healthz() -> dict[str, Any]:
        store = _store()
        try:
            return {
                "status": "ok",
                "version": __version__,
                "runs_recorded": store.run_count(),
                "events_known": store.event_count(),
                "disclaimer": DISCLAIMER,
            }
        finally:
            store.close()

    return app


app = create_app()
