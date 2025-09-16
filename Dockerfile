FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 python3-pip wget git curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --upgrade pip
RUN pip3 install runpod

# Copy workflow JSON into container
COPY DatingAPPsDaddy.json /app/

# Download models into correct folders
RUN mkdir -p /app/models/unet /app/models/loras /app/models/vae

# Unet
RUN wget -O /app/models/unet/unet.safetensors \
  "https://civitai.com/api/download/models/1085456?type=Model&format=SafeTensor&size=full&fp=fp8"

# Loras (HuggingFace)
RUN wget -O /app/models/loras/portrait_lora64.safetensors \
  "https://huggingface.co/ali-vilab/ACE_Plus/resolve/main/portrait/comfyui_portrait_lora64.safetensors?download=true"

# Loras (Civitai)
RUN wget -O /app/models/loras/loras_extra.safetensors \
  "https://civitai.com/api/download/models/981081?type=Model&format=SafeTensor"

# VAE
RUN wget -O /app/models/vae/vae.safetensors \
  "https://huggingface.co/lovis93/testllm/resolve/main/ae.safetensors"

# Copy handler
COPY handler.py /app/

# Run handler on container start
CMD ["python3", "handler.py"]

