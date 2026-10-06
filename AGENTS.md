# Agent guide

## Purpose and scope

This repository configures an existing Apple Silicon Mac with nix-darwin and
Home Manager. It provides persistent command-line tools, native macOS apps,
shell configuration, and selected desktop and editor preferences. It is not a
NixOS configuration, an Intel Mac configuration, or a project development shell.

These instructions apply throughout the repository. Follow the user's current
instructions and previously established authorization. Read the relevant source
before editing: this guide describes the architecture, while the Nix modules and
scripts define the actual behavior. `README.md` is the user-facing operational
guide. Historical verification notes in it are not proof that the current tree
has passed a build or been activated.

## Working principles

- Make the requested change in its source of truth. A live-machine repair alone
  is insufficient when the request concerns deployment or a new laptop.
- Preserve unrelated working-tree changes. Start with `git status --short` and
  inspect the relevant diff before editing. Do not reset, discard, commit, or
  push changes unless the task authorizes it.
- Keep changes focused. Do not update dependencies, migrate package managers,
  reformat unrelated files, or rewrite the app inventory as incidental cleanup.
- Distinguish editing, evaluation, building, activation, and runtime
  verification. A successful build does not mean that the configuration has been
  activated or that a GUI application works correctly.
- Proceed with authorized edits and proportionate checks without repeatedly
  asking for confirmation. Reuse authorization already given in the
  conversation. A request to edit configuration does not itself request system
  activation, application replacement, or unrelated package upgrades.
- Preserve existing apps, self-updates, user preferences, credentials, and data.
  Retain the repository's backup, atomic-write, retry, and idempotency behavior.
- Prefer the existing modules and helpers over parallel installation mechanisms
  or new abstractions for a single entry.
- Do not edit generated files in `/nix/store`, `/run/current-system`, or managed
  shell dotfiles. Edit the repository source and use the appropriate deployment
  path. Keep secrets, credentials, and private migration backups outside Git.
- Give concise progress updates during longer work. Report what changed, what
  was checked, what remains pending, and whether live state changed. Do not
  claim a visual or interactive fix from static configuration checks alone.

## Repository map

| Path                                  | Responsibility                                                                                                                                                             |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `AGENTS.md`                           | Instructions for agents working in this repository.                                                                                                                        |
| `README.md`                           | Installation, migration, maintenance, troubleshooting, and user commands.                                                                                                  |
| `Makefile`                            | `make build` runs the progress monitor; `make install` activates; `make test` uses uv; `make test-nix` runs the full Nix settings check; `make lock` updates flake inputs. |
| `host.nix`                            | Existing account, home override, Apple Silicon platform, Nix ownership, and Darwin compatibility version.                                                                  |
| `flake.nix`                           | Inputs, module wiring, `darwinConfigurations.mac`, app package outputs, and the settings check.                                                                            |
| `flake.lock`                          | Exact upstream input revisions; keep unchanged for routine configuration edits.                                                                                            |
| `configuration.nix`                   | System CLI packages, Zsh integration, fonts, Nix settings, and Homebrew declarations.                                                                                      |
| `home.nix`                            | Home Manager shell/Git configuration, prompt file, helper commands, and user activation.                                                                                   |
| `desktop.nix`                         | Applies the desktop preferences described in `settings/desktop.json`.                                                                                                      |
| `android.nix`                         | Composed Android SDK, Java runtime, SDK license configuration, and environment variables.                                                                                  |
| `mac-apps.nix`                        | Single inventory of vendor app downloads, hashes, bundle names, formats, and per-app exceptions.                                                                           |
| `app-installation.nix`                | Produces native installation manifests and orders system activation.                                                                                                       |
| `pkgs/app-sources.nix`                | Creates fixed-output `fetchurl` downloads from the app inventory.                                                                                                          |
| `pkgs/macos-apps.nix`                 | Filters enabled inventory entries and exposes app package derivations.                                                                                                     |
| `pkgs/mk-macos-app.nix`               | Extracts app archives or stages vendor PKGs during a build.                                                                                                                |
| `scripts/install_native_apps.py`      | Installs writable DMG/ZIP bundles as the user, with native metadata and replacement backups.                                                                               |
| `scripts/install_native_pkgs.py`      | Installs missing PKG products as root and verifies the expected app exists.                                                                                                |
| `scripts/restore_settings.py`         | Seeds editor files, restores Dock/Terminal snapshots, and maintains Terminal Shift+Enter bindings.                                                                         |
| `scripts/mac_preferences.py`          | Binary-safe CFPreferences access without a PyObjC dependency.                                                                                                              |
| `scripts/curl_progress.py`            | Converts curl's meter to structured Nix phase updates, preserving diagnostics, stdout, and exit status.                                                                    |
| `scripts/setup_editors.py`            | Explicit editor extension installation/configuration and verification.                                                                                                     |
| `scripts/verify_development_tools.py` | Read-only checks of Xcode, Command Line Tools, clang, and SDK selection.                                                                                                   |
| `settings/`                           | Checked-in preference snapshots, prompt configuration, and extension inventories.                                                                                          |
| `tests/`                              | Python tests of migration, installers, developer tools, and generated shell startup behavior.                                                                              |
| `.pre-commit-config.yaml`             | Prek hooks for formatting, syntax, and repository hygiene.                                                                                                                 |
| `.github/workflows/check.yml`         | Linux CI for portable tests, hooks, and lockfile metadata validation.                                                                                                      |
| `old/`                                | Historical reference only; not imported by the active flake.                                                                                                               |
| `result`                              | Local Nix build output link, when present; not configuration source.                                                                                                       |

