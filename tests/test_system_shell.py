"""Exercise system Bash migration without touching live /etc files."""

import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_system_shell


class SystemShellTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.etc = Path(temporary.name)
        self.bashrc = self.etc / "bashrc"

    def test_preserves_bytes_mode_and_existing_backup_and_retries_are_noops(self):
        original = b"# Custom Bash setup\n\xff\n"
        self.bashrc.write_bytes(original)
        self.bashrc.chmod(0o640)
        existing = self.etc / "bashrc.before-nix-darwin"
        existing.write_text("old backup")
        prepare_system_shell.prepare(self.etc)
        backups = list(self.etc.glob("bashrc.before-nix-darwin.*/bashrc"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), original)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE(backups[0].parent.stat().st_mode), 0o700)
        self.assertEqual(existing.read_text(), "old backup")
        prepare_system_shell.prepare(self.etc)
        self.bashrc.symlink_to(self.etc / "static/bashrc")
        prepare_system_shell.prepare(self.etc)
        self.assertEqual(self.bashrc.readlink(), self.etc / "static/bashrc")
        self.assertEqual(
            list(self.etc.glob("bashrc.before-nix-darwin.*/bashrc")), backups
        )

    def test_refuses_unrelated_symlink_and_directory(self):
        target = self.etc / "custom"
        target.write_text("keep")
        for destination in (target, self.etc / "missing"):
            self.bashrc.symlink_to(destination)
            with self.assertRaises(RuntimeError):
                prepare_system_shell.prepare(self.etc)
            self.assertEqual(self.bashrc.readlink(), destination)
            self.bashrc.unlink()
        self.assertEqual(target.read_text(), "keep")
        self.bashrc.mkdir()
        with self.assertRaises(RuntimeError):
            prepare_system_shell.prepare(self.etc)
        self.assertEqual(list(self.etc.glob("bashrc.before-nix-darwin*")), [])

    def test_failed_backup_leaves_original_and_can_retry(self):
        self.bashrc.write_text("keep")
        with (
            patch.object(Path, "rename", side_effect=OSError("failed backup")),
            self.assertRaises(OSError),
        ):
            prepare_system_shell.prepare(self.etc)
        self.assertEqual(self.bashrc.read_text(), "keep")
        self.assertEqual(list(self.etc.glob("bashrc.before-nix-darwin*")), [])
        prepare_system_shell.prepare(self.etc)
        self.assertFalse(self.bashrc.exists())
