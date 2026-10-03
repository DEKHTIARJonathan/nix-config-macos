#!/usr/bin/env python3
"""Seed writable editor preferences without overwriting existing files."""
import argparse
import json
from pathlib import Path


def seed(source, home, flutter):
    files = {
        "code-settings.json": "Library/Application Support/Code/User/settings.json",
        "cursor-settings.json": "Library/Application Support/Cursor/User/settings.json",
        "cursor-keybindings.json": "Library/Application Support/Cursor/User/keybindings.json",
        "zed-settings.jsonc": ".config/zed/settings.json",
    }
    for name, destination in files.items():
        target = home / destination
        # Include dangling symlinks: they are existing user configuration too.
        if target.exists() or target.is_symlink():
            print(f"Keeping {target}")
            continue
        text = (source / name).read_text()
        if name == "code-settings.json":
            value = json.loads(text)
            value["dart.flutterSdkPath"] = str(flutter)
            text = json.dumps(value, indent=2) + "\n"
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("x") as stream:
                stream.write(text)
            print(f"Seeded {target}")
        except FileExistsError:
            print(f"Keeping {target}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--flutter", type=Path, required=True)
    args = parser.parse_args()
    seed(args.source, args.home, args.flutter)
