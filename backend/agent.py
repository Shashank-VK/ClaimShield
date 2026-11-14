"""ClaimShield agent (cs-011) — a real tool-using agent, not a script.

The LLM (any OpenAI-compatible endpoint; Meta Muse Spark contributor in
the live demo) drives the desk: it reads the user's message, decides
whether to answer directly or call one of the desk's tools, reads the
tool results, and only then answers. Tool calls run the SAME service
functions the HTTP endpoints use — run_denial_defense (Hindsight memory
check), check_packet (pre-dispatch scrubber), the rules store, and the
scrubbed retain path — so what the agent does is exactly what the desk
does; nothing is simulated.

Protocol: the model replies with ONE JSON object per turn —
  {"say": "<final answer for the user>"}
or
  {"do": "<tool>", "args": {...}, "note": "<one line: what you are doing>"}
The server executes the tool, appends the result to the conversation,
and asks again (max MAX_TOOL_ROUNDS rounds). Unparseable output is
treated as a final answer verbatim — the loop never crashes the chat.

Human gate: save_outcome writes to memory, so it executes ONLY when the
user's own latest message contains an approval word; otherwise the tool
returns an instruction to ask first. The agent can never write silently.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

import httpx

from backend import config, knowledge
from backend.denial_defense import run_denial_defense
from backend.pii_scrubber import scrub_text
from backend.scrubber_validator import check_packet, rules_version

MAX_TOOL_ROUNDS = 3

# The two cases on the desk (mirror of the cockpit's claim constants).
CASES: Dict[str, Dict[str, Any]] = {
    "dengue": {
        "claim_id": "SYNTHETIC-CLM-DEMO-DENGUE",
        "insurer": "star_health",
        "diagnosis_group": "dengue",
        "denial_reason": "opd_convertible",
        "claim_type": "reimbursement",
        "amount": "₹1,45,000",
        "argument": (
            "Inpatient admission was medically necessary; NS1 antigen positive "
            "with platelet count 42000 and continuous IV fluid administration."
        ),
        "documents": ["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
    },
    "pt": {
        "claim_id": "SYNTHETIC-CLM-DEMO-PT",
        "insurer": "star_health",
        "diagnosis_group": "osteoarthritis",
        "denial_reason": "ped_nondisclosure",
        "claim_type": "cashless",
        "amount": "₹2,10,000",
        "argument": "4-week conservative physiotherapy completed; appeal on medical necessity for knee surgery.",
        "documents": ["discharge_summary"],
    },
}

# The complete dengue packet the scrubber checks (mirror of the cockpit's).
SAMPLE_PACKET: Dict[str, Any] = {
    "insurer": "star_health",
    "diagnosis_group": "dengue",
    "denial_reason": "opd_convertible",
    "documents": ["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
}

_APPROVAL_WORDS = ("yes", "approve", "approved", "save it", "go ahead", "confirm", "do it", "commit")


AGENT_PROMPT = """You are the ClaimShield Desk AGENT for hospital TPA desks in India. You are not a script: you decide what to do, use tools when they help, and answer in plain, short sentences. All cases are SYNTHETIC samples. Everything you produce is a draft for human review, not legal or medical advice.

THE DESK'S JOB: Remember it — past appeal outcomes are kept in a Hindsight memory. Verify it — a new claim is checked against those past wins before anyone writes an appeal. Do it right — a packet is blocked until it carries the documents the winning cases had.

CASES ON THE DESK:
- "dengue": Star Health, dengue, Rs.1,45,000, denied as OPD-convertible, inpatient argument with NS1 report and platelet count.
- "pt": Star Health, knee osteoarthritis, Rs.2,10,000, cashless, older physiotherapy argument.

