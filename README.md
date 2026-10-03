# macOS Nix configuration

This is a nix-darwin configuration for your supplied package inventory. NixOS is
the Linux distribution; nix-darwin provides the corresponding system
configuration layer on macOS. Your everyday tools remain available without
entering a development shell.

## Files

| File                | Purpose                                                         |
| ------------------- | --------------------------------------------------------------- |
| `host.nix`          | Account, CPU architecture, Nix ownership, compatibility version |
| `flake.nix`         | Inputs and the configuration named `mac`                        |
| `configuration.nix` | Persistent packages, shell integration, Homebrew management     |
| `android.nix`       | Native Nix Android tools and Java runtime                       |
| `flake.lock`        | Generated on your Mac; exact input revisions                    |

Your original package descriptions are preserved inline. All 23 inventory
entries have native Nix representations. Homebrew is configured for future
additions, with empty formula/cask lists and automatic removal disabled.

## Before building

1. Install Nix if it is not already installed. Follow the current nix-darwin
   prerequisite instructions linked below. This project does not install Nix
   before the first build.
2. Extract this directory somewhere you own, for example `~/mac-nix`.
3. Edit `host.nix`: replace `CHANGE_ME` with `id -un` and select your native CPU
   architecture. `aarch64-darwin` is Apple Silicon; `x86_64-darwin` is Intel.
4. Set `manageNix = false` if you use Determinate Nix. Its daemon remains
   externally managed. Make sure flakes and nix-command are enabled in that
   installation; the explicit bootstrap flags below enable them per command.
5. If you already use nix-darwin, preserve your existing `stateVersion` and
   merge this configuration with your existing modules.

The configuration targets matching stable 26.05 branches. Before upgrading to a
newer release, check its macOS architecture support; newer nixpkgs branches have
dropped Intel support. The first lock resolves the stable branch heads, then
subsequent builds reuse those exact revisions.

## Lock and build without applying changes

Run as your normal user from the extracted directory:

```bash
cd ~/mac-nix
nix --extra-experimental-features 'nix-command flakes' flake lock
nix --extra-experimental-features 'nix-command flakes' build .#darwinConfigurations.mac.system
```

This downloads/builds the system closure and creates `result`; it does not
activate it, change macOS settings, or migrate Homebrew. Keep `flake.lock`.

If you put this directory in Git, Nix includes only tracked files. Stage the
configuration files and `flake.lock` before rebuilding. You do not need Git to
use this flake.

## First activation

After the build succeeds, use the documented nix-darwin bootstrap command:

```bash
sudo nix --extra-experimental-features 'nix-command flakes' run github:nix-darwin/nix-darwin/nix-darwin-26.05#darwin-rebuild -- switch --flake .#mac
```

The bootstrap launcher comes from the matching release branch; the system
configuration itself uses your local flake and lock. Activation configures
system shell initialization, installs the persistent package profile, adopts
Homebrew, and exposes the Hidden Bar application. If nix-darwin reports a
conflicting existing `/etc` file, inspect and back up the named file before
following its instructions. If macOS requests App Management permission for the
terminal, grant it so activation can install the app.

Open a new terminal after activation. Check a few representative tools:

```bash
command -v git rg node rustup adb sdkmanager
git --version
node --version
adb version
sdkmanager --list_installed
echo "$ANDROID_HOME"
```

Most native Nix commands should resolve through `/run/current-system/sw/bin`. If
a Homebrew version wins, inspect shell startup files for PATH overrides or shell
aliases. Extend PATH rather than replacing nix-darwin's initialized PATH.

## Complete inventory mapping

| Original entry           | Native Nix representation                          |
| ------------------------ | -------------------------------------------------- |
| bun                      | `pkgs.bun`                                         |
| cmake                    | `pkgs.cmake`                                       |
| coreutils                | `pkgs.coreutils`                                   |
| ffmpeg                   | `pkgs.ffmpeg`                                      |
| gh                       | `pkgs.gh`                                          |
| git                      | `pkgs.git`                                         |
| git-lfs                  | `pkgs.git-lfs`                                     |
| gradle                   | `pkgs.gradle`                                      |
| htop                     | `pkgs.htop`                                        |
| iperf3                   | `pkgs.iperf3`                                      |
| jq                       | `pkgs.jq`                                          |
| neovim                   | `pkgs.neovim`                                      |
| ninja                    | `pkgs.ninja`                                       |
| nixfmt                   | `pkgs.nixfmt`                                      |
| node                     | `pkgs.nodejs` (includes npm)                       |
| prek                     | `pkgs.prek`                                        |
| ripgrep                  | `pkgs.ripgrep`                                     |
| rustup                   | `pkgs.rustup`                                      |
| shellcheck               | `pkgs.shellcheck`                                  |
| trash                    | `pkgs.darwin.trash` (same upstream implementation) |
| tree                     | `pkgs.tree`                                        |
| android-commandlinetools | `pkgs.androidenv.composeAndroidPackages` SDK       |
| android-platform-tools   | Same composed SDK, including adb and fastboot      |
| hiddenbar                | `pkgs.hidden-bar`                                  |

