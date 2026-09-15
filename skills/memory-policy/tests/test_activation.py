import contextlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import activation
import cursor_projection
import install
import memory_files
import native_backends
import sync
import status


class ActivationTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='memory-sync-activation-test-')
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.profile = native_backends.Profile.load(self.home)
        self.source = Path(install.__file__).resolve().parents[3]
        self.codex_config = self.home / '.codex/config.toml'
        self.claude_config = self.home / '.claude/settings.json'
        self.router = self.home / '.cursor/rules/memory-policy.mdc'
        self.note_id = 'temporary-memory-verification'
        self.text = 'My temporary memory verification phrase is lilac-wren-12.'

    def write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode() if isinstance(content, str) else content)

    def files(self):
        return {str(path.relative_to(self.home)): path.read_bytes() for path in self.home.rglob('*') if path.is_file() and not path.is_symlink()}

    def installer(self, apply=False):
        command = [sys.executable, '-B', str(Path(install.__file__)), '--home', str(self.home), '--activate-sync']
        return subprocess.run(command + (['--apply'] if apply else []), capture_output=True, text=True)

    def activate(self):
        result = self.installer(apply=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def plan(self, text=None, operation='set'):
        return sync.make_plan(self.profile, native_backends.DESTINATIONS, operation, self.note_id, self.text if text is None and operation == 'set' else text)

    def apply(self, plan):
        return sync.apply_plan(self.profile, plan, plan.digest())

    def test_activation_preview_is_read_only_and_apply_is_idempotent(self):
        preview = self.installer()
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertEqual(list(self.home.iterdir()), [])
        self.activate()
        available = native_backends.backends(self.profile)
        self.assertTrue(all(backend.error is None for backend in available.values()), available)
        self.assertEqual(available['cursor'].report()['storage_kind'], 'file-bridge')
        self.assertIsNone(available['cursor'].report()['native_directory'])
        self.assertEqual(sync.inspect(self.profile, native_backends.DESTINATIONS, self.note_id)['copy_state'], 'absent')
        before = self.files()
        timestamps = {name: (self.home / name).stat().st_mtime_ns for name in before}
        rerun = self.activate()
        self.assertIn('Applied 0 file changes.', rerun.stdout)
        self.assertEqual(self.files(), before)
        self.assertEqual({name: (self.home / name).stat().st_mtime_ns for name in before}, timestamps)

    def test_existing_settings_native_memories_and_router_extras_are_preserved(self):
        codex = '# Keep this comment\r\nmodel = "example-model"\r\n[features]\r\nmemories = false # existing choice\r\nother = true\r\n[memories]\r\ngenerate_memories = false\r\n[plugins.other]\r\nenabled = true\r\n'
        claude = {'hooks': {'Stop': [{'command': 'keep-me'}]}, 'statusLine': {'type': 'command', 'command': 'status'}, 'modelSettings': {'effort': 'high'}, 'tui': {'theme': 'system'}, 'autoMemoryEnabled': False}
        old_router = native_backends.CURSOR_RULE_HEADER + activation.LEGACY_POLICY
        extra = '\n# My unrelated rule\nKeep this exact extra text.\n'
        self.write(self.codex_config, codex)
        self.write(self.claude_config, json.dumps(claude))
        self.write(self.router, old_router + extra)
        old_project = self.home / '.claude/projects/example/memory/MEMORY.md'
        old_codex = self.home / '.codex/memories/MEMORY.md'
        self.write(old_project, 'Existing project memories.\n')
        self.write(old_codex, 'Existing native Codex memories.\n')
        before = self.files()
        self.activate()
        updated_codex = self.codex_config.read_bytes().decode()
        self.assertEqual(updated_codex, codex.replace('memories = false #', 'memories = true #').replace('[memories]\r\n', '[memories]\r\nuse_memories = true\r\n'))
        parsed = tomllib.loads(updated_codex)
        self.assertFalse(parsed['memories']['generate_memories'])
        updated_claude = json.loads(self.claude_config.read_bytes())
        expected = {**claude, 'autoMemoryEnabled': True, 'autoMemoryDirectory': str(self.home / 'Work/.agents/memory-sync/claude')}
        self.assertEqual(updated_claude, expected)
        self.assertTrue(self.router.read_text().endswith(extra))
        self.assertEqual(old_project.read_text(), 'Existing project memories.\n')
        self.assertEqual(old_codex.read_text(), 'Existing native Codex memories.\n')
        backups = list((self.home / 'Work/.agents/memory-sync/backups').glob('*.bak'))
        self.assertEqual({path.read_bytes() for path in backups}, {before['.codex/config.toml'], before['.claude/settings.json'], before['.cursor/rules/memory-policy.mdc']})
        for path in backups:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertIn('Applied 0 file changes.', self.activate().stdout)

    def test_existing_absolute_claude_directory_is_retained(self):
        existing = self.home / 'existing-claude-memory'
        self.write(existing / 'MEMORY.md', 'An existing index.\n')
        self.write(self.claude_config, json.dumps({'autoMemoryDirectory': str(existing), 'hooks': {'Stop': []}}))
        self.activate()
        self.assertEqual(json.loads(self.claude_config.read_text())['autoMemoryDirectory'], str(existing))
        self.assertEqual((existing / 'MEMORY.md').read_text(), 'An existing index.\n')

    def test_arbitrary_router_and_unsupported_toml_fail_before_mutation(self):
        self.write(self.router, '# My own rule\nDo not replace me.\n')
        before = self.files()
        result = self.installer(apply=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('arbitrary user rules', result.stderr)
        self.assertEqual(self.files(), before)
        self.router.unlink()
        self.write(self.codex_config, 'features = { memories = false }\n')
        before = self.files()
        result = self.installer(apply=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Unsupported TOML', result.stderr)
        self.assertEqual(self.files(), before)
        self.assertFalse((self.home / '.agents/AGENTS.md').exists())

    def test_all_three_create_update_delete_and_bridge_byte_preservation(self):
        self.activate()
        bridge = self.home / 'Work/.agents/memory-sync/cursor/MEMORY.md'
        original = 'Existing bridge prose with café.\r\n'.encode()
        bridge.write_bytes(original)
        result = self.apply(self.plan())
        self.assertEqual(result['status'], 'applied')
        self.assertEqual(len(result['physical_file_readback']), 6)
        self.assertEqual(result['storage_kinds'], {'codex': 'native', 'claude': 'native', 'cursor': 'file-bridge'})
        self.assertEqual(sync.inspect(self.profile, native_backends.DESTINATIONS, self.note_id)['copy_state'], 'consistent')
        self.assertEqual(self.apply(self.plan())['status'], 'unchanged')
        self.apply(self.plan('My temporary memory verification phrase is amber-gull-92.'))
        self.assertEqual(sync.inspect(self.profile, native_backends.DESTINATIONS, self.note_id)['copy_state'], 'consistent')
        self.apply(self.plan(operation='delete'))
        self.assertEqual(bridge.read_bytes(), original)
        self.assertEqual(sync.inspect(self.profile, native_backends.DESTINATIONS, self.note_id)['copy_state'], 'absent')

    def test_cursor_configuration_and_startup_rule_are_plan_guards(self):
        self.activate()
        plan = self.plan()
        self.router.write_text(self.router.read_text() + '\nAn unrelated rule added after review.\n')
        with self.assertRaisesRegex(memory_files.SyncError, 'State changed'):
            self.apply(plan)
        plan = self.plan()
        configuration = self.home / 'Work/.agents/memory-sync/config.json'
        value = json.loads(configuration.read_bytes())
        value['extra'] = 'new configuration value'
        configuration.write_text(json.dumps(value))
        with self.assertRaisesRegex(memory_files.SyncError, 'State changed'):
            self.apply(plan)
        self.router.write_text(self.router.read_text().replace('alwaysApply: true', 'alwaysApply: false'))
        before = self.files()
        with self.assertRaisesRegex(memory_files.SyncError, 'alwaysApply'):
            self.plan()
        self.assertEqual(self.files(), before)

    def test_bridge_drift_is_reported_and_never_auto_propagated(self):
        self.activate()
        self.apply(self.plan())
        bridge = self.home / 'Work/.agents/memory-sync/cursor/MEMORY.md'
        bridge.write_text(bridge.read_text().replace('lilac-wren-12', 'native-wren-99'))
        before = self.files()
        report = sync.inspect(self.profile, native_backends.DESTINATIONS, self.note_id)
        self.assertEqual(report['copy_state'], 'drift')
        self.assertEqual(self.files(), before)

    def test_bridge_path_and_version_validation_and_symlink_preflight(self):
        self.activate()
        configuration = self.home / 'Work/.agents/memory-sync/config.json'
        original = configuration.read_bytes()
        invalid = [
            {'version': True, 'cursor': {'mode': 'file-bridge', 'directory': str(self.home / 'Work/.agents/memory-sync/cursor')}},
            {'version': 1, 'cursor': {'mode': 'native', 'directory': str(self.home / 'Work/.agents/memory-sync/cursor')}},
            {'version': 1, 'cursor': {'mode': 'file-bridge', 'directory': '/tmp/outside-bridge'}},
        ]
        for value in invalid:
            configuration.write_text(json.dumps(value))
            with self.assertRaises(memory_files.SyncError):
                self.plan()
        configuration.write_bytes(original)
        bridge = self.home / 'Work/.agents/memory-sync/cursor/MEMORY.md'
        bridge.unlink()
        bridge.symlink_to(self.codex_config)
        before = self.files()
        with self.assertRaises(memory_files.SyncError):
            self.plan()
        self.assertEqual(self.files(), before)

    def test_status_accepts_router_extras_and_custom_bridge_subdirectory(self):
        directory = self.home / 'Work/.agents/memory-sync/cursor/personal'
        configuration = self.home / 'Work/.agents/memory-sync/config.json'
        self.write(configuration, json.dumps({'version': 1, 'cursor': {'mode': 'file-bridge', 'directory': str(directory)}}))
        self.activate()
        self.router.write_text(self.router.read_text() + '\nAn additional user rule.\n')
        output = io.StringIO()
        environment = {'CODEX_HOME': str(self.profile.codex_home), 'CLAUDE_CONFIG_DIR': str(self.profile.claude_home)}
        with patch.object(Path, 'home', return_value=self.home), patch.dict(os.environ, environment), patch.object(status, 'inspect_codex', return_value={'available': True}), contextlib.redirect_stdout(output):
            status.main()
        report = json.loads(output.getvalue())
        self.assertTrue(report['cursor']['local_policy_rule']['correct'])
        self.assertTrue(report['native_sync']['all_three_ready'])
        self.assertEqual(report['cursor']['synchronization']['directory'], str(directory))

    def test_existing_bridge_notes_are_preloaded_without_unmanaged_text(self):
        bridge = self.home / 'Work/.agents/memory-sync/cursor/MEMORY.md'
        original = ('Unmanaged text must stay out.\n' + memory_files.block('z-style', 'I prefer café.\n  Keep these spaces.\n') + memory_files.block('a-process', 'I prefer concise plans.')).encode()
        self.write(bridge, original)
        self.activate()
        rule = self.home / '.cursor/rules/personal-memories.mdc'
        content = rule.read_bytes()
        self.assertIn(b'alwaysApply: true', content)
        self.assertIn(b'memorySyncVersion: 1', content)
        self.assertIn(b'memorySyncGenerated: cursor-personal-memories', content)
        self.assertNotIn(b'Unmanaged text must stay out.', content)
        records = cursor_projection.projection_records(content, bridge, rule)
        self.assertEqual(records, {'a-process': 'I prefer concise plans.', 'z-style': 'I prefer café.\n  Keep these spaces.\n'})
        self.assertLess(content.index(b'a-process:begin'), content.index(b'z-style:begin'))
        self.assertEqual(bridge.read_bytes(), original)
        self.assertEqual(stat.S_IMODE(rule.stat().st_mode), 0o600)
        self.assertIn('Applied 0 file changes.', self.activate().stdout)

    def test_old_managed_router_is_upgraded_to_direct_recall_without_audits(self):
        _, desired = install.cursor_local_rule(self.home, self.source)
        old_body = (
            f'{native_backends.CURSOR_START}\n'
            'At the start of every new task, read the bridge memory file.\n'
            f'{native_backends.CURSOR_END}\n'
        )
        old = desired[:desired.index(native_backends.CURSOR_START)] + old_body + '\nKeep my extra rule.\n'
        self.write(self.router, old)
        self.activate()
        current = self.router.read_text()
        self.assertIn('already supplied by the always-applied `personal-memories.mdc` rule', current)
        self.assertIn('Answer ordinary recall questions directly', current)
        self.assertIn('without running a memory-policy, status, or compatibility audit', current)
        self.assertNotIn('At the start of every new task, read', current)
        self.assertTrue(current.endswith('\nKeep my extra rule.\n'))

    def test_projection_drift_is_visible_even_when_all_source_copies_match(self):
        self.activate()
        self.apply(self.plan())
        projection = self.home / '.cursor/rules/personal-memories.mdc'
        projection.write_text(projection.read_text().replace('lilac-wren-12', 'stale-wren-15'))
        backend = native_backends.backends(self.profile)['cursor'].report()
        self.assertFalse(backend['ready'])
        self.assertFalse(backend['projection']['current'])
        self.assertEqual(backend['projection']['path'], str(projection))
        report = sync.inspect(self.profile, native_backends.DESTINATIONS, self.note_id)
        self.assertEqual(report['copy_state'], 'drift')
        self.assertTrue(report['observed_drift'])
        self.assertFalse(report['destinations']['cursor']['projection']['current'])
        self.assertEqual(self.apply(self.plan())['status'], 'applied')
        self.assertTrue(native_backends.backends(self.profile)['cursor'].report()['ready'])

    def test_unrelated_projection_or_bridge_drift_blocks_sync_and_activation(self):
        self.activate()
        self.apply(self.plan())
        projection = self.home / '.cursor/rules/personal-memories.mdc'
        bridge = self.home / 'Work/.agents/memory-sync/cursor/MEMORY.md'
        other = sync.make_plan(self.profile, native_backends.DESTINATIONS, 'set', 'reply-style', 'I prefer short replies.')
        self.apply(other)
        projection_before, bridge_before = projection.read_bytes(), bridge.read_bytes()
        for changed in [projection, bridge]:
            changed.write_bytes(changed.read_bytes().replace(b'I prefer short replies.', b'An unapproved unrelated edit.'))
            before = self.files()
            with self.assertRaisesRegex(memory_files.SyncError, 'outside the approved note: reply-style'):
                self.plan('My temporary memory verification phrase is approved-wren-16.')
            self.assertEqual(self.files(), before)
            result = self.installer(apply=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('projection drift', result.stderr)
            self.assertEqual(self.files(), before)
            projection.write_bytes(projection_before)
            bridge.write_bytes(bridge_before)

    def test_missing_projection_requires_explicit_installer_activation(self):
        self.activate()
        self.apply(self.plan())
        projection = self.home / '.cursor/rules/personal-memories.mdc'
        projection.unlink()
        before = self.files()
        with self.assertRaisesRegex(memory_files.SyncError, 'Missing Cursor personal-memory rule'):
            self.plan()
        self.assertEqual(self.files(), before)
        state = native_backends.backends(self.profile)['cursor'].report()
        self.assertFalse(state['ready'])
        self.assertFalse(state['projection']['exists'])
        self.activate()
        self.assertIn(self.text, projection.read_text())
        self.assertEqual(self.apply(self.plan())['status'], 'unchanged')

    def test_projection_collisions_and_malformed_markers_fail_before_writes(self):
        self.activate()
        self.apply(self.plan())
        projection = self.home / '.cursor/rules/personal-memories.mdc'
        bridge = self.home / 'Work/.agents/memory-sync/cursor/MEMORY.md'
        saved_projection, saved_bridge = projection.read_bytes(), bridge.read_bytes()
        cases = [
            (projection, b'# An unrelated user rule\n'),
            (projection, saved_projection + b'<!-- memory-sync:broken:begin -->\n'),
            (projection, saved_projection.replace(b'alwaysApply: true', b'alwaysApply: false')),
            (bridge, saved_bridge + b'<!-- memory-sync:broken:begin -->\n'),
        ]
        for path, content in cases:
            path.write_bytes(content)
            before = self.files()
            with self.assertRaises(memory_files.SyncError):
                self.plan()
            self.assertEqual(self.files(), before)
            result = self.installer(apply=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.files(), before)
            projection.write_bytes(saved_projection)
            bridge.write_bytes(saved_bridge)

    def test_projection_failure_retries_only_the_reviewed_note_for_each_operation(self):
        self.activate()
        projection = self.home / '.cursor/rules/personal-memories.mdc'
        keep = sync.make_plan(self.profile, native_backends.DESTINATIONS, 'set', 'reply-style', 'I prefer short replies.')
        self.apply(keep)
        for operation, text in [('set', self.text), ('set', 'My temporary memory verification phrase is blue-wren-13.'), ('delete', None)]:
            with self.subTest(operation=operation, text=text):
                plan = self.plan(text, operation)
                original_change = memory_files.atomic_change

                def fail_projection(path, before, after):
                    if path == projection:
                        raise OSError('simulated projection write failure')
                    original_change(path, before, after)

                with patch.object(sync, 'atomic_change', side_effect=fail_projection):
                    result = self.apply(plan)
                self.assertEqual(result['status'], 'partial_failure')
                self.assertEqual(len(result['completed_paths']), 5)
                self.assertFalse(result['physical_file_readback'][-1]['matches'])
                fresh = self.plan(text, operation)
                self.assertNotEqual(plan.digest(), fresh.digest())
                with self.assertRaisesRegex(memory_files.SyncError, 'digest mismatch'):
                    sync.apply_plan(self.profile, fresh, plan.digest())
                retried = self.apply(fresh)
                self.assertEqual(retried['completed_paths'], [str(projection)])
                self.assertTrue(all(copy['matches'] for copy in retried['physical_file_readback']))
                self.assertEqual(self.apply(self.plan(text, operation))['status'], 'unchanged')
                self.assertEqual(projection.read_text().count('I prefer short replies.'), 1)
        self.assertNotIn(self.note_id, projection.read_text())

    def test_projection_dependency_catches_a_source_write_after_bridge_apply(self):
        self.activate()
        bridge = self.home / 'Work/.agents/memory-sync/cursor/MEMORY.md'
        projection = self.home / '.cursor/rules/personal-memories.mdc'
        original_projection = projection.read_bytes()
        original_change = memory_files.atomic_change

        def edit_source_after_apply(path, before, after):
            original_change(path, before, after)
            if path == bridge:
                bridge.write_bytes(bridge.read_bytes() + memory_files.block('unapproved-note', 'An unrelated native write.').encode())

        with patch.object(sync, 'atomic_change', side_effect=edit_source_after_apply):
            result = self.apply(self.plan())
        self.assertEqual(result['status'], 'partial_failure')
        self.assertIn('Projection source changed', result['error'])
        self.assertEqual(projection.read_bytes(), original_projection)
        with self.assertRaisesRegex(memory_files.SyncError, 'outside the approved note: unapproved-note'):
            self.plan()

    def test_projection_bytes_are_bound_to_the_reviewed_plan(self):
        self.activate()
        plan = self.plan()
        projection = self.home / '.cursor/rules/personal-memories.mdc'
        bridge = self.home / 'Work/.agents/memory-sync/cursor/MEMORY.md'
        projection.write_bytes(cursor_projection.render_records({self.note_id: 'A changed current value.'}, bridge))
        before = self.files()
        with self.assertRaisesRegex(memory_files.SyncError, 'State changed'):
            self.apply(plan)
        self.assertEqual(self.files(), before)

    def test_managed_router_refresh_preserves_surrounding_user_text(self):
        _, current = install.cursor_local_rule(self.home, self.source)
        before = (current + '\nUser content stays here.\n').encode()
        desired = current.replace('Require approval of the exact memory change.', 'Require explicit approval of the exact memory change.')
        updated = activation.update_cursor_router(before, desired)
        self.assertEqual(updated, (desired + '\nUser content stays here.\n').encode())
        self.assertEqual(activation.update_cursor_router(updated, desired), updated)


if __name__ == '__main__':
    unittest.main()
