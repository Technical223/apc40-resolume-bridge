#!/bin/sh
# Native Finder entry point. No terminal window, sudo, or security changes.
BASE=$(CDPATH= cd -- "$(dirname -- "$0")/../Resources" && pwd) || exit 1
DATA="$HOME/Library/Application Support/APC40 Bridge macOS Preview"
mkdir -p "$DATA" || exit 1
PYTHON=""
for candidate in /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if [ -x "$candidate" ] && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    STAGE=$(mktemp -d "$DATA/bootstrap-report.XXXXXX") || exit 1
    {
        printf 'APC40 macOS Preview: Python 3.9+ not found. Install Python from python.org, then open the preview again.\n'
        /usr/bin/sw_vers
        /usr/bin/uname -m
    } > "$STAGE/bootstrap.log"
    cp "$STAGE/bootstrap.log" "$DATA/bootstrap.log"
    EXPORT="$HOME/Desktop"
    if [ ! -d "$EXPORT" ] || [ ! -w "$EXPORT" ]; then EXPORT="$DATA/reports"; mkdir -p "$EXPORT"; fi
    ZIP="$EXPORT/APC40-macOS-debug-bootstrap-$(date +%Y%m%d-%H%M%S)-$$.zip"
    /usr/bin/ditto -c -k --keepParent "$STAGE" "$ZIP"
    /usr/bin/osascript - "$ZIP" <<'APPLESCRIPT'
on run argv
    display dialog ("Python 3.9 or newer is required. Install the macOS Python package from python.org, then reopen this app. No system settings were changed.\n\nBootstrap diagnostics: " & item 1 of argv) with title "APC40 Bridge macOS Preview" buttons {"OK"} default button "OK"
end run
APPLESCRIPT
    exit 1
fi
exec "$PYTHON" "$BASE/mac_bridge.py" >> "$DATA/bootstrap.log" 2>&1
