FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    COMFY_DIR=/workspace/ComfyUI \
    DATA_DIR=/runpod-volume \
    HF_HOME=/workspace/.cache/huggingface

# --- System deps ---
RUN apt-get update && apt-get install -y \
    git wget curl ca-certificates python3 python3-pip python3-venv \
    ffmpeg libgl1 libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# --- Python deps (base) ---
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# --- Get ComfyUI ---
RUN mkdir -p /workspace && \
    git clone --depth=1 https://github.com/comfyanonymous/ComfyUI ${COMFY_DIR}

# --- Add our repo content ---
WORKDIR /workspace
COPY comfyui/extra_model_paths.yaml /workspace/comfyui/extra_model_paths.yaml
COPY comfyui/workflows/APIAutoFaceACE.json ${COMFY_DIR}/workflows/APIAutoFaceACE.json

COPY custom_nodes.txt /workspace/custom_nodes.txt
COPY models_manifest.json /workspace/models_manifest.json

COPY scripts/ /workspace/scripts/
RUN chmod +x /workspace/scripts/first_boot.sh

# --- Your handler + start script ---
COPY handler.py /workspace/handler.py
COPY start.sh /workspace/start.sh
RUN chmod +x /workspace/start.sh

# --- Expose ComfyUI port (internal) ---
EXPOSE 8188

CMD ["/workspace/start.sh"]
