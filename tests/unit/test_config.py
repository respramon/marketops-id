"""Configuration loading and secret handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from marketops.config import (
    DEFAULT_SCORING_PATH,
    SECTORS_BASE_URL,
    Settings,
    Watchlist,
    load_scoring,
    load_watchlist,
)


class TestScoringConfig:
    def test_shipped_config_loads_and_validates(self) -> None:
        config = load_scoring(DEFAULT_SCORING_PATH)
        assert config.priority.p1_min == 75
        assert config.priority.p2_min == 50
        assert config.priority.p3_min == 25
        assert config.maximum_score == 100

    def test_bands_are_strictly_ordered(self) -> None:
        config = load_scoring(DEFAULT_SCORING_PATH)
        assert config.priority.p3_min < config.priority.p2_min < config.priority.p1_min

    def test_weight_lookup_of_a_disabled_rule_is_zero(self) -> None:
        config = load_scoring(DEFAULT_SCORING_PATH)
        assert config.weight("nonexistent", "nope") == 0
        assert config.weight("filing", "nope") == 0

    def test_all_thresholds_are_present(self) -> None:
        thresholds = load_scoring(DEFAULT_SCORING_PATH).thresholds
        assert thresholds.ownership_change_pct == 0.5
        assert thresholds.transaction_value_idr == 25_000_000_000
        assert thresholds.price_move_small_pct == 3.0
        assert thresholds.price_move_large_pct == 7.0
        assert thresholds.foreign_flow_ratio_small == 2.0
        assert thresholds.foreign_flow_ratio_large == 4.0
        assert thresholds.corporate_action_window_days == 7

    def test_suspension_override_reaches_the_maximum(self) -> None:
        """If this ever drifts below the cap, a halted stock stops being P1."""
        config = load_scoring(DEFAULT_SCORING_PATH)
        assert config.weight("suspension", "override_score") >= config.maximum_score

    def test_a_missing_file_is_an_explicit_error(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_scoring(tmp_path / "absent.yml")

    def test_a_non_mapping_file_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yml"
        path.write_text("- just\n- a\n- list\n", encoding="utf-8")
        with pytest.raises(ValueError, match="YAML mapping"):
            load_scoring(path)

    def test_an_incomplete_config_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "partial.yml"
        path.write_text("priority:\n  p1_min: 75\n", encoding="utf-8")
        with pytest.raises(ValueError):
            load_scoring(path)

    def test_config_is_deep_copyable_for_experiments(self) -> None:
        config = load_scoring(DEFAULT_SCORING_PATH)
        clone = config.model_copy(deep=True)
        clone.priority.p1_min = 90
        assert config.priority.p1_min == 75

    def test_reloading_produces_an_equal_config(self) -> None:
        assert load_scoring(DEFAULT_SCORING_PATH) == load_scoring(DEFAULT_SCORING_PATH)


class TestWatchlist:
    def test_shipped_watchlist_loads(self) -> None:
        watchlist = load_watchlist()
        assert isinstance(watchlist, Watchlist)
        assert "BBCA" in watchlist.covered

    def test_symbols_are_normalised_on_load(self, tmp_path: Path) -> None:
        path = tmp_path / "w.yml"
        path.write_text(
            "covered:\n  - bbca.jk\n  - ' tlkm '\ncovered_bonus: 5\nmuted:\n  - noise.JK\n",
            encoding="utf-8",
        )
        watchlist = load_watchlist(path)
        assert watchlist.covered == ["BBCA", "TLKM"]
        assert watchlist.muted == ["NOISE"]

    def test_membership_is_case_and_suffix_insensitive(self) -> None:
        watchlist = Watchlist(covered=["BBCA"], covered_bonus=5, muted=["NOISE"])
        assert watchlist.is_covered("bbca") is True
        assert watchlist.is_covered("BBCA") is True
        assert watchlist.is_muted("noise") is True
        assert watchlist.is_covered("ANTM") is False

    def test_absent_file_yields_an_empty_watchlist(self, tmp_path: Path) -> None:
        watchlist = load_watchlist(tmp_path / "nope.yml")
        assert watchlist.covered == []
        assert watchlist.muted == []
        assert watchlist.covered_bonus == 0

    def test_null_lists_are_tolerated(self, tmp_path: Path) -> None:
        path = tmp_path / "w.yml"
        path.write_text("covered:\nmuted:\ncovered_bonus: 3\n", encoding="utf-8")
        watchlist = load_watchlist(path)
        assert watchlist.covered == []
        assert watchlist.covered_bonus == 3


class TestSettings:
    def test_defaults_are_safe_without_any_environment(self) -> None:
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.has_api_key is False
        assert settings.has_any_webhook is False
        assert settings.max_api_credits_per_run == 15
        assert settings.max_enrich_tickers == 5
        assert settings.http_timeout == 15.0
        assert settings.max_retries == 3

    def test_secrets_are_wrapped_and_never_reprd(self) -> None:
        settings = Settings(  # type: ignore[call-arg]
            _env_file=None,
            SECTORS_API_KEY="sk-DO-NOT-LEAK",
            DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/1/LEAKY",
        )
        rendered = repr(settings) + str(settings)
        assert "sk-DO-NOT-LEAK" not in rendered
        assert "LEAKY" not in rendered
        assert settings.sectors_api_key is not None
        assert settings.sectors_api_key.get_secret_value() == "sk-DO-NOT-LEAK"

    def test_model_dump_does_not_expose_secrets(self) -> None:
        settings = Settings(_env_file=None, SECTORS_API_KEY="sk-DO-NOT-LEAK")  # type: ignore[call-arg]
        assert "sk-DO-NOT-LEAK" not in str(settings.model_dump())

    def test_blank_api_key_counts_as_absent(self) -> None:
        """An empty GitHub Secret must not look like a configured key."""
        for blank in ("", "   "):
            settings = Settings(_env_file=None, SECTORS_API_KEY=blank)  # type: ignore[call-arg]
            assert settings.has_api_key is False

    def test_non_blank_secret_typo_that_is_too_short_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least 8 characters"):
            Settings(_env_file=None, SECTORS_API_KEY="short")  # type: ignore[call-arg]

    def test_webhook_presence_detection(self) -> None:
        discord = Settings(_env_file=None, DISCORD_WEBHOOK_URL="https://x.test/h")  # type: ignore[call-arg]
        generic = Settings(_env_file=None, GENERIC_WEBHOOK_URL="https://y.test/h")  # type: ignore[call-arg]
        assert discord.has_any_webhook is True
        assert generic.has_any_webhook is True

    def test_environment_overrides_are_read(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MARKETOPS_MAX_API_CREDITS_PER_RUN", "7")
        monkeypatch.setenv("MARKETOPS_MAX_ENRICH_TICKERS", "2")
        monkeypatch.setenv("MARKETOPS_LOOKBACK_DAYS", "5")
        settings = Settings(_env_file=None)  # type: ignore[call-arg]
        assert settings.max_api_credits_per_run == 7
        assert settings.max_enrich_tickers == 2
        assert settings.lookback_days == 5

    @pytest.mark.parametrize(
        ("variable", "value"),
        [
            ("MARKETOPS_MAX_API_CREDITS_PER_RUN", "0"),
            ("MARKETOPS_LOOKBACK_DAYS", "0"),
            ("MARKETOPS_LOOKBACK_DAYS", "91"),
            ("MARKETOPS_HTTP_TIMEOUT", "0"),
            ("MARKETOPS_MAX_RETRIES", "-1"),
            ("MARKETOPS_MAX_CONCURRENCY", "0"),
        ],
    )
    def test_out_of_range_values_are_rejected(
        self, monkeypatch: pytest.MonkeyPatch, variable: str, value: str
    ) -> None:
        """A typo in a GitHub Secret should fail loudly at startup."""
        monkeypatch.setenv(variable, value)
        with pytest.raises(ValueError):
            Settings(_env_file=None)  # type: ignore[call-arg]

    def test_unknown_environment_variables_are_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("MARKETOPS_SOMETHING_ELSE", "x")
        assert Settings(_env_file=None) is not None  # type: ignore[call-arg]


class TestConstants:
    def test_base_url_matches_the_published_openapi_server(self) -> None:
        assert SECTORS_BASE_URL == "https://api.sectors.app"
