"""Install writable vendor app bundles, preserving self-updates on later rebuilds."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
import zipfile


@contextmanager
def unpack(entry):
    root = Path(tempfile.mkdtemp(prefix="mac-config-app-"))
    mount = None
    try:
        if entry["format"] == "dmg":
            candidate = root / "mount"
            candidate.mkdir()
            subprocess.run(["/usr/bin/hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", str(candidate), entry["source"]], check=True)
            mount = candidate
            yield mount / entry.get("appPath", entry["appName"])
        elif entry["format"] == "zip":
            subprocess.run(["/usr/bin/ditto", "-xk", entry["source"], str(root)], check=True)
            yield root / entry.get("appPath", entry["appName"])
        else:
            raise ValueError(f"Unsupported app format: {entry['format']}")
    finally:
        if mount is not None:
            try:
                subprocess.run(["/usr/bin/hdiutil", "detach", str(mount)], check=True)
            except subprocess.SubprocessError:
                print(f"Image remains mounted at {mount}; detach it before removing {root}")
                raise
        shutil.rmtree(root)


def archive_bundle(source, backups):
    """Keep a verified native ZIP outside vendor bundle discovery/relocation."""
    backups.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = backups / f"{source.name}.{stamp}-{uuid.uuid4().hex[:8]}.zip.bckp"
    with tempfile.TemporaryDirectory(prefix=".archive-", dir=backups) as directory:
        staged = Path(directory) / "bundle.zip"
        subprocess.run(["/usr/bin/ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                        "--rsrc", "--extattr", str(source), str(staged)], check=True)
        with zipfile.ZipFile(staged) as archive:
            if not archive.namelist() or archive.testzip() is not None:
                raise RuntimeError(f"Invalid app backup: {source}")
        staged.chmod(0o600)
        os.replace(staged, backup)
    print(f"Backup: {backup}")
    return backup


def install_bundle(source, destination, backups, replace=False, remove_finder_info=False,
                   remove_quarantine=False):
    """Stage a complete native copy before moving the old bundle to its backup."""
    if destination.exists() or destination.is_symlink():
        if not replace:
            print(f"Keeping installed app: {destination}")
            return
    info = plistlib.loads((source / "Contents/Info.plist").read_bytes())
    if not info.get("CFBundleIdentifier"):
        raise ValueError(f"Missing bundle identifier: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".mac-config-", dir=destination.parent) as directory:
        staged = Path(directory) / destination.name
        subprocess.run(["/usr/bin/ditto", "--rsrc", "--extattr", str(source), str(staged)], check=True)
        if remove_finder_info:
            # Preserve quarantine and detached code-signing attributes.
            subprocess.run(["/usr/bin/xattr", "-dr", "com.apple.FinderInfo", str(staged)], check=True)
        if remove_quarantine:
            subprocess.run(["/usr/bin/xattr", "-dr", "com.apple.quarantine", str(staged)], check=True)
        # Read-only source images must not disable the installed app's updater.
        for root, directories, files in os.walk(staged):
            for path in [Path(root), *(Path(root) / name for name in directories + files)]:
                if not path.is_symlink():
                    path.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IWUSR)
        backup = None
        if destination.exists() or destination.is_symlink():
            if not replace:
                print(f"Keeping newly installed app: {destination}")
                return
            backups.mkdir(parents=True, exist_ok=True, mode=0o700)
            if backups.stat().st_dev != destination.parent.stat().st_dev:
                raise RuntimeError("App backups must be on the same filesystem as /Applications for atomic replacement")
            quit_running_app(destination)
            archive_bundle(destination, backups)
            backup = backups / f".retired-{uuid.uuid4().hex}-{destination.name}"
            os.replace(destination, backup)
        try:
            os.replace(staged, destination)
        except OSError:
            if backup is not None:
                os.replace(backup, destination)
            raise
        if backup is not None:
            try:
                if backup.is_symlink():
                    backup.unlink()
                else:
                    shutil.rmtree(backup)
            except OSError as error:
                print(f"Installed successfully; archived old bundle also remains at {backup}: {error}")
    print(f"Installed {destination.name} {info.get('CFBundleShortVersionString', '')}")


def quit_running_app(target):
    def running():
        result = subprocess.run(["/bin/ps", "-axo", "comm="], capture_output=True, text=True, check=True)
        return any(line.startswith(str(target) + "/") for line in result.stdout.splitlines())

    if not running():
        return
    info = plistlib.loads((target / "Contents/Info.plist").read_bytes())
    identifier = json.dumps(info["CFBundleIdentifier"])
    subprocess.run(["/usr/bin/osascript", "-e", f"tell application id {identifier} to quit"], check=True, timeout=60)
    for _ in range(20):
        if not running():
            return
        time.sleep(0.5)
    raise RuntimeError(f"{target.name} is still running; close it and retry")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--applications", type=Path, default=Path("/Applications"))
    parser.add_argument("--backups", type=Path, default=Path.home() / ".local/state/nix-macos-config/apps")
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--only", nargs="+", help="Install only these inventory names")
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as the configured user so installed apps remain user-writable")
    manifest = json.loads(args.manifest.read_text())
    if args.only:
        unknown = set(args.only) - manifest.keys()
        if unknown:
            parser.error("Unknown apps: " + ", ".join(sorted(unknown)))
        manifest = {name: manifest[name] for name in args.only}
    failed = False
    for name, entry in manifest.items():
        target = args.applications / entry["appName"]
        if (target.exists() or target.is_symlink()) and not args.replace_existing:
            print(f"Keeping installed app: {target}")
            continue
        try:
            args.applications.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(args.applications / ".mac-config-install.lock",
                                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, "a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                # Another activation may have installed it while this one waited.
                if (target.exists() or target.is_symlink()) and not args.replace_existing:
                    print(f"Keeping installed app: {target}")
                    continue
                with unpack(entry) as source:
                    install_bundle(source, target, args.backups, args.replace_existing,
                                   entry.get("removeFinderInfo", False),
                                   entry.get("removeQuarantine", False))
        except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
            print(f"Failed to install {name}: {error}")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
