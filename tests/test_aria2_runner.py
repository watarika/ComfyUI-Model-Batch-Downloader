from pathlib import Path
from types import SimpleNamespace

import pytest

from model_batch_downloader.aria2_runner import BatchDownloadError, run_downloads
from model_batch_downloader.manifest import ResolvedItem


def make_item(
    tmp_path,
    name="model.safetensors",
    item_id="model",
    url=None,
    existing_path=None,
):
    return ResolvedItem(
        url or "https://huggingface.co/a/resolve/main/" + name,
        "diffusion_models",
        "",
        name,
        item_id,
        8,
        tmp_path / name,
        Path(name),
        existing_path,
    )


def test_complete_file_is_skipped_without_process(tmp_path):
    target = tmp_path / "model.safetensors"
    target.write_bytes(b"ready")
    resolved = make_item(tmp_path, existing_path=target)
    calls = []

    result = run_downloads(
        (resolved,), "aria2c", {}, lambda *args, **kwargs: calls.append(args)
    )

    assert result.entries["model"].status == "skipped"
    assert result.entries["model"].bytes == 5
    assert calls == []


def test_partial_sidecar_marks_success_as_resumed_and_deletes_control_file(tmp_path):
    resolved = make_item(tmp_path)
    sidecar = Path(str(resolved.destination) + ".aria2")
    sidecar.write_text("state", encoding="utf-8")
    seen = {}

    def fake_run(command, **_kwargs):
        seen["command"] = command
        seen["control_path"] = Path(command[-1])
        seen["control"] = seen["control_path"].read_text(encoding="utf-8")
        resolved.destination.write_bytes(b"done")
        sidecar.unlink()
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    result = run_downloads(
        (resolved,), "aria2c", {"HF_TOKEN": "secret"}, fake_run
    )

    assert result.entries["model"].status == "resumed"
    assert "secret" not in " ".join(seen["command"])
    assert "Authorization: Bearer secret" in seen["control"]
    assert not seen["control_path"].exists()


def test_new_civitai_download_puts_token_only_in_control_file(tmp_path):
    resolved = make_item(
        tmp_path,
        url="https://civitai.com/api/download/models/42?format=SafeTensor",
    )
    seen = {}

    def fake_run(command, **_kwargs):
        seen["command"] = command
        seen["control"] = Path(command[-1]).read_text(encoding="utf-8")
        resolved.destination.write_bytes(b"done")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    result = run_downloads(
        (resolved,), "aria2c", {"CIVITAI_API_TOKEN": "cv_secret"}, fake_run
    )

    assert result.entries["model"].status == "downloaded"
    assert "cv_secret" not in " ".join(seen["command"])
    assert "format=SafeTensor&token=cv_secret" in seen["control"]
    assert "allow-overwrite=false" in seen["control"]
    assert "auto-file-renaming=false" in seen["control"]


def test_failure_continues_then_raises_redacted_summary(tmp_path):
    first = make_item(tmp_path, "a.safetensors", "a")
    second = make_item(tmp_path, "b.safetensors", "b")
    attempts = []

    def fake_run(command, **_kwargs):
        attempts.append(command)
        if len(attempts) == 2:
            second.destination.write_bytes(b"ok")
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(
            returncode=3, stdout="", stderr="Authorization: Bearer secret"
        )

    with pytest.raises(BatchDownloadError) as captured:
        run_downloads(
            (first, second), "aria2c", {"HF_TOKEN": "secret"}, fake_run
        )

    assert len(attempts) == 2
    assert "secret" not in str(captured.value)
    assert "[REDACTED]" in str(captured.value)
    assert "a" in str(captured.value)


def test_process_exception_continues_to_next_item(tmp_path):
    first = make_item(tmp_path, "a.safetensors", "a")
    second = make_item(tmp_path, "b.safetensors", "b")
    attempts = 0

    def fake_run(_command, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("launch failed")
        second.destination.write_bytes(b"ok")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with pytest.raises(BatchDownloadError, match="launch failed"):
        run_downloads((first, second), "aria2c", {}, fake_run)

    assert attempts == 2


def test_success_requires_completed_file_and_removed_sidecar(tmp_path):
    resolved = make_item(tmp_path)

    def fake_run(_command, **_kwargs):
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with pytest.raises(BatchDownloadError, match="did not complete"):
        run_downloads((resolved,), "aria2c", {}, fake_run)
