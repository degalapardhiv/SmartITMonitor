#!/usr/bin/env bash
# Smart IT Monitor - agent onboarding for endpoint machines.
#
# Usage:
#   ./deploy.sh http://<SERVER_LAN_IP>:8000
#   ./deploy.sh http://<SERVER_LAN_IP>:8000 --service   # also install a systemd unit
#
# This script:
#   1. Detects this machine's hostname, primary IPv4 and OS.
#   2. Registers it with the backend (POST /agent/register).
#   3. Writes agent/.agent.env with the returned device id/token + LAN-tuned
#      real-time intervals (see agent/.agent.env.example).
#   4. Optionally installs a systemd service and starts the agent.
#
# Run this once on every endpoint behind your switches.

set -euo pipefail

SERVER_URL="${1:-}"
if [[ -z "$SERVER_URL" ]]; then
    echo "Usage: $0 <SERVER_LAN_IP_OR_URL> [--service]" >&2
    echo "Example: $0 http://10.0.0.10:8000" >&2
    exit 1
fi
SERVER_URL="${SERVER_URL%/}"

INSTALL_SERVICE=0
if [[ "${2:-}" == "--service" ]]; then
    INSTALL_SERVICE=1
fi

AGENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$AGENT_DIR")"

# --- Detect identity --------------------------------------------------------
HOSTNAME="$(hostname)"

OS_DETECTED="$(uname -s)-$(uname -m)"
if [[ -f /etc/os-release ]]; then
    OS_DETECTED="$(grep PRETTY_NAME /etc/os-release | cut -d= -f2 | tr -d '"')"
fi

IP=""
if command -v hostname >/dev/null 2>&1; then
    IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
fi
if [[ -z "$IP" ]]; then
    IP="$(ip -o -4 addr show scope global 2>/dev/null | awk '{print $4}' | head -1 | cut -d/ -f1 || true)"
fi
if [[ -z "$IP" ]]; then
    echo "Could not detect the primary IPv4 address." >&2
    exit 1
fi

echo "Registering: hostname=$HOSTNAME ip=$IP os=$OS_DETECTED"
echo "Server: $SERVER_URL"

# --- Register with the backend ---------------------------------------------
REGISTER_JSON="$(python3 - "$HOSTNAME" "$IP" "$OS_DETECTED" <<'EOF'
import json, sys
print(json.dumps({"hostname": sys.argv[1], "ip": sys.argv[2], "os": sys.argv[3]}))
EOF
)"

RESP="$(curl -sf -X POST "$SERVER_URL/agent/register" \
    -H "Content-Type: application/json" \
    -d "$REGISTER_JSON" \
    || { echo "Registration failed. Is the server reachable at $SERVER_URL?" >&2; exit 1; })"

DEVICE_ID="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['device_id'])" "$RESP")"
AGENT_TOKEN="$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['agent_token'])" "$RESP")"

echo "Registered: device_id=$DEVICE_ID"

# --- Write agent/.agent.env (LAN-tuned, real-time) -------------------------
cat > "$AGENT_DIR/.agent.env" <<EOF
SMARTIT_API_URL=$SERVER_URL
SMARTIT_DEVICE_ID=$DEVICE_ID
SMARTIT_AGENT_TOKEN=$AGENT_TOKEN
SMARTIT_DEPARTMENT=Unknown
SMARTIT_LAB=Unknown
SMARTIT_LOCATION=Unknown
SMARTIT_INTERVAL=5
SMARTIT_NETWORK_DISCOVERY_INTERVAL=60
SMARTIT_DEPLOYMENT_POLL_INTERVAL=15
SMARTIT_ACTIVITY_INTERVAL=30
SMARTIT_SOFTWARE_POLL_INTERVAL=30
SMARTIT_WEB_ACCESS_POLL_INTERVAL=15
EOF
chmod 600 "$AGENT_DIR/.agent.env"

echo "Wrote $AGENT_DIR/.agent.env"
echo "NOTE: set SMARTIT_NETWORK_RANGES there if endpoints span multiple subnets/VLANs."
echo "NOTE: set SMARTIT_REBOOT_CMD for OS-deployment reimaging (e.g. systemctl reboot)."

# --- Python venv for the agent ---------------------------------------------
PYTHON_BIN="$REPO_ROOT/.venv-agent/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
    PYTHON_BIN="$(command -v python3)"
fi
echo "Installing agent dependencies into venv..."
"$PYTHON_BIN" -m venv "$REPO_ROOT/.venv-agent" 2>/dev/null || true
"$REPO_ROOT/.venv-agent/bin/pip" install -q -r "$AGENT_DIR/requirements.txt" 2>/dev/null || \
    echo "warning: could not install requirements (check network) - run.sh will use existing venv"

if [[ "$INSTALL_SERVICE" -eq 1 ]]; then
    UNIT="/etc/systemd/system/smartit-agent.service"
    cat > "$UNIT" <<EOF
[Unit]
Description=Smart IT Monitor Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=$AGENT_DIR/.agent.env
WorkingDirectory=$AGENT_DIR
ExecStart=$REPO_ROOT/.venv-agent/bin/python $AGENT_DIR/smartit_agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable smartit-agent
    systemctl restart smartit-agent
    echo "Installed and started systemd unit: smartit-agent.service"
else
    echo "Next: start the agent with:  bash $AGENT_DIR/run.sh"
fi

echo "Onboarding complete for $HOSTNAME (device_id=$DEVICE_ID)."