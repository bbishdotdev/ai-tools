#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from native_backends import CURSOR_RULE_HEADER, FileChange, Profile, cursor_startup_rule
from memory_files import SyncError, file_hash, read_file
from activation import (
    activation_changes, apply_changes, backup_path, claude_configuration,
    cursor_configuration, update_cursor_router,
)


def installation_links(home, source, codex_home=None, claude_home=None):
    canonical = home / '.agents'
    workspace = home / 'Work'
    skill = workspace / '.agents/skills/memory-policy'
    policy = workspace / 'AGENTS.md'
    return {
        skill: source / 'skills/memory-policy',
        policy: source / 'rules/memory-policy.md',
        workspace / 'CLAUDE.md': policy,
        canonical / 'skills/memory-policy': skill,
        canonical / 'AGENTS.md': policy,
        (codex_home or home / '.codex') / 'AGENTS.md': canonical / 'AGENTS.md',
        (claude_home or home / '.claude') / 'CLAUDE.md': canonical / 'AGENTS.md',
        (claude_home or home / '.claude') / 'skills/memory-policy': canonical / 'skills/memory-policy',
        home / '.cursor/skills/memory-policy': canonical / 'skills/memory-policy',
    }


def cursor_local_rule(home, source, directory=None):
    path = home / '.cursor/rules/memory-policy.mdc'
    policy = (source / 'rules/memory-policy.md').read_text()
    content = CURSOR_RULE_HEADER + '<!-- memory-sync-policy:begin -->\n' + policy + '<!-- memory-sync-policy:end -->\n\n' + cursor_startup_rule(home, directory)
    return path, content


def main():
    parser = argparse.ArgumentParser(description='Install the shared memory policy. Optionally activate native Codex/Claude synchronization and the Cursor file bridge.')
    parser.add_argument('--home', type=Path, help='Isolated target home. Ignores CODEX_HOME and CLAUDE_CONFIG_DIR.')
    parser.add_argument('--apply', action='store_true', help='Apply after preflight. Default only prints the plan.')
    parser.add_argument('--activate-sync', action='store_true', help='Enable native Codex/Claude memory and the Cursor file bridge, preserving existing settings and memory files.')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[3]
    for required in ['skills/memory-policy/SKILL.md', 'rules/memory-policy.md']:
        if not (source / required).is_file():
            parser.exit(1, f'Missing source file: {source / required}\n')
    profile = Profile.load(args.home)
    home = profile.home
    links = installation_links(home, source, profile.codex_home, profile.claude_home)
    conflicts = []
    for destination, target in links.items():
        present = destination.exists() or destination.is_symlink()
        correct = destination.is_symlink() and destination.resolve() == target.resolve()
        if present and not correct:
            conflicts.append(str(destination))
        print(f'{"present" if correct else "create"}: {destination} -> {target}')
    if conflicts:
        parser.exit(1, 'Existing paths require review; nothing changed:\n' + '\n'.join(conflicts) + '\n')
    try:
        cursor_config, cursor_directory = cursor_configuration(profile)
        cursor_path, cursor_content = cursor_local_rule(home, source, cursor_directory)
        cursor_before = read_file(cursor_path)
        cursor_after = update_cursor_router(cursor_before, cursor_content)
        router_change = FileChange('cursor-router', cursor_path, cursor_before, cursor_after, 'configuration')
        changes = [router_change]
        if args.activate_sync:
            claude_config, claude_directory = claude_configuration(profile)
            changes = activation_changes(profile, router_change, cursor_config, claude_config, claude_directory, cursor_directory)
        print(json.dumps({
            'activate_sync': args.activate_sync,
            'changes': [{
                'path': str(change.path), 'kind': change.kind, 'action': change.action,
                'before_sha256': file_hash(change.before), 'after_sha256': file_hash(change.after),
                'backup': str(backup_path(home, change)) if change.kind == 'configuration' and change.before is not None and change.before != change.after else None,
            } for change in changes],
        }, indent=2))
        if not args.apply:
            return
        for destination, target in links.items():
            if destination.is_symlink() and destination.resolve() == target.resolve():
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(target)
        completed = apply_changes(profile, changes)
        invalid = [str(path) for path, target in links.items() if not path.is_symlink() or path.resolve() != target.resolve() or not target.exists()]
        if invalid:
            raise SyncError('Installation incomplete; inspect these paths: ' + ', '.join(invalid))
        print(f'Applied {len(completed)} file changes. Existing native memory files were retained.')
        if args.activate_sync:
            print('Synchronization activated. Codex and Claude use native memory; Cursor uses the explicit file bridge. No personal memories were created.')
        else:
            print('Policy links installed. Native memory settings and content were not changed.')
        print(f'Cursor global routing also uses the User Rules UI. Keep its rule aligned with {source / "rules/memory-policy.md"}.')
    except (OSError, SyncError, UnicodeError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
