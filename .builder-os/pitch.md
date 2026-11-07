# Pitch: ClaimShield Desk

Date: 2026-11-07 (00:00 IST)
Appetite: ~18 hours (Fri 6 Nov ~23:50 → Sat 7 Nov 18:00 IST) — hard limit.
Circuit breaker date: Sat 7 Nov 12:00 IST — if the minimum shippable version (W1 checker + W3 appeal packet + W6 rule patch + 60-sec demo, all deterministic) is not done by this date, kill the cockpit polish and the evaluation harness and ship the API + scripted demo only.
Submission deadline: Sat 7 Nov 23:59 IST.

## Problem
A hospital TPA desk processes cashless and reimbursement claims all day. Claims come back denied or short-paid — "OPD-convertible", PED non-disclosure against an unrelated illness, room-rent proportionate deductions, delayed intimation — and the desk's response is a generic reconsideration letter written from memory. Nobody remembers which argument and document bundle reversed a similar rejection by the same insurer, because nobody records appeal outcomes. Worse, even when an appeal wins, the pre-submission checklist does not change, so the same incomplete file goes out next week and gets denied again. The desk's current tools are a spreadsheet checklist and phone calls to the insurer; the pain is measured in blocked beds, family deposits paid at discharge, and lakhs left unrecovered (PRD §2, TEAM-SUMMARY §2; 30 verified Indian judicial cases across 5 denial patterns in research pack-2).

## Solution
Fat-marker sketch: a 3-pane cockpit. Left: a live Band room stream where @ClaimAuditor drafts the appeal, @PolicyCritic vetoes weak packets, and a human clicks Approve. Centre: a Hindsight "Cognitive X-Ray" showing the recalled past wins, the observation proof counts, and the redaction toasts. Right: the repo viewer showing the scrubber rule file and its diff. Underneath: a FastAPI backend, a Hindsight memory bank that retains every verdict, and a declarative rules file the coding agent patches after approval. The flow is one workflow: denied claim in → recall past wins → draft + critic veto → human approves → rule patched → the next incomplete packet is BLOCKED before dispatch. The 60-second demo tells it in four beats: Day-1 generic appeal loses ₹1,45,000; memory redacts the SSN and recalls three wins; the critic blocks a stale 4-week PT argument citing proof_count 5; the coder commits the validator live and the next incomplete packet is blocked.

## Rabbit Holes
- Building the full 50-section PRD (W2 reimbursement pack builder, W4 Ombudsman/Bima Bharosa escalation drafts, multi-desk tenancy, OCR): the PRD itself marks these P1/P2 and out of the demo; each is a day of work that does not change the demo's verdict.
- Chasing Hindsight Cloud + Band Desktop accounts first: both need his sign-in and billing steps; the build must run on pluggable adapters with honest in-memory/local fallbacks, or the night dies waiting on accounts.
- A second workflow (e.g. a code-review agent or a churn scorer): the brief rewards one workflow done visibly; breadth is the classic way to demo nothing working.
- Perfecting the evaluation harness before the demo works: the harness proves learning, but a harness with no working demo proves nothing; demo first, harness second.

## No-gos (explicitly NOT in this version — minimum 2 items required)
- W2 reimbursement pack builder (intimation draft, discharge checklist, cover note): excluded from this version — P1 in the PRD, not in the 60-sec demo; it is a second workflow that would split the night.
- W4 escalation drafts (grievance officer, Bima Bharosa, Ombudsman, consumer commission): excluded — drafts-only P1, and the brief's support/compliance examples make it a misread risk in the demo.
- OCR / reading scanned documents: excluded — v1 checker works on a structured packet manifest only (PRD §1.8).
- Real patient data: excluded — all hospitals, patients and amounts are synthetic and badged SYNTHETIC (PRD §1.8).
- Band MCP and Band Native Memories: excluded — MCP cannot deliver room messages and Native Memories are Enterprise-only (verified, PRD §4.1).

## Reversibility Assessment
This project creates two semi-irreversible commitments: (1) the public API contract (endpoints + `scrubber_rules.json` schema) — once the cockpit and demo script depend on it, changing it rebuilds the demo; (2) the Hindsight bank template (missions, directives, tag taxonomy) — changing missions after seeding invalidates the seeded observations. Both are locked in the design note before code (Gate 4). Everything else (in-memory vs Cloud backend, SDK vs local room bus, Next.js vs static export) is a two-way door: the adapters are pluggable and the build log records which one actually ran.
