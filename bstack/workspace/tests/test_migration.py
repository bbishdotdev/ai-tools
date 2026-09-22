"""Frozen schema-1 data, additive rollback, replay, and worktree migration races."""
import contextlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wayfinder.core import Workspace, DomainError, SCHEMA, SCHEMA_VERSION
from wayfinder import migration

CLI = Path(__file__).resolve().parents[1] / 'cli.py'
FIXTURE = json.loads((Path(__file__).parent / 'fixtures/workspace-v1.json').read_text())
OLD_TABLES = tuple(FIXTURE['tables'])


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.project = self.base / 'repo'
        self.project.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.project), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def freeze(self, git=False):
        if git:
            self.git('init')
            self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.com', 'commit', '--allow-empty', '-m', 'init')
        directory = self.project / '.bstack/workspace'
        directory.mkdir(parents=True)
        self.db_path = directory / 'wayfinder.sqlite3'
        self.metadata_path = directory / 'metadata.json'
        metadata = {**FIXTURE['metadata'], 'root': str(self.project)}
        self.metadata_bytes = json.dumps(metadata, indent=3).encode() + b'\n'
        self.metadata_path.write_bytes(self.metadata_bytes)
        if git:
            self.binding = self.project / '.git/bstack-wayfinder.json'
            self.binding.write_bytes(self.metadata_bytes)
        with contextlib.closing(sqlite3.connect(self.db_path)) as db, db:
            db.executescript(SCHEMA)
            for table, rows in FIXTURE['tables'].items():
                for row in rows:
                    if table == 'workspace':
                        row = [row[0], str(self.project), row[2]]
                    db.execute('INSERT INTO ' + table + ' VALUES (' + ','.join('?' for _ in row) + ')', row)
            db.execute('PRAGMA user_version=1')
            db.commit()
            db.execute('PRAGMA journal_mode=WAL')
        self.before = self.snapshot()

    def snapshot(self):
        with contextlib.closing(sqlite3.connect(self.db_path)) as db, db:
            return {table: db.execute('SELECT * FROM ' + table + ' ORDER BY rowid').fetchall() for table in OLD_TABLES}

    def assert_preserved(self, version):
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(self.metadata_path.read_bytes(), self.metadata_bytes)
        if hasattr(self, 'binding'):
            self.assertEqual(self.binding.read_bytes(), self.metadata_bytes)
        with contextlib.closing(sqlite3.connect(self.db_path)) as db, db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], version)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            new_tables = set(row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")) - set(OLD_TABLES)
            self.assertEqual(new_tables, {'specs', 'spec_revisions', 'tickets', 'ticket_relationships'} if version == 2 else set())

    def test_real_v1_rows_claim_wait_answer_history_replays_and_metadata_survive(self):
        self.freeze(git=True)
        workspace = Workspace.discover(self.project)
        self.assert_preserved(2)
        for replay in FIXTURE['replays']:
            self.assertEqual(workspace.operate(replay['envelope']), replay['result'])
        self.assert_preserved(2)
        backup = self.db_path.with_name('wayfinder.schema-v1.sqlite3')
        self.assertTrue(backup.is_file())
        with contextlib.closing(sqlite3.connect(backup)) as db, db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT * FROM requests ORDER BY rowid').fetchall(), self.before['requests'])
        backup_bytes = backup.read_bytes()
        self.assertEqual(Workspace.initialize(self.project).info, workspace.info)
        self.assertEqual(Workspace.discover(self.project).info, workspace.info)
        self.assertEqual(backup.read_bytes(), backup_bytes)
        self.assert_preserved(2)

    def test_backup_failure_stops_before_any_schema_write(self):
        self.freeze()
        with patch('wayfinder.migration.backup_v1', side_effect=OSError('disk full')):
            with self.assertRaises(DomainError):
                Workspace.discover(self.project)
        self.assert_preserved(1)
        Workspace.discover(self.project)
        self.assert_preserved(2)

    def test_failure_midway_through_ddl_rolls_back_entire_upgrade(self):
        self.freeze()
        statements = migration.KANBAN_DDL[:3] + ('CREATE TABLE broken (',) + migration.KANBAN_DDL[3:]
        with patch('wayfinder.migration.KANBAN_DDL', statements):
            with self.assertRaises(DomainError):
                Workspace.discover(self.project)
        self.assert_preserved(1)
        Workspace.discover(self.project)
        self.assert_preserved(2)

    def test_crash_immediately_after_commit_opens_idempotently(self):
        self.freeze(git=True)
        original = migration.upgrade
        def committed_then_failed(db, path):
            original(db, path)
            raise OSError('simulated process loss after commit')
        with patch('wayfinder.migration.upgrade', side_effect=committed_then_failed):
            with self.assertRaises(DomainError):
                Workspace.discover(self.project)
        self.assert_preserved(2)
        Workspace.discover(self.project)
        self.assert_preserved(2)

    def test_bad_binding_database_identity_future_version_and_missing_store_never_upgrade(self):
        self.freeze(git=True)
        cases = [('metadata', None), ('identity', None), ('version', 99), ('incomplete', None)]
        original = self.db_path.read_bytes()
        for case, value in cases:
            if case == 'metadata':
                self.metadata_path.write_text(json.dumps({**FIXTURE['metadata'], 'root': str(self.project), 'id': 'wrong'}))
            else:
                with contextlib.closing(sqlite3.connect(self.db_path)) as db, db:
                    if case == 'identity':
                        db.execute("UPDATE workspace SET id='wrong'")
                    elif case == 'version':
                        db.execute('PRAGMA user_version=99')
                    else:
                        db.execute('DROP TABLE requests')
            with self.assertRaises(DomainError):
                Workspace.discover(self.project)
            self.assertFalse(self.db_path.with_name('wayfinder.schema-v1.sqlite3').exists())
            self.metadata_path.write_bytes(self.metadata_bytes)
            for suffix in ['', '-wal', '-shm']:
                self.db_path.with_name(self.db_path.name + suffix).unlink(missing_ok=True)
            self.db_path.write_bytes(original)
        self.db_path.unlink()
        with self.assertRaises(DomainError):
            Workspace.discover(self.project)
        self.assertFalse(self.db_path.exists())

    def test_two_worktrees_upgrade_one_store_and_keep_one_backup(self):
        self.freeze(git=True)
        tree = self.base / 'tree'
        self.git('worktree', 'add', '-b', 'second', str(tree))
        processes = [subprocess.Popen([sys.executable, str(CLI), '--project', str(project), 'call'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for project in [self.project, tree]]
        for process in processes:
            process.stdin.write(json.dumps({'op': 'workspace.read', 'input': {}})); process.stdin.close()
        results = []
        for process in processes:
            process.wait(timeout=10)
            results.append(json.loads(process.stdout.read()))
            self.assertEqual(process.stderr.read(), '')
            process.stdout.close(); process.stderr.close()
        self.assertTrue(all(result['ok'] for result in results), results)
        self.assertEqual(results[0], results[1])
        self.assertEqual(len(list(self.db_path.parent.glob('wayfinder.schema-v1*'))), 1)
        self.assertEqual(Workspace.discover(tree).db_path, self.db_path)
        self.assert_preserved(2)

    def test_every_operation_checks_schema_inside_transaction_before_replay(self):
        self.freeze()
        workspace = Workspace.discover(self.project)
        with contextlib.closing(sqlite3.connect(self.db_path)) as db, db:
            db.execute('PRAGMA user_version=99')
        for envelope in [{'op': 'board.read', 'input': {}}, FIXTURE['replays'][0]['envelope']]:
            result = workspace.operate(envelope)
            self.assertFalse(result['ok'])
            self.assertEqual(result['error']['code'], 'workspace_missing')
        self.assertEqual(self.snapshot(), self.before)

    def test_backup_includes_committed_live_wal_data(self):
        self.freeze()
        with contextlib.closing(sqlite3.connect(self.db_path)) as writer:
            writer.execute('PRAGMA wal_autocheckpoint=0')
            writer.execute("INSERT INTO requests VALUES ('wal-receipt','hash','{}')")
            writer.commit()
            self.before = self.snapshot()
            Workspace.discover(self.project)
            self.assert_preserved(2)
            with contextlib.closing(sqlite3.connect(self.db_path.with_name('wayfinder.schema-v1.sqlite3'))) as backup, backup:
                self.assertEqual(backup.execute("SELECT result FROM requests WHERE id='wal-receipt'").fetchone(), ('{}',))


if __name__ == '__main__':
    unittest.main()
