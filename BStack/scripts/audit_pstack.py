#!/usr/bin/env python3
"""Inventory the vendored PStack files without executing their workflows."""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENGINEERING = ROOT / "engineering"
MANIFEST = ROOT / "pstack-provenance.json"
OUTPUT = ROOT / "audit" / "pstack-inventory.json"
CATALOG = ROOT / "audit" / "catalog.md"
PLAYBOOK_PURPOSES = {
    "authoring-a-skill": "Author through Cursor create-skill, validate, and prepare a PR.",
    "autonomous-run": "Drive one task until an explicit completion condition is met.",
    "autopilot-full": "Run independent PR owners through verification and authorized merging.",
    "autopilot-stack": "Build one verified PR chain for the operator to land.",
    "babysit": "Check or drive PR conflicts, review comments, and CI toward merge readiness.",
    "bug-fix": "Reproduce, find the mechanism, fix, and prove the original symptom is gone.",
    "eval": "Compare skill or prompt variants with blinded candidates and a judge.",
    "feature": "Understand, design, delegate implementation, verify, and prepare delivery.",
    "hillclimb": "Improve one measured target through controlled, recorded experiments.",
    "investigation": "Return a cited explanation or recommendation without changing code.",
    "multi-phase-plan": "Create a detailed PR program with explicit dependencies and verification lanes.",
    "opening-a-pr": "Prepare the worktree, commits, cleanup, writing, and forge submission.",
    "orchestrate": "Coordinate a multi-day program with owners, briefs, state records, and verifiers.",
    "pause-safely": "Stop work at a recoverable boundary and leave a resume note.",
    "perf-issue": "Measure a baseline, fix a demonstrated bottleneck, and compare traces.",
    "prototype": "Build a disposable experiment to settle a design or behavior question.",
    "refactoring": "Change structure in small steps while preserving observed behavior.",
    "runtime-forensics": "Capture and diagnose a live runtime symptom without automatically fixing it.",
    "session-pickup": "Reconstruct a prior session and route the remaining work.",
    "shipping": "Independently verify and land only the contiguous safe part of a PR stack.",
    "trace-forensics": "Query a captured profile or trace and attribute its strongest finding to source.",
    "visual-parity": "Compare against a fixed visual baseline while migrating one component at a time.",
    "worktree-cleanup": "Audit worktrees and simulator state before reclaiming confirmed-unused storage.",
}
EXTERNAL = {
    "create-skill": "external-skill:create-skill",
    "verify-this": "external-skill:verify-this",
    "loop": "host-command:loop",
    "goal": "host-command:goal",
}


def frontmatter(text):
    parts = text.split("---", 2)
    if not text.startswith("---\n") or len(parts) != 3:
        raise ValueError("Missing frontmatter")
    fields = {}
    current = None
    for line in parts[1].splitlines():
        match = re.match(r"^([\w-]+):\s*(.*)$", line)
        if match:
            current, value = match.groups()
            if value in (">", ">-", "|", "|-"):
                fields[current] = ""
            elif value.startswith('"'):
                fields[current] = json.loads(value)
            elif value.startswith("'"):
                fields[current] = value[1:-1].replace("''", "'")
            else:
                fields[current] = value
        elif line.startswith("  ") and current:
            fields[current] += " " + line.strip()
    return fields, parts[2], text[: len(text) - len(parts[2])].count("\n")


def owner(relative):
    parts = relative.parts
    if parts[:3] == ("skills", "poteto-mode", "playbooks"):
        return "playbook:" + relative.stem
    if parts[0] == "skills" and len(parts) > 1:
        return "skill:" + parts[1]
    if parts[0] == "agents":
        return "agent:" + relative.stem
    if parts[:3] == ("automations", "benny", "skills"):
        return "automation-skill:" + parts[3]
    return "document:" + relative.as_posix()


