# ClaimShield Desk — Team Summary (5-Minute Read)

**Product:** ClaimShield Desk — AI-Powered Denial Defense & Pre-Dispatch Scrubber for Indian Hospital TPA Desks  
**Version:** 3.1 · 6 Nov 2026  
**Team:** 4-person hackathon team  
**Full PRD:** `prd.md` (1,187 lines) — this summary is the condensed version

---

## 1. What We Are Building (in one sentence)

An agent that learns from appeal outcomes which insurance denials are wrongful, builds the winning appeal packet, and rewrites the hospital desk's pre-submission checklist so the same denial never happens twice.

**Elevator pitch for judges:** *"A hospital desk gets a ₹1,45,000 dengue claim denied as 'OPD-convertible.' Day 1, a generic appeal letter is sent and lost. Day 20, our agent cites three past wins for the same insurer + denial code, blocks a stale argument invalidated by a new payer policy, and a local coding agent commits a scrubber rule that flags the missing document before the claim ever leaves the hospital."*

---

## 2. Why This Problem (and Why We Win)

### The pain (verified with real cases)
- Indian insurers deny or short-pay a large share of health claims; fewer than 1% are appealed.
- When appealed, >80% of Medicare Advantage denials and ~53% of commercial appeals get overturned — money is left on the table.
- Even after a hospital wins an appeal, nobody updates the pre-submission checklist, so the same incomplete claim goes out next week and is denied again.

### Why existing tools fail
- **Plain RAG** returns similar-sounding past appeals — even ones that lost.
- **Existing tools** draft text letters but never patch the pre-submission rules engine.
- **Hindsight cookbook's ClaimsIQ** is insurer-side triage. We are **provider-side** (hospital/TPA desk) appeal representment + auto-patching intake scrubbers.

### Why we win on judging criteria

| Criterion | Weight | How We Score |
|-----------|--------|--------------|
| Innovation | 30% | Provider-side appeal + auto-patching scrubber; not in brief's idea tables or cookbook |
| Hindsight memory | 25% | Memory is the *entire* value prop — agent knows which denials to fight because it remembers past WON/LOST verdicts with `proof_count` |
| Technical | 20% | PHI redaction, backdated timestamps, per-payer observation scopes, Band SDK delete-test pass, `fs mount` → coding agent commit |
| UX / Demo | 15% | "$4,200 denied → recovered + scrubber rule committed live" is instantly visceral |
| Real-world impact | 10% | Documented denial pain; clear path to hospital revenue-cycle sales |

---

## 3. How It Works (Architecture at a Glance)

```
[Denied Claim / 835 Remittance]
        │
        ▼
[FastAPI Backend] ──▶ [Hindsight 1.2 Bank: claimshield-india]
        │                    │ retain / recall / reflect
        │                    ▼
        │           Observations with proof_count
        │                    │
        │                    ▼
        │           Knowledge Pages → hindsight fs mount → ./mounted-playbooks/
        │
        ▼
[Band AI Room: @ClaimAuditor → @PolicyCritic → @ScrubberCoder]
        │                    │
        ▼                    ▼
   Drafts appeal       Vetoes weak packets
   (recall + reflect)  (blockable verdict)
        │                    │
        ▼                    ▼
   Human approves      @mention handoff to coding agent
        │                    │
        ▼                    ▼
   [Band Desktop jamd] reads mounted Markdown → patches scrubber_rules.json
```

### The 4-beat 60-second demo

| Beat | Time | What Judges See |
|------|------|-----------------|
| **Day 1 Failure** | 0:00–0:15 | ₹1,45,000 dengue denial → generic appeal → rejected (₹0 recovered) |
| **Memory Defense + Recall** | 0:15–0:30 | Raw 835 with patient SSN → red toast: `[REDACTED:ssn]`; `@ClaimAuditor` queries Hindsight |
| **Critic Veto + Learning** | 0:30–0:45 | `@PolicyCritic` blocks 4-week PT argument, cites observation `proof_count: 5`, attaches 6-week PT + X-ray excerpt |
| **Rule Patch** | 0:45–0:60 | Human approves → `@ScrubberCoder` commits `scrubbers/uhc_cpt73721_validator.py` live → new incomplete packet BLOCKED |

---

## 4. Tech Stack

| Layer | Technology | Version | Role |
|-------|-----------|---------|------|
| Memory Engine | Hindsight 1.2.0 | 1.2.0 | retain/recall/reflect, observations, knowledge pages, Memory Defense |
| Specialized Models | hs-decide-1-flash / hs-rerank-1 / hs-embed-1 | 1.0 | Decision model, reranker, embeddings |
| Filesystem Bridge | hindsight fs mount | CLI | Projects Knowledge Pages as Markdown to disk |
| Multi-Agent Coordination | Band SDK (Python) | 6.0.1 | Agent room, @mention routing, dependent handoff |
| Local Coding Agent | OpenCode / Claude Code | Latest | Reads mounted Markdown, patches rules file |
| Backend | FastAPI | Latest | Webhook listener, API routes, checker engine |
| Frontend | Next.js / React | Latest | 3-pane cockpit dashboard |
| Language | Python 3.11+ | 3.11+ | Backend + Band SDK agents |

