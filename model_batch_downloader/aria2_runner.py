from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from queue import Empty, Full, Queue
import subprocess
import tempfile
import threading
import time
from typing import Callable, Mapping
from urllib.parse import urlsplit

from .manifest import ResolvedItem
from .progress import format_bytes, parse_aria2_progress
from .security import auth_for_url, authenticated_url, redact


logger = logging.getLogger(__name__)
_CIVITAI_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
)
_STREAM_END = object()
_STREAM_QUEUE_SIZE = 40


@dataclass(frozen=True, slots=True)
class DownloadRecord:
    item_id: str
    model_type: str
    relative_path: str
    absolute_path: str
    status: str
    bytes: int
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class DownloadResult:
    entries: dict[str, DownloadRecord]


@dataclass(frozen=True, slots=True)
class DownloadFailure:
    item_id: str
    source: str
    exit_code: int | None
    detail: str


class BatchDownloadError(RuntimeError):
    def __init__(self, failures: tuple[DownloadFailure, ...]):
        self.failures = failures
        lines = ["One or more model downloads failed:"]
        lines.extend(
            f"- {failure.item_id} ({failure.source}, exit={failure.exit_code}): "
            f"{failure.detail}"
            for failure in failures
        )
        super().__init__("\n".join(lines))


def _safe_source(url: str) -> str:
    parsed = urlsplit(url)
    return f"{parsed.hostname or 'unknown'}{parsed.path}"


def _control_text(
    item: ResolvedItem, environ: Mapping[str, str]
) -> tuple[str, tuple[str, ...]]:
    auth = auth_for_url(item.url, environ)
    source_url = authenticated_url(item.url, auth)
    lines = [
        source_url,
        f"  dir={item.destination.parent}",
        f"  out={item.destination.name}",
        "  continue=true",
        "  auto-file-renaming=false",
        "  allow-overwrite=false",
        f"  split={item.split}",
        f"  max-connection-per-server={item.split}",
    ]
    if auth.provider == "civitai":
        lines.append(f"  user-agent={_CIVITAI_USER_AGENT}")
    if auth.header:
        lines.append(f"  header={auth.header[0]}: {auth.header[1]}")
    return "\n".join(lines) + "\n", auth.secrets


def _existing_complete_path(item: ResolvedItem) -> Path | None:
    if item.existing_path and item.existing_path.is_file():
        return item.existing_path
    if item.destination.is_file():
        return item.destination
    return None


def _stream_process_lines(process, check_interrupted):
    output = Queue(maxsize=_STREAM_QUEUE_SIZE)
    stopping = threading.Event()

    def put_output(value):
        while not stopping.is_set():
            try:
                output.put(value, timeout=0.1)
                return True
            except Full:
                continue
        return False

    def read_output():
        try:
            if process.stdout is not None:
                for line in process.stdout:
                    if not put_output(line):
                        break
        finally:
            put_output(_STREAM_END)

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    try:
        while True:
            check_interrupted()
            try:
                line = output.get(timeout=0.1)
            except Empty:
                if process.poll() is not None and not reader.is_alive():
                    break
                continue
            if line is _STREAM_END:
                break
            yield line
    except BaseException:
        try:
            _stop_process(process)
        finally:
            raise
    finally:
        stopping.set()
        reader.join()


