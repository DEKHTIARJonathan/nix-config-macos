.DEFAULT_GOAL := build

.PHONY: setup build install test test-nix lock

# Find a fresh Nix installation even before the calling shell is restarted.
export PATH := $(PATH):/nix/var/nix/profiles/default/bin:$(HOME)/.nix-profile/bin
NIX_FEATURES := --extra-experimental-features 'nix-command flakes'

# Install bootstrap prerequisites only; building and activation stay explicit.
setup:
	/bin/bash scripts/setup.sh

# Build as the current user, with a separate progress row per download.
# Finish independent downloads/builds even when another source has a bad hash.
build:
	nix $(NIX_FEATURES) run --no-update-lock-file .#nix-output-monitor -- \
	    build .#darwinConfigurations.mac.system \
		$(NIX_FEATURES) --no-update-lock-file --keep-going --out-link result

# Use the built system's launcher, including on a laptop's first activation.
# switch also records the system generation for subsequent rollbacks.
install: build
	sudo ./result/sw/bin/darwin-rebuild switch --flake .#mac --no-update-lock-file

# Explicitly refresh flake input revisions; ordinary builds keep them pinned.
lock:
	nix $(NIX_FEATURES) flake update

# Test settings migration, app installation, download progress, and tool checks.
test:
	uv run --with json5==0.13.0 python -B -m unittest discover -s tests -v

# Also validate generated Home Manager Zsh files on Apple Silicon.
test-nix:
	nix $(NIX_FEATURES) build --no-update-lock-file --no-link -L .#checks.aarch64-darwin.settings
