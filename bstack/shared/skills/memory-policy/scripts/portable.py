#!/usr/bin/env python3
"""Preview or install the bundled, optional user-wide memory component."""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tomllib
import uuid

sys.dont_write_bytecode = True
from activation import (activation_changes, backup_path, claude_configuration,
                        cursor_configuration, update_cursor_router)
from cursor_hooks import context_hook
from layout import component_source, policy_source
from memory_files import (SyncError, atomic_change, exact_edit, file_hash,
                          parent_directory, read_file, sync_lock, text_file)
from native_backends import CURSOR_RULE_HEADER, FileChange, Profile, backends, cursor_startup_rule, read_config


PAYLOAD_SCRIPTS = ('activation.py', 'cursor_context.py', 'cursor_hooks.py',
                   'cursor_projection.py', 'layout.py', 'memory_files.py',
                   'native_backends.py', 'portable.py', 'sync.py')
BEGIN = '<!-- bstack-memory:begin -->'
END = '<!-- bstack-memory:end -->'


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n').encode()


def legacy_installation(profile):
    home = profile.home
    path = home / 'Work/.agents/memory-sync/config.json'
    raw, config = read_config(path)
    legacy_skill = home / 'Work/.agents/skills/memory-policy'
    skill_present = legacy_skill.exists() or legacy_skill.is_symlink()
    if raw is None and not skill_present:
        return None
    cursor = config.get('cursor', {})
    if raw is not None and (config.get('version') != 1 or not isinstance(cursor, dict) or cursor.get('mode') != 'file-bridge'):
        raise SyncError('Unrecognized legacy memory configuration; review it before portable setup')
    return {'status': 'legacy_external', 'runtime': str(legacy_skill), 'config': str(path),
            'reason': 'An existing Work-based memory installation is managed separately. Portable migration is not implemented; nothing will be replaced.'}


def payload(source=None):
    source = source or component_source()
    entry = source / 'SKILL.md'
    if not entry.exists():
        entry = source / 'WORKFLOW.md'
    files = {'SKILL.md': read_file(entry), 'policy.md': read_file(policy_source(source))}
    files.update({'scripts/' + name: read_file(source / 'scripts' / name) for name in PAYLOAD_SCRIPTS})
    references = source / 'references'
    for path in sorted(references.rglob('*')):
        if path.is_symlink():
            raise SyncError(f'Unsafe memory payload reference: {path}')
        if path.is_file():
            files[str(path.relative_to(source))] = read_file(path)
    if any(value is None for value in files.values()):
        raise SyncError('The bundled memory component is incomplete')
    return files


def link_snapshot(path):
    try:
        with parent_directory(path) as directory:
            try:
                info = os.stat(path.name, dir_fd=directory, follow_symlinks=False)
            except FileNotFoundError:
                return None
            if not stat.S_ISLNK(info.st_mode):
                raise SyncError(f'Unowned memory skill path: {path}')
            return os.readlink(path.name, dir_fd=directory)
    except SyncError as error:
        if isinstance(error.__cause__, FileNotFoundError):
            return None
        raise


def links_for(profile):
    canonical = profile.home / '.agents/skills/memory-policy'
    links = {str(canonical): str(profile.layout.runtime)}
    for root in (profile.codex_home, profile.claude_home, profile.home / '.cursor'):
        path = str(root / 'skills/memory-policy')
        if path != str(canonical):
            links[path] = str(canonical)
    return links


def block_change(path, before, desired, previous):
    text = text_file(before, path)
    if previous is not None:
        if text.count(previous) != 1 or text.count(BEGIN) != 1 or text.count(END) != 1:
            raise SyncError(f'Owned global memory instruction changed: {path}')
        updated = text.replace(previous, desired, 1)
    else:
        if BEGIN in text or END in text:
            raise SyncError(f'Unowned global memory instruction markers: {path}')
        separator = '' if not text else '\n' if text.endswith('\n') else '\n\n'
        updated = text + separator + desired
    return FileChange('policy', path, before, updated.encode(), 'configuration')


