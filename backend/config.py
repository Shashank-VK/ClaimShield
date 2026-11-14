"""Environment configuration and provider key loaders for ClaimShield Desk."""

import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load KEY=VALUE lines from a project-root .env file, if one exists.

    Real environment variables always win; the file only fills gaps.
    No dependency: the format we need is one KEY=VALUE per line.
    (.env is gitignored — keys never enter the repo.)
    """
    for candidate in (Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"):
        try:
            if not candidate.is_file():
                continue
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
            return
        except OSError:
            continue


_load_dotenv()


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


# OpenRouter (optional): powers free-form Assistant chat answers when a key
# is set. Without a key the Assistant keeps its scripted answers and the
# demo is completely unaffected.
OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def get_openrouter_api_key() -> str:
    """Fetch current OPENROUTER_API_KEY from environment (or .env)."""
    return os.getenv("OPENROUTER_API_KEY", "").strip()


def get_openrouter_model() -> str:
    """Model slug for OpenRouter chat completions."""
    return os.getenv("OPENROUTER_MODEL", OPENROUTER_MODEL).strip() or "openai/gpt-4o-mini"


def get_openrouter_base_url() -> str:
    """OpenRouter API base URL."""
    return os.getenv("OPENROUTER_BASE_URL", OPENROUTER_BASE_URL).strip()


def get_webhook_secret() -> str:
    """HMAC secret for /webhooks/hindsight (dev default; set HINDSIGHT_WEBHOOK_SECRET in production)."""
    return os.getenv("HINDSIGHT_WEBHOOK_SECRET", "dev-only-change-me")
