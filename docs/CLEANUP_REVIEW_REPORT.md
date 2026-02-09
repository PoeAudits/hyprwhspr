# Hyprwhspr Cleanup Review Report (Phase 2 + Phase 3)

Date: 2026-02-08  
Scope: `lib/`, `tests/`, `scripts/`, `bin/`, `config/`, `docs/`  
Skipped: `.git`, `node_modules`, `dist`, `build`, `__pycache__`, `vendor`, `.opencode`, `.tmux.local`, generated artifacts

## Method

- Focus areas selected: **Dead code**, **Redundancy**, **Complexity**
- Seeker agents dispatched: 3 (one per selected topic)
- Impact score (1-10) weighted by:
  - estimated lines affected
  - centrality of the code path
  - hot path/runtime impact
- Findings sorted by impact descending within each category.

## Findings by Category

### 1) Dead Code / Unused Paths

| Impact | Frequency | Location | Description | Est. Lines | Fix Effort |
|---|---:|---|---|---:|---|
| 7 | 1 | `lib/src/local_model_manager.py:192` | `convert_transformers_to_gguf()` appears unreferenced by CLI/tests | 60 | Small (1 file, low risk) |
| 6 | 7 methods | `lib/src/audio_manager.py:231` | Unused configuration setters/status methods (never called by runtime) | 110 | Medium (1 file, low-medium risk) |
| 5 | 2 funcs | `lib/src/credential_manager.py:104` | `list_credentials()` and `delete_credential()` not referenced | 18 | Small (1 file, low risk) |
| 4 | 8 funcs/methods | `lib/src/logger.py:103`, `lib/src/logger.py:244` | Legacy logger wrappers/methods not referenced (`log_success`, etc.) | 20 | Small (1 file, low risk) |
| 3 | 1 func + imports | `lib/src/output_control.py:122`, `lib/src/cli_commands.py:149`, `lib/src/cli_commands.py:172` | `log_verbose()` dead path + unused imports | 6 | Trivial (2 files, very low risk) |

### 2) Redundancy / Duplication

| Impact | Frequency | Location | Description | Est. Lines | Fix Effort |
|---|---:|---|---|---:|---|
| 9 | 3 implementations | `scripts/install-deps.sh:186`, `lib/src/cli_commands.py:317`, `lib/src/text_injector.py:34` | ydotool detection/version/remediation duplicated across installer, CLI, runtime | 220 | Medium (3 files, medium risk) |
| 8 | 3 implementations | `scripts/install-deps.sh:102`, `lib/src/cli_commands.py:255`, `lib/src/backend_installer.py:86` | Python compatibility gate duplicated (same distro guidance and version policy) | 160 | Medium (3 files, medium risk) |
| 7 | 2 implementations | `lib/src/backend_installer.py:770`, `lib/src/backend_installer.py:955` | GPU presence detection duplicated in same file (`setup_nvidia_support` vs `detect_gpu_type`) | 180 | Medium (1 file, medium risk) |
| 6 | 2 modules | `lib/src/pulse_monitor.py:31`, `lib/src/device_monitor.py:30` | Monitor lifecycle/thread scaffolding nearly identical | 240 | Medium (2 files, medium risk) |
| 6 | 3 implementations | `lib/src/local_model_manager.py:45`, `lib/src/local_model_manager.py:335`, `lib/src/backend_installer.py:955` | GPU capability probing split and duplicated across modules | 120 | Medium (2 files, medium risk) |
| 4 | 4 repeated branches | `lib/src/text_injector.py:155` | Repeated paste key chord subprocess logic; data-driven table possible | 30 | Small (1 file, low risk) |

### 3) Complexity / Overengineering

| Impact | Frequency | Location | Description | Est. Lines | Fix Effort |
|---|---:|---|---|---:|---|
| 10 | 1 hotspot | `lib/src/audio_capture.py:22` | `AudioCapture` is a ~1k LOC multi-responsibility class (capture, threading, recovery, persistence, notifications) | 1000 | High (multi-file extraction, high risk) |
| 10 | 1 hotspot | `lib/src/cli_commands.py:1310` | `setup_command` is ~800 LOC mixing prompts, validation, config mutation, subprocess/system changes | 800 | High (multi-file extraction, high risk) |
| 8 | 1 function | `lib/src/cli_commands.py:925` | `_prompt_remote_provider_selection()` has deep nested loops/branches and repeated prompt/validation paths | 250 | Medium (1-2 files, medium risk) |
| 7 | 1 function | `lib/src/audio_capture.py:71` | `_initialize_sounddevice()` has deep nested fallback logic and repeated condition blocks | 100 | Medium (1 file, medium risk) |
| 7 | 1 function | `lib/src/audio_capture.py:832` | `recover_audio_capture()` has complex state machine with intertwined flags/joins/locks | 140 | Medium-High (1 file, high runtime risk) |
| 7 | 1 script | `scripts/install-deps.sh:1` | Installer script is large with long distro branches and repeated echo/branch patterns | 450 | Medium (1 script, medium risk) |
| 6 | 1 function | `lib/src/cli_commands.py:703` | `_prompt_backend_selection()` mixes UI, backend normalization, reinstall flags, compatibility behavior | 160 | Medium (1 file, medium risk) |

## Summary Table

