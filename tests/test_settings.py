"""Exercise migration behavior without touching the real user's preferences."""

import copy
import json
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import restore_settings as restore
import setup_editors as editors
import verify_development_tools as development


class FakePreferences:
    def __init__(self, values=None):
        self.values = copy.deepcopy(values or {})
        self.fail = False
        self.writes = 0

    def read(self, domain):
        return copy.deepcopy(self.values.get(domain, {}))

    def write(self, domain, updates):
        if self.fail:
            raise RuntimeError("Simulated preference failure")
        self.values.setdefault(domain, {}).update(copy.deepcopy(updates))
        self.writes += 1


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "Home with spaces"
        self.source = ROOT / "settings"

    def test_editor_seed_preserves_edits_and_broken_symlink(self):
        zed = self.home / ".config/zed/settings.json"
        zed.parent.mkdir(parents=True)
        zed.symlink_to(self.home / "absent")
        restore.seed_editors(self.source, self.home)
        code = self.home / "Library/Application Support/Code/User/settings.json"
        self.assertNotIn("dart.flutterSdkPath", json.loads(code.read_text()))
        code.write_text('{"userEdit": true}')
        restore.seed_editors(self.source, self.home)
        self.assertTrue(json.loads(code.read_text())["userEdit"])
        self.assertTrue(zed.is_symlink())

    def test_explicit_editor_restore_backs_up_without_following_symlinks(self):
        restore.seed_editors(self.source, self.home)
        zed = self.home / ".config/zed/settings.json"
        external = self.home / "external.json"
        external.write_text("external data")
        zed.unlink()
        zed.symlink_to(external)
        restore.seed_editors(self.source, self.home, replace=True)
        self.assertFalse(zed.is_symlink())
        self.assertEqual(external.read_text(), "external data")
        backups = list((restore.state_directory(self.home) / "backups").iterdir())
        self.assertTrue(any(p.is_symlink() and p.readlink() == external for p in backups))

    def test_dry_run_has_no_files_or_preference_writes(self):
        preferences = FakePreferences()
        restore.seed_editors(self.source, self.home, dry_run=True)
        restore.restore_desktop("terminal", self.source, self.home, preferences, once=True, dry_run=True)
        self.assertFalse(self.home.exists())
        self.assertEqual(preferences.writes, 0)

    def test_terminal_merges_binary_data_and_only_restores_once(self):
        domain = "com.apple.Terminal"
        preferences = FakePreferences({domain: {"Window Settings": {"Personal": {"value": 1}}, "unrelated": 7}})
        restore.restore_desktop("terminal", self.source, self.home, preferences, once=True)
        current = preferences.read(domain)
        self.assertIn("Personal", current["Window Settings"])
        self.assertEqual(current["unrelated"], 7)
        profile = current["Window Settings"]["Basic (Shift-Enter)"]
        self.assertIsInstance(profile["Font"], bytes)
        self.assertEqual(current["Default Window Settings"], "Basic (Shift-Enter)")
        preferences.values[domain]["Default Window Settings"] = "Personal"
        restore.restore_desktop("terminal", self.source, self.home, preferences, once=True)
        self.assertEqual(preferences.writes, 1)
        self.assertEqual(preferences.read(domain)["Default Window Settings"], "Personal")
        restore.restore_desktop("terminal", self.source, self.home, preferences)
        self.assertEqual(preferences.writes, 2)

    def test_failed_restore_can_retry_without_completion_marker(self):
        preferences = FakePreferences()
        preferences.fail = True
        with self.assertRaises(RuntimeError):
            restore.restore_desktop("terminal", self.source, self.home, preferences, once=True)
        self.assertFalse((restore.state_directory(self.home) / "terminal-restored").exists())
        preferences.fail = False
        restore.restore_desktop("terminal", self.source, self.home, preferences, once=True)
        self.assertTrue((restore.state_directory(self.home) / "terminal-restored").exists())

    def test_dock_paths_skip_missing_and_preserve_other_preferences(self):
        source = Path(self.temporary.name) / "source"
        source.mkdir()
        applications = Path(self.temporary.name) / "Applications"
        managed = applications / "Example App.app"
        managed.mkdir(parents=True)
        original = Path(self.temporary.name) / "old/Example App.app"
        original.mkdir(parents=True)
        system_app = Path(self.temporary.name) / "System App.app"
        system_app.mkdir()
        items = [
            {"name": "Example", "path": str(original), "managed": True},
            {"name": "System", "path": str(system_app), "managed": False},
            {"name": "Missing", "path": str(applications / "Missing.app"), "managed": True},
        ]
        (source / "dock.json").write_text(json.dumps(items))
        preferences = FakePreferences({"com.apple.dock": {"persistent-others": ["Downloads"], "tilesize": 64}})
        with patch.object(restore.subprocess, "run"):
            restore.restore_desktop("dock", source, self.home, preferences, applications=applications)
        current = preferences.read("com.apple.dock")
        entries = current["persistent-apps"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["tile-data"]["file-data"]["_CFURLString"], managed.as_uri() + "/")
        self.assertEqual(current["persistent-others"], ["Downloads"])
        self.assertEqual(current["tilesize"], 64)
        managed.rmdir()
        self.assertEqual(restore.dock_entries(items, applications)[0]["tile-data"]["file-data"]["_CFURLString"], original.as_uri() + "/")

    def test_empty_dock_does_not_write_or_mark_complete(self):
        source = Path(self.temporary.name) / "source"
        source.mkdir()
        (source / "dock.json").write_text("[]")
        preferences = FakePreferences()
        with self.assertRaisesRegex(RuntimeError, "No Dock applications"):
            restore.restore_desktop("dock", source, self.home, preferences, once=True)
        self.assertEqual(preferences.writes, 0)
        self.assertFalse(self.home.exists())

    def test_zed_setup_merges_jsonc_and_reports_pending_downloads(self):
        target = self.home / ".config/zed/settings.json"
        target.parent.mkdir(parents=True)
        target.write_text('{// user comment\n"buffer_font_size": 19, "auto_install_extensions": {"extra": true},}')
        extensions = [{"id": "nix", "version": "1"}]
        editors.setup_zed(extensions, self.home)
        value = json.loads(target.read_text())
        self.assertEqual(value["buffer_font_size"], 19)
        self.assertEqual(value["auto_install_extensions"], {"extra": True, "nix": True})
        with self.assertRaisesRegex(RuntimeError, "not installed yet"):
            editors.verify_zed(extensions, self.home)
        installed = self.home / "Library/Application Support/Zed/extensions/installed/nix/extension.toml"
        installed.parent.mkdir(parents=True)
        installed.touch()
        editors.verify_zed(extensions, self.home)

    def test_code_setup_keeps_installed_extensions_and_collects_failures(self):
        cli = Path(self.temporary.name) / "code"
        cli.touch(mode=0o700)
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            if "--list-extensions" in args:
                return subprocess.CompletedProcess(args, 0, "EXISTING.extension\n", "")
            return subprocess.CompletedProcess(args, int(args[-1] == "missing.extension"))

        with self.assertRaisesRegex(RuntimeError, "missing.extension"):
            editors.setup_code([{"id": x} for x in ["existing.extension", "missing.extension", "another.extension"]], cli, run)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[-1][-1], "another.extension")

    def run_editor_setup(self, editor, *options):
        arguments = ["setup-editors", editor, "--source", str(self.source), "--home", str(self.home), *options]
        with patch.object(sys, "argv", arguments), patch.object(editors.os, "geteuid", return_value=501):
            return editors.main()

    def test_editor_selection_only_seeds_selected_settings(self):
        for selected, other in [("code", "zed"), ("zed", "code")]:
            with self.subTest(editor=selected):
                self.home = Path(self.temporary.name) / selected
                with patch.object(editors, "setup_code") as code, patch.object(editors, "setup_zed") as zed:
                    self.assertEqual(self.run_editor_setup(selected), 0)
                files = json.loads((self.source / "editor-files.json").read_text())
                self.assertTrue((self.home / files[f"{selected}-settings.json"]).is_file())
                self.assertFalse((self.home / files[f"{other}-settings.json"]).exists())
                self.assertEqual(code.called, selected == "code")
                self.assertEqual(zed.called, selected == "zed")

    def test_unselected_editor_cannot_block_setup(self):
        self.home.mkdir()
        (self.home / ".config").write_text("Cannot create Zed settings under this file")
        with patch.object(editors, "setup_code") as setup:
            self.assertEqual(self.run_editor_setup("code"), 0)
        setup.assert_called_once()

    def test_all_editors_continue_after_seeding_failure(self):
        self.home.mkdir()
        (self.home / "Library").write_text("Cannot create VS Code settings under this file")
        with patch.object(editors, "setup_code") as code, patch.object(editors, "setup_zed") as zed:
            self.assertEqual(self.run_editor_setup("all"), 1)
        code.assert_not_called()
        zed.assert_called_once()
        self.assertTrue((self.home / ".config/zed/settings.json").is_file())

    def test_editor_verification_does_not_seed_settings(self):
        with patch.object(editors, "verify_zed") as verify:
            self.assertEqual(self.run_editor_setup("zed", "--verify"), 0)
        verify.assert_called_once()
        self.assertFalse(self.home.exists())

    def test_developer_tools_require_full_xcode_and_completed_first_launch(self):
        def run(args, **kwargs):
            outputs = {"-p": "/Applications/Xcode.app/Contents/Developer", "--show-sdk-path": "/sdk", "clang": "/clang"}
            return subprocess.CompletedProcess(args, 0, outputs.get(args[-1], "ready"), "")

        self.assertEqual(development.verify(run, lambda _: True), 0)

        def incomplete(args, **kwargs):
            if "-checkFirstLaunchStatus" in args:
                return subprocess.CompletedProcess(args, 1, "", "")
            return run(args, **kwargs)

        self.assertEqual(development.verify(incomplete, lambda _: True), 1)

        def clt_only(args, **kwargs):
            if args[-1] == "-p":
                return subprocess.CompletedProcess(args, 0, "/Library/Developer/CommandLineTools", "")
            return run(args, **kwargs)

        self.assertEqual(development.verify(clt_only, lambda _: True), 1)

    def test_captured_terminal_is_valid_binary_plist(self):
        captured = plistlib.loads((self.source / "terminal.plist").read_bytes())
        self.assertIn(captured["Startup Window Settings"], captured["Window Settings"])


if __name__ == "__main__":
    unittest.main()
