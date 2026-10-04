{
  description = "macOS utilities and applications, managed with nix-darwin";

  inputs = {
    # Matching stable release branches keep nixpkgs and nix-darwin compatible.
    # The Darwin branch includes macOS build fixes. 26.05 supports both
    # Apple Silicon and Intel; do not move an Intel Mac to a branch that
    # has dropped x86_64-darwin support.
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-26.05-darwin";

    nix-darwin = {
      url = "github:nix-darwin/nix-darwin/nix-darwin-26.05";
      # Use one shared nixpkgs revision rather than two independent copies.
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Manages the Homebrew installation itself. The homebrew options in
    # configuration.nix manage its formulae and casks separately.
    nix-homebrew.url = "github:zhaofengli/nix-homebrew";
  };

  # `nix flake lock` creates flake.lock with the exact input revisions.
  # Keep that generated file alongside these files, preferably in Git.
  # Ordinary rebuilds reuse the lock; `nix flake update` changes it.
  outputs =
    {
      self,
      nix-darwin,
      nix-homebrew,
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
          ./configuration.nix
          ./android.nix
          ./macos-apps.nix
        ];
      };

      # Build one app with `nix build .#signal`; `.src` builds just its download.
      packages.${host.system} = appPackages;
    };
}
