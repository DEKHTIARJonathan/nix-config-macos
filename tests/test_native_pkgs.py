"""Exercise missing-app recovery and preservation without running vendor installers."""

from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import install_native_pkgs as pkgs


class NativePackageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.applications = Path(temporary.name)
        self.manifest = {"example": {"appName": "Example.app", "source": "/pinned/example.pkg"}}
        self.target = self.applications / "Example.app"

    def create_app(self, *args, **kwargs):
        contents = self.target / "Contents"
        contents.mkdir(parents=True, exist_ok=True)
        (contents / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": "test.example", "CFBundleShortVersionString": "99.0",
        }))

    def test_missing_app_installs_and_repeat_activation_preserves_it(self):
        with patch.object(pkgs.subprocess, "run", side_effect=self.create_app) as run:
            self.assertEqual(pkgs.install_packages(self.manifest, self.applications), 0)
            self.assertEqual(pkgs.install_packages(self.manifest, self.applications), 0)
        run.assert_called_once_with([
            "/usr/sbin/installer", "-pkg", "/pinned/example.pkg", "-target", "/",
        ], check=True)

    def test_empty_app_directory_does_not_count_as_installed(self):
        self.target.mkdir()
        with patch.object(pkgs.subprocess, "run", side_effect=self.create_app) as run:
            self.assertEqual(pkgs.install_packages(self.manifest, self.applications), 0)
        run.assert_called_once()

    def test_existing_self_updated_app_is_untouched(self):
        self.create_app()
        before = (self.target / "Contents/Info.plist").read_bytes()
        with patch.object(pkgs.subprocess, "run") as run:
            self.assertEqual(pkgs.install_packages(self.manifest, self.applications), 0)
        run.assert_not_called()
        self.assertEqual((self.target / "Contents/Info.plist").read_bytes(), before)

    def test_corrupt_bundle_is_repaired(self):
        contents = self.target / "Contents"
        contents.mkdir(parents=True)
        for invalid in [b"broken plist", plistlib.dumps([]), plistlib.dumps({})]:
            with self.subTest(invalid=invalid):
                (contents / "Info.plist").write_bytes(invalid)
                with patch.object(pkgs.subprocess, "run", side_effect=self.create_app) as run:
                    self.assertEqual(pkgs.install_packages(self.manifest, self.applications), 0)
                run.assert_called_once()

    def test_failure_is_reported_and_other_packages_are_attempted(self):
        manifest = {"failed": {"appName": "Failed.app", "source": "/failed.pkg"}, **self.manifest}
        def install(command, **kwargs):
            if command[2] == "/failed.pkg":
                raise subprocess.CalledProcessError(1, command)
            self.create_app()
        with patch.object(pkgs.subprocess, "run", side_effect=install) as run:
            self.assertEqual(pkgs.install_packages(manifest, self.applications), 1)
        self.assertEqual(run.call_count, 2)
        self.assertTrue(pkgs.installed_app(self.target))

    def test_success_exit_without_expected_bundle_is_failure(self):
        with patch.object(pkgs.subprocess, "run"):
            self.assertEqual(pkgs.install_packages(self.manifest, self.applications), 1)

    def test_dry_run_never_installs(self):
        with patch.object(pkgs.subprocess, "run") as run:
            self.assertEqual(pkgs.install_packages(self.manifest, self.applications, dry_run=True), 0)
        run.assert_not_called()

    def test_non_root_execution_is_rejected(self):
        with patch.object(sys, "argv", ["install-pkgs", "--manifest", "/unused"]), \
                patch.object(pkgs.os, "geteuid", return_value=501):
            with self.assertRaises(SystemExit) as error:
                pkgs.main()
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
