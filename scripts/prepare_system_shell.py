"""Preserve an unmanaged /etc/bashrc before nix-darwin adopts the path."""

import os
import stat
import sys
import tempfile
from pathlib import Path


def prepare(etc=Path("/etc")):
    bashrc = etc / "bashrc"
    try:
        mode = bashrc.lstat().st_mode
    except FileNotFoundError:
        return
    if stat.S_ISLNK(mode):
        if os.readlink(bashrc) == str(etc / "static/bashrc"):
            return
        raise RuntimeError(f"Refusing unrelated symlink: {bashrc}")
    if not stat.S_ISREG(mode):
        raise RuntimeError(f"Refusing non-regular file: {bashrc}")

    # A private, unique directory preserves existing backups and keeps the
    # atomic rename on the same filesystem. Failure leaves the original intact.
    directory = Path(tempfile.mkdtemp(prefix="bashrc.before-nix-darwin.", dir=etc))
    backup = directory / "bashrc"
    try:
        bashrc.rename(backup)
    except OSError:
        directory.rmdir()
        raise
    print(f"Preserved {bashrc} at {backup}", flush=True)


if __name__ == "__main__":
    try:
        prepare()
    except (OSError, RuntimeError) as error:
        print(f"Shell migration failed: {error}", file=sys.stderr)
        sys.exit(1)
