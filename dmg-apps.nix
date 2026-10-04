# Shared inventory for DMG/ZIP app bundles and native PKG installers.
# Set hash = lib.fakeHash when updating; build, copy Nix's reported hash,
# and build again to verify the download and installation layout.
{ lib }:
let
  arm = [ "aarch64-darwin" ];
in
{
  ariane = {
    version = "26.4.1";
    url = "https://github.com/Ariane-s-Line/Ariane-Release/releases/download/26.4.1/Ariane-26.4.1-MACOS-M-SERIES-AARCH64.dmg";
    hash = "sha256-E1tDRd4jwGt6CnBcVcFSsV05OOosLbfanTRT05TGbBg=";
    appName = "Ariane.app";
    platforms = arm;
  };
  mole = {
    dmgExtractor = "7zz";
    version = "1.15.0";
    url = "https://cdn.tw93.fun/mole/Mole-1.15.0.dmg";
    hash = "sha256-eZAMUi6XJUmngneTiOhkyAMhV1qyoe1TTN7GMt8DBhQ=";
    appName = "Mole.app";
  };
  bazecor = {
    version = "1.10.0";
    url = "https://github.com/Dygmalab/Bazecor/releases/download/v1.10.0/Bazecor-1.10.0-arm64.dmg";
    hash = "sha256-Ah7J42TWPE+z2QDxI8S1Us0gs1bYRxpWiX1cgI4Vqkg=";
    appName = "Bazecor.app";
    platforms = arm;
  };
  titanmesh = {
    version = "1.0.0";
    url = "https://github.com/OpenSpeleo/TitanMesh-Releases/releases/download/v1.0.0/titanmesh-v1.0.0-macos-universal.dmg";
    hash = "sha256-YDvnzD01rHTsjhdqx3jTg5is3DZxv7WJNemarUl4j+Y=";
    appName = "TitanMesh.app";
    removeQuarantine = true;
  };
  speleodb-compass-sidecar = {
    version = "26.9.23";
    url = "https://github.com/OpenSpeleo/speleodb_compass_sidecar/releases/download/v26.9.23/SpeleoDB.Compass.Sidecar_26.9.23_aarch64.dmg";
    hash = "sha256-kPLC3B/m8XtOWmO6cb3s4oYHW9ZnK45kuk0fqEYYUSI=";
    appName = "SpeleoDB Compass Sidecar.app";
    removeQuarantine = true;
    platforms = arm;
  };
  frameforge = {
    dmgExtractor = "7zz";
    version = "1.2.0";
    url = "https://github.com/OpenSpeleo/FrameForge-Releases/releases/download/v1.2.0/FrameForge_1.2.0_aarch64.dmg";
    hash = "sha256-Qj+hjvq7GxCjFhg1ICfpH8s3iyAkxqbvuzVK7+2CCNM=";
    appName = "FrameForge.app";
    removeQuarantine = true;
    platforms = arm;
  };
  gl-kvm = {
    dmgExtractor = "7zz";
    version = "1.6.0-release1";
    url = "https://static.gl-inet.com/edge-app-staging/kvm-mac/1.6.0-release/1789007253290/gl-kvm-1.6.0-release1.dmg";
    hash = "sha256-nWLt2AliPK8jgvbZ8Q9TYQoF/NFDwbFTkRVWL89BQog=";
    appName = "GLKVM.app";
  };
  handbrake = {
    version = "1.11.2";
    # The supplied rotation.php page embeds this actual DMG URL.
    url = "https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrake-1.11.2.dmg";
    hash = "sha256-Sv4nqqd6e7sNzaGjNdlqX1NknyZJ+4TeaYL/7MNd6dc=";
    appName = "HandBrake.app";
  };
  protonvpn = {
    version = "6.5.1";
    url = "https://protonvpn.com/download/macos/6.5.1/ProtonVPN_mac_v6.5.1.dmg";
    hash = "sha256-1QpJ8UxQsO+K1oqJ/JaF1WmbotT5LLTDQxcpG0JUNfg=";
    appName = "ProtonVPN.app";
  };
  rambox = {
    version = "2.7.1";
    downloadName = "rambox-latest.dmg";
    url = "https://rambox.app/api/download?os=mac&package=dmg";
    hash = "sha256-UfBP2LVBcQUw1pwSrQc5NIN0ZTVk/sCM0Zt2EldhL+s=";
    appName = "Rambox.app";
  };
  signal = {
    version = "8.29.0";
    url = "https://updates.signal.org/desktop/signal-desktop-mac-universal-8.29.0.dmg";
    hash = "sha256-K58n4W/WOVPQSMX9S/qlM4M4jAgotl731zZL4H7tMpI=";
    appName = "Signal.app";
  };
  vlc = {
    # plugins.dat has a detached signature stored in extended attributes.
    # Restore the native bundle at activation; the Nix store drops xattrs.
    preserveXattrs = true;
    version = "3.0.24";
    url = "https://get.videolan.org/vlc/3.0.24/macosx/vlc-3.0.24-universal.dmg";
    hash = "sha256-LI6J9/QuU8L7Doe236ObSfE2SyUICqouR2rHTA176zw=";
    appName = "VLC.app";
  };
  zed = {
    dmgExtractor = "7zz";
    version = "1.22.0";
    # download-success is an HTML page; use the matching release asset.
    url = "https://github.com/zed-industries/zed/releases/download/v1.22.0/Zed-aarch64.dmg";
    hash = "sha256-taWmmE8x/vE4cmigdrCRlUSiiFDFz3zX9r9p5gEZf90=";
    appName = "Zed.app";
    platforms = arm;
  };
  vscode = {
    version = "1.140.0";
    downloadName = "vscode-07f806f999227108933c2e30515b26eecc1fda74.dmg";
    url = "https://vscode.download.prss.microsoft.com/dbazure/download/stable/07f806f999227108933c2e30515b26eecc1fda74/VSCode-darwin-arm64.dmg";
    hash = "sha256-Wcx3EotORVHaDJfwQ3/WHT0LK8R9gMO5KchZNoo5odM=";
    appName = "Visual Studio Code.app";
    platforms = arm;
  };
  gitkraken = {
    version = "12.6.0";
    url = "https://release.gitkraken.dev/gkd/production/normal/darwin/arm64/12.6.0/3K6vJ86wvnBNQdR1D23qN80JvdP/installGitKraken.dmg";
    hash = "sha256-1TEOAmnLHJR7wZFQBN+5jmbKJGsCR2nRj7t50KlrTRc=";
    appName = "GitKraken.app";
    platforms = arm;
  };
  onepassword = {
    version = "8.12.38";
    downloadName = "onepassword-latest.pkg";
    format = "pkg";
    # The supplied ZIP contains only a downloader. This is the full installer
    # recommended for managed deployments by support.1password.com.
    url = "https://downloads.1password.com/mac/1Password.pkg";
    hash = "sha256-ZZmDh5Stl13qbuZ4gMIcmiGG//ITGndgnrB1nZi1Mek=";
    appName = "1Password.app";
  };
  nordvpn = {
    version = "10.12.0";
    downloadName = "nordvpn-latest.pkg";
    format = "pkg";
    url = "https://downloads.nordcdn.com/apps/macos/generic/NordVPN-OpenVPN/latest/NordVPN.pkg";
    hash = "sha256-UTwGA9O1s2whRYU5SVSLPtQqSDDkvMc/1U1UkSTB3Qc=";
    appName = "NordVPN.app";
  };
  tailscale = {
    version = "1.102.4";
    format = "pkg";
    url = "https://pkgs.tailscale.com/stable/Tailscale-1.102.4-macos.pkg";
    hash = "sha256-tAtzOvdiM/0eSvesrrMlJo5V5oGMFcbpqp549CckXFs=";
    appName = "Tailscale.app";
  };
  insta360-studio = {
    version = "6.0.6";
    format = "zip-pkg";
    url = "https://wassets.insta360.com/common/f8aaff945c6c43b5908a352329d4aa43/Insta360_Studio_6.0.6_release_insta360(RC_build99)_20260929_153449_signed_1790668492358.zip";
    hash = "sha256-qYyyqSUudzDQ6cBzfVXHTAa5mTcvrawLRJK52Dlaaxc=";
    appName = "Insta360 Studio.app";
  };
}
