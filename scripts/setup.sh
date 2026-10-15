#!/bin/bash
# Bootstrap with macOS's built-in Bash and utilities; no Nix/Python/Brew needed.
set -euo pipefail

fail() {
    printf 'setup: %s\n' "$*" >&2
    exit 1
}

developer_tools_ready() {
    xcrun clang --version >/dev/null 2>&1 &&
        xcrun --sdk macosx --show-sdk-path >/dev/null 2>&1 &&
        git --version >/dev/null 2>&1 &&
        make --version >/dev/null 2>&1
}

ensure_developer_tools() {
    if developer_tools_ready; then
        printf 'Apple command-line developer tools are ready.\n'
        return
    fi

    # A selected but broken installation needs repair, not an automatic switch
    # away from the user's chosen Xcode or silent acceptance of its license.
    if xcode-select -p >/dev/null 2>&1; then
        fail 'The selected Apple developer tools are not usable. Complete Xcode first-launch setup or repair the Command Line Tools, then rerun setup.'
    fi

    printf 'Installing Apple Command Line Tools. Complete the macOS installation dialog; setup will wait (up to 30 minutes). Ctrl-C cancels.\n'
    xcode-select --install
    local attempt
    for ((attempt = 0; attempt < 180; attempt++)); do
        if developer_tools_ready; then
            return
        fi
        sleep 10
    done
    fail 'Command Line Tools are still unavailable. Finish their installation, then rerun setup.'
}

existing_nix_state() {
    [[ -e /nix/store || -e /etc/nix/nix.conf || -L /etc/nix/nix.conf ||
        -e /nix/receipt.json ]]
}

download_and_install_nix() (
    # Finish the download before executing it, and always remove the temporary
    # script. The upstream multi-user installer prompts for sudo as needed.
    # Keep this subshell-scoped, not function-local: Bash 3.2 unwinds locals
    # before an EXIT trap on failure.
    setup_tmp=$(mktemp -d "${TMPDIR:-/tmp}/nix-macos-setup.XXXXXX")
    trap 'rm -rf "$setup_tmp"' EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    curl --fail --show-error --silent --location --retry 3 \
        --proto '=https' --proto-redir '=https' \
        --output "$setup_tmp/install-nix" https://nixos.org/nix/install
    /bin/bash "$setup_tmp/install-nix" --daemon
)

ensure_nix() {
    if command -v nix >/dev/null 2>&1; then
        printf 'Using the existing Nix installation.\n'
    else
        if existing_nix_state; then
            fail 'Found an existing Nix store/configuration but no nix executable. Repair its PATH or installation before retrying; setup will not reinstall over it.'
        fi
        printf 'Installing upstream Nix (multi-user daemon)...\n'
        download_and_install_nix
        hash -r
    fi

    command -v nix >/dev/null 2>&1 || fail 'The installer finished but nix is unavailable. Check the installer output before retrying.'
    nix --version
    # Use explicit features so existing user/root configuration stays intact.
    # Pinging the daemon checks access without fetching flake inputs or apps.
    nix --extra-experimental-features 'nix-command flakes' store ping --store daemon
}

main() {
    [[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] ||
        fail 'Run setup in a native Apple Silicon macOS terminal (not under Rosetta).'
    [[ $(id -u) != 0 ]] || fail 'Run setup as your normal user, without sudo; installers request elevation when needed.'

    # Append fallbacks so an existing installation or project PATH still wins.
    export PATH="$PATH:/nix/var/nix/profiles/default/bin:$HOME/.nix-profile/bin"
    ensure_developer_tools
    ensure_nix
    printf '\nSetup complete. Review host.nix and settings/git.json, then run make build or make install.\n'
    printf 'Homebrew, configured tools/apps, and Rosetta are handled by make install.\n'
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
