import json

import pytest

from model_batch_downloader.manifest import ManifestError, derive_id, parse_manifest


def test_parse_manifest_applies_defaults():
    items = parse_manifest(
        json.dumps(
            [
                {
                    "url": "https://huggingface.co/acme/model/resolve/main/model.fp16.safetensors",
                    "model_type": "diffusion_models",
                }
            ]
        )
    )
    assert len(items) == 1
    assert items[0].subfolder == ""
    assert items[0].filename is None
    assert items[0].item_id is None
    assert items[0].split == 16


@pytest.mark.parametrize("split", [0, 17, 1.5, "16"])
def test_parse_manifest_rejects_invalid_split(split):
    with pytest.raises(ManifestError, match="split"):
        parse_manifest(
            json.dumps(
                [
                    {
                        "url": "https://example.com/model.safetensors",
                        "model_type": "checkpoints",
                        "split": split,
                    }
                ]
            )
        )


def test_parse_manifest_rejects_unknown_fields():
    with pytest.raises(ManifestError, match="item 0.*unknown field.*splti"):
        parse_manifest(
            json.dumps(
                [
                    {
                        "url": "https://example.com/model.safetensors",
                        "model_type": "checkpoints",
                        "splti": 16,
                    }
                ]
            )
        )


@pytest.mark.parametrize(
    "subfolder", ["../escape", "/absolute", "C:\\models", "safe/../../escape"]
)
def test_parse_manifest_rejects_unsafe_subfolder(subfolder):
    with pytest.raises(ManifestError, match="subfolder"):
        parse_manifest(
            json.dumps(
                [
                    {
                        "url": "https://example.com/model.safetensors",
                        "model_type": "checkpoints",
                        "subfolder": subfolder,
                    }
                ]
            )
        )


def test_parse_manifest_rejects_empty_array():
    with pytest.raises(ManifestError, match="non-empty array"):
        parse_manifest("[]")


def test_parse_manifest_rejects_non_http_url():
    with pytest.raises(ManifestError, match="HTTP or HTTPS"):
        parse_manifest(
            json.dumps(
                [{"url": "file:///tmp/model.safetensors", "model_type": "checkpoints"}]
            )
        )


def test_derive_id_removes_only_final_suffix():
    assert derive_id("model.fp16.safetensors") == "model.fp16"


@pytest.mark.parametrize(
    "filename", ["../model.safetensors", "folder/model.safetensors", "CON.safetensors"]
)
def test_parse_manifest_rejects_unsafe_explicit_filename(filename):
    with pytest.raises(ManifestError, match="filename"):
        parse_manifest(
            json.dumps(
                [
                    {
                        "url": "https://example.com/model.safetensors",
                        "model_type": "checkpoints",
                        "filename": filename,
                    }
                ]
            )
        )
