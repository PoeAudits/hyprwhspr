# Media Pause/Resume on Dictation Implementation Plan

## Overview

Implement automatic media player pause/resume during dictation to prevent background music/audio from interfering with speech-to-text accuracy. When a user initiates dictation, active media players (Spotify, YouTube, VLC, etc.) will automatically pause. After transcription and text injection complete, previously-playing players resume automatically. This feature operates independently from the core dictation logic and is disabled by default via configuration.

## Current State Analysis

### What Exists Now
- Functional dictation pipeline: hotkey trigger → audio capture → transcription → text injection
- Configuration system via `config_manager.py` supporting boolean feature toggles
- Error handling patterns that gracefully degrade on external tool failures
- State tracking via boolean flags (`is_recording`, `is_processing`) with guard checks
- Subprocess-based external tool execution (ffplay, ydotool, paplay) with timeouts and error handling
- Centralized logging via `logger.py` with functions like `log_debug()`, `log_error()`, `log_warning()`

### What's Missing
- No media player control or pause/resume functionality
- No playerctl integration or MPRIS support
- No configuration option for media pause on dictation

### Key Constraints
- Must not affect audio_level file output during recording
- Must not affect recording_status file behavior
- All failures must be silent (no crashes or disruptions to dictation)
- Must support both toggle and push-to-talk hotkey modes
- Must handle player exits gracefully without restart attempts

## Desired End State

### Success Criteria

After implementation, the feature will:

1. **Functional Behavior**:
   - Pause all currently playing media players when dictation hotkey is activated
   - Track which specific players were paused by the system
   - Resume only those tracked players after text injection completes
   - Handle player exits/closures gracefully (no crash, no restart attempts)
   - Work correctly in both toggle and push-to-talk modes

2. **Configuration**:
   - Feature is disabled by default: `media_pause_on_dictation: false`
   - Users can enable via configuration: `media_pause_on_dictation: true`
   - Feature can be toggled without application restart

3. **Robustness**:
   - All media control operations silently handle failures
   - Dictation continues normally if media control unavailable
   - Application remains stable regardless of playerctl availability
   - Missing players during resume are skipped without error

4. **Integration**:
   - Minimal integration points in main.py (two method calls)
   - No interaction with transcription or text injection logic
   - No impact on existing audio feedback or level monitoring
   - Pause happens before audio capture starts (prevents audio capture)
   - Resume happens after text injection completes (ensures feedback latency)

### Verification Steps

1. Start Spotify, trigger dictation hotkey → Spotify pauses immediately
2. Speak into microphone, complete dictation (release hotkey or press again)
3. Verify Spotify resumes automatically after text is injected
4. Start multiple players (Spotify + YouTube), verify both pause and both resume
5. Disable feature in config, trigger dictation with music playing → music continues uninterrupted
6. Close a player while dictation in progress → application doesn't crash, remaining players resume

## Key Discoveries from Code Investigation

### Integration Point 1: `_start_recording()` - lib/main.py:106-129
```python
# Current flow:
_start_recording():
    is_recording = True
    write_recording_status(True)
    audio_manager.play_start_sound()           # Line 118
    audio_capture.start_recording()            # Line 121 ← PAUSE POINT AFTER THIS
    _start_audio_level_monitoring()            # Line 124
```
**Pause should be called after audio_capture.start_recording() and before returning**

### Integration Point 2: `_process_audio()` - lib/main.py:159-181
```python
# Current flow:
_process_audio(audio_data):
    is_processing = True
    transcription = whisper_manager.transcribe_audio(audio_data)  # Line 168
    _inject_text(transcription)                # Line 174 ← RESUME POINT AFTER THIS
    is_processing = False
```
**Resume should be called after _inject_text() completes, within try-except that already exists**

### Subprocess Execution Pattern - lib/src/audio_manager.py:170-195
The codebase uses this pattern for external tool execution:
```python
def _play_with_ffplay(self, sound_file: Path, volume: float) -> bool:
    try:
        cmd = ['ffplay', '-nodisp', '-autoexit', ...]
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True
    except Exception as e:
        print(f"ffplay failed: {e}")
        return False
```
**Pattern: Try execution, catch all exceptions, return boolean success/failure, no re-raise**

