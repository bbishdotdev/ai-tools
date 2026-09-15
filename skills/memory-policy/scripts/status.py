#!/usr/bin/env python3
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

sys.dont_write_bytecode = True
from install import cursor_local_rule, installation_links


def read_settings(path):
    try:
        with path.open('rb') as handle:
            if path.suffix == '.toml':
                settings = tomllib.load(handle)
            else:
                settings = json.load(handle)
        return settings if isinstance(settings, dict) else {'read_error': 'ExpectedObject'}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as error:
        return {'read_error': type(error).__name__}


def inspect_codex(binary):
    if not binary:
        return {'available': False}
    try:
        version = subprocess.run([binary, '--version'], text=True, capture_output=True, timeout=10, check=True)
        features = subprocess.run([binary, 'features', 'list'], text=True, capture_output=True, timeout=10, check=True)
        selected = {}
        for line in features.stdout.splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[0] in {'memories', 'external_agent_memory_import'}:
                selected[fields[0]] = fields[-1] == 'true'
        return {'version': version.stdout.strip(), 'feature_flags': selected}
    except (OSError, subprocess.SubprocessError) as error:
        return {'read_error': type(error).__name__}


def inventory(roots):
    result = []
    for root in sorted(set(roots)):
        try:
            result.append({'root': str(root), 'exists': root.is_dir(), 'markdown_files': sum(1 for path in root.rglob('*.md') if path.is_file())})
        except OSError as error:
            result.append({'root': str(root), 'read_error': type(error).__name__})
    return result


def main():
    home = Path.home()
    source = Path(__file__).resolve().parents[3]
    codex_home = Path(os.environ.get('CODEX_HOME', home / '.codex')).expanduser().resolve()
    claude_home = Path(os.environ.get('CLAUDE_CONFIG_DIR', home / '.claude')).expanduser().resolve()
    codex = read_settings(codex_home / 'config.toml')
    claude = read_settings(claude_home / 'settings.json')
    configured = claude.get('autoMemoryDirectory')
    claude_roots = list((claude_home / 'projects').glob('*/memory')) + [claude_home / 'agent-memory']
    if isinstance(configured, str) and Path(configured).expanduser().is_absolute():
        claude_roots.append(Path(configured).expanduser())
    links = installation_links(home, source, codex_home, claude_home)
    cursor_path, cursor_content = cursor_local_rule(home, source)
    memory_settings = codex.get('memories', {})
    if not isinstance(memory_settings, dict):
        memory_settings = {'read_error': 'ExpectedTable'}
    desktop = Path('/usr/lib/chatgpt/resources/codex')
    report = {
        'read_only': True,
        'scope': 'Local installation only; no cloud stores, private databases, or memory contents are read.',
        'policy_links': {str(path): {'correct': path.is_symlink() and path.resolve() == target.resolve(), 'target': str(target)} for path, target in links.items()},
        'codex': {
            'home': str(codex_home),
            'cli': inspect_codex(shutil.which('codex')),
            'desktop': inspect_codex(str(desktop)) if desktop.exists() else {'available': False},
            'memory_settings': {key: memory_settings.get(key, 'unset; product default applies') for key in ['generate_memories', 'use_memories']},
            'memory_settings_read_error': memory_settings.get('read_error'),
            'config_read_error': codex.get('read_error'),
            'inventory': inventory([codex_home / 'memories']),
        },
        'claude': {
            'home': str(claude_home),
            'autoMemoryEnabled': claude.get('autoMemoryEnabled', 'unset; product default applies'),
            'autoMemoryDirectory': configured,
            'autoDreamEnabled': claude.get('autoDreamEnabled', 'unset; product default applies'),
            'config_read_error': claude.get('read_error'),
            'inventory': inventory(claude_roots),
        },
        'cursor': {
            'native_memory_status': 'Unknown; no supported native memory read interface verified. Local file absence does not establish remote memory absence.',
            'local_policy_rule': {'path': str(cursor_path), 'correct': cursor_path.is_file() and not cursor_path.is_symlink() and cursor_path.read_text() == cursor_content, 'scope': 'Workspaces beneath the home directory; discovered through workspace ancestry.'},
            'global_policy_rule': 'Verify in the User Rules UI against rules/memory-policy.md. This helper does not query account-held rules.',
        },
        'native_sync': {
            'installed': False,
            'reason': 'A global per-memory interface and approval coverage have not passed verification across all three products.',
            'compatibility_reference': str(source / 'skills/memory-policy/references/native-interfaces.md'),
        },
    }
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
