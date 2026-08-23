#!/usr/bin/env bash
# Installs the Nexa focused-window GNOME Shell extension (user-local, no sudo).
# Needed on GNOME Wayland so that "what app am I using?" returns a real answer.
set -euo pipefail

UUID="nexa-focused-window@nexa.local"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/extensions/$UUID"
DEST="$HOME/.local/share/gnome-shell/extensions/$UUID"

if [ ! -f "$SRC/metadata.json" ] || [ ! -f "$SRC/extension.js" ]; then
  echo "error: extension sources not found under $SRC" >&2
  echo "run this script from an intact nexa checkout." >&2
  exit 1
fi

if command -v gnome-shell >/dev/null 2>&1; then
  echo "Detected: $(gnome-shell --version)"
  MAJOR="$(gnome-shell --version | grep -oE '[0-9]+' | head -1)"
  case "$MAJOR" in
    45|46|47|48|49|50) ;;
    *) echo "warning: GNOME $MAJOR isn't in this extension's supported list [45-50];" >&2
       echo "         enabling may refuse. If so, tell Nexa's maintainer to add it." >&2 ;;
  esac
else
  echo "warning: gnome-shell not found — this extension only applies to GNOME." >&2
fi

mkdir -p "$DEST"
install -m 644 "$SRC/metadata.json" "$DEST/metadata.json"
install -m 644 "$SRC/extension.js" "$DEST/extension.js"
echo "Installed to $DEST"

if gnome-extensions enable "$UUID" 2>/dev/null; then
  echo "Extension enabled. Verifying..."
else
  echo ""
  echo "GNOME only discovers new extensions at login (Wayland can't reload the shell)."
  echo "Do this once:"
  echo "  1. Log out and log back in."
  echo "  2. Run:  gnome-extensions enable $UUID"
  echo ""
fi

echo "Verify with:"
echo "  gdbus call --session --dest org.nexa.FocusedWindow --object-path /org/nexa/FocusedWindow --method org.nexa.FocusedWindow.Get"
echo "Then in Nexa:  what app am i using?"
