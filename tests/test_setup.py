"""Test bootstrap control flow with fake installers and developer tools."""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/setup.sh"

# Every system probe/installer is mocked. Only Bash and temporary-file utilities
# run for real, so these tests also work on Linux without Nix or Apple tools.
MOCKS = r'''
record() { printf '%s\n' "$*" >> "$TEST_ROOT/calls"; }
uname() {
    if [[ $1 == -s ]]; then printf '%s\n' "${TEST_OS:-Darwin}";
    else printf '%s\n' "${TEST_ARCH:-arm64}"; fi
}
id() { printf '%s\n' "${TEST_UID:-501}"; }
xcrun() { record "xcrun $*"; [[ -e "$TEST_ROOT/tools-ready" ]]; }
git() { record "git $*"; return 0; }
make() { record "make $*"; return 0; }
xcode-select() {
    record "xcode-select $*"
    if [[ $1 == -p ]]; then return "${SELECTED_STATUS:-1}"; fi
    return "${TOOLS_INSTALL_STATUS:-0}"
}
sleep() {
    record "sleep $*"
    if [[ ${TOOLS_NEVER_READY:-0} == 0 ]]; then
        touch "$TEST_ROOT/tools-ready"
    fi
}
command() {
    if [[ "$*" == '-v nix' && ! -e "$TEST_ROOT/nix-ready" ]]; then
        return 1
    fi
    builtin command "$@"
}
nix() {
    record "nix $*"
    if [[ $1 == --version ]]; then return "${NIX_VERSION_STATUS:-0}"; fi
    return "${NIX_PING_STATUS:-0}"
}
existing_nix_state() { [[ ${NIX_STATE:-0} == 1 ]]; }
curl() {
    record "curl $*"
    if [[ ${DOWNLOAD_STATUS:-0} != 0 ]]; then return "$DOWNLOAD_STATUS"; fi
    local output=''
    while [[ $# -gt 0 ]]; do
        if [[ $1 == --output ]]; then output=$2; break; fi
        shift
    done
    [[ -n $output ]] || return 99
    cat > "$output" <<'INSTALLER'
printf 'installer %s\n' "$*" >> "$TEST_ROOT/calls"
if [ "${INSTALL_STATUS:-0}" != 0 ]; then exit "$INSTALL_STATUS"; fi
if [ "${INSTALL_NO_NIX:-0}" = 0 ]; then touch "$TEST_ROOT/nix-ready"; fi
INSTALLER
}
'''


class SetupTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ("tools-ready", "nix-ready"):
            (self.root / name).touch()

    def run_setup(self, body="main", **variables):
        env = dict(os.environ, TEST_ROOT=str(self.root), TMPDIR=str(self.root))
        env.update(variables)
        result = subprocess.run(
            ["/bin/bash", "--noprofile", "--norc", "-c",
             f"source {shlex.quote(str(SCRIPT))}\n{MOCKS}\n{body}"],
            env=env, text=True, capture_output=True, timeout=10,
        )
        calls = self.root / "calls"
        self.calls = calls.read_text() if calls.exists() else ""
        return result

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_no_install(self):
        self.assertNotIn("curl ", self.calls)
        self.assertNotIn("installer ", self.calls)
        self.assertNotIn("xcode-select --install", self.calls)

    def test_existing_installations_are_reused_on_repeated_runs(self):
        for _ in range(2):
            result = self.run_setup()
            self.assert_success(result)
            self.assert_no_install()
            self.assertIn("nix --version", self.calls)
            self.assertIn(
                "nix --extra-experimental-features nix-command flakes store ping --store daemon",
                self.calls,
            )
            self.assertIn("Setup complete", result.stdout)

    def test_missing_nix_is_downloaded_installed_and_verified(self):
        (self.root / "nix-ready").unlink()
        result = self.run_setup()
        self.assert_success(result)
        self.assertIn("https://nixos.org/nix/install", self.calls)
        self.assertIn("installer --daemon", self.calls)
        self.assertIn("nix --version", self.calls)
        self.assertEqual(list(self.root.glob("nix-macos-setup.*")), [])

    def test_download_failure_never_executes_installer(self):
        (self.root / "nix-ready").unlink()
        result = self.run_setup(DOWNLOAD_STATUS="22")
        self.assertEqual(result.returncode, 22, result.stderr)
        self.assertNotIn("installer ", self.calls)
        self.assertNotIn("Setup complete", result.stdout)
        self.assertEqual(list(self.root.glob("nix-macos-setup.*")), [])

    def test_installer_failure_cleans_up_and_propagates(self):
        (self.root / "nix-ready").unlink()
        result = self.run_setup(INSTALL_STATUS="42")
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertNotIn("nix --version", self.calls)
        self.assertEqual(list(self.root.glob("nix-macos-setup.*")), [])

    def test_installer_success_without_executable_is_failure(self):
        (self.root / "nix-ready").unlink()
        result = self.run_setup(INSTALL_NO_NIX="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nix is unavailable", result.stderr)

    def test_partial_installation_is_not_overwritten(self):
        (self.root / "nix-ready").unlink()
        result = self.run_setup(NIX_STATE="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("setup will not reinstall", result.stderr)
        self.assert_no_install()

    def test_broken_existing_nix_or_daemon_is_not_reinstalled(self):
        for variable in ("NIX_VERSION_STATUS", "NIX_PING_STATUS"):
            with self.subTest(variable=variable):
                result = self.run_setup(**{variable: "7"})
                self.assertEqual(result.returncode, 7, result.stderr)
                self.assert_no_install()
                self.assertNotIn("Setup complete", result.stdout)

    def test_missing_developer_tools_waits_for_installation(self):
        (self.root / "tools-ready").unlink()
        result = self.run_setup()
        self.assert_success(result)
        self.assertIn("xcode-select --install", self.calls)
        self.assertLess(self.calls.index("sleep 10"), self.calls.index("nix --version"))

    def test_unusable_selected_tools_are_preserved(self):
        (self.root / "tools-ready").unlink()
        result = self.run_setup(SELECTED_STATUS="0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("selected Apple developer tools", result.stderr)
        self.assert_no_install()
        self.assertNotIn("nix --version", self.calls)

    def test_developer_tools_installer_failure_stops_setup(self):
        (self.root / "tools-ready").unlink()
        result = self.run_setup(TOOLS_INSTALL_STATUS="4")
        self.assertEqual(result.returncode, 4, result.stderr)
        self.assertNotIn("nix --version", self.calls)

    def test_cancelled_developer_tools_installation_times_out(self):
        (self.root / "tools-ready").unlink()
        result = self.run_setup(TOOLS_NEVER_READY="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("still unavailable", result.stderr)
        self.assertNotIn("nix --version", self.calls)

    def test_wrong_platform_or_root_is_rejected_before_work(self):
        for variables in ({"TEST_OS": "Linux"}, {"TEST_ARCH": "x86_64"}, {"TEST_UID": "0"}):
            with self.subTest(variables=variables):
                result = self.run_setup(**variables)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.calls, "")

    def test_path_fallbacks_preserve_existing_precedence(self):
        result = self.run_setup(r'''
original_path=$PATH
ensure_developer_tools() { :; }
ensure_nix() {
    [[ $PATH == "$original_path:/nix/var/nix/profiles/default/bin:$HOME/.nix-profile/bin" ]]
}
main
''')
        self.assert_success(result)


if __name__ == "__main__":
    unittest.main()
