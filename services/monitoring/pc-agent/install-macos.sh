#!/bin/bash
# install-macos.sh — deploy the metric agent as a launchd user agent.
#
# macOS TCC blocks launchd-spawned processes from running code under
# ~/Desktop, ~/Documents, ~/Downloads. This repo often lives in one of those,
# so we deploy a self-contained copy to ~/Library/Application Support and point
# launchd at that. Re-run this script after changing agent.py or the config.
#
# Config: uses config.local.yaml if present, else config.yaml.

set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HOME/Library/Application Support/homelab-metric-agent"
PLIST="$HOME/Library/LaunchAgents/com.homelab.metricagent.plist"
LABEL="com.homelab.metricagent"
LOG="$HOME/Library/Logs/homelab-metric-agent.log"

CONFIG_SRC="$SRC_DIR/config.yaml"
[ -f "$SRC_DIR/config.local.yaml" ] && CONFIG_SRC="$SRC_DIR/config.local.yaml"
echo "Config source: $CONFIG_SRC"

command -v python3 >/dev/null || { echo "python3 not found (brew install python)"; exit 1; }

mkdir -p "$APP_DIR"
cp "$SRC_DIR/agent.py" "$SRC_DIR/requirements.txt" "$APP_DIR/"
cp "$CONFIG_SRC" "$APP_DIR/config.yaml"

if [ ! -d "$APP_DIR/.venv" ]; then
    echo "Creating venv..."
    python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

PYBIN="$APP_DIR/.venv/bin/python3"

mkdir -p "$(dirname "$PLIST")" "$(dirname "$LOG")"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYBIN</string>
        <string>$APP_DIR/agent.py</string>
        <string>-c</string>
        <string>$APP_DIR/config.yaml</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>ProcessType</key><string>Background</string>
    <key>StandardOutPath</key><string>$LOG</string>
    <key>StandardErrorPath</key><string>$LOG</string>
</dict>
</plist>
PLISTEOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"

echo "Loaded $LABEL. Logs: $LOG"
sleep 3
launchctl list | grep "$LABEL" || true
