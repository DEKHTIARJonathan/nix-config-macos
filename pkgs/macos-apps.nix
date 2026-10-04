{ pkgs }:
let
  inherit (pkgs) lib;
  inventory = import ../dmg-apps.nix { inherit lib; };
  sources = import ./app-sources.nix { inherit pkgs; };
  mkApp = pkgs.callPackage ./mk-macos-app.nix { };
  supported = lib.filterAttrs (
    _: app:
    (app.enable or true)
    && builtins.elem pkgs.stdenv.hostPlatform.system (app.platforms or lib.platforms.darwin)
  ) inventory;
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
      "downloadName"
      "preserveXattrs"
    ]
  )
) supported
