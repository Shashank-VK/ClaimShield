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


def test_agent_save_outcome_runs_with_user_approval(desk):
    adapter, room, rules = desk
    result = run_agent(
        "Yes, save it — the dengue appeal was won",
        adapter=adapter, room=room, rules_data=rules,
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
