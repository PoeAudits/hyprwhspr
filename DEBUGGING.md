# hyprwhspr Debugging Guide

This document explains how to locate logs, diagnose issues, and fix common problems with hyprwhspr.

## Log Locations

### System Logs (Journalctl)

If running via systemd, logs are available in the systemd journal:

```bash
# View recent logs (last 50 lines)
journalctl --user -u hyprwhspr -n 50

# Follow logs in real-time
journalctl --user -u hyprwhspr -f

# View logs with timestamps and full output
journalctl --user -u hyprwhspr -o short-full

# View only errors
journalctl --user -u hyprwhspr -p err

# View logs from the last 2 hours
journalctl --user -u hyprwhspr --since "2 hours ago"
```

### Application Output (Manual Execution)

When running hyprwhspr manually (not via systemd), you can see output directly in your terminal:

```bash
# Run hyprwhspr with full output
hyprwhspr

# Or directly with Python
python /path/to/lib/main.py
```

### PipeWire Logs

Since audio-related issues are common, check PipeWire status:

```bash
# Check PipeWire service status
systemctl --user status pipewire

# View PipeWire logs
journalctl --user -u pipewire -n 50

# Check PipeWire daemon is running
pw-cli info | grep -i "pipewire"
```

### Audio Device Logs

Check audio device availability:

```bash
# List available audio devices
pacmd list-sources 2>/dev/null || pactl list sources

# Check default audio source
pactl get-default-source

# Check PulseAudio/PipeWire status
pactl info
```

## Common Issues and Solutions

### "pipewire is down" or Audio Playback Timeouts

**Symptoms:**
- Error: `subprocess.TimeoutExpired: Command '['ffplay', ...]' timed out after 10 seconds`
- "pipewire is down" message after recording
- Audio feedback sounds not playing

**Root Causes:**
1. PipeWire is not running or not responding
2. PipeWire connection lost (I/O error)
3. Audio device unavailable or misconfigured
4. ffplay cannot connect to audio server
5. WAYLAND_DISPLAY or XDG_RUNTIME_DIR incorrect

**Diagnostic Steps:**

```bash
# 1. Check if PipeWire is running
systemctl --user status pipewire

# 2. Check for PipeWire errors
journalctl --user -u pipewire --since "5 minutes ago" -p err

# 3. Check hyprwhspr logs
journalctl --user -u hyprwhspr --since "5 minutes ago" | grep -i "error\|timeout\|exception"

# 4. Test audio playback manually
ffplay /usr/share/sounds/freedesktop/stereo/complete.oga

# 5. Check PipeWire socket exists
ls -la /run/user/$UID/pipewire-0

# 6. Verify audio device is available
pw-record --list-targets

# 7. Check environment variables
echo "WAYLAND_DISPLAY=$WAYLAND_DISPLAY"
echo "XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR"
```

**Solutions:**

1. **Restart PipeWire:**
```bash
systemctl --user restart pipewire
systemctl --user restart pipewire-pulse  # If using PulseAudio bridge
```

2. **Kill stale ffplay processes:**
```bash
pkill -f ffplay
```

3. **Reload systemd and restart hyprwhspr:**
```bash
systemctl --user daemon-reload
systemctl --user restart hyprwhspr
```

4. **Disable audio feedback if audio is problematic:**
```bash
# Edit config manually
nano ~/.config/hyprwhspr/config.json

# Set "audio_feedback": false
```

5. **Use alternative audio player (aplay instead of ffplay):**
```bash
# Install alsa-utils if not present
sudo pacman -S alsa-utils

# Test with aplay
aplay /usr/share/sounds/freedesktop/stereo/complete.oga
```

### hyprwhspr Not Starting

**Symptoms:**
- Service fails to start via systemd
- `systemctl --user status hyprwhspr` shows failed state

**Diagnostic Steps:**

```bash
# 1. Check service status and error
systemctl --user status hyprwhspr

# 2. View full error logs
journalctl --user -u hyprwhspr -n 100

# 3. Check if Python venv exists
ls -la ~/.local/share/hyprwhspr/venv/bin/python

# 4. Try running manually to see full error
python ~/.local/share/hyprwhspr/venv/bin/python /path/to/lib/main.py

# 5. Check permissions
ls -la /dev/uinput
groups $USER  # Check if in 'input' group
```

**Solutions:**

1. **Fix permissions:**
```bash
hyprwhspr setup  # Re-run setup to fix permissions
```

2. **Repair backend installation:**
```bash
hyprwhspr backend repair
```

3. **Reset installation state:**
```bash
hyprwhspr state reset
```

4. **Check if already running:**
```bash
# Multiple instances can conflict
pgrep -a hyprwhspr

# Kill existing instances
pkill hyprwhspr

# Try starting again
systemctl --user start hyprwhspr
```

### Audio Recording Issues

**Symptoms:**
- No audio captured during recording
- Very short recordings (< 0.5 seconds)
- Audio device errors

**Diagnostic Steps:**

```bash
# 1. Check audio device setup
pw-record --list-targets

# 2. Record a test file
pw-record test.wav

# 3. Check recorded audio
file test.wav
```

**Solutions:**

1. **Configure specific audio device:**
```bash
# List devices
hyprwhspr config show | grep audio_device

# Set device (replace X with device ID)
# Edit ~/.config/hyprwhspr/config.json and set "audio_device": X
```

