"""Run generated Home Manager startup files in an isolated home via the Nix check."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.environ.get("ZSH_ENV_FILE"), "Generated startup files are supplied by the Nix check")
class ZshTests(unittest.TestCase):
    def test_subshells_preserve_project_toolchain(self):
        for interactive in (False, True):
            for nix_shell in (False, True):
                with self.subTest(interactive=interactive, nix_shell=nix_shell), tempfile.TemporaryDirectory() as directory:
                    home = Path(directory)
                    for variable, name in [("ZSH_ENV_FILE", ".zshenv"), ("ZSH_RC_FILE", ".zshrc")]:
                        content = Path(os.environ[variable]).read_text()
                        # Relocate generated cache/history/plugin paths to the fixture.
                        content = content.replace(os.environ["ZSH_HOME_DIRECTORY"], directory)
                        (home / name).write_text(content)
                    project = home / "project tools/bin"
                    cargo = home / ".cargo/bin"
                    for folder in (project, cargo):
                        folder.mkdir(parents=True)
                        (folder / "node").write_text("#!/bin/sh\nexit 0\n")
                        (folder / "node").chmod(0o755)
                    (home / ".cargo/env").write_text('export PATH="$HOME/.cargo/bin:$PATH"\n')
                    environment = {
                        "HOME": directory,
                        "ZDOTDIR": directory,
                        "PATH": f"{project}:/run/current-system/sw/bin:/usr/bin:/bin",
                        "TERM": "dumb",
                    }
                    if nix_shell:
                        environment["IN_NIX_SHELL"] = "impure"
                    result = subprocess.run(
                        [os.environ["ZSH_TEST_BIN"], "-dic" if interactive else "-dc",
                         'print -r -- "NODE:$commands[node]"; print -r -- "PATH:$PATH"'],
                        env=environment, capture_output=True, text=True, check=True,
                    )
                    lines = result.stdout.splitlines()
                    self.assertIn(f"NODE:{project}/node", lines)
                    paths = next(line.removeprefix("PATH:").split(":") for line in lines if line.startswith("PATH:"))
                    self.assertEqual(paths[0], str(project))
                    self.assertIn(str(cargo), paths)
                    self.assertEqual(paths.count("/run/current-system/sw/bin"), 1)


if __name__ == "__main__":
    unittest.main()
