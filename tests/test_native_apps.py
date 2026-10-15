"""Check native installation, self-update preservation, and failed-replacement recovery."""

import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

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
        (contents / "Info.plist").write_bytes(
            plistlib.dumps(
                {
                    "CFBundleIdentifier": "test.example",
                    "CFBundleShortVersionString": "1.0",
                }
            )
        )
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

    def test_discovery_ignores_helpers_metadata_and_symlinked_apps(self):
        shutil.copytree(self.source, self.root / "image/__MACOSX/Other.app")
        shutil.copytree(self.source, self.root / "image/.Trashes/Deleted.app")
        shutil.copytree(
            self.root / "image/__MACOSX/Other.app",
            self.source / "Contents/Helpers/Helper.app",
        )
        (self.root / "image/Applications").symlink_to(
            self.root / "Applications", target_is_directory=True
        )
        (self.root / "image/Linked.app").symlink_to(
            self.source, target_is_directory=True
        )
        self.assertEqual(apps.find_bundle(self.root / "image"), self.source)

    def test_discovery_finds_bundle_inside_wrapper_directory(self):
        wrapper = self.root / "image/Release files"
        wrapper.mkdir()
        self.source.rename(wrapper / "Vendor Name.app")
        self.assertEqual(
            apps.find_bundle(self.root / "image"), wrapper / "Vendor Name.app"
        )

    def test_discovery_rejects_ambiguous_archives(self):
        shutil.copytree(self.source, self.root / "image/Uninstaller.app")
        with self.assertRaisesRegex(ValueError, "found 2"):
            apps.find_bundle(self.root / "image")

    def test_discovery_rejects_missing_or_invalid_bundle(self):
        with self.assertRaisesRegex(ValueError, "found 0"):
            apps.find_bundle(self.source / "Contents")
        (self.source / "Contents/Info.plist").unlink()
        with self.assertRaisesRegex(ValueError, "invalid app bundle"):
            apps.find_bundle(self.root / "image")

    def archive_command(self, command, **kwargs):
        if command[:2] == ["/usr/bin/hdiutil", "attach"]:
            shutil.copytree(self.root / "image", command[-2], dirs_exist_ok=True)
        elif command[:2] == ["/usr/bin/hdiutil", "detach"]:
            pass
        elif command[:2] == ["/usr/bin/ditto", "-xk"]:
            shutil.copytree(self.root / "image", command[-1], dirs_exist_ok=True)
        else:
            return self.ditto(command, **kwargs)
        return subprocess.CompletedProcess(command, 0)

    def install_discovered(
        self, format="dmg", replace=False, remove_quarantine=False, app_name=None
    ):
        manifest = self.root / "apps.json"
        manifest.write_text(
            json.dumps(
                {
                    "example": {
                        "source": "fixture",
                        "format": format,
                        "removeQuarantine": remove_quarantine,
                        "appName": app_name,
                    }
                }
            )
        )
        args = [
            "install-apps",
            "--manifest",
            str(manifest),
            "--applications",
            str(self.destination.parent),
            "--backups",
            str(self.backups),
        ]
        if replace:
            args.append("--replace-existing")
        with (
            patch.object(sys, "argv", args),
            patch.object(apps.os, "geteuid", return_value=501),
        ):
            return apps.main()

    def test_unnamed_dmg_and_zip_install_using_discovered_bundle_name(self):
        self.source.rename(self.source.with_name("Vendor Name.app"))
        for format in ("dmg", "zip"):
            with (
                self.subTest(format=format),
                patch.object(apps.subprocess, "run", side_effect=self.archive_command),
            ):
                self.assertEqual(self.install_discovered(format), 0)
                installed = self.destination.parent / "Vendor Name.app"
                self.assertEqual(
                    (installed / "Contents/data").read_text(), "vendor bundle"
                )
                shutil.rmtree(installed)

    def test_name_override_renames_discovered_nested_bundle(self):
        wrapper = self.root / "image/Release"
        wrapper.mkdir()
        self.source.rename(wrapper / "Vendor Name.app")
        for format in ("dmg", "zip"):
            with (
                self.subTest(format=format),
                patch.object(apps.subprocess, "run", side_effect=self.archive_command),
            ):
                self.assertEqual(
                    self.install_discovered(format, app_name="Renamed.app"), 0
                )
                installed = self.destination.parent / "Renamed.app"
                self.assertEqual(
                    (installed / "Contents/data").read_text(), "vendor bundle"
                )
                shutil.rmtree(installed)

    def test_name_override_does_not_select_between_multiple_apps(self):
        shutil.copytree(self.source, self.root / "image/Uninstaller.app")
        with patch.object(apps.subprocess, "run", side_effect=self.archive_command):
            self.assertEqual(self.install_discovered(app_name="Example.app"), 1)
        self.assertFalse(self.destination.exists())

    def test_discovered_app_preserves_existing_bundle_and_symlink(self):
        self.existing_app()
        for symlink in (False, True):
            if symlink:
                self.destination.rename(self.root / "existing.app")
                self.destination.symlink_to(
                    self.root / "existing.app", target_is_directory=True
                )
            with (
                self.subTest(symlink=symlink),
                patch.object(apps.subprocess, "run", side_effect=self.archive_command),
            ):
                self.assertEqual(self.install_discovered(), 0)
            self.assertEqual(
                (self.destination / "updated").read_text(), "self-updated version"
            )
        self.quit_app.assert_not_called()
        self.assertFalse(self.backups.exists())

    def test_discovered_app_applies_requested_quarantine_cleanup_to_staged_copy(self):
        cleaned = []

        def native_command(command, **kwargs):
            if command[0] == "/usr/bin/xattr":
                self.assertEqual(
                    command[:3], ["/usr/bin/xattr", "-dr", "com.apple.quarantine"]
                )
                staged = Path(command[-1])
                self.assertNotEqual(staged, self.destination)
                self.assertTrue((staged / "Contents/Info.plist").exists())
                cleaned.append(staged)
                return subprocess.CompletedProcess(command, 0)
            return self.archive_command(command, **kwargs)

        with patch.object(apps.subprocess, "run", side_effect=native_command):
            self.assertEqual(self.install_discovered(remove_quarantine=True), 0)
        self.assertEqual(len(cleaned), 1)
        self.assertTrue((self.destination / "Contents/Info.plist").exists())

    def test_discovered_app_waiting_for_lock_preserves_other_installer_result(self):
        with (
            patch.object(
                apps.fcntl, "flock", side_effect=lambda *args: self.existing_app()
            ),
            patch.object(apps.subprocess, "run", side_effect=self.archive_command),
        ):
            self.assertEqual(self.install_discovered(), 0)
        self.assertEqual(
            (self.destination / "updated").read_text(), "self-updated version"
        )

    def test_discovered_app_replacement_keeps_verified_backup(self):
        self.existing_app()
        with patch.object(apps.subprocess, "run", side_effect=self.archive_command):
            self.assertEqual(self.install_discovered(replace=True), 0)
        (backup,) = self.backups.glob("*.zip.bckp")
        with zipfile.ZipFile(backup) as archive:
            self.assertEqual(
                archive.read("Example.app/updated"), b"self-updated version"
            )
        self.assertTrue((self.destination / "Contents/Info.plist").exists())

    def test_ambiguous_dmg_fails_without_installing_and_is_detached(self):
        shutil.copytree(self.source, self.root / "image/Uninstaller.app")
        with patch.object(
            apps.subprocess, "run", side_effect=self.archive_command
        ) as run:
            self.assertEqual(self.install_discovered(), 1)
        self.assertFalse(self.destination.exists())
        self.assertTrue(
            any(
                call.args[0][:2] == ["/usr/bin/hdiutil", "detach"]
                for call in run.call_args_list
            )
        )

    def test_build_discovery_command_only_prints_path(self):
        result = subprocess.run(
            [
                sys.executable,
                str(Path(apps.__file__)),
                "--find-bundle",
                str(self.root / "image"),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), str(self.source))
        self.assertFalse(self.destination.parent.exists())

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
        manifest.write_text(
            json.dumps(
                {
                    "example": {
                        "appName": "Example.app",
                        "source": "/missing",
                        "format": "dmg",
                    }
                }
            )
        )
        args = [
            "install-apps",
            "--manifest",
            str(manifest),
            "--applications",
            str(self.destination.parent),
        ]
        with (
            patch.object(sys, "argv", args),
            patch.object(apps.os, "geteuid", return_value=501),
            patch.object(apps, "unpack") as unpack,
        ):
            self.assertEqual(apps.main(), 0)
        unpack.assert_not_called()
        self.assertEqual(
            (self.destination / "updated").read_text(), "self-updated version"
        )

    def test_install_waiting_for_lock_preserves_other_installer_result(self):
        manifest = self.root / "apps.json"
        manifest.write_text(
            json.dumps(
                {
                    "example": {
                        "appName": "Example.app",
                        "source": "/missing",
                        "format": "dmg",
                    }
                }
            )
        )
        args = [
            "install-apps",
            "--manifest",
            str(manifest),
            "--applications",
            str(self.destination.parent),
        ]
        with (
            patch.object(sys, "argv", args),
            patch.object(apps.os, "geteuid", return_value=501),
            patch.object(
                apps.fcntl, "flock", side_effect=lambda *args: self.existing_app()
            ),
            patch.object(apps, "unpack") as unpack,
        ):
            self.assertEqual(apps.main(), 0)
        unpack.assert_not_called()
        self.assertEqual(
            (self.destination / "updated").read_text(), "self-updated version"
        )

    def test_explicit_replacement_keeps_original_as_bckp(self):
        self.existing_app()
        with patch.object(apps.subprocess, "run", side_effect=self.ditto):
            apps.install_bundle(
                self.source, self.destination, self.backups, replace=True
            )
        (backup,) = self.backups.glob("*.bckp")
        self.assertTrue(backup.name.endswith(".zip.bckp"))
        with zipfile.ZipFile(backup) as archive:
            self.assertEqual(
                archive.read("Example.app/updated"), b"self-updated version"
            )
        self.assertFalse(list(self.backups.glob(".retired-*")))
        self.assertTrue((self.destination / "Contents/Info.plist").exists())

    def test_failed_copy_leaves_installed_app_untouched(self):
        self.existing_app()
        with (
            patch.object(
                apps.subprocess,
                "run",
                side_effect=subprocess.CalledProcessError(1, "ditto"),
            ),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            apps.install_bundle(
                self.source, self.destination, self.backups, replace=True
            )
        self.assertTrue((self.destination / "updated").exists())
        self.assertFalse(self.backups.exists())

    def test_failed_final_rename_restores_original_app(self):
        self.existing_app()
        replace = os.replace

        def fail_install(source, target):
            if (
                Path(source).parent.name.startswith(".mac-config-")
                and Path(target) == self.destination
            ):
                raise OSError("Simulated replacement failure")
            return replace(source, target)

        with (
            patch.object(apps.subprocess, "run", side_effect=self.ditto),
            patch.object(apps.os, "replace", side_effect=fail_install),
            self.assertRaisesRegex(OSError, "Simulated replacement"),
        ):
            apps.install_bundle(
                self.source, self.destination, self.backups, replace=True
            )
        self.assertEqual(
            (self.destination / "updated").read_text(), "self-updated version"
        )

    def test_failed_archive_leaves_installed_app_untouched(self):
        self.existing_app()

        def fail_archive(command, **kwargs):
            if "-c" in command:
                raise subprocess.CalledProcessError(1, "ditto")
            return self.ditto(command, **kwargs)

        with (
            patch.object(apps.subprocess, "run", side_effect=fail_archive),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            apps.install_bundle(
                self.source, self.destination, self.backups, replace=True
            )
        self.assertEqual(
            (self.destination / "updated").read_text(), "self-updated version"
        )
        self.assertFalse(list(self.backups.glob("*.bckp")))

    def test_refused_quit_preserves_installed_app(self):
        self.existing_app()
        self.quit_app.side_effect = RuntimeError("Still running")
        with (
            patch.object(apps.subprocess, "run", side_effect=self.ditto),
            self.assertRaisesRegex(RuntimeError, "Still running"),
        ):
            apps.install_bundle(
                self.source, self.destination, self.backups, replace=True
            )
        self.assertEqual(
            (self.destination / "updated").read_text(), "self-updated version"
        )
        self.assertFalse(list(self.backups.glob("*.bckp")))

    def test_corrupt_archive_leaves_installed_app_untouched(self):
        self.existing_app()

        def corrupt_archive(command, **kwargs):
            if "-c" in command:
                Path(command[-1]).write_bytes(b"truncated archive")
                return subprocess.CompletedProcess(command, 0)
            return self.ditto(command, **kwargs)

        with (
            patch.object(apps.subprocess, "run", side_effect=corrupt_archive),
            self.assertRaises(zipfile.BadZipFile),
        ):
            apps.install_bundle(
                self.source, self.destination, self.backups, replace=True
            )
        self.assertEqual(
            (self.destination / "updated").read_text(), "self-updated version"
        )

    def test_app_created_during_staging_is_preserved(self):
        def create_app(command, **kwargs):
            result = self.ditto(command, **kwargs)
            self.existing_app()
            return result

        with patch.object(apps.subprocess, "run", side_effect=create_app):
            apps.install_bundle(self.source, self.destination, self.backups)
        self.assertEqual(
            (self.destination / "updated").read_text(), "self-updated version"
        )
        self.assertFalse(self.backups.exists())
        self.quit_app.assert_not_called()

    def test_attribute_failure_leaves_installed_app_untouched(self):
        self.existing_app()

        def fail_attributes(command, **kwargs):
            if command[0] == "/usr/bin/xattr":
                self.assertNotEqual(command[-1], str(self.destination))
                raise subprocess.CalledProcessError(1, "xattr")
            return self.ditto(command, **kwargs)

        with (
            patch.object(apps.subprocess, "run", side_effect=fail_attributes),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            apps.install_bundle(
                self.source,
                self.destination,
                self.backups,
                replace=True,
                remove_quarantine=True,
            )
        self.assertEqual(
            (self.destination / "updated").read_text(), "self-updated version"
        )
        self.assertFalse(self.backups.exists())

    def test_failed_detach_does_not_recurse_into_mounted_image(self):
        mount_root = self.root / "mount-test"
        mount_root.mkdir()

        def hdiutil(command, **kwargs):
            if command[1] == "detach":
                raise subprocess.CalledProcessError(1, "hdiutil")
            return subprocess.CompletedProcess(command, 0)

        entry = {"format": "dmg", "source": "image.dmg", "appName": "Example.app"}
        with (
            patch.object(apps.tempfile, "mkdtemp", return_value=str(mount_root)),
            patch.object(apps.subprocess, "run", side_effect=hdiutil),
            patch.object(apps.shutil, "rmtree") as remove,
            self.assertRaises(subprocess.CalledProcessError),
            apps.unpack(entry),
        ):
            pass
        remove.assert_not_called()

    @unittest.skipUnless(sys.platform == "darwin", "Native macOS archive metadata")
    def test_native_archive_restores_attributes_and_dereferences_top_level_symlink(
        self,
    ):
        self.existing_app()
        payload = self.destination / "updated"
        subprocess.run(
            [
                "/usr/bin/xattr",
                "-w",
                "com.example.backup-test",
                "preserved metadata",
                str(payload),
            ],
            check=True,
        )
        payload.chmod(0o444)
        (self.destination / "relative-link").symlink_to("updated")
        link = self.root / "links/Example.app"
        link.parent.mkdir()
        link.symlink_to(self.destination)
        backup = apps.archive_bundle(link, self.backups)
        # Removing the source proves this archive is independent of store GC.
        shutil.rmtree(self.destination)
        restored = self.root / "restored"
        subprocess.run(
            ["/usr/bin/ditto", "-x", "-k", str(backup), str(restored)], check=True
        )
        app = restored / "Example.app"
        self.assertFalse(app.is_symlink())
        self.assertEqual((app / "updated").read_text(), "self-updated version")
        self.assertEqual((app / "updated").stat().st_mode & 0o777, 0o444)
        attribute = subprocess.run(
            ["/usr/bin/xattr", "-p", "com.example.backup-test", str(app / "updated")],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(attribute.stdout.strip(), "preserved metadata")
        self.assertEqual(os.readlink(app / "relative-link"), "updated")


@unittest.skipUnless(
    os.environ.get("APP_BUILD_PHASES"),
    "Generated app build phases require the Nix check",
)
class AppBuildTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.phases = json.loads(Path(os.environ["APP_BUILD_PHASES"]).read_text())
        self.archive = self.root / "fixture.dmg"
        self.work = self.root / "unpacked"
        self.work.mkdir()
        self.output = self.root / "output"
        self.tools = self.root / "tools"
        self.tools.mkdir()
        self.calls = self.root / "extractor-calls.jsonl"
        sevenzip = shutil.which("7zz")
        # These small ZIP fixtures exercise real 7zz extraction. Only image
        # inspection is mocked; HFS routing uses a recording undmg stub.
        stub = f"""#!{sys.executable}
import json
import os
from pathlib import Path
import sys
tool = Path(sys.argv[0]).name
with open(os.environ["DMG_TEST_CALLS"], "a") as log:
    log.write(json.dumps([tool, *sys.argv[1:]]) + "\\n")
if tool == "undmg":
    sys.exit(int(os.environ.get("DMG_TEST_EXTRACT_STATUS", "0")))
if sys.argv[1] == "l":
    print(os.environ["DMG_TEST_LISTING"])
    sys.exit(int(os.environ.get("DMG_TEST_LIST_STATUS", "0")))
status = int(os.environ.get("DMG_TEST_EXTRACT_STATUS", "0"))
if status:
    sys.exit(status)
os.execv({sevenzip!r}, [{sevenzip!r}, *sys.argv[1:]])
"""
        for tool in ("7zz", "undmg"):
            executable = self.tools / tool
            executable.write_text(stub)
            executable.chmod(0o755)

    def make_archive(self, names, link_target="payload"):
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name in names:
                archive.writestr(
                    f"{name}/Contents/Info.plist",
                    plistlib.dumps({"CFBundleIdentifier": "test.fixture"}),
                )
                archive.writestr(f"{name}/Contents/MacOS/payload", "payload")
                archive.writestr(
                    f"{name}/Contents/Helpers/Helper.app/Contents/Info.plist", b"helper"
                )
                link = zipfile.ZipInfo(f"{name}/Contents/MacOS/helper")
                link.create_system = 3
                link.external_attr = 0o120777 << 16
                archive.writestr(link, link_target)
            link = zipfile.ZipInfo("Applications")
            link.create_system = 3
            link.external_attr = 0o120777 << 16
            archive.writestr(link, "/Applications")

    def phase(self, name, listing="Type = Dmg\nType = APFS\n----------\n", **overrides):
        env = dict(
            os.environ,
            src=str(self.archive),
            out=str(self.output),
            PATH=str(self.tools) + os.pathsep + os.environ["PATH"],
            DMG_TEST_LISTING=listing,
            DMG_TEST_CALLS=str(self.calls),
            **overrides,
        )
        return subprocess.run(
            ["bash", "-e", "-c", "runHook() { :; }\n" + self.phases[name]],
            check=False,
            cwd=self.work,
            env=env,
            capture_output=True,
            text=True,
        )

    def extractor_calls(self):
        return [json.loads(line) for line in self.calls.read_text().splitlines()]

    def test_hfs_selects_undmg_and_ignores_type_text_in_file_listing(self):
        result = self.phase(
            "autoUnpack", listing="Type = Dmg\nType = HFS\n----------\nType = APFS\n"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [call[:2] for call in self.extractor_calls()],
            [
                ["7zz", "l"],
                ["undmg", str(self.archive)],
            ],
        )

    def test_unknown_and_ambiguous_filesystems_do_not_extract(self):
        for listing in (
            "Type = Dmg\nType = FAT\n----------\n",
            "Type = HFS\nType = APFS\n----------\n",
        ):
            with self.subTest(listing=listing):
                self.calls.unlink(missing_ok=True)
                result = self.phase("autoUnpack", listing=listing)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Expected one HFS or APFS", result.stderr)
                self.assertEqual(len(self.extractor_calls()), 1)
                self.assertFalse(self.output.exists())

    def test_failed_inspection_does_not_start_extraction(self):
        result = self.phase("autoUnpack", DMG_TEST_LIST_STATUS="2")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self.extractor_calls()), 1)

    def test_failed_extraction_does_not_try_a_different_extractor(self):
        for filesystem in ("HFS", "APFS"):
            with self.subTest(filesystem=filesystem):
                self.calls.unlink(missing_ok=True)
                result = self.phase(
                    "autoUnpack",
                    listing=f"Type = Dmg\nType = {filesystem}\n----------\n",
                    DMG_TEST_EXTRACT_STATUS="7",
                )
                self.assertEqual(result.returncode, 7)
                self.assertEqual(len(self.extractor_calls()), 2)

    def test_7zz_discovers_nested_app_preserving_helpers_and_links(self):
        self.make_archive(["Release/Vendor Name.app"])
        for name in ("autoUnpack", "autoInstall"):
            result = self.phase(name)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        app = self.output / "Applications/Vendor Name.app"
        self.assertEqual((app / "Contents/MacOS/helper").read_text(), "payload")
        self.assertTrue((app / "Contents/MacOS/helper").is_symlink())
        self.assertTrue(
            (app / "Contents/Helpers/Helper.app/Contents/Info.plist").exists()
        )
        self.assertFalse((self.work / "Applications").is_symlink())

    def test_7zz_rejects_parent_symlinks(self):
        self.make_archive(["Vendor Name.app"], link_target="../Info.plist")
        result = self.phase("autoUnpack")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            (self.work / "Vendor Name.app/Contents/MacOS/helper").is_symlink()
        )

    def test_7zz_multiple_apps_fail_even_with_name_override(self):
        self.make_archive(["Release/Vendor Name.app", "Uninstaller.app"])
        result = self.phase("autoUnpack")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.phase("autoInstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("found 2", result.stderr)
        self.assertFalse(self.output.exists())
        result = self.phase("namedInstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("found 2", result.stderr)
        self.assertFalse(self.output.exists())

    def test_7zz_name_override_renames_discovered_nested_app(self):
        self.make_archive(["Release/Vendor Name.app"])
        result = self.phase("namedUnpack")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.phase("namedInstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            (self.output / "Applications/Renamed.app/Contents/Info.plist").exists()
        )

    def test_dmg_pkg_stages_single_nested_installer(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("Release/Installer.pkg", "fixture installer")
        for phase in ("pkgUnpack", "pkgInstall"):
            result = self.phase(phase)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            (self.output / "share/macos-pkgs/app-discovery-fixture.pkg").read_text(),
            "fixture installer",
        )

    def test_dmg_pkg_still_rejects_multiple_installers(self):
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("First.pkg", "first")
            archive.writestr("Second.pkg", "second")
        result = self.phase("pkgUnpack")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.phase("pkgInstall")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expected exactly one PKG", result.stderr)


if __name__ == "__main__":
    unittest.main()
