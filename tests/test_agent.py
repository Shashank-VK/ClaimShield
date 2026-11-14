"""Agent loop tests (cs-011): the LLM drives, the tools are real.

The model is faked with a script of canned replies; the tools run
against the real in-memory Hindsight adapter and rules, so a tool call
in the loop produces the same verdicts the HTTP endpoints produce.
"""

import json

import pytest

from backend.agent import run_agent
from backend.denial_defense import build_room
from backend.hindsight_adapter import HindsightAdapter
from backend.scrubber_validator import DEFAULT_RULES_PATH, load_rules


@pytest.fixture()
def desk():
    adapter = HindsightAdapter()
    return adapter, build_room(adapter), load_rules(DEFAULT_RULES_PATH)


def scripted(replies):
    queue = list(replies)

    def _call(messages):
        assert queue, "model called more times than scripted"
        return queue.pop(0)

    return _call


def test_agent_answers_directly_without_tools(desk):
    adapter, room, rules = desk
    result = run_agent(
        "What does this desk do?",
        adapter=adapter, room=room, rules_data=rules,
        call_model=scripted(['{"say": "It checks claims against past wins."}']),
    )
    assert result["reply"] == "It checks claims against past wins."
    assert result["actions"] == []
    assert "strategy_result" not in result


def test_agent_calls_memory_check_and_answers_from_result(desk):
    adapter, room, rules = desk
    result = run_agent(
        "Check the dengue claim against memory",
        adapter=adapter, room=room, rules_data=rules,
        call_model=scripted([
            '{"do": "check_appeal", "args": {"case": "dengue"}, "note": "Checking memory"}',
            '{"say": "Checked. The verdict is in the pane."}',
        ]),
    )
    assert [a["tool"] for a in result["actions"]] == ["check_appeal"]
    assert "verdict=" in result["actions"][0]["summary"]
    strategy = result["strategy_result"]
    assert strategy["verdict"] in ("APPROVE", "VETO")
    assert isinstance(strategy["proof_count"], int)
    assert result["reply"] == "Checked. The verdict is in the pane."


def test_agent_save_outcome_blocked_without_user_approval(desk):
    adapter, room, rules = desk
    seen = {}

    def _call(messages):
        if any("TOOL RESULT save_outcome" in m["content"] for m in messages):
            seen["fed_back"] = True
            return '{"say": "I need your approval before saving."}'
        return '{"do": "save_outcome", "args": {"case": "dengue", "outcome": "WON"}, "note": "Saving"}'

    result = run_agent(
        "The dengue appeal outcome came in",
        adapter=adapter, room=room, rules_data=rules, call_model=_call,
    )
    assert seen.get("fed_back")
    assert "NOT SAVED" in result["actions"][0]["summary"]


def test_agent_save_outcome_runs_with_user_approval(desk, tmp_path):
    adapter, room, rules = desk
    result = run_agent(
        "Yes, save it — the dengue appeal was won",
        adapter=adapter, room=room, rules_data=rules,
        knowledge_path=tmp_path / "k.json",
        call_model=scripted([
            '{"do": "save_outcome", "args": {"case": "dengue", "outcome": "WON"}, "note": "Saving the outcome"}',
            '{"say": "Saved. Future checks will use it."}',
        ]),
    )
    assert "saved outcome=WON" in result["actions"][0]["summary"]
    assert result["reply"] == "Saved. Future checks will use it."


def test_agent_treats_unparseable_output_as_the_answer(desk):
    adapter, room, rules = desk
    result = run_agent(
        "Hello",
        adapter=adapter, room=room, rules_data=rules,
        call_model=scripted(["Just a plain answer, no JSON."]),
    )
    assert result["reply"] == "Just a plain answer, no JSON."
    assert result["actions"] == []


def test_agent_returns_none_when_model_unavailable(desk):
    adapter, room, rules = desk
    result = run_agent(
        "Check the claim",
        adapter=adapter, room=room, rules_data=rules,
        call_model=lambda messages: None,
    )
    assert result is None


def test_agent_reads_knowledge_document_for_insurance_questions(desk):
    from backend.knowledge import load_knowledge

    adapter, room, rules = desk
    result = run_agent(
        "How do I get reimbursement and what documents are needed?",
        adapter=adapter, room=room, rules_data=rules,
        knowledge_data=load_knowledge(),
        call_model=scripted([
            '{"do": "lookup_knowledge", "args": {"topic": "reimbursement"}, "note": "Reading the knowledge document"}',
            '{"say": "Here is the process and the document list."}',
        ]),
    )
    assert [a["tool"] for a in result["actions"]] == ["lookup_knowledge"]
    summary = result["actions"][0]["summary"]
    assert "discharge summary" in summary.lower()
    assert "claim form" in summary.lower()


def test_agent_knowledge_lookup_by_insurer_and_treatment(desk):
    from backend.knowledge import load_knowledge, lookup

    data = load_knowledge()
    star = lookup(data, insurer="Star Health")
    assert "OPD-convertible" in star
    knee = lookup(data, treatment="knee")
    assert "physiotherapy" in knee.lower()
    missing = lookup(data, topic="nonsense")
    assert "No matching entry" in missing


def test_hidden_traps_lookup_room_rent_and_knee():
    from backend.knowledge import load_knowledge, lookup

    data = load_knowledge()
    room = lookup(data, insurer="Star Health", treatment="room allotment")
    assert "5,000" in room and "proportionate" in room.lower()
    assert "1,25,000" in room  # worked example: family pays half the bill
    knee = lookup(data, treatment="knee replacement")
    assert "70,000" in knee
    traps = lookup(data, topic="hidden_traps")
    assert "robotic" in traps.lower() and "25,000" in traps


def test_agent_save_outcome_also_updates_knowledge_document(desk, tmp_path):
    import json as _json

    from backend.knowledge import load_knowledge

    adapter, room, rules = desk
    kpath = tmp_path / "knowledge.json"
    kpath.write_text(_json.dumps(load_knowledge()), encoding="utf-8")
    result = run_agent(
        "Yes, save it — the dengue appeal was won",
        adapter=adapter, room=room, rules_data=rules,
        knowledge_data=load_knowledge(), knowledge_path=kpath,
        call_model=scripted([
            '{"do": "save_outcome", "args": {"case": "dengue", "outcome": "WON"}, "note": "Saving"}',
            '{"say": "Saved."}',
        ]),
    )
    assert "saved outcome=WON" in result["actions"][0]["summary"]
    updated = _json.loads(kpath.read_text(encoding="utf-8"))
    assert updated["learned_outcomes"][-1]["case"] == "dengue"
    assert updated["learned_outcomes"][-1]["outcome"] == "WON"
