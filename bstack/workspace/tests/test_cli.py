import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'cli.py'


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def run_cli(self, *args, document=None):
        result = subprocess.run([sys.executable, str(CLI), '--project', str(self.project), *args],
                                input=json.dumps(document) if document is not None else '',
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.stderr, '')
        return result.returncode, json.loads(result.stdout)

    def test_init_stdin_file_and_independent_restart(self):
        code, initialized = self.run_cli('init')
        self.assertEqual(code, 0)
        workspace = initialized['value']['workspace']
        document = {'op': 'map.create', 'requestId': 'cli-map', 'actor': {'id': 'owner', 'kind': 'human'},
                    'input': {'title': 'Via CLI', 'destination': 'Persistence', 'scope': 'CLI test'}}
        request = self.project / 'request.json'
        request.write_text(json.dumps(document))
        code, created = self.run_cli('call', '--file', str(request))
        self.assertEqual(code, 0, created)
        code, replay = self.run_cli('call', document=document)
        self.assertEqual(code, 0)
        self.assertEqual(created, replay)
        code, read = self.run_cli('call', document={'op': 'workspace.read', 'input': {}})
        self.assertEqual(code, 0)
        self.assertEqual(read['value']['workspace'], workspace)
        self.assertEqual(len(read['value']['maps']), 1)
        self.assertEqual(read['value']['maps'][0]['title'], 'Via CLI')

    def test_missing_store_and_invalid_json_exit_nonzero_with_json(self):
        code, result = self.run_cli('call', document={'op': 'workspace.read', 'input': {}})
        self.assertEqual(code, 1)
        self.assertEqual(result['error']['code'], 'workspace_missing')
        self.assertFalse((self.project / '.bstack/workspace').exists())
        self.run_cli('init')
        code, result = self.run_cli('call')
        self.assertEqual(code, 1)
        self.assertEqual(result['error']['code'], 'validation')
        request = self.project / 'invalid.json'
        for invalid in ['{"op":"workspace.read","op":"map.create","input":{}}', '{"op":"question.search","input":{"ready":NaN}}', 'null', '{}', 'x' * 300000]:
            request.write_text(invalid)
            code, result = self.run_cli('call', '--file', str(request))
            self.assertEqual(code, 1)
            self.assertEqual(result['error']['code'], 'validation')

    def test_bad_flags_are_json_errors(self):
        code, result = self.run_cli('unknown')
        self.assertEqual(code, 1)
        self.assertEqual(result['error']['code'], 'validation')

    def test_serve_port_zero_emits_startup_record_and_reads_durable_state(self):
        _, initialized = self.run_cli('init')
        process = subprocess.Popen([sys.executable, str(CLI), '--project', str(self.project), 'serve', '--port', '0'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            import selectors
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                self.assertTrue(selector.select(timeout=5), 'Server did not flush its startup record')
            startup = json.loads(process.stdout.readline())
            self.assertEqual(set(startup), {'url', 'workspace'})
            self.assertEqual(startup['workspace'], initialized['value']['workspace'])
            self.assertTrue(startup['url'].startswith('http://127.0.0.1:'))
            connection = http.client.HTTPConnection(startup['url'].removeprefix('http://'), timeout=3)
            try:
                connection.request('GET', '/api/bootstrap')
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read())['workspace'], startup['workspace'])
            finally:
                connection.close()
        finally:
            process.terminate()
            process.wait(timeout=5)
            process.stdout.close()
            self.assertEqual(process.stderr.read(), '')
            process.stderr.close()


if __name__ == '__main__':
    unittest.main()
