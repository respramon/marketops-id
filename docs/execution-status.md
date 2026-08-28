# Execution Status

Status snapshot: **2026-08-28, Asia/Jakarta**. `PASS` means the code or
artifact exists and has been verified locally or against cited public
evidence. A `BLOCKED` item names an external fact that cannot truthfully be
fabricated from this workspace.

## Compliance

PARTIAL

Official homepage, rules, Track 2, and Sectors v2 documentation were
re-verified on 2026-08-27. The solo participant confirmed Sectors onboarding
was completed before implementation. Portal registration, personal eligibility,
credit claiming, social posting, and final portal submission remain account
owner actions.

## Sectors Integration

PASS

The typed v2 client implements filings, suspensions, one-day movers, batched
news, selective foreign flow, and selective corporate actions. Exact endpoint,
authentication, parameter, response, credit, and failure details are recorded
in `docs/sectors-api-map.md`. `SECTORS_API_KEY` is configured as a GitHub Secret
(its value was never retrieved or printed). Manual authenticated live run
[`33039796607`](https://github.com/respramon/marketops-id/actions/runs/33039796607)
exercised all six capabilities: 77 normalized events, 33 candidates, five
selectively enriched tickers, and 15/15 estimated credits. Its only warning was
the explicit one-page news cap, so the report correctly remained `PARTIAL`.

## Core Pipeline

PASS

Discovery, canonical normalization, deterministic candidate selection,
selective enrichment, correlation, scoring, fail-soft source verdicts, and
JSON/HTML/Markdown artifact generation run end to end in sanitized fixture
mode and in the authenticated live QA run cited above.

## Deduplication

PASS

SQLite uses deterministic SHA-256 event IDs and atomic claims. Final local
replay on 2026-08-27 observed 16 new events and five dry-preview cards on run
one; the identical second replay suppressed 16 duplicates and rendered zero
preview cards. No external delivery was claimed.

The final exact CLI acceptance pair (without dry-notify) used a fresh database:
run `run-20260827-104147-8a8ba2` observed 16 new events; run
`run-20260827-104148-2dc614` observed zero new events and suppressed 16. Both
reported zero deliveries and `PARTIAL` because no webhook is configured, which
is the intended fail-soft result rather than a false success claim.

## Tests

PASS

Locally verified on 2026-08-28 after the SEC-001 remediation changes:

```text
ruff check .                                      PASS
mypy src                                          PASS (14 source files)
pytest --cov=marketops --cov-report=term-missing  PASS (400 tests, 95.62% coverage)
```

One third-party FastAPI/Starlette TestClient deprecation warning was emitted;
it did not fail the suite. `submission/assets/test-pass.svg` and
`test-pass-local.png` record the current local summary;
`submission/assets/test-pass.png` remains the separate logged-out capture of
the earlier public GitHub Actions result.

## CI

PASS

The repository is public at
<https://github.com/respramon/marketops-id>. Public
[CI run `33040157886`](https://github.com/respramon/marketops-id/actions/runs/33040157886)
passed Ruff, mypy, pytest/coverage, the installed-wheel smoke test, report
upload, and gate enforcement for commit `3f3bed7`. Official third-party
Actions are pinned to immutable release SHAs.

This is the last verified public code checkpoint. The SEC-001 remediation is
now committed locally as `2e51bd8` and is green on the full local gate (Ruff,
mypy, 400 tests, 95.62% coverage), but it has not been pushed, so it has not
yet passed public CI. Notification, Automation, and Security Audit remain
blocked regardless of this earlier green run and the local gate.

## Automation

BLOCKED

The production workflow has both `workflow_dispatch` for tests and a weekday
`17 0 * * 1-5` schedule, equivalent to approximately 07:17 WIB. Scheduled
cycles select `live` mode, restore SQLite state, write structured artifacts,
save state, and never auto-commit runtime data.

The scheduler is currently **disabled manually** as containment for SEC-001.
It must not be re-enabled until the redacting logger and pre-upload artifact
scrub are committed, pushed, CI-verified, and exercised with a newly issued
webhook in a clean manual run.

Two public manual fixture runs verified the hosted execution path without
claiming Track 2 qualification. Run
[`33036266340`](https://github.com/respramon/marketops-id/actions/runs/33036266340)
observed 16 new events and saved state; run
[`33036310666`](https://github.com/respramon/marketops-id/actions/runs/33036310666)
restored that state, suppressed 16 duplicates, produced zero previews, and
uploaded the complete run history.

Manual authenticated live runs historically verified the production data and
delivery paths. Run `33039796607` exercised all six Sectors capabilities. The initial
Discord delivery returned HTTP 400 because the aggregate embed text exceeded
Discord's message limit; count-and-text-aware batching was added in commit
`3f3bed7`. Run
[`33040201783`](https://github.com/respramon/marketops-id/actions/runs/33040201783)
then delivered 16 pending cards across three messages. Run
[`33040251479`](https://github.com/respramon/marketops-id/actions/runs/33040251479)
restored that production state, suppressed 77 duplicates, and delivered zero
notifications. All of these live runs used `workflow_dispatch`; none is
claimed as schedule-triggered Track 2 proof. The affected delivery artifacts
were deleted after their `workflow.log` files were found to contain the full
Discord webhook URL. Public run metadata and job pages remain, but the deleted
artifacts are no longer available as downloadable submission evidence.

## Unattended Run Evidence

BLOCKED

No genuine GitHub Actions `schedule` run exists yet. The scheduler is disabled,
the old webhook is revoked, and the Discord GitHub Secret was removed during
incident containment. Evidence collection cannot begin until remediation and
a clean replacement delivery are verified, after which three new real
schedule-triggered live executions and their matching artifacts/screenshots
are still required. Manual live and fixture runs remain non-qualifying.

## Dashboard

PASS

The read-only FastAPI dashboard renders P1/P2/P3 cards, score explanations,
correlated evidence, source health, run metrics, replay labels, and history.
`submission/assets/dashboard.png` and `p1-card.png` are reviewed local fixture
captures and are labeled accordingly.

## Notification

BLOCKED

Manual live run `33040201783` historically delivered 16 cards across three
messages, and replay `33040251479` delivered zero after suppressing 77
duplicates. That delivery path later produced SEC-001: `httpx` INFO output put
the full webhook URL into an uploaded `workflow.log`. The affected artifacts
were deleted, the old webhook was revoked with HTTP 204, local sensitive logs
were deleted, and the stale GitHub Secret was removed. No current Discord sink
is configured. Notification returns to PASS only after the two-layer
remediation is published and a new webhook completes a clean artifact-verified
delivery test.

## README

PASS

The guide explains the problem, intended research user, Sectors dependence,
automated workflow, score, local/live commands, evidence boundaries, tests,
and non-trading positioning.

## Security Audit

BLOCKED

Repository scans did not find a committed production credential, but that
scope missed generated workflow artifacts. SEC-001 confirms that three public
artifacts contained the full Discord webhook URL. Containment is complete;
remediation is committed locally (`2e51bd8`) and green on the full local gate,
but not yet pushed, public-CI-verified, or safely exercised.
All three affected artifact IDs now resolve absent/404. A post-containment scan
of six remaining MarketOps artifacts (38 files) and 9/9 accessible job logs
returned zero findings for the defined credential patterns.
The structured finding and exact recovery sequence are in
`docs/security-audit.md`.

## Demo Assets

PARTIAL

Local dashboard, P1 card, architecture, public CI, and hosted-deduplication QA
captures are present. Visual timeline MP4s, scripts, captions, storyboard, and
assembly instructions are present, but the existing MP4s/captions predate
SEC-001 and require regeneration. Scheduled Actions history/detail remain
intentionally pending until genuine schedule events exist. The old
artifact-derived Discord summary is historical and must not be used as current
safe-delivery proof; a replacement capture is required after remediation.

## Submission Package

PARTIAL

Problem statement, description, Track 2 justification, social copy, checklist,
scripts, captions, storyboard, and video assembly guide are present. The public
repository URL is inserted. Public video URLs, genuine scheduled-run evidence,
and portal entry still require external actions. Authenticated live Sectors QA
remains historical engineering evidence. Current safe webhook delivery and
artifact evidence must be regenerated after SEC-001 remediation.

## Current Blocker

`[BLOCKED: SECURITY REMEDIATION + HUMAN ACTION REQUIRED]` SEC-001 is contained,
but its two-layer fix, though committed locally (`2e51bd8`) and green on the
full local gate, is not yet pushed or public-CI-verified, there is no current
Discord webhook secret, and the scheduler is disabled. Genuine schedule count
remains zero.

## Next Action

Push the committed remediation (`2e51bd8`) and confirm public CI is green. Then
create a new Discord webhook through the account owner, store it only in GitHub
Secrets, perform and inspect one safe manual delivery, and only then re-enable
the weekday scheduler. Three later genuine `schedule` runs must still be captured
before recording the final judging video.
