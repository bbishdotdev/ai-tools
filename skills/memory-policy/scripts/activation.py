import copy
import json
import re
import tomllib

from cursor_projection import plan_projection

from memory_files import SyncError, atomic_change, file_hash, read_file, sync_lock, text_file
from native_backends import (
    CLAUDE_INDEX, CODEX_MEMORY, CODEX_SUMMARY, CURSOR_END, CURSOR_INDEX,
    CURSOR_RULE_HEADER, CURSOR_START, FileChange, absolute_path, read_config,
)


LEGACY_POLICY = """# Native memory policy

Before creating, changing, deleting, extracting, or synchronizing durable memories, read and follow `~/.agents/skills/memory-policy/SKILL.md`.

Require the user's explicit approval of the exact memory change. Keep memories limited to personal facts, agent behavior, and general operating preferences. Approved memories must persist through the native memory systems of Codex, Claude Code, and Cursor; disclose an unavailable destination before saving a partial copy. Project or app knowledge belongs in project instructions, documentation, or skills.

Keep native memory enabled. This routing instruction is not a memory store and does not claim control over background writers that do not load it.
"""
POLICY_START = '<!-- memory-sync-policy:begin -->'
POLICY_END = '<!-- memory-sync-policy:end -->'


def replace_router_block(text, replacement, start, end):
    pattern = re.compile(re.escape(start) + r'\n.*?' + re.escape(end) + r'\n', re.DOTALL)
    if text.count(start) != 1 or text.count(end) != 1:
        raise SyncError('Malformed managed Cursor router markers; preserve and review the rule before updating')
    block = pattern.search(replacement)
    if block is None or pattern.search(text) is None:
        raise SyncError('Unrecognized managed Cursor router layout')
    return pattern.sub(lambda _: block[0], text, count=1)


def update_cursor_router(before, desired):
    if before is None:
        return desired.encode('utf-8')
    text = before.decode('utf-8')
    legacy = CURSOR_RULE_HEADER + LEGACY_POLICY
    if text.startswith(legacy):
        return (desired + text[len(legacy):]).encode('utf-8')
    if not text.startswith(CURSOR_RULE_HEADER):
        raise SyncError('Existing Cursor rule is not the known generated router; nothing will overwrite arbitrary user rules')
    updated = replace_router_block(text, desired, POLICY_START, POLICY_END)
    updated = replace_router_block(updated, desired, CURSOR_START, CURSOR_END)
    return updated.encode('utf-8')


def set_toml_boolean(text, table, key):
    parsed = tomllib.loads(text)
    current = parsed.get(table, {})
    if not isinstance(current, dict):
        raise SyncError(f'Expected a TOML table for {table}')
    if key in current and not isinstance(current[key], bool):
        raise SyncError(f'Expected boolean {table}.{key} before activation')
    if current.get(key) is True:
        return text
    headers = list(re.finditer(r'(?m)^[ \t]*\[([^\r\n]+)\][ \t]*(?:#[^\r\n]*)?(?:\r?\n|$)', text))
    matching = [(position, match) for position, match in enumerate(headers) if match[1].strip() == table]
    newline = '\r\n' if '\r\n' in text else '\n'
    if table not in parsed:
        separator = '' if not text or text.endswith('\n') else newline
        return text + separator + newline + f'[{table}]' + newline + f'{key} = true' + newline
    if len(matching) != 1:
        raise SyncError(f'Unsupported TOML formatting for {table}; activation requires an ordinary [{table}] table')
    position, header = matching[0]
    end = headers[position + 1].start() if position + 1 < len(headers) else len(text)
    body = text[header.end():end]
    pattern = re.compile(r'(?m)^([ \t]*' + re.escape(key) + r'[ \t]*=[ \t]*)(true|false)([ \t]*(?:#[^\r\n]*)?)(\r?\n|$)')
    if key in current:
        if len(pattern.findall(body)) != 1:
            raise SyncError(f'Unsupported TOML formatting for {table}.{key}; review this field manually')
        body = pattern.sub(lambda match: match[1] + 'true' + match[3] + match[4], body, count=1)
    else:
        separator = '' if text[:header.end()].endswith('\n') else newline
        body = separator + f'{key} = true' + newline + body
    return text[:header.end()] + body + text[end:]


def codex_configuration(path):
    before, config = read_config(path)
    expected = copy.deepcopy(config)
    for table, key in [('features', 'memories'), ('memories', 'use_memories')]:
        if not isinstance(expected.setdefault(table, {}), dict):
            raise SyncError(f'Expected a TOML table for {table}')
        expected[table][key] = True
    text = text_file(before, path)
    for table, key in [('features', 'memories'), ('memories', 'use_memories')]:
        text = set_toml_boolean(text, table, key)
    if tomllib.loads(text) != expected:
        raise SyncError('Codex TOML roundtrip changed unrelated settings; activation stopped')
    return FileChange('codex', path, before, text.encode('utf-8'), 'configuration')


