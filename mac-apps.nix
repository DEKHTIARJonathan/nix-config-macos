# Shared inventory for DMG/ZIP app bundles and native PKG installers.
# Set hash = lib.fakeHash when updating; build, copy Nix's reported hash,
# and build again to verify the download and installation layout.
{ lib }:
{
  # ====================== LOCAL LLM ====================== #
  bionic = {
    version = "latest";
    downloadName = "bionic-latest.dmg";
    url = "https://lmstudio.ai/download/bionic/latest/darwin/arm64";
    hash = "sha256-0HxGsvlFtCKnwUTsBCi3Z50hEgw5+vvKRz2WFbXfQ8g=";
    appName = "Bionic.app";
  };
  lm-studio = {
    version = "latest";
    downloadName = "lm-studio-latest.dmg";
    url = "https://lmstudio.ai/download/latest/darwin/arm64";
    hash = "sha256-BfdXAzZwIteXXmQx51bglycDcGO7iBjVizZpYGkliok=";
    appName = "LM Studio.app";
  };
  # ====================== GIS ====================== #
  ariane = {
    version = "26.4.1";
    url = "https://github.com/Ariane-s-Line/Ariane-Release/releases/download/26.4.1/Ariane-26.4.1-MACOS-M-SERIES-AARCH64.dmg";
    hash = "sha256-E1tDRd4jwGt6CnBcVcFSsV05OOosLbfanTRT05TGbBg=";
    appName = "Ariane.app";
  };
  google-earth-pro = {
    # Explicit Intel exception: the Apple Silicon host needs Rosetta 2.
    version = "latest";
    format = "dmg-pkg";
    downloadName = "google-earth-pro-intel.dmg";
    url = "https://dl.google.com/earth/client/advanced/current/GoogleEarthProMac-Intel.dmg";
    hash = "sha256-IN8PSSfzEvjUfmApS5p3/WDkS+YUdqWB+5GVwCm6CJM=";
    appName = "Google Earth Pro.app";
  };
  # ====================== Dev Tools ====================== #
  android-studio = {
    version = "2026.2.1.8";
    url = "https://edgedl.me.gvt1.com/android/studio/install/2026.2.1.8/android-studio-rabbit1-mac_arm.dmg";
    hash = "sha256-FtSg+KUkE7UYafwY1b3N+c7NOGFc17t88U1RuZ0v71Q=";
    appName = "Android Studio.app";
  };
  docker-desktop = {
    version = "latest";
    downloadName = "docker-desktop.dmg";
    url = "https://desktop.docker.com/mac/main/arm64/Docker.dmg";
    hash = "sha256-AhR+TVWf9B4dnXvmOlVBATQCNwZMe23yNFSKoRHr8Ew=";
    appName = "Docker.app";
  };
  gitkraken = {
    version = "latest";
    url = "https://api.gitkraken.dev/releases/production/darwin/arm64/active/installGitKraken.dmg";
    hash = "sha256-1TEOAmnLHJR7wZFQBN+5jmbKJGsCR2nRj7t50KlrTRc=";
    appName = "GitKraken.app";
  };
  vscode = {
    version = "latest";
    downloadName = "vscode.dmg";
    url = "https://code.visualstudio.com/sha/download?build=stable&os=darwin-arm64-dmg";
    hash = "sha256-qw7MdIVdXTjomGBSNLwDOye3nyAubxKhFEL8QQrgZWE=";
    appName = "Visual Studio Code.app";
  };
  zed = {
    dmgExtractor = "7zz";
    version = "1.22.0";
    # download-success is an HTML page; use the matching release asset.
    url = "https://github.com/zed-industries/zed/releases/download/v1.22.0/Zed-aarch64.dmg";
    hash = "sha256-taWmmE8x/vE4cmigdrCRlUSiiFDFz3zX9r9p5gEZf90=";
    appName = "Zed.app";
  };
  # ====================== Browsers ====================== #
  brave = {
    # Vendor helper bundles carry FinderInfo that fails strict signature checks.
    removeFinderInfo = true;
    dmgExtractor = "7zz";
    # The signed updater links MacOS/ksadmin to ../Helpers/ksadmin inside its bundle.
    allowParentSymlinks = true;
    version = "latest";
    downloadName = "brave-browser.dmg";
    url = "https://laptop-updates.brave.com/download/BRV010?bitness=64";
    hash = "sha256-p5M5es79W8Pype7S9C0Gi026aykfZa8At6TpFyIufVA=";
    appName = "Brave Browser.app";
  };
  chrome = {
    version = "154.0.8037.98";
    downloadName = "googlechrome.dmg";
    url = "https://dl.google.com/tag/s/appguid%3DCOM.GOOGLE.CHROME%26iid%3D%7BA28A17CD-130C-A433-15D3-6C506FCA1744%7D%26brand%3DGGRO/chrome/mac/universal/stable/googlechrome.dmg";
    hash = "sha256-7gLzm6L/ravtkTWCggjEzH5DuuGLCL+0Ie0AIvkrnd0=";
    appName = "Google Chrome.app";
  };
  firefox = {
    version = "latest";
    downloadName = "Firefox.dmg";
    url = "https://download.mozilla.org/?product=firefox-latest-ssl&os=osx&lang=en-US";
    hash = "sha256-QKCmSRIGNUYCVtrprWPkA3f3cybLycRJpdCh1/XdeYI=";
    appName = "Firefox.app";
  };
  # ====================== Mac Tools ====================== #
  bazecor = {
    version = "1.10.0";
    url = "https://github.com/Dygmalab/Bazecor/releases/download/v1.10.0/Bazecor-1.10.0-arm64.dmg";
    hash = "sha256-Ah7J42TWPE+z2QDxI8S1Us0gs1bYRxpWiX1cgI4Vqkg=";
    appName = "Bazecor.app";
  };
  gl-kvm = {
    dmgExtractor = "7zz";
    version = "1.6.0-release1";
    url = "https://static.gl-inet.com/edge-app-staging/kvm-mac/1.6.0-release/1789007253290/gl-kvm-1.6.0-release1.dmg";
    hash = "sha256-nWLt2AliPK8jgvbZ8Q9TYQoF/NFDwbFTkRVWL89BQog=";
    appName = "GLKVM.app";
  };
  mole = {
    dmgExtractor = "7zz";
    version = "latest";
    url = "https://mole.fit/download";
    hash = "sha256-eZAMUi6XJUmngneTiOhkyAMhV1qyoe1TTN7GMt8DBhQ=";
    appName = "Mole.app";
  };
  raycast = {
    version = "latest";
    url = "https://www.raycast.com/download/mac";
    hash = "sha256-P8QGQZiujT/4jxW0j/jbZxce88uz/4BaODceKP+Zpgw=";
    appName = "Raycast.app";
  };
  rodecaster-app = {
    version = "latest";
    format = "zip-pkg";
    downloadName = "rodecaster-app.zip";
    url = "https://update.rode.com/rc-app/RODECaster_App_MACOS.zip";
    hash = "sha256-+3fenJZN/aH8wgKSC6VmTQoL3pgJASK6uuWGDpbnwh4=";
    appName = "RODECaster App.app";
  };
  # ====================== USAH Apps ====================== #
  frameforge = {
    dmgExtractor = "7zz";
    version = "1.2.0";
    url = "https://github.com/OpenSpeleo/FrameForge-Releases/releases/download/v1.2.0/FrameForge_1.2.0_aarch64.dmg";
    hash = "sha256-Qj+hjvq7GxCjFhg1ICfpH8s3iyAkxqbvuzVK7+2CCNM=";
    appName = "FrameForge.app";
    removeQuarantine = true;
  };
  titanmesh = {
    version = "1.1.0";
    url = "https://github.com/OpenSpeleo/TitanMesh-Releases/releases/download/v1.1.0/titanmesh-v1.1.0-macos-universal.dmg";
    hash = "sha256-aWzjouiCxBo/07yB2YN5ce1/c30wQ1wu1QYOw5odVpQ=";
    appName = "TitanMesh.app";
    removeQuarantine = true;
  };
  speleodb-compass-sidecar = {
    version = "26.9.23";
    url = "https://github.com/OpenSpeleo/speleodb_compass_sidecar/releases/download/v26.9.23/SpeleoDB.Compass.Sidecar_26.9.23_aarch64.dmg";
    hash = "sha256-kPLC3B/m8XtOWmO6cb3s4oYHW9ZnK45kuk0fqEYYUSI=";
    appName = "SpeleoDB Compass Sidecar.app";
    removeQuarantine = true;
  };
  # ====================== Video Tools ====================== #
  handbrake = {
    version = "1.11.2";
    # The supplied rotation.php page embeds this actual DMG URL.
    url = "https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrake-1.11.2.dmg";
    hash = "sha256-Sv4nqqd6e7sNzaGjNdlqX1NknyZJ+4TeaYL/7MNd6dc=";
    appName = "HandBrake.app";
  };
  insta360-studio = {
    version = "6.0.6";
    format = "zip-pkg";
    url = "https://wassets.insta360.com/common/f8aaff945c6c43b5908a352329d4aa43/Insta360_Studio_6.0.6_release_insta360(RC_build99)_20260929_153449_signed_1790668492358.zip";
    hash = "sha256-qYyyqSUudzDQ6cBzfVXHTAa5mTcvrawLRJK52Dlaaxc=";
    appName = "Insta360 Studio.app";
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
  # ====================== VPN ====================== #
  nordvpn = {
    version = "latest";
    downloadName = "nordvpn-latest.pkg";
    format = "pkg";
    url = "https://downloads.nordcdn.com/apps/macos/generic/NordVPN-OpenVPN/latest/NordVPN.pkg";
    hash = "sha256-UTwGA9O1s2whRYU5SVSLPtQqSDDkvMc/1U1UkSTB3Qc=";
    appName = "NordVPN.app";
  };
  protonvpn = {
    version = "6.5.1";
    url = "https://protonvpn.com/download/macos/6.5.1/ProtonVPN_mac_v6.5.1.dmg";
    hash = "sha256-1QpJ8UxQsO+K1oqJ/JaF1WmbotT5LLTDQxcpG0JUNfg=";
    appName = "ProtonVPN.app";
  };
  # ====================== Communication ====================== #
  rambox = {
    version = "latest";
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
  slack = {
    version = "latest";
    downloadName = "slack-latest.dmg";
    url = "https://slack.com/api/desktop.latestRelease?arch=universal&redirect=true&variant=dmg";
    hash = "sha256-iQnCIrgFVSwYs+hkANxrkAf4i5mtuhC8IQ0513Z+EW8=";
    appName = "Slack.app";
  };
  # ====================== Password Managers ====================== #
  onepassword = {
    version = "latest";
    downloadName = "onepassword-latest.pkg";
    format = "pkg";
    # The supplied ZIP contains only a downloader. This is the full installer
    # recommended for managed deployments by support.1password.com.
    url = "https://downloads.1password.com/mac/1Password.pkg";
    hash = "sha256-kCuAIcMIGF8w6SqGoxEypZpNcWgczt7WtS2Q7Hq5s1M=";
    appName = "1Password.app";
  };
  # ====================== Networking ====================== #
  tailscale = {
    version = "latest";
    format = "pkg";
    url = "https://pkgs.tailscale.com/stable/Tailscale-latest-macos.pkg";
    hash = "sha256-Z+xV8Y7ir6wKj7V/eBGXf0rW3x3r1KGH+g2z27XUAdU=";
    appName = "Tailscale.app";
  };
}