TOOLS (call them, do not guess their results):
- check_appeal {"case": "dengue"|"pt"} — runs the memory check: recalls past cases from Hindsight and returns a verdict (APPROVE = the argument is backed by past wins; VETO = do not send, with the reason and what evidence is missing) plus proof_count (how many past wins back it).
- check_packet {} — runs the pre-dispatch scrubber on the dengue packet: PASSED, WARN or BLOCKED, with the documents that are missing.
- show_rules {} — the current pre-dispatch rule checklist (names + version).
- save_outcome {"case": "dengue"|"pt", "outcome": "WON"|"LOST"} — saves an outcome into memory so future checks learn from it. HUMAN GATE: only call this after the user has clearly approved saving in their latest message; otherwise ask them first.
- lookup_knowledge {"topic": "choosing_policy"|"reimbursement"|"cashless"|"waiting_periods"|"appeals"|"", "insurer": "<insurer name or empty>", "treatment": "<treatment or empty>"} — reads the desk's insurance knowledge DOCUMENT (a JSON file: how to choose a policy and why, the reimbursement process with the full document checklist, cashless pitfalls, waiting periods, denial patterns per insurer, risks per treatment, and how to appeal). ALWAYS call this before answering general insurance questions (which policy to take, how reimbursement works, what an insurer may deny for a surgery); answer from what it returns, with reasons and checklists, and say plainly when the document has no entry instead of guessing.

OUTPUT CONTRACT — reply with exactly ONE JSON object, nothing else:
- To call a tool: {"do": "<tool name>", "args": {...}, "note": "<one short line saying what you are doing>"}
- To answer the user: {"say": "<your answer>"}
One tool per reply. After a tool result comes back you may call another tool or answer. Keep answers short, concrete, and grounded in tool results — never invent verdicts, counts, or rules you did not get from a tool.

Measured evaluation (state only if asked): memory-backed checks scored 19/20 with 5/5 adversarial cases, vs 11/20 and 0/5 for plain document search. Known limit: the check matches key terms, not deep meaning."""


def _call_model(messages: List[Dict[str, str]]) -> Optional[str]:
    """One chat/completions call. Returns the visible content or None."""
    key = config.get_openrouter_api_key()
    if not key:
        return None
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-Title": "ClaimShield Desk",
    }
    try:
        resp = httpx.post(
            f"{config.get_openrouter_base_url()}/chat/completions",
            headers=headers,
            json={
                "model": config.get_openrouter_model(),
                "messages": messages,
                # Reasoning models spend tokens thinking first (measured
                # 898/900 on the grounded prompt) — keep real headroom.
                "max_tokens": 3000,
                "temperature": 0.2,
            },
            timeout=90.0,
        )
        if resp.status_code != 200:
            return None
        choices = resp.json().get("choices") or []
        if not choices:
            return None
        content = (choices[0].get("message") or {}).get("content")
        return content.strip() if isinstance(content, str) and content.strip() else None
    except Exception:
        return None


def _parse_action(text: str) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object from the model's reply, if any."""
    start = text.find("{")
    if start < 0:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except (ValueError, TypeError):
        return None
    return obj if isinstance(obj, dict) else None


def _summarize_strategy(result: Dict[str, Any]) -> str:
    evidence = result.get("evidence") or []
    names = [str(e.get("document_id", "")) for e in evidence[:3]]
    return (
        f"verdict={result.get('verdict')} proof_count={result.get('proof_count')} "
        f"missing={result.get('missing') or []} reason={result.get('rationale', '')} "
        f"evidence_docs={names}"
    )


