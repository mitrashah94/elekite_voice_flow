#!/bin/bash
# VoiceFlow launcher
# Usage: ./start.sh [--cli] [--settings]

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ "$1" = "--settings" ]; then
    python3 "$SCRIPT_DIR/settings_gui.py"
elif [ "$1" = "--cli" ]; then
    python3 "$SCRIPT_DIR/voiceflow.py" --cli
else
    python3 "$SCRIPT_DIR/voiceflow.py"
fi
