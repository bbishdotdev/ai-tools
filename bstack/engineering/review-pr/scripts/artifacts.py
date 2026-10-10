import hashlib
import io
import zipfile

from contracts import ReviewError

MAX_ZIP_BYTES = 250 * 1024 * 1024


def checked_path(value):
    if (not isinstance(value, str) or not value or any(char in value for char in ("\\", ":", "\x00"))
            or any(part in ("", ".", "..", ".git") for part in value.split("/"))):
        raise ReviewError("ZIP mappings and members require normalized relative paths")
    return value


def validate_zip_trees(value):
    if not isinstance(value, dict):
        raise ReviewError("zip_trees must map ZIP paths to source-tree paths")
    for archive, source in value.items():
        if not checked_path(archive).lower().endswith(".zip"):
            raise ReviewError("zip_trees archive paths must end in .zip")
        checked_path(source)
    return dict(value)


class ZipBuffer(io.BytesIO):
    def write(self, data):
        if self.tell() + len(data) > MAX_ZIP_BYTES:
            raise ReviewError("Reconstructed ZIP exceeds the 250 MiB snapshot limit")
        return super().write(data)


def verify_zip(name, source, index, snapshot, side, commit):
    if index[name]["mode"] not in {"100644", "100755"}:
        raise ReviewError("Mapped archive is not a regular file")
    prefix = source + "/"
    members = sorted(path for path in index if path.startswith(prefix))
    if not members:
        raise ReviewError("Mapped source tree is missing or empty")
    with ZipBuffer() as output:
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in members:
                record = index[path]
                if record["mode"] not in {"100644", "100755"} or record["lines"] is None:
                    raise ReviewError(f"Mapped source must contain only regular text files: {path}")
                member = zipfile.ZipInfo(checked_path(path[len(prefix):]), date_time=(1980, 1, 1, 0, 0, 0))
                member.create_system = 3
                member.external_attr = int(record["mode"], 8) << 16
                member.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(member, (snapshot / path).read_bytes())
        actual = (snapshot / name).read_bytes()
        if output.getvalue() != actual:
            raise ReviewError("Archive bytes differ from the canonical ZIP of the pinned source tree")
    return {"path": name, "source_tree": source, "side": side, "commit": commit,
            "blob": index[name]["sha"], "sha256": hashlib.sha256(actual).hexdigest(), "files": len(members),
            "verification": "Exact physical content match with the canonical ZIP of pinned text files; semantic correctness still requires review."}


def coverage(changes, trees, snapshots, commits, zip_trees):
    limits, verified = [], []
    for name in changes:
        if not any(name in tree and tree[name]["lines"] is None for tree in trees.values()):
            continue
        if name not in zip_trees:
            limits.append(f"Changed content cannot be inspected as text: {name}")
            continue
        try:
            evidence = [verify_zip(name, zip_trees[name], tree, snapshots[side], side, commits[side])
                        for side, tree in trees.items() if name in tree]
            verified.extend(evidence)
        except (ReviewError, OSError, ValueError, zipfile.LargeZipFile) as exc:
            limits.append(f"Changed ZIP could not be verified: {name}: {exc}")
    return limits, verified
