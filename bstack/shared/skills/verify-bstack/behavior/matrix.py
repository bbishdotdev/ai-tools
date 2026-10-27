#!/usr/bin/env python3
"""Render the README compatibility matrix from recorded behavior results."""
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from run import RESULTS, ROOT, SCENARIOS

ASSET = ROOT / "bstack/assets/compatibility.svg"
COLUMNS = (("skills", "Skills"), ("auto", "Auto mode"), ("pr", "PR workflows"), ("hooks", "Hooks"))
BADGES = {
    "supported": ("#16392f", "#2f8066", "#70d6a8", "#d9f9e8", "Supported"),
    "partial": ("#3a301d", "#907442", "#f2c875", "#ffeac0", "Partial"),
    "unsupported": ("#292d34", "#555d67", "#9da7b3", "#d1d7df", "Not supported"),
}


def proven(row):
    return row is not None and row["repeats"] > 0 and row["passes"] == row["repeats"]


def status(host, column):
    if column not in host["bindings"]:
        return "unsupported"
    required = [name for name, scenario in SCENARIOS.items() if scenario["column"] == column]
    rows = [host["scenarios"].get(name) for name in required]
    if not all(proven(row) for row in rows):
        return "partial"
    if column == "hooks":
        runs = host["scenarios"].values()
        if any(row["reminder_hook_runs"] < row["repeats"] for row in runs) or set(host["scenarios"]) != set(SCENARIOS):
            return "partial"
    return "supported"


def badge(name):
    fill, stroke, dot, ink, label = BADGES[name]
    return (f'<g id="{name}"><rect width="130" height="28" rx="7" fill="{fill}" stroke="{stroke}"/>'
            f'<circle cx="15" cy="14" r="5" fill="{dot}"/><text x="27" y="18" fill="{ink}" font-size="12" '
            f'font-weight="600">{label}</text></g>')


def render(data):
    groups = [("CLI", [h for h in data["hosts"].values() if h["surface"] == "cli"]),
              ("DESKTOP / EDITOR", [h for h in data["hosts"].values() if h["surface"] == "desktop"])]
    rows, y, stripe = [], 172, 0
    for title, hosts in groups:
        rows.append(f'<text x="36" y="{y}" fill="#8998a8" font-size="12" font-weight="700" letter-spacing="2">{title}</text>')
        y += 5
        for host in hosts:
            cells = "".join(f'<use href="#{status(host, key)}" x="{332 + 205 * index}" y="{y + 7}"/>'
                            for index, (key, _) in enumerate(COLUMNS))
            fill = "#171c22" if stripe % 2 == 0 else "#101318"
            rows.append(f'<g><rect x="24" y="{y}" width="1072" height="42" rx="6" fill="{fill}"/>'
                        f'<text x="38" y="{y + 27}" fill="#edf1f5" font-size="15" font-weight="550">{host["label"]}</text>'
                        f'{cells}</g>')
            y += 46
            stripe += 1
        y += 37
    height = y + 30
    header = "".join(f'<text x="{342 + 205 * index}" y="128">{label}</text>' for index, (_, label) in enumerate(COLUMNS))
    footer = ("Supported: every mapped behavior scenario passed every repeat on the recorded run. "
              "Partial: a binding exists but is not yet proven. Not supported: no bstack binding yet.")
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1120 {height}" role="img" aria-labelledby="title description">',
        '<title id="title">bstack tool compatibility</title>',
        '<desc id="description">Status by tool across skills, automatic routing, PR workflows, and hooks, generated from recorded behavior scenarios.</desc>',
        "<defs>" + "\n".join(badge(name) for name in BADGES) + "</defs>",
        f'<rect width="1120" height="{height}" rx="18" fill="#101318"/>',
        '<g font-family="Inter, ui-sans-serif, system-ui, sans-serif">',
        '<text x="34" y="48" fill="#f2f5f8" font-size="25" font-weight="700">Tool compatibility</text>',
        f'<text x="34" y="76" fill="#a8b3bf" font-size="14">Proven by behavior scenarios, last recorded {data["updated"] or "never"}</text>',
        '<rect x="24" y="101" width="1072" height="43" rx="8" fill="#1b2027"/>',
        f'<g fill="#c8d1d9" font-size="13" font-weight="700"><text x="37" y="128">Tool</text>{header}</g>',
        *rows,
        f'<line x1="24" y1="{y - 32}" x2="1096" y2="{y - 32}" stroke="#343c46"/>',
        f'<text x="34" y="{y}" fill="#a8b3bf" font-size="13">{footer}</text>',
        "</g></svg>", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the committed asset is stale")
    args = parser.parse_args()
    data = json.loads(RESULTS.read_text())
    svg = render(data)
    if args.check:
        stale = ASSET.read_text() != svg
        print("stale" if stale else "current")
        return int(stale)
    ASSET.write_text(svg)
    for host in data["hosts"].values():
        print(f'{host["label"]:22} ' + "  ".join(f"{key}={status(host, key)}" for key, _ in COLUMNS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
