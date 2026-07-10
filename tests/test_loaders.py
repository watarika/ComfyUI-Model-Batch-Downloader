from model_batch_downloader.aria2_runner import DownloadRecord, DownloadResult
import model_batch_downloader.loaders as subject


def result(model_type, relative_path="folder/model.safetensors", item_id="asset"):
    return DownloadResult(
        {
            item_id: DownloadRecord(
                item_id,
                model_type,
                relative_path,
                "C:/models/" + relative_path,
                "downloaded",
                123,
                1.0,
            )
        }
    )


def test_checkpoint_loader_delegates_relative_path(monkeypatch):
    seen = []
    monkeypatch.setattr(
        subject.CheckpointLoaderSimple,
        "load_checkpoint",
        lambda self, name: seen.append(name) or ("m", "c", "v"),
    )
    assert subject.ModelBatchDownloaderCheckpointLoader().load(
        result("checkpoints"), "asset"
    ) == ("m", "c", "v")
    assert seen == ["folder/model.safetensors"]


def test_diffusion_loader_passes_weight_dtype(monkeypatch):
    seen = []
    monkeypatch.setattr(
        subject.UNETLoader,
        "load_unet",
        lambda self, name, dtype: seen.append((name, dtype)) or ("model",),
    )
    assert subject.ModelBatchDownloaderDiffusionModelLoader().load(
        result("diffusion_models"), "asset", "fp8_e4m3fn"
    ) == ("model",)
    assert seen == [("folder/model.safetensors", "fp8_e4m3fn")]


def test_text_encoder_maps_auto_and_krea2(monkeypatch):
    seen = []
    monkeypatch.setattr(
        subject.CLIPLoader,
        "load_clip",
        lambda self, name, type, device: seen.append((name, type, device)) or ("clip",),
    )
    loader = subject.ModelBatchDownloaderTextEncoderLoader()
    loader.load(result("text_encoders"), "asset", "auto", "default")
    loader.load(result("text_encoders"), "asset", "krea2", "cpu")
    assert seen == [
        ("folder/model.safetensors", "stable_diffusion", "default"),
        ("folder/model.safetensors", "krea2", "cpu"),
    ]


def test_wrong_category_fails_before_delegation():
    try:
        subject.ModelBatchDownloaderVAELoader().load(result("loras"), "asset")
    except ValueError as exc:
        assert "asset" in str(exc) and "loras" in str(exc) and "vae" in str(exc)
    else:
        raise AssertionError("category mismatch must fail")


def test_vae_loader_delegates_relative_path(monkeypatch):
    seen = []
    monkeypatch.setattr(
        subject.VAELoader,
        "load_vae",
        lambda self, name: seen.append(name) or ("vae",),
    )
    assert subject.ModelBatchDownloaderVAELoader().load(result("vae"), "asset") == (
        "vae",
    )
    assert seen == ["folder/model.safetensors"]


def test_lora_loader_delegates_models_and_strengths(monkeypatch):
    seen = []
    monkeypatch.setattr(
        subject.LoraLoader,
        "load_lora",
        lambda self, model, clip, name, strength_model, strength_clip: seen.append(
            (model, clip, name, strength_model, strength_clip)
        )
        or ("patched-model", "patched-clip"),
    )
    output = subject.ModelBatchDownloaderLoRALoader().load(
        "model", "clip", result("loras"), "asset", 0.8, 0.0
    )
    assert output == ("patched-model", "patched-clip")
    assert seen == [("model", "clip", "folder/model.safetensors", 0.8, 0.0)]
