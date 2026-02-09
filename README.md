<h1 align="center">
    hyprwhspr
</h1>

<p align="center">
    <b>Native speech-to-text for Linux</b> - Fast, accurate and private system-wide dictation
</p>

<p align="center">
    instant performance | Parakeet / Whisper / ElevenLabs / REST API | stylish visuals
</p>

 <p align="center">
    <i>Supports Arch, Debian, Ubuntu, Fedora, openSUSE and more</i>
 </p>

https://github.com/user-attachments/assets/4c223e85-2916-494f-b7b1-766ce1bdc991

---

- **Built for Linux** - Native AUR package for Arch, or use Debian/Ubuntu/Fedora/openSUSE
- **Local, very fast defaults** - Instant, private and accurate performance via in-memory models
- **Latest models** - Turbo-v3? Parakeet TDT V3? Latest and greatest
- **onnx-asr for wild CPU speeds** - No GPU? Optimized for great speed on any hardware
- **REST API or websockets** - Secure, fast wires to top clouds like ElevenLabs
- **Local GGUF websocket server** - Run local realtime transcription with on-demand auto-start
- **Themed visualizer** - Visualizes your voice, will automatch Omarchy theme
- **Word overides and prompts** - Custom hot keys, common words, and more
- **Multi-lingual** - Great performance in many languages
- **Long form mode with saving** - Pause, think, resume, pause: submit... Bam!
- **Auto-paste anywhere** - Instant paste into any active buffer, or even auto enter (optional)
- **Audio ducking 🦆** - Reduces system volume on record (optional)

## Quick start

### Prerequisites

- **Linux** with systemd (Arch, Debian, Ubuntu, Fedora, openSUSE, etc.)
- **Requires a Wayland session** (GNOME, KDE Plasma Wayland, Sway, Hyprland)

- **Waybar** (optional, for status bar)
- **gtk4** (optional, for visualizer)
- **NVIDIA GPU** (optional, for CUDA acceleration)
- **AMD/Intel GPU / APU** (optional, for Vulkan acceleration)

### Quick start (Arch Linux)

On the AUR:

```bash
# Install for stable
yay -S hyprwhspr

# Or install for bleeding edge
yay -S hyprwhspr-git
```

Then run the auto installer, or perform your own:

```bash
# Run interactive setup
hyprwhspr setup
```

**The setup will walk you through the process:**

1. ✅ Configure transcription backend (Parakeet TDT V3, pywhispercpp, REST API, or Realtime WebSocket)
2. ✅ Download models (if using pywhispercpp backend)
3. ✅ Configure themed visualizer for maximum coolness (optional)
4. ✅ Configure Waybar integration (optional)
5. ✅ Set up systemd user services 
6. ✅ Set up permissions
7. ✅ Validate installation

### First use

> Ensure your microphone of choice is available in audio settings!

1. **Log out and back in** (for group permissions)
2. **Press `Super+Alt+D`** to start dictation - _beep!_
3. **Speak naturally**
4. **Press `Super+Alt+D`** again to stop dictation - _boop!_
5. **Bam!** Text appears in active buffer!

