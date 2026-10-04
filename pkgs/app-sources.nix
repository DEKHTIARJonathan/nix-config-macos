{ pkgs }:
let
  inherit (pkgs) lib;
  inventory = import ../dmg-apps.nix { inherit lib; };
in
lib.mapAttrs (
  name: app:
  let
    format = app.format or "dmg";
    extension = if format == "zip-pkg" then "zip" else format;
  in
  pkgs.fetchurl {
    inherit (app) url hash;
    name = app.downloadName or "${name}-${app.version}.${extension}";
  }
) inventory
