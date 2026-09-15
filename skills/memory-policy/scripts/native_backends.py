from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import tomllib

from memory_files import (
    NOTE_ID, SyncError, absolute_path, block, change_section, file_hash,
    read_file, section_body, sections, text_file,
)


DESTINATIONS = ('codex', 'claude', 'cursor')
MAX_NOTE_BYTES = 4096
CLAUDE_INDEX_LINES = 200
CODEX_SUMMARY = "v1\n\n## User Profile\n\n## User preferences\n\n## General Tips\n\n## What's in Memory\n"
CODEX_MEMORY = '# Personal memories\n'
CLAUDE_INDEX = '# User memories\n'
CURSOR_UNAVAILABLE = (
    'No verified ordinary-desktop native memory adapter for Cursor. The inspected cached '
    'rollout disables its native user-store harness; this is not a live gate check. '
    'No shared-file bridge or private API is used.'
)


@dataclass(frozen=True)
class Profile:
    home: Path
    codex_home: Path
    claude_home: Path
    isolated: bool

    @classmethod
    def load(cls, home=None):
        root = absolute_path(home or Path.home())
        codex = root / '.codex' if home is not None else absolute_path(os.environ.get('CODEX_HOME', root / '.codex'))
        claude = root / '.claude' if home is not None else absolute_path(os.environ.get('CLAUDE_CONFIG_DIR', root / '.claude'))
        return cls(root, codex, claude, home is not None)


@dataclass(frozen=True)
class Backend:
    name: str
    root: Path | None
    config_path: Path | None
    config_bytes: bytes | None
    error: str | None

    def report(self):
        return {
            'ready': self.error is None,
            'native_directory': str(self.root) if self.root else None,
            'reason': self.error,
            'scope': 'User-level configuration only. Set/delete also preflight target files. Fresh-session recall is a separate check.',
        }


@dataclass(frozen=True)
class FileChange:
    destination: str
    path: Path
    before: bytes | None
    after: bytes | None

    @property
    def action(self):
        if self.before == self.after:
            return 'unchanged'
        if self.after is None:
            return 'delete'
        return 'create' if self.before is None else 'update'


def validate_note(note_id, text=None):
    if not re.fullmatch(NOTE_ID, note_id):
        raise SyncError('Note id must start with a lower-case letter and contain only lower-case letters, digits, or hyphens (maximum 64 characters)')
    if text is None:
        return
    if not text.strip():
        raise SyncError('Memory text must not be empty')
    if '<!-- memory-sync:' in text:
        raise SyncError('Memory text cannot contain reserved memory-sync ownership markers')
    if any(ord(character) < 32 and character not in '\n\t' for character in text):
        raise SyncError('Memory text contains an unsupported control character; use UTF-8 text with LF line endings')
    if len(text.encode('utf-8')) > MAX_NOTE_BYTES:
        raise SyncError(f'Memory text exceeds the helper limit of {MAX_NOTE_BYTES} UTF-8 bytes; split it into concise, separately approved notes')


def read_config(path):
    raw = read_file(path)
    if raw is None:
        return raw, {}
    try:
        if path.suffix == '.toml':
            config = tomllib.loads(raw.decode('utf-8'))
        else:
            config = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as error:
        raise SyncError(f'Malformed configuration at {path}: {type(error).__name__}') from error
    if not isinstance(config, dict):
        raise SyncError(f'Expected a configuration object at {path}')
    return raw, config


def boolean_setting(settings, key, default, path):
    value = settings.get(key, default)
    if not isinstance(value, bool):
        raise SyncError(f'Expected boolean {key} in {path}')
    return value


def codex_backend(profile):
    path = profile.codex_home / 'config.toml'
    raw = None
    try:
        raw, config = read_config(path)
        features, memories = config.get('features', {}), config.get('memories', {})
        if not isinstance(features, dict) or not isinstance(memories, dict):
            raise SyncError(f'Expected features and memories tables in {path}')
        enabled = boolean_setting(features, 'memories', False, path)
        usable = boolean_setting(memories, 'use_memories', True, path)
        boolean_setting(memories, 'generate_memories', True, path)
        if not enabled or not usable:
            raise SyncError('Codex requires [features].memories = true and [memories].use_memories not false; review native settings separately')
        return Backend('codex', profile.codex_home / 'memories', path, raw, None)
    except SyncError as error:
        return Backend('codex', profile.codex_home / 'memories', path, raw, str(error))


