import importlib.util
from pathlib import Path
import sys


def test_plugin_registers_seven_namespaced_nodes():
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
        "ModelBatchDownloaderCheckpointLoader",
        "ModelBatchDownloaderDiffusionModelLoader",
        "ModelBatchDownloaderJSON",
        "ModelBatchDownloaderLoRALoader",
        "ModelBatchDownloaderTextEncoderLoader",
        "ModelBatchDownloaderVAELoader",
    ]
    assert module.WEB_DIRECTORY == "./web"