| Metric | Value |
|---|---:|
| Total issues found | 18 |
| Dead code issues | 5 |
| Redundancy issues | 6 |
| Complexity issues | 7 |
| Estimated dead code removable | 214 LOC |
| Estimated redundant/simplifiable code | 3,850 LOC (overlap-adjusted high-level estimate) |

Notes:
- Redundancy/complexity totals overlap by nature; estimate is directional for cleanup planning.
- No significant complexity/redundancy hotspots were reported under `tests/` and `docs/`.

## Phase 3: Cleanup Plan (Ranked by Impact/Effort)

### Phase A - Quick Wins (high value, low risk)

#### Batch A1: Remove clearly unused symbols and imports
- Files: `lib/src/output_control.py`, `lib/src/cli_commands.py`, `lib/src/logger.py`, `lib/src/credential_manager.py`, `lib/src/local_model_manager.py`, `lib/src/audio_manager.py`
- Approach:
  - Remove `log_verbose` and dead imports
  - Remove/flag legacy logger wrappers not used by runtime
  - Remove unreferenced credential and model conversion APIs (or mark internal if planned)
  - Prune unused `AudioManager` setters/status if no external API contract depends on them
- Risk/test:
  - Risk: low-medium (public API expectations)
  - Test: CLI smoke (`hyprwhspr --help`, setup dry paths), audio feedback smoke, model listing/downloading tests
- Expected simplification: ~180-220 LOC

#### Batch A2: Data-drive repeated key chord logic
- Files: `lib/src/text_injector.py`
- Approach:
  - Replace repeated subprocess blocks with a mapping table and one executor loop
- Risk/test:
  - Risk: low
  - Test: ydotool path and fallback mode tests, manual text injection check
- Expected simplification: ~20-30 LOC

### Phase B - Medium Effort (high leverage)

#### Batch B1: Centralize Python compatibility checks
- Files: `lib/src/backend_installer.py`, `lib/src/cli_commands.py`, `scripts/install-deps.sh`
- Approach:
  - Extract one authoritative compatibility checker/message formatter
  - Have CLI and installer consume same policy/message source
- Risk/test:
  - Risk: medium (install UX regressions)
  - Test: version matrix checks (supported/unsupported versions), distro guidance text snapshots
- Expected simplification: ~120-170 LOC

#### Batch B2: Consolidate ydotool capability detection/remediation policy
- Files: `lib/src/cli_commands.py`, `lib/src/text_injector.py`, `scripts/install-deps.sh`
- Approach:
  - Share version parsing and minimum-version rules
  - Keep shell script install mechanics but call into shared policy text/rules where possible
- Risk/test:
  - Risk: medium
  - Test: mocked ydotool versions (missing/old/new), Debian backports branch, runtime injection fallback
- Expected simplification: ~150-230 LOC

#### Batch B3: Unify GPU detection helpers
- Files: `lib/src/backend_installer.py`, `lib/src/local_model_manager.py`
- Approach:
  - Extract common GPU probe utility returning structured capabilities
  - Reuse in installer selection and local model manager
- Risk/test:
  - Risk: medium
  - Test: mock command outputs (`nvidia-smi`, `rocm-smi`, `vulkaninfo`), backend-selection regression tests
- Expected simplification: ~120-200 LOC

#### Batch B4: Shared monitor lifecycle base
- Files: `lib/src/pulse_monitor.py`, `lib/src/device_monitor.py`
- Approach:
  - Create a common base for start/stop/thread/error scaffolding
  - Keep backend-specific watch implementations in child classes
- Risk/test:
  - Risk: medium (thread lifecycle changes)
  - Test: monitor start/stop idempotency, callback dispatch behavior, dependency-missing handling
- Expected simplification: ~80-150 LOC

### Phase C - Deep Refactors (high impact, higher risk)

#### Batch C1: Decompose `setup_command`
- Files: `lib/src/cli_commands.py` (+ likely new modules under `lib/src/`)
- Approach:
  - Split into pure decision functions + side-effect executors
  - Isolate provider/backend prompting, environment checks, and mutating operations
  - Add boundary tests around each setup stage
- Risk/test:
  - Risk: high (setup flow regression)
  - Test: scenario matrix for local/remote backends, reinstall path, waybar/systemd branches
- Expected simplification: ~250-450 LOC reduced and major maintainability gain

#### Batch C2: Break up `AudioCapture` monolith
- Files: `lib/src/audio_capture.py` (+ new modules)
- Approach:
  - Split responsibilities into components: device init, stream lifecycle, recovery controller, persistence, notifications
  - Replace implicit flag choreography with a smaller explicit state model
- Risk/test:
  - Risk: high (runtime and threading)
  - Test: recording start/stop, forced stream failure recovery, long-run stability, race-condition checks
- Expected simplification: ~300-500 LOC reduced plus clearer ownership boundaries

## Highest-Impact Findings

1. `lib/src/audio_capture.py:22` - monolithic class with high threading/recovery complexity (impact 10)
2. `lib/src/cli_commands.py:1310` - oversized setup orchestration function (impact 10)
3. `scripts/install-deps.sh:186`, `lib/src/cli_commands.py:317`, `lib/src/text_injector.py:34` - triplicated ydotool logic (impact 9)
4. `scripts/install-deps.sh:102`, `lib/src/cli_commands.py:255`, `lib/src/backend_installer.py:86` - triplicated Python compatibility gates (impact 8)
5. `lib/src/local_model_manager.py:192` + `lib/src/audio_manager.py:231` - concentrated dead code removal opportunities (impact 7/6)