### Configuration Pattern - lib/src/config_manager.py:16-40
All settings stored in `default_config` dict:
```python
self.default_config = {
    'primary_shortcut': 'SUPER+ALT+D',
    'push_to_talk': False,
    # ... other settings ...
}
```
**Pattern: Add new boolean setting to dict with default value and comment**

### State Tracking Pattern - lib/main.py:48-52
```python
self.is_recording = False
self.is_processing = False
self.current_transcription = ""
```
**Pattern: Store state as instance variable, check before operations, reset in error handlers**

### Error Handling Pattern - lib/src/text_injector.py:76-114
```python
def inject_text(self, text: str) -> bool:
    if not text or text.strip() == "":
        return True  # Not an error
    
    try:
        success = False
        if self.ydotool_available:
            success = self._inject_via_clipboard_and_hotkey(text)
        else:
            success = self._inject_via_clipboard(text)
        return success
    except Exception as e:
        print(f"Primary injection method failed: {e}")
        return False
```
**Pattern: Validate inputs, try operation, return boolean, catch exceptions without re-raise**

### Logging Pattern - lib/src/backend_installer.py
The codebase uses centralized logging from `logger.py`:
- `log_debug(message)` - Debug level (for troubleshooting)
- `log_warning(message)` - Warning level (degraded functionality)
- `log_error(message)` - Error level (significant failures)
- `print(f"message")` - For silent console output in error handlers

**Pattern: Use log_debug() for operational details, silent print() for errors in catch blocks**

## Implementation Approach

### Architecture Decision: Separate Module
Create a new `MediaController` class in `lib/src/media_controller.py` to keep media control logic independent from main application flow. This follows the pattern of `AudioManager`, `TextInjector`, etc. where each concern has its own module.

### Key Design Principles
1. **Graceful Degradation**: If playerctl unavailable or fails, dictation continues normally
2. **Silent Operation**: No user notifications, errors, or status messages (resumed media serves as confirmation)
3. **State Independence**: Pause and resume operations are independent (resume happens even if pause failed)
4. **Player Independence**: Missing players during resume are silently skipped
5. **Synchronous Execution**: Pause/resume happen synchronously in main thread (no additional threading)

### Subprocess Strategy
Use `playerctl` via subprocess.run() with:
- Command-line list format (not shell=True) for safety
- 5-second timeout to prevent hanging
- `capture_output=True` to suppress console output
- Boolean return value for success/failure
- Silent exception handling (log at debug level only)

## Phase 1: Foundation - MediaController Module & Configuration

### Overview
Create the core MediaController class and add configuration support. This phase is self-contained and testable in isolation.

### Changes Required

#### 1. Create lib/src/media_controller.py

**File**: `lib/src/media_controller.py`

