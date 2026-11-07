# FINAL — Demo video script (~3:00, screen recording + AI voiceover)

**Setup before recording:** backend on :8000
(`uvicorn backend.main:app --host 127.0.0.1 --port 8000`), frontend on
:3000 from a **production build** (`npm run build` + `npm run start` —
no dev overlay in the recording). Light theme. **1920×1080.**
`scrubber_rules.json` must be **v3** before recording; Beat 4 commits v4
— **restore the file to v3 after the take**. All cases shown are SYNTHETIC.

**Voiceover:** recorded by Shashank himself (his voice, sent as audio
files — the AI voiceover was replaced by his order 7 Nov ~14:00 IST),
one clip per section below, first person, conversational. Narration text
is verbatim — do not improvise new claims or numbers.

## 0:00–0:20 — Intro (cockpit overview on screen)

"Hi, we're Team God Protocol. This is ClaimShield Desk — a denial-defense tool for Indian hospital billing desks. Every claim a desk handles can be denied, and every denial handled badly is money a hospital never recovers. So every appeal outcome goes into Hindsight memory with a proof count — and the next denial of the same pattern is drafted from what actually worked, not from a guess."

## 0:20–0:50 — The problem: Beat 1, Day-1 generic appeal fails

Click Beat 1, hold on the X-Ray. "Here's the desk today, with no memory. A dengue claim, denied as OPD-convertible. The auditor drafts a generic appeal — no evidence cited, no prior case referenced — and the critic vetoes it. Proof zero. Nothing was learned, nothing was recorded, so the next dengue denial will get the exact same generic appeal. This is the failure the desk repeats, every single day."

## 0:50–1:20 — Beat 2: PII is scrubbed before anything is retained

Click Beat 2, hold on the redaction toast and the Band Room. "Before anything is retained, the scrubber redacts it. A raw document comes in with a social security number — and PAN, Aadhaar, and mobile numbers get the same treatment, across two layers: the backend pass and the native pass. Nothing identifiable ever reaches memory. The desk learns from the pattern of a denial, never from the identity of the patient behind it."

## 1:20–2:00 — Beat 3: the critic vetoes a stale argument

Click Beat 3, hold on the X-Ray veto with the missing evidence. "Now the critic earns its keep. The desk drafts an appeal on a four-week physio trial. But Star Health's October bulletin killed that tactic — six weeks plus an X-ray is the requirement now. The critic runs three checks before anything goes out: it vetoes anything fabricated or back-dated, it catches arguments built on superseded tactics, and it demands grounding — every claim must share real words with the evidence it cites. Here it sees the superseded observation in memory, vetoes the draft, and names exactly what is missing. A plain RAG system would have sent it."

## 2:00–2:40 — Beat 4: human approval becomes a rule

Click Beat 4, hold on the Repo Viewer (rule v4) and the blocked re-check. "A human approves the complete dengue packet, and the scrubber gains a new rule: the platelet report is now required. No rule is ever written by the machine alone — every commit needs a human approval first. And the same packet that passed a minute ago is blocked until the report is attached. The denial never happens again — because the desk remembered, and a human signed off on the lesson."

## 2:40–3:00 — Wrap: the proof of learning (outcomes rail on screen)

"Measured, not claimed. On a twenty-case eval plus five adversarial ones, Hindsight scored nineteen out of twenty, and five out of five. Stateless scored sixteen out of twenty. Plain RAG scored eleven out of twenty — and approved the poisoned packet. The one honest miss: a bare delayed-intimation appeal passes the grounding check, because it shares the words with the denial itself. Keyword grounding is not semantic understanding — and that is the next thing to fix. The code is in the repo linked below."

---

**Deliverable:** `submission/claimshield-desk-demo.mp4`, 1920×1080, ~3:00,
screen recording + the voiceover above. YouTube upload + thumbnail are
shashank's steps (his account, his photo) — the file is the deliverable.
