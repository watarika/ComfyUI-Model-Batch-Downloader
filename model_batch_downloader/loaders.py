"""Companion loaders for assets produced by the batch downloader."""

from nodes import CheckpointLoaderSimple, CLIPLoader, LoraLoader, UNETLoader, VAELoader

from .aria2_runner import DownloadResult


def _record(result: DownloadResult, item_id: str, expected: str):
    if not isinstance(result, DownloadResult):
        raise TypeError("download_result must come from Model Download Batch")
    try:
        record = result.entries[item_id]
    except KeyError as exc:
        raise ValueError(f"download_result has no item id {item_id!r}") from exc
    if record.model_type != expected:
        raise ValueError(
            f"item {item_id!r} has model_type {record.model_type!r}; "
            f"this loader requires {expected!r}"
        )
    return record


class ModelBatchDownloaderCheckpointLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "download_result": ("DOWNLOAD_RESULT",),
                "id": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP", "VAE")
    FUNCTION = "load"
    CATEGORY = "model/download/loaders"

    def load(self, download_result, id):
        record = _record(download_result, id, "checkpoints")
        return CheckpointLoaderSimple().load_checkpoint(record.relative_path)


class ModelBatchDownloaderDiffusionModelLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "download_result": ("DOWNLOAD_RESULT",),
                "id": ("STRING", {"default": ""}),
                "weight_dtype": (
                    ["default", "fp8_e4m3fn", "fp8_e4m3fn_fast", "fp8_e5m2"],
                    {"advanced": True},
                ),
            }
        }

    RETURN_TYPES = ("MODEL",)
    FUNCTION = "load"
    CATEGORY = "model/download/loaders"

    def load(self, download_result, id, weight_dtype):
        record = _record(download_result, id, "diffusion_models")
        return UNETLoader().load_unet(record.relative_path, weight_dtype)


class ModelBatchDownloaderTextEncoderLoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "download_result": ("DOWNLOAD_RESULT",),
                "id": ("STRING", {"default": ""}),
                "type": (["auto", "krea2"],),
            },
            "optional": {
                "device": (["default", "cpu"], {"advanced": True}),
            },
        }

    RETURN_TYPES = ("CLIP",)
    FUNCTION = "load"
    CATEGORY = "model/download/loaders"

    def load(self, download_result, id, type, device="default"):
        record = _record(download_result, id, "text_encoders")
        clip_type = "stable_diffusion" if type == "auto" else type
        return CLIPLoader().load_clip(record.relative_path, clip_type, device)


class ModelBatchDownloaderVAELoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "download_result": ("DOWNLOAD_RESULT",),
                "id": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("VAE",)
    FUNCTION = "load"
    CATEGORY = "model/download/loaders"

    def load(self, download_result, id):
        record = _record(download_result, id, "vae")
        return VAELoader().load_vae(record.relative_path)


class ModelBatchDownloaderLoRALoader:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
                "clip": ("CLIP",),
                "download_result": ("DOWNLOAD_RESULT",),
                "id": ("STRING", {"default": ""}),
                "strength_model": (
                    "FLOAT",
                    {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01},
                ),
                "strength_clip": (
                    "FLOAT",
                    {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    FUNCTION = "load"
    CATEGORY = "model/download/loaders"

    def load(
        self,
        model,
        clip,
        download_result,
        id,
        strength_model,
        strength_clip,
    ):
        record = _record(download_result, id, "loras")
        return LoraLoader().load_lora(
            model,
            clip,
            record.relative_path,
            strength_model,
            strength_clip,
        )


LOADER_CLASS_MAPPINGS = {
    "ModelBatchDownloaderCheckpointLoader": ModelBatchDownloaderCheckpointLoader,
    "ModelBatchDownloaderDiffusionModelLoader": ModelBatchDownloaderDiffusionModelLoader,
    "ModelBatchDownloaderTextEncoderLoader": ModelBatchDownloaderTextEncoderLoader,
    "ModelBatchDownloaderVAELoader": ModelBatchDownloaderVAELoader,
    "ModelBatchDownloaderLoRALoader": ModelBatchDownloaderLoRALoader,
}

LOADER_DISPLAY_NAME_MAPPINGS = {
    "ModelBatchDownloaderCheckpointLoader": "Downloaded Checkpoint Loader",
    "ModelBatchDownloaderDiffusionModelLoader": "Downloaded Diffusion Model Loader",
    "ModelBatchDownloaderTextEncoderLoader": "Downloaded Text Encoder Loader",
    "ModelBatchDownloaderVAELoader": "Downloaded VAE Loader",
    "ModelBatchDownloaderLoRALoader": "Downloaded LoRA Loader",
}
