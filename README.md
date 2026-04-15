# ReClaw Scaffold

A minimal, clone-and-run starter kit for building a personal AI agent.

This is the scaffold that the [ReClaw Playbook](https://reclawplaybook.com) teaches you to build and extend. Clone it, configure it, and have a working Discord-connected agent in under 30 minutes.

---

## What You Get

- A Discord bot that responds to messages using Claude
- A heartbeat system that checks for open tasks every 30 minutes and logs `HEARTBEAT_OK`
- Flat-file memory (read/write/search Markdown files — no database)
- Persona routing (different behavior in different Discord channels)
- An overnight autoresearch loop that evaluates response quality while you sleep
- Systemd service files for running the agent 24/7 on a Linux server
- Template files for SOUL.md, USER.md, AGENTS.md, and DIRECTIVE.md

**What this is NOT:** a finished product. It's a starting point. The Playbook teaches you to extend it.

---

## Prerequisites

Before you start:

- **WSL2 + Ubuntu** (or any Linux — macOS works too)
- **Python 3.10+**
- **A Discord server** where you have admin access
- **Claude Max subscription** (for the Claude Code SDK proxy) — or an Anthropic API key

---

## 30-Minute Quick Start

### Step 1 — Clone and Setup (2 min)

```bash
git clone https://github.com/reclawplaybook/reclaw-scaffold.git
cd reclaw-scaffold
chmod +x setup.sh
./setup.sh
```

This creates a virtual environment, installs dependencies, and copies template files.

### Step 2 — Create a Discord Bot (5 min)

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** → give it a name
3. Go to **Bot** → click **Add Bot**
4. Under **Privileged Gateway Intents**, enable **Message Content Intent**
5. Copy the **Token** — you'll need it for `.env`
6. Go to **OAuth2 → URL Generator** → select `bot` scope → select `Send Messages` and `Read Message History` permissions
7. Open the generated URL and invite the bot to your server

### Step 3 — Configure .env (2 min)

```bash
# .env was already created by setup.sh — open it and fill in:
nano .env
```

Required fields:
```
DISCORD_BOT_TOKEN=    ← paste your bot token
DISCORD_GUILD_ID=     ← right-click your server → Copy Server ID
```

To get your Server ID: in Discord, go to **Settings → Advanced → Developer Mode** (enable it), then right-click your server name and select **Copy Server ID**.

### Step 4 — Edit USER.md (15 min — do not skip)

```bash
nano workspace/USER.md
```

This is the most important step. The agent reads USER.md on every message. The more context you give it about who you are, what you're working on, and how you communicate, the better it performs out of the box.

Also edit `workspace/SOUL.md` to give the agent its name and voice.

### Step 5 — Run a Dry-Run Test (1 min)

```bash
source venv/bin/activate
python src/main.py --dry-run
```

You should see:
```
Memory: OK
Persona router: OK (default='assistant')
Heartbeat check_tasks: OK (0 item(s))
=== DRY RUN COMPLETE — all checks passed ===
```

If you see errors, check that your `.env` is filled in and your venv is active.

### Step 6 — Start the Agent (1 min)

```bash
source venv/bin/activate
python src/main.py
```

You should see `Agent online as YourBotName#0000`. Go to your Discord server and send a message in any channel the bot can read. It should respond.

### Step 7 — Install as a Systemd Service (5 min)

To keep the agent running 24/7 (and restart on failure):

```bash
# Edit the service file with your actual paths
nano systemd/openclaw.service
# Replace YOUR_USERNAME with your Linux username

# Install and enable the service
mkdir -p ~/.config/systemd/user
cp systemd/openclaw.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable openclaw
systemctl --user start openclaw

# Verify it's running
systemctl --user status openclaw

# Keep service running when you log out
loginctl enable-linger $USER
```

### Step 8 — Verify the Heartbeat (5 min wait)

After the agent has been running for a few minutes:

```bash
cat workspace/memory/heartbeat.log
```

You should see timestamped `HEARTBEAT_OK` lines. If this file isn't updating, something is wrong with the heartbeat loop.

---

## Architecture Overview

```
src/
├── main.py          — entry point; Discord client + heartbeat scheduler
├── agent.py         — core LLM call; loads SOUL + AGENTS + USER + memory
├── heartbeat.py     — fires every 30 min; logs HEARTBEAT_OK or sends alerts
├── memory.py        — read/write/search flat Markdown memory files
└── persona_router.py — maps channel IDs → persona names + soul files

workspace/
├── SOUL.md          — agent's identity and voice (you fill this in)
├── USER.md          — who you are and what you need (you fill this in)
├── AGENTS.md        — operating rules (you fill this in)
├── DIRECTIVE.md     — mission and current goals (you fill this in)
├── memory/          — all memory files live here
├── souls/           — optional persona-specific soul files
├── skills/          — skill templates (trigger phrases + prompt templates)
└── autoresearch/    — overnight evaluation loop
```

---

## Persona Routing

To make the agent behave differently in different channels:

1. Create `workspace/persona_routing.json`:
```json
{
  "YOUR_CHANNEL_ID": "chief-of-staff",
  "ANOTHER_CHANNEL_ID": "engineer"
}
```

2. Create a soul file for each persona at `workspace/souls/chief-of-staff.md`

The agent will layer the persona soul on top of the base SOUL.md when routing to that channel.

---

## Adding Memory

The agent auto-saves substantive exchanges to `workspace/memory/agent_log.md`.

You can also write directly:
```python
from memory import write_memory
write_memory("tasks.md", "- [ ] Follow up with client about proposal\n")
```

Or just open the files in a text editor — they're plain Markdown.

---

## Overnight Autoresearch

The autoresearch loop evaluates agent quality while you sleep:

```bash
# Install the systemd timer (fires nightly at 2am)
cp systemd/reclaw-autoresearch.service ~/.config/systemd/user/
cp systemd/reclaw-autoresearch.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable reclaw-autoresearch.timer
systemctl --user start reclaw-autoresearch.timer

# Run a single evaluation cycle manually
python workspace/autoresearch/orchestrator.py

# Dry-run (no LLM calls)
python workspace/autoresearch/orchestrator.py --dry-run
```

Results are written to `workspace/autoresearch/logs/` as JSONL files.

---

## What to Build Next

This scaffold is intentionally minimal. The [ReClaw Playbook](https://reclawplaybook.com) covers:

- Multi-persona routing with distinct voice files
- The full self-learning loop (nightly prompt optimization)
- Tool integrations (web search, calendar, email, Twitter/X)
- Mission control and task management
- Board meeting system for weekly agent performance reviews
- Deploying to a VPS for always-on operation

---

## Troubleshooting

**Bot isn't responding in Discord:**
- Check `journalctl --user -u openclaw -f` for errors
- Verify **Message Content Intent** is enabled in the Discord Developer Portal
- Confirm the bot has permissions to read and send in the channel

**`HEARTBEAT_OK` not appearing:**
- Check that the agent has been running for at least 30 minutes
- Verify `HEARTBEAT_INTERVAL_MINUTES` in `.env`
- Run manually: `python -c "from heartbeat import run_heartbeat; run_heartbeat()"`

**Claude proxy not connecting:**
- Ensure Claude Code is running: `claude` in a terminal should start the session
- Default proxy URL is `http://127.0.0.1:3456` — check `OPENCLAW_PROXY_URL` in `.env`
- Alternatively, set `OPENCLAW_USE_SDK=false` and provide `ANTHROPIC_API_KEY`

**Permission errors on memory files:**
- Run `ls -la workspace/memory/` — check file ownership
- The agent process needs write access to `workspace/memory/`

---

## License

MIT. Use this however you want.

---

*Built on the ReClaw architecture. Questions? See the [Playbook](https://reclawplaybook.com).*
