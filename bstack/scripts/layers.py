#!/usr/bin/env python3
"""Check pinned imports and review an upstream candidate without changing files."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_parts(relative):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError(f"Unsafe relative path: {relative!r}")
    parts = relative.split("/")
    if PurePosixPath(relative).is_absolute() or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"Unsafe relative path: {relative!r}")
    return parts


def safe_path(root, relative):
    path = root
    for part in relative_parts(relative):
        path = path / part
        if path.is_symlink():
            raise ValueError(f"Symlink is not an imported file: {path}")
    return path


def tree_files(root):
    files = set()
    if not root.is_dir():
        raise ValueError(f"Directory missing: {root}")
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"Symlink is not an imported file: {path}")
        if path.is_file():
            files.add(path.relative_to(root).as_posix())
        elif not path.is_dir():
            raise ValueError(f"Unsupported file type: {path}")
    return files


def import_errors(root, manifest):
    errors = []
    destination = safe_path(root, manifest["destination"])
    scopes = review_scopes(manifest)
    expected = {}
    source_paths = set()
    for entry in manifest["files"]:
        relative = entry["path"]
        path = safe_path(destination, relative)
        source_path = candidate_path(manifest, entry)
        if source_path in source_paths:
            errors.append(f"Duplicate upstream path: {source_path}")
        source_paths.add(source_path)
        if "review_paths" in manifest and not any(source_path == scope or source_path.startswith(scope + "/") for scope in scopes):
            errors.append(f"Upstream file outside review paths: {source_path}")
        if relative in expected:
            errors.append(f"Duplicate import entry: {relative}")
        expected[relative] = entry
        locked = entry.get("upstream_sha256")
        if not isinstance(locked, str) or len(locked) != 64:
            errors.append(f"Missing upstream digest: {relative}")
        if entry.get("installed_sha256", locked) != locked:
            errors.append(f"Import lock contains an adaptation: {relative}")
        if not path.is_file():
            errors.append(f"Missing imported file: {relative}")
        elif digest(path) != locked:
            errors.append(f"Local vendor content differs: {relative}")
        elif oct(stat.S_IMODE(path.stat().st_mode)) != entry["mode"]:
            errors.append(f"Local vendor permissions differ: {relative}")
    for relative in sorted(tree_files(destination) - expected.keys()):
        errors.append(f"Unrecorded vendor file: {relative}")
    return errors


def load(root):
    config = json.loads(safe_path(root, "layers.json").read_text())
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported layers schema")
    sources = {}
    for source in config["sources"]:
        if source["id"] in sources:
            raise ValueError(f"Duplicate source: {source['id']}")
        sources[source["id"]] = json.loads(safe_path(root, source["manifest"]).read_text())
    return config, sources


def check(root=ROOT):
    config, sources = load(root)
    errors = []
    for source, manifest in sources.items():
        errors.extend(f"{source}: {error}" for error in import_errors(root, manifest))
    names = set()
    for layer in config["layers"]:
        name = layer["id"]
        if name in names:
            errors.append(f"Duplicate layer: {name}")
        names.add(name)
        if layer["kind"] not in ("policy-overlay", "whole-skill-override"):
            errors.append(f"Unknown layer kind: {name}")
        manifest = sources.get(layer["source"])
        if manifest is None:
            errors.append(f"Unknown layer source: {name}")
            continue
        directory = safe_path(root, layer["path"])
        if not safe_path(directory, layer["entrypoint"]).is_file():
            errors.append(f"Missing layer entrypoint: {name}")
        else:
            tree_files(directory)
        vendor = safe_path(root, manifest["destination"])
        if directory == vendor or directory.is_relative_to(vendor):
            errors.append(f"Layer overlaps immutable import: {name}")
        files = {entry["path"]: entry for entry in manifest["files"]}
        if not layer["upstream_files"]:
            errors.append(f"No upstream review bases: {name}")
        for base in layer["upstream_files"]:
            safe_path(vendor, base["path"])
            entry = files.get(base["path"])
            if entry is None or base["sha256"] != entry["upstream_sha256"]:
                errors.append(f"Layer base differs from upstream lock: {name}: {base['path']}")
        if layer["kind"] == "whole-skill-override":
            target = layer["replaces"]
            safe_path(vendor, target)
            if not any(path.startswith(target + "/") for path in files):
                errors.append(f"Override target missing from import: {name}")
            else:
                override_source_prefixes(manifest, target)
    return {"status": "invalid" if errors else "clean", "errors": errors,
            "sources": list(sources), "layers": sorted(names)}


def candidate_path(manifest, entry):
    companion = manifest.get("companions")
    prefix = companion["source_path"] if companion and entry.get("source") == companion["source_path"] else manifest["source_path"]
    if prefix != "":
        relative_parts(prefix)
    relative = entry.get("source_path", entry["path"])
    relative_parts(relative)
    return prefix + "/" + relative if prefix else relative


def review_scopes(manifest):
    prefix = manifest["source_path"]
    if prefix != "":
        relative_parts(prefix)
    scopes = manifest.get("review_paths")
    if scopes is None:
        if not prefix:
            raise ValueError("Repository-root imports require explicit review_paths")
        scopes = [prefix]
        companion = manifest.get("companions")
        if companion:
            scopes.extend(companion["source_path"] + "/skills/" + skill for skill in companion["skills"])
    if not isinstance(scopes, list) or not scopes:
        raise ValueError("review_paths must be a nonempty list of file or directory paths")
    for scope in scopes:
        relative_parts(scope)
    return scopes


def override_source_prefixes(manifest, target):
    prefixes = set()
    for entry in manifest["files"]:
        if not entry["path"].startswith(target + "/"):
            continue
        relative = entry["path"][len(target) + 1:]
        source = candidate_path(manifest, entry)
        if source != relative and not source.endswith("/" + relative):
            raise ValueError(f"Override mapping must preserve skill-relative paths: {entry['path']}")
        prefix = source[:-len(relative)]
        if not prefix:
            raise ValueError(f"Override mapping cannot cover the upstream repository root: {entry['path']}")
        prefixes.add(prefix)
    return prefixes


def review_update(source, candidate, root=ROOT):
    current = check(root)
    if current["errors"]:
        return {"status": "invalid", "errors": current["errors"]}
    config, sources = load(root)
    if source not in sources:
        raise ValueError(f"Unknown source: {source}")
    candidate = Path(candidate).absolute()
    if candidate.is_symlink() or not candidate.is_dir():
        raise ValueError(f"Candidate must be a real checkout directory: {candidate}")
    manifest = sources[source]
    expected, changes = {}, []
    for entry in manifest["files"]:
        relative = candidate_path(manifest, entry)
        path = safe_path(candidate, relative)
        expected[relative] = entry["path"]
        if not path.exists():
            changes.append({"path": entry["path"], "candidate_path": relative, "change": "removed"})
        elif not path.is_file():
            raise ValueError(f"Candidate file is not regular: {path}")
        elif digest(path) != entry["upstream_sha256"] or oct(stat.S_IMODE(path.stat().st_mode)) != entry["mode"]:
            changes.append({"path": entry["path"], "candidate_path": relative, "change": "changed",
                            "sha256": digest(path), "mode": oct(stat.S_IMODE(path.stat().st_mode))})
    additions = set()
    for scope in review_scopes(manifest):
        path = safe_path(candidate, scope)
        if not path.exists():
            continue
        paths = [scope] if path.is_file() else [scope + "/" + relative for relative in tree_files(path)]
        additions.update(relative for relative in paths if relative not in expected)
    additions = sorted(additions)
    reviews = []
    changed = {item["path"] for item in changes}
    for layer in config["layers"]:
        if layer["source"] != source:
            continue
        watched = {base["path"] for base in layer["upstream_files"]}
        affected = sorted(changed & watched)
        added = []
        if layer["kind"] == "whole-skill-override":
            affected = sorted(set(affected) | {p for p in changed if p.startswith(layer["replaces"] + "/")})
            prefixes = override_source_prefixes(manifest, layer["replaces"])
            added = [p for p in additions if any(p.startswith(prefix) for prefix in prefixes)]
        reviews.append({"layer": layer["id"], "review_required": bool(affected or added),
                        "affected_files": affected, "added_files": added})
    return {"status": "review_required" if changes or additions else "unchanged", "source": source,
            "pinned_commit": manifest["commit"], "candidate": str(candidate), "changes": changes,
            "added_files": additions, "layer_reviews": reviews,
            "note": "Read-only comparison. Review dependencies and behavior even when no layer base changed. Lock refresh and adoption are manual."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("check")
    review = sub.add_parser("review-update")
    review.add_argument("--source", required=True)
    review.add_argument("--candidate", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = check() if args.action == "check" else review_update(args.source, args.candidate)
    except (ValueError, KeyError, OSError) as error:
        report = {"status": "invalid", "errors": [str(error)]}
    print(json.dumps(report, indent=2))
    return 1 if report["status"] == "invalid" else 0


if __name__ == "__main__":
    raise SystemExit(main())
