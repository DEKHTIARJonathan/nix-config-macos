#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

command -v nixfmt >/dev/null || { echo 'Run: nix develop -c bash scripts/check.sh' >&2; exit 1; }
nixfmt --check ./*.nix
statix check .
deadnix --fail .
shellcheck scripts/*.sh
python3 -B -m unittest discover -s tests -v
python3 scripts/inventory.py --check

if [[ "${1:-}" != --offline ]]; then
  for host in macbook-arm macbook-intel; do
    nix eval --no-update-lock-file --raw ".#darwinConfigurations.${host}.system.drvPath" >/dev/null
  done
  nix flake check --no-update-lock-file
fi
