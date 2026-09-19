#!/usr/bin/env python3
"""Assemble and check the reviewed, self-contained bstack consumer release."""
import argparse
from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import stat
import sys
import tempfile

import layers


ROOT = Path(__file__).resolve().parents[1]
CAPSULE = "skills/poteto-mode"
ROUTER = "content/shared/skills/bstack-router/WORKFLOW.md"
UNSLOP = "content/shared/skills/unslop/WORKFLOW.md"
LINK = re.compile(r"(\[[^\]\n]*\]\()([^\s)]+)(\))")
CODE = re.compile(r"`([^`\n]+)`")
PSTACK_PATH = re.compile(r"(?<![\w/])pstack/(?:skills|agents)/[A-Za-z0-9_./-]+")
SUPPORT_PATH = re.compile(r"(?<![\w/.])(?:scripts|references|playbooks)/[A-Za-z0-9_./-]+")
ENTRYPOINTS = {
    "mode": "SKILL.md",
    "router": ROUTER,
    "unslop": UNSLOP,
    "setup": "content/setup/WORKFLOW.md",
    "index": "content/index.json",
    "controller": "scripts/bstack.py",
    "reminder": "runtime/reminder.py",
    "verification": "content/shared/skills/verify-bstack/WORKFLOW.md",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


@dataclass(frozen=True)
class Asset:
    data: bytes
    mode: int
    source: str
    source_sha256: str
    transforms: tuple = ()

    def record(self, path):
        return {"path": path, "sha256": sha(self.data), "mode": self.mode,
                "source": self.source, "source_sha256": self.source_sha256,
                "transforms": list(self.transforms)}


def source_asset(relative, root=ROOT):
    if PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts:
        raise ValueError(f"Unsafe source path: {relative}")
    path = root.parent / relative
    for ancestor in (path, *path.parents):
        if ancestor == root.parent:
            break
        if ancestor.is_symlink():
            raise ValueError(f"Symlink source is not a release input: {relative}")
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected regular source file: {relative}")
    data = path.read_bytes()
    return Asset(data, stat.S_IMODE(path.stat().st_mode), relative, sha(data))


def generated_asset(data, source="bstack/scripts/package.py", root=ROOT, transforms=()):
    origin = source_asset(source, root)
    return Asset(data if isinstance(data, bytes) else data.encode(), 0o644,
                 origin.source, origin.source_sha256, tuple(transforms))


def private_path(source, upstream):
    if source.startswith(upstream + "/"):
        source = "engineering/" + source[len(upstream) + 1:]
    path = PurePosixPath("content") / source
    return str(path.with_name("WORKFLOW.md") if path.name == "SKILL.md" else path)


def local_target(source, target, mapping):
    base, separator, anchor = target.partition("#")
    if not base or ":" in base or base.startswith(("/", "~")):
        return None
    if base.startswith("bstack/"):
        canonical = base[len("bstack/"):]
    elif base.startswith("pstack/"):
        canonical = base
    else:
        canonical = posixpath.normpath(posixpath.join(posixpath.dirname(source), base))
    result = mapping.get(canonical)
    if result is None and base.startswith(("scripts/", "references/", "playbooks/")) and "/skills/" in source:
        prefix, skill = source.split("/skills/", 1)
        skill_root = prefix + "/skills/" + skill.split("/", 1)[0]
        result = mapping.get(skill_root + "/" + base)
    if result is None:
        prefix = canonical.rstrip("/") + "/"
        children = [path for path in mapping if path.startswith(prefix)]
        if children:
            destinations = {str(PurePosixPath(mapping[path]).parents[len(PurePosixPath(path[len(prefix):]).parts) - 1])
                            for path in children}
            if len(destinations) == 1:
                result = destinations.pop() + "/"
    return result + (separator + anchor if separator else "") if result else None


def relative_target(destination, target):
    path, separator, anchor = target.partition("#")
    result = posixpath.relpath(path, posixpath.dirname(destination))
    return result + ("/" if path.endswith("/") and not result.endswith("/") else "") + (separator + anchor if separator else "")


def transform_markdown(asset, source, destination, mapping, policy=False):
    text = asset.data.decode()
    changed = []

    if destination == "content/engineering/skills/poteto-mode/playbooks/multi-phase-plan.md":
        replacements = {
            "`git show origin/main:pstack/skills/poteto-mode/playbooks/<execution playbook>.md`": '`cat "<absolute installed execution-playbook path>"`',
            "`git show origin/main:<control skill path>`": '`cat "<absolute installed control-workflow path>"`',
            "`git show origin/main:pstack/skills/<each other leaf skill the program uses>`": '`cat "<absolute installed leaf-workflow path>"` for each selected leaf',
            "`pstack/skills/poteto-mode/playbooks/<execution playbook>.md`": "`<absolute installed execution-playbook path>`",
            "Read these from trunk at program start.": "Read these installed workflow files at program start.",
            "Re-read the execution playbook from trunk and the armed /goal.": "Re-read the installed execution playbook at its resolved package path and the armed /goal.",
        }
        for before, after in replacements.items():
            if before not in text:
                raise ValueError("Review changed multi-phase packaging template: " + before)
            text = text.replace(before, after)
        instruction = (
            "When writing the plan, resolve its execution playbook, control workflow, and every selected leaf through the "
            "[packaged index](" + relative_target(destination, "content/index.json") + "). Replace each installed-path "
            "placeholder with the resolved absolute filename in this installed capsule. Repeat the leaf-read item for every "
            "selected leaf. These workflow files come from the reviewed package, not the consumer repository's trunk.\n\n"
        )
        text = text.replace("````markdown\n", instruction + "````markdown\n", 1)
        changed.append("bind-program-template-to-installed-workflow-paths")
    if destination in ("content/engineering/skills/poteto-mode/playbooks/autopilot-full.md",
                       "content/engineering/skills/poteto-mode/playbooks/autopilot-stack.md"):
        text = text.replace("re-read this playbook from trunk with", "re-read this bundled playbook with")
        changed.append("reread-installed-playbook")

    def link(match):
        target = local_target(source, match[2], mapping)
        if target is None:
            return match[0]
        value = relative_target(destination, target)
        return match[1] + value + match[3]

    rewritten = LINK.sub(link, text)
    if rewritten != text:
        changed.append("rewrite-local-markdown-links")
    text = rewritten

    def code(match):
        value = match[1]
        if "/" in value and " " not in value:
            target = local_target(source, value, mapping)
            if target:
                return "`" + relative_target(destination, target) + "`"
        return match[0]

    rewritten = CODE.sub(code, text)
    if rewritten != text:
        changed.append("rewrite-concrete-code-paths")
    text = rewritten

    def upstream_path(match):
        target = local_target(source, match[0], mapping)
        return relative_target(destination, target) if target else match[0]

    # Installed dependencies may be outside the consumer's Git history.
    def git_read(match):
        target = local_target(source, match[1], mapping)
        return "cat " + relative_target(destination, target) if target else match[0]

    rewritten = re.sub(r"git show origin/main:(pstack/(?:skills|agents)/[A-Za-z0-9_./-]+)", git_read, text)
    if rewritten != text:
        changed.append("replace-upstream-git-read-with-installed-file-read")
    text = rewritten
    rewritten = PSTACK_PATH.sub(upstream_path, text)
    if rewritten != text:
        changed.append("rewrite-concrete-upstream-paths")
    text = rewritten
    rewritten = SUPPORT_PATH.sub(upstream_path, text)
    if rewritten != text:
        changed.append("rewrite-skill-root-support-paths")
    text = rewritten
    if destination == "content/engineering/skills/typescript-best-practices/references/patterns.md":
        text = text.replace("in `SKILL.md`", "in `../WORKFLOW.md`")
        changed.append("rewrite-known-parent-workflow-reference")
    if source.startswith("shared/skills/"):
        rewritten = re.sub(r"(?m)^(  attribution:) .+$", r"\1 " + relative_target(destination, "ATTRIBUTION.md"), text)
        if rewritten != text:
            changed.append("rewrite-attribution-metadata")
        text = rewritten
    if policy:
        banner = (
            "> This packaged dependency follows [bstack's policy](" + relative_target(destination, ROUTER) + "). "
            "Read or reuse that policy before following these instructions. Resolve skill names through the "
            "[workflow index](" + relative_target(destination, "content/index.json") + "). "
            "Use bundled workflows and replacements; do not fetch upstream latest. "
            "Resolve packaged paths relative to this document; use resolved helper paths from the consumer project.\n\n"
        )
        if text.startswith("---\n"):
            boundary = text.find("\n---\n", 4)
            if boundary == -1:
                raise ValueError(f"Unclosed frontmatter: {source}")
            boundary += len("\n---\n")
            text = text[:boundary] + "\n" + banner + text[boundary:].lstrip("\n")
        else:
            text = banner + text
        changed.append("bind-bstack-policy")
    if source.endswith("/SKILL.md"):
        changed.append("private-workflow-filename")
    return replace(asset, data=text.encode(), transforms=asset.transforms + tuple(changed))


def attribution_asset(root, mapping, sources):
    asset = source_asset("ATTRIBUTION.md", root)
    text = asset.data.decode()
    origins = {}
    for manifest in sources.values():
        for entry in manifest["files"]:
            source = "bstack/" + manifest["destination"] + "/" + entry["path"]
            origins[source] = (manifest["repository"] + "/blob/" + manifest["commit"] + "/"
                               + layers.candidate_path(manifest, entry))
            if PurePosixPath(entry["path"]).name == "LICENSE" or entry["path"].startswith("licenses/"):
                notice = source_asset(source, root).data.decode().strip()
                if notice not in text:
                    raise ValueError("Canonical attribution is missing the complete notice: " + source)

    def link(match):
        target = local_target("../ATTRIBUTION.md", match[2], mapping)
        if target is not None:
            return match[1] + target + match[3]
        path, separator, anchor = match[2].partition("#")
        if not path or ":" in path:
            return match[0]
        if path in origins:
            return match[1] + origins[path] + (separator + anchor if separator else "") + match[3]
        label = match[1][1:-2]
        return label + " (`" + path + "`, source repository only)"

    return replace(asset, data=LINK.sub(link, text).encode(), transforms=("render-canonical-attribution-links",))


def assemble(root=ROOT):
    checked = layers.check(root)
    if checked["errors"]:
        raise ValueError("Source layers are invalid: " + "; ".join(checked["errors"]))
    selection = json.loads((root / "package/selection.json").read_text())
    if selection.get("schema_version") != 1 or selection.get("name") != "bstack":
        raise ValueError("Unsupported release selection")
    if len(selection["skills"]) != len(set(selection["skills"])):
        raise ValueError("Duplicate skill selection")
    _, sources = layers.load(root)
    pinned = sources["pstack"]
    upstream = pinned["destination"]
    selected = []
    for skill in selection["skills"]:
        directory = layers.safe_path(root, upstream + "/skills/" + skill)
        if not (directory / "SKILL.md").is_file():
            raise ValueError(f"Selected workflow missing: {skill}")
        selected.extend(upstream + "/skills/" + skill + "/" + path for path in sorted(layers.tree_files(directory)))
    selected.extend(upstream + "/agents/" + agent for agent in selection["agents"])
    for skill in ("bstack-router", "unslop"):
        directory = root / "shared/skills" / skill
        selected.extend("shared/skills/" + skill + "/" + path for path in sorted(layers.tree_files(directory))
                        if not path.startswith("agents/"))
    verify_scripts = root / "shared/skills/verify-bstack/scripts"
    selected.extend("shared/skills/verify-bstack/scripts/" + path for path in sorted(layers.tree_files(verify_scripts))
                    if "__pycache__" not in PurePosixPath(path).parts and path.endswith(".py"))
    mapping = {source: private_path(source, upstream) for source in selected}
    mapping.update({
        upstream + "/skills/unslop/SKILL.md": UNSLOP,
        upstream + "/skills/setup-pstack/SKILL.md": ENTRYPOINTS["setup"],
        "../ATTRIBUTION.md": "ATTRIBUTION.md",
        "../LICENSE": "LICENSE",
        "layers.json": "content/layers.json",
    })
    mapping.update({"pstack/" + source[len(upstream) + 1:]: target for source, target in list(mapping.items())
                    if source.startswith(upstream + "/")})
    assets = {}
    for source in selected:
        destination = mapping[source]
        asset = source_asset("bstack/" + source, root)
        if source.endswith(".md"):
            asset = transform_markdown(asset, source, destination, mapping, policy=source.startswith(upstream + "/"))
        assets[destination] = asset

    for template, target in (("SKILL.md", "SKILL.md"), ("README.md", "README.md"),
                             ("setup.md", ENTRYPOINTS["setup"]),
                             ("verify.md", ENTRYPOINTS["verification"])):
        asset = source_asset("bstack/package/templates/" + template, root)
        data = asset.data.decode().replace("@VERSION@", selection["version"]).replace("@PSTACK_COMMIT@", pinned["commit"])
        assets[target] = replace(asset, data=data.encode(), transforms=("render-release-template",))
    assets["ATTRIBUTION.md"] = attribution_asset(root, mapping, sources)
    for source, target in (("LICENSE", "LICENSE"),
                           ("bstack/package/runtime.py", ENTRYPOINTS["controller"]),
                           ("bstack/shared/router/hook.py", ENTRYPOINTS["reminder"]),
                           ("bstack/shared/router/reminder.txt", "runtime/reminder.txt")):
        assets[target] = source_asset(source, root)
    assets["agents/openai.yaml"] = generated_asset(
        'interface:\n  display_name: "Poteto Mode in bstack"\n'
        '  short_description: "Explicit engineering workflows through bstack"\n'
        '  default_prompt: "Use $poteto-mode for this engineering task."\n'
        'policy:\n  allow_implicit_invocation: false\n', root=root, transforms=("manual-entry-metadata",))
    skills = {skill: mapping[upstream + "/skills/" + skill + "/SKILL.md"] for skill in selection["skills"]}
    skills.update({"poteto-mode": ROUTER, "bstack-router": ROUTER, "unslop": UNSLOP,
                   "setup-pstack": ENTRYPOINTS["setup"], "setup-bstack": ENTRYPOINTS["setup"],
                   "verify-bstack": ENTRYPOINTS["verification"]})
    agents = {Path(agent).stem: mapping[upstream + "/agents/" + agent] for agent in selection["agents"]}
    playbooks = {PurePosixPath(source).stem: target for source, target in mapping.items()
                 if source.startswith(upstream + "/skills/poteto-mode/playbooks/") and source.endswith(".md")}
    index = {"schema_version": 1, "paths_relative_to": "capsule", "policy": ROUTER,
             "skills": skills, "agents": agents, "playbooks": playbooks,
             "upstream_router": mapping[upstream + "/skills/poteto-mode/SKILL.md"]}
    assets["content/index.json"] = generated_asset(json_bytes(index), "bstack/package/selection.json", root,
                                                   ("resolve-selected-workflows-and-overrides",))
    layer_summary = {"schema_version": 1, "package": "bstack", "policy": ROUTER,
                     "source_revision": pinned["commit"],
                     "replacements": {"unslop": UNSLOP, "setup-pstack": ENTRYPOINTS["setup"]},
                     "note": "Review source history and original hashes in manifest.json. This is the runtime layer summary."}
    assets["content/layers.json"] = generated_asset(json_bytes(layer_summary), "bstack/layers.json", root,
                                                    ("emit-portable-runtime-layer-summary",))
    manifest = {"schema_version": 1, "name": selection["name"], "version": selection["version"],
                "entrypoints": ENTRYPOINTS, "source_revision": pinned["commit"],
                "source_repository": pinned["repository"], "upstream_updates": "reviewed-build-only",
                "installation_source": "bundled-files-only",
                "native_plugin_manifests": ["claude", "cursor"],
                "native_plugin_deferred": {"codex": "The native validator rejects the shared manual-entry flag. CLI installation is separate."},
                "files": [assets[path].record(path) for path in sorted(assets)]}
    assets["manifest.json"] = generated_asset(json_bytes(manifest), root=root, transforms=("manifest-excludes-own-hash",))
    release = {CAPSULE + "/" + path: asset for path, asset in assets.items()}
    common = {"name": "bstack", "version": selection["version"],
              "description": "Portable engineering workflows with bstack policies and optional local routing.",
              "author": {"name": "Brenden Bishop"}, "license": "MIT", "skills": "./skills/"}
    for host in ("claude", "cursor"):
        native = dict(common)
        release[f".{host}-plugin/plugin.json"] = generated_asset(json_bytes(native), root=root,
                                                                 transforms=("bstack-native-plugin-metadata",))
    release["README.md"] = generated_asset(
        "# bstack\n\nVersion " + selection["version"] + ". Install the `poteto-mode` skill from this directory through skills.sh. "
        "The [complete capsule](skills/poteto-mode/README.md) contains bstack's policies, customizations, dependencies, setup controller, and notices. "
        "Installation uses only these bundled, reviewed files and never fetches upstream latest. "
        "For an offline install from a clone or transferred directory, run `python3 skills/poteto-mode/scripts/bstack.py install --project <project-root> --hosts codex claude cursor grok` from this release directory. "
        "The offline path requires Python only; skills.sh is an optional distribution route. Run the explicit setup command after skills.sh installation for project bindings and optional auto mode. Native manifests identify the same bstack package; "
        "they do not enable hooks or establish native installation support.\n", root=root,
        transforms=("release-entry-guide",))
    errors = closure_errors(release)
    if errors:
        raise ValueError("Release dependency validation failed: " + "; ".join(errors))
    for path, asset in release.items():
        if str(root).encode() in asset.data:
            raise ValueError(f"Absolute source checkout leaked into release: {path}")
    return release


def closure_errors(release):
    errors = []
    paths = set(release)
    directories = {str(parent) for path in paths for parent in PurePosixPath(path).parents}
    exposed = sorted(path for path in paths if PurePosixPath(path).name == "SKILL.md")
    if exposed != [CAPSULE + "/SKILL.md"]:
        errors.append("Expected exactly one public SKILL.md: " + repr(exposed))
    for path, asset in release.items():
        if not path.endswith(".md"):
            continue
        for match in LINK.finditer(asset.data.decode()):
            target = match[2].split("#", 1)[0]
            if not target or ":" in target or target == "url":
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(path), target))
            if target.startswith("/") or resolved.startswith("../") or resolved not in paths | directories:
                errors.append(f"Unresolved packaged link: {path}: {target}")
    index = json.loads(release[CAPSULE + "/content/index.json"].data)
    for target in [index["policy"], index["upstream_router"], *index["skills"].values(), *index["agents"].values(), *index["playbooks"].values()]:
        if CAPSULE + "/" + target not in paths:
            errors.append("Unresolved workflow index target: " + target)
    for name, target in ENTRYPOINTS.items():
        if CAPSULE + "/" + target not in paths:
            errors.append("Missing entrypoint: " + name)
    return errors


