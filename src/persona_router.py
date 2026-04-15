"""
src/persona_router.py — Channel-to-Persona Routing

Maps Discord channel IDs to persona names so the agent can behave differently
in different channels. For example:
  - #work-planning → "chief-of-staff"
  - #family        → "personal-assistant"
  - #code-review   → "engineer"

Configuration lives in workspace/persona_routing.json (not committed — you
create this from the template after cloning). This file is gitignored because
it contains your channel IDs.

Each persona can have its own soul file at workspace/souls/{persona_name}.md,
which is layered on top of the base SOUL.md when routing to that persona.

If no routing file exists, all messages use the default "assistant" persona.
"""

import os
import json
import logging

logger = logging.getLogger("persona_router")

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "..", "workspace")
ROUTING_FILE = os.path.join(WORKSPACE_DIR, "persona_routing.json")
SOULS_DIR = os.path.join(WORKSPACE_DIR, "souls")

# Default persona name used when no routing match is found
DEFAULT_PERSONA = "assistant"


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _load_routing() -> dict[str, str]:
    """
    Load channel_id → persona_name mapping from JSON.

    Returns empty dict if the file doesn't exist (single-persona mode).

    Expected format:
    {
        "1234567890123456789": "chief-of-staff",
        "9876543210987654321": "engineer"
    }
    """
    if not os.path.exists(ROUTING_FILE):
        logger.debug(
            f"No persona_routing.json found at {ROUTING_FILE}. "
            "Using default persona for all channels."
        )
        return {}

    try:
        with open(ROUTING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.warning("persona_routing.json is not a JSON object — ignoring")
            return {}
        return data
    except json.JSONDecodeError:
        logger.exception("persona_routing.json is invalid JSON — ignoring")
        return {}
    except Exception:
        logger.exception("Error loading persona_routing.json")
        return {}


# Cache the routing table in memory to avoid reading disk on every message
_routing_cache: dict[str, str] | None = None


def _get_routing() -> dict[str, str]:
    global _routing_cache
    if _routing_cache is None:
        _routing_cache = _load_routing()
    return _routing_cache


def get_persona(channel_id: str) -> str:
    """
    Return the persona name for a given Discord channel ID.

    Args:
        channel_id: Discord channel ID as a string (e.g. "1234567890123456789")

    Returns:
        Persona name string. Falls back to DEFAULT_PERSONA if not found.
    """
    routing = _get_routing()
    persona = routing.get(channel_id, DEFAULT_PERSONA)
    logger.debug(f"channel_id={channel_id} → persona='{persona}'")
    return persona


# ---------------------------------------------------------------------------
# Soul loading
# ---------------------------------------------------------------------------

def load_soul(persona_name: str) -> str:
    """
    Load the persona-specific soul file from workspace/souls/{persona_name}.md.

    This content is layered on top of the base SOUL.md to give a persona its
    specific voice, focus, and behavioral rules.

    Args:
        persona_name: e.g. "chief-of-staff", "engineer", "assistant"

    Returns:
        Soul file content as a string, or "" if no persona-specific soul exists.
    """
    if not persona_name or persona_name == DEFAULT_PERSONA:
        return ""

    soul_path = os.path.join(SOULS_DIR, f"{persona_name}.md")
    if not os.path.exists(soul_path):
        logger.debug(f"No soul file for persona '{persona_name}' at {soul_path}")
        return ""

    try:
        with open(soul_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        logger.exception(f"Error loading soul for persona '{persona_name}'")
        return ""


# ---------------------------------------------------------------------------
# Utility: reload routing without restarting
# ---------------------------------------------------------------------------

def reload_routing():
    """Force-reload the routing table from disk. Useful after editing the JSON."""
    global _routing_cache
    _routing_cache = None
    routing = _get_routing()
    logger.info(f"Routing reloaded: {len(routing)} channel(s) configured")
    return routing


# ---------------------------------------------------------------------------
# Manual test entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    print("Default persona:", get_persona("000000000000000000"))
    print("Soul (default):", load_soul("assistant") or "(empty — expected)")
