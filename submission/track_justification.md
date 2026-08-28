# Track 2 Justification: Automation & Workflows

MarketOps ID belongs in Track 2 because its primary product value is a recurring
routine that completes without a person initiating each cycle. The Research
Attention Score is one stage inside that workflow; it is not the product's
fundamental purpose.

## The Recurring Routine

```text
Weekday schedule at approximately 07:17 WIB
  -> Sectors API v2 discovery
  -> canonical event normalization
  -> candidate selection
  -> selective Sectors enrichment
  -> evidence correlation per ticker
  -> deterministic Research Attention Score
  -> persistent duplicate suppression
  -> prioritized research queue
  -> webhook notification
  -> logs, run state, and audit artifacts
```

The dashboard is deliberately read-only: it shows work a completed pipeline run
has already produced. `workflow_dispatch` and the CLI remain available for
testing and incident diagnosis, but they are not presented as Track 2
qualification.

## Why Sectors Is Core

Sectors supplies all live inputs that make the workflow useful:

- filings and suspensions discover event-driven research candidates;
- top one-day changes discover material market movement;
- ticker-linked news provides context across selected candidates;
- foreign-flow history is transformed into an explainable anomaly ratio;
- corporate actions identify upcoming evidence for review;
- source references and URLs give the analyst provenance.

Without Sectors, MarketOps ID has no live candidate universe, correlated
evidence, score inputs, or research queue. The sanitized fixture adapter exists
only for zero-credit deterministic testing and is visibly marked as replay.

## Unattended Operation and Auditability

The production scheduler is designed to restore persistent SQLite state, run in
live mode, upload logs and report artifacts, and save updated state for the next
weekday. Each `RunReport` records trigger, timestamps, status, source health,
events, new/duplicate counts, candidates, notification count, and estimated
credits. The event fingerprint is stable across runners, so repeated evidence
is not re-alerted. The scheduler is currently disabled during SEC-001
containment.

The same production path was exercised through public manual Actions QA.
An authenticated live run historically delivered 16 pending research cards across three
Discord messages after batching by both embed count and aggregate text size.
Its identical live replay restored production state, recognized 77 duplicates,
and sent zero notifications. The live reports were `PARTIAL` only because the
news source visibly hit its configured record cap; they never presented that
gap as an all-clear. The delivery artifacts are no longer public: a later audit
found the full webhook URL in three `workflow.log` files, and those artifacts
were deleted. See `evidence/manual-live-qa.md` for the incident-aware audit
trail.

## Qualification Evidence Status

`[BLOCKED: AWAITING GENUINE SCHEDULED RUNS]`

The local pipeline, public CI, artifact upload, cross-run state restore,
authenticated Sectors calls, notification, and artifact security are verified.
SEC-001 is remediated: the two-layer fix passed public CI and a newly issued
webhook completed clean delivery run [`33155463943`](https://github.com/respramon/marketops-id/actions/runs/33155463943) (18 cards,
zero errors, webhook-free artifact), and the scheduler is re-enabled. Every
public production QA run so far still has event `workflow_dispatch`; a manual
run is not enough for Track 2. The owner must capture at least three later
genuine GitHub Actions runs whose event is `schedule`, along with clean logs,
artifacts, timestamps, state restoration, and notification results. Those real entries belong in
`evidence/unattended-runs.md` and must appear in the judging video.

## Scope and Safety

MarketOps ID stops at monitoring, correlation, research triage, scoring,
alerting, and decision support. It never produces BUY/SELL advice, target
prices, trading signals, or brokerage execution.
