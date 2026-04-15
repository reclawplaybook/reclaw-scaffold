"""
src/heartbeat.py — HEARTBEAT_OK Pattern

Fires every 30 minutes (controlled by main.py's scheduler).

Behavior:
  - Check for open tasks in workspace/memory/tasks.md
  - Check for any flagged items from the previous heartbeat log
  - If nothing actionable: write HEARTBEAT_OK to heartbeat.log and stay quiet
  - If something actionable: send a Discord message to the designated channel

The "HEARTBEAT_OK" contract:
  Every successful quiet heartbeat appends a timestamped HEARTBEAT_OK line to
  workspace/memory/heartbeat.log. If that file stops updating, something is wrong.
  This gives you a dead-man's switch you can monitor externally (e.g., with a cron
  job that alerts if the log hasn't been updated in > 1 hour).

To add your own checks, implement a function that returns a list of strings and
add it to the CHECKS list near the bottom of this file.
"""

import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("heartbeat")

WORKSPACE_DIR = os.path.join(os.path.dirname(__file__), "..", "workspace")
MEMORY_DIR = os.path.join(WORKSPACE_DIR, "memory")
HEARTBEAT_LOG = os.path.join(MEMORY_DIR, "heartbeat.log")
TASKS_FILE = os.path.join(MEMORY_DIR, "tasks.md")


# ---------------------------------------------------------------------------
# Individual check functions — each returns a list of alert strings (empty = OK)
# ---------------------------------------------------------------------------

def check_tasks() -> list[str]:
    """
    Read workspace/memory/tasks.md and surface any open items.

    An open item is any line that starts with '- [ ]' (GitHub-style checkbox).
    Returns a list of open task strings, or empty list if none / file missing.
    """
    if not os.path.exists(TASKS_FILE):
        return []

    open_tasks = []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("- [ ]"):
                    task_text = stripped[len("- [ ]"):].strip()
                    if task_text:
                        open_tasks.append(task_text)
    except Exception:
        logger.exception("Error reading tasks.md")
    return open_tasks


def check_stale_heartbeat() -> list[str]:
    """
    Check if the heartbeat log itself is stale (hasn't been updated in > 2 hours).
    This catches cases where the heartbeat loop died silently.
    Returns an alert list if stale, empty list if OK.
    """
    if not os.path.exists(HEARTBEAT_LOG):
        return []  # First run — nothing to check yet

    try:
        mtime = os.path.getmtime(HEARTBEAT_LOG)
        age_hours = (datetime.utcnow().timestamp() - mtime) / 3600
        if age_hours > 2:
            return [f"Heartbeat log is {age_hours:.1f}h old — may have missed beats"]
    except Exception:
        logger.exception("Error checking heartbeat log mtime")
    return []


# ---------------------------------------------------------------------------
# CHECKS registry — add your own functions here
# ---------------------------------------------------------------------------
CHECKS = [
    check_tasks,
    check_stale_heartbeat,
    # add more: check_calendar, check_email_flags, etc.
]


# ---------------------------------------------------------------------------
# Core heartbeat runner
# ---------------------------------------------------------------------------
def _log_ok():
    """Append a HEARTBEAT_OK line to the heartbeat log."""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(HEARTBEAT_LOG, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} HEARTBEAT_OK\n")
    logger.info("HEARTBEAT_OK")


def _build_discord_message(alerts: list[str]) -> str:
    """Format a list of alert strings into a Discord message."""
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"**Heartbeat Alert — {timestamp}**"]
    for alert in alerts:
        lines.append(f"- {alert}")
    return "\n".join(lines)


def run_heartbeat(discord_client=None) -> None:
    """
    Main heartbeat function. Called by main.py's scheduler every 30 minutes.

    Args:
        discord_client: An active discord.Client instance (optional).
                        If not provided, alerts are only logged — not sent.
    """
    logger.info("Running heartbeat checks...")

    all_alerts: list[str] = []
    for check_fn in CHECKS:
        try:
            results = check_fn()
            all_alerts.extend(results)
        except Exception:
            logger.exception(f"Check {check_fn.__name__} raised an exception")

    if not all_alerts:
        _log_ok()
        return

    # There are alerts — log them and optionally send to Discord
    logger.warning(f"Heartbeat has {len(all_alerts)} alert(s): {all_alerts}")

    heartbeat_channel_id = os.getenv("DISCORD_HEARTBEAT_CHANNEL", "")
    if discord_client and heartbeat_channel_id:
        channel = discord_client.get_channel(int(heartbeat_channel_id))
        if channel:
            import asyncio
            message = _build_discord_message(all_alerts)
            # Schedule the coroutine on the event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(channel.send(message), loop)
        else:
            logger.warning(
                f"DISCORD_HEARTBEAT_CHANNEL={heartbeat_channel_id} not found — "
                "check the channel ID and that the bot has access."
            )
    else:
        logger.info(
            "Alerts found but no Discord client/channel configured — "
            "set DISCORD_HEARTBEAT_CHANNEL in .env to receive notifications."
        )

    # Still log OK so the file's mtime stays fresh (we did run, we just had alerts)
    _log_ok()


# ---------------------------------------------------------------------------
# Manual test entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_heartbeat()
