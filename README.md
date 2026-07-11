# ComfyUI Model Batch Downloader

[English] [<a href="README_ja.md">日本語</a>]

This custom node downloads multiple ComfyUI model files from Hugging Face, Civitai, and arbitrary HTTP/HTTPS URLs with `aria2c`, then loads supported files within the same ComfyUI queue. Its thirteen destination categories are `checkpoints`, `diffusion_models`, `text_encoders`, `vae`, `loras`, `controlnet`, `embeddings`, `upscale_models`, `onnx`, `sam3`, `llm`, `ultralytics_bbox`, and `ultralytics_segm`.

Existing files are not overwritten, and checksums are not verified. Incomplete files with an `.aria2` sidecar are resumed.

## Requirements

- ComfyUI
- Python 3.10 or later
- The `aria2c` command, available on the `PATH` of the environment that starts ComfyUI

`aria2c` is not bundled with this repository and is not installed automatically.

## Installation

Run this from the ComfyUI directory.

```powershell
git clone https://github.com/watarika/ComfyUI-Model-Batch-Downloader.git custom_nodes/ComfyUI-Model-Batch-Downloader
```

Then restart ComfyUI. No additional Python packages are required.

## Authentication

Do not enter tokens in nodes or workflow JSON. Set them as environment variables for the process that starts ComfyUI.

| Service | Environment variable |
|---|---|
| Hugging Face | `HF_TOKEN` |
| Civitai | `CIVITAI_API_TOKEN` |

PowerShell example:

```powershell
$env:HF_TOKEN = "hf_..."
$env:CIVITAI_API_TOKEN = "..."
python main.py
```

Linux example:

```bash
export HF_TOKEN='hf_...'
export CIVITAI_API_TOKEN='...'
python main.py
```

Tokens are sent only to the corresponding domains and are not stored in the manifest, `DOWNLOAD_RESULT`, or UI state.

## Nodes

- `Model Download Batch`: A list UI with add and remove buttons. It stores canonical JSON internally.
- `Model Download Batch (JSON)`: A direct JSON-input version using the same core.
- `Load Checkpoint (Downloaded)`: Loads models from the `checkpoints` category using ComfyUI's standard checkpoint loader behavior.
- `Load Diffusion Model (Downloaded)`: Loads models from the `diffusion_models` category using ComfyUI's standard diffusion-model loader behavior.
- `Load CLIP (Downloaded)`: Uses the same `type` choices as ComfyUI's standard `Load CLIP`, including `krea2`, `ideogram4`, and `flux2`.
- `Load VAE (Downloaded)`: Loads models from the `vae` category using ComfyUI's standard VAE loader behavior.
- `Load ControlNet (Downloaded)`: Loads models from the `controlnet` category using ComfyUI's standard ControlNet loader behavior.
- `Load Upscale Model (Downloaded)`: Loads models from the `upscale_models` category using ComfyUI's standard upscale-model loader behavior.
- `Load LoRA (Downloaded)`: Loads models from the `loras` category using ComfyUI's standard LoRA loader behavior. For model-only LoRAs, `strength_clip` can be set to 0.

Both download nodes have an arbitrary-type `passthrough` input and output. They can be inserted into an existing connection or run unconnected as output nodes. To use downloaded results, connect `download_result` to the corresponding Downloaded Loader and specify the manifest `id`.

## Usage examples

The following model families illustrate common setups; they are examples, not an exhaustive compatibility list.

- Illustrious: Download an all-in-one checkpoint to `checkpoints`, then load it with `Load Checkpoint (Downloaded)`.
- Anima: Download a separate diffusion model, text encoder, and VAE to `diffusion_models`, `text_encoders`, and `vae`, then load each one with its corresponding Downloaded Loader.
- Krea 2: Download a separate diffusion model and VAE to `diffusion_models` and `vae`. Download its text encoder to `text_encoders`, then select `krea2` in `Load CLIP (Downloaded)`.

## Download progress

While a download node is running, it displays ComfyUI's standard progress bar, the same one used by KSampler. With multiple files, the bar does not reset; it advances from 0 to 100% across the entire batch.

Approximately once per second, the ComfyUI log shows the current ID, percentage, speed, and ETA.

```text
[Model Batch Downloader] anima_model 42%  18.3MiB  ETA 31s
```

Authentication tokens and authenticated URLs are never written to the log.

## Manifest

The root is a JSON array containing at least one item. Each item supports these fields:

| Field | Required | Description |
|---|---:|---|
| `url` | Yes | HTTP/HTTPS URL |
| `model_type` | Yes | One of the thirteen categories in the compatibility table below |
| `subfolder` | No | Destination under the corresponding ComfyUI model root |
| `filename` | No | If omitted, resolved from the response or URL |
| `id` | No | If omitted, the filename without its final extension |
| `split` | No | 1–16; default 16 |

