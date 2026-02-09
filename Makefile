SHELL := /usr/bin/env bash

CLI := ./bin/hyprwhspr
INSTALL_DEPS := ./scripts/install-deps.sh
SETUP_ARGS ?=
TEST_ARGS ?=
MODEL ?=
PROFILE ?=
REPO ?=
FILE ?=
LOCAL_PATH ?=
LOCAL_REPO ?= mistralai/Voxtral-Mini-4B-Realtime-2602
PYTHON ?= python3

.PHONY: help deps local-runtime-deps setup setup-auto setup-local-model setup-local-model-path setup-local-gguf bootstrap link hf-login status validate test test-live model-current model-set model-list-local model-recommend model-download model-download-gguf profiles profile-use server-start server-stop server-status local-up local-down local-voxtral logs restart run update clean

help:
	@printf "hyprwhspr local workflow targets\n\n"
	@printf "  make deps        Install distro dependencies (Ubuntu/Debian/Fedora/openSUSE)\n"
	@printf "  make local-runtime-deps Install Python deps for local model servers\n"
	@printf "  make setup       Run interactive hyprwhspr setup\n"
	@printf "  make setup-auto  Run automated setup (pass flags via SETUP_ARGS=\"...\")\n"
	@printf "  make setup-local-model Configure local safetensors model (pass REPO=...)\n"
	@printf "  make setup-local-model-path Configure local safetensors model dir (pass LOCAL_PATH=...)\n"
	@printf "  make setup-local-gguf Configure local GGUF file (pass LOCAL_PATH=...)\n"
	@printf "  make bootstrap   Install deps and run interactive setup\n"
	@printf "  make hf-login    Login to HuggingFace CLI\n"
	@printf "  make link        Symlink local CLI into ~/.local/bin\n"
	@printf "  make status      Show current service and backend status\n"
	@printf "  make validate    Validate installation and permissions\n"
	@printf "  make test        Run end-to-end test (pass flags via TEST_ARGS=\"...\")\n"
	@printf "  make test-live   Run live microphone test (3s capture)\n"
	@printf "  make model-current  Show active model for current backend\n"
	@printf "  make model-set   Set active model (pass MODEL=...)\n"
	@printf "  make model-list-local List cached local GGUF models\n"
	@printf "  make model-recommend Show local GPU/quant recommendation\n"
	@printf "  make model-download Download safetensors repo snapshot (pass REPO=...)\n"
	@printf "  make model-download-gguf Download GGUF (pass REPO=... FILE=...)\n"
	@printf "  make profiles    List local model profiles\n"
	@printf "  make profile-use Apply local model profile (pass PROFILE=...)\n"
	@printf "  make server-start Start local model server\n"
	@printf "  make server-stop Stop local model server\n"
	@printf "  make server-status Show local model server status\n"
	@printf "  make local-up    Start server and print status\n"
	@printf "  make local-down  Stop server and print status\n"
	@printf "  make local-voxtral One-shot setup for official Voxtral safetensors repo\n"
	@printf "  make logs        Tail user service logs\n"
	@printf "  make restart     Restart hyprwhspr user service\n"
	@printf "  make run         Run hyprwhspr from this checkout\n"
	@printf "  make update      Pull latest changes and run setup auto\n"
	@printf "  make clean       Remove Python cache artifacts\n\n"
	@printf "Examples:\n"
	@printf "  make setup-auto SETUP_ARGS=\"--backend cpu --no-waybar\"\n"
	@printf "  make test TEST_ARGS=\"--mic-only\"\n"

deps:
	bash "$(INSTALL_DEPS)"

local-runtime-deps:
	"$(PYTHON)" -m pip install --user fastapi uvicorn torch transformers safetensors accelerate huggingface_hub

setup:
	"$(CLI)" setup

setup-auto:
	"$(CLI)" setup auto $(SETUP_ARGS)

setup-local-model:
	@test -n "$(REPO)" || (printf "Usage: make setup-local-model REPO=<org/repo>\n" && exit 1)
	"$(CLI)" setup --local-model --repo "$(REPO)"

setup-local-model-path:
	@test -n "$(LOCAL_PATH)" || (printf "Usage: make setup-local-model-path LOCAL_PATH=<model-directory>\n" && exit 1)
	"$(CLI)" setup --local-model --local-path "$(LOCAL_PATH)"

setup-local-gguf:
	@test -n "$(LOCAL_PATH)" || (printf "Usage: make setup-local-gguf LOCAL_PATH=<model.gguf>\n" && exit 1)
	"$(CLI)" setup --local-gguf --local-path "$(LOCAL_PATH)"

bootstrap: deps setup

hf-login:
	python3 -m huggingface_hub.cli.hf auth login

link:
	mkdir -p "$${HOME}/.local/bin"
	ln -sf "$(abspath $(CLI))" "$${HOME}/.local/bin/hyprwhspr"
	@printf "Linked %s -> %s\n" "$${HOME}/.local/bin/hyprwhspr" "$(abspath $(CLI))"

status:
	"$(CLI)" status

validate:
	"$(CLI)" validate

test:
	"$(CLI)" test $(TEST_ARGS)

test-live:
	"$(CLI)" test --live

model-current:
	"$(CLI)" model current

model-set:
	@test -n "$(MODEL)" || (printf "Usage: make model-set MODEL=<model-id>\n" && exit 1)
	"$(CLI)" model set "$(MODEL)"

model-list-local:
	"$(CLI)" model list-local

model-recommend:
	"$(CLI)" model recommend

model-download:
	@test -n "$(REPO)" || (printf "Usage: make model-download REPO=<org/repo>\n" && exit 1)
	"$(CLI)" model download --repo "$(REPO)"

model-download-gguf:
	@test -n "$(REPO)" || (printf "Usage: make model-download-gguf REPO=<repo-id> FILE=<file.gguf>\n" && exit 1)
	@test -n "$(FILE)" || (printf "Usage: make model-download-gguf REPO=<repo-id> FILE=<file.gguf>\n" && exit 1)
	"$(CLI)" model download --repo "$(REPO)" --file "$(FILE)"

profiles:
	"$(CLI)" backend list-profiles

profile-use:
	@test -n "$(PROFILE)" || (printf "Usage: make profile-use PROFILE=<name>\n" && exit 1)
	"$(CLI)" backend use-profile "$(PROFILE)"

server-start:
	"$(CLI)" backend server start

server-stop:
	"$(CLI)" backend server stop

server-status:
	"$(CLI)" backend server status

local-up: server-start server-status

local-down: server-stop server-status

local-voxtral: local-runtime-deps
	"$(CLI)" setup --local-model --repo "$(LOCAL_REPO)"
	"$(CLI)" backend use-profile "$$(printf '%s' "$(LOCAL_REPO)" | sed 's#/#--#g')-local"
	"$(CLI)" backend server start
	"$(CLI)" backend server status

logs:
	journalctl --user -u hyprwhspr.service -f

restart:
	"$(CLI)" systemd restart

run:
	"$(CLI)"

update:
	git pull --ff-only
	"$(CLI)" setup auto $(SETUP_ARGS)
	"$(CLI)" status

clean:
	find . -type d \( -name __pycache__ -o -name .pytest_cache \) -prune -exec rm -rf {} +
	find . -type f -name '*.py[co]' -delete