**Contents**:
```python
"""
Media controller for managing player pause/resume during dictation
"""

import subprocess
from typing import List, Optional


class MediaController:
    """Controls media player pause/resume via playerctl/MPRIS"""
    
    def __init__(self, config_manager=None):
        """
        Initialize media controller
        
        Args:
            config_manager: ConfigManager instance for accessing settings
        """
        self.config_manager = config_manager
        
        # Load configuration
        if self.config_manager:
            self.enabled = self.config_manager.get_setting('media_pause_on_dictation', False)
        else:
            self.enabled = False
        
        # Track which players were paused
        self.paused_players: List[str] = []
        
        # Check if playerctl is available
        self.playerctl_available = self._check_playerctl_available()
    
    def _check_playerctl_available(self) -> bool:
        """Check if playerctl command is available on the system"""
        try:
            result = subprocess.run(
                ['which', 'playerctl'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _execute_playerctl(self, args: List[str]) -> bool:
        """
        Execute a playerctl command safely
        
        Args:
            args: List of arguments to pass to playerctl (e.g., ['pause'] or ['play', '-p', 'spotify'])
        
        Returns:
            True if command succeeded, False otherwise
        """
        try:
            cmd = ['playerctl'] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=5,
                check=False
            )
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
    
    def _get_active_players(self) -> List[str]:
        """
        Get list of currently playing media players
        
        Returns:
            List of player names that are currently playing
        """
        try:
            result = subprocess.run(
                ['playerctl', '--list-all'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )
            
            if result.returncode != 0:
                return []
            
            # Get list of all players
            all_players = result.stdout.strip().split('\n')
            all_players = [p.strip() for p in all_players if p.strip()]
            
            # Check which players are currently playing (status = "Playing")
            playing_players = []
            for player in all_players:
                try:
                    status_result = subprocess.run(
                        ['playerctl', '-p', player, 'status'],
                        capture_output=True,
                        text=True,
                        timeout=2,
                        check=False
                    )
                    if status_result.returncode == 0:
                        status = status_result.stdout.strip()
                        if status == 'Playing':
                            playing_players.append(player)
                except Exception:
                    continue
            
            return playing_players
        except Exception:
            return []
    
    def pause_active_players(self) -> bool:
        """
        Pause all currently playing media players
        
        Tracks which players were paused so they can be resumed later.
        
        Returns:
            True if at least one player was paused, False if none were playing
        """
        if not self.enabled or not self.playerctl_available:
            self.paused_players = []
            return False
        
        try:
            # Get list of currently playing players
            self.paused_players = self._get_active_players()
            
            if not self.paused_players:
                return False
            
            # Pause all playing players
            for player in self.paused_players:
                self._execute_playerctl(['-p', player, 'pause'])
            
            return True
        except Exception:
            self.paused_players = []
            return False
    
    def resume_paused_players(self) -> bool:
        """
        Resume media players that were paused during dictation
        
        Only resumes players that were tracked as paused, ignoring any
        players that may have exited during dictation.
        
        Returns:
            True if at least one player was resumed, False otherwise
        """
        if not self.enabled:
            self.paused_players = []
            return False
        
        if not self.paused_players:
            return False
        
        try:
            resumed_count = 0
            for player in self.paused_players:
                # Try to resume each player; skip if it no longer exists
                if self._execute_playerctl(['-p', player, 'play']):
                    resumed_count += 1
            
            # Clear the paused players list regardless of resume success
            self.paused_players = []
            
            return resumed_count > 0
        except Exception:
            self.paused_players = []
            return False
    
    def is_enabled(self) -> bool:
        """Check if media pause feature is enabled"""
        return self.enabled
```

**Key Details**:
- `_check_playerctl_available()` uses `which playerctl` to verify tool availability
- `_execute_playerctl()` wraps playerctl execution with timeout (5s) and error handling
- `_get_active_players()` queries playerctl to find currently playing players
- `pause_active_players()` tracks which players were paused for later resume
- `resume_paused_players()` only resumes tracked players (missing ones are skipped)
- All methods handle exceptions silently and return boolean success/failure
- State is stored in `self.paused_players` list

#### 2. Update lib/src/config_manager.py

**File**: `lib/src/config_manager.py`
**Line**: Around line 16-40 in `default_config` dictionary

Add this entry to the `default_config` dict (in alphabetical order or with other boolean toggles):

```python
'media_pause_on_dictation': False,  # Automatically pause media players during dictation
```

**Location in context**:
```python
self.default_config = {
    'primary_shortcut': 'SUPER+ALT+D',
    'push_to_talk': False,
    'model': 'base',
    'threads': 4,
    'language': None,
    'word_overrides': {},
    'whisper_prompt': 'Transcribe with proper capitalization...',
    'clipboard_behavior': False,
    'clipboard_clear_delay': 5.0,
    'paste_mode': 'ctrl_shift',
    'shift_paste': True,
    'transcription_backend': 'pywhispercpp',
    'rest_endpoint_url': None,
    'rest_api_provider': None,
    'rest_api_key': None,
    'rest_headers': {},
    'rest_body': {},
    'rest_timeout': 30,
    'rest_audio_format': 'wav',
    'media_pause_on_dictation': False,  # ← ADD THIS LINE
}
```

### Success Criteria - Phase 1

#### Verification Steps:
1. [x] MediaController class can be imported without errors
2. [x] MediaController initializes with config_manager instance
3. [x] `_check_playerctl_available()` returns True/False correctly based on system
4. [x] `is_enabled()` returns False by default (disabled feature)
5. [x] Config has `media_pause_on_dictation` key with default value of False
6. [x] Config can be updated: `config.set_setting('media_pause_on_dictation', True)`

---

