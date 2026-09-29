"""A bounded, read-only catalog of the selected repository Markdown decisions."""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
from urllib.parse import unquote, urlsplit

from wayfinder.core import DomainError, _git_location


MAX_FILES = 256
MAX_FILE_BYTES = 262144
MAX_TOTAL_BYTES = 8388608
MAX_SCAN_ITEMS = 4096
MAX_HEADER_LINES = 128
STATUSES = {"accepted", "proposed", "rejected", "superseded", "retired"}
PRIVATE_PARTS = {".bstack", ".git"}
LINK = re.compile(r"\[([^\]\n]*)\]\((<[^>\n]+>|[^\s()]+)\)")
FIELD = re.compile(r"^(Status|Supersedes|Superseded by):\s*(.*)$", re.IGNORECASE)


@dataclass(frozen=True)
class AdrEntry:
    path: str
    title: str
    identifier: str | None
    declared_status: str | None
    supersedes: tuple[str, ...]
    superseded_by: tuple[str, ...]

    def value(self):
        return {"path": self.path, "title": self.title, "id": self.identifier,
                "declaredStatus": self.declared_status, "supersedes": list(self.supersedes),
                "supersededBy": list(self.superseded_by)}


@dataclass(frozen=True)
class AdrFinding:
    code: str
    paths: tuple[str, ...]
    message: str

    def value(self):
        return {"code": self.code, "paths": list(self.paths), "message": self.message}


@dataclass(frozen=True)
class AdrCatalog:
    root: Path
    path: str
    exists: bool
    entries: tuple[AdrEntry, ...]
    findings: tuple[AdrFinding, ...]

    def value(self):
        return {"root": str(self.root), "path": self.path, "exists": self.exists,
                "scope": "selected-path-only", "entries": [entry.value() for entry in self.entries],
                "findings": [finding.value() for finding in self.findings]}


def _fail(code, message, **details):
    raise DomainError(code, message, **details)


def _confined(path, root):
    try:
        resolved = path.resolve()
        resolved.relative_to(root)
        return resolved
    except (ValueError, RuntimeError):
        _fail("adr_path", "ADR paths must resolve inside the active checkout")


def _files(selected, root, findings):
    pending, files, seen = [selected], [], 0
    while pending:
        path = pending.pop()
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            findings.append(AdrFinding("skipped_symlink", (relative,), "Symlink was not followed."))
            continue
        if any(part in PRIVATE_PARTS for part in path.relative_to(root).parts):
            findings.append(AdrFinding("skipped_private", (relative,), "Private workspace or Git content was not scanned."))
            continue
        _confined(path, root)
        if path.is_dir():
            with os.scandir(path) as children:
                for child in children:
                    seen += 1
                    if seen > MAX_SCAN_ITEMS:
                        _fail("adr_limit", f"Selected tree exceeds {MAX_SCAN_ITEMS} filesystem entries")
                    pending.append(Path(child.path))
        elif path.suffix.lower() == ".md":
            if not path.is_file():
                findings.append(AdrFinding("skipped_file", (relative,), "Not a regular Markdown file."))
                continue
            files.append(path)
            if len(files) > MAX_FILES:
                _fail("adr_limit", f"Selected path exceeds {MAX_FILES} Markdown files")
    return sorted(files)


