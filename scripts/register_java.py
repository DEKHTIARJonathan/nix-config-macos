"""Register Nix JDK bundles for macOS discovery without replacing other JDKs."""

import argparse
import os
from pathlib import Path
import sys
import tempfile


def register(bundles, directory=Path("/Library/Java/JavaVirtualMachines"), store=Path("/nix/store")):
    if directory.is_symlink():
        raise RuntimeError(f"Refusing symlinked Java registry: {directory}")

    # Check every source and destination before changing any registrations.
    pending = []
    for version, bundle in bundles.items():
        relative = bundle.relative_to(store)
        expected = ("Library", "Java", "JavaVirtualMachines", f"zulu-{version}.jdk")
        if len(relative.parts) != 5 or relative.parts[1:] != expected:
            raise RuntimeError(f"Unexpected Nix JDK bundle: {bundle}")
        for member in ("Contents/Info.plist", "Contents/Home/bin/java", "Contents/Home/bin/javac"):
            if not (bundle / member).is_file():
                raise RuntimeError(f"Incomplete JDK bundle: {bundle / member}")

        destination = directory / f"nix-jdk-{version}.jdk"
        if destination.is_symlink():
            previous = destination.readlink()
            # Recognize only our version-specific Nix bundle links, including
            # dangling links left by an older generation. Never follow them.
            try:
                old_relative = previous.relative_to(store)
            except ValueError:
                old_relative = Path()
            if len(old_relative.parts) != 5 or old_relative.parts[1:] != expected:
                raise RuntimeError(f"Refusing unrelated JDK symlink: {destination} -> {previous}")
            if previous == bundle:
                continue
        elif destination.exists():
            raise RuntimeError(f"Refusing existing JDK installation: {destination}")
        pending.append((destination, bundle))

    if not pending:
        return
    directory.mkdir(parents=True, exist_ok=True)
    # Stage on the same filesystem so a failed replacement leaves the old
    # registration intact. Repeated activation can safely retry each link.
    with tempfile.TemporaryDirectory(prefix=".nix-jdks-", dir=directory) as temporary:
        for destination, bundle in pending:
            staged = Path(temporary) / destination.name
            staged.symlink_to(bundle)
            os.replace(staged, destination)
            print(f"Registered {destination} -> {bundle}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jdk21", type=Path, required=True)
    parser.add_argument("--jdk25", type=Path, required=True)
    args = parser.parse_args()
    try:
        register({"21": args.jdk21, "25": args.jdk25})
    except (OSError, ValueError, RuntimeError) as error:
        print(f"JDK registration failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
