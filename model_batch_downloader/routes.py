"""HTTP routes used by the browser-side manifest editor."""

from __future__ import annotations

import asyncio
import os

from aiohttp import web
from server import PromptServer

from .manifest import derive_id
from .resolution import probe_filename
from .security import auth_for_url, redact, resolve_download_source


@PromptServer.instance.routes.post("/model-batch-downloader/resolve")
async def resolve_download_name(request: web.Request) -> web.Response:
    """Resolve a remote URL to the filename and implicit model id."""
    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Request body must be valid JSON."}, status=400)

    url = payload.get("url") if isinstance(payload, dict) else None
    if not isinstance(url, str) or not url.strip():
        return web.json_response({"error": "url must be a string"}, status=400)

    auth = auth_for_url(url, os.environ)
    try:
        source = await asyncio.to_thread(resolve_download_source, url, auth)
        filename = await asyncio.to_thread(
            probe_filename,
            source.url,
            source.headers,
        )
    except Exception as exc:
        return web.json_response(
            {"error": redact(str(exc), auth.secrets)},
            status=400,
        )

    return web.json_response({"filename": filename, "id": derive_id(filename)})
