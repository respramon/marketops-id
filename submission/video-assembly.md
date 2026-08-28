# Video Assembly and Truth-Labeling Guide

This guide covers the 57-second teaser and the 2:48 judging video. It does not
authorize substituting a manual run, fixture replay, mock notification, or a
workflow configuration screen for live scheduled-run proof.

## Before Recording

1. Start from the matching script and captions in this directory.
   The existing SRT files predate the SEC-001 narration update and must be
   regenerated before assembly.
2. Inspect every source screen for browser profiles, API keys, webhook URLs,
   private repositories, hidden tabs, and notification previews that could be
   mistaken for a real delivery.
3. For fixture media, keep this exact banner legible in the frame:

   ```text
   SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA
   Used for deterministic testing and demo.
   ```

4. For Track 2 qualification media, verify the evidence first against
   `evidence/unattended-runs.md`. The action event must be `schedule`, the mode
   must be `live`, and the run ID/timestamps/artifact name must agree.

## Required Labels

| Surface | Required label |
|---|---|
| Fixture dashboard, report, replay, or notification preview | `SANITIZED HISTORICAL REPLAY - NOT LIVE MARKET DATA` |
| Manual GitHub Actions dispatch | `Manual test — not scheduled-run proof` |
| Workflow YAML or architecture diagram before a real schedule run | `Configured locally — currently disabled; scheduled-run evidence pending` |
| Dry-notify preview | `Preview only — no external delivery` |
| Historical Discord delivery summary | `SEC-001 CONTAINED — NOT CURRENT SAFE-DELIVERY PROOF`, `MANUAL QA`, and `NOT SCHEDULED-RUN PROOF` |
| Post-remediation manual delivery | `CLEAN MANUAL QA — NOT SCHEDULED-RUN PROOF`; show the independently scanned artifact result |
| Real schedule artifact | Show the actual `schedule` trigger, `live` mode, run ID, and timestamp; do not add an unsupported claim. |
| Real webhook result | `Delivered` only when the run artifact and destination visibly confirm it; otherwise state the actual failure/zero-delivery reason. |

## Assembly Sequence

1. Record clean source clips at 1080p. Keep critical UI text readable at the
   final export resolution.
2. Add narration according to the timestamped script, then import the matching
   `.srt` file without changing its timing unless the narration is re-recorded.
3. Use only simple cuts or short fades; do not obscure required labels with
   transitions, captions, or a presenter overlay.
4. Export the teaser at no more than 60 seconds and the judging video at no
   more than 3 minutes. Watch both exports end-to-end with audio and captions.
5. Re-verify the repository and every video link in a logged-out browser. The
   repository is already public; each unpublished video remains
   `[BLOCKED: HUMAN ACTION REQUIRED]`.

## Evidence Gates Before Publishing

- `SECTORS_API_KEY`: `[PASS]` as a GitHub Secret; authenticated live Actions QA
  succeeded. Never record or publish its value.
- Webhook delivery: `[BLOCKED]`. Run `33040201783` historically delivered 16
  cards, but its artifact contained the old webhook URL and was deleted. The
  webhook is revoked, its secret is removed, and a clean replacement run is
  required after remediation.
- Genuine GitHub Actions scheduled runs: `[BLOCKED]`. The scheduler is disabled
  during recovery, genuine count is zero, and three later `schedule` events
  must be recorded in `evidence/unattended-runs.md` after safe re-enablement.
- Public repository: `[PASS]` at <https://github.com/respramon/marketops-id>,
  verified logged out on 2026-08-27.
- Public/unlisted video links: `[PENDING]` until uploaded and accessible without
  the owner's login.

If any gate is still blocked, retain the pending disclosure in the judging
video and do not claim completion of that external step.

## Manual Live QA Shot Sequence

For a compact incident-aware engineering narrative, these public run metadata
pages may be shown in order:

1. live dry-notify run `33039796607` for authenticated Sectors ingestion;
2. delivery attempt `33039918857` and its explicit Discord HTTP 400;
3. fix commit `3f3bed7` plus green CI run `33040157886`;
4. historical delivery run `33040201783`: 16 cards, three messages, plus a
   visible disclosure that its affected artifact was deleted under SEC-001;
5. identical replay `33040251479`: 77 duplicates, zero notifications.

Keep `workflow_dispatch — manual live QA` visible throughout. This sequence is
historical technical-execution and incident-containment context only. It cannot
replace a clean post-remediation delivery or the three required `schedule`
shots. Never imply that the deleted artifacts remain downloadable.

Before final assembly, replace the historical delivery segment with the new
public CI result, a clean manually delivered notification, and a separately
scanned artifact. Only then re-enable the scheduler and capture the three later
scheduled runs.
