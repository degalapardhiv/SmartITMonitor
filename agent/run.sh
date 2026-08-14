#!/bin/bash
set -euo pipefail

# Resolve the repo root (this script lives in agent/).
AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$AGENT_DIR")"
cd "$REPO_ROOT"

# Load agent environment if present (agent/.agent.env or repo-root .agent.env).
if [[ -f "$AGENT_DIR/.agent.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$AGENT_DIR/.agent.env"
    set +a
elif [[ -f "$REPO_ROOT/.agent.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$REPO_ROOT/.agent.env"
    set +a
fi

# Defaults (each is overridable via the environment or .agent.env).
export SMARTIT_API_URL="${SMARTIT_API_URL:-http://127.0.0.1:8000}"
export SMARTIT_DEVICE_ID="${SMARTIT_DEVICE_ID:-}"
export SMARTIT_AGENT_TOKEN="${SMARTIT_AGENT_TOKEN:-}"
export SMARTIT_INTERVAL="${SMARTIT_INTERVAL:-5}"

if [[ -z "$SMARTIT_DEVICE_ID" ]]; then
    echo "run.sh: SMARTIT_DEVICE_ID is not set." >&2
    echo "run.sh: Register the device via POST /agent/register or the admin UI," >&2
    echo "run.sh: then set SMARTIT_DEVICE_ID and SMARTIT_AGENT_TOKEN in agent/.agent.env." >&2
    exit 1
fi

if [[ -z "$SMARTIT_AGENT_TOKEN" ]]; then
    echo "run.sh: warning: SMARTIT_AGENT_TOKEN is not set." >&2
    echo "run.sh: The backend will reject metric submissions without it." >&2
fi

PYTHON_BIN="$REPO_ROOT/.venv-agent/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "run.sh: warning: .venv-agent not found, falling back to python3." >&2
    PYTHON_BIN="python3"
fi

exec "$PYTHON_BIN" -u "$AGENT_DIR/smartit_agent.py"
