"""Run generated Home Manager startup files in an isolated home via the Nix check."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from restore_settings import seed_zshrc


def write_startup_files(home):
    for variable, name in [("ZSH_ENV_FILE", ".zshenv"), ("ZSH_RC_FILE", ".config/zsh/nix-zshrc")]:
        content = Path(os.environ[variable]).read_text()
        destination = home / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content.replace(os.environ["ZSH_HOME_DIRECTORY"], str(home)))
    seed_zshrc(home)


@unittest.skipUnless(os.environ.get("ZSH_ENV_FILE"), "Generated startup files are supplied by the Nix check")
class ZshTests(unittest.TestCase):
    def test_writable_entry_point_retains_app_edits_and_loads_managed_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            write_startup_files(home)
            with (home / ".zshrc").open("a") as stream:
                stream.write('export APP_SETTING="preserved"\n')
            with (home / ".config/zsh/nix-zshrc").open("a") as stream:
                stream.write('export MANAGED_SETTING="updated"\n')
            seed_zshrc(home)
            result = subprocess.run(
                [os.environ["ZSH_TEST_BIN"], "-dic", 'print -r -- "$APP_SETTING:$MANAGED_SETTING"'],
                env={"HOME": directory, "ZDOTDIR": directory, "PATH": "/usr/bin:/bin",
                     "TERM": "dumb", "__ETC_ZSHENV_SOURCED": "1"},
                capture_output=True, text=True, check=True,
            )
            self.assertIn("preserved:updated", result.stdout.splitlines())

    def test_docker_desktop_tools_preserve_inherited_precedence(self):
        for interactive in (False, True):
            for inherited_docker in ("missing", "desktop", "project"):
                with self.subTest(interactive=interactive, inherited_docker=inherited_docker), tempfile.TemporaryDirectory() as directory:
                    home = Path(directory)
                    write_startup_files(home)
                    docker = home / ".docker/bin"
                    project = home / "project tools/bin"
                    docker.mkdir(parents=True)
                    project.mkdir(parents=True)
                    completions = home / ".docker/completions"
                    completions.mkdir(parents=True)
                    (completions / "_docker").write_text("#compdef docker\n_docker() { :; }\n")
                    for tool in (docker / "docker", docker / "docker-credential-desktop", project / "docker"):
                        tool.write_text("#!/bin/sh\nexit 0\n")
                        tool.chmod(0o755)
                    environment = {
                        "HOME": directory,
                        "ZDOTDIR": directory,
                        "PATH": {"missing": "/usr/bin:/bin", "desktop": f"{docker}:/usr/bin:/bin",
                                 "project": f"{project}:/usr/bin:/bin"}[inherited_docker],
                        "TERM": "dumb",
                        "__ETC_ZSHENV_SOURCED": "1",
                    }
                    result = subprocess.run(
                        [os.environ["ZSH_TEST_BIN"], "-dic" if interactive else "-dc",
                         'print -r -- "DOCKER:$commands[docker]"; '
                         'print -r -- "HELPER:$commands[docker-credential-desktop]"; '
                         'print -r -- "FPATH:$FPATH"; '
                         'print -r -- "COMPLETION:${_comps[docker]}"; '
                         'print -r -- "PATH:$PATH"'],
                        env=environment, capture_output=True, text=True, check=True,
                    )
                    lines = result.stdout.splitlines()
                    self.assertIn(f"DOCKER:{project if inherited_docker == 'project' else docker}/docker", lines)
                    self.assertIn(f"HELPER:{docker}/docker-credential-desktop", lines)
                    paths = next(line.removeprefix("PATH:").split(":") for line in lines if line.startswith("PATH:"))
                    self.assertEqual(paths.count(str(docker)), 1)
                    fpaths = next(line.removeprefix("FPATH:").split(":") for line in lines if line.startswith("FPATH:"))
                    self.assertEqual(fpaths.count(str(completions)), 1)
                    if interactive:
                        self.assertIn("COMPLETION:_docker", lines)

    def test_cargo_tools_are_available_without_env_setup_and_path_stays_unique(self):
        for interactive in (False, True):
            for env_file in (False, True):
                with self.subTest(interactive=interactive, env_file=env_file), tempfile.TemporaryDirectory() as directory:
                    home = Path(directory)
                    write_startup_files(home)
                    cargo = home / ".cargo/bin"
                    project = home / "project tools/bin"
                    for folder in (cargo, project):
                        folder.mkdir(parents=True)
                        tool = folder / "cargo-path-test-tool"
                        tool.write_text("#!/bin/sh\nexit 0\n")
                        tool.chmod(0o755)
                    if env_file:
                        (home / ".cargo/env").write_text('# Existing env file without a PATH update\n')
                    environment = {
                        "HOME": directory, "ZDOTDIR": directory,
                        "PATH": "/usr/bin:/bin", "TERM": "dumb",
                        "__ETC_ZSHENV_SOURCED": "1",
                    }
                    command = ('source "$HOME/.zshenv"; '
                               'print -r -- "TOOL:$commands[cargo-path-test-tool]"; '
                               'print -r -- "PATH:$PATH"')
                    for inherited_project in (False, True):
                        if inherited_project:
                            environment["PATH"] = f"{project}:/usr/bin:/bin"
                        result = subprocess.run(
                            [os.environ["ZSH_TEST_BIN"], "-dic" if interactive else "-dc", command],
                            env=environment, capture_output=True, text=True, check=True,
                        )
                        lines = result.stdout.splitlines()
                        expected = project if inherited_project else cargo
                        self.assertIn(f"TOOL:{expected}/cargo-path-test-tool", lines)
                        paths = next(line.removeprefix("PATH:").split(":") for line in lines if line.startswith("PATH:"))
                        self.assertEqual(paths.count(str(cargo)), 1)
                        self.assertLess(paths.index("/run/current-system/sw/bin"), paths.index(str(cargo)))
                        if inherited_project:
                            self.assertEqual(paths[0], str(project))

    def test_subshells_preserve_project_toolchain(self):
        for interactive in (False, True):
            for nix_shell in (False, True):
                with self.subTest(interactive=interactive, nix_shell=nix_shell), tempfile.TemporaryDirectory() as directory:
                    home = Path(directory)
                    write_startup_files(home)
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
                        # Even -d reads /etc/zshenv. Isolate these HM unit tests
                        # from the real host's newly activated Darwin bootstrap.
                        "__ETC_ZSHENV_SOURCED": "1",
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
