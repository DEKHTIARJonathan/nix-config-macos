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
| `mac-apps.nix`          | Shared inventory: app versions, URLs, hashes, and formats             |
| `app-installation.nix`  | Installs missing native app bundles and PKG products                  |
| `pkgs/mk-macos-app.nix` | Shared DMG/ZIP app and embedded PKG builder                           |
| `pkgs/app-sources.nix`  | Fixed-output downloads from the inventory                             |
| `pkgs/macos-apps.nix`   | Enabled Apple Silicon app packages                                    |
| `flake.lock`            | Generated on your Mac; exact input revisions                          |

Your original 23 package entries have native Nix representations. Chrome,
Firefox, Brave, Raycast, and the personal environment described below are also
declared here. CLI tools and system configuration are managed by Nix; GUI apps
are writable native installations. Homebrew manages Hidden Bar, Codex CLI,
Claude Code, Railway CLI, and herdr, with automatic removal disabled.

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
make build
```

Stop here if either command fails. The build prepares the complete system and
creates `result`; it does not activate it, change macOS settings, or migrate
Homebrew. The full build already passed during review; repeating it normally
reuses the Nix store. Keep the existing `flake.lock`. Do not run
`nix flake update` as part of the initial migration.

Git-backed flakes exclude untracked files. Add new configuration files to Git
before building; edits to already tracked files need no commit to take effect.

### 4. Activate nix-darwin for the first time

To build and activate the configuration, run:

```sh
make install
```

`make install` first runs `make build` as your user, then uses `sudo` to run
`darwin-rebuild switch` from the built `result` system. This works before
`darwin-rebuild` is on PATH and records the system generation for rollbacks. The
switch step re-evaluates the locked flake and normally reuses the completed
build. If the build fails, activation does not run. This is the step that
changes the system. Activation configures shell initialization, installs the
persistent Nix package profile, manages the Nix daemon, adopts existing native
Homebrew, and installs missing app bundles in `/Applications`. Existing apps are
preserved, including versions installed by their own updaters. It also activates
Home Manager, applies desktop preferences, and performs the first-time personal
settings restoration described below.

Existing Homebrew packages remain installed because `cleanup = "none"`;
automatic Brew updates and upgrades are disabled. Existing applications are left
in place. Missing PKG products are installed automatically with Apple’s
`installer` as root, before app bundles and Home Manager settings restoration.
[nix-homebrew](https://github.com/zhaofengli/nix-homebrew) provides the
existing-installation adoption via `autoMigrate = true`.

PAM authentication files remain managed by macOS
(`security.pam.services.sudo_local.enable = false`), because this laptop
protects `/etc/pam.d`.

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
open '/Applications'
```

Both feature checks should include `flakes` and `nix-command` without extra
flags. Most Nix CLI tools should resolve through `/run/current-system/sw/bin`;
their Brew counterparts may still appear later in `type -a`. If a Brew version
wins, inspect `.zprofile` and `.zshrc` for later `brew shellenv` calls, PATH
assignments, aliases, or version-manager initialization. Keep Nix's system
profile before duplicate Brew commands when you want the Nix versions to run.

Docker Desktop owns the Docker CLI and credential helpers in `~/.docker/bin`;
Home Manager adds that directory to Zsh's PATH, including noninteractive shells.
Launch Docker Desktop once to complete its setup, then check
`command -v docker`, `docker version`, and `docker compose version` in a new
terminal. If the CLI is missing, check Docker Desktop's CLI tools installation
setting and select the user directory. The engine must be running for server
commands to work.

Docker Desktop's completion setup writes scripts to `~/.docker/completions`.
Home Manager includes that directory in `FPATH` before Oh My Zsh initializes
completion. The writable `~/.zshrc` lets Docker's setup button add its shell
configuration. Open a new terminal and check `print -r -- ${_comps[docker]}`: it
should show `_docker` when the completion script is installed.

