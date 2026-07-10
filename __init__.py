"""ComfyUI Model Batch Downloader node registration."""

if __package__:
    from .model_batch_downloader import routes as _routes
    from .model_batch_downloader.loaders import (
        LOADER_CLASS_MAPPINGS,
        LOADER_DISPLAY_NAME_MAPPINGS,
    )
    from .model_batch_downloader.nodes import ModelBatchDownloader, ModelBatchDownloaderJSON
else:  # Support direct test/import of this hyphenated repository root.
    from model_batch_downloader import routes as _routes
    from model_batch_downloader.loaders import (
        LOADER_CLASS_MAPPINGS,
        LOADER_DISPLAY_NAME_MAPPINGS,
    )
    from model_batch_downloader.nodes import ModelBatchDownloader, ModelBatchDownloaderJSON

del _routes  # Import registers the HTTP route as a side effect.


NODE_CLASS_MAPPINGS = {
    "ModelBatchDownloader": ModelBatchDownloader,
    "ModelBatchDownloaderJSON": ModelBatchDownloaderJSON,
    **LOADER_CLASS_MAPPINGS,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ModelBatchDownloader": "Model Download Batch",
    "ModelBatchDownloaderJSON": "Model Download Batch (JSON)",
    **LOADER_DISPLAY_NAME_MAPPINGS,
}

WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
