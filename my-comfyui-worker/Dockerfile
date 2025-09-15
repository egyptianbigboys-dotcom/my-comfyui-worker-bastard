# ==============================
# Dockerfile for ComfyUI Worker
# ==============================

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git wget curl libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git .
WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create custom folders
RUN mkdir -p /app/models/unet \
    /app/models/loras \
    /app/models/vae \
    /app/workflows

# Download models
# --- UNET ---
RUN wget -O /app/models/unet/unet.safetensors "https://civitai.com/api/download/models/1085456?type=Model&format=SafeTensor&size=full&fp=fp8"

# --- LORAS ---
RUN wget -O /app/models/loras/portrait_lora64.safetensors "https://huggingface.co/ali-vilab/ACE_Plus/resolve/main/portrait/comfyui_portrait_lora64.safetensors?download=true"
RUN wget -O /app/models/loras/extra_lora.safetensors "https://civitai.com/api/download/models/981081?type=Model&format=SafeTensor"

# --- VAE ---
RUN wget -O /app/models/vae/ae.safetensors "https://huggingface.co/lovis93/testllm/resolve/main/ae.safetensors"

# Copy workflow into the container
COPY Flux_Ace++FaceSwap_DatingAPPsDaddy-Patreon_v4.json /app/workflows/

# Default command
CMD ["python", "main.py", "--listen", "0.0.0.0", "--port", "8188"]