Important settings files:

- `settings/desktop.json`: appearance, locale, Dock behavior, and trackpad
  values.
- `settings/dock.json`: captured app order; this does not install those apps.
- `settings/terminal.plist`: binary Terminal profile snapshot and startup
  settings.
- `settings/p10k.zsh`: Powerlevel10k prompt configuration.
- `settings/git.json`: global Git settings, including the user's identity.
- `settings/code-settings.json` and `settings/zed-settings.json`: writable
  editor settings seeds.
- `settings/editor-files.json`: maps editor seeds to user-relative destinations.
- `settings/editor-extensions.json`: requested extension IDs and captured
  metadata.
- `settings/capture.json`: provenance and intentional exclusions for the
  original capture; its hashes describe that capture, not necessarily current
  file content.

## Host, inputs, and compatibility

The configuration name is `mac`; it is not the computer's hostname. Commands use
`.#mac` or `.#darwinConfigurations.mac.system` regardless of the host's name.
Run commands from the repository root rather than copying a historical absolute
path from documentation.

The supported platform is `aarch64-darwin`. `host.nix` describes an existing
macOS account; do not turn it into account-creation logic. Read the username and
optional home override from that file instead of hardcoding personal paths in
new helpers. Review `settings/git.json` when adapting to another person.

`manageNix = true` lets nix-darwin manage upstream Nix. An externally managed
Nix distribution may require `false`; do not change this based only on the name
of the installer originally used. Preserve the disabled sudo PAM customization
on this managed Mac.

Darwin `stateVersion` and Home Manager `home.stateVersion` are compatibility
settings, not package versions. Do not increment them during routine upgrades.
Keep nixpkgs, nix-darwin, and Home Manager release branches compatible, and keep
their existing shared-nixpkgs wiring.

Ordinary package additions from existing inputs reuse `flake.lock`. `make lock`
runs `nix flake update` to refresh all declared inputs (or create a missing
lockfile), without building or activating. Run it only as a requested input
update, and review the resulting lock diff separately from vendor app hash
changes. Git-backed flakes omit untracked source files: ensure newly referenced
source files are included before a build, staging only intended files when
appropriate. Do not stage unrelated user work.

## Choosing where software belongs

| Request                             | Default location and behavior                                                                               |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Add a Nix CLI such as `wget`        | Add its nixpkgs attribute to `environment.systemPackages` in `configuration.nix`, with a short description. |
| Add a vendor DMG, ZIP, or PKG       | Add one entry to `mac-apps.nix`; the existing wiring discovers it.                                          |
| Change a Brew-owned tool            | Edit the existing `homebrew.brews` or `homebrew.casks` declarations.                                        |
| Change personal Zsh or Git behavior | Edit `home.nix`, `settings/p10k.zsh`, or `settings/git.json`, as applicable.                                |
| Change desktop preferences          | Edit the relevant `settings/` source or its restoration logic.                                              |
| Add an Android SDK component        | Declare the required component in `android.nix`.                                                            |

Do not install duplicate npm, Homebrew, or manually downloaded copies of a tool
already assigned an owner. Homebrew intentionally remains available for the
selected tools in `configuration.nix`. Preserve `cleanup = "none"`, disabled
automatic upgrades/updates, and shell integration that keeps fallback Brew paths
behind the default Nix paths. Do not uninstall old copies during an addition.

