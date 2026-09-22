import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wayfinder.core import Workspace
from wayfinder.server import create_server


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.workspace = Workspace.initialize(self.project)
        self.start_server()

    def tearDown(self):
        self.stop_server()
        self.temporary.cleanup()

    def start_server(self):
        self.server = create_server(self.workspace, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.origin = f'http://127.0.0.1:{self.server.server_address[1]}'
        status, body = self.request('GET', '/api/bootstrap')
        self.assertEqual(status, 200)
        self.token = json.loads(body)['token']

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive())

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=3)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            return response.status, response.read().decode()
        finally:
            connection.close()

    def operation(self, op, value, **overrides):
        document = {'op': op, 'input': value}
        if not op.endswith(('.read', '.search')):
            document.update(requestId=str(uuid.uuid4()), actor={'kind': 'human', 'id': 'http-test'})
        document.update(overrides)
        status, body = self.request('POST', '/api/operation', json.dumps(document), {
            'Content-Type': 'application/json', 'Origin': self.origin, 'X-Wayfinder-Token': self.token,
        })
        return status, json.loads(body)

    def cli(self, document):
        result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'cli.py'),
                                 '--project', str(self.project), 'call'], input=json.dumps(document),
                                text=True, capture_output=True, timeout=8)
        return result.returncode, json.loads(result.stdout)

    def create_map(self):
        status, result = self.operation('map.create', {
            'title': 'Persistent map', 'destination': 'Resume after restart', 'scope': 'HTTP verification',
        })
        self.assertEqual(status, 200, result)
        self.assertTrue(result['ok'])
        return result['value']['map']

    def test_http_create_cli_read_and_restart(self):
        created = self.create_map()
        code, result = self.cli({'op': 'map.read', 'input': {'mapId': created['id']}})
        self.assertEqual(code, 0, result)
        self.assertEqual(result['value']['map']['title'], 'Persistent map')
        self.stop_server()
        self.workspace = Workspace.discover(self.project)
        self.start_server()
        status, result = self.operation('workspace.read', {})
        self.assertEqual(status, 200)
        self.assertEqual([value['id'] for value in result['value']['maps']], [created['id']])

    def test_cli_edit_conflicts_with_old_browser_revision(self):
        map_value = self.create_map()
        status, result = self.operation('question.create', {
            'mapId': map_value['id'], 'title': 'Choose storage', 'body': 'Original', 'method': 'research',
        })
        self.assertEqual(status, 200, result)
        question = result['value']['question']
        code, edited = self.cli({
            'op': 'question.update', 'requestId': 'cli-edit', 'actor': {'id': 'cli-user', 'kind': 'human'},
            'input': {'questionId': question['id'], 'expectedRev': question['rev'], 'patch': {'body': 'Saved through CLI'}},
        })
        self.assertEqual(code, 0, edited)
        status, conflict = self.operation('question.update', {
            'questionId': question['id'], 'expectedRev': question['rev'], 'patch': {'body': 'Stale browser draft'},
        })
        self.assertEqual(status, 409, conflict)
        self.assertEqual(conflict['error']['code'], 'conflict')
        status, current = self.operation('question.read', {'questionId': question['id']})
        self.assertEqual(status, 200)
        self.assertEqual(current['value']['question']['body'], 'Saved through CLI')

    def test_bootstrap_rejects_foreign_origin_host_and_fetch_site(self):
        for headers in [{'Origin': 'https://unrelated.example'}, {'Host': 'unrelated.example'},
                        {'Sec-Fetch-Site': 'cross-site'}]:
            with self.subTest(headers=headers):
                status, body = self.request('GET', '/api/bootstrap', headers=headers)
                self.assertEqual(status, 403, body)
                self.assertNotIn(self.token, body)

    def test_mutation_requires_all_origin_token_and_json_conditions(self):
        document = json.dumps({'op': 'map.create', 'requestId': 'forged',
                               'actor': {'id': 'outside', 'kind': 'human'},
                               'input': {'title': 'Unwanted', 'destination': 'Bad', 'scope': 'Bad'}})
        valid = {'Origin': self.origin, 'X-Wayfinder-Token': self.token, 'Content-Type': 'application/json'}
        for missing in ['Origin', 'X-Wayfinder-Token']:
            headers = {key: value for key, value in valid.items() if key != missing}
            with self.subTest(missing=missing):
                status, body = self.request('POST', '/api/operation', document, headers)
                self.assertEqual(status, 403, body)
        for patch in [{'Origin': 'https://unrelated.example'}, {'X-Wayfinder-Token': 'wrong'},
                      {'X-Wayfinder-Token': '\u00e9'},
                      {'Content-Type': 'text/plain'}]:
            with self.subTest(patch=patch):
                status, _ = self.request('POST', '/api/operation', document, {**valid, **patch})
                self.assertIn(status, [400, 403, 415])
        _, result = self.operation('workspace.read', {})
        self.assertEqual(result['value']['maps'], [])

    def test_malformed_and_oversized_payloads_are_rejected(self):
        headers = {'Origin': self.origin, 'X-Wayfinder-Token': self.token, 'Content-Type': 'application/json'}
        for body in ['{broken', '[]', 'null', '"not an operation"']:
            with self.subTest(size=len(body)):
                status, _ = self.request('POST', '/api/operation', body, headers)
                self.assertIn(status, [400, 413])
        status, _ = self.request('POST', '/api/operation', '', {
            **headers, 'Content-Length': str(2 * 1024 * 1024),
        })
        self.assertIn(status, [400, 413])
        status, result = self.operation('workspace.read', {})
        self.assertEqual(status, 200)
        self.assertEqual(result['value']['maps'], [])

    def test_static_allowlist_does_not_serve_workspace_or_source(self):
        secret = 'private-workspace-file-cannot-be-served'
        (self.project / 'private.md').write_text(secret)
        for path in ['/private.md', '/../private.md', '/%2e%2e/private.md', '/cli.py', '/cli.py?map=example', '/.bstack/workspace/wayfinder.sqlite3']:
            with self.subTest(path=path):
                status, body = self.request('GET', path)
                self.assertEqual(status, 404)
                self.assertNotIn(secret, body)
        status, body = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertIn('<div id="root">', body)
        deep_status, deep_body = self.request('GET', '/?map=example&view=atlas&item=example')
        self.assertEqual(deep_status, 200)
        self.assertEqual(deep_body, body)

    def test_restart_revokes_browser_token_but_preserves_workspace(self):
        created = self.create_map()
        previous_token = self.token
        self.stop_server()
        self.start_server()
        self.assertNotEqual(previous_token, self.token)
        status, _ = self.request('POST', '/api/operation', '{"op":"workspace.read","input":{}}', {
            'Origin': self.origin, 'Content-Type': 'application/json', 'X-Wayfinder-Token': previous_token,
        })
        self.assertEqual(status, 403)
        _, result = self.operation('workspace.read', {})
        self.assertEqual(result['value']['maps'][0]['id'], created['id'])


if __name__ == '__main__':
    unittest.main()
