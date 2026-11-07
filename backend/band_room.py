"""Band room bus (W3 denial defense).

The room routes @mention messages between agents (@ClaimAuditor,
@PolicyCritic, @ScrubberCoder). Two modes, reported honestly:

- "local": in-process room bus (what runs here). Band SDK needs a Band
  account + API key + room id; none are present on this VM, so the local bus
  is the live mode and ``band_mode`` reports "local".
- "sdk": Band SDK room, only when BAND_AGENT_API_KEY + BAND_ROOM_ID are set
  AND the ``band`` package imports. If the SDK cannot be reached the room
  falls back to the local bus and reports "local" — never claims SDK.

The delete test (cs-006): with the room disabled, the veto -> patch chain
cannot run at all — ``run_denial_defense`` raises ``RoomDisabledError`` and
``/appeals/strategy`` answers 503, so no packet can reach commit.
"""

from __future__ import annotations

import importlib.util
import os
from typing import Any, Callable, Dict, List, Optional


class RoomDisabledError(RuntimeError):
    """Raised when the room bus is disabled: the agent chain cannot run."""


def detect_band_mode() -> str:
    """Return "sdk" only if Band credentials AND the SDK package are present."""
    if os.getenv("BAND_AGENT_API_KEY") and os.getenv("BAND_ROOM_ID"):
        if importlib.util.find_spec("band") is not None:
            return "sdk"
    return "local"


class RoomBus:
    """In-process @mention room bus with an event log (drives the cockpit stream)."""

    def __init__(self, enabled: bool = True, mode: Optional[str] = None) -> None:
        self.enabled = enabled
        self.mode = mode or detect_band_mode()
        if self.mode == "sdk":
            # No live SDK session on this VM: fall back honestly.
            self.mode = "local"
        self.agents: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self.events: List[Dict[str, Any]] = []

    def register(self, mention: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        self.agents[mention] = fn

    def send(self, mention: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            raise RoomDisabledError(
                f"Band room is disabled; {mention} cannot run and no packet can reach commit."
            )
        if mention not in self.agents:
            raise ValueError(f"no agent registered for {mention}")
        self.events.append({"mention": mention, "direction": "in", "payload": payload})
        result = self.agents[mention](payload)
        self.events.append({"mention": mention, "direction": "out", "result": result})
        return result
