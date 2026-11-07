"""Deterministic PII scrubber (PRD §6.7).

Runs BEFORE any ``retain()`` so no Indian ID ever reaches the Hindsight bank.

Two layers, matching the demo's toast labels:
- backend layer (this module): PAN, Aadhaar, Indian mobile — the native
  Memory Defense detector does NOT cover these.
- native layer (simulated here; the real Hindsight Memory Defense catches
  US-style SSN / credit cards): SSN and 16-digit cards.

The mobile pattern extends the PRD form ``\\+91[\\s-]?\\d{10}`` with the
common 5-5 spaced form (``+91 98765 43210``). All other patterns are the
PRD regexes verbatim.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
MOBILE_RE = re.compile(r"\+91[\s-]?(?:\d{10}|\d{5}[\s-]?\d{5})\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD_RE = re.compile(r"\b\d{4}[- ]\d{4}[- ]\d{4}[- ]\d{4}\b")

# (pattern, replacement token, layer) in application order. Card runs before
# Aadhaar so a 16-digit grouped card is not half-eaten as a 12-digit Aadhaar.
_RULES: List[Tuple[re.Pattern, str, str]] = [
    (CARD_RE, "[REDACTED:card]", "native"),
    (PAN_RE, "[REDACTED:pan]", "backend"),
    (MOBILE_RE, "[REDACTED:phone]", "backend"),
    (AADHAAR_RE, "[REDACTED:aadhaar]", "backend"),
    (SSN_RE, "[REDACTED:ssn]", "native"),
]


def scrub_text(text: str) -> Tuple[str, List[str], Dict[str, str]]:
    """Scrub ``text`` and report what was caught.

    Returns ``(scrubbed_text, pii_scrubbed, pii_layers)`` where
    ``pii_scrubbed`` is the list of replacement tokens used (e.g.
    ``["[REDACTED:pan]", "[REDACTED:ssn]"]``) and ``pii_layers`` maps each
    token to the layer that caught it (``"backend"`` or ``"native"``) for the
    UI toast. Clean text passes through unchanged with empty lists.
    """
    scrubbed = text
    pii_scrubbed: List[str] = []
    pii_layers: Dict[str, str] = {}
    for pattern, token, layer in _RULES:
        if pattern.search(scrubbed):
            scrubbed = pattern.sub(token, scrubbed)
            if token not in pii_scrubbed:
                pii_scrubbed.append(token)
            pii_layers[token] = layer
    return scrubbed, pii_scrubbed, pii_layers
