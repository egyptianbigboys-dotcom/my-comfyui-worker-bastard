# --------------------------
# ComfyUI RunPod Serverless
# --------------------------

# 1) Base image with CUDA + Python (match RunPod GPU environment)
FROM runpod/pytorch:3.10-2.0.1-118

# 2) Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WORKSPACE=/workspace

WORKDIR $WORKSPACE

# 3) Install system dependencies
RUN apt-get update && apt-get install -y \
    git wget curl zip \
    && rm -rf /var/lib/apt/lists/*

# 4) Install ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git ComfyUI

# 5) Install Python requirements
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r ComfyUI/requirements.txt \
    && pip install runpod

# 6) Copy repo files into container
COPY . $WORKSPACE

# Ensure scripts are executable
RUN chmod +x $WORKSPACE/*.sh

# 7) Expose ComfyUI port
EXPOSE 8188

# 8) Entrypoint
CMD ["bash", "start.sh"]
