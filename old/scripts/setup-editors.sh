#!/usr/bin/env bash
# Explicit user action; never run from a system activation.
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-}" in
  code) editor='/Applications/Nix Apps/Visual Studio Code.app/Contents/Resources/app/bin/code' ;;
  cursor) editor='/Applications/Nix Apps/Cursor.app/Contents/Resources/app/bin/cursor' ;;
  *) echo 'Usage: bash scripts/setup-editors.sh code|cursor' >&2; exit 2 ;;
esac
[[ -x "$editor" ]] || { echo "Editor CLI not found: $editor" >&2; exit 1; }
failed=0
while IFS= read -r extension; do
  [[ -n "$extension" ]] || continue
  "$editor" --install-extension "$extension" || { echo "Install manually: $extension" >&2; failed=1; }
done < "settings/$1-extensions.txt"
exit "$failed"
