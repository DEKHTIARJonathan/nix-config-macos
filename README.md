# macOS Nix configuration

This is an Apple Silicon-only nix-darwin configuration for your supplied package
inventory. Intel Macs are not supported. NixOS is the Linux distribution;
nix-darwin provides the corresponding system configuration layer on macOS. Your
everyday tools remain available without entering a development shell.

## Files

| File                    | Purpose                                                               |
| ----------------------- | --------------------------------------------------------------------- |
| `host.nix`              | Account, Apple Silicon platform, Nix ownership, compatibility version |
| `flake.nix`             | Inputs and the configuration named `mac`                              |
| `configuration.nix`     | Persistent packages, shell integration, Homebrew management           |
| `home.nix`              | Home Manager: Zsh, Git, writable settings seeding, restore commands   |
| `desktop.nix`           | Captured appearance, locale, Dock, and trackpad preferences           |
| `settings/`             | Live Mac settings snapshot, profiles, and extension inventories       |
| `scripts/`              | User settings restoration, editor setup, developer-tools verification |
| `android.nix`           | Native Nix Android tools and Java runtime                             |
| `dmg-apps.nix`          | Shared inventory: app versions, URLs, hashes, and formats             |
| `macos-apps.nix`        | Installs app bundles and exposes PKGs for manual installation         |
| `pkgs/mk-macos-app.nix` | Shared DMG, ZIP, PKG, and ZIP-containing-PKG builder                  |
| `pkgs/app-sources.nix`  | Fixed-output downloads from the inventory                             |
| `pkgs/macos-apps.nix`   | Enabled Apple Silicon app packages                                    |
| `flake.lock`            | Generated on your Mac; exact input revisions                          |

Your original 23 package entries have native Nix representations. Chrome,
Firefox, Brave, Raycast, and the personal environment described below are also
managed by Nix. Homebrew is configured for future additions, with empty
formula/cask lists and automatic removal disabled.

## Migration on this Mac, in order

Run these steps yourself in Terminal. Preparing this configuration has not
activated nix-darwin or removed any existing applications. Keep existing apps
and Homebrew until you have verified their replacements.

At the migration check on 2026-10-04, this Mac already had upstream Nix 2.31.2
at `/usr/local/bin/nix`, Homebrew at `/opt/homebrew/bin/brew`, and flakes
enabled in Jonathan's user Nix configuration. `darwin-rebuild` was not yet on
PATH. There is no need to reinstall Nix on this Mac.

### 1. Check the host and record existing installations

```bash
cd /Users/jonathan/git_projects/nix-macos-config
id -un
uname -m
nix --version
cat host.nix
```

The current `host.nix` is set to `username = "jonathan"`,
`system = "aarch64-darwin"`, `manageNix = true`, and `stateVersion = 7`. Keep
those values for this Mac. `manageNix = true` lets nix-darwin manage upstream
Nix, its daemon, and its system configuration when you activate.

Record Homebrew packages/services and preserve shell configuration before
activation. This records your setup; it is not a backup of application data:

```bash
migration_backup=$(mktemp -d "$HOME/nix-migration-backup.XXXXXX")
HOMEBREW_NO_AUTO_UPDATE=1 brew bundle dump --file="$migration_backup/Brewfile"
brew list --versions > "$migration_backup/brew-versions.txt"
brew services list > "$migration_backup/brew-services.txt"
for migration_file in "$HOME/.zshenv" "$HOME/.zprofile" "$HOME/.zshrc"; do
  if [ -f "$migration_file" ]; then
    /bin/cp -p "$migration_file" "$migration_backup/"
  fi
done
printf 'Migration records: %s\n' "$migration_backup"
```

The backup directory is private and outside this repository. Keep it while
migrating. The Brewfile records installed items; it does not pin their old
versions for an exact restore.

### 2. Enable flakes by default

Flakes and `nix-command` are already enabled for Jonathan. The following block
also works when setting up another user: it preserves existing settings and adds
the feature line only if that exact line is absent.

```bash
nix_user_config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/nix"
mkdir -p "$nix_user_config_dir"
if ! /usr/bin/grep -Fqx 'extra-experimental-features = nix-command flakes' \
  "$nix_user_config_dir/nix.conf" 2>/dev/null; then
  printf '\nextra-experimental-features = nix-command flakes\n' \
    >> "$nix_user_config_dir/nix.conf"
fi
nix config show experimental-features
```

