#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${RECLAW_REPO_URL:-https://github.com/reclawplaybook/reclaw-scaffold.git}"
INSTALL_DIR="${RECLAW_INSTALL_DIR:-$HOME/my-reclaw}"
NONINTERACTIVE="${RECLAW_NONINTERACTIVE:-0}"
START_AGENT="${RECLAW_START:-1}"

detect_os() {
  case "$(uname -s)" in
    Darwin) echo "macos" ;;
    Linux)
      if grep -qi microsoft /proc/version 2>/dev/null; then echo "wsl2"; else echo "linux"; fi
      ;;
    *) echo "unknown" ;;
  esac
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_git_hint() {
  os="$1"
  if need_cmd git; then return 0; fi
  echo "git is required."
  if [ "$os" = "macos" ]; then
    echo "Install Xcode Command Line Tools with: xcode-select --install"
  else
    echo "Install git with: sudo apt update && sudo apt install -y git"
  fi
  exit 1
}

ensure_node() {
  if need_cmd node && [ "$(node -p "Number(process.versions.node.split('.')[0])")" -ge 22 ]; then
    return 0
  fi

  echo "Installing Node.js 22 via nvm..."
  export NVM_DIR="$HOME/.nvm"
  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
  fi
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"
  nvm install 22
  nvm use 22
}

ensure_claude() {
  if need_cmd claude; then return 0; fi
  echo "Installing Claude Code CLI..."
  npm install -g @anthropic-ai/claude-code
}

copy_scaffold() {
  mkdir -p "$INSTALL_DIR"
  if [ -f "$(pwd)/package.json" ] && [ -d "$(pwd)/src" ]; then
    copy_tree "$(pwd)" "$INSTALL_DIR"
  else
    tmp="$(mktemp -d)"
    git clone --depth 1 "$REPO_URL" "$tmp"
    copy_tree "$tmp" "$INSTALL_DIR"
    rm -rf "$tmp"
  fi
}

copy_tree() {
  src="$1"
  dest="$2"
  if need_cmd rsync; then
    rsync -a --exclude .git --exclude node_modules "$src/" "$dest/"
  else
    (cd "$src" && tar --exclude .git --exclude node_modules -cf - .) | (cd "$dest" && tar -xf -)
  fi
}

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

tier_minutes() {
  case "$1" in
    max20x|3) echo 15 ;;
    max5x|2) echo 30 ;;
    *) echo 60 ;;
  esac
}

tier_name() {
  case "$1" in
    max20x|3) echo "max20x" ;;
    max5x|2) echo "max5x" ;;
    *) echo "pro" ;;
  esac
}

render_template() {
  src="$1"
  dest="$2"
  sed \
    -e "s/{{AGENT_NAME}}/${AGENT_NAME//\//\\/}/g" \
    -e "s/{{USER_NAME}}/${USER_NAME//\//\\/}/g" \
    -e "s/{{USER_WORK}}/${USER_WORK//\//\\/}/g" \
    "$src" > "$dest"
}

main() {
  os="$(detect_os)"
  echo "ReClaw installer starting ($os)"
  install_git_hint "$os"
  ensure_node
  ensure_claude
  copy_scaffold

  cd "$INSTALL_DIR"
  npm install

  USER_NAME="${RECLAW_USER_NAME:-$(ask "What's your name? " "Operator")}"
  USER_WORK="${RECLAW_USER_WORK:-$(ask "What do you do? (one sentence) " "I run work that needs reliable follow-through.")}"
  tier_answer="${RECLAW_TIER:-$(ask "Which Claude tier? [1] Pro \$20/mo [2] Max 5x \$100/mo [3] Max 20x \$200/mo " "1")}"
  CLAUDE_TIER="$(tier_name "$tier_answer")"
  HEARTBEAT_INTERVAL="$(tier_minutes "$tier_answer")"
  api_key="${ANTHROPIC_API_KEY:-$(ask "Paste your Anthropic API key (or press Enter to use Claude Code OAuth): " "")}"
  connect_discord="${RECLAW_CONNECT_DISCORD:-$(ask "Connect Discord? [y/n] " "n")}"
  discord_token=""
  if [ "$connect_discord" = "y" ] || [ "$connect_discord" = "Y" ]; then
    discord_token="${DISCORD_BOT_TOKEN:-$(ask "Paste your Discord bot token: " "")}"
  fi
  AGENT_NAME="${RECLAW_AGENT_NAME:-ReClaw}"

  render_template templates/SOUL.md SOUL.md
  render_template templates/USER.md USER.md
  render_template templates/DIRECTIVE.md DIRECTIVE.md
  cp templates/AGENTS.md AGENTS.md
  mkdir -p memory

  node bin/write-env.mjs .env \
    "AGENT_NAME=$AGENT_NAME" \
    "USER_NAME=$USER_NAME" \
    "USER_WORK=$USER_WORK" \
    "CLAUDE_TIER=$CLAUDE_TIER" \
    "HEARTBEAT_INTERVAL=$HEARTBEAT_INTERVAL" \
    "HEARTBEAT_ON_START=false" \
    "ANTHROPIC_API_KEY=$api_key" \
    "DISCORD_BOT_TOKEN=$discord_token" \
    "DISCORD_CHANNEL_ID=" \
    "RECLAW_HOME=$INSTALL_DIR" \
    "MEMORY_DIR=memory" \
    "LOG_LEVEL=info"

  mkdir -p "$HOME/.local/bin"
  ln -sf "$INSTALL_DIR/bin/reclaw" "$HOME/.local/bin/reclaw"
  chmod +x "$INSTALL_DIR/bin/reclaw" "$INSTALL_DIR/bin/write-env.mjs" "$INSTALL_DIR/reclaw-doctor.sh"

  echo
  echo "Running reclaw doctor..."
  if ! RECLAW_HOME="$INSTALL_DIR" bash reclaw-doctor.sh; then
    echo "Doctor found issues. Fix them, then run: reclaw doctor"
    exit 1
  fi

  echo
  echo "ReClaw installed at $INSTALL_DIR"
  echo

  # ── AI Team Setup ──
  setup_team="${RECLAW_SETUP_TEAM:-$(ask "Set up an AI team? (specialist agents for research, finance, fitness, home, engineering) [y/n] " "y")}"
  if [ "$setup_team" = "y" ] || [ "$setup_team" = "Y" ]; then
    chmod +x "$INSTALL_DIR/bin/team-setup.sh"
    USER_NAME="$USER_NAME" AGENT_NAME="$AGENT_NAME" CLAUDE_TIER="$CLAUDE_TIER" \
      RECLAW_HOME="$INSTALL_DIR" bash "$INSTALL_DIR/bin/team-setup.sh"
  else
    echo "Skipped team setup. You can run it later with: reclaw team-setup"
  fi

  echo
  echo "Next: talk to it with 'reclaw test-message \"hello\"' or start it with 'reclaw start'."
  if [ "$START_AGENT" = "1" ]; then
    exec "$INSTALL_DIR/bin/reclaw" start
  fi
}

main "$@"