def check_runtime(profile, installed):
    runtime = profile.layout.runtime
    expected = installed.get('files', {}) if installed else {}
    if not isinstance(expected, dict) or installed and not expected or any(not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts or not isinstance(value, str) for name, value in expected.items()):
        raise SyncError('Invalid portable memory runtime manifest')
    if runtime.is_symlink():
        raise SyncError('The portable memory runtime must not be a symlink')
    if runtime.exists() and not runtime.is_dir():
        raise SyncError('The portable memory runtime must be a directory')
    actual = {str(path.relative_to(runtime)) for path in runtime.rglob('*') if path.is_file() or path.is_symlink()}
    if actual != set(expected):
        raise SyncError('Portable memory runtime ownership or file inventory changed; review before setup')
    for name, expected_hash in expected.items():
        if file_hash(read_file(runtime / name)) != expected_hash:
            raise SyncError(f'Portable memory runtime was edited: {name}')
    return expected


def configuration_preview(change, profile):
    """Show owned setting changes without printing unrelated JSON or memory values."""
    if change.destination in ('codex', 'claude', 'cursor'):
        parse = tomllib.loads if change.path.suffix == '.toml' else json.loads
        initial = b'{}' if parse is json.loads else b''
        old = parse((change.before or initial).decode())
        new = parse(change.after.decode())
        keys = {'codex': [('features', 'memories'), ('memories', 'use_memories')],
                'claude': [('autoMemoryEnabled',), ('autoMemoryDirectory',)],
                'cursor': [('version',), ('cursor',)]}[change.destination]
        edits = []
        for fields in keys:
            before, after = old, new
            for field in fields:
                before = before.get(field) if isinstance(before, dict) else None
                after = after.get(field) if isinstance(after, dict) else None
            if before != after:
                edits.append({'setting': '.'.join(fields), 'before': before, 'after': after})
        return {'settings': edits, 'formatting': 'JSON settings may be reformatted; unrelated values are retained and omitted from this preview.'}
    if change.destination == 'cursor-hook':
        return {'managed_hook': {'event': 'beforeSubmitPrompt', **context_hook(profile.home, profile.layout)}}
    return {'edit': exact_edit(change.before, change.after)}


@dataclass
class Plan:
    profile: Profile
    source: Path
    changes: list
    links: list
    guards: list
    component_sha256: str

    def digest(self):
        value = {'schema': 1, 'component': self.component_sha256,
                 'changes': [{'path': str(change.path), 'before': file_hash(change.before), 'after': file_hash(change.after)} for change in self.changes],
                 'links': self.links, 'guards': self.guards}
        return hashlib.sha256(encoded(value)).hexdigest()

    def preview(self):
        changes = []
        for change in self.changes:
            item = {'path': str(change.path), 'kind': change.kind, 'action': change.action,
                    'before_sha256': file_hash(change.before), 'after_sha256': file_hash(change.after)}
            if change.kind == 'configuration' and change.before != change.after:
                item.update(configuration_preview(change, self.profile))
                item['backup'] = str(backup_path(self.profile.home, change, self.profile.layout)) if change.before is not None else None
            changes.append(item)
        return {'status': 'plan', 'read_only': True, 'plan_sha256': self.digest(),
                'runtime': str(self.profile.layout.runtime), 'state': str(self.profile.layout.state),
                'destinations': ['codex', 'claude', 'cursor'], 'changes': changes,
                'links': self.links, 'notice': 'Optional user-wide setup. No personal memories are added or migrated. The digest binds the setup bytes, not consent to save personal notes. Existing Claude project memories remain intact; a newly configured shared directory becomes its future startup index.',
                'native_recall': 'Not tested; verify in fresh application sessions.'}