## Phase 2: Integration - Hotkey Lifecycle Hooks

### Overview
Integrate MediaController into the main application lifecycle. Minimal changes to existing code (just two method calls).

### Changes Required

#### 1. Update lib/main.py - Initialize MediaController

**File**: `lib/main.py`
**Location**: In `__init__` method of `hyprwhsprApp` class (around line 33-46)

After existing component initialization, add:

```python
# Initialize media controller for pause/resume during dictation
self.media_controller = MediaController(self.config)
```

**Full context** (lib/main.py:33-46):
```python
def __init__(self):
    # Initialize core components
    self.config = ConfigManager()

    # Initialize audio capture with configured device
    audio_device_id = self.config.get_setting('audio_device', None)
    self.audio_capture = AudioCapture(device_id=audio_device_id)

    # Initialize audio feedback manager
    self.audio_manager = AudioManager(self.config)

    self.whisper_manager = WhisperManager()
    self.text_injector = TextInjector(self.config)
    self.media_controller = MediaController(self.config)  # ← ADD THIS LINE
    self.global_shortcuts = None

    # Application state
    self.is_recording = False
    self.is_processing = False
    # ... rest of __init__ ...
```

**Also add import** at top of lib/main.py (around line 23-28):
```python
from media_controller import MediaController
```

#### 2. Update lib/main.py - Pause on Recording Start

**File**: `lib/main.py`
**Location**: In `_start_recording()` method (around line 106-129)

After `audio_capture.start_recording()` call, add pause call:

```python
# Pause active media players if feature enabled
if self.media_controller.is_enabled():
    self.media_controller.pause_active_players()
```

**Full context** (lib/main.py:106-129):
```python
def _start_recording(self):
    """Start voice recording"""
    if self.is_recording:
        return

    try:
        self.is_recording = True
        
        # Write recording status to file for tray script
        self._write_recording_status(True)
        
        # Play start sound
        self.audio_manager.play_start_sound()
        
        # Start audio capture
        self.audio_capture.start_recording()
        
        # Pause active media players if feature enabled
        if self.media_controller.is_enabled():
            self.media_controller.pause_active_players()  # ← ADD THESE LINES
        
        # Start audio level monitoring thread
        self._start_audio_level_monitoring()
        
    except Exception as e:
        print(f"[ERROR] Failed to start recording: {e}")
        self.is_recording = False
        self._write_recording_status(False)
```

**Timing rationale**: Pause happens AFTER audio capture starts, ensuring system is ready before pausing media (prevents race conditions).

#### 3. Update lib/main.py - Resume After Text Injection

**File**: `lib/main.py`
**Location**: In `_process_audio()` method (around line 159-181)

After `_inject_text(transcription)` call, add resume call:

```python
# Resume previously-playing media players
if self.media_controller.is_enabled():
    self.media_controller.resume_paused_players()
```

**Full context** (lib/main.py:159-181):
```python
def _process_audio(self, audio_data):
    """Process recorded audio: transcribe and inject"""
    if self.is_processing:
        return

    try:
        self.is_processing = True
        
        # Transcribe audio
        transcription = self.whisper_manager.transcribe_audio(audio_data)
        
        # Only proceed if transcription succeeded
        if transcription:
            # Store result
            self.current_transcription = transcription
            
            # Inject transcribed text into active application
            self._inject_text(transcription)
            
            # Resume previously-playing media players
            if self.media_controller.is_enabled():
                self.media_controller.resume_paused_players()  # ← ADD THESE LINES
        
    except Exception as e:
        print(f"[ERROR] Error processing audio: {e}")
    finally:
        self.is_processing = False
```

**Timing rationale**: Resume happens AFTER text injection completes, ensuring all dictation output is done before resuming media. This minimizes any interference between injection and resumed audio.

### Success Criteria - Phase 2

#### Verification Steps:
1. [x] Application starts without errors (MediaController import works)
2. [x] MediaController is initialized in app constructor
3. [x] Feature toggle works: `config.set_setting('media_pause_on_dictation', False)` disables the feature
4. [x] Feature toggle works: `config.set_setting('media_pause_on_dictation', True)` enables the feature
5. [x] Pause/resume calls are only made when feature is enabled
6. [x] Integration points don't cause any syntax or runtime errors

