"""Secret-safe logging and artifact hygiene.

Webhook URLs are bearer credentials.  HTTP clients commonly include request
URLs in INFO logs, so relying only on application-level exception messages is
not enough.  This module provides two independent controls:

* a formatter that redacts configured secrets and Discord webhook URL shapes;
* a final artifact scrub that removes any credential which reached a file and
  fails the workflow after making the uploaded evidence safe.

Neither control prints a secret or the content of a contaminated file.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import tempfile
from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REDACTION = "[REDACTED]"
SECRET_ENV_NAMES = (
    "SECTORS_API_KEY",
    "DISCORD_WEBHOOK_URL",
    "GENERIC_WEBHOOK_URL",
)

_DISCORD_WEBHOOK_TEXT = re.compile(
    r"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/"
    r"api(?:/v\d+)?/webhooks/[0-9]+/[^\s\"'<>]+",
    re.IGNORECASE,
)
_DISCORD_WEBHOOK_BYTES = re.compile(
    rb"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/"
    rb"api(?:/v\d+)?/webhooks/[0-9]+/[^\s\"'<>]+",
    re.IGNORECASE,
)


def normalized_secrets(values: Iterable[str | None]) -> tuple[str, ...]:
    """Return unique, non-blank secret strings in longest-first order."""
    candidates = {value for value in values if value and value.strip()}
    return tuple(sorted(candidates, key=len, reverse=True))


def redact_text(value: str, secrets: Iterable[str] = ()) -> str:
    """Remove exact configured secrets plus recognizable Discord credentials."""
    redacted = value
    for secret in normalized_secrets(secrets):
        redacted = redacted.replace(secret, REDACTION)
    return _DISCORD_WEBHOOK_TEXT.sub("https://discord.com/api/webhooks/[REDACTED]", redacted)


def redact_structure(value: Any, secrets: Iterable[str] = ()) -> Any:
    """Recursively redact strings before external data is persisted or delivered."""
    normalized = normalized_secrets(secrets)

    def walk(item: Any) -> Any:
        if isinstance(item, str):
            return redact_text(item, normalized)
        if isinstance(item, dict):
            return {walk(key): walk(nested) for key, nested in item.items()}
        if isinstance(item, list):
            return [walk(nested) for nested in item]
        if isinstance(item, tuple):
            return tuple(walk(nested) for nested in item)
        return item

    return walk(value)


class SecretRedactingFormatter(logging.Formatter):
    """Redact the final rendered line, including exception tracebacks."""

    def __init__(
        self,
        fmt: str,
        datefmt: str | None = None,
        *,
        secrets: Iterable[str] = (),
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)
        self._secrets = normalized_secrets(secrets)

    def format(self, record: logging.LogRecord) -> str:
        return redact_text(super().format(record), self._secrets)


class JsonSecretRedactingFormatter(logging.Formatter):
    """Serialize one valid JSON object per record and redact every text field."""

    def __init__(self, *, secrets: Iterable[str] = ()) -> None:
        super().__init__()
        self._secrets = normalized_secrets(secrets)

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat(
            timespec="milliseconds"
        )
        payload: dict[str, str] = {
            "ts": timestamp.replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact_text(record.getMessage(), self._secrets),
        }
        if record.exc_info:
            payload["exception"] = redact_text(
                self.formatException(record.exc_info),
                self._secrets,
            )
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_safe_logging(
    level: str,
    *,
    json_logs: bool = False,
    secrets: Iterable[str] = (),
) -> None:
    """Configure root logging with redaction and quiet HTTP transport logs."""
    handler = logging.StreamHandler()
    if json_logs:
        handler.setFormatter(JsonSecretRedactingFormatter(secrets=secrets))
    else:
        handler.setFormatter(
            SecretRedactingFormatter(
                "%(asctime)s  %(levelname)-7s  %(name)-22s  %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
                secrets=secrets,
            )
        )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # httpx logs the complete request URL at INFO.  Webhook tokens live in the
    # URL, so transport request lines are never useful enough to justify that
    # exposure.  The formatter remains a defense-in-depth backstop.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def _redact_bytes(value: bytes, secrets: tuple[bytes, ...]) -> tuple[bytes, int]:
    redacted = value
    occurrences = 0
    for secret in secrets:
        count = redacted.count(secret)
        if count:
            redacted = redacted.replace(secret, REDACTION.encode("utf-8"))
            occurrences += count
    redacted, pattern_count = _DISCORD_WEBHOOK_BYTES.subn(
        b"https://discord.com/api/webhooks/[REDACTED]",
        redacted,
    )
    return redacted, occurrences + pattern_count


def _atomic_write(path: Path, value: bytes) -> None:
    """Replace one artifact atomically so interruption cannot leave a partial file."""
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=".marketops-redact-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
            temporary_path = Path(handle.name)
        temporary_path.replace(path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _inspect_tree(
    root: Path,
    secrets: Iterable[str],
    *,
    sanitize: bool,
) -> tuple[int, int]:
    """Find credentials below ``root`` and optionally rewrite affected files."""
    resolved_root = root.resolve(strict=True)
    if not resolved_root.is_dir():
        raise NotADirectoryError(resolved_root)

    encoded_secrets = tuple(secret.encode("utf-8") for secret in normalized_secrets(secrets))
    occurrences = 0
    files_changed = 0
    for path in resolved_root.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        resolved_path = path.resolve(strict=True)
        if not resolved_path.is_relative_to(resolved_root):
            continue
        original = resolved_path.read_bytes()
        redacted, file_occurrences = _redact_bytes(original, encoded_secrets)
        if not file_occurrences:
            continue
        occurrences += file_occurrences
        if sanitize:
            _atomic_write(resolved_path, redacted)
            files_changed += 1
    return occurrences, files_changed


def scan_secret_tree(root: Path, secrets: Iterable[str] = ()) -> tuple[int, int]:
    """Detect credentials without changing files, including SQLite state bytes."""
    occurrences, _ = _inspect_tree(root, secrets, sanitize=False)
    return occurrences, 0


def sanitize_artifact_tree(root: Path, secrets: Iterable[str] = ()) -> tuple[int, int]:
    """Atomically redact secrets from regular files below ``root``.

    Returns ``(occurrences_redacted, files_changed)``. Symlinks and paths which
    resolve outside the artifact root are ignored so the cleanup cannot mutate
    unrelated files.
    """
    return _inspect_tree(root, secrets, sanitize=True)


def _environment_secrets() -> tuple[str, ...]:
    return normalized_secrets(os.environ.get(name) for name in SECRET_ENV_NAMES)


def _write_scan_outputs(path: Path, *, findings: int, files_changed: int, mode: str) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write("scan_complete=true\n")
        handle.write(f"findings={findings}\n")
        handle.write(f"files_changed={files_changed}\n")
        handle.write(f"scan_mode={mode}\n")


def main(argv: Sequence[str] | None = None) -> int:
    """Detect or sanitize credentials without echoing credential values."""
    parser = argparse.ArgumentParser(description="Scan MarketOps state or run artifacts")
    parser.add_argument("target_dir", type=Path)
    parser.add_argument(
        "--detect-only",
        action="store_true",
        help="report findings without changing any file",
    )
    parser.add_argument(
        "--fail-if-found",
        action="store_true",
        help="exit non-zero after a completed scan if any credential was found",
    )
    parser.add_argument(
        "--github-output",
        type=Path,
        help="append non-sensitive completion outputs for a GitHub Actions step",
    )
    args = parser.parse_args(argv)
    scan = scan_secret_tree if args.detect_only else sanitize_artifact_tree
    occurrences, files_changed = scan(args.target_dir, _environment_secrets())
    mode = "detect" if args.detect_only else "sanitize"
    if args.github_output is not None:
        _write_scan_outputs(
            args.github_output,
            findings=occurrences,
            files_changed=files_changed,
            mode=mode,
        )
    print(
        f"secret_scan mode={mode} findings={occurrences} files_changed={files_changed}"
    )
    return 4 if args.fail_if_found and occurrences else 0


if __name__ == "__main__":  # pragma: no cover - exercised through ``main`` tests
    raise SystemExit(main())
