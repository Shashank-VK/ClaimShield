"""Tests for the optional OpenRouter Assistant (2026-11-14).

The LLM is mocked throughout — no real key, no network. What is pinned:
no key -> no call and None; a good response -> its text; any failure ->
None (the chat falls back to scripted answers); the request is grounded
(system prompt carries the measured eval numbers + live rules context);
the endpoint returns reply null + source "scripted" without a key.
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import assistant_llm
from backend.hindsight_adapter import HindsightAdapter
from backend.main import create_app

CONTEXT = {
    "rules_version": 4,
    "rules": [
        {
            "insurer": "star_health",
            "diagnosis_group": "dengue",
            "version": 4,
            "proof_count": 6,
            "is_active": True,
            "required_docs": ["discharge_summary", "platelet_report"],
        }
    ],
}


class _Resp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def _ok_payload(text="Memory is what makes the desk improve."):
    return {"choices": [{"message": {"content": text}}]}


def test_no_key_returns_none_and_never_calls(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    def boom(*a, **k):
        raise AssertionError("httpx.post must not be called without a key")

    monkeypatch.setattr(httpx, "post", boom)
    assert assistant_llm.answer("why did the claim stop?", context=CONTEXT) is None


def test_good_response_returns_text_and_sends_grounded_request(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    # Hermetic against a developer .env (config loads it at import):
    # this test asserts the built-in defaults, so pin them explicitly.
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    seen = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(url=url, headers=headers, json=json)
        return _Resp(200, _ok_payload())

    monkeypatch.setattr(httpx, "post", fake_post)
    out = assistant_llm.answer(
        "why did the claim stop?",
        history=[{"from": "user", "text": "hi"}, {"from": "desk", "text": "hello"}],
        context=CONTEXT,
    )
    assert out == "Memory is what makes the desk improve."
    assert seen["url"].endswith("/chat/completions")
    assert seen["headers"]["Authorization"] == "Bearer sk-or-test"
    assert seen["json"]["model"] == "openai/gpt-4o-mini"
    system = seen["json"]["messages"][0]["content"]
    assert "19 of 20" in system  # measured eval numbers are in the grounding
    assert "version 4" in system and "platelet_report" in system  # live rules context
    roles = [m["role"] for m in seen["json"]["messages"]]
    assert roles == ["system", "user", "assistant", "user"]


def test_http_error_and_network_failure_return_none(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: _Resp(500, {}))
    assert assistant_llm.answer("q", context=CONTEXT) is None

    def netfail(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", netfail)
    assert assistant_llm.answer("q", context=CONTEXT) is None


def test_endpoint_without_key_is_scripted(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = TestClient(create_app(HindsightAdapter()))
    resp = client.post("/assistant/chat", json={"message": "what is this desk?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] is None
    assert body["source"] == "scripted"
    assert client.get("/health").json()["llm"] == "off"


def test_endpoint_with_key_returns_llm_reply(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    monkeypatch.setattr(
        "backend.agent.run_agent",
        lambda message, history=None, **kw: {"reply": "A grounded answer.", "actions": []},
    )
    client = TestClient(create_app(HindsightAdapter()))
    resp = client.post(
        "/assistant/chat",
        json={"message": "explain step 3", "history": [{"from": "user", "text": "hi"}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "A grounded answer."
    assert body["source"] == "agent"
    assert body["actions"] == []
    assert client.get("/health").json()["llm"] == "openrouter"
