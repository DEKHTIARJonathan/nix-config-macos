{
  host,
  lib,
  pkgs,
  ...
}:
{
  assertions = [
    {
      assertion = host.username != "CHANGE_ME" && host.username != "";
      message = "Set username in host.nix to your existing macOS account name (id -un).";
    }
    {
      assertion = builtins.elem host.system [
        "aarch64-darwin"
        "x86_64-darwin"
      ];
      message = "Set system in host.nix to aarch64-darwin or x86_64-darwin.";
    }
  ];

  nixpkgs.hostPlatform = host.system;
  system.primaryUser = host.username;
  system.stateVersion = host.stateVersion;

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
  # Personal ~/.zshrc configuration continues to load normally. A custom
  # PATH assignment there should extend $PATH rather than discard it.
  programs.zsh.enable = true;

  # These packages are installed persistently for the machine's users.
  # Names below are nixpkgs attributes, which can differ from Brew names.
  # Package versions come from flake.lock's nixpkgs revision. To change a
  # version, select a versioned attribute or update that input deliberately.
  environment.systemPackages = with pkgs; [
    # Incredibly fast JavaScript runtime, bundler, test runner, and package manager
    # Installed by Nix: update through this configuration, not `bun upgrade`.
    bun

    # Cross-platform make
    cmake

    # GNU File, Shell, and Text utilities
    # Nix exposes unprefixed names (e.g. ls, cp, date). This differs from
    # Homebrew's usual g-prefixed setup. /bin/ls still invokes Apple's ls.
    coreutils

    # Play, record, convert, and stream select audio and video codecs
    ffmpeg

    # GitHub command-line tool
    # Your existing login stays user-managed; `gh auth login` if needed.
    gh

    # Distributed revision control system
    # Installs Git without replacing your existing ~/.gitconfig.
    git

    # Git extension for versioning large files
    # Run `git lfs install` once as your user to configure Git's LFS filters.
    git-lfs

    # Open-source build automation tool based on the Groovy and Kotlin DSL
    # Existing projects should normally use their own ./gradlew wrapper.
    gradle

    # Improved top (interactive process viewer)
    htop

    # Update of iperf: measures TCP, UDP, and SCTP bandwidth
    iperf3

    # Lightweight and flexible command-line JSON processor
    jq

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

    # Fast Git hook manager written in Rust, drop-in alternative to pre-commit
    prek

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

    # Utility to hide menu bar items
    # Nix packages the upstream .app; nix-darwin exposes it in
    # /Applications/Nix Apps. Open it and enable launch at login in its UI
    # if desired. See README for removing your previous Homebrew copy.
    hidden-bar
  ];

  # Homebrew installation management. It remains available for future
  # macOS applications that are missing or unsuitable in nixpkgs.
  nix-homebrew = {
    enable = true;
    user = host.username;

    # Adopt an existing Homebrew installation at its standard prefix.
    # nix-homebrew manages Homebrew's own files; it is more than a PATH edit.
    autoMigrate = true;

    # One native Homebrew installation is enough for the supplied inventory.
    # On Apple Silicon, enable this only if you need a separate Intel brew
    # installation; install Rosetta first. Intel Macs leave this false.
    enableRosetta = false;

    # Keep existing/custom taps usable during migration. Consequently their
    # contents are NOT pinned by flake.lock. For fully declarative taps,
    # add homebrew-core/homebrew-cask flake inputs with flake = false,
    # declare nix-homebrew.taps, then set mutableTaps = false.
    mutableTaps = true;
  };

  # Package management through nix-darwin's Homebrew Bundle integration.
  # All supplied packages have native Nix equivalents, so these are empty.
  # Add future formulae/casks here instead of also installing Nix copies.
  homebrew = {
    enable = true;

    brews = [ ];
    casks = [ ];

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
