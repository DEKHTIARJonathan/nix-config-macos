{
  lib,
  pkgs,
  host,
  ...
}:
let
  inventory = import ./mac-apps.nix { inherit lib; };
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
  installerManifest = pkgs.writeText "native-macos-pkgs.json" (
    builtins.toJSON (
      lib.mapAttrs (name: package: {
        inherit (inventory.${name}) appName;
        source = "${package}/share/macos-pkgs/${name}.pkg";
      }) installers
    )
  );
  installPkgs = pkgs.writeShellScriptBin "mac-config-install-pkgs" ''
    exec ${pkgs.python3}/bin/python3 ${./scripts/install_native_pkgs.py} \
      --manifest ${installerManifest} "$@"
  '';
in
{
  # Downloads are pinned; native installers and app copies run at activation.
  environment.systemPackages = [
    installApps
    installPkgs
  ]
  ++ builtins.attrValues installers;
  environment.pathsToLink = [ "/share/macos-pkgs" ];

  # Native apps are installed directly in /Applications. Replace nix-darwin's
  # unused app-copy step, which otherwise creates an empty Nix Apps directory.
  system.activationScripts.applications.text = lib.mkForce ''
    if [ -d '/Applications/Nix Apps' ] && [ ! -L '/Applications/Nix Apps' ]; then
      if ! /bin/rmdir '/Applications/Nix Apps' 2>/dev/null; then
        echo 'Preserving /Applications/Nix Apps: it is not empty or could not be removed.' >&2
      fi
    fi
  '';

  # Install missing apps before Home Manager restores Dock entries. Preserve
  # existing apps, including self-updated versions, on subsequent rebuilds.
  system.activationScripts.postActivation.text = lib.mkBefore ''
    ${installPkgs}/bin/mac-config-install-pkgs
    launchctl asuser "$(id -u ${lib.escapeShellArg host.username})" \
      sudo -u ${lib.escapeShellArg host.username} --set-home \
      ${installApps}/bin/mac-config-install-apps
  '';
}
