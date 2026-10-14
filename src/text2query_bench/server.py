"""
An HTTP endpoint of the TEXT2SPARQL protocol in front of a system.

``GET /?question=...&dataset=...`` returns the JSON object::

    {"dataset": ..., "question": ..., "query": ..., "language": ...,
     "explanation": ..., "valid": ..., "calls": ..., "tokens": ...}

as the TEXT2SPARQL challenge expects (its ``query`` holding a NeuroLang
query instead of a SPARQL one). An unknown dataset gives a 404 error and
a missing parameter a 400 error. The server answers one request at a
time: the engine is not shared between threads.
"""

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse


def make_handler(system, datasets: set, language: str = "en"):
    """Return the request handler answering with *system*."""

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802 (http.server's name)
            url = urlparse(self.path)
            if url.path not in ("", "/"):
                self._send(404, {"detail": "Not found"})
                return
            params = parse_qs(url.query)
            question = params.get("question", [""])[0]
            dataset = params.get("dataset", [""])[0]
            if not question or not dataset:
                self._send(400, {"detail": "question and dataset needed"})
                return
            if dataset not in datasets:
                self._send(404, {"detail": f"Unknown dataset {dataset}"})
                return
            generation = system.generate(question, language)
            self._send(200, {
                "dataset": dataset, "question": question,
                "query": generation.query, "language": generation.language,
                "explanation": generation.explanation,
                "valid": generation.valid, "error": generation.error,
                "calls": generation.calls, "tokens": generation.tokens,
            })

        def log_message(self, format, *args):  # noqa: A002
            pass

    return Handler


def make_server(system, datasets, host="127.0.0.1", port=8000) -> HTTPServer:
    """Return the server answering the questions on *datasets*."""
    return HTTPServer((host, port), make_handler(system, set(datasets)))
