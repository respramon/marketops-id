# Manual Live QA Evidence

This file records production-shaped validation performed on 2026-08-27 and
the security containment that followed. Every run here was triggered by
`workflow_dispatch`; none is genuine scheduled Track 2 evidence.

## Current Evidence Boundary

- `mode: live` means Sectors Financial API v2 was called with the configured
  GitHub Secret.
- `trigger: manual` / GitHub event `workflow_dispatch` means QA, not unattended
  schedule proof.
- The delivery and replay counters below were verified before containment and
  remain historical facts.
- They are **not current downloadable artifact proof**. Affected artifacts were
  deleted after SEC-001 confirmed that `workflow.log` contained the full
  Discord webhook URL. Only public run metadata/job pages remain for those
  affected runs.
- This Markdown file contains no credential value. It must never be used to
  claim that no artifact leaked.

## Run Sequence

| Stage | Public Actions run | Pipeline run ID | Historical result / current evidence state |
|---|---|---|---|
| Live dry-notify | [`33039796607`](https://github.com/respramon/marketops-id/actions/runs/33039796607) | `run-20260827-113414-15d21a` | Authenticated live ingest completed `PARTIAL`: 77 events, 33 candidates, 16 preview cards, 0 deliveries, 15/15 estimated credits. The only warning was the explicit news record-cap gap. |
| First real delivery attempt | [`33039918857`](https://github.com/respramon/marketops-id/actions/runs/33039918857) | `run-20260827-113643-c3009f` | Live ingest completed, but Discord rejected the oversized payload with HTTP 400. Zero notifications were recorded and the cards remained pending. Artifact `9633450679` contained one webhook-URL occurrence and was deleted. |
| Limit-safe notifier fix | [`commit 3f3bed7`](https://github.com/respramon/marketops-id/commit/3f3bed7) / [CI `33040157886`](https://github.com/respramon/marketops-id/actions/runs/33040157886) | n/a | Delivery batching by Discord's embed-count and aggregate-text limits passed the then-current public tests. This fix addressed payload size, not the later log-disclosure finding. |
| Successful live delivery | [`33040201783`](https://github.com/respramon/marketops-id/actions/runs/33040201783) | `run-20260827-114228-5b57a4` | Historically delivered 16 pending cards across three messages; 77 events, 33 candidates, and 15/15 estimated credits. Artifact `9633552799` contained three webhook-URL occurrences and was deleted. The public run page remains, but its source artifact is unavailable. |
| Identical live replay | [`33040251479`](https://github.com/respramon/marketops-id/actions/runs/33040251479) | `run-20260827-114322-84b6e0` | Historically restored production state, recognized 77 duplicates, and sent zero notifications. This remains manual QA and cannot fill a scheduled-run slot. |

The successful delivery contained zero newly discovered events because it
restored state written by the earlier failed-delivery attempt. That historically
verified the intended retry eligibility: an event becomes ineligible only
after at least one configured real sink succeeds.

## Fixture Webhook Control

The webhook path was also exercised without Sectors credit use:

| Public Actions run | Mode / trigger | Historical result / current evidence state |
|---|---|---|
| [`33039840251`](https://github.com/respramon/marketops-id/actions/runs/33039840251) | `fixture` / `workflow_dispatch` | Historically delivered five Discord cards. Artifact `9633422018` contained one webhook-URL occurrence and was deleted. |
| [`33039882610`](https://github.com/respramon/marketops-id/actions/runs/33039882610) | identical fixture replay / `workflow_dispatch` | Historically sent zero because every event was already processed. |

Fixture runs consume zero real Sectors credits even when metadata estimates the
equivalent live cost.

## SEC-001 Containment

On 2026-08-27, a value-safe audit found five total occurrences across the three
artifact IDs listed above. Containment completed as follows:

- all three affected public artifacts were deleted irreversibly and now return
  absent/404;
- sensitive local `workflow.log` copies were deleted;
- revocation of the old Discord webhook returned HTTP 204;
- the stale `DISCORD_WEBHOOK_URL` GitHub Secret was deleted;
- the scheduler was disabled manually.

The six remaining MarketOps artifacts were audited across 38 files with zero
Discord URL/path, named-secret assignment, Authorization credential,
GitHub/AWS token, or private-key findings. All nine accessible job logs were
also scanned with zero findings. This narrows the confirmed exposure; it does
not undo the deleted-artifact disclosure.

## Quality Gates

Public CI run [`33040157886`](https://github.com/respramon/marketops-id/actions/runs/33040157886)
predates SEC-001 remediation and passed Ruff, strict mypy, installed-wheel
smoke, and 378 tests at 94.93% coverage. Current local QA on 2026-08-28 passes
Ruff, mypy across 14 source files, and 400 tests at 95.62% coverage. A new
public CI run and clean delivery artifact are still required.

## What This Proves—and Does Not Prove

The historical sequence demonstrated authenticated Sectors ingestion,
fail-soft reporting, API-budget enforcement, retry eligibility, Discord
batching, state restoration, and a quiet replay. It also exposed a real
artifact-security defect. It does **not** establish a currently safe webhook
path, a downloadable clean delivery artifact, or a GitHub scheduler firing.

Only a post-remediation clean manual delivery can restore notification proof.
Only three later `schedule` entries in
[`unattended-runs.md`](unattended-runs.md) can establish Track 2 qualification.
