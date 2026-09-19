#!/usr/bin/env python3
"""Reject false installation evidence without launching any model."""
import hashlib
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'shared/skills/verify-bstack/scripts'))
import installation
from installation import successful_read, inspect_bundle, inspect_bindings, native_discovery, probe
from codex_hooks import trust_limit


class EvidenceTests(unittest.TestCase):
    project = Path('/tmp/example-project')

    def test_search_exclusions_are_not_forbidden_file_reads(self):
        command = '/usr/bin/bash -lc "cat .bstack/package/shared/unslop/SKILL.md; rg --files -g \'!**/runtime/**\' -g \'!**/verify-bstack/**\'"'
        scrubbed = installation.without_exclusion_globs([command])
        self.assertNotIn('/runtime/', json.dumps(scrubbed))
        self.assertIn('unslop/SKILL.md', json.dumps(scrubbed))
        reads = installation.without_exclusion_globs(['cat .bstack/config.json', 'rg token .bstack/package/runtime/'])
        self.assertIn('.bstack/config.json', json.dumps(reads))
        self.assertIn('/runtime/', json.dumps(reads))

    def test_cursor_search_records_inputs_and_matched_paths_without_source_text(self):
        event = {'type': 'tool_call', 'subtype': 'completed', 'tool_call': {'grepToolCall': {
            'args': {'pattern': 'Bug fix|bug-fix|playbook', 'path': str(self.project / '.bstack'),
                     'glob': '**/*.{md,json,yml,yaml}'},
            'result': {'success': {'workspaceResults': {str(self.project): {'content': {'matches': [
                {'file': '.bstack/config.json', 'matches': [{'lineNumber': 94, 'content': 'managed instruction'}]},
                {'file': '.bstack/package/README.md', 'matches': [
                    {'lineNumber': 5, 'content': 'Do not read turns.sqlite3 or /runtime/ source.'}]}]}}}}}}}}
        accesses = installation.tool_accesses([event])
        self.assertEqual(accesses[0]['input'], event['tool_call']['grepToolCall']['args'])
        self.assertIn('.bstack/config.json', accesses[1]['search_result_paths'])
        self.assertNotIn('turns.sqlite3', json.dumps(accesses))
        self.assertNotIn('/runtime/', json.dumps(accesses))

    def test_glob_filename_listing_is_not_source_content_access(self):
        events = [
            {'type': 'tool_call', 'subtype': 'completed', 'tool_call': {'globToolCall': {
                'args': {'pattern': '**/*'},
                'result': {'success': {'files': ['.bstack/config.json']}}}}},
            {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Glob', 'id': 'glob',
                'input': {'pattern': '**/*'}}]}},
            {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'glob',
                'content': '.bstack/config.json'}]}}]
        self.assertNotIn('.bstack/config.json', json.dumps(installation.tool_accesses(events)))

    def test_grok_json_search_result_extracts_file_matches_without_source_text(self):
        result = {'type': 'GrepSearch', 'stdout': list(b'matched source text'), 'file_matches': [
            {'path': '.bstack/config.json', 'matches': [{'line': 94, 'content': 'managed instruction'}]},
            {'path': '.bstack/package/README.md', 'matches': [
                {'line': 5, 'content': 'Do not read turns.sqlite3 or /runtime/ source.'}]}]}
        events = [
            {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Grep', 'id': 'grep',
                'input': {'path': '.bstack', 'pattern': 'bug-fix'}}]}},
            {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'grep',
                'content': json.dumps(result)}]}}]
        accesses = installation.tool_accesses(events)
        self.assertEqual(accesses[1]['search_result_paths'], ['.bstack/config.json', '.bstack/package/README.md'])
        self.assertNotIn('turns.sqlite3', json.dumps(accesses))
        self.assertNotIn('/runtime/', json.dumps(accesses))

    def test_search_accesses_keep_non_read_inputs_and_drop_negative_globs(self):
        events = [
            {'type': 'item.completed', 'item': {'type': 'command_execution',
                'command': "rg Bug .bstack/config.json -g '!**/runtime/**'"}},
            {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Grep', 'id': 'grep',
                'input': {'path': '.bstack/package/runtime/', 'pattern': 'receipt'}}]}},
            {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'grep',
                'content': '.bstack/config.json:94: managed instruction'}]}},
            {'type': 'tool_call', 'subtype': 'started', 'tool_call': {'grepToolCall': {
                'args': {'path': '.bstack/package/engineering', 'glob': '!**/runtime/**', 'pattern': 'Bug'}}}}]
        accesses = installation.tool_accesses(events)
        self.assertIn('.bstack/config.json', accesses[0]['input'])
        self.assertNotIn('/runtime/', accesses[0]['input'])
        self.assertIn('/runtime/', accesses[1]['input']['path'])
        self.assertEqual(accesses[2]['search_result_paths'], ['.bstack/config.json'])
        self.assertNotIn('glob', accesses[3]['input'])

    def test_cursor_attachment_needs_current_session_completed_event_and_exact_receipt(self):
        event = {'type': 'tool_call', 'subtype': 'completed', 'session_id': 'current', 'tool_call': {
            'hookAdditionalContexts': [{'hookEventName': 'postToolUse',
                'content': 'After-tool verification receipt: abc123.'}]}}
        self.assertTrue(installation.cursor_hook_context_attached([event], 'current', 'abc123'))
        self.assertFalse(installation.cursor_hook_context_attached([event], 'other', 'abc123'))
        self.assertFalse(installation.cursor_hook_context_attached([event], 'current', 'abc12'))
        self.assertFalse(installation.cursor_hook_context_attached([event], 'current', None))
        event['subtype'] = 'started'
        self.assertFalse(installation.cursor_hook_context_attached([event], 'current', 'abc123'))

    def test_read_requires_successful_matching_tool_result(self):
        target = self.project / 'router/WORKFLOW.md'
        call = {'message': {'content': [{'type': 'tool_use', 'id': 'read-1',
                                         'input': {'file_path': str(target)}}]}}
        result = {'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'read-1',
                                           'content': 'inherit-parent', 'is_error': False}]}}
        self.assertFalse(successful_read([call], target, self.project, ['inherit-parent']))
        self.assertTrue(successful_read([call, result], target, self.project, ['inherit-parent']))
        result['message']['content'][0]['is_error'] = True
        self.assertFalse(successful_read([call, result], target, self.project, ['inherit-parent']))

    def test_unrelated_result_or_path_cannot_prove_read(self):
        target = self.project / 'router/WORKFLOW.md'
        call = {'message': {'content': [{'type': 'tool_use', 'id': 'a',
                                         'input': {'file_path': str(target)}}]}}
        result = {'message': {'content': [{'type': 'tool_result', 'tool_use_id': 'b',
                                           'content': 'inherit-parent'}]}}
        self.assertFalse(successful_read([call, result], target, self.project, ['inherit-parent']))
        result['message']['content'][0]['tool_use_id'] = 'a'
        call['message']['content'][0]['input']['file_path'] = '/tmp/elsewhere/WORKFLOW.md'
        self.assertFalse(successful_read([call, result], target, self.project, ['inherit-parent']))

    def test_cursor_read_requires_result_and_content(self):
        target = self.project / 'fixture.txt'
        event = {'type': 'tool_call', 'subtype': 'completed', 'tool_call': {'readToolCall': {
            'args': {'path': str(target)}, 'result': {'error': 'denied'}}}}
        self.assertFalse(successful_read([event], target, self.project, ['nonce']))
        event['tool_call']['readToolCall']['result'] = {'success': {'content': 'nonce'}}
        self.assertTrue(successful_read([event], target, self.project, ['nonce']))

    def test_codex_read_must_name_the_exact_target(self):
        target = self.project / 'router/WORKFLOW.md'
        event = {'type': 'item.completed', 'item': {'type': 'command_execution', 'exit_code': 0,
                 'command': 'cat /tmp/other/WORKFLOW.md', 'aggregated_output': 'inherit-parent'}}
        self.assertFalse(successful_read([event], target, self.project, ['inherit-parent']))
        event['item']['command'] = f"/bin/bash -lc 'cat {target}'"
        self.assertTrue(successful_read([event], target, self.project, ['inherit-parent']))
        event['item']['command'] = 'cat router/WORKFLOW.md'
        self.assertTrue(successful_read([event], target, self.project, ['inherit-parent']))
        event['item']['exit_code'] = 1
        self.assertFalse(successful_read([event], target, self.project, ['inherit-parent']))

    def test_native_discovery_does_not_trust_model_claims(self):
        claim = {'type': 'assistant', 'skills': ['how']}
        self.assertEqual(native_discovery([claim])['status'], 'not_observed')
        native = {'type': 'system', 'subtype': 'init', 'slash_commands': ['how', 'poteto-mode']}
        evidence = native_discovery([claim, native])
        self.assertEqual(evidence['status'], 'observed')
        self.assertEqual(evidence['observations'], [
            {'event': 'system', 'subtype': 'init', 'field': 'slash_commands', 'value': ['how', 'poteto-mode']}])

    def test_empty_hooks_do_not_explain_missing_delivery(self):
        status = {'hooks_list': {'data': [{'cwd': str(self.project), 'hooks': []}]}}
        self.assertIsNone(trust_limit(status, self.project))
        self.assertIsNone(trust_limit({'error': 'untrusted-looking query failure'}, self.project))

    def test_only_matching_native_project_gate_is_a_limit(self):
        layer = {'name': {'type': 'project', 'dotCodexFolder': str(self.project / '.codex')},
                 'hooksFeature': True, 'disabledReason': 'Add this as a trusted project to load hooks.'}
        self.assertIn('project trust', trust_limit({'config_layers': [layer]}, self.project))
        layer['name']['dotCodexFolder'] = '/unrelated/.codex'
        self.assertIsNone(trust_limit({'config_layers': [layer]}, self.project))

    def test_native_hook_trust_is_distinct_from_delivery_failure(self):
        hook = {'sourcePath': str(self.project / '.codex/hooks.json'),
                'eventName': 'user_prompt_submit', 'trustStatus': 'modified'}
        entry = {'cwd': str(self.project), 'hooks': [hook], 'errors': []}
        status = {'hooks_list': {'data': [entry]}}
        self.assertIn('modified', trust_limit(status, self.project))
        hook['trustStatus'] = 'trusted'
        self.assertIsNone(trust_limit(status, self.project))
        hook['trustStatus'] = 'untrusted'
        entry['errors'] = ['invalid hook configuration']
        self.assertIsNone(trust_limit(status, self.project))


class InstalledPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bstack-installed-test-')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.bundle = self.project / '.bstack/package'
        self.bundle.mkdir(parents=True)
        files = {'engineering/how/SKILL.md': '# How\n## Step 1. Assess Complexity\n## Output Format\n',
                 'engineering/poteto-mode/WORKFLOW.md': '## Principles\n## Playbooks\n',
                 'index.json': json.dumps({'upstream_router': 'engineering/poteto-mode/WORKFLOW.md'}),
                 'shared/router/WORKFLOW.md': '## Select and continue\ninherit-parent\n## Capabilities and authorization\n'}
        for name, content in files.items():
            target = self.bundle / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
            target.chmod(0o644)
        self.manifest = {'schema_version': 2, 'name': 'bstack', 'version': 'test',
                         'public_skills': {'how': {'path': 'engineering/how/SKILL.md', 'description': 'Explain code', 'implicit': False}},
                         'entrypoints': {'router': 'shared/router/WORKFLOW.md', 'index': 'index.json'}, 'files': [
                             {'path': name, 'mode': 0o644, 'sha256': hashlib.sha256(content.encode()).hexdigest()}
                             for name, content in files.items()]}
        self.save_manifest()
        self.wrapper = self.project / '.agents/skills/how/SKILL.md'
        self.wrapper.parent.mkdir(parents=True)
        self.wrapper.write_text('---\nname: how\ndisable-model-invocation: true\n---\nRead ' + str(self.bundle / 'engineering/how/SKILL.md'))
        policy = self.wrapper.parent / 'agents/openai.yaml'
        policy.parent.mkdir()
        policy.write_text('policy:\n  allow_implicit_invocation: false\n')
        for directory in ('.claude', '.cursor', '.grok'):
            link = self.project / directory / 'skills/how'
            link.parent.mkdir(parents=True)
            link.symlink_to('../../.agents/skills/how')

    def save_manifest(self):
        (self.bundle / 'manifest.json').write_text(json.dumps(self.manifest))

    def test_canonical_manifest_and_public_bindings_match(self):
        integrity = inspect_bundle(self.bundle)
        self.assertEqual(integrity['hash_failures'], [])
        self.assertEqual(integrity['packaged_public_skills'], ['engineering/how/SKILL.md'])
        bindings = inspect_bindings(self.project, self.bundle, ['codex', 'claude', 'cursor', 'grok'])
        self.assertEqual(bindings['failures'], [])
        self.assertEqual(bindings['filesystem_skill_names'], ['how'])

    def test_wrong_host_link_or_implicit_default_fails(self):
        link = self.project / '.claude/skills/how'
        link.unlink()
        link.symlink_to('../../.agents/skills/missing')
        self.wrapper.write_text(self.wrapper.read_text().replace('invocation: true', 'invocation: false'))
        failures = inspect_bindings(self.project, self.bundle, ['claude'])['failures']
        self.assertIn('invalid public binding: how', failures)
        self.assertIn('invalid host binding: claude/how', failures)

    def test_extra_public_skill_and_mode_change_fail_integrity(self):
        extra = self.bundle / 'engineering/principles/example/SKILL.md'
        extra.parent.mkdir(parents=True)
        extra.write_text('# Internal')
        (self.bundle / 'engineering/how/SKILL.md').chmod(0o755)
        failures = inspect_bundle(self.bundle)['hash_failures']
        self.assertIn('engineering/how/SKILL.md', failures)
        self.assertIn('unlisted: engineering/principles/example/SKILL.md', failures)
        self.assertIn('public skill paths do not match manifest', failures)

    def test_unexpected_internal_binding_is_not_a_public_skill(self):
        extra = self.project / '.agents/skills/bstack-router/SKILL.md'
        extra.parent.mkdir(parents=True)
        extra.write_text('# Router')
        self.assertIn('installed public skill names differ from manifest',
                      inspect_bindings(self.project, self.bundle, ['codex'])['failures'])

    def test_direct_probe_requires_observed_how_and_router_reads(self):
        response = {'type': 'result', 'session_id': 'test-session', 'result': json.dumps({
            'skill': 'how', 'purpose': 'Explain the code architecture.', 'coding_delegate': 'inherit-parent'})}
        stream = [response]
        with patch.object(installation.verify, 'process', return_value=(0, json.dumps(response))):
            result = probe('claude', 'claude', self.project, self.bundle, self.project / 'claim-only', 'direct')
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['installed_how_read'])
        self.assertFalse(result['checks']['installed_router_read'])
        for index, name in enumerate(('engineering/how/SKILL.md', 'shared/router/WORKFLOW.md')):
            target = self.bundle / name
            stream.extend([{'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'id': str(index), 'name': 'Read', 'input': {'file_path': str(target)}}]}},
                {'type': 'user', 'message': {'content': [
                    {'type': 'tool_result', 'tool_use_id': str(index), 'content': target.read_text()}]}}])
        with patch.object(installation.verify, 'process', return_value=(0, '\n'.join(map(json.dumps, stream)))):
            result = probe('claude', 'claude', self.project, self.bundle, self.project / 'actual-reads', 'direct')
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['native_skill_discovery']['status'], 'not_observed')
        target = self.bundle / 'engineering/poteto-mode/WORKFLOW.md'
        upstream_read = [
            {'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'id': 'upstream', 'name': 'Read', 'input': {'file_path': str(target)}}]}},
            {'type': 'user', 'message': {'content': [
                {'type': 'tool_result', 'tool_use_id': 'upstream', 'content': target.read_text()}]}}]
        with patch.object(installation.verify, 'process', return_value=(0, '\n'.join(map(json.dumps, stream + upstream_read)))):
            result = probe('claude', 'claude', self.project, self.bundle, self.project / 'unneeded-router', 'direct')
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['no_upstream_router_read'])
        upstream_read[1]['message']['content'][0]['content'] = '## Principles'
        with patch.object(installation.verify, 'process', return_value=(0, '\n'.join(map(json.dumps, stream + upstream_read)))):
            result = probe('claude', 'claude', self.project, self.bundle, self.project / 'partial-router', 'direct')
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['no_upstream_router_read'])
        stream.append({'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': 'delegate', 'name': 'Task', 'input': {'prompt': 'Explain'}}]}})
        with patch.object(installation.verify, 'process', return_value=(0, '\n'.join(map(json.dumps, stream)))):
            result = probe('claude', 'claude', self.project, self.bundle, self.project / 'delegated', 'direct')
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['no_delegation'])

    def test_search_of_state_is_a_strict_probe_failure(self):
        event = {'type': 'tool_call', 'subtype': 'completed', 'tool_call': {'grepToolCall': {
            'args': {'pattern': 'bug-fix', 'path': str(self.project / '.bstack')},
            'result': {'success': {'workspaceResults': {str(self.project): {'content': {'matches': [
                {'file': '.bstack/config.json', 'matches': [{'lineNumber': 94, 'content': 'managed text'}]}]}}}}}}}}
        with patch.object(installation.verify, 'process', return_value=(0, json.dumps(event))):
            result = probe('cursor', 'cursor', self.project, self.bundle, self.project / 'state-search', 'direct')
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['no_receipt_source_read'])
        self.assertIn('.bstack/config.json', json.dumps(result['tool_accesses']))

    def test_emitted_and_attached_hook_does_not_replace_model_echo(self):
        def process(argv, folder, env, timeout, stdin):
            receipt = 'abc123'
            record = {'host': 'cursor', 'session_id': 'current', 'event': 'postToolUse',
                      'receipt': receipt, 'observed_at_ns': 1, 'turn_id': 'turn-one'}
            (Path(env['BSTACK_VERIFY_DIR']) / 'receipt.json').write_text(json.dumps(record))
            stream = [
                {'type': 'tool_call', 'subtype': 'completed', 'session_id': 'current', 'tool_call': {
                    'hookAdditionalContexts': [{'hookEventName': 'postToolUse',
                        'content': 'After-tool verification receipt: abc123.'}]}},
                {'type': 'result', 'session_id': 'current', 'result': '{"receipt": null}'}]
            return 0, '\n'.join(map(json.dumps, stream))

        with patch.object(installation.verify, 'process', side_effect=process):
            result = probe('cursor', 'cursor', self.project, self.bundle, self.project / 'missing-echo', 'auto-1')
        self.assertTrue(result['hook_emitted'])
        self.assertTrue(result['native_hook_context_attached'])
        self.assertFalse(result['fresh_hook_receipt_delivered'])
        self.assertFalse(result['checks']['current_turn_hook_delivery'])
        self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
