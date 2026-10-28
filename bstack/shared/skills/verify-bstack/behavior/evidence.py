#!/usr/bin/env python3
"""Record computer-use evidence for one prepared case: window screenshots, a step log, and notes."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess


def active_window_geometry():
    window = json.loads(subprocess.run(["hyprctl", "activewindow", "-j"], capture_output=True, text=True,
                                       check=True).stdout or "{}")
    if not window.get("size"):
        return None, None
    (x, y), (width, height) = window["at"], window["size"]
    return f"{x},{y} {width}x{height}", window.get("class")


def shot(case, slug, full=False):
    screens = case / "screens"
    screens.mkdir(exist_ok=True)
    number = len(list(screens.glob("*.png"))) + 1
    name = f"{number:03d}-{re.sub(r'[^a-z0-9]+', '-', slug.lower()).strip('-')}.png"
    geometry, window = (None, None) if full else active_window_geometry()
    command = ["grim", *(["-g", geometry] if geometry else []), str(screens / name)]
    subprocess.run(command, check=True)
    return screens / name, window


def step(case, intent, action, observed, result, screenshot):
    log = case / "steps.jsonl"
    number = sum(1 for _ in log.open()) + 1 if log.exists() else 1
    entry = {"step": number, "at": datetime.now(timezone.utc).isoformat(), "intent": intent, "action": action,
             "observed": observed, "result": result, "screenshot": screenshot}
    with log.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("shot", help="Screenshot the active window into the case's screens/ folder")
    capture.add_argument("case", type=Path)
    capture.add_argument("slug")
    capture.add_argument("--full", action="store_true", help="Capture the whole screen instead of the active window")
    logging = commands.add_parser("step", help="Append one action to the case's steps.jsonl")
    logging.add_argument("case", type=Path)
    logging.add_argument("--intent", required=True)
    logging.add_argument("--action", required=True)
    logging.add_argument("--observed", required=True)
    logging.add_argument("--result", choices=("ok", "retry", "blocked", "failed"), default="ok")
    logging.add_argument("--shot", default=None, help="Screenshot path returned by `shot`")
    noting = commands.add_parser("note", help="Append a finding to the case's notes.md")
    noting.add_argument("case", type=Path)
    noting.add_argument("text")
    args = parser.parse_args()
    if args.command == "shot":
        path, window = shot(args.case, args.slug, args.full)
        print(json.dumps({"screenshot": str(path), "window": window}))
    elif args.command == "step":
        print(json.dumps(step(args.case, args.intent, args.action, args.observed, args.result, args.shot)))
    else:
        with (args.case / "notes.md").open("a") as handle:
            handle.write(f"- {datetime.now(timezone.utc).isoformat()} {args.text}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
