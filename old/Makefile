HOST ?= $(shell test "$$(uname -m)" = arm64 && echo macbook-arm || echo macbook-intel)

.PHONY: check fmt build switch update docs
check:
	nix develop -c bash scripts/check.sh
fmt:
	nix fmt -- ./*.nix
build:
	nix build '.#darwinConfigurations.$(HOST).system'
switch:
	sudo darwin-rebuild switch --flake '.#$(HOST)'
update:
	nix flake update
docs:
	python3 scripts/inventory.py
