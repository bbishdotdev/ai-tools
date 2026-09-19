import json
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import cursor_context
import cursor_hooks
import cursor_projection
import install
import memory_files
import native_backends
import sync


class CursorContextTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='memory-cursor-context-test-')
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.profile = native_backends.Profile.load(self.home)
        self.hooks = self.home / '.cursor/hooks.json'
        self.bridge = self.home / 'Work/.agents/memory-sync/cursor/MEMORY.md'
        self.projection = self.home / '.cursor/rules/personal-memories.mdc'
        self.note_id = 'temporary-memory-verification'
        self.text = 'My temporary memory verification phrase is amber-otter-42.'

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)

    def activate(self):
        result = subprocess.run([sys.executable, '-B', install.__file__, '--home', str(self.home), '--activate-sync', '--apply'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def files(self):
        return {str(path.relative_to(self.home)): (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.home.rglob('*') if path.is_file() and not path.is_symlink()}

    def plan(self, text):
        return sync.make_plan(self.profile, native_backends.DESTINATIONS, 'set' if text else 'delete', self.note_id, text)

    def save(self, text):
        plan = self.plan(text)
        self.assertEqual(len(plan.changes), 6)
        result = sync.apply_plan(self.profile, plan, plan.digest())
        self.assertIn(result['status'], ['applied', 'unchanged'])
        return result

    def context(self):
        before = self.files()
        command = shlex.split(cursor_hooks.context_hook(self.home)['command'])
        result = subprocess.run(command, input='{"prompt":"DO-NOT-LOG-THIS-PROMPT"}', capture_output=True, text=True, timeout=2)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertNotIn('DO-NOT-LOG-THIS-PROMPT', result.stdout)
        self.assertLessEqual(len(result.stdout.encode()), cursor_context.MAX_OUTPUT_BYTES)
        response = json.loads(result.stdout)
        self.assertIs(response['continue'], True)
        self.assertEqual(self.files(), before)
        return response['additional_context']

    def test_current_context_create_update_delete_and_noop(self):
        self.activate()
        empty = self.context()
        self.assertIn('There are no current synchronized personal-memory notes', empty)
        self.assertIn(memory_files.file_hash(self.bridge.read_bytes()), empty)
        self.save(self.text)
        created = self.context()
        self.assertIn(self.text, created)
        self.assertIn(memory_files.file_hash(self.bridge.read_bytes()), created)
        self.assertNotEqual(empty, created)
        self.assertEqual(self.save(self.text)['status'], 'unchanged')
        self.assertEqual(self.context(), created)
        updated = 'My temporary memory verification phrase is café-pelican-17.\n  Keep spaces.\n'
        self.save(updated)
        current = self.context()
        self.assertNotIn(self.text, current)
        self.assertIn(updated, current)
        self.save(None)
        deleted = self.context()
        self.assertNotIn(updated, deleted)
        self.assertIn('There are no current synchronized personal-memory notes', deleted)
        self.assertIn('supersedes earlier synchronized memory snapshots', deleted)
        self.assertEqual(deleted, empty)

    def test_only_managed_entries_are_supplied(self):
        bridge = 'Private unmanaged bridge prose.\n' + memory_files.block('a-style', 'I prefer café.\n  Exact spaces.\n')
        self.write(self.bridge, bridge)
        self.activate()
        context = self.context()
        self.assertNotIn('Private unmanaged bridge prose', context)
        self.assertIn('I prefer café.\n  Exact spaces.\n', context)
        self.assertEqual(self.bridge.read_text(), bridge)

    def test_missing_drift_malformed_and_hook_errors_invalidate_old_context(self):
        self.activate()
        self.save(self.text)
        originals = {path: path.read_bytes() for path in [self.bridge, self.projection, self.hooks]}
        cases = [
            (self.bridge, None),
            (self.bridge, originals[self.bridge].replace(b'amber-otter-42', b'changed-unsynced')),
            (self.projection, originals[self.projection] + b'Unmanaged collision\n'),
            (self.bridge, b'<!-- memory-sync:broken:begin -->\n'),
            (self.bridge, b'\xff'),
            (self.hooks, b'{broken-json'),
            (self.hooks, None),
        ]
        for path, content in cases:
            with self.subTest(path=path, content=content):
                if content is None:
                    path.unlink()
                else:
                    path.write_bytes(content)
                context = self.context()
                self.assertIn('snapshot unavailable', context)
                self.assertNotIn(self.text, context)
                self.assertIn('Continue unrelated work normally', context)
                path.write_bytes(originals[path])

    def test_oversize_snapshot_is_not_partially_supplied(self):
        self.activate()
        records = {'one': 'First personal fact. ' + '界' * 1300, 'two': 'Second personal fact. ' + '界' * 1300, 'three': 'Third personal fact. ' + '界' * 1300}
        self.bridge.write_text(''.join(memory_files.block(key, body) for key, body in records.items()))
        self.projection.write_bytes(cursor_projection.render_projection(self.bridge.read_bytes(), self.bridge))
        context = self.context()
        self.assertIn('exceeds the hook output limit', context)
        self.assertIn(str(self.bridge), context)
        for body in records.values():
            self.assertNotIn(body[:20], context)

    def test_hooks_preserve_unrelated_entries_backup_and_repair_owned_execution(self):
        expected = cursor_hooks.context_hook(self.home)
        unrelated = {'command': 'another-hook', 'type': 'command', 'timeout': 4, 'extra': {'keep': True}}
        owned = {**expected, 'async': True, 'type': 'prompt', 'prompt': 'Old prompt', 'loop_limit': 1, 'description': 'Keep my description'}
        before = json.dumps({'version': 1, 'custom': {'keep': ['everything']}, 'hooks': {'beforeSubmitPrompt': [unrelated, owned], 'stop': [{'command': 'stop-hook'}]}}).encode()
        self.write(self.hooks, before)
        self.assertFalse(cursor_hooks.inspect_hooks(self.home).ready)
        self.activate()
        after = json.loads(self.hooks.read_bytes())
        self.assertEqual(after['custom'], {'keep': ['everything']})
        self.assertEqual(after['hooks']['stop'], [{'command': 'stop-hook'}])
        self.assertEqual(after['hooks']['beforeSubmitPrompt'], [unrelated, {**owned, **expected}])
        self.assertTrue(cursor_hooks.inspect_hooks(self.home).ready)
        backups = list((self.home / 'Work/.agents/memory-sync/backups').glob('cursor-hook-*.bak'))
        self.assertEqual([path.read_bytes() for path in backups], [before])
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
        snapshot = self.files()
        self.assertIn('Applied 0 file changes.', self.activate().stdout)
        self.assertEqual(snapshot, self.files())

    def test_owned_hook_execution_drift_prevents_ready(self):
        self.activate()
        before = json.loads(self.hooks.read_bytes())
        for key, value in [('type', 'prompt'), ('async', True), ('failClosed', True), ('matcher', 'NeverMatches'), ('loop_limit', 1)]:
            with self.subTest(key=key):
                changed = json.loads(json.dumps(before))
                changed['hooks']['beforeSubmitPrompt'][0][key] = value
                self.hooks.write_text(json.dumps(changed))
                backend = native_backends.cursor_backend(self.profile)
                self.assertFalse(backend.report()['ready'])
                self.assertFalse(backend.report()['context_hook']['configured'])
        self.hooks.write_text(json.dumps(before))
        self.assertTrue(native_backends.cursor_backend(self.profile).report()['ready'])

    def test_malformed_hooks_preflight_does_not_write_native_files(self):
        for content in ['{broken', '[]', '{"version":2}', '{"hooks":{"beforeSubmitPrompt":{}}}']:
            with self.subTest(content=content):
                self.write(self.hooks, content)
                before = self.files()
                result = subprocess.run([sys.executable, '-B', install.__file__, '--home', str(self.home), '--activate-sync', '--apply'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(before, self.files())
                self.assertEqual(list(self.home.iterdir()), [self.home / '.cursor'])

    def test_hooks_are_plan_guards_even_for_unrelated_config_changes(self):
        self.activate()
        plan = self.plan(self.text)
        original = self.hooks.read_bytes()
        self.hooks.write_bytes(original + b'\n')
        before = self.files()
        with self.assertRaisesRegex(memory_files.SyncError, 'State changed after review'):
            sync.apply_plan(self.profile, plan, plan.digest())
        self.assertEqual(self.files(), before)
        fresh = self.plan(self.text)
        self.assertNotEqual(plan.digest(), fresh.digest())
        self.assertEqual(sync.apply_plan(self.profile, fresh, fresh.digest())['status'], 'applied')

    def test_snapshot_race_supplies_no_notes(self):
        self.activate()
        self.save(self.text)
        original_read = cursor_context.read_file
        reads = 0

        def changing_read(path):
            nonlocal reads
            if path == self.bridge:
                reads += 1
                if reads == 2:
                    return b'Changed during verification.\n'
            return original_read(path)

        with patch.object(cursor_context, 'read_file', side_effect=changing_read):
            response = json.loads(cursor_context.snapshot_response(self.profile))
        self.assertIs(response['continue'], True)
        self.assertIn('changed while the snapshot was being read', response['additional_context'])
        self.assertNotIn(self.text, response['additional_context'])


if __name__ == '__main__':
    unittest.main()
