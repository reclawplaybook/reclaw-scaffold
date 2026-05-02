# ReClaw Scaffold

Working starter scaffold for the ReClaw Playbook.

## Quick Start

```bash
curl -fsSL https://raw.githubusercontent.com/reclawplaybook/reclaw-scaffold/master/install.sh | bash
```

The installer creates `~/my-reclaw`, installs Node 22 if needed, installs Claude Code, writes identity files, runs `reclaw doctor`, and starts the agent.

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
- Claude Code OAuth or an Anthropic API key

The installer can install Node 22 via `nvm` and Claude Code via `npm`.

## What It Includes

- Persistent Node agent
- Plain-file memory
- Claude Code prompt calls
- Scheduled heartbeats
- Discord support
- `reclaw doctor` diagnostics
- Six specialist team templates

This is intentionally small. The Playbook explains how to customize identity, memory, heartbeats, Discord, and the team.
