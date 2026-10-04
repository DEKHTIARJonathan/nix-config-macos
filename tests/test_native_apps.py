"""Check native installation, self-update preservation, and failed-replacement recovery."""

import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import install_native_apps as apps


class NativeAppTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "image/Example.app"
        contents = self.source / "Contents"
        contents.mkdir(parents=True)
        (contents / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleIdentifier": "test.example", "CFBundleShortVersionString": "1.0",
        }))
        (contents / "data").write_text("vendor bundle")
        (contents / "data").chmod(0o444)
        self.destination = self.root / "Applications/Example.app"
        self.backups = self.root / "backups"
        quit_app = patch.object(apps, "quit_running_app")
        self.quit_app = quit_app.start()
        self.addCleanup(quit_app.stop)

    @staticmethod
    def ditto(command, **kwargs):
        if command[0] != "/usr/bin/ditto":
            raise AssertionError(command)
        if "-c" in command:
            source = Path(command[-2])
            with zipfile.ZipFile(command[-1], "w") as archive:
                for path in source.rglob("*"):
                    archive.write(path, path.relative_to(source.parent))
        else:
            shutil.copytree(command[-2], command[-1], symlinks=True)
        return subprocess.CompletedProcess(command, 0)

    def existing_app(self):
        self.destination.mkdir(parents=True)
        (self.destination / "updated").write_text("self-updated version")

    def test_install_makes_native_bundle_writable(self):
        with patch.object(apps.subprocess, "run", side_effect=self.ditto):
            apps.install_bundle(self.source, self.destination, self.backups)
        data = self.destination / "Contents/data"
        self.assertEqual(data.read_text(), "vendor bundle")
        self.assertTrue(data.stat().st_mode & 0o200)
        self.assertFalse(self.destination.is_symlink())
        self.assertFalse(self.backups.exists())

    def test_rebuild_does_not_unpack_or_replace_self_updated_apps(self):
        self.existing_app()
        manifest = self.root / "apps.json"
        manifest.write_text(json.dumps({"example": {"appName": "Example.app", "source": "/missing", "format": "dmg"}}))
        args = ["install-apps", "--manifest", str(manifest), "--applications", str(self.destination.parent)]
        with patch.object(sys, "argv", args), patch.object(apps.os, "geteuid", return_value=501), patch.object(apps, "unpack") as unpack:
            self.assertEqual(apps.main(), 0)
        unpack.assert_not_called()
        self.assertEqual((self.destination / "updated").read_text(), "self-updated version")

    def test_install_waiting_for_lock_preserves_other_installer_result(self):
        manifest = self.root / "apps.json"
        manifest.write_text(json.dumps({"example": {"appName": "Example.app", "source": "/missing", "format": "dmg"}}))
        args = ["install-apps", "--manifest", str(manifest), "--applications", str(self.destination.parent)]
        with patch.object(sys, "argv", args), patch.object(apps.os, "geteuid", return_value=501), \
                patch.object(apps.fcntl, "flock", side_effect=lambda *args: self.existing_app()), \
                patch.object(apps, "unpack") as unpack:
            self.assertEqual(apps.main(), 0)
        unpack.assert_not_called()
        self.assertEqual((self.destination / "updated").read_text(), "self-updated version")

    def test_explicit_replacement_keeps_original_as_bckp(self):
        self.existing_app()
        with patch.object(apps.subprocess, "run", side_effect=self.ditto):
            apps.install_bundle(self.source, self.destination, self.backups, replace=True)
        backup, = self.backups.glob("*.bckp")
        self.assertTrue(backup.name.endswith(".zip.bckp"))
        with zipfile.ZipFile(backup) as archive:
            self.assertEqual(archive.read("Example.app/updated"), b"self-updated version")
        self.assertFalse(list(self.backups.glob(".retired-*")))
        self.assertTrue((self.destination / "Contents/Info.plist").exists())

    def test_failed_copy_leaves_installed_app_untouched(self):
        self.existing_app()
        with patch.object(apps.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "ditto")):
            with self.assertRaises(subprocess.CalledProcessError):
                apps.install_bundle(self.source, self.destination, self.backups, replace=True)
        self.assertTrue((self.destination / "updated").exists())
        self.assertFalse(self.backups.exists())

    def test_failed_final_rename_restores_original_app(self):
        self.existing_app()
        replace = os.replace

        def fail_install(source, target):
            if Path(source).parent.name.startswith(".mac-config-") and Path(target) == self.destination:
                raise OSError("Simulated replacement failure")
            return replace(source, target)

        with patch.object(apps.subprocess, "run", side_effect=self.ditto), patch.object(apps.os, "replace", side_effect=fail_install):
            with self.assertRaisesRegex(OSError, "Simulated replacement"):
                apps.install_bundle(self.source, self.destination, self.backups, replace=True)
        self.assertEqual((self.destination / "updated").read_text(), "self-updated version")

    def test_failed_archive_leaves_installed_app_untouched(self):
        self.existing_app()

        def fail_archive(command, **kwargs):
            if "-c" in command:
                raise subprocess.CalledProcessError(1, "ditto")
            return self.ditto(command, **kwargs)

        with patch.object(apps.subprocess, "run", side_effect=fail_archive):
            with self.assertRaises(subprocess.CalledProcessError):
                apps.install_bundle(self.source, self.destination, self.backups, replace=True)
        self.assertEqual((self.destination / "updated").read_text(), "self-updated version")
        self.assertFalse(list(self.backups.glob("*.bckp")))

    def test_refused_quit_preserves_installed_app(self):
        self.existing_app()
        self.quit_app.side_effect = RuntimeError("Still running")
        with patch.object(apps.subprocess, "run", side_effect=self.ditto):
            with self.assertRaisesRegex(RuntimeError, "Still running"):
                apps.install_bundle(self.source, self.destination, self.backups, replace=True)
        self.assertEqual((self.destination / "updated").read_text(), "self-updated version")
        self.assertFalse(list(self.backups.glob("*.bckp")))

    def test_corrupt_archive_leaves_installed_app_untouched(self):
        self.existing_app()

        def corrupt_archive(command, **kwargs):
            if "-c" in command:
                Path(command[-1]).write_bytes(b"truncated archive")
                return subprocess.CompletedProcess(command, 0)
            return self.ditto(command, **kwargs)

        with patch.object(apps.subprocess, "run", side_effect=corrupt_archive):
            with self.assertRaises(zipfile.BadZipFile):
                apps.install_bundle(self.source, self.destination, self.backups, replace=True)
        self.assertEqual((self.destination / "updated").read_text(), "self-updated version")

    def test_app_created_during_staging_is_preserved(self):
        def create_app(command, **kwargs):
            result = self.ditto(command, **kwargs)
            self.existing_app()
            return result

        with patch.object(apps.subprocess, "run", side_effect=create_app):
            apps.install_bundle(self.source, self.destination, self.backups)
        self.assertEqual((self.destination / "updated").read_text(), "self-updated version")
        self.assertFalse(self.backups.exists())
        self.quit_app.assert_not_called()

    def test_attribute_failure_leaves_installed_app_untouched(self):
        self.existing_app()

        def fail_attributes(command, **kwargs):
            if command[0] == "/usr/bin/xattr":
                self.assertNotEqual(command[-1], str(self.destination))
                raise subprocess.CalledProcessError(1, "xattr")
            return self.ditto(command, **kwargs)

        with patch.object(apps.subprocess, "run", side_effect=fail_attributes):
            with self.assertRaises(subprocess.CalledProcessError):
                apps.install_bundle(self.source, self.destination, self.backups,
                                    replace=True, remove_quarantine=True)
        self.assertEqual((self.destination / "updated").read_text(), "self-updated version")
        self.assertFalse(self.backups.exists())

    def test_failed_detach_does_not_recurse_into_mounted_image(self):
        mount_root = self.root / "mount-test"
        mount_root.mkdir()

        def hdiutil(command, **kwargs):
            if command[1] == "detach":
                raise subprocess.CalledProcessError(1, "hdiutil")
            return subprocess.CompletedProcess(command, 0)

        entry = {"format": "dmg", "source": "image.dmg", "appName": "Example.app"}
        with patch.object(apps.tempfile, "mkdtemp", return_value=str(mount_root)), \
                patch.object(apps.subprocess, "run", side_effect=hdiutil), \
                patch.object(apps.shutil, "rmtree") as remove:
            with self.assertRaises(subprocess.CalledProcessError):
                with apps.unpack(entry):
                    pass
        remove.assert_not_called()

    @unittest.skipUnless(sys.platform == "darwin", "Native macOS archive metadata")
    def test_native_archive_restores_attributes_and_dereferences_top_level_symlink(self):
        self.existing_app()
        payload = self.destination / "updated"
        subprocess.run(["/usr/bin/xattr", "-w", "com.example.backup-test", "preserved metadata", str(payload)], check=True)
        payload.chmod(0o444)
        (self.destination / "relative-link").symlink_to("updated")
        link = self.root / "links/Example.app"
        link.parent.mkdir()
        link.symlink_to(self.destination)
        backup = apps.archive_bundle(link, self.backups)
        # Removing the source proves this archive is independent of store GC.
        shutil.rmtree(self.destination)
        restored = self.root / "restored"
        subprocess.run(["/usr/bin/ditto", "-x", "-k", str(backup), str(restored)], check=True)
        app = restored / "Example.app"
        self.assertFalse(app.is_symlink())
        self.assertEqual((app / "updated").read_text(), "self-updated version")
        self.assertEqual((app / "updated").stat().st_mode & 0o777, 0o444)
        attribute = subprocess.run(["/usr/bin/xattr", "-p", "com.example.backup-test", str(app / "updated")],
                                   check=True, capture_output=True, text=True)
        self.assertEqual(attribute.stdout.strip(), "preserved metadata")
        self.assertEqual(os.readlink(app / "relative-link"), "updated")


if __name__ == "__main__":
    unittest.main()
