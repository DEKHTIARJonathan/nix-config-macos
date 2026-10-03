# Validation

Inventory captured on 2026-09-29; implementation checked on 2026-09-30.

## Inputs

`flake.lock` pins these upstream revisions. Home Manager and nix-darwin both
follow the same nixpkgs input.

| Input        | Branch               | Revision                                   |
| ------------ | -------------------- | ------------------------------------------ |
| nixpkgs      | nixpkgs-26.05-darwin | `dc8993a5c130c05a8565579014968a112d416d76` |
| nix-darwin   | nix-darwin-26.05     | `c3e90c89649b07d1a96e4b9dd6cd0d6e44b91a74` |
| Home Manager | release-26.05        | `a6631107a83ceab5872f298a2ea710859c80c4cb` |

The lockfile uses GitHub references and Nix-generated content hashes, with no
local paths. Evaluation used complete source archives at these revisions.
Independent `nix hash path` checks of all three source trees match the lockfile.

## Passed

- Both complete nix-darwin system derivations evaluate, including Home Manager,
  all selected packages and their transitive dependencies.
- The actual `flake.nix` output function evaluates for both architectures:
  configurations, development shells, formatters, repository check derivations
  and package audits.
- All 71 selected Nix inventory entries on Apple Silicon and 69 on Intel have
  supported platform metadata and are not marked broken. Their resolved versions
  match the README inventory. Shared packages resolve to the same version on
  both architectures.
- `nixfmt --check`, `statix check`, `deadnix --fail` and ShellCheck pass.
- Both settings migration tests pass: fresh installation with a home path
  containing spaces, preservation of subsequent user edits, and preservation of
  an existing dangling symlink.
- The inventory regression test accepts Markdown wrapping/table alignment
  changes while still rejecting a changed package version (three tests total).
- Inventory validation and generated README consistency pass for 163 entries
  (162 distinct items, with separate architecture routes for QGIS).
- Editor extension ID lists match their detailed inventory manifests.
- The exported Terminal profile passes `plutil -lint`.

## Issues resolved during evaluation

- Intel QGIS pulls in `arrow-cpp`, which is marked broken in this nixpkgs
  revision. Intel therefore uses the Homebrew QGIS cask. Apple Silicon uses Nix.
  No broken-package override was enabled.
- Java is explicitly installed and `JAVA_HOME` is set so the Android SDK
  command-line installer has a runtime. The available JDK is 25.0.3; the
  observed Homebrew JDK was 26.0.2.
- Orchard's current Apple container runtime uses Homebrew. Nix's `container`
  0.12.3 is older than Orchard 2.x requires, and `pkgs.orchard` is a different
  product. Both Orchard and its runtime are omitted on Intel.
- Corepack has lower package priority than the explicitly selected pnpm package.

## Limits and first-machine verification

This Mac has no usable system Nix installation. Validation used an extracted Nix
2.31.2 runtime and an isolated temporary store; it did not install Nix or
activate nix-darwin. Linters were run individually because macOS strips the
temporary dynamic-library search paths when launching the system shell.

The standard Git-backed flake command crashed in this relocated runtime. Direct
evaluation of the flake output function against the exact input source trees
succeeded. This is not a successful end-to-end `make check` or system build.

No complete system closure was built or activated, and no GUI application,
Homebrew/App Store installation, login, license or hardware driver was tested on
a fresh Mac. The CI workflow is provided but has not been run here. App Store,
Homebrew, vendor downloads and extension marketplaces remain external services;
their future availability is not guaranteed by `flake.lock`.

On a Mac with Nix installed, add the new files to Git before using the flake,
then run the README's `make check` and `make build` steps. After activation,
verify a fresh shell, editor launch/extensions, GUI apps, writable SDKs, browser
integration and device permissions. Repeat the build/runtime checks on an Intel
Mac before treating that profile as deployment-tested.
