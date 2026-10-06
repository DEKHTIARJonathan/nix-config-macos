{
  description = "Apple Silicon macOS utilities and applications, managed with nix-darwin";

  inputs = {
    # Matching stable release branches keep nixpkgs and nix-darwin compatible.
    # The Darwin branch includes macOS build fixes.
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-26.05-darwin";

    nix-darwin = {
      url = "github:nix-darwin/nix-darwin/nix-darwin-26.05";
      # Use one shared nixpkgs revision rather than two independent copies.
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Manages the Homebrew installation itself. The homebrew options in
    # configuration.nix manage its formulae and casks separately.
    nix-homebrew.url = "github:zhaofengli/nix-homebrew";

    home-manager = {
      url = "github:nix-community/home-manager/release-26.05";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  # `nix flake lock` creates flake.lock with the exact input revisions.
  # Keep that generated file alongside these files, preferably in Git.
  # Ordinary rebuilds reuse the lock; `nix flake update` changes it.
  outputs =
    {
      self,
      nix-darwin,
      nix-homebrew,
      home-manager,
      ...
    }:
    let
      host = import ./host.nix;
      appPackages = import ./pkgs/macos-apps.nix { pkgs = self.darwinConfigurations.mac.pkgs; };
    in
    {
      # "mac" is a configuration name, not your computer's hostname.
      # All commands use `--flake .#mac`; no hostname change is required.
      darwinConfigurations.mac = nix-darwin.lib.darwinSystem {
        # Pass our machine settings to every imported module.
        specialArgs = { inherit host; };

        modules = [
          nix-homebrew.darwinModules.nix-homebrew
          home-manager.darwinModules.home-manager
          {
            home-manager = {
              useGlobalPkgs = true;
              useUserPackages = true;
              backupFileExtension = "before-nix";
              extraSpecialArgs = { inherit host; };
              users.${host.username} = import ./home.nix;
            };
          }
          ./configuration.nix
          ./android.nix
          ./app-installation.nix
          ./desktop.nix
        ];
      };

      # Build one app with `nix build .#signal`; `.src` builds just its download.
      packages.${host.system} = appPackages // {
        # Available on the first build, without installing the system first.
        inherit (self.darwinConfigurations.mac.pkgs) nix-output-monitor;
      };

      checks.${host.system}.settings =
        let
          pkgs = self.darwinConfigurations.mac.pkgs;
          python = pkgs.python3.withPackages (ps: [ ps.json5 ]);
          home = self.darwinConfigurations.mac.config.home-manager.users.${host.username};
        in
        pkgs.runCommand "mac-config-settings-tests"
          {
            nativeBuildInputs = [ python ];
            ZSH_ENV_FILE = "${home.home-files}/.zshenv";
            ZSH_RC_FILE = "${home.home-files}/.zshrc";
            ZSH_HOME_DIRECTORY = home.home.homeDirectory;
            ZSH_TEST_BIN = "${pkgs.zsh}/bin/zsh";
          }
          ''
            cp -R ${./scripts} scripts
            cp -R ${./settings} settings
            cp -R ${./tests} tests
            python3 -B -m unittest discover -s tests -v
            touch "$out"
          '';
    };
}
