"""Audio helpers for safetensors websocket server."""

from __future__ import annotations

import base64
from dataclasses import dataclass

import numpy as np


@dataclass
class AudioFeatures:
    duration_s: float
    rms: float
    peak: float
    zero_crossing_rate: float


class AudioProcessor:
    def __init__(self, sample_rate_hz: int = 24000):
        self._sample_rate_hz = sample_rate_hz
        self._audio_bytes = bytearray()

    def clear(self) -> None:
        self._audio_bytes = bytearray()

    def append_base64_pcm16(self, audio_base64: str) -> None:
        if not audio_base64:
            return
        chunk_bytes = base64.b64decode(audio_base64)
        if chunk_bytes:
            self._audio_bytes.extend(chunk_bytes)

    def commit_features(self) -> AudioFeatures | None:
        audio_f32 = self._decode_pcm16_to_float32(bytes(self._audio_bytes))
        self.clear()
        if audio_f32.size == 0:
            return None
        return self._extract_features(audio_f32)

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
