"""Migration behavior: existing user configuration must survive rebuilds."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("seed_settings", ROOT / "scripts/seed-settings.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SeedSettingsTests(unittest.TestCase):
    def test_fresh_home_and_repeated_run(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder) / "Home with spaces"
            MODULE.seed(ROOT / "settings", home, Path("/nix/store/test-flutter"))
            settings = home / "Library/Application Support/Code/User/settings.json"
            self.assertEqual(json.loads(settings.read_text())["dart.flutterSdkPath"], "/nix/store/test-flutter")
            settings.write_text('{"userEdit": true}\n')
            MODULE.seed(ROOT / "settings", home, Path("/nix/store/new-flutter"))
            self.assertEqual(json.loads(settings.read_text()), {"userEdit": True})

    def test_existing_broken_symlink_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            settings = home / ".config/zed/settings.json"
            settings.parent.mkdir(parents=True)
            settings.symlink_to(home / "missing-external-config")
            MODULE.seed(ROOT / "settings", home, Path("/nix/store/test-flutter"))
            self.assertTrue(settings.is_symlink())
            self.assertEqual(settings.readlink(), home / "missing-external-config")


if __name__ == "__main__":
    unittest.main()
