import logging
from pathlib import Path
from queue import Queue
from threading import Thread

import pytest

from model_batch_downloader.aria2_runner import BatchDownloadError, run_downloads
from model_batch_downloader.manifest import ResolvedItem


class FakeProcess:
    def __init__(self, lines=(), returncode=0, on_wait=None):
        self.stdout = iter(lines)
        self.final_returncode = returncode
        self.returncode = None
        self.on_wait = on_wait
        self.terminated = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.on_wait:
            self.on_wait()
        self.returncode = self.final_returncode
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -1

    def kill(self):
        self.terminated = True
        self.returncode = -9


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
        (resolved,),
        "aria2c",
        {},
        start_process=lambda *args, **kwargs: calls.append(args),
    )

    assert result.entries["model"].status == "skipped"
    assert result.entries["model"].bytes == 5
    assert calls == []


def test_partial_sidecar_marks_success_as_resumed_and_deletes_control_file(tmp_path):
    resolved = make_item(tmp_path)
    sidecar = Path(str(resolved.destination) + ".aria2")
    sidecar.write_text("state", encoding="utf-8")
    seen = {}

    def fake_start(command, **_kwargs):
        seen["command"] = command
        seen["control_path"] = Path(command[-1])
        seen["control"] = seen["control_path"].read_text(encoding="utf-8")

        def finish():
            resolved.destination.write_bytes(b"done")
            sidecar.unlink()

        return FakeProcess(["[#id 1MiB/2MiB(50%) CN:8 DL:1MiB ETA:1s]\n"], on_wait=finish)

    result = run_downloads(
        (resolved,),
        "aria2c",
        {"HF_TOKEN": "secret"},
        start_process=fake_start,
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

    def fake_start(command, **_kwargs):
        seen["command"] = command
        seen["control"] = Path(command[-1]).read_text(encoding="utf-8")
        return FakeProcess(
            on_wait=lambda: resolved.destination.write_bytes(b"done")
        )

    result = run_downloads(
        (resolved,),
        "aria2c",
        {"CIVITAI_API_TOKEN": "cv_secret"},
        start_process=fake_start,
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

    def fake_start(command, **_kwargs):
        attempts.append(command)
        if len(attempts) == 2:
            return FakeProcess(
                on_wait=lambda: second.destination.write_bytes(b"ok")
            )
        return FakeProcess(
            ["Authorization: Bearer secret\n"],
            returncode=3,
        )

    with pytest.raises(BatchDownloadError) as captured:
        run_downloads(
            (first, second),
            "aria2c",
            {"HF_TOKEN": "secret"},
            start_process=fake_start,
        )

    assert len(attempts) == 2
    assert "secret" not in str(captured.value)
    assert "[REDACTED]" in str(captured.value)
    assert "a" in str(captured.value)


def test_process_exception_continues_to_next_item(tmp_path):
    first = make_item(tmp_path, "a.safetensors", "a")
    second = make_item(tmp_path, "b.safetensors", "b")
    attempts = 0

    def fake_start(_command, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OSError("launch failed")
        return FakeProcess(
            on_wait=lambda: second.destination.write_bytes(b"ok")
        )

    with pytest.raises(BatchDownloadError, match="launch failed"):
        run_downloads(
            (first, second),
            "aria2c",
            {},
            start_process=fake_start,
        )

    assert attempts == 2


def test_success_requires_completed_file_and_removed_sidecar(tmp_path):
    resolved = make_item(tmp_path)

    def fake_start(_command, **_kwargs):
        return FakeProcess()

    with pytest.raises(BatchDownloadError, match="did not complete"):
        run_downloads(
            (resolved,),
            "aria2c",
            {},
            start_process=fake_start,
        )


def test_streams_batch_progress_and_logs_one_summary_per_second(
    tmp_path, caplog, monkeypatch
):
    first = make_item(tmp_path, "a.safetensors", "a")
    second = make_item(tmp_path, "b.safetensors", "b")
    progress = []
    clock = [0.0]

    def monotonic():
        clock[0] += 1.1
        return clock[0]

    monkeypatch.setattr(
        "model_batch_downloader.aria2_runner.time.monotonic",
        monotonic,
    )

    def fake_start(_command, **_kwargs):
        item = first if not first.destination.exists() else second
        lines = [
            "[#id 1MiB/4MiB(25%) CN:8 DL:1MiB ETA:3s]\n",
            "[#id 2MiB/4MiB(50%) CN:8 DL:1MiB ETA:2s]\n",
            "[#id 3MiB/4MiB(75%) CN:8 DL:1MiB ETA:1s]\n",
        ]
        return FakeProcess(lines, on_wait=lambda: item.destination.write_bytes(b"done"))

    with caplog.at_level(logging.INFO):
        run_downloads(
            (first, second),
            "aria2c",
            {},
            start_process=fake_start,
            progress_callback=lambda current, total: progress.append((current, total)),
        )

    assert progress[0] == (0, 200)
    assert progress[-1] == (200, 200)
    assert progress == sorted(progress)
    assert "[Model Batch Downloader] start  a (1/2)" in caplog.text
    assert "a 25%  1MiB  ETA 3s" in caplog.text
    assert "done   b" in caplog.text


def test_skip_advances_one_complete_batch_interval(tmp_path):
    target = tmp_path / "model.safetensors"
    target.write_bytes(b"ready")
    resolved = make_item(tmp_path, existing_path=target)
    progress = []

    run_downloads(
        (resolved,),
        "aria2c",
        {},
        start_process=lambda *_args, **_kwargs: pytest.fail("must not start"),
        progress_callback=lambda current, total: progress.append((current, total)),
    )

    assert progress == [(0, 100), (100, 100)]


def test_failure_log_and_summary_redact_tokens(tmp_path, caplog):
    resolved = make_item(tmp_path)
    process = FakeProcess(
        ["Authorization: Bearer secret\n"],
        returncode=3,
    )

    with caplog.at_level(logging.INFO), pytest.raises(BatchDownloadError) as captured:
        run_downloads(
            (resolved,),
            "aria2c",
            {"HF_TOKEN": "secret"},
            start_process=lambda *_args, **_kwargs: process,
        )

    combined = caplog.text + str(captured.value)
    assert "secret" not in combined
    assert "[REDACTED]" in combined


def test_interruption_terminates_process_and_propagates(tmp_path):
    resolved = make_item(tmp_path)
    process = FakeProcess(
        [
            "[#id 1MiB/4MiB(25%) CN:8 DL:1MiB ETA:3s]\n",
            "[#id 2MiB/4MiB(50%) CN:8 DL:1MiB ETA:2s]\n",
        ]
    )
    checks = 0

    def check_interrupted():
        nonlocal checks
        checks += 1
        if checks == 2:
            raise InterruptedError("cancelled")

    with pytest.raises(InterruptedError, match="cancelled"):
        run_downloads(
            (resolved,),
            "aria2c",
            {},
            start_process=lambda *_args, **_kwargs: process,
            check_interrupted=check_interrupted,
        )

    assert process.terminated is True


def test_base_exception_terminates_process_and_reader_then_propagates(
    tmp_path, monkeypatch
):
    class Cancelled(BaseException):
        pass

    resolved = make_item(tmp_path)
    process = FakeProcess(["noise\n"] * 10_000)
    readers = []

    def tracking_thread(*args, **kwargs):
        reader = Thread(*args, **kwargs)
        readers.append(reader)
        return reader

    monkeypatch.setattr(
        "model_batch_downloader.aria2_runner.threading.Thread",
        tracking_thread,
    )

    def check_interrupted():
        raise Cancelled("cancelled")

    with pytest.raises(Cancelled, match="cancelled"):
        run_downloads(
            (resolved,),
            "aria2c",
            {},
            start_process=lambda *_args, **_kwargs: process,
            check_interrupted=check_interrupted,
        )

    assert process.terminated is True
    assert len(readers) == 1
    assert readers[0].is_alive() is False


def test_stream_reader_uses_bounded_queue(tmp_path, monkeypatch):
    resolved = make_item(tmp_path)
    maxsizes = []

    def tracking_queue(maxsize=0):
        maxsizes.append(maxsize)
        return Queue(maxsize)

    monkeypatch.setattr(
        "model_batch_downloader.aria2_runner.Queue",
        tracking_queue,
    )

    run_downloads(
        (resolved,),
        "aria2c",
        {},
        start_process=lambda *_args, **_kwargs: FakeProcess(
            ["notice\n"],
            on_wait=lambda: resolved.destination.write_bytes(b"done"),
        ),
    )

    assert len(maxsizes) == 1
    assert maxsizes[0] > 0
