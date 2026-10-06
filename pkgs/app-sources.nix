{ pkgs }:
let
  inherit (pkgs) lib;
  inventory = import ../mac-apps.nix { inherit lib; };
in
lib.mapAttrs (
  name: app:
  let
    format = app.format or "dmg";
    extension =
      if format == "zip-pkg" then
        "zip"
      else if format == "dmg-pkg" then
        "dmg"
      else
        format;
  in
  pkgs.fetchurl {
    inherit (app) url hash;
    name = app.downloadName or "${name}-${app.version}.${extension}";
  }
) inventory
