from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from email.message import Message
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from .manifest import (
    ManifestError,
    ManifestItem,
    ResolvedItem,
    derive_id,
    validate_filename,
)
from .security import auth_for_url, authenticated_url, redact


def probe_filename(url: str, headers: Mapping[str, str]) -> str:
    request = Request(url, headers=dict(headers), method="HEAD")
    try:
        response = urlopen(request, timeout=20)
    except Exception:
        request = Request(
            url,
            headers={**dict(headers), "Range": "bytes=0-0"},
            method="GET",
        )
        response = urlopen(request, timeout=20)

    with response:
        disposition = response.headers.get("Content-Disposition")
        if disposition:
            message = Message()
            message["Content-Disposition"] = disposition
            filename = message.get_filename()
            if filename:
                return validate_filename(Path(unquote(filename)).name)

        for candidate_url in (response.geturl(), url):
            basename = Path(unquote(urlsplit(candidate_url).path)).name
            if basename and "." in basename:
                return validate_filename(basename)

    raise ManifestError("remote response did not provide a safe filename")


def _contained(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def resolve_manifest(
    items: tuple[ManifestItem, ...],
    roots_by_type: Mapping[str, Sequence[Path]],
    probe: Callable[[str, Mapping[str, str]], str],
    environ: Mapping[str, str] | None = None,
) -> tuple[ResolvedItem, ...]:
    environment = os.environ if environ is None else environ
    resolved: list[ResolvedItem] = []
    ids: set[str] = set()
    destinations: set[str] = set()

    for index, item in enumerate(items):
        roots = tuple(
            Path(root).resolve() for root in roots_by_type.get(item.model_type, ())
        )
        if not roots:
            raise ManifestError(
                f"item {index} has no configured root for {item.model_type}"
            )

        auth = auth_for_url(item.url, environment)
        headers = {auth.header[0]: auth.header[1]} if auth.header else {}
        try:
            filename = item.filename or probe(
                authenticated_url(item.url, auth), headers
            )
        except Exception as exception:
            raise ManifestError(
                f"item {index} filename resolution failed: "
                f"{redact(str(exception), auth.secrets)}"
            ) from exception

        item_id = item.item_id or derive_id(filename)
        id_key = item_id.casefold()
        if id_key in ids:
            raise ManifestError(f"duplicate id after resolution: {item_id}")
        ids.add(id_key)

        relative = (
            Path(item.subfolder) / filename if item.subfolder else Path(filename)
        )
        destination = (roots[0] / relative).resolve()
        if not _contained(roots[0], destination):
            raise ManifestError(
                f"item {index} destination escapes the {item.model_type} root"
            )

        destination_key = os.path.normcase(str(destination))
        if destination_key in destinations:
            raise ManifestError(f"duplicate destination after resolution: {relative}")
        destinations.add(destination_key)

        existing = None
        for root in roots:
            candidate = (root / relative).resolve()
            if not _contained(root, candidate):
                raise ManifestError(
                    f"item {index} existing path escapes a configured model root"
                )
            if candidate.is_file() and existing is None:
                existing = candidate

        resolved.append(
            ResolvedItem(
                item.url,
                item.model_type,
                item.subfolder,
                filename,
                item_id,
                item.split,
                destination,
                relative,
                existing,
            )
        )

    return tuple(resolved)
