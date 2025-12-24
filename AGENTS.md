# hyprwhspr Agent Developer Guide

This document provides guidance for developers and agents working with the hyprwhspr codebase.

## Project Overview

**hyprwhspr** is a voice dictation service for Hyprland that uses Whisper for speech-to-text and ydotool for text injection. It supports multiple transcription backends (local pywhispercpp, remote REST APIs like OpenAI/Groq, and Parakeet).

## Code Structure

```
hyprwhspr/
├── bin/
│   └── hyprwhspr              # Main entry point script
├── lib/
│   ├── main.py                # Application entry point (headless mode)
│   ├── cli.py                 # CLI command router
│   └── src/
│       ├── audio_capture.py   # Audio recording (sounddevice)
│       ├── audio_manager.py   # Audio feedback (beeps)
│       ├── backend_installer.py # Installation/setup
│       ├── cli_commands.py    # CLI implementation
│       ├── config_manager.py  # Configuration file handling
│       ├── credential_manager.py # Secure credential storage
│       ├── global_shortcuts.py # Hotkey binding
│       ├── instance_detection.py # Single instance management
│       ├── logger.py           # Logging utilities
│       ├── media_controller.py # Media player pause/resume
│       ├── output_control.py  # Output/formatting
│       ├── provider_registry.py # REST API provider configs
│       ├── text_injector.py   # Text input (ydotool)
│       └── whisper_manager.py # Transcription backend
├── config/
│   ├── hyprland/hyprwhspr-tray.sh # Tray/Waybar integration
│   ├── systemd/hyprwhspr.service
│   ├── systemd/parakeet-*.service
│   └── waybar/                # Waybar configuration
├── share/assets/              # Sound effects
├── DEBUGGING.md               # Debugging guide
└── README.md                  # User documentation

```

## Key Modules and Responsibilities

### Audio Pipeline

1. **audio_capture.py** - Records audio using sounddevice at 16kHz mono
   - Uses threading for non-blocking recording
   - Supports device selection and audio level monitoring
   - Thread-safe with locks

2. **audio_manager.py** - Plays audio feedback
   - Uses ffplay (with fallback to aplay/paplay)
   - Handles audio file resolution
   - Plays start/stop sounds

3. **whisper_manager.py** - Handles transcription
   - Supports multiple backends: local pywhispercpp, REST APIs, Parakeet
   - Model management and downloading

4. **text_injector.py** - Injects transcribed text
   - Uses ydotool for input
   - Handles special characters and formatting

### System Integration

1. **global_shortcuts.py** - Hotkey binding (uinput/evdev)
   - Toggle vs push-to-talk modes
   - Requires /dev/input and /dev/uinput access

2. **media_controller.py** - Pause/resume media during recording
   - Integrates with MPRIS for player control

3. **instance_detection.py** - Ensures single instance
   - Lock file mechanism
   - systemd detection

### Configuration and Setup

1. **config_manager.py** - JSON configuration
   - Default config locations: `~/.config/hyprwhspr/config.json`
   - Settings include: backend, model, hotkey, audio preferences

2. **credential_manager.py** - Secure credential storage
   - Uses keyring or encrypted file storage
   - For REST API keys (OpenAI, Groq, etc.)

3. **backend_installer.py** - Installation and setup
   - Creates Python venv
   - Installs pywhispercpp or Parakeet
   - Manages dependencies

### CLI and Output

1. **cli_commands.py** - All CLI functionality
   - `setup` - Initial configuration wizard
   - `config` - Configuration management
   - `systemd` - Service management
   - `model` - Whisper model management
   - `waybar` - Waybar integration
   - `validate` - Installation validation
   - `backend repair` - Repair corrupted installation
   - `state` - State file management

2. **output_control.py** - Unified output formatting
   - Verbosity levels (quiet, normal, verbose, debug)
   - Log file support
   - Progress indicators

## Error Handling Standards

### Key Principles

1. **All errors must be handled** - No bare `except:`
2. **Specific exception types** - Use `except FileNotFoundError:` not `except Exception:`
3. **Informative messages** - Include context and actionable steps
4. **Logging** - Use logger module for errors/warnings

### Error Handling Pattern

```python
try:
    # Operation
    result = risky_operation()
except FileNotFoundError as e:
    log_error(f"Config file not found: {e}")
    return False
except Exception as e:
    log_error(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    return False
```

## Debugging Common Issues

### "pipewire is down" After Recording

**Root Cause:** Audio playback (ffplay) timing out connecting to PipeWire
- Check: `systemctl --user status pipewire`
- Check: `journalctl --user -u pipewire --since "5 minutes ago"`
- Fix: `systemctl --user restart pipewire`

See [DEBUGGING.md](./DEBUGGING.md) for full troubleshooting guide.

### Service Won't Start

**Check:**
```bash
systemctl --user status hyprwhspr  # Status
journalctl --user -u hyprwhspr -n 50  # Logs
hyprwhspr validate  # Validation
```

**Common Causes:**
- Missing permissions (input group)
- Python venv corrupted
- Missing ydotool service
- Audio device unavailable

**Fix:**
```bash
hyprwhspr setup  # Re-run setup
hyprwhspr backend repair  # Repair installation
```

### High CPU Usage

**Check:**
- Model size: `ls -lh ~/.local/share/pywhispercpp/models/`
- CPU usage: `top -p $(pgrep -f hyprwhspr)`

**Solutions:**
- Use smaller model: `hyprwhspr model download tiny.en`
- Use GPU: `hyprwhspr setup` and select NVIDIA/AMD
- Switch to REST API: Use cloud provider

## Testing

### Unit Testing

