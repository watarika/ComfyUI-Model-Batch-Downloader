from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Callable
from typing import Mapping
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import HTTPErrorProcessor, Request, build_opener


_HTTP_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
CIVITAI_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
)
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


@dataclass(frozen=True, slots=True)
class AuthData:
    provider: str
    header: tuple[str, str] | None = None

    @property
    def secrets(self) -> tuple[str, ...]:
        values: list[str] = []
        if self.header:
            values.append(self.header[1].removeprefix("Bearer "))
        return tuple(value for value in values if value)


@dataclass(frozen=True, slots=True)
class DownloadSource:
    url: str
    headers: dict[str, str]


class _NoRedirect(HTTPErrorProcessor):
    def http_response(self, request, response):
        return response

    https_response = http_response


def _open_without_redirect(request: Request):
    return build_opener(_NoRedirect).open(request, timeout=20)


def provider_for_url(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if host == "huggingface.co" or host.endswith(".huggingface.co"):
        return "huggingface"
    if host in {"civitai.com", "civitai.red"}:
        return "civitai"
    return "public"


def _trusted_civitai_origin(url: str) -> bool:
    parsed = urlsplit(url)
    return (
        parsed.scheme.lower() == "https"
        and (parsed.hostname or "").lower() in {"civitai.com", "civitai.red"}
        and parsed.port in {None, 443}
    )


def auth_for_url(url: str, environ: Mapping[str, str]) -> AuthData:
    provider = provider_for_url(url)
    if provider == "huggingface" and environ.get("HF_TOKEN"):
        return AuthData(
            provider, header=("Authorization", f"Bearer {environ['HF_TOKEN']}")
        )
    if provider == "civitai" and environ.get("CIVITAI_API_TOKEN"):
        return AuthData(
            provider,
            header=("Authorization", f"Bearer {environ['CIVITAI_API_TOKEN']}"),
        )
    return AuthData(provider)


def resolve_download_source(
    url: str,
    auth: AuthData,
    open_request: Callable[[Request], object] = _open_without_redirect,
) -> DownloadSource:
    headers = {auth.header[0]: auth.header[1]} if auth.header else {}
    if auth.provider != "civitai":
        return DownloadSource(url, headers)
    if not _trusted_civitai_origin(url):
        raise RuntimeError("Civitai download URLs must use HTTPS on the standard port")

    headers["User-Agent"] = CIVITAI_USER_AGENT
    current_url = url
    for _ in range(10):
        request = Request(
            current_url,
            headers={**headers, "Range": "bytes=0-0"},
            method="GET",
        )
        response = open_request(request)
        try:
            status = response.status
            location = response.headers.get("Location")
        finally:
            response.close()

        if status not in _REDIRECT_STATUSES or not location:
            return DownloadSource(current_url, headers)

        next_url = urljoin(current_url, location)
        if urlsplit(next_url).scheme.lower() != "https":
            raise RuntimeError("Civitai download redirects must remain on HTTPS")
        if not _trusted_civitai_origin(next_url):
            return DownloadSource(next_url, {"User-Agent": CIVITAI_USER_AGENT})
        current_url = next_url

    raise RuntimeError("Civitai download URL exceeded the redirect limit")


def _sanitize_url(match: re.Match[str]) -> str:
    url = match.group(0)
    try:
        parsed = urlsplit(url)
    except ValueError:
        return f"{url.split(':', 1)[0]}://[REDACTED]"
    netloc = parsed.netloc
    if "@" in netloc:
        netloc = f"[REDACTED]@{netloc.rsplit('@', 1)[1]}"
    return urlunsplit(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            "[REDACTED]" if parsed.query else "",
            "[REDACTED]" if parsed.fragment else "",
        )
    )


def redact(text: str, secrets: tuple[str, ...] = ()) -> str:
    clean = text
    for secret in sorted((secret for secret in secrets if secret), key=len, reverse=True):
        clean = clean.replace(secret, "[REDACTED]")
    clean = re.sub(
        r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+",
        r"\1[REDACTED]",
        clean,
    )
    clean = re.sub(r"(?i)([?&]token=)[^&\s]+", r"\1[REDACTED]", clean)
    return _HTTP_URL_PATTERN.sub(_sanitize_url, clean)
