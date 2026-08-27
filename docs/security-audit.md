# Security Audit

Audit date: **2026-08-27 (Asia/Jakarta)**

This is a repository-focused pre-publication audit of the Python/FastAPI
application, GitHub Actions workflows, and submission material. It is not a
penetration test of Sectors, Discord, GitHub, or the operator's workstation.

## Result

**PASS for the working tree and published Git history, with external evidence
gates still pending.**

No credential value was found in the working tree, index, or full repository
history at the audit checkpoint. The public repository was also opened in a
logged-out browser. The scan is repeated after this audit record is published
and immediately before freeze because later commits or recording artifacts can
introduce new exposure.

## Checks Performed

| Check | Result | Evidence |
|---|---|---|
| Environment-only credentials | PASS | `Settings` reads `SECTORS_API_KEY`, `DISCORD_WEBHOOK_URL`, and `GENERIC_WEBHOOK_URL` as `SecretStr`; no source file contains a production value. |
| Ignore policy | PASS | `.env`, keys, databases, logs, artifacts, cache directories, and browser-test output are ignored. `.env.example` contains empty placeholders only. |
| Working-tree secret scan | PASS | A strict production-credential pattern scan returned zero matches in the working tree and index. Only aggregate counts were printed, never candidate values. |
| Git-history secret scan | PASS | The same scan returned zero matches across every commit present at the audit checkpoint. A post-push scan covers the audit commit itself; repeat again after the final freeze commit. |
| API request security | PASS | Sectors base URL is fixed to HTTPS; the raw API key is sent only in the verified `Authorization` header and is never logged. |
| Webhook secrecy | PASS | Webhook exceptions report sink/status only, not URLs. Payloads and artifacts omit configured webhook URLs. |
| Untrusted source links | PASS | Provenance URLs accept only absolute HTTP(S) links with a host and reject control characters, `javascript:`, `data:`, and relative URLs. |
| HTML rendering | PASS | Jinja autoescaping is enabled. External text is rendered as text; source links carry `rel="noopener noreferrer"`. |
| Dashboard hardening | PASS | Read-only routes, Trusted Host allowlist, disabled interactive docs by default, CSP with scripts disabled, `nosniff`, `DENY` framing, referrer policy, permissions policy, and no-store cache headers are tested. |
| SQLite safety | PASS | All value queries are parameterized. Table/column names are static internal SQL. WAL mode and transactional event claims protect state writes. |
| CI secret handling | PASS | Workflow reads secrets only through GitHub Secrets, disables checkout credential persistence, and uploads artifacts that contain no configured webhook URL or API key. |
| Workflow supply chain | PASS | Official GitHub Actions are pinned to full immutable commit SHAs corresponding to verified releases; action upgrades require an explicit reviewed change. |
| Dependency repeatability | PASS | Direct dependencies are exact-pinned and `uv.lock` is committed for reproducible resolution. |
| Installed distribution | PASS | Public CI builds and installs the wheel outside the checkout, then runs `doctor` and fixture mode to prove packaged configuration, templates, static assets, and fixtures are present. |

### GitHub Actions release pins

Verified against the official GitHub release API on 2026-08-27:

| Action | Release | Immutable commit |
|---|---|---|
| `actions/checkout` | `v7.0.1` | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/setup-python` | `v7.0.0` | `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| `actions/cache` | `v6.1.0` | `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` |
| `actions/upload-artifact` | `v7.0.1` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |

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
2. Repeat the full-history scan after the final commit. If a real secret is
   found, stop, revoke/rotate it, and clean history according to GitHub
   guidance before submission.
3. Before recording, inspect browser tabs, terminal output, Actions logs, downloaded artifacts, and Discord screenshots for credential exposure.
4. Add the exact deployed dashboard hostname to `MARKETOPS_ALLOWED_HOSTS` before exposing the FastAPI service beyond local use.
5. GitHub Actions cache is persistence for this small daily workflow, not a backup service. Archive the three qualifying run artifacts separately before cache/artifact retention expires.

## Non-Findings Clarification

The test suite contains deliberately non-routable/example values to prove
redaction behavior. They are not production credentials and are exercised only
through mocked HTTP. This distinction is documented so a future broader
scanner finding is investigated rather than silently ignored.