Nix installs Rustup, while Rustup manages toolchains separately. Do not add a
competing global Rust compiler or run `rustup self update` against the Nix copy.
The Android SDK is read-only and initially small: add only project-required API
levels, build tools, emulators, or NDKs. Do not use `sdkmanager --install` to
modify its store path. Finder-launched Android Studio may require explicit SDK
selection after store paths change.

## Required app download and hash workflow

This workflow is an explicit user preference. Do not substitute a prefetch or
URL-pinning workflow because it appears more convenient or reproducible.

1. Add or edit the app in `mac-apps.nix` using the **exact supplied download
   URL**. Preserve generic and `latest` endpoints. Do not follow redirects to
   replace them with version-specific CDN URLs. Existing unrelated URLs stay
   unchanged.
2. Set `hash = lib.fakeHash;` for new or changed download content. Keep existing
   hashes for unrelated entries.
3. For a configuration-edit request, stop at the edits and checks that do not
   download installers. Do not start an app build, prefetch, or direct download
   merely to discover its hash unless the user explicitly requests the build.
4. When the normal rebuild produces a fixed-output hash mismatch, use the exact
   `got: sha256-...` value for the identified app. This can come from an error
   pasted by the user or a build the user asked the agent to run.
5. Replace that app's placeholder with the reported hash. Preserve its supplied
   URL. Never use the placeholder's `specified:` value as the real hash.
6. Run further builds only within the requested scope. If the user has already
   authorized completing a build, continue through hash replacement and retry
   without asking for that authorization again.
7. Clearly report pending fake hashes. Configuration edits can be complete while
   download/build verification remains pending; do not claim otherwise.

Do not use `nix store prefetch-file`, `nix-prefetch-url`, `curl`, `wget`,
browser fetches, or another download mechanism to calculate hashes ahead of this
flow. The presence of `wget` in the package list does not change this rule. A
generic URL is intentional even though upstream may later replace its content: a
future hash mismatch must be resolved explicitly rather than silently accepted.

Use an observed version as package metadata when known. If the version is
unknown and not needed to fulfill the edit, use an honest placeholder such as
`"latest"` rather than inventing a release number or downloading the installer
to discover it. Metadata does not authorize changing the supplied URL.

Example configuration-only addition:

```nix
example = {
  version = "latest";
  downloadName = "example-latest.dmg";
  url = "https://vendor.example/download/latest/darwin/arm64";
  hash = lib.fakeHash;
  appName = "Example.app";
};
```

The installed bundle name must be accurate. Use available evidence; if its name
or archive layout is unverified, report that limitation instead of claiming the
package builds. Prefer Apple Silicon or universal assets. Intel-only exceptions
must remain explicit rather than changing the host platform.

### App inventory fields

| Field                 | Meaning                                                                                                 |
| --------------------- | ------------------------------------------------------------------------------------------------------- |
| `version`             | Package metadata; not a guarantee of the currently self-updated native version.                         |
| `url`                 | User-supplied download endpoint.                                                                        |
| `hash`                | Fixed-output SHA-256 in SRI form, or `lib.fakeHash` while awaiting a mismatch.                          |
| `appName`             | Expected installed `.app` name, including spaces and capitalization.                                    |
| `downloadName`        | Explicit store filename, useful for endpoints without an archive suffix.                                |
| `format`              | `dmg` by default; also `zip`, `pkg`, `zip-pkg`, and `dmg-pkg`.                                          |
| `appPath`             | Bundle path within the archive; defaults to `appName`.                                                  |
| `dmgExtractor`        | `undmg` by default; `7zz` is available for layouts such as APFS DMGs.                                   |
| `allowParentSymlinks` | Narrow extraction exception for a known vendor bundle layout.                                           |
| `enable`              | Defaults to true; false excludes the entry from app package outputs and installation.                   |
| `removeFinderInfo`    | Targeted native-copy exception for an evidenced FinderInfo/signature issue.                             |
| `removeQuarantine`    | Targeted native-copy exception; never a blanket Gatekeeper change.                                      |
| `preserveXattrs`      | Existing inventory annotation; native deployment already preserves extended attributes for all bundles. |

Do not add extraction, quarantine, symlink, or signature exceptions
speculatively. Do not patch or re-sign vendor binaries as a routine installation
workaround.

