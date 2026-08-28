"""Regression tests for secret-safe logs and uploaded run artifacts."""

from __future__ import annotations

import io
import json
import logging
import sys
from pathlib import Path

import pytest

from marketops.security import (
    REDACTION,
    JsonSecretRedactingFormatter,
    SecretRedactingFormatter,
    configure_safe_logging,
    main,
    normalized_secrets,
    redact_structure,
    redact_text,
    sanitize_artifact_tree,
    scan_secret_tree,
)

HOOK = "https://discord.com/api/webhooks/1234567890/fake-sensitive-token"
API_KEY = "fake-sectors-key-for-redaction"


def test_redact_text_removes_exact_secrets_and_webhook_shapes() -> None:
    rendered = redact_text(f"key={API_KEY} request={HOOK}", (API_KEY,))
    assert API_KEY not in rendered
    assert "fake-sensitive-token" not in rendered
    assert rendered.count(REDACTION) == 2


def test_even_short_non_blank_configured_secrets_are_redacted() -> None:
    assert normalized_secrets(("x", " ", None)) == ("x",)
    assert redact_text("prefix-x-suffix", ("x",)) == "prefi[REDACTED]-[REDACTED]-suffi[REDACTED]"


def test_nested_external_data_is_redacted_before_persistence() -> None:
    value = {"warning": [f"reflected {API_KEY}", {"url": HOOK}], "count": 2}
    redacted = redact_structure(value, (API_KEY,))
    rendered = json.dumps(redacted)
    assert API_KEY not in rendered
    assert "fake-sensitive-token" not in rendered
    assert redacted["count"] == 2


def test_formatter_redacts_message_arguments_and_exception_text() -> None:
    formatter = SecretRedactingFormatter("%(levelname)s %(message)s", secrets=(API_KEY,))
    try:
        raise RuntimeError(f"transport exposed {HOOK}")
    except RuntimeError:
        record = logging.LogRecord(
            "marketops.test",
            logging.ERROR,
            __file__,
            1,
            "request %s failed with %s",
            (HOOK, API_KEY),
            sys.exc_info(),
        )
    rendered = formatter.format(record)
    assert HOOK not in rendered
    assert API_KEY not in rendered
    assert REDACTION in rendered


def test_json_formatter_emits_valid_single_line_json_with_redacted_exception() -> None:
    formatter = JsonSecretRedactingFormatter(secrets=(API_KEY, HOOK))
    try:
        raise RuntimeError(f"line one\nline two {API_KEY}")
    except RuntimeError:
        record = logging.LogRecord(
            "marketops.json",
            logging.ERROR,
            __file__,
            1,
            'remote said "quoted"\nworkflow.trigger=fake %s',
            (HOOK,),
            sys.exc_info(),
        )
    rendered = formatter.format(record)
    parsed = json.loads(rendered)
    assert rendered.count("\n") == 0
    assert parsed["logger"] == "marketops.json"
    assert 'remote said "quoted"' in parsed["msg"]
    assert "workflow.trigger=fake" in parsed["msg"]
    assert API_KEY not in rendered
    assert "fake-sensitive-token" not in rendered
    assert REDACTION in parsed["exception"]


def test_safe_logging_quiets_http_transport_request_lines() -> None:
    configure_safe_logging("INFO", secrets=(HOOK,))
    assert logging.getLogger("httpx").getEffectiveLevel() == logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() == logging.WARNING


def test_artifact_sanitizer_redacts_without_touching_symlink(
    tmp_path: Path,
) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    workflow_log = artifact_dir / "workflow.log"
    workflow_log.write_text(f"key={API_KEY}\nPOST {HOOK}\n", encoding="utf-8")

    outside = tmp_path / "outside.log"
    outside.write_text(HOOK, encoding="utf-8")
    link = artifact_dir / "outside-link.log"
    try:
        link.symlink_to(outside)
    except OSError:
        link = None

    occurrences, files_changed = sanitize_artifact_tree(artifact_dir, (API_KEY,))
    sanitized = workflow_log.read_text(encoding="utf-8")
    assert occurrences == 2
    assert files_changed == 1
    assert API_KEY not in sanitized
    assert "fake-sensitive-token" not in sanitized
    assert outside.read_text(encoding="utf-8") == HOOK
    if link is not None:
        assert link.is_symlink()


def test_artifact_sanitizer_reports_a_clean_tree(tmp_path: Path) -> None:
    (tmp_path / "safe.log").write_text("workflow.status=OK", encoding="utf-8")
    assert sanitize_artifact_tree(tmp_path, (API_KEY,)) == (0, 0)


def test_detection_only_finds_state_secret_without_mutating_file(tmp_path: Path) -> None:
    state = tmp_path / "marketops.db"
    state.write_bytes(b"SQLite-prefix-" + API_KEY.encode() + b"-suffix")
    assert scan_secret_tree(tmp_path, (API_KEY,)) == (1, 0)
    assert API_KEY.encode() in state.read_bytes()


def test_atomic_redaction_failure_leaves_original_file_intact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contaminated = tmp_path / "workflow.log"
    contaminated.write_text(HOOK, encoding="utf-8")

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr("marketops.security.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated interruption"):
        sanitize_artifact_tree(tmp_path, (HOOK,))
    assert contaminated.read_text(encoding="utf-8") == HOOK
    assert not list(tmp_path.glob(".marketops-redact-*.tmp"))


def test_artifact_cli_reports_only_after_redacting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    contaminated = tmp_path / "workflow.log"
    github_output = tmp_path / "github-output.txt"
    contaminated.write_text(HOOK, encoding="utf-8")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", HOOK)

    assert main([str(tmp_path), "--github-output", str(github_output)]) == 0
    assert "fake-sensitive-token" not in contaminated.read_text(encoding="utf-8")
    output = capsys.readouterr().out
    assert HOOK not in output
    assert "findings=1" in output
    outputs = github_output.read_text(encoding="utf-8")
    assert "scan_complete=true" in outputs
    assert "findings=1" in outputs
    assert "files_changed=1" in outputs


def test_detect_cli_fails_after_completed_scan_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contaminated = tmp_path / "marketops.db"
    github_output = tmp_path / "github-output.txt"
    contaminated.write_text(API_KEY, encoding="utf-8")
    monkeypatch.setenv("SECTORS_API_KEY", API_KEY)
    assert (
        main(
            [
                str(tmp_path),
                "--detect-only",
                "--fail-if-found",
                "--github-output",
                str(github_output),
            ]
        )
        == 4
    )
    assert contaminated.read_text(encoding="utf-8") == API_KEY
    assert "scan_complete=true" in github_output.read_text(encoding="utf-8")


def test_artifact_cli_accepts_a_clean_tree(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "safe.json").write_text("{}", encoding="utf-8")
    assert main([str(tmp_path), "--fail-if-found"]) == 0
    assert "findings=0" in capsys.readouterr().out


def test_formatter_output_can_be_captured_without_secret() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SecretRedactingFormatter("%(message)s", secrets=(HOOK,)))
    logger = logging.getLogger("marketops.redaction-test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    logger.info("HTTP Request: POST %s", HOOK)
    assert HOOK not in stream.getvalue()
    assert "fake-sensitive-token" not in stream.getvalue()
