"""
src/main.py — Service Entry Point

This is the top-level entry point for your personal AI agent. It:
  - Loads environment variables from .env
  - Initializes the Discord client and registers the message handler
  - Starts the heartbeat scheduler (fires every 30 minutes)
  - Runs the async event loop

Usage:
    python src/main.py

For production, use the systemd service file in /systemd/openclaw.service.
"""

import os
import sys
import asyncio
import logging
import argparse
import threading
import schedule
import time
import discord
from dotenv import load_dotenv

from agent import process_message
from persona_router import get_persona
from heartbeat import run_heartbeat

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

# ---------------------------------------------------------------------------
# Load environment
# ---------------------------------------------------------------------------
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
HEARTBEAT_INTERVAL_MINUTES = int(os.getenv("HEARTBEAT_INTERVAL_MINUTES", "30"))


# ---------------------------------------------------------------------------
# Discord client
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    logger.info(f"Agent online as {client.user}")


@client.event
async def on_message(message: discord.Message):
    """Route every incoming message through the agent."""
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    persona_name = get_persona(str(message.channel.id))
    logger.info(
        f"Message in #{message.channel} → persona '{persona_name}' | "
        f"from {message.author}: {message.content[:80]}"
    )

    async with message.channel.typing():
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None, process_message, message.content, persona_name
            )
            if response:
                # Discord has a 2000-char limit per message
                for chunk in [response[i:i+2000] for i in range(0, len(response), 2000)]:
                    await message.channel.send(chunk)
        except Exception as exc:
            logger.exception("Error processing message")
            await message.channel.send(f"[Agent error: {exc}]")


# ---------------------------------------------------------------------------
# Heartbeat scheduler (runs in a background thread)
# ---------------------------------------------------------------------------
def _heartbeat_thread(loop: asyncio.AbstractEventLoop):
    """Background thread that fires run_heartbeat on a schedule."""

    async def _async_heartbeat():
        await asyncio.get_event_loop().run_in_executor(None, run_heartbeat, client)

    def _job():
        asyncio.run_in_thread = None  # avoid shadowing
        future = asyncio.run_coroutine_threadsafe(
            asyncio.get_event_loop().run_in_executor(None, run_heartbeat, client),
            loop,
        )
        try:
            future.result(timeout=120)
        except Exception:
            logger.exception("Heartbeat error")

    schedule.every(HEARTBEAT_INTERVAL_MINUTES).minutes.do(_job)
    logger.info(f"Heartbeat scheduled every {HEARTBEAT_INTERVAL_MINUTES} minutes")

    while True:
        schedule.run_pending()
        time.sleep(30)


# ---------------------------------------------------------------------------
# Dry-run mode (for testing without Discord)
# ---------------------------------------------------------------------------
def dry_run():
    """Verify the agent stack loads and basic components work."""
    logger.info("=== DRY RUN MODE ===")

    # Test memory
    from memory import write_memory, read_memory, search_memory
    write_memory("test.md", "# Test\nThis is a dry-run test entry.")
    content = read_memory("test.md")
    assert "dry-run" in content, "Memory read/write failed"
    results = search_memory("dry-run")
    assert results, "Memory search returned nothing"
    logger.info("Memory: OK")

    # Test persona router
    persona = get_persona("000000000000000000")
    assert isinstance(persona, str), "Persona router failed"
    logger.info(f"Persona router: OK (default='{persona}')")

    # Test heartbeat (log-only, no Discord)
    from heartbeat import check_tasks
    result = check_tasks()
    assert isinstance(result, list), "Heartbeat check_tasks failed"
    logger.info(f"Heartbeat check_tasks: OK ({len(result)} item(s))")

    logger.info("=== DRY RUN COMPLETE — all checks passed ===")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main():
    if not DISCORD_BOT_TOKEN:
        logger.error(
            "DISCORD_BOT_TOKEN is not set. Copy .env.example → .env and fill it in."
        )
        sys.exit(1)

    # Start heartbeat in background thread
    loop = asyncio.get_event_loop()
    hb_thread = threading.Thread(
        target=_heartbeat_thread, args=(loop,), daemon=True, name="heartbeat"
    )
    hb_thread.start()

    await client.start(DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReClaw Scaffold Agent")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify all components load correctly without connecting to Discord.",
    )
    args = parser.parse_args()

    if args.dry_run:
        dry_run()
    else:
        asyncio.run(main())
