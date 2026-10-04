{
  lib,
  pkgs,
  host,
  ...
}:
let
  inventory = import ./dmg-apps.nix { inherit lib; };
  sources = import ./pkgs/app-sources.nix { inherit pkgs; };
  packages = import ./pkgs/macos-apps.nix { inherit pkgs; };
  installers = lib.filterAttrs (_: package: package.isInstaller) packages;
  bundles = lib.filterAttrs (_: package: !package.isInstaller) packages;
  manifest = pkgs.writeText "native-macos-apps.json" (
    builtins.toJSON (
      lib.mapAttrs (name: _: {
        inherit (inventory.${name}) appName;
        source = sources.${name};
        format = inventory.${name}.format or "dmg";
        appPath = inventory.${name}.appPath or inventory.${name}.appName;
        removeQuarantine = inventory.${name}.removeQuarantine or false;
        removeFinderInfo = inventory.${name}.removeFinderInfo or false;
      }) bundles
    )
  );
  installApps = pkgs.writeShellScriptBin "mac-config-install-apps" ''
    exec ${pkgs.python3}/bin/python3 ${./scripts/install_native_apps.py} \
      --manifest ${manifest} "$@"
  '';
in
{
  # Nix stages installers and pins downloads; installed GUI apps stay writable.
  environment.systemPackages = [ installApps ] ++ builtins.attrValues installers;
  environment.pathsToLink = [ "/share/macos-pkgs" ];

  # Install missing apps before Home Manager restores Dock entries. Preserve
  # existing apps, including self-updated versions, on subsequent rebuilds.
  system.activationScripts.postActivation.text = lib.mkBefore ''
    launchctl asuser "$(id -u ${lib.escapeShellArg host.username})" \
      sudo -u ${lib.escapeShellArg host.username} --set-home \
      ${installApps}/bin/mac-config-install-apps
  '';
}