def claude_backend(profile):
    path = profile.claude_home / 'settings.json'
    raw, root = None, None
    try:
        raw, config = read_config(path)
        enabled = boolean_setting(config, 'autoMemoryEnabled', True, path)
        configured = config.get('autoMemoryDirectory')
        if not isinstance(configured, str) or not configured or '\x00' in configured or not Path(configured).is_absolute():
            raise SyncError('Claude requires an absolute, fixed user-level autoMemoryDirectory; review native settings separately')
        configured_root = absolute_path(configured)
        if profile.isolated and not configured_root.is_relative_to(profile.home):
            raise SyncError('--home requires autoMemoryDirectory inside that disposable home')
        root = configured_root
        if not enabled:
            raise SyncError('Claude autoMemoryEnabled is false; review native settings separately')
        return Backend('claude', root, path, raw, None)
    except SyncError as error:
        return Backend('claude', root, path, raw, str(error))


def backends(profile):
    return {
        'codex': codex_backend(profile),
        'claude': claude_backend(profile),
        'cursor': Backend('cursor', None, None, None, CURSOR_UNAVAILABLE),
    }


def codex_payload(note_id, text, summary):
    if summary:
        return f'### Personal memory: {note_id}\n\n{text}'
    return (
        f'# Task Group: Personal memory {note_id}\n'
        'scope: User preferences and behavior across projects\n'
        'applies_to: cwd=all; reuse_rule=Personal memory applies across projects\n\n'
        + text
    )


def codex_note(content, note_id, path, summary):
    body = section_body(content, note_id, path)
    if body is None:
        return None
    prefix = codex_payload(note_id, '', summary)
    if not body.startswith(prefix):
        raise SyncError(f'Unrecognized managed entry in {path}; inspect before repairing')
    return body[len(prefix):]


def description(text):
    return ' '.join(text.split())


def topic_bytes(note_id, text):
    header = (
        '---\n'
        f'name: {json.dumps(note_id)}\n'
        f'description: {json.dumps(description(text), ensure_ascii=False)}\n'
        'type: user\n---\n\n'
    )
    return (header + block(note_id, text)).encode('utf-8')


def topic_note(content, note_id, path):
    if content is None:
        return None
    body = section_body(content, note_id, path)
    if body is None or topic_bytes(note_id, body) != content:
        raise SyncError(f'Unmanaged or modified topic-file collision at {path}; review the whole file before replacing it')
    return body


def index_payload(note_id, text):
    readable = description(text).replace('\\', '\\\\').replace('[', '\\[').replace(']', '\\]').replace('<', '&lt;').replace('>', '&gt;')
    return f'- [{note_id}](memory-sync-{note_id}.md): {readable}'


def check_index(content, path):
    text = text_file(content, path)
    for note_id, match in sections(text).items():
        line = text[:match.end()].count('\n')
        if line > CLAUDE_INDEX_LINES:
            raise SyncError(f'Managed Claude index entry {note_id} exceeds the native first-{CLAUDE_INDEX_LINES}-line startup window at {path}; shorten or reorganize the index before syncing')


def changes_for(backend, note_id, text):
    if backend.name == 'codex':
        changes = []
        for name, initial, summary in [('MEMORY.md', CODEX_MEMORY, False), ('memory_summary.md', CODEX_SUMMARY, True)]:
            path = backend.root / name
            before = read_file(path)
            codex_note(before, note_id, path, summary)
            payload = codex_payload(note_id, text, summary) if text is not None else None
            after = change_section(before, note_id, payload, initial, path, after_version=summary)
            changes.append(FileChange(backend.name, path, before, after))
    else:
        topic, index = backend.root / f'memory-sync-{note_id}.md', backend.root / 'MEMORY.md'
        previous_topic, previous_index = read_file(topic), read_file(index)
        topic_note(previous_topic, note_id, topic)
        payload = index_payload(note_id, text) if text is not None else None
        next_index = change_section(previous_index, note_id, payload, CLAUDE_INDEX, index)
        check_index(next_index, index)
        changes = [
            FileChange(backend.name, topic, previous_topic, topic_bytes(note_id, text) if text is not None else None),
            FileChange(backend.name, index, previous_index, next_index),
        ]
    return changes if text is not None else list(reversed(changes))


def inspect_backend(backend, note_id):
    if backend.root is None:
        return {'copies': [], 'error': backend.error}
    copies = []
    if backend.name == 'codex':
        for name, summary in [('MEMORY.md', False), ('memory_summary.md', True)]:
            path = backend.root / name
            raw = read_file(path)
            content = codex_note(raw, note_id, path, summary)
            copies.append({'path': str(path), 'content': content, 'content_sha256': file_hash(content.encode('utf-8')) if content is not None else None})
    else:
        topic, index = backend.root / f'memory-sync-{note_id}.md', backend.root / 'MEMORY.md'
        content = topic_note(read_file(topic), note_id, topic)
        raw_index = read_file(index)
        entry = section_body(raw_index, note_id, index)
        expected = index_payload(note_id, content) if content is not None else None
        check_index(raw_index, index)
        copies.append({
            'path': str(topic), 'content': content,
            'content_sha256': file_hash(content.encode('utf-8')) if content is not None else None,
            'index_path': str(index), 'index_matches': entry == expected,
        })
    return {'copies': copies, 'error': None}
