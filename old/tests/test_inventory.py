"""README formatting may change; package data must still be checked."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("inventory", ROOT / "scripts/inventory.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class InventoryFormattingTests(unittest.TestCase):
    def test_wrapping_and_table_alignment_do_not_change_inventory(self):
        compact = "Package inventory.\n\n| Item | Version |\n|---|---|\n| Tool | 1.2 |\n"
        formatted = "Package\ninventory.\n\n| Item   | Version |\n| ------ | ------- |\n| Tool   | 1.2     |\n"
        self.assertEqual(MODULE.comparable_markdown(compact), MODULE.comparable_markdown(formatted))
        self.assertNotEqual(
            MODULE.comparable_markdown(compact),
            MODULE.comparable_markdown(formatted.replace("1.2", "1.3")),
        )
