# ClaimShield Desk — Press Release

FOR IMMEDIATE RELEASE

Bengaluru, 6 November 2026 — Shashank Karamudi today announced ClaimShield Desk, a denial-defense and pre-dispatch scrubber for Indian hospital insurance (TPA) desks that learns from appeal outcomes.

The problem: Indian hospital desks watch cashless and reimbursement claims get denied or short-paid every day — a dengue claim of ₹1,45,000 refused as "OPD-convertible", a missing discharge summary blocking a bed at discharge, a family paying a deposit while a query drags on. The desk writes a generic reconsideration letter, loses, and nobody updates the checklist — so the same incomplete file goes out next week and is denied again for the same reason. Fewer than 1% of denied claims are ever appealed, and every appeal that does win leaves no trace in the desk's process.

The solution: ClaimShield Desk remembers every appeal outcome. When a new denial arrives, it recalls the past wins for the same insurer and denial reason, drafts an appeal packet citing the evidence that actually worked, blocks weak arguments a critic has already seen fail, and — once a human approves — patches the desk's own pre-submission checklist so the incomplete packet can never leave the hospital again.

Customer quote: "We won the same dengue appeal three times and still sent out the same incomplete file the fourth week. Now the desk itself stops it before dispatch."

How to get started: A desk coordinator pastes a packet manifest or a denial letter into the cockpit; the checker answers PASS, WARN or BLOCKED in seconds.

---

# Frequently Asked Questions

Q: What does ClaimShield Desk NOT do?
A: (1) It does not replace a broker, lawyer or doctor — every output is a draft for human review, never legal or medical advice. (2) It does not read scanned documents — the v1 checker works on a structured packet manifest only (no OCR). (3) It does not move money, act as a TPA, or make coverage decisions.

Q: Why not plain RAG over past appeals?
A: Plain RAG returns similar-sounding past appeals — including the ones that lost. ClaimShield Desk keeps outcome-labelled observations with proof counts, so it knows which evidence bundles actually won for this insurer and denial reason, and its critic can veto an argument a newer payer bulletin already invalidated. That outcome memory is the product; RAG alone cannot supply it (PRD §2.3).

Q: What is the risk if this does not work?
A: Honest answer: a bad appeal packet costs a desk days of rework and a lost claim worth lakhs, and a wrong scrubber rule could block good packets. That is why every packet is a human-reviewed draft, why the critic's veto is blockable rather than advisory, why rule patches need human approval and keep a rollback history, and why all demo data is synthetic and badged SYNTHETIC. The system never touches real patient data in v1.

---

# Skeptical Customer Challenge (working-backwards, Gate 2)

1. "So what? My desk already has a checklist on a spreadsheet — why would I change what I do now?" — Because the spreadsheet never learns: it cannot tell you that the last three Star Health dengue wins all needed the NS1 report plus the ICD-10 final bill, nor can it stop a packet missing them. The product's only claim is the learning loop, and the demo must prove it (Day-1 loss vs Day-20 win) or there is no product.
2. "You claim it learns from outcomes — but my desk has no outcome data, only a pile of PDFs." — True for v1: the seeder ships 4 epochs of backdated synthetic history modelled on 30 verified Indian judicial cases (PRD research pack-2). A real desk would need its own verdict capture (W5) before the memory is worth anything; the demo proves the mechanism, not a production memory.
3. "An AI drafting my appeal letters sounds like a compliance risk — who is liable when it cites a wrong rule?" — The packet cites only retrieved sources with IDs and carries a footer disclaimer on every page; nothing is sent without a human approving it. If the citations cannot be validated against retrieved memory, the packet is not generated.
4. "What specifically does this do that Plum's Claims Lens does not?" — Plum is insurer/broker-side for its own members; ClaimShield Desk is insurer-agnostic and sits at the hospital desk, and it closes the loop Plum does not: the rejection reason patches the pre-claim rule set (research pack-6 verdict).
5. "A 60-second demo with a ₹1,45,000 dengue case is synthetic theatre. Why should I believe any of it?" — You should not believe the numbers: every amount is badged SYNTHETIC and the IRDAI statistics are explicitly unverified and never shown. What the demo proves is the mechanism — recall, veto, patch, re-block — which is deterministic and testable.
