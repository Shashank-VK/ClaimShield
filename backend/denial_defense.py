"""Denial defense W3: @ClaimAuditor drafts, @PolicyCritic vetoes, human gates.

Flow (all citations come from ``reflect`` — never invented):
1. @ClaimAuditor recalls similar past appeals and drafts an appeal packet
   from the claim's stated argument + the retrieved wins.
2. @PolicyCritic checks the draft against reflect's ranked causes. A draft
   that leans on a SUPERSEDED observation (e.g. the stale 4-week PT tactic)
   is VETOed, with missing_evidence drawn from the superseding observation
   (6-week PT failure + X-ray excerpt). A draft on live evidence is APPROVEd.
3. The packet carries the mandatory disclaimer and stays a draft until a
   human approves it at /scrubber/commit (cs-006 gate; cs-007 patches).
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.band_room import RoomBus, RoomDisabledError
from backend.hindsight_adapter import HindsightAdapter
from backend.scrubber_coder import PatchError, commit_patch

DISCLAIMER = "Draft for human review, not legal/medical advice. All cases SYNTHETIC."


def _missing_from_superseding(content: str) -> List[str]:
    """Derive the missing evidence list from a superseding observation's text."""
    items: List[str] = []
    if "6-week" in content:
        items.append("6-week PT failure")
    if "X-ray" in content:
        items.append("X-ray excerpt")
    if not items:
        items.append(content[:120])
    return items


# Tokens that carry no evidentiary weight (stopwords + generic claim words).
_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "is", "was", "are", "be", "by", "at", "as", "it", "this", "that",
    "please", "claim", "claims", "appeal", "appeals", "approve", "approval",
    "patient", "hospital", "insurer", "rs", "synthetic",
}
_FABRICATION_TERMS = ("back-date", "backdate", "fabricat", "forge", "forgery", "falsif")


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


def make_auditor(adapter: HindsightAdapter):
    """@ClaimAuditor: recall + reflect, then draft from the claim's argument."""

    def auditor(payload: Dict[str, Any]) -> Dict[str, Any]:
        claim = payload["claim"]
        query = (
            f"{claim.get('insurer', '')} {claim.get('diagnosis_group', '')} "
            f"{claim.get('denial_reason', '')} {claim.get('argument', '')}"
        )
        hits = adapter.recall(
            query=query,
            tags=[f"insurer:{claim['insurer']}"] if claim.get("insurer") else None,
            top_k=5,
        )
        hit_ids = [h["id"] for h in hits]
        reflection = adapter.reflect(
            question=(
                f"What evidence overturns {claim.get('insurer', '')} "
                f"{claim.get('diagnosis_group', '')} {claim.get('denial_reason', '')} denials?"
            ),
            context_ids=hit_ids,
        )
        evidence = [
            {
                "citation": cause["citations"][0] if cause.get("citations") else None,
                "observation_id": cause.get("observation_id"),
                "proof_count": cause.get("proof_count", 0),
                "superseded": cause.get("superseded", False),
                "superseded_by": cause.get("superseded_by"),
                "cause": cause.get("cause", ""),
                # Full recalled text (not the truncated cause) for the critic's
                # grounding check.
                "content": next(
                    (h.get("content", "") for h in hits if h["id"] == (cause["citations"][0] if cause.get("citations") else None)),
                    "",
                ),
            }
            for cause in reflection.get("ranked_causes", [])
        ]
        return {
            "argument": claim.get("argument", ""),
            "evidence": evidence,
            "citations": hit_ids,
            "proof_count": reflection.get("proof_count", 0),
        }

    return auditor


