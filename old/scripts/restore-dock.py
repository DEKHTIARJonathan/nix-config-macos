#!/usr/bin/env python3
"""Restore the captured Dock order after installing apps; omit missing apps."""
import json
import plistlib
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parent.parent
apps = json.loads((root / "settings/dock.json").read_text())
entries = []
for item in apps:
    path = Path(item["path"])
    if not path.exists():
        print(f"Skipping missing app: {path}")
        continue
    entries.append({
        "tile-data": {
            "file-data": {"_CFURLString": path.as_uri() + "/", "_CFURLStringType": 15},
            "file-label": item["name"],
            "file-type": 41,
        },
        "tile-type": "file-tile",
    })
if not entries:
    raise SystemExit("No applications found; Dock was not changed.")
# Preserve every other preference: defaults import can replace the whole domain.
current = subprocess.run(
    ["defaults", "export", "com.apple.dock", "-"], capture_output=True, check=True
)
domain = plistlib.loads(current.stdout)
domain["persistent-apps"] = entries
data = plistlib.dumps(domain)
subprocess.run(["defaults", "import", "com.apple.dock", "-"], input=data, check=True)
subprocess.run(["killall", "Dock"], check=False)
