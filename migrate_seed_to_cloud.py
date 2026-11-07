#!/usr/bin/env python3
"""Migrate the 13 synthetic seed records to Hindsight Cloud bank claimshield-india.

One-off, run only after the local demo is verified green (shashank's order:
local first, then move to Cloud). Reads the key from
~/.config/provider-keys/hindsight.key (never printed, never committed).

HONEST LIMIT: the Cloud retain path carries content + tags + timestamp +
document_id only. The explicit in-memory observation fields (proof_count,
tactic, supersedes) are NOT sent to Cloud — Cloud builds its own
observations. So after migrating, the proof_count values Cloud returns may
differ from the seeded in-memory values (dengue 5, PT 6). This script
prints the Cloud-returned proof_counts so the difference is visible, not
assumed. If they differ, the demo should stay on the memory backend.

Usage (from builds/claimshield-desk):
    .venv/bin/python migrate_seed_to_cloud.py

Exit codes:
    0  all 13 records retained on Cloud and the headline dengue record recalls
    1  migration or verification FAILED
    2  key file not present
"""

import os
import sys
import time
from pathlib import Path

KEY_FILE = Path.home() / ".config" / "provider-keys" / "hindsight.key"
BANK_ID = "claimshield-india"
HEADLINE_DOC = "SYNTHETIC-CLM-E2-DENGUE-HEADLINE"
HEADLINE_TAGS = [
    "insurer:star_health",
    "denial_reason:opd_convertible",
    "diagnosis_group:dengue",
    "desk_id:hyd_01",
    "claim_type:reimbursement",
    "synthetic",
]


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
    from seed_history import seed

    adapter = HindsightAdapter(bank_id=BANK_ID)
    print(f"backend_name: {adapter.backend_name}")
    if adapter.backend_name != "cloud":
        print("FAIL: backend is not cloud — key not picked up.")
        return 1

    summary = seed(adapter)
    print(f"seeded {summary['total']} records (backend: {summary['backend']})")
    if summary["total"] != 13:
        print(f"FAIL: expected 13 records, got {summary['total']}.")
        return 1

    # Verify: headline dengue record must recall on Cloud.
    found = None
    for attempt in range(1, 7):
        hits = adapter.recall(
            query="Star Health dengue NS1 platelet IV fluids",
            tags=HEADLINE_TAGS,
            top_k=5,
        )
        for h in hits:
            if h.get("document_id") == HEADLINE_DOC:
                found = h
                break
        if found:
            print(f"recall: headline doc found on attempt {attempt}.")
            break
        print(f"recall: attempt {attempt}/6 — headline not visible yet, waiting 5s...")
        time.sleep(5)

    if not found:
        print("FAIL: headline dengue record did not recall on Cloud (30s).")
        return 1

    print(f"headline proof_count as returned by Cloud: {found.get('proof_count')}")
    print("NOTE: seeded in-memory proof_count for the headline observation was 5;")
    print("Cloud builds its own observations, so compare the value above honestly.")
    print("PASS: 13 seed records retained on Cloud bank claimshield-india.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
