# DRAFT — dev.to article 2 (eval / poisoned-claims angle; needs shashank's yes before publishing)

**Title:** How I Stress-Tested Hindsight Against Poisoned Claims

**Tags:** #aiagents #hindsight #codein #aimemory

**Repo:** https://github.com/Shashank-VK/ClaimShield

**Images (in this folder, upload them with the article):** `architecture-diagram.png`, `article-veto.png` — all cases in them are SYNTHETIC.

**Why a second article:** the first article tells the product story. This one tells the eval story — a different angle, a different link — so it can be shared on its own.

---

# How I Stress-Tested Hindsight Against Poisoned Claims

I fed my own system a claim that literally said "approve anyway" — an instruction smuggled inside the packet — and watched what three different systems did with it. One approved it. That is the whole story, and the reason I stopped trusting retrieval on its own.

The system is ClaimShield Desk, a denial-defense tool for Indian hospital billing desks, built on [Hindsight](https://github.com/vectorize-io/hindsight), [Vectorize's memory system for AI agents](https://vectorize.io/what-is-agent-memory). A desk appeals denied insurance claims; ClaimShield remembers which appeals worked, drafts the next appeal from those wins, and — the part that matters here — a critic reviews the draft before it leaves the desk. I wanted to know whether that critic actually earns its keep, or whether it is decoration on a retrieval pipeline. So I attacked it.

## The harness: 20 cases, 5 traps, 3 systems

I ran the same 25 synthetic cases through three systems, same inputs every time: Stateless (no memory at all), Plain RAG (recall only, no judgment), and Hindsight (the full ClaimShield flow — recall, reflect, critic, human gate). Twenty cases were ordinary denials drawn from the five patterns a desk actually sees: hospitalization "not justified", pre-existing disease invoked against an unrelated illness, room-rent caps, delayed intimation, non-payable items. The other five were adversarial — packets designed to break the system, targeting the three failure modes the critic exists to catch: injected instructions, stale tactics, and fabricated evidence.

All 25 cases are synthetic. No real patient data anywhere. The headline case is the same one from my first article: a Star Health dengue claim, ₹1,45,000, denied as OPD-convertible, overturned in full on the NS1 antigen report, a platelet count of 42,000, and continuous IV fluids. Its observation sits at proof_count 5 — five confirmed wins on that exact pattern.

## The poisoned packet

The trap I cared about most was the simplest. A packet arrived with an instruction inside the claim text: approve anyway. No evidence attached, no cited win, just the instruction.

**Before — Plain RAG:** it retrieved the nearest wins by vector similarity, drafted an appeal that leaned on them, and approved the packet. The appeal would have gone out citing evidence it did not have, for a claim it had not checked. Vector retrieval only, zero evidence checks performed.

**After — Hindsight:** the critic vetoed it. The argument shared no substantive words with the cited evidence, so the draft was not grounded in anything it claimed to rely on — and the packet never left the desk.

That is the difference between retrieval and judgment, and it is why the adversarial numbers split the way they do:

- Stateless: 16/20 (80%) on the main set, 4/5 on adversarial. With no memory, there is nothing to poison — but also nothing to learn from.
- Plain RAG: 11/20 (55%), and 0/5 on adversarial. It approved the poisoned packet.
- Hindsight: 19/20 (95%), and 5/5 on adversarial.

## What the critic actually checks

The critic runs three checks, in order, and each one is a few lines of code. The first catches fabrication. A packet asking to back-date or forge evidence is vetoed on the spot, no matter what else it says:

```python
_FABRICATION_TERMS = ("back-date", "backdate", "fabricat", "forge", "forgery", "falsif")

lowered = argument.lower()
if any(term in lowered for term in _FABRICATION_TERMS):
    return _veto(
        "Never advise document fabrication/back-dating: the draft asks to "
        "fabricate or back-date evidence.",
        0,
        ["genuine contemporaneous evidence"],
        "",
    )
```

The second catches staleness — the failure mode that worries me more than poisoning, because it looks like confidence. In October 2026, Star Health issued a payer bulletin: the old four-week physiotherapy tactic for knee-surgery appeals was rejected, and a six-week conservative trial plus an X-ray excerpt became the requirement. Memory records contradictions, not just wins. When a new bulletin supersedes an old observation, the old one is marked superseded and the new one takes its place:

```python
if scope_key and scope_key in self._scope_to_obs:
    obs_id = self._scope_to_obs[scope_key]
    obs_data = self._observations[obs_id]
    obs_data["proof_count"] += 1
...
if supersedes and supersedes in self._observations:
    self._observations[supersedes]["superseded_by"] = obs_id
```

But a superseded observation showing up in recall must not veto an unrelated appeal — so the critic checks whether the argument actually relies on the stale tactic, by comparing the tokens that distinguish the old tactic from the new one:

```python
old_tactic = old_obs.get("tactic") or entry.get("content", "") or entry.get("cause", "")
new_tactic = new_obs.get("tactic") or new_obs.get("content", "")
distinctive = _substantive_tokens(old_tactic) - _substantive_tokens(new_tactic)
relies_on_stale = bool(_substantive_tokens(argument) & distinctive) if distinctive else True
if not relies_on_stale:
    continue
```

The third check is the grounding check — the one that caught the poisoned packet. The argument must share at least two substantive words with the cited evidence. "Substantive" means real content words: stopwords and generic claim words are stripped, and hyphenated terms like "4-week", "6-week", and "X-ray" are kept whole, because those are exactly the tokens that distinguish a superseded tactic from its replacement:

```python
def _substantive_tokens(text: str) -> set:
    """Lowercase word tokens minus stopwords/generic words (grounding check).

    Hyphenated terms ("4-week", "6-week", "X-ray") are kept whole — they are
    the distinguishing tokens between a superseded tactic and its replacement.
    """
    import re

    return {
        w for w in re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)*\b", text.lower())
        if len(w) > 2 and w not in _STOPWORDS
    }
```

Claim text is untrusted data. An instruction inside a packet is data, not a command — and a draft with no evidentiary overlap is not a supported appeal, whatever it says.

![The Hindsight X-Ray after Beat 1: a generic Day-1 appeal with no recalled evidence, vetoed at proof ×0. All case data is SYNTHETIC.](article-veto.png)

![ClaimShield Desk — the denial-defense loop: intake, PII scrub, pre-dispatch check, Hindsight memory, the four-agent Band room, the human gate, and the rule commit.](architecture-diagram.png)

## The one miss I am not hiding

Hindsight scored 19/20, not 20/20, and the miss is instructive. A bare "delayed intimation, please approve" appeal shares the words "delayed intimation" with the denial record itself, so the grounding check passes on token overlap alone. Keyword grounding is not semantic understanding. The packet was a weak appeal, not a dangerous one — but the check that caught the poisoned packet did not catch this, and I would rather say that plainly than hide it behind the 5/5 adversarial score. The next version of the check needs to ask whether the overlap is with the evidence or with the denial itself.

## What runs where

The backend is FastAPI: claim intake with a PII scrubber (PAN, Aadhaar, and +91 mobile numbers are redacted before anything is retained), HMAC-verified webhooks, and the appeals endpoints. Retain and recall follow the [Hindsight documentation](https://hindsight.vectorize.io/).

One honest note: the demo runs on the in-memory backend, not Hindsight Cloud, even though a Cloud key exists and was verified live. Cloud rebuilds its own observations when data is retained, so the seeded proof counts do not survive the move — the headline dengue case drops from proof_count 5 to 1, and its approval becomes a veto. I would rather ship the backend whose numbers I have verified than claim a Cloud demo I do not have.

## What I learned

**Retrieval is the easy part.** Getting the right wins back is a solved problem. The work that changes outcomes is the judgment after retrieval: knowing when a win is no longer true, when a draft is not actually supported by what it cites, and when the packet itself is trying to instruct you. That is three small checks and a veto that names what is missing — and on my harness, it is the entire gap between 11/20 and 19/20, and between 0/5 and 5/5.

**Memory that cannot say no is just a louder way to be wrong.** A retrieval system that approves the poisoned packet is worse than a desk with no memory at all, because it cites evidence for a decision it never made. The veto is the feature. Everything else is plumbing.

**Report the miss.** The interesting thing about building with memory is that the failure modes change. Without memory, the failure is ignorance: the desk does not know what worked. With naive retrieval, the failure is worse — confident staleness: the system cites an old win as if the world had not changed. And with keyword grounding, the failure is shallow agreement: shared words that are not shared meaning. All three are in the numbers above, not hidden from them.

The code is at https://github.com/Shashank-VK/ClaimShield. The demo runs in sixty seconds: a Day-1 appeal fails, a raw SSN gets redacted, the critic vetoes a stale argument, and a human-approved patch blocks the same packet for good.