## Build and deployment architecture

The app inventory feeds fixed-output source derivations and package outputs.
`nix build .#example.src` downloads only the source; `nix build .#example`
checks extraction or stages its installer. Both may fetch substantial data.
Neither command installs the native app in `/Applications`.

Supported archive behavior:

| Format                | Build output                       | Activation                                        |
| --------------------- | ---------------------------------- | ------------------------------------------------- |
| `dmg` / `zip`         | Extracted `.app` for layout checks | Native writable bundle copy into `/Applications`. |
| `pkg`                 | Staged vendor PKG                  | Apple's installer runs for a missing product.     |
| `zip-pkg` / `dmg-pkg` | Exactly one extracted PKG          | Same native PKG installation flow.                |

Archives containing multiple PKGs fail instead of choosing an arbitrary one.
Store-built app bundles are verification artifacts, not the deployed copies: the
Nix store cannot retain all extended attributes used by some signatures.

Activation runs missing PKG installations as root, then native app installation
as the configured user, before Home Manager restores user settings. Native DMGs
are mounted read-only and copied with Apple's `ditto`, preserving resources and
extended attributes. Installed bundles remain writable for vendor updaters.

Ordinary rebuilds preserve existing apps, including self-updated copies. A new
inventory version/hash updates the bootstrap source, not every installed app.
Explicit replacement is a separate operation. Preserve installation locks,
staging, backup verification, atomic rename recovery, and failure propagation.

Replacement backups are native ZIP archives ending in `.zip.bckp` under the
user's private state directory. Do not leave ordinary unpacked backup apps where
vendor installers may discover them. App replacement may quit an app; avoid it
unless replacement is within the request. PKG installers can affect services,
drivers, and files outside `/Applications`; Nix rollback does not undo those
changes. Removing an inventory entry does not uninstall the native app.

## Shell, fonts, and Terminal

Home Manager owns the generated Zsh settings and `.p10k.zsh`. The writable
`~/.zshrc` loads the managed `~/.config/zsh/nix-zshrc`, allowing applications
such as Docker Desktop to append setup lines. `seed_zshrc()` in
`scripts/restore_settings.py` backs up and migrates the old managed symlink
before Home Manager's link cleanup. It preserves regular-file content and
subsequent app edits, refuses unrelated symlinks, and respects dry runs. Do not
turn this entry point back into a store symlink or overwrite app additions.
Preserve instant-prompt ordering, the Oh My Zsh Git plugin, and the existing
Powerlevel10k loading path. Keep inherited project toolchains ahead of fallback
system paths in subshells. Retain conditional Cargo and Python framework
initialization. Local user extensions belong in `~/.zshrc.local`, not edits to
generated store files.

For broken prompt icons, distinguish three independent layers:

1. The font package is installed and registered with macOS.
2. The actual terminal window/profile selects that font.
3. The prompt emits a glyph supported by that font and has not hidden the icon.

Do not diagnose only from the saved default profile. Existing windows can use a
different profile, and installed font metadata alone does not prove the glyph
will render. MesloLGS NF is declared in `configuration.nix`; the captured Basic
profiles use it at 11 points and Clear Dark uses it at 12 points. Preserve font
size, colors, and unrelated profile settings during a repair.

Zed uses its own `terminal.font_family` setting, independent of Apple Terminal.
Keep `"MesloLGS NF"` in `settings/zed-settings.json` and the corresponding
`terminal.integrated.fontFamily` in `settings/code-settings.json`.
`restore_editor_fonts()` maintains these terminal font keys on every activation
and shares the VS Code font across profiles through
`workbench.settings.applyToAllProfiles`. Seeding still preserves existing files;
the separate font repair backs up original bytes, refuses symlinks, and writes
atomically. Changed JSONC/JSON5 files become JSON; comments remain in backups.
Preserve editor/UI fonts, terminal size, and other settings. macOS has no
universal terminal-font preference; additional apps require their own settings.

Shift+Enter is maintained by `terminal_keybindings()` in
`scripts/restore_settings.py`. Both `$000D` (Shift+Return) and `$0003`
(Shift+keypad Enter) send `\x1b[13;2u`. This distinguishes the key from ordinary
Return for Codex CLI. These two mappings are applied to all profiles on every
Terminal activation pass, including when `--once` skips the profile snapshot.
Keep other bindings intact. Merely adding a binding to Basic (Shift-Enter) is
insufficient for a user running Clear Dark or a custom profile.

