"""Knowledge-chat tests (cs-014): /assistant/chat reads the knowledge
document (backend/knowledge/insurance_knowledge.json) and answers
insurance questions deterministically — no LLM key involved.

Desk commands are NOT knowledge questions: they must fall through to
the agent, which (with no key in tests) returns a null reply.
"""

import re

import pytest
from fastapi.testclient import TestClient

from backend.hindsight_adapter import HindsightAdapter
from backend.main import create_app

SECRET = "test-secret"


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_WEBHOOK_SECRET", SECRET)
    # No LLM in these tests: the knowledge path must answer on its own,
    # and non-knowledge messages must fall through to a null reply.
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    return TestClient(create_app(HindsightAdapter()))


def _chat(client, message):
    resp = client.post("/assistant/chat", json={"message": message})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_red_flags_lists_all_hidden_traps(client):
    body = _chat(client, "red flags in all the insurance or hidden policies list them")
    assert body["reply"], "knowledge question must not come back null"
    assert body["source"] == "knowledge"
    assert "Room-rent cap" in body["reply"]
    assert "Knee" in body["reply"]
    numbered = [ln for ln in body["reply"].splitlines() if re.match(r"^\d+\.\s", ln)]
    assert len(numbered) >= 8, f"expected the trap list, got: {body['reply'][:300]}"


def test_star_assure_card_answers_from_insurer_entry(client):
    body = _chat(client, "5 LAKH star assure card")
    assert body["reply"], "insurer question must not come back null"
    assert "Star" in body["reply"]
    # The room-rent trap on Star Assure: 1% of Rs.5 lakh SI = Rs.5,000/day.
    assert "Rs.5,000/day" in body["reply"]


def test_reimbursement_process_and_documents(client):
    body = _chat(client, "how does reimbursement work, what documents are needed")
    assert body["reply"], "process question must not come back null"
    assert "Discharge summary" in body["reply"]


def test_desk_command_is_not_a_knowledge_question(client):
    body = _chat(client, "check the dengue claim against past wins")
    # Command guard: knowledge layer stays out; with no LLM key the
    # agent cannot answer either, so the reply stays null (scripted).
    assert body["reply"] is None
    assert body["source"] == "scripted"


def test_unrelated_message_returns_null(client):
    body = _chat(client, "hello there")
    assert body["reply"] is None
