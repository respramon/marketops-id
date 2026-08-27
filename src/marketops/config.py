"""Configuration loading: environment settings plus YAML scoring/watchlist rules.

Two distinct concerns live here:

* :class:`Settings` - operational environment (secrets, budgets, paths). Read
  from environment variables / ``.env``. Secrets are wrapped in ``SecretStr``
  so they cannot be printed by accident.
* :class:`ScoringConfig` / :class:`Watchlist` - product rules, read from YAML
  under ``config/``. These are deliberately data, not code, so an analyst can
  retune the triage without touching Python.
"""

from __future__ import annotations

from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Development uses the repository's human-editable assets. A built wheel has
# those same assets force-included under ``marketops/resources`` (see
# ``pyproject.toml``), so GitHub Actions can install the package normally and
# still execute from any working directory.
_SOURCE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = _SOURCE_ROOT if (_SOURCE_ROOT / "config").is_dir() else Path.cwd()


def asset_path(*parts: str) -> Path:
    """Locate a repository asset in source checkout or installed package.

    The top-level ``config/``, ``fixtures/``, ``templates/``, and ``static/``
    directories stay editable and visible to hackathon judges. Hatch force-
    includes them in the wheel so the production workflow does not accidentally
    depend on editable installation or a source checkout layout.
    """
    local = REPO_ROOT.joinpath(*parts)
    if local.exists():
        return local
    packaged = resources.files("marketops").joinpath("resources")
    for part in parts:
        packaged = packaged.joinpath(part)
    return Path(str(packaged))


DEFAULT_SCORING_PATH = asset_path("config", "scoring.yml")
DEFAULT_WATCHLIST_PATH = asset_path("config", "watchlist.yml")
DEFAULT_FIXTURE_DIR = asset_path("fixtures", "sanitized")

SECTORS_BASE_URL = "https://api.sectors.app"
"""Verified against https://docs.sectors.app/schema.json (OpenAPI 3.0.3, v2.0.0)."""


