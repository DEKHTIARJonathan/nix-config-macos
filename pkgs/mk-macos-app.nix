{
  lib,
  stdenvNoCC,
  undmg,
  unzip,
  _7zz,
  python3,
}:
{
  pname,
  src,
  appName ? null,
  format ? "dmg",
}:
assert lib.assertMsg (builtins.elem format [
  "dmg"
  "zip"
  "pkg"
  "zip-pkg"
  "dmg-pkg"
]) "Unsupported macOS installer format: ${format}";
let
  isDmg = builtins.elem format [
    "dmg"
    "dmg-pkg"
  ];
  isInstaller = builtins.elem format [
    "pkg"
    "zip-pkg"
    "dmg-pkg"
  ];
in
assert lib.assertMsg (
  !isInstaller || appName != null
) "PKG entry ${pname} requires appName to verify installation";
stdenvNoCC.mkDerivation (
  {
    name = pname;
    inherit pname src;

    nativeBuildInputs =
      lib.optionals isDmg [
        undmg
        _7zz
      ]
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
          app="$(${python3}/bin/python3 ${../scripts/install_native_apps.py} --find-bundle .)"
          appName=${if appName != null then lib.escapeShellArg appName else ''"''${app##*/}"''}
          mkdir -p "$out/Applications"
          cp -R "$app" "$out/Applications/$appName"
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
  // lib.optionalAttrs isDmg {
    unpackPhase = ''
      runHook preUnpack
      # Inspect archive headers only: filenames must not affect detection.
      listing="$(LC_ALL=C 7zz l -slt "$src")"
      filesystem="$(printf '%s\n' "$listing" | awk '
        /^----------$/ { files = 1 }
        !files && /^Type = (HFS|APFS)$/ { print $3 }
      ')"
      case "$filesystem" in
        HFS)
          echo "Detected HFS DMG; extracting with undmg"
          undmg "$src"
          ;;
        APFS)
          echo "Detected APFS DMG; extracting with 7zz"
          # Omit the Applications shortcut and xattr streams; keep bundle links.
          7zz x -y -sns- -bso0 -bsp0 "$src" ${lib.optionalString (!isInstaller) "'-ir!*.app/*'"}
          ;;
        *)
          echo "Expected one HFS or APFS filesystem in the DMG; detected: ''${filesystem:-none}" >&2
          exit 1
          ;;
      esac
      runHook postUnpack
    '';
  }
)
