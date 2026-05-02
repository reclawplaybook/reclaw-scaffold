#!/usr/bin/env bash
set -u

ROOT="${RECLAW_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
cd "$ROOT" || exit 1

required_fail=0
required_total=0
required_pass=0
optional_total=0
optional_pass=0
source_mode=0

pass() { printf '✓ %s\n' "$1"; }
fail() { printf '✗ %s\n' "$1"; }
skip() { printf '%s\n' "- $1"; }

required() {
  required_total=$((required_total + 1))
  if "$@"; then
    required_pass=$((required_pass + 1))
    return 0
  fi
  required_fail=$((required_fail + 1))
  return 1
}

optional() {
  optional_total=$((optional_total + 1))
  if "$@"; then
    optional_pass=$((optional_pass + 1))
    return 0
  fi
  return 1
}

check_node() {
  if ! command -v node >/dev/null 2>&1; then
    fail "Node.js is not installed"
    return 1
  fi
  major="$(node -p "Number(process.versions.node.split('.')[0])")"
  if [ "$major" -lt 22 ]; then
    fail "Node.js v22+ required (found $(node -v))"
    return 1
  fi
  pass "Node.js installed ($(node -v))"
}

check_claude() {
  if command -v claude >/dev/null 2>&1; then
    pass "Claude Code CLI installed ($(claude --version 2>/dev/null | head -1))"
    return 0
  fi
  fail "Claude Code CLI is not installed"
  return 1
}

check_auth() {
  if [ -n "${ANTHROPIC_API_KEY:-}" ] || grep -q '^ANTHROPIC_API_KEY=.' .env 2>/dev/null; then
    pass "Anthropic API key configured"
    return 0
  fi
  if command -v claude >/dev/null 2>&1 && claude auth status >/dev/null 2>&1; then
    pass "Claude Code OAuth configured"
    return 0
  fi
  fail "Configure ANTHROPIC_API_KEY or run 'claude auth'"
  return 1
}

check_templates() {
  if [ ! -s AGENTS.md ] && [ -s templates/AGENTS.md ] && [ -s templates/SOUL.md ] && [ -s templates/USER.md ] && [ -s templates/DIRECTIVE.md ] && [ -s templates/.env.example ]; then
    source_mode=1
    pass "Scaffold templates exist"
    return 0
  fi

  missing=0
  for file in AGENTS.md SOUL.md USER.md DIRECTIVE.md .env; do
    if [ ! -s "$file" ]; then
      missing=1
      fail "Missing $file"
    fi
  done
  [ "$missing" -eq 0 ] && pass "Template files exist" && return 0
  return 1
}

check_memory() {
  if [ "$source_mode" -eq 1 ]; then
    tmp_memory="$(mktemp -d)"
    if test -w "$tmp_memory"; then
      rm -rf "$tmp_memory"
      pass "Temporary memory directory is writable"
      return 0
    fi
    rm -rf "$tmp_memory"
    fail "Temporary memory directory is not writable"
    return 1
  fi

  mkdir -p memory || return 1
  testfile="memory/.doctor-test"
  if printf 'ok\n' > "$testfile" && grep -q ok "$testfile"; then
    rm -f "$testfile"
    pass "Memory directory exists and is writable"
    return 0
  fi
  fail "Memory directory is not writable"
  return 1
}

check_agent_syntax() {
  if node --check src/main.js >/dev/null && node --check src/memory.js >/dev/null && node --check src/heartbeat.js >/dev/null && node --check src/config.js >/dev/null && node --check bin/write-env.mjs >/dev/null; then
    pass "Agent source passes syntax checks"
    return 0
  fi
  fail "Agent source syntax check failed"
  return 1
}

check_agent_response() {
  tmp_memory="$(mktemp -d)"
  if MEMORY_DIR="$tmp_memory" RECLAW_TEST_MODE=true node src/main.js --test-message "doctor ping" | grep -q "doctor ping"; then
    rm -rf "$tmp_memory"
    pass "Agent responds to a test message"
    return 0
  fi
  rm -rf "$tmp_memory"
  fail "Agent did not respond to a test message"
  return 1
}

check_memory_commands() {
  tmp_memory="$(mktemp -d)"
  if MEMORY_DIR="$tmp_memory" RECLAW_TEST_MODE=true node src/main.js --remember "doctor TODO memory check" >/dev/null \
    && MEMORY_DIR="$tmp_memory" RECLAW_TEST_MODE=true node src/main.js --memory-search "doctor TODO memory check" | grep -q "doctor TODO memory check"; then
    rm -rf "$tmp_memory"
    pass "Memory commands write and search notes"
    return 0
  fi
  rm -rf "$tmp_memory"
  fail "Memory commands failed"
  return 1
}

check_claude_call() {
  if [ "${RECLAW_SKIP_CLAUDE_TEST:-}" = "1" ]; then
    skip "Claude live API test skipped by RECLAW_SKIP_CLAUDE_TEST=1"
    return 0
  fi
  if timeout 45 claude -p --output-format text "Reply with exactly RECLAW_OK." 2>/tmp/reclaw-claude-test.err | grep -q "RECLAW_OK"; then
    pass "Agent can make a Claude Code test call"
    return 0
  fi
  fail "Claude Code test call failed ($(tr '\n' ' ' </tmp/reclaw-claude-test.err | cut -c1-160))"
  return 1
}

check_discord() {
  if grep -q '^DISCORD_BOT_TOKEN=.' .env 2>/dev/null || [ -n "${DISCORD_BOT_TOKEN:-}" ]; then
    pass "Discord bot token configured"
    return 0
  fi
  skip "Discord bot not configured (optional)"
  return 1
}

required check_node
required check_claude
required check_auth
required check_templates
required check_memory
required check_agent_syntax
required check_agent_response
required check_memory_commands
required check_claude_call
check_paperclip() {
  if command -v npx >/dev/null 2>&1 && npx paperclipai --version >/dev/null 2>&1; then
    local version
    version="$(npx paperclipai --version 2>/dev/null | head -1)"
    pass "Team manager CLI installed ($version)"
    return 0
  fi
  skip "Team manager CLI not installed (optional — needed for team setup)"
  return 1
}

check_paperclip_running() {
  local url="${PAPERCLIP_API_URL:-http://127.0.0.1:3101}"
  if curl -s --max-time 3 "$url/api" >/dev/null 2>&1; then
    pass "Team manager running at $url"
    return 0
  fi
  skip "Team manager not running (optional — start with: npx paperclipai run)"
  return 1
}

check_team_package() {
  if [ -d "$ROOT/templates/team" ] && [ -s "$ROOT/templates/team/.paperclip.yaml" ]; then
    local agent_count
    agent_count="$(find "$ROOT/templates/team/agents" -name 'AGENTS.md' 2>/dev/null | wc -l)"
    pass "Team package exists ($agent_count agent templates)"
    return 0
  fi
  skip "Team package not found (optional)"
  return 1
}

optional check_discord
optional check_paperclip
optional check_paperclip_running
optional check_team_package

printf '\n%d/%d required checks passed, %d/%d optional checks passed\n' "$required_pass" "$required_total" "$optional_pass" "$optional_total"

if [ "$required_fail" -eq 0 ]; then
  exit 0
fi
exit 1
