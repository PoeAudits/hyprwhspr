---
type: feature
priority: medium
created: 2025-12-11T00:00:00Z
status: reviewed
tags: [media-control, dictation, feature]
keywords: [playerctl, media-pause, media-resume, MPRIS, audio-player, spotify, youtube, dictation-lifecycle]
patterns: [media-control-integration, state-tracking, separation-of-concerns, error-handling, configuration-management]
---

# FEATURE-001: Auto-pause media players during dictation and resume when complete

## Description
Automatically pause active media players (Spotify, YouTube, VLC, etc.) when the dictation hotkey is activated, and resume the same players after dictation is complete. This prevents background music from interfering with audio capture during speech-to-text dictation.

The feature should track which players were actively playing at the start of dictation and only resume those specific players, ensuring that manually-paused players remain paused. The implementation must be decoupled from the transcription logic and operate independently through the dictation lifecycle.

## Context
When a user initiates dictation while music is playing, the background audio can be captured by the microphone, reducing transcription accuracy and introducing unwanted noise. By pausing playback during recording and automatically resuming afterward, the user experience is improved without requiring manual media control.

This feature is particularly important for users with Spotify, YouTube, or other media streaming applications running in the background during work or writing sessions.

## Requirements

### Functional Requirements
- **Auto-pause on dictation start**: Detect all currently playing media players at the moment the dictation hotkey is triggered and pause them
- **Selective resume**: Track which specific players were paused by the system; only resume those players after dictation completes
- **Independent operation**: Media pause/resume logic must operate independently from transcription and text injection; no interaction with base logic unless unavoidable
- **Support both hotkey modes**: Function correctly in both toggle mode (hotkey press/press) and push-to-talk mode (key press/release)
- **Unified player interface**: Use `playerctl` or equivalent MPRIS (Media Player Remote Interfacing Specification) compliant interface to avoid Spotify-specific dependencies
- **State isolation**: Do not resume players that were already paused before dictation started
- **Player exit handling**: If a player exits/closes while dictation is in progress, do not attempt to restart or reconnect to it; gracefully handle missing players
- **Audio level independence**: Do not affect or interact with the audio level monitoring system (`audio_level` file written during recording)

### Non-Functional Requirements
- **Graceful error handling**: Any failure in media control must not crash the application or interfere with dictation functionality; errors should be silently handled
- **No system audio impact**: Only affect media application players (Spotify, YouTube, VLC, browsers); do not pause system notifications or system sounds
- **Zero additional latency for dictation**: Text injection timing must not be affected; move any resume operations to after dictation completes
- **Configuration default**: Feature disabled by default (`media_pause_on_dictation: false` in config)
- **Fail-safe behavior**: If player control fails, dictation continues normally without retry logic
- **No user notifications**: No visual, audio, or status messages for pause/resume events; resumed media serves as implicit confirmation

## Current State
- Audio capture, transcription, and text injection pipelines are functional and independent
- Application supports both toggle and push-to-talk hotkey modes
- Configuration system allows feature toggles via JSON config files
- No media player control or pause/resume functionality exists
- Status files written during recording: `recording_status` (boolean) and `audio_level` (float); these must not be affected

## Desired State
- Media players automatically pause when dictation hotkey is activated
- Recording and transcription proceed uninterrupted with reduced background noise
- After dictation completes and text is injected, previously-playing media automatically resumes
- Feature is configurable and disabled by default
- Feature operates independently with minimal interaction with existing dictation logic
- Application remains stable and responsive regardless of media control success or failure

## Research Context

### Keywords to Search
- **playerctl** - Standard MPRIS interface for controlling media players across Linux desktops (primary implementation mechanism)
- **MPRIS** - Media Player Remote Interfacing Specification; D-Bus based protocol for media control
- **subprocess** - Python subprocess module for executing playerctl commands; verify error handling patterns
- **state-tracking** - Existing state tracking in main.py (is_recording, is_processing); pattern to follow for tracking paused players
- **configuration** - config_manager.py patterns for adding new feature toggles and settings
- **error-handling** - Existing try-except patterns in audio_manager.py and whisper_manager.py for non-fatal errors
- **threading** - Main app uses threading (recording thread, level monitoring thread); verify thread-safety for media operations
- **Spotify** - Primary use case; ensure solution works with Spotify's MPRIS interface compliance
- **fallback-mechanisms** - Research alternative approaches if playerctl unavailable (dbus direct, player-specific APIs)

