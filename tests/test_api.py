"""Tests for the FastAPI backend (cs-004): /health, HMAC webhooks, dedupe, SSE."""

import hashlib
import hmac
import json
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.hindsight_adapter import HindsightAdapter
from backend.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SECRET = "test-secret"
UVICORN_PORT = 8123


def _sign(body: bytes) -> str:
    return "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("HINDSIGHT_WEBHOOK_SECRET", SECRET)
    return TestClient(create_app(HindsightAdapter()))


def test_health_reports_real_backend_and_band_mode(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["backend"] == "memory"
    assert body["band_mode"] == "local"
    assert "rules_version" in body


def test_intake_retains_and_returns_pii(client):
    resp = client.post(
        "/webhooks/claim-intake",
        json={
            "document_id": "SYNTHETIC-CLM-API-01",
            "content": "SSN 123-45-6789 in the packet. Star Health dengue claim.",
            "tags": ["insurer:star_health", "synthetic"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "retained"
    assert body["memory_unit_count"] == 1
    assert "[REDACTED:ssn]" in body["pii_scrubbed"]
    assert "123-45-6789" not in body["content"]


def test_hindsight_bad_hmac_401(client):
    body = json.dumps({"event_id": "evt-1", "event_type": "retain.completed"}).encode()
    resp = client.post(
        "/webhooks/hindsight", content=body, headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 401
    resp = client.post(
        "/webhooks/hindsight",
        content=body,
        headers={"Content-Type": "application/json", "X-Hindsight-Signature": "sha256=deadbeef"},
    )
    assert resp.status_code == 401


def test_hindsight_dedupe_processes_once(client):
    body = json.dumps(
        {"event_id": "evt-dedupe-1", "event_type": "consolidation.completed", "payload": {}}
    ).encode()
    headers = {"Content-Type": "application/json", "X-Hindsight-Signature": _sign(body)}
    first = client.post("/webhooks/hindsight", content=body, headers=headers)
    assert first.status_code == 200
    assert first.json()["status"] == "processed"
    second = client.post("/webhooks/hindsight", content=body, headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert second.json()["processed"] is False


def test_bad_payloads_422_not_500(client):
    # Missing event_id, valid HMAC.
    body = json.dumps({"event_type": "retain.completed"}).encode()
    resp = client.post(
        "/webhooks/hindsight",
        content=body,
        headers={"Content-Type": "application/json", "X-Hindsight-Signature": _sign(body)},
    )
    assert resp.status_code == 422
    # Missing content on intake.
    resp = client.post("/webhooks/claim-intake", json={"tags": []})
    assert resp.status_code == 422
    # Malformed JSON on the webhook, valid HMAC.
    body = b"{not json"
    resp = client.post(
        "/webhooks/hindsight",
        content=body,
        headers={"Content-Type": "application/json", "X-Hindsight-Signature": _sign(body)},
    )
    assert resp.status_code == 422


def test_sse_replays_last_events(client):
    body = json.dumps(
        {"event_id": "evt-replay-1", "event_type": "consolidation.completed", "payload": {"proof_count": 6}}
    ).encode()
    resp = client.post(
        "/webhooks/hindsight",
        content=body,
        headers={"Content-Type": "application/json", "X-Hindsight-Signature": _sign(body)},
    )
    assert resp.status_code == 200

    seen = []
    with client.stream("GET", "/sse/stream") as stream:
        assert stream.status_code == 200
        for line in stream.iter_lines():
            if line.startswith("data:"):
                seen.append(json.loads(line[len("data:"):]))
            if any(e.get("event_id") == "evt-replay-1" for e in seen):
                break
    assert any(e.get("event_id") == "evt-replay-1" for e in seen)


def test_sse_live_delivery(client):
    received: list = []

    def _read_stream():
        with client.stream("GET", "/sse/stream") as stream:
            for line in stream.iter_lines():
                if line.startswith("data:"):
                    received.append(json.loads(line[len("data:"):]))
                if any(e.get("event_id") == "evt-live-1" for e in received):
                    return

    thread = threading.Thread(target=_read_stream, daemon=True)
    thread.start()
    time.sleep(0.5)  # let the subscriber register
    body = json.dumps(
        {"event_id": "evt-live-1", "event_type": "retain.completed", "payload": {}}
    ).encode()
    resp = client.post(
        "/webhooks/hindsight",
        content=body,
        headers={"Content-Type": "application/json", "X-Hindsight-Signature": _sign(body)},
    )
    assert resp.status_code == 200
    thread.join(timeout=10)
    assert any(e.get("event_id") == "evt-live-1" for e in received)


def test_uvicorn_starts_and_health_answers():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app",
         "--host", "127.0.0.1", "--port", str(UVICORN_PORT)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.time() + 15
        body = None
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                    f"http://127.0.0.1:{UVICORN_PORT}/health", timeout=2
                ) as resp:
                    body = json.loads(resp.read().decode())
                    break
            except Exception:
                time.sleep(0.5)
        assert body is not None, "uvicorn did not answer /health in time"
        assert body["status"] == "ok"
        assert body["backend"] == "memory"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
