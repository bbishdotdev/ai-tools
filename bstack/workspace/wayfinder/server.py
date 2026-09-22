from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import socket
from urllib.parse import urlsplit

from .core import MAX_REQUEST_BYTES, canonical

ASSETS = Path(__file__).resolve().parents[1] / "assets"
FILES = {"/": ("index.html", "text/html; charset=utf-8"),
         "/index.html": ("index.html", "text/html; charset=utf-8"),
         "/app.js": ("app.js", "text/javascript; charset=utf-8"),
         "/style.css": ("style.css", "text/css; charset=utf-8"),
         "/app.js.LEGAL.txt": ("app.js.LEGAL.txt", "text/plain; charset=utf-8"),
         "/THIRD_PARTY_NOTICES.txt": ("THIRD_PARTY_NOTICES.txt", "text/plain; charset=utf-8")}
STATUS = {"validation": 400, "not_found": 404, "workspace_missing": 404, "storage": 500}


def _decode(raw):
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Invalid JSON number")))


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address


class Handler(BaseHTTPRequestHandler):
    server_version = "Wayfinder"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    def log_message(self, format, *args):
        pass

    def respond(self, status, value, content_type="application/json; charset=utf-8"):
        body = canonical(value).encode() if isinstance(value, (dict, list)) else value
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, socket.timeout):
                pass

    def error(self, status, code, message):
        self.respond(status, {"ok": False, "error": {"code": code, "message": message}})

    def send_error(self, code, message=None, explain=None):
        self.error(code, "validation", message or "Invalid HTTP request")

    def allowed(self, mutation=False):
        hosts = self.headers.get_all("Host", [])
        origins = self.headers.get_all("Origin", [])
        sites = self.headers.get_all("Sec-Fetch-Site", [])
        if hosts != [self.server.expected_host]:
            self.error(403, "forbidden", "Unexpected Host")
            return False
        if origins and origins != [self.server.origin] or sites and sites != ["same-origin"] and sites != ["none"]:
            self.error(403, "forbidden", "Cross-origin requests are forbidden")
            return False
        if mutation:
            tokens = self.headers.get_all("X-Wayfinder-Token", [])
            if (origins != [self.server.origin] or len(tokens) != 1 or not tokens[0].isascii()
                    or not secrets.compare_digest(tokens[0], self.server.token)):
                self.error(403, "forbidden", "Origin and valid workspace token are required")
                return False
        return True

    def do_GET(self):
        if not self.allowed():
            return
        if self.path == "/api/bootstrap":
            self.respond(200, {"token": self.server.token, "workspace": self.server.workspace.info})
            return
        parsed = urlsplit(self.path)
        asset = FILES.get(parsed.path) if not parsed.scheme and not parsed.netloc else None
        if not asset:
            self.error(404, "not_found", "Resource not found")
            return
        path = ASSETS / asset[0]
        if path.is_symlink() or not path.is_file():
            self.error(404, "not_found", "Compiled asset not found")
            return
        self.respond(200, path.read_bytes(), asset[1])

    def do_POST(self):
        if not self.allowed(mutation=True):
            return
        if self.path != "/api/operation":
            self.error(404, "not_found", "Operation endpoint not found")
            return
        types = self.headers.get_all("Content-Type", [])
        if len(types) != 1 or types[0].lower().split(";", 1)[0].strip() != "application/json":
            self.error(400, "validation", "Content-Type must be application/json")
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get_all("Transfer-Encoding") or len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit():
            self.error(400, "validation", "One valid Content-Length is required")
            return
        if len(lengths[0]) > 10 or int(lengths[0]) > MAX_REQUEST_BYTES:
            self.error(413, "validation", "Request body is too large")
            return
        length = int(lengths[0])
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("Incomplete request")
            envelope = _decode(body.decode("utf-8"))
        except socket.timeout:
            self.error(400, "validation", "Timed out reading request")
            return
        except (ValueError, UnicodeError, RecursionError):
            self.error(400, "validation", "Request must contain valid JSON")
            return
        result = self.server.workspace.operate(envelope)
        status = 200 if result["ok"] else STATUS.get(result["error"]["code"], 409)
        self.respond(status, result)


def create_server(workspace, port=0):
    server = Server(("127.0.0.1", port), Handler)
    server.workspace = workspace
    server.token = secrets.token_urlsafe(32)
    server.expected_host = f"127.0.0.1:{server.server_address[1]}"
    server.origin = "http://" + server.expected_host
    return server
