{
  pkgs,
  lib,
  username,
  ...
}:
let
  software = import ./software.nix { inherit pkgs lib; };
in
{
  users.users.${username}.home = "/Users/${username}";
  nixpkgs.config.allowUnfree = true;
  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];
  programs.zsh.enable = true;
  environment.systemPackages = software.packages;
  fonts.packages = software.fonts;
  inherit (software) assertions;

  homebrew = {
    enable = true;
    taps = [ "kenn-io/tap" ];
    inherit (software) brews casks masApps;
    onActivation = {
      autoUpdate = false;
      upgrade = false;
      cleanup = "none";
    };
  };

  system = {
    stateVersion = 7;
    primaryUser = username;
    defaults = {
      NSGlobalDomain = {
        AppleInterfaceStyle = "Dark";
        NSAutomaticCapitalizationEnabled = true;
        NSAutomaticPeriodSubstitutionEnabled = true;
        "com.apple.trackpad.scaling" = 0.875;
      };
      CustomUserPreferences.NSGlobalDomain = {
        AppleLanguages = [ "en-US" ];
        AppleLocale = "en_US";
      };
      dock = {
        autohide = true;
        orientation = "bottom";
        tilesize = 64;
        show-recents = false;
        # Vendor/manual apps are restored before applying this captured order.
        # The explicit restore command avoids dead Dock entries on first switch.
      };
      finder = {
        FXPreferredViewStyle = "clmv";
        _FXSortFoldersFirst = true;
      };
      trackpad = {
        Clicking = true;
        TrackpadRightClick = true;
        TrackpadThreeFingerDrag = false;
      };
    };
  };
}