Use `plistlib` for binary Terminal snapshots and nested archived font data. Use
the CFPreferences helper for live preferences; text/XML exports can mishandle
embedded control characters. Back up before live writes. Terminal may cache its
preferences, so explain when a full quit/reopen is needed; do not close the
user's active sessions just to validate a change.

## User settings and migration behavior

`home.nix` runs `mac-config-restore all --once` after Home Manager's write
boundary. Desktop defaults in `desktop.nix` are applied each rebuild. Dock and
Terminal snapshots have separate completion markers beneath
`~/.local/state/nix-macos-config`; Terminal's managed key mappings are the
intentional exception to one-time profile restoration.

Preserve these contracts when changing migration code:

- Missing editor settings are seeded as writable files. Existing files and
  symlinks, including dangling symlinks, are preserved by default.
- The separate editor-fonts pass maintains only the VS Code/Zed terminal font
  keys and VS Code's shared-profile entry, including with `all --once`.
- Explicit editor replacement backs up the existing object and does not write
  through its symlink target.
- Terminal snapshots merge profiles. Repeated activation preserves user profile
  choices except for explicitly managed keys.
- Dock restoration skips missing apps and retains unrelated preferences. Missing
  Dock entries are not requests to install more software.
- Completion markers are written only after successful operations. Failures must
  remain eligible for retry.
- Dry runs do not create files, backups, markers, or preference writes.
- Backups and state stay private and outside the repository. Nix rollback does
  not restore writable preferences; use the saved backups when needed.

Home Manager uses `.before-nix` backups when adopting managed dotfiles. If a
backup already exists, inspect the conflict rather than overwriting or deleting
it blindly.

Editor extension setup is explicit, not part of routine activation. VS Code uses
its native CLI for missing extensions; Zed merges `auto_install_extensions` and
installs on launch. Preserve existing settings/extensions and refuse writes
through symlinks. Captured extension versions are audit metadata, not a mandate
to downgrade. Do not reintroduce excluded machine-specific SDK/interpreter or
temporary extension paths from old snapshots.

## Validation strategy

Use the smallest checks that provide useful evidence for the requested change.
Do not download vendor installers to validate an inventory-only edit. Do not
write tests that simply repeat a package-list addition or a documentation edit.
Add behavioral regression tests for migration, preservation, failure recovery,
installer changes, or shell-path logic.

### Local checks without vendor downloads

From the repository root, substituting only files relevant to the edit:

```sh
git diff --check
nixfmt --check configuration.nix mac-apps.nix
prek run --files configuration.nix mac-apps.nix AGENTS.md
```

Prek can initialize its own hook environments; it does not validate vendor DMG
contents. Check for formatting changes made by hooks and rerun failed hooks
after addressing their output.

Use `make test` to run the suite through uv, matching Linux CI. The target runs
`uv run --with json5==0.13.0 python -B -m unittest discover -s tests -v`; uv
supplies the dependency environment. CI installs uv with `astral-sh/setup-uv`
and calls `make test`. Do not add Python selectors or manual venv/pip setup.

Use `make test-nix` on Apple Silicon to run the complete Nix settings check. It
supplies packaged Python/json5 and generated Home Manager Zsh files. The Nix
builder runs unittest directly, without uv or network dependency resolution.
Neither target builds vendor apps or activates the system. Tests use temporary
homes and mocked preferences. Native tests are platform-dependent. Generated Zsh
startup tests require the Nix check's environment; do not describe a uv run with
skipped tests as equivalent coverage.

### Nix checks and builds

Choose these only when their scope is appropriate and any app downloads are
within the user's request. Even evaluation/metadata commands may fetch missing
flake inputs; do not describe them as necessarily offline.

```sh
nix flake metadata --no-update-lock-file
nix build --no-update-lock-file --no-link .#checks.aarch64-darwin.settings
```

The settings derivation runs Python tests with `json5` and generated Home
Manager Zsh files. It does not need to install GUI apps. Linux CI runs the
portable Python tests, Prek, and lockfile metadata validation; it does not
establish that Apple Silicon app extraction, native installation, or GUI
rendering succeeds.

For an explicitly requested app build, follow the fake-hash workflow above:

```sh
nix build --no-update-lock-file --no-link .#example.src
# Replace lib.fakeHash with the exact reported got: hash, then retry as authorized.
nix build --no-update-lock-file --no-link .#example
```

