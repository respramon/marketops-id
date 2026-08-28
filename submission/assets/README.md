# Demo Asset Provenance

Assets in this folder are intentionally separated by evidence type.

| Asset | Status | Provenance / permitted claim |
|---|---|---|
| `dashboard.png` | LOCAL FIXTURE CAPTURE | Captured from the running read-only dashboard after a sanitized historical replay. Its visible replay banner means it is not live market data or scheduled-run proof. |
| `p1-card.png` | LOCAL FIXTURE CAPTURE | Cropped P1 research card from the same fixture dashboard. Use only alongside the fixture disclosure. |
| `architecture.png` / `architecture.svg` | REPOSITORY DIAGRAM | Code-native architecture diagram. It shows configured design, not proof. While SEC-001 recovery is open, pair it with a visible **scheduler currently disabled** label. |
| `actions-history.png` | PENDING PLACEHOLDER | Must be replaced by a real public GitHub Actions history after three `schedule` runs. Do not use as proof. |
| `scheduled-run.png` | PENDING PLACEHOLDER | Must be replaced by a real detail page for a live schedule run. Do not use as proof. |
| `discord-result.png` / `discord-result.svg` | HISTORICAL / INCIDENT-CONTAINED SUMMARY | Records the previously verified manual delivery/replay counters and explicitly discloses SEC-001 containment. The delivery artifact was deleted after its `workflow.log` exposed the old webhook URL. This asset is **not current safe-delivery proof**, **not a Discord UI screenshot**, and **not scheduled-run proof**. Current safe-delivery proof is post-remediation run `33155463943` (18 cards, zero errors, webhook-free artifact); replace this image with a capture from it. |
| `live-manual-dashboard.png` | HISTORICAL MANUAL REPORT CAPTURE | Captured from the previously inspected manual live report. It may illustrate Sectors/correlation output only when labeled historical `workflow_dispatch` QA. It is not current delivery evidence, its source delivery artifact was deleted, and it is not scheduled-run proof. |
| `test-pass.png` | PUBLIC CI CAPTURE | Logged-out capture of successful public [GitHub Actions run `33040157886`](https://github.com/respramon/marketops-id/actions/runs/33040157886) for notifier fix `3f3bed7`. The run passed Ruff, mypy, 378 pytest tests with 94.93% coverage, and installed-wheel smoke. It is push-triggered CI, not scheduled-run proof. |
| `test-pass.svg` / `test-pass-local.png` | LOCAL QA SUMMARY | Current local result captured 28 Aug 2026 WIB after Ruff, mypy across 14 source files, and pytest passed: 400 tests and 95.62% coverage. It is not GitHub Actions evidence. |
| `hosted-dedupe-qa.png` / `hosted-dedupe-qa.svg` | PUBLIC MANUAL QA SUMMARY | Derived only from the two public `workflow_dispatch` fixture artifacts. It shows state restoration and duplicate suppression, and visibly states that it is not scheduled-run proof. |

The visual-only MP4 files in `submission/` are intentionally named
`no-voice`. They are pre-incident assembly timelines, not public submission
videos, and must be rebuilt to include the SEC-001 status. Regenerate matching
SRT files, replace pending evidence shots, and only then add approved narration.

The Discord summary may be used only when the historical, manual, containment,
and non-proof labels remain legible. It must not appear as current notification
evidence. After the two-layer logging/artifact remediation is public and a new
webhook passes a clean run, replace or supplement it with a redacted destination
capture and an independently scanned artifact; never expose the webhook URL.
