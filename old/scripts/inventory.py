#!/usr/bin/env python3
"""Validate the installation inventory and render its README tables."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START = "<!-- inventory:start -->"
END = "<!-- inventory:end -->"
SYSTEMS = ["aarch64-darwin", "x86_64-darwin"]


def load_inventory():
    inventory = json.loads((ROOT / "inventory.json").read_text())
    names, owners = set(), set()
    for item in inventory["items"]:
        assert item["name"] not in names, f"Duplicate item: {item['name']}"
        names.add(item["name"])
        assert item["provider"] in {"nix", "cask", "brew", "mas", "manual", "bundled", "macos"}
        assert item["notes"], f"Missing disposition: {item['name']}"
        assert set(item.get("systems", SYSTEMS)) <= set(SYSTEMS)
        if item["provider"] in {"nix", "cask", "brew", "mas"}:
            assert item["package"], f"Missing package: {item['name']}"
            owner = (item["provider"], item["package"])
            assert owner not in owners, f"Duplicate installer: {owner}"
            owners.add(owner)
        if item["provider"] == "mas":
            assert isinstance(item["package"], int)
    return inventory


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def comparable_markdown(text):
    """Ignore formatter-only wrapping and table separator alignment."""
    text = re.sub(r"(?m)^\|[ :|\-]+\|$", "<table-separator>", text)
    return " ".join(text.split())


def render(inventory):
    text = [START, "", f"Inventory captured {inventory['audited']}. Nix versions refer to the committed lockfile; Homebrew versions are audit-time observations, not pins.", ""]
    for category in ["Applications", "Developer tools", "Fonts", "Device components"]:
        text += [f"### {category}", "", "| Item | Installed | Install source | Available version | ARM / Intel | Difference / remaining setup |", "|---|---|---|---|---|---|"]
        for item in sorted((x for x in inventory["items"] if x["category"] == category), key=lambda x: x["name"].lower()):
            provider = item["provider"]
            label = {"nix": "pkgs.", "cask": "cask: ", "brew": "brew: ", "mas": "App Store: ", "manual": "Manual", "bundled": "Bundled: ", "macos": "macOS"}[provider]
            if item["package"]: label += str(item["package"])
            if item.get("url"): label = f"[{label}]({item['url']})"
            systems = item.get("systems", SYSTEMS)
            arch = " / ".join("yes" if system in systems else "no" for system in SYSTEMS)
            if provider in {"manual", "bundled", "macos"}: arch = "vendor / vendor" if provider == "manual" else "both"
            version = item.get("availableVersion", "store current" if provider == "mas" else "see notes")
            text.append("| " + " | ".join(cell(x) for x in [item["name"], item["installed"], label, version, arch, item["notes"]]) + " |")
        text.append("")
    text += ["### Homebrew dependency libraries", "", "These are resolved by their parent packages. Nix closures need not contain the same library versions or expose Homebrew's incidental executables globally.", "", "| Library | Observed version |", "|---|---|"]
    for item in json.loads((ROOT / "settings/dependencies.json").read_text()):
        text.append(f"| {cell(item['name'])} | {cell(item['version'])} |")
    text += ["", "### Editor extensions", "", "Availability below means an exact attribute was found in the 26.05 extension set; platform compatibility is not a build claim. Extensions are installed in writable editor profiles through their marketplaces.", "", "| Extension | Editor | Installed version | In nixpkgs.vscode-extensions |", "|---|---|---|---|"]
    for item in json.loads((ROOT / "settings/editor-extensions.json").read_text()):
        text.append(f"| `{item['id']}` | {item['editor']} | {item['version']} | {'yes' if item['nixAttribute'] else 'no exact attribute found'} |")
    text += ["", "### Browser extensions", "", "Restore through browser sync or each browser's extension store. The manifest preserves IDs for lookup; profiles, cookies and credentials are not included.", "", "| Browser | Extension | Version |", "|---|---|---|"]
    for item in json.loads((ROOT / "settings/browser-extensions.json").read_text()):
        text.append(f"| {item['browser']} | {cell(item['name'])} (`{cell(item['id'])}`) | {item['version']} |")
    text += ["", "### Ruby gems", "", "Non-default installed gems, newest version per name. Restore executable tools as user gems under Nix Ruby; dependencies should normally come from a project's Gemfile rather than a global copy of this list.", "", "| Gem | Version | Executables |", "|---|---|---|"]
    for item in json.loads((ROOT / "settings/ruby-gems.json").read_text()):
        text.append(f"| {item['name']} | {item['version']} | {', '.join(item['executables']) or 'dependency'} |")
    text += ["", END]
    return "\n".join(text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    inventory = load_inventory()
    path = ROOT / "README.md"
    old = path.read_text()
    assert old.count(START) == old.count(END) == 1, "README needs exactly one inventory section"
    new = old.split(START)[0] + render(inventory) + old.split(END)[1]
    if args.check:
        if comparable_markdown(old) != comparable_markdown(new):
            raise SystemExit("README tables are stale; run python3 scripts/inventory.py")
        print(f"Inventory valid: {len(inventory['items'])} unique items; README tables match.")
    else:
        path.write_text(new)


if __name__ == "__main__":
    main()
