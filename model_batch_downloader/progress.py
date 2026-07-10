from __future__ import annotations

from dataclasses import dataclass
import re


ARIA2_PROGRESS = re.compile(
    r"\((?P<percent>\d{1,3})%\).*?\bDL:(?P<speed>[^\s\]]+)"
    r"(?:\s+ETA:(?P<eta>[^\s\]]+))?"
)


@dataclass(frozen=True, slots=True)
class Aria2Progress:
    percent: int
    speed: str | None
    eta: str | None


def parse_aria2_progress(line: str) -> Aria2Progress | None:
    match = ARIA2_PROGRESS.search(line)
    if not match:
        return None
    percent = min(100, int(match.group("percent")))
    return Aria2Progress(percent, match.group("speed"), match.group("eta"))


def format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{int(size)} B" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")