2. **Check audio capture permissions:**
```bash
# User must be in 'audio' group
groups $USER | grep audio

# If missing, re-run setup
hyprwhspr setup
```

### Text Injection Not Working

**Symptoms:**
- Text is not being typed/pasted into applications
- Transcription completes but no output

**Diagnostic Steps:**

```bash
# 1. Check ydotool service
systemctl --user status ydotool

# 2. Verify permissions
ls -la /dev/uinput

# 3. Check if user is in input group
groups $USER | grep input
```

**Solutions:**

1. **Restart ydotool:**
```bash
systemctl --user restart ydotool
```

2. **Fix permissions:**
```bash
hyprwhspr setup
```

3. **Log out and back in** for group changes to take effect

### High CPU Usage / Performance Issues

**Symptoms:**
- hyprwhspr consuming 100% CPU
- Transcription taking too long
- System feels sluggish

**Diagnostic Steps:**

```bash
# 1. Check CPU usage
top -p $(pgrep -f "hyprwhspr.*main.py")

# 2. Check if using correct backend
hyprwhspr config show | grep transcription_backend

# 3. Check model size
ls -lh ~/.local/share/pywhispercpp/models/

# 4. Monitor resources during recording
watch -n 1 'ps aux | grep hyprwhspr'
```

**Solutions:**

1. **Use a smaller model:**
```bash
# List available models
hyprwhspr model list

# Download smaller model
hyprwhspr model download tiny.en
```

2. **Use GPU acceleration:**
```bash
hyprwhspr setup  # Select NVIDIA or AMD backend
```

3. **Restart service:**
```bash
systemctl --user restart hyprwhspr
```

## Debugging Techniques

### Increase Verbosity

Run with verbose logging:

```bash
# For CLI commands
hyprwhspr --verbose status
hyprwhspr --debug setup

# Manual execution
python -u /path/to/lib/main.py  # Unbuffered output
```

### Monitor Systemd Service

```bash
# Watch service logs in real-time
journalctl --user -u hyprwhspr -f

# In another terminal, test the service
systemctl --user restart hyprwhspr
```

### Check Environment Variables

```bash
# View environment for running process
cat /proc/$(pgrep -f hyprwhspr)/environ | tr '\0' '\n'

# View system audio environment
echo "PULSE_RUNTIME_PATH=$PULSE_RUNTIME_PATH"
echo "PIPEWIRE_REMOTE=$PIPEWIRE_REMOTE"
```

### Test Individual Components

```bash
# Test audio capture
python -c "
from lib.src.audio_capture import AudioCapture
ac = AudioCapture()
print('Available:', ac.is_available())
print('Devices:', ac.get_available_input_devices())
"

# Test Whisper
python -c "
from lib.src.whisper_manager import WhisperManager
wm = WhisperManager()
print('Initialized:', wm.initialize())
"

# Test text injection
python -c "
from lib.src.text_injector import TextInjector
ti = TextInjector(None)
ti.inject_text('test')
"
```

## Useful Commands

### Service Management

```bash
# View service logs
journalctl --user -u hyprwhspr

# Check service status
systemctl --user status hyprwhspr

# Restart service
systemctl --user restart hyprwhspr

# Start/stop service
systemctl --user start hyprwhspr
systemctl --user stop hyprwhspr

# Enable/disable on boot
systemctl --user enable hyprwhspr
systemctl --user disable hyprwhspr
```

### Configuration Management

```bash
# View current config
hyprwhspr config show

# Edit config
hyprwhspr config edit

# Reset to defaults
hyprwhspr config init
```

### Validation and Repair

```bash
# Full validation
hyprwhspr validate

# Repair installation
hyprwhspr backend repair

# Reset state file
hyprwhspr state reset

# Check state
hyprwhspr state show
```

### Audio Device Management

```bash
# List available input devices
pw-record --list-targets

# Record test audio
pw-record test.wav && pw-play test.wav

# Check audio levels
pw-mon
```

## Getting Help

If you encounter issues:

1. **Collect logs:**
   ```bash
   journalctl --user -u hyprwhspr > /tmp/hyprwhspr-logs.txt
   journalctl --user -u pipewire >> /tmp/hyprwhspr-logs.txt
   ```

2. **Run validation:**
   ```bash
   hyprwhspr validate 2>&1 | tee /tmp/hyprwhspr-validation.txt
   ```

3. **Check system info:**
   ```bash
   uname -a
   systemctl --user list-units | grep hyprwhspr
   pw-cli info
   ```

4. **Report with context:**
   - Include log files from above
   - Describe what you were doing when the issue occurred
   - Include output of `hyprwhspr status` and `hyprwhspr validate`
   - Include relevant system information

## Configuration File Location

- **User Config:** `~/.config/hyprwhspr/config.json`
- **System Config:** `/usr/lib/hyprwhspr/lib/src/config_manager.py` (defaults)
- **Service Files:** `~/.config/systemd/user/hyprwhspr.service`
- **Waybar Config:** `~/.config/waybar/config.jsonc`

## File Structure

```
~/.local/share/hyprwhspr/
├── venv/                    # Python virtual environment (backend)
├── models/                  # Downloaded Whisper models
└── state.json               # Installation state tracking

~/.config/hyprwhspr/
├── config.json              # User configuration
├── recording_status         # Recording status file (temp)
├── audio_level              # Audio level file (temp)
└── hyprwhspr.lock          # Instance lock file (temp)
```