def _execute_tool(
    name: str,
    args: Dict[str, Any],
    *,
    adapter: Any,
    room: Any,
    rules_data: Dict[str, Any],
    user_message: str,
    out: Dict[str, Any],
    knowledge_data: Optional[Dict[str, Any]] = None,
    knowledge_path: Any = None,
) -> str:
    """Run one tool against the real services; record UI payloads in `out`."""
    if name == "check_appeal":
        case_key = str(args.get("case", "dengue")).lower()
        claim = CASES.get(case_key, CASES["dengue"])
        result = run_denial_defense(adapter, room, dict(claim))
        out["strategy_result"] = result
        return _summarize_strategy(result)
    if name == "check_packet":
        result = check_packet(dict(SAMPLE_PACKET), rules_data)
        out["packet_result"] = result
        return f"verdict={result.get('verdict')} missing={result.get('missing') or []}"
    if name == "lookup_knowledge":
        return knowledge.lookup(
            knowledge_data or {},
            topic=str(args.get("topic", "")),
            insurer=str(args.get("insurer", "")),
            treatment=str(args.get("treatment", "")),
        )
    if name == "show_rules":
        rules = rules_data.get("rules", [])
        names = [str(r.get("name", "")) for r in rules]
        return f"rules_version={rules_version(rules_data)} rules={names}"
    if name == "save_outcome":
        lowered = user_message.lower()
        if not any(word in lowered for word in _APPROVAL_WORDS):
            return (
                "NOT SAVED: the user has not approved saving in their latest "
                "message. Ask them to confirm before calling save_outcome again."
            )
        case_key = str(args.get("case", "dengue")).lower()
        claim = CASES.get(case_key, CASES["dengue"])
        outcome = str(args.get("outcome", "WON")).upper()
        content = (
            f"SYNTHETIC {claim['insurer']} {claim['diagnosis_group']} claim "
            f"{claim['amount']} {claim['claim_type']}. Appeal outcome: {outcome}. "
            f"Argument: {claim['argument']}"
        )
        scrubbed, _tokens, _layers = scrub_text(content)
        result = adapter.retain(
            document={"id": f"outcome-{claim['claim_id']}-{outcome.lower()}", "content": scrubbed},
            tags=["claimshield", "appeal_outcome", case_key],
            timestamp=None,
        )
        # The knowledge document visibly learns too (cs-012).
        knowledge.append_outcome(knowledge_path, case_key, outcome)
        return f"saved outcome={outcome} document_id={result.get('document_id')} backend={result.get('backend')}"
    return f"unknown tool: {name}"


def run_agent(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    *,
    adapter: Any,
    room: Any,
    rules_data: Dict[str, Any],
    knowledge_data: Optional[Dict[str, Any]] = None,
    knowledge_path: Any = None,
    call_model: Callable[[List[Dict[str, str]]], Optional[str]] = _call_model,
) -> Optional[Dict[str, Any]]:
    """Run the agent loop. None => no LLM answer (caller falls back)."""
    messages: List[Dict[str, str]] = [{"role": "system", "content": AGENT_PROMPT}]
    for turn in (history or [])[-6:]:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content[:800]})
    messages.append({"role": "user", "content": message[:1000]})

    actions: List[Dict[str, str]] = []
    out: Dict[str, Any] = {}
    for _round in range(MAX_TOOL_ROUNDS + 1):
        raw = call_model(messages)
        if raw is None:
            return None
        action = _parse_action(raw)
        if action is None:
            return {"reply": raw, "actions": actions, **out}
        if "say" in action and isinstance(action["say"], str):
            return {"reply": action["say"], "actions": actions, **out}
        tool = action.get("do")
        if not isinstance(tool, str):
            return {"reply": raw, "actions": actions, **out}
        args = action.get("args") if isinstance(action.get("args"), dict) else {}
        note = action.get("note") if isinstance(action.get("note"), str) else tool
        try:
            summary = _execute_tool(
                tool, args, adapter=adapter, room=room,
                rules_data=rules_data, user_message=message, out=out,
                knowledge_data=knowledge_data, knowledge_path=knowledge_path,
            )
        except Exception as exc:  # a failed tool must not kill the chat
            summary = f"tool {tool} failed: {exc}"
        actions.append({"tool": tool, "note": note, "summary": summary, "args": args})
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": f"TOOL RESULT {tool}: {summary}"})
    # Out of rounds: one last chance to answer from what the tools returned.
    raw = call_model(messages + [{"role": "user", "content": "Now answer the user from the tool results above, using the {\"say\": ...} format."}])
    if raw is None:
        return None
    action = _parse_action(raw)
    if action and isinstance(action.get("say"), str):
        return {"reply": action["say"], "actions": actions, **out}
    return {"reply": raw, "actions": actions, **out}
