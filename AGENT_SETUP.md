# ReClaw Agent Self-Setup Protocol

## What This Is

You are an AI agent. This file tells you exactly what to do to set up a new ReClaw instance on this machine. Follow every step in order. Do not skip steps. If a step fails, log the error and continue unless the step is marked BLOCKING.

This protocol is designed to be executed autonomously — no human input required except where explicitly marked [HUMAN REQUIRED].

---

## Prerequisites Check

Run these commands to verify the environment is ready before proceeding.

```bash
# Check Python version (must be 3.10+)
python3 --version

# Check git
git --version

# Check pip
pip3 --version

# Check available disk space (need at least 500MB)
df -h ~

# Check if systemd is available (for service install)
systemctl --version 2>/dev/null && echo "systemd available" || echo "systemd not available — service install will be skipped"
```

If Python is below 3.10, STOP. Log: "PREREQ_FAIL: Python 3.10+ required." Do not continue.

If git is not found, run:
```bash
sudo apt-get update && sudo apt-get install -y git
```

---

## Step 1: Clone the Scaffold

ACTION:
```bash
git clone https://github.com/reclawplaybook/reclaw-scaffold.git ~/my-reclaw
```

VERIFY:
```bash
ls ~/my-reclaw/src/main.py && echo "CLONE_OK" || echo "CLONE_FAIL"
```

Expected output: `CLONE_OK`

If CLONE_FAIL: check network connectivity. Retry once. If still failing, log and STOP (BLOCKING).

---

## Step 2: Install Dependencies

ACTION:
```bash
cd ~/my-reclaw && pip3 install -r requirements.txt
```

VERIFY:
```bash
python3 -c "import discord, anthropic, dotenv, requests, schedule; print('DEPS_OK')"
```

Expected output: `DEPS_OK`

If import fails, run:
```bash
pip3 install discord.py anthropic python-dotenv requests schedule openai
```

---

## Step 3: Copy Environment Template

ACTION:
```bash
cp ~/my-reclaw/.env.example ~/my-reclaw/.env
```

VERIFY:
```bash
ls ~/my-reclaw/.env && echo "ENV_FILE_OK"
```

---

## Step 4: Configure Identity

ACTION: Copy templates to workspace and fill in the identity files.

```bash
cp ~/my-reclaw/templates/USER.md ~/my-reclaw/workspace/USER.md
cp ~/my-reclaw/templates/SOUL.md ~/my-reclaw/workspace/SOUL.md
cp ~/my-reclaw/templates/AGENTS.md ~/my-reclaw/workspace/AGENTS.md
cp ~/my-reclaw/templates/DIRECTIVE.md ~/my-reclaw/workspace/DIRECTIVE.md
```

Then edit `~/my-reclaw/workspace/USER.md`. Replace every `[PLACEHOLDER]` with real values. Use the template below:

```markdown
# USER.md — [OWNER_NAME]
> Tell the agent who you are. More detail = better performance.

## Identity
- Name: [OWNER_NAME]
- Location: [CITY, STATE]
- Occupation: [OCCUPATION]
- Timezone: [TIMEZONE, e.g. America/Chicago]

## Businesses / Projects
- [PROJECT_1_NAME]: [ONE_SENTENCE_DESCRIPTION]
- [PROJECT_2_NAME]: [ONE_SENTENCE_DESCRIPTION]

## Communication Preferences
- Preferred response style: [e.g. direct, no fluff]
- Vocabulary notes: [any abbreviations or terms to know]
- Do not repeat: [what you hate seeing restated]

## Schedule Patterns
- Morning: [typical morning focus]
- Workday: [primary work focus]
- Evening: [typical evening activities]

## What You Expect From the Agent
- [EXPECTATION_1]
- [EXPECTATION_2]
- [EXPECTATION_3]
```

