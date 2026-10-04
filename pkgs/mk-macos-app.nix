{
  lib,
  stdenvNoCC,
  undmg,
  unzip,
  _7zz,
}:
{
  pname,
  version,
  src,
  appName,
  format ? "dmg",
  appPath ? appName,
  dmgExtractor ? "undmg",
  allowParentSymlinks ? false,
}:
assert lib.assertMsg (builtins.elem format [
  "dmg"
  "zip"
  "pkg"
  "zip-pkg"
  "dmg-pkg"
]) "Unsupported macOS installer format: ${format}";
assert lib.assertMsg (builtins.elem dmgExtractor [
  "undmg"
  "7zz"
]) "Unsupported DMG extractor: ${dmgExtractor}";
let
  isInstaller = builtins.elem format [
    "pkg"
    "zip-pkg"
    "dmg-pkg"
  ];
in
stdenvNoCC.mkDerivation (
  {
    inherit pname version src;

    nativeBuildInputs =
      lib.optional (builtins.elem format [
        "dmg"
        "dmg-pkg"
      ]) (if dmgExtractor == "7zz" then _7zz else undmg)
      ++ lib.optional (builtins.elem format [
        "zip"
        "zip-pkg"
      ]) unzip;
    sourceRoot = ".";
    dontUnpack = format == "pkg";
    # Skip all patch/build/fixup hooks: preserve the complete vendor bundle,
    # including signed resources and ad-hoc signatures on OpenSpeleo apps.
    phases = [
      "unpackPhase"
      "installPhase"
    ];

    installPhase = ''
      runHook preInstall
    ''
    + (
      if isInstaller then
        ''
          mkdir -p "$out/share/macos-pkgs"
          ${
            if format == "pkg" then
              ''
                cp "$src" "$out/share/macos-pkgs/${pname}.pkg"
              ''
            else
              ''
                # Accept a nested archive layout, but never choose between PKGs.
                packages=()
                while IFS= read -r -d "" package; do
                  packages+=("$package")
                done < <(find . -name __MACOSX -prune -o -name '*.pkg' -print0 -prune)
                if [ "''${#packages[@]}" -ne 1 ]; then
                  echo "Expected exactly one PKG in ${pname}'s archive, found ''${#packages[@]}" >&2
                  exit 1
                fi
                cp -R "''${packages[0]}" "$out/share/macos-pkgs/${pname}.pkg"
              ''
          }
        ''
      else
        ''
          app=${lib.escapeShellArg appPath}
          if [ ! -f "$app/Contents/Info.plist" ]; then
            echo "Missing app bundle: $app" >&2
            find . -maxdepth 3 -name '*.app' -print >&2
            exit 1
          fi
          mkdir -p "$out/Applications"
          cp -R "$app" "$out/Applications/"${lib.escapeShellArg appName}
        ''
    )
    + ''
      runHook postInstall
    '';

    passthru = { inherit appName format isInstaller; };
    meta = {
      platforms = [ "aarch64-darwin" ];
      sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
    };
  }
  //
    lib.optionalAttrs
      (
        builtins.elem format [
          "dmg"
          "dmg-pkg"
        ]
        && dmgExtractor == "7zz"
      )
      {
        unpackPhase = ''
          runHook preUnpack
          # 7-Zip also reads APFS DMGs. Extract only the selected app, preserve
          # symlinks, and omit xattr streams (which otherwise become extra files).
          7zz x -y -sns- ${lib.optionalString allowParentSymlinks "-snld"} -bso0 -bsp0 "$src" ${
            lib.optionalString (!isInstaller) (lib.escapeShellArg "${appPath}/*")
          }
          runHook postUnpack
        '';
      }
)