```bash
# Test individual components
python -c "
from lib.src.audio_capture import AudioCapture
ac = AudioCapture()
print('Audio capture available:', ac.is_available())
"

python -c "
from lib.src.whisper_manager import WhisperManager
wm = WhisperManager()
print('Whisper initialized:', wm.initialize())
"
```

### Integration Testing

```bash
# Full service test
systemctl --user restart hyprwhspr
journalctl --user -u hyprwhspr -f

# In another terminal, test hotkey
# Press hotkey to start recording, check logs
```

### Manual Testing

```bash
# Run directly without systemd
python /path/to/lib/main.py

# Test recording
python -c "
from lib.src.audio_capture import AudioCapture
ac = AudioCapture()
ac.start_recording()
import time; time.sleep(3)  # Record for 3 seconds
audio = ac.stop_recording()
print(f'Recorded {len(audio)} samples')
"
```

## Logging and Debugging

### Log Locations

| Type | Location |
|------|----------|
| Systemd | `journalctl --user -u hyprwhspr` |
| Manual run | Terminal stdout/stderr |
| PipeWire | `journalctl --user -u pipewire` |
| Config | `~/.config/hyprwhspr/config.json` |

### Increasing Verbosity

```bash
# CLI commands
hyprwhspr --verbose setup
hyprwhspr --debug validate

# Manual execution
python -u /path/to/lib/main.py  # Unbuffered output
```

### Useful Debug Commands

```bash
# Check all audio devices
pw-record --list-targets

# Monitor audio in real-time
pw-mon

# Check PipeWire status
pw-cli info

# List running processes
pgrep -a hyprwhspr

# Check service dependencies
systemctl --user list-dependencies hyprwhspr
```

## Development Workflow

### Making Changes

1. **Identify the module** - Use `grep` to find where error occurs
2. **Add logging** - Use `log_error()`, `log_warning()`, `log_info()`
3. **Test locally** - Run systemd service or manual execution
4. **Check logs** - Review journalctl output
5. **Fix the issue** - Make changes with proper error handling

### Code Quality

- **Type annotations** - All function parameters and returns
- **Docstrings** - Module and function documentation
- **Error handling** - Specific exceptions, informative messages
- **Logging** - All significant operations and errors
- **Testing** - Manual testing before deploying

### Configuration Changes

Edit `~/.config/hyprwhspr/config.json`:

```bash
# View current config
hyprwhspr config show

# Edit config
nano ~/.config/hyprwhspr/config.json

# Validate config
hyprwhspr validate

# Restart to apply
systemctl --user restart hyprwhspr
```

## Common Tasks

### Add a New Audio Device

1. List available devices: `pw-record --list-targets`
2. Edit config: `nano ~/.config/hyprwhspr/config.json`
3. Set `"audio_device": <device_id>`
4. Restart: `systemctl --user restart hyprwhspr`

### Add a New REST API Provider

1. Edit `lib/src/provider_registry.py`
2. Add provider configuration
3. Test: `hyprwhspr setup` and select provider
4. Verify: Check logs in `journalctl --user -u hyprwhspr`

### Improve Error Messages

1. Find error location with `grep -r "ErrorMessage"`
2. Add context and fix suggestion
3. Use `log_error()` with formatted message
4. Test: Run and trigger the error

### Debug Audio Issues

1. Check PipeWire: `systemctl --user status pipewire`
2. Test audio: `ffplay /usr/share/sounds/freedesktop/stereo/complete.oga`
3. Check logs: `journalctl --user -u pipewire -n 50`
4. Restart: `systemctl --user restart pipewire`
5. Check hyprwhspr logs: `journalctl --user -u hyprwhspr -n 50`

## Performance Optimization

### Critical Sections

- **Audio callback** (`audio_capture.py:_record_audio`) - Must be fast
- **Text injection** (`text_injector.py:inject_text`) - Low latency required
- **Transcription** (`whisper_manager.py:transcribe_audio`) - Can be slower (background task)

### Optimization Tips

1. Use smaller models for faster transcription
2. Use GPU acceleration when available
3. Cache results when possible
4. Minimize I/O in hot paths
5. Use threading for long operations

## Dependencies

### Core Dependencies
- **sounddevice** - Audio capture
- **numpy** - Audio processing
- **pyaudio** (fallback) - ALSA audio backend
- **ydotool** - Text injection (external tool)
- **rich** - CLI formatting

### Optional Dependencies
- **pywhispercpp** - Local transcription (optional)
- **torch** - GPU acceleration (optional)
- **requests** - REST API calls (built-in)

### System Dependencies
- **ydotool** - Text input
- **ffplay** or **aplay** - Audio playback
- **Python 3.8+** - Runtime

## Architecture Decisions

### Why Sounddevice?

- Cross-platform audio capture
- Hardware-level access
- Callback-based recording
- Low-latency monitoring

### Why ydotool?

- Works with Wayland (unlike xdotool)
- No root required (with permissions)
- Reliable text injection

### Why systemd User Service?

- Starts automatically on login
- Survives logout
- Better logging with journalctl
- Integrated with system

### Why Multiple Backends?

- **Local (pywhispercpp)** - Fast, no latency, no internet required
- **REST API** - Flexible, supports cloud providers
- **Parakeet** - Latest NVIDIA model, local REST server

## Contact and Support

For issues:
1. Check [DEBUGGING.md](./DEBUGGING.md)
2. Review logs: `journalctl --user -u hyprwhspr`
3. Run validation: `hyprwhspr validate`
4. Try repair: `hyprwhspr backend repair`
5. Review code comments

## Additional Resources

- [README.md](./README.md) - User guide
- [DEBUGGING.md](./DEBUGGING.md) - Troubleshooting
- [Whisper Documentation](https://github.com/openai/whisper)
- [PipeWire Documentation](https://pipewire.org/)
- [Hyprland Documentation](https://wiki.hyprland.org/)
