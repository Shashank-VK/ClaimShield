"""Tests for the PII scrubber (cs-003, PRD §6.7)."""

from fastapi.testclient import TestClient

from backend.hindsight_adapter import HindsightAdapter
from backend.main import create_app
from backend.pii_scrubber import scrub_text

PAN = "ABCDE1234F"
AADHAAR_SPACED = "1234 5678 9012"
AADHAAR_PLAIN = "123456789012"
MOBILE = "+91 9876543210"
SSN = "123-45-6789"


def test_pan_redacted():
    scrubbed, tokens, layers = scrub_text(f"PAN {PAN} on file")
    assert scrubbed == "PAN [REDACTED:pan] on file"
    assert "[REDACTED:pan]" in tokens
    assert layers["[REDACTED:pan]"] == "backend"


def test_aadhaar_spaced_and_unspaced():
    scrubbed, tokens, layers = scrub_text(f"Aadhaar {AADHAAR_SPACED} and {AADHAAR_PLAIN}")
    assert AADHAAR_SPACED not in scrubbed
    assert AADHAAR_PLAIN not in scrubbed
    assert scrubbed.count("[REDACTED:aadhaar]") == 2
    assert layers["[REDACTED:aadhaar]"] == "backend"


def test_mobile_redacted():
    scrubbed, tokens, layers = scrub_text(f"Call {MOBILE} or +919876543210")
    assert MOBILE not in scrubbed
    assert "+919876543210" not in scrubbed
    assert scrubbed.count("[REDACTED:phone]") == 2
    assert layers["[REDACTED:phone]"] == "backend"


def test_ssn_native_layer():
    scrubbed, tokens, layers = scrub_text(f"SSN {SSN} in the packet")
    assert SSN not in scrubbed
    assert "[REDACTED:ssn]" in tokens
    assert layers["[REDACTED:ssn]"] == "native"


def test_clean_text_unchanged():
    text = "Star Health dengue claim Rs.1,45,000, NS1 antigen positive, platelet 42000."
    scrubbed, tokens, layers = scrub_text(text)
    assert scrubbed == text
    assert tokens == []
    assert layers == {}


def test_intake_ssn_redacted_and_nothing_raw_stored():
    adapter = HindsightAdapter()
    client = TestClient(create_app(adapter))
    content = (
        f"Claim packet: PAN {PAN}, Aadhaar {AADHAAR_SPACED}, mobile {MOBILE}, "
        f"SSN {SSN}. Star Health dengue claim."
    )
    resp = client.post(
        "/webhooks/claim-intake",
        json={
            "document_id": "SYNTHETIC-CLM-PII-01",
            "content": content,
            "tags": ["insurer:star_health", "diagnosis_group:dengue", "synthetic"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "retained"
    assert "[REDACTED:ssn]" in body["pii_scrubbed"]
    assert "[REDACTED:pan]" in body["pii_scrubbed"]
    assert "[REDACTED:aadhaar]" in body["pii_scrubbed"]
    assert "[REDACTED:phone]" in body["pii_scrubbed"]
    assert body["pii_layers"]["[REDACTED:ssn]"] == "native"
    assert body["pii_layers"]["[REDACTED:pan]"] == "backend"
    for raw in (PAN, AADHAAR_SPACED, MOBILE, SSN):
        assert raw not in body["content"], f"raw value leaked in response: {raw}"

    # Nothing raw in any stored record.
    hits = adapter.recall("Star Health dengue", tags=["insurer:star_health"], top_k=5)
    assert hits, "intake must have retained the packet"
    stored = hits[0]["content"]
    for raw in (PAN, AADHAAR_SPACED, MOBILE, SSN):
        assert raw not in stored, f"raw value leaked in stored record: {raw}"
    assert "[REDACTED:ssn]" in stored
