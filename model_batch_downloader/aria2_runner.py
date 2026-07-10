from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Callable, Mapping
from urllib.parse import urlsplit

from .manifest import ResolvedItem
from .security import auth_for_url, authenticated_url, redact


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
    if auth.header:
        lines.append(f"  header={auth.header[0]}: {auth.header[1]}")
    return "\n".join(lines) + "\n", auth.secrets


def _existing_complete_path(item: ResolvedItem) -> Path | None:
    if item.existing_path and item.existing_path.is_file():
        return item.existing_path
    if item.destination.is_file():
        return item.destination
    return None


def run_downloads(
    items: tuple[ResolvedItem, ...],
    executable: str,
    environ: Mapping[str, str] | None = None,
    run_process: Callable[..., object] = subprocess.run,
) -> DownloadResult:
    environment = os.environ if environ is None else environ
    entries: dict[str, DownloadRecord] = {}
    failures: list[DownloadFailure] = []

    for item in items:
        sidecar = Path(str(item.destination) + ".aria2")
        complete = _existing_complete_path(item)
        if complete and not sidecar.exists():
            entries[item.item_id] = DownloadRecord(
                item.item_id,
                item.model_type,
                item.relative_path.as_posix(),
                str(complete),
                "skipped",
                complete.stat().st_size,
                0.0,
            )
            continue

        item.destination.parent.mkdir(parents=True, exist_ok=True)
        started_resumed = sidecar.exists()
        control_text, secrets = _control_text(item, environment)
        control_path: Path | None = None
        started = time.monotonic()

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

            completed = run_process(
                [executable, "--input-file", str(control_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            return_code = getattr(completed, "returncode", None)
            stdout = getattr(completed, "stdout", "") or ""
            stderr = getattr(completed, "stderr", "") or ""
            if return_code != 0 or not item.destination.is_file() or sidecar.exists():
                detail = redact(
                    (stderr or stdout or "aria2 did not complete the file")[:2000],
                    secrets,
                )
                failures.append(
                    DownloadFailure(
                        item.item_id,
                        _safe_source(item.url),
                        return_code,
                        detail,
                    )
                )
                continue

            entries[item.item_id] = DownloadRecord(
                item.item_id,
                item.model_type,
                item.relative_path.as_posix(),
                str(item.destination),
                "resumed" if started_resumed else "downloaded",
                item.destination.stat().st_size,
                time.monotonic() - started,
            )
        except Exception as exception:
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

    if failures:
        raise BatchDownloadError(tuple(failures))
    return DownloadResult(entries)
