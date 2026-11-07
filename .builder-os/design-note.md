# Design Note: ClaimShield Desk architecture (Hindsight adapter + Band room bus + FastAPI + Next.js cockpit)

Date: 2026-11-07 (00:00 IST)
Project: ClaimShield Desk
Appetite remaining: ~18 hours (to Sat 7 Nov 18:00 IST)
Continues from: .builder-os/pitch.md
Triggered by: >1 day effort AND external interface change (Hindsight + Band APIs) AND irreversible decisions (API contract + bank template) — all three triggers apply.

## Context
The pitch commits to a demo in ~18 hours in which memory must be visibly load-bearing: a denied claim is recalled from past wins, a critic vetoes a stale argument with a proof count, and a coding agent patches a live rule. That requires four integrations that have never run on this VM — Hindsight 1.2, Band SDK 6.0.1 (stack versions per PRD §4), a FastAPI backend, and a Next.js cockpit — plus two external accounts (Hindsight Cloud, Band) that need the user's sign-in. If the architecture couples the demo to any one of those integrations being live, the night dies waiting on an account. The design must therefore make every external integration pluggable behind an interface with an honest fallback, while keeping the observable behaviour (recall → veto → patch → re-block) identical.

## Goals
- The 60-second 4-beat demo runs end to end deterministically (Day-1 loss ₹0 → redaction toast → critic VETO citing proof_count → live rule commit → new incomplete packet BLOCKED).
- Every claimed benefit is sourced: appeal citations trace to retrieved memory IDs (citation precision 100%, hallucinated citations 0, measured by the harness).
- Decision accuracy on the 20-case harness is measured and reported honestly (target >85% per PRD §18.1; the number reported is the measured one).
- No secret, no real patient data, and no unverified statistic reaches the repo or the UI.

## Non-Goals (minimum 2 required)
- This design does NOT cover W2 reimbursement pack builder or W4 escalation drafts — both are deferred by the pitch's No-gos, not by this note.
- This design does NOT cover multi-desk tenancy — one desk (`desk_id: hyd_01`), one shared bank `claimshield-india` with per-insurer tag scopes; tenancy is a v2 concern.
- This design does NOT cover OCR or scanned-document intake — the checker consumes a structured packet manifest only.

## Design
One FastAPI backend owns all state transitions. It exposes the contract in `docs/api/openapi.yaml` (7 endpoints: claim-intake, hindsight webhook, appeals/strategy, appeals/veto, scrubber/commit, eval/run, health, plus SSE). Memory goes through a `HindsightAdapter` interface (retain/recall/reflect + observations with proof_count): Cloud when `HINDSIGHT_API_KEY` is set, local Docker (`ghcr.io/vectorize-io/hindsight:latest` :8888, image and port per PRD §6.5 / research pack-4) when reachable, else an in-memory implementation with the same semantics. Bank template (`bank-template.json`) carries the PRD §6.4 missions/directives verbatim, mandatory tags, `tags_match: any_strict`, per-insurer observation scopes, and `DECISION_MODEL_ENABLED=false` + `ENABLE_DECISION_PRUNE=false` so recall does not depend on the decision model (verified: recall fails if the decision model is unreachable — PRD §14 and §24; TEAM-SUMMARY §7 fallback; research pack-4 decision-model section). The Band room goes through a `RoomBus` interface (@mention handoffs `@ClaimAuditor` → `@PolicyCritic` → human gate → `@ScrubberCoder`, agent handoffs per PRD §5): Band SDK room when credentials exist, else a local in-process bus with identical semantics and an honest `band_mode` flag. Design requirement: the delete test must hold either way — the veto→patch chain is specified to break when the room is removed (tested by cs-005; see failure-mode row 2). The checker is a declarative `scrubber_rules.json` (PRD §6.6 schema) with versioned history and rollback; the coding agent patches it only after human approval and only after `pytest tests/test_scrubber.py` passes. The cockpit is Next.js 14+ with three panes fed by REST + SSE (last-50 replay, gated on `consolidation.completed`, webhook event per PRD §6.2). PII is scrubbed deterministically (PAN/Aadhaar/mobile regexes) before any retain; native Memory Defense covers only `ssn_us` + `credit_card` (verified: Hindsight Memory Defense docs via research pack-4; PRD §6.7) and is the second layer, and the UI toast labels which layer caught what.

## Alternatives Considered (minimum 1 required)
1. Plain RAG (vector DB over past appeals, no Hindsight observations) — Rejected because: it returns similar-sounding appeals including ones that lost, carries no outcome-labelled proof counts, and cannot support the critic's "this argument was invalidated by the Oct 2026 bulletin" veto; the PRD §2.3 gap analysis and the Hindsight Memory judging weight of 25% (problem-statement doc judging criteria; PRD §1) both require outcome memory, not similarity search.
2. LangGraph crew instead of the Band room — Rejected because: the hackathon requires Band ("download and use Band AI desktop", problem-statement §33–35) and the PRD's delete test is defined on the Band room; a LangGraph crew would satisfy the coordination need but forfeit the Band criterion and the room-stream demo pane. Band SDK is also the verified path — Band MCP cannot deliver room messages (PRD §4.1).
3. Streamlit single-page UI instead of the Next.js 3-pane cockpit — Rejected because: PRD §7 locks the Next.js cockpit, and the demo needs the room stream, the memory X-Ray and the repo diff visible simultaneously; a single scrolling page would hide the veto and the patch from each other at the moment the judges need to see both. (Streamlit remains the fallback only if Node 22 cannot be installed on the VM, recorded as a dated exception in the build log.)

