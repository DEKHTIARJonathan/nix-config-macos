"""Install missing PKG applications with Apple's native installer during activation."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import plistlib
import subprocess


def installed_app(path):
    """Require an actual app bundle, not a stale receipt or empty directory."""
    try:
        info = plistlib.loads((path / "Contents/Info.plist").read_bytes())
        return isinstance(info, dict) and bool(info.get("CFBundleIdentifier"))
    except (OSError, ValueError, plistlib.InvalidFileException):
        return False


def install_packages(manifest, applications=Path("/Applications"), dry_run=False):
    failed = False
    for name, entry in manifest.items():
        target = applications / entry["appName"]
        if installed_app(target):
            print(f"Keeping installed app: {target}", flush=True)
            continue
        if dry_run:
            print(f"Would install {name}: {entry['source']} -> {target}", flush=True)
            continue
        try:
            print(f"Installing {name} from {entry['source']}", flush=True)
            subprocess.run([
                "/usr/sbin/installer", "-pkg", entry["source"], "-target", "/",
            ], check=True)
            if not installed_app(target):
                raise RuntimeError(f"Installer completed but expected app is missing or invalid: {target}")
            print(f"Installed {target}", flush=True)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            print(f"Failed to install {name}: {error}", flush=True)
            failed = True
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and os.geteuid() != 0:
        parser.error("Run with sudo; vendor PKG installers require root")
    manifest = json.loads(args.manifest.read_text())
    if args.dry_run:
        return install_packages(manifest, dry_run=True)
    # Serialize activations and recheck app presence after acquiring the lock.
    descriptor = os.open("/var/run/mac-config-install-pkgs.lock",
                         os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return install_packages(manifest)


if __name__ == "__main__":
    raise SystemExit(main())
