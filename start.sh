#!/usr/bin/env bash
set -euo pipefail

# Paths used everywhere
export COMFY_DIR="/workspace/ComfyUI"
export DATA_DIR="/runpod-volume"   # Serverless network volume mount. Verified by docs. 

echo "[start] COMFY_DIR=$COMFY_DIR"
echo "[start] DATA_DIR=$DATA_DIR"

# 1) Optional first-boot installer (will run later in Step 8)
if [ -x "/workspace/scripts/first_boot.sh" ]; then
  echo "[start] running first_boot.sh"
  bash /workspace/scripts/first_boot.sh
else
  echo "[start] first_boot.sh not present yet — skipping (that’s OK for now)"
fi

# 2) Start ComfyUI headless
echo "[start] launching ComfyUI..."
python3 "${COMFY_DIR}/main.py" \
  --listen 0.0.0.0 \
  --port 8188 \
  --output-directory /workspace/outputs \
  --input-directory /workspace/inputs \
  > /workspace/comfyui.log 2>&1 &

# 3) Wait for ComfyUI HTTP to come up (simple curl loop, no extra deps)
echo "[start] waiting for ComfyUI on :8188 ..."
for i in $(seq 1 60); do
  if curl -sSf "http://127.0.0.1:8188" >/dev/null 2>&1; then
    echo "[start] ComfyUI is up."
    break
  fi
  sleep 1
  if [ "$i" -eq 60 ]; then
    echo "[start] ERROR: ComfyUI did not start within 60s"
    exit 1
  fi
done

# 4) Start RunPod Serverless handler (blocks)
echo "[start] starting handler..."
python3 /workspace/handler.py