### Patterns to Investigate
- **Configuration pattern** - How config_manager.py adds new boolean/string settings; look for defaults handling (config_manager.py:24-25 for example)
- **State tracking pattern** - How main.py tracks `is_recording` and `is_processing` states; follow similar pattern for tracking paused players
- **Error handling pattern** - How audio_manager.py gracefully handles audio playback failures (line 107-227); apply to media control
- **Subprocess execution pattern** - How text_injector.py and audio_manager.py execute external commands (ffplay, aplay, ydotool); pattern for playerctl calls
- **Lifecycle hooks** - Where _start_recording() and _stop_recording() are called in main.py (lines 106-181); where to inject pause/resume calls
- **Callback mechanism** - How GlobalShortcuts._trigger_callback() works (line 433); understand thread-safety of media operations
- **Graceful degradation** - How application handles missing audio devices (audio_capture.py:65-110); apply same resilience to missing players

### Key Decisions Made
- **Use playerctl over alternatives**: MPRIS-based solution is most portable across players and doesn't require player-specific authentication or APIs (unlike Spotify Web API)
- **Track paused players at start only**: Store list of playing players when hotkey triggers; only resume those, ensuring user intent is preserved
- **Decoupled implementation**: Create separate `media_control.py` module to keep logic independent from main app flow
- **Async-friendly design**: Use subprocess with timeouts to prevent hanging if player unresponsive
- **Configuration-driven**: Add `media_pause_on_dictation` (bool, default: false) to config to allow opt-in
- **Fail-silent strategy**: All media control operations wrapped in try-except; failures logged but not raised
- **Resume after text injection**: Place resume call after `_inject_text()` completes to minimize latency impact on dictation feedback

## Success Criteria

### Automated Verification
- [ ] Unit tests for `MediaController` class that verify pause/resume commands are generated correctly
- [ ] Unit tests verify that only previously-playing players are resumed (state tracking accuracy)
- [ ] Unit tests for error handling: verify no exceptions escape when playerctl unavailable or player exits
- [ ] Integration tests with mock playerctl that simulate multi-player scenarios
- [ ] Integration tests verify pause happens before audio capture starts
- [ ] Integration tests verify resume happens after text injection completes
- [ ] Test suite verifies both toggle and push-to-talk modes work correctly
- [ ] Config tests verify `media_pause_on_dictation` defaults to false and can be toggled
- [ ] No changes to audio_level file output or recording_status file behavior

### Manual Verification
- [ ] Start Spotify playback, trigger dictation hotkey, verify Spotify pauses immediately
- [ ] Speak into microphone, complete dictation by releasing hotkey (push-to-talk) or pressing again (toggle)
- [ ] Verify Spotify resumes automatically after dictation completes and text is injected
- [ ] Manually pause Spotify, start dictation without Spotify playing, verify dictation works and Spotify remains paused
- [ ] Start multiple players (Spotify + YouTube), trigger dictation, verify both pause; verify both resume
- [ ] Close a player while dictation is in progress; verify application doesn't crash and remaining players resume
- [ ] Disable feature in config, trigger dictation with music playing, verify music continues uninterrupted
- [ ] Verify no console errors or exceptions logged for media control operations
- [ ] Test with playerctl unavailable (uninstall or mock unavailability), verify dictation works normally
- [ ] Verify audio level file is still written correctly during dictation with media control enabled

## Current State Details

### Recording Lifecycle (main.py:106-181)

