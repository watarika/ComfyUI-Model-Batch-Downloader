from pathlib import Path
import sys
import types


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))


if "comfy" not in sys.modules:
    comfy = types.ModuleType("comfy")
    comfy.__path__ = []
    comfy_utils = types.ModuleType("comfy.utils")
    comfy_model_management = types.ModuleType("comfy.model_management")

    class ProgressBar:
        def __init__(self, total):
            self.total = total

        def update_absolute(self, value, total=None):
            return None

    comfy_utils.ProgressBar = ProgressBar
    comfy_model_management.throw_exception_if_processing_interrupted = lambda: None
    comfy.utils = comfy_utils
    comfy.model_management = comfy_model_management
    sys.modules["comfy"] = comfy
    sys.modules["comfy.utils"] = comfy_utils
    sys.modules["comfy.model_management"] = comfy_model_management


if "folder_paths" not in sys.modules:
    folder_paths = types.ModuleType("folder_paths")
    folder_paths.models_dir = str(PLUGIN_ROOT / ".test-models")
    folder_paths.folder_names_and_paths = {
        name: ([str(PLUGIN_ROOT / ".test-models" / name)], set())
        for name in (
            "checkpoints",
            "diffusion_models",
            "text_encoders",
            "vae",
            "loras",
        )
    }

    def get_folder_paths(name):
        paths, _extensions = folder_paths.folder_names_and_paths[name]
        return paths

    folder_paths.get_folder_paths = get_folder_paths
    sys.modules["folder_paths"] = folder_paths


if "server" not in sys.modules:
    server = types.ModuleType("server")

    class Routes:
        def post(self, _path):
            return lambda function: function

    class PromptServer:
        instance = types.SimpleNamespace(routes=Routes())

    server.PromptServer = PromptServer
    sys.modules["server"] = server


if "nodes" not in sys.modules:
    comfy_nodes = types.ModuleType("nodes")

    def fake_loader_method(self, *args, **kwargs):
        return None

    methods = {
        "CheckpointLoaderSimple": "load_checkpoint",
        "CLIPLoader": "load_clip",
        "LoraLoader": "load_lora",
        "UNETLoader": "load_unet",
        "VAELoader": "load_vae",
    }
    for class_name, method_name in methods.items():
        setattr(
            comfy_nodes,
            class_name,
            type(class_name, (), {method_name: fake_loader_method}),
        )
    sys.modules["nodes"] = comfy_nodes
