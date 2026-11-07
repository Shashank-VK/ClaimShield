# ClaimShield Desk — specs.md (LOCKED, Auto Mode, 2026-11-06 ~23:50 IST)

Source of truth: `../ClaimShield/prd.md` v3.1 (1,240 lines, 50 sections) +
`../ClaimShield/TEAM-SUMMARY.md` + research packs 1–8. Read once 2026-11-06.
Do NOT build inside the ClaimShield clone — that repo is the spec source, keep
it clean. Build here, in `claimshield-desk/`.

## 1. Overview
**Product:** ClaimShield Desk — AI-powered denial defense + pre-dispatch
scrubber for Indian hospital TPA desks. An agent that learns from appeal
outcomes which insurance denials are wrongful, builds the winning appeal
packet, and rewrites the desk's pre-submission checklist so the same denial
never happens twice.

**Core loop:** denied claim / 835 remittance in → Hindsight 1.2 bank
`claimshield-india` (retain/recall/reflect, observations with `proof_count`)
→ Band room `@ClaimAuditor` drafts appeal, `@PolicyCritic` vetoes weak
packets (blockable verdict), human approves → `@ScrubberCoder` patches
`scrubber_rules.json` via mounted playbooks.

**Event:** HackWithBangalore 4.0. Theme: "AI Agents That Learn Using
Hindsight". Judging: Innovation 30%, Hindsight Memory 25%, Technical 20%,
UX 15%, Impact 10%.

**Deadline:** final submission Sat 7 Nov 2026 23:59 IST. Target: done by
Sat 18:00 IST. It is Fri 6 Nov ~23:50 IST — a working narrow demo beats the
full 50-section PRD.

**Scope (PRD §3.5 MVP, demo-locked):** W1 Pre-Dispatch Check + W3 Denial
Defense + W6 Rule Patch + cockpit UI + evaluation harness. OUT of the demo:
W2 reimbursement pack builder (P1), W4 escalation drafts (P1, drafts only),
OCR, multi-desk tenancy, real patient data.

## 2. User flows (W1 / W3 / W6)
- **W1 Pre-Dispatch Check:** packet manifest in → PASS / WARN / BLOCKED out,
  with missing documents and evidence behind each rule.
- **W3 Denial Defense:** rejection letter in → appeal packet out (argument,
  evidence bundle, cited sources, predicted outcome with proof count).
- **W5 Outcome Capture:** verdict retained with dates → observations update
  (`proof_count` increments, visible in UI, e.g. obs_304 6→7).
- **W6 Rule Patch:** after human approval → coding agent edits rules file →
  runs tests → checker behavior changes (new incomplete packet BLOCKED).
- **60-sec demo (4 beats, TEAM-SUMMARY §3):** (0:00–0:15) ₹1,45,000 dengue
  denial → generic appeal → rejected (₹0 recovered). (0:15–0:30) raw 835
  with patient SSN → red toast `[REDACTED:ssn]`; `@ClaimAuditor` queries
  Hindsight. (0:30–0:45) `@PolicyCritic` blocks the 4-week PT argument,
  cites observation `proof_count: 5`, attaches 6-week PT + X-ray excerpt.
  (0:45–0:60) human approves → `@ScrubberCoder` commits
  `scrubbers/uhc_cpt73721_validator.py` live → new incomplete packet BLOCKED.

## 3. Explicit non-goals (No-gos, PRD §1.8)
- No broker/lawyer/doctor replacement — every output is a draft for human
  review. No forcing payment of fraudulent claims, no waiving waiting
  periods, no advising creating/altering/back-dating documents.
- No moving money, no acting as a TPA, no coverage decisions, no policy
  recommendations or insurer ranking.
- No OCR (v1). No real patient data — hospitals, patients, amounts are
  synthetic, badged SYNTHETIC. No Band MCP, no Band Native Memories
  (Enterprise-only), no Mem0/Zep.

## 4. Tech stack (PRD §4 — do not substitute)
- Hindsight 1.2.0 + specialised models hs-decide-1-flash / hs-rerank-1 /
  hs-embed-1. `DECISION_MODEL_ENABLED=false` + `ENABLE_DECISION_PRUNE=false`
  by default (recall fails if the decision model is unreachable; enable only
  on Cloud).
