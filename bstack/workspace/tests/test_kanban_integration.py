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

CLI = Path(__file__).resolve().parents[1] / 'cli.py'
AUTHORITY = {'kind': 'human', 'decider': 'Fixture owner', 'confirmation': 'Approved fixture scope'}


class KanbanIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.workspace = Workspace.initialize(self.project)
        self.start()

    def start(self):
        self.server = create_server(self.workspace, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive())

    def tearDown(self):
        self.stop()
        self.temporary.cleanup()

    def call(self, op, value=None, via='http', request_id=None):
        envelope = {'op': op, 'input': value or {}}
        if not op.endswith(('.read', '.search')):
            envelope.update(requestId=request_id or str(uuid.uuid4()),
                            actor={'id': 'integration-owner', 'kind': 'human'})
        if via == 'cli':
            result = subprocess.run([sys.executable, str(CLI), '--project', str(self.project), 'call'],
                                    input=json.dumps(envelope), text=True, capture_output=True, timeout=10)
            self.assertIn(result.returncode, (0, 1), result.stderr)
            return json.loads(result.stdout)
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_address[1], timeout=5)
        try:
            connection.request('POST', '/api/operation', json.dumps(envelope), {
                'Content-Type': 'application/json', 'Origin': self.server.origin,
                'X-Wayfinder-Token': self.server.token,
            })
            return json.loads(connection.getresponse().read())
        finally:
            connection.close()

    def success(self, op, value=None, **options):
        result = self.call(op, value, **options)
        self.assertTrue(result['ok'], result)
        return result['value']

    def read_ticket(self, ticket, via='http'):
        return self.success('ticket.read', {'ticketId': ticket['id']}, via=via)['ticket']

    def move(self, ticket, state, **data):
        current = self.read_ticket(ticket)
        return self.success('ticket.transition', {
            'ticketId': ticket['id'], 'expectedRev': current['rev'], 'to': state, **data,
        })['ticket']

    def test_accepted_plan_spec_ticket_and_stale_sources_across_adapters(self):
        mapping = self.success('map.create', {
            'title': 'Checkout', 'destination': 'Local implementation', 'scope': 'Checkout only',
        }, via='cli')['map']
        question = self.success('question.create', {
            'mapId': mapping['id'], 'title': 'Choose storage', 'method': 'grilling',
        })['question']
        question = self.success('question.resolve', {
            'questionId': question['id'], 'expectedRev': question['rev'],
            'answer': {'markdown': 'Use local SQLite', 'authority': AUTHORITY, 'references': []},
        }, via='cli')['question']
        spec = self.success('spec.create', {
            'mapId': mapping['id'], 'title': 'Checkout spec', 'markdown': 'Persist checkout locally.',
            'questionIds': [question['id']],
        })['spec']
        approved = self.success('spec.approve', {
            'specId': spec['id'], 'expectedRev': spec['rev'], 'authority': AUTHORITY,
            'questionSources': [{'questionId': question['id'], 'answerId': question['answer']['id'],
                                 'revision': question['answer']['revision']}],
        }, via='cli')
        ticket = self.success('ticket.create', {
            'mapId': mapping['id'], 'specId': spec['id'], 'title': 'Persist checkout',
            'body': 'Save the checkout through the local store.',
            'acceptanceCriteria': 'Checkout survives process restart.', 'authority': AUTHORITY,
            'labels': ['checkout'],
        })['ticket']
        for state in ['ready', 'in-progress', 'review']:
            ticket = self.move(ticket, state)
        ticket = self.move(ticket, 'done', completion={'markdown': 'Restart check passed.', 'references': []})
        self.assertTrue(ticket['satisfiesDependency'])
        self.stop()
        self.workspace = Workspace.discover(self.project)
        self.start()
        self.assertEqual(self.read_ticket(ticket, via='cli')['completion']['markdown'], 'Restart check passed.')
        current_question = self.success('question.read', {'questionId': question['id']})['question']
        self.success('question.reopen', {
            'questionId': question['id'], 'expectedRev': current_question['rev'],
        }, via='cli')
        stale = self.read_ticket(ticket)
        self.assertEqual(stale['state'], 'done')
        self.assertTrue(stale['needsSourceReview'])
        self.assertFalse(stale['satisfiesDependency'])
        self.assertGreater(stale['rev'], ticket['rev'])
        history = self.success('spec.read', {'specId': spec['id']})
        self.assertFalse(history['spec']['usableApproval'])
        self.assertEqual(history['revisions'][0]['markdown'], approved['revision']['markdown'])

    def test_hidden_cross_map_blocker_and_stale_browser_save(self):
        first_map = self.success('map.create', {'title': 'A', 'destination': 'A', 'scope': 'A'})['map']
        second_map = self.success('map.create', {'title': 'B', 'destination': 'B', 'scope': 'B'})['map']
        tickets = [self.success('ticket.create', {
            'mapId': mapping['id'], 'title': title, 'body': title, 'acceptanceCriteria': 'Checked',
            'authority': AUTHORITY,
        })['ticket'] for title, mapping in [('Prerequisite', first_map), ('Dependent', second_map)]]
        predecessor, dependent = tickets
        self.success('ticket.relationship.add', {
            'kind': 'blocks', 'from': predecessor['id'], 'to': dependent['id'],
            'expectedFromRev': predecessor['rev'], 'expectedToRev': dependent['rev'],
        }, via='cli')
        board = self.success('board.read', {'mapId': second_map['id']})
        self.assertEqual([item['id'] for item in board['tickets']], [dependent['id']])
        self.assertEqual(board['tickets'][0]['blockedBy'], [predecessor['id']])
        dependent = self.read_ticket(dependent)
        denied = self.call('ticket.transition', {
            'ticketId': dependent['id'], 'expectedRev': dependent['rev'], 'to': 'ready',
        })
        self.assertFalse(denied['ok'])
        self.assertEqual(denied['error']['code'], 'not_ready')
        edited = self.success('ticket.update', {
            'ticketId': dependent['id'], 'expectedRev': dependent['rev'], 'patch': {'body': 'CLI saved body'},
        }, via='cli')['ticket']
        conflict = self.call('ticket.update', {
            'ticketId': dependent['id'], 'expectedRev': dependent['rev'], 'patch': {'body': 'Old browser draft'},
        })
        self.assertEqual(conflict['error']['code'], 'conflict')
        self.assertEqual(conflict['error']['current']['body'], edited['body'])

    def test_cross_adapter_exact_request_replay(self):
        data = {'title': 'Created once', 'body': 'Standalone work', 'acceptanceCriteria': 'One ticket',
                'authority': AUTHORITY}
        first = self.call('ticket.create', data, request_id='uncertain-create')
        self.assertTrue(first['ok'], first)
        self.assertEqual(first, self.call('ticket.create', data, via='cli', request_id='uncertain-create'))
        changed = self.call('ticket.create', {**data, 'title': 'Different'}, via='cli', request_id='uncertain-create')
        self.assertEqual(changed['error']['code'], 'request_reused')
        self.assertEqual(len(self.success('board.read')['tickets']), 1)


if __name__ == '__main__':
    unittest.main()
