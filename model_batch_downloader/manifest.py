from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
import re
from urllib.parse import urlsplit


SUPPORTED_MODEL_TYPES = frozenset(
    {"checkpoints", "diffusion_models", "text_encoders", "vae", "loras"}
)
ALLOWED_FIELDS = frozenset({"url", "model_type", "subfolder", "filename", "id", "split"})
WINDOWS_RESERVED = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)


class ManifestError(ValueError):
    """Raised when a download manifest violates its contract."""


@dataclass(frozen=True, slots=True)
class ManifestItem:
    url: str
    model_type: str
    subfolder: str = ""
    filename: str | None = None
    item_id: str | None = None
    split: int = 16


@dataclass(frozen=True, slots=True)
class ResolvedItem:
    url: str
    model_type: str
    subfolder: str
    filename: str
    item_id: str
    split: int
    destination: Path
    relative_path: Path
    existing_path: Path | None


def validate_filename(filename: str) -> str:
    if not isinstance(filename, str) or not filename.strip():
        raise ManifestError("filename must be a non-empty string")
    value = filename.strip()
    if value != PurePath(value).name or value != PureWindowsPath(value).name:
        raise ManifestError("filename must not contain directory components")
    if value in {".", ".."} or any(ord(character) < 32 for character in value):
        raise ManifestError("filename contains unsafe characters")
    if re.search(r'[<>:"/\\|?*]', value):
        raise ManifestError("filename contains characters unsupported on Windows")
    if value.rstrip(" .") != value:
        raise ManifestError("filename must not end in a space or period")
    if value.split(".", 1)[0].upper() in WINDOWS_RESERVED:
        raise ManifestError("filename is a Windows reserved device name")
    return value


def derive_id(filename: str) -> str:
    value = Path(validate_filename(filename)).stem
    if not value:
        raise ManifestError("derived id is empty")
    return value


def _validate_subfolder(value: object) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise ManifestError("subfolder must be a string")
    windows = PureWindowsPath(value)
    posix = PurePosixPath(value)
    if (
        windows.is_absolute()
        or posix.is_absolute()
        or ".." in windows.parts
        or ".." in posix.parts
    ):
        raise ManifestError("subfolder must remain below the model root")
    return value.replace("\\", "/").strip("/")


def parse_manifest(manifest_json: str) -> tuple[ManifestItem, ...]:
    try:
        payload = json.loads(manifest_json)
    except (TypeError, json.JSONDecodeError) as exception:
        raise ManifestError(f"invalid manifest JSON: {exception}") from exception
    if not isinstance(payload, list) or not payload:
        raise ManifestError("manifest root must be a non-empty array")

    items: list[ManifestItem] = []
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            raise ManifestError(f"item {index} must be an object")
        unknown = sorted(set(raw) - ALLOWED_FIELDS)
        if unknown:
            raise ManifestError(f"item {index} has unknown field(s): {', '.join(unknown)}")

        url = raw.get("url")
        if not isinstance(url, str) or urlsplit(url).scheme not in {"http", "https"}:
            raise ManifestError(f"item {index} url must use HTTP or HTTPS")

        model_type = raw.get("model_type")
        if model_type not in SUPPORTED_MODEL_TYPES:
            raise ManifestError(f"item {index} model_type is unsupported: {model_type!r}")

        split = raw.get("split", 16)
        if type(split) is not int or not 1 <= split <= 16:
            raise ManifestError(f"item {index} split must be an integer from 1 through 16")

        filename = raw.get("filename")
        if filename is not None:
            filename = validate_filename(filename)

        item_id = raw.get("id")
        if item_id is not None and (
            not isinstance(item_id, str) or not item_id.strip()
        ):
            raise ManifestError(f"item {index} id must be a non-empty string")

        items.append(
            ManifestItem(
                url=url,
                model_type=model_type,
                subfolder=_validate_subfolder(raw.get("subfolder", "")),
                filename=filename,
                item_id=item_id.strip() if item_id is not None else None,
                split=split,
            )
        )
    return tuple(items)