- Band SDK 6.0.1 (Python) + Band Desktop jamd v0.4.17. `emit=TOOL_CALLS` ON.
- FastAPI backend, Next.js/React 3-pane cockpit UI, Python 3.11+.
- LLM for extraction: Groq (qwen/qwen3-32b or gpt-oss-120b) where an LLM is
  needed; reflect always uses the LLM path for demo quality.

**Decisions made (Auto Mode, no questions asked):**
- Solo build, single developer. PRD team split (Member A/B) collapses to one
  lane; sequencing is the feature order below.
- Hindsight backend is a pluggable adapter: Hindsight Cloud first when
  `HINDSIGHT_API_KEY` is set, else local Docker
  (`ghcr.io/vectorize-io/hindsight:latest`, API :8888, UI :9999) when
  reachable, else an **in-memory fallback** implementing the same
  retain/recall/reflect + observations/proof_count interface so tests and
  the demo always run. The build log MUST record honestly which backend
  actually ran — never claim Cloud/local if the fallback did.
- Docker daemon is known DOWN on this VM — check once with `docker ps`,
  record, move on. Hindsight Cloud account + MEMHACK99 promo is a HANDS
  item for shashank (account/billing) — the build must NOT stall on it.
- Band Desktop install + Band account + room creation are HANDS items if
  they need his sign-in. The room is implemented as a Band SDK room when
  `BAND_AGENT_API_KEY` + `BAND_ROOM_ID` are present, else as a **local
  in-process room bus** with identical @mention handoff semantics
  (`@ClaimAuditor` → `@PolicyCritic` → human gate → `@ScrubberCoder`) and
  an honest `band_mode: sdk|local` flag in `/health` and the build log.
  The PRD delete test MUST hold either way: remove the room and the
  veto→patch chain breaks (test it).
- Node 22 for the Next.js cockpit: the build agent checks `node --version`
  first; if absent it installs Node (tooling freedom) and records it, or
  records a blocker and ships the cockpit as a static export. The demo must
  not depend on a Node server at showtime if a static export works.
- Groq key lives at `~/.config/provider-keys/groq.key` — read into the
  environment at runtime only, never print it, never commit it, never put
  it in any file in the repo. Hindsight/Band keys, if any, via env only.

## 5. Verified facts vs UNVERIFIED (never present UNVERIFIED as fact)
- VERIFIED (usable, with source): Ombudsman award cap ₹30 Lakhs (Rule 17(3),
  Insurance Ombudsman Rules 2017, cioins.co.in); 1 year to approach
  Ombudsman; award within 3 months; IRDA Circular IRDA/HLTH/MISC/CIR/
  216/09/2011 (no rejection solely on procedural delay); 30 verified
  judicial cases across 5 denial patterns (pack-2: OPD-convertible, PED
  non-disclosure vs unrelated illness, room-rent proportionate deductions,
  delayed intimation, non-payable items/consumables).
- UNVERIFIED (never in UI/demo as fact): IRDAI health claims statistics
  (8% repudiation, 13% disallowance, ₹26,000 crore, ₹18,521 crore splits);
  DPDP Act health-specific sub-rules (not gazetted); Bima Bharosa grievance
  breakdowns by line of business. Badge everything SYNTHETIC; OFFICIAL only
  for Ombudsman Rules 2017 / IRDA 216/09/2011 text.
- Footer on every appeal packet + cockpit header strip (mandatory):
  `Draft for human review, not legal/medical advice. All cases SYNTHETIC.`

