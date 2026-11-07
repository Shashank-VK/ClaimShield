"""ScrubberCoder (W6): patch scrubber_rules.json after human approval.

The coder never writes a bad rule: the patch is validated FIRST, applied to
an in-memory copy, and only then saved. If the supplied probe packet is not
BLOCKED by the new rule, the patch is rolled back (the file is restored to
its pre-patch bytes) and the caller gets a 422-style error — no silent bad
state. The committed rule's diff is fully visible: rule_id, version,
supersedes, source_obs and proof_count are recorded in the rule itself and
in rule_history.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from backend.scrubber_validator import (
    DEFAULT_RULES_PATH,
    check_packet,
    load_rules,
    save_rules,
)

REQUIRED_FIELDS = (
    "family",
    "insurer",
    "diagnosis_group",
    "denial_reason",
    "requires",
    "source_obs",
)


class PatchError(ValueError):
    """A patch that failed validation or its probe check (nothing was written)."""


def validate_rule(rule: Dict[str, Any]) -> None:
    """Raise PatchError on any malformed patch (checked before any write)."""
    for field in REQUIRED_FIELDS:
        if field not in rule or rule[field] in (None, "", []):
            raise PatchError(f"patch is missing required field: {field}")
    requires = rule["requires"]
    if not isinstance(requires, list) or not all(isinstance(d, str) for d in requires):
        raise PatchError("patch 'requires' must be a non-empty list of document names")
    for field in ("blocks_when_missing", "warn_when_missing"):
        items = rule.get(field, [])
        if not isinstance(items, list) or not all(isinstance(d, str) for d in items):
            raise PatchError(f"patch '{field}' must be a list of document names")
        for doc in items:
            if doc not in requires:
                raise PatchError(
                    f"patch '{field}' names {doc!r}, which is not in 'requires'"
                )
    if not isinstance(rule.get("proof_count", 0), int) or rule.get("proof_count", 0) < 0:
        raise PatchError("patch 'proof_count' must be a non-negative integer")


def apply_patch_to_data(data: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a validated patch to a rules dict (in memory). Returns the new rule."""
    validate_rule(rule)
    family = rule["family"]
    siblings = [r for r in data.get("rules", []) if r["rule_id"].startswith(family + "_v")]
    prev_version = max((r.get("version", 0) for r in siblings), default=0)
    version = prev_version + 1
    new_rule = {
        "rule_id": f"{family}_v{version}",
        "insurer": rule["insurer"],
        "diagnosis_group": rule["diagnosis_group"],
        "denial_reason": rule["denial_reason"],
        "requires": list(rule["requires"]),
        "blocks_when_missing": list(rule.get("blocks_when_missing", [])),
        "warn_when_missing": list(rule.get("warn_when_missing", [])),
        "version": version,
        "supersedes": prev_version if prev_version else None,
        "source_obs": rule["source_obs"],
        "proof_count": rule.get("proof_count", 0),
        "is_active": True,
    }
    for old in siblings:
        old["is_active"] = False
    data.setdefault("rules", []).append(new_rule)
    data.setdefault("rule_history", []).append({
        "action": "patched",
        "rule_id": new_rule["rule_id"],
        "version": version,
        "supersedes": new_rule["supersedes"],
        "source_obs": new_rule["source_obs"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return new_rule


def commit_patch(
    rule: Dict[str, Any],
    path: Path | str = DEFAULT_RULES_PATH,
    probe_packet: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate, commit, and probe-verify a patch. Rolls back on probe failure.

    Returns {"rule": committed_rule, "previous_version": int,
    "probe_verdict": str|None}. Raises PatchError (file untouched) when the
    patch is invalid or the probe packet is not BLOCKED by the new rule.
    """
    if path is None:
        path = DEFAULT_RULES_PATH
    validate_rule(rule)
    original = load_rules(path)
    working = copy.deepcopy(original)
    new_rule = apply_patch_to_data(working, rule)
    probe_verdict = None
    if probe_packet is not None:
        probe_verdict = check_packet(probe_packet, working)["verdict"]
        if probe_verdict != "BLOCKED":
            raise PatchError(
                f"patch {new_rule['rule_id']} did not BLOCK the probe packet "
                f"(verdict: {probe_verdict}); nothing was written"
            )
    save_rules(working, path)
    return {
        "rule": new_rule,
        "previous_version": new_rule["supersedes"],
        "probe_verdict": probe_verdict,
    }
