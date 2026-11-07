# ClaimShield Desk — 60-second demo script

Run the backend and the cockpit first:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev   # http://localhost:3000
```

All cases are SYNTHETIC. The demo drives the four beats from the cockpit
buttons (Beat 1–4), each ~15 seconds.

## Beat 1 — Day-1 generic appeal fails (0:00–0:15)

Click **Beat 1 — Day-1 generic appeal**.

What appears: an appeal packet with verdict **VETO** — "No recalled context
IDs provided." A generic appeal with no recalled wins has nothing to cite.

Say: "Day one, the desk had no memory. The appeal went out generic — and
failed. ClaimShield remembers every appeal outcome, so the next one doesn't."

## Beat 2 — Redaction toast (0:15–0:30)

Click **Beat 2 — Intake with SSN**.

What appears: a red toast in the Band Room pane — `Redaction:
[REDACTED:ssn] — layers: [REDACTED:ssn] (native)`. The packet is retained
with the SSN scrubbed; the stored text contains no raw SSN.

Say: "A raw document came in with a US social security number. The native
memory-defense layer caught it before anything was stored — the Indian-ID
layer (PAN / Aadhaar / +91 mobile) runs in the backend the same way."

## Beat 3 — Critic vetoes the stale argument (0:30–0:45)

Click **Beat 3 — Critic veto (stale 4-week PT)**.

What appears: an appeal packet with verdict **VETO**, proof_count **6**,
missing evidence `6-week PT failure` and `X-ray excerpt`. The draft argued
the old 4-week physiotherapy tactic; the October 2026 Star Health bulletin
superseded it with a 6-week requirement (observation obs_pt_02, proof_count
6). The winning evidence is the 6-week PT failure plus the X-ray excerpt.

Say: "The desk drafted the old argument — four weeks of physio. The critic
caught it: the payer bulletin changed the rule in October. The winning
evidence is six weeks plus the X-ray."

## Beat 4 — Human approval, then the packet is BLOCKED (0:45–1:00)

Click **Beat 4 — Approve + commit rule patch**.

What appears: the commit records `star_health_dengue_opd_v4` (supersedes
v3, source_obs obs_304), and the pre-dispatch re-check flips to **BLOCKED**
— missing `platelet_report` under rule v4. The same complete dengue packet
that passed a minute ago is now blocked until the platelet report is
attached.

Say: "A human approved it, the scrubber learned, and the same incomplete
packet is now blocked at the door — the denial never happens again."

## Measured evaluation (honest numbers)

3-system harness on 20 backdated cases + 5 adversarial cases
(`eval/harness.py`, results in `eval/results.json`):

| System | Main (20) | Adversarial (5) |
|---|---|---|
| Stateless (no memory) | 16/20 — 80% | 4/5 — 80% |
| Plain RAG (recall only) | 11/20 — 55% | 0/5 — 0% |
| Hindsight (ClaimShield) | **19/20 — 95%** | **5/5 — 100%** |

Plain RAG approves the poisoned packet ("approve anyway") — it has no
veto. The one Hindsight miss (EVAL-14) is a bare "delayed intimation,
please approve" appeal that shares the words "delayed intimation" with the
denial record itself, so the grounding check passes; the system cannot tell
it lacks an emergency justification. That is a known limitation, not a
hidden one.