class Settings(BaseSettings):
    """Runtime environment for a MarketOps run."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Credentials (never logged) ---------------------------------------
    sectors_api_key: SecretStr | None = Field(default=None, validation_alias="SECTORS_API_KEY")
    discord_webhook_url: SecretStr | None = Field(
        default=None, validation_alias="DISCORD_WEBHOOK_URL"
    )
    generic_webhook_url: SecretStr | None = Field(
        default=None, validation_alias="GENERIC_WEBHOOK_URL"
    )

    # --- API credit discipline --------------------------------------------
    max_api_credits_per_run: int = Field(
        default=15, ge=1, validation_alias="MARKETOPS_MAX_API_CREDITS_PER_RUN"
    )
    max_enrich_tickers: int = Field(
        default=5, ge=0, validation_alias="MARKETOPS_MAX_ENRICH_TICKERS"
    )

    # --- Data window -------------------------------------------------------
    lookback_days: int = Field(default=3, ge=1, le=90, validation_alias="MARKETOPS_LOOKBACK_DAYS")
    foreign_flow_window_days: int = Field(
        default=14, ge=2, le=90, validation_alias="MARKETOPS_FOREIGN_FLOW_WINDOW_DAYS"
    )

    # --- Paths -------------------------------------------------------------
    db_path: Path = Field(default=Path("data/marketops.db"), validation_alias="MARKETOPS_DB_PATH")
    artifact_dir: Path = Field(default=Path("artifacts"), validation_alias="MARKETOPS_ARTIFACT_DIR")
    scoring_path: Path = Field(
        default=DEFAULT_SCORING_PATH, validation_alias="MARKETOPS_SCORING_PATH"
    )
    watchlist_path: Path = Field(
        default=DEFAULT_WATCHLIST_PATH, validation_alias="MARKETOPS_WATCHLIST_PATH"
    )
    fixture_dir: Path = Field(default=DEFAULT_FIXTURE_DIR, validation_alias="MARKETOPS_FIXTURE_DIR")

    # --- HTTP reliability ---------------------------------------------------
    http_timeout: float = Field(default=15.0, gt=0, validation_alias="MARKETOPS_HTTP_TIMEOUT")
    max_retries: int = Field(default=3, ge=0, le=10, validation_alias="MARKETOPS_MAX_RETRIES")
    max_concurrency: int = Field(
        default=3, ge=1, le=10, validation_alias="MARKETOPS_MAX_CONCURRENCY"
    )
    log_level: str = Field(default="INFO", validation_alias="MARKETOPS_LOG_LEVEL")

    # --- Read-only dashboard security -------------------------------------
    allowed_hosts: str = Field(
        default="localhost,127.0.0.1,testserver",
        validation_alias="MARKETOPS_ALLOWED_HOSTS",
    )
    enable_api_docs: bool = Field(
        default=False,
        validation_alias="MARKETOPS_ENABLE_API_DOCS",
    )

    @property
    def has_api_key(self) -> bool:
        """True when a non-empty Sectors API key is configured."""
        return bool(self.sectors_api_key and self.sectors_api_key.get_secret_value().strip())

    @property
    def has_any_webhook(self) -> bool:
        """True when at least one notification sink is configured."""
        return bool(self.discord_webhook_url or self.generic_webhook_url)

    @property
    def allowed_host_list(self) -> list[str]:
        """Validated Host allowlist for the read-only dashboard."""
        hosts = [host.strip() for host in self.allowed_hosts.split(",") if host.strip()]
        return hosts or ["localhost", "127.0.0.1", "testserver"]


class PriorityBands(BaseModel):
    """Score thresholds separating P1 / P2 / P3."""

    p1_min: int
    p2_min: int
    p3_min: int


class Thresholds(BaseModel):
    """Numeric constants the scoring weights compare against."""

    ownership_change_pct: float
    transaction_value_idr: float
    price_move_small_pct: float
    price_move_large_pct: float
    foreign_flow_ratio_small: float
    foreign_flow_ratio_large: float
    corporate_action_window_days: int
    foreign_flow_min_baseline_days: int


class CandidateSelection(BaseModel):
    """How the candidate universe is ordered before paid enrichment."""

    preliminary_weights: dict[str, int]
    skip_enrichment_when_score_pinned: bool = True


class ScoringConfig(BaseModel):
    """The full, data-driven Research Attention Score ruleset."""

    priority: PriorityBands
    weights: dict[str, dict[str, int]]
    limits: dict[str, int]
    thresholds: Thresholds
    candidate_selection: CandidateSelection

    @property
    def maximum_score(self) -> int:
        return self.limits["maximum_score"]

    def weight(self, group: str, key: str) -> int:
        """Look up a single weight, defaulting to 0 when a rule is disabled."""
        return int(self.weights.get(group, {}).get(key, 0))


class Watchlist(BaseModel):
    """Standing analyst coverage. Symbols are stored without the .JK suffix."""

    covered: list[str] = Field(default_factory=list)
    covered_bonus: int = 0
    muted: list[str] = Field(default_factory=list)

    @field_validator("covered", "muted", mode="before")
    @classmethod
    def _canonicalise(cls, value: Any) -> Any:
        """Accept whatever spelling an analyst types into the YAML.

        Stripping matters: an unnoticed trailing space in ``watchlist.yml``
        would otherwise store " TLKM " and silently drop that ticker's
        coverage, which is exactly the kind of quiet failure this product
        exists to prevent.
        """
        if value is None:
            return []
        if isinstance(value, list):
            cleaned = [str(v).strip().upper().removesuffix(".JK") for v in value]
            return [symbol for symbol in cleaned if symbol]
        return value

    @staticmethod
    def _key(symbol: str) -> str:
        return symbol.strip().upper().removesuffix(".JK")

    def is_covered(self, symbol: str) -> bool:
        return self._key(symbol) in self.covered

    def is_muted(self, symbol: str) -> bool:
        return self._key(symbol) in self.muted


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration file must contain a YAML mapping: {path}")
    return data


def load_scoring(path: Path | None = None) -> ScoringConfig:
    """Load and validate ``config/scoring.yml``."""
    return ScoringConfig.model_validate(_read_yaml(path or DEFAULT_SCORING_PATH))


def load_watchlist(path: Path | None = None) -> Watchlist:
    """Load ``config/watchlist.yml``, tolerating an absent file."""
    target = path or DEFAULT_WATCHLIST_PATH
    if not target.exists():
        return Watchlist()
    return Watchlist.model_validate(_read_yaml(target))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings singleton."""
    return Settings()
