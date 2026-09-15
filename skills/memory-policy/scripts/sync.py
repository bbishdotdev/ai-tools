#!/usr/bin/env python3
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from memory_files import SyncError, atomic_change, exact_edit, file_hash, read_file, sync_lock
from native_backends import (
    DESTINATIONS, MAX_NOTE_BYTES, Profile, backends, changes_for,
    inspect_backend, validate_note,
)


@dataclass(frozen=True)
class Plan:
    operation: str
    note_id: str
    text: str | None
    destinations: tuple
    guards: tuple
    changes: tuple

    def digest(self):
        state = {
            'format': 'native-memory-sync-v1',
            'operation': self.operation, 'id': self.note_id, 'text': self.text,
            'destinations': self.destinations,
            'configuration': [{'path': str(path), 'sha256': file_hash(raw)} for path, raw in self.guards],
            'files': [{'path': str(change.path), 'before': file_hash(change.before), 'after': file_hash(change.after)} for change in self.changes],
        }
        return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()

    def preview(self):
        return {
            'status': 'plan', 'operation': self.operation, 'id': self.note_id,
            'text': self.text, 'destinations': self.destinations, 'plan_sha256': self.digest(),
            'approval': 'The digest binds these bytes to this plan. It does not prove human approval. Obtain approval of the exact change before applying.',
            'changes': [{
                'destination': change.destination, 'path': str(change.path), 'action': change.action,
                'before_sha256': file_hash(change.before), 'after_sha256': file_hash(change.after),
                'edit': exact_edit(change.before, change.after) if change.before != change.after else None,
            } for change in self.changes],
        }


def parse_destinations(value):
    names = value.split(',')
    if not names or len(names) != len(set(names)) or any(name not in DESTINATIONS for name in names):
        raise argparse.ArgumentTypeError('Use unique comma-separated destinations from codex,claude,cursor')
    return tuple(name for name in DESTINATIONS if name in names)


def make_plan(profile, destinations, operation, note_id, text):
    validate_note(note_id, text)
    available = backends(profile)
    selected = [available[name] for name in destinations]
    errors = [f'{backend.name}: {backend.error}' for backend in selected if backend.error]
    if errors:
        raise SyncError('Native preflight failed before memory writes. ' + ' '.join(errors))
    guards = tuple((backend.config_path, backend.config_bytes) for backend in selected)
    changes = tuple(change for backend in selected for change in changes_for(backend, note_id, text))
    paths = [change.path for change in changes]
    if len(paths) != len(set(paths)) or set(paths).intersection(path for path, _ in guards):
        raise SyncError('Native destinations overlap; configure distinct native memory directories before syncing')
    return Plan(operation, note_id, text, destinations, guards, changes)


def file_readback(changes):
    report = []
    for change in changes:
        entry = {'path': str(change.path), 'expected_sha256': file_hash(change.after)}
        try:
            actual = read_file(change.path)
            entry.update({'actual_sha256': file_hash(actual), 'matches': actual == change.after})
        except SyncError as error:
            entry.update({'matches': False, 'error': str(error)})
        report.append(entry)
    return report


