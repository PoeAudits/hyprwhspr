from pathlib import Path

from lib.src.local_model_manager import LocalModelManager


def test_recommend_quantization_thresholds() -> None:
    manager = LocalModelManager()
    assert manager.recommend_quantization(4096) == "Q4_K_M"
    assert manager.recommend_quantization(12288) == "Q5_K_M"
    assert manager.recommend_quantization(24576) == "Q6_K"


def test_validate_local_model_rejects_non_gguf(tmp_path: Path) -> None:
    manager = LocalModelManager()
    bad_path = tmp_path / "model.bin"
    bad_path.write_bytes(b"hello")
    valid, message = manager.validate_local_model(str(bad_path))
    assert valid is False
    assert "gguf" in message.lower()