Any snags, please [create an issue](https://github.com/goodroot/hyprwhspr/issues/new/choose).

### Local model quick start (safetensors first, GGUF optional)

You can run a local websocket server and point `realtime-ws` at `ws://127.0.0.1:8000/v1/realtime`.

Recommended flow is to start from official HuggingFace safetensors repos and run them directly via the local safetensors server.

```bash
# 1) Check GPU + quantization recommendation
hyprwhspr model recommend

# 2) Configure from official safetensors repo (downloads + runs directly)
hyprwhspr setup --local-model \
  --repo mistralai/Voxtral-Mini-4B-Realtime-2602

# 4) Optional: inspect or control the server manually
hyprwhspr backend server status
hyprwhspr backend server start
hyprwhspr backend server stop
```

If you already have a local `.gguf` file (optional direct path):

```bash
hyprwhspr setup --local-gguf --local-path /path/to/model.gguf
```

#### Official Mistral repo example (`.safetensors`)

`mistralai/Voxtral-Mini-4B-Realtime-2602` is distributed as HuggingFace transformer weights (`.safetensors`).

hyprwhspr now supports this directly via `--local-model` (no conversion required).

```bash
# 1) Login (for gated/private repos)
huggingface-cli login

# 2) Configure local model directly from the repo
hyprwhspr setup --local-model \
  --repo mistralai/Voxtral-Mini-4B-Realtime-2602

# 3) Check server status
hyprwhspr backend server status
```

Optional: direct GGUF path remains available via `hyprwhspr setup --local-gguf ...`.

### Updating

```bash
# Update via your AUR helper
yay -Syu hyprwhspr

# If needed, re-run setup (idempotent)
hyprwhspr setup
```

### Other Linux distros

hyprwhspr can run on any Linux distribution with systemd.

**Quick install (recommended):**

Use the install script to automatically install dependencies for your distro:

```bash
# Download and run the install script
curl -fsSL https://raw.githubusercontent.com/goodroot/hyprwhspr/main/scripts/install-deps.sh | bash

# Clone and run setup
git clone https://github.com/goodroot/hyprwhspr.git ~/hyprwhspr
cd ~/hyprwhspr
./bin/hyprwhspr setup
```

The script supports Ubuntu, Debian, Fedora, and openSUSE.

> Non-Arch distro support is new - please report any snags!

### Local setup with Make

If you cloned this repo and want a repeatable local workflow, use the included `Makefile`:

```bash
# Show available commands
make help

# Install distro dependencies and run interactive setup
make bootstrap

# Re-run automated setup with flags
make setup-auto SETUP_ARGS="--backend cpu --no-waybar"

# Keep your local checkout updated and refresh setup
make update
```

Useful day-to-day targets:

- `make status` - current service + backend status
- `make validate` - verify installation/permissions
- `make test` - end-to-end test (or `make test-live`)
- `make logs` - tail `hyprwhspr.service` logs
- `make link` - symlink this checkout into `~/.local/bin/hyprwhspr`
- `make model-recommend` - show local GPU/quant recommendation
- `make local-runtime-deps` - install Python dependencies for local model servers
- `make hf-login` - login to HuggingFace CLI
- `make model-download REPO=...` - download safetensors model snapshot
- `make model-download-gguf REPO=... FILE=...` - download a GGUF model
- `make setup-local-model REPO=...` - configure local safetensors model (recommended)
- `make setup-local-model-path LOCAL_PATH=...` - configure local safetensors model directory
- `make setup-local-gguf LOCAL_PATH=...` - configure local GGUF file
- `make local-up` - start local model server and print status
- `make local-down` - stop local model server and print status
- `make local-voxtral` - one-shot setup/start for official Voxtral safetensors repo
- `make server-status` - show local model server status

Voxtral quick path with Make:

```bash
make hf-login
make local-voxtral
```

<details>
<summary><b>Manual installation instructions</b></summary>

**Debian / Ubuntu:**

```bash
# Install system dependencies (NOTE: do NOT install ydotool from apt)
sudo apt install python3 python3-pip python3-venv git cmake make build-essential \
    python3-dev libportaudio2 python3-numpy python3-scipy python3-evdev \
    python3-requests python3-psutil python3-rich \
    python3-gi gir1.2-gtk-4.0 gir1.2-gtk4layershell-1.0 \
    pipewire pipewire-pulse wl-clipboard wget

# Install ydotool 1.0+ from Debian backports (required!)
wget http://deb.debian.org/debian/pool/main/y/ydotool/ydotool_1.0.4-2~bpo13+1_amd64.deb
sudo dpkg -i ydotool_1.0.4-2~bpo13+1_amd64.deb
sudo apt install -f  # Fix any dependency issues

# Install Python packages not in Debian repos
pip install --user --break-system-packages sounddevice pyperclip

# Clone and run setup
git clone https://github.com/goodroot/hyprwhspr.git ~/hyprwhspr
cd ~/hyprwhspr
./bin/hyprwhspr setup
```

> **Note:** On Ubuntu 22.04 LTS, `gir1.2-gtk4layershell-1.0` may not be available. The mic-osd visualizer will be disabled, but dictation works fine without it.

**Fedora:**

```bash
# Install system dependencies
sudo dnf install python3 python3-pip python3-devel git cmake make gcc-c++ \
    python3-sounddevice python3-numpy python3-scipy python3-evdev \
    python3-pyperclip python3-requests python3-psutil python3-rich \
    python3-gobject gtk4 gtk4-layer-shell \
    pipewire pipewire-pulseaudio ydotool wl-clipboard

# Clone and run setup
git clone https://github.com/goodroot/hyprwhspr.git ~/hyprwhspr
cd ~/hyprwhspr
./bin/hyprwhspr setup
```

**openSUSE:**

```bash
# Install system dependencies
sudo zypper install python3 python3-pip python3-devel git cmake make gcc-c++ \
    python3-sounddevice python3-numpy python3-scipy python3-evdev \
    python3-pyperclip python3-requests python3-psutil python3-rich \
    python3-gobject typelib-1_0-Gtk-4_0 \
    pipewire pipewire-pulseaudio ydotool wl-clipboard

# Optional: For mic-osd visualizer (Tumbleweed only, from community repo)
# sudo zypper addrepo https://download.opensuse.org/repositories/devel:languages:zig/openSUSE_Tumbleweed/devel:languages:zig.repo
# sudo zypper refresh && sudo zypper install gtk4-layer-shell

# Clone and run setup
git clone https://github.com/goodroot/hyprwhspr.git ~/hyprwhspr
cd ~/hyprwhspr
./bin/hyprwhspr setup
```

</details>

**Post-installation (non-Arch distros):**

The setup wizard handles most configuration automatically:

- Creates `~/.local/bin/hyprwhspr` symlink (so the command works from anywhere)
- Configures systemd services
- Sets up permissions (groups, udev rules)

After setup completes:

```bash
# Log out and back in for group permissions to take effect
# Then verify everything is running:
hyprwhspr status
```

### CLI commands

After installation, use the `hyprwhspr` CLI to manage your installation:

- `hyprwhspr setup` - Interactive initial setup
  - `hyprwhspr setup --local-model --repo <org/repo>` - Configure local model from safetensors repo (recommended)
  - `hyprwhspr setup --local-gguf --local-path <file.gguf>` - Configure direct GGUF runtime model
  - `hyprwhspr setup auto` - Automated setup with optional parameters:
    - `--backend {nvidia,vulkan,cpu,onnx-asr}` - Specify backend (default: auto-detect GPU)
    - `--model MODEL` - Model to download (default: base for whisper, auto for onnx-asr)
    - `--no-waybar` - Skip waybar integration
    - `--no-mic-osd` - Disable mic-osd visualization
    - `--no-systemd` - Skip systemd service setup
    - `--hypr-bindings` - Enable Hyprland compositor bindings
- `hyprwhspr config` - Manage configuration (init/show/edit)
- `hyprwhspr waybar` - Manage Waybar integration (install/remove/status)
- `hyprwhspr mic-osd` - Manage microphone visualization overlay (enable/disable/status)
- `hyprwhspr systemd` - Manage systemd services (install/enable/disable/status/restart)
- `hyprwhspr model` - Manage models (download/list/status)
  - `hyprwhspr model download --repo <repo>` - Download safetensors repo snapshot to local cache
  - `hyprwhspr model download --repo <repo> --file <file.gguf>` - Download GGUF from HuggingFace
  - `hyprwhspr model list-local` - List cached GGUF models
  - `hyprwhspr model recommend` - Show GPU + quantization recommendation
  - `hyprwhspr model set MODEL_ID` - Switch active model for the current backend
  - `hyprwhspr model current` - Show active model for the current backend
- `hyprwhspr status` - Overall status check
- `hyprwhspr validate` - Validate installation
- `hyprwhspr test` - Test microphone and backend connectivity end-to-end
  - `--live` - Record live audio (3s) instead of using test.wav
  - `--mic-only` - Only test microphone, skip transcription
- `hyprwhspr keyboard` - Keyboard device management (list/test)
- `hyprwhspr backend` - Backend management (repair/reset)
  - `hyprwhspr backend server start|stop|status` - Manage local GGUF websocket server
  - `hyprwhspr backend add-profile NAME --url ... --model ...` - Save local realtime model profile
  - `hyprwhspr backend list-profiles` - List local realtime model profiles
  - `hyprwhspr backend use-profile NAME` - Activate a local realtime model profile
- `hyprwhspr state` - State management (show/validate/reset)
- `hyprwhspr uninstall` - Completely remove hyprwhspr and all data

## Documentation

For full configuration and customization, see the **[Configuration guide](docs/CONFIGURATION.md)**.

For implementation-level behavior guarantees, see **[Behavioral specification](docs/SPECIFICATION.md)**.

- [Minimal configuration](docs/CONFIGURATION.md#minimal-configuration)
- [Recording modes](docs/CONFIGURATION.md#recording-modes) -- toggle, push-to-talk, auto, long-form
- [Custom hotkeys](docs/CONFIGURATION.md#custom-hotkeys) -- key support, secondary shortcuts, Hyprland bindings
- [Transcription backends](docs/CONFIGURATION.md#transcription-backends) -- REST API, Realtime WebSocket
- [Models](docs/CONFIGURATION.md#models) -- Parakeet, Whisper
- [Audio and visual feedback](docs/CONFIGURATION.md#audio-and-visual-feedback) -- visualizer, audio feedback, ducking
- [Text processing](docs/CONFIGURATION.md#text-processing) -- word overrides, filler words, symbol replacements
- [Paste and clipboard behavior](docs/CONFIGURATION.md#paste-and-clipboard-behavior) -- paste mode, non-QWERTY, auto-submit
- [Integrations](docs/CONFIGURATION.md#integrations) -- Waybar, Hyprland bindings, external hotkey systems
- [Troubleshooting](docs/CONFIGURATION.md#troubleshooting)

## Getting help

1. **Check logs**: `journalctl --user -u hyprwhspr.service` `journalctl --user -u ydotool.service`
2. **Verify permissions**: Run the permissions fix script
3. **Test components**: Check ydotool, audio devices, whisper.cpp
4. **Report issues**: [Create an issue](https://github.com/goodroot/hyprwhspr/issues/new/choose) - logging info helpful!

## License

MIT License - see [LICENSE](LICENSE) file.

## Contributing

Create an issue, happy to help!  

For pull requests, also best to start with an issue.

---

**Built with ❤️ in 🇨🇦**