def inspect_files(manifest):
    expected = {item["path"]: item for item in manifest["files"]}
    errors, files = [], []
    for path in sorted(ENGINEERING.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(ENGINEERING).as_posix()
        if "node_modules" in path.parts or "__pycache__" in path.parts:
            continue
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        entry = expected.get(relative)
        if entry is None:
            errors.append("Unrecorded file: " + relative)
        elif digest != entry["installed_sha256"]:
            errors.append("Content differs from import: " + relative)
        if entry and oct(path.stat().st_mode & 0o777) != entry["mode"]:
            errors.append("Permissions differ from import: " + relative)
        files.append({"path": relative, "bytes": len(content), "sha256": digest})
    actual = {item["path"] for item in files}
    errors.extend("Missing file: " + path for path in sorted(expected.keys() - actual))
    return files, errors


def collect_skills(manifest):
    records, aliases = [], dict(EXTERNAL)
    companions = set(manifest["companions"]["skills"])
    paths = list(ENGINEERING.glob("skills/*/SKILL.md"))
    paths += list(ENGINEERING.glob("automations/benny/skills/*/SKILL.md"))
    for path in sorted(paths):
        relative = path.relative_to(ENGINEERING)
        text = path.read_text()
        meta, body, _ = frontmatter(text)
        name = path.parent.name
        dormant = relative.parts[0] == "automations"
        node = owner(relative)
        aliases[name] = node
        if name.startswith("principle-"):
            aliases[name.removeprefix("principle-")] = node
        records.append({
            "id": node, "name": name, "declared_name": meta.get("name"),
            "path": relative.as_posix(), "description": meta.get("description", "").strip(),
            "manual_only": meta.get("disable-model-invocation", "false") == "true",
            "group": "dormant-automation" if dormant else "companion" if name in companions else "principle" if name.startswith("principle-") else "workflow",
            "characters": len(text), "body_words": len(body.split()),
            "name_matches_directory": meta.get("name") == name,
        })
    for path in sorted(ENGINEERING.glob("agents/*.md")):
        meta, _, _ = frontmatter(path.read_text())
        aliases[path.stem] = "agent:" + path.stem
        aliases[meta["name"]] = "agent:" + path.stem
    for path in sorted(ENGINEERING.glob("skills/poteto-mode/playbooks/*.md")):
        aliases[path.stem] = "playbook:" + path.stem
        title = path.read_text().splitlines()[0].lstrip("# ")
        aliases[title] = "playbook:" + path.stem
    return records, aliases


def scan_references(aliases):
    edges = defaultdict(list)
    links, unresolved = [], []
    for path in sorted(ENGINEERING.rglob("*.md")):
        relative = path.relative_to(ENGINEERING)
        source = owner(relative)
        text = path.read_text()
        if text.startswith("---\n"):
            _, body, offset = frontmatter(text)
        else:
            body, offset = text, 0
        for number, line in enumerate(body.splitlines(), offset + 1):
            targets = set()
            for match in re.finditer(r"`([^`\n]+)`|\*\*([^*\n]+)\*\*", line):
                value = (match.group(1) or match.group(2)).strip().removeprefix("/")
                if value in aliases:
                    targets.add(aliases[value])
            for match in re.finditer(r"(?<![\w-])(principle-[a-z0-9-]+)(?![\w-])", line):
                if match.group(1) in aliases:
                    targets.add(aliases[match.group(1)])
            for match in re.finditer(r"playbooks/([a-z0-9-]+)\.md", line):
                name = match.group(1)
                if name in aliases:
                    targets.add(aliases[name])
            for match in re.finditer(r"\[[^\]]*\]\(([^\s)]+)\)", line):
                href = match.group(1).split("#", 1)[0]
                if not href or re.match(r"[a-z]+:", href) or href.startswith("/"):
                    continue
                resolved = (path.parent / href).resolve()
                item = {"file": relative.as_posix(), "line": number, "target": href}
                links.append(item)
                if not resolved.exists():
                    unresolved.append(item)
                elif resolved.is_relative_to(ENGINEERING):
                    targets.add(owner(resolved.relative_to(ENGINEERING)))
            for target in targets - {source}:
                edges[(source, target)].append({"file": relative.as_posix(), "line": number})
    return [
        {"source": source, "target": target, "kind": "textual-reference", "evidence": evidence}
        for (source, target), evidence in sorted(edges.items())
    ], links, unresolved


def build_inventory():
    manifest = json.loads(MANIFEST.read_text())
    files, errors = inspect_files(manifest)
    skills, aliases = collect_skills(manifest)
    edges, links, unresolved = scan_references(aliases)
    registered = [skill for skill in skills if skill["group"] != "dormant-automation"]
    pstack = [skill for skill in registered if skill["group"] != "companion"]
    top_sources = Counter(edge["target"] for edge in edges if not edge["source"].startswith("document:"))
    routes = {}
    examples = {
        "entry": ["poteto-mode"],
        "principles_all": [skill["name"] for skill in skills if skill["group"] == "principle"],
        "feature_design_example": ["poteto-mode", "how", "architect", "arena", "unslop"],
        "writing_example": ["technical-writing", "unslop"],
    }
    for name, members in examples.items():
        paths = [ENGINEERING / "skills" / member / "SKILL.md" for member in members]
        if name == "feature_design_example":
            paths.append(ENGINEERING / "skills/poteto-mode/playbooks/feature.md")
        routes[name] = {"files": [p.relative_to(ENGINEERING).as_posix() for p in paths], "characters": sum(len(p.read_text()) for p in paths)}
    playbooks = []
    for path in sorted(ENGINEERING.glob("skills/poteto-mode/playbooks/*.md")):
        text = path.read_text()
        playbooks.append({"name": path.stem, "path": path.relative_to(ENGINEERING).as_posix(), "characters": len(text)})
    return {
        "schema_version": 1, "upstream_commit": manifest["commit"],
        "method": "Static source inventory. Edges are explicit code-span, bold-name, principle-name, playbook-path, or relative-Markdown-link references. They include optional references and examples; they are not executed calls or proof of runtime reachability. Plain unmarked prose references may be absent. Built-ins and dynamically discovered tools need separate capability checks.",
        "summary": {
            "files": len(files), "bytes": sum(f["bytes"] for f in files),
            "pstack_skills": len(pstack), "principles": sum(s["group"] == "principle" for s in skills),
            "companion_skills": len(registered) - len(pstack), "dormant_automation_skills": len(skills) - len(registered),
            "manual_only_pstack_after_unslop_override": sum(s["manual_only"] for s in pstack),
            "manual_only_upstream": manifest["upstream_inventory"]["manual_only_skills"],
            "agents": len(list(ENGINEERING.glob("agents/*.md"))), "playbooks": len(playbooks),
            "manifest_skill_characters": sum(s["characters"] for s in registered),
            "manifest_metadata_characters": sum(len(s["declared_name"] or "") + len(s["description"]) for s in registered),
            "textual_reference_edges": len(edges), "relative_markdown_links": len(links),
        },
        "integrity_errors": errors, "unresolved_relative_markdown_links": unresolved,
        "name_mismatches_preserved_from_upstream": [s["path"] for s in skills if not s["name_matches_directory"]],
        "largest_reference_targets": [{"id": key, "distinct_source_nodes": count} for key, count in top_sources.most_common(12)],
        "illustrative_read_sets": routes, "skills": skills, "playbooks": playbooks,
        "references": edges, "files": files,
    }


def render_catalog(inventory):
    lines = [
        "# PStack catalog", "",
        "Generated from the pinned BStack import. Start with [the architectural audit](pstack.md).", "",
        "Purpose text comes from each skill's description. Manual means the file declares `disable-model-invocation: true`; normal means it does not. This records metadata, not proof that any host loaded the skill. Character counts cover the complete SKILL.md, not its supporting files. Dormant Benny skills are outside the plugin manifest's discovery directory.", "",
    ]
    groups = [("workflow", "Workflow and utility skills"), ("principle", "Engineering principles"),
              ("companion", "Required companion skills"), ("dormant-automation", "Dormant automation skills")]
    for key, title in groups:
        lines += ["## " + title, "", "| Skill | Purpose and trigger | Discovery | Characters |", "| --- | --- | --- | ---: |"]
        for skill in inventory["skills"]:
            if skill["group"] != key:
                continue
            description = skill["description"].replace("|", "\\|")
            mode = "Manual" if skill["manual_only"] else "Normal"
            if skill["name"] == "unslop":
                mode += "; code-maverick override"
            lines.append(f"| [{skill['name']}](../engineering/{skill['path']}) | {description} | {mode} | {skill['characters']:,} |")
        lines.append("")
    lines += ["## Playbooks", "", "These are selected files within poteto-mode, not separately registered skills.", "",
              "| Playbook | Purpose | Characters |", "| --- | --- | ---: |"]
    for item in inventory["playbooks"]:
        lines.append(f"| [{item['name']}](../engineering/{item['path']}) | {PLAYBOOK_PURPOSES[item['name']]} | {item['characters']:,} |")
    lines += ["", "## Agents", "",
              "| Agent | Purpose | Dependency |", "| --- | --- | --- |",
              "| [poteto-agent](../engineering/agents/poteto-agent.md) | Give delegates the same operating instructions as the parent | Reads the full poteto-mode wrapper and relevant principle leaves |",
              "| [Comment Sicko](../engineering/agents/comment-sicko.md) | Delete comments and flag code that needs a clearer structure | May investigate disputed claims through how and why; no application-code changes in this agent |", "",
              "## Mechanical support", "", "| Entry | Purpose |", "| --- | --- |",
              "| [check-plan.mjs](../engineering/skills/poteto-mode/scripts/check-plan.mjs) | Validate a specific multi-phase plan format, including fixed verification lane wording |",
              "| [orch.ts](../engineering/skills/poteto-mode/scripts/orch/orch.ts) and [store.ts](../engineering/skills/poteto-mode/scripts/orch/store.ts) | CLI and file storage for orchestration units, verification ledger, inbox, gates, and frontier; do not spawn agents |",
              "| [watch-pr](../engineering/skills/poteto-mode/scripts/watch-pr/watch-pr) | GitHub PR watcher with CLI, GitHub adapter, readiness policy, rendering, types, and bundled tests |",
              "| [bootstrap.ts](../engineering/skills/poteto-mode/scripts/bootstrap.ts) | Install locked Bun dependencies next to the script when needed |",
              "| [worktree-audit.sh](../engineering/skills/poteto-mode/scripts/worktree-audit.sh) | Inspect worktree size, age, Git/PR state, and Cursor transcripts for cleanup decisions |",
              "| [log.sh](../engineering/skills/show-me-your-work/scripts/log.sh) | Append sanitized rows to the decision TSV |", "",
              "The [guide](../engineering/docs/guide/README.md) explains upstream use. The [Benny pack](../engineering/automations/benny/README.md) includes configuration and automation templates. Images and license files are preserved. See [the inventory](pstack-inventory.json) for every file and explicit textual-reference edge with source locations.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate the inventory JSON")
    args = parser.parse_args()
    inventory = build_inventory()
    encoded = json.dumps(inventory, indent=2, ensure_ascii=False) + "\n"
    catalog = render_catalog(inventory)
    if inventory["integrity_errors"]:
        raise SystemExit("\n".join(inventory["integrity_errors"]))
    if args.write:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(encoded)
        CATALOG.write_text(catalog)
    elif not OUTPUT.exists() or OUTPUT.read_text() != encoded:
        raise SystemExit("Inventory is absent or stale. Review changes, then run with --write.")
    elif not CATALOG.exists() or CATALOG.read_text() != catalog:
        raise SystemExit("Catalog is absent or stale. Review changes, then run with --write.")
    print(json.dumps(inventory["summary"], indent=2))
    print("Import hashes and permissions match. Inventory is current.")
    print(f"Unresolved upstream relative Markdown links: {len(inventory['unresolved_relative_markdown_links'])}")


if __name__ == "__main__":
    main()
