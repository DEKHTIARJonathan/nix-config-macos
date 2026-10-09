"""Exercise JDK discovery registration using only temporary directories."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import register_java


class JavaRegistrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.store = self.root / "store"
        self.registry = self.root / "JavaVirtualMachines"
        self.bundles = {version: self.bundle(version, "initial") for version in ("21", "25")}

    def bundle(self, version, revision):
        bundle = self.store / f"{revision}-zulu-{version}" / "Library/Java/JavaVirtualMachines" / f"zulu-{version}.jdk"
        for member in ("Contents/Info.plist", "Contents/Home/bin/java", "Contents/Home/bin/javac"):
            path = bundle / member
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"fixture {version} {member}")
        return bundle

    def register(self):
        register_java.register(self.bundles, self.registry, self.store)

    def test_installs_complete_bundles_and_repeated_activation_is_noop(self):
        self.register()
        for version, bundle in self.bundles.items():
            link = self.registry / f"nix-jdk-{version}.jdk"
            self.assertEqual(link.readlink(), bundle)
            self.assertTrue((link / "Contents/Info.plist").is_file())
            self.assertTrue((link / "Contents/Home/bin/javac").is_file())
        with patch.object(register_java.os, "replace", side_effect=AssertionError("unexpected rewrite")):
            self.register()

    def test_updates_and_rolls_back_links_without_touching_other_jdks(self):
        self.register()
        unrelated = self.registry / "vendor.jdk"
        unrelated.mkdir()
        (unrelated / "keep").write_text("user installation")
        original = self.bundles["21"]
        self.bundles["21"] = self.bundle("21", "upgrade")
        self.register()
        link = self.registry / "nix-jdk-21.jdk"
        self.assertEqual(link.readlink(), self.bundles["21"])
        self.bundles["21"] = original
        self.register()
        self.assertEqual(link.readlink(), original)
        self.assertEqual((unrelated / "keep").read_text(), "user installation")

    def test_repairs_dangling_managed_link(self):
        self.registry.mkdir()
        link = self.registry / "nix-jdk-21.jdk"
        link.symlink_to(self.store / "removed-generation/Library/Java/JavaVirtualMachines/zulu-21.jdk")
        self.register()
        self.assertEqual(link.readlink(), self.bundles["21"])

    def test_conflicts_are_preserved_and_preflight_prevents_partial_registration(self):
        self.registry.mkdir()
        destination = self.registry / "nix-jdk-25.jdk"
        for kind in ("file", "directory", "symlink", "dangling-symlink"):
            with self.subTest(kind=kind):
                if kind == "file":
                    destination.write_text("keep")
                elif kind == "directory":
                    destination.mkdir()
                else:
                    target = self.root / "unrelated"
                    if kind == "symlink":
                        target.mkdir()
                    destination.symlink_to(target)
                previous = destination.lstat()
                with self.assertRaisesRegex(RuntimeError, "Refusing"):
                    self.register()
                self.assertEqual(destination.lstat(), previous)
                self.assertFalse((self.registry / "nix-jdk-21.jdk").exists())
                if destination.is_symlink():
                    destination.unlink()
                    if target.exists():
                        target.rmdir()
                elif destination.is_dir():
                    destination.rmdir()
                else:
                    destination.unlink()

    def test_incomplete_bundle_and_symlinked_registry_are_refused(self):
        (self.bundles["25"] / "Contents/Home/bin/javac").unlink()
        with self.assertRaisesRegex(RuntimeError, "Incomplete"):
            self.register()
        self.assertFalse(self.registry.exists())
        target = self.root / "unrelated"
        target.mkdir()
        self.registry.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, "symlinked Java registry"):
            self.register()
        self.assertEqual(list(target.iterdir()), [])

    def test_failed_replacement_preserves_old_link_and_is_retryable(self):
        self.register()
        previous = self.bundles["21"]
        self.bundles["21"] = self.bundle("21", "upgrade")
        with patch.object(register_java.os, "replace", side_effect=OSError("simulated failure")):
            with self.assertRaisesRegex(OSError, "simulated failure"):
                self.register()
        self.assertEqual((self.registry / "nix-jdk-21.jdk").readlink(), previous)
        self.assertFalse(list(self.registry.glob(".nix-jdks-*")))
        self.register()
        self.assertEqual((self.registry / "nix-jdk-21.jdk").readlink(), self.bundles["21"])


if __name__ == "__main__":
    unittest.main()
