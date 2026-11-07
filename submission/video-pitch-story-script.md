# ClaimShield Desk — Video Pitch STORY Script v2 (3–5 min, with cut plan)
### Team God Protocol · HackWithBangalore 4.0 demo video · ~590 words ≈ 3:55 at natural pace
### Written 7 Nov 2026 — his order: "write a 3-5 min script story, use the parts from this cinematic video and cut-match them properly, only show the product only when needed"

**Supersedes v1** (the ~500-word story without a cut plan). Same facts, same numbers, same team voice — now timed to the NotebookLM footage and the product footage, with the product appearing ONLY at the five proof moments.

**Voice:** team voice ("we"). **Narration voice:** his own audio throughout — SINGLE voice (single male voice, Indian English accent, the 210s file he sent 18:40 IST). Split into the 7 sections at Vosk-verified word boundaries and loudnormed to I=-17. The NotebookLM video plays MUTED under the narration (its own narrator is never used); the product footage is silent screen recording, so his voice is the only voice in the whole video.

**Sources:**
- NLM = NotebookLM cinematic video `workspace/browser_downloads/sess-548612229/browser-download-20261107T101631.841396223Z-1-ClaimShield_Desk__Architecting_Memory_Over_RAG.mp4` — 8:39, 1280×720, 30fps. Visuals mapped frame-by-frame (every 30s) on 7 Nov; ranges below are the usable slices.
- PRODUCT = light-theme silent take `submission/claimshield-desk-demo-light-silent.mp4` — 1920×1080, 191s. Sections: Intro 0–20s, Beat 1 20–50s, Beat 2 50–80s, Beat 3 80–120s, Beat 4 120–160s, Wrap 160–191s.

