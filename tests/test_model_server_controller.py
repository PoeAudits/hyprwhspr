from pathlib import Path

from lib.src.model_server_controller import ModelServerController


def test_is_running_cleans_stale_pid_file(tmp_path: Path) -> None:
    controller = ModelServerController()
    controller.pid_file = tmp_path / "model-server.pid"
    controller.log_file = tmp_path / "model-server.log"

    controller.pid_file.write_text("999999", encoding="utf-8")
    assert controller.is_running() is False
    assert controller.pid_file.exists() is False