def _metadata(content, path, findings):
    title, fields, status_section = None, {}, False
    lines = content.splitlines()
    fence, titles = None, 0
    for line in lines:
        stripped = line.strip()
        marker = re.match(r"(`{3,}|~{3,})", stripped)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None and re.match(r"^#\s+", line) and line[2:].strip().casefold() != "status":
            titles += 1
    for line in lines[:MAX_HEADER_LINES]:
        line = line.strip()
        if not line:
            continue
        if line.startswith(("```", "~~~", ">", "<!--", "---")):
            break
        heading = re.fullmatch(r"(#{1,6})\s+(.+?)(?:\s+#+)?", line)
        if heading:
            level, label = heading.groups()
            if title is None and level == "#" and label.casefold() != "status":
                title = label
                continue
            if label.casefold() == "status":
                status_section = True
                continue
            break
        field = FIELD.fullmatch(line)
        if field:
            key, value = field.groups()
            fields.setdefault(key.casefold(), []).append(value.strip())
            status_section = False
            continue
        if status_section:
            fields.setdefault("status", []).append(line)
            status_section = False
            continue
        if re.fullmatch(r"[A-Za-z][A-Za-z -]{0,40}:\s*.*", line):
            continue
        break
    else:
        if len(lines) > MAX_HEADER_LINES:
            findings.append(AdrFinding("metadata_unchecked", (path,), "Opening metadata exceeds 128 lines; later lines were not parsed."))
    if titles > 1:
        fields = {}
        findings.append(AdrFinding("metadata_unchecked", (path,), "Multiple top-level headings may contain separate decisions; metadata was not interpreted."))
    for key, values in list(fields.items()):
        if len(values) != 1 or len(values[0]) > 2048:
            findings.append(AdrFinding("metadata_unchecked", (path,), f"Repeated or oversized {key} metadata was not interpreted."))
            del fields[key]
    status = fields.get("status", [None])[0]
    if status is None or status.casefold() not in STATUSES:
        findings.append(AdrFinding("status_unknown", (path,), "Declared status is missing or unfamiliar; read the record before relying on it."))
    if title and len(title) > 256:
        findings.append(AdrFinding("metadata_unchecked", (path,), "Title was shortened to 256 characters in the catalog."))
    return (title or Path(path).stem)[:256], status, fields


def _links(value, source, root, findings):
    relative = source.relative_to(root).as_posix()
    targets = set()
    if LINK.sub("", value).strip(" ,;"):
        findings.append(AdrFinding("link_unchecked", (relative,), "Supersession metadata contains unsupported text or reference syntax."))
    for match in LINK.finditer(value):
        target = match.group(2).strip("<>")
        try:
            url = urlsplit(target)
        except ValueError:
            findings.append(AdrFinding("link_unchecked", (relative,), "Malformed supersession URL was not checked."))
            continue
        if url.scheme or url.netloc or not url.path or url.query:
            findings.append(AdrFinding("link_unchecked", (relative,), "External, anchor-only, or query-bearing supersession link was not checked."))
            continue
        name = unquote(url.path)
        if "\x00" in name or "\\" in name or Path(name).is_absolute() or Path(name).suffix.lower() != ".md":
            findings.append(AdrFinding("link_unchecked", (relative,), "Supersession link must be a relative Markdown path."))
            continue
        try:
            destination = _confined(source.parent / name, root)
        except DomainError:
            findings.append(AdrFinding("link_escape", (relative,), "Supersession link resolves outside the active checkout or through a symlink loop."))
            continue
        target_path = destination.relative_to(root).as_posix()
        if any(part in PRIVATE_PARTS for part in destination.relative_to(root).parts):
            findings.append(AdrFinding("link_unchecked", (relative,), "Supersession link into private workspace or Git content was not checked."))
            continue
        targets.add(target_path)
        if not destination.is_file():
            findings.append(AdrFinding("link_missing", (relative, target_path), "Recognized supersession target is missing or is not a file."))
        if url.fragment:
            findings.append(AdrFinding("link_unchecked", (relative, target_path), "Target file was checked; its fragment was not."))
    return tuple(sorted(targets))


