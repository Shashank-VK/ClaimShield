"""Tests for the pre-dispatch checker (cs-005, PRD §6.6)."""

import copy
import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.hindsight_adapter import HindsightAdapter
from backend.main import create_app
from backend.scrubber_validator import (
    check_packet,
    load_rules,
    rollback,
    save_rules,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = PROJECT_ROOT / "scrubber_rules.json"

COMPLETE_DENGUE = {
    "insurer": "star_health",
    "diagnosis_group": "dengue",
    "denial_reason": "opd_convertible",
    "documents": ["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
}


def test_complete_packet_passes():
    result = check_packet(COMPLETE_DENGUE)
    assert result["verdict"] == "PASS"
    assert result["missing"] == []
    assert result["rule_id"] == "star_health_dengue_opd_v3"
    assert result["source_obs"] == "obs_304"
    assert result["proof_count"] == 5


def test_missing_discharge_summary_blocked_with_evidence():
    packet = dict(COMPLETE_DENGUE, documents=["ns1_antigen_report", "final_bill_icd10"])
    result = check_packet(packet)
    assert result["verdict"] == "BLOCKED"
    assert "discharge_summary" in result["missing"]
    assert result["source_obs"] == "obs_304"
    assert result["proof_count"] == 5
    # The cited rule must exist in the file (never invented).
    data = load_rules()
    assert any(r["rule_id"] == result["rule_id"] for r in data["rules"])


def test_missing_only_ns1_warns():
    packet = dict(COMPLETE_DENGUE, documents=["discharge_summary", "final_bill_icd10"])
    result = check_packet(packet)
    assert result["verdict"] == "WARN"
    assert result["missing"] == ["ns1_antigen_report"]
    assert result["rule_id"] == "star_health_dengue_opd_v3"


def test_no_matching_rule_passes_without_inventing_one():
    packet = {
        "insurer": "icici_lombard",
        "diagnosis_group": "dengue",
        "denial_reason": "opd_convertible",
        "documents": [],
    }
    result = check_packet(packet)
    assert result["verdict"] == "PASS"
    assert result["rule_id"] is None


def test_rollback_restores_prior_behaviour():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "scrubber_rules.json"
        data = copy.deepcopy(load_rules())
        save_rules(data, path)

        # v3 active: missing only NS1 warns.
        assert check_packet(
            dict(COMPLETE_DENGUE, documents=["discharge_summary", "final_bill_icd10"]),
            load_rules(path),
        )["verdict"] == "WARN"

        # Roll back to v2: v2 has the same requires/warn shape, so WARN holds;
        # roll back to v1 (no NS1 in requires): the same packet now PASSES.
        rollback("star_health_dengue_opd", 2, path)
        v2 = check_packet(
            dict(COMPLETE_DENGUE, documents=["discharge_summary", "final_bill_icd10"]),
            load_rules(path),
        )
        assert v2["rule_id"] == "star_health_dengue_opd_v2"
        assert v2["verdict"] == "WARN"

        rollback("star_health_dengue_opd", 1, path)
        v1 = check_packet(
            dict(COMPLETE_DENGUE, documents=["discharge_summary", "final_bill_icd10"]),
            load_rules(path),
        )
        assert v1["rule_id"] == "star_health_dengue_opd_v1"
        assert v1["verdict"] == "PASS"

        history = load_rules(path)["rule_history"]
        assert any(h["action"] == "rollback" and h["version"] == 1 for h in history)


def test_rule_history_records_every_version():
    data = load_rules()
    versions = sorted(
        r["version"] for r in data["rules"] if r["rule_id"].startswith("star_health_dengue_opd")
    )
    assert versions == [1, 2, 3]
    active = [r for r in data["rules"] if r["rule_id"].startswith("star_health_dengue_opd") and r["is_active"]]
    assert len(active) == 1 and active[0]["version"] == 3
    assert len(data["rule_history"]) >= 3


def test_health_reports_loaded_rules_version():
    client = TestClient(create_app(HindsightAdapter()))
    body = client.get("/health").json()
    assert body["rules_loaded"] is True
    assert body["rules_version"] == 3
