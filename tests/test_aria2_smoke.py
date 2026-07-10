from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import threading
import time

import pytest

from model_batch_downloader.aria2_runner import run_downloads
from model_batch_downloader.manifest import ResolvedItem


DATA = (b"model-downloader-smoke" * 50_000)[: 1024 * 1024]
CHUNK_SIZE = 16 * 1024
CHUNK_DELAY = 0.035


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        start = 0
        end = len(DATA) - 1
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            start_text, end_text = range_header.removeprefix("bytes=").split("-", 1)
            if start_text:
                start = int(start_text)
                if end_text:
                    end = min(int(end_text), end)
            else:
                start = max(len(DATA) - int(end_text), 0)
            if start >= len(DATA) or end < start:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{len(DATA)}")
                self.end_headers()
                return
            self.send_response(206)
            self.send_header(
                "Content-Range", f"bytes {start}-{end}/{len(DATA)}"
            )
        else:
            self.send_response(200)
        body = memoryview(DATA)[start : end + 1]
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        for offset in range(0, len(body), CHUNK_SIZE):
            self.wfile.write(body[offset : offset + CHUNK_SIZE])
            self.wfile.flush()
            if offset + CHUNK_SIZE < len(body):
                time.sleep(CHUNK_DELAY)

    def log_message(self, _format, *_args):
        return


@pytest.mark.skipif(shutil.which("aria2c") is None, reason="aria2c not installed")
def test_real_aria2_downloads_from_local_range_server(tmp_path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        destination = tmp_path / "tiny.safetensors"
        item = ResolvedItem(
            f"http://127.0.0.1:{server.server_port}/tiny.safetensors",
            "diffusion_models",
            "",
            destination.name,
            "tiny",
            1,
            destination,
            Path(destination.name),
            None,
        )
        progress = []
        started = time.monotonic()
        result = run_downloads(
            (item,),
            shutil.which("aria2c"),
            {},
            progress_callback=lambda current, total: progress.append(
                (current, total)
            ),
        )
        elapsed = time.monotonic() - started
        assert result.entries["tiny"].status == "downloaded"
        assert destination.read_bytes() == DATA
        assert elapsed > 1.0
        assert progress[0] == (0, 100)
        assert progress[-1] == (100, 100)
        assert any(0 < current < total for current, total in progress)
        assert progress == sorted(progress)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
