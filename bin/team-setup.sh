#!/usr/bin/env bash
set -euo pipefail

# ReClaw Playbook — AI Team Setup
# Called from install.sh or standalone via `reclaw team-setup`

ROOT="${RECLAW_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TEAM_DIR="$ROOT/team-package"
TEMPLATE_DIR="$ROOT/templates/team"
NONINTERACTIVE="${RECLAW_NONINTERACTIVE:-0}"

ask() {
  prompt="$1"
  default="${2:-}"
  if [ "$NONINTERACTIVE" = "1" ]; then
    printf '%s\n' "$default"
    return
  fi
  read -r -p "$prompt" answer
  printf '%s\n' "${answer:-$default}"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

check_paperclip() {
  if need_cmd npx && npx paperclipai --version >/dev/null 2>&1; then
    return 0
  fi
  echo "Team manager CLI not found. Installing..."
  npm install -g paperclipai 2>/dev/null || npm install -g @anthropic-ai/paperclipai 2>/dev/null || {
    echo "Could not install team manager CLI. Install it manually:"
    echo "  npm install -g paperclipai"
    echo ""
    echo "Then re-run: reclaw team-setup"
    exit 1
  }
}

check_paperclip_running() {
  local url="${PAPERCLIP_API_URL:-http://127.0.0.1:3101}"
  if curl -s --max-time 3 "$url/api" >/dev/null 2>&1; then
    return 0
  fi

  echo ""
  echo "Team manager server not detected at $url"
  echo ""
  echo "To start it:"
  echo "  npx paperclipai run"
  echo ""
  echo "Or if you haven't set it up yet:"
  echo "  npx paperclipai onboard --run"
  echo ""

  start_it="${RECLAW_START_PAPERCLIP:-$(ask "Start team manager now? [y/n] " "y")}"
  if [ "$start_it" = "y" ] || [ "$start_it" = "Y" ]; then
    echo "Starting team manager in background..."
    npx paperclipai onboard -y --run &
    PAPERCLIP_PID=$!
    echo "Waiting for team manager to start..."
    for i in $(seq 1 30); do
      if curl -s --max-time 2 "$url/api" >/dev/null 2>&1; then
        echo "Team manager is running (PID $PAPERCLIP_PID)"
        return 0
      fi
      sleep 1
    done
    echo "Team manager didn't start in 30s. Run 'npx paperclipai onboard --run' manually."
    exit 1
  else
    echo "Skipping team setup. Run 'reclaw team-setup' after starting the team manager."
    exit 0
  fi
}

select_agents() {
  echo ""
  echo "Choose which specialists to include in your team:"
  echo ""
  echo "  [1] Scout   — Research, market intel, comparisons"
  echo "  [2] Roy     — Finance, bookkeeping, taxes"
  echo "  [3] Duke    — Fitness, health tracking, workouts"
  echo "  [4] Darlene — Home management, groceries, errands"
  echo "  [5] Tank    — Engineering, code, infrastructure"
  echo "  [A] All of the above"
  echo ""

  selection="${RECLAW_TEAM_AGENTS:-$(ask "Which agents? (comma-separated, e.g. 1,2,5 or A for all) " "A")}"

  SELECTED_AGENTS="ops-ceo"  # CEO always included

  if [ "$selection" = "A" ] || [ "$selection" = "a" ]; then
    SELECTED_AGENTS="ops-ceo,scout-researcher,roy-finance,duke-fitness,darlene-home,tank-engineer"
  else
    IFS=',' read -ra choices <<< "$selection"
    for c in "${choices[@]}"; do
      c="$(echo "$c" | tr -d ' ')"
      case "$c" in
        1) SELECTED_AGENTS="$SELECTED_AGENTS,scout-researcher" ;;
        2) SELECTED_AGENTS="$SELECTED_AGENTS,roy-finance" ;;
        3) SELECTED_AGENTS="$SELECTED_AGENTS,duke-fitness" ;;
        4) SELECTED_AGENTS="$SELECTED_AGENTS,darlene-home" ;;
        5) SELECTED_AGENTS="$SELECTED_AGENTS,tank-engineer" ;;
      esac
    done
  fi

  echo ""
  echo "Selected agents: $SELECTED_AGENTS"
}

