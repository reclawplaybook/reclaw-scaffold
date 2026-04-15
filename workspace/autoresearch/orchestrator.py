"""
workspace/autoresearch/orchestrator.py — Overnight Optimization Loop

This script runs nightly (via the systemd timer in /systemd/) to automatically
improve the agent's prompt and memory quality.

What it does each night:
  1. Loads a set of test cases from test_cases/general.json
  2. Runs each test case through evaluate.py to get the agent's actual response
  3. Scores each response with judge.py (LLM-as-judge, 1-5 scale)
  4. Logs results to logs/ with a timestamp
  5. Prints a summary: average score, worst-performing cases

Over time, review the logs to identify where the agent underperforms,
then improve SOUL.md, AGENTS.md, or add memory entries to address gaps.

Usage:
    python workspace/autoresearch/orchestrator.py

Or via systemd timer (fires nightly at 2am by default):
    systemctl --user start reclaw-autoresearch.timer
"""

import json
import logging
import os
import sys
from datetime import datetime

# Allow imports from src/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from evaluate import run_evaluation
from judge import score_response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("orchestrator")

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_CASES_FILE = os.path.join(HERE, "test_cases", "general.json")
LOGS_DIR = os.path.join(HERE, "logs")


def load_test_cases() -> list[dict]:
    """Load test cases from the JSON file."""
    with open(TEST_CASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def run_night(dry_run: bool = False) -> dict:
    """
    Execute one full evaluation cycle.

    Args:
        dry_run: If True, skip actual LLM calls (for testing the loop itself).

    Returns:
        Summary dict with scores and any failed cases.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(LOGS_DIR, f"{timestamp}.jsonl")
    os.makedirs(LOGS_DIR, exist_ok=True)

    test_cases = load_test_cases()
    logger.info(f"Loaded {len(test_cases)} test case(s)")

    scores = []
    results = []

    for i, case in enumerate(test_cases):
        case_id = case.get("id", f"case_{i}")
        prompt = case["prompt"]
        criteria = case.get("criteria", "Be helpful and accurate.")

        logger.info(f"[{i+1}/{len(test_cases)}] Running case: {case_id}")

        if dry_run:
            response = "[DRY RUN — skipping LLM call]"
            score = {"score": 3, "rationale": "dry run"}
        else:
            response = run_evaluation(prompt)
            score = score_response(prompt, response, criteria)

        result = {
            "id": case_id,
            "prompt": prompt,
            "response": response,
            "score": score.get("score"),
            "rationale": score.get("rationale"),
        }
        results.append(result)

        numeric_score = score.get("score")
        if isinstance(numeric_score, (int, float)):
            scores.append(numeric_score)

        logger.info(f"  Score: {score.get('score')}/5 — {score.get('rationale', '')[:80]}")

        # Append to log file
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")

    avg_score = sum(scores) / len(scores) if scores else 0
    failed = [r for r in results if r["score"] is not None and r["score"] < 3]

    summary = {
        "timestamp": timestamp,
        "total_cases": len(test_cases),
        "avg_score": round(avg_score, 2),
        "failed_cases": len(failed),
        "log_path": log_path,
    }

    logger.info(
        f"\n=== Night Complete ===\n"
        f"  Cases run:    {len(test_cases)}\n"
        f"  Avg score:    {avg_score:.2f}/5\n"
        f"  Below 3/5:    {len(failed)}\n"
        f"  Log written:  {log_path}\n"
    )

    if failed:
        logger.warning("Cases scoring below 3/5:")
        for r in failed:
            logger.warning(f"  [{r['id']}] score={r['score']} — {r['rationale'][:80]}")

    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run overnight autoresearch cycle")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM calls")
    args = parser.parse_args()
    run_night(dry_run=args.dry_run)