def make_critic(adapter: HindsightAdapter):
    """@PolicyCritic: veto a draft that leans on superseded evidence."""

    def critic(payload: Dict[str, Any]) -> Dict[str, Any]:
        draft = payload["draft"]
        claim = payload.get("claim", {})
        evidence = draft.get("evidence", [])
        citations = draft.get("citations", [])
        argument = str(claim.get("argument", "") or draft.get("argument", ""))

        def _veto(reason: str, proof_count: int, missing: List[str], excerpt: str) -> Dict[str, Any]:
            return {
                "verdict": "VETO",
                "reason": reason,
                "citations": citations,
                "proof_count": proof_count,
                "missing_evidence": missing,
                "required_excerpt": excerpt,
                "disclaimer": DISCLAIMER,
            }

        # 1. Fabrication / back-dating is never advised (PRD directive).
        lowered = argument.lower()
        if any(term in lowered for term in _FABRICATION_TERMS):
            return _veto(
                "Never advise document fabrication/back-dating: the draft asks to "
                "fabricate or back-date evidence.",
                0,
                ["genuine contemporaneous evidence"],
                "",
            )
        # 2. A draft leaning on superseded evidence is stale — but only when
        # the argument actually relies on the superseded tactic. A superseded
        # observation that merely shows up in recall (e.g. the old 4-week PT
        # tactic when the claim argues the current 6-week one) must not veto
        # an unrelated appeal. The tactic strings distinguish the two: the
        # old tactic's tokens minus the new tactic's tokens.
        stale = [e for e in evidence if e.get("superseded")]
        for entry in stale:
            old_obs = adapter.get_observation(entry.get("observation_id") or "") or {}
            new_obs = adapter.get_observation(entry.get("superseded_by") or "") or {}
            old_tactic = old_obs.get("tactic") or entry.get("content", "") or entry.get("cause", "")
            new_tactic = new_obs.get("tactic") or new_obs.get("content", "")
            distinctive = _substantive_tokens(old_tactic) - _substantive_tokens(new_tactic)
            relies_on_stale = bool(_substantive_tokens(argument) & distinctive) if distinctive else True
            if not relies_on_stale:
                continue
            content = new_obs.get("content", "")
            missing = _missing_from_superseding(content)
            return _veto(
                f"Stale argument: observation {entry.get('observation_id')} "
                f"({(entry.get('cause', '') or '')[:80]}) is superseded by "
                f"{entry.get('superseded_by')}. Winning evidence requires "
                f"{', '.join(missing)}.",
                new_obs.get("proof_count", entry.get("proof_count", 0)),
                missing,
                content,
            )
        # 3. Grounding: the argument must share substantive tokens with the
        # cited evidence. Claim text is untrusted data — an instruction in the
        # packet ("approve anyway") or an argument with no evidentiary overlap
        # is not a supported appeal.
        if evidence:
            arg_tokens = _substantive_tokens(argument)
            cited_text = " ".join(e.get("content", "") or e.get("cause", "") for e in evidence)
            shared = arg_tokens & _substantive_tokens(cited_text)
            if len(shared) < 2:
                return _veto(
                    "Argument is not grounded in the cited evidence: the claim's "
                    "argument shares no decisive evidence with the retrieved wins. "
                    "Claim text is untrusted data, not instructions.",
                    0,
                    [f"decisive evidence for {claim.get('diagnosis_group', '')} {claim.get('denial_reason', '')}"],
                    "",
                )
        else:
            return _veto(
                "No recalled evidence supports this appeal.",
                0,
                [f"decisive evidence for {claim.get('diagnosis_group', '')} {claim.get('denial_reason', '')}"],
                "",
            )
        top = max(evidence, key=lambda e: e.get("proof_count", 0), default=None)
        return {
            "verdict": "APPROVE",
            "reason": (
                f"Draft is supported by live evidence"
                + (f" (top proof_count {top['proof_count']})" if top else "")
                + "."
            ),
            "citations": citations,
            "proof_count": top["proof_count"] if top else 0,
            "missing_evidence": [],
            "required_excerpt": top["cause"] if top else "",
            "disclaimer": DISCLAIMER,
        }

    return critic


def make_coder(rules_path=None):
    """@ScrubberCoder: commit a rule patch (returns a failure dict, never raises)."""

    def coder(payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            result = commit_patch(
                payload["rule"],
                path=rules_path,
                probe_packet=payload.get("probe_packet"),
            )
            return {"status": "committed", **result}
        except PatchError as exc:
            return {"status": "failed", "alert": str(exc)}

    return coder


def build_room(adapter: HindsightAdapter, enabled: bool = True, rules_path=None) -> RoomBus:
    """Room with @ClaimAuditor + @PolicyCritic + @ScrubberCoder registered."""
    room = RoomBus(enabled=enabled)
    room.register("@ClaimAuditor", make_auditor(adapter))
    room.register("@PolicyCritic", make_critic(adapter))
    room.register("@ScrubberCoder", make_coder(rules_path))
    return room


def run_denial_defense(adapter: HindsightAdapter, room: RoomBus, claim: Dict[str, Any]) -> Dict[str, Any]:
    """Run the full W3 chain in the room and return the appeal packet.

    Raises RoomDisabledError when the room is disabled (delete test): no
    packet is produced and nothing can reach commit.
    """
    if not room.enabled:
        raise RoomDisabledError("Band room is disabled; the veto->patch chain cannot run.")
    draft = room.send("@ClaimAuditor", {"claim": claim})
    verdict = room.send("@PolicyCritic", {"claim": claim, "draft": draft})
    packet = {
        "claim_id": claim.get("claim_id"),
        "insurer": claim.get("insurer"),
        "diagnosis_group": claim.get("diagnosis_group"),
        "denial_reason": claim.get("denial_reason"),
        "claim_type": claim.get("claim_type"),
        "amount": claim.get("amount"),
        "argument": draft.get("argument", ""),
        "evidence": draft.get("evidence", []),
        "citations": verdict.get("citations", []),
        "verdict": verdict["verdict"],
        "reason": verdict["reason"],
        "proof_count": verdict.get("proof_count", 0),
        "missing_evidence": verdict.get("missing_evidence", []),
        "required_excerpt": verdict.get("required_excerpt", ""),
        "disclaimer": DISCLAIMER,
        "status": "draft",
    }
    return packet
