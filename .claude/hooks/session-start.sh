#!/bin/bash
set -euo pipefail

# Only run in Claude Code remote environment (web)
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo "🔧 Setting up emilybot development environment..."

# Install mise if not present
if ! command -v mise &> /dev/null; then
  echo "📦 Installing mise..."
  curl https://mise.run | sh
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "✓ mise already installed ($(mise --version))"
fi

# Install uv if not present
if ! command -v uv &> /dev/null; then
  echo "📦 Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "✓ uv already installed ($(uv --version))"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
uv sync

echo "✅ Development environment ready!"
