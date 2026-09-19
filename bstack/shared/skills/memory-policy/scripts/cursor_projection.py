from dataclasses import dataclass
import json
from pathlib import Path

from memory_files import SyncError, block, file_hash, read_file, sections, text_file


@dataclass(frozen=True)
class ProjectionState:
    path: Path
    source: Path
    before: bytes | None
    expected: bytes | None
    error: str | None
    exists: bool | None

    @property
    def current(self):
        return self.error is None and self.before == self.expected

    def report(self):
        reason = self.error
        if reason is None and not self.current:
            reason = 'Generated Cursor rule differs from its approved bridge source.'
        return {
            'path': str(self.path), 'source': str(self.source),
            'exists': self.exists, 'current': self.current,
            'expected_sha256': file_hash(self.expected), 'actual_sha256': file_hash(self.before),
            'reason': reason,
        }


def managed_records(content, source):
    return {note_id: match['body'] for note_id, match in sections(text_file(content, source)).items()}


def render_records(records, source):
    header = (
        '---\ndescription: Approved personal memories\nalwaysApply: true\n'
        'memorySyncGenerated: cursor-personal-memories\nmemorySyncVersion: 1\n'
        f'memorySyncSource: {json.dumps(str(source), ensure_ascii=False)}\n---\n\n'
        '# Personal memories\n\n'
    )
    return (header + ''.join(block(note_id, records[note_id]) for note_id in sorted(records))).encode('utf-8')


def render_projection(content, source):
    return render_records(managed_records(content, source), source)


def projection_records(content, source, path):
    if content is None:
        raise SyncError(f'Missing Cursor personal-memory rule at {path}; run install.py --activate-sync to materialize approved bridge notes')
    records = managed_records(content, path)
    if render_records(records, source) != content:
        raise SyncError(f'Unowned or malformed Cursor personal-memory rule at {path}; review the collision before replacing it')
    return records


def inspect_projection(source, path):
    before, expected, exists = None, None, None
    try:
        before = read_file(path)
        exists = before is not None
        content = read_file(source)
        expected = render_projection(content, source)
        projection_records(before, source, path)
        return ProjectionState(path, source, before, expected, None, exists)
    except SyncError as error:
        return ProjectionState(path, source, before, expected, str(error), exists)


def plan_projection(source_before, source_after, previous, source, path, note_id=None):
    source_records = managed_records(source_before, source)
    if previous is not None or note_id is not None:
        existing = projection_records(previous, source, path)
        unrelated = {
            key for key in source_records.keys() | existing.keys()
            if key != note_id and source_records.get(key) != existing.get(key)
        }
        if unrelated:
            names = ', '.join(sorted(unrelated))
            raise SyncError(f'Cursor projection drift outside the approved note: {names}; inspect and review those exact changes before synchronizing')
    return render_projection(source_after, source)
