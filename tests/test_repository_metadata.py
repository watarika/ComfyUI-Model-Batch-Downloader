from pathlib import Path
import tomllib


ROOT = Path(__file__).parents[1]


def test_pyproject_contains_publication_metadata():
    with (ROOT / "pyproject.toml").open("rb") as file:
        data = tomllib.load(file)

    project = data["project"]
    assert project["name"] == "comfyui-model-batch-downloader"
    assert project["description"] == (
        "Download and load multiple ComfyUI model files from Hugging Face, "
        "Civitai, and HTTP URLs."
    )
    assert project["version"] == "0.1.0"
    assert project["requires-python"] == ">=3.10"
    assert project["license"] == {"file": "LICENSE"}
    assert project["dependencies"] == []
    assert project["urls"]["Repository"] == (
        "https://github.com/watarika/ComfyUI-Model-Batch-Downloader"
    )

    comfy = data["tool"]["comfy"]
    assert comfy == {
        "PublisherId": "watarika",
        "DisplayName": "ComfyUI Model Batch Downloader",
        "Icon": "",
    }


def test_registry_workflow_matches_publication_contract():
    workflow = (ROOT / ".github/workflows/publish_action.yml").read_text(
        encoding="utf-8"
    )
    expected = """name: Publish to Comfy registry
on:
  workflow_dispatch:
  push:
    branches:
      - main
    paths:
      - "pyproject.toml"

jobs:
  publish-node:
    name: Publish Custom Node to registry
    runs-on: ubuntu-latest
    if: ${{ github.repository_owner == 'watarika' }}
    steps:
      - name: Check out code
        uses: actions/checkout@v4
      - name: Publish Custom Node
        uses: Comfy-Org/publish-node-action@v1
        with:
          personal_access_token: ${{ secrets.REGISTRY_ACCESS_TOKEN }}
"""
    assert workflow.replace("\r\n", "\n") == expected


def test_mit_license_has_approved_copyright():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    expected = """MIT License

Copyright (c) 2026 watarika

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    assert license_text.replace("\r\n", "\n") == expected


def test_readmes_are_bilingual_and_cover_the_same_topics():
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    japanese = (ROOT / "README_ja.md").read_text(encoding="utf-8")

    assert '[English] [<a href="README_ja.md">日本語</a>]' in english
    assert '[<a href="README.md">English</a>] [日本語]' in japanese
    assert "Hugging Face, Civitai, and arbitrary HTTP/HTTPS URLs" in english
    assert "Hugging Face、Civitai、任意のHTTP/HTTPS URL" in japanese
    assert (
        "git clone https://github.com/watarika/ComfyUI-Model-Batch-Downloader.git "
        "custom_nodes/ComfyUI-Model-Batch-Downloader"
    ) in english
    assert "REGISTRY_ACCESS_TOKEN" in english
    assert "REGISTRY_ACCESS_TOKEN" in japanese

    section_pairs = (
        ("## Requirements", "## 必要なもの"),
        ("## Installation", "## インストール"),
        ("## Authentication", "## 認証"),
        ("## Nodes", "## ノード"),
        ("## Download progress", "## ダウンロード進捗"),
        ("## Manifest", "## Manifest"),
        ("## Existing files and errors", "## 既存ファイルとエラー"),
        ("## Troubleshooting", "## トラブルシューティング"),
        ("## Comfy Registry publishing", "## Comfy Registryへの公開"),
        ("## Development", "## 開発時の確認"),
    )
    for english_heading, japanese_heading in section_pairs:
        assert english_heading in english
        assert japanese_heading in japanese


def test_readmes_describe_generic_scope_with_model_family_examples():
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    japanese = (ROOT / "README_ja.md").read_text(encoding="utf-8")

    assert (
        "downloads multiple ComfyUI model files from Hugging Face, Civitai, "
        "and arbitrary HTTP/HTTPS URLs"
    ) in english
    assert (
        "Hugging Face、Civitai、任意のHTTP/HTTPS URLから複数のComfyUIモデルファイル"
    ) in japanese
    assert "## Usage examples" in english
    assert "## 利用例" in japanese

    for model_name in ("Illustrious", "Anima", "Krea 2"):
        assert model_name in english
        assert model_name in japanese

    assert "used with Illustrious, Anima, and Krea 2" not in english
    assert "Illustrious、Anima、Krea 2で使う" not in japanese


def test_readmes_document_extended_category_contract_in_both_languages():
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    japanese = (ROOT / "README_ja.md").read_text(encoding="utf-8")

    categories = (
        "checkpoints",
        "diffusion_models",
        "text_encoders",
        "vae",
        "loras",
        "controlnet",
        "embeddings",
        "upscale_models",
        "onnx",
        "sam3",
        "llm",
        "ultralytics_bbox",
        "ultralytics_segm",
    )
    destinations = (
        "models/checkpoints",
        "models/diffusion_models",
        "models/text_encoders",
        "models/vae",
        "models/loras",
        "models/controlnet",
        "models/embeddings",
        "models/upscale_models",
        "models/onnx",
        "models/sam3",
        "models/llm",
        "models/ultralytics/bbox",
        "models/ultralytics/segm",
    )
    for readme in (english, japanese):
        for category in categories:
            assert f"`{category}`" in readme
        for destination in destinations:
            assert f"`{destination}`" in readme
        assert "`Load ControlNet (Downloaded)`" in readme
        assert "`Load Upscale Model (Downloaded)`" in readme
        assert "Impact Pack" in readme
        assert "`comfyui-sam3`" in readme
        assert "Impact Subpack" in readme

    assert "prompt references" in english
    assert "プロンプト参照" in japanese
    assert "single-file downloads only" in english
    assert "単一ファイルのダウンロードのみ" in japanese
    assert "repository snapshots or multi-file inference" in english
    assert "リポジトリsnapshotや複数ファイル推論" in japanese
    assert "optional custom nodes are not dependencies" in english
    assert "任意のcustom nodeはこのdownloaderの依存関係ではありません" in japanese
