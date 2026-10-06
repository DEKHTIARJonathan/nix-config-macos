.DEFAULT_GOAL := build

.PHONY: build install test test-nix lock

# Build as the current user, with a separate progress row per download.
build:
	nix run --no-update-lock-file .#nix-output-monitor -- \
	    build .#darwinConfigurations.mac.system \
		--no-update-lock-file --out-link result

# Use the built system's launcher, including on a laptop's first activation.
# switch also records the system generation for subsequent rollbacks.
install: build
	sudo ./result/sw/bin/darwin-rebuild switch --flake .#mac --no-update-lock-file

# Explicitly refresh flake input revisions; ordinary builds keep them pinned.
lock:
	nix flake update

# Test settings migration, app installation, download progress, and tool checks.
test:
	uv run --with json5==0.13.0 python -B -m unittest discover -s tests -v

# Also validate generated Home Manager Zsh files on Apple Silicon.
test-nix:
	nix build --no-update-lock-file --no-link -L .#checks.aarch64-darwin.settings
