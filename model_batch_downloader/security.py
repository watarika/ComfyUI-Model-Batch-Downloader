from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_HTTP_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class AuthData:
    provider: str
    header: tuple[str, str] | None = None
    query_token: str | None = None

    @property
    def secrets(self) -> tuple[str, ...]:
        values: list[str] = []
        if self.header:
            values.append(self.header[1].removeprefix("Bearer "))
        if self.query_token:
            values.append(self.query_token)
        return tuple(value for value in values if value)


def provider_for_url(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    if host == "huggingface.co" or host.endswith(".huggingface.co"):
        return "huggingface"
    if host == "civitai.com" or host.endswith(".civitai.com"):
        return "civitai"
    return "public"


def auth_for_url(url: str, environ: Mapping[str, str]) -> AuthData:
    provider = provider_for_url(url)
    if provider == "huggingface" and environ.get("HF_TOKEN"):
        return AuthData(
            provider, header=("Authorization", f"Bearer {environ['HF_TOKEN']}")
        )
    if provider == "civitai" and environ.get("CIVITAI_API_TOKEN"):
        return AuthData(provider, query_token=environ["CIVITAI_API_TOKEN"])
    return AuthData(provider)


def authenticated_url(url: str, auth: AuthData) -> str:
    if not auth.query_token:
        return url
    parsed = urlsplit(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["token"] = auth.query_token
    return urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, urlencode(query), "")
    )


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
