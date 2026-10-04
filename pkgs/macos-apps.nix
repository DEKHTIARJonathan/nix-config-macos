{ pkgs }:
assert pkgs.lib.assertMsg (
  pkgs.stdenv.hostPlatform.system == "aarch64-darwin"
) "macOS app packages support Apple Silicon only.";
let
  inherit (pkgs) lib;
  inventory = import ../dmg-apps.nix { inherit lib; };
  sources = import ./app-sources.nix { inherit pkgs; };
  mkApp = pkgs.callPackage ./mk-macos-app.nix { };
  enabled = lib.filterAttrs (_: app: app.enable or true) inventory;
in
lib.mapAttrs (
  name: app:
  mkApp (
    {
      pname = name;
      src = sources.${name};
    }
    // builtins.removeAttrs app [
      "url"
      "hash"
      "enable"
      "removeQuarantine"
      "removeFinderInfo"
      "downloadName"
      "preserveXattrs"
    ]
  )
) enabled
