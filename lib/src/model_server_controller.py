"""Controller for local websocket server lifecycle."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    from .paths import DATA_DIR, MODEL_SERVER_LOG_FILE, MODEL_SERVER_PID_FILE
except ImportError:
    from paths import DATA_DIR, MODEL_SERVER_LOG_FILE, MODEL_SERVER_PID_FILE


@dataclass
class ServerStatus:
    """Server status view."""

    state: str
    pid: int | None
    host: str
    port: int
    log_file: Path
    error: str | None = None


class ModelServerController:
    """Start/stop/check the local websocket model server."""

    def __init__(self) -> None:
        self.pid_file = MODEL_SERVER_PID_FILE
        self.log_file = MODEL_SERVER_LOG_FILE
        self.default_host = "127.0.0.1"
        self.default_port = 8000

    def start_server(
        self,
        model_path: Path,
        source_type: str = "gguf",
        port: int = 8000,
        idle_timeout: int = 300,
        host: str = "127.0.0.1",
        n_gpu_layers: int = -1,
        n_ctx: int = 8192,
    ) -> bool:
        """Start local model server if not already running."""
        if self.is_running():
            return True

        if not model_path.exists():
            return False

        if source_type == "gguf" and not model_path.is_file():
            return False
        if source_type == "safetensors" and not model_path.is_dir():
            return False

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        server_script_path = self._server_script_path(source_type)
        if not server_script_path.exists():
            return False

        env_vars = os.environ.copy()
        env_vars["HYPRWHSPR_MODEL_PATH"] = str(model_path)
        env_vars["HYPRWHSPR_SERVER_PORT"] = str(port)
        env_vars["HYPRWHSPR_SERVER_HOST"] = host
        env_vars["HYPRWHSPR_IDLE_TIMEOUT"] = str(idle_timeout)
        env_vars["HYPRWHSPR_N_GPU_LAYERS"] = str(n_gpu_layers)
        env_vars["HYPRWHSPR_N_CTX"] = str(n_ctx)
        env_vars["HYPRWHSPR_MODEL_SOURCE_TYPE"] = source_type

        command = [
            sys.executable,
            str(server_script_path),
            "--model-path",
            str(model_path),
            "--port",
            str(port),
            "--host",
            host,
            "--idle-timeout",
            str(idle_timeout),
        ]
        if source_type == "gguf":
            command.extend(
                [
                    "--n-gpu-layers",
                    str(n_gpu_layers),
                    "--n-ctx",
                    str(n_ctx),
                ]
            )

        with open(self.log_file, "a", encoding="utf-8") as log_handle:
            process = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=env_vars,
            )

        self.pid_file.write_text(str(process.pid), encoding="utf-8")
        return self.wait_for_ready(host=host, port=port, timeout=30)

    def stop_server(self) -> bool:
        """Stop local server process if running."""
        pid_value = self._read_pid()
        if pid_value is None:
            self._cleanup_stale_pid_file()
            return True

        if not self._is_process_alive(pid_value):
            self._cleanup_stale_pid_file()
            return True

        try:
            os.kill(pid_value, signal.SIGTERM)
            for _ in range(30):
                if not self._is_process_alive(pid_value):
                    self._cleanup_stale_pid_file()
                    return True
                time.sleep(0.1)

            os.kill(pid_value, signal.SIGKILL)
            self._cleanup_stale_pid_file()
            return True
        except ProcessLookupError:
            self._cleanup_stale_pid_file()
            return True
        except Exception:
            return False

    def is_running(self) -> bool:
        """Return whether the server process appears alive."""
        pid_value = self._read_pid()
        if pid_value is None:
            self._cleanup_stale_pid_file()
            return False

        if self._is_process_alive(pid_value):
            return True

        self._cleanup_stale_pid_file()
        return False

    def wait_for_ready(
        self,
        timeout: int = 30,
        host: str | None = None,
        port: int | None = None,
    ) -> bool:
        """Wait until TCP listener accepts connections."""
        host_value = host or self.default_host
        port_value = port or self.default_port
        deadline_unix_s = time.time() + max(1, timeout)
        while time.time() < deadline_unix_s:
            if not self.is_running():
                time.sleep(0.1)
                continue

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.settimeout(0.5)
                try:
                    client_socket.connect((host_value, int(port_value)))
                    return True
                except OSError:
                    time.sleep(0.1)

        return False

    def get_status(self) -> ServerStatus:
        """Get current local model server status."""
        pid_value = self._read_pid()
        if pid_value is None:
            return ServerStatus(
                state="stopped",
                pid=None,
                host=self.default_host,
                port=self.default_port,
                log_file=self.log_file,
            )

        if self._is_process_alive(pid_value):
            state = "ready" if self.wait_for_ready(timeout=1) else "starting"
            return ServerStatus(
                state=state,
                pid=pid_value,
                host=self.default_host,
                port=self.default_port,
                log_file=self.log_file,
            )

        self._cleanup_stale_pid_file()
        return ServerStatus(
            state="error",
            pid=pid_value,
            host=self.default_host,
            port=self.default_port,
            log_file=self.log_file,
            error="stale pid file",
        )

    def _server_script_path(self, source_type: str) -> Path:
        lib_path = Path(__file__).resolve().parent.parent
        if source_type == "safetensors":
            return lib_path / "backends" / "local_safetensors_server" / "server.py"
        return lib_path / "backends" / "local_ws_server" / "server.py"

    def _read_pid(self) -> int | None:
        if not self.pid_file.exists():
            return None
        try:
            return int(self.pid_file.read_text(encoding="utf-8").strip())
        except Exception:
            return None

    def _cleanup_stale_pid_file(self) -> None:
        try:
            self.pid_file.unlink(missing_ok=True)
        except Exception:
            return

    def _is_process_alive(self, pid_value: int) -> bool:
        try:
            os.kill(pid_value, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
