#!/usr/bin/env python3
import argparse
import os
from pathlib import Path


def installation_links(home, source, codex_home=None, claude_home=None):
    canonical = home / '.agents'
    skill = canonical / 'skills/memory-policy'
    policy = canonical / 'AGENTS.md'
    return {
        skill: source / 'skills/memory-policy',
        policy: source / 'rules/memory-policy.md',
        (codex_home or home / '.codex') / 'AGENTS.md': policy,
        (claude_home or home / '.claude') / 'CLAUDE.md': policy,
        (claude_home or home / '.claude') / 'skills/memory-policy': skill,
        home / '.cursor/skills/memory-policy': skill,
    }


def cursor_local_rule(home, source):
    path = home / '.cursor/rules/memory-policy.mdc'
    content = '---\ndescription: Shared native memory approval policy\nalwaysApply: true\n---\n\n' + (source / 'rules/memory-policy.md').read_text()
    return path, content


def main():
    parser = argparse.ArgumentParser(description='Install shared memory policy links without changing native memory settings or content.')
    parser.add_argument('--home', type=Path, help='Isolated target user directory. When omitted, use the real home and respect CODEX_HOME and CLAUDE_CONFIG_DIR.')
    parser.add_argument('--apply', action='store_true', help='Create links after preflight. Default only prints the plan.')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[3]
    for required in ['skills/memory-policy/SKILL.md', 'rules/memory-policy.md']:
        if not (source / required).is_file():
            parser.exit(1, f'Missing source file: {source / required}\n')
    home = (args.home or Path.home()).resolve()
    codex_home = Path(os.environ.get('CODEX_HOME', home / '.codex')).expanduser().resolve() if args.home is None else home / '.codex'
    claude_home = Path(os.environ.get('CLAUDE_CONFIG_DIR', home / '.claude')).expanduser().resolve() if args.home is None else home / '.claude'
    links = installation_links(home, source, codex_home, claude_home)
    cursor_path, cursor_content = cursor_local_rule(home, source)
    conflicts = []
    for destination, target in links.items():
        present = destination.exists() or destination.is_symlink()
        correct = destination.is_symlink() and destination.resolve() == target.resolve()
        if present and not correct:
            conflicts.append(str(destination))
        print(f'{"present" if correct else "create"}: {destination} -> {target}')
    cursor_present = cursor_path.exists() or cursor_path.is_symlink()
    cursor_correct = cursor_path.is_file() and not cursor_path.is_symlink() and cursor_path.read_text() == cursor_content
    if cursor_present and not cursor_correct:
        conflicts.append(str(cursor_path))
    print(f'{"present" if cursor_correct else "create"}: {cursor_path} (generated router for workspaces beneath the home directory)')
    if conflicts:
        parser.exit(1, 'Existing paths require review; nothing changed:\n' + '\n'.join(conflicts) + '\n')
    if not args.apply:
        return
    for destination, target in links.items():
        if destination.is_symlink():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(target)
    if not cursor_correct:
        cursor_path.parent.mkdir(parents=True, exist_ok=True)
        with cursor_path.open('x') as handle:
            handle.write(cursor_content)
    invalid = [str(path) for path, target in links.items() if not path.is_symlink() or path.resolve() != target.resolve() or not target.exists()]
    if invalid:
        parser.exit(1, 'Installation incomplete; inspect these paths:\n' + '\n'.join(invalid) + '\n')
    if cursor_path.is_symlink() or cursor_path.read_text() != cursor_content:
        parser.exit(1, f'Installation incomplete; inspect {cursor_path}\n')
    print('Policy links installed. Native memory settings and content were not changed.')
    print(f'Cursor global routing uses the User Rules UI. Add or update the rule from {source / "rules/memory-policy.md"}; preserve other rules.')


if __name__ == '__main__':
    main()
