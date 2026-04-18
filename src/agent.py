"""
src/agent.py — Core Reasoning Loop

This is the brain of your agent. For every incoming message it:
  1. Loads the agent's identity context (SOUL.md, AGENTS.md, USER.md, persona soul)
  2. Searches memory for relevant context (keyword search, not vector)
  3. Calls Claude via an OpenAI-compatible interface (works with the local Claude Code proxy)
  4. Returns the response text

To swap in a different LLM or use the Anthropic SDK directly, only this file needs to change.
"""

import os
import logging
from openai import OpenAI
from dotenv import load_dotenv

from memory import search_memory, write_memory
from persona_router import load_soul

load_dotenv()

logger = logging.getLogger("agent")

# ---------------------------------------------------------------------------
# Config — all overridable via .env
# ---------------------------------------------------------------------------
OPENCLAW_PROXY_URL = os.getenv("OPENCLAW_PROXY_URL", "http://127.0.0.1:3456")
OPENCLAW_USE_SDK = os.getenv("OPENCLAW_USE_SDK", "true").lower() == "true"
MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-4-6")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

# Path to workspace context files (relative to repo root; adjust if needed)
WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "..", "workspace")
SOUL_PATH = os.path.join(WORKSPACE_DIR, "SOUL.md")
AGENTS_PATH = os.path.join(WORKSPACE_DIR, "AGENTS.md")
USER_PATH = os.path.join(WORKSPACE_DIR, "USER.md")

# ---------------------------------------------------------------------------
# Claude client (OpenAI-compatible)
# ---------------------------------------------------------------------------
_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key="not-required-for-local-proxy",  # proxy handles auth
            base_url=OPENCLAW_PROXY_URL,
        )
    return _client


# ---------------------------------------------------------------------------
# Context loading helpers
# ---------------------------------------------------------------------------
def _read_file(path: str) -> str:
    """Read a file, return empty string if missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _build_system_prompt(persona_name: str) -> str:
    """Assemble the system prompt from SOUL + AGENTS + USER + persona soul."""
    parts = []

    soul = _read_file(SOUL_PATH)
    if soul:
        parts.append(f"# Agent Identity\n{soul}")

    agents = _read_file(AGENTS_PATH)
    if agents:
        parts.append(f"# Operating Rules\n{agents}")

    user = _read_file(USER_PATH)
    if user:
        parts.append(f"# User Profile\n{user}")

    persona_soul = load_soul(persona_name)
    if persona_soul:
        parts.append(f"# Persona: {persona_name}\n{persona_soul}")

    if not parts:
        parts.append(
            "You are a helpful personal AI agent. "
            "Be direct, concise, and useful. No filler."
        )

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Memory injection
# ---------------------------------------------------------------------------
def _inject_memory(user_message: str) -> str:
    """Search memory and return relevant context as a formatted block."""
    hits = search_memory(user_message)
    if not hits:
        return ""
    lines = ["[Relevant memory context:]"]
    for filename, snippet in hits:
        lines.append(f"  [{filename}] {snippet}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def process_message(user_message: str, persona_name: str = "assistant") -> str:
    """
    Core agent function. Takes a raw user message and returns a response string.

    Args:
        user_message:  The raw text received from the user.
        persona_name:  Which persona context to load (from persona_router).

    Returns:
        The agent's response as a plain string.
    """
    system_prompt = _build_system_prompt(persona_name)

    # Prepend any relevant memory context to the user message
    memory_context = _inject_memory(user_message)
    if memory_context:
        augmented_message = f"{memory_context}\n\nUser: {user_message}"
    else:
        augmented_message = user_message

    logger.debug(
        f"Calling model '{MODEL_NAME}' | persona='{persona_name}' | "
        f"user_msg_len={len(user_message)} | memory_context={'yes' if memory_context else 'no'}"
    )

    try:
        response = _get_client().chat.completions.create(
            model=MODEL_NAME,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": augmented_message},
            ],
        )
        reply = response.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("LLM call failed")
        raise RuntimeError(f"Agent call failed: {exc}") from exc

    # Auto-save heuristic: if the response is substantive, offer to log it
    if len(reply) > 200:
        _maybe_save_to_memory(user_message, reply)

    return reply


def _maybe_save_to_memory(user_message: str, response: str) -> None:
    """
    Save notable agent exchanges to memory automatically.

    Heuristic: responses longer than 200 characters are considered substantive.
    You can make this smarter — e.g., check for keywords, ask the user, etc.
    """
    from datetime import datetime

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    entry = (
        f"\n## {timestamp}\n"
        f"**Q:** {user_message[:200]}\n"
        f"**A:** {response[:500]}\n"
    )
    try:
        write_memory("agent_log.md", entry)
        logger.debug("Saved exchange to agent_log.md")
    except Exception:
        logger.warning("Could not auto-save exchange to memory", exc_info=True)