The output must contain both `flakes` and `nix-command`; additional features are
fine. Nix reads this file on each invocation, so no shell restart or daemon
restart is needed for this user setting. These commands use Nix's default user
config location; if you deliberately set `NIX_USER_CONF_FILES`, edit the file
named by that override instead. See the
[Nix configuration-file reference](https://nix.dev/manual/nix/2.31/command-ref/conf-file.html).

User settings do not configure root's `sudo nix`. The first activation below
therefore still supplies explicit feature flags. After activation,
`configuration.nix` enables both features system-wide through
`nix.settings.experimental-features`. Keep that declaration; do not manually
edit nix-darwin's generated `/etc/nix/nix.conf`.

### 3. Build using the existing lock, without activating

```bash
cd /Users/jonathan/git_projects/nix-macos-config
nix flake metadata --no-update-lock-file
nix build .#darwinConfigurations.mac.system --no-update-lock-file
```

Stop here if either command fails. The build prepares the complete system and
creates `result`; it does not activate it, change macOS settings, or migrate
Homebrew. The full build already passed during review; repeating it normally
reuses the Nix store. Keep the existing `flake.lock`. Do not run
`nix flake update` as part of the initial migration.

Git-backed flakes exclude untracked files. Add new configuration files to Git
before building; edits to already tracked files need no commit to take effect.

### 4. Activate nix-darwin for the first time

Only after the build succeeds, run the
[nix-darwin bootstrap command](https://github.com/nix-darwin/nix-darwin#step-2-installing-nix-darwin):

```bash
sudo nix --extra-experimental-features 'nix-command flakes' \
  run github:nix-darwin/nix-darwin/nix-darwin-26.05#darwin-rebuild -- \
  switch --flake .#mac --no-update-lock-file
```

This is the step that changes the system. The bootstrap launcher comes from the
matching release branch; the system configuration uses your local flake and
lock. Activation configures shell initialization, installs the persistent Nix
package profile, manages the Nix daemon, adopts existing native Homebrew, and
installs the app bundles in `/Applications/Nix Apps`. It also activates Home
Manager, applies desktop preferences, and performs the first-time personal
settings restoration described below.

Existing Homebrew packages remain installed because `cleanup = "none"`;
automatic Brew updates and upgrades are disabled. Existing applications outside
`Nix Apps` are left in place. The four PKG products are only staged for manual
installation. [nix-homebrew](https://github.com/zhaofengli/nix-homebrew)
provides the existing-installation adoption via `autoMigrate = true`.

If activation reports a conflicting existing `/etc` file, inspect and preserve
the specifically named file, then follow the message and rerun the same command.
Do not delete `/etc/nix` or Homebrew to work around a conflict. If macOS
requests App Management permission for your terminal, allow it so activation can
install the app copies.

### 5. Open a new terminal and verify the replacements

```bash
cd /Users/jonathan/git_projects/nix-macos-config
command -v darwin-rebuild
nix config show experimental-features
sudo nix config show experimental-features
type -a nix git node rg rustup adb sdkmanager brew
git --version
node --version
adb version
sdkmanager --list_installed
printf 'ANDROID_HOME=%s\nJAVA_HOME=%s\n' "$ANDROID_HOME" "$JAVA_HOME"
brew list --versions
brew services list
open '/Applications/Nix Apps'
```

Both feature checks should include `flakes` and `nix-command` without extra
flags. Most Nix CLI tools should resolve through `/run/current-system/sw/bin`;
their Brew counterparts may still appear later in `type -a`. If a Brew version
wins, inspect `.zprofile` and `.zshrc` for later `brew shellenv` calls, PATH
assignments, aliases, or version-manager initialization. Keep Nix's system
profile before duplicate Brew commands when you want the Nix versions to run.

Quit an old app before launching its exact copy from `Nix Apps`. Check your
settings and normal workflows, then update Dock shortcuts and login items. For
example, after quitting the old Signal instance:

```bash
open '/Applications/Nix Apps/Signal.app'
```

For Android projects, check the SDK components and IDE/project SDK paths before
removing the old SDK; see [Android SDK maintenance](#android-sdk-maintenance).
The Nix SDK is read-only and initially contains command-line/platform tools
only.

### 6. Remove old copies individually, after verification

Follow [Removing previous installations](#removing-previous-installations)
below. There is no required mass-uninstall step. Keep Homebrew itself: this
configuration intentionally manages it for packages that need it.

Keep existing NordVPN, Tailscale, Insta360 Studio, and 1Password installations.
Nix only stages their PKGs; activation does not adopt, reinstall, or control the
versions of those installed products. When you actually want to install or
update one, open only its installer, for example:

```bash
open /run/current-system/sw/share/macos-pkgs/tailscale.pkg
```

The other staged files are `nordvpn.pkg`, `insta360-studio.pkg`, and
`onepassword.pkg` in the same directory. Apple's Installer handles choices and
administrator authorization. See
[PKG installation and updates](#pkg-installation-and-updates).

### 7. Use the normal rebuild command afterward

```bash
cd /Users/jonathan/git_projects/nix-macos-config
nix build .#darwinConfigurations.mac.system --no-update-lock-file
sudo darwin-rebuild switch --flake .#mac --no-update-lock-file
```

No bootstrap launcher or feature flags are needed after successful activation.
See [Normal maintenance](#normal-maintenance) for deliberate package/input
updates.

### Adapting these steps to another Mac

Install Nix first if `nix --version` fails; follow the current
[nix-darwin prerequisites](https://github.com/nix-darwin/nix-darwin#prerequisites).
Use an Apple Silicon Mac, change the checkout path and account in `host.nix`,
and keep `system = "aarch64-darwin"`. Use `manageNix = false` for Determinate
Nix, which manages its own daemon; keep user-level flakes enabled and follow
that distribution's guidance for root's configuration. With `manageNix = false`,
this flake does not set system-wide Nix options. The installer and the Nix
distribution are distinct.

For an existing nix-darwin installation, merge modules and preserve its
`stateVersion`. This configuration targets matching stable 26.05 branches and
already includes a lock.

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
# From a repository that needs LFS:
git lfs install --local
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

Home Manager owns global Git configuration and shell dotfiles; make changes in
`home.nix` and `settings/git.json`, or use `~/.zshrc.local` for extra shell
customizations. Use repository-local Git settings for LFS filters and project
overrides. GitHub credentials and Neovim settings remain user-managed. Open
`/Applications/Nix Apps/Hidden Bar.app` and configure launch at login in the
application if desired.

## Personal environment restoration

The settings were captured directly from this Mac on 2026-10-04. `old/` is a
historical reference and is not imported. Home Manager follows the existing
nixpkgs input; adding it updates the lockfile without updating the other inputs.
Keep `home.stateVersion = "26.05"` when updating packages.

Home Manager manages Zsh, Oh My Zsh's Git plugin, Powerlevel10k, and the current
prompt configuration. MesloLGS NF is installed for the prompt and Terminal.
`code` and `vscode` launch VS Code; `zed` launches Zed. Login shells use
nix-darwin's default tool order; subshells preserve inherited project
toolchains. Existing Cargo initialization and the Python 3.12 framework path are
retained conditionally; no extra Python/Flutter toolchain or old Android/Java
environment is restored.

The captured global Git settings include Jonathan Dekhtiar's name/email, an
empty signing key, disabled commit signing, disabled forced annotated-tag
signing, and disabled ignored-file advice. Review the identity before adapting
this configuration to another account.

Existing managed dotfiles are backed up with `.before-nix` on adoption. If a
backup already exists, Home Manager stops instead of replacing it; move that
backup aside before retrying. Home Manager's generated Git and shell files are
managed by Nix, while editor settings stay writable.

### Preferences and first activation

Every rebuild applies Dark appearance, `en-US`/`en_US`, automatic capitalization
and period substitution, and captured trackpad preferences (including speed
`0.875`, tap-to-click, tap-to-drag, gestures, and click thresholds). Dock
preferences are autohide enabled, delay `0.0`, animation modifier `0.25`, bottom
placement, size 64, and no recent applications.

On the first Home Manager activation, after applications are installed:

- Missing VS Code/Zed settings files are seeded. Existing files and symlinks,
  including dangling symlinks, are preserved.
- The captured 33-entry Dock order is restored. Managed apps resolve to
  `/Applications/Nix Apps`, with existing original locations as fallback.
  Missing apps are reported and skipped; folder stacks and other preferences are
  preserved. Apps in the Dock snapshot are not implicitly installed.
- The 13 captured Terminal profiles are merged with existing profiles. **Basic
  (Shift-Enter)** is selected for default/startup windows, with its MesloLGS NF
  11-point font and captured key mappings. Shell selection and Secure Keyboard
  Entry preferences are restored. Existing sessions stay open; reopen Terminal
  to reload its preferences.

Dock and Terminal each have their own completion marker under
`~/.local/state/nix-macos-config`. Subsequent activations preserve changes to
Dock order and Terminal profiles. Failed operations remain eligible for retry.
Missing Dock apps do not block restoration; explicitly rerun it after installing
them. Preference backups are binary plists in the private `backups/` directory
under that state directory. Explicit editor restores also back up replaced
files.

After activation, these commands run as your user (never with `sudo`):

```sh
mac-config-restore all --dry-run
mac-config-restore dock
mac-config-restore terminal
mac-config-restore editors                 # Seed only missing files
mac-config-restore editors --replace-existing  # Back up and replace editor files
```

The underlying `scripts/restore_settings.py` also supports `--source`, `--home`,
and `--once`; Home Manager invokes `all --once` and respects activation dry
runs. Restore commands deliberately reapply captured preferences unless `--once`
is specified. Nix rollback does not undo writable preferences; retain the
backups.

### Editors and extensions

VS Code and Zed keep their captured preferences in writable user files. There
were no user shortcut, snippet, task, or additional profile files to restore.
The Flutter SDK path, explicit Python interpreter path, temporary Postman
instruction files, and version-specific Continue extension schema reference were
omitted as requested. The `.github/instructions` setting is retained.

The inventory records 37 VS Code extensions and nine Zed extensions: Dockerfile,
Git Firefly, HTML, Log, Make, Nix, reStructuredText, Ruby, and TOML. Observed
versions are an audit snapshot, not marketplace pins. Existing extensions are
not downgraded or removed.

```sh
mac-config-setup-editors all
# Open Zed so it can download the requested extensions, then:
mac-config-setup-editors all --verify
```

`code` and `zed` can replace `all` to select one editor. VS Code installs
missing IDs through its managed app CLI and reports failures. Zed uses
`auto_install_extensions` on launch. The explicit Zed setup command backs up and
merges that key into existing JSON/JSONC settings, preserving other values;
comments are normalized when a merge is needed. It refuses to write through
symlinks. Verification exits nonzero while any requested extension is missing.
Routine activation never runs marketplace installation commands.

### Browsers and Raycast

These app versions come from the current nixpkgs lock:

| Application   | Nix version   | Existing app at capture |
| ------------- | ------------- | ----------------------- |
| Google Chrome | 154.0.8037.93 | 154.0.8037.97           |
| Firefox       | 157.0         | 152.0.5                 |
| Brave         | 1.96.59       | 154.1.96.61             |
| Raycast       | 1.104.17      | 1.104.31                |

The Nix apps live in `/Applications/Nix Apps`; previous copies remain in
`/Applications` until deliberately removed. The locked Chrome, Brave, and
Raycast releases are older than the currently installed copies. Verify profile
compatibility before migrating to those versions. Browser profiles, logins, and
extensions remain user-managed. Raycast settings and plugins are configured by
hand; no Raycast database or export is captured or imported.

### Xcode and Apple developer tools

```sh
mac-config-verify-development-tools
# Before activation, using an existing Python:
python3 scripts/verify_development_tools.py
```

This read-only check verifies full Xcode selection, its version and first-launch
readiness, the Command Line Tools receipt and files, clang, and macOS SDK
resolution. It returns nonzero with diagnostics for missing/incomplete tools; it
never installs tools, changes `xcode-select`, or accepts licenses.

On this Mac, Xcode **27.0 (27A266a)** is selected, Command Line Tools **27.0**
are installed, and clang and the macOS SDK resolve. However,
`xcodebuild -checkFirstLaunchStatus` returns a failure. Open Xcode to complete
its requested first-launch setup, then rerun the verifier.

### Settings validation

```sh
nix build --no-update-lock-file --no-link .#checks.aarch64-darwin.settings
nix build --no-update-lock-file --no-link .#darwinConfigurations.mac.system
```

The settings tests use temporary homes and mocked preferences. They cover repeat
activation, existing files/symlinks, backups, failure retries, Dock path
resolution, binary Terminal profiles, extension setup failures, and developer
tool diagnostics. The same portable tests run in CI. Runtime GUI verification is
performed after activation: open a new shell, check aliases and Git values,
launch the editors/browsers, verify extensions, and check Dock/Terminal
behavior.

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

## Downloaded macOS applications

`dmg-apps.nix` is the shared inventory for all downloaded applications.
`macos-apps.nix` consumes it during system configuration, and the same packages
are exposed as flake outputs. Architecture-specific entries are automatically
excluded on incompatible hosts.

| Format          | Build behavior                                | Activation behavior                    |
| --------------- | --------------------------------------------- | -------------------------------------- |
| `dmg` (default) | Extract HFS/APFS image, copy the named `.app` | Install in `/Applications/Nix Apps`    |
| `zip`           | Extract ZIP, copy the named `.app`            | Install in `/Applications/Nix Apps`    |
| `pkg`           | Stage the complete, unmodified installer      | Expose it for manual installation      |
| `zip-pkg`       | Extract ZIP and require exactly one PKG       | Expose the PKG for manual installation |

Every download uses `fetchurl` and a fixed SHA-256 hash. Building prepares files
in the Nix store; it never runs a vendor installer, launches an app, or changes
`/Applications`. Only unpack and install phases run, preserving original
binaries and resources without patching or re-signing. Signatures stored in
extended attributes require the native activation copy described below for VLC;
the Nix store cannot preserve those attributes.

Add an entry to `dmg-apps.nix`; no additional module edits are needed. Use an
Apple Silicon or universal macOS download; all app packages target Apple
Silicon:

```nix
example = {
  version = "1.2.3";
  url = "https://example.com/Example-1.2.3.dmg";
  hash = lib.fakeHash;
  appName = "Example.app";
  # format = "zip";  # Default: "dmg"; also "pkg" or "zip-pkg".
  # appPath = "Subdirectory/Example.app";  # Default: appName.
  # dmgExtractor = "7zz";  # For APFS DMGs; default: "undmg" (HFS).
  # preserveXattrs = true;  # DMGs requiring native copying at activation.
  # downloadName = "example-latest.dmg";  # Stable store filename for a mutable URL.
  # enable = false;  # Exclude an entry without deleting it.
};
```

PKGs are always staged for manual installation. ZIPs containing multiple PKGs
are rejected instead of selecting an arbitrary installer.

To update an app, change its version/URL, set `hash = lib.fakeHash;`, and build
its download. Copy the `got: sha256-...` value from Nix's mismatch error into
`hash`, then build the complete package to verify extraction:

```bash
# Stage newly added files first when using a Git-backed flake.
nix build .#example.src --no-link
# Replace the fake hash with Nix's reported hash, then:
nix build .#example --no-link
sudo darwin-rebuild switch --flake .#mac
```

For the existing inventory, substitute an attribute such as `signal`, `ariane`,
`onepassword`, or `insta360-studio`. App versions/hashes are independent of
`flake.lock`; `nix flake update` alone does not update them. A mutable `latest`
URL is still pinned by its hash, but a fresh download will fail if the vendor
replaces the file. Prefer versioned download URLs when the vendor provides them.

### PKG installation and updates

PKGs are **downloaded and staged only**. Rebuilding or activating the system
does not run them. Open a prepared installer in Apple's Installer UI, which
handles choices, authorization, and prompts:

```bash
nix build .#nordvpn
open result/share/macos-pkgs/nordvpn.pkg
```

After activation, staged installers are also available under
`/run/current-system/sw/share/macos-pkgs/`. The supplied 1Password ZIP contains
only a downloader, so the inventory uses the vendor's complete PKG. Insta360's
ZIP is unpacked to expose its PKG. HandBrake and Zed download pages are resolved
to their underlying versioned GitHub DMGs.

Native installers may add services, drivers, system extensions, or other files
outside the Nix store. They may stop running apps, request permissions, or
require a restart. Nix cannot make those effects transactional or automatically
reverse them. Removing a PKG entry does not uninstall the product; use its
vendor's uninstall procedure. Nix rollback does not guarantee a supported vendor
downgrade. PKG-installed apps may also update themselves outside Nix.

Apps copied into `Nix Apps` are read-only and should be updated through Nix.

### Bundles with signatures in extended attributes

VLC sets `preserveXattrs = true` because its `plugins.dat` signature is stored
in filesystem extended attributes, which the Nix store does not retain. For this
entry, activation mounts the pinned DMG read-only, copies the app with Apple's
`ditto --rsrc --extattr`, restores its read-only permissions, and detaches the
image. This preserves the original signature without re-signing or bypassing
Gatekeeper. The ordinary package build still validates the download and bundle
layout; its store copy always lacks these attributes. The copy in
`/Applications/Nix Apps` receives them during activation. The source DMG stays
referenced by the activation script and can be reused.

### OpenSpeleo apps

The three OpenSpeleo entries set `removeQuarantine = true`. Activation removes
only the quarantine attribute from those specific copies in `Nix Apps`. No
system-wide Gatekeeper setting is changed, and vendor signatures are not
replaced or treated as trusted. The source hash pins the exact downloaded bytes.
macOS can still require explicit user approval for an untrusted app.

## Removing previous installations

The initial activation keeps existing Homebrew packages. First list their exact
names and review any running services:

```bash
brew list --formula
brew list --cask
brew services list
```

For a formula, check that its Nix replacement runs and that no remaining Brew
formula depends on it. For example, if Brew's `ripgrep` is installed:

```bash
type -a rg
brew uses --installed --recursive ripgrep
# Only after checking the output above:
brew uninstall --formula ripgrep
```

Keep a formula if another Brew package or service still needs it. Avoid forced
dependency removal, bulk uninstall loops, and `brew autoremove` during the
initial migration. Declaring a CLI package in Nix does not recreate a Brew
service's configuration or data.

For a Brew cask with a tested Nix app replacement, quit the old application and
remove its old login item, then uninstall its cask using the exact name from
`brew list --cask`. For example, if Hidden Bar came from Brew:

```bash
brew uninstall --cask hiddenbar
open '/Applications/Nix Apps/Hidden Bar.app'
```

Reconfigure its login behavior in the Nix copy. Avoid `--zap` or app-cleanup
utilities: they can delete settings and other application data. See the
[Homebrew uninstall reference](https://docs.brew.sh/Manpage#uninstall-remove-rm-options-installed_formula-installed_cask-).
For an app installed manually, move only the old `/Applications/Name.app` bundle
to the Trash in Finder after testing its replacement. Keep its files in
`~/Library` and its Keychain entries. Update Dock shortcuts and login items to
the Nix copy. Old and new copies can otherwise both appear in app searches.

Do not uninstall the four PKG products just because their installers are now
declared in Nix: they have no Nix-managed installed-app replacement. Keep their
existing Brew registrations too if applicable.

Only after updating Android SDK paths, declaring any project-required SDK
components, and verifying your Android workflows, remove the old casks if they
are installed:

```bash
brew uninstall --cask android-commandlinetools android-platform-tools
```

Do not enable automatic Homebrew cleanup until all Homebrew-installed items you
intend to keep are represented in its lists. Keeping `cleanup = "none"` is valid
indefinitely; it simply allows additional unmanaged Brew packages.

GNU coreutils deserve special attention: the Nix installation exposes GNU
commands with unprefixed names. Explicit `/bin/ls`, `/bin/cp`, etc. still invoke
the macOS versions when a script requires their behavior.

## Normal maintenance

Apply a package-list or configuration edit using the existing lock:

```bash
cd /Users/jonathan/git_projects/nix-macos-config
nix build .#darwinConfigurations.mac.system --no-update-lock-file
sudo darwin-rebuild switch --flake .#mac --no-update-lock-file
```

Update input revisions, build for review, then apply:

```bash
cd /Users/jonathan/git_projects/nix-macos-config
nix flake update
nix build .#darwinConfigurations.mac.system --no-update-lock-file
sudo darwin-rebuild switch --flake .#mac --no-update-lock-file
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

All 19 inventory packages were built on Apple Silicon using the checked-in lock.
Downloads were first built with fake hashes, then rebuilt with the hashes
reported by Nix; the corrected builds reused the cached downloads. HFS and APFS
DMGs, direct PKGs, and Insta360's ZIP containing a PKG were verified. The full
Apple Silicon system also built successfully. No apps have been activated and no
PKG installer has been executed as part of this change.

The supplied HandBrake and Zed links were HTML pages, so their versioned release
assets are used. The supplied 1Password ZIP contains only its downloader; the
complete PKG is staged instead, following
[1Password’s deployment guidance](https://support.1password.com/deploy-1password/).
Mutable endpoints currently pin Rambox 2.7.1, 1Password 8.12.38, and NordVPN
10.12.0 by hash. The supplied VS Code commit is version 1.140.0.

- [nix-darwin setup](https://github.com/nix-darwin/nix-darwin)
- [nix-darwin options](https://nix-darwin.github.io/nix-darwin/manual/)
- [nix-homebrew](https://github.com/zhaofengli/nix-homebrew)
- [Nixpkgs Android documentation](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/android.section.md)
- [Hidden Bar package](https://github.com/NixOS/nixpkgs/blob/c27cdad491a991b11ed731760aa2ef8db0cb0410/pkgs/by-name/hi/hidden-bar/package.nix)
- [macOS trash package](https://github.com/NixOS/nixpkgs/blob/c27cdad491a991b11ed731760aa2ef8db0cb0410/pkgs/os-specific/darwin/by-name/tr/trash/package.nix)
