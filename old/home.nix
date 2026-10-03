{
  config,
  lib,
  pkgs,
  username,
  ...
}:
{
  home = {
    inherit username;
    homeDirectory = "/Users/${username}";
    stateVersion = "26.05";
    file.".p10k.zsh".source = ./settings/p10k.zsh;
    sessionVariables = {
      ANDROID_HOME = "${config.home.homeDirectory}/Library/Android/sdk";
      JAVA_HOME = pkgs.jdk25.home;
    };
    # GUI apps keep writable settings. Copy only files that do not exist.
    activation.seedEditors = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      run ${pkgs.python3}/bin/python3 ${./scripts/seed-settings.py} \
        --source ${./settings} --home ${lib.escapeShellArg config.home.homeDirectory} \
        --flutter ${pkgs.flutter}
    '';
  };

  programs.git = {
    enable = true;
    settings = {
      user = {
        name = "Jonathan Dekhtiar";
        email = "jonathan@dekhtiar.com";
      };
      commit.gpgSign = false;
      tag.forceSignAnnotated = false;
      advice.addIgnoredFile = false;
    };
  };
  programs.zsh = {
    enable = true;
    dotDir = config.home.homeDirectory;
    oh-my-zsh = {
      enable = true;
      plugins = [ "git" ];
    };
    plugins = [
      {
        name = "powerlevel10k";
        src = pkgs.zsh-powerlevel10k;
        file = "share/zsh-powerlevel10k/powerlevel10k.zsh-theme";
      }
    ];
    shellAliases = {
      code = "cursor";
      vscode = "'/Applications/Nix Apps/Visual Studio Code.app/Contents/Resources/app/bin/code'";
    };
    initContent = lib.mkMerge [
      (lib.mkOrder 500 ''
        if [[ -r "''${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-''${(%):-%n}.zsh" ]]; then
          source "''${XDG_CACHE_HOME:-$HOME/.cache}/p10k-instant-prompt-''${(%):-%n}.zsh"
        fi
      '')
      (lib.mkOrder 1500 ''
        [[ ! -f "$HOME/.p10k.zsh" ]] || source "$HOME/.p10k.zsh"
        # Keep Nix ahead of manually installed CLI tools. SDKs remain writable.
        path+=("$HOME/.local/bin" "$HOME/.cargo/bin" "$HOME/Library/Android/sdk/platform-tools")
        [[ ! -d "$HOME/.lmstudio/bin" ]] || path+=("$HOME/.lmstudio/bin")
        typeset -U path
        [[ ! -f "$HOME/.zshrc.local" ]] || source "$HOME/.zshrc.local"
      '')
    ];
  };
}
