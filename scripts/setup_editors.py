"""Explicit marketplace setup; never called by system activation."""

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

import json5

from restore_settings import atomic_write, backup_path, seed_editors


CODE = Path("/Applications/Nix Apps/Visual Studio Code.app/Contents/Resources/app/bin/code")


def setup_code(extensions, cli=CODE, runner=subprocess.run):
    if not cli.is_file() or not os.access(cli, os.X_OK):
        raise RuntimeError(f"VS Code CLI is missing: {cli}; activate the configuration first")
    installed = runner([str(cli), "--list-extensions"], capture_output=True, text=True, check=True)
    existing = set(installed.stdout.lower().splitlines())
    failed = []
    for entry in extensions:
        name = entry["id"]
        if name.lower() in existing:
            print(f"Keeping installed VS Code extension: {name}")
            continue
        result = runner([str(cli), "--install-extension", name], check=False)
        if result.returncode:
            failed.append(name)
    if failed:
        raise RuntimeError("VS Code extensions failed: " + ", ".join(failed))


def setup_zed(extensions, home):
    target = home / ".config/zed/settings.json"
    # An explicit command may merge settings, but must not replace a symlink
    # or edit an external configuration through one.
    if target.is_symlink():
        raise RuntimeError(f"{target} is a symlink; configure auto_install_extensions in its owner")
    settings = json5.loads(target.read_text()) if target.exists() else {}
    previous = settings.get("auto_install_extensions", {})
    desired = {**previous, **{entry["id"]: True for entry in extensions}}
    if desired != previous:
        settings["auto_install_extensions"] = desired
        if target.exists():
            backup = backup_path(home, "zed-settings.json")
            shutil.copy2(target, backup)
            backup.chmod(0o600)
            print(f"Backup: {backup}")
        atomic_write(target, (json.dumps(settings, indent=2) + "\n").encode())
    print("Zed extension requests configured. Open Zed to download them; then run --verify.")


def verify_zed(extensions, home):
    installed = home / "Library/Application Support/Zed/extensions/installed"
    missing = [entry["id"] for entry in extensions if not (installed / entry["id"] / "extension.toml").is_file()]
    if missing:
        raise RuntimeError("Zed extensions not installed yet: " + ", ".join(missing))
    print("All captured Zed extensions are installed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("editor", choices=["code", "zed", "all"])
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent / "settings")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--verify", action="store_true", help="Only check whether captured extensions are installed")
    args = parser.parse_args()
    inventory = json.loads((args.source / "editor-extensions.json").read_text())
    if os.geteuid() == 0:
        parser.error("Run as the configured user, not root")
    failed = False
    for editor in (["code", "zed"] if args.editor == "all" else [args.editor]):
        try:
            if not args.verify:
                seed_editors(args.source, args.home, editor=editor)
            if editor == "zed":
                (verify_zed if args.verify else setup_zed)(inventory[editor], args.home)
            elif args.verify:
                result = subprocess.run([str(CODE), "--list-extensions"], capture_output=True, text=True, check=True)
                missing = {x["id"].lower() for x in inventory[editor]} - set(result.stdout.lower().splitlines())
                if missing:
                    raise RuntimeError("VS Code extensions missing: " + ", ".join(sorted(missing)))
                print("All captured VS Code extensions are installed")
            else:
                setup_code(inventory[editor])
        except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
            print(f"{editor}: {error}")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
