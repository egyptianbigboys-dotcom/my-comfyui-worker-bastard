import runpod
import json
import os

# Path to workflow JSON
WORKFLOW_PATH = os.path.join(os.path.dirname(__file__), "Flux_Ace++_FaceSwap_DatingAPPsDaddy-Patreon_v4.json")

# Load workflow once at startup
try:
    with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
        WORKFLOW = json.load(f)
except FileNotFoundError:
    WORKFLOW = None

def handler(job):
    """
    RunPod handler — receives input from API call and processes it.
    Right now, it just loads the workflow and returns the input.
    Later you can plug this into ComfyUI for real face-swapping.
    """
    inp = job["input"]

    if WORKFLOW is None:
        return {"error": "Workflow JSON not found inside container."}

    return {
        "status": "success",
        "workflow_loaded": True,
        "workflow_name": os.path.basename(WORKFLOW_PATH),
        "input_received": inp
    }

# Start the serverless worker
runpod.serverless.start({"handler": handler})