---

## Related Implementation Notes

### Manual Testing Verification (Post-Implementation)

After Phase 2 is complete, perform manual testing to verify:

1. **Basic Pause/Resume**:
   - [ ] Start Spotify playback
   - [ ] Enable `media_pause_on_dictation` in config
   - [ ] Trigger dictation hotkey
   - [ ] Verify Spotify pauses immediately
   - [ ] Complete dictation (release hotkey or press again)
   - [ ] Verify Spotify resumes automatically after text is injected

2. **State Preservation**:
   - [ ] Manually pause Spotify
   - [ ] Start dictation (Spotify should remain paused)
   - [ ] Complete dictation
   - [ ] Verify Spotify remains paused (wasn't resumed because it wasn't playing)

3. **Multi-Player Support**:
   - [ ] Start Spotify playback
   - [ ] Open YouTube video and start playback (in browser)
   - [ ] Enable `media_pause_on_dictation`
   - [ ] Trigger dictation hotkey
   - [ ] Verify both Spotify and YouTube pause
   - [ ] Complete dictation
   - [ ] Verify both resume

4. **Player Exit Handling**:
   - [ ] Start Spotify playback
   - [ ] Trigger dictation hotkey (Spotify pauses)
   - [ ] Close Spotify while dictation in progress
   - [ ] Complete dictation
   - [ ] Verify application doesn't crash
   - [ ] Verify remaining players (if any) resume normally

5. **Feature Toggle**:
   - [ ] Disable `media_pause_on_dictation` in config
   - [ ] Start Spotify playback
   - [ ] Trigger dictation hotkey
   - [ ] Verify Spotify continues playing (not paused)
   - [ ] Complete dictation
   - [ ] Verify application works normally

6. **Both Hotkey Modes**:
   - [ ] Test with `push_to_talk: false` (toggle mode)
   - [ ] Test with `push_to_talk: true` (push-to-talk mode)
   - [ ] Verify pause/resume works correctly in both modes

### Implementation Notes

1. **No Additional Logging**: The MediaController class uses silent error handling (return boolean values). No log_debug() calls are added for operational details, keeping the feature unobtrusive. Debug investigation can be done by inspecting the return values in production if needed.

2. **Playerctl Dependency**: The feature requires `playerctl` to be installed on the system. If not available, the feature gracefully disables itself (returns False from pause/resume). The application continues working normally.

3. **MPRIS Compliance**: playerctl uses MPRIS (Media Player Remote Interfacing Specification) which is supported by:
   - Spotify (via MPRIS bridge)
   - YouTube (in browsers supporting MPRIS)
   - VLC
   - MPV
   - Audacious
   - Most other Linux media players

4. **State Management**: The `paused_players` list is cleared after every pause/resume operation, preventing state leakage between dictation sessions.

5. **Future Enhancement Potential** (not in scope):
   - Per-application pause exclusions (e.g., allow Slack notifications even during recording)
   - Audio ducking instead of pause (reduce volume instead of stopping)
   - Pause/resume hotkey bindings separate from dictation

## What We're NOT Doing

- **No automatic testing infrastructure**: No unit tests, mocking framework, or CI integration (testing happens manually)
- **No GUI for feature toggle**: Feature is toggled via config.json only
- **No system notification**: No visual/audio feedback for pause/resume events
- **No resume on interruption**: If user interrupts dictation before text injection, media doesn't resume (only resumes after complete dictation flow)
- **No player restart**: Missing/closed players are not attempted to be restarted
- **No audio ducking**: Feature only supports pause/resume, not volume reduction
- **No logging output**: Silent operation (no debug, error, or info messages)
- **No per-player configuration**: Cannot exclude specific players from pause
- **No fallback mechanism**: If playerctl unavailable, feature is disabled (no attempt to use D-Bus directly)

## References

- Original ticket: `thoughts/tickets/feature_media_pause_resume.md`
- Similar implementation patterns: 
  - AudioManager (subprocess execution): `lib/src/audio_manager.py:107-195`
  - TextInjector (state tracking): `lib/src/text_injector.py:39-114`
  - Config pattern: `lib/src/config_manager.py:16-110`
  - Error handling pattern: `lib/src/audio_manager.py:142-227`