GUI apps use their normal `/Applications` locations and remain writable. To
explicitly reinstall pinned versions, use the native installer command:

```bash
mac-config-install-apps --only signal zed --replace-existing
```

Replacement requests quit running apps gracefully and stop if an app remains
open. Each old bundle is archived and verified as a timestamped `.zip.bckp`
under `~/.local/state/nix-macos-config/apps` before replacement. Extended
attributes and internal symlinks are preserved. The backup directory must be on
the same filesystem as `/Applications` because it also holds the original
temporarily for atomic rename recovery. App settings are not deleted. Extract a
backup with
`ditto -x -k '/path/to/Example.app.TIMESTAMP.zip.bckp' '/path/to/recovery'`;
quit the app before restoring the recovered bundle to `/Applications`.

For Android projects, check the SDK components and IDE/project SDK paths before
removing the old SDK; see [Android SDK maintenance](#android-sdk-maintenance).
The Nix SDK is read-only and initially contains command-line/platform tools
only.

### 6. Remove old copies individually, after verification

Follow [Removing previous installations](#removing-previous-installations)
below. There is no required mass-uninstall step. Keep Homebrew itself: this
configuration intentionally manages it for packages that need it.

Activation installs missing NordVPN, Tailscale, Insta360 Studio, 1Password,
RØDECaster, and Google Earth Pro apps using their pinned vendor PKGs. Existing
app bundles are preserved, including self-updated versions. To explicitly update
or repair an existing installation, open its staged installer, for example:

```bash
open /run/current-system/sw/share/macos-pkgs/tailscale.pkg
```

The other staged files are `nordvpn.pkg`, `insta360-studio.pkg`,
`onepassword.pkg`, `rodecaster-app.pkg`, and `google-earth-pro.pkg` in the same
directory. Apple's Installer handles choices and administrator authorization.
See [PKG installation and updates](#pkg-installation-and-updates).

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
| coreutils                | Use macOS's built-in utilities                     |
| ffmpeg                   | `pkgs.ffmpeg`                                      |
| gh                       | `pkgs.gh`                                          |
| git                      | `pkgs.git`                                         |
| git-lfs                  | `pkgs.git-lfs`                                     |
| make                     | `pkgs.gnumake`                                     |
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
| uv                       | `pkgs.uv`                                          |
| android-commandlinetools | `pkgs.androidenv.composeAndroidPackages` SDK       |
| android-platform-tools   | Same composed SDK, including adb and fastboot      |
| hiddenbar                | Homebrew cask `hiddenbar`                          |

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

Home Manager owns global Git configuration and the generated shell settings;
make persistent configuration changes in `home.nix` and `settings/git.json`, or
use `~/.zshrc.local` for extra shell customizations. `~/.zshrc` is a writable
entry point that loads `~/.config/zsh/nix-zshrc`; applications can append setup
lines to it. Rebuilds update the generated file and preserve those additions.
Use repository-local Git settings for LFS filters and project overrides. GitHub
credentials and Neovim settings remain user-managed. Open
`/Applications/Hidden Bar.app` and configure launch at login in the application
if desired.

## Personal environment restoration

Home Manager installs the `review-agent` skill at
`~/.agents/skills/review-agent/SKILL.md`. Its source is
`settings/agent-skills/review-agent/SKILL.md`; edit that source and activate to
update it. The skill requests an adversarial sub-agent review, a corrective plan
and implementation, full tests, `prek run -a`, and a final commit when invoked.
Activation only installs the skill; it does not run the review.

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
environment is restored. `~/.cargo/bin` is also included when `~/.cargo/env` is
absent or does not update PATH, so Cargo-installed tools are available in
interactive and noninteractive Zsh shells. Inherited project tools retain
priority, and duplicate paths are removed.

The captured global Git settings include Jonathan Dekhtiar's name/email, an
empty signing key, disabled commit signing, disabled forced annotated-tag
signing, and disabled ignored-file advice. Review the identity before adapting
this configuration to another account.

Existing managed dotfiles are backed up with `.before-nix` on adoption. If a
backup already exists, Home Manager stops instead of replacing it; move that
backup aside before retrying. Home Manager's generated Git and shell files are
managed by Nix, while `.zshrc` and editor settings stay writable. When migrating
the old Home Manager `.zshrc` symlink, its contents are backed up privately
under `~/.local/state/nix-macos-config/backups` before replacing it with the
writable entry point. Existing regular `.zshrc` files retain their content after
the new source line; unrelated symlinks require manual review. The shell
migration runs before Home Manager removes obsolete links, respects dry runs,
and preserves the writable file on subsequent activations. Rolling back to a
configuration that manages `.zshrc` directly may require resolving a Home
Manager backup conflict; preserve application additions before doing so.

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
  `/Applications`, with existing original locations as fallback. Missing apps
  are reported and skipped; folder stacks and other preferences are preserved.
  Apps in the Dock snapshot are not implicitly installed.
- The 13 captured Terminal profiles are merged with existing profiles. **Basic
  (Shift-Enter)** is selected for default/startup windows, with its MesloLGS NF
  11-point font and captured key mappings. Shell selection and Secure Keyboard
  Entry preferences are restored. Existing sessions stay open; reopen Terminal
  to reload its preferences. **Clear Dark** also uses MesloLGS NF, at 12 points,
  so Powerlevel10k icons render in windows using that profile.

Powerlevel10k shows the branch and Git/provider icons using the installed
MesloLGS NF font. Both icons are configured in `settings/p10k.zsh`; setting
`POWERLEVEL9K_VCS_BRANCH_ICON` or `POWERLEVEL9K_VCS_VISUAL_IDENTIFIER_EXPANSION`
to an empty value hides the corresponding icon. VS Code and Zed terminal fonts
are repaired automatically on every activation, including existing settings.
There is no macOS setting that forces a font in every application: other
terminals still need an application-specific setting. Workspace or remote
settings can also override an editor's user defaults.

Dock and Terminal each have their own completion marker under
`~/.local/state/nix-macos-config`. Subsequent activations preserve changes to
Dock order and Terminal profiles, except for Shift+Return and Shift+keypad
Enter: every activation sets these two bindings in all Terminal profiles to send
`ESC [13;2u` (Shift+Enter), allowing Codex CLI to insert a line break while
plain Enter still submits. This also repairs existing laptops and profiles
created after the initial deployment. Other key bindings and profile settings
are preserved. After a binding repair, fully quit and reopen Terminal to load
it. Failed operations remain eligible for retry. Missing Dock apps do not block
restoration; explicitly rerun it after installing them. Preference backups are
binary plists in the private `backups/` directory under that state directory.
Explicit editor restores also back up replaced files.

After activation, these commands run as your user (never with `sudo`):

```sh
mac-config-restore all --dry-run
mac-config-restore dock
mac-config-restore terminal
mac-config-restore editors                 # Seed only missing files
mac-config-restore editor-fonts            # Repair VS Code/Zed terminal fonts
mac-config-restore editors --replace-existing  # Back up and replace editor files
```

The underlying `scripts/restore_settings.py` also supports `--source`, `--home`,
and `--once`; Home Manager invokes `all --once` and respects activation dry
runs. Restore commands deliberately reapply captured preferences unless `--once`
is specified. Nix rollback does not undo writable preferences; retain the
backups.

### Editors and extensions

VS Code and Zed keep their captured preferences in writable user files.
`settings/code-settings.json` sets `terminal.integrated.fontFamily` to
`'MesloLGS NF'`; `settings/zed-settings.json` sets `terminal.font_family` to
`MesloLGS NF`. Activation maintains these keys in existing settings as well as
new installations. VS Code also adds the font key to
`workbench.settings.applyToAllProfiles`, retaining existing entries. Other
settings, including terminal sizes and editor/UI fonts, are preserved. The font
repair skips missing files, refuses symlinks, and backs up original bytes
privately before an atomic write. Changed JSONC/JSON5 files are serialized as
JSON, so comments and formatting remain in the backup. Unchanged files are not
rewritten. Reload the editor if an open terminal retains its previous font.
There were no user shortcut, snippet, task, or additional profile files to
restore. The Flutter SDK path, explicit Python interpreter path, temporary
Postman instruction files, and version-specific Continue extension schema
reference were omitted as requested. The `.github/instructions` setting is
retained.

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
missing IDs through its native app CLI and reports failures. Zed uses
`auto_install_extensions` on launch. The explicit Zed setup command backs up and
merges that key into existing JSON/JSONC settings, preserving other values;
comments are normalized when a merge is needed. It refuses to write through
symlinks. Verification exits nonzero while any requested extension is missing.
Routine activation never runs marketplace installation commands.

### Native applications and updates

`mac-apps.nix` pins vendor downloads by SHA-256, including Chrome, Firefox,
Brave, Raycast, Android Studio, Docker Desktop, Google Earth Pro, and RØDECaster
App. Chrome, Brave, Docker, and RØDECaster use mutable vendor endpoints:
changing their hash/version is an explicit bootstrap update, independent of
`flake.lock`. The archive filename is not assumed to be the installed app's
version.

DMG/ZIP app bundles live directly in `/Applications`, owned by the installing
user and writable so their built-in updaters can run. Vendor PKGs determine
their own ownership and update behavior. Ordinary rebuilds install only missing
DMG/ZIP apps and never downgrade self-updated copies. `mac-config-install-apps`
uses Apple's `hdiutil` and `ditto`, preserving extended attributes and vendor
signatures. Zed's seeded settings enable its automatic updates. Existing editor
settings remain preserved unless explicitly restored or edited.

Browser profiles, logins, extensions, Docker data, and Android SDKs remain
user-managed. Raycast settings and plugins are configured by hand; no Raycast
export is captured in the repository. Local migration backups may contain app
profiles and must remain private.

Hidden Bar stays a Homebrew cask. Codex CLI and Claude Code use the `codex` and
`claude-code` casks; Railway CLI and herdr use the `railway` and `herdr`
formulae. These are separate from the Codex and Claude desktop apps. Claude's
package-manager auto-update is enabled with
`CLAUDE_CODE_PACKAGE_MANAGER_AUTO_UPDATE=1`. Homebrew’s shell initialization is
disabled so it cannot put legacy Brew tools ahead of Nix; Brew-only CLIs remain
available later in PATH. Other Homebrew updates are explicit:

```sh
brew upgrade --cask codex
brew upgrade railway
```

Existing credentials are retained. Avoid installing duplicate npm copies of
these CLIs. Other npm global packages need a writable user prefix when using
Nix's Node installation.

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
make test
```

`make test` requires uv and uses `uv run --with json5==0.13.0` to supply its
Python dependency and run unittest. Linux CI installs uv with
`astral-sh/setup-uv` and calls the same `make test` target. No Python override
or manual virtual environment setup is needed.

For the complete Apple Silicon Nix check, including generated Home Manager Zsh
files, run `make test-nix`. This uses Nix's packaged Python/json5 inside the
builder. Both targets use temporary test data; neither builds vendor apps,
activates the system, or updates the lockfile. The uv run skips tests requiring
generated Zsh files; platform-specific tests also skip on unsupported hosts.

The settings tests use temporary homes and mocked preferences. They cover repeat
activation, existing files/symlinks, backups, failure retries, Dock path
resolution, binary Terminal profiles, extension setup failures, and developer
tool diagnostics. The portable tests run in CI and are supplemented on macOS by
a native archive round-trip test, covering extended attributes, permissions, and
symlinks. App installer tests also cover preserved self-updates, concurrent
installation, backup failures, failed replacement, attribute failures, and
mounted-image cleanup. Runtime GUI verification is performed after activation:
open a new shell, check aliases and Git values, launch the editors/browsers,
verify extensions, and check Dock/Terminal behavior.

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

`mac-apps.nix` is the shared inventory for all downloaded applications.
`app-installation.nix` consumes it during system configuration, and the same
packages are exposed as flake outputs. The host targets Apple Silicon. Google
Earth Pro is an explicitly allowed Intel application and requires Rosetta 2 as
do some vendor SDK installers. Before other activation steps,
`configuration.nix` checks Intel execution with
`/usr/bin/arch -x86_64 /usr/bin/true`. If unavailable, activation runs
`/usr/sbin/softwareupdate --install-rosetta --agree-to-license` as root and
verifies Intel execution again. This automatically accepts Apple's Rosetta
license and may download Rosetta from Apple. A failed installation or failed
verification stops activation and remains eligible for retry; working Rosetta
installations are left alone. Evaluation and `make build` do not install it.
This does not enable Intel Homebrew or change the ARM64 build target.

| Format          | Build behavior                                | Activation behavior                      |
| --------------- | --------------------------------------------- | ---------------------------------------- |
| `dmg` (default) | Extract HFS/APFS image, copy the named `.app` | Install in `/Applications`               |
| `zip`           | Extract ZIP, copy the named `.app`            | Install in `/Applications`               |
| `pkg`           | Stage the complete, unmodified installer      | Install missing app with Apple installer |
| `zip-pkg`       | Extract ZIP and require exactly one PKG       | Install missing app with Apple installer |
| `dmg-pkg`       | Extract DMG and require exactly one PKG       | Install missing app with Apple installer |

Every download uses `fetchurl` and a fixed SHA-256 hash. Building prepares files
in the Nix store; it never runs a vendor installer, launches an app, or changes
`/Applications`. Only unpack and install phases run, preserving original
binaries and resources without patching or re-signing. Signatures stored in
extended attributes require the native activation copy described below for VLC;
the Nix store cannot preserve those attributes.

Add an entry to `mac-apps.nix`; no additional module edits are needed. Use an
Apple Silicon or universal macOS download where available. The host remains
Apple Silicon even for explicitly permitted Intel apps:

```nix
example = {
  version = "1.2.3";
  url = "https://example.com/Example-1.2.3.dmg";
  hash = lib.fakeHash;
  appName = "Example.app";
  # format = "zip";  # Default: "dmg"; also "pkg", "zip-pkg", or "dmg-pkg".
  # appPath = "Subdirectory/Example.app";  # Default: appName.
  # dmgExtractor = "7zz";  # For APFS DMGs; default: "undmg" (HFS).
  # downloadName = "example-latest.dmg";  # Stable store filename for a mutable URL.
  # enable = false;  # Exclude an entry without deleting it.
};
```

PKGs are staged during the build and run as root during activation when the
expected app is missing. Archives containing multiple PKGs are rejected instead
of selecting an arbitrary installer.

To add or update an app, preserve the exact supplied URL, including generic
`latest` endpoints, and set `hash = lib.fakeHash;`. Configuration-only edits
leave that placeholder pending; do not prefetch installers or start downloads
just to discover hashes. When your normal rebuild reports a hash mismatch, copy
the exact `got: sha256-...` value into that app's `hash` without changing its
URL. If explicitly building the app, use this sequence:

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
replaces the file. Keep the supplied URL and resolve that mismatch explicitly;
do not replace generic endpoints with version-specific redirect targets. See
[AGENTS.md](AGENTS.md) for the repository workflow.

### Download progress

Run from the repository root:

```sh
make build   # Build with progress; create result without activating.
make install # Build, then activate with sudo.
make test    # Run tests through uv, as CI does.
make test-nix # Run the complete Apple Silicon Nix settings check.
make lock    # Update flake.lock to the latest allowed input revisions.
```

Bare `make` also builds. Build, install, and test preserve `flake.lock`; only
`make lock` explicitly updates it. `make build` uses the standard
[nix-output-monitor](https://github.com/maralorn/nix-output-monitor) from the
locked flake, equivalent to:

```sh
nix run --no-update-lock-file .#nix-output-monitor -- build .#darwinConfigurations.mac.system --no-update-lock-file
```

This works before the first system activation and does not depend on shell
configuration. Nix first obtains the monitor; it then runs the requested build.
The monitor's own initial download uses the native Nix display.

The download builder converts curl's meter into structured Nix phase updates
such as `download 42.0%`. The monitor displays these beside each active build,
with updates limited to twice per second per download. It does not flood the log
with progress-bar lines. Percentages require a known transfer size; otherwise
the status says `downloading (size unknown)`. Ordinary curl errors are
preserved, as are stdout, exit status, fetchurl retries, and Nix hash
verification. A 100% transfer is not proof of successful hash verification.

Plain `nix build .#darwinConfigurations.mac.system --no-update-lock-file` also
shows the phase, but its native renderer only has one live status row. The flake
cannot add rows to that already running client. No shell alias or function is
installed. The Makefile invokes the monitor explicitly; the Nix executable is
unchanged.

### PKG installation and updates

Building downloads and stages PKGs without running them. During system
activation, `mac-config-install-pkgs` runs
`/usr/sbin/installer -pkg … -target /` as root for each missing app. It
preserves existing app bundles, verifies that each successful installer produced
the expected app, and reports failures with a nonzero exit status. A failed
activation can be retried; apps already installed are skipped. Vendor ownership,
services, and drivers are handled by the installer.

Preview missing PKG installations without making changes:

```sh
mac-config-install-pkgs --dry-run
```

For an explicit update or repair of an existing app, open a prepared installer
in Apple's Installer UI, which handles choices, authorization, and prompts:

```bash
nix build .#nordvpn
open result/share/macos-pkgs/nordvpn.pkg
```

After activation, staged installers are also available under
`/run/current-system/sw/share/macos-pkgs/`. The supplied 1Password ZIP contains
only a downloader, so the inventory uses the vendor's complete PKG. Insta360 and
RØDECaster ZIPs are unpacked to expose their PKGs; RØDECaster requires its
vendor installer for driver components. Google Earth Pro’s Intel DMG contains a
signed PKG, which is installed the same way when its app is missing. HandBrake
and Zed download pages are resolved to their underlying versioned GitHub DMGs.

Keep application rollback copies in ZIP archives ending in `.zip.bckp`, not only
unpacked app directories. Vendor cleanup scripts and Apple Installer relocation
can discover and modify unpacked backup apps. Keep configuration backups
separately as `.bckp` files.

Native installers may add services, drivers, system extensions, or other files
outside the Nix store. They may stop running apps, request permissions, or
require a restart. Nix cannot make those effects transactional or automatically
reverse them. Removing a PKG entry does not uninstall the product; use its
vendor's uninstall procedure. Nix rollback does not guarantee a supported vendor
downgrade. PKG-installed apps may also update themselves outside Nix.

Native app copies are writable and may update themselves. Nix records the
bootstrap download, not the version currently installed by a native updater.

### Bundles with signatures in extended attributes

All native DMG installations mount the verified image read-only and copy the app
with `ditto --rsrc --extattr`. This preserves signatures stored in extended
attributes, including VLC's `plugins.dat`. Store-built `.app` artifacts are
useful for extraction checks but are not the deployed copies: the Nix store
cannot retain those extended attributes. Installed bundles retain user write
permission for native updates.

### OpenSpeleo apps

The three OpenSpeleo entries set `removeQuarantine = true`. Activation removes
only the quarantine attribute from those specific native copies. No system-wide
Gatekeeper setting is changed, and vendor signatures are not replaced or treated
as trusted. The source hash pins the exact downloaded bytes. macOS can still
require explicit user approval for an untrusted app.

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

Keep Hidden Bar's Homebrew cask registration: it is the declared installation.
Native apps use their existing `/Applications` paths, so do not delete those
bundles as “old copies” after migration. Explicit replacement already preserves
the former bundle in a verified `.zip.bckp` archive. Do not use cask `--zap` or
app-cleanup utilities because they delete settings and app data.

The six PKG products use vendor installers during activation and retain their
vendor uninstall procedures and services.

Only after updating Android SDK paths, declaring any project-required SDK
components, and verifying your Android workflows, remove the old casks if they
are installed:

```bash
brew uninstall --cask android-commandlinetools android-platform-tools
```

Do not enable automatic Homebrew cleanup until all Homebrew-installed items you
intend to keep are represented in its lists. Keeping `cleanup = "none"` is valid
indefinitely; it simply allows additional unmanaged Brew packages.

GNU coreutils are intentionally omitted from the global package list so `cp`,
`ls`, `mv`, `date`, and other basic utilities use macOS's native
implementations. Their behavior can differ from GNU tools; for example,
Cerbero's DMG extraction expects Apple's directory-copy behavior. After
activating this change, open a new shell and check `command -v cp` (expected
`/bin/cp`). Existing build caches with incorrectly nested extracted files still
need a separate repair.

## Normal maintenance

Apply a package-list or configuration edit using the existing lock:

```bash
cd /Users/jonathan/git_projects/nix-macos-config
nix build .#darwinConfigurations.mac.system --no-update-lock-file
sudo darwin-rebuild switch --flake .#mac --no-update-lock-file
```

Adding a package from an existing nixpkgs input, such as `gnumake`, uses the
revision already pinned in `flake.lock`; it does not need a lockfile update.
`make lock` runs `nix flake update`, updating all inputs within their declared
branches. It creates the lockfile if missing and does not build or activate the
system. Vendor app hashes remain separate.

Update input revisions, test and build for review, then apply:

```bash
cd /Users/jonathan/git_projects/nix-macos-config
make lock
make test
make build
make install
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

The inventory is checked on Apple Silicon using the checked-in lock. Downloads
are pinned by their verified SHA-256 hashes. HFS and APFS DMGs, direct PKGs, and
Insta360's ZIP containing a PKG were verified. The full Apple Silicon system
also built successfully. Runtime deployment and verification are recorded
separately in the private migration backup directory.

The supplied HandBrake and Zed links were HTML pages, so their versioned release
assets are used. The supplied 1Password ZIP contains only its downloader; the
complete PKG is used instead, following
[1Password’s deployment guidance](https://support.1password.com/deploy-1password/).
Mutable endpoints currently pin Rambox 2.7.1, 1Password 8.12.38, and NordVPN
10.12.0 by hash. The supplied VS Code commit is version 1.140.0.

- [nix-darwin setup](https://github.com/nix-darwin/nix-darwin)
- [nix-darwin options](https://nix-darwin.github.io/nix-darwin/manual/)
- [nix-homebrew](https://github.com/zhaofengli/nix-homebrew)
- [Nixpkgs Android documentation](https://github.com/NixOS/nixpkgs/blob/master/doc/languages-frameworks/android.section.md)
- [Hidden Bar package](https://github.com/NixOS/nixpkgs/blob/c27cdad491a991b11ed731760aa2ef8db0cb0410/pkgs/by-name/hi/hidden-bar/package.nix)
- [macOS trash package](https://github.com/NixOS/nixpkgs/blob/c27cdad491a991b11ed731760aa2ef8db0cb0410/pkgs/os-specific/darwin/by-name/tr/trash/package.nix)
