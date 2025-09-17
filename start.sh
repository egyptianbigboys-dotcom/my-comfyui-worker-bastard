#!/usr/bin/env bash
set -euo pipefail

export COMFY_DIR="/workspace/ComfyUI"
export DATA_DIR="/runpod-volume"

# --- First-boot installer (idempotent) ---
bash /workspace/scripts/first_boot.sh

# --- Start ComfyUI headless on 0.0.0.0:8188 ---
python3 "${COMFY_DIR}/main.py" \
  --listen 0.0.0.0 \
  --port 8188 \
  --output-directory /workspace/outputs \
  --input-directory /workspace/inputs \
  > /workspace/comfyui.log 2>&1 &

# --- Wait for ComfyUI HTTP to come up ---
python3 /workspace/scripts/healthcheck.py --url http://127.0.0.1:8188 --retries 60 --delay 1

# --- Start RunPod Serverless handler (blocks) ---
python3 /workspace/handler.py
