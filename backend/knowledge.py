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
