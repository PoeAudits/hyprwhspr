"""Local GGUF model management helpers."""

from __future__ import annotations

import re
import os
import subprocess
import time
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import requests

try:
    from .paths import MODEL_CACHE_DIR
except ImportError:
    from paths import MODEL_CACHE_DIR


DOWNLOAD_TIMEOUT_SECONDS = 60
DOWNLOAD_CHUNK_SIZE_BYTES = 1024 * 1024
DOWNLOAD_RETRY_COUNT_MAX = 3


@dataclass
class CachedModel:
    """Metadata for a cached local GGUF file."""

    name: str
    path: Path
    size_bytes: int
    modified_unix_s: float
    context_size: int


class LocalModelManager:
    """Manage local GGUF downloads, validation, and cache metadata."""

    def __init__(self) -> None:
        self.cache_dir = MODEL_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def detect_gpu(self) -> tuple[bool, str, int]:
        """Detect GPU availability and approximate VRAM in MB."""
        nvidia_vram_mb = self._detect_gpu_nvidia_vram_mb()
        if nvidia_vram_mb > 0:
            return (True, "cuda", nvidia_vram_mb)

        rocm_vram_mb = self._detect_gpu_rocm_vram_mb()
        if rocm_vram_mb > 0:
            return (True, "rocm", rocm_vram_mb)

        vulkan_vram_mb = self._detect_gpu_vulkan_vram_mb()
        if vulkan_vram_mb > 0:
            return (True, "vulkan", vulkan_vram_mb)

        return (False, "none", 0)

    def recommend_quantization(self, vram_mb: int) -> str:
        """Recommend GGUF quantization based on available VRAM."""
        if vram_mb <= 0:
            return "Q4_K_M"
        if vram_mb < 8192:
            return "Q4_K_M"
        if vram_mb <= 16384:
            return "Q5_K_M"
        return "Q6_K"

    def download_model(
        self,
        repo_id: str,
        filename: str,
        progress_callback=None,
    ) -> Path:
        """Download a GGUF model from Hugging Face with resume support."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        target_path = self.cache_dir / filename
        tmp_path = target_path.with_suffix(f"{target_path.suffix}.part")
        download_url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"

        if target_path.exists() and target_path.stat().st_size > 0:
            return target_path

        for retry_index in range(DOWNLOAD_RETRY_COUNT_MAX):
            try:
                resume_size_bytes = tmp_path.stat().st_size if tmp_path.exists() else 0
                headers = {}
                if resume_size_bytes > 0:
                    headers["Range"] = f"bytes={resume_size_bytes}-"

                with requests.get(
                    download_url,
                    stream=True,
                    timeout=DOWNLOAD_TIMEOUT_SECONDS,
                    headers=headers,
                ) as response:
                    if response.status_code not in (200, 206):
                        raise RuntimeError(
                            f"Download failed with HTTP status {response.status_code}"
                        )

                    total_from_header = response.headers.get("Content-Length")
                    total_size_bytes = (
                        int(total_from_header) + resume_size_bytes
                        if total_from_header
                        else None
                    )
                    write_mode = "ab" if resume_size_bytes > 0 else "wb"
                    downloaded_size_bytes = resume_size_bytes

                    with open(tmp_path, write_mode) as file_handle:
                        for chunk_bytes in response.iter_content(
                            chunk_size=DOWNLOAD_CHUNK_SIZE_BYTES
                        ):
                            if not chunk_bytes:
                                continue
                            file_handle.write(chunk_bytes)
                            downloaded_size_bytes += len(chunk_bytes)

                            if progress_callback is not None:
                                progress_callback(
                                    downloaded_size_bytes, total_size_bytes
                                )

                if tmp_path.stat().st_size <= 0:
                    raise RuntimeError("Downloaded file is empty")

                tmp_path.replace(target_path)
                return target_path

            except Exception:
                if retry_index >= (DOWNLOAD_RETRY_COUNT_MAX - 1):
                    raise
                time.sleep(1.5 * (retry_index + 1))

        raise RuntimeError("Download failed after retries")

    def download_transformers_repo(self, repo_id: str) -> Path:
        """Download a HuggingFace transformers repo snapshot via huggingface-cli."""
        repo_slug = repo_id.replace("/", "--")
        target_dir = self.cache_dir / repo_slug
        if target_dir.exists() and any(target_dir.glob("*.safetensors")):
            return target_dir

        target_dir.mkdir(parents=True, exist_ok=True)
        command = self._huggingface_cli_command() + [
            "download",
            repo_id,
            "--local-dir",
            str(target_dir),
        ]
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to download transformers repo (exit code {result.returncode})"
            )

        if not any(target_dir.glob("*.safetensors")):
            raise RuntimeError(
                "Downloaded repo does not contain .safetensors files; verify repo content"
            )
        return target_dir

    def validate_local_model(self, path: str) -> tuple[bool, str]:
        """Validate local GGUF model path."""
        model_path = Path(path).expanduser().resolve()
        if not model_path.exists():
            return (False, f"Model file not found: {model_path}")
        if not model_path.is_file():
            return (False, f"Model path is not a file: {model_path}")
        if model_path.suffix.lower() != ".gguf":
            return (False, "Model file must use .gguf extension")
        if model_path.stat().st_size < 1024 * 1024:
            return (False, "Model file is unexpectedly small")
        return (True, str(model_path))

    def validate_local_transformers_model(self, path: str) -> tuple[bool, str]:
        """Validate local transformers model directory (safetensors)."""
        model_dir = Path(path).expanduser().resolve()
        if not model_dir.exists():
            return (False, f"Model directory not found: {model_dir}")
        if not model_dir.is_dir():
            return (False, f"Model path is not a directory: {model_dir}")
        if not any(model_dir.glob("*.safetensors")):
            return (False, "No .safetensors files found in model directory")
        if not (model_dir / "config.json").exists():
            return (False, "Missing config.json in model directory")
        return (True, str(model_dir))

    def convert_transformers_to_gguf(
        self,
        model_dir: Path,
        quantization: str = "Q5_K_M",
    ) -> Path:
        """Convert local transformers model dir to GGUF using llama.cpp."""
        llama_cpp_root = self._resolve_llama_cpp_root()
        convert_script = llama_cpp_root / "convert_hf_to_gguf.py"
        if not convert_script.exists():
            raise RuntimeError(
                f"convert_hf_to_gguf.py not found at {convert_script}; install llama.cpp first"
            )

        model_slug = model_dir.name
        f16_path = self.cache_dir / f"{model_slug}-f16.gguf"
        quant_path = self.cache_dir / f"{model_slug}-{quantization.lower()}.gguf"

        if not f16_path.exists():
            convert_result = subprocess.run(
                [
                    "python",
                    str(convert_script),
                    str(model_dir),
                    "--outfile",
                    str(f16_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            if convert_result.returncode != 0:
                error_text = (
                    convert_result.stderr.strip() or convert_result.stdout.strip()
                )
                raise RuntimeError(f"GGUF conversion failed: {error_text}")

        quantize_candidates = [
            llama_cpp_root / "build" / "bin" / "llama-quantize",
            llama_cpp_root / "llama-quantize",
        ]
        quantize_binary = next(
            (candidate for candidate in quantize_candidates if candidate.exists()),
            None,
        )

        if quantize_binary is None:
            return f16_path
        if quant_path.exists():
            return quant_path

        quant_result = subprocess.run(
            [
                str(quantize_binary),
                str(f16_path),
                str(quant_path),
                quantization,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if quant_result.returncode != 0:
            error_text = quant_result.stderr.strip() or quant_result.stdout.strip()
            raise RuntimeError(f"GGUF quantization failed: {error_text}")
        return quant_path

    def get_model_context_size(self, model_path: Path) -> int:
        """Best-effort GGUF context size detection."""
        try:
            with open(model_path, "rb") as file_handle:
                scan_bytes = file_handle.read(16 * 1024 * 1024)

            candidates = (
                b"context_length",
                b"n_ctx",
                b"llama.context_length",
                b"n_ctx_train",
            )
            for candidate_key in candidates:
                key_index = scan_bytes.find(candidate_key)
                if key_index < 0:
                    continue
                window_start = max(0, key_index - 64)
                window_end = min(len(scan_bytes), key_index + 128)
                window_bytes = scan_bytes[window_start:window_end]
                match = re.search(rb"(\d{3,6})", window_bytes)
                if match:
                    value = int(match.group(1))
                    if 256 <= value <= 262144:
                        return value
        except Exception:
            return 8192

        return 8192

    def list_cached_models(self) -> list[CachedModel]:
        """List cached GGUF models in cache directory."""
        models: list[CachedModel] = []
        for gguf_path in sorted(self.cache_dir.glob("*.gguf")):
            try:
                stat_result = gguf_path.stat()
                models.append(
                    CachedModel(
                        name=gguf_path.name,
                        path=gguf_path,
                        size_bytes=stat_result.st_size,
                        modified_unix_s=stat_result.st_mtime,
                        context_size=self.get_model_context_size(gguf_path),
                    )
                )
            except OSError:
                continue

        models.sort(key=lambda item: item.modified_unix_s, reverse=True)
        return models

    def prune_cache(self, max_total_size_bytes: int, max_models_count: int) -> int:
        """Apply LRU-style pruning and return number of removed files."""
        if max_total_size_bytes <= 0 and max_models_count <= 0:
            return 0

        models = self.list_cached_models()
        models.sort(key=lambda item: item.modified_unix_s)

        total_size_bytes = sum(item.size_bytes for item in models)
        removed_count = 0
        while models:
            over_size = (
                max_total_size_bytes > 0 and total_size_bytes > max_total_size_bytes
            )
            over_count = max_models_count > 0 and len(models) > max_models_count
            if not over_size and not over_count:
                break

            oldest_model = models.pop(0)
            try:
                oldest_model.path.unlink(missing_ok=True)
                total_size_bytes -= oldest_model.size_bytes
                removed_count += 1
            except OSError:
                continue

        return removed_count

    def _detect_gpu_nvidia_vram_mb(self) -> int:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.total",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=3,
            )
            if result.returncode != 0:
                return 0
            values = [
                int(line.strip()) for line in result.stdout.splitlines() if line.strip()
            ]
            return max(values) if values else 0
        except Exception:
            return 0

    def _detect_gpu_rocm_vram_mb(self) -> int:
        commands = [
            ["rocm-smi", "--showmeminfo", "vram"],
            ["amd-smi", "list", "--json"],
        ]
        for command in commands:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=4,
                )
                if result.returncode != 0:
                    continue

                matches = re.findall(r"(\d+)\s*MB", result.stdout, re.IGNORECASE)
                if matches:
                    return max(int(match) for match in matches)

                bytes_matches = re.findall(r"(\d{8,})", result.stdout)
                if bytes_matches:
                    return max(int(value) // (1024 * 1024) for value in bytes_matches)
            except Exception:
                continue
        return 0

    def _detect_gpu_vulkan_vram_mb(self) -> int:
        try:
            result = subprocess.run(
                ["vulkaninfo", "--summary"],
                capture_output=True,
                text=True,
                check=False,
                timeout=4,
            )
            if result.returncode != 0:
                return 0

            mb_matches = re.findall(r"(\d+)\s*MB", result.stdout, re.IGNORECASE)
            if mb_matches:
                return max(int(match) for match in mb_matches)

            bytes_matches = re.findall(
                r"(\d{8,})\s*bytes", result.stdout, re.IGNORECASE
            )
            if bytes_matches:
                return max(int(match) // (1024 * 1024) for match in bytes_matches)
        except Exception:
            return 0

        return 0

    def _resolve_llama_cpp_root(self) -> Path:
        env_root_raw = os.environ.get("LLAMA_CPP_ROOT", "").strip()
        if env_root_raw:
            env_root = Path(env_root_raw)
            resolved_env_root = env_root.expanduser().resolve()
            if resolved_env_root.exists():
                return resolved_env_root

        candidates = [
            (Path.home() / "llama.cpp").resolve(),
            (Path.cwd() / "llama.cpp").resolve(),
        ]
        for candidate in candidates:
            if candidate.exists() and (candidate / "convert_hf_to_gguf.py").exists():
                return candidate

        return (Path.home() / "llama.cpp").resolve()

    def _huggingface_cli_command(self) -> list[str]:
        binary_path = shutil.which("huggingface-cli")
        if binary_path:
            return [binary_path]

        hf_binary_path = shutil.which("hf")
        if hf_binary_path:
            return [hf_binary_path]

        module_check = subprocess.run(
            [sys.executable, "-c", "import huggingface_hub"],
            capture_output=True,
            text=True,
            check=False,
        )
        if module_check.returncode == 0:
            return [sys.executable, "-m", "huggingface_hub.cli.hf"]

        raise RuntimeError(
            "HuggingFace CLI is not available. Install with: pip install --user huggingface_hub"
        )
