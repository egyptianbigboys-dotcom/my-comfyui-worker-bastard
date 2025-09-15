import runpod
import json
import subprocess
import os


# Load your workflow JSON once at startup
WORKFLOW_PATH = "Flux_Ace++_FaceSwap_DatingAPPsDaddy-Patreon_v4.json"

with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
    WORKFLOW_JSON = json.load(f)


def run_comfyui(input_data):
    """
    Runs ComfyUI workflow with given input parameters.
    input_data is the 'input' field of the request.
    """

    # TODO: Here you plug input_data into workflow.json if you want dynamic changes
    workflow_file = "temp_workflow.json"
    with open(workflow_file, "w", encoding="utf-8") as f:
        json.dump(WORKFLOW_JSON, f)

    # Run ComfyUI CLI (assuming installed in Docker image)
    result = subprocess.run(
        ["python3", "main.py", "--workflow", workflow_file],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {"error": result.stderr}

    # For now we just return success (later you can return the generated image path)
    return {"output": "Workflow executed successfully."}


# This is the handler RunPod calls
def handler(event):
    """
    event = {
      "input": { ... user parameters ... }
    }
    """
    input_data = event.get("input", {})
    result = run_comfyui(input_data)
    return result


# Start the worker
runpod.serverless.start({"handler": handler}) 
