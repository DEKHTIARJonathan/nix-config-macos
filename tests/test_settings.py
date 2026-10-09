"""Exercise migration behavior without touching the real user's preferences."""

import copy
import json
import os
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


@unittest.skipUnless(os.environ.get("PRE_ACTIVATION_FILE"), "Generated activation script is supplied by the Nix check")
class RosettaActivationTests(unittest.TestCase):
    def test_installation_skip_verification_and_failure_propagation(self):
        script = Path(os.environ["PRE_ACTIVATION_FILE"]).read_text()
        # Replace absolute Apple commands before execution: these tests never
        # install software or depend on the host's actual Rosetta state.
        script = script.replace("/usr/bin/arch", "mock_arch")
        script = script.replace("/usr/sbin/softwareupdate", "mock_softwareupdate")
        harness = '''
            set -e
            rosetta_ready=$ROSETTA_READY
            mock_arch() {
                printf 'probe %s\\n' "$*" >> "$ROSETTA_LOG"
                test "$rosetta_ready" = 1
            }
            mock_softwareupdate() {
                printf 'install %s\\n' "$*" >> "$ROSETTA_LOG"
                if test "$ROSETTA_INSTALL_FAILS" = 1; then return 42; fi
                rosetta_ready=$ROSETTA_INSTALL_WORKS
            }
        '''
        cases = [
            # ready, installer fails, installation works, success, probes, installs
            (True, False, False, True, 2, 0),
            (False, False, True, True, 3, 1),
            (False, True, False, False, 1, 1),
            (False, False, False, False, 2, 1),
        ]
        for ready, fails, works, success, probes, installs in cases:
            with self.subTest(ready=ready, fails=fails, works=works), tempfile.TemporaryDirectory() as directory:
                log = Path(directory) / "commands.log"
                result = subprocess.run(
                    ["/bin/sh", "-c", harness + script + script + '\nprintf "activation continued\\n"\n'],
                    env={"PATH": os.defpath, "ROSETTA_LOG": str(log),
                         "ROSETTA_READY": str(int(ready)), "ROSETTA_INSTALL_FAILS": str(int(fails)),
                         "ROSETTA_INSTALL_WORKS": str(int(works))},
                    capture_output=True, text=True,
                )
                self.assertEqual(result.returncode == 0, success, result.stderr)
                self.assertEqual("activation continued" in result.stdout, success)
                commands = log.read_text().splitlines()
                self.assertEqual(commands.count("probe -x86_64 /usr/bin/true"), probes)
                self.assertEqual(commands.count("install --install-rosetta --agree-to-license"), installs)
                self.assertEqual(len(commands), probes + installs)


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / "Home with spaces"
        self.source = ROOT / "settings"

    def test_zshrc_migrates_managed_link_without_changing_store_file(self):
        store = Path(self.temporary.name) / "store"
        generated = store / "example-home-manager-files/.zshrc"
        generated.parent.mkdir(parents=True)
        generated.write_bytes(b"# generated configuration\n")
        generated.chmod(0o444)
        self.home.mkdir()
        target = self.home / ".zshrc"
        target.symlink_to(generated)
        restore.seed_zshrc(self.home, store=store)
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertIn(b'source "$HOME/.config/zsh/nix-zshrc"', target.read_bytes())
        self.assertNotIn(b"# generated configuration", target.read_bytes())
        self.assertEqual(generated.read_bytes(), b"# generated configuration\n")
        backups = list((restore.state_directory(self.home) / "backups").iterdir())
        self.assertEqual([p.read_bytes() for p in backups], [generated.read_bytes()])
        self.assertFalse(backups[0].is_symlink())
        with target.open("ab") as stream:
            stream.write(b"# Docker additions\n")
        previous = target.read_bytes()
        restore.seed_zshrc(self.home, store=store)
        self.assertEqual(target.read_bytes(), previous)
        self.assertEqual(list(backups[0].parent.iterdir()), backups)

    def test_zshrc_adopts_existing_file_and_preserves_content(self):
        self.home.mkdir()
        target = self.home / ".zshrc"
        original = b"# existing user settings\nexport PERSONAL=value\n"
        target.write_bytes(original)
        restore.seed_zshrc(self.home)
        self.assertTrue(target.read_bytes().endswith(original))
        backups = list((restore.state_directory(self.home) / "backups").iterdir())
        self.assertEqual([p.read_bytes() for p in backups], [original])

    def test_zshrc_preserves_unmanaged_and_dangling_symlinks(self):
        self.home.mkdir()
        external = self.home / "external"
        external.write_bytes(b"unchanged")
        for destination in (external, self.home / "absent"):
            with self.subTest(destination=destination):
                target = self.home / ".zshrc"
                target.symlink_to(destination)
                with self.assertRaisesRegex(RuntimeError, "unmanaged symlink"):
                    restore.seed_zshrc(self.home)
                self.assertEqual(target.readlink(), destination)
                self.assertEqual(external.read_bytes(), b"unchanged")
                self.assertFalse(restore.state_directory(self.home).exists())
                target.unlink()

    def test_zshrc_dry_run_and_failed_write_are_retryable(self):
        restore.seed_zshrc(self.home, dry_run=True)
        self.assertFalse(self.home.exists())
        self.home.mkdir()
        target = self.home / ".zshrc"
        target.write_bytes(b"# existing settings\n")
        with patch.object(restore.os, "replace", side_effect=OSError("simulated write failure")):
            with self.assertRaises(OSError):
                restore.seed_zshrc(self.home)
        self.assertEqual(target.read_bytes(), b"# existing settings\n")
        restore.seed_zshrc(self.home)
        self.assertTrue(target.read_bytes().endswith(b"# existing settings\n"))

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

    def test_editor_fonts_preserve_settings_backup_and_repeat_without_writes(self):
        restore.seed_editors(self.source, self.home)
        code = self.home / "Library/Application Support/Code/User/settings.json"
        zed = self.home / ".config/zed/settings.json"
        original_code = b'''{// personal settings
          "terminal.integrated.fontFamily": "Menlo",
          "terminal.integrated.fontSize": 17,
          "editor.fontFamily": "Other font",
          "workbench.settings.applyToAllProfiles": ["editor.fontSize"],
        }'''
        original_zed = b'{"terminal": {"font_size": 19, "font_family": "Menlo"}, "ui_font_size": 16}'
        code.write_bytes(original_code)
        zed.write_bytes(original_zed)
        restore.restore_editor_fonts(self.source, self.home, dry_run=True)
        self.assertEqual(code.read_bytes(), original_code)
        self.assertFalse(restore.state_directory(self.home).exists())
        restore.restore_editor_fonts(self.source, self.home)
        updated_code = json.loads(code.read_text())
        self.assertEqual(updated_code["terminal.integrated.fontFamily"], "'MesloLGS NF'")
        self.assertEqual(updated_code["terminal.integrated.fontSize"], 17)
        self.assertEqual(updated_code["editor.fontFamily"], "Other font")
        self.assertEqual(updated_code["workbench.settings.applyToAllProfiles"],
                         ["editor.fontSize", "terminal.integrated.fontFamily"])
        updated_zed = json.loads(zed.read_text())
        self.assertEqual(updated_zed, {"terminal": {"font_size": 19, "font_family": "MesloLGS NF"},
                                      "ui_font_size": 16})
        folder = restore.state_directory(self.home) / "backups"
        backups = list(folder.iterdir())
        self.assertCountEqual([p.read_bytes() for p in backups], [original_code, original_zed])
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in backups))
        with patch.object(restore, "atomic_write") as write:
            restore.restore_editor_fonts(self.source, self.home)
            write.assert_not_called()
        self.assertCountEqual(list(folder.iterdir()), backups)

    def test_editor_fonts_skip_missing_files_and_refuse_symlinks(self):
        restore.restore_editor_fonts(self.source, self.home)
        self.assertFalse(self.home.exists())
        code = self.home / "Library/Application Support/Code/User/settings.json"
        code.parent.mkdir(parents=True)
        external = self.home / "external.json"
        external.write_text('{}')
        for destination in (external, self.home / "absent"):
            code.symlink_to(destination)
            with self.assertRaisesRegex(RuntimeError, "symlink"):
                restore.restore_editor_fonts(self.source, self.home)
            self.assertEqual(code.readlink(), destination)
            self.assertEqual(external.read_text(), '{}')
            code.unlink()
        code.parent.rename(code.parent.with_name("RealUser"))
        code.parent.symlink_to(code.parent.with_name("RealUser"), target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            restore.restore_editor_fonts(self.source, self.home)
        self.assertFalse(restore.state_directory(self.home).exists())

    def test_editor_fonts_invalid_settings_are_preserved(self):
        code = self.home / "Library/Application Support/Code/User/settings.json"
        code.parent.mkdir(parents=True)
        for content in ('broken', '[]', '{"workbench.settings.applyToAllProfiles": null}',
                        '{"duplicate": 1, "duplicate": 2}'):
            code.write_text(content)
            with self.assertRaises(ValueError):
                restore.restore_editor_fonts(self.source, self.home)
            self.assertEqual(code.read_text(), content)
            self.assertFalse(restore.state_directory(self.home).exists())

    def test_editor_font_failed_write_preserves_original_and_can_retry(self):
        code = self.home / "Library/Application Support/Code/User/settings.json"
        code.parent.mkdir(parents=True)
        code.write_bytes(b'{}')
        replace = restore.os.replace

        def fail_settings_write(source, target):
            if target == code:
                raise OSError("simulated write failure")
            return replace(source, target)

        with patch.object(restore.os, "replace", side_effect=fail_settings_write):
            with self.assertRaises(OSError):
                restore.restore_editor_fonts(self.source, self.home)
        self.assertEqual(code.read_bytes(), b'{}')
        backups = list((restore.state_directory(self.home) / "backups").iterdir())
        self.assertEqual([p.read_bytes() for p in backups], [b'{}'])
        restore.restore_editor_fonts(self.source, self.home)
        self.assertEqual(json.loads(code.read_text())["terminal.integrated.fontFamily"], "'MesloLGS NF'")

    def test_gitkraken_fonts_preserve_profiles_and_backup_only_on_change(self):
        targets = [self.home / f".gitkraken/profiles/{name}/profile" for name in ("one", "two")]
        original = b'{"cli":{"fontFamily":"Menlo","fontSize":17},"editor":{"fontFamily":"Menlo"},"other":true}'
        for target in targets:
            target.parent.mkdir(parents=True)
            target.write_bytes(original)
        restore.restore_gitkraken_fonts(self.source, self.home, dry_run=True)
        self.assertFalse(restore.state_directory(self.home).exists())
        self.assertTrue(all(target.read_bytes() == original for target in targets))
        restore.restore_gitkraken_fonts(self.source, self.home)
        for target in targets:
            self.assertEqual(json.loads(target.read_bytes()), {
                "cli": {"fontFamily": '"MesloLGS NF"', "fontSize": 17},
                "editor": {"fontFamily": "Menlo"}, "other": True,
            })
        backups = list((restore.state_directory(self.home) / "backups").iterdir())
        self.assertEqual([p.read_bytes() for p in backups], [original, original])
        self.assertTrue(all(p.stat().st_mode & 0o777 == 0o600 for p in backups))
        with patch.object(restore, "atomic_write") as write, patch.object(restore.subprocess, "run") as run:
            restore.restore_gitkraken_fonts(self.source, self.home)
            write.assert_not_called()
            run.assert_not_called()

    def test_gitkraken_fonts_failed_write_is_retryable(self):
        target = self.home / ".gitkraken/profiles/one/profile"
        target.parent.mkdir(parents=True)
        target.write_bytes(b'{}')
        replace = restore.os.replace

        def fail_profile_write(source, destination):
            if destination == target:
                raise OSError("simulated write failure")
            return replace(source, destination)

        with patch.object(restore.os, "replace", side_effect=fail_profile_write):
            with self.assertRaises(OSError):
                restore.restore_gitkraken_fonts(self.source, self.home)
        self.assertEqual(target.read_bytes(), b'{}')
        restore.restore_gitkraken_fonts(self.source, self.home)
        self.assertEqual(json.loads(target.read_bytes())["cli"]["fontFamily"], '"MesloLGS NF"')

    def test_gitkraken_fonts_migrate_unquoted_value_rejected_by_app(self):
        target = self.home / ".gitkraken/profiles/one/profile"
        target.parent.mkdir(parents=True)
        original = b'{"cli":{"fontFamily":"MesloLGS NF","fontSize":14},"editor":{"fontFamily":"Menlo"}}'
        target.write_bytes(original)
        restore.restore_gitkraken_fonts(self.source, self.home)
        settings = json.loads(target.read_bytes())
        # Literal option value emitted by GitKraken 12.6's font selector. Its
        # startup validation resets any unmatched value to the default font.
        self.assertEqual(settings["cli"]["fontFamily"], '"MesloLGS NF"')
        self.assertEqual(settings["cli"]["fontSize"], 14)
        self.assertEqual(settings["editor"]["fontFamily"], "Menlo")
        backups = list((restore.state_directory(self.home) / "backups").iterdir())
        self.assertEqual([p.read_bytes() for p in backups], [original])
        with patch.object(restore, "atomic_write") as write:
            restore.restore_gitkraken_fonts(self.source, self.home)
            write.assert_not_called()

    def test_gitkraken_fonts_preserve_invalid_files_and_refuse_symlinks(self):
        restore.restore_gitkraken_fonts(self.source, self.home)
        self.assertFalse(self.home.exists())
        target = self.home / ".gitkraken/profiles/one/profile"
        target.parent.mkdir(parents=True)
        for content in ('broken', '[]', '{"cli":null}', '{"cli":{},"cli":{}}'):
            target.write_text(content)
            with self.assertRaises(ValueError):
                restore.restore_gitkraken_fonts(self.source, self.home)
            self.assertEqual(target.read_text(), content)
        target.unlink()
        target.symlink_to(self.home / "absent")
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            restore.restore_gitkraken_fonts(self.source, self.home)
        target.unlink()
        target.parent.rename(target.parent.with_name("real"))
        target.parent.symlink_to(target.parent.with_name("real"), target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            restore.restore_gitkraken_fonts(self.source, self.home)
        self.assertFalse(restore.state_directory(self.home).exists())

    def test_editor_keybindings_preserve_other_actions_and_are_idempotent(self):
        restore.seed_editors(self.source, self.home)
        code = self.home / "Library/Application Support/Code/User/keybindings.json"
        profile = code.parent / "profiles/custom/keybindings.json"
        profile.parent.mkdir(parents=True)
        empty_profile = code.parent / "profiles/new/keybindings.json"
        empty_profile.parent.mkdir(parents=True)
        zed = self.home / ".config/zed/keymap.json"
        code_original = b'[{"key":"shift+enter","command":"userAction","when":"editorTextFocus"}]'
        zed_original = b'[{"context":"Editor","bindings":{"shift-enter":"userAction"}}]'
        for target, content in ((code, code_original), (profile, code_original), (zed, zed_original)):
            target.write_bytes(content)
        restore.restore_editor_keybindings(self.source, self.home, dry_run=True)
        self.assertEqual(code.read_bytes(), code_original)
        self.assertFalse(restore.state_directory(self.home).exists())
        restore.restore_editor_keybindings(self.source, self.home)
        self.assertEqual(json.loads(empty_profile.read_bytes())[-1]["when"], "terminalFocus")
        for target in (code, profile):
            updated = json.loads(target.read_bytes())
            self.assertEqual(updated[:-1], json.loads(code_original))
            self.assertEqual(updated[-1]["when"], "terminalFocus")
            self.assertEqual(updated[-1]["args"]["text"], "\x1b[13;2u")
        updated = json.loads(zed.read_bytes())
        self.assertEqual(updated[:-1], json.loads(zed_original))
        self.assertEqual(updated[-1], {"context": "Terminal", "bindings": {
            "shift-enter": ["terminal::SendText", "\x1b[13;2u"]}})
        with patch.object(restore, "atomic_write") as write:
            restore.restore_editor_keybindings(self.source, self.home)
            write.assert_not_called()
        backups = list((restore.state_directory(self.home) / "backups").iterdir())
        self.assertCountEqual([p.read_bytes() for p in backups], [code_original, code_original, zed_original])

    def test_editor_keybindings_missing_invalid_and_symlink_files(self):
        restore.restore_editor_keybindings(self.source, self.home)
        self.assertFalse(self.home.exists())
        target = self.home / "Library/Application Support/Code/User/keybindings.json"
        target.parent.mkdir(parents=True)
        for content in ('broken', '{}', '[null]', '[{"key":1,"key":2}]'):
            target.write_text(content)
            with self.assertRaises(ValueError):
                restore.restore_editor_keybindings(self.source, self.home)
            self.assertEqual(target.read_text(), content)
        target.unlink()
        target.symlink_to(self.home / "absent")
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            restore.restore_editor_keybindings(self.source, self.home)
        self.assertFalse(restore.state_directory(self.home).exists())
        target.unlink()
        restore.restore_editor_keybindings(self.source, self.home, dry_run=True)
        self.assertFalse(target.exists())
        restore.restore_editor_keybindings(self.source, self.home)
        self.assertEqual(json.loads(target.read_bytes())[-1]["args"]["text"], "\x1b[13;2u")

    def test_editor_keybindings_failed_write_preserves_original_for_retry(self):
        target = self.home / ".config/zed/keymap.json"
        target.parent.mkdir(parents=True)
        target.write_bytes(b'[]')
        replace = restore.os.replace

        def fail_keymap_write(source, destination):
            if destination == target:
                raise OSError("simulated write failure")
            return replace(source, destination)

        with patch.object(restore.os, "replace", side_effect=fail_keymap_write):
            with self.assertRaises(OSError):
                restore.restore_editor_keybindings(self.source, self.home)
        self.assertEqual(target.read_bytes(), b'[]')
        restore.restore_editor_keybindings(self.source, self.home)
        self.assertEqual(json.loads(target.read_bytes())[-1]["context"], "Terminal")

    def test_all_once_repairs_gitkraken_without_querying_or_stopping_processes(self):
        target = self.home / ".gitkraken/profiles/one/profile"
        target.parent.mkdir(parents=True)
        target.write_bytes(b'{}')
        arguments = ["restore_settings", "all", "--once", "--home", str(self.home), "--source", str(self.source)]
        with patch.object(sys, "argv", arguments), patch.object(restore.os, "geteuid", return_value=501), \
                patch.object(restore.subprocess, "run", side_effect=AssertionError("Must not query or stop GitKraken")), \
                patch.object(restore, "Preferences", return_value=FakePreferences()), \
                patch.object(restore, "restore_desktop"):
            self.assertEqual(restore.main(), 0)
        self.assertEqual(json.loads(target.read_bytes())["cli"]["fontFamily"], '"MesloLGS NF"')
        keymap = self.home / ".config/zed/keymap.json"
        self.assertEqual(json.loads(keymap.read_bytes())[-1]["context"], "Terminal")

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
        for name in ["Basic (Shift-Enter)", "Clear Dark", "Personal"]:
            keys = current["Window Settings"][name]["keyMapBoundKeys"]
            self.assertEqual(keys["$000D"], "\x1b[13;2u")
            self.assertEqual(keys["$0003"], "\x1b[13;2u")
        preferences.values[domain]["Default Window Settings"] = "Personal"
        restore.restore_desktop("terminal", self.source, self.home, preferences, once=True)
        self.assertEqual(preferences.writes, 1)
        self.assertEqual(preferences.read(domain)["Default Window Settings"], "Personal")
        restore.restore_desktop("terminal", self.source, self.home, preferences)
        self.assertEqual(preferences.writes, 2)

    def test_terminal_keybindings_migrate_existing_profiles_without_resetting_them(self):
        domain = "com.apple.Terminal"
        original = {
            "Default Window Settings": "Personal",
            "Window Settings": {
                "Personal": {"Font": b"custom font", "keyMapBoundKeys": {"F704": "custom"}},
                "Clear Dark": {"Font": b"modified font", "keyMapBoundKeys": {"$000D": "\r"}},
            },
            "unrelated": True,
        }
        preferences = FakePreferences({domain: original})
        marker = restore.state_directory(self.home) / "terminal-restored"
        marker.parent.mkdir(parents=True)
        marker.touch()
        restore.restore_desktop("terminal", self.source, self.home, preferences, once=True, dry_run=True)
        self.assertEqual(preferences.writes, 0)
        self.assertFalse((marker.parent / "backups").exists())

        restore.restore_desktop("terminal", self.source, self.home, preferences, once=True)
        current = preferences.read(domain)
        self.assertEqual(current["Default Window Settings"], "Personal")
        self.assertEqual(current["unrelated"], True)
        self.assertEqual(set(current["Window Settings"]), {"Personal", "Clear Dark"})
        for name, profile in current["Window Settings"].items():
            self.assertEqual(profile["Font"], original["Window Settings"][name]["Font"])
            self.assertEqual(profile["keyMapBoundKeys"]["$000D"], "\x1b[13;2u")
            self.assertEqual(profile["keyMapBoundKeys"]["$0003"], "\x1b[13;2u")
        self.assertEqual(current["Window Settings"]["Personal"]["keyMapBoundKeys"]["F704"], "custom")
        backup, = (marker.parent / "backups").iterdir()
        self.assertEqual(plistlib.loads(backup.read_bytes()), original)

        restore.restore_desktop("terminal", self.source, self.home, preferences, once=True)
        self.assertEqual(preferences.writes, 1)

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
