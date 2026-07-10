from pathlib import Path
import sys
import types


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT))


if "folder_paths" not in sys.modules:
    folder_paths = types.ModuleType("folder_paths")
    folder_paths.get_folder_paths = lambda name: [str(PLUGIN_ROOT / ".test-models" / name)]
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
