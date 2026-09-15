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
        self.assertEqual(len(result['physical_file_readback']), 5)
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

    def test_managed_router_refresh_preserves_surrounding_user_text(self):
        _, current = install.cursor_local_rule(self.home, self.source)
        before = (current + '\nUser content stays here.\n').encode()
        desired = current.replace('Require approval of the exact memory change.', 'Require explicit approval of the exact memory change.')
        updated = activation.update_cursor_router(before, desired)
        self.assertEqual(updated, (desired + '\nUser content stays here.\n').encode())
        self.assertEqual(activation.update_cursor_router(updated, desired), updated)


if __name__ == '__main__':
    unittest.main()
