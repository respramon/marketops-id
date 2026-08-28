# Security Audit

Audit status date: **2026-08-28 (Asia/Jakarta)**

This is a repository-focused security review of the Python/FastAPI
application, GitHub Actions workflows, generated evidence, and submission
material. It is not a penetration test of Sectors, Discord, GitHub, or the
operator's workstation.

## Result

**BLOCKED pending verified remediation of SEC-001.**

The source tree and Git history did not contain a committed production
credential at the earlier checkpoint. That result did **not** cover generated
workflow artifacts. On 2026-08-27, a full Discord webhook URL was confirmed in
three publicly downloadable `workflow.log` artifacts. The affected artifacts
and sensitive local copies were deleted, the old webhook was revoked, the
stale GitHub secret was deleted, and the scheduler was disabled manually.

Those actions contain the known credential. They do not make the old artifacts
valid evidence, and they do not complete the remediation. Notification,
scheduled automation, and the final security gate remain blocked until the
two-layer logging/artifact fix is committed and pushed, public CI passes, a new
webhook is configured, and a clean replacement delivery run is inspected.

Post-containment verification confirmed that all three affected artifact IDs
are absent/404. The six remaining MarketOps artifacts were scanned across 38
files with zero Discord URL/path, named-secret assignment, Authorization
credential, GitHub/AWS token, or private-key findings. All 9 of 9 accessible
job logs also returned zero findings. This bounds the known incident; it does
not erase the confirmed exposure in the deleted artifacts.

The uncommitted remediation passes local Ruff, mypy across 14 source files,
and 400 tests at 95.62% coverage. Local success reduces regression risk but
does not replace review of the pushed workflow, hosted CI, or a newly generated
artifact.

## Security Findings

### SEC-001: Discord webhook credential disclosed in uploaded workflow logs

- **Rule ID:** `SEC-001` (secret logging and artifact-publication boundary)
- **Severity:** **High**
- **Status:** **Contained; remediation pending verification**
- **Location:** Historical commit `3f3bed7`,
  `src/marketops/cli.py::_configure_logging` lines 39-52, where the `httpx`
  logger inherited INFO logging; and `.github/workflows/marketops.yml` lines
  166-187 and 245-254, where pipeline output was appended to
  `artifacts/workflow.log` and that directory was uploaded.
- **Evidence:** The relevant sanitized configuration was
  `logging.basicConfig(level=..., stream=sys.stdout, force=True)`, followed by
  `"${args[@]}" 2>&1 | tee -a "${MARKETOPS_ARTIFACT_DIR}/workflow.log"` and an
  artifact upload with `path: artifacts/`. A value-safe scan confirmed one full
  Discord webhook URL occurrence in artifact `9633422018` from run
  `33039840251`, one in artifact
  `9633450679` from run `33039918857`, and three in artifact `9633552799` from
  run `33040201783`. The credential value is intentionally omitted. All three
  public artifacts were then deleted irreversibly.
- **Root cause:** `httpx` writes the complete request URL at INFO level. A
  Discord webhook token is embedded in the URL path, so capturing process
  output with `tee` copied the bearer credential into `workflow.log`. GitHub's
  console masking was not a substitute for sanitizing files before artifact
  upload.
- **Impact:** Anyone who downloaded an affected public artifact before deletion
  could have obtained the webhook capability and posted unauthorized messages
  to its destination until revocation. No conclusion is made here about
  whether an unknown party downloaded it or abused it.
- **Fix:** The current uncommitted remediation adds a secret-redacting log
  formatter, lowers `httpx`/`httpcore` transport logging below INFO, and adds a
  pre-upload artifact scrub that fails the workflow if it has to redact a
  credential. These controls must still be committed, pushed, tested in public
  CI, and exercised by a clean replacement run.
- **Mitigation/containment:** The affected public artifacts were deleted; local
  sensitive `workflow.log` copies were deleted; revocation of the old Discord
  webhook returned HTTP 204; `DISCORD_WEBHOOK_URL` was removed from GitHub
  Secrets; and the production scheduler was disabled manually.
- **False-positive notes:** This is a confirmed disclosure, not a scanner-only
  match. Counts were collected without printing the URL. The old GitHub run
  metadata and job pages may remain public, but the affected downloadable
  artifacts no longer exist. A passing repository-history scan does not negate
  an artifact-only leak.

## Checks Performed

