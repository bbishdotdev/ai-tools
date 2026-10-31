#!/usr/bin/env python3
"""Render the README compatibility matrix from recorded behavior results."""
import argparse
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
from run import RESULTS, ROOT, SCENARIOS

ASSET = ROOT / "bstack/assets/compatibility.svg"
TOOLS_ASSET = ROOT / "bstack/assets/supported-tools.svg"
LOGOS = ROOT / "bstack/assets/logos"
TOOLS = (("Claude Code", "claude-code", ("claude-cli", "claude-desktop")),
         ("Codex", "codex", ("codex-cli", "codex-desktop")),
         ("Cursor", "cursor", ("cursor-cli", "cursor-desktop")),
         ("OpenCode", "opencode", ("opencode-cli", "opencode-desktop")),
         ("GitHub Copilot", "github-copilot", ("copilot-cli", "vscode-copilot")),
         ("Grok", "grok", ("grok-cli",)),
         ("Amp", "amp", ("amp-cli",)))
SURFACE_PILLS = {"CLI": ("#20262e", "#4a535e", "#c8d1d9"), "CLI + Desktop": ("#132f3a", "#2f7a90", "#bfeaf7")}
MODELS = ROOT / "bstack/audit/model-results.md"
ORDER = ("codex-cli", "claude-cli", "cursor-cli", "grok-cli", "amp-cli", "copilot-cli", "opencode-cli",
         "codex-desktop", "claude-desktop", "cursor-desktop", "vscode-copilot", "opencode-desktop",
         "codex-tui", "claude-tui", "cursor-tui", "grok-tui", "amp-tui", "opencode-tui")
QUALITY_SCENARIOS = ("misleading-bug", "feature-verifier", "adr-rejected", "late-pr", "direct-pr", "compaction-resume")
COLUMNS = (("skills", "Skills"), ("auto", "Auto mode"), ("pr", "PR workflows"), ("hooks", "Hooks"))
BADGES = {
    "supported": ("#16392f", "#2f8066", "#70d6a8", "#d9f9e8", "Supported"),
    "partial": ("#3a301d", "#907442", "#f2c875", "#ffeac0", "Partial"),
    "unsupported": ("#292d34", "#555d67", "#9da7b3", "#d1d7df", "Not supported"),
}


def proven(row):
    return (row is not None and row["repeats"] > 0 and row["passes"] == row["repeats"]
            and row.get("attempts", row["repeats"]) == row["repeats"] and not row.get("errors"))


def status(host, column):
    if column not in host["bindings"]:
        return "unsupported"
    skipped = set(host.get("not_applicable", []))
    required = [name for name, scenario in SCENARIOS.items() if scenario["column"] == column and name not in skipped]
    rows = [host["scenarios"].get(name) for name in required]
    if not all(proven(row) for row in rows):
        return "partial"
    if column == "hooks":
        runs = [row for name, row in host["scenarios"].items() if SCENARIOS[name].get("reminder", True)]
        if any(row.get("errors") or row.get("attempts", row["repeats"]) != row["repeats"]
               or row["reminder_hook_runs"] < row["repeats"] for row in runs) \
                or set(host["scenarios"]) != set(SCENARIOS) - skipped:
            return "partial"
    return "supported"


def badge(name):
    fill, stroke, dot, ink, label = BADGES[name]
    return (f'<g id="{name}"><rect width="130" height="28" rx="7" fill="{fill}" stroke="{stroke}"/>'
            f'<circle cx="15" cy="14" r="5" fill="{dot}"/><text x="27" y="18" fill="{ink}" font-size="12" '
            f'font-weight="600">{label}</text></g>')


def render(data):
    hosts = [data["hosts"][key] for key in ORDER]
    groups = [("CLI", [h for h in hosts if h["surface"] == "cli"]),
              ("INTERACTIVE CLI", [h for h in hosts if h["surface"] == "tui" and h["scenarios"]]),
              ("DESKTOP / EDITOR", [h for h in hosts if h["surface"] == "desktop"])]
    groups = [(title, members) for title, members in groups if members]
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
    footer = ("Supported: every recorded attempt passed integration. Partial: bound but not yet proven. "
              "Model quality is tracked separately.")
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


def logo(key, x, y, width, height):
    source = (LOGOS / f"{key}.svg").read_text()
    view = re.search(r'viewBox="([^"]+)"', source).group(1)
    body = re.search(r"<svg[^>]*>(.*)</svg>", source, re.S).group(1)
    return f'<svg x="{x}" y="{y}" width="{width}" height="{height}" viewBox="{view}" fill="#edf1f5">{body}</svg>'


