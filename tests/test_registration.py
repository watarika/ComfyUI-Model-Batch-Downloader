import importlib.util
from pathlib import Path
import sys


def test_plugin_registers_nine_namespaced_nodes():
    root = Path(__file__).resolve().parents[1]
    init_file = root / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "model_batch_downloader_plugin",
        init_file,
        submodule_search_locations=[str(root)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert sorted(module.NODE_CLASS_MAPPINGS) == [
        "ModelBatchDownloader",
        "ModelBatchDownloaderCLIPLoader",
        "ModelBatchDownloaderCheckpointLoader",
        "ModelBatchDownloaderControlNetLoader",
        "ModelBatchDownloaderDiffusionModelLoader",
        "ModelBatchDownloaderJSON",
        "ModelBatchDownloaderLoRALoader",
        "ModelBatchDownloaderUpscaleModelLoader",
        "ModelBatchDownloaderVAELoader",
    ]
    assert "ModelBatchDownloaderCLIPLoader" in module.NODE_CLASS_MAPPINGS
    assert "ModelBatchDownloaderTextEncoderLoader" not in module.NODE_CLASS_MAPPINGS
    assert module.NODE_DISPLAY_NAME_MAPPINGS == {
        "ModelBatchDownloader": "Model Download Batch",
        "ModelBatchDownloaderJSON": "Model Download Batch (JSON)",
        "ModelBatchDownloaderCheckpointLoader": "Load Checkpoint (Downloaded)",
        "ModelBatchDownloaderControlNetLoader": "Load ControlNet (Downloaded)",
        "ModelBatchDownloaderDiffusionModelLoader": "Load Diffusion Model (Downloaded)",
        "ModelBatchDownloaderCLIPLoader": "Load CLIP (Downloaded)",
        "ModelBatchDownloaderVAELoader": "Load VAE (Downloaded)",
        "ModelBatchDownloaderLoRALoader": "Load LoRA (Downloaded)",
        "ModelBatchDownloaderUpscaleModelLoader": "Load Upscale Model (Downloaded)",
    }
    assert module.WEB_DIRECTORY == "./web"