def make_plan(profile, source=None):
    source = source or component_source()
    legacy = legacy_installation(profile)
    if legacy:
        raise SyncError(legacy['reason'])
    previous_bytes, previous = read_config(profile.layout.manifest)
    old_files = check_runtime(profile, previous)
    source_files = payload(source)
    file_hashes = {name: file_hash(value) for name, value in sorted(source_files.items())}
    component_hash = hashlib.sha256(encoded(file_hashes)).hexdigest()
    changes = [FileChange('runtime', profile.layout.runtime / name,
                          read_file(profile.layout.runtime / name), source_files.get(name), 'runtime')
               for name in sorted(set(old_files) | set(source_files))]
    links = links_for(profile)
    previous_links = previous.get('links', {})
    if not isinstance(previous_links, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in previous_links.items()):
        raise SyncError('Invalid portable memory skill ownership')
    if previous_bytes is not None and set(previous_links) != set(links):
        raise SyncError('Portable memory native homes or skill bindings changed; relocation is not implemented')
    link_changes = []
    for name, target in links.items():
        path = Path(name)
        before = link_snapshot(path)
        if before is not None and (previous_links.get(name) != before or before != target):
            raise SyncError(f'Unowned or changed memory skill link: {path}')
        if before is None and name in previous_links:
            raise SyncError(f'Owned memory skill link was removed: {path}')
        link_changes.append({'path': name, 'before': before, 'after': target})

    policy = (f'For personal memory changes, read and follow `{profile.layout.runtime / "SKILL.md"}` '
              'and require approval of the exact content. '
              f'The shared policy is `{profile.layout.runtime / "policy.md"}`. '
              'For ordinary recall, use supplied memories directly; load only the relevant source if context is missing.\n')
    block = BEGIN + '\n' + policy + END + '\n'
    blocks = {str(path): block for path in {profile.home / '.agents/AGENTS.md', profile.codex_home / 'AGENTS.md', profile.claude_home / 'CLAUDE.md'}}
    previous_blocks = previous.get('blocks', {})
    if not isinstance(previous_blocks, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in previous_blocks.items()):
        raise SyncError('Invalid portable memory policy ownership')
    if previous_bytes is not None and set(previous_blocks) != set(blocks):
        raise SyncError('Portable memory global instruction bindings changed; relocation is not implemented')
    policy_changes = [block_change(Path(path), read_file(Path(path)), value, previous_blocks.get(path))
                      for path, value in sorted(blocks.items())]
    cursor_config, cursor_directory = cursor_configuration(profile)
    claude_config, claude_directory = claude_configuration(profile)
    for native_home in (profile.codex_home, profile.claude_home):
        if native_home.is_relative_to(profile.layout.root) or profile.layout.root.is_relative_to(native_home):
            raise SyncError('Native application homes must be separate from the portable memory runtime and state')
    if (claude_directory.is_relative_to(profile.layout.runtime)
            or profile.layout.root.is_relative_to(claude_directory)
            or claude_directory.is_relative_to(profile.layout.state) and not claude_directory.is_relative_to(profile.layout.claude)):
        raise SyncError('Claude native memory must be separate from the runtime and shared state infrastructure')
    router_path = profile.home / '.cursor/rules/memory-policy.mdc'
    desired_router = CURSOR_RULE_HEADER + '<!-- memory-sync-policy:begin -->\n' + policy + '<!-- memory-sync-policy:end -->\n\n' + cursor_startup_rule(profile.home, cursor_directory, profile.layout)
    router_before = read_file(router_path)
    if previous_bytes is None and router_before is not None:
        raise SyncError('Existing Cursor memory policy is not owned by this portable installation')
    if previous_bytes is not None and (not isinstance(previous.get('cursor_router'), str) or not text_file(router_before, router_path).startswith(previous['cursor_router'])):
        raise SyncError('Owned Cursor memory policy changed; review it before setup')
    router = FileChange('cursor-router', router_path, router_before, update_cursor_router(router_before, desired_router), 'configuration')
    activation = activation_changes(profile, router, cursor_config, claude_config, claude_directory, cursor_directory)
    manifest = {'schema': 1, 'name': 'bstack-memory', 'home': str(profile.home),
                'native_homes': {'codex': str(profile.codex_home), 'claude': str(profile.claude_home)},
                'files': file_hashes, 'component_sha256': component_hash, 'links': links, 'blocks': blocks,
                'cursor_router': desired_router}
    changes.append(FileChange('installation', profile.layout.manifest, previous_bytes, encoded(manifest), 'manifest'))
    changes.extend(policy_changes + activation)
    paths = [str(change.path) for change in changes] + list(links)
    if len(paths) != len(set(paths)):
        raise SyncError('Portable memory installation destinations overlap')
    if profile.isolated and any(not Path(path).is_relative_to(profile.home) for path in paths):
        raise SyncError('--home requires all setup destinations inside the disposable home')
    for change in changes:
        if change.kind == 'configuration' and change.before is not None and change.before != change.after:
            backup = backup_path(profile.home, change, profile.layout)
            existing = read_file(backup)
            if existing is not None and existing != change.before:
                raise SyncError(f'Configuration backup collision at {backup}')
    guards = [{'path': str(path), 'sha256': file_hash(expected)} for change in changes for path, expected in change.dependencies]
    return Plan(profile, source, changes, link_changes, guards, component_hash)


