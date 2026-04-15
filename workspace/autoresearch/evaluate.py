"""
workspace/autoresearch/evaluate.py — Test Case Runner

Runs a single prompt through the agent and returns the response.
Called by orchestrator.py for each test case.

This is intentionally thin — it just calls process_message() from src/agent.py
with the "assistant" persona. Swap in a different persona if your test cases
need one.

Usage (standalone):
    python workspace/autoresearch/evaluate.py "What are today's top priorities?"
"""

import os
import sys
import logging

# Allow imports from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

logger = logging.getLogger("evaluate")


def run_evaluation(prompt: str, persona: str = "assistant") -> str:
    """
    Run a prompt through the agent and return the response text.

    Args:
        prompt:  The input prompt / test question.
        persona: Persona to use (default: "assistant").

    Returns:
        The agent's response as a string.
        Returns an error string (prefixed with "[ERROR]") if the call fails.
    """
    try:
        from agent import process_message
        return process_message(prompt, persona_name=persona)
    except Exception as exc:
        logger.exception(f"Evaluation failed for prompt: {prompt[:80]}")
        return f"[ERROR] {exc}"


# ---------------------------------------------------------------------------
# Manual test entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Say hello in one sentence."
    print(f"Prompt: {prompt}")
    response = run_evaluation(prompt)
    print(f"Response:\n{response}")
