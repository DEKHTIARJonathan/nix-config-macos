{ lib, pkgs, ... }:
let
  inventory = import ./dmg-apps.nix { inherit lib; };
  packages = import ./pkgs/macos-apps.nix { inherit pkgs; };
  bundles = lib.filterAttrs (_: package: !package.isInstaller) packages;
  nativeCopies = lib.filterAttrs (name: _: inventory.${name}.preserveXattrs or false) packages;
in
{
  environment.systemPackages = builtins.attrValues packages;
  environment.pathsToLink = [ "/share/macos-pkgs" ];

  assertions = lib.mapAttrsToList (name: package: {
    assertion = package.format == "dmg";
    message = "${name}: preserveXattrs requires a DMG containing an app bundle.";
  }) nativeCopies;

  # PKGs are only staged in /share/macos-pkgs, never executed by Nix.
  system.activationScripts.postActivation.text = lib.mkAfter (
    lib.concatStringsSep "\n" (
      lib.mapAttrsToList (name: package: ''
        # The Nix store cannot retain detached signatures in extended attributes.
        # Copy this bundle from the verified DMG with Apple's native tools.
        (
          mountpoint=$(mktemp -d /private/tmp/nix-app-${name}.XXXXXX)
          trap '
            /usr/bin/hdiutil detach "$mountpoint" >/dev/null 2>&1 || true
            rmdir "$mountpoint" 2>/dev/null || true
          ' EXIT
          /usr/bin/hdiutil attach -readonly -nobrowse -mountpoint "$mountpoint" ${package.src}
          /usr/bin/ditto --rsrc --extattr \
            "$mountpoint/"${lib.escapeShellArg (inventory.${name}.appPath or package.appName)} \
            ${lib.escapeShellArg "/Applications/Nix Apps/${package.appName}"}
          chmod -R a-w ${lib.escapeShellArg "/Applications/Nix Apps/${package.appName}"}
        )
      '') nativeCopies
    )
    + lib.concatStringsSep "\n" (
      lib.mapAttrsToList (
        name: package:
        lib.optionalString (inventory.${name}.removeQuarantine or false) ''
          # Explicit exception for this app only; Gatekeeper remains enabled.
          /usr/bin/xattr -dr com.apple.quarantine ${lib.escapeShellArg "/Applications/Nix Apps/${package.appName}"}
        ''
      ) bundles
    )
  );
}