def claude_configuration(profile):
    path = profile.claude_home / 'settings.json'
    before, config = read_config(path)
    configured = config.get('autoMemoryDirectory')
    directory = profile.home / 'Work/.agents/memory-sync/claude'
    if configured is not None:
        if not isinstance(configured, str) or '\x00' in configured or not configured.startswith('/'):
            raise SyncError('Existing Claude autoMemoryDirectory must be absolute; review it before activation')
        directory = absolute_path(configured)
    if profile.isolated and not directory.is_relative_to(profile.home):
        raise SyncError('--home requires Claude memory inside the disposable home')
    updated = {**config, 'autoMemoryEnabled': True, 'autoMemoryDirectory': str(directory)}
    after = before if updated == config else (json.dumps(updated, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    return FileChange('claude', path, before, after, 'configuration'), directory


def cursor_configuration(profile):
    path = profile.home / 'Work/.agents/memory-sync/config.json'
    before, config = read_config(path)
    base = profile.home / 'Work/.agents/memory-sync/cursor'
    directory = base
    if before is None:
        config = {'version': 1, 'cursor': {'mode': 'file-bridge', 'directory': str(directory)}}
        after = (json.dumps(config, indent=2) + '\n').encode('utf-8')
    else:
        cursor = config.get('cursor')
        if type(config.get('version')) is not int or config['version'] != 1 or not isinstance(cursor, dict) or cursor.get('mode') != 'file-bridge':
            raise SyncError('Existing synchronization configuration is not a version-1 Cursor file bridge; review it before activation')
        value = cursor.get('directory')
        if not isinstance(value, str) or '\x00' in value or not value.startswith('/'):
            raise SyncError('Existing Cursor bridge directory must be absolute')
        directory = absolute_path(value)
        if not directory.is_relative_to(base):
            raise SyncError('Cursor bridge directory must stay under Work/.agents/memory-sync/cursor')
        after = before
    return FileChange('cursor', path, before, after, 'configuration'), directory


def activation_changes(profile, router_change, cursor_config, claude_config, claude_directory, cursor_directory):
    codex_config = codex_configuration(profile.codex_home / 'config.toml')
    scaffolds = [
        ('codex', profile.codex_home / 'memories/MEMORY.md', CODEX_MEMORY),
        ('codex', profile.codex_home / 'memories/memory_summary.md', CODEX_SUMMARY),
        ('claude', claude_directory / 'MEMORY.md', CLAUDE_INDEX),
        ('cursor', cursor_directory / 'MEMORY.md', CURSOR_INDEX),
    ]
    changes = []
    for name, path, content in scaffolds:
        before = read_file(path)
        text_file(before, path)
        changes.append(FileChange(name, path, before, before if before is not None else content.encode('utf-8'), 'empty scaffold'))
    bridge = next(change for change in changes if change.destination == 'cursor')
    projection_path = profile.home / '.cursor/rules/personal-memories.mdc'
    previous_projection = read_file(projection_path)
    next_projection = plan_projection(bridge.before, bridge.after, previous_projection, bridge.path, projection_path)
    changes.append(FileChange('cursor', projection_path, previous_projection, next_projection, 'generated projection', ((bridge.path, bridge.after),)))
    changes.extend([codex_config, claude_config, cursor_config, router_change])
    paths = [change.path for change in changes]
    if len(paths) != len(set(paths)):
        raise SyncError('Activation destinations overlap; use separate native memory directories')
    return changes


def backup_path(home, change):
    label = change.destination + '-' + change.path.name.replace('.', '-')
    return home / 'Work/.agents/memory-sync/backups' / f'{label}-{file_hash(change.before)}.bak'


def apply_changes(profile, changes):
    completed = []
    try:
        with sync_lock(profile.home):
            for change in changes:
                if read_file(change.path) != change.before:
                    raise SyncError(f'Activation plan changed at {change.path}; run a new preview')
                if change.kind == 'configuration' and change.before is not None and change.before != change.after:
                    backup = backup_path(profile.home, change)
                    existing = read_file(backup)
                    if existing is not None and existing != change.before:
                        raise SyncError(f'Configuration backup collision at {backup}')
            for change in changes:
                for path, expected in change.dependencies:
                    if read_file(path) != expected:
                        raise SyncError(f'Projection source changed at {path}; review a new activation plan')
                if change.before == change.after:
                    continue
                if change.kind == 'configuration' and change.before is not None:
                    backup = backup_path(profile.home, change)
                    if read_file(backup) is None:
                        atomic_change(backup, None, change.before)
                atomic_change(change.path, change.before, change.after)
                completed.append(str(change.path))
            if any(read_file(change.path) != change.after for change in changes):
                raise SyncError('Activation readback changed; inspect files before retrying')
    except (OSError, SyncError, KeyboardInterrupt) as error:
        raise SyncError(f'Activation incomplete. Completed files: {completed}. {error}. No rollback was attempted; inspect current files before retrying.') from error
    return completed
