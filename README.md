# Mac configuration

Personal macOS software and settings managed with **nix-darwin and nixpkgs 26.05**. There are two profiles: `macbook-arm` (Apple Silicon) and `macbook-intel` (Intel). Nix is preferred for native Mac applications and CLI tools; Homebrew and the Mac App Store cover the remaining packaged applications.

The reference machine runs macOS 26.7. This reproduces software and selected settings, with the version differences listed below. It does not copy application data, logins, licenses, models, virtual machines or hardware identities. Only the newest observed installation of each item is inventoried. Employer-managed software is outside this configuration.

## Initial installation on another Mac

1. Install macOS, create your local administrator account and sign in. macOS 26.7 is the reference version; application requirements may prevent using the full inventory on older systems.
2. Install Apple's Command Line Tools and wait for the installation to finish:

   ```sh
   xcode-select --install
   ```

3. Install upstream Nix in multi-user mode using the [official installer](https://nix.dev/manual/nix/stable/installation/installing-binary.html):

   ```sh
   curl -L https://nixos.org/nix/install | sh -s -- --daemon
   ```

   Open a new terminal and run `nix --version`. This configuration lets nix-darwin manage upstream Nix. An existing Determinate Nix installation needs its documented integration settings instead; do not overlay a second installer on it.

4. Install [Homebrew](https://brew.sh/) using its official installer:

   ```sh
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

   Use native Homebrew: `/opt/homebrew` on Apple Silicon or `/usr/local` on Intel. Follow its printed shell setup instructions. A second Intel Homebrew installation under Rosetta is not needed.

5. Sign into the Mac App Store. Acquire the applications listed in the App Store rows below before the first switch; `mas` cannot sign in or purchase an app for you. Accept any account terms interactively.
6. Clone or copy this repository into a directory owned by your account. Set `username` in `flake.nix` and review the Git identity in `home.nix`. If you initialize Git locally, add the configuration files before using a Git-backed flake: Nix ignores untracked files in a Git repository.
7. Enable the CLI features for this bootstrap shell, choose the matching profile, and check/build it:

   ```sh
   export NIX_CONFIG='experimental-features = nix-command flakes'
   # Apple Silicon:
   export MAC_CONFIG_HOST=macbook-arm
   # On Intel, use: export MAC_CONFIG_HOST=macbook-intel
   nix develop -c bash scripts/check.sh
   nix build ".#darwinConfigurations.${MAC_CONFIG_HOST}.system"
   ```

   Evaluation includes both profiles; building must use the native architecture or a matching remote builder. Some source-built GUI packages have large closures and can take substantial time on an empty cache.

8. Activate from a local graphical terminal:

   ```sh
   sudo nix --extra-experimental-features 'nix-command flakes' \
     run github:nix-darwin/nix-darwin/nix-darwin-26.05#darwin-rebuild -- \
     switch --flake ".#${MAC_CONFIG_HOST}"
   ```

   Grant Terminal App Management permission if macOS requests it. Nix applications are copied by nix-darwin into `/Applications/Nix Apps`; casks and App Store apps live in `/Applications`. Existing Home Manager files are backed up with `.before-nix`; if that backup already exists, move it aside deliberately before retrying. Homebrew cleanup is disabled, so existing installations are not automatically removed. When adopting Nix on an existing Mac, migrate each app to one installation owner rather than keeping two copies with the same bundle identifier.

9. Open a new terminal. Complete the manual-install and data-migration checklist below, initialize development tools, and seed editor extensions:

   ```sh
   bash scripts/setup-development.sh rust
   bash scripts/setup-development.sh android
   bash scripts/setup-editors.sh code
   bash scripts/setup-editors.sh cursor
   open settings/Basic-Shift-Enter.terminal
   python3 scripts/restore-dock.py
   ```

   The Android command prompts for licenses and downloads the architecture-appropriate emulator image. If Google no longer publishes a listed image, select a supported image in Android Studio; this is not a silent Nix substitution. In Terminal settings choose the imported **Basic (Shift-Enter)** profile as both the default and startup profile. Dock restoration skips applications that are not yet installed and can be rerun after installing them.

### Intel differences

- QGIS uses the Homebrew cask on Intel because the 26.05 Nix dependency `arrow-cpp` is marked broken there. Apple Silicon keeps the Nix package.
- Orchard uses Apple Containers and is limited to Apple Silicon; see its [upstream requirements](https://github.com/andrew-waters/orchard).
- LM Studio is explicitly omitted: the audited Nix package and current cask have no Intel Mac build.
- Xcode 27 requires Apple Silicon and macOS 26.6+. The Intel profile omits its App Store entry. Install the **Xcode 26 universal distribution** from [Apple Developer downloads](https://developer.apple.com/download/all/), then select it with `sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer`. Open Xcode to accept its license and install requested components.
- Android emulator images use `x86_64` instead of `arm64-v8a`. Rust initialization installs both Darwin targets, but Windows/Linux linkers are not supplied by adding a Rust target.
- Homebrew formulas without an Intel bottle may compile from source. App Store and vendor downloads may change architecture support independently of the lockfile.
- On Apple Silicon, install Rosetta only when an Intel-only vendor application requires it, using Apple's normal installation prompt.

## Daily use and maintenance

```sh
make check                   # lint, migration tests, both-profile evaluation, flake checks
make fmt                     # format Nix source
make build                   # native profile; override with HOST=macbook-intel
make switch                  # activate the native profile
make update                  # deliberately update the three locked inputs
make docs                    # regenerate inventory tables after inventory edits
```

After updating inputs, inspect the diff, rerun checks and build before switching. Keep `system.stateVersion = 7` and `home.stateVersion = "26.05"` unchanged unless following a documented state migration. Both Home Manager and nix-darwin follow the same nixpkgs input; no unstable overlay is used.

`inventory.json` is the installation list and the source of the software tables below. To add a package, add one item with its source (`nix`, `cask`, `brew` or `mas`), package attribute/token/ID and a meaningful note. `systems` is needed only for a real architecture restriction. `software.nix` resolves Nix attributes and asserts platform support instead of silently omitting packages. Do not add the same application to two providers.

Refresh `availableVersion` after a lockfile update by comparing the two audit outputs, then regenerate the README:

```sh
nix eval --json .#packageAudit.aarch64-darwin
nix eval --json .#packageAudit.x86_64-darwin
python3 scripts/inventory.py
```

Nix GUI applications update through the lockfile; do not use self-updaters to modify managed bundles. Homebrew auto-update/upgrade and cleanup are disabled during activation. Update those separately with `brew update` and intentional `brew upgrade` commands; use the App Store for store updates. The lockfile does not pin cask downloads, store versions, Rust toolchains installed by rustup or marketplace extensions.

For a Nix rollback, list generations with `sudo darwin-rebuild --list-generations`, then use `sudo darwin-rebuild switch --rollback` or a documented `--switch-generation` selection. Keep prior generations until the new one is tested. This cannot undo Homebrew/App Store updates, writable settings or application database migrations; back up personal data independently.

## Settings ownership

| Setting | Owner and behavior |
|---|---|
| Zsh / Oh My Zsh / Git plugin | Home Manager; immutable configuration, with Nix ahead of user-installed executables; optional `~/.zshrc.local` is sourced last |
| Powerlevel10k | Nix theme plus the captured `settings/p10k.zsh` |
| Git | Observed name/email, disabled commit signing and ignored-file advice; review identity for another user |
| `code` / `vscode` | `code` remains a Cursor shell alias; `vscode` explicitly launches VS Code |
| Dark appearance / language / locale | nix-darwin: Dark, `en-US`, `en_US` |
| Dock | nix-darwin: autohide, bottom, size 64, no recents; explicit restore command applies the recorded app order |
| Finder | Column view, folders first |
| Trackpad | Tap-to-click and secondary click enabled, three-finger drag disabled, speed 0.875 |
| Terminal | Captured binary `.terminal` profile includes fonts/colors and Shift-Enter handling; import and choose it in Terminal |
| VS Code / Cursor / Zed | Seeded once into writable user files; existing files and symlinks are never overwritten |
| Cursor keybinding | `cmd+i` invokes `composerMode.agent` |
| Python / Flutter editor paths | Portable Python command and the selected Nix Flutter SDK replace this Mac's absolute paths; update an already-seeded Flutter path after SDK updates |
| Editor extensions | Captured IDs and versions below; explicit setup commands use vendor marketplaces and report any failures |
| Zed extensions | Install TOML, Nix, Dockerfile, reStructuredText, HTML, Git Firefly, Make, Log, WGSL and Ruby from Zed's extension browser |
| Browser extensions | Restore using browser sync or the recorded IDs; extension configuration is separate |
| MesloLGS NF / Open Sans | Nix font packages; exact original Open Sans variable fonts require a separate licensed/source-file restore |
| Raycast / AltTab / Moom / Mac Mouse Fix / Bazecor | Export settings/keymaps from the original application, then import into the new installation |
| AI tools | Recreate portable settings/plugins from their supported exports; review hooks and machine-specific paths before restoring |
| Credentials and application data | Private backup/sync, outside Nix and this repository |

Editor extension entries marked available in Nix are informational. They use writable marketplace installations so editor-specific registries, updates and user profiles continue to work. A Nix attribute existing does not establish compatibility with Cursor's extension registry or license terms. The scripts use the explicit app CLI, avoiding the `code` alias.

## Manual installation and migration checklist

- Use the installation source in each **Manual** row below. For privately distributed apps, retain the original installer or obtain a release from the project owner; a locally found app does not prove a public installer or Intel build exists. FrameForge, TitanMesh and Compass Sidecar have source repositories identified in the table.
- Install Adobe Creative Cloud from Adobe, sign in and install Photoshop. Restore presets separately. Restore commercial licenses for Araxis, Moom, Screen Studio, Metashape, DecoPlanner and other paid products.
- Wine Stable and the GStreamer runtime casks were disabled on 2026-09-01 for Gatekeeper failures. They are intentionally not activation dependencies. Consult the upstream distribution for a supported installer; this repository does not disable Gatekeeper or force-install disabled casks. Nix GStreamer libraries are not the same as the vendor system framework.
- Restore RØDE, audio, printer and hardware drivers using their vendor installers when the associated device is used. Approve system extensions, microphone, camera, screen capture and Accessibility permissions through macOS. Installer-owned background helpers are recreated by their parent applications.
- Sign into 1Password, browsers, messaging, cloud storage, VPNs and developer services. Re-establish browser integration and system-extension permissions. Never commit vaults, SSH keys, tokens, certificates, browser profiles, cookies or license files.
- Restore Raycast exports, keyboard layouts, mouse/window-manager preferences, Terminal profile, browser sync and editor profiles. Import Postman workspaces, pgAdmin connections and QGIS plugins privately because exports can contain credentials.
- Copy source repositories, survey/GIS data, Garmin maps, Adobe assets, notes, application databases and LM Studio models from a backup. Docker/Podman images, volumes and VMs are data migrations; the configuration only installs their tools. Podman setup is explicit: `podman machine init`, then `podman machine start`.
- Review portable settings from `~/.claude/settings.json`, `~/.config/opencode/opencode.json`, `~/.codex` and related app exports. Do not copy authentication files, conversations or arbitrary hooks into the Nix store. Existing configuration for a tool does not by itself cause that tool to be installed.
- Install standalone tools absent from 26.05 only when required:

  ```sh
  cargo install --locked create-tauri-app --version 4.7.0
  npm install --global --prefix "$HOME/.local" unirepo-cli@0.6.0
  mise install conda:conda@26.5.0
  ```

  For Railpack use its [upstream installation guide](https://railpack.com/getting-started). For WebAssembly, use a project-specific `wasm-bindgen-cli` matching the crate version in that project's lockfile; 26.05's default is not the observed 0.2.123. Nix-managed Cargo tools must be updated through Nix, not `cargo install-update`.

- Restore Ruby tools as user gems under Nix Ruby, for example `gem install --user-install xcodeproj -v 1.27.0`. Add the executable directory reported by `ruby -e 'puts Gem.user_dir'` plus `/bin` to `~/.zshrc.local` if needed. Prefer each project's Gemfile for dependencies; do not install gems into Apple's system Ruby or Nix's store.

## Validation

`make check` runs Nix formatting, statix, deadnix, ShellCheck, inventory/documentation consistency checks, migration tests, explicit evaluation of both profiles and `nix flake check`. CI uses native ARM and Intel macOS runners and never activates the configuration, installs GUI apps or logs into the App Store.

Build and runtime verification are separate from evaluation. On a new Mac, run `make build`, switch, then check `git --version`, `node --version`, `python3 --version`, `rustup show` and a fresh Zsh session. Launch the GUI apps and verify 1Password/browser integration, sound/camera permissions and device helpers. See `VALIDATION.md` for the results obtained while implementing this configuration.

## Inventory

The initial source audit used nixpkgs revision `dc8993a5c130c05a8565579014968a112d416d76`. Current resolved versions are maintained in the tables below. Availability means the named package supports the selected architecture in its metadata and passes configuration evaluation; it is not a claim that every app has been launched on both kinds of Mac.

<!-- inventory:start -->

Inventory captured 2026-09-29. Nix versions refer to the committed lockfile; Homebrew versions are audit-time observations, not pins.

### Applications

| Item | Installed | Install source | Available version | ARM / Intel | Difference / remaining setup |
|---|---|---|---|---|---|
| 1Password | 8.12.36 | pkgs._1password-gui | 8.12.21 | yes / yes | Grant app/browser integration permissions after launch; import vaults by signing in. |
| 1Password for Safari | 8.12.37 | [App Store: 1569813296](https://apps.apple.com/app/id1569813296) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| Adobe Photoshop 2025 | 26.0.0 | [Manual](https://www.adobe.com/products/photoshop.html) | see notes | vendor / vendor | Install Creative Cloud from Adobe, sign in, then install Photoshop. Restore presets and license separately. |
| AltTab | 11.4.3 | pkgs.alt-tab-macos | 10.12.0 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Android Studio | 2025.3 | [cask: android-studio](https://formulae.brew.sh/cask/android-studio) | 2026.1.4.8,quail4-patch1 | yes / yes | 26.05 android-studio supports Linux, not this macOS app. Keep its SDK writable. |
| AnkerWork | 3.0.4 | [cask: ankerwork](https://formulae.brew.sh/cask/ankerwork) | 3.0.4 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| APMPMetadata | 1.5 | [App Store: 6752358792](https://apps.apple.com/app/id6752358792) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| Apple Configurator | 2.20 | [App Store: 1037126344](https://apps.apple.com/app/id1037126344) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| Araxis Merge | 2024.6001 | [cask: araxis-merge](https://formulae.brew.sh/cask/araxis-merge) | 2026.1 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Ariane | 26.4.1 | Manual | see notes | vendor / vendor | Obtain the vendor macOS installer and restore application preferences and survey data. |
| Audacity | 3.7.0.0 | pkgs.audacity | 3.7.7 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| balenaEtcher | 2.1.4 | [cask: balenaetcher](https://formulae.brew.sh/cask/balenaetcher) | 2.1.7 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Bazecor | 1.8.3 | [cask: bazecor](https://formulae.brew.sh/cask/bazecor) | 1.10.0 | yes / yes | Nix package is Linux-only. Export keyboard layers separately. |
| Brave Browser | 152.1.94.121 | pkgs.brave | 1.96.59 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Claude | 1.44121.4 | [cask: claude](https://formulae.brew.sh/cask/claude) | 2.9939.4,a166d8a7c640e65ad825ebfb99d74ccbb9c8940d | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Codex | 26.810.52044 | [Manual](https://openai.com/codex/) | see notes | vendor / vendor | Install the desktop app from its official distribution. pkgs.codex is the CLI. The codex-app cask is deprecated and older than this installed app. |
| Concept2 Utility | 7.18 | [cask: concept2-utility](https://formulae.brew.sh/cask/concept2-utility) | 7.18.00 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Cursor | 3.9.16 | pkgs.code-cursor | 3.5.17 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| DecoPlanner | 4.6.5 | [Manual](https://www.gue.com/decoplanner) | see notes | vendor / vendor | Obtain the vendor macOS installer and activate your license. |
| Developer | 11.1 | [App Store: 640199958](https://apps.apple.com/app/id640199958) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| Docker | 4.91.0 | [cask: docker-desktop](https://formulae.brew.sh/cask/docker-desktop) | 4.93.0,240920 | yes / yes | Docker owns its CLI, Compose, credential helpers and Kubernetes integration; do not install competing copies. |
| Evernote | 10.114.2 | [cask: evernote](https://formulae.brew.sh/cask/evernote) | 10.105.4,20240910164757,a2e60a8d876a07eded5d212fa56ba45214114ad0 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Firefox | 152.0.5 | pkgs.firefox-bin | 156.0.1 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Fortuna | 0.4.0 | Manual | see notes | vendor / vendor | Obtain the original signed release; no matching 26.05 package or Homebrew cask found. |
| FrameForge | 1.0.0 | [Manual](https://github.com/DEKHTIARJonathan/FrameForge) | see notes | vendor / vendor | Install a project release, or follow the project build instructions. Source repository found locally; access may be required. |
| Garmin BaseCamp | 4.8.13 | [cask: garmin-basecamp](https://formulae.brew.sh/cask/garmin-basecamp) | 4.8.13 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Garmin MapInstall | 4.3.6 | Bundled: garmin-basecamp | see notes | both | Installed by the BaseCamp package; do not add a second installer. |
| Garmin MapManager | 3.1.3 | Bundled: garmin-basecamp | see notes | both | Installed by the BaseCamp package; do not add a second installer. |
| GitKraken | 12.5.0 | pkgs.gitkraken | 12.1.1 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| GLKVM | 1.4.0 | [cask: glkvm](https://formulae.brew.sh/cask/glkvm) | 1.5.0,1782704518562,release1 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Google Chrome | 154.0.8037.92 | pkgs.google-chrome | 154.0.8037.58 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Google Earth Pro | 7.3 | [cask: google-earth-pro](https://formulae.brew.sh/cask/google-earth-pro) | 7.3.7.1327 | yes / yes | Nix package is Linux-only. |
| GoPro Quik | 2.2.0 | [App Store: 561350520](https://apps.apple.com/app/id561350520) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| HandBrake | 1.10.2 | [cask: handbrake-app](https://formulae.brew.sh/cask/handbrake-app) | 1.11.2 | yes / yes | Nix package is marked broken on Darwin. |
| Hidden Bar | 1.10 | pkgs.hidden-bar | 1.10 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| IDLE | 3.12.4 | [Manual](https://www.python.org/downloads/macos/) | see notes | vendor / vendor | Nix Python with tkinter provides IDLE tooling; python.org is needed for the original macOS app bundle. |
| Insta360 Studio | 5.9.2 | [cask: insta360-studio](https://formulae.brew.sh/cask/insta360-studio) | 6.0.5,release_insta360,RC_build14,_20260914_170949_signed_1789378030265,06db645109da4b238b629f847dda1aba | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Keynote Creator Studio | 15.3.1 | [App Store: 361285480](https://apps.apple.com/app/id361285480) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| LM Studio | 0.4.12+1 | pkgs.lmstudio | 0.4.15-2 | yes / no | No x86_64-darwin package or current Intel cask. Intel profile omits this app explicitly. |
| Mac Mouse Fix | 3.0.8 | [cask: mac-mouse-fix](https://formulae.brew.sh/cask/mac-mouse-fix) | 3.1.0 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| MeshLab2025.07 | 2025.07 | pkgs.meshlab | 2025.07 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| MetashapePro | 2.1.3 | [cask: metashapepro](https://formulae.brew.sh/cask/metashapepro) | 2.3.2 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Microsoft Excel | 16.113.2 | [cask: microsoft-excel](https://formulae.brew.sh/cask/microsoft-excel) | 16.113.26092012 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Microsoft OneNote | 16.113.2 | [cask: microsoft-onenote](https://formulae.brew.sh/cask/microsoft-onenote) | 16.113.26092012 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Microsoft Outlook | 16.113.2 | [cask: microsoft-outlook](https://formulae.brew.sh/cask/microsoft-outlook) | 16.113.26091740 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Microsoft PowerPoint | 16.113.3 | [cask: microsoft-powerpoint](https://formulae.brew.sh/cask/microsoft-powerpoint) | 16.113.26092012 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Microsoft Teams | 26246.1709.5146.8945 | [cask: microsoft-teams](https://formulae.brew.sh/cask/microsoft-teams) | 26225.1708.5124.9749 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Microsoft Word | 16.113.2 | [cask: microsoft-word](https://formulae.brew.sh/cask/microsoft-word) | 16.113.26092012 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Mole | 1.15.0 | [cask: mole-app](https://formulae.brew.sh/cask/mole-app) | 1.16.0 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Moom | 4.5.1 | [cask: moom](https://formulae.brew.sh/cask/moom) | 4.6.0 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| net.downloadhelper.coapp | 2.0.19 | [cask: netdownloadhelpercoapp](https://formulae.brew.sh/cask/netdownloadhelpercoapp) | 2.0.19 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. Homebrew marks this cask deprecated: discontinued. |
| NordVPN | 10.11.0 | [cask: nordvpn](https://formulae.brew.sh/cask/nordvpn) | 10.12.0 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Notion | 7.21.0 | pkgs.notion-app | 4.24.0 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Obsidian | 1.12.7 | pkgs.obsidian | 1.13.7 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| OneDrive | 26.153.0809 | [cask: onedrive](https://formulae.brew.sh/cask/onedrive) | 26.153.0809.0004 | yes / yes | Nix onedrive is a Linux CLI, not the installed Mac client. |
| Orchard | 2.4.3 | [cask: orchard](https://github.com/andrew-waters/orchard) | 2.4.3 | yes / no | Native GUI for Apple Containers. Requires macOS 26+ and Apple Silicon; install the Apple container runtime using the upstream setup instructions. |
| Personal Assistant | 1.2.9 | Manual | see notes | vendor / vendor | Use the original application distributor; confirm current download availability. |
| pgAdmin 4 | 9.5 | [cask: pgadmin4](https://formulae.brew.sh/cask/pgadmin4) | 9.18 | yes / yes | Keep the native desktop bundle; the Nix package provides a different Python deployment. |
| Plaud | 1.0.10 | [cask: plaud](https://formulae.brew.sh/cask/plaud) | 1.3.11 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Postman | 12.11.3 | pkgs.postman | 11.94.0 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| ProtonVPN | 6.5.1 | [cask: protonvpn](https://formulae.brew.sh/cask/protonvpn) | 6.5.1 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Python Launcher | 3.12.4 | [Manual](https://www.python.org/downloads/macos/) | see notes | vendor / vendor | python.org provides this macOS launcher bundle; the Nix Python package does not recreate it. |
| QGIS | 4.0.0 | pkgs.qgis | 4.0.3 | yes / no | Nix on Apple Silicon. Intel uses the QGIS cask because the 26.05 Arrow dependency is marked broken there. Restore plugins and projects separately. |
| QGIS (Intel) | 4.0.0 | [cask: qgis](https://formulae.brew.sh/cask/qgis) | 4.2.3 | no / yes | Intel fallback for the broken Nix Arrow dependency. Current cask version is not lockfile-pinned. |
| Rambox | 2.7.1 | [cask: rambox](https://formulae.brew.sh/cask/rambox) | 2.7.1 | yes / yes | Nix package is Linux-only. |
| Raycast | 1.104.30 | pkgs.raycast | 1.104.17 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Safari | 27.0 | macOS | see notes | both | Supplied and updated by macOS. |
| Screen Studio | 3.5.1-4051 | [cask: screen-studio](https://formulae.brew.sh/cask/screen-studio) | 3.7.5-4595 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Shadow PC | 9.9.10457 | [cask: shadow](https://formulae.brew.sh/cask/shadow) | 9.9.10481 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Signal | 8.28.0 | pkgs.signal-desktop | 8.25.0 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Slack | 4.52.162 | pkgs.slack | 4.49.89 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| SpeleoDB Compass Sidecar | 26.7.26 | [Manual](https://github.com/OpenSpeleo/speleodb_compass_sidecar) | see notes | vendor / vendor | Install the matching project release and restore the application data separately. |
| Spotify | 1.3.0.277 | pkgs.spotify | 1.2.92.147 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Tailscale | 1.96.5 | [cask: tailscale-app](https://formulae.brew.sh/cask/tailscale-app) | 1.102.4 | yes / yes | Use the signed GUI and system extension; pkgs.tailscale is a different CLI/service installation. |
| Telegram | 12.2 | [cask: telegram](https://formulae.brew.sh/cask/telegram) | 12.10,282985 | yes / yes | Keep the native Telegram for macOS client; telegram-desktop is a different application. |
| TestFlight | 4.4.0 | [App Store: 899247664](https://apps.apple.com/app/id899247664) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| The Unarchiver | 4.3.9 | [cask: the-unarchiver](https://formulae.brew.sh/cask/the-unarchiver) | 4.3.9,147,1742287964 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| TitanMesh | 1.0.0 | [Manual](https://github.com/DEKHTIARJonathan/TitanMesh) | see notes | vendor / vendor | Install a project release or build from source; restore identities and signing material privately. |
| Tor Browser | 14.0.6 | [cask: tor-browser](https://formulae.brew.sh/cask/tor-browser) | 15.0.23 | yes / yes | 26.05 tor-browser has Linux sources only. |
| Transporter | 1.4.5 | [App Store: 1450874784](https://apps.apple.com/app/id1450874784) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| Viewer | 2.1.3 | [Manual](https://www.agisoft.com/downloads/installer/) | see notes | vendor / vendor | Install Agisoft Viewer from the vendor; Metashape Professional is a separate application. |
| Virtual Desktop Streamer | 1.34.12 | [cask: virtual-desktop-streamer](https://formulae.brew.sh/cask/virtual-desktop-streamer) | 1.34.22 | yes / yes | No equivalent native Darwin package selected; vendor updates and licenses remain separate. |
| Visual Studio Code | 1.139.1 | pkgs.vscode | 1.119.0 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| VLC | 3.0.21 | pkgs.vlc-bin | 3.0.23 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| WhatsApp | 26.38.20 | pkgs.whatsapp-for-mac | 2.26.19.17 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Windows App | 11.4.1 | [App Store: 1295203466](https://apps.apple.com/app/id1295203466) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| Wine Stable | 11.0_1 | [Manual](https://github.com/Gcenx/macOS_Wine_builds/releases) | see notes | vendor / vendor | Homebrew wine-stable is disabled for Gatekeeper failures. Use a supported upstream distribution if available; Rosetta is required on ARM. No automatic security bypass. |
| Wondershare PDFelement | 12.1.28 | [App Store: 1470732135](https://apps.apple.com/app/id1470732135) | store current | yes / yes | Requires App Store sign-in/acquisition; current store version is not pinned by Nix. |
| Xcode | 27.0 | [App Store: 497799835](https://apps.apple.com/app/id497799835) | store current | yes / no | ARM: App Store. Intel: manually install Xcode 26 from Apple Developer downloads; Xcode 27 requires Apple Silicon. |
| Yubico Authenticator | 7.3.3 | [cask: yubico-authenticator](https://formulae.brew.sh/cask/yubico-authenticator) | 7.4.1 | yes / yes | Nix yubioath-flutter is Linux-only. |
| YubiKey Manager | 1.2.5 | [Manual](https://www.yubico.com/support/download/yubikey-manager/) | see notes | vendor / vendor | Legacy GUI, removed from nixpkgs. Do not substitute the CLI or Authenticator without noting the different interface. |
| Zed | 1.12.0 | pkgs.zed-editor | 1.3.6 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |
| Zoho Meeting | 4.1.0 | [Manual](https://www.zoho.com/meeting/desktop-app.html) | see notes | vendor / vendor | Install the vendor macOS application; sign in and grant microphone/camera permissions. |
| zoom.us | 7.0.0 (77593) | pkgs.zoom-us | 7.1.5.84650 | yes / yes | Update through the Nix lockfile; app is managed under /Applications/Nix Apps. |

### Developer tools

| Item | Installed | Install source | Available version | ARM / Intel | Difference / remaining setup |
|---|---|---|---|---|---|
| a2ps | 4.15.8 | pkgs.a2ps | 4.15.7 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Android platform tools | 37.0.1 | [cask: android-platform-tools](https://formulae.brew.sh/cask/android-platform-tools) | 37.0.1 | yes / yes | Keep SDK packages and licenses in a writable user SDK directory. |
| Android SDK | 36.1 / build-tools 36.1.0 / NDK 28.2.13676358 | [Manual](https://developer.android.com/studio) | see notes | vendor / vendor | Use scripts/setup-development.sh android; accept SDK licenses interactively. |
| Android SDK command-line tools | 15859902 | [cask: android-commandlinetools](https://formulae.brew.sh/cask/android-commandlinetools) | 15859902 | yes / yes | Keep SDK packages and licenses in a writable user SDK directory. |
| Bun | 1.3.14 | pkgs.bun | 1.3.13 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| cargo-audit | 0.22.2 | pkgs.cargo-audit | 0.22.1 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| cargo-binstall | 1.21.1 | pkgs.cargo-binstall | 1.19.1 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| cargo-deny | 0.20.2 | pkgs.cargo-deny | 0.19.6 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| cargo-edit | 0.13.7 | pkgs.cargo-edit | 0.13.10 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| cargo-machete | 0.9.2 | pkgs.cargo-machete | 0.9.2 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| cargo-nextest | 0.9.143 | pkgs.cargo-nextest | 0.9.136 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| cargo-outdated | 0.19.0 | pkgs.cargo-outdated | 0.19.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| cargo-update | 18.2.0 | pkgs.cargo-update | 20.0.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| cargo-wizard | 0.2.3 | pkgs.cargo-wizard | 0.2.3 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Claude Code | 2.1.177 | pkgs.claude-code | 2.1.223 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| CMake | 4.4.2 | pkgs.cmake | 4.1.6 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Codex CLI | 0.158.0 | pkgs.codex | 0.146.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Conda | 26.5.0 | [Manual](https://mise.jdx.dev/) | see notes | vendor / vendor | mise install conda:conda@26.5.0; activate only where required. |
| Corepack | 0.34.6 | pkgs.corepack | 0.36.0 | yes / yes | Lower path priority than the explicit pnpm package; do not run corepack enable against the Nix store. |
| create-tauri-app | 4.7.0 | [Manual](https://crates.io/crates/create-tauri-app) | see notes | vendor / vendor | cargo install --locked create-tauri-app --version 4.7.0 |
| FFmpeg | 8.1.2 | pkgs.ffmpeg_8 | 8.1.2 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Flutter / Dart | 3.35.6 / 3.9.2 | pkgs.flutter | 3.41.9 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Git LFS | 3.7.1 | pkgs.git-lfs | 3.7.1 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| GitHub CLI | 2.97.0 | pkgs.gh | 2.101.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Gradle | 9.7.0 | pkgs.gradle_9 | 9.4.1 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| GStreamer.framework | 1.28.6 | [Manual](https://gstreamer.freedesktop.org/download/) | see notes | vendor / vendor | Homebrew cask is disabled for Gatekeeper failures. Use a supported vendor framework installer. Nix libraries do not recreate the system framework. |
| herdr | 0.9.1 | [brew: herdr](https://formulae.brew.sh/formula/herdr) | 0.9.2 | yes / yes | Formula 0.9.2 verified; Intel has no bottle in this snapshot and may build from source. |
| Ionic CLI | 7.2.1 | pkgs.ionic-cli | 7.2.1 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| iperf3 | 3.21 | pkgs.iperf3 | 3.20 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Java Development Kit | OpenJDK 26.0.2 | pkgs.jdk25 | 25.0.3 | yes / yes | 26.05 provides JDK 25, not the observed JDK 26. JAVA_HOME is configured for Android sdkmanager and Java tools; Gradle may use its own Nix runtime. |
| JSON Schema CLI | 0.46.3 | pkgs.jsonschema-cli | 0.46.6 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Jujutsu | 0.44.0 | pkgs.jujutsu | 0.41.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| kind | standalone binary | pkgs.kind | 0.31.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| mise | 2026.5.10 | pkgs.mise | 2026.5.12 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| NASM | 3.02 | pkgs.nasm | 3.02 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Node.js / npm | 26.7.0 / 11.19.0 | pkgs.nodejs_26 | 26.10.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| npm-check-updates | 22.2.0 | pkgs.npm-check-updates | 19.3.2 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| OpenMP | 22.1.8 | pkgs.llvmPackages.openmp | 21.1.8 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Oracle Java browser plugin | installed framework | [Manual](https://www.java.com/) | see notes | vendor / vendor | Legacy browser plugin/control panel; a Nix JDK is not an equivalent. Reinstall only from a supported vendor distribution. |
| Pi coding agent | 0.70.6 | pkgs.pi-coding-agent | 0.75.4 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| pnpm | 11.1.3 | pkgs.pnpm_11 | 11.27.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Podman | 5.3.2 | pkgs.podman | 5.8.7 | yes / yes | Initialize the VM explicitly with podman machine init/start; no VM or daemon is created by activation. |
| prek | 0.4.14 | pkgs.prek | 0.3.11 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Python | 3.12.4 | pkgs.python312 | 3.12.14 | yes / yes | Includes pip, packaging and tkinter. Use uv/venvs for projects; never pip-install into the Nix store. |
| Railpack | 0.0.55 | [Manual](https://railpack.com/getting-started) | see notes | vendor / vendor | Use the upstream installer or release binary; absent from audited nixpkgs. |
| Railway CLI | 4.16.1 | pkgs.railway | 4.36.1 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| roborev | 0.55.0 | [brew: kenn-io/tap/roborev](https://github.com/kenn-io/homebrew-tap) | 0.69.0 | yes / yes | Tap supplies both Mac architectures. Initialize hooks only in repositories where wanted. |
| Ruby / Bundler | macOS Ruby 2.6.10 / Bundler 1.17.2 | pkgs.ruby | 3.4.9 | yes / yes | Use Nix Ruby for user gems, leaving Apple system Ruby untouched. Project Gemfiles pin their own dependencies. |
| Rust toolchain | 1.98.0 | [Manual](https://rustup.rs/) | see notes | vendor / vendor | Use scripts/setup-development.sh rust; cross targets do not provide foreign OS linkers. |
| Rustup | 1.29.0 | pkgs.rustup | 1.29.0 | yes / yes | Nix owns rustup; initialize Rust 1.98.0, components and targets separately. |
| ShellCheck | 0.11.0 | pkgs.shellcheck | 0.11.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Tauri CLI | 2.10.0 | pkgs.cargo-tauri | 2.11.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| Trunk | 0.21.14 | pkgs.trunk | 0.21.14 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| unirepo-cli | 0.6.0 | [Manual](https://www.npmjs.com/package/unirepo-cli) | see notes | vendor / vendor | npm install --global --prefix "$HOME/.local" unirepo-cli@0.6.0 |
| uv | 0.12.17 | pkgs.uv | 0.11.21 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| wasm-bindgen CLI | 0.2.123 | pkgs.wasm-bindgen-cli | 0.2.121 | yes / yes | 0.2.123 is not packaged at the audited revision; the default is 0.2.121. Match each project Cargo.lock when building WebAssembly. |
| wasm-pack | 0.15.0 | pkgs.wasm-pack | 0.15.0 | yes / yes | Use the version pinned by 26.05; executable paths change to Nix profiles. |
| WireGuard helpers | GLKVM bundled | Manual | see notes | vendor / vendor | Installed by GLKVM; no separate competing Nix daemon. |

### Fonts

| Item | Installed | Install source | Available version | ARM / Intel | Difference / remaining setup |
|---|---|---|---|---|---|
| MesloLGS NF | four installed styles | pkgs.meslo-lgs-nf | unstable-2023-04-03 | yes / yes | Powerlevel10k font; includes regular, bold and italic variants. |
| Open Sans | variable width/weight fonts | pkgs.open-sans | 1.11 | yes / yes | 26.05 ships version 1.11; not the same variable font files. Preserve original files privately if exact typography matters. |
| RØDE fonts and Arial Unicode | installed vendor fonts | Manual | see notes | vendor / vendor | Restore from licensed vendor/Office installers; do not redistribute font binaries. |

### Device components

| Item | Installed | Install source | Available version | ARM / Intel | Difference / remaining setup |
|---|---|---|---|---|---|
| MSTeamsAudioDevice | installed audio driver | Manual | see notes | vendor / vendor | Restore through the owning vendor application/driver installer and approve requested macOS permissions. |
| OculusRemoteDesktopASP | installed audio driver | Manual | see notes | vendor / vendor | Restore through the owning vendor application/driver installer and approve requested macOS permissions. |
| ParrotAudioPlugin | installed audio driver | Manual | see notes | vendor / vendor | Restore through the owning vendor application/driver installer and approve requested macOS permissions. |
| RodeUnify | installed audio driver | Manual | see notes | vendor / vendor | Restore through the owning vendor application/driver installer and approve requested macOS permissions. |
| VirtualDesktopMicrophone | installed audio driver | Manual | see notes | vendor / vendor | Restore through the owning vendor application/driver installer and approve requested macOS permissions. |
| VirtualDesktopSpeakers | installed audio driver | Manual | see notes | vendor / vendor | Restore through the owning vendor application/driver installer and approve requested macOS permissions. |
| ZoomAudioDevice | installed audio driver | Manual | see notes | vendor / vendor | Restore through the owning vendor application/driver installer and approve requested macOS permissions. |

### Homebrew dependency libraries

These are resolved by their parent packages. Nix closures need not contain the same library versions or expose Homebrew's incidental executables globally.

| Library | Observed version |
|---|---|
| ada-url | 4.0.0 |
| bdw-gc | 8.2.12 |
| brotli | 1.2.0 |
| c-ares | 1.34.8 |
| ca-certificates | 2026-08-13 |
| cairo | 1.18.4 |
| dav1d | 1.5.4 |
| fmt | 12.2.0 |
| fontconfig | 2.18.3 |
| freetype | 2.14.3 |
| gettext | 1.0 |
| giflib | 6.1.3 |
| glib | 2.88.3 |
| gmp | 6.3.0 |
| gradle-completion | 9.6.1 |
| graphite2 | 1.3.15 |
| harfbuzz | 14.3.0 |
| hdrhistogram_c | 0.11.10 |
| icu4c@78 | 78.3 |
| jpeg-turbo | 3.2.0 |
| json-c | 0.19 |
| lame | 4.0 |
| libffi | 3.7.1 |
| libnghttp2 | 1.70.0 |
| libnghttp3 | 1.18.0 |
| libngtcp2 | 1.25.0 |
| libpaper | 2.2.8 |
| libpng | 1.6.58 |
| libtiff | 4.7.2 |
| libunistring | 1.4.2 |
| libuv | 1.52.1 |
| libvmaf | 3.2.0 |
| libvpx | 1.16.0 |
| libx11 | 1.8.13 |
| libxau | 1.0.12 |
| libxcb | 1.17.0 |
| libxdmcp | 1.1.5 |
| libxext | 1.3.7 |
| libxrender | 0.9.12 |
| little-cms2 | 2.19 |
| llhttp | 9.4.3 |
| lz4 | 1.10.0 |
| lzo | 2.10 |
| merve | 1.2.2_1 |
| mpg123 | 1.33.7 |
| nbytes | 0.1.4 |
| openjdk | 26.0.2 |
| openssl@3 | 3.6.3 |
| openssl@4 | 4.0.2 |
| opus | 1.6.1 |
| pcre2 | 10.47_1 |
| pixman | 0.46.4 |
| readline | 8.3.3 |
| sdl2-compat | 2.32.70 |
| sdl3 | 3.4.14 |
| simdjson | 4.6.6 |
| simdutf | 9.0.0 |
| sqlite | 3.53.4 |
| svt-av1 | 4.2.0 |
| uvwasi | 0.0.23 |
| webp | 1.6.0 |
| x264 | r3222 |
| x265 | 4.2 |
| xorgproto | 2025.1 |
| xz | 5.8.3 |
| zstd | 1.5.7_1 |

### Editor extensions

Availability below means an exact attribute was found in the 26.05 extension set; platform compatibility is not a build claim. Extensions are installed in writable editor profiles through their marketplaces.

| Extension | Editor | Installed version | In nixpkgs.vscode-extensions |
|---|---|---|---|
| `1yib.rust-bundle` | Code | 1.0.0 | no exact attribute found |
| `awei-sumaho.apple-container-manager` | Code | 0.9.5 | no exact attribute found |
| `bbenoist.nix` | Code | 1.0.1 | yes |
| `charliermarsh.ruff` | Code | 2026.84.0 | yes |
| `dustypomerleau.rust-syntax` | Code | 0.6.1 | no exact attribute found |
| `juggernautjp.less-toml` | Code | 0.6.0 | no exact attribute found |
| `leighlondon.eml` | Code | 0.4.0 | no exact attribute found |
| `leonhard-s.python-sphinx-highlight` | Code | 0.3.0 | no exact attribute found |
| `mikestead.dotenv` | Code | 1.0.1 | yes |
| `ms-azuretools.vscode-containers` | Code | 2.5.2 | yes |
| `ms-azuretools.vscode-docker` | Code | 2.0.0 | yes |
| `ms-python.debugpy` | Code | 2026.6.0 | yes |
| `ms-python.python` | Code | 2026.4.0 | yes |
| `ms-python.vscode-pylance` | Code | 2025.9.1 | yes |
| `ms-python.vscode-python-envs` | Code | 1.38.0 | yes |
| `ms-vscode-remote.remote-containers` | Code | 0.469.0 | yes |
| `ms-vscode-remote.remote-ssh` | Code | 0.128.0 | yes |
| `ms-vscode-remote.remote-ssh-edit` | Code | 0.87.0 | yes |
| `ms-vscode-remote.remote-wsl` | Code | 0.104.3 | yes |
| `ms-vscode-remote.vscode-remote-extensionpack` | Code | 0.26.0 | yes |
| `ms-vscode.cpptools` | Code | 1.34.4 | yes |
| `ms-vscode.makefile-tools` | Code | 0.12.17 | yes |
| `ms-vscode.remote-explorer` | Code | 0.5.0 | yes |
| `ms-vscode.remote-server` | Code | 1.5.3 | no exact attribute found |
| `redhat.java` | Code | 1.56.0 | yes |
| `rodolphebarbanneau.python-docstring-highlighter` | Code | 0.2.4 | no exact attribute found |
| `rust-lang.rust-analyzer` | Code | 0.3.3065 | yes |
| `tamasfe.even-better-toml` | Code | 0.21.2 | yes |
| `vscjava.vscode-gradle` | Code | 3.18.0 | yes |
| `vscjava.vscode-java-debug` | Code | 0.59.0 | yes |
| `vscjava.vscode-java-dependency` | Code | 0.27.6 | yes |
| `vscjava.vscode-java-pack` | Code | 0.31.1 | yes |
| `vscjava.vscode-java-test` | Code | 0.46.0 | yes |
| `vscjava.vscode-maven` | Code | 0.45.3 | yes |
| `webnative.webnative` | Code | 2.2.16 | no exact attribute found |
| `yzhang.markdown-all-in-one` | Code | 3.6.3 | yes |
| `zainchen.json` | Code | 2.0.2 | yes |
| `anysphere.cursorpyright` | Cursor | 1.0.12 | no exact attribute found |
| `anysphere.remote-containers` | Cursor | 1.0.37 | no exact attribute found |
| `charliermarsh.ruff` | Cursor | 2026.56.0 | yes |
| `docker.docker` | Cursor | 0.18.0 | yes |
| `eamodio.gitlens` | Cursor | 18.2.0 | yes |
| `github.vscode-github-actions` | Cursor | 0.32.1 | yes |
| `juggernautjp.less-toml` | Cursor | 0.6.0 | no exact attribute found |
| `leighlondon.eml` | Cursor | 0.4.0 | no exact attribute found |
| `leonhard-s.python-sphinx-highlight` | Cursor | 0.3.0 | no exact attribute found |
| `ms-azuretools.vscode-containers` | Cursor | 2.4.5 | yes |
| `ms-azuretools.vscode-docker` | Cursor | 2.0.0 | yes |
| `ms-python.debugpy` | Cursor | 2026.6.0 | yes |
| `ms-python.python` | Cursor | 2025.6.1 | yes |
| `ms-toolsai.jupyter-keymap` | Cursor | 1.1.2 | yes |
| `ms-vscode-remote.remote-ssh` | Cursor | 0.113.1 | yes |
| `ms-vscode-remote.remote-ssh-edit` | Cursor | 0.87.0 | yes |
| `ms-vscode-remote.remote-wsl` | Cursor | 0.81.8 | yes |
| `ms-vscode-remote.vscode-remote-extensionpack` | Cursor | 0.26.0 | yes |
| `ms-vscode.cpptools` | Cursor | 1.23.6 | yes |
| `ms-vscode.makefile-tools` | Cursor | 0.12.17 | yes |
| `ms-vscode.remote-explorer` | Cursor | 0.5.0 | yes |
| `ms-vscode.remote-server` | Cursor | 1.5.2 | no exact attribute found |
| `redhat.java` | Cursor | 1.55.0 | yes |
| `rodolphebarbanneau.python-docstring-highlighter` | Cursor | 0.2.4 | no exact attribute found |
| `rust-lang.rust-analyzer` | Cursor | 0.3.2955 | yes |
| `tamasfe.even-better-toml` | Cursor | 0.21.2 | yes |
| `tauri-apps.tauri-vscode` | Cursor | 0.2.10 | yes |
| `visualstudioexptteam.intellicode-api-usage-examples` | Cursor | 0.2.9 | yes |
| `visualstudioexptteam.vscodeintellicode` | Cursor | 1.3.2 | yes |
| `vscjava.vscode-gradle` | Cursor | 3.17.3 | yes |
| `vscjava.vscode-java-debug` | Cursor | 0.59.0 | yes |
| `vscjava.vscode-java-dependency` | Cursor | 0.27.6 | yes |
| `vscjava.vscode-java-pack` | Cursor | 0.31.1 | yes |
| `vscjava.vscode-java-test` | Cursor | 0.45.0 | yes |
| `vscjava.vscode-maven` | Cursor | 0.45.3 | yes |
| `webnative.webnative` | Cursor | 2.2.13 | no exact attribute found |
| `yzhang.markdown-all-in-one` | Cursor | 3.6.3 | yes |
| `zainchen.json` | Cursor | 2.0.2 | yes |

### Browser extensions

Restore through browser sync or each browser's extension store. The manifest preserves IDs for lookup; profiles, cookies and credentials are not included.

| Browser | Extension | Version |
|---|---|---|
| Brave | 1Password – Password Manager (`aeblfdkhhhdcdjpifhhbdiojplfjncoa`) | 8.12.36.40 |
| Brave | Proton VPN: Fast & Secure (`jplgfhpmjnbigmhklmmbgecoobifkmpa`) | 1.3.6 |
| Brave | Tampermonkey (`dhdgffkkebhmkfjojejmpbldmpobfkfo`) | 5.5.0 |
| Brave | VPN for Chrome: NordVPN proxy protection (`fjoaledfpmneenckfbpdfhkmimnjocfa`) | 6.0.1 |
| Brave | Video Download Helper (`lmjnegcaeklhafolokijcfjliaokphfk`) | 10.5.49.2 |
| Chrome | 1Password – Password Manager (`aeblfdkhhhdcdjpifhhbdiojplfjncoa`) | 8.12.37.1 |
| Chrome | AI Exporter - Save ChatGPT, Claude and Gemini chats to PDF, MD and more (`kagjkiiecagemklhmhkabbalfpbianbe`) | 4.5.0 |
| Chrome | ColorZilla (`bhlhnicpbhignbdhedgjhgdocnmhomnp`) | 4.1 |
| Chrome | Google Docs Offline (`ghbmnnjooekpmoecnnnilnnbdlolhkhi`) | 1.110.1 |
| Chrome | Google Translate (`aapbdbdomjkkjkaonfhkkikfgjllcleb`) | 2.0.17 |
| Chrome | Privacy Badger (`pkehgijcmpdhfbdbbnkijodmdjhbjlgp`) | 2026.9.15 |
| Chrome | Proton Pass: Free Password Manager (`ghmbeldphafepmbegfdlkpapadhbakde`) | 1.40.2 |
| Chrome | Proton VPN: Fast & Secure (`jplgfhpmjnbigmhklmmbgecoobifkmpa`) | 1.3.6 |
| Chrome | Screen Recorder & Screenshot App for Chrome \| Scrnli (`ijejnggjjphlenbhmjhhgcdpehhacaal`) | 4.3.9 |
| Chrome | Tab Suspender (`laameccjpleogmfhilmffpdbiibgbekf`) | 1.0.4 |
| Chrome | Tab Suspender (`fiabciakcmgepblmdkmemdbbkilneeeh`) | 2.0.12 |
| Chrome | Video Download Helper (`lmjnegcaeklhafolokijcfjliaokphfk`) | 10.5.49.2 |
| Chrome | uBlock Origin Lite (`ddkjiahejlhfcafbddmgiahcphecmpfh`) | 2026.926.2202 |
| Firefox | 1Password – Password Manager (`{d634138d-c276-4fc8-924b-40a0ea21d284}`) | 8.12.32.33 |
| Firefox | Capital One Shopping: Save Now (`{aff8af88-06a9-4eee-b383-3af08c47b8c8}`) | 0.1.1219 |
| Firefox | Credit Card Nicknames for Amazon (`ccna@philippesabourin.com`) | 1.0.14 |
| Firefox | Disable JavaScript (`{41f9e51d-35e4-4b29-af66-422ff81c8b41}`) | 2.3.2resigned1 |
| Firefox | Distract Me Not (`{5f884915-160e-4276-a216-770a753a3abe}`) | 2.8.3 |
| Firefox | Eno® from Capital One® (`{4d5b7a5e-5232-9e45-97f4-f8e1ca2626e5}`) | 6.0.0 |
| Firefox | Export Cookies (`{36bdf805-c6f2-4f41-94d2-9b646342c1dc}`) | 0.3.2 |
| Firefox | GNOME Shell integration (`chrome-gnome-shell@gnome.org`) | 12.1 |
| Firefox | GitHub Code Folding (`{b588f8ac-dbdf-4397-bcd7-3d29be2f17d7}`) | 0.1.2resigned1 |
| Firefox | Github Repo Size (`github-repo-size@mattelrah.com`) | 1.7.0 |
| Firefox | Githunt (`{e65b64ad-4343-44eb-8163-1f83ad706344}`) | 1.6.2 |
| Firefox | Google Translator for Firefox (`translator@zoli.bod`) | 3.0.3.4resigned1 |
| Firefox | New Tab (`newtab@mozilla.org`) | 154.4.20260708.42619 |
| Firefox | NordVPN - a VPN proxy extension for Firefox (`nordvpnproxy@nordvpn.com`) | 5.2.2 |
| Firefox | Popup window (`PopupWindow@ettoolong`) | 0.1.3 |
| Firefox | Privacy Badger (`jid1-MnnxcxisBPnSXQ@jetpack`) | 2026.9.15 |
| Firefox | Resize Window & Viewport (`morisdov@windowviewportresizer`) | 1.0.7resigned1 |
| Firefox | Session Manager (`{8196dd58-b7e8-4705-8ef5-de28ecf312bb}`) | 1.0.2 |
| Firefox | Tab Session Manager (`Tab-Session-Manager@sienori`) | 7.4.0 |
| Firefox | Table of Contents for GitHub (`@github-readme-toc`) | 0.2.6resigned1 |
| Firefox | To Google Translate (`jid1-93WyvpgvxzGATw@jetpack`) | 4.3.1 |
| Firefox | User-Agent Switcher and Manager (`{a6c4a591-f1b2-4f03-b3ff-767e5bedf4e7}`) | 0.7.1 |
| Firefox | Video DownloadHelper (`{b9db16a4-6edc-47ec-a1f4-b86292ed211d}`) | 9.5.0.2 |
| Firefox | Want My RSS (`{4d567245-e70d-466a-bb2f-390fc7fb25c2}`) | 0.38 |
| Firefox | Web App Mode (`WebAppMode@ettoolong`) | 0.0.9 |
| Firefox | Web Developer (`{c45c406e-ab73-11d8-be73-000a95be3b12}`) | 3.0.1 |
| Firefox | uBlock Origin (`uBlock0@raymondhill.net`) | 1.73.0 |

### Ruby gems

Non-default installed gems, newest version per name. Restore executable tools as user gems under Nix Ruby; dependencies should normally come from a project's Gemfile rather than a global copy of this list.

| Gem | Version | Executables |
|---|---|---|
| CFPropertyList | 2.3.6 | dependency |
| addressable | 2.8.8 | dependency |
| atomos | 0.1.3 | dependency |
| base64 | 0.3.0 | dependency |
| bigdecimal | 4.0.1 | dependency |
| claide | 1.1.0 | dependency |
| cocoapods-deintegrate | 1.0.5 | dependency |
| cocoapods-downloader | 2.1 | dependency |
| cocoapods-plugins | 1.0.0 | dependency |
| cocoapods-search | 1.0.1 | dependency |
| cocoapods-trunk | 1.6.0 | dependency |
| cocoapods-try | 1.2.0 | dependency |
| colored2 | 3.1.2 | dependency |
| csv | 3.3.5 | dependency |
| date | 3.5.1 | dependency |
| dbm | 1.1.0 | dependency |
| did_you_mean | 2.0.0 | dependency |
| escape | 0.0.4 | dependency |
| etc | 1.4.6 | dependency |
| fcntl | 1.3.0 | dependency |
| fileutils | 1.8.0 | dependency |
| forwardable | 1.4.0 | dependency |
| fourflusher | 2.3.1 | dependency |
| gh_inspector | 1.1.3 | dependency |
| io-console | 0.8.2 | dependency |
| ipaddr | 1.2.8 | dependency |
| libxml-ruby | 5.0.5 | dependency |
| logger | 1.7.0 | dependency |
| matrix | 0.4.3 | dependency |
| mini_portile2 | 2.8.9 | dependency |
| minitest | 5.11.3 | dependency |
| molinillo | 0.8.0 | dependency |
| mutex_m | 0.3.0 | dependency |
| nanaimo | 0.4.0 | dependency |
| nap | 1.1.0 | dependency |
| net-telnet | 0.2.0 | dependency |
| netrc | 0.11.0 | dependency |
| nkf | 0.2.0 | dependency |
| nokogiri | 1.13.8 | nokogiri |
| ostruct | 0.6.3 | dependency |
| power_assert | 3.0.1 | dependency |
| prettyprint | 0.2.0 | dependency |
| prime | 0.1.4 | dependency |
| public_suffix | 4.0.7 | dependency |
| racc | 1.8.1 | racc |
| rake | 13.3.1 | rake |
| rexml | 3.4.4 | dependency |
| rss | 0.3.2 | dependency |
| ruby-macho | 2.5.1 | dependency |
| shell | 0.8.1 | dependency |
| singleton | 0.3.0 | dependency |
| sqlite3 | 1.3.13 | dependency |
| strscan | 3.1.7 | dependency |
| test-unit | 3.7.7 | test-unit |
| thwait | 0.2.0 | dependency |
| tsort | 0.2.0 | dependency |
| webrick | 1.9.2 | dependency |
| xcodeproj | 1.27.0 | xcodeproj |
| xmlrpc | 0.3.3 | dependency |
| zlib | 3.2.2 | dependency |

<!-- inventory:end -->

## Upstream references

- [nix-darwin setup](https://github.com/nix-darwin/nix-darwin#readme)
- [Home Manager with nix-darwin](https://nix-community.github.io/home-manager/installation/nix-darwin.html)
- [26.05 package source](https://github.com/NixOS/nixpkgs/tree/nixpkgs-26.05-darwin)
- [Homebrew integration options](https://github.com/nix-darwin/nix-darwin/blob/nix-darwin-26.05/modules/homebrew.nix)
- [Wine cask status](https://github.com/Homebrew/homebrew-cask/blob/master/Casks/w/wine-stable.rb)
- [GStreamer cask status](https://github.com/Homebrew/homebrew-cask/blob/master/Casks/g/gstreamer-runtime.rb)