def apply_link(entry):
    path = Path(entry['path'])
    if link_snapshot(path) != entry['before']:
        raise SyncError(f'Memory skill binding changed: {path}')
    if entry['before'] == entry['after']:
        return
    with parent_directory(path, create=True) as directory:
        os.symlink(entry['after'], path.name, dir_fd=directory)
        os.fsync(directory)


def publish_runtime(plan):
    changes = [change for change in plan.changes if change.kind == 'runtime']
    if all(change.before == change.after for change in changes):
        return None
    runtime = plan.profile.layout.runtime
    stage = '.runtime-stage-' + uuid.uuid4().hex
    previous = '.runtime-previous-' + uuid.uuid4().hex
    moved = False
    published = False
    with parent_directory(runtime, create=True) as directory:
        os.mkdir(stage, 0o700, dir_fd=directory)
        try:
            for change in changes:
                if change.after is not None:
                    target = runtime.parent / stage / change.path.relative_to(runtime)
                    atomic_change(target, None, change.after)
            if any(read_file(change.path) != change.before for change in changes):
                raise SyncError('Runtime changed during staging; setup stopped')
            if runtime.exists():
                os.rename(runtime.name, previous, src_dir_fd=directory, dst_dir_fd=directory)
                moved = True
            os.rename(stage, runtime.name, src_dir_fd=directory, dst_dir_fd=directory)
            published = True
            os.fsync(directory)
        except (OSError, SyncError, KeyboardInterrupt):
            if published:
                os.rename(runtime.name, stage, src_dir_fd=directory, dst_dir_fd=directory)
            if moved:
                os.rename(previous, runtime.name, src_dir_fd=directory, dst_dir_fd=directory)
            shutil.rmtree(stage, dir_fd=directory)
            raise
    return {'backup': previous if moved else None, 'stage': stage}


def restore_runtime(plan, published):
    if published is None:
        return
    runtime = plan.profile.layout.runtime
    wanted = {str(change.path.relative_to(runtime)): file_hash(change.after)
              for change in plan.changes if change.kind == 'runtime' and change.after is not None}
    check_runtime(plan.profile, {'files': wanted})
    with parent_directory(runtime) as directory:
        os.rename(runtime.name, published['stage'], src_dir_fd=directory, dst_dir_fd=directory)
        if published['backup'] is not None:
            os.rename(published['backup'], runtime.name, src_dir_fd=directory, dst_dir_fd=directory)
        shutil.rmtree(published['stage'], dir_fd=directory)
        os.fsync(directory)


def discard_previous_runtime(profile, published):
    if published and published['backup']:
        with parent_directory(profile.layout.runtime) as directory:
            shutil.rmtree(published['backup'], dir_fd=directory)


def rollback(plan, attempted_files, attempted_links, published):
    errors = []
    for entry in reversed(attempted_links):
        try:
            current = link_snapshot(Path(entry['path']))
            if current == entry['before']:
                continue
            if current != entry['after'] or entry['before'] is not None:
                raise SyncError('Skill link changed during rollback')
            path = Path(entry['path'])
            with parent_directory(path) as directory:
                os.unlink(path.name, dir_fd=directory)
                os.fsync(directory)
        except (OSError, SyncError) as error:
            errors.append({'path': entry['path'], 'error': str(error)})
    for change in reversed(attempted_files):
        try:
            current = read_file(change.path)
            if current == change.before:
                continue
            atomic_change(change.path, change.after, change.before)
        except (OSError, SyncError) as error:
            errors.append({'path': str(change.path), 'error': str(error)})
    try:
        restore_runtime(plan, published)
    except (OSError, SyncError) as error:
        errors.append({'path': str(plan.profile.layout.runtime), 'error': str(error)})
    return errors


