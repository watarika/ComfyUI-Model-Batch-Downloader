import asyncio
import json

import model_batch_downloader.routes as subject
from model_batch_downloader.security import CIVITAI_USER_AGENT, DownloadSource


class Request:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


def test_preview_returns_resolved_filename_and_id(monkeypatch):
    seen = {}

    def fake_probe(url, headers):
        seen["url"] = url
        seen["headers"] = headers
        return "model.fp16.safetensors"

    monkeypatch.setattr(subject, "probe_filename", fake_probe)
    monkeypatch.setattr(
        subject,
        "resolve_download_source",
        lambda url, _auth: DownloadSource(
            url,
            {
                "Authorization": "Bearer cv_secret",
                "User-Agent": CIVITAI_USER_AGENT,
            },
        ),
    )
    monkeypatch.setenv("CIVITAI_API_TOKEN", "cv_secret")

    response = asyncio.run(
        subject.resolve_download_name(
            Request({"url": "https://civitai.com/api/download/models/42"})
        )
    )
    payload = json.loads(response.text)

    assert response.status == 200
    assert payload == {"filename": "model.fp16.safetensors", "id": "model.fp16"}
    assert seen["url"] == "https://civitai.com/api/download/models/42"
    assert seen["headers"] == {
        "Authorization": "Bearer cv_secret",
        "User-Agent": CIVITAI_USER_AGENT,
    }


def test_preview_rejects_non_string_url():
    response = asyncio.run(subject.resolve_download_name(Request({"url": 42})))
    assert response.status == 400
    assert json.loads(response.text) == {"error": "url must be a string"}


def test_preview_redacts_token_from_failure(monkeypatch):
    def fake_probe(url, headers):
        raise RuntimeError(f"failed: {url} headers={headers}")

    monkeypatch.setattr(subject, "probe_filename", fake_probe)
    monkeypatch.setattr(
        subject,
        "resolve_download_source",
        lambda url, _auth: DownloadSource(
            url,
            {
                "Authorization": "Bearer cv_secret",
                "User-Agent": CIVITAI_USER_AGENT,
            },
        ),
    )
    monkeypatch.setenv("CIVITAI_API_TOKEN", "cv_secret")

    response = asyncio.run(
        subject.resolve_download_name(
            Request({"url": "https://civitai.com/api/download/models/42"})
        )
    )
    payload = json.loads(response.text)

    assert response.status == 400
    assert "cv_secret" not in payload["error"]
    assert "[REDACTED]" in payload["error"]
