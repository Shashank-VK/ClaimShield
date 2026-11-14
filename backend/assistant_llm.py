"""Optional LLM answers for the Assistant chat, via OpenRouter.

Added 2026-11-14 (his order: wire an LLM in for the live showing).
Design rules:
- OPTIONAL: with no OPENROUTER_API_KEY set, answer() returns None and the
  Assistant keeps its scripted answers. The 4-step demo never touches this.
- GROUNDED: the model only receives facts this module states (product
  facts, the measured eval numbers, the known limit) plus a live summary
  of the current checklist passed in by the caller. It is told to say
  "I don't know" rather than invent claim outcomes.
- FAIL-SAFE: any network/HTTP/parse failure returns None — the chat falls
  back to the scripted answers instead of erroring in front of an audience.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import httpx

from backend import config

_FACTS = """You are the Assistant inside ClaimShield Desk, a tool for hospital
billing (TPA) desks in India. Answer briefly, in plain words, in at most
4 short sentences. Only talk about this desk and the claim shown. Never
invent claim outcomes, numbers, or rules. If you do not know, say so.
Never give legal or medical advice.

What the desk does, in 3 steps:
1. REMEMBER — every past appeal result is saved in memory, along with how
   many times it worked (its backing).
2. VERIFY — a new claim is checked against the past cases that won. An
   appeal is drafted from those cases; a second checker stops it when
   there is no evidence behind it ("Stopped — needs fixing") or when the
   winning argument it relies on has been replaced by a newer one.
3. DO IT RIGHT — a human approves every rule change; only then does the
   checklist learn. The next incomplete packet is blocked before sending
   ("Blocked").

Safety: private details (names, ID numbers, phone numbers) are removed
before anything is saved. Nothing is sent automatically. Every case in
the demo is a sample case, marked SYNTHETIC.

Measured results (25 sample cases: 20 normal, 5 tricky):
- With memory: 19 of 20 normal cases decided right, all 5 tricky caught.
- Without memory: 16 of 20.
- With simple search only: 11 of 20, 0 of 5 tricky.
Known limit: a bare "please approve" letter that copies the denial's own
words can pass the wording check — the check reads words, not meaning.
The demo runs on built-in memory; the desk's memory can also connect to
Hindsight Cloud."""


def build_system_prompt(context: Optional[Dict] = None) -> str:
    """Grounded system prompt: fixed facts + the live checklist summary."""
    prompt = _FACTS
    context = context or {}
    rules = context.get("rules") or []
    if rules:
        active = [r for r in rules if r.get("is_active", True)]
        lines = [
            f"- {r.get('insurer', '?')} / {r.get('diagnosis_group', '?')}: "
            f"version {r.get('version', '?')}, backed by {r.get('proof_count', 0)} wins, "
            f"must have: {', '.join(r.get('required_docs') or []) or 'not stated'}"
            for r in active
        ]
        prompt += (
            f"\n\nThe checklist right now (version {context.get('rules_version', '?')}, "
            f"{len(active)} rules in use):\n" + "\n".join(lines)
        )
    return prompt


def answer(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    context: Optional[Dict] = None,
) -> Optional[str]:
    """One grounded answer, or None (no key / any failure) for fallback."""
    key = config.get_openrouter_api_key()
    if not key or not (message or "").strip():
        return None

    messages = [{"role": "system", "content": build_system_prompt(context)}]
    for item in (history or [])[-6:]:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        role = "user" if item.get("from") == "user" else "assistant"
        messages.append({"role": role, "content": text[:1000]})
    messages.append({"role": "user", "content": message.strip()[:2000]})

    try:
        resp = httpx.post(
            f"{config.get_openrouter_base_url()}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "X-Title": "ClaimShield Desk",
            },
            json={
                "model": config.get_openrouter_model(),
                "messages": messages,
                "max_tokens": 400,
                "temperature": 0.3,
            },
            timeout=25.0,
        )
    except Exception:
        return None
    if resp.status_code != 200:
        return None
    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None
    content = (content or "").strip()
    return content or None