def _stop_process(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def run_downloads(
    items: tuple[ResolvedItem, ...],
    executable: str,
    environ: Mapping[str, str] | None = None,
    start_process: Callable[..., object] = subprocess.Popen,
    progress_callback: Callable[[int, int], None] | None = None,
    check_interrupted: Callable[[], None] | None = None,
) -> DownloadResult:
    environment = os.environ if environ is None else environ
    check = check_interrupted or (lambda: None)
    total_progress = len(items) * 100
    if progress_callback:
        progress_callback(0, total_progress)
    entries: dict[str, DownloadRecord] = {}
    failures: list[DownloadFailure] = []

    for item_index, item in enumerate(items):
        item_start = item_index * 100
        item_end = item_start + 100
        sidecar = Path(str(item.destination) + ".aria2")
        complete = _existing_complete_path(item)
        if complete and not sidecar.exists():
            logger.info(
                "[Model Batch Downloader] skip   %s (already exists)",
                item.item_id,
            )
            entries[item.item_id] = DownloadRecord(
                item.item_id,
                item.model_type,
                item.relative_path.as_posix(),
                str(complete),
                "skipped",
                complete.stat().st_size,
                0.0,
            )
            if progress_callback:
                progress_callback(item_end, total_progress)
            continue

        logger.info(
            "[Model Batch Downloader] start  %s (%d/%d)",
            item.item_id,
            item_index + 1,
            len(items),
        )
        item.destination.parent.mkdir(parents=True, exist_ok=True)
        started_resumed = sidecar.exists()
        control_text, secrets = _control_text(item, environment)
        control_path: Path | None = None
        started = time.monotonic()
        propagate_exception = False

        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                suffix=".aria2-input",
                delete=False,
            ) as handle:
                control_path = Path(handle.name)
                handle.write(control_text)
            try:
                control_path.chmod(0o600)
            except OSError:
                pass

            process = start_process(
                [
                    executable,
                    "--show-console-readout=true",
                    "--summary-interval=1",
                    "--console-log-level=notice",
                    "--input-file",
                    str(control_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            output_tail = deque(maxlen=40)
            highest_percent = -1
            last_log_time = float("-inf")
            stream = _stream_process_lines(process, check)
            try:
                try:
                    for line in stream:
                        safe_line = redact(line.rstrip(), secrets)
                        if safe_line:
                            output_tail.append(safe_line)
                        status = parse_aria2_progress(safe_line)
                        if status is None:
                            continue
                        if status.percent <= highest_percent:
                            continue
                        highest_percent = status.percent
                        if progress_callback:
                            progress_callback(
                                item_start + status.percent,
                                total_progress,
                            )
                        now = time.monotonic()
                        if now - last_log_time >= 1.0:
                            eta = f"  ETA {status.eta}" if status.eta else ""
                            logger.info(
                                "[Model Batch Downloader] %s %d%%  %s%s",
                                item.item_id,
                                status.percent,
                                status.speed or "-",
                                eta,
                            )
                            last_log_time = now
                    return_code = process.wait()
                except BaseException:
                    propagate_exception = True
                    try:
                        _stop_process(process)
                    finally:
                        raise
            finally:
                stream.close()

            if return_code != 0 or not item.destination.is_file() or sidecar.exists():
                detail = "\n".join(output_tail) or "aria2 did not complete the file"
                failures.append(
                    DownloadFailure(
                        item.item_id,
                        _safe_source(item.url),
                        return_code,
                        detail,
                    )
                )
                logger.info(
                    "[Model Batch Downloader] fail   %s (exit=%s)",
                    item.item_id,
                    return_code,
                )
            else:
                elapsed = time.monotonic() - started
                entries[item.item_id] = DownloadRecord(
                    item.item_id,
                    item.model_type,
                    item.relative_path.as_posix(),
                    str(item.destination),
                    "resumed" if started_resumed else "downloaded",
                    item.destination.stat().st_size,
                    elapsed,
                )
                logger.info(
                    "[Model Batch Downloader] done   %s %s in %.1fs",
                    item.item_id,
                    format_bytes(item.destination.stat().st_size),
                    elapsed,
                )
        except Exception as exception:
            if propagate_exception:
                raise
            failures.append(
                DownloadFailure(
                    item.item_id,
                    _safe_source(item.url),
                    None,
                    redact(str(exception), secrets),
                )
            )
        finally:
            if control_path is not None:
                control_path.unlink(missing_ok=True)

        if progress_callback:
            progress_callback(item_end, total_progress)

    if failures:
        raise BatchDownloadError(tuple(failures))
    return DownloadResult(entries)