def apply_plan(plan, digest):
    if plan.digest() != digest:
        raise SyncError('Setup plan digest mismatch; nothing changed. Preview and review the current plan.')
    completed = []
    with sync_lock(plan.profile.home, plan.profile.layout):
        current = make_plan(plan.profile, plan.source)
        if current.digest() != digest:
            raise SyncError('Setup state changed after review; no configuration or memory changes applied.')
        attempted_files, attempted_links, published = [], [], None
        try:
            published = publish_runtime(current)
            if published:
                completed.append(str(current.profile.layout.runtime))
            for change in current.changes:
                if change.kind == 'runtime':
                    continue
                for path, expected in change.dependencies:
                    if read_file(path) != expected:
                        raise SyncError(f'Setup dependency changed: {path}')
                if change.before == change.after:
                    continue
                if change.kind == 'configuration' and change.before is not None:
                    backup = backup_path(plan.profile.home, change, plan.profile.layout)
                    if read_file(backup) is None:
                        atomic_change(backup, None, change.before)
                attempted_files.append(change)
                atomic_change(change.path, change.before, change.after)
                completed.append(str(change.path))
            for entry in current.links:
                if entry['before'] != entry['after']:
                    attempted_links.append(entry)
                apply_link(entry)
                if entry['before'] != entry['after']:
                    completed.append(entry['path'])
            if any(read_file(change.path) != change.after for change in current.changes) or any(link_snapshot(Path(entry['path'])) != entry['after'] for entry in current.links):
                raise SyncError('Portable memory setup readback changed')
        except (OSError, SyncError, KeyboardInterrupt) as error:
            errors = rollback(current, attempted_files, attempted_links, published)
            return {'status': 'partial_failure' if errors else 'rolled_back', 'error': str(error) or type(error).__name__,
                    'attempted_paths': completed, 'rollback_errors': errors,
                    'recovery': 'Concurrent edits were preserved; inspect rollback errors before retrying.' if errors else 'Installer changes were rolled back. Preview and retry setup; private configuration backups were retained.'}
        cleanup_warning = None
        try:
            discard_previous_runtime(current.profile, published)
        except (OSError, SyncError) as error:
            cleanup_warning = 'Setup is complete, but the previous code snapshot could not be removed: ' + str(error)
    report = {'status': 'applied' if completed else 'unchanged', 'runtime': str(plan.profile.layout.runtime),
            'state': str(plan.profile.layout.state), 'completed_paths': completed,
            'native_recall': 'Not tested; verify in fresh application sessions.',
            'notice': 'Memory configuration is user-wide and independent of project removal. Start fresh agent sessions to load global instructions.'}
    if cleanup_warning:
        report['cleanup_warning'] = cleanup_warning
    return report


def status_report(profile):
    legacy = legacy_installation(profile)
    if legacy:
        return {**legacy, 'read_only': True, 'native_recall': 'Not tested.'}
    raw, installed = read_config(profile.layout.manifest)
    if raw is None:
        return {'status': 'not_installed', 'read_only': True,
                'notice': 'Memory setup is optional and user-wide. Project installation does not activate it.'}
    check_runtime(profile, installed)
    for name, target in installed.get('links', {}).items():
        if link_snapshot(Path(name)) != target:
            raise SyncError(f'Portable memory skill binding changed: {name}')
    for name, block in installed.get('blocks', {}).items():
        text = text_file(read_file(Path(name)), Path(name))
        if text.count(block) != 1:
            raise SyncError(f'Portable memory policy binding changed: {name}')
    reports = {name: backend.report() for name, backend in backends(profile).items()}
    ready = all(report['ready'] for report in reports.values())
    return {'status': 'ready' if ready else 'needs_attention', 'read_only': True,
            'runtime': str(profile.layout.runtime), 'state': str(profile.layout.state),
            'component_sha256': installed['component_sha256'], 'destinations': reports,
            'native_recall': 'Not tested; file consistency does not establish fresh-session recall.',
            'approval_coverage': 'Exact personal-note approval remains required. This setup does not control native background writers.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('setup', 'status'):
        command = commands.add_parser(name)
        command.add_argument('--home', type=Path, help='Disposable home; ignore production application environment paths.')
        if name == 'setup':
            command.add_argument('--apply-plan', metavar='SHA256')
    args = parser.parse_args()
    try:
        profile = Profile.load(args.home, portable=True)
        if args.command == 'status':
            report = status_report(profile)
        else:
            plan = make_plan(profile)
            report = apply_plan(plan, args.apply_plan) if args.apply_plan is not None else plan.preview()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2 if report['status'] in ('partial_failure', 'rolled_back', 'needs_attention') else 0
    except (OSError, SyncError, UnicodeError, ValueError) as error:
        print(json.dumps({'status': 'blocked', 'error': str(error), 'recovery': 'Inspect current installation and review a fresh setup plan. No personal memories were migrated.'}, indent=2))
        return 2


if __name__ == '__main__':
    sys.exit(main())
