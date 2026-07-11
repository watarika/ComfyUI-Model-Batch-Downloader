from pathlib import Path
from urllib.request import Request

import pytest

import model_batch_downloader.resolution as resolution
import model_batch_downloader.security as security
from model_batch_downloader.manifest import ManifestError, ManifestItem
from model_batch_downloader.resolution import resolve_manifest
from model_batch_downloader.security import (
    auth_for_url,
    provider_for_url,
    redact,
)


def test_resolve_uses_content_disposition_and_derives_id(tmp_path):
    item = ManifestItem(
        "https://civitai.com/api/download/models/42", "checkpoints"
    )
    resolved = resolve_manifest(
        (item,),
        {"checkpoints": (tmp_path / "checkpoints",)},
        probe=lambda _url, _headers: "Realism.Illustrious.safetensors",
        environ={},
    )
    assert resolved[0].filename == "Realism.Illustrious.safetensors"
    assert resolved[0].item_id == "Realism.Illustrious"
    assert resolved[0].relative_path == Path("Realism.Illustrious.safetensors")


def test_resolve_rejects_case_insensitive_duplicate_ids(tmp_path):
    items = (
        ManifestItem(
            "https://example.com/a.safetensors",
            "loras",
            filename="a.safetensors",
            item_id="Style",
        ),
        ManifestItem(
            "https://example.com/b.safetensors",
            "loras",
            filename="b.safetensors",
            item_id="style",
        ),
    )
    with pytest.raises(ManifestError, match="duplicate id"):
        resolve_manifest(items, {"loras": (tmp_path,)}, lambda *_: None, {})


def test_resolve_rejects_duplicate_destination(tmp_path):
    items = (
        ManifestItem(
            "https://example.com/a.safetensors",
            "loras",
            filename="same.safetensors",
            item_id="first",
        ),
        ManifestItem(
            "https://example.com/b.safetensors",
            "loras",
            filename="same.safetensors",
            item_id="second",
        ),
    )
    with pytest.raises(ManifestError, match="duplicate destination"):
        resolve_manifest(items, {"loras": (tmp_path,)}, lambda *_: None, {})


def test_resolve_skips_existing_file_in_secondary_root(tmp_path):
    primary, secondary = tmp_path / "primary", tmp_path / "secondary"
    existing = secondary / "krea2" / "qwen_image_vae.safetensors"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"existing")
    item = ManifestItem(
        "https://example.com/qwen_image_vae.safetensors",
        "vae",
        subfolder="krea2",
        filename="qwen_image_vae.safetensors",
    )
    resolved = resolve_manifest(
        (item,), {"vae": (primary, secondary)}, lambda *_: None, {}
    )[0]
    assert resolved.existing_path == existing.resolve()
    assert resolved.destination == (
        primary / "krea2" / "qwen_image_vae.safetensors"
    ).resolve()


def test_resolve_rejects_secondary_root_symlink_escape(tmp_path):
    primary = tmp_path / "primary"
    secondary = tmp_path / "secondary"
    outside = tmp_path / "outside"
    primary.mkdir()
    secondary.mkdir()
    outside.mkdir()
    try:
        (secondary / "linked").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks are unavailable for this Windows account")
    (outside / "model.safetensors").write_bytes(b"outside")
    item = ManifestItem(
        "https://example.com/model.safetensors",
        "checkpoints",
        subfolder="linked",
        filename="model.safetensors",
    )
    with pytest.raises(ManifestError, match="escapes"):
        resolve_manifest(
            (item,), {"checkpoints": (primary, secondary)}, lambda *_: None, {}
        )


@pytest.mark.parametrize("domain", ("civitai.com", "civitai.red"))
def test_auth_uses_environment_only(domain):
    huggingface = auth_for_url(
        "https://huggingface.co/a/b", {"HF_TOKEN": "hf_secret"}
    )
    assert huggingface.header == ("Authorization", "Bearer hf_secret")

    civitai = auth_for_url(
        f"https://{domain}/api/download/models/1",
        {"CIVITAI_API_TOKEN": "cv_secret"},
    )
    assert provider_for_url(f"https://{domain}/api/download/models/1") == "civitai"
    assert civitai.header == ("Authorization", "Bearer cv_secret")


def test_public_host_has_no_authentication():
    auth = auth_for_url("https://example.com/model.safetensors", {})
    assert auth.provider == "public"
    assert auth.header is None


