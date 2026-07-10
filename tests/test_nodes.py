import json

import pytest

import model_batch_downloader.nodes as subject


def sample_manifest():
    return json.dumps(
        [
            {
                "url": "https://example.com/a.safetensors",
                "model_type": "checkpoints",
                "filename": "a.safetensors",
            }
        ]
    )


def test_both_nodes_share_executor_and_preserve_identity(monkeypatch):
    sentinel = object()
    result = object()
    calls = []
    monkeypatch.setattr(
        subject,
        "execute_manifest",
        lambda manifest_json, passthrough=None: calls.append(manifest_json)
        or (passthrough, result),
    )

    assert subject.ModelBatchDownloader().download(sample_manifest(), sentinel) == (
        sentinel,
        result,
    )
    assert subject.ModelBatchDownloaderJSON().download(sample_manifest(), sentinel) == (
        sentinel,
        result,
    )
    assert calls == [sample_manifest(), sample_manifest()]


def test_authoring_nodes_are_output_nodes_and_always_change():
    for node_class in (
        subject.ModelBatchDownloader,
        subject.ModelBatchDownloaderJSON,
    ):
        assert node_class.OUTPUT_NODE is True
        assert node_class.RETURN_NAMES == ("passthrough", "download_result")
        assert str(node_class.RETURN_TYPES[1]) == "DOWNLOAD_RESULT"
        assert node_class.IS_CHANGED(sample_manifest()) != node_class.IS_CHANGED(
            sample_manifest()
        )


def test_table_and_json_nodes_expose_same_backend_schema():
    assert subject.ModelBatchDownloader.INPUT_TYPES() == (
        subject.ModelBatchDownloaderJSON.INPUT_TYPES()
    )
    schema = subject.ModelBatchDownloader.INPUT_TYPES()
    assert schema["required"]["manifest_json"][0] == "STRING"
    assert "passthrough" in schema["optional"]


def test_execute_manifest_fails_before_parsing_when_aria2_missing(monkeypatch):
    monkeypatch.setattr(subject.shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="aria2c"):
        subject.execute_manifest("[]")


def test_execute_manifest_connects_runner_to_comfy_progress(monkeypatch):
    progress = []
    interruption_checks = []
    resolved = (object(), object())
    download_result = object()

    class ProgressBar:
        def __init__(self, total):
            assert total == 200

        def update_absolute(self, value, total=None):
            progress.append((value, total))

    monkeypatch.setattr(subject.comfy.utils, "ProgressBar", ProgressBar)
    monkeypatch.setattr(subject, "parse_manifest", lambda _json: (object(),))
    monkeypatch.setattr(subject, "resolve_manifest", lambda *_args: resolved)
    monkeypatch.setattr(subject.shutil, "which", lambda _name: "aria2c")
    monkeypatch.setattr(
        subject.comfy.model_management,
        "throw_exception_if_processing_interrupted",
        lambda: interruption_checks.append(True),
    )

    def fake_run(items, executable, environ, progress_callback, check_interrupted):
        assert items is resolved
        assert executable == "aria2c"
        progress_callback(75, 200)
        check_interrupted()
        return download_result

    monkeypatch.setattr(subject, "run_downloads", fake_run)

    assert subject.execute_manifest(sample_manifest(), roots_by_type={}) == (
        None,
        download_result,
    )
    assert progress == [(75, 200)]
    assert interruption_checks == [True]
