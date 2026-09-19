import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import memory_files
import native_backends
import sync


class NativeSyncTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='native-memory-sync-test-')
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.profile = native_backends.Profile.load(self.home)
        self.codex = self.home / '.codex/memories'
        self.claude = self.home / 'claude-native'
        self.codex.mkdir(parents=True)
        self.claude.mkdir()
        self.profile.claude_home.mkdir()
        self.codex_config = self.profile.codex_home / 'config.toml'
        self.claude_config = self.profile.claude_home / 'settings.json'
        self.codex_config.write_text('[features]\nmemories = true\n')
        self.claude_config.write_text(json.dumps({'autoMemoryEnabled': True, 'autoMemoryDirectory': str(self.claude)}))
        self.note_id = 'temporary-memory-verification'
        self.text = 'My temporary memory verification phrase is silver-owl-24.'
        self.destinations = ('codex', 'claude')
        self.helper = Path(sync.__file__)

    def plan(self, text=None, operation='set', note_id=None):
        return sync.make_plan(self.profile, self.destinations, operation, note_id or self.note_id, self.text if text is None and operation == 'set' else text)

    def apply(self, plan):
        return sync.apply_plan(self.profile, plan, plan.digest())

    def files(self):
        return {str(path.relative_to(self.home)): path.read_bytes() for path in self.home.rglob('*') if path.is_file()}

    def cli(self, *arguments, destinations='codex,claude'):
        result = subprocess.run([sys.executable, '-B', str(self.helper), '--home', str(self.home), '--destinations', destinations, *arguments], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_cli_dry_run_apply_update_delete_and_idempotency(self):
        before = self.files()
        code, preview = self.cli('set', self.note_id, '--text', self.text)
        self.assertEqual(code, 0)
        self.assertEqual(self.files(), before)
        self.assertFalse((self.home / 'Work').exists())
        code, result = self.cli('set', self.note_id, '--text', self.text, '--apply-plan', preview['plan_sha256'])
        self.assertEqual((code, result['status']), (0, 'applied'))
        self.assertTrue(all(item['matches'] for item in result['physical_file_readback']))
        self.assertEqual(sync.inspect(self.profile, self.destinations, self.note_id)['copy_state'], 'consistent')
        no_op = self.plan()
        snapshots = {change.path: change.path.stat().st_mtime_ns for change in no_op.changes}
        self.assertEqual(self.apply(no_op)['status'], 'unchanged')
        self.assertEqual({path: path.stat().st_mtime_ns for path in snapshots}, snapshots)
        updated = self.plan('My temporary memory verification phrase is azure-owl-27.')
        self.assertEqual(self.apply(updated)['status'], 'applied')
        self.assertEqual(sync.inspect(self.profile, self.destinations, self.note_id)['copy_state'], 'consistent')
        self.assertEqual(self.apply(self.plan(operation='delete'))['status'], 'applied')
        self.assertEqual(sync.inspect(self.profile, self.destinations, self.note_id)['copy_state'], 'absent')
        self.assertEqual(self.apply(self.plan(operation='delete'))['status'], 'unchanged')
        self.assertEqual(self.codex_config.read_bytes(), before['.codex/config.toml'])
        self.assertEqual(self.claude_config.read_bytes(), before['.claude/settings.json'])

    def test_default_all_three_fails_before_memory_or_lock_writes(self):
        before = self.files()
        code, result = self.cli('set', self.note_id, '--text', self.text, destinations='codex,claude,cursor')
        self.assertEqual((code, result['status']), (2, 'blocked'))
        self.assertIn('Cursor', result['error'])
        self.assertEqual(self.files(), before)
        self.assertFalse((self.home / 'Work').exists())

    def test_existing_bytes_and_other_managed_notes_survive_delete(self):
        originals = {
            self.codex / 'MEMORY.md': 'Native facts\r\nDo not change café.'.encode(),
            self.codex / 'memory_summary.md': b'v1\r\n\r\nNative summary with no final newline',
            self.claude / 'MEMORY.md': b'# Native index\r\n\r\n- [Existing note](existing.md)',
        }
        for path, content in originals.items():
            path.write_bytes(content)
        self.apply(self.plan())
        self.apply(self.plan('I prefer short replies.', note_id='reply-style'))
        self.apply(self.plan(operation='delete'))
        self.assertEqual(sync.inspect(self.profile, self.destinations, 'reply-style')['copy_state'], 'consistent')
        self.apply(self.plan(operation='delete', note_id='reply-style'))
        for path, content in originals.items():
            self.assertEqual(path.read_bytes(), content)

    def test_plan_edits_exactly_reconstruct_reviewed_bytes(self):
        self.apply(self.plan('I prefer café.'))
        plan = self.plan('I prefer cafés and concise answers.\nUse examples.')
        for change, preview in zip(plan.changes, plan.preview()['changes']):
            edit = preview['edit']
            if edit is None:
                self.assertEqual(change.before, change.after)
                continue
            before = change.before or b''
            offset = edit['byte_offset']
            removed = edit['remove'].encode('utf-8')
            inserted = edit['insert'].encode('utf-8')
            self.assertEqual(before[offset:offset + len(removed)], removed)
            self.assertEqual(before[:offset] + inserted + before[offset + len(removed):], change.after or b'')

    def test_stale_plan_and_configuration_drift_require_review(self):
        plan = self.plan()
        (self.codex / 'MEMORY.md').write_text('A native writer added this.\n')
        before = self.files()
        with self.assertRaisesRegex(memory_files.SyncError, 'State changed'):
            self.apply(plan)
        self.assertEqual({key: value for key, value in self.files().items() if not key.startswith('Work/')}, before)
        plan = self.plan()
        self.codex_config.write_text('[features]\nmemories = true\n[memories]\ngenerate_memories = false\n')
        with self.assertRaisesRegex(memory_files.SyncError, 'State changed'):
            self.apply(plan)

    def test_invalid_configuration_is_fail_closed(self):
        cases = [
            (self.codex_config, 'broken = [', 'Malformed'),
            (self.codex_config, '[features]\nmemories = false\n', 'requires'),
            (self.codex_config, '[features]\nmemories = true\n[memories]\nuse_memories = false\n', 'requires'),
            (self.codex_config, '[features]\nmemories = "true"\n', 'boolean'),
            (self.claude_config, '[]', 'object'),
            (self.claude_config, '{"autoMemoryDirectory":"relative"}', 'absolute'),
            (self.claude_config, json.dumps({'autoMemoryDirectory': str(self.claude), 'autoMemoryEnabled': False}), 'false'),
        ]
        for path, content, message in cases:
            with self.subTest(content=content):
                original = path.read_bytes()
                path.write_text(content)
                with self.assertRaisesRegex(memory_files.SyncError, message):
                    self.plan()
                path.write_bytes(original)
        self.assertFalse((self.home / 'Work').exists())
        self.assertFalse((self.codex / 'MEMORY.md').exists())

    def test_disposable_home_ignores_environment_and_rejects_external_memory(self):
        with patch.dict(os.environ, {'CODEX_HOME': '/not/used', 'CLAUDE_CONFIG_DIR': '/not/used'}):
            profile = native_backends.Profile.load(self.home)
            self.assertEqual(profile, self.profile)
        self.claude_config.write_text(json.dumps({'autoMemoryDirectory': '/tmp/outside-disposable-home'}))
        with self.assertRaisesRegex(memory_files.SyncError, 'inside that disposable home'):
            self.plan()
        report = sync.inspect(self.profile, self.destinations, self.note_id)
        self.assertEqual(report['destinations']['claude']['copies'], [])

    def test_symlink_hardlink_unmanaged_and_malformed_files_are_preserved(self):
        target = self.home / 'unmanaged.md'
        target.write_text('Never replace this.\n')
        path = self.claude / f'memory-sync-{self.note_id}.md'
        cases = [
            lambda: path.symlink_to(target),
            lambda: os.link(target, path),
            lambda: path.write_text('Unmanaged topic.\n'),
            lambda: path.write_bytes(b'\xff'),
            lambda: path.write_text(f'<!-- memory-sync:{self.note_id}:begin -->\n'),
        ]
        for create in cases:
            with self.subTest(create=create):
                create()
                with self.assertRaises(memory_files.SyncError):
                    self.plan()
                self.assertEqual(target.read_text(), 'Never replace this.\n')
                self.assertFalse((self.codex / 'MEMORY.md').exists())
                path.unlink()
        self.claude.rmdir()
        self.claude.symlink_to(self.home / '.codex')
        with self.assertRaisesRegex(memory_files.SyncError, 'safely access'):
            self.plan()

    def test_overlapping_destinations_are_rejected(self):
        self.claude_config.write_text(json.dumps({'autoMemoryDirectory': str(self.codex)}))
        with self.assertRaisesRegex(memory_files.SyncError, 'overlap'):
            self.plan()

    def test_note_validation_and_index_startup_window(self):
        for invalid in ['../note', 'NOTE', '-note', 'a' * 65]:
            with self.assertRaisesRegex(memory_files.SyncError, 'Note id'):
                self.plan(note_id=invalid)
        for invalid in ['', '  ', 'body\x00', '<!-- memory-sync:x:begin -->', 'a' * (native_backends.MAX_NOTE_BYTES + 1)]:
            with self.assertRaises(memory_files.SyncError):
                self.plan(text=invalid)
        original = ('existing index entry\n' * 220).encode()
        (self.claude / 'MEMORY.md').write_bytes(original)
        self.apply(self.plan())
        current = (self.claude / 'MEMORY.md').read_bytes()
        self.assertTrue(current.endswith(original))
        self.assertIn(self.note_id, '\n'.join(current.decode().splitlines()[:200]))
        (self.claude / 'MEMORY.md').write_bytes(b'padding\n' * 200 + current)
        with self.assertRaisesRegex(memory_files.SyncError, 'first-200-line'):
            self.plan()

    def test_native_change_mid_apply_is_preserved_and_retry_converges(self):
        plan = self.plan()
        original_change = memory_files.atomic_change
        called = []
        raced_path = plan.changes[1].path
        native_text = b'v1\nA native writer changed the summary.\n'

        def racing_change(path, before, after):
            called.append(path)
            if len(called) == 2:
                path.write_bytes(native_text)
            original_change(path, before, after)

        with patch.object(sync, 'atomic_change', side_effect=racing_change):
            result = self.apply(plan)
        self.assertEqual(result['status'], 'partial_failure')
        self.assertEqual(len(result['completed_paths']), 1)
        self.assertEqual(raced_path.read_bytes(), native_text)
        self.assertFalse((self.claude / 'MEMORY.md').exists())
        fresh = self.plan()
        self.assertNotEqual(fresh.digest(), plan.digest())
        with self.assertRaisesRegex(memory_files.SyncError, 'digest mismatch'):
            sync.apply_plan(self.profile, fresh, plan.digest())
        self.assertEqual(self.apply(fresh)['status'], 'applied')
        self.assertIn(b'A native writer changed the summary.', raced_path.read_bytes())
        self.assertEqual(sync.inspect(self.profile, self.destinations, self.note_id)['copy_state'], 'consistent')

    def test_configuration_change_mid_apply_stops_before_next_file(self):
        plan = self.plan()
        original_change = memory_files.atomic_change

        def changing_config(path, before, after):
            original_change(path, before, after)
            self.codex_config.write_text('[features]\nmemories = false\n')

        with patch.object(sync, 'atomic_change', side_effect=changing_config):
            result = self.apply(plan)
        self.assertEqual(result['status'], 'partial_failure')
        self.assertEqual(len(result['completed_paths']), 1)
        self.assertIn('configuration changed', result['error'])
        self.assertFalse(plan.changes[1].path.exists())

    def test_final_readback_detects_external_change(self):
        plan = self.plan()
        original_change = memory_files.atomic_change

        def changing_prior_file(path, before, after):
            original_change(path, before, after)
            if path == plan.changes[-1].path:
                plan.changes[0].path.write_text('Native rewrite after our first write.\n')

        with patch.object(sync, 'atomic_change', side_effect=changing_prior_file):
            result = self.apply(plan)
        self.assertEqual(result['status'], 'partial_failure')
        self.assertFalse(result['physical_file_readback'][0]['matches'])

    def test_atomic_failure_cleans_staging_file_and_keeps_original(self):
        path = self.codex / 'MEMORY.md'
        path.write_bytes(b'Original\n')
        with patch.object(memory_files.os, 'replace', side_effect=OSError('simulated replace failure')):
            with self.assertRaisesRegex(memory_files.SyncError, 'safely access'):
                memory_files.atomic_change(path, b'Original\n', b'Replacement\n')
        self.assertEqual(path.read_bytes(), b'Original\n')
        self.assertFalse(list(self.codex.glob('.memory-sync-*.tmp')))

    def test_lock_and_restrictive_file_permissions(self):
        with memory_files.sync_lock(self.home):
            with self.assertRaisesRegex(memory_files.SyncError, 'Another memory-sync'):
                with memory_files.sync_lock(self.home):
                    self.fail('Concurrent lock unexpectedly acquired')
        plan = self.plan()
        self.apply(plan)
        for change in plan.changes:
            self.assertEqual(stat.S_IMODE(change.path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.home / 'Work/.agents/memory-sync/lock').stat().st_mode), 0o600)

    def test_inspect_detects_native_copy_drift_without_propagating_it(self):
        self.apply(self.plan())
        path = self.codex / 'MEMORY.md'
        path.write_text(path.read_text().replace('silver-owl-24', 'native-owl-51'))
        before = self.files()
        report = sync.inspect(self.profile, self.destinations, self.note_id)
        self.assertEqual(report['copy_state'], 'drift')
        self.assertTrue(report['observed_drift'])
        self.assertEqual(self.files(), before)


if __name__ == '__main__':
    unittest.main()
