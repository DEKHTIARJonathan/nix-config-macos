{
  config,
  lib,
  pkgs,
  host,
  ...
}:
let
  python = pkgs.python3.withPackages (ps: [ ps.json5 ]);
  restore = pkgs.writeShellScriptBin "mac-config-restore" ''
    exec ${python}/bin/python3 ${./scripts}/restore_settings.py \
      --source ${./settings} --home ${lib.escapeShellArg config.home.homeDirectory} "$@"
  '';
  editors = pkgs.writeShellScriptBin "mac-config-setup-editors" ''
    exec ${python}/bin/python3 ${./scripts}/setup_editors.py \
      --source ${./settings} --home ${lib.escapeShellArg config.home.homeDirectory} "$@"
  '';
  verifyTools = pkgs.writeShellScriptBin "mac-config-verify-development-tools" ''
    exec ${python}/bin/python3 ${./scripts}/verify_development_tools.py "$@"
  '';
in
{
  home = {
    username = host.username;
    homeDirectory = host.homeDirectory or "/Users/${host.username}";
    stateVersion = "26.05";
    sessionVariables.CLAUDE_CODE_PACKAGE_MANAGER_AUTO_UPDATE = "1";
    packages = [
      restore
      editors
      verifyTools
    ];
    file.".p10k.zsh".source = ./settings/p10k.zsh;
    # Keep the entry point writable for application setup (for example Docker).
    # Home Manager still updates the generated shell configuration separately.
    file."./.zshrc".target = ".config/zsh/nix-zshrc";
    activation.writableZshrc = lib.hm.dag.entryBetween [ "linkGeneration" ] [ "writeBoundary" ] ''
      run ${restore}/bin/mac-config-restore zshrc
    '';
    activation.restoreSettings = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      run ${restore}/bin/mac-config-restore all --once
    '';
  };

  programs.git = {
    enable = true;
    settings = builtins.fromJSON (builtins.readFile ./settings/git.json);
  };

  # Home Manager now defaults to XDG Git configuration. Adopt the existing
  # ~/.gitconfig itself so it cannot override the captured settings afterward.
  xdg.configFile."git/config".target = "${config.home.homeDirectory}/.gitconfig";

  programs.zsh = {
    enable = true;
    dotDir = config.home.homeDirectory;
    oh-my-zsh = {
      enable = true;
      plugins = [ "git" ];
    };
    # Preserve the live Oh My Zsh history behavior rather than HM's defaults.
    history = {
      size = 50000;
      save = 10000;
      append = true;
      extended = true;
      expireDuplicatesFirst = true;
    };
    plugins = [
      {
        name = "powerlevel10k";
        src = pkgs.zsh-powerlevel10k;
        file = "share/zsh-powerlevel10k/powerlevel10k.zsh-theme";
      }
    ];
    shellAliases = {
      code = "'/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code'";
      vscode = "'/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code'";
      zed = "'/Applications/Zed.app/Contents/MacOS/cli'";
    };
    # Keep inherited project tools ahead of Cargo and fallback Nix paths.
    # nix-darwin establishes the default tool order for login shells.
    envExtra = ''
      () {
        local -a inherited_path=("''${path[@]}")
        [[ ! -f "$HOME/.cargo/env" ]] || source "$HOME/.cargo/env"
        path=("''${inherited_path[@]}" "''${path[@]}" /run/current-system/sw/bin /etc/profiles/per-user/${lib.escapeShellArg host.username}/bin)
        # cargo install puts user tools here even without a Rustup env file.
        path+=("$HOME/.cargo/bin")
        # Docker Desktop owns these CLI and credential-helper symlinks.
        # Keep them available to scripts as well as interactive shells.
        path+=("$HOME/.docker/bin")
        typeset -gU path
      }
      # Register Docker's completions before Oh My Zsh initializes completion.
      # Make the directory visible to noninteractive completion checks too.
      fpath+=("$HOME/.docker/completions")
      typeset -U fpath
      export FPATH
    '';
    profileExtra = ''
      # Retain the locally installed Python framework when it exists.
      if [[ -d /Library/Frameworks/Python.framework/Versions/3.12/bin ]]; then
        path+=(/Library/Frameworks/Python.framework/Versions/3.12/bin)
      fi
    '';
    initContent = lib.mkMerge [
      (lib.mkOrder 500 ''
        if [[ -r "''${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-''${(%):-%n}.zsh" ]]; then
          source "''${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-''${(%):-%n}.zsh"
        fi
      '')
      (lib.mkOrder 1500 ''
        [[ ! -f "$HOME/.p10k.zsh" ]] || source "$HOME/.p10k.zsh"
        # Add local tools without overriding an inherited development environment.
        path+=("$HOME/.local/bin")
        typeset -U path
        [[ ! -f "$HOME/.zshrc.local" ]] || source "$HOME/.zshrc.local"
      '')
    ];
  };
}
