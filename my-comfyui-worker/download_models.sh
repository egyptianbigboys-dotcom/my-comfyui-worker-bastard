#!/bin/bash
set -e

# Create model folders if they don’t exist
mkdir -p models/unet
mkdir -p models/loras
mkdir -p models/vae

echo "Downloading models..."

# UNet (Diffusion Model)
wget -O models/unet/flux_fill_fp8.safetensors "https://civitai.com/api/download/models/1085456?type=Model&format=SafeTensor&size=full&fp=fp8"

# Loras
wget -O models/loras/comfyui_portrait_lora64.safetensors "https://huggingface.co/ali-vilab/ACE_Plus/resolve/main/portrait/comfyui_portrait_lora64.safetensors?download=true"
wget -O models/loras/flux_turbo_alpha.safetensors "https://civitai.com/api/download/models/981081?type=Model&format=SafeTensor"

# VAE
wget -O models/vae/ae.safetensors "https://huggingface.co/lovis93/testllm/resolve/main/ae.safetensors"

echo "✅ All models downloaded successfully!"