def apply_plan(profile, plan, reviewed_digest):
    if plan.digest() != reviewed_digest:
        raise SyncError('Plan digest mismatch; nothing applied. Inspect current copies and review a new dry-run plan')
    with sync_lock(profile.home):
        current = make_plan(profile, plan.destinations, plan.operation, plan.note_id, plan.text)
        if current.digest() != reviewed_digest:
            raise SyncError('State changed after review; nothing applied. Inspect current copies and review a new dry-run plan')
        completed = []
        try:
            for change in current.changes:
                for path, expected in current.guards:
                    if read_file(path) != expected:
                        raise SyncError(f'Native configuration changed at {path}; review a new plan')
                if change.before == change.after:
                    continue
                atomic_change(change.path, change.before, change.after)
                completed.append(str(change.path))
            readback = file_readback(current.changes)
            if not all(entry['matches'] for entry in readback):
                raise SyncError('File readback differs from the reviewed result; native writers may have changed a copy')
        except (OSError, SyncError, KeyboardInterrupt) as error:
            return {
                'status': 'partial_failure', 'error': str(error), 'completed_paths': completed,
                'physical_file_readback': file_readback(current.changes),
                'recovery': 'No rollback was attempted. Inspect every copy and review a fresh plan before retrying.',
                'native_recall': 'Not tested by this command.',
            }
        return {
            'status': 'applied' if completed else 'unchanged', 'id': current.note_id,
            'destinations': current.destinations, 'completed_paths': completed,
            'physical_file_readback': readback,
            'native_recall': 'Not tested by this command. Verify in fresh native sessions.',
            'concurrency': 'Cooperating sync commands share a lock. Native writers do not; cross-file atomicity is not guaranteed.',
        }


def inspect(profile, destinations, note_id):
    validate_note(note_id)
    available = backends(profile)
    report, values, complete, index_matches = {}, [], True, True
    for name in destinations:
        backend = available[name]
        try:
            result = inspect_backend(backend, note_id)
        except SyncError as error:
            result = {'copies': [], 'error': str(error)}
        report[name] = {'readiness': backend.report(), **result}
        complete = complete and result['error'] is None
        values.extend(copy['content'] for copy in result['copies'])
        index_matches = index_matches and all(copy.get('index_matches', True) for copy in result['copies'])
    drift = len(set(values)) > 1 or not index_matches
    state = 'unavailable' if not complete else 'drift' if drift else 'absent' if not any(value is not None for value in values) else 'consistent'
    return {
        'status': 'inspection', 'read_only': True, 'id': note_id, 'copy_state': state,
        'observed_drift': drift, 'destinations': report,
        'native_recall': 'This is physical file inspection, not a native-session recall test.',
    }


def main():
    parser = argparse.ArgumentParser(description='Review and synchronize approved personal native memories. Dry-run by default; native settings are never changed.')
    parser.add_argument('--home', type=Path, help='Disposable home. Ignores CODEX_HOME and CLAUDE_CONFIG_DIR and requires Claude native memory inside this home.')
    parser.add_argument('--destinations', type=parse_destinations, default=DESTINATIONS, help='Default codex,claude,cursor. Use a subset only when the user explicitly authorizes partial synchronization.')
    commands = parser.add_subparsers(dest='command', required=True)
    for operation in ['set', 'delete']:
        command = commands.add_parser(operation)
        command.add_argument('id')
        if operation == 'set':
            command.add_argument('--text', required=True, help=f'Exact approved note text; helper limit {MAX_NOTE_BYTES} UTF-8 bytes. Do not put secrets in shell arguments.')
        command.add_argument('--apply-plan', metavar='SHA256', help='Apply only if this previously reviewed plan digest still matches. The digest is not proof of human consent.')
    commands.add_parser('status')
    commands.add_parser('inspect').add_argument('id')
    args = parser.parse_args()
    profile = Profile.load(args.home)
    try:
        if args.command == 'status':
            report = {'read_only': True, 'backends': {name: backend.report() for name, backend in backends(profile).items()}}
        elif args.command == 'inspect':
            report = inspect(profile, args.destinations, args.id)
        else:
            plan = make_plan(profile, args.destinations, args.command, args.id, getattr(args, 'text', None))
            report = apply_plan(profile, plan, args.apply_plan) if args.apply_plan is not None else plan.preview()
    except (OSError, SyncError, UnicodeError) as error:
        print(json.dumps({'status': 'blocked', 'error': str(error), 'recovery': 'If an apply was requested, inspect current copies before retrying.'}, indent=2))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 3 if report.get('status') == 'partial_failure' else 0


if __name__ == '__main__':
    raise SystemExit(main())