**NOT used:** Band MCP (cannot deliver room messages), Band Native Memories (Enterprise-only), Mem0/Zep, OCR (out of scope v1).

---

## 5. Work Split (2 People)

### Member A — Hindsight Memory & Backend Lead
- Author `bank-template.json` (missions, directives, observation scopes, Memory Defense config)
- Build `seed_history.py` (4-epoch backdated synthetic data)
- FastAPI webhook listener (`retain.completed`, `consolidation.completed`, `memory_defense.triggered`)
- PII scrubber (deterministic Indian-ID scrubber before retain)
- 3-system evaluation harness (Stateless vs Plain RAG vs Hindsight)
- Technical article + social post

### Member B — Band Room, Coding Agent & UI Lead
- Install Band Desktop, create room, register `@ClaimAuditor`, `@PolicyCritic`, `@ScrubberCoder`
- Band SDK Python agents with @mention handoffs and execution telemetry ON
- `@ScrubberCoder` reads mounted `./mounted-playbooks/` and patches `scrubber_rules.json`
- Next.js 3-pane cockpit UI (Band Room stream + Hindsight Cognitive X-Ray + Repo Viewer)
- Record 60-second demo video + article + social post

---

## 6. Critical Verified Facts (from primary sources)

| Fact | Source |
|------|--------|
| Ombudsman award cap: ₹30 Lakhs (not ₹50 Lakhs) | Rule 17(3), Insurance Ombudsman Rules 2017 via cioins.co.in |
| Time to approach Ombudsman: 1 year from rejection | cioins.co.in FAQs |
| Ombudsman award timeline: 3 months | cioins.co.in FAQs |
| Hindsight Memory Defense covers only `ssn_us` + `credit_card` (NOT PAN/Aadhaar) | hindsight.vectorize.io/developer/memory-defense |
| Band MCP cannot deliver room messages; SDK required | docs.band.ai/connect/choose-integration-path |
| Recall fails if decision model unreachable | hindsight.vectorize.io/developer/decision-models |
| Banks fully isolated; no cross-bank reads | hindsight.vectorize.io/developer/api/memory-banks |
| 30 verified judicial cases across 5 denial patterns | Indian Kanoon (research2.txt) |

**UNVERIFIED (do not present as fact in UI/demo):**
- IRDAI health claims statistics (8% repudiation, 13% disallowance, ₹26,000 crore) — PDFs exist but couldn't be parsed
- DPDP Act health-specific sub-rules — not yet gazetted
- Bima Bharosa grievance breakdowns by line of business

---

## 7. Key Risks & Fallbacks

| Risk | Fallback |
|------|----------|
| Band room looks decorative | Enforce delete test: critic veto + coding agent patch depend on @mention handoff; execution events ON |
| Hindsight Cloud down | Local Docker `ghcr.io/vectorize-io/hindsight:latest` backup ready |
| Recall fails (decision model missing) | `ENABLE_DECISION_PRUNE=false` flag; recall runs without decision model |
| Memory Defense misses Indian IDs | Backend deterministic scrubber + native card/token toast for demo |
| Unverified stats in UI | Badge everything SYNTHETIC; no unverified numbers shown |

---

## 8. Organizer Questions (UNRESOLVED — need answers)

1. Where is the official Content Guide (formats, word counts, video duration)?
2. Can our demo video double as the Content Guide video?
3. Does showing Band inside the product satisfy the "use Band" requirement?
4. Does MEMHACK99 credit cover Hindsight Inference API usage?
5. What is the submission deadline and live demo slot length?

---

## 9. What to Do First (Implementation Order)

1. **Member A:** Set up Hindsight (Cloud + local Docker backup), author `bank-template.json`, build `seed_history.py`
2. **Member B:** Install Band Desktop, create Band room, register 3 agents
3. **Both:** Build FastAPI backend + Band agents in parallel (Week 1–2)
4. **Both:** Build cockpit UI + checker (Week 3)
5. **Both:** Run evaluation, record demo, write content (Week 4)

---

## 10. Files in This Folder

| File | Purpose |
|------|---------|
| `prd.md` | Full master PRD (1,187 lines) — single source of truth |
| `TEAM-SUMMARY.md` | This file — 5-minute read |
| `research1.txt` | Unverified Indian regulatory claims table |
| `research2.txt` | 30 verified case records across 5 denial patterns |
| `research4.txt` | Hindsight + Band technical verification |

---

**Bottom line:** We're building a hospital-desk denial defense agent that learns from outcomes and auto-patches intake rules. Memory is the star, Band is the coordination plane, and the 60-second demo shows a denied claim becoming a permanent engineering guardrail. Read `prd.md` for full specs; start with Section 3 (work split) and Section 9 (what to do first).