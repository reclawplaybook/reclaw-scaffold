"""
workspace/autoresearch/judge.py — LLM-as-Judge Scorer

Scores an agent response on a 1–5 scale using another LLM call.
This is the "LLM-as-judge" pattern: the same model (or a different one)
evaluates the quality of a response against stated criteria.

Why this works:
  - Faster and cheaper than human eval at scale
  - Consistent enough to catch regressions over time
  - You can tune the judge prompt to match your quality bar

Usage (standalone):
    python workspace/autoresearch/judge.py
"""

import os
import sys
import json
import logging

# Allow imports from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

logger = logging.getLogger("judge")

OPENCLAW_PROXY_URL = os.getenv("OPENCLAW_PROXY_URL", "http://127.0.0.1:3456")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "claude-opus-4-5")

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key="not-required-for-local-proxy",
            base_url=OPENCLAW_PROXY_URL,
        )
    return _client


JUDGE_SYSTEM_PROMPT = """You are an objective evaluator of AI assistant responses.

Your job is to score a response on a 1-5 scale based on the stated criteria.

Scoring rubric:
  5 — Excellent: fully addresses the prompt, accurate, well-structured, no fluff
  4 — Good: addresses the prompt, minor gaps or verbosity
  3 — Adequate: partially addresses the prompt, some relevant content
  2 — Poor: misses key points, inaccurate, or overly generic
  1 — Fail: wrong, harmful, or completely off-topic

Respond ONLY with a JSON object in this exact format:
{"score": <1-5 integer>, "rationale": "<one sentence explanation>"}
"""


def score_response(
    prompt: str,
    response: str,
    criteria: str = "Be helpful, accurate, and concise.",
) -> dict:
    """
    Score an agent response using LLM-as-judge.

    Args:
        prompt:    The original user prompt.
        response:  The agent's response to evaluate.
        criteria:  Quality criteria specific to this test case.

    Returns:
        Dict with keys: "score" (int 1-5) and "rationale" (str).
        Returns {"score": None, "rationale": "<error>"} on failure.
    """
    judge_prompt = (
        f"Prompt: {prompt}\n\n"
        f"Criteria: {criteria}\n\n"
        f"Response to evaluate:\n{response}\n\n"
        "Score this response."
    )

    try:
        result = _get_client().chat.completions.create(
            model=JUDGE_MODEL,
            max_tokens=256,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": judge_prompt},
            ],
        )
        raw = result.choices[0].message.content or ""
        # Extract JSON from the response
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        return {
            "score": int(parsed.get("score", 0)),
            "rationale": str(parsed.get("rationale", "")),
        }
    except json.JSONDecodeError:
        logger.warning(f"Judge returned non-JSON: {raw[:200]}")
        return {"score": None, "rationale": f"Parse error: {raw[:100]}"}
    except Exception as exc:
        logger.exception("Judge scoring failed")
        return {"score": None, "rationale": f"Error: {exc}"}


# ---------------------------------------------------------------------------
# Manual test entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_prompt = "What is 2 + 2?"
    test_response = "The answer is 4."
    test_criteria = "Must provide the correct numerical answer."
    result = score_response(test_prompt, test_response, test_criteria)
    print(f"Score: {result['score']}/5")
    print(f"Rationale: {result['rationale']}")