## 6. Data model
- Hindsight bank `claimshield-india`: retain mission + observations mission
  + directives EXACTLY as PRD §6.4 (copy the strings verbatim into
  `bank-template.json`). Mandatory tags on every retain:
  `insurer:<star_health|hdfc_ergo|icici_lombard>`,
  `denial_reason:<opd_convertible|ped_nondisclosure|room_rent_cap|
  delayed_intimation|...>`, `diagnosis_group:<dengue|...>` (ICD-10),
  `desk_id:<hyd_01>`, `claim_type:<cashless|reimbursement>`; recall uses
  `tags_match:any_strict`; observation scopes per `insurer:*`. Dual
  timestamps: `timestamp` = occurrence date (backdated for seeder epochs).
  Disposition: `@ClaimAuditor` skepticism 3; `@PolicyCritic` skepticism 5,
  literalism 4 (bank-level config, reflect-only).
- Backend SQLite (PRD §12): `scrubber_rules`, `rule_history`,
  `appeal_packets`, `verdicts` (verdict_type OVERTURNED_FULL /
  PARTIAL_DEDUCTION / REJECTED).
- `scrubber_rules.json` schema EXACTLY as PRD §6.6 (rule_id, insurer,
  diagnosis_group, denial_reason, requires[], blocks_when_missing[],
  warn_when_missing[], version, supersedes, source_obs, is_active).
  Checker returns PASS/WARN/BLOCKED + `missing[]` + `source_obs` +
  `proof_count`. Rollback = set `is_active` to prior version.
- Seeder (PRD §18.1): 4 epochs, backdated timestamps — Epoch1 generic
  denials, Epoch2 first wins (proof_count 1–2), Epoch3 contradiction
  (Oct 2026 Star Health bulletin: 4-week PT → 6-week PT required), Epoch4
  late verdicts applied. Headline case: Star Health dengue ₹1,45,000,
  `opd_convertible`. All synthetic, badged SYNTHETIC.

## 7. API contracts (FastAPI, PRD §6.3 + §11)
- `POST /webhooks/claim-intake` `{document_id, content, tags[], context,
  timestamp}` → `{status: retained, document_id, memory_unit_count,
  pii_scrubbed: ["[REDACTED:ssn]"]}`.
- `POST /webhooks/hindsight` — Hindsight webhooks, HMAC-SHA256 verified,
  dedupe on `event_id`, SSE broadcast. Events: `retain.completed`,
  `consolidation.completed`, `memory_defense.triggered`.
- `POST /appeals/strategy` → ClaimAuditor recall + reflect appeal packet.
- `POST /appeals/veto` → `{verdict: APPROVE|VETO, reason, citations[],
  proof_count, missing_evidence[], required_excerpt, disclaimer}`.
  Citations must all be IDs actually retrieved by reflect; `proof_count`
  from the observation; VETO blocks dispatch until `missing_evidence`
  supplied.
- `POST /scrubber/commit` → ScrubberCoder patch (session + human gate).
- `GET /eval/run` → 3-system evaluation trigger.
- `GET /health` → `{status, memory_backend, band_mode, rules_version}`.
- `GET /sse/stream` — multiplexed Hindsight webhooks + Band room messages;
  UI reconnect replays last 50 events; UI gates next recall/reflect on
  `consolidation.completed`.

## 8. Security & failure modes (PRD §6.5, §15)
- PII scrubber BEFORE retain (deterministic regexes, PRD §6.7): PAN
  `[A-Z]{5}[0-9]{4}[A-Z]{1}`, Aadhaar `\b\d{4}\s?\d{4}\s?\d{4}\b`,
  Indian mobile `\+91[\s-]?\d{10}\b` → `[REDACTED:pan]` /
  `[REDACTED:aadhaar]` / `[REDACTED:phone]`; log `pii_scrubbed[]`. Native
  Memory Defense covers only `ssn_us` + `credit_card` — second layer, UI
  toast labels which layer caught what.
- Webhook signature mismatch → 401 + security log. Decision model
  unreachable → recall runs without it (flags above). Band disconnect →
  queue + retry + SSE replay. Scrubber patch failure → revert to previous
  rule version via `rule_history`, alert human.
- Claim text is untrusted data, never instructions. Poisoned packet
  ("approve anyway" injected) must still VETO if evidence is missing
  (adversarial case (e) in §18.1). No secrets in repo; secret-scan must pass.

