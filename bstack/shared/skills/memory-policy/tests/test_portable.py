import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import cursor_hooks
import memory_files
import native_backends
import portable
import sync


class PortableMemoryTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='bstack-portable-memory-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.source = self.root / 'project/shared/memory'
        for name, data in portable.payload().items():
            self.write(self.source / ('WORKFLOW.md' if name == 'SKILL.md' else name), data)
        self.script = self.source / 'scripts/portable.py'

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def files(self):
        return {str(path.relative_to(self.home)): ('link', os.readlink(path)) if path.is_symlink() else ('file', path.read_bytes())
                for path in self.home.rglob('*') if path.is_file() or path.is_symlink()}

    def cli(self, command, *args, script=None, env=None, isolated=True):
        argv = [sys.executable, '-B', str(script or self.script), command]
        if isolated:
            argv.extend(['--home', str(self.home)])
        result = subprocess.run([*argv, *args], capture_output=True, text=True, env=env)
        self.assertEqual(result.stderr, '', result.stderr)
        return result.returncode, json.loads(result.stdout)

    def setup_memory(self):
        code, plan = self.cli('setup')
        self.assertEqual(code, 0, plan)
        code, result = self.cli('setup', '--apply-plan', plan['plan_sha256'])
        self.assertEqual(code, 0, result)
        self.assertIn(result['status'], ('applied', 'unchanged'))
        self.profile = native_backends.Profile.load(self.home)
        return result

    def sync_cli(self, *args):
        command = [sys.executable, '-B', str(self.profile.layout.runtime / 'scripts/sync.py'), '--home', str(self.home), *args]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stderr, '')
        return json.loads(result.stdout)

    def save(self, value):
        args = ['set', 'portable-check', '--text', value] if value else ['delete', 'portable-check']
        plan = self.sync_cli(*args)
        result = self.sync_cli(*args, '--apply-plan', plan['plan_sha256'])
        self.assertTrue(all(item['matches'] for item in result['physical_file_readback']), result)
        return result

    def test_preview_is_read_only_and_activation_is_idempotent(self):
        code, report = self.cli('status')
        self.assertEqual((code, report['status']), (0, 'not_installed'))
        code, preview = self.cli('setup')
        self.assertEqual((code, preview['status']), (0, 'plan'))
        self.assertEqual(list(self.home.iterdir()), [])
        self.setup_memory()
        self.assertFalse((self.home / 'Work').exists())
        before = self.files()
        result = self.setup_memory()
        self.assertEqual(result['status'], 'unchanged')
        self.assertEqual(self.files(), before)
        code, report = self.cli('status')
        self.assertEqual((code, report['status']), (0, 'ready'))
        self.assertEqual(report['destinations']['cursor']['storage_kind'], 'file-bridge')
        self.assertEqual(report['native_recall'], 'Not tested; file consistency does not establish fresh-session recall.')

    def test_existing_native_contents_settings_and_global_rules_survive(self):
        phrase = 'PRIVATE EXISTING PERSONAL NOTE'
        codex_native = self.home / '.codex/memories/MEMORY.md'
        claude_directory = self.home / 'existing-claude'
        self.write(codex_native, phrase)
        self.write(claude_directory / 'MEMORY.md', phrase)
        codex = 'model = "other"\n[features]\nmemories = false\n[memories]\ngenerate_memories = false\n'
        self.write(self.home / '.codex/config.toml', codex)
        self.write(self.home / '.claude/settings.json', json.dumps({'autoMemoryDirectory': str(claude_directory), 'autoDreamEnabled': False, 'hooks': {'Stop': [{'command': 'leave-me'}]}}))
        self.write(self.home / '.cursor/hooks.json', json.dumps({'hooks': {'beforeSubmitPrompt': [{'command': 'existing-hook'}]}}))
        self.write(self.home / '.codex/AGENTS.md', 'Existing global instructions.\n')
        code, preview = self.cli('setup')
        self.assertEqual(code, 0, preview)
        self.assertNotIn(phrase, json.dumps(preview))
        self.setup_memory()
        self.assertEqual(codex_native.read_text(), phrase)
        self.assertEqual((claude_directory / 'MEMORY.md').read_text(), phrase)
        native = tomllib.loads((self.home / '.codex/config.toml').read_text())
        self.assertFalse(native['memories']['generate_memories'])
        self.assertEqual(native['model'], 'other')
        claude = json.loads((self.home / '.claude/settings.json').read_text())
        self.assertEqual(claude['autoMemoryDirectory'], str(claude_directory))
        self.assertFalse(claude['autoDreamEnabled'])
        self.assertEqual(claude['hooks']['Stop'], [{'command': 'leave-me'}])
        hooks = json.loads((self.home / '.cursor/hooks.json').read_text())
        self.assertEqual(hooks['hooks']['beforeSubmitPrompt'][0], {'command': 'existing-hook'})
        self.assertTrue((self.home / '.codex/AGENTS.md').read_text().startswith('Existing global instructions.\n'))
        backups = list(self.profile.layout.backups.glob('*.bak'))
        self.assertIn(codex.encode(), [path.read_bytes() for path in backups])
        self.assertNotIn(phrase, json.dumps(self.cli('status')[1]))

    def test_copied_runtime_survives_project_deletion_and_syncs_all_three(self):
        self.setup_memory()
        shutil.rmtree(self.source.parents[1])
        script = self.profile.layout.runtime / 'scripts/portable.py'
        self.assertEqual(self.cli('status', script=script)[1]['status'], 'ready')
        for value in ('Synthetic portable note one.', 'Synthetic portable note two.', None):
            self.save(value)
            inspection = self.sync_cli('inspect', 'portable-check')
            self.assertEqual(inspection['copy_state'], 'consistent' if value else 'absent')
            hook = cursor_hooks.context_hook(self.home)
            result = subprocess.run(shlex.split(hook['command']), input='{"prompt":"irrelevant"}', capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            text = json.loads(result.stdout)['additional_context']
            if value:
                self.assertIn(value, text)
            else:
                self.assertIn('There are no current synchronized personal-memory notes', text)
        self.assertFalse((self.home / 'Work').exists())

    def test_explicit_runtime_update_preserves_notes_and_has_one_hook(self):
        self.setup_memory()
        self.save('A synthetic note retained through an update.')
        roots = [self.profile.codex_home / 'memories', self.profile.layout.claude, self.profile.layout.cursor]
        native = {path: path.read_bytes() for root in roots for path in root.rglob('*.md')}
        self.write(self.source / 'WORKFLOW.md', (self.source / 'WORKFLOW.md').read_text() + '\nA revised installed instruction.\n')
        code, plan = self.cli('setup')
        self.assertEqual(code, 0, plan)
        self.assertTrue(any(change['action'] == 'update' and change['kind'] == 'runtime' for change in plan['changes']))
        self.assertEqual({path: path.read_bytes() for path in native}, native)
        self.setup_memory()
        self.assertEqual({path: path.read_bytes() for path in native}, native)
        self.assertIn('A revised installed instruction.', (self.profile.layout.runtime / 'SKILL.md').read_text())
        hooks = json.loads((self.home / '.cursor/hooks.json').read_text())['hooks']['beforeSubmitPrompt']
        self.assertEqual(len(hooks), 1)
        self.assertEqual(self.sync_cli('inspect', 'portable-check')['copy_state'], 'consistent')

    def test_stale_preview_and_edited_runtime_block_without_mutation(self):
        code, preview = self.cli('setup')
        self.assertEqual(code, 0)
        self.write(self.home / '.codex/config.toml', 'model = "changed-after-preview"\n')
        before = self.files()
        code, result = self.cli('setup', '--apply-plan', preview['plan_sha256'])
        self.assertEqual((code, result['status']), (2, 'blocked'))
        self.assertEqual(self.files(), before)
        self.setup_memory()
        self.write(self.profile.layout.runtime / 'SKILL.md', 'An edited owned skill.\n')
        before = self.files()
        code, result = self.cli('setup')
        self.assertEqual((code, result['status']), (2, 'blocked'))
        self.assertEqual(self.files(), before)

    def test_legacy_installation_is_reported_without_migration(self):
        self.write(self.home / 'Work/.agents/memory-sync/config.json', json.dumps({'version': 1, 'cursor': {'mode': 'file-bridge', 'directory': str(self.home / 'Work/.agents/memory-sync/cursor')}}))
        before = self.files()
        code, result = self.cli('status')
        self.assertEqual((code, result['status']), (0, 'legacy_external'))
        code, result = self.cli('setup')
        self.assertEqual((code, result['status']), (2, 'blocked'))
        self.assertEqual(self.files(), before)
        self.assertFalse((self.home / '.local').exists())

    def test_skill_collision_and_global_instruction_symlink_refused(self):
        destination = self.home / '.agents/skills/memory-policy'
        destination.mkdir(parents=True)
        self.write(destination / 'SKILL.md', 'Unrelated skill.')
        before = self.files()
        self.assertEqual(self.cli('setup')[0], 2)
        self.assertEqual(self.files(), before)
        shutil.rmtree(destination)
        outside = self.root / 'unrelated-policy.md'
        outside.write_text('Never overwrite this.')
        target = self.home / '.codex/AGENTS.md'
        target.parent.mkdir()
        target.symlink_to(outside)
        before = self.files()
        self.assertEqual(self.cli('setup')[0], 2)
        self.assertEqual(outside.read_text(), 'Never overwrite this.')
        self.assertEqual(self.files(), before)

    def test_symlinked_runtime_parent_and_external_claude_directory_refused_in_isolation(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.home / '.local').symlink_to(outside)
        self.assertEqual(self.cli('setup')[0], 2)
        self.assertEqual(list(outside.iterdir()), [])
        (self.home / '.local').unlink()
        self.write(self.home / '.claude/settings.json', json.dumps({'autoMemoryDirectory': str(outside)}))
        before = self.files()
        self.assertEqual(self.cli('setup')[0], 2)
        self.assertEqual(self.files(), before)
        self.assertEqual(list(outside.iterdir()), [])

    def test_isolated_home_ignores_production_environment_overrides(self):
        outside = self.root / 'outside'
        environment = {**os.environ, 'CODEX_HOME': str(outside / 'codex'), 'CLAUDE_CONFIG_DIR': str(outside / 'claude')}
        code, preview = self.cli('setup', env=environment)
        self.assertEqual(code, 0, preview)
        code, result = self.cli('setup', '--apply-plan', preview['plan_sha256'], env=environment)
        self.assertEqual(code, 0, result)
        self.assertFalse(outside.exists())
        self.assertTrue((self.home / '.codex/config.toml').exists())

    def test_native_profile_roots_persist_across_host_environment(self):
        codex = self.home / 'custom-codex'
        claude = self.home / 'custom-claude'
        environment = {**os.environ, 'HOME': str(self.home), 'CODEX_HOME': str(codex), 'CLAUDE_CONFIG_DIR': str(claude)}
        code, preview = self.cli('setup', env=environment, isolated=False)
        self.assertEqual(code, 0, preview)
        code, result = self.cli('setup', '--apply-plan', preview['plan_sha256'], env=environment, isolated=False)
        self.assertEqual(code, 0, result)
        environment.pop('CODEX_HOME')
        environment.pop('CLAUDE_CONFIG_DIR')
        code, status = self.cli('status', env=environment, isolated=False)
        self.assertEqual((code, status['status']), (0, 'ready'))
        self.assertEqual(status['destinations']['codex']['directory'], str(codex / 'memories'))
        self.assertFalse((self.home / '.codex').exists())
        environment['CODEX_HOME'] = str(self.home / 'other-codex')
        before = self.files()
        code, report = self.cli('status', env=environment, isolated=False)
        self.assertEqual((code, report['status']), (2, 'blocked'))
        self.assertIn('CODEX_HOME differs', report['error'])
        self.assertEqual(self.files(), before)

    def test_manifest_destination_changes_invalidate_a_reviewed_sync(self):
        self.setup_memory()
        plan = sync.make_plan(self.profile, native_backends.DESTINATIONS, 'set', 'test-entry', 'Synthetic test.')
        manifest = self.profile.layout.manifest
        data = json.loads(manifest.read_text())
        data['native_homes']['codex'] = str(self.home / 'another-codex')
        manifest.write_text(json.dumps(data))
        before = self.files()
        with self.assertRaises(memory_files.SyncError):
            sync.apply_plan(self.profile, plan, plan.digest())
        self.assertEqual(self.files(), before)

    def test_partial_destination_sync_also_guards_recorded_native_homes(self):
        self.setup_memory()
        plan = sync.make_plan(self.profile, ('codex', 'claude'), 'set', 'test-entry', 'Synthetic test.')
        manifest = self.profile.layout.manifest
        data = json.loads(manifest.read_text())
        data['native_homes']['claude'] = str(self.home / 'another-claude')
        manifest.write_text(json.dumps(data))
        before = self.files()
        with self.assertRaises(memory_files.SyncError):
            sync.apply_plan(self.profile, plan, plan.digest())
        self.assertEqual(self.files(), before)

    def test_production_external_native_homes_work_in_registered_cursor_hook(self):
        external = self.root / 'external-native'
        environment = {**os.environ, 'HOME': str(self.home), 'CODEX_HOME': str(external / 'codex'), 'CLAUDE_CONFIG_DIR': str(external / 'claude')}
        code, plan = self.cli('setup', env=environment, isolated=False)
        self.assertEqual(code, 0, plan)
        code, result = self.cli('setup', '--apply-plan', plan['plan_sha256'], env=environment, isolated=False)
        self.assertEqual(code, 0, result)
        hook = json.loads((self.home / '.cursor/hooks.json').read_text())['hooks']['beforeSubmitPrompt'][0]
        other_host = {**os.environ, 'HOME': str(self.root / 'different-host-home'), 'CODEX_HOME': str(self.root / 'another-codex')}
        response = subprocess.run(shlex.split(hook['command']), env=other_host, capture_output=True, text=True)
        self.assertEqual(response.returncode, 0, response.stderr)
        self.assertIn('There are no current synchronized personal-memory notes', json.loads(response.stdout)['additional_context'])
        self.assertFalse((self.root / 'different-host-home').exists())
        self.assertFalse((self.root / 'another-codex').exists())
        code, result = self.cli('status')
        self.assertEqual(code, 2, result)
        self.assertIn('inside the disposable home', result['error'])

    def test_setup_preview_omits_unrelated_configuration_secrets(self):
        secret = 'UNRELATED-PRIVATE-CONFIGURATION'
        self.write(self.home / '.claude/settings.json', json.dumps({'custom': secret, 'autoMemoryEnabled': False}))
        self.write(self.home / '.cursor/hooks.json', json.dumps({'hooks': {'beforeSubmitPrompt': [{'command': 'custom-hook --secret ' + secret}]}}))
        code, preview = self.cli('setup')
        self.assertEqual(code, 0, preview)
        self.assertNotIn(secret, json.dumps(preview))
        hook = next(change for change in preview['changes'] if 'managed_hook' in change)
        self.assertIn('cursor_context.py', hook['managed_hook']['command'])
        self.assertEqual(hook['managed_hook']['event'], 'beforeSubmitPrompt')

    def test_initial_setup_failure_rolls_back_then_retries(self):
        profile = native_backends.Profile.load(self.home, portable=True)
        plan = portable.make_plan(profile, self.source)
        original = portable.atomic_change

        for failure in (OSError('simulated policy write failure'), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__):
                def fail_policy(path, before, after):
                    if path == self.home / '.agents/AGENTS.md' and after is not None:
                        raise failure
                    return original(path, before, after)

                with patch.object(portable, 'atomic_change', side_effect=fail_policy):
                    report = portable.apply_plan(plan, plan.digest())
                self.assertEqual(report['status'], 'rolled_back', report)
                self.assertFalse(profile.layout.manifest.exists())
                self.assertFalse(profile.layout.runtime.exists())
        self.setup_memory()
        self.assertEqual(self.cli('status')[1]['status'], 'ready')

    def test_update_stage_and_post_publish_failures_preserve_old_runtime_and_notes(self):
        self.setup_memory()
        self.save('A synthetic note surviving installer failures.')
        installed = self.profile.layout.manifest.read_bytes()
        runtime = {path: path.read_bytes() for path in self.profile.layout.runtime.rglob('*') if path.is_file()}
        native = {change.path: change.before for change in sync.make_plan(self.profile, native_backends.DESTINATIONS, 'set', 'portable-check', 'A synthetic note surviving installer failures.').changes}
        self.write(self.source / 'WORKFLOW.md', (self.source / 'WORKFLOW.md').read_text() + '\nRevised source.\n')
        original = portable.atomic_change
        copied = []

        def fail_second_stage(path, before, after):
            if any(part.startswith('.runtime-stage-') for part in path.parts):
                copied.append(path)
                if len(copied) == 2:
                    raise OSError('simulated stage failure')
            return original(path, before, after)

        plan = portable.make_plan(self.profile, self.source)
        with patch.object(portable, 'atomic_change', side_effect=fail_second_stage):
            result = portable.apply_plan(plan, plan.digest())
        self.assertEqual(result['status'], 'rolled_back', result)
        self.assertEqual(self.profile.layout.manifest.read_bytes(), installed)
        self.assertEqual({path: path.read_bytes() for path in runtime}, runtime)
        config_path = self.home / '.codex/config.toml'
        config_path.write_text(config_path.read_text().replace('memories = true', 'memories = false'))
        plan = portable.make_plan(self.profile, self.source)

        def fail_after_swap(path, before, after):
            if path == config_path and after != before:
                raise OSError('simulated config failure')
            return original(path, before, after)

        with patch.object(portable, 'atomic_change', side_effect=fail_after_swap):
            result = portable.apply_plan(plan, plan.digest())
        self.assertEqual(result['status'], 'rolled_back', result)
        self.assertEqual(self.profile.layout.manifest.read_bytes(), installed)
        self.assertEqual({path: path.read_bytes() for path in runtime}, runtime)
        self.assertEqual({path: path.read_bytes() for path in native}, native)
        self.setup_memory()
        self.assertEqual(self.cli('status')[1]['status'], 'ready')

    def test_rollback_preserves_concurrent_configuration_change(self):
        profile = native_backends.Profile.load(self.home, portable=True)
        plan = portable.make_plan(profile, self.source)
        original = portable.atomic_change
        target = self.home / '.codex/AGENTS.md'
        injected = False

        def concurrent_edit(path, before, after):
            nonlocal injected
            result = original(path, before, after)
            if path == target and not injected:
                injected = True
                path.write_text(path.read_text() + '\nConcurrent user edit.\n')
                raise OSError('simulated error after concurrent edit')
            return result

        with patch.object(portable, 'atomic_change', side_effect=concurrent_edit):
            result = portable.apply_plan(plan, plan.digest())
        self.assertEqual(result['status'], 'partial_failure')
        self.assertTrue(result['rollback_errors'])
        self.assertIn('Concurrent user edit.', target.read_text())

    def test_native_destinations_cannot_overlap_replaceable_runtime_or_state(self):
        root = self.home / '.local/share/bstack/memory'
        for directory in (root / 'runtime', root / 'runtime/nested', root / 'state', root / 'state/cursor'):
            with self.subTest(directory=directory):
                self.write(self.home / '.claude/settings.json', json.dumps({'autoMemoryDirectory': str(directory)}))
                before = self.files()
                code, report = self.cli('setup')
                self.assertEqual((code, report['status']), (2, 'blocked'))
                self.assertEqual(self.files(), before)
        (self.home / '.claude/settings.json').unlink()
        environment = {**os.environ, 'HOME': str(self.home), 'CODEX_HOME': str(root / 'runtime'), 'CLAUDE_CONFIG_DIR': str(self.home / '.claude')}
        before = self.files()
        code, report = self.cli('setup', env=environment, isolated=False)
        self.assertEqual((code, report['status']), (2, 'blocked'))
        self.assertEqual(self.files(), before)


if __name__ == '__main__':
    unittest.main()
