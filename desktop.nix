{ ... }:
let
  captured = builtins.fromJSON (builtins.readFile ./settings/desktop.json);
in
{
  system.defaults = {
    NSGlobalDomain = captured.global;
    dock = captured.dock;
    finder = captured.finder;
    trackpad = captured.trackpad;
    # Preserve the separately captured built-in and Bluetooth settings.
    CustomUserPreferences = captured.custom;
  };
}
