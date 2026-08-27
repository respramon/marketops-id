# Official Rules Verification

MarketOps ID rule review for **Sectors Hackathon Indonesia 2026**.

- Initial verification date: **2026-08-26**
- Latest re-verification date: **2026-08-27**
- Verification timezone: **Asia/Jakarta (WIB, UTC+7)**
- Declared track: **Track 2 — Automation & Workflows**
- Team format: **Solo participant (team of one)**
- Onboarding gate: **PASS — the participant explicitly confirmed completion before project implementation began**

## Official Sources

Only the following official pages were used for this compliance review:

1. [Sectors Hackathon 2026 homepage](https://hackathon.sectors.app/)
2. [Official rules](https://hackathon.sectors.app/rules)
3. [Track 2 — Automation & Workflows](https://hackathon.sectors.app/tracks/automation-workflows)

The implementation must be rechecked against these pages immediately before final submission. If the official rules or portal differ from this document, the official source controls.

## Re-verification — 2026-08-27

The four official sources named in the task were re-opened on 2026-08-27 WIB.
No material requirement changed from the 2026-08-26 table below. In particular:

| Check | Status | Implementation impact |
|---|---|---|
| Build/submission dates and public-repository/video requirements | VERIFIED | Continue to keep the repository public, remove credentials, and complete all artifacts before the submission freeze. |
| Track 2 autonomous-run requirement | VERIFIED | A manual or fixture replay remains insufficient; the judging video must show the configured schedule together with real unattended-run evidence. |
| Sectors core-data and no-trading boundaries | VERIFIED | Keep the six v2 capabilities on the critical path and keep the research-triage disclaimer on every product surface. |
| v2 documentation and raw `Authorization` header example | VERIFIED | Keep the typed v2 client; do not fall back to v1 or add a `Bearer` prefix. |

The original per-row verification dates are retained as an audit trail; this
section records the latest official-source re-check.

## Compliance Table

| Requirement | Official source | Verification date | Status | Impact on implementation and submission |
|---|---|---:|---|---|
| Registration opened on 19 August 2026. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | VERIFIED | The event is open and the current build date is within the official period. |
| Registration closes on **22 September 2026 at 23:59 WIB**. | [Homepage](https://hackathon.sectors.app/), [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | HUMAN PORTAL CHECK REQUIRED | The participant must complete or confirm solo-team registration in the hackathon portal before this deadline. Local code cannot prove portal registration. |
| The build period runs from **19 August 2026 through 30 September 2026 at 23:59 WIB**. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | VERIFIED | Project implementation may proceed on the verification date. All implementation and fixes must finish before submission/freeze. |
| Submission closes on **30 September 2026 at 23:59 WIB**; the server determines whether it is on time. | [Homepage](https://hackathon.sectors.app/), [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | PENDING HUMAN SUBMISSION | Finish and submit early enough to avoid a deadline or upload failure. |
| Judging is asynchronous from **1–8 October 2026**; winners are announced **9 October 2026**. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | VERIFIED | There is no live presentation. The repository, judging video, and submission copy must explain and prove the project without presenter assistance. |
| The competition is open to Indonesian citizens or residents domiciled in Indonesia. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | HUMAN ELIGIBILITY CONFIRMATION REQUIRED | The participant must confirm this eligibility fact in the portal; it cannot be inferred from the workspace. |
| All ages may participate; a participant under 18 needs parent/guardian consent covering media publication and prize acceptance. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | HUMAN CHECK / NOT APPLICABLE IF 18+ | Obtain and retain the required consent if the participant is under 18. |
| Employees, contractors, judges, mentors, and organizers of Supertype, Sectors, and Algoritma, and their immediate families, are ineligible. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | HUMAN ELIGIBILITY CONFIRMATION REQUIRED | The participant must verify that no exclusion applies. |
| Solo participation is allowed and a solo participant is treated as a team of one. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | PASS | MarketOps ID can be entered by the current solo participant. Use one participant name and one official representative in submission materials. |
| Each participant may register on only one team, and each team may submit only one project. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | HUMAN CONFIRMATION REQUIRED | Do not join another team or submit this project, or another project, as a second entry. |
| Every participant must create a Sectors account and fully complete Sectors App onboarding **before any project code is written**. | [Homepage](https://hackathon.sectors.app/), [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | PASS — USER CONFIRMED | The sole participant answered that onboarding was completed; the first mandatory human gate is satisfied. Preserve evidence if the portal exposes onboarding status. |
| A team whose participant has not completed onboarding by the registration deadline may be invalid. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | PASS BY USER CONFIRMATION; PORTAL VERIFICATION PENDING | Ensure the portal reflects the completed onboarding before 22 September 2026. |
| A registered team receives **1,000 Sectors API credits** after all members complete onboarding. Claiming credits locks the roster. | [Homepage](https://hackathon.sectors.app/), [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | HUMAN PORTAL ACTION / NOT VERIFIED | The solo participant should claim the grant through the team page when ready. The roster becomes final after claim. |
| Creating additional accounts to obtain extra credits for the same project is prohibited. Credits are only for this competition project during the build period. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | REQUIRED | Use one eligible account and implement an API-budget guard. Do not attempt to extend the allowance through another account. |
| No project code may have been written before 19 August 2026. Planning, research, sketches, and designs before the window were allowed. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-27 | PASS | The repository and complete project history begin on 27 August 2026; first commit `6cd9e80` introduced the implementation inside the build window. Recheck history at freeze. |
| The project repository must be created during the build period. Judges may inspect commit history. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-27 | PASS | GitHub reports repository creation at `2026-08-27T03:09:50Z`; first commit `6cd9e80` is dated `2026-08-27T10:09:30+07:00`, both within the build period that began 19 August 2026. |
| Public templates, boilerplate, frameworks, libraries, and public open-source code are allowed if they are not a finished product; the first commit must be in the build period. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | REQUIRED | Dependencies and ordinary scaffolding are allowed. MarketOps ID itself must be built during the competition. |
| The project must be exclusive to Sectors Hackathon, contain no work migrated from previous projects, and not be submitted to another competition or hackathon. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | HUMAN AND REPOSITORY CONFIRMATION REQUIRED | Maintain clean provenance and do not cross-submit MarketOps ID. |
| AI coding tools, including generation and agents, are permitted without a disclosure requirement. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | PASS | Autonomous implementation assistance is permitted; judging evaluates the result. |
| Every project must use Sectors MCP or the Sectors REST API as a **core data source**, not as a decorative call. The product should lose core functionality if Sectors data is removed. | [Official rules](https://hackathon.sectors.app/rules), [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | IMPLEMENTATION AND DEMO PROOF REQUIRED | Sectors must drive discovery, evidence enrichment, correlation, research scoring, and queue output. Saved fixtures may support deterministic development but must not be represented as live data. |
| The project must be a working prototype or MVP with an end-to-end core workflow. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | IMPLEMENTATION AND QA REQUIRED | The scheduled ingestion-to-notification path must actually run. Claims in submission copy must match verified functionality. |
| Live deployment is not required; a public repository and judging video showing the end-to-end workflow can satisfy the product-works gate. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | VERIFIED | A reliable local/dashboard demo plus public repo and video is acceptable, but Track 2 still requires genuine autonomous-run evidence. |
| Technology stack, tools, language, platform, and license are unrestricted; no specific open-source license is required. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | PASS | Python, SQLite, GitHub Actions, and a conventional repository license are permitted. |
| Track 2 is for products in which Sectors data operates inside real, recurring routines. | [Official rules](https://hackathon.sectors.app/rules), [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | REQUIRED | Position MarketOps ID primarily as a recurring autonomous research workflow; the score and dashboard support that workflow. |
| The automation must run on a **schedule or trigger without human intervention per cycle**. | [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | IMPLEMENTATION REQUIRED | Provide a real scheduled workflow. `workflow_dispatch` may be offered for testing, but a manual-only run does not qualify. |
| The judging video must show schedule/trigger configuration together with logs, timestamps, or screenshots of unattended runs. | [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | UNATTENDED EVIDENCE PENDING | Genuine scheduled executions require external GitHub Actions time to occur. Capture the schedule, trigger type, run timestamps, logs/artifacts, and notification result before recording the judging video. |
| A manual run without unattended evidence is insufficient for Track 2. | [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | CRITICAL / PENDING EVIDENCE | Fixture/manual executions validate engineering but cannot replace proof of scheduled runs. |
| Workflows firing on market events, daily scheduled pipelines, condition-driven alert bots, custom scripts, n8n, messaging bots, and CI schedulers are examples that qualify. | [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | VERIFIED | GitHub Actions scheduling plus webhook delivery is a valid architecture if it runs unattended. |
| An AI/LLM component is optional for Track 2. | [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | PASS | The deterministic, explainable scoring engine does not need a black-box model. |
| An autonomous pipeline that also produces scores may fit Track 2 or Track 3; the team chooses the track matching its fundamental purpose. | [Official rules](https://hackathon.sectors.app/rules), [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | PASS WITH POSITIONING REQUIREMENT | Select Track 2 and consistently explain that autonomous monitoring and delivery are the product core; scoring is a triage stage. |
| If a project misses its declared track requirement, judges may move it to another fitting track rather than disqualify it; a project fitting no track may be disqualified. | [Official rules](https://hackathon.sectors.app/rules), [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | REQUIRED | Make Track 2 qualification unmistakable through genuine scheduled-run evidence. Use official Slack `#discussion` for an unresolved track interpretation. |
| Automated trade execution is prohibited in every track. Analysis, screening, scoring, alerting, and decision support are allowed, but real/brokerage-connected buy or sell execution is not. | [Official rules](https://hackathon.sectors.app/rules), [Track 2](https://hackathon.sectors.app/tracks/automation-workflows) | 2026-08-26 | REQUIRED | Do not add brokerage connections or order placement. MarketOps ID must stop at monitoring, triage, and evidence-linked notification. |
| Projects must not provide financial advice and must be positioned as information and analysis tools, not investment recommendations. A disclaimer should appear where relevant. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | IMPLEMENTATION AND CONTENT QA REQUIRED | UI, reports, notifications, README, and videos must say “Research triage only” and must not contain BUY/SELL recommendations, target prices, trading signals, or performance promises. |
| Submission must be made through the hackathon portal. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | HUMAN PORTAL ACTION REQUIRED | Automation can prepare artifacts and copy but cannot complete authenticated portal submission for the participant. |
| Submission requires a **public repository link**. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-27 | PASS | The repository is public at [respramon/marketops-id](https://github.com/respramon/marketops-id) and was verified in a logged-out browser. Keep it public through the required retention period. |
| The repository must remain public for at least 90 days after winners are announced. Making it private sooner forfeits prize eligibility. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | POST-SUBMISSION HUMAN OBLIGATION | Keep the repository public for at least 90 days after 9 October 2026. |
| All API keys must be removed before submission. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | SECURITY AUDIT REQUIRED | Store secrets only in environment variables or GitHub Secrets. Scan the working tree and Git history before freeze. Never place real keys in screenshots, artifacts, logs, or demo video. |
| Submission requires a **one-minute teaser video** showing the product working, published publicly on YouTube or social media. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | PUBLIC VIDEO AND HUMAN UPLOAD PENDING | Produce a real screen-recording teaser at a safe duration of no more than 60 seconds; the internal 55–58 second target is appropriate. Human authentication is required to upload/publish it. |
| Submission requires a judging video of **up to three minutes** covering the problem, intended audience, and core workflow. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | VIDEO AND HUMAN UPLOAD PENDING | Keep the final cut at or below 3:00. Public or unlisted YouTube/Vimeo, link-shared Google Drive, and Loom are accepted; verify anonymous access. |
| Submission requires a one-sentence problem statement explaining who the product is for and what problem it solves. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | SUBMISSION COPY REQUIRED | Keep the statement specific to Indonesian equity research analysts and autonomous research triage. |
| Submission requires track selection and participant names. The homepage additionally describes a “team snapshot.” | [Homepage](https://hackathon.sectors.app/), [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | COPY READYING AND PORTAL CHECK REQUIRED | Select Track 2, list the solo participant, and prepare a concise team snapshot in case the portal requests it. Follow the actual portal fields. |
| Submission requires a social media post publishing the project and tagging the official Sectors account. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | SOCIAL POST AND HUMAN AUTHENTICATION PENDING | Prepare final copy and media. The official handle is not specified on the three reviewed pages; verify it from the portal or an official channel instead of guessing. Human account access is required to publish. |
| Submission and videos may use Bahasa Indonesia or English; neither is favored in scoring. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | PASS | Bahasa Indonesia, English, or carefully reviewed bilingual assets are acceptable. |
| Submitting freezes both repository and application immediately, or they freeze at the deadline, whichever occurs first. No commits, pushes, edits, changes, or bug fixes are allowed afterward. | [Homepage](https://hackathon.sectors.app/), [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | CRITICAL FINAL-GATE REQUIREMENT | Run final tests, verify public artifacts, capture evidence, finish all commits, and freeze before clicking submit. Do not modify the project afterward. |
| The only freeze exception is a leaked credential: notify official Slack `#support`, revoke and rotate it first, then push a commit containing only its removal. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | CRITICAL INCIDENT PROCEDURE | A credential leak is a submission blocker. Follow the official exception exactly; do not bundle other fixes. |
| Eligibility checking is pass/fail and verifies a complete submission, a working product, Sectors as a core source, and onboarding for every participant. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | FINAL QA REQUIRED | The final checklist and video must provide direct evidence for all four conditions. |
| Scoring weights are **Real-world usability 40%**, **Video demo & storytelling 30%**, and **Technical depth & execution 30%**. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | VERIFIED | Optimize for a usable zero-click analyst workflow, a clear evidence-backed story, and code/tests that judges can inspect. |
| By submitting, participants permit Sectors and Supertype to display and promote submission materials without additional compensation. Project IP remains with participants. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | ACKNOWLEDGED | Use only publishable data/assets, preserve third-party attribution, and avoid confidential information in screenshots and videos. |
| Projects must not infringe third-party intellectual property and must comply with the event code of conduct. | [Official rules](https://hackathon.sectors.app/rules) | 2026-08-26 | CONTENT AND LICENSE REVIEW REQUIRED | Review fixture provenance, images, fonts, code licenses, and all public copy before submission. |

## Official Wording Excerpts

Short excerpts retained to anchor the highest-risk interpretations:

> “Every participant finishes onboarding before project code is written.”

Source: [Sectors Hackathon 2026 homepage](https://hackathon.sectors.app/)

> “The product should lose its core functionality if Sectors data is removed.”

Source: [Official rules](https://hackathon.sectors.app/rules)

> “A workflow that requires a human to manually run it each time does not qualify for this track.”

Source: [Track 2 — Automation & Workflows](https://hackathon.sectors.app/tracks/automation-workflows)

## Internal Standards Versus Official Minimums

The following project decisions are intentionally stronger or more specific than the published rules and must not be presented as official requirements:

- The official Track 2 page does **not** specify a numeric minimum of unattended runs. MarketOps ID targets at least three genuine scheduled runs to make the evidence convincing.
- The official Track 2 page does **not** require GitHub Actions specifically. It explicitly allows CI schedulers and other autonomous platforms; GitHub Actions is the chosen implementation.
- **07:17 WIB** is a product scheduling decision, not an official rule. The official requirement is autonomous operation on a schedule or trigger.
- The official page calls for a “one-minute teaser” but uses the explicit phrase “up to three minutes” only for the judging video. MarketOps ID will use a conservative teaser duration of no more than 60 seconds.
- A live deployment is not mandatory, but it can improve usability evidence if it is secure and stable.
- The reviewed pages require the social post to tag the official Sectors account but do not identify a handle. The handle must be verified from the portal or an official Sectors channel at publication time.

## Current External Blockers

These items cannot truthfully be marked complete from the local workspace alone:

1. Confirm eligibility facts and solo registration in the hackathon portal.
2. Confirm or claim the 1,000-credit grant and retain portal evidence.
3. Verify repository creation/first-commit dates are within the build period.
4. Create and verify an anonymously accessible public GitHub repository.
5. Add real credentials only through secure environment/GitHub Secrets mechanisms.
6. Accumulate and capture genuine scheduled unattended GitHub Actions runs.
7. Perform authenticated webhook delivery proof using the participant's webhook secret.
8. Publish the teaser video and judging video and verify their public/unlisted accessibility.
9. Publish the required social post using the verified official Sectors handle.
10. Submit through the authenticated hackathon portal only after final QA and freeze.

## Pre-Submission Reverification

Immediately before submission:

1. Reopen all three official URLs above and compare dates, requirements, video constraints, and portal fields.
2. Verify repository visibility anonymously and confirm all required video/social links work without owner authentication.
3. Confirm Sectors is visibly essential in the implementation, README, and judging video.
4. Confirm the judging video shows the schedule/trigger plus unattended run evidence rather than only `workflow_dispatch`.
5. Run secret scans over both the working tree and Git history.
6. Complete final tests, artifacts, evidence capture, and submission copy before the freeze-triggering portal submission.
7. After submission, do not commit, push, edit, or otherwise change the repository or application unless following the official leaked-credential exception.
