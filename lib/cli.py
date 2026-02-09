#!/usr/bin/env python3
"""
hyprwhspr CLI - Command-line interface for managing hyprwhspr
"""

import sys
import argparse
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Import output control early to set verbosity
try:
    from src.output_control import OutputController, VerbosityLevel
except ImportError:
    from output_control import OutputController, VerbosityLevel

from cli_commands import (
    setup_command,
    omarchy_command,
    config_command,
    waybar_command,
    mic_osd_command,
    systemd_command,
    model_command,
    status_command,
    validate_command,
    test_command,
    backend_repair_command,
    backend_reset_command,
    backend_list_profiles_command,
    backend_use_profile_command,
    backend_add_profile_command,
    model_download_command,
    model_list_local_command,
    model_recommend_command,
    server_start_command,
    server_status_command,
    server_stop_command,
    setup_local_gguf_command,
    setup_local_model_command,
    state_show_command,
    state_validate_command,
    state_reset_command,
    uninstall_command,
    keyboard_command,
    record_command,
)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog="hyprwhspr",
        description="hyprwhspr - ferocious speech-to-text for Linux",
    )

    # Global verbosity flags
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Quiet mode: only show errors"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose mode: show detailed output",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: show all output including debug messages",
    )
    parser.add_argument(
        "--no-progress", action="store_true", help="Disable progress indicators"
    )
    parser.add_argument(
        "--log-file", type=str, metavar="PATH", help="Write all output to log file"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # setup command
    setup_parser = subparsers.add_parser("setup", help="Full initial setup")
    setup_parser.add_argument(
        "--python",
        dest="python_path",
        metavar="PATH",
        help="Path to Python executable for venv (e.g., /usr/bin/python3.14)",
    )
    setup_parser.add_argument(
        "--local-model",
        action="store_true",
        help="Configure local model from safetensors repo or local path (recommended)",
    )
    setup_parser.add_argument(
        "--local-gguf",
        action="store_true",
        help="Configure local GGUF websocket backend (direct GGUF path)",
    )
    setup_parser.add_argument(
        "--repo", help="Hugging Face repo ID for local GGUF setup"
    )
    setup_parser.add_argument("--file", help="GGUF filename for --repo")
    setup_parser.add_argument(
        "--local-path",
        help="Local GGUF file path for local GGUF setup",
    )
    setup_parser.add_argument(
        "--gpu-layers",
        type=int,
        default=-1,
        help="GPU layers to offload (default: -1)",
    )
    setup_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for local websocket server (default: 8000)",
    )
    setup_subparsers = setup_parser.add_subparsers(
        dest="setup_action", help="Setup actions"
    )
    auto_parser = setup_subparsers.add_parser("auto", help="Automated setup")
    auto_parser.add_argument(
        "--backend",
        choices=["nvidia", "vulkan", "cpu", "onnx-asr"],
        help="Backend to install (default: auto-detect GPU)",
    )
    auto_parser.add_argument(
        "--model",
        help="Model to download (default: base for whisper, auto for onnx-asr)",
    )
    auto_parser.add_argument(
        "--no-waybar", action="store_true", help="Skip waybar integration"
    )
    auto_parser.add_argument(
        "--no-mic-osd", action="store_true", help="Disable mic-osd visualization"
    )
    auto_parser.add_argument(
        "--no-systemd", action="store_true", help="Skip systemd service setup"
    )
    auto_parser.add_argument(
        "--hypr-bindings",
        action="store_true",
        help="Enable Hyprland compositor bindings",
    )
    auto_parser.add_argument(
        "--python",
        dest="python_path",
        metavar="PATH",
        help="Path to Python executable for venv (e.g., /usr/bin/python3.14)",
    )

    # install command
    install_parser = subparsers.add_parser("install", help="Installation management")
    install_subparsers = install_parser.add_subparsers(
        dest="install_action", help="Install actions"
    )
    install_subparsers.add_parser(
        "auto", help=argparse.SUPPRESS
    )  # Hidden for backwards compatibility, use 'setup auto' instead

    # config command
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(
        dest="config_action", help="Config actions"
    )
    config_subparsers.add_parser("init", help="Create default config")
    config_subparsers.add_parser("show", help="Display current config")
    config_subparsers.add_parser("edit", help="Open config in editor")

    # waybar command
    waybar_parser = subparsers.add_parser("waybar", help="Waybar integration")
    waybar_subparsers = waybar_parser.add_subparsers(
        dest="waybar_action", help="Waybar actions"
    )
    waybar_subparsers.add_parser("install", help="Add module to waybar config")
    waybar_subparsers.add_parser("remove", help="Remove module from waybar config")
    waybar_subparsers.add_parser("status", help="Check if waybar is configured")

    # mic-osd command
    mic_osd_parser = subparsers.add_parser(
        "mic-osd", help="Microphone visualization overlay"
    )
    mic_osd_subparsers = mic_osd_parser.add_subparsers(
        dest="mic_osd_action", help="Mic-OSD actions"
    )
    mic_osd_subparsers.add_parser(
        "enable", help="Enable visualization during recording"
    )
    mic_osd_subparsers.add_parser("disable", help="Disable visualization")
    mic_osd_subparsers.add_parser("status", help="Check mic-osd status")

    # systemd command
    systemd_parser = subparsers.add_parser("systemd", help="Systemd service management")
    systemd_subparsers = systemd_parser.add_subparsers(
        dest="systemd_action", help="Systemd actions"
    )
    systemd_subparsers.add_parser("install", help="Copy service, enable, start")
    systemd_subparsers.add_parser("enable", help="Enable service")
    systemd_subparsers.add_parser("disable", help="Disable service")
    systemd_subparsers.add_parser("status", help="Show service status")
    systemd_subparsers.add_parser("restart", help="Restart service")

    # model command
    model_parser = subparsers.add_parser("model", help="Model management")
    model_subparsers = model_parser.add_subparsers(
        dest="model_action", help="Model actions"
    )
    model_download_parser = model_subparsers.add_parser(
        "download", help="Download model"
    )
    model_download_parser.add_argument(
        "name", nargs="?", default="base", help="Model name (default: base)"
    )
    model_download_parser.add_argument(
        "--repo", help="HF repo ID for model download (safetensors repo or GGUF host)"
    )
    model_download_parser.add_argument(
        "--file",
        help="Optional GGUF filename (if omitted, downloads safetensors repo snapshot)",
    )
    model_subparsers.add_parser("list", help="List available models")
    model_subparsers.add_parser("list-local", help="List cached local GGUF models")
    model_subparsers.add_parser(
        "recommend", help="Show GPU quantization recommendation"
    )
    model_subparsers.add_parser("status", help="Check installed models")
    model_set_parser = model_subparsers.add_parser(
        "set", help="Set active model for current backend"
    )
    model_set_parser.add_argument("name", help="Model identifier to activate")
    model_subparsers.add_parser("current", help="Show active model for current backend")

    # status command
    subparsers.add_parser("status", help="Overall status check")

    # validate command
    subparsers.add_parser("validate", help="Validate installation")

    # test command
    test_parser = subparsers.add_parser(
        "test", help="Test microphone and backend connectivity"
    )
    test_parser.add_argument(
        "--live",
        action="store_true",
        help="Record live audio instead of using test.wav",
    )
    test_parser.add_argument(
        "--mic-only",
        action="store_true",
        help="Only test microphone, skip transcription",
    )

    # keyboard command
    keyboard_parser = subparsers.add_parser(
        "keyboard", help="Keyboard device management"
    )
    keyboard_subparsers = keyboard_parser.add_subparsers(
        dest="keyboard_action", help="Keyboard actions"
    )
    keyboard_subparsers.add_parser("list", help="List available keyboard devices")
    keyboard_subparsers.add_parser("test", help="Test keyboard device accessibility")

    # record command (for external hotkey systems)
    record_parser = subparsers.add_parser(
        "record", help="Control recording (for external hotkeys)"
    )
    record_subparsers = record_parser.add_subparsers(
        dest="record_action", help="Recording actions"
    )
    record_start_parser = record_subparsers.add_parser("start", help="Start recording")
    record_start_parser.add_argument(
        "--lang",
        dest="language",
        metavar="CODE",
        help="Language code for transcription (e.g., en, it, de)",
    )
    record_subparsers.add_parser("stop", help="Stop recording")
    record_toggle_parser = record_subparsers.add_parser(
        "toggle", help="Toggle recording on/off"
    )
    record_toggle_parser.add_argument(
        "--lang",
        dest="language",
        metavar="CODE",
        help="Language code for transcription (e.g., en, it, de)",
    )
    record_subparsers.add_parser("status", help="Show current recording status")

    # backend command
    backend_parser = subparsers.add_parser("backend", help="Backend management")
    backend_subparsers = backend_parser.add_subparsers(
        dest="backend_action", help="Backend actions"
    )
    backend_subparsers.add_parser("repair", help="Repair corrupted installation")
    backend_subparsers.add_parser("reset", help="Reset installation state")
    backend_subparsers.add_parser("list-profiles", help="List local model profiles")
    backend_use_profile_parser = backend_subparsers.add_parser(
        "use-profile", help="Apply a local model profile"
    )
    backend_use_profile_parser.add_argument("name", help="Profile name")
    backend_add_profile_parser = backend_subparsers.add_parser(
        "add-profile", help="Add/update a local model profile"
    )
    backend_add_profile_parser.add_argument("name", help="Profile name")
    backend_add_profile_parser.add_argument(
        "--url", required=True, help="WebSocket URL for realtime endpoint"
    )
    backend_add_profile_parser.add_argument(
        "--model", required=True, help="Model identifier for this profile"
    )
    backend_add_profile_parser.add_argument(
        "--protocol",
        choices=["openai-realtime", "vllm-realtime"],
        default="vllm-realtime",
        help="Realtime protocol style (default: vllm-realtime)",
    )
    backend_add_profile_parser.add_argument(
        "--auth-mode",
        choices=["none", "bearer", "header"],
        default="none",
        help="WebSocket authentication mode (default: none)",
    )
    backend_add_profile_parser.add_argument(
        "--api-key-header",
        default=None,
        help="Header name to use when --auth-mode header",
    )
    backend_add_profile_parser.add_argument(
        "--model-path",
        default=None,
        help="Optional local GGUF path for auto-start",
    )
    backend_add_profile_parser.add_argument(
        "--no-auto-start-server",
        action="store_true",
        help="Disable local server auto-start for this profile",
    )

    backend_server_parser = backend_subparsers.add_parser(
        "server", help="Local model server management"
    )
    backend_server_subparsers = backend_server_parser.add_subparsers(
        dest="server_action", help="Server actions"
    )
    backend_server_start_parser = backend_server_subparsers.add_parser(
        "start", help="Start local model server"
    )
    backend_server_start_parser.add_argument(
        "--model-path", default=None, help="GGUF model path"
    )
    backend_server_start_parser.add_argument(
        "--port", type=int, default=8000, help="Server port"
    )
    backend_server_start_parser.add_argument(
        "--idle-timeout",
        type=int,
        default=300,
        help="Idle timeout in seconds",
    )
    backend_server_subparsers.add_parser("stop", help="Stop local model server")
    backend_server_subparsers.add_parser(
        "status", help="Show local model server status"
    )

    # state command
    state_parser = subparsers.add_parser("state", help="State management")
    state_subparsers = state_parser.add_subparsers(
        dest="state_action", help="State actions"
    )
    state_subparsers.add_parser("show", help="Show current state")
    state_validate_parser = state_subparsers.add_parser(
        "validate", help="Validate state consistency"
    )
    state_reset_parser = state_subparsers.add_parser("reset", help="Reset state file")
    state_reset_parser.add_argument(
        "--all", action="store_true", help="Also remove installations"
    )

    # uninstall command
    uninstall_parser = subparsers.add_parser(
        "uninstall", help="Completely remove hyprwhspr and all user data"
    )
    uninstall_parser.add_argument(
        "--keep-models",
        action="store_true",
        help="Keep downloaded Whisper models (faster reinstall)",
    )
    uninstall_parser.add_argument(
        "--remove-permissions",
        action="store_true",
        help="Automatically remove system permissions (groups, udev rules)",
    )
    uninstall_parser.add_argument(
        "--skip-permissions",
        action="store_true",
        help="Skip permission removal entirely",
    )
    uninstall_parser.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompt (non-interactive)"
    )

    args = parser.parse_args()

    # Set verbosity level
    if args.quiet:
        OutputController.set_verbosity(VerbosityLevel.QUIET)
    elif args.debug:
        OutputController.set_verbosity(VerbosityLevel.DEBUG)
    elif args.verbose:
        OutputController.set_verbosity(VerbosityLevel.VERBOSE)
    else:
        OutputController.set_verbosity(VerbosityLevel.NORMAL)

    # Set progress enabled
    if args.no_progress:
        OutputController.set_progress_enabled(False)

    # Set log file if specified
    if args.log_file:
        OutputController.set_log_file(Path(args.log_file))

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route to appropriate command handler
    try:
        if args.command == "setup":
            if hasattr(args, "setup_action") and args.setup_action == "auto":
                if not omarchy_command(args):
                    sys.exit(1)
            elif getattr(args, "local_gguf", False) or getattr(
                args, "local_model", False
            ):
                source = args.local_path or args.repo
                if not source:
                    setup_parser.error(
                        "--local-model/--local-gguf requires --local-path or --repo"
                    )

                use_gguf_path = bool(getattr(args, "local_gguf", False))
                if use_gguf_path and args.repo and not args.file:
                    setup_parser.error("--local-gguf with --repo requires --file")

                ok = False
                if use_gguf_path:
                    ok = setup_local_gguf_command(
                        source=source,
                        filename=args.file,
                        gpu_layers=args.gpu_layers,
                        port=args.port,
                    )
                else:
                    ok = setup_local_model_command(
                        source=source,
                        filename=args.file,
                        gpu_layers=args.gpu_layers,
                        port=args.port,
                    )

                if not ok:
                    sys.exit(1)
            elif hasattr(args, "setup_action") and args.setup_action:
                setup_parser.print_help()
                sys.exit(1)
            else:
                python_path = getattr(args, "python_path", None)
                setup_command(python_path=python_path)
        elif args.command == "install":
            if not args.install_action:
                install_parser.print_help()
                sys.exit(1)
            if args.install_action == "auto":
                if not omarchy_command(args):
                    sys.exit(1)
        elif args.command == "config":
            if not args.config_action:
                config_parser.print_help()
                sys.exit(1)
            config_command(args.config_action)
        elif args.command == "waybar":
            if not args.waybar_action:
                waybar_parser.print_help()
                sys.exit(1)
            waybar_command(args.waybar_action)
        elif args.command == "mic-osd":
            if not args.mic_osd_action:
                mic_osd_parser.print_help()
                sys.exit(1)
            mic_osd_command(args.mic_osd_action)
        elif args.command == "systemd":
            if not args.systemd_action:
                systemd_parser.print_help()
                sys.exit(1)
            systemd_command(args.systemd_action)
        elif args.command == "model":
            if not args.model_action:
                model_parser.print_help()
                sys.exit(1)
            if args.model_action == "download" and args.repo:
                if not model_download_command(args.repo, getattr(args, "file", None)):
                    sys.exit(1)
                return
            if args.model_action == "list-local":
                model_list_local_command()
                return
            if args.model_action == "recommend":
                model_recommend_command()
                return
            model_name = getattr(args, "name", "base")
            model_command(
                args.model_action,
                model_name,
                repo_id=getattr(args, "repo", None),
                filename=getattr(args, "file", None),
            )
        elif args.command == "status":
            status_command()
        elif args.command == "validate":
            validate_command()
        elif args.command == "test":
            test_command(
                live=getattr(args, "live", False),
                mic_only=getattr(args, "mic_only", False),
            )
        elif args.command == "keyboard":
            if not args.keyboard_action:
                keyboard_parser.print_help()
                sys.exit(1)
            keyboard_command(args.keyboard_action)
        elif args.command == "backend":
            if not args.backend_action:
                backend_parser.print_help()
                sys.exit(1)
            if args.backend_action == "repair":
                backend_repair_command()
            elif args.backend_action == "reset":
                backend_reset_command()
            elif args.backend_action == "list-profiles":
                backend_list_profiles_command()
            elif args.backend_action == "use-profile":
                backend_use_profile_command(args.name)
            elif args.backend_action == "add-profile":
                backend_add_profile_command(
                    name=args.name,
                    websocket_url=args.url,
                    model=args.model,
                    protocol=args.protocol,
                    auth_mode=args.auth_mode,
                    api_key_header=args.api_key_header,
                    auto_start_server=not bool(args.no_auto_start_server),
                    model_path=args.model_path,
                )
            elif args.backend_action == "server":
                if not args.server_action:
                    backend_server_parser.print_help()
                    sys.exit(1)
                if args.server_action == "start":
                    if not server_start_command(
                        model_path=getattr(args, "model_path", None),
                        port=getattr(args, "port", 8000),
                        idle_timeout=getattr(args, "idle_timeout", 300),
                    ):
                        sys.exit(1)
                elif args.server_action == "stop":
                    if not server_stop_command():
                        sys.exit(1)
                elif args.server_action == "status":
                    server_status_command()
        elif args.command == "state":
            if not args.state_action:
                state_parser.print_help()
                sys.exit(1)
            if args.state_action == "show":
                state_show_command()
            elif args.state_action == "validate":
                state_validate_command()
            elif args.state_action == "reset":
                state_reset_command(getattr(args, "all", False))
        elif args.command == "record":
            if not args.record_action:
                record_parser.print_help()
                sys.exit(1)
            record_command(args.record_action, language=getattr(args, "language", None))
        elif args.command == "uninstall":
            uninstall_command(
                keep_models=getattr(args, "keep_models", False),
                remove_permissions=getattr(args, "remove_permissions", False),
                skip_permissions=getattr(args, "skip_permissions", False),
                yes=getattr(args, "yes", False),
            )
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
