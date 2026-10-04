{ pkgs, ... }:
let
  # Command-line tooling equivalent to your two Android Homebrew casks.
  # Versions default to those recorded by the locked nixpkgs revision;
  # "latest" within that snapshot does not mean a live Google lookup.
  androidPackages = pkgs.androidenv.composeAndroidPackages {
    # Exclude the obsolete pre-commandlinetools Android SDK tools package.
    toolsVersion = null;

    # The original inventory contains tools, not project SDK platforms.
    # Declare your project's API levels and build-tools versions here when
    # you need Android builds, for example:
    # platformVersions = [ "35" ];
    # buildToolsVersions = [ "35.0.0" ];
    # Those are examples: match your actual project's requirements.
    platformVersions = [ ];
    buildToolsVersions = [ ];

    # Keep the initial SDK small. Enable components only when needed.
    includeEmulator = false;
    includeSystemImages = false;
    includeSources = false;
    includeNDK = false;

    # Your standalone pkgs.cmake is already installed. An Android project
    # may require a specific SDK CMake version; declare it here if so.
    includeCmake = false;
  };

  androidSdk = androidPackages.androidsdk;
  androidSdkRoot = "${androidSdk}/libexec/android-sdk";
in
{
  # Google's SDK packages require their license and are marked unfree.
  # Applying this configuration records acceptance of the Android SDK
  # license. Read the SDK terms before building if you have not accepted
  # them: https://developer.android.com/studio/terms
  nixpkgs.config = {
    allowUnfree = true;
    android_sdk.accept_license = true;
  };

  environment.systemPackages = [
    # Command-line tools for building and debugging Android apps
    # android-commandlinetools -> sdkmanager, avdmanager, etc.
    # Android SDK component
    # android-platform-tools -> adb, fastboot, etc.
    # Both tool sets come from one composed SDK, avoiding duplicate adb.
    androidSdk

    # Supporting runtime for Google's Java-based command-line tools and
    # typical Gradle/Android projects. Change the Java major if your project
    # requires another version; this makes Java available persistently too.
    pkgs.jdk17
  ];

  environment.variables = {
    # Read by command-line Android tooling and Gradle in normal shells.
    ANDROID_HOME = androidSdkRoot;

    # Deprecated upstream, retained for older tools that still read it.
    # Both variables intentionally point at the same SDK.
    ANDROID_SDK_ROOT = androidSdkRoot;

    JAVA_HOME = "${pkgs.jdk17.home}";
  };

  # IMPORTANT: the Nix SDK is read-only. Add components above and rebuild;
  # `sdkmanager --install` cannot modify this SDK. You can still query it.
  # Android Studio launched through Finder does not necessarily inherit
  # these shell variables: select its SDK directory explicitly in the UI.
  # Use `echo "$ANDROID_HOME"` in a fresh terminal to get the current path.
  # Revisit that IDE setting after SDK updates, because store paths change.
}
