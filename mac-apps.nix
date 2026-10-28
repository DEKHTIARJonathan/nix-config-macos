# Shared inventory for DMG/ZIP app bundles and native PKG installers.
# Set hash = lib.fakeHash when updating; build, copy Nix's reported hash,
# and build again to verify the download and installation layout.
{ lib }:
{
  # ====================== Optional Drivers ====================== #
  brother-scanner = {
    # Explicit installation only; no /Applications app is expected.
    manualInstall = true;
    format = "dmg-pkg";
    url = "https://download.brother.com/welcome/dlf106898/Brother_ScannerDrivers_ICA_1_16_0.dmg";
    hash = "sha256-rCTcnvUEMAmy8mRuBIYYg9gbrrbR0TE5sWhgKLgPWcA=";
  };
  # ====================== LOCAL LLM ====================== #
  bionic = {
    url = "https://lmstudio.ai/download/bionic/latest/darwin/arm64";
    hash = "sha256-Q6tNoah/HEoQU/t+W+/EZJnxy02oH718uBdxsixKNz8=";
  };
  lm-studio = {
    url = "https://lmstudio.ai/download/latest/darwin/arm64";
    hash = "sha256-BfdXAzZwIteXXmQx51bglycDcGO7iBjVizZpYGkliok=";
  };
  # ====================== GIS ====================== #
  ariane = {
    url = "https://github.com/Ariane-s-Line/Ariane-Release/releases/download/26.4.1/Ariane-26.4.1-MACOS-M-SERIES-AARCH64.dmg";
    hash = "sha256-E1tDRd4jwGt6CnBcVcFSsV05OOosLbfanTRT05TGbBg=";
  };
  google-earth-pro = {
    # Explicit Intel exception: the Apple Silicon host needs Rosetta 2.
    format = "dmg-pkg";
    url = "https://dl.google.com/earth/client/advanced/current/GoogleEarthProMac-Intel.dmg";
    hash = "sha256-IN8PSSfzEvjUfmApS5p3/WDkS+YUdqWB+5GVwCm6CJM=";
    appName = "Google Earth Pro.app";
  };
  qgis = {
    # Explicit Intel exception: the Apple Silicon host needs Rosetta 2.
    url = "https://download.qgis.org/downloads/macos/pr/qgis_pr_final-4_2_3.dmg";
    hash = "sha256-zzrz09IooOKgq3+2s3BSrngGTQrvk7EvQfm9ck/SNAE=";
  };
  # ====================== Dev Tools ====================== #
  android-studio = {
    url = "https://edgedl.me.gvt1.com/android/studio/install/2026.2.1.8/android-studio-rabbit1-mac_arm.dmg";
    hash = "sha256-FtSg+KUkE7UYafwY1b3N+c7NOGFc17t88U1RuZ0v71Q=";
  };
  docker-desktop = {
    url = "https://desktop.docker.com/mac/main/arm64/Docker.dmg";
    hash = "sha256-0hvYeH6HYbIsKxt4w0/6mau2wGIZtDuoS2tFCHo1yf4=";
  };
  gitkraken = {
    url = "https://api.gitkraken.dev/releases/production/darwin/arm64/active/installGitKraken.dmg";
    hash = "sha256-1TEOAmnLHJR7wZFQBN+5jmbKJGsCR2nRj7t50KlrTRc=";
  };
  vscode = {
    url = "https://code.visualstudio.com/sha/download?build=stable&os=darwin-arm64-dmg";
    hash = "sha256-rAR3Suuj/XEQySgz2RlRRtUIZCe6ssqQIgDnrZ8Bip4=";
  };
  zed = {
    # download-success is an HTML page; use the matching release asset.
    url = "https://github.com/zed-industries/zed/releases/download/v1.22.0/Zed-aarch64.dmg";
    hash = "sha256-taWmmE8x/vE4cmigdrCRlUSiiFDFz3zX9r9p5gEZf90=";
  };
  # ====================== Browsers ====================== #
  brave = {
    url = "https://referrals.brave.com/latest/Brave-Browser.dmg";
    hash = "sha256-0NauI9Vpg2LvvOwih3jO5//uFgXmDH0kIJ+mfX2zmEU=";
  };
  chrome = {
    url = "https://dl.google.com/tag/s/appguid%3DCOM.GOOGLE.CHROME%26iid%3D%7BA28A17CD-130C-A433-15D3-6C506FCA1744%7D%26brand%3DGGRO/chrome/mac/universal/stable/googlechrome.dmg";
    hash = "sha256-FdnYoz7rhYZnlG8enSnSqCYZIUyJ0bsWqxE8tj7BE1U=";
  };
  firefox = {
    url = "https://download.mozilla.org/?product=firefox-latest-ssl&os=osx&lang=en-US";
    hash = "sha256-3+hQjuiIDOwVeCU+sCuRVLWXGlXoMtlzlvRjzQe172c=";
  };
  # ====================== Mac Tools ====================== #
  bazecor = {
    url = "https://github.com/Dygmalab/Bazecor/releases/download/v1.10.0/Bazecor-1.10.0-arm64.dmg";
    hash = "sha256-Ah7J42TWPE+z2QDxI8S1Us0gs1bYRxpWiX1cgI4Vqkg=";
  };
  gl-kvm = {
    url = "https://static.gl-inet.com/edge-app-staging/kvm-mac/1.6.0-release/1789007253290/gl-kvm-1.6.0-release1.dmg";
    hash = "sha256-nWLt2AliPK8jgvbZ8Q9TYQoF/NFDwbFTkRVWL89BQog=";
  };
  mole = {
    url = "https://mole.fit/download";
    hash = "sha256-OFNAe2uFEtCv+d4oypqatMYAh/YXx+PFrS/jAhiXxmY=";
  };
  raycast = {
    url = "https://www.raycast.com/download/mac";
    hash = "sha256-NZmQ56RSlWDyzsfTKd+txRaEYd2znZb+sif24mk/GmY=";
  };
  rodecaster-app = {
    format = "zip-pkg";
    url = "https://update.rode.com/rc-app/RODECaster_App_MACOS.zip";
    hash = "sha256-+3fenJZN/aH8wgKSC6VmTQoL3pgJASK6uuWGDpbnwh4=";
    appName = "RODECaster App.app";
  };
  tmog = {
    url = "https://tmog.org/rtm/downloads/TMOG-Task-Manager-1.0.0-20260923234339-macOS-universal.dmg";
    hash = "sha256-eMSC5Zjhb6W0eeBalgmjpMH3jfzpYEaL6nfw+5gYmJU=";
  };
  # ====================== USAH Apps ====================== #
  frameforge = {
    url = "https://github.com/OpenSpeleo/FrameForge-Releases/releases/download/v1.2.0/FrameForge_1.2.0_aarch64.dmg";
    hash = "sha256-Qj+hjvq7GxCjFhg1ICfpH8s3iyAkxqbvuzVK7+2CCNM=";
    removeQuarantine = true;
  };
  titanmesh = {
    url = "https://github.com/OpenSpeleo/TitanMesh-Releases/releases/download/v1.1.0/titanmesh-v1.1.0-macos-universal.dmg";
    hash = "sha256-aWzjouiCxBo/07yB2YN5ce1/c30wQ1wu1QYOw5odVpQ=";
    removeQuarantine = true;
  };
  speleodb-compass-sidecar = {
    url = "https://github.com/OpenSpeleo/speleodb_compass_sidecar/releases/download/v26.9.23/SpeleoDB.Compass.Sidecar_26.9.23_aarch64.dmg";
    hash = "sha256-kPLC3B/m8XtOWmO6cb3s4oYHW9ZnK45kuk0fqEYYUSI=";
    removeQuarantine = true;
  };
  # ====================== Video Tools ====================== #
  handbrake = {
    url = "https://github.com/HandBrake/HandBrake/releases/download/1.11.2/HandBrake-1.11.2.dmg";
    hash = "sha256-Sv4nqqd6e7sNzaGjNdlqX1NknyZJ+4TeaYL/7MNd6dc=";
  };
  insta360-studio = {
    format = "zip-pkg";
    url = "https://wassets.insta360.com/common/f8aaff945c6c43b5908a352329d4aa43/Insta360_Studio_6.0.6_release_insta360(RC_build99)_20260929_153449_signed_1790668492358.zip";
    hash = "sha256-qYyyqSUudzDQ6cBzfVXHTAa5mTcvrawLRJK52Dlaaxc=";
    appName = "Insta360 Studio.app";
  };
  vlc = {
    url = "https://get.videolan.org/vlc/3.0.24/macosx/vlc-3.0.24-universal.dmg";
    hash = "sha256-LI6J9/QuU8L7Doe236ObSfE2SyUICqouR2rHTA176zw=";
  };
  # ====================== VPN ====================== #
  nordvpn = {
    format = "pkg";
    url = "https://downloads.nordcdn.com/apps/macos/generic/NordVPN-OpenVPN/latest/NordVPN.pkg";
    hash = "sha256-pg+SIqziTSR8FpHPZudaPSU8y4rEQXFeI10IFDA/Ogo=";
    appName = "NordVPN.app";
  };
  protonvpn = {
    url = "https://protonvpn.com/download/macos/6.5.1/ProtonVPN_mac_v6.5.1.dmg";
    hash = "sha256-1QpJ8UxQsO+K1oqJ/JaF1WmbotT5LLTDQxcpG0JUNfg=";
  };
  # ====================== Communication ====================== #
  rambox = {
    url = "https://rambox.app/api/download?os=mac&package=dmg";
    hash = "sha256-JK5DJEyat8PstdjY4YVJoa2dDQFFU5biwfT2bmMTX/Y=";
  };
  signal = {
    url = "https://updates.signal.org/desktop/signal-desktop-mac-universal-8.29.0.dmg";
    hash = "sha256-K58n4W/WOVPQSMX9S/qlM4M4jAgotl731zZL4H7tMpI=";
  };
  slack = {
    url = "https://slack.com/api/desktop.latestRelease?arch=universal&redirect=true&variant=dmg";
    hash = "sha256-iQnCIrgFVSwYs+hkANxrkAf4i5mtuhC8IQ0513Z+EW8=";
  };
  whatsapp = {
    url = "https://web.whatsapp.com/desktop/mac_native/release/?configuration=Release";
    hash = "sha256-af99kJpk2BgWHh9fuJNo0lUqyRIZ0TA/7djoleNxyek=";
  };
  # ====================== Password Managers ====================== #
  onepassword = {
    format = "pkg";
    # The supplied ZIP contains only a downloader. This is the full installer
    # recommended for managed deployments by support.1password.com.
    url = "https://downloads.1password.com/mac/1Password.pkg";
    hash = "sha256-kCuAIcMIGF8w6SqGoxEypZpNcWgczt7WtS2Q7Hq5s1M=";
    appName = "1Password.app";
  };
  # ====================== Networking ====================== #
  lulu = {
    url = "https://github.com/objective-see/LuLu/releases/download/v4.5.1/LuLu_4.5.1.dmg";
    hash = "sha256-mPTTQn9Mb8z5aA/tIoeb6Qpa6B6A64YWwddYdVtrtiQ=";
  };
  tailscale = {
    format = "pkg";
    url = "https://pkgs.tailscale.com/stable/Tailscale-latest-macos.pkg";
    hash = "sha256-Z+xV8Y7ir6wKj7V/eBGXf0rW3x3r1KGH+g2z27XUAdU=";
    appName = "Tailscale.app";
  };
}
