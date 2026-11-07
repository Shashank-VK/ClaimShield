"""Tests for the 4-epoch seeder (cs-002)."""

from backend.hindsight_adapter import HindsightAdapter
from seed_history import EPOCHS, HEADLINE_TAGS, seed

CUTOFF = "2026-11-07"


def _fresh_seeded():
    adapter = HindsightAdapter()
    summary = seed(adapter)
    return adapter, summary


def test_epochs_load_in_order_with_backdated_timestamps():
    adapter, summary = _fresh_seeded()
    assert summary["epochs"] == [
        "E1_generic_denials",
        "E2_first_wins",
        "E3_bulletin_contradiction",
        "E4_late_verdicts",
    ]
    assert summary["total"] == 13
    assert summary["epoch_counts"] == {
        "E1_generic_denials": 3,
        "E2_first_wins": 6,
        "E3_bulletin_contradiction": 2,
        "E4_late_verdicts": 2,
    }
    assert summary["backend"] == "memory"

    timestamps = [r["timestamp"] for r in summary["records"]]
    assert timestamps == sorted(timestamps), "epochs must load in chronological order"
    assert all(ts < CUTOFF for ts in timestamps), "all seed timestamps must be backdated"


def test_bulletin_contradiction_present():
    adapter, _ = _fresh_seeded()
    old_obs = adapter.get_observation("obs_pt_01")
    new_obs = adapter.get_observation("obs_pt_02")
    assert old_obs is not None and new_obs is not None
    assert old_obs["superseded_by"] == "obs_pt_02"
    assert new_obs["proof_count"] == 6

    reflection = adapter.reflect(
        question="What is the required PT conservative duration for Star Health knee surgery?",
        context_ids=["SYNTHETIC-CLM-E2-PT-4WK", "SYNTHETIC-CLM-E3-BULLETIN-PT6WK"],
    )
    ranked = reflection["ranked_causes"]
    assert len(ranked) >= 1
    assert not ranked[0]["superseded"], "the active 6-week PT observation must rank first"
    assert ranked[0]["observation_id"] == "obs_pt_02"


def test_new_win_increments_headline_proof_count():
    adapter, _ = _fresh_seeded()

    def headline_proof_count():
        hits = adapter.recall(
            query="Star Health dengue OPD convertible overturned",
            tags=["insurer:star_health"],
            top_k=5,
        )
        assert hits, "headline dengue win must be recallable"
        return hits[0]["observation"]["proof_count"]

    assert headline_proof_count() == 5

    adapter.retain(
        document={
            "id": "SYNTHETIC-CLM-NEW-WIN-01",
            "content": "SYNTHETIC Star Health dengue claim Rs.1,02,000 reimbursement. Denial: OPD convertible. "
            "Appeal OVERTURNED_FULL with NS1 antigen report and indoor case papers.",
        },
        tags=list(HEADLINE_TAGS),
        timestamp="2026-11-05T10:00:00Z",
    )
    assert headline_proof_count() == 6


def test_all_seeded_records_synthetic():
    _, summary = _fresh_seeded()
    for record in summary["records"]:
        assert record["id"].startswith("SYNTHETIC-"), record["id"]
        assert "synthetic" in record["tags"], record["id"]
        assert "SYNTHETIC" in record["content"], record["id"]


def test_headline_case_present():
    adapter, summary = _fresh_seeded()
    headline = next(
        r for r in summary["records"] if r["id"] == "SYNTHETIC-CLM-E2-DENGUE-HEADLINE"
    )
    assert "1,45,000" in headline["content"]
    assert "OVERTURNED_FULL" in headline["content"]
    assert "NS1" in headline["content"]

    hits = adapter.recall(
        query="Star Health dengue OPD convertible overturned inpatient necessity",
        tags=["insurer:star_health"],
        top_k=5,
    )
    assert hits[0]["id"] == "SYNTHETIC-CLM-E2-DENGUE-HEADLINE" or \
        "dengue" in hits[0]["content"].lower()
