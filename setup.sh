#!/bin/bash
# setup.sh — One-Command Setup Script
#
# Creates a Python virtual environment, installs all dependencies,
# and copies template files to the right places.
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# After running:
#   1. Edit .env — fill in your Discord token and Claude proxy settings
#   2. Edit workspace/USER.md — tell the agent who you are (15 min well spent)
#   3. Edit workspace/SOUL.md — give the agent its personality
#   4. Start the agent: source venv/bin/activate && python src/main.py

set -e  # Exit immediately on any error

echo "=== ReClaw Scaffold Setup ==="
echo ""

# ---------------------------------------------------------------------------
# 1. Check Python version
# ---------------------------------------------------------------------------
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "ERROR: Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
fi
echo "[1/5] Python $PYTHON_VERSION — OK"

# ---------------------------------------------------------------------------
# 2. Create virtual environment
# ---------------------------------------------------------------------------
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[2/5] Virtual environment created"
else
    echo "[2/5] Virtual environment already exists — skipping"
fi

# ---------------------------------------------------------------------------
# 3. Install dependencies
# ---------------------------------------------------------------------------
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "[3/5] Dependencies installed"

# ---------------------------------------------------------------------------
# 4. Copy .env.example → .env (if .env doesn't exist)
# ---------------------------------------------------------------------------
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[4/5] .env created from .env.example"
else
    echo "[4/5] .env already exists — not overwriting"
fi

# ---------------------------------------------------------------------------
# 5. Copy templates to workspace/ (if files don't exist)
# ---------------------------------------------------------------------------
mkdir -p workspace/memory workspace/souls workspace/skills

copy_if_missing() {
    local src="$1"
    local dst="$2"
    if [ ! -f "$dst" ]; then
        cp "$src" "$dst"
        echo "       Copied: $dst"
    else
        echo "       Exists: $dst (not overwriting)"
    fi
}

echo "[5/5] Copying templates to workspace/:"
copy_if_missing templates/SOUL.md workspace/SOUL.md
copy_if_missing templates/USER.md workspace/USER.md
copy_if_missing templates/AGENTS.md workspace/AGENTS.md
copy_if_missing templates/DIRECTIVE.md workspace/DIRECTIVE.md

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit .env         — add your Discord token and model settings"
echo "  2. Edit workspace/USER.md   — tell the agent who you are (don't skip!)"
echo "  3. Edit workspace/SOUL.md   — customize the agent's voice"
echo "  4. Run a dry-run test:"
echo "     source venv/bin/activate"
echo "     python src/main.py --dry-run"
echo "  5. Start the agent:"
echo "     python src/main.py"
echo ""
echo "See README.md for full step-by-step instructions."
