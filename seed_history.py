"""4-epoch seeder for the ClaimShield Desk Hindsight bank.

Seeds synthetic (SYNTHETIC-badged) claim history into bank ``claimshield-india``
in epoch order with backdated occurrence timestamps:

  E1  generic denials            (Jun 2026)
  E2  first wins                 (Aug 2026)  - incl. the headline Star Health
                                                dengue Rs.1,45,000 OPD win and
                                                the 4-week PT tactic (obs_pt_01)
  E3  Oct 2026 bulletin          (Oct 2026)  - Star Health payer bulletin:
                                                6-week PT supersedes 4-week PT
                                                (obs_pt_02 supersedes obs_pt_01)
  E4  late verdicts applied      (Nov 2026)  - delayed-intimation + room-rent
                                                verdicts arriving late

Denial patterns come from research pack-2 (30 verified judicial cases across
5 patterns: opd_convertible, ped_nondisclosure, room_rent_cap,
delayed_intimation, non_payable_items). All cases are SYNTHETIC - no real
patient data. No LLM, no network, no secrets.

Run:  python seed_history.py   (seeds the in-memory adapter and prints a summary)
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.hindsight_adapter import HindsightAdapter

BANK_ID = "claimshield-india"
HEADLINE_TAGS = [
    "insurer:star_health",
    "denial_reason:opd_convertible",
    "diagnosis_group:dengue",
    "desk_id:hyd_01",
    "claim_type:reimbursement",
    "synthetic",
]


def _rec(
    record_id: str,
    content: str,
    tags: List[str],
    timestamp: str,
    proof_count: int | None = None,
    observation: Dict[str, Any] | None = None,
    supersedes: str | None = None,
) -> Dict[str, Any]:
    rec: Dict[str, Any] = {
        "id": record_id,
        "content": content,
        "tags": tags,
        "timestamp": timestamp,
    }
    if proof_count is not None:
        rec["proof_count"] = proof_count
    if observation is not None:
        rec["observation"] = observation
    if supersedes is not None:
        rec["supersedes"] = supersedes
    return rec


def _tags(insurer: str, denial_reason: str, diagnosis_group: str, claim_type: str) -> List[str]:
    return [
        f"insurer:{insurer}",
        f"denial_reason:{denial_reason}",
        f"diagnosis_group:{diagnosis_group}",
        "desk_id:hyd_01",
        f"claim_type:{claim_type}",
        "synthetic",
    ]


# ---------------------------------------------------------------------------
# Epochs
# ---------------------------------------------------------------------------

EPOCH_1_GENERIC_DENIALS = [
    _rec(
        "SYNTHETIC-CLM-E1-DENGUE-01",
        "SYNTHETIC Star Health dengue claim Rs.98,000 reimbursement. Denial: OPD convertible under Clause 3.1, "
        "hospitalisation not justified. Verdict: REJECTED (no appeal filed yet).",
        _tags("star_health", "opd_convertible", "dengue", "reimbursement"),
        "2026-06-12T10:00:00Z",
        proof_count=1,
    ),
    _rec(
        "SYNTHETIC-CLM-E1-CATARACT-01",
        "SYNTHETIC HDFC ERGO cataract surgery claim Rs.45,000 cashless pre-auth. Deduction: room rent cap "
        "proportionate deduction applied. Verdict: PARTIAL_DEDUCTION.",
        _tags("hdfc_ergo", "room_rent_cap", "cataract", "cashless"),
        "2026-06-18T10:00:00Z",
    ),
    _rec(
        "SYNTHETIC-CLM-E1-INTIMATION-01",
        "SYNTHETIC ICICI Lombard acute gastroenteritis claim Rs.62,000 reimbursement. Repudiation: delayed "
        "intimation, documents submitted late. Verdict: REJECTED (appeal pending).",
        _tags("icici_lombard", "delayed_intimation", "gastroenteritis", "reimbursement"),
        "2026-06-25T10:00:00Z",
    ),
]

EPOCH_2_FIRST_WINS = [
    _rec(
        "SYNTHETIC-CLM-E2-DENGUE-HEADLINE",
        "SYNTHETIC Star Health dengue claim Rs.1,45,000 reimbursement. Initial denial: OPD convertible under "
        "Clause 3.1. Appeal OVERTURNED_FULL with NS1 antigen positive report, platelet count 42000, and "
        "continuous IV fluid administration sheets proving inpatient medical necessity.",
        list(HEADLINE_TAGS),
        "2026-08-05T11:00:00Z",
    ),
    _rec(
        "SYNTHETIC-CLM-E2-DENGUE-02",
        "SYNTHETIC Star Health dengue claim Rs.1,12,000 reimbursement. Denial: OPD convertible. Appeal "
        "OVERTURNED_FULL with NS1 antigen report and indoor case papers showing IV fluids and vitals monitoring.",
        list(HEADLINE_TAGS),
        "2026-08-12T11:00:00Z",
    ),
    _rec(
        "SYNTHETIC-CLM-E2-PT-4WK",
        "SYNTHETIC Star Health knee osteoarthritis claim Rs.2,10,000 cashless. Appeal OVERTURNED_FULL on "
        "4-week conservative physiotherapy documentation accepted as conservative-trial evidence.",
        _tags("star_health", "ped_nondisclosure", "osteoarthritis", "cashless"),
        "2026-08-15T10:00:00Z",
        observation={"id": "obs_pt_01", "proof_count": 3, "tactic": "4-week PT conservative trial"},
    ),
    _rec(
        "SYNTHETIC-CLM-E2-DENGUE-03",
        "SYNTHETIC Star Health dengue claim Rs.87,500 reimbursement. Denial: OPD convertible. Appeal "
        "OVERTURNED_FULL: treating physician advised admission on clinical presentation; desk referee opinion "
        "cannot override the attending specialist.",
        list(HEADLINE_TAGS),
        "2026-08-19T11:00:00Z",
    ),
    _rec(
        "SYNTHETIC-CLM-E2-DENGUE-04",
        "SYNTHETIC Star Health dengue claim Rs.1,28,400 reimbursement. Denial: OPD convertible. Appeal "
        "OVERTURNED_FULL with discharge summary, NS1 antigen report and final bill (ICD-10) proving admission.",
        list(HEADLINE_TAGS),
        "2026-08-26T11:00:00Z",
    ),
    _rec(
        "SYNTHETIC-CLM-E2-DENGUE-05",
        "SYNTHETIC Star Health dengue claim Rs.96,300 reimbursement. Denial: OPD convertible. Appeal "
        "OVERTURNED_FULL: emergency admission warranted by sudden fever with severe weakness and sepsis markers.",
        list(HEADLINE_TAGS),
        "2026-08-29T11:00:00Z",
    ),
]

EPOCH_3_BULLETIN_CONTRADICTION = [
    _rec(
        "SYNTHETIC-CLM-E3-BULLETIN-PT6WK",
        "SYNTHETIC Star Health Oct 2026 payer bulletin: 4-week physiotherapy conservative trial REJECTED as "
        "insufficient; 6-week conservative PT failure plus X-ray excerpt now required for knee osteoarthritis "
        "appeals. This bulletin supersedes the 4-week PT tactic (obs_pt_01).",
        _tags("star_health", "ped_nondisclosure", "osteoarthritis", "cashless"),
        "2026-10-20T10:00:00Z",
        observation={"id": "obs_pt_02", "proof_count": 6, "tactic": "6-week conservative PT trial"},
        supersedes="obs_pt_01",
    ),
    _rec(
        "SYNTHETIC-CLM-E3-ENTERIC-01",
        "SYNTHETIC Star Health enteric fever with sepsis claim Rs.48,089 reimbursement. Denial: PED "
        "non-disclosure invoked against an unrelated illness. Appeal OVERTURNED_FULL: insurer must prove the "
        "undisclosed condition caused the claimed event (causal nexus); it did not.",
        _tags("star_health", "ped_nondisclosure", "enteric_fever", "reimbursement"),
        "2026-10-24T10:00:00Z",
    ),
]

EPOCH_4_LATE_VERDICTS = [
    _rec(
        "SYNTHETIC-CLM-E4-INTIMATION-WIN",
        "SYNTHETIC ICICI Lombard acute gastroenteritis claim Rs.62,000 reimbursement (late verdict on the "
        "Jun 2026 delayed-intimation repudiation). Appeal OVERTURNED_FULL: emergency hospitalisation cannot be "
        "defeated by delay in intimation; the insurer failed to examine the treating doctor.",
        _tags("icici_lombard", "delayed_intimation", "gastroenteritis", "reimbursement"),
        "2026-11-02T10:00:00Z",
    ),
    _rec(
        "SYNTHETIC-CLM-E4-ROOMRENT-PARTIAL",
        "SYNTHETIC HDFC ERGO cataract surgery claim Rs.45,000 cashless (late verdict on the Jun 2026 room-rent "
        "deduction). Verdict: PARTIAL_DEDUCTION stands, but the proportionate deduction is capped to the "
        "room-rent excess only, not the full bill.",
        _tags("hdfc_ergo", "room_rent_cap", "cataract", "cashless"),
        "2026-11-03T10:00:00Z",
    ),
]

EPOCHS: List[Dict[str, Any]] = [
    {"name": "E1_generic_denials", "records": EPOCH_1_GENERIC_DENIALS},
    {"name": "E2_first_wins", "records": EPOCH_2_FIRST_WINS},
    {"name": "E3_bulletin_contradiction", "records": EPOCH_3_BULLETIN_CONTRADICTION},
    {"name": "E4_late_verdicts", "records": EPOCH_4_LATE_VERDICTS},
]


def seed(adapter: HindsightAdapter | None = None) -> Dict[str, Any]:
    """Retain all epochs in order into ``adapter`` (fresh in-memory one by default).

    Returns a summary with the epochs, the retained record dicts (in load order)
    and per-epoch counts. The adapter's scope observations accumulate proof_count
    as corroborating wins land on the same insurer+denial_reason+diagnosis_group.
    """
    adapter = adapter or HindsightAdapter()
    retained: List[Dict[str, Any]] = []
    epoch_counts: Dict[str, int] = {}
    for epoch in EPOCHS:
        count = 0
        for record in epoch["records"]:
            adapter.retain(
                document=record,
                tags=record["tags"],
                timestamp=record["timestamp"],
            )
            retained.append(record)
            count += 1
        epoch_counts[epoch["name"]] = count
    return {
        "bank_id": BANK_ID,
        "epochs": [e["name"] for e in EPOCHS],
        "epoch_counts": epoch_counts,
        "records": retained,
        "total": len(retained),
        "backend": adapter.backend_name,
    }


if __name__ == "__main__":
    summary = seed()
    print(f"Seeded {summary['total']} synthetic records into bank {summary['bank_id']} "
          f"(backend: {summary['backend']})")
    for name, count in summary["epoch_counts"].items():
        print(f"  {name}: {count} records")
