# Security Audit

Audit date: **2026-08-27 (Asia/Jakarta)**

This is a repository-focused pre-publication audit of the Python/FastAPI
application, GitHub Actions workflows, and submission material. It is not a
penetration test of Sectors, Discord, GitHub, or the operator's workstation.

## Result

**PASS for the local working tree, with external evidence gates still pending.**

No credential value was found in the scanned working tree. The repository had
no commits at audit time, so a full Git-history scan must be repeated after the
first commit and again immediately before freeze.

## Checks Performed

| Check | Result | Evidence |
|---|---|---|
| Environment-only credentials | PASS | `Settings` reads `SECTORS_API_KEY`, `DISCORD_WEBHOOK_URL`, and `GENERIC_WEBHOOK_URL` as `SecretStr`; no source file contains a production value. |
| Ignore policy | PASS | `.env`, keys, databases, logs, artifacts, cache directories, and browser-test output are ignored. `.env.example` contains empty placeholders only. |
| Working-tree secret scan | PASS | Pattern scan detected only intentionally fake test values in `tests/`; no real key/token value was found. Output was limited to paths so no candidate value was exposed. |
| Git-history secret scan | PENDING | `git log --all` was empty at audit time. Re-run after commit/push and before submission. |
| API request security | PASS | Sectors base URL is fixed to HTTPS; the raw API key is sent only in the verified `Authorization` header and is never logged. |
| Webhook secrecy | PASS | Webhook exceptions report sink/status only, not URLs. Payloads and artifacts omit configured webhook URLs. |
| Untrusted source links | PASS | Provenance URLs accept only absolute HTTP(S) links with a host and reject control characters, `javascript:`, `data:`, and relative URLs. |
| HTML rendering | PASS | Jinja autoescaping is enabled. External text is rendered as text; source links carry `rel="noopener noreferrer"`. |
| Dashboard hardening | PASS | Read-only routes, Trusted Host allowlist, disabled interactive docs by default, CSP with scripts disabled, `nosniff`, `DENY` framing, referrer policy, permissions policy, and no-store cache headers are tested. |
| SQLite safety | PASS | All value queries are parameterized. Table/column names are static internal SQL. WAL mode and transactional event claims protect state writes. |
| CI secret handling | PASS | Workflow reads secrets only through GitHub Secrets, disables checkout credential persistence, and uploads artifacts that contain no configured webhook URL or API key. |
| Dependency repeatability | PASS | Direct dependencies are exact-pinned and `uv.lock` is committed for reproducible resolution. |

## Threat Boundaries and Controls

| Boundary | Main risk | Control |
|---|---|---|
| GitHub Secrets/local environment -> pipeline | Credential disclosure | `SecretStr`, no secret logging, ignored `.env`, scan before freeze. |
| Sectors API -> normalization | Malformed or hostile payload | Pydantic/domain normalization, malformed-row accounting, URL allowlist, Jinja escaping. |
| Pipeline -> Discord/generic webhook | URL or payload leakage / false delivery claim | URL never rendered; delivery counted only after successful HTTP response; dry preview is explicitly not delivery. |
| Scheduler -> SQLite | Duplicate alert race / state loss | SQLite primary keys plus atomic event claims; workflow concurrency and cached state restore/save. |
| Browser -> dashboard | XSS, clickjacking, host-header abuse | script-free CSP, autoescaping, URL filtering, security headers, Host allowlist, no write routes. |

## Residual Risk and Required Final Checks

1. Add real values only through GitHub Secrets or an ignored local `.env`; never paste them into an issue, terminal recording, screenshot, artifact, or this repository.
2. After the first commit, scan all history. If a real secret is found, revoke/rotate it before any public push and clean history according to GitHub guidance.
3. Before recording, inspect browser tabs, terminal output, Actions logs, downloaded artifacts, and Discord screenshots for credential exposure.
4. Add the exact deployed dashboard hostname to `MARKETOPS_ALLOWED_HOSTS` before exposing the FastAPI service beyond local use.
5. GitHub Actions cache is persistence for this small daily workflow, not a backup service. Archive the three qualifying run artifacts separately before cache/artifact retention expires.

## Non-Findings Clarification

The test suite contains deliberately non-routable/example credential-shaped
strings to prove redaction behavior. They are not production credentials and
are exercised only through mocked HTTP. This distinction is documented so a
future scanner finding is investigated rather than silently ignored.