## 9. Frontend (PRD §7, §30)
- Next.js 14+ / React, 3-pane cockpit: left Band Room Stream (message list,
  @mention tags, Approve button = human gate, footer disclaimer), centre
  Hindsight Cognitive X-Ray (webhook toasts with layer label, reflect trace,
  observation cards with proof_count), right Repo Viewer (mounted-playbooks
  Markdown + code diff + file tree). Badges: SYNTHETIC / REAL-CASE /
  OFFICIAL. Clinical, precise, audit-ready; slate/indigo base, red block /
  green pass / amber warn. No emojis, no cartoonish figures.

## 10. Evaluation harness (PRD §18.1)
- 3 systems on 20 backdated dengue/OPD cases across 4 epochs: (1)
  Stateless, (2) Plain RAG (history/vector, no observations), (3) Hindsight
  (retain/recall/reflect + observations + scopes). Metrics: decision
  accuracy target >85%, citation precision 100%, hallucinated citations 0,
  documents-missed rate <5%, proof_count increment visible (obs_304 6→7),
  latency <5s. Report MEASURED numbers honestly, even if below target.
- 5 adversarial cases (must pass): (a) insurer tactic change (old 4-week PT
  refused), (b) stale bulletin (expired rule drops, history kept),
  (c) lesson-from-failure applied to a new dengue case, (d) backdated
  temporal query ("Oct 2026 Star Health dengue wins"), (e) poisoned packet.

## 11. Ordered feature breakdown (UPHILL first — see feature_list.json)
1. `cs-001` Hindsight memory adapter + bank-template.json
2. `cs-002` 4-epoch seeder (seed_history.py) + proof_count increments
3. `cs-003` PII scrubber (PAN/Aadhaar/mobile) + redaction toasts
4. `cs-004` FastAPI backend (webhooks HMAC + SSE + all endpoints)
5. `cs-005` Pre-dispatch checker W1 (scrubber_rules.json + validator)
6. `cs-006` Band room + denial defense W3 (Auditor → Critic veto → human gate → appeal packet)
7. `cs-007` Rule patch W6 (ScrubberCoder patches rules + pytest + rollback)
8. `cs-008` Next.js 3-pane cockpit UI
9. `cs-009` Evaluation harness + 60-sec demo script + README + final verify

## 12. Verification commands
- `python -m pytest -q` (all tests must pass)
- `./.builder-os/init.sh` (must exit 0)
- `bash ~/workspace/Build-it/BUILDER-OS/scripts/secret-scan.sh .` (must exit
  0; scan project SOURCE, exclude `.venv/__pycache__` and `node_modules`)
- Demo check: `POST /demo` equivalent (or the scripted 4-beat run) shows
  Day-1 loss ₹0 → redaction toast → critic VETO citing proof_count →
  live rule commit → new incomplete packet BLOCKED. Report measured eval
  numbers honestly.

## 13. Decision log — LLM provider change (2026-11-06 ~23:59 IST, shashank's order)
- LLM provider: Groq → OmniRoute. NO GROQ anywhere in the product: do not
  use qwen/qwen3-32b or gpt-oss-120b, do not read the Groq key, do not wire
  any Groq client. (Supersedes §4 "LLM for extraction: Groq".)
- Product LLM: OmniRoute (http://localhost:20128/v1, OpenAI-compatible),
  model `gemini/gemini-3.1-flash-lite` — verified live by main 2026-11-06
  ~23:56 IST (~10s). API key from ~/.config/omniroute-local/client_key
  into env at runtime only, never printed/committed/filed.
- Do NOT use `auto/best-fast` (broken: routes to retired gemini-2.5-flash
  404 + rate-limited big-pickle) or `gemini/gemini-3.8-flash` via OmniRoute
  (unproven, empty in 60s). Retry 3.8 only after a live probe.
- Quirk: with tiny max_tokens the reply can land in reasoning_content
  with empty message content — use sensible max_tokens and read
  choices[0].message.content, falling back to reasoning_content.
- Hindsight's own specialised models (hs-decide-1-flash / hs-rerank-1 /
  hs-embed-1) unchanged; this change is only the product LLM for
  extraction/reflect.
