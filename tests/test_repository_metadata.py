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
    assert project["version"] == "0.2.0"
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
    section_pairs = (
        ("## Requirements", "## 必要なもの"),
        ("## Installation", "## インストール"),
        ("## Authentication", "## 認証"),
        ("## Nodes", "## ノード"),
        ("## Download progress", "## ダウンロード進捗"),
        ("## Manifest", "## Manifest"),
        ("## Existing files and errors", "## 既存ファイルとエラー"),
        ("## Troubleshooting", "## トラブルシューティング"),
    )
    for english_heading, japanese_heading in section_pairs:
        assert english_heading in english
        assert japanese_heading in japanese


def test_maintainer_information_lives_only_in_contributing():
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    japanese = (ROOT / "README_ja.md").read_text(encoding="utf-8")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    for readme in (english, japanese):
        assert "REGISTRY_ACCESS_TOKEN" not in readme
        assert "uv run --no-project" not in readme
        assert "node --test" not in readme
        assert "uvx ruff check" not in readme

    assert "## Comfy Registry publishing" not in english
    assert "## Development" not in english
    assert "## Comfy Registryへの公開" not in japanese
    assert "## 開発時の確認" not in japanese

    for required in (
        "# Contributing",
        "## Development checks",
        "uv run --no-project --with pytest --with aiohttp python -m pytest -q",
        "node --test",
        "uvx ruff check .",
        "## Comfy Registry publishing",
        "watarika",
        "REGISTRY_ACCESS_TOKEN",
        "pyproject.toml",
        "main",
        "Publish to Comfy registry",
        "semantic version",
    ):
        assert required in contributing


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

    def compatibility_rows(readme, header):
        lines = readme.splitlines()
        start = lines.index(header) + 2
        rows = []
        for line in lines[start:]:
            if not line.strip():
                break
            cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
            assert len(cells) == 3
            rows.append(cells)
        return tuple(rows)

    shared_rows = (
        ("`checkpoints`", "`models/checkpoints`", "`Load Checkpoint (Downloaded)`"),
        ("`diffusion_models`", "`models/diffusion_models`", "`Load Diffusion Model (Downloaded)`"),
        ("`text_encoders`", "`models/text_encoders`", "`Load CLIP (Downloaded)`"),
        ("`vae`", "`models/vae`", "`Load VAE (Downloaded)`"),
        ("`loras`", "`models/loras`", "`Load LoRA (Downloaded)`"),
        ("`controlnet`", "`models/controlnet`", "`Load ControlNet (Downloaded)`"),
        ("`upscale_models`", "`models/upscale_models`", "`Load Upscale Model (Downloaded)`"),
        ("`onnx`", "`models/onnx`", "Impact Pack"),
        ("`ultralytics_bbox`", "`models/ultralytics/bbox`", "Impact Subpack"),
        ("`ultralytics_segm`", "`models/ultralytics/segm`", "Impact Subpack"),
    )
    english_rows = shared_rows[:6] + (
        ("`embeddings`", "`models/embeddings`", "ComfyUI prompt references; no companion loader"),
    ) + shared_rows[6:8] + (
        ("`sam3`", "`models/sam3`", "`comfyui-sam3` path-based `(down)Load SAM3 Model`; default `models/sam3/sam3.pt`"),
        ("`llm`", "`models/llm`", "`ComfyUI_LLM_SDXL_Adapter`: `LLM Model Loader` / `LLM GGUF Model Loader`; no companion loader"),
    ) + shared_rows[8:]
    japanese_rows = shared_rows[:6] + (
        ("`embeddings`", "`models/embeddings`", "ComfyUIのプロンプト参照。companion loaderなし"),
    ) + shared_rows[6:8] + (
        ("`sam3`", "`models/sam3`", "`comfyui-sam3`のpath-based `(down)Load SAM3 Model`。既定値`models/sam3/sam3.pt`"),
        ("`llm`", "`models/llm`", "`ComfyUI_LLM_SDXL_Adapter`: `LLM Model Loader` / `LLM GGUF Model Loader`。companion loaderなし"),
    ) + shared_rows[8:]

    assert compatibility_rows(
        english, "| `model_type` | Default directory | Companion loader / consumer |"
    ) == english_rows
    assert compatibility_rows(
        japanese, "| `model_type` | 既定のディレクトリ | 対応loader / consumer |"
    ) == japanese_rows

    assert "prompt references" in english
    assert "プロンプト参照" in japanese
    assert "single-file downloads only" in english
    assert "単一ファイルのダウンロードのみ" in japanese
    assert "repository snapshots or multi-file inference" in english
    assert "リポジトリsnapshotや複数ファイル推論" in japanese
    assert "optional custom nodes are not dependencies" in english
    assert "任意のcustom nodeはこのdownloaderの依存関係ではありません" in japanese
