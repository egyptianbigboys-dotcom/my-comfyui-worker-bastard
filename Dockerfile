# Use official Python image
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY handler.py .
COPY download_models.sh .
COPY Flux_Ace++FaceSwap_DatingAPPsDaddy-Patreon_v4.json ./workflow.json

# Create models directories
RUN mkdir -p /app/models/unet /app/models/loras /app/models/vae

# Download models
RUN curl -L -o /app/models/unet/unet.safetensors "https://civitai.com/api/download/models/1085456?type=Model&format=SafeTensor&size=full&fp=fp8" && \
    curl -L -o /app/models/loras/comfyui_portrait_lora64.safetensors "https://huggingface.co/ali-vilab/ACE_Plus/resolve/main/portrait/comfyui_portrait_lora64.safetensors?download=true" && \
    curl -L -o /app/models/loras/flux1-turbo-alpha.safetensors "https://civitai.com/api/download/models/981081?type=Model&format=SafeTensor" && \
    curl -L -o /app/models/vae/ae.safetensors "https://huggingface.co/lovis93/testllm/resolve/main/ae.safetensors"

# Runpod handler
CMD ["python", "-u", "handler.py"]
