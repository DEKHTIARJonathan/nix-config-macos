{
  config,
  host,
  lib,
  pkgs,
  ...
}:
{
  # This managed laptop protects /etc/pam.d. Keep macOS authentication intact.
  security.pam.services.sudo_local.enable = false;

  assertions = [
    {
      assertion = host.username != "CHANGE_ME" && host.username != "";
      message = "Set username in host.nix to your existing macOS account name (id -un).";
    }
    {
      assertion = host.system == "aarch64-darwin";
      message = "This configuration supports Apple Silicon only; set system in host.nix to aarch64-darwin.";
    }
  ];

  nixpkgs.hostPlatform = host.system;
  system.primaryUser = host.username;
  system.stateVersion = host.stateVersion;

  # Intel-only vendor installers need Rosetta even when their payload is ARM64.
  # Probe actual execution support so later switches skip a working installation.
  system.activationScripts.preActivation.text = ''
    if ! /usr/bin/arch -x86_64 /usr/bin/true >/dev/null 2>&1; then
      echo "Installing Rosetta for Intel application compatibility..."
      if ! /usr/sbin/softwareupdate --install-rosetta --agree-to-license; then
        echo "Rosetta installation failed; retry activation after resolving the error." >&2
        exit 1
      fi
      if ! /usr/bin/arch -x86_64 /usr/bin/true >/dev/null 2>&1; then
        echo "Rosetta installation finished, but Intel execution still fails." >&2
        exit 1
      fi
    fi
  '';

  # Describe the EXISTING account for modules that need its home directory.
  # This is not a request to create a new macOS account.
  users.users.${host.username}.home = host.homeDirectory or "/Users/${host.username}";

  # Set false in host.nix for an externally managed Nix distribution.
  nix.enable = host.manageNix;
  nix.settings = lib.mkIf host.manageNix {
    # Required by the `nix` commands and flake-based configuration here.
    experimental-features = [
      "nix-command"
      "flakes"
    ];
  };

  # macOS's default shell. System initialization loads the persistent Nix
  # paths automatically; no `nix develop` or per-terminal activation needed.
  # Home Manager manages personal Zsh and Git configuration in home.nix.
  programs.zsh.enable = true;
  programs.zsh.interactiveShellInit = ''
    fpath=(${config.nix-homebrew.package}/completions/zsh $fpath /opt/homebrew/share/zsh/site-functions)
  '';
  # Keep Brew-only tools available without prepending old Brew CLI copies.
  environment.systemPath = lib.mkAfter [
    "/opt/homebrew/bin"
    "/opt/homebrew/sbin"
  ];

  # These packages are installed persistently for the machine's users.
  # Names below are nixpkgs attributes, which can differ from Brew names.
  # Package versions come from flake.lock's nixpkgs revision. To change a
  # version, select a versioned attribute or update that input deliberately.
  # Use macOS's native core utilities (cp, ls, mv, date, etc.). Installing
  # GNU coreutils here shadows them and can break macOS-specific build scripts.
  environment.systemPackages = with pkgs; [
    # Incredibly fast JavaScript runtime, bundler, test runner, and package manager
    # Installed by Nix: update through this configuration, not `bun upgrade`.
    bun

    # Cross-platform make
    cmake

    # Play, record, convert, and stream select audio and video codecs
    ffmpeg

    # GitHub command-line tool
    # Your existing login stays user-managed; `gh auth login` if needed.
    gh

    # Distributed revision control system
    # Home Manager restores the captured global Git settings.
    git

    # Git extension for versioning large files
    # Run `git lfs install --local` in repositories that need LFS filters.
    git-lfs

    # GNU Make for the repository's build, install, and test targets.
    gnumake

    # Open-source build automation tool based on the Groovy and Kotlin DSL
    # Existing projects should normally use their own ./gradlew wrapper.
    gradle

    # Improved top (interactive process viewer)
    htop

    # Update of iperf: measures TCP, UDP, and SCTP bandwidth
    iperf3

    # Lightweight and flexible command-line JSON processor
    jq

    # x86 assembler required by FFmpeg builds targeting x86
    nasm

    # Ambitious Vim-fork focused on extensibility and agility
    # Existing ~/.config/nvim files remain user-managed.
    neovim

    # Small build system for use with gyp or CMake
    ninja

    # Nix formatter used by the system-language prek hook.
    nixfmt

    # Open-source, cross-platform JavaScript runtime environment
    # Includes npm. A versioned attribute (e.g. nodejs_24) can pin a major.
    # Global npm installs are separate from this Nix package list. Prefer
    # project dependencies; Nix's Node installation directory is read-only.
    nodejs

    # Discover library compiler and linker flags for builds such as FFmpeg
    pkg-config

    # Fast Git hook manager written in Rust, drop-in alternative to pre-commit
    prek

    # Python interpreter for shells and development tools
    python3

    # Search tool like grep and The Silver Searcher
    ripgrep

    # Rust toolchain installer
    # Preserves your choice of Rustup. Nix manages this installer and its
    # command proxies; Rustup manages toolchains under ~/.rustup separately.
    # Run `rustup default stable` once if you do not already have a toolchain.
    # Use `rustup update` for those toolchains, not `rustup self update`.
    # We intentionally do not also install pkgs.rustc or pkgs.cargo, which
    # would compete with Rustup's rustc/cargo proxies on PATH.
    rustup

    # Static analysis and lint tool, for (ba)sh scripts
    shellcheck

    # CLI tool that moves files or folder to the trash
    # The SAME ali-rantakari macOS utility as the Homebrew `trash` formula.
    # Use the Darwin package, not the unrelated Linux/XDG trash-cli utility.
    darwin.trash

    # Display directories as trees (with optional color/HTML output)
    tree

    # Python dependency environments for make test, matching CI.
    uv

    # Download files over HTTP, HTTPS, and FTP.
    wget

    # Compress and decompress XZ and LZMA archives.
    xz

  ];

  fonts.packages = [ pkgs.meslo-lgs-nf ];

  # Homebrew installation management. It remains available for future
  # macOS applications that are missing or unsuitable in nixpkgs.
  nix-homebrew = {
    enableZshIntegration = false;
    enableBashIntegration = false;
    enable = true;
    user = host.username;

    # Adopt an existing Homebrew installation at its standard prefix.
    # nix-homebrew manages Homebrew's own files; it is more than a PATH edit.
    autoMigrate = true;

    # Manage only the native Apple Silicon Homebrew installation.
    enableRosetta = false;

    # Keep existing/custom taps usable during migration. Consequently their
    # contents are NOT pinned by flake.lock. For fully declarative taps,
    # add homebrew-core/homebrew-cask flake inputs with flake = false,
    # declare nix-homebrew.taps, then set mutableTaps = false.
    mutableTaps = true;
  };

  # Native apps and frequently updated CLIs maintained outside the Nix store.
  homebrew = {
    enable = true;

    brews = [
      "railway"
      "herdr"
      "mactop"
    ];
    casks = [
      "hiddenbar"
      "codex"
      "claude-code"
    ];

    onActivation = {
      # Migration mode: do not uninstall packages absent from these lists.
      # Existing Brew copies may coexist until you explicitly remove them.
      # "uninstall" later makes the lists authoritative, removing unlisted
      # Homebrew packages. Use it only after inventorying everything else.
      cleanup = "none";

      # Rebuilding the Nix configuration does not implicitly upgrade Brew.
      autoUpdate = false;
      upgrade = false;
    };
  };
}
