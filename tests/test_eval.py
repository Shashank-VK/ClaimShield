"""Tests for the 3-system evaluation harness + the four demo beats (cs-009)."""

import json
import shutil
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.hindsight_adapter import HindsightAdapter
from backend.main import create_app
from eval.harness import ADVERSARIAL, CASES, RESULTS_PATH, run_harness
from seed_history import seed

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_RULES = PROJECT_ROOT / "scrubber_rules.json"

DENGUE_CLAIM = {
    "claim_id": "SYNTHETIC-CLM-DEMO-DENGUE",
    "insurer": "star_health",
    "diagnosis_group": "dengue",
    "denial_reason": "opd_convertible",
    "claim_type": "reimbursement",
    "amount": "₹1,45,000",
    "argument": "Inpatient admission was medically necessary; NS1 antigen positive "
    "with platelet count 42000 and continuous IV fluid administration.",
    "documents": ["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
}

PT_CLAIM = {
    "claim_id": "SYNTHETIC-CLM-DEMO-PT",
    "insurer": "star_health",
    "diagnosis_group": "osteoarthritis",
    "denial_reason": "ped_nondisclosure",
    "claim_type": "cashless",
    "amount": "₹2,10,000",
    "argument": "4-week conservative physiotherapy completed; appeal on medical "
    "necessity for knee surgery.",
    "documents": ["discharge_summary"],
}

V4_PATCH = {
    "family": "star_health_dengue_opd",
    "insurer": "star_health",
    "diagnosis_group": "dengue",
    "denial_reason": "opd_convertible",
    "requires": ["discharge_summary", "ns1_antigen_report", "final_bill_icd10", "platelet_report"],
    "blocks_when_missing": ["discharge_summary", "platelet_report"],
    "warn_when_missing": ["ns1_antigen_report"],
    "source_obs": "obs_304",
    "proof_count": 6,
}

COMPLETE_DENGUE_PACKET = {
    "insurer": "star_health",
    "diagnosis_group": "dengue",
    "denial_reason": "opd_convertible",
    "documents": ["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
}


def test_harness_runs_all_cases_and_writes_real_numbers():
    results = run_harness()
    assert len(CASES) == 20
    assert len(ADVERSARIAL) == 5
    assert len(results["cases"]) == 20
    assert len(results["adversarial"]) == 5
    for name, s in results["systems"].items():
        assert s["main_total"] == 20 and s["adversarial_total"] == 5
        assert 0.0 <= s["main_accuracy"] <= 1.0
        assert 0.0 <= s["adversarial_accuracy"] <= 1.0
    assert RESULTS_PATH.exists()
    stored = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    assert stored["systems"] == results["systems"]
    assert stored["backend"] == "memory"
    assert stored["band_mode"] == "local"


def test_poisoned_packet_is_vetoed():
    results = run_harness()
    poisoned = next(c for c in results["adversarial"] if c["id"] == "ADV-01-poisoned")
    assert poisoned["hindsight"] == "VETO", "claim text is untrusted data: 'approve anyway' must not win"
    assert all(c["hindsight"] == "VETO" for c in results["adversarial"])
    # Plain RAG has no defense: it approves the poisoned packet. That is the
    # point of the comparison, and the harness must show it honestly.
    assert poisoned["plain_rag"] == "APPROVE"


def test_demo_beats_end_to_end():
    tmp = Path(tempfile.mkdtemp()) / "scrubber_rules.json"
    shutil.copy(REAL_RULES, tmp)
    adapter = HindsightAdapter()
    seed(adapter)
    client = TestClient(create_app(adapter, rules_path=tmp))

    # Beat 1: generic Day-1 appeal (no history) fails.
    resp = client.post(
        "/appeals/strategy",
        json={**DENGUE_CLAIM, "claim_id": "SYNTHETIC-CLM-DAY1", "insurer": "care_health",
              "argument": "Please approve this claim."},
    )
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "VETO"

    # Beat 2: raw SSN in the packet triggers the redaction toast.
    resp = client.post(
        "/webhooks/claim-intake",
        json={"document_id": "SYNTHETIC-CLM-SSN-01",
              "content": "Claim packet: SSN 123-45-6789 in the document.",
              "tags": ["insurer:star_health", "synthetic"]},
    )
    assert resp.status_code == 200
    assert "[REDACTED:ssn]" in resp.json()["pii_scrubbed"]

    # Beat 3: the critic vetoes the stale 4-week PT argument.
    resp = client.post("/appeals/strategy", json=PT_CLAIM)
    packet = resp.json()
    assert packet["verdict"] == "VETO"
    assert "6-week PT failure" in packet["missing_evidence"]
    assert packet["proof_count"] == 6

    # Beat 4: human approval + commit the v4 patch, then the same complete
    # packet is BLOCKED.
    resp = client.post(
        "/scrubber/commit",
        json={"claim_id": DENGUE_CLAIM["claim_id"], "approved": True,
              "rule": V4_PATCH, "probe_packet": COMPLETE_DENGUE_PACKET},
    )
    assert resp.status_code == 200
    assert resp.json()["probe_verdict"] == "BLOCKED"
    recheck = client.post("/scrubber/check", json=COMPLETE_DENGUE_PACKET).json()
    assert recheck["verdict"] == "BLOCKED"
    assert "platelet_report" in recheck["missing"]
    assert recheck["rule_id"] == "star_health_dengue_opd_v4"
