from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import threading

import pytest

from model_batch_downloader.aria2_runner import run_downloads
from model_batch_downloader.manifest import ResolvedItem


DATA = b"model-downloader-smoke" * 4096


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        start = 0
        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            start = int(range_header.removeprefix("bytes=").split("-", 1)[0] or 0)
            self.send_response(206)
            self.send_header(
                "Content-Range", f"bytes {start}-{len(DATA) - 1}/{len(DATA)}"
            )
        else:
            self.send_response(200)
        body = DATA[start:]
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
            4,
            destination,
            Path(destination.name),
            None,
        )
        result = run_downloads((item,), shutil.which("aria2c"), {})
        assert result.entries["tiny"].status == "downloaded"
        assert destination.read_bytes() == DATA
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