## Rabbit Holes
- Writing a custom Hindsight client from scratch instead of using the adapter + `hindsight-client`: the PRD's verified mechanics (webhook HMAC, dedupe on event_id, fs mount) are the contract; re-implementing them burns the night.
- Making the in-memory fallback "smart" (embeddings, reranking): it only needs keyword + tag-scoped retrieval that is honest about being a fallback; fake sophistication would be invented capability.
- Hand-rolling the Band room protocol: the RoomBus interface is the seam; anything deeper is Band SDK's job or the local bus's exact @mention semantics, nothing more.

## Cross-cutting Concerns
- Security: claim text is untrusted data, never instructions (poisoned-packet adversarial case must still VETO); webhook HMAC-SHA256 (PRD §6.2) + dedupe; no secrets in repo (secret-scan Gate 6); PII scrubber before retain.
- Performance: appeal strategy <5s, demo end-to-end 60s (PRD §9); SSE replay bounded to last 50 events.
- Backward-compatibility: API contract versioned (`/v1/` implied by OpenAPI 3.1 doc); `scrubber_rules.json` versions are append-only with rollback via `is_active`.
- Monitoring: what proves this design works — `/health` reports real `memory_backend` + `band_mode` + `rules_version`; the harness writes measured accuracy/citation numbers; the demo script asserts all four beats.

## Top-3 Failure Modes (failure-mode-analyzer)
| # | Failure Mode | User-Visible Impact | Strategy (Prevent vs Tolerate) | Local Test Simulation |
|---|---|---|---|---|
| 1 | Hindsight unreachable / decision model unreachable (recall fails) | Cockpit shows no recalled wins; appeal packet has no citations | Tolerate: adapter falls back (Cloud → Docker → in-memory); `DECISION_MODEL_ENABLED=false` + `ENABLE_DECISION_PRUNE=false` by default so recall never depends on the decision model | Kill the Hindsight endpoint in a test and assert recall still returns seeded wins from the fallback; assert `/health` reports the fallback honestly |
| 2 | Band room decorative or disconnected (no @mention handoff) | Critic never vetoes; rule patch never fires; demo shows a chat log, not coordination | Prevent: delete test — veto→patch chain must break without the room; every @mention handoff is recorded as a visible tool-call event in the SSE stream (design requirement); queue + retry on disconnect with SSE replay | Disable the room bus in a test and assert `/scrubber/commit` is refused and no packet reaches patch; assert the handoff events appear in the SSE stream when enabled |
| 3 | Memory Defense misses Indian IDs (PAN/Aadhaar) | Real PII retained in the bank and shown in the UI | Prevent: deterministic backend scrubber (PAN/Aadhaar/mobile regexes) runs BEFORE retain; native MD is only the second layer for ssn_us/credit_card (PRD §6.7; research pack-4); UI toast labels the layer | Feed a packet containing PAN + Aadhaar + mobile in a test and assert none appears in any stored record or log, and `pii_scrubbed[]` lists all three |

## FCAR Status
- Round 1 (fresh-context reviewer, 2026-11-06 ~23:47 IST): 4/5 PASS, item 3 FAIL — two claims lacked named sources in the artifact ("native Memory Defense (ssn_us/credit_card only)" and "recall never fails on an unreachable decision model"). Revised same night: both claims now cite PRD §6.7/§14/§24, TEAM-SUMMARY §7, research pack-4, and the absolute "never fails" is reworded to the sourced, bounded "does not depend on the decision model".
- Round 2: re-dispatched to a new fresh-context reviewer (see build-log)
- Round 2 verdict (~23:49 IST): 4/5 PASS, item 3 FAIL again — one new claim lacked a named source ("the 25% Hindsight judging weight" in Alternatives #1). Revised same night: the figure now cites the problem-statement doc judging criteria + PRD §1. Round 3 re-dispatched to a new fresh-context reviewer. (Note: the artifact was scanned for other bare figures while fixing this — appeal <5s and 60s demo cite PRD §9, >85% cites PRD §18.1, 100%/0 citations are harness-measured, MCP cites PRD §4.1.)
- Round 3 verdict (~23:52 IST): 4/5 PASS, item 3 FAIL again — two more claims flagged: "`emit=TOOL_CALLS` ON so handoffs are visible" and "The delete test holds either way". Revised same night: the `emit=TOOL_CALLS` line is reworded from an asserted SDK fact to a design requirement (handoff recorded as a visible tool-call event in the SSE stream), and the delete-test line is reworded from an asserted fact to a stated design requirement tested by cs-005. A full-figure sweep was done at the same time: Docker image/port now cites PRD §6.5, agent handoffs PRD §5, `consolidation.completed` PRD §6.2, HMAC PRD §6.2, stack versions PRD §4, MD coverage in the failure table PRD §6.7. Round 4 re-dispatched to a new fresh-context reviewer.
- Round 4 verdict (~23:53 IST): 5/5 PASS — all rubric items pass. Gate 4 CLOSED.
[x] FCAR passed (all rubric items)
[ ] FCAR passed with documented exception: [exception text here]
