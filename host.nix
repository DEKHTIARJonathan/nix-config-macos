# Machine-specific settings. Start here; the other files rarely need editing.
{
  # REQUIRED: replace with the output of `id -un` on your Mac.
  username = "jonathan";

  # Apple Silicon (M1/M2/M3/etc.): aarch64-darwin.
  # Intel: x86_64-darwin. Run `uname -m` to check your architecture.
  # Use the native architecture even if your terminal runs under Rosetta.
  system = "aarch64-darwin";

  # true: nix-darwin manages upstream Nix and its daemon/configuration.
  # false: your existing Nix installation remains externally managed.
  # Set false if you installed Determinate Nix; that distribution manages
  # its own daemon. The installer and the Nix distribution are distinct:
  # an upstream Nix installation can use true regardless of its installer.
  manageNix = true;

  # Compatibility defaults for a NEW nix-darwin installation.
  # Keep this value when updating packages. It is not a package version.
  # If adapting an existing nix-darwin configuration, preserve its value.
  stateVersion = 7;

  # Optional: uncomment if your existing home directory is elsewhere.
  # homeDirectory = "/Users/yourname";
}