def render_tools(data):
    width, tile, top = 1120, 1072 / len(TOOLS), 70
    tiles = []
    for index, (name, key, hosts) in enumerate(TOOLS):
        bound = [data["hosts"][host] for host in hosts if data["hosts"][host]["bindings"]]
        surfaces = "CLI + Desktop" if any(host["surface"] == "desktop" for host in bound) else "CLI"
        fill, stroke, ink = SURFACE_PILLS[surfaces]
        x, center = 24 + index * tile, 24 + index * tile + tile / 2
        pill = 7.4 * len(surfaces) + 22
        tiles.append(f'<g><rect x="{x + 4:.1f}" y="{top}" width="{tile - 8:.1f}" height="146" rx="10" fill="#171c22"/>'
                     f'{logo(key, f"{center - 32:.1f}", top + 20, 64, 38)}'
                     f'<text x="{center:.1f}" y="{top + 88}" text-anchor="middle" fill="#edf1f5" font-size="15" '
                     f'font-weight="600">{name}</text>'
                     f'<rect x="{center - pill / 2:.1f}" y="{top + 104}" width="{pill:.1f}" height="24" rx="12" '
                     f'fill="{fill}" stroke="{stroke}"/><text x="{center:.1f}" y="{top + 120}" text-anchor="middle" '
                     f'fill="{ink}" font-size="12" font-weight="600">{surfaces}</text></g>')
    names = ", ".join(name for name, _, _ in TOOLS)
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 240" role="img" aria-labelledby="tools-title tools-description">',
        '<title id="tools-title">Tools bstack supports</title>',
        f'<desc id="tools-description">{names}. Each is marked CLI or CLI plus desktop.</desc>',
        f'<rect width="{width}" height="240" rx="18" fill="#101318"/>',
        '<g font-family="Inter, ui-sans-serif, system-ui, sans-serif">',
        '<text x="34" y="46" fill="#f2f5f8" font-size="21" font-weight="700">Works with</text>',
        *tiles, "</g></svg>", ""])


def render_models(data):
    header = "| Tool | Model | " + " | ".join(QUALITY_SCENARIOS) + " |"
    lines = ["# Model results", "",
             "How each model did with bstack on each host. Each cell is `integration · quality of repeats`. "
             "Integration means the model loaded and followed bstack's routing, workflows, and hooks. Quality "
             "means it then did the work well: hidden tests, avoiding rejected alternatives, verifier coverage, "
             "and correct answers. Errors are ungraded attempts and appear separately from completed repeats. "
             "The compatibility matrix uses the most recent integration result per host.", "", f"Last recorded: {data['updated'] or 'never'}.", "",
             header, "|" + " --- |" * (len(QUALITY_SCENARIOS) + 2)]
    rows = sorted(data.get("models", {}).values(), key=lambda row: (ORDER.index(row["host"]), row["model"] or ""))
    for row in rows:
        cells = []
        for name in QUALITY_SCENARIOS:
            cell = row["scenarios"].get(name)
            if cell is None:
                cells.append("-")
                continue
            text = f"{cell['passes']} · {cell['quality_passes']} of {cell['repeats']}" if cell["repeats"] else "ungraded"
            errors = cell.get("errors", [])
            if errors:
                limits = sum(error["kind"] == "provider_limit" for error in errors)
                counts = [(limits, "provider limit"), (len(errors) - limits, "execution error")]
                labels = [f"{count} {label}{'s' if count != 1 else ''}" for count, label in counts if count]
                attempts = cell.get("attempts", cell["repeats"] + len(errors))
                text += f"; {', '.join(labels)} of {attempts} attempt{'s' if attempts != 1 else ''}"
            cells.append(text)
        lines.append(f"| {data['hosts'][row['host']]['label']} | `{row['model'] or 'default'}` | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the committed asset is stale")
    args = parser.parse_args()
    data = json.loads(RESULTS.read_text())
    svg, models, tools = render(data), render_models(data), render_tools(data)
    if args.check:
        stale = (ASSET.read_text() != svg or not MODELS.exists() or MODELS.read_text() != models
                 or not TOOLS_ASSET.exists() or TOOLS_ASSET.read_text() != tools)
        print("stale" if stale else "current")
        return int(stale)
    ASSET.write_text(svg)
    MODELS.write_text(models)
    TOOLS_ASSET.write_text(tools)
    for host in data["hosts"].values():
        print(f'{host["label"]:22} ' + "  ".join(f"{key}={status(host, key)}" for key, _ in COLUMNS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
