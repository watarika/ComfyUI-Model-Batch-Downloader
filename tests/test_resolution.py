from pathlib import Path

import pytest

from model_batch_downloader.manifest import ManifestError, ManifestItem
from model_batch_downloader.resolution import resolve_manifest
from model_batch_downloader.security import auth_for_url, authenticated_url, redact


def test_resolve_uses_content_disposition_and_derives_id(tmp_path):
    item = ManifestItem(
        "https://civitai.com/api/download/models/42", "checkpoints"
    )
    resolved = resolve_manifest(
        (item,),
        {"checkpoints": (tmp_path / "checkpoints",)},
        probe=lambda _url, _headers: "Realism.Illustrious.safetensors",
        environ={},
    )
    assert resolved[0].filename == "Realism.Illustrious.safetensors"
    assert resolved[0].item_id == "Realism.Illustrious"
    assert resolved[0].relative_path == Path("Realism.Illustrious.safetensors")


def test_resolve_rejects_case_insensitive_duplicate_ids(tmp_path):
    items = (
        ManifestItem(
            "https://example.com/a.safetensors",
            "loras",
            filename="a.safetensors",
            item_id="Style",
        ),
        ManifestItem(
            "https://example.com/b.safetensors",
            "loras",
            filename="b.safetensors",
            item_id="style",
        ),
    )
    with pytest.raises(ManifestError, match="duplicate id"):
        resolve_manifest(items, {"loras": (tmp_path,)}, lambda *_: None, {})


def test_resolve_rejects_duplicate_destination(tmp_path):
    items = (
        ManifestItem(
            "https://example.com/a.safetensors",
            "loras",
            filename="same.safetensors",
            item_id="first",
        ),
        ManifestItem(
            "https://example.com/b.safetensors",
            "loras",
            filename="same.safetensors",
            item_id="second",
        ),
    )
    with pytest.raises(ManifestError, match="duplicate destination"):
        resolve_manifest(items, {"loras": (tmp_path,)}, lambda *_: None, {})


def test_resolve_skips_existing_file_in_secondary_root(tmp_path):
    primary, secondary = tmp_path / "primary", tmp_path / "secondary"
    existing = secondary / "krea2" / "qwen_image_vae.safetensors"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing")
    item = ManifestItem(
        "https://example.com/qwen_image_vae.safetensors",
        "vae",
        subfolder="krea2",
        filename="qwen_image_vae.safetensors",
    )
    resolved = resolve_manifest(
        (item,), {"vae": (primary, secondary)}, lambda *_: None, {}
    )[0]
    assert resolved.existing_path == existing.resolve()
    assert resolved.destination == (
        primary / "krea2" / "qwen_image_vae.safetensors"
    ).resolve()


def test_resolve_rejects_secondary_root_symlink_escape(tmp_path):
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary"
    outside = tmp_path / "outside"
    primary.mkdir()
    secondary.mkdir()
    outside.mkdir()
    try:
        (secondary / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are unavailable for this Windows account")
    (outside / "model.safetensors").write_bytes(b"outside")
    item = ManifestItem(
        "https://example.com/model.safetensors",
        "checkpoints",
        subfolder="linked",
        filename="model.safetensors",
    )
    with pytest.raises(ManifestError, match="escapes"):
        resolve_manifest(
            (item,), {"checkpoints": (primary, secondary)}, lambda *_: None, {}
        )


def test_auth_uses_environment_only():
    huggingface = auth_for_url(
        "https://huggingface.co/a/b", {"HF_TOKEN": "hf_secret"}
    )
    assert huggingface.header == ("Authorization", "Bearer hf_secret")

    civitai = auth_for_url(
        "https://civitai.com/api/download/models/1",
        {"CIVITAI_API_TOKEN": "cv_secret"},
    )
    assert civitai.query_token == "cv_secret"
    assert authenticated_url(
        "https://civitai.com/api/download/models/1?format=SafeTensor", civitai
    ).endswith("format=SafeTensor&token=cv_secret")


def test_public_host_has_no_authentication():
    auth = auth_for_url("https://example.com/model.safetensors", {})
    assert auth.provider == "public"
    assert auth.header is None
    assert auth.query_token is None


def test_redact_removes_exact_and_pattern_secrets():
    text = (
        "Authorization: Bearer hf_secret "
        "https://civitai.com/x?token=cv_secret"
    )
    clean = redact(text, ("hf_secret", "cv_secret"))
    assert "hf_secret" not in clean
    assert "cv_secret" not in clean
    assert "[REDACTED]" in clean


def test_resolution_error_redacts_civitai_token(tmp_path):
    item = ManifestItem(
        "https://civitai.com/api/download/models/42", "checkpoints"
    )

    def failing_probe(url, _headers):
        raise RuntimeError(f"failed request: {url}")

    with pytest.raises(ManifestError) as captured:
        resolve_manifest(
            (item,),
            {"checkpoints": (tmp_path,)},
            failing_probe,
            {"CIVITAI_API_TOKEN": "cv_secret"},
        )
    assert "cv_secret" not in str(captured.value)
    assert "[REDACTED]" in str(captured.value)
