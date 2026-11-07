"""Tests for the Band room + denial defense W3 (cs-006)."""

import pytest
from fastapi.testclient import TestClient

from backend.band_room import RoomDisabledError
from backend.denial_defense import build_room, run_denial_defense
from backend.hindsight_adapter import HindsightAdapter
from backend.main import create_app
from seed_history import seed

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


@pytest.fixture()
def seeded():
    adapter = HindsightAdapter()
    seed(adapter)
    return adapter


@pytest.fixture()
def client(seeded):
    return TestClient(create_app(seeded))


def test_headline_dengue_produces_approved_packet(client):
    resp = client.post("/appeals/strategy", json=DENGUE_CLAIM)
    assert resp.status_code == 200, resp.text
    packet = resp.json()
    assert packet["verdict"] == "APPROVE"
    assert packet["proof_count"] == 5
    assert packet["citations"], "packet must cite retrieved wins"
    assert packet["status"] == "draft"
    assert "Draft for human review" in packet["disclaimer"]
    assert "SYNTHETIC" in packet["disclaimer"]


def test_stale_four_week_pt_argument_vetoed(client):
    resp = client.post("/appeals/strategy", json=PT_CLAIM)
    assert resp.status_code == 200, resp.text
    packet = resp.json()
    assert packet["verdict"] == "VETO"
    assert "6-week PT failure" in packet["missing_evidence"]
    assert any("X-ray" in m for m in packet["missing_evidence"])
    assert "6-week" in packet["required_excerpt"]
    assert packet["proof_count"] == 6


def test_citations_are_validated(seeded, client):
    resp = client.post("/appeals/strategy", json=DENGUE_CLAIM)
    packet = resp.json()
    query = (
        f"{DENGUE_CLAIM['insurer']} {DENGUE_CLAIM['diagnosis_group']} "
        f"{DENGUE_CLAIM['denial_reason']} {DENGUE_CLAIM['argument']}"
    )
    recalled_ids = {
        h["id"]
        for h in seeded.recall(query, tags=["insurer:star_health"], top_k=5)
    }
    assert packet["citations"], "packet must have citations"
    for citation in packet["citations"]:
        assert citation in recalled_ids, f"citation {citation} was not retrieved"
    for ev in packet["evidence"]:
        assert ev["citation"] in recalled_ids


def test_delete_test_room_disabled(seeded):
    room = build_room(seeded, enabled=False)
    with pytest.raises(RoomDisabledError):
        run_denial_defense(seeded, room, DENGUE_CLAIM)

    disabled_client = TestClient(create_app(seeded, room_enabled=False))
    resp = disabled_client.post("/appeals/strategy", json=DENGUE_CLAIM)
    assert resp.status_code == 503

    # With the room present, the same chain completes.
    enabled_client = TestClient(create_app(seeded, room_enabled=True))
    resp = enabled_client.post("/appeals/strategy", json=DENGUE_CLAIM)
    assert resp.status_code == 200
    assert resp.json()["verdict"] == "APPROVE"


def test_human_gate_commit_refused_without_approval(client):
    resp = client.post(
        "/scrubber/commit", json={"claim_id": "SYNTHETIC-CLM-DEMO-DENGUE", "approved": False}
    )
    assert resp.status_code == 403
    resp = client.post(
        "/scrubber/commit", json={"claim_id": "SYNTHETIC-CLM-DEMO-DENGUE", "approved": True}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "committed"


def test_veto_endpoint_reviews_a_draft(client):
    strategy = client.post("/appeals/strategy", json=PT_CLAIM).json()
    assert strategy["verdict"] == "VETO"
    resp = client.post(
        "/appeals/veto",
        json={
            "claim": PT_CLAIM,
            "draft": {
                "argument": strategy["argument"],
                "evidence": strategy["evidence"],
                "citations": strategy["citations"],
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verdict"] == "VETO"
    assert "6-week PT failure" in body["missing_evidence"]
    assert body["disclaimer"].startswith("Draft for human review")
