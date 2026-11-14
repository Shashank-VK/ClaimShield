"""FastAPI backend for ClaimShield Desk.

cs-003: intake endpoint (PII scrub before retain).
cs-004: /health, HMAC-verified /webhooks/hindsight with dedupe on event_id,
        and /sse/stream (multiplexed events, last-50 replay on reconnect).
cs-006 adds /appeals/strategy + /appeals/veto; cs-007 adds /scrubber/commit;
cs-009 adds /eval/run.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import queue as queue_module
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError

from backend.scrubber_validator import check_packet

from backend import agent
from backend.band_room import RoomDisabledError
from backend.config import get_openrouter_api_key, get_webhook_secret
from backend.denial_defense import build_room, make_critic, run_denial_defense
from backend.hindsight_adapter import HindsightAdapter
from backend.pii_scrubber import scrub_text
from backend.scrubber_coder import PatchError, commit_patch
from backend.scrubber_validator import DEFAULT_RULES_PATH, load_rules, rules_version

DISCLAIMER = "Draft for human review, not legal/medical advice. All cases SYNTHETIC."
SSE_REPLAY_LIMIT = 50


class ClaimIntakeRequest(BaseModel):
    document_id: Optional[str] = None
    content: str
    tags: List[str] = Field(default_factory=list)
    context: Optional[str] = None
    timestamp: Optional[str] = None


class ClaimIntakeResponse(BaseModel):
    status: str
    document_id: str
    memory_unit_count: int
    pii_scrubbed: List[str]
    pii_layers: Dict[str, str]
    content: str
    backend: str


class HindsightWebhookRequest(BaseModel):
    event_id: str
    event_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class ClaimRequest(BaseModel):
    claim_id: str
    insurer: str
    diagnosis_group: str
    denial_reason: str
    claim_type: str = "reimbursement"
    amount: Optional[str] = None
    argument: str = ""
    documents: List[str] = Field(default_factory=list)


class DraftRequest(BaseModel):
    argument: str = ""
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)


class VetoRequest(BaseModel):
    claim: ClaimRequest
    draft: DraftRequest


class CommitRequest(BaseModel):
    claim_id: str
    approved: bool = False
    note: str = ""
    rule: Optional[Dict[str, Any]] = None
    probe_packet: Optional[Dict[str, Any]] = None


class CheckRequest(BaseModel):
    insurer: str
    diagnosis_group: str
    denial_reason: str
    documents: List[str] = Field(default_factory=list)


class AssistantHistoryItem(BaseModel):
    from_: str = Field(default="", alias="from")
    text: str = ""

    model_config = {"populate_by_name": True}


class AssistantChatRequest(BaseModel):
    message: str
    history: List[AssistantHistoryItem] = Field(default_factory=list)


def _verify_hmac(secret: str, body: bytes, signature: Optional[str]) -> bool:
    """Check the X-Hindsight-Signature header (``sha256=<hex>`` or raw hex)."""
    if not signature:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    given = signature[len("sha256="):] if signature.startswith("sha256=") else signature
    return hmac.compare_digest(expected, given)


def create_app(
    adapter: Optional[HindsightAdapter] = None,
    room_enabled: bool = True,
    rules_path=None,
) -> FastAPI:
    app = FastAPI(title="ClaimShield Desk")
    # The cockpit runs on localhost:3000 and calls this API from the browser.
    # FRONTEND_ORIGIN (env) adds the deployed cockpit origin for live hosting;
    # a bare host is treated as https://<host> (Render's fromService gives a host).
    _cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    _frontend_origin = os.environ.get("FRONTEND_ORIGIN", "").strip()
    if _frontend_origin and not _frontend_origin.startswith("http"):
        _frontend_origin = "https://" + _frontend_origin
    if _frontend_origin:
        _cors_origins.append(_frontend_origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.adapter = adapter or HindsightAdapter()
    app.state.rules_path = rules_path or DEFAULT_RULES_PATH
    app.state.room = build_room(app.state.adapter, enabled=room_enabled, rules_path=app.state.rules_path)
    app.state.committed: List[Dict[str, Any]] = []
    app.state.events: Deque[Dict[str, Any]] = deque(maxlen=SSE_REPLAY_LIMIT)
    # Threading queues: the stream and the webhook POST can run on different
    # event loops (TestClient portals, uvicorn workers), so the bus must not
    # be loop-affine. asyncio.Queue would silently drop cross-loop wakes.
    app.state.subscribers: Set[queue_module.Queue] = set()
    app.state.seen_event_ids: Set[str] = set()

    def _broadcast(event: Dict[str, Any]) -> None:
        app.state.events.append(event)
        for sub in list(app.state.subscribers):
            sub.put(event)

    @app.get("/health")
    def health():
        try:
            version = rules_version(load_rules(app.state.rules_path))
            loaded = version > 0
        except Exception:
            version, loaded = 0, False
        return {
            "status": "ok",
            "backend": app.state.adapter.backend_name,
            "band_mode": app.state.room.mode,
            "rules_version": version,
            "rules_loaded": loaded,
            "llm": "openrouter" if get_openrouter_api_key() else "off",
        }

    @app.post("/assistant/chat")
    def assistant_chat(req: AssistantChatRequest):
        # The agent (cs-011): the LLM decides whether to answer directly
        # or call the desk's tools (memory check, packet check, rules,
        # save outcome) and answers from their real results. With no LLM
        # key (or any failure) reply is null and the cockpit falls back
        # to its scripted answers.
        rules_data = load_rules(app.state.rules_path)
        result = agent.run_agent(
            req.message,
            history=[h.model_dump(by_alias=True) for h in req.history],
            adapter=app.state.adapter,
            room=app.state.room,
            rules_data=rules_data,
        )
        if result is None:
            return {"reply": None, "source": "scripted", "actions": []}
        return {
            "reply": result["reply"],
            "source": "agent",
            "actions": result.get("actions", []),
            "strategy_result": result.get("strategy_result"),
            "packet_result": result.get("packet_result"),
        }

    @app.post("/webhooks/claim-intake", response_model=ClaimIntakeResponse)
    def claim_intake(req: ClaimIntakeRequest):
        # Scrub BEFORE retain: no raw PII ever reaches the bank.
        scrubbed, tokens, layers = scrub_text(req.content)
        result = app.state.adapter.retain(
            document={"id": req.document_id, "content": scrubbed},
            tags=list(req.tags),
            timestamp=req.timestamp,
        )
        event = {
            "event_type": "retain.completed",
            "document_id": result["document_id"],
            "memory_unit_count": result.get("memory_unit_count", 1),
            "pii_scrubbed": tokens,
            "backend": result.get("backend", app.state.adapter.backend_name),
        }
        _broadcast(event)
        return ClaimIntakeResponse(
            status="retained",
            document_id=result["document_id"],
            memory_unit_count=result.get("memory_unit_count", 1),
            pii_scrubbed=tokens,
            pii_layers=layers,
            content=scrubbed,
            backend=result.get("backend", app.state.adapter.backend_name),
        )

    @app.post("/webhooks/hindsight")
    async def hindsight_webhook(request: Request):
        body = await request.body()
        if not _verify_hmac(get_webhook_secret(), body, request.headers.get("X-Hindsight-Signature")):
            raise HTTPException(status_code=401, detail="invalid HMAC signature")
        try:
            data = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(status_code=422, detail="body is not valid JSON")
        try:
            event = HindsightWebhookRequest.model_validate(data)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        if event.event_id in app.state.seen_event_ids:
            return {"status": "duplicate", "event_id": event.event_id, "processed": False}
        app.state.seen_event_ids.add(event.event_id)
        _broadcast({
            "event_type": event.event_type,
            "event_id": event.event_id,
            **event.payload,
        })
        return {"status": "processed", "event_id": event.event_id, "processed": True}

    @app.get("/sse/stream")
    async def sse_stream():
        sub: queue_module.Queue = queue_module.Queue()
        app.state.subscribers.add(sub)

        async def event_generator():
            try:
                # Replay the last 50 events first (reconnect catch-up).
                for past in list(app.state.events):
                    yield f"event: {past.get('event_type', 'message')}\ndata: {json.dumps(past)}\n\n"
                while True:
                    try:
                        event = await asyncio.to_thread(sub.get, True, 1.0)
                    except queue_module.Empty:
                        continue
                    yield f"event: {event.get('event_type', 'message')}\ndata: {json.dumps(event)}\n\n"
            finally:
                app.state.subscribers.discard(sub)

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    @app.post("/appeals/strategy")
    def appeals_strategy(req: ClaimRequest):
        # Delete test: a disabled room cannot run the chain at all.
        if not app.state.room.enabled:
            raise HTTPException(status_code=503, detail="Band room is disabled")
        try:
            return run_denial_defense(app.state.adapter, app.state.room, req.model_dump())
        except RoomDisabledError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    @app.post("/appeals/veto")
    def appeals_veto(req: VetoRequest):
        if not app.state.room.enabled:
            raise HTTPException(status_code=503, detail="Band room is disabled")
        critic = make_critic(app.state.adapter)
        return critic({"claim": req.claim.model_dump(), "draft": req.draft.model_dump()})

    @app.get("/scrubber/rules")
    def scrubber_rules():
        return load_rules(app.state.rules_path)

    @app.post("/scrubber/check")
    def scrubber_check(req: CheckRequest):
        return check_packet(req.model_dump(), load_rules(app.state.rules_path))

    @app.post("/scrubber/commit")
    def scrubber_commit(req: CommitRequest):
        # Human gate: no approval flag, no commit. cs-007 applies the rule patch.
        if not req.approved:
            raise HTTPException(
                status_code=403,
                detail="human approval required: commit without an approval flag is refused",
            )
        record = {"claim_id": req.claim_id, "approved": True, "note": req.note, "status": "committed"}
        if req.rule is not None:
            try:
                result = commit_patch(
                    req.rule, path=app.state.rules_path, probe_packet=req.probe_packet
                )
            except PatchError as exc:
                raise HTTPException(status_code=422, detail=str(exc))
            record.update(
                {
                    "rule": result["rule"],
                    "previous_version": result["previous_version"],
                    "probe_verdict": result["probe_verdict"],
                }
            )
        app.state.committed.append(record)
        return {"status": "committed", "claim_id": req.claim_id, "approved": True, **{k: v for k, v in record.items() if k in ("rule", "previous_version", "probe_verdict")}}

    return app


app = create_app()

# Seed the demo bank once at import so the served API has history to recall.
try:
    from seed_history import seed as _seed

    _seed(app.state.adapter)
except Exception:
    pass
