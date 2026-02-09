"""FastAPI websocket server for local GGUF realtime transcription."""

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

from audio_processor import AudioProcessor

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None


@dataclass
class ServerConfig:
    """Runtime server config."""

    model_path: str
    host: str
    port: int
    idle_timeout_s: int
    n_gpu_layers: int
    n_ctx: int


SERVER_CONFIG: ServerConfig | None = None
APP_STATE = {
    "llama_model": None,
    "last_activity_unix_s": time.time(),
    "shutdown_requested": False,
}

app = FastAPI()


def _build_config_from_args() -> ServerConfig:
    parser = argparse.ArgumentParser(
        description="hyprwhspr local GGUF websocket server"
    )
    parser.add_argument("--model-path", required=True, help="Path to GGUF model")
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
        "--n-gpu-layers",
        type=int,
        default=int(os.environ.get("HYPRWHSPR_N_GPU_LAYERS", "-1")),
    )
    parser.add_argument(
        "--n-ctx",
        type=int,
        default=int(os.environ.get("HYPRWHSPR_N_CTX", "8192")),
    )

    parsed_args = parser.parse_args()
    return ServerConfig(
        model_path=parsed_args.model_path,
        host=parsed_args.host,
        port=parsed_args.port,
        idle_timeout_s=max(30, parsed_args.idle_timeout),
        n_gpu_layers=parsed_args.n_gpu_layers,
        n_ctx=max(512, parsed_args.n_ctx),
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
    if Llama is None:
        raise RuntimeError("llama-cpp-python is required for local_ws_server")

    APP_STATE["llama_model"] = Llama(
        model_path=SERVER_CONFIG.model_path,
        n_gpu_layers=SERVER_CONFIG.n_gpu_layers,
        n_ctx=SERVER_CONFIG.n_ctx,
        verbose=False,
    )
    asyncio.create_task(_idle_shutdown_watcher())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    APP_STATE["shutdown_requested"] = True
    APP_STATE["llama_model"] = None


@app.websocket("/v1/realtime")
async def realtime_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    APP_STATE["last_activity_unix_s"] = time.time()

    processor = AudioProcessor(
        llama_model=APP_STATE.get("llama_model"), sample_rate_hz=24000
    )
    await websocket.send_json({"type": "session.created"})

    try:
        while True:
            message_text = await websocket.receive_text()
            APP_STATE["last_activity_unix_s"] = time.time()

            try:
                event_data = json.loads(message_text)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": {"message": "Invalid JSON payload"},
                    }
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
                transcript_text = processor.commit_and_transcribe()
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


def main() -> None:
    global SERVER_CONFIG
    SERVER_CONFIG = _build_config_from_args()
    uvicorn.run(app, host=SERVER_CONFIG.host, port=SERVER_CONFIG.port, log_level="info")


if __name__ == "__main__":
    main()