Without `subfolder`, each category uses the following directory. A configured ComfyUI folder path for the category takes precedence over this default.

| `model_type` | Default directory | Companion loader / consumer |
|---|---|---|
| `checkpoints` | `models/checkpoints` | `Load Checkpoint (Downloaded)` |
| `diffusion_models` | `models/diffusion_models` | `Load Diffusion Model (Downloaded)` |
| `text_encoders` | `models/text_encoders` | `Load CLIP (Downloaded)` |
| `vae` | `models/vae` | `Load VAE (Downloaded)` |
| `loras` | `models/loras` | `Load LoRA (Downloaded)` |
| `controlnet` | `models/controlnet` | `Load ControlNet (Downloaded)` |
| `embeddings` | `models/embeddings` | ComfyUI prompt references; no companion loader |
| `upscale_models` | `models/upscale_models` | `Load Upscale Model (Downloaded)` |
| `onnx` | `models/onnx` | Impact Pack |
| `sam3` | `models/sam3` | `comfyui-sam3` path-based `(down)Load SAM3 Model`; default `models/sam3/sam3.pt` |
| `llm` | `models/llm` | `ComfyUI_LLM_SDXL_Adapter`: `LLM Model Loader` / `LLM GGUF Model Loader`; no companion loader |
| `ultralytics_bbox` | `models/ultralytics/bbox` | Impact Subpack |
| `ultralytics_segm` | `models/ultralytics/segm` | Impact Subpack |

Embedding files are used through prompt references and have no companion loader. `comfyui-sam3` consumes a path string through its path-based `(down)Load SAM3 Model`; its default `models/sam3/sam3.pt` points to this downloader's default SAM3 destination, but this downloader does not provide a SAM3 companion loader. For LLM files, `ComfyUI_LLM_SDXL_Adapter` reads `models/llm` through `LLM Model Loader` and `LLM GGUF Model Loader`. LLM support covers single-file downloads only; it does not automatically provide repository snapshots or multi-file inference. Impact Pack, `comfyui-sam3`, `ComfyUI_LLM_SDXL_Adapter`, Impact Subpack, and other optional custom nodes are not dependencies of this downloader; install and use them separately when you need their consumer nodes.

A concrete usage example for Anima:

```json
[
  {
    "url": "https://huggingface.co/owner/repo/resolve/main/anima-model.safetensors",
    "model_type": "diffusion_models",
    "subfolder": "anima",
    "id": "anima_model",
    "split": 16
  },
  {
    "url": "https://huggingface.co/owner/repo/resolve/main/qwen3-0.6b.safetensors",
    "model_type": "text_encoders",
    "subfolder": "anima",
    "id": "anima_encoder"
  },
  {
    "url": "https://huggingface.co/owner/repo/resolve/main/qwen-image-vae.safetensors",
    "model_type": "vae",
    "id": "qwen_vae"
  }
]
```

Connect `download_result` to the three corresponding loaders and specify `anima_model`, `anima_encoder`, and `qwen_vae`, respectively.

If a URL resolves to `model.fp16.safetensors` and `id` is omitted, the ID is `model.fp16`. For sources such as the Civitai API where the filename cannot be determined from the URL suffix, use `Resolve filename / ID` in the list UI to resolve it in advance. An explicit `id` is recommended for stable references in the JSON version.

## Existing files and errors

- If a completed file exists, it is marked `skipped` without starting aria2.
- If `<filename>.aria2` exists, the download resumes in aria2 continuation mode.
- Multiple items are processed in order. If one fails, the remaining items are still attempted, and failures are reported together at the end.
- Destinations are restricted to the configured ComfyUI model roots.
- Duplicate IDs or destinations within a manifest are errors.

## Troubleshooting

- `aria2c is required`: Confirm that `aria2c --version` works in the same environment as ComfyUI, then restart ComfyUI.
- Hugging Face 401/403: Check `HF_TOKEN` and your repository access permissions.
- Civitai 401/403: Check `CIVITAI_API_TOKEN`.
- `duplicate id`: Assign a unique explicit `id` to one of the entries.
- category mismatch: Connect to the Downloaded Loader corresponding to the ID's `model_type`.
- No loader for an extended category: Use the consumer shown in the compatibility table. External consumer plugins are independently installed and maintained; this downloader only owns downloading the file to the selected destination.

## Comfy Registry publishing

The Publisher ID is `watarika`. The GitHub Secret `REGISTRY_ACCESS_TOKEN` must contain the Comfy Registry API key. Publishing can be started manually, and also runs when `pyproject.toml` changes on `main`.

## Development

```powershell
uv run --with pytest --with aiohttp --no-project pytest tests -v
node --test tests-js/manifest_state.test.mjs
uvx ruff check .
```
