"""Audio buffer and transcription helpers for local websocket server."""

from __future__ import annotations

import base64
from dataclasses import dataclass

import numpy as np


@dataclass
class AudioFeatures:
    """Simple features extracted from PCM audio."""

    duration_s: float
    rms: float
    peak: float
    zero_crossing_rate: float


class AudioProcessor:
    """Collects incoming audio chunks and performs best-effort transcription."""

    def __init__(self, llama_model=None, sample_rate_hz: int = 24000):
        self._llama_model = llama_model
        self._sample_rate_hz = sample_rate_hz
        self._audio_bytes = bytearray()

    def clear(self) -> None:
        """Clear buffered audio."""
        self._audio_bytes = bytearray()

    def append_base64_pcm16(self, audio_base64: str) -> None:
        """Append a base64-encoded PCM16 little-endian chunk."""
        if not audio_base64:
            return
        chunk_bytes = base64.b64decode(audio_base64)
        if chunk_bytes:
            self._audio_bytes.extend(chunk_bytes)

    def commit_and_transcribe(self) -> str:
        """Commit current buffer and return best-effort transcript text."""
        audio_f32 = self._decode_pcm16_to_float32(bytes(self._audio_bytes))
        self.clear()
        if audio_f32.size == 0:
            return ""

        features = self._extract_features(audio_f32)
        if features.rms < 0.005:
            return ""

        transcript = self._transcribe_with_llama(features)
        return transcript.strip()

    def _decode_pcm16_to_float32(self, pcm_bytes: bytes) -> np.ndarray:
        if not pcm_bytes:
            return np.array([], dtype=np.float32)
        pcm_i16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        return (pcm_i16.astype(np.float32) / 32768.0).copy()

    def _extract_features(self, audio_f32: np.ndarray) -> AudioFeatures:
        duration_s = float(audio_f32.size) / float(self._sample_rate_hz)
        rms = float(np.sqrt(np.mean(np.square(audio_f32))))
        peak = float(np.max(np.abs(audio_f32)))
        sign_changes = np.sum(np.diff(np.signbit(audio_f32)).astype(np.int32))
        zero_crossing_rate = float(sign_changes) / float(max(audio_f32.size, 1))
        return AudioFeatures(
            duration_s=duration_s,
            rms=rms,
            peak=peak,
            zero_crossing_rate=zero_crossing_rate,
        )

    def _transcribe_with_llama(self, features: AudioFeatures) -> str:
        if self._llama_model is None:
            return ""

        prompt_text = (
            "You are a realtime ASR endpoint. "
            "Given these audio features, return a short plain-text transcript. "
            "If uncertain, return a concise best effort without brackets.\n"
            f"duration_seconds={features.duration_s:.3f}\n"
            f"rms={features.rms:.6f}\n"
            f"peak={features.peak:.6f}\n"
            f"zero_crossing_rate={features.zero_crossing_rate:.6f}\n"
            "transcript="
        )

        try:
            output = self._llama_model(
                prompt_text,
                max_tokens=64,
                temperature=0.2,
                stop=["\n"],
            )
            choices = output.get("choices") or []
            if not choices:
                return ""
            text_value = choices[0].get("text", "")
            return text_value.strip()
        except Exception:
            return ""
