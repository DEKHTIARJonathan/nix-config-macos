"""Seed writable shell/editor files and restore captured Dock/Terminal preferences."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import uuid

from mac_preferences import Preferences


def terminal_keybindings(profiles):
    """Send CSI-u Shift+Enter instead of an indistinguishable plain Return."""
    return {
        name: {
            **profile,
            "keyMapBoundKeys": {
                **profile.get("keyMapBoundKeys", {}),
                "$000D": "\x1b[13;2u",  # Shift+Return
                "$0003": "\x1b[13;2u",  # Shift+keypad Enter
            },
        }
        for name, profile in profiles.items()
    }


def state_directory(home):
    return home / ".local/state/nix-macos-config"


def backup_path(home, name):
    folder = state_directory(home) / "backups"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return folder / f"{stamp}-{uuid.uuid4().hex[:8]}-{name}"


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def seed_zshrc(home, dry_run=False, *, store=Path("/nix/store")):
    """Migrate the HM symlink to a writable loader; retain app/user additions."""
    target = home / ".zshrc"
    loader = b'source "$HOME/.config/zsh/nix-zshrc"\n'
    exists = target.exists() or target.is_symlink()
    managed_link = False
    if target.is_symlink():
        link = target.readlink()
        managed_link = link.parent.parent == store and link.parent.name.endswith("-home-manager-files") and link.name == ".zshrc"
        if not managed_link:
            raise RuntimeError(f"Refusing to replace an unmanaged symlink: {target}")
    current = target.read_bytes() if exists else b""
    if not managed_link and loader in current.splitlines(keepends=True):
        print(f"Keeping {target}")
        return
    content = b"# Nix settings load first; application setup may edit this writable file.\n" + loader
    if not managed_link:
        content += current
    print(f"{'Would restore' if dry_run else 'Restoring'} writable {target}")
    if dry_run:
        return
    if exists:
        backup = backup_path(home, "zshrc")
        # Save content independently of the old Nix generation's lifetime.
        atomic_write(backup, current)
        print(f"Backup: {backup}")
    atomic_write(target, content)


def seed_editors(source, home, replace=False, dry_run=False, *, editor=None):
    files = json.loads((source / "editor-files.json").read_text())
    if editor is not None:
        name = f"{editor}-settings.json"
        files = {name: files[name]}
    for name, relative in files.items():
        target = home / relative
        exists = target.exists() or target.is_symlink()
        if exists and not replace:
            print(f"Keeping {target}")
            continue
        print(f"{'Would restore' if dry_run else 'Restoring'} {target}")
        if dry_run:
            continue
        content = (source / name).read_bytes()
        if exists:
            backup = backup_path(home, target.name)
            # Back up symlinks themselves; never write through them.
            shutil.copy2(target, backup, follow_symlinks=False)
            print(f"Backup: {backup}")
            atomic_write(target, content)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with target.open("xb") as stream:
                    stream.write(content)
            except FileExistsError:
                print(f"Keeping newly created {target}")


def dock_entries(items, applications=Path("/Applications")):
    entries = []
    for item in items:
        original = Path(item["path"])
        candidates = [original]
        if item["managed"]:
            candidates.insert(0, applications / original.name)
        selected = next((path for path in candidates if path.exists()), None)
        if selected is None:
            print(f"Skipping missing app: {item['name']} ({original})")
            continue
        entries.append({
            "tile-data": {
                "file-data": {"_CFURLString": selected.as_uri() + "/", "_CFURLStringType": 15},
                "file-label": item["name"],
                "file-type": 41,
            },
            "tile-type": "file-tile",
        })
    return entries


def restore_desktop(component, source, home, preferences, once=False, dry_run=False,
                    applications=Path("/Applications")):
    marker = state_directory(home) / f"{component}-restored"
    keep_snapshot = once and marker.exists()
    if keep_snapshot and component != "terminal":
        print(f"Keeping previously restored {component}")
        return
    domain = {"dock": "com.apple.dock", "terminal": "com.apple.Terminal"}[component]
    current = preferences.read(domain)
    if component == "dock":
        items = json.loads((source / "dock.json").read_text())
        entries = dock_entries(items, applications)
        if not entries:
            raise RuntimeError("No Dock applications found; preferences and completion marker unchanged")
        updates = {"persistent-apps": entries}
    elif keep_snapshot:
        # Profile restoration is one-time, but these two bindings are managed
        # on every activation, including profiles added after the first switch.
        profiles = terminal_keybindings(current.get("Window Settings", {}))
        if profiles == current.get("Window Settings", {}):
            print("Keeping previously restored terminal; key bindings are current")
            return
        updates = {"Window Settings": profiles}
    else:
        updates = plistlib.loads((source / "terminal.plist").read_bytes())
        updates["Window Settings"] = terminal_keybindings({
            **current.get("Window Settings", {}),
            **updates["Window Settings"],
        })
    print(f"{'Would restore' if dry_run else 'Restoring'} {component}")
    if dry_run:
        return
    backup = backup_path(home, f"{component}.plist")
    atomic_write(backup, plistlib.dumps(current, fmt=plistlib.FMT_BINARY))
    print(f"Backup: {backup}")
    preferences.write(domain, updates)
    # Persist the marker only after a successful preference write. Missing Dock
    # apps are reported but do not prevent restoring the apps that are present.
    atomic_write(marker, b"Restored; use mac-config-restore to reapply explicitly.\n")
    if component == "dock":
        subprocess.run(["/usr/bin/killall", "Dock"], check=False, capture_output=True)
    else:
        print("Terminal preferences saved; existing windows are left open. Reopen Terminal to reload.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("component", choices=["zshrc", "editors", "dock", "terminal", "all"])
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parent.parent / "settings")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--once", action="store_true", help="Skip previously restored Dock/Terminal preferences")
    parser.add_argument("--replace-existing", action="store_true", help="Back up and replace existing editor files")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry_run = args.dry_run or bool(os.environ.get("DRY_RUN"))
    if os.geteuid() == 0 and not dry_run:
        parser.error("Run as the configured user, not root")
    components = ["editors", "dock", "terminal"] if args.component == "all" else [args.component]
    failed = False
    preferences = None
    for component in components:
        try:
            if component == "zshrc":
                seed_zshrc(args.home, dry_run)
            elif component == "editors":
                seed_editors(args.source, args.home, args.replace_existing, dry_run)
            else:
                if preferences is None:
                    preferences = Preferences()
                restore_desktop(component, args.source, args.home, preferences, args.once, dry_run)
        except (OSError, ValueError, RuntimeError) as error:
            print(f"Failed to restore {component}: {error}")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
