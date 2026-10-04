"""Check Apple developer tools without installing or changing anything."""

from pathlib import Path
import subprocess


def verify(runner=subprocess.run, exists=lambda path: Path(path).exists()):
    failed = False

    def command(label, arguments):
        nonlocal failed
        try:
            result = runner(arguments, capture_output=True, text=True, check=False)
        except OSError as error:
            print(f"FAIL {label}: {error}")
            failed = True
            return None
        if result.returncode:
            detail = (result.stderr or result.stdout).strip() or f"exit status {result.returncode}"
            print(f"FAIL {label}: {detail}")
            failed = True
            return None
        print(f"OK {label}: {result.stdout.strip() or 'ready'}")
        return result.stdout.strip()

    selected = command("Selected developer directory", ["/usr/bin/xcode-select", "-p"])
    if not selected or not selected.endswith(".app/Contents/Developer") or not exists(selected):
        print("FAIL Select a full Xcode installation with sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer")
        failed = True
    command("Xcode version", ["/usr/bin/xcodebuild", "-version"])
    if command("Xcode first-launch readiness", ["/usr/bin/xcodebuild", "-checkFirstLaunchStatus"]) is None:
        print("Open Xcode to accept its license and complete first-launch setup.")
    command("Command Line Tools receipt", ["/usr/sbin/pkgutil", "--pkg-info", "com.apple.pkg.CLTools_Executables"])
    if not exists("/Library/Developer/CommandLineTools/usr/bin/clang"):
        print("FAIL Command Line Tools files missing; install them using xcode-select --install")
        failed = True
    for label, args in [
        ("clang", ["/usr/bin/xcrun", "--find", "clang"]),
        ("macOS SDK", ["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"]),
    ]:
        path = command(label, args)
        if path and not exists(path):
            print(f"FAIL {label} path does not exist: {path}")
            failed = True
    command("Compiler readiness", ["/usr/bin/xcrun", "clang", "--version"])
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(verify())