If you have context about the operator (from prior memory files, conversation history, or USER.md in the current agent's workspace), use it to fill in as many fields as possible. Leave fields as [PLACEHOLDER] only if you have no information.

VERIFY:
```bash
grep -c "\[OWNER_NAME\]" ~/my-reclaw/workspace/USER.md && echo "Still has placeholders — fill in manually" || echo "USER_MD_OK"
```

---

## Step 5: Create Discord Bot

[HUMAN REQUIRED — this step cannot be automated]

Instruct the operator to complete the following:

1. Navigate to: https://discord.com/developers/applications
2. Click "New Application" — name it anything (e.g. the agent's intended name)
3. Go to the "Bot" tab on the left sidebar
4. Click "Reset Token" and copy the token — save it securely
5. Under "Privileged Gateway Intents", enable: MESSAGE CONTENT INTENT, SERVER MEMBERS INTENT, PRESENCE INTENT
6. Go to "OAuth2" → "URL Generator"
7. Check scopes: `bot`, `applications.commands`
8. Check bot permissions: Send Messages, Read Message History, Embed Links
9. Copy the generated URL, open it in a browser, add the bot to your Discord server
10. Right-click your Discord server name → Copy Server ID (requires Developer Mode: Settings → Advanced → Developer Mode)

When complete, the operator should have:
- DISCORD_BOT_TOKEN (long string starting with M or OD)
- DISCORD_GUILD_ID (18-digit number)

Log: "Awaiting Discord credentials from operator."

---

## Step 6: Configure Environment Variables

ACTION: Write the Discord credentials and other config to .env.

```bash
# After operator provides DISCORD_BOT_TOKEN and DISCORD_GUILD_ID:
# Replace the placeholders in .env

sed -i "s|^DISCORD_BOT_TOKEN=.*|DISCORD_BOT_TOKEN=[DISCORD_BOT_TOKEN_VALUE]|" ~/my-reclaw/.env
sed -i "s|^DISCORD_GUILD_ID=.*|DISCORD_GUILD_ID=[DISCORD_GUILD_ID_VALUE]|" ~/my-reclaw/.env
```

Full .env reference — ensure these are set:

```bash
# Required
DISCORD_BOT_TOKEN=[FROM_DISCORD_DEVELOPER_PORTAL]
DISCORD_GUILD_ID=[18_DIGIT_SERVER_ID]

# Claude routing (Claude Code SDK — Claude Max subscription)
OPENCLAW_USE_SDK=true
OPENCLAW_PROXY_URL=http://127.0.0.1:3456

# Optional — enhanced capabilities
PERPLEXITY_API_KEY=[OPTIONAL_FOR_WEB_SEARCH]
DISCORD_HEARTBEAT_CHANNEL=[OPTIONAL_CHANNEL_ID]
```

VERIFY:
```bash
grep "DISCORD_BOT_TOKEN" ~/my-reclaw/.env | grep -v "=$" && echo "TOKEN_SET" || echo "TOKEN_MISSING"
```

---

## Step 7: Personalize Agent Soul

ACTION: Edit `~/my-reclaw/workspace/SOUL.md` — replace all [PLACEHOLDER] fields.

Template:
```markdown
# SOUL.md — [AGENT_NAME]

## Name
[AGENT_NAME]

## Voice
- Direct. No filler. No "Great question!"
- Opinionated when you have a view
- Honest about uncertainty
- Match the energy: casual in chat, precise when coding

## Core Behaviors
- Just do it. Full permissions. Never say "blocked" or "need permission."
- Write it down. If you learn something, save it to memory.
- Don't fabricate. Use tools to check before reporting.
- One thing at a time. Complete each piece before moving on.

## Operator
[AGENT_NAME] works for [OWNER_NAME]. [OWNER_NAME] is the human operator.
```

---

## Step 8: First Run Test

ACTION:
```bash
cd ~/my-reclaw && python3 src/main.py --dry-run 2>&1 | head -30
```

Expected output contains:
- No Python traceback errors
- Something like: "Starting ReClaw..." or "Agent initialized" or similar startup message

If you see `ModuleNotFoundError`: re-run Step 2.
If you see `discord.errors.LoginFailure`: the DISCORD_BOT_TOKEN is wrong — return to Step 6.
If you see `FileNotFoundError` for SOUL.md or USER.md: re-run the copy commands in Step 4.

Log result: `FIRST_RUN_TEST: [PASS/FAIL] — [error message if any]`

---

## Step 9: Install as systemd Service

ACTION (only if systemd is available — verified in Prerequisites):

```bash
# Copy service file
sudo cp ~/my-reclaw/systemd/openclaw.service /etc/systemd/system/reclaw.service

# Edit the service file to set correct user and path
sudo sed -i "s|/home/USER|$HOME|g" /etc/systemd/system/reclaw.service
sudo sed -i "s|User=USER|User=$USER|g" /etc/systemd/system/reclaw.service

# Reload systemd and enable
sudo systemctl daemon-reload
sudo systemctl enable reclaw.service
sudo systemctl start reclaw.service
```

VERIFY:
```bash
sudo systemctl status reclaw.service --no-pager | head -20
```

Expected: `Active: active (running)`

If WSL2 and systemd is not available, use this alternative:
```bash
# Create a startup script instead
cat > ~/start-reclaw.sh << 'EOF'
#!/bin/bash
cd ~/my-reclaw
nohup python3 src/main.py >> ~/my-reclaw/workspace/logs/agent.log 2>&1 &
echo "ReClaw started. PID: $!"
EOF
chmod +x ~/start-reclaw.sh
~/start-reclaw.sh
```

---

## Step 10: Verify Heartbeat

ACTION: Wait up to 3 minutes after startup, then check:

```bash
# Check heartbeat log
cat ~/my-reclaw/workspace/memory/heartbeat.log 2>/dev/null | tail -5

# Check agent process is running
pgrep -f "python3 src/main.py" && echo "PROCESS_RUNNING" || echo "PROCESS_NOT_FOUND"
```

Expected: The heartbeat log contains a recent `HEARTBEAT_OK` entry with a timestamp within the last 30 minutes.

If heartbeat log is empty after 5 minutes: check agent logs at `~/my-reclaw/workspace/logs/agent.log`

---

## Step 11: Seed Initial Memory

ACTION: Create the first memory files to give the agent context.

```bash
mkdir -p ~/my-reclaw/workspace/memory

# Create a tasks file
cat > ~/my-reclaw/workspace/memory/tasks.md << 'EOF'
# Open Tasks
[AGENT_NAME] was just set up. First task: introduce yourself in the Discord heartbeat channel.

## Setup Checklist
- [x] Cloned from scaffold
- [x] Dependencies installed
- [x] .env configured
- [x] USER.md personalized
- [ ] First heartbeat confirmed
- [ ] First Discord message sent
EOF

# Create a context file
cat > ~/my-reclaw/workspace/memory/setup-context.md << 'EOF'
# Setup Context
Date of installation: $(date +%Y-%m-%d)
Setup method: AGENT_SETUP.md autonomous protocol
Scaffold version: reclaw-scaffold (github.com/reclawplaybook/reclaw-scaffold)
EOF
```

---

## Setup Complete

Log the following summary:

```
RECLAW_SETUP_COMPLETE
=====================
Install path: ~/my-reclaw
Service: [systemd/manual — which was used]
Discord bot: [configured/pending]
First run test: [PASS/FAIL]
Heartbeat: [confirmed/pending]
Next step: Send a test message to your Discord server to confirm the bot is listening.
```

---

## Error Recovery

### Python version too old
```bash
# Ubuntu/Debian
sudo apt-get install -y python3.11 python3.11-pip
# Then use python3.11 instead of python3
```

### discord.py install fails
```bash
pip3 install "discord.py[voice]" --upgrade
```

### Bot not responding in Discord
1. Confirm MESSAGE CONTENT INTENT is enabled in Discord Developer Portal
2. Confirm the bot was invited to the server (OAuth2 URL from Step 5)
3. Check: `sudo journalctl -u reclaw.service -n 50` or `cat ~/my-reclaw/workspace/logs/agent.log | tail -50`

### Claude SDK connection refused (port 3456)
The Claude Code proxy is not running. This requires Claude Code to be active:
```bash
# Start Claude Code in proxy mode (separate terminal)
claude --serve --port 3456
```

### Permission denied on systemd
```bash
# Run with sudo or add user to systemd group
sudo systemctl start reclaw.service
```

### Git clone fails (network)
```bash
# Try SSH instead
git clone git@github.com:reclawplaybook/reclaw-scaffold.git ~/my-reclaw
```

---

*This protocol was designed for autonomous execution by an AI agent running the ReClaw/OpenClaw framework. If you are a human reading this: run bootstrap.py instead — it handles all of this interactively.*
