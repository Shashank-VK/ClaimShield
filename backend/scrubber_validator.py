"""Pre-dispatch scrubber validator (PRD §6.6, W1).

Reads declarative rules from ``scrubber_rules.json`` and checks a packet
manifest against them. The checker never invents a rule: every BLOCKED/WARN
cites a ``rule_id`` present in the file, and a packet with no matching active
rule PASSES with ``rule_id`` None.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "scrubber_rules.json"


def load_rules(path: Path | str = DEFAULT_RULES_PATH) -> Dict[str, Any]:
    """Load the rules file (``{"rules": [...], "rule_history": [...]}``)."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_rules(data: Dict[str, Any], path: Path | str = DEFAULT_RULES_PATH) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def active_rules(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [r for r in data.get("rules", []) if r.get("is_active")]


def rules_version(data: Dict[str, Any]) -> int:
    """Highest version among active rules (0 when no rules are loaded)."""
    act = active_rules(data)
    return max((r.get("version", 0) for r in act), default=0)


def _match_rule(packet: Dict[str, Any], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for rule in active_rules(data):
        if (
            rule.get("insurer") == packet.get("insurer")
            and rule.get("diagnosis_group") == packet.get("diagnosis_group")
            and rule.get("denial_reason") == packet.get("denial_reason")
        ):
            return rule
    return None


def check_packet(packet: Dict[str, Any], data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Check a packet manifest.

    ``packet``: ``{"insurer", "diagnosis_group", "denial_reason",
    "documents": [names...]}``. Returns ``{"verdict": PASS|WARN|BLOCKED,
    "missing": [...], "rule_id", "source_obs", "proof_count", "version"}``.
    """
    if data is None:
        data = load_rules()
    rule = _match_rule(packet, data)
    if rule is None:
        return {
            "verdict": "PASS",
            "missing": [],
            "rule_id": None,
            "source_obs": None,
            "proof_count": 0,
            "version": 0,
            "note": "no matching active rule",
        }
    documents = set(packet.get("documents", []))
    missing = [d for d in rule.get("requires", []) if d not in documents]
    if any(d in rule.get("blocks_when_missing", []) for d in missing):
        verdict = "BLOCKED"
    elif any(d in rule.get("warn_when_missing", []) for d in missing):
        verdict = "WARN"
    else:
        verdict = "PASS"
    return {
        "verdict": verdict,
        "missing": missing,
        "rule_id": rule["rule_id"],
        "source_obs": rule.get("source_obs"),
        "proof_count": rule.get("proof_count", 0),
        "version": rule.get("version", 0),
    }


def rollback(rule_id: str, to_version: int, path: Path | str = DEFAULT_RULES_PATH) -> Dict[str, Any]:
    """Roll back a rule family to a prior version: flip ``is_active`` and log it.

    ``rule_id`` is the family prefix (e.g. ``star_health_dengue_opd``); the
    versioned rule ids are ``<family>_v<version>``. Returns the restored rule.
    """
    data = load_rules(path)
    family = [r for r in data.get("rules", []) if r["rule_id"].startswith(rule_id)]
    if not family:
        raise ValueError(f"no rule family {rule_id!r}")
    target = next((r for r in family if r.get("version") == to_version), None)
    if target is None:
        raise ValueError(f"no version {to_version} for rule family {rule_id!r}")
    for rule in family:
        rule["is_active"] = rule is target
    data.setdefault("rule_history", []).append({
        "action": "rollback",
        "rule_id": target["rule_id"],
        "version": to_version,
        "source_obs": target.get("source_obs"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    save_rules(data, path)
    return target