**Start Recording** (`_start_recording()`, line 106-128):
1. `audio_manager.play_start_sound()` - optional feedback
2. `audio_capture.start_recording()` - begins capturing audio
3. `_start_audio_level_monitoring()` - spawns level monitoring thread
4. **← INSERT MEDIA PAUSE HERE**

**Stop Recording** (`_stop_recording()`, line 131-157):
1. `audio_capture.stop_recording()` - returns audio data
2. `audio_manager.play_stop_sound()` - optional feedback
3. `_process_audio(audio_data)` - calls transcription

**Process Audio** (`_process_audio()`, line 159-181):
1. `whisper_manager.transcribe_audio()` - transcribes audio
2. Stores result in `self.current_transcription`
3. `_inject_text()` - injects into active application
4. **← INSERT MEDIA RESUME HERE (after text injection)**

### Relevant Existing Code Patterns

**Error Handling Pattern** (audio_manager.py:142-227):
```python
try:
    # Attempt audio playback
    subprocess.Popen(..., stdout=DEVNULL, stderr=DEVNULL)
except Exception as e:
    logger.warning(f"Failed to play sound: {e}")
    # Continue gracefully without raising
```

**State Tracking Pattern** (main.py:48-51):
```python
self.is_recording = False
self.is_processing = False
self.current_transcription = ""
```

**Subprocess Pattern** (text_injector.py:uses ydotool via subprocess):
- Executes external commands
- Handles file not found errors
- Runs without blocking main thread

## Architectural Integration

### New Module: `lib/src/media_controller.py`

**Class: MediaController**
- `__init__(config)` - Initialize with feature enabled/disabled flag
- `pause_active_players()` - Execute playerctl pause, track which players paused
- `resume_paused_players()` - Resume only players that were playing before pause
- `_get_playing_players()` - Query playerctl for list of currently playing players
- `_execute_playerctl_command(command, args)` - Safe subprocess wrapper with timeout
- All methods handle exceptions silently; never raise

### Configuration Addition: `config.json`
```json
{
  "media_pause_on_dictation": false
}
```

### Integration Points in `main.py`

**Line 33 (hyprwhsprApp.__init__)**:
- Add: `self.media_controller = MediaController(config)` after existing managers

**Line 118 (inside _start_recording, after audio_capture.start_recording())**:
```python
if self.media_controller.is_enabled():
    self.media_controller.pause_active_players()
```

**Line 174 (inside _process_audio, after text_injector.inject_text())**:
```python
if self.media_controller.is_enabled():
    self.media_controller.resume_paused_players()
```

## Related Information
- Existing audio_manager.py shows pattern for subprocess-based external tool control
- Existing config_manager.py shows pattern for adding new configuration options
- GlobalShortcuts._trigger_callback() shows how callbacks are executed in threads
- Recording flow in main.py shows exact lifecycle points for integration

## Notes

### Research Before Implementation
1. Verify playerctl command syntax: `playerctl --list-all` (list players), `playerctl -p <player> play-pause` (toggle)
2. Verify MPRIS player discovery: Spotify and major players should be MPRIS-compliant
3. Research timeout behavior: How long should we wait for playerctl to respond?
4. Verify subprocess stderr/stdout capture to prevent console pollution
5. Check if playerctl can differentiate between paused and stopped states (important for state tracking)
6. Determine if D-Bus is available on typical Linux Hyprland systems (MPRIS runs on D-Bus)

### Implementation Notes
- Keep media_controller.py focused and minimal; avoid feature creep
- Use existing logger from logger.py for any debug info (disabled in production)
- Ensure thread-safety: pause happens in main thread (hotkey callback), resume happens in main thread (after transcription)
- Consider: Should we add logging for debugging? (Optional: log pause/resume operations at DEBUG level)
- Consider: Should configuration also allow excluding specific players? (Out of scope for v1)

### Future Enhancements (Out of Scope)
- Per-application pause exclusions
- Pause/resume hotkey bindings separate from dictation
- Integration with system DBus directly instead of playerctl
- Web-based players that don't support MPRIS
- Audio ducking instead of pause (reduce volume instead)
