{ pkgs }:
let
  inherit (pkgs) lib;
  inventory = import ../mac-apps.nix { inherit lib; };
  # Report curl progress as Nix build phases, understood by nix-output-monitor.
  # Keep fetchurl's normal download/retry/hash behavior and preserve errors.
  fetchurl = pkgs.fetchurl.override (original: {
    curl = pkgs.writeShellScriptBin "curl" ''
      exec ${pkgs.python3}/bin/python3 ${../scripts/curl_progress.py} ${lib.getExe original.curl} "$@"
    '';
  });
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
  fetchurl {
    inherit (app) url hash;
    name = app.downloadName or "${name}-${app.version}.${extension}";
    # The wrapper converts this meter into per-build structured status updates.
    curlOptsList = [ "--progress-bar" ];
  }
) inventory
