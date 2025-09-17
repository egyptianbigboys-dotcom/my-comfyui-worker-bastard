#!/usr/bin/env python3
import base64
import io
import json
import os
import time
import typing as T
from dataclasses import dataclass

import requests
import runpod

# --------- Config ---------
COMFY_URL = os.environ.get("COMFY_URL", "http://127.0.0.1:8188")
WORKFLOW_PATH = "/workspace/comfyui/workflows/APIAutoFaceACE.json"
UPLOAD_ENDPOINT = f"{COMFY_URL}/upload/image"
PROMPT_ENDPOINT = f"{COMFY_URL}/prompt"
HISTORY_ENDPOINT = f"{COMFY_URL}/history"
VIEW_ENDPOINT = f"{COMFY_URL}/view"  # /view?filename=xxx&subfolder=yyy&type=output
HTTP_TIMEOUT = (5, 60)  # connect, read timeouts

# --------- Helpers ---------
def _b64_to_bytes(b64_str: str) -> bytes:
    b64_str = b64_str.strip()
    # Allow data URI
    if b64_str.startswith("data:"):
        b64_str = b64_str.split(",", 1)[1]
    return base64.b64decode(b64_str)

def _get_bytes_from_url(url: str) -> bytes:
    r = requests.get(url, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    return r.content

def _upload_image_to_comfy(name_hint: str, data: bytes) -> str:
    """
    Upload an image to ComfyUI /upload/image and return the stored filename
    that should be used in 'LoadImage' node's 'image' input.
    """
    files = {"image": (name_hint, io.BytesIO(data), "application/octet-stream")}
    r = requests.post(UPLOAD_ENDPOINT, files=files, timeout=HTTP_TIMEOUT)
    # On success, ComfyUI returns JSON like {"name": "yourfile.png"}
    try:
        r.raise_for_status()
        js = r.json()
        # ComfyUI sometimes returns list or dict depending on version; handle both
        if isinstance(js, dict) and "name" in js:
            return js["name"]
        if isinstance(js, list) and js and isinstance(js[0], dict) and "name" in js[0]:
            return js[0]["name"]
        # Fallback: plain text or unexpected shape
        if isinstance(js, str):
            return js
        raise RuntimeError(f"Unexpected upload response: {js}")
    except Exception:
        # Some builds return text/plain with the saved filename
        if r.status_code == 200 and r.text.strip():
            return r.text.strip()
        raise

def _load_workflow(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Workflow not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _find_image_input_nodes(workflow: dict) -> T.List[T.Tuple[str, dict]]:
    """
    Heuristic: find nodes that likely accept image filenames.
    We scan for nodes whose inputs contain an 'image' key (string).
    Returns list of (node_id, node_dict) preserving workflow order.
    """
    candidates = []
    # Workflow format: {"last_node_id": ..., "nodes": {"<id>": {"class_type": "...", "inputs": {...}}}}
    nodes = workflow.get("nodes") or workflow  # support both flattened or nested shapes
    if isinstance(nodes, dict):
        iterable = nodes.items()
    else:
        # Some exports keep as list [{"id": "N123", "class_type": "...", "inputs": {...}}, ...]
        iterable = ((str(n.get("id", idx)), n) for idx, n in enumerate(nodes))

    for node_id, node in iterable:
        inputs = node.get("inputs", {}) if isinstance(node, dict) else {}
        if not isinstance(inputs, dict):
            continue
        # If the node has a string 'image' input -> it's likely a LoadImage-like node
        # Also allow variants like 'image1', 'image2'
        for key in inputs.keys():
            if key.lower().startswith("image"):
                # keep once per node
                candidates.append((node_id, node))
                break
    return candidates

def _inject_filenames(
    workflow: dict,
    mapping: T.List[T.Tuple[str, str, str]]  # list of (node_id, input_key, filename)
) -> dict:
    # Mutate in-place
    updated = 0
    nodes = workflow.get("nodes") or workflow
    if isinstance(nodes, dict):
        for node_id, input_key, filename in mapping:
            node = nodes.get(node_id)
            if node and isinstance(node.get("inputs"), dict):
                node["inputs"][input_key] = filename
                updated += 1
    else:
        # list form
        for node_id, input_key, filename in mapping:
            for node in nodes:
                if str(node.get("id")) == str(node_id) and isinstance(node.get("inputs"), dict):
                    node["inputs"][input_key] = filename
                    updated += 1
                    break
    if updated == 0:
        raise RuntimeError("No workflow inputs were updated — check node IDs / keys.")
    return workflow

def _post_prompt(workflow: dict) -> str:
    r = requests.post(PROMPT_ENDPOINT, json=workflow, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    js = r.json()
    prompt_id = js.get("prompt_id") or js.get("promptId") or js.get("id")
    if not prompt_id:
        raise RuntimeError(f"Missing prompt_id in response: {js}")
    return prompt_id

@dataclass
class OutputImage:
    filename: str
    subfolder: str
    type_: str  # "output" etc.

def _wait_for_result(prompt_id: str, timeout_s: int = 180) -> T.List[OutputImage]:
    """
    Poll /history/<id> until images are ready or timeout.
    """
    t0 = time.time()
    while True:
        r = requests.get(f"{HISTORY_ENDPOINT}/{prompt_id}", timeout=HTTP_TIMEOUT)
        if r.status_code == 404:
            # Not yet ready
            time.sleep(0.8)
        else:
            r.raise_for_status()
            js = r.json()
            # ComfyUI returns {"history": {"<id>": {"outputs": {"<node_id>": {"images":[...]}}}}}
            hist = js.get("history") or {}
            entry = hist.get(prompt_id) or {}
            outputs = entry.get("outputs") or {}
            images: T.List[OutputImage] = []
            for node_id, node_out in outputs.items():
                imgs = node_out.get("images") or []
                for im in imgs:
                    images.append(
                        OutputImage(
                            filename=im.get("filename"),
                            subfolder=im.get("subfolder", ""),
                            type_=im.get("type", "output"),
                        )
                    )
            if images:
                return images
            # still running?
            time.sleep(0.8)

        if time.time() - t0 > timeout_s:
            raise TimeoutError(f"ComfyUI did not produce output within {timeout_s}s")

def _download_output_as_b64(img: OutputImage) -> str:
    """
    Fetch output bytes from /view and return base64 string.
    """
    params = {"filename": img.filename}
    if img.subfolder:
        params["subfolder"] = img.subfolder
    if img.type_:
        params["type"] = img.type_
    rr = requests.get(VIEW_ENDPOINT, params=params, timeout=HTTP_TIMEOUT)
    rr.raise_for_status()
    return base64.b64encode(rr.content).decode("utf-8")

# --------- Main RunPod handler ---------
def rp_handler(event):
    """
    Expected input payload in event['input']:

    {
      "source_b64": "<base64 string>",           // OR "source_url": "http(s)://..."
      "target_b64": "<base64 string>",           // OR "target_url": "http(s)://..."
      "node_mapping": {
          "source": {"node_id": "12", "input_key": "image"},
          "target": {"node_id": "34", "input_key": "image"}
      }
    }

    node_mapping is optional. If omitted, we auto-detect the first two image-file inputs.
    """
    try:
        inp = (event or {}).get("input") or {}
        if not inp:
            return {"error": "Missing input payload."}

        # 1) Collect source/target bytes
        if "source_b64" in inp:
            src_bytes = _b64_to_bytes(inp["source_b64"])
        elif "source_url" in inp:
            src_bytes = _get_bytes_from_url(inp["source_url"])
        else:
            return {"error": "Provide 'source_b64' or 'source_url'."}

        if "target_b64" in inp:
            tgt_bytes = _b64_to_bytes(inp["target_b64"])
        elif "target_url" in inp:
            tgt_bytes = _get_bytes_from_url(inp["target_url"])
        else:
            return {"error": "Provide 'target_b64' or 'target_url'."}

        # 2) Upload to ComfyUI input storage and get filenames
        src_name = _upload_image_to_comfy("source.png", src_bytes)
        tgt_name = _upload_image_to_comfy("target.png", tgt_bytes)

        # 3) Load workflow JSON
        workflow = _load_workflow(WORKFLOW_PATH)

        # 4) Determine which nodes to inject the filenames into
        mapping_payload = inp.get("node_mapping")
        inject_plan: T.List[T.Tuple[str, str, str]] = []

        if mapping_payload and isinstance(mapping_payload, dict):
            # explicit mapping
            m_source = mapping_payload.get("source")
            m_target = mapping_payload.get("target")
            if not (m_source and m_target):
                return {"error": "node_mapping must include both 'source' and 'target' entries."}
            inject_plan.append((str(m_source["node_id"]), str(m_source["input_key"]), src_name))
            inject_plan.append((str(m_target["node_id"]), str(m_target["input_key"]), tgt_name))
        else:
            # heuristic: pick the first two image inputs we can find
            image_nodes = _find_image_input_nodes(workflow)
            if len(image_nodes) < 2:
                return {"error": "Could not find two image input nodes in the workflow. Consider providing 'node_mapping'."}
            # For each candidate, find the first input key starting with 'image'
            def first_image_key(nd: dict) -> str:
                for k in (nd.get("inputs") or {}):
                    if k.lower().startswith("image"):
                        return k
                raise KeyError("image input key not found")

            src_node_id, src_node = image_nodes[0]
            tgt_node_id, tgt_node = image_nodes[1]
            inject_plan.append((str(src_node_id), first_image_key(src_node), src_name))
            inject_plan.append((str(tgt_node_id), first_image_key(tgt_node), tgt_name))

        # 5) Inject filenames into workflow
        workflow = _inject_filenames(workflow, inject_plan)

        # 6) Submit prompt and wait for results
        prompt_id = _post_prompt(workflow)
        images = _wait_for_result(prompt_id, timeout_s=300)  # give it up to 5 minutes

        # 7) Fetch outputs as base64; return the first by default + all if needed
        outputs_b64 = [_download_output_as_b64(img) for img in images]
        result = {
            "status": "ok",
            "outputs_base64": outputs_b64,
            "count": len(outputs_b64),
            "prompt_id": prompt_id
        }
        return result

    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

# RunPod entry
runpod.serverless.start({"handler": rp_handler})
