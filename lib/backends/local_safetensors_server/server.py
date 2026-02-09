"""FastAPI websocket server for local safetensors realtime transcription."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import time
from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from audio_processor import AudioFeatures, AudioProcessor

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ImportError:
    torch = None
    AutoModelForCausalLM = None
    AutoTokenizer = None


@dataclass
class ServerConfig:
    model_path: str
    host: str
    port: int
    idle_timeout_s: int
    max_new_tokens: int


SERVER_CONFIG: ServerConfig | None = None
APP_STATE = {
    "tokenizer": None,
    "model": None,
    "last_activity_unix_s": time.time(),
    "shutdown_requested": False,
}

app = FastAPI()


def _build_config_from_args() -> ServerConfig:
    parser = argparse.ArgumentParser(
        description="hyprwhspr local safetensors websocket server"
    )
    parser.add_argument(
        "--model-path", required=True, help="Path to local model directory"
    )
    parser.add_argument(
        "--host", default=os.environ.get("HYPRWHSPR_SERVER_HOST", "127.0.0.1")
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("HYPRWHSPR_SERVER_PORT", "8000"))
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=int(os.environ.get("HYPRWHSPR_IDLE_TIMEOUT", "300")),
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=64,
    )
    parsed = parser.parse_args()
    return ServerConfig(
        model_path=parsed.model_path,
        host=parsed.host,
        port=parsed.port,
        idle_timeout_s=max(30, parsed.idle_timeout),
        max_new_tokens=max(16, parsed.max_new_tokens),
    )


async def _idle_shutdown_watcher() -> None:
    while not APP_STATE["shutdown_requested"]:
        await asyncio.sleep(1.0)
        idle_timeout_s = SERVER_CONFIG.idle_timeout_s if SERVER_CONFIG else 300
        elapsed_s = time.time() - float(APP_STATE["last_activity_unix_s"])
        if elapsed_s > idle_timeout_s:
            APP_STATE["shutdown_requested"] = True
            os.kill(os.getpid(), signal.SIGTERM)


@app.on_event("startup")
async def startup_event() -> None:
    if SERVER_CONFIG is None:
        raise RuntimeError("Server config not initialized")
    if torch is None or AutoModelForCausalLM is None or AutoTokenizer is None:
        raise RuntimeError(
            "transformers + torch are required for local safetensors server"
        )

    model_dir = SERVER_CONFIG.model_path
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    device_map = "auto" if torch.cuda.is_available() else None
    APP_STATE["tokenizer"] = AutoTokenizer.from_pretrained(
        model_dir, trust_remote_code=True
    )
    APP_STATE["model"] = AutoModelForCausalLM.from_pretrained(
        model_dir,
        torch_dtype=dtype,
        device_map=device_map,
        trust_remote_code=True,
    )
    asyncio.create_task(_idle_shutdown_watcher())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    APP_STATE["shutdown_requested"] = True
    APP_STATE["tokenizer"] = None
    APP_STATE["model"] = None


@app.websocket("/v1/realtime")
async def realtime_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    APP_STATE["last_activity_unix_s"] = time.time()
    processor = AudioProcessor(sample_rate_hz=24000)
    await websocket.send_json({"type": "session.created"})

    try:
        while True:
            message_text = await websocket.receive_text()
            APP_STATE["last_activity_unix_s"] = time.time()

            try:
                event_data = json.loads(message_text)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "error": {"message": "Invalid JSON"}}
                )
                continue

            event_type = event_data.get("type")
            if event_type == "session.update":
                await websocket.send_json({"type": "session.updated"})
                continue

            if event_type == "input_audio_buffer.clear":
                processor.clear()
                await websocket.send_json({"type": "input_audio_buffer.cleared"})
                continue

            if event_type == "input_audio_buffer.append":
                processor.append_base64_pcm16(event_data.get("audio", ""))
                continue

            if event_type == "input_audio_buffer.commit":
                await websocket.send_json({"type": "input_audio_buffer.committed"})
                features = processor.commit_features()
                transcript_text = _infer_transcript_from_features(features)
                if transcript_text:
                    await websocket.send_json(
                        {"type": "transcription.delta", "delta": transcript_text}
                    )
                await websocket.send_json(
                    {"type": "transcription.done", "text": transcript_text}
                )
                continue

            await websocket.send_json(
                {
                    "type": "error",
                    "error": {"message": f"Unsupported event type: {event_type}"},
                }
            )
    except WebSocketDisconnect:
        return


def _infer_transcript_from_features(features: AudioFeatures | None) -> str:
    if features is None:
        return ""
    if features.rms < 0.005:
        return ""

    tokenizer = APP_STATE.get("tokenizer")
    model = APP_STATE.get("model")
    if tokenizer is None or model is None:
        return ""

    prompt_text = (
        "You are a realtime ASR endpoint. "
        "Given these audio features, return only a short plain-text transcript. "
        "If uncertain, return a concise best effort without brackets.\n"
        f"duration_seconds={features.duration_s:.3f}\n"
        f"rms={features.rms:.6f}\n"
        f"peak={features.peak:.6f}\n"
        f"zero_crossing_rate={features.zero_crossing_rate:.6f}\n"
        "transcript="
    )

    try:
        inputs = tokenizer(prompt_text, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {key: value.to(device) for key, value in inputs.items()}
        output_tokens = model.generate(
            **inputs,
            max_new_tokens=SERVER_CONFIG.max_new_tokens if SERVER_CONFIG else 64,
            do_sample=False,
        )
        generated_tokens = output_tokens[0][inputs["input_ids"].shape[1] :]
        text_value = tokenizer.decode(
            generated_tokens, skip_special_tokens=True
        ).strip()
        return text_value
    except Exception:
        return ""


def main() -> None:
    global SERVER_CONFIG
    SERVER_CONFIG = _build_config_from_args()
    uvicorn.run(app, host=SERVER_CONFIG.host, port=SERVER_CONFIG.port, log_level="info")


if __name__ == "__main__":
    main()
