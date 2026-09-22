#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

from wayfinder.core import DomainError, MAX_REQUEST_BYTES, Workspace, canonical
from wayfinder.server import _decode, create_server
from wayfinder.requests import execute, read_json, replay


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise DomainError("validation", message)


def main(argv=None):
    try:
        parser = Parser(description="Local Wayfinder workspace")
        parser.add_argument("--project", type=Path, default=Path.cwd())
        commands = parser.add_subparsers(dest="command", required=True)
        commands.add_parser("init")
        call = commands.add_parser("call")
        call.add_argument("--file", type=Path)
        request = commands.add_parser("request", help="Run an operation from input data and saved receipts")
        request.add_argument("operation")
        request.add_argument("--input-file", type=Path, help="Operation input only; defaults to {}")
        request.add_argument("--actor", help="Stable agent session identity; required for writes")
        request.add_argument("--basis", type=Path, action="append", default=[], help="Reviewed record receipt; repeat for sources/endpoints")
        request.add_argument("--claim", type=Path, action="append", default=[], help="Claim receipt if separate from the basis")
        request.add_argument("--receipt", type=Path, help="New private receipt file; required for writes")
        retry = commands.add_parser("replay", help="Replay the exact saved mutation after an uncertain result")
        retry.add_argument("--receipt", type=Path, required=True)
        serve = commands.add_parser("serve")
        serve.add_argument("--port", type=int, default=4174)
        args = parser.parse_args(argv)
        if args.command == "init":
            workspace = Workspace.initialize(args.project)
            print(canonical(workspace.operate({"op": "workspace.read", "input": {}})))
            return 0
        workspace = Workspace.discover(args.project)
        if args.command in {"request", "replay"}:
            if args.command == "replay":
                result = replay(workspace, args.receipt)
            else:
                data = read_json(args.input_file) if args.input_file else {}
                result = execute(workspace, args.operation, data, args.actor, args.basis, args.claim, args.receipt)
            print(canonical(result))
            return 0 if result["ok"] else 1
        if args.command == "serve":
            if not 0 <= args.port <= 65535:
                raise DomainError("validation", "port must be from 0 to 65535")
            server = create_server(workspace, args.port)
            print(canonical({"url": server.origin, "workspace": workspace.info}), flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        if args.file:
            with args.file.open("rb") as stream:
                content = stream.read(MAX_REQUEST_BYTES + 1)
        else:
            content = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        if len(content) > MAX_REQUEST_BYTES:
            raise DomainError("validation", "Request is too large")
        try:
            envelope = _decode(content.decode("utf-8"))
        except (ValueError, UnicodeError, RecursionError):
            raise DomainError("validation", "Request must contain valid JSON") from None
        result = workspace.operate(envelope)
        print(canonical(result))
        return 0 if result["ok"] else 1
    except DomainError as error:
        print(canonical(error.response()))
        return 1
    except OSError as error:
        print(canonical({"ok": False, "error": {"code": "io", "message": str(error)}}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
