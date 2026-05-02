# ReClaw Scaffold

Working starter scaffold for the ReClaw Playbook.

## Quick Start

### Free demo mode

Use this first if you do not have Claude, ChatGPT, or an API key yet. Demo mode proves the local loop: install, memory, search, doctor checks, and canned agent replies.

**Windows:**

Download `install-windows.ps1`, right-click it, and choose **Run with PowerShell**. If Windows blocks scripts, open PowerShell and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

**macOS, Linux, or WSL2:**

```bash
curl -fsSL https://raw.githubusercontent.com/reclawplaybook/reclaw-scaffold/master/install.sh | bash
```

Choose **Demo/free test mode** when the installer asks for the AI brain.

The installer creates `~/my-reclaw`, installs Node 22 if needed, writes identity files, runs `reclaw doctor`, and starts the agent.

### Live AI mode

After the local loop works, switch to Claude Code OAuth or an Anthropic API key by setting `RECLAW_PROVIDER=claude` in `.env`.

## Manual Install

```bash
git clone https://github.com/reclawplaybook/reclaw-scaffold ~/reclaw-scaffold
cd ~/reclaw-scaffold
bash install.sh
```

## Commands

```bash
reclaw doctor
reclaw test-message "What are you?"
reclaw remember "Follow up Friday."
reclaw memory-search "Friday"
reclaw heartbeat
reclaw team-setup
reclaw start
```

## Requirements

- macOS, Linux, or WSL2
- Git
- Node.js 22+
- Claude Code OAuth or an Anthropic API key for live AI mode
- No paid AI subscription for demo mode

The installer can install Node 22 via `nvm`. Claude Code is only installed when you choose live AI mode.

## What It Includes

- Persistent Node agent
- Plain-file memory
- Claude Code prompt calls
- Scheduled heartbeats
- Discord support
- `reclaw doctor` diagnostics
- Six specialist team templates

This is intentionally small. The Playbook explains how to customize identity, memory, heartbeats, Discord, and the team.
