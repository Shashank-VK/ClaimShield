#!/usr/bin/env python3
"""Check the two demo-critical behaviours against Hindsight Cloud directly.

Runs the dengue strategy (beat 1/4 shape) and the stale 4-week PT claim
(beat 3) through run_denial_defense with a Cloud adapter — WITHOUT importing
backend.main, so the seeder does NOT re-run and the bank is not double-seeded.

Usage (from builds/claimshield-desk):
    .venv/bin/python check_cloud_beats.py

Exit 0: both behaviours observed and printed (verdicts may differ from
memory — the point is to report Cloud's real behaviour, not to force a pass).
Exit 1: the Cloud calls themselves failed.
Exit 2: key file not present.
"""

import os
import sys
from pathlib import Path

KEY_FILE = Path.home() / ".config" / "provider-keys" / "hindsight.key"
BANK_ID = "claimshield-india"

DENGUE = {
    "claim_id": "SYNTHETIC-CLM-DEMO-DENGUE",
    "insurer": "star_health",
    "diagnosis_group": "dengue",
    "denial_reason": "opd_convertible",
    "claim_type": "reimbursement",
    "amount": "₹1,45,000",
    "argument": "Inpatient admission was medically necessary; NS1 antigen positive with platelet count 42000 and continuous IV fluid administration.",
    "documents": ["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
}
PT = {
    "claim_id": "SYNTHETIC-CLM-DEMO-PT",
    "insurer": "star_health",
    "diagnosis_group": "osteoarthritis",
    "denial_reason": "ped_nondisclosure",
    "claim_type": "cashless",
    "amount": "₹2,10,000",
    "argument": "4-week conservative physiotherapy completed; appeal on medical necessity for knee surgery.",
    "documents": ["discharge_summary"],
}


def main() -> int:
    if not KEY_FILE.exists():
        print("KEY MISSING: no key file at ~/.config/provider-keys/hindsight.key yet.")
        return 2
    key = KEY_FILE.read_text().strip()
    if not key:
        print("KEY MISSING: key file exists but is empty.")
        return 2
    print("Key file present (value never printed).")

    os.environ["HINDSIGHT_API_KEY"] = key
    os.environ["DECISION_MODEL_ENABLED"] = "false"
    os.environ["ENABLE_DECISION_PRUNE"] = "false"

    from backend.hindsight_adapter import HindsightAdapter
    from backend.denial_defense import build_room, run_denial_defense

    adapter = HindsightAdapter(bank_id=BANK_ID)
    print(f"backend_name: {adapter.backend_name}")
    if adapter.backend_name != "cloud":
        print("FAIL: backend is not cloud.")
        return 1

    room = build_room(adapter, enabled=True)

    try:
        d = run_denial_defense(adapter, room, DENGUE)
        print(
            f"CLOUD dengue strategy: verdict={d.get('verdict')} "
            f"proof_count={d.get('proof_count')} "
            f"citations={d.get('citations')}"
        )
    except Exception as e:  # noqa: BLE001 - report, don't crash the PT check
        print(f"CLOUD dengue strategy: ERROR {type(e).__name__}: {e}")
        return 1

    try:
        p = run_denial_defense(adapter, room, PT)
        print(
            f"CLOUD PT claim: verdict={p.get('verdict')} "
            f"proof_count={p.get('proof_count')} "
            f"missing_evidence={p.get('missing_evidence')}"
        )
    except Exception as e:  # noqa: BLE001
        print(f"CLOUD PT claim: ERROR {type(e).__name__}: {e}")
        return 1

    print("Memory-backend expectations for comparison: dengue APPROVE proof_count 5;")
    print("PT VETO proof_count 6, missing ['6-week PT failure', 'X-ray excerpt'].")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
