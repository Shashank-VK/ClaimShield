#!/usr/bin/env python3
"""Verify Hindsight Cloud is actually live for ClaimShield Desk.

Reads the API key from ~/.config/provider-keys/hindsight.key (never
printed, never committed), then runs a retain/recall round-trip against
the real Cloud API on a throwaway bank (claimshield-verify) so the demo
bank stays clean.

Usage (from builds/claimshield-desk):
    .venv/bin/python verify_hindsight_cloud.py

Exit codes:
    0  cloud round-trip passed (backend=cloud, retain on Cloud, recall returned it)
    1  verification FAILED (backend not cloud, or retain/recall did not reach Cloud)
    2  key file not present yet (account step still pending — not a failure)
"""

import os
import sys
import time
import uuid
from pathlib import Path

KEY_FILE = Path.home() / ".config" / "provider-keys" / "hindsight.key"
VERIFY_BANK = "claimshield-verify"
MARKER = "claimshield-cloud-verify"


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> int:
    if not KEY_FILE.exists():
        print("KEY MISSING: no key file at ~/.config/provider-keys/hindsight.key yet.")
        print("The Hindsight account step is still pending — nothing to verify.")
        return 2

    key = KEY_FILE.read_text().strip()
    if not key:
        print("KEY MISSING: key file exists but is empty.")
        return 2
    print("Key file present (value never printed).")

    # Set env BEFORE importing the adapter (it reads env live, but be explicit).
    os.environ["HINDSIGHT_API_KEY"] = key
    os.environ["DECISION_MODEL_ENABLED"] = "false"
    os.environ["ENABLE_DECISION_PRUNE"] = "false"

    from backend.hindsight_adapter import HindsightAdapter

    adapter = HindsightAdapter(bank_id=VERIFY_BANK)
    backend = adapter.backend_name
    print(f"backend_name: {backend}")
    if backend != "cloud":
        fail(f"backend_name is {backend!r}, expected 'cloud' — key not picked up.")

    doc_id = f"verify-cloud-{uuid.uuid4().hex[:8]}"
    content = (
        f"{MARKER} synthetic verification document: Star Health dengue claim, "
        "denied as OPD-convertible, overturned on NS1 report and platelet count. "
        "This document exists only to prove the Cloud round-trip works."
    )
    tags = [
        "insurer:star_health",
        "denial_reason:opd_convertible",
        "diagnosis_group:dengue",
        "desk:verify",
    ]

    retained = adapter.retain(document={"id": doc_id, "content": content}, tags=tags)
    print(f"retain: status={retained.get('status')} backend={retained.get('backend')}")
    if retained.get("backend") != "cloud":
        fail("retain fell through to the in-memory backend — Cloud did not accept it.")

    # Cloud recall can lag the retain; poll briefly for the doc to appear.
    found = False
    for attempt in range(1, 7):
        hits = adapter.recall(query=MARKER, tags=tags, top_k=5)
        if any(h.get("document_id") == doc_id for h in hits):
            found = True
            print(f"recall: doc {doc_id} returned on attempt {attempt}.")
            break
        print(f"recall: attempt {attempt}/6 — doc not visible yet, waiting 5s...")
        time.sleep(5)

    if not found:
        fail("retain reached Cloud but recall never returned the document (30s).")

    print("PASS: Hindsight Cloud round-trip verified (retain + recall on real Cloud).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