For an explicitly requested complete system build:

```sh
nix build --no-update-lock-file --no-link .#darwinConfigurations.mac.system
```

A full system build can fetch all declared app sources even when their native
apps already exist. Pending fake hashes intentionally prevent successful source
verification until the mismatch workflow has been completed. Do not bypass them
or run an unsolicited full build to make the check appear green.

## Activation and operational commands

Build progress must work on the first build, before system activation. Do not
wrap or alias `nix` in shell startup files, or require sourcing a shell
function. The native Nix client renders one live status row; a flake cannot
reconfigure the running client's renderer into a multiline dashboard. Be
explicit about that limitation instead of promising that an activation-time
change fixes the first build. Preserve stdout, errors, exit codes, hash
verification, and cancellation. Validate display changes with local fixtures,
without downloading vendor installers or activating the system.

From the repository root, `make build` runs the flake's `nix-output-monitor` and
builds `.#darwinConfigurations.mac.system` into `result`, without changing the
lockfile. `make install` depends on that successful build, then runs
`sudo ./result/sw/bin/darwin-rebuild switch --flake .#mac --no-update-lock-file`.
The bundled launcher works before the first activation; `switch` records the
system generation. Bare `make` means `make build`. Adding or editing these
targets does not authorize running a full build or activation. Check recipes
with dry runs and mock commands when appropriate.

On an already bootstrapped machine, when activation is requested:

```sh
sudo darwin-rebuild switch --flake .#mac --no-update-lock-file
```

For a new laptop, first review the account, Git identity, Apple Silicon
platform, Nix ownership, and compatibility settings. Follow the bootstrap
sequence in `README.md`, resolve build errors, then activate. Preserve existing
installations and credentials until replacements are verified. Do not introduce
a mass cleanup or reinstall Nix just because `darwin-rebuild` is not yet on
PATH.

The following commands are available after deployment. They are an operational
reference, not instructions to run them all on every task.

| Command                                                     | Effect                                                                          |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `mac-config-restore all --dry-run`                          | Preview restoration without writing preferences or state.                       |
| `mac-config-restore terminal --once`                        | Preserve an already restored snapshot while repairing the managed key mappings. |
| `mac-config-restore terminal`                               | Explicitly reapply the captured Terminal snapshot and managed key mappings.     |
| `mac-config-restore dock`                                   | Explicitly restore captured Dock order.                                         |
| `mac-config-restore editors`                                | Seed missing editor settings.                                                   |
| `mac-config-restore editor-fonts`                           | Repair VS Code/Zed terminal fonts with backups.                                 |
| `mac-config-restore editors --replace-existing`             | Back up and replace editor settings.                                            |
| `mac-config-setup-editors all`                              | Request installation/configuration of missing editor extensions.                |
| `mac-config-setup-editors all --verify`                     | Check extension installation.                                                   |
| `mac-config-verify-development-tools`                       | Read-only Xcode/CLT/SDK diagnostics.                                            |
| `mac-config-install-apps --only example`                    | Install a missing native app as the user.                                       |
| `mac-config-install-apps --only example --replace-existing` | Explicitly back up and replace a native app.                                    |
| `mac-config-install-pkgs --dry-run`                         | Preview missing PKG installations.                                              |
| `sudo mac-config-install-pkgs`                              | Run native installers for missing PKG products.                                 |

User preference/editor commands and native bundle installation run as the
configured user, not root. PKG installation requires root. Never fix a
permission error by making user preferences or writable app copies root-owned.

After activation, verify the behavior relevant to the change: command resolution
in a new shell, active Terminal profile and keyboard behavior, or the affected
app's native installation. A restart requirement is a remaining user action, not
something already tested by a build. Do not accept developer-tool licenses or
change `xcode-select` as a side effect of the read-only verification command.

## Documentation and completion

Keep this guide, the README, and code comments consistent when changing a
workflow. Preserve the explicit download rules even if an older example or
historical note recommends resolving a versioned URL. Do not turn dated local
observations into permanent requirements for every laptop.

A completion report should state the changed source files, relevant validation,
and any outstanding hash, build, activation, restart, or runtime verification.
Separate changes saved in this checkout from changes applied to the machine and
from changes committed or pushed to Git. A new laptop can only consume the
updated configuration once the changes are transferred through the user's chosen
workflow.