**Cut rules (from the v1 rejection):** gaps between voice clips ≤0.4s (v1's 0.8s gaps read as dead air); zoom gentler than v1 — the "THE DESK DECIDES." headline must never be cut at max zoom; verify every section is audible before shipping; NLM inserts are upscaled 720p→1080p (soft but fine for diagrams).

**Honesty notes:** the staffer and the family are ILLUSTRATIVE — a story, not real people. The claim (Star Health dengue ₹1,45,000, denied "OPD-convertible"), the October bulletin (4-week PT out, 6-week + X-ray in), the poisoned packet, and every number (proof ×5, 19/20, 5/5, 16/20, 11/20) are the verified SYNTHETIC demo data. The on-screen "All cases SYNTHETIC" disclaimer stays on every frame that shows case data. Scope: cashless AND reimbursement (PRD) — the family paid out of pocket and files for reimbursement. Boundary kept: the Reimbursement Pack Builder (W2) is P1, NOT in the demo — the story names reimbursement as scope but invents no demo beat for it.

---

## 1. HOOK — "The desk where hope waits" (~30s)
**Visuals: his clip (denied claim form, hand writes APPEAL), zoomed 1.25x to hide the Gemini watermark, slowed to half speed with a held final frame + gentle push-in — with a "ClaimShield Desk — Built on Hindsight" title band over the first 5 seconds (added 7 Nov 17:35 IST so the Hindsight word lands at second 0). No product yet.**

> Hi, we're Team God Protocol. Every hospital has a desk where hope goes to wait. A family paid the bill out of pocket and filed for reimbursement — one lakh forty-five thousand rupees — and the insurer answers in a single line: OPD-convertible. Denied. The person at the desk appeals the way she always has: a generic letter, no evidence attached. It fails. Six months later, the same denial comes back. Same appeal. Same failure.

## 2. PROBLEM — "It didn't fail because it didn't care" (~35s)
**Visuals: NLM 0:30–1:30** — the appeal-draft loop, then the hospital corridor sketch (systemic drain, inefficiency path). Still no product — the problem is a story, not a screen.

> The desk didn't fail because it didn't care. It failed because it forgot. The desk handles both kinds of claims — cashless approvals at the counter, and reimbursement claims from families who already paid and are waiting to be paid back — thousands a day. The knowledge was there — a senior staffer knew Star Health overturns dengue denials when the NS1 report and the IV fluid sheets are attached. But that knowledge lived in one person's head, or in a spreadsheet nobody opens. And when she was on leave, or the file was buried, every new denial started from zero. So we asked a simple question: what if the desk itself could remember?

## 3. THE TURN — "The desk remembers" (~35s)
**Visuals: NLM 1:30–2:30** — our real architecture diagram (the denial-defense loop: intake, PII scrubber, pre-dispatch check, Hindsight memory bank claimshield-india, @ClaimAuditor, @PolicyCritic, human approve, @ScrubberCoder, rule commit), then the DO NOT SEND barrier. Then **PRODUCT Beat 1 (~0:30–0:45 of the light take)** — the X-Ray pane, VETO proof ×0, for one held beat: the generic appeal, no evidence. This is the FIRST time the product appears, and only for the proof.

> That's ClaimShield Desk. Every appeal outcome — overturned, partially paid, rejected, cashless or reimbursement — is retained in Hindsight memory, with a proof count: how many times that pattern has actually worked. When the dengue denial comes in now, the desk doesn't guess. It recalls the win at proof five, cites the NS1 report, and drafts the appeal from what worked. The same denial that failed twice now walks in with evidence behind it. And the first thing the desk learns is what a failure looks like: a generic appeal, no recalled evidence, vetoed at proof zero.

## 4. THE SCRUB — "Nothing is remembered unscrubbed" (~25s)
**Visuals: NLM 4:00–4:30** — the dual-layer PII redaction diagram (backend regex: PAN, Aadhaar, phone redacted; native layer: SSN, card). Then **PRODUCT Beat 2 (~0:55–1:15 of the light take)** — the redaction toast and `retain.completed` in the Band Room, one held beat.

> Before any of that, the desk scrubs the packet. PAN, Aadhaar, phone numbers — redacted before a single word is remembered. A raw SSN in a document gets caught by the second layer too. Nothing about a patient is ever retained unscrubbed. Memory you can't trust with data is memory you can't trust at all.

## 5. THE CRITIC — "Memory that can't say no" (~45s)
**Visuals: NLM 5:00–5:30** — the 4-WEEK POLICY sketch giving way to the newer 6-weeks policy, then the @PolicyCritic validation framework (temporal integrity, superseded-tactic filtering, evidence grounding). Then **NLM 6:00–6:30** — Plain RAG with no grounding, the "approve anyway" packet, then the poisoned-packet VETO stamp. Then **PRODUCT Beat 3 (~1:30–1:55 of the light take)** — the X-Ray VETO proof ×6 with the missing-evidence list, one held beat.

> But memory alone isn't enough. Memory can go stale — and stale memory is worse than no memory. In October, Star Health changed the rule for knee-surgery appeals: the old four-week physio trial was out; six weeks plus an X-ray was in. The desk drafted on the old argument anyway. And the critic caught it — vetoed the appeal before it left the desk, and named exactly what was missing. It does the same to a poisoned packet that just says "approve anyway": no evidence, no grounds, vetoed. A plain RAG system approves that packet. Memory that can't say no is just a louder way to be wrong.

## 6. THE HUMAN GATE — "It learns" (~30s)
**Visuals: NLM 7:00–7:30** — the scrubber_rules.json code window (dengue rule v3), then the woman at the hospital desk with the padlock screen. Then **PRODUCT Beat 4 (~2:05–2:35 of the light take)** — the Repo Viewer at v4 and the BLOCKED banner, one held beat.

> And nothing becomes a rule without a human. A person approves the packet, and the scrubber learns: from now on, the dengue rule needs the platelet report too. The same complete packet that passed a minute earlier is blocked until the report is attached. The denial never happens again. The desk doesn't just remember. It learns.

## 7. WRAP — "The desk remembers now" (~40s)
**Visuals: PRODUCT Wrap (~2:45–3:10 of the light take)** — the "Measured, not claimed" eval strip, slow pull-back to the full cockpit. Then **NLM 8:30–8:39** — the closing loop diagram (intake → memory vault → multi-agent chamber → pre-dispatch firewall), hold on the final frame. (NLM 8:00's bar chart is NOT used — its numbers are right but its axis labels are garbled; the product's eval strip carries the numbers instead.)

> We measured it, we didn't claim it. On twenty cases plus five adversarial ones: Stateless scored sixteen out of twenty. Plain RAG scored eleven — and approved the poisoned packet. Hindsight scored nineteen out of twenty, five out of five adversarial. A desk that remembers — cashless or reimbursement — is a desk that stops losing the same fight twice. That's ClaimShield Desk — built by Team God Protocol, with Hindsight memory. The desk remembers now.

---

## Cut plan at a glance

| # | Section | Time | Visuals | Product? |
|---|---------|------|---------|----------|
| 1 | Hook | ~0:30 | His clip (denied claim form, hand writes APPEAL), zoomed 1.25x to hide the Gemini watermark, slowed to half speed with a held final frame + gentle push-in — replaced the generated still 7 Nov 17:27 IST on his call | No |
| 2 | Problem | ~0:35 | NLM 0:30–1:30 (appeal loop → corridor drain) | No |
| 3 | The turn | ~0:35 | NLM 1:30–2:30 (architecture diagram → DO NOT SEND) + PRODUCT Beat 1 veto | Proof only |
| 4 | The scrub | ~0:25 | NLM 4:00–4:30 (dual-layer redaction) + PRODUCT Beat 2 toast | Proof only |
| 5 | The critic | ~0:45 | NLM 5:00–5:30 (4-week → 6-week, critic framework) + NLM 6:00–6:30 (Plain RAG, poisoned VETO) + PRODUCT Beat 3 veto | Proof only |
| 6 | Human gate | ~0:30 | NLM 7:00–7:30 (rules.json v3, desk + padlock) + PRODUCT Beat 4 commit/BLOCKED | Proof only |
| 7 | Wrap | ~0:40 | PRODUCT eval strip + NLM 8:30–8:39 (closing loop) | Proof only |
| | **Total** | **~3:55** | **NLM ~2:55, product ~1:00** | |

**NLM segments NOT used:** 3:30 (chat-interface critique slide — wrong subject), 4:30 (JSON structural diagram — abstract, adds nothing), 8:00 (eval bar chart — garbled axis labels). NLM 1:00 corridor labels ("systemic resource drain") are NotebookLM's paraphrase, not our terms — used as atmosphere only, never quoted as fact.

## What happens next (once he approves this script)
1. Voiceover is his own audio throughout — done 7 Nov ~18:51 IST (single voice, Indian accent; his 210s file, split at Vosk-verified word boundaries, loudnormed).
2. Assemble: NLM slices (muted, upscaled to 1080p) + product proof moments (gentle zoom, headline never cut) + Fenrir voice as master track, gaps ≤0.4s.
3. Verify before showing him: ffprobe (1920×1080, audio present), per-section audibility check (the v1 lesson), spot-check frames at each product moment.
4. Output: `submission/claimshield-desk-demo-final-v2.mp4`. The held v1 file stays untouched. Do NOT upload.
