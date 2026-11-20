#!/usr/bin/env python3
"""Small loopback-only HTTP receiver for installer report smoke tests."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class Receiver(BaseHTTPRequestHandler):
    output_file: Path

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw": body}
        with self.output_file.open("a", encoding="utf-8") as output:
            output.write(json.dumps({"path": self.path, "payload": payload}, ensure_ascii=False) + "\n")
        self.send_response(204)
        self.end_headers()

    def log_message(self, format, *args):
        return


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ready-file", required=True)
    arguments = parser.parse_args()

    Receiver.output_file = Path(arguments.output)
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), Receiver)
    Path(arguments.ready_file).write_text(str(server.server_port), encoding="utf-8")
    server.serve_forever()


if __name__ == "__main__":
    main()
