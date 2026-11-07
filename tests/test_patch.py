"""Tests for the rule patch W6 (cs-007, ScrubberCoder)."""

import json
import shutil
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.denial_defense import build_room
from backend.hindsight_adapter import HindsightAdapter
from backend.main import create_app
from backend.scrubber_coder import PatchError, commit_patch
from backend.scrubber_validator import check_packet, load_rules
from seed_history import seed

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REAL_RULES = PROJECT_ROOT / "scrubber_rules.json"

COMPLETE_DENGUE = {
    "insurer": "star_health",
    "diagnosis_group": "dengue",
    "denial_reason": "opd_convertible",
    "documents": ["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
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


def _tmp_rules():
    tmp = tempfile.mkdtemp()
    path = Path(tmp) / "scrubber_rules.json"
    shutil.copy(REAL_RULES, path)
    return path


def _seeded_adapter():
    adapter = HindsightAdapter()
    seed(adapter)
    return adapter


def test_commit_patch_blocks_previously_passing_packet():
    path = _tmp_rules()
    assert check_packet(COMPLETE_DENGUE, load_rules(path))["verdict"] == "PASS"

    client = TestClient(create_app(_seeded_adapter(), rules_path=path))
    resp = client.post(
        "/scrubber/commit",
        json={
            "claim_id": "SYNTHETIC-CLM-DEMO-DENGUE",
            "approved": True,
            "rule": V4_PATCH,
            "probe_packet": COMPLETE_DENGUE,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "committed"
    assert body["rule"]["rule_id"] == "star_health_dengue_opd_v4"
    assert body["rule"]["version"] == 4
    assert body["rule"]["supersedes"] == 3
    assert body["rule"]["source_obs"] == "obs_304"
    assert body["probe_verdict"] == "BLOCKED"

    # The same complete packet is now BLOCKED by the new rule version.
    after = check_packet(COMPLETE_DENGUE, load_rules(path))
    assert after["verdict"] == "BLOCKED"
    assert "platelet_report" in after["missing"]
    assert after["rule_id"] == "star_health_dengue_opd_v4"

    # Diff viewable: history records the patch; v3 is deactivated.
    data = load_rules(path)
    assert any(
        h["action"] == "patched" and h["rule_id"] == "star_health_dengue_opd_v4"
        for h in data["rule_history"]
    )
    v3 = next(r for r in data["rules"] if r["rule_id"] == "star_health_dengue_opd_v3")
    assert v3["is_active"] is False


def test_failing_patch_reverts_and_alerts():
    path = _tmp_rules()
    client = TestClient(create_app(_seeded_adapter(), rules_path=path))

    # Bad rule: missing 'requires'.
    bad = {k: v for k, v in V4_PATCH.items() if k != "requires"}
    resp = client.post(
        "/scrubber/commit",
        json={"claim_id": "X", "approved": True, "rule": bad, "probe_packet": COMPLETE_DENGUE},
    )
    assert resp.status_code == 422
    assert "requires" in resp.json()["detail"]

    # Probe-failing patch: valid shape but does not BLOCK the probe packet.
    weak = dict(
        V4_PATCH,
        requires=["discharge_summary", "ns1_antigen_report", "final_bill_icd10"],
        blocks_when_missing=[],
        warn_when_missing=["ns1_antigen_report"],
    )
    resp = client.post(
        "/scrubber/commit",
        json={"claim_id": "X", "approved": True, "rule": weak, "probe_packet": COMPLETE_DENGUE},
    )
    assert resp.status_code == 422
    assert "did not BLOCK" in resp.json()["detail"]

    # File untouched: v3 still active, the packet still PASSES.
    data = load_rules(path)
    v3 = next(r for r in data["rules"] if r["rule_id"] == "star_health_dengue_opd_v3")
    assert v3["is_active"] is True
    assert check_packet(COMPLETE_DENGUE, data)["verdict"] == "PASS"
    assert not any(
        h.get("action") == "patched" and h.get("version") == 4 for h in data["rule_history"]
    )


def test_commit_patch_unit_level():
    path = _tmp_rules()
    result = commit_patch(V4_PATCH, path=path, probe_packet=COMPLETE_DENGUE)
    assert result["rule"]["rule_id"] == "star_health_dengue_opd_v4"
    assert result["previous_version"] == 3

    with_path = _tmp_rules()
    try:
        commit_patch({k: v for k, v in V4_PATCH.items() if k != "requires"}, path=with_path)
    except PatchError as exc:
        assert "requires" in str(exc)
    else:
        raise AssertionError("bad patch must raise PatchError")
    assert load_rules(with_path)["rules"][2]["is_active"] is True


def test_room_scrubber_coder_agent():
    path = _tmp_rules()
    room = build_room(_seeded_adapter(), rules_path=path)
    result = room.send("@ScrubberCoder", {"rule": V4_PATCH, "probe_packet": COMPLETE_DENGUE})
    assert result["status"] == "committed"
    assert result["rule"]["rule_id"] == "star_health_dengue_opd_v4"

    bad_path = _tmp_rules()
    room2 = build_room(_seeded_adapter(), rules_path=bad_path)
    failed = room2.send("@ScrubberCoder", {"rule": {"family": "x"}, "probe_packet": COMPLETE_DENGUE})
    assert failed["status"] == "failed"
    assert failed["alert"], "a failed patch must carry an alert"
    assert check_packet(COMPLETE_DENGUE, load_rules(bad_path))["verdict"] == "PASS"
