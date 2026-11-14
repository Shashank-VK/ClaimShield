"""Insurance knowledge document (cs-012) — the desk's readable brain.

Per shashank's call (2026-11-14): for the demo, facts live in a DOCUMENT,
not inside the Hindsight bank. One JSON file the agent reads through its
lookup_knowledge tool: insurer denial patterns, reimbursement/cashless
processes and document checklists, waiting periods, policy-choice
guidance and the appeals path. Anyone can open the file and see exactly
what the agent knows; a research refresh rewrites it; saved outcomes are
appended to its learned_outcomes so the document visibly grows.

Hindsight keeps its own job — the episodic win/loss memory behind the
case checks (proof counts, vetoes). Facts here, memory there.
"""

from __future__ import annotations

import json
import re
import textwrap
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parent / "knowledge" / "insurance_knowledge.json"

_TOPICS = ("choosing_policy", "reimbursement", "cashless", "waiting_periods", "appeals", "statutory_rights")


def load_knowledge(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path) if path else DEFAULT_KNOWLEDGE_PATH
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def lookup(
    data: Dict[str, Any],
    topic: str = "",
    insurer: str = "",
    treatment: str = "",
) -> str:
    """Return the relevant slice of the knowledge document as compact text."""
    topic = (topic or "").strip().lower()
    insurer = (insurer or "").strip().lower()
    treatment = (treatment or "").strip().lower()
    parts: List[str] = []

    # Hidden traps first — they carry the actionable caps and decisions.
    traps = data.get("hidden_traps", [])
    if topic == "hidden_traps":
        if traps:
            parts.append(f"hidden_traps: {json.dumps(traps, ensure_ascii=False)}")
    elif traps:
        query = f"{topic} {insurer} {treatment}"
        matched = []
        for t in traps:
            ins = [str(i).lower() for i in t.get("insurers", [])]
            trt = [str(x).lower() for x in t.get("treatments", [])]
            kw = [str(k).lower() for k in t.get("keywords", [])]
            if insurer and any(insurer in i or i in insurer for i in ins):
                matched.append(t)
            elif treatment and any(treatment in x or x.split("/")[0].strip() in treatment for x in trt):
                matched.append(t)
            elif any(k in query for k in kw):
                matched.append(t)
        if matched:
            parts.append(f"hidden_traps: {json.dumps(matched, ensure_ascii=False)}")

    if topic in _TOPICS and data.get(topic):
        parts.append(f"{topic}: {json.dumps(data[topic], ensure_ascii=False)}")
    if insurer:
        for entry in data.get("insurers", []):
            if insurer in str(entry.get("name", "")).lower():
                parts.append(f"insurer {entry['name']}: {json.dumps(entry, ensure_ascii=False)}")
    if treatment:
        for entry in data.get("treatment_risks", []):
            hay = str(entry.get("treatment", "")).lower()
            if treatment in hay or hay.split("/")[0].strip() in treatment:
                parts.append(f"treatment {entry['treatment']}: {json.dumps(entry, ensure_ascii=False)}")
    if not parts:
        available = ", ".join(_TOPICS + ("hidden_traps",))
        names = ", ".join(e.get("name", "") for e in data.get("insurers", []))
        treats = ", ".join(e.get("treatment", "") for e in data.get("treatment_risks", []))
        return (
            "No matching entry in the knowledge document. "
            f"Topics available: {available}. Insurers covered: {names}. Treatments covered: {treats}."
        )
    return "\n".join(parts)[:6000]


# ---------------------------------------------------------------------------
# Deterministic chat answers (cs-014): /assistant/chat READS THIS DOCUMENT
# and answers insurance questions straight from it — no LLM key needed, so
# a question never comes back {"reply": null} just because the model is
# off. Desk commands (run / check / step / packet…) are NOT knowledge
# questions: they return None here so the agent / scripted routing keeps
# owning them.

_INSURER_ALIASES = {
    "star": "Star Health",
    "bajaj": "Bajaj Allianz (now Bajaj General)",
    "hdfc": "HDFC Ergo",
    "icici": "ICICI Lombard",
    "niva": "Niva Bupa",
    "care": "Care Health",
}

_TREATMENT_WORDS = (
    "knee", "cataract", "dengue", "robotic", "robot",
    "hernia", "gallbladder", "hysterectomy", "fever",
)

_COMMAND_START = re.compile(r"^(run|do|execute|show|check|approve|save|scrub)\b")
_COMMAND_PHRASES = ("step", "past wins", "packet", "this claim")


