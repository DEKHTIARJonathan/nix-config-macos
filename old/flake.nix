{
  description = "Jonathan's Mac — nix-darwin 26.05, Intel and Apple Silicon";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-26.05-darwin";
    nix-darwin.url = "github:nix-darwin/nix-darwin/nix-darwin-26.05";
    nix-darwin.inputs.nixpkgs.follows = "nixpkgs";
    home-manager.url = "github:nix-community/home-manager/release-26.05";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    {
      nixpkgs,
      nix-darwin,
      home-manager,
      ...
    }:
    let
      # Change this one value before setting up a different local account.
      username = "jonathan";
      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
      mkMac =
        system:
        nix-darwin.lib.darwinSystem {
          specialArgs = { inherit username; };
          modules = [
            { nixpkgs.hostPlatform = system; }
            ./darwin.nix
            home-manager.darwinModules.home-manager
            {
              home-manager = {
                useGlobalPkgs = true;
                useUserPackages = true;
                backupFileExtension = "before-nix";
                extraSpecialArgs = { inherit username; };
                users.${username} = import ./home.nix;
              };
            }
          ];
        };
    in
    {
      darwinConfigurations = {
        macbook-arm = mkMac "aarch64-darwin";
        macbook-intel = mkMac "x86_64-darwin";
      };
      formatter = forAllSystems (system: nixpkgs.legacyPackages.${system}.nixfmt);
      devShells = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShellNoCC {
            packages = with pkgs; [
              nixfmt
              statix
              deadnix
              shellcheck
              python3
            ];
          };
        }
      );
      checks = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          repository =
            pkgs.runCommand "mac-config-checks"
              {
                nativeBuildInputs = with pkgs; [
                  nixfmt
                  statix
                  deadnix
                  shellcheck
                  python3
                ];
              }
              ''
                cp -R ${./.} source
                chmod -R u+w source
                cd source
                bash scripts/check.sh --offline
                touch "$out"
              '';
        }
      );
      # Useful for auditing versions without activating either configuration.
      packageAudit = forAllSystems (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true;
          };
          software = import ./software.nix {
            inherit pkgs;
            inherit (nixpkgs) lib;
          };
        in
        software.audit
      );
    };
}