| Check | Result | Evidence |
|---|---|---|
| Environment-only credentials | PASS | `Settings` reads credential variables as `SecretStr`; no production value is intentionally stored in source. |
| GitHub Secret configuration | BLOCKED | `SECTORS_API_KEY` remains environment-managed. The stale `DISCORD_WEBHOOK_URL` secret was deliberately deleted after SEC-001; a replacement must not be added until the remediation is verified. |
| Ignore policy | PASS | `.env`, keys, databases, logs, artifacts, cache directories, and browser-test output are ignored. `.env.example` contains empty placeholders only. |
| Working-tree and Git-history scan | PASS, limited scope | Earlier strict scans found no committed production credential. Generated Actions artifacts are a separate publication boundary and caused SEC-001. Repeat both repository and artifact scans after remediation and before freeze. |
| Post-containment artifact/log scan | PASS for remaining material | The three affected artifact IDs are absent/404. Six remaining artifacts (38 files) and 9/9 accessible job logs produced zero findings across the defined credential patterns. |
| API request security | PASS | The Sectors base URL is fixed to HTTPS; its key is sent in the verified `Authorization` header. No Sectors-key exposure is part of the confirmed finding; repeat artifact scanning after the replacement run. |
| Webhook secrecy | BLOCKED | The old webhook is revoked and removed, but the redacting formatter and artifact scrub are not yet committed/pushed/CI-verified. |
| Untrusted source links | PASS | Provenance URLs accept only absolute HTTP(S) links with a host and reject control characters, `javascript:`, `data:`, and relative URLs. |
| HTML rendering | PASS | Jinja autoescaping is enabled. External text is rendered as text; source links carry `rel="noopener noreferrer"`. |
| Dashboard hardening | PASS | Read-only routes, Trusted Host allowlist, disabled interactive docs by default, script-free CSP, security headers, and no-store cache headers are tested. |
| SQLite safety | PASS | Value queries are parameterized; table and column names are static internal SQL. WAL mode and transactional event claims protect writes. |
| CI secret handling | BLOCKED | Historical artifact upload exposed the Discord URL. The two-layer remediation and replacement artifact must pass without a secret match before this returns to PASS. |
| Workflow supply chain | PASS | Official GitHub Actions are pinned to immutable commit SHAs corresponding to verified releases. |
| Dependency repeatability | PASS | Direct dependencies are exact-pinned and `uv.lock` is committed. |
| Installed distribution | PASS at last public checkpoint | Public CI previously built and exercised the wheel outside the checkout; rerun after the security patch. |

### GitHub Actions release pins

Verified against the official GitHub release API on 2026-08-27:

| Action | Release | Immutable commit |
|---|---|---|
| `actions/checkout` | `v7.0.1` | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/setup-python` | `v7.0.0` | `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| `actions/cache` | `v6.1.0` | `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` |
| `actions/upload-artifact` | `v7.0.1` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |

## Threat Boundaries and Controls

| Boundary | Main risk | Current control/state |
|---|---|---|
| GitHub Secrets/local environment -> pipeline | Credential disclosure | `SecretStr` and ignored `.env`; SEC-001 shows that downstream library logs and generated files also require redaction. |
| Sectors API -> normalization | Malformed or hostile payload | Pydantic/domain normalization, malformed-row accounting, URL allowlist, and Jinja escaping. |
| Pipeline -> Discord/generic webhook | URL leakage or false delivery claim | Old credential revoked. Delivery state is counted only after sink success; future operation is blocked until redacting logs and artifact scrub are verified. |
| Runner output -> public artifact | Secret copied from process logs | Pending two layers: final-line redaction/quiet HTTP transport logs, then pre-upload recursive scrub with fail-on-match. |
| Scheduler -> SQLite | Duplicate alert race or state loss | SQLite primary keys, atomic event claims, workflow concurrency, and cached-state restore/save. Scheduler currently disabled during containment. |
| Browser -> dashboard | XSS, clickjacking, host-header abuse | Script-free CSP, autoescaping, URL filtering, security headers, Host allowlist, and no write routes. |

## Required Recovery Sequence

1. Commit and push the redacting logger plus pre-upload artifact scrub.
2. Run the full local gates and public CI; inspect output without printing any
   candidate secret values.
3. Create a new Discord webhook and store it only as the GitHub
   `DISCORD_WEBHOOK_URL` secret.
4. Run a controlled manual delivery, download its artifact privately, and
   verify that the webhook URL is absent while the expected redaction gate
   reports clean.
5. Re-enable the scheduler only after the safe live path is verified.
6. Start collecting three new genuine `schedule` runs. Old manual runs cannot
   fill those slots, and their deleted artifacts cannot be cited as current
   downloadable evidence.
7. Repeat the working-tree, index, Git-history, runtime-log, artifact, and media
   scans immediately before freeze.

## Non-Findings Clarification

The test suite may contain deliberately non-routable/example values used to
prove redaction. They are not production credentials. Such matches must be
reviewed and documented; they must never become a blanket allowlist that could
hide a future real credential.
