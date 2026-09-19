#!/usr/bin/env python3
"""Reject false installation evidence without launching any model."""
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'shared/skills/verify-bstack/scripts'))
from installation import successful_read
from codex_hooks import trust_limit


class EvidenceTests(unittest.TestCase):
    project = Path('/tmp/example-project')

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


if __name__ == '__main__':
    unittest.main()
