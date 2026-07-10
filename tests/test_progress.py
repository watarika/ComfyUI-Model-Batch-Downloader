import pytest

from model_batch_downloader.progress import (
    Aria2Progress,
    format_bytes,
    parse_aria2_progress,
)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "[#abc 420MiB/1.0GiB(41%) CN:16 DL:18MiB ETA:33s]",
            Aria2Progress(41, "18MiB", "33s"),
        ),
        (
            "[#abc 0B/0B(0%) CN:1 DL:0B]",
            Aria2Progress(0, "0B", None),
        ),
        ("Download complete: /models/a.safetensors", None),
        ("", None),
    ],
)
def test_parse_aria2_progress(line, expected):
    assert parse_aria2_progress(line) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0 B"),
        (1024, "1.00 KiB"),
        (1024**2 * 3, "3.00 MiB"),
        (1024**3 * 2, "2.00 GiB"),
    ],
)
def test_format_bytes(value, expected):
    assert format_bytes(value) == expected
