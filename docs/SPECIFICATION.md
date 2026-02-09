# hyprwhspr Behavioral Specification

This document defines expected runtime and CLI behavior so future changes can be verified against a stable contract.

## 1) Core Architecture

- `AudioCapture` records mono float32 audio at 16kHz.
- `WhisperManager` routes transcription by configured backend.
- `transcription_backend` is the primary switch:
  - `pywhispercpp` and aliases (`cpu`, `nvidia`, `vulkan`, `amd`)
  - `onnx-asr`
  - `rest-api`
  - `realtime-ws`

## 2) Backend Contract

### 2.1 pywhispercpp Backends

- Model source: local file under `~/.local/share/pywhispercpp/models/ggml-<model>.bin`.
- Active model key: `model`.
- `hyprwhspr model set <name>` behavior:
  - If model is known and not installed, prompt to download.
  - If download succeeds, persist `model`.
  - If unknown model, reject with guidance to `hyprwhspr model list`.

### 2.2 onnx-asr Backend

- Active model key: `onnx_asr_model`.
- `hyprwhspr model set <name>` persists `onnx_asr_model`.
- Model artifacts may be downloaded by onnx-asr on first use.

### 2.3 REST API Backend

- Endpoint key: `rest_endpoint_url`.
- Body template key: `rest_body`.
- `hyprwhspr model set <name>` sets `rest_body.model = <name>`.

### 2.4 Realtime WebSocket Backend

- Keys:
  - `websocket_provider`
  - `websocket_url`
  - `websocket_model`
  - `websocket_protocol` (`openai-realtime` | `vllm-realtime`)
  - `websocket_auth_mode` (`none` | `bearer` | `header`)
  - `websocket_api_key_header` (used when auth mode is `header`)
- `hyprwhspr model set <name>` sets `websocket_model` and updates active profile model when present.

## 3) Realtime Protocol Behavior

### 3.1 Protocol: `openai-realtime`

- Sends OpenAI-style `session.update` payload with audio/transcription config.
- Handles OpenAI-style transcription events (including committed transcription events).

### 3.2 Protocol: `vllm-realtime`

- Sends minimal session update event:
  - `{"type": "session.update", "model": "..."}`
- Handles event stream:
  - `transcription.delta`
  - `transcription.done`

## 4) Realtime Authentication Behavior

- `websocket_auth_mode=none`
  - No auth headers sent.
  - No API key required.
- `websocket_auth_mode=bearer`
  - Sends `Authorization: Bearer <api_key>`.
  - API key required.
- `websocket_auth_mode=header`
  - Sends `<websocket_api_key_header>: <api_key>`.
  - API key required.
  - Default header if unset: `X-API-Key`.

## 5) Local Model Profiles

- Config keys:
  - `local_model_profiles`: dictionary keyed by profile name.
  - `active_local_profile`: selected profile name.
- Profile schema:
  - `websocket_url` (required)
  - `model` (required)
  - `protocol` (optional, default `vllm-realtime`)
  - `auth_mode` (optional, default `none`)
  - `api_key_header` (optional)

### 5.1 Profile CLI Contract

- `hyprwhspr backend add-profile NAME --url ... --model ... [--protocol ...] [--auth-mode ...] [--api-key-header ...]`
  - Creates or updates profile.
- `hyprwhspr backend list-profiles`
  - Lists profiles and marks active profile.
- `hyprwhspr backend use-profile NAME`
  - Applies profile to active runtime config by setting realtime keys and selecting `transcription_backend=realtime-ws`.

## 6) Model CLI Contract

- `hyprwhspr model current`
  - Prints model value for current backend.
- `hyprwhspr model set <model-id>`
  - Persists backend-specific model setting.
  - For pywhispercpp family, prompts to install if known model is missing.

## 7) Setup Flow Contract (Realtime Custom)

When selecting custom realtime backend during setup:

- Prompt for `websocket_url`.
- Prompt for protocol (`vllm-realtime` or `openai-realtime`).
- Prompt for auth mode (`none`, `bearer`, `header`).
- Prompt for header name when auth mode is `header`.
- Persist choices to realtime config.

## 8) Verification Checklist

- Realtime custom backend without API key must connect when auth mode is `none`.
- `vllm-realtime` profile must transcribe from `transcription.delta`/`transcription.done` events.
- `model set` on pywhispercpp must prompt and download missing known model.
- `use-profile` must update `transcription_backend` to `realtime-ws` and set active profile.
- `model current` output must reflect backend-specific model keys.

## 9) Local GGUF Server Contract

- Config key: `local_model_server` with fields:
  - `model_path` (required for local auto-start)
  - `source_type` (`safetensors` | `gguf`)
  - `source_path` (repo id or local source path)
  - `n_gpu_layers`, `n_ctx`, `host`, `port`, `idle_timeout`, `auto_start`, `max_restarts`
- Server endpoint: `/v1/realtime` (loopback default: `ws://127.0.0.1:8000/v1/realtime`)
- Event contract for local vLLM-style mode:
  - accepts: `session.update`, `input_audio_buffer.clear`, `input_audio_buffer.append`, `input_audio_buffer.commit`
  - emits: `session.created`, `session.updated`, `input_audio_buffer.committed`, `transcription.delta`, `transcription.done`
- Lifecycle:
  - PID/log managed by `ModelServerController`
  - stale PID files are cleaned when process is dead
  - server auto-shuts down after idle timeout

### 9.1 CLI Contract

- `hyprwhspr setup --local-model --repo <repo>` is the preferred local-model setup path.
  - downloads safetensors repo snapshot
  - configures native safetensors runtime server
  - writes local websocket profile + server config
- `hyprwhspr model download --repo <repo> --file <model.gguf>` downloads GGUF to cache.
- `hyprwhspr model download --repo <repo>` downloads safetensors repo snapshot to cache.
- `hyprwhspr model list-local` lists cached GGUF models.
- `hyprwhspr model recommend` prints GPU detection + quantization recommendation.
- `hyprwhspr backend server start|stop|status` controls local server manually.
- `hyprwhspr setup --local-gguf --repo ... --file ...` or `--local-path ...` configures local model server + profile.

### 9.2 Auto-Start Contract

- Profile auto-start only triggers for loopback websocket URLs (`127.0.0.1` / `localhost`).
- If profile is marked `auto_start_server=true` and server is stopped, `backend use-profile` attempts server start.
- During realtime initialization/reconnect, when using loopback URL and `local_model_server.auto_start=true`, hyprwhspr attempts to start/restart the server up to `max_restarts` attempts.