build_package() {
  echo ""
  echo "Building team package..."

  rm -rf "$TEAM_DIR"
  mkdir -p "$TEAM_DIR/agents"

  # Get user config from .env
  USER_NAME="${USER_NAME:-$(grep '^USER_NAME=' "$ROOT/.env" 2>/dev/null | cut -d= -f2 || echo "Operator")}"
  AGENT_NAME="${AGENT_NAME:-$(grep '^AGENT_NAME=' "$ROOT/.env" 2>/dev/null | cut -d= -f2 || echo "ReClaw")}"
  CLAUDE_TIER="${CLAUDE_TIER:-$(grep '^CLAUDE_TIER=' "$ROOT/.env" 2>/dev/null | cut -d= -f2 || echo "pro")}"

  # Determine model and heartbeat based on tier
  case "$CLAUDE_TIER" in
    max20x) AGENT_MODEL="claude-sonnet-4-6"; HEARTBEAT_SEC=900 ;;
    max5x)  AGENT_MODEL="claude-sonnet-4-6"; HEARTBEAT_SEC=1800 ;;
    *)      AGENT_MODEL="claude-sonnet-4-6"; HEARTBEAT_SEC=3600 ;;
  esac

  TEAM_NAME="${RECLAW_TEAM_NAME:-$(ask "Team name? " "${USER_NAME}'s AI Team")}"

  # Process .paperclip.yaml — filter to selected agents
  local yaml_src="$TEMPLATE_DIR/.paperclip.yaml"

  # Simple template rendering
  sed \
    -e "s/{{TEAM_NAME}}/${TEAM_NAME//\//\\/}/g" \
    -e "s/{{USER_NAME}}/${USER_NAME//\//\\/}/g" \
    -e "s/{{AGENT_NAME}}/${AGENT_NAME//\//\\/}/g" \
    -e "s/{{AGENT_MODEL}}/${AGENT_MODEL//\//\\/}/g" \
    -e "s/{{HEARTBEAT_SEC}}/$HEARTBEAT_SEC/g" \
    "$yaml_src" > "$TEAM_DIR/.paperclip.yaml"

  # Copy selected agent AGENTS.md files
  IFS=',' read -ra agents <<< "$SELECTED_AGENTS"
  for agent in "${agents[@]}"; do
    agent="$(echo "$agent" | tr -d ' ')"
    if [ -d "$TEMPLATE_DIR/agents/$agent" ]; then
      mkdir -p "$TEAM_DIR/agents/$agent"
      for f in "$TEMPLATE_DIR/agents/$agent"/*; do
        [ -f "$f" ] || continue
        sed \
          -e "s/{{USER_NAME}}/${USER_NAME//\//\\/}/g" \
          -e "s/{{AGENT_NAME}}/${AGENT_NAME//\//\\/}/g" \
          "$f" > "$TEAM_DIR/agents/$agent/$(basename "$f")"
      done
    fi
  done

  echo "Package built at $TEAM_DIR"
}

import_team() {
  echo ""
  echo "Importing team..."

  local api_url="${PAPERCLIP_API_URL:-http://127.0.0.1:3101}"

  npx paperclipai company import "$TEAM_DIR" \
    --target new \
    --new-company-name "$TEAM_NAME" \
    --include company,agents \
    --yes \
    --api-base "$api_url" \
    2>&1

  import_status=$?
  if [ $import_status -eq 0 ]; then
    echo ""
    echo "Team imported successfully!"
    echo ""
    echo "Your agents are ready. To connect them:"
    echo ""
    echo "  1. Open the team dashboard: ${PAPERCLIP_UI_URL:-http://localhost:3100}"
    echo "  2. Find your team: '$TEAM_NAME'"
    echo "  3. Each agent needs a local CLI adapter — run:"
    echo "     npx paperclipai agent local-cli <agent-name> --company-id <id>"
    echo ""
    echo "  Or let the CEO agent manage the team by triggering its heartbeat:"
    echo "     npx paperclipai heartbeat run --agent-id <ceo-agent-id>"
    echo ""
  else
    echo ""
    echo "Import failed. You can retry with:"
    echo "  reclaw team-setup"
    echo ""
    echo "Or import manually:"
    echo "  npx paperclipai company import $TEAM_DIR --target new --yes"
  fi
}

main() {
  echo ""
  echo "═══════════════════════════════════════════"
  echo "  ReClaw Playbook — Team Setup"
  echo "═══════════════════════════════════════════"
  echo ""
  echo "This sets up your AI team"
  echo "with specialist agents for your key domains."
  echo ""

  check_paperclip
  check_paperclip_running
  select_agents
  build_package
  import_team

  echo "Done! Your AI team is ready."
}

main "$@"
