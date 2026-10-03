#!/usr/bin/env bash
# Downloads/initializes user runtimes only when explicitly invoked.
set -euo pipefail
case "${1:-}" in
  rust)
    rustup toolchain install 1.98.0 --profile default --component rust-src
    rustup default 1.98.0
    rustup target add --toolchain 1.98.0 \
      aarch64-apple-darwin x86_64-apple-darwin wasm32-unknown-unknown x86_64-pc-windows-gnu
    ;;
  android)
    sdk_root="$HOME/Library/Android/sdk"
    mkdir -p "$sdk_root"
    case "$(uname -m)" in
      arm64) image_arch=arm64-v8a ;;
      x86_64) image_arch=x86_64 ;;
      *) echo 'Unsupported Mac architecture' >&2; exit 1 ;;
    esac
    # sdkmanager prompts for licenses; the script does not auto-accept them.
    sdkmanager --sdk_root="$sdk_root" --licenses
    sdkmanager --sdk_root="$sdk_root" \
      'platforms;android-36.1' 'build-tools;36.1.0' 'sources;android-36.1' \
      'ndk;28.2.13676358' emulator \
      "system-images;android-36.1;google_apis_playstore;$image_arch"
    ;;
  *) echo 'Usage: bash scripts/setup-development.sh rust|android' >&2; exit 2 ;;
esac
