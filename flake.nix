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
          mkApp = pkgs.callPackage ./pkgs/mk-macos-app.nix { };
          fixture = {
            pname = "app-discovery-fixture";
            src = pkgs.writeText "unused-fixture-source" "";
          };
          autoApp = mkApp fixture;
          namedApp = mkApp (
            fixture
            // {
              appName = "Renamed.app";
            }
          );
          pkgApp = mkApp (
            fixture
            // {
              format = "dmg-pkg";
              appName = "Fixture.app";
            }
          );
        in
        pkgs.runCommand "mac-config-settings-tests"
          {
            nativeBuildInputs = [
              python
              pkgs._7zz
              pkgs.undmg
            ];
            # Exercise generated build commands with local archives, never vendors.
            APP_BUILD_PHASES = pkgs.writeText "app-build-phases.json" (
              builtins.toJSON {
                autoInstall = autoApp.installPhase;
                autoUnpack = autoApp.unpackPhase;
                namedInstall = namedApp.installPhase;
                namedUnpack = namedApp.unpackPhase;
                pkgUnpack = pkgApp.unpackPhase;
                pkgInstall = pkgApp.installPhase;
              }
            );
            ZSH_ENV_FILE = "${home.home-files}/.zshenv";
            ZSH_RC_FILE = "${home.home-files}/.config/zsh/nix-zshrc";
            ZSH_HOME_DIRECTORY = home.home.homeDirectory;
            ZSH_TEST_BIN = "${pkgs.zsh}/bin/zsh";
            PRE_ACTIVATION_FILE = pkgs.writeText "mac-config-pre-activation.sh" self.darwinConfigurations.mac.config.system.activationScripts.preActivation.text;
            DEBLOAT_ACTIVATION_FILE = pkgs.writeText "mac-config-debloat.sh" self.darwinConfigurations.mac.config.system.activationScripts.debloat.text;
            DEBLOAT_USERNAME = host.username;
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