Both Android entries are included in one SDK package.

## One-time user setup

If Git LFS is not already configured:

```bash
git lfs install
```

If Rustup has no default toolchain yet:

```bash
rustup default stable
```

Existing Rustup toolchains stay under `~/.rustup`. Nix pins Rustup itself, not
those downloaded toolchains. Update them using `rustup update`, or let project
`rust-toolchain.toml` files select them. Do not run `rustup self update` against
the Nix installation. A fully Nix-declared compiler can be added later in a
project flake or through a Rust toolchain overlay.

Keep Git identity, GitHub credentials, Neovim settings, and shell dotfiles as
they are during migration. This inventory does not specify their contents. Open
`/Applications/Nix Apps/Hidden Bar.app` and configure launch at login in the
application if desired.

## Android SDK maintenance

The initial SDK contains command-line tools and platform-tools, matching your
casks. It does not invent API levels, build-tools, an NDK, or emulator images
for projects whose requirements you have not supplied. Declare the components
you need in `android.nix`, then rebuild. The SDK is read-only, so Gradle and
Android Studio cannot automatically install missing components into it.

The license acceptance and unfree-package allowance are explicit in
`android.nix`. Review
[Google's SDK terms](https://developer.android.com/studio/terms) before building
if you have not accepted them.

For Finder-launched Android Studio, select the SDK directory explicitly; shell
environment variables are not a machine-wide environment for every GUI process.
Existing project `local.properties` files may still point to your old SDK.
Update `sdk.dir` where appropriate. Store paths can change after updates.

If you prefer installing SDK components interactively, switch Android back to
Homebrew: remove `./android.nix` from the flake's modules and add
`"android-commandlinetools"` and `"android-platform-tools"` to `homebrew.casks`.
Set up a writable SDK and Java runtime for that workflow. Use one SDK owner at a
time to avoid mismatched adb binaries and SDK paths.

## Removing previous Homebrew copies

The initial activation keeps existing Homebrew packages. After verifying Nix
versions, remove the old formulae in small batches using `brew uninstall`.
Review dependents with `brew uses --installed PACKAGE` first; other Homebrew
software may still require a formula. Avoid forced dependency removal.

For Hidden Bar, quit the old application and remove its old login item, then run
`brew uninstall --cask hiddenbar`. Open the Nix copy and configure its login
behavior. Old and new copies can otherwise both appear in app searches. Remove
the two old Android casks after updating SDK paths and checking tools.

Do not enable automatic Homebrew cleanup until all Homebrew-installed items you
intend to keep are represented in its lists. Keeping `cleanup = "none"` is valid
indefinitely; it simply allows additional unmanaged Brew packages.

GNU coreutils deserve special attention: the Nix installation exposes GNU
commands with unprefixed names. Explicit `/bin/ls`, `/bin/cp`, etc. still invoke
the macOS versions when a script requires their behavior.

## Normal maintenance

Apply a package-list or configuration edit using the existing lock:

```bash
sudo darwin-rebuild switch --flake ~/mac-nix#mac
```

Update input revisions, build for review, then apply:

```bash
cd ~/mac-nix
nix flake update
# If using Git, stage the updated lock before building.
nix build .#darwinConfigurations.mac.system
sudo darwin-rebuild switch --flake .#mac
```

For an externally managed Nix installation without permanently enabled features,
keep using `--extra-experimental-features 'nix-command flakes'`.

Keep known-good configuration/lock revisions in version control. To revert,
restore a known-good revision, build it, then switch. Nix package generations do
not roll back Homebrew adoption, changes to user files, app preferences, or
separately downloaded Rustup toolchains.

Homebrew itself is pinned through nix-homebrew's locked input. With mutable taps
enabled, its package catalog and any future Brew packages are not fully
reproducible through the Nix lock. Automatic Brew updates/upgrades are disabled
here; manage Brew updates separately when you start using its package lists.

## Verification status and references

This configuration was reviewed against upstream package definitions and
documentation, but was not evaluated or built here: this environment has no Nix
executable or macOS builder. The build-only command above is the actual
validation step on your Mac. No `flake.lock` is fabricated or supplied.

- [nix-darwin setup](https://github.com/nix-darwin/nix-darwin)
- [nix-darwin options](https://nix-darwin.github.io/nix-darwin/manual/)
- [nix-homebrew](https://github.com/zhaofengli/nix-homebrew)
- [Nixpkgs Android documentation](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/android.section.md)
- [Hidden Bar package](https://github.com/NixOS/nixpkgs/blob/c27cdad491a991b11ed731760aa2ef8db0cb0410/pkgs/by-name/hi/hidden-bar/package.nix)
- [macOS trash package](https://github.com/NixOS/nixpkgs/blob/c27cdad491a991b11ed731760aa2ef8db0cb0410/pkgs/os-specific/darwin/by-name/tr/trash/package.nix)