def test_civitai_cross_origin_redirect_drops_bearer_header():
    assert hasattr(security, "resolve_download_source")
    requests = []

    class Response:
        status = 307
        headers = {"Location": "https://b2.civitai.com/file/model?signature=signed"}

        def close(self):
            pass

    def open_request(request):
        requests.append(request)
        return Response()

    auth = auth_for_url(
        "https://civitai.red/api/download/models/42",
        {"CIVITAI_API_TOKEN": "cv_secret"},
    )
    source = security.resolve_download_source(
        "https://civitai.red/api/download/models/42",
        auth,
        open_request=open_request,
    )

    assert source.url == "https://b2.civitai.com/file/model?signature=signed"
    assert source.headers == {"User-Agent": security.CIVITAI_USER_AGENT}
    assert requests[0].get_header("Authorization") == "Bearer cv_secret"
    assert requests[0].get_header("User-agent") == security.CIVITAI_USER_AGENT


def test_civitai_direct_response_keeps_bearer_for_aria2():
    assert hasattr(security, "resolve_download_source")
    class Response:
        status = 200
        headers = {}

        def close(self):
            pass

    auth = auth_for_url(
        "https://civitai.red/api/download/models/42",
        {"CIVITAI_API_TOKEN": "cv_secret"},
    )
    source = security.resolve_download_source(
        "https://civitai.red/api/download/models/42",
        auth,
        open_request=lambda _request: Response(),
    )

    assert source.url == "https://civitai.red/api/download/models/42"
    assert source.headers == {
        "Authorization": "Bearer cv_secret",
        "User-Agent": security.CIVITAI_USER_AGENT,
    }


def test_civitai_redirect_rejects_https_downgrade():
    class Response:
        status = 307
        headers = {"Location": "http://civitai.red/file/model"}

        def close(self):
            pass

    auth = auth_for_url(
        "https://civitai.red/api/download/models/42",
        {"CIVITAI_API_TOKEN": "cv_secret"},
    )

    with pytest.raises(RuntimeError, match="HTTPS"):
        security.resolve_download_source(
            "https://civitai.red/api/download/models/42",
            auth,
            open_request=lambda _request: Response(),
        )


def test_civitai_redirect_to_nonstandard_port_drops_bearer():
    class Response:
        status = 307
        headers = {"Location": "https://civitai.red:8443/file/model"}

        def close(self):
            pass

    auth = auth_for_url(
        "https://civitai.red/api/download/models/42",
        {"CIVITAI_API_TOKEN": "cv_secret"},
    )
    source = security.resolve_download_source(
        "https://civitai.red/api/download/models/42",
        auth,
        open_request=lambda _request: Response(),
    )

    assert source.url == "https://civitai.red:8443/file/model"
    assert source.headers == {"User-Agent": security.CIVITAI_USER_AGENT}


def test_probe_redirect_drops_bearer_outside_original_origin():
    assert hasattr(resolution, "_SafeRedirectHandler")
    handler = resolution._SafeRedirectHandler()
    original = Request(
        "https://civitai.red/api/download/models/42",
        headers={
            "Authorization": "Bearer cv_secret",
            "User-Agent": security.CIVITAI_USER_AGENT,
        },
    )

    redirected = handler.redirect_request(
        original,
        None,
        307,
        "Temporary Redirect",
        {},
        "https://b2.civitai.com/file/model?signature=signed",
    )

    assert redirected.get_header("Authorization") is None
    assert redirected.get_header("User-agent") == security.CIVITAI_USER_AGENT


def test_redact_removes_exact_and_pattern_secrets():
    text = (
        "Authorization: Bearer hf_secret "
        "https://civitai.com/x?token=cv_secret"
    )
    clean = redact(text, ("hf_secret", "cv_secret"))
    assert "hf_secret" not in clean
    assert "cv_secret" not in clean
    assert "[REDACTED]" in clean


@pytest.mark.parametrize(
    ("text", "secret", "expected"),
    [
        (
            "download https://cdn.example.com/model?X-Amz-Signature=supersecret&part=1#signed",
            "supersecret",
            "https://cdn.example.com/model?[REDACTED]#[REDACTED]",
        ),
        (
            "download https://alice:password@example.com/models/model.safetensors",
            "password",
            "https://[REDACTED]@example.com/models/model.safetensors",
        ),
    ],
)
def test_redact_sanitizes_authenticated_urls(text, secret, expected):
    clean = redact(text)

    assert secret not in clean
    assert expected in clean


def test_redact_safely_replaces_malformed_url():
    clean = redact(
        "download https://[alice:password@example.com/model?signature=supersecret"
    )

    assert clean == "download https://[REDACTED]"


def test_resolution_error_redacts_civitai_token(tmp_path):
    item = ManifestItem(
        "https://civitai.com/api/download/models/42", "checkpoints"
    )

    def failing_probe(url, headers):
        raise RuntimeError(f"failed request: {url} headers={headers}")

    with pytest.raises(ManifestError) as captured:
        resolve_manifest(
            (item,),
            {"checkpoints": (tmp_path,)},
            failing_probe,
            {"CIVITAI_API_TOKEN": "cv_secret"},
        )
    assert "cv_secret" not in str(captured.value)
    assert "[REDACTED]" in str(captured.value)
