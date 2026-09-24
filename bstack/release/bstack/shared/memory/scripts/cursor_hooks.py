from dataclasses import dataclass
import json
from pathlib import Path
import shlex

from memory_files import SyncError, read_file
from layout import Layout


@dataclass(frozen=True)
class HookState:
    path: Path
    raw: bytes | None
    ready: bool
    error: str | None

    def report(self):
        return {
            'path': str(self.path), 'event': 'beforeSubmitPrompt',
            'configured': self.ready, 'reason': self.error,
            'scope': 'Local hook registration only; model-visible context delivery requires a live Cursor check.',
        }


def context_hook(home, layout=None):
    layout = layout or Layout.load(home)
    script = layout.runtime / 'scripts/cursor_context.py'
    return {
        'command': shlex.join(['python3', '-B', str(script), '--profile-home' if layout.portable else '--home', str(home)]),
        'type': 'command', 'async': False, 'timeout': 2, 'failClosed': False,
        'matcher': 'UserPromptSubmit', 'loop_limit': None,
    }


def parse_hooks(raw, path):
    try:
        config = {} if raw is None else json.loads(raw)
    except (ValueError, UnicodeDecodeError) as error:
        raise SyncError(f'Malformed Cursor hooks configuration at {path}') from error
    if not isinstance(config, dict):
        raise SyncError(f'Expected a Cursor hooks object at {path}')
    if 'version' in config and (type(config['version']) is not int or config['version'] != 1):
        raise SyncError(f'Unsupported Cursor hooks version at {path}; expected version 1')
    hooks = config.get('hooks', {})
    if not isinstance(hooks, dict) or not isinstance(hooks.get('beforeSubmitPrompt', []), list):
        raise SyncError(f'Expected hooks.beforeSubmitPrompt to be an array at {path}')
    return config


def hooks_configuration(home, layout=None):
    path = home / '.cursor/hooks.json'
    before = read_file(path)
    config = parse_hooks(before, path)
    expected = context_hook(home, layout)
    hooks = dict(config.get('hooks', {}))
    entries = []
    found = False
    for entry in hooks.get('beforeSubmitPrompt', []):
        if isinstance(entry, dict) and entry.get('command') == expected['command']:
            if not found:
                entries.append({**entry, **expected})
                found = True
        else:
            entries.append(entry)
    if not found:
        entries.append(expected)
    hooks['beforeSubmitPrompt'] = entries
    updated = {**config, 'version': 1, 'hooks': hooks}
    after = before if config == updated else (json.dumps(updated, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    return path, before, after


def inspect_hooks(home, layout=None):
    layout = layout or Layout.load(home)
    path = home / '.cursor/hooks.json'
    raw = None
    try:
        raw = read_file(path)
        config = parse_hooks(raw, path)
        expected = context_hook(home, layout)
        matches = [entry for entry in config.get('hooks', {}).get('beforeSubmitPrompt', [])
                   if isinstance(entry, dict) and entry.get('command') == expected['command']]
        ready = config.get('version') == 1 and len(matches) == 1 and all(type(matches[0].get(key)) is type(value) and matches[0].get(key) == value for key, value in expected.items())
        if not ready:
            raise SyncError('Cursor requires its current-snapshot beforeSubmitPrompt hook; ' + layout.setup_hint)
        return HookState(path, raw, True, None)
    except SyncError as error:
        return HookState(path, raw, False, str(error))