def _check(entries, root, findings):
    by_path = {entry.path: entry for entry in entries}
    identifiers, graph = {}, {entry.path: set() for entry in entries}
    for entry in entries:
        status = (entry.declared_status or "").casefold()
        if entry.identifier is not None:
            identifiers.setdefault(str(int(entry.identifier)), []).append(entry.path)
        for target in (*entry.supersedes, *entry.superseded_by):
            if target not in by_path and (root / target).is_file():
                findings.append(AdrFinding("link_unchecked", (entry.path, target), "Target exists outside the catalog; its metadata was not checked."))
        for older in entry.supersedes:
            if older in by_path and status in {"accepted", "superseded"}:
                graph[entry.path].add(older)
                if entry.path not in by_path[older].superseded_by:
                    findings.append(AdrFinding("supersession_not_reciprocal", (older, entry.path), "Supersedes has no matching Superseded by declaration."))
        for newer in entry.superseded_by:
            if newer in by_path:
                replacement_status = (by_path[newer].declared_status or "").casefold()
                if status == "superseded" and replacement_status in {"proposed", "rejected"}:
                    findings.append(AdrFinding("replacement_not_effective", (entry.path, newer), "Superseded record points to a proposed or rejected replacement."))
                if replacement_status in {"accepted", "superseded"}:
                    graph[newer].add(entry.path)
                if replacement_status in {"accepted", "superseded"} and entry.path not in by_path[newer].supersedes:
                    findings.append(AdrFinding("supersession_not_reciprocal", (entry.path, newer), "Superseded by has no matching Supersedes declaration."))
        if entry.superseded_by and status in STATUSES - {"superseded"}:
            findings.append(AdrFinding("status_link_conflict", (entry.path,), "Recognized status is not superseded but Superseded by is declared."))
        if status == "superseded" and not entry.superseded_by:
            findings.append(AdrFinding("replacement_missing", (entry.path,), "Superseded status has no recognized replacement link."))
    for paths in identifiers.values():
        if len(paths) > 1:
            findings.append(AdrFinding("duplicate_id", tuple(paths), "Numeric ADR ID is used by more than one catalog entry."))

    visited, active = set(), []

    def visit(path):
        if path in active:
            cycle = tuple(sorted(active[active.index(path):]))
            findings.append(AdrFinding("supersession_cycle", cycle, "Recognized supersession links contain a cycle."))
        elif path not in visited:
            active.append(path)
            for target in sorted(graph[path]):
                visit(target)
            active.pop()
            visited.add(path)

    for path in sorted(graph):
        visit(path)


def inspect_adrs(project: Path, path: str = "docs/adr") -> AdrCatalog:
    """Inspect a selected file/tree in the active checkout without any writes."""
    project = Path(project).resolve()
    if not project.is_dir():
        _fail("adr_path", "Project directory does not exist")
    git = _git_location(project)
    root = git[0] if git else project
    if not path or "\x00" in path:
        _fail("adr_path", "Select a Markdown file or directory inside the active checkout")
    selected = _confined(root / path, root)
    relative = selected.relative_to(root).as_posix()
    if any(part in PRIVATE_PARTS for part in selected.relative_to(root).parts):
        _fail("adr_path", "Private workspace and Git content are not an ADR catalog")
    findings = []
    if not selected.exists():
        findings.append(AdrFinding("path_missing", (relative,), "Selected path does not exist; no other ADR locations were searched."))
        return AdrCatalog(root, relative, False, (), tuple(findings))
    if not selected.is_dir() and (not selected.is_file() or selected.suffix.lower() != ".md"):
        _fail("adr_path", "Select a Markdown file or directory")
    entries, total = [], 0
    for source in _files(selected, root, findings):
        file_path = source.relative_to(root).as_posix()
        descriptor = os.open(source, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                _fail("adr_io", "ADR is not a regular file", path=file_path)
            content = stream.read(MAX_FILE_BYTES + 1)
        total += len(content)
        if len(content) > MAX_FILE_BYTES or total > MAX_TOTAL_BYTES:
            _fail("adr_limit", "ADR input exceeds 256 KiB per file or 8 MiB total", path=file_path)
        try:
            text = content.decode("utf-8-sig")
        except UnicodeError:
            _fail("adr_encoding", "ADR file must contain UTF-8 text", path=file_path)
        title, status, fields = _metadata(text, file_path, findings)
        identifier = re.match(r"(?:adr[-_])?(\d+)(?:[-_. ]|$)", source.stem, re.IGNORECASE)
        entries.append(AdrEntry(file_path, title, identifier.group(1) if identifier else None, status,
                                _links(fields.get("supersedes", [""])[0], source, root, findings),
                                _links(fields.get("superseded by", [""])[0], source, root, findings)))
    _check(entries, root, findings)
    ordered = tuple(sorted(set(findings), key=lambda item: (item.paths, item.code, item.message)))
    return AdrCatalog(root, relative, True, tuple(entries), ordered)
