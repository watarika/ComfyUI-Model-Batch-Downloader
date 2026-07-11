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
    for expected in (
        "workflow_dispatch:",
        "branches:",
        "- main",
        "paths:",
        '- "pyproject.toml"',
        "github.repository_owner == 'watarika'",
        "actions/checkout@v4",
        "Comfy-Org/publish-node-action@v1",
        "secrets.REGISTRY_ACCESS_TOKEN",
    ):
        assert expected in workflow


def test_mit_license_has_approved_copyright():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.startswith("MIT License\n")
    assert "Copyright (c) 2026 watarika" in license_text
    assert "Permission is hereby granted, free of charge" in license_text
    assert 'THE SOFTWARE IS PROVIDED "AS IS"' in license_text
