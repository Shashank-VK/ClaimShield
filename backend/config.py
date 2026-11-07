"""Environment configuration and provider key loaders for ClaimShield Desk."""

import os


def _parse_bool(val, default: bool = False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "on")


# Hindsight memory configuration
HINDSIGHT_API_KEY: str = os.getenv("HINDSIGHT_API_KEY", "")
HINDSIGHT_BASE_URL: str = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")

# Decision model flags (disabled by default so local OSS never fails)
DECISION_MODEL_ENABLED: bool = _parse_bool(os.getenv("DECISION_MODEL_ENABLED"), False)
ENABLE_DECISION_PRUNE: bool = _parse_bool(os.getenv("ENABLE_DECISION_PRUNE"), False)

# Band agent configuration (defaults only, for later multi-agent features)
BAND_AGENT_API_KEY: str = os.getenv("BAND_AGENT_API_KEY", "")
BAND_ROOM_ID: str = os.getenv("BAND_ROOM_ID", "")
BAND_BASE_URL: str = os.getenv("BAND_BASE_URL", "https://api.band.ai")


def get_hindsight_api_key() -> str:
    """Fetch current HINDSIGHT_API_KEY from environment."""
    return os.getenv("HINDSIGHT_API_KEY", "").strip()


def get_hindsight_base_url() -> str:
    """Fetch current HINDSIGHT_BASE_URL from environment."""
    return os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io").strip()


def is_decision_model_enabled() -> bool:
    """Check if decision model is enabled in environment."""
    return _parse_bool(os.getenv("DECISION_MODEL_ENABLED"), DECISION_MODEL_ENABLED)


def is_decision_prune_enabled() -> bool:
    """Check if decision prune is enabled in environment."""
    return _parse_bool(os.getenv("ENABLE_DECISION_PRUNE"), ENABLE_DECISION_PRUNE)


def get_webhook_secret() -> str:
    """HMAC secret for /webhooks/hindsight (dev default; set HINDSIGHT_WEBHOOK_SECRET in production)."""
    return os.getenv("HINDSIGHT_WEBHOOK_SECRET", "dev-only-change-me")