def file_set(directory):
    return layers.tree_files(directory)


def check(package, root=ROOT):
    expected = assemble(root)
    errors = []
    actual = file_set(package)
    for path in sorted(actual - expected.keys()):
        errors.append("Unexpected release file: " + path)
    for path in sorted(expected):
        file = package / path
        asset = expected[path]
        if path not in actual:
            errors.append("Missing release file: " + path)
        elif file.read_bytes() != asset.data:
            errors.append("Stale or altered release file: " + path)
        elif stat.S_IMODE(file.stat().st_mode) != asset.mode:
            errors.append("Release mode differs: " + path)
    return {"status": "invalid" if errors else "clean", "errors": errors,
            "files": len(expected), "public_skills": ["poteto-mode"], "name": "bstack"}


def build(output, root=ROOT):
    expected = assemble(root)
    output = output.absolute()
    if output.is_symlink():
        raise ValueError("Release output cannot be a symlink")
    output = output.resolve()
    if output == root or root.is_relative_to(output) or (output.is_relative_to(root) and output != root / "release"):
        raise ValueError("Build output must be bstack/release or outside the source tree")
    if output.exists() and any(output.iterdir()) and not (output / CAPSULE / "manifest.json").is_file():
        raise ValueError("Refusing to replace a non-release directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".bstack-release-", dir=output.parent))
    try:
        for relative, asset in expected.items():
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(asset.data)
            path.chmod(asset.mode)
        if output.exists():
            previous = staging.with_name(staging.name + "-previous")
            output.rename(previous)
            try:
                staging.rename(output)
            except BaseException:
                previous.rename(output)
                raise
            shutil.rmtree(previous)
        else:
            staging.rename(output)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"status": "built", "files": len(expected), "public_skills": ["poteto-mode"], "name": "bstack"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--output", type=Path, default=ROOT / "release")
    check_parser = sub.add_parser("check")
    check_parser.add_argument("--package", type=Path, default=ROOT / "release")
    args = parser.parse_args()
    try:
        result = build(args.output) if args.command == "build" else check(args.package)
    except (ValueError, KeyError, OSError) as error:
        result = {"status": "invalid", "errors": [str(error)]}
    print(json.dumps(result, indent=2))
    return 1 if result["status"] == "invalid" else 0


if __name__ == "__main__":
    sys.exit(main())