def _trim(text: Any, width: int) -> str:
    return textwrap.shorten(" ".join(str(text or "").split()), width=width, placeholder="…")


def _trap_full(t: Dict[str, Any]) -> str:
    """One trap in full: clause -> worked example -> decision."""
    lines = [str(t.get("trap", "")).strip(), str(t.get("hidden_clause", "")).strip()]
    if t.get("worked_example"):
        lines.append(str(t["worked_example"]).strip())
    lines.append(f"Decision: {t.get('decision', '')}")
    return "\n".join(x for x in lines if x)


def _traps_for_insurer(data: Dict[str, Any], canonical: str) -> List[Dict[str, Any]]:
    canon = canonical.lower()
    out: List[Dict[str, Any]] = []
    for t in data.get("hidden_traps", []):
        for ins in t.get("insurers", []):
            il = str(ins).lower()
            if il and (il in canon or canon in il):
                out.append(t)
                break
    return out


def _traps_for_treatment(data: Dict[str, Any], word: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for t in data.get("hidden_traps", []):
        trts = [str(x).lower() for x in t.get("treatments", [])]
        kws = [str(k).lower() for k in t.get("keywords", [])]
        if any(word in x for x in trts) or word in kws:
            out.append(t)
    return out


def answer_question(data: Dict[str, Any], message: str) -> Optional[str]:
    """Answer an insurance question from the knowledge document.

    Returns a plain-text reply, or None when the message is a desk
    command or matches nothing the document covers.
    """
    if not data or not message:
        return None
    msg = " ".join(str(message).lower().split())

    # Command guard: desk actions belong to the agent / scripted routing.
    if _COMMAND_START.match(msg):
        return None
    if any(p in msg for p in _COMMAND_PHRASES):
        return None

    insurer: Optional[str] = None
    for alias, canonical in _INSURER_ALIASES.items():
        if re.search(rf"\b{alias}\b", msg):
            insurer = canonical
            break
    treatment: Optional[str] = None
    for w in _TREATMENT_WORDS:
        if re.search(rf"\b{w}\b", msg):
            treatment = "robotic" if w == "robot" else w
            break

    # a) Hidden traps / red flags — list them all.
    if re.search(r"red flags?|hidden|traps?|watch out", msg):
        traps = data.get("hidden_traps", [])
        if traps:
            lines = ["Hidden traps in these policies — the clauses that quietly cut claims:"]
            for i, t in enumerate(traps, 1):
                lines.append(
                    f"{i}. {t.get('trap', '')} — {_trim(t.get('hidden_clause', ''), 200)} "
                    f"Decision: {t.get('decision', '')}"
                )
            return "\n".join(lines)

    # b) Reimbursement process + documents.
    if "reimburse" in msg:
        r = data.get("reimbursement") or {}
        if r:
            lines = ["Reimbursement — you pay the hospital first, then claim the money back from the insurer."]
            if r.get("when"):
                lines.append(str(r["when"]))
            if r.get("steps"):
                lines.append("How it works:")
                lines += [f"{i}. {s}" for i, s in enumerate(r["steps"], 1)]
            if r.get("documents"):
                lines.append("Documents needed:")
                lines += [f"- {doc}" for doc in r["documents"]]
            if r.get("common_rejection_reasons"):
                lines.append("Common rejection reasons:")
                lines += [f"- {x}" for x in r["common_rejection_reasons"]]
            return "\n".join(lines)

    # c) Cashless process + pitfalls.
    if "cashless" in msg:
        c = data.get("cashless") or {}
        if c:
            lines = ["Cashless — the insurer settles directly with a network hospital."]
            if c.get("steps"):
                lines.append("How it works:")
                lines += [f"{i}. {s}" for i, s in enumerate(c["steps"], 1)]
            if c.get("pitfalls"):
                lines.append("Watch out:")
                lines += [f"- {x}" for x in c["pitfalls"]]
            return "\n".join(lines)

    # d) Waiting periods.
    if "waiting" in msg:
        w = data.get("waiting_periods") or {}
        if w:
            lines = ["Waiting periods — these claims are not payable until the wait is over:"]
            if w.get("initial"):
                lines.append(f"Initial wait: {w['initial']}")
            if w.get("specific_diseases"):
                lines.append(f"Specific diseases: {w['specific_diseases']}")
            if w.get("pre_existing"):
                lines.append(f"Pre-existing diseases: {w['pre_existing']}")
            if w.get("maternity"):
                lines.append(f"Maternity: {w['maternity']}")
            if w.get("note"):
                lines.append(str(w["note"]))
            return "\n".join(lines)

    # e) Appeals path (+ statutory-rights highlights).
    if re.search(r"appeal|grievance|ombudsman", msg):
        a = data.get("appeals") or {}
        if a:
            lines = ["If a claim is denied or cut, climb the ladder — in this order:"]
            for i, rung in enumerate(a.get("ladder", []), 1):
                lines.append(
                    f"{i}. {rung.get('forum', '')} — {rung.get('what', '')} "
                    f"(Timeline: {rung.get('timeline', '')})"
                )
            if a.get("success_factors"):
                lines.append("What wins appeals:")
                lines += [f"- {x}" for x in a["success_factors"]]
            rights = data.get("statutory_rights") or []
            if rights:
                lines.append("Rights backing you:")
                lines += [f"- {x}" for x in rights[:3]]
            return "\n".join(lines)

    # f) Choosing a policy.
    if re.search(r"which insurance|which policy|best policy|choosing|choose", msg):
        c = data.get("choosing_policy") or {}
        if c:
            lines = ["Choosing a policy — match the plan to who is covered:"]
            for key, val in (c.get("by_profile") or {}).items():
                lines.append(f"{key.replace('_', ' ').title()}: {val}")
            if c.get("red_flags"):
                lines.append("Red flags when buying:")
                lines += [f"- {x}" for x in c["red_flags"]]
            return "\n".join(lines)

    # g) Statutory rights.
    if re.search(r"\brights\b|irdai", msg):
        rights = data.get("statutory_rights") or []
        if rights:
            lines = ["Your statutory rights (IRDAI rules — they bind every insurer):"]
            lines += [f"- {x}" for x in rights]
            return "\n".join(lines)

    # h) A named insurer: metrics, denial patterns, its hidden traps.
    if insurer:
        entry = next((e for e in data.get("insurers", []) if e.get("name") == insurer), None)
        if entry:
            lines = [f"{entry['name']} — what this desk watches for:"]
            m = entry.get("metrics", {}) or {}
            bits = []
            if m.get("complaints_per_10k_claims") is not None:
                bits.append(f"complaints {m['complaints_per_10k_claims']} per 10,000 claims")
            if m.get("csr_3yr_avg"):
                bits.append(f"claim settlement ratio (3-yr avg) {m['csr_3yr_avg']}")
            if m.get("icr"):
                bits.append(f"incurred claim ratio {m['icr']}")
            if m.get("network_hospitals"):
                bits.append(f"network hospitals {m['network_hospitals']}")
            if bits:
                lines.append(" · ".join(bits))
            patterns = entry.get("patterns", [])[:3]
            if patterns:
                lines.append("Known denial patterns:")
                for p in patterns:
                    lines.append(f"- {p.get('pattern', '')} — {_trim(p.get('prevention', ''), 200)}")
            traps = _traps_for_insurer(data, insurer)
            if traps:
                lines.append("Hidden traps on this insurer's plans:")
                lines += [_trap_full(t) for t in traps]
            return "\n".join(lines)

    # i) A named treatment: risk entry + its hidden traps.
    if treatment:
        parts: List[str] = []
        for e in data.get("treatment_risks", []):
            if treatment in str(e.get("treatment", "")).lower():
                lines = [f"{str(e['treatment']).title()} — risks this desk prepares for:"]
                lines += [f"- {x}" for x in e.get("risks", [])]
                if e.get("prepare"):
                    lines.append("Prepare:")
                    lines += [f"- {x}" for x in e["prepare"]]
                parts.append("\n".join(lines))
        parts += [_trap_full(t) for t in _traps_for_treatment(data, treatment)]
        if parts:
            return "\n\n".join(parts)

    # j) Any trap whose keywords show up in the message.
    matched = [
        t for t in data.get("hidden_traps", [])
        if any(
            re.search(rf"\b{re.escape(str(k).lower())}\b", msg)
            for k in t.get("keywords", []) if k
        )
    ]
    if matched:
        return "\n\n".join(_trap_full(t) for t in matched)

    # k) Nothing in the document covers this.
    return None


def append_outcome(path: Optional[Path], case_key: str, outcome: str) -> bool:
    """Append a saved outcome to the document's learned_outcomes (visible learning)."""
    p = Path(path) if path else DEFAULT_KNOWLEDGE_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        data.setdefault("learned_outcomes", []).append(
            {"case": case_key, "outcome": outcome.upper(), "saved_on": date.today().isoformat()}
        )
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception:
        return False
