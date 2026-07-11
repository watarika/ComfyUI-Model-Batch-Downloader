from __future__ import annotations

import os
import shutil

import comfy.model_management
import comfy.utils
import folder_paths

from .aria2_runner import run_downloads
from .manifest import parse_manifest
from .resolution import probe_filename, resolve_manifest


class AnyType(str):
    def __ne__(self, _other: object) -> bool:
        return False


ANY = AnyType("*")
DOWNLOAD_RESULT = "DOWNLOAD_RESULT"
_MODEL_ROOTS = {
    "checkpoints": ("checkpoints",),
    "diffusion_models": ("diffusion_models",),
    "text_encoders": ("text_encoders",),
    "vae": ("vae",),
    "loras": ("loras",),
    "controlnet": ("controlnet",),
    "embeddings": ("embeddings",),
    "upscale_models": ("upscale_models",),
    "onnx": ("onnx",),
    "sam3": ("sam3",),
    "llm": ("llm",),
    "ultralytics_bbox": ("ultralytics", "bbox"),
    "ultralytics_segm": ("ultralytics", "segm"),
}


def _roots() -> dict[str, tuple[str, ...]]:
    roots = {}
    for name, relative_path in _MODEL_ROOTS.items():
        if name in folder_paths.folder_names_and_paths:
            roots[name] = tuple(folder_paths.get_folder_paths(name))
        else:
            roots[name] = (os.path.join(folder_paths.models_dir, *relative_path),)
    return roots


def execute_manifest(
    manifest_json: str,
    passthrough=None,
    roots_by_type=None,
    executable=None,
):
    aria2 = executable or shutil.which("aria2c")
    if not aria2:
        raise RuntimeError(
            "aria2c is required but was not found on PATH. Install aria2 for "
            "Windows or your Linux distribution, then restart ComfyUI."
        )
    items = parse_manifest(manifest_json)
    resolved = resolve_manifest(
        items,
        roots_by_type or _roots(),
        probe_filename,
        os.environ,
    )
    progress = comfy.utils.ProgressBar(len(resolved) * 100)
    result = run_downloads(
        resolved,
        aria2,
        os.environ,
        progress_callback=progress.update_absolute,
        check_interrupted=(
            comfy.model_management.throw_exception_if_processing_interrupted
        ),
    )
    return passthrough, result


class _DownloadNodeBase:
    RETURN_TYPES = (ANY, DOWNLOAD_RESULT)
    RETURN_NAMES = ("passthrough", "download_result")
    FUNCTION = "download"
    OUTPUT_NODE = True
    CATEGORY = "model/download"

    @classmethod
    def IS_CHANGED(cls, manifest_json, passthrough=None):
        return float("nan")

    def download(self, manifest_json: str, passthrough=None):
        return execute_manifest(manifest_json, passthrough)


class ModelBatchDownloader(_DownloadNodeBase):
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "manifest_json": (
                    "STRING",
                    {"multiline": True, "default": "[]"},
                )
            },
            "optional": {"passthrough": (ANY,)},
        }


class ModelBatchDownloaderJSON(_DownloadNodeBase):
    @classmethod
    def INPUT_TYPES(cls):
        return ModelBatchDownloader.INPUT_TYPES()
