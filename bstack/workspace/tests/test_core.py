import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wayfinder.core import DomainError, LEASE_SECONDS, SCHEMA_VERSION, Workspace

CLI = Path(__file__).resolve().parents[1] / 'cli.py'
HUMAN = {'id': 'owner', 'kind': 'human'}
AGENT = {'id': 'worker', 'kind': 'agent'}


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.workspace = Workspace.initialize(self.project)
        self.mapping = self.write('map.create', title='Ship it', destination='Working planner', scope='First slice')['map']

    def tearDown(self):
        self.temporary.cleanup()

    def call(self, op, data=None, actor=HUMAN, request_id=None):
        document = {'op': op, 'input': data or {}}
        if op not in {'workspace.read', 'map.read', 'question.read', 'question.search'}:
            document.update(actor=actor, requestId=request_id or str(uuid.uuid4()))
        return self.workspace.operate(document)

    def write(self, op, actor=HUMAN, request_id=None, **data):
        result = self.call(op, data, actor, request_id)
        self.assertTrue(result['ok'], result)
        return result['value']

    def question(self, title='Question', **data):
        return self.write('question.create', mapId=self.mapping['id'], title=title, method='research', **data)['question']

    def read(self, question):
        return self.call('question.read', {'questionId': question['id']})['value']['question']

    def map(self):
        return self.call('map.read', {'mapId': self.mapping['id']})['value']['map']

    def connect(self, source, target, kind='blocks', remove=False):
        return self.write('relationship.remove' if remove else 'relationship.add', mapId=self.mapping['id'],
                          expectedMapRev=self.map()['rev'], kind=kind, **{'from': source['id'], 'to': target['id']})

    def change(self, op, question, **data):
        current = self.read(question)
        return self.write(op, questionId=question['id'], expectedRev=current['rev'], **data)['question']

    def resolve(self, question, **kwargs):
        return self.change('question.resolve', question, answer={
            'markdown': 'Accepted decision', 'authority': {'kind': 'human', 'decider': 'Owner', 'confirmation': 'Agreed here'},
            'references': ['README.md'],
        }, **kwargs)

    def error(self, result, code):
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], code, result)

    def test_restart_preserves_records_and_schema(self):
        question = self.resolve(self.question(body='Body', labels=['planning']))
        before = self.call('map.read', {'mapId': self.mapping['id']})
        self.workspace = Workspace.discover(self.project)
        self.assertEqual(before, self.call('map.read', {'mapId': self.mapping['id']}))
        self.assertEqual(question, self.read(question))
        with sqlite3.connect(self.workspace.db_path) as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], SCHEMA_VERSION)
            self.assertGreater(db.execute('SELECT COUNT(*) FROM history').fetchone()[0], 1)

    def test_request_replay_covers_create_resolve_and_failures(self):
        document = dict(mapId=self.mapping['id'], title='Exactly once', method='research')
        first = self.call('question.create', document, request_id='create-once')
        self.assertEqual(first, self.call('question.create', document, request_id='create-once'))
        self.error(self.call('question.create', {**document, 'title': 'Different'}, request_id='create-once'), 'request_reused')
        question = first['value']['question']
        resolve = dict(questionId=question['id'], expectedRev=question['rev'], answer={
            'markdown': 'Final', 'authority': {'kind': 'delegated', 'decider': 'Worker', 'scope': 'Storage choice', 'grantReference': 'User instruction'}, 'references': []})
        resolved = self.call('question.resolve', resolve, request_id='resolve-once')
        self.assertTrue(resolved['ok'], resolved)
        self.assertEqual(resolved, self.call('question.resolve', resolve, request_id='resolve-once'))
        self.assertEqual(len(self.call('question.read', {'questionId': question['id']})['value']['answers']), 1)
        stale = self.call('question.update', {'questionId': question['id'], 'expectedRev': 1, 'patch': {'body': 'stale'}}, request_id='failure-once')
        self.error(stale, 'conflict')
        self.change('question.reopen', question)
        self.assertEqual(stale, self.call('question.update', {'questionId': question['id'], 'expectedRev': 1, 'patch': {'body': 'stale'}}, request_id='failure-once'))

    def test_stale_edits_do_not_overwrite_and_map_revisions_advance(self):
        question = self.question()
        old_map = self.map()
        current = self.change('question.update', question, patch={'body': 'Saved body', 'labels': ['one'], 'priority': 4})
        self.assertGreater(self.map()['rev'], old_map['rev'])
        stale = self.call('question.update', {'questionId': question['id'], 'expectedRev': question['rev'], 'patch': {'body': 'stale'}})
        self.error(stale, 'conflict')
        self.assertEqual(stale['error']['current'], current)
        self.error(self.call('map.update', {'mapId': old_map['id'], 'expectedRev': old_map['rev'], 'patch': {'title': 'stale'}}), 'conflict')

    def test_empty_ready_set_and_unknown_areas_do_not_mean_complete(self):
        self.assertFalse(self.map()['complete'])
        self.resolve(self.question())
        self.assertTrue(self.map()['complete'])
        mapping = self.map()
        self.write('map.update', mapId=mapping['id'], expectedRev=mapping['rev'], patch={'unresolved': 'Unknown area remains'})
        self.assertFalse(self.map()['complete'])

    def test_diamond_readiness_and_answer_prerequisite_revisions(self):
        a, b, c, d = [self.question(name) for name in 'ABCD']
        for source, target in [(a, b), (a, c), (b, d), (c, d)]:
            self.connect(source, target)
        self.assertEqual(self.read(b)['status'], 'Blocked')
        self.assertEqual({q['id'] for q in self.call('question.search', {'ready': True})['value']['questions']}, {a['id']})
        a = self.resolve(a)
        self.assertEqual({q['id'] for q in self.call('question.search', {'ready': True})['value']['questions']}, {b['id'], c['id']})
        b = self.resolve(b)
        self.assertFalse(self.read(d)['ready'])
        c = self.resolve(c)
        d = self.resolve(d)
        self.assertEqual(d['answer']['prerequisites'], sorted([
            {'questionId': b['id'], 'answerId': b['answer']['id'], 'revision': 1},
            {'questionId': c['id'], 'answerId': c['answer']['id'], 'revision': 1},
        ], key=lambda entry: entry['questionId']))
        self.assertTrue(self.map()['complete'])

    def test_independent_graph_cycles_normalization_and_invalid_endpoints(self):
        a, b, c = [self.question(name) for name in 'ABC']
        self.connect(a, b)
        self.connect(b, c)
        self.connect(c, b, 'parent')
        for kind, source, target, code in [('blocks', c, a, 'cycle'), ('parent', b, c, 'cycle'),
                                           ('blocks', a, b, 'validation'), ('related', a, a, 'validation')]:
            before = self.call('map.read', {'mapId': self.mapping['id']})
            result = self.call('relationship.add', {'mapId': self.mapping['id'], 'expectedMapRev': self.map()['rev'], 'kind': kind, 'from': source['id'], 'to': target['id']})
            self.error(result, code)
            self.assertEqual(before, self.call('map.read', {'mapId': self.mapping['id']}))
        self.connect(b, a, 'related')
        self.error(self.call('relationship.add', {'mapId': self.mapping['id'], 'expectedMapRev': self.map()['rev'], 'kind': 'related', 'from': a['id'], 'to': b['id']}), 'validation')
        self.connect(a, b, 'related', remove=True)
        other = self.write('map.create', title='Other', destination='Other', scope='Other')['map']
        foreign = self.write('question.create', mapId=other['id'], title='Foreign', method='research')['question']
        for target, code in [(foreign['id'], 'validation'), ('missing', 'not_found')]:
            self.error(self.call('relationship.add', {'mapId': self.mapping['id'], 'expectedMapRev': self.map()['rev'], 'kind': 'blocks', 'from': a['id'], 'to': target}), code)

    def test_reopening_invalidates_transitive_work_and_history_is_immutable(self):
        a, b, c = [self.question(name) for name in 'ABC']
        self.connect(a, b)
        self.connect(b, c)
        a, b, c = self.resolve(a), self.resolve(b), self.resolve(c)
        self.change('question.reopen', a)
        for question in [b, c]:
            current = self.read(question)
            self.assertEqual(current['state'], 'needs-review')
            self.assertIsNone(current['answer'])
            self.assertGreater(current['rev'], question['rev'])
        previous = self.read(c)
        self.change('question.reopen', a)
        self.assertGreater(self.read(c)['rev'], previous['rev'])
        self.resolve(a)
        self.change('question.review', b)
        b = self.resolve(b)
        self.assertEqual(b['answer']['revision'], 2)
        answers = self.call('question.read', {'questionId': b['id']})['value']['answers']
        self.assertEqual([answer['revision'] for answer in answers], [1, 2])
        self.assertEqual(answers[0]['prerequisites'][0]['revision'], 1)
        self.assertEqual(answers[1]['prerequisites'][0]['revision'], 2)

    def test_new_prerequisite_answer_invalidates_maintenance_work_and_review_acknowledgement(self):
        a, b = self.question('A'), self.question('B')
        self.connect(a, b)
        b = self.read(b)
        claim = self.write('claim.acquire', actor=AGENT, questionId=b['id'], expectedRev=b['rev'])
        self.resolve(a)
        b = self.read(b)
        self.assertEqual(b['state'], 'needs-review')
        self.assertIsNone(b['claim'])
        self.error(self.call('claim.renew', {'questionId': b['id'], 'claimToken': claim['claimToken'], 'fence': claim['fence']}, AGENT), 'stale_claim')
        self.change('question.reopen', a)
        b = self.change('question.review', b)
        self.assertEqual(b['state'], 'open')
        self.resolve(a)
        self.assertEqual(self.read(b)['state'], 'needs-review')

    def test_excluded_blocker_never_satisfies_dependency(self):
        a, b = self.question('A'), self.question('B')
        self.connect(a, b)
        self.change('question.exclude', a)
        b = self.read(b)
        self.assertEqual(b['blockedBy'], [a['id']])
        self.error(self.call('question.resolve', {'questionId': b['id'], 'expectedRev': b['rev'], 'answer': {'markdown': 'No', 'authority': {'kind': 'human', 'decider': 'Me', 'confirmation': 'Yes'}, 'references': []}}), 'not_ready')
        self.assertFalse(self.map()['complete'])

    def test_edge_changes_invalidate_work_preserve_wait_and_revoke_claims(self):
        a, b, c = [self.question(name) for name in 'ABC']
        self.connect(b, c)
        b = self.change('question.update', b, patch={'progress': 'Already investigated'})
        c = self.change('wait.set', c, reason='Ask owner')
        claim = self.write('claim.acquire', actor=AGENT, questionId=c['id'], expectedRev=c['rev'])
        self.connect(a, b)
        self.assertEqual(self.read(b)['state'], 'needs-review')
        current = self.read(c)
        self.assertEqual(current['state'], 'needs-review')
        self.assertEqual(current['wait'], 'Ask owner')
        self.assertIsNone(current['claim'])
        self.error(self.call('claim.renew', {'questionId': c['id'], 'claimToken': claim['claimToken'], 'fence': claim['fence']}, actor=AGENT), 'stale_claim')
        old_rev = current['rev']
        self.connect(a, b, remove=True)
        self.assertGreater(self.read(c)['rev'], old_rev)

    def test_agent_claim_required_human_takeover_and_stale_fence(self):
        question = self.question()
        self.error(self.call('question.update', {'questionId': question['id'], 'expectedRev': question['rev'], 'patch': {'body': 'Agent'}}, AGENT), 'stale_claim')
        claim = self.write('claim.acquire', actor=AGENT, questionId=question['id'], expectedRev=question['rev'])
        question = claim['question']
        credentials = {key: claim[key] for key in ['claimToken', 'fence']}
        self.assertNotIn('claimToken', json.dumps(self.call('workspace.read')))
        self.assertNotIn('tokenHash', json.dumps(self.call('question.read', {'questionId': question['id']})))
        self.error(self.call('question.update', {'questionId': question['id'], 'expectedRev': question['rev'], 'patch': {'body': 'Human'}}, HUMAN), 'claimed')
        self.write('question.update', actor=AGENT, questionId=question['id'], expectedRev=question['rev'], patch={'body': 'Agent'}, **credentials)
        question = self.change('claim.takeover', question)
        self.assertIsNone(question['claim'])
        self.error(self.call('question.update', {'questionId': question['id'], 'expectedRev': question['rev'], 'patch': {'body': 'Stale worker'}, **credentials}, AGENT), 'stale_claim')
        next_claim = self.write('claim.acquire', actor=AGENT, questionId=question['id'], expectedRev=question['rev'])
        self.assertGreater(next_claim['fence'], claim['fence'])

    def test_claim_expiry_release_and_restart_preserve_waits(self):
        question = self.change('wait.set', self.question(), reason='Owner decision')
        claim = self.write('claim.acquire', actor=AGENT, questionId=question['id'], expectedRev=question['rev'])
        credentials = {key: claim[key] for key in ['claimToken', 'fence']}
        renewed = self.write('claim.renew', actor=AGENT, questionId=question['id'], **credentials)
        self.assertGreaterEqual(renewed['expiresAt'], claim['expiresAt'])
        self.workspace = Workspace.discover(self.project)
        with patch('wayfinder.core.time.time', return_value=time.time() + LEASE_SECONDS + 10):
            current = self.read(question)
            self.assertIsNone(current['claim'])
            self.assertEqual(current['wait'], 'Owner decision')
            self.error(self.call('claim.renew', {'questionId': question['id'], **credentials}, AGENT), 'stale_claim')
            second = self.write('claim.acquire', actor=AGENT, questionId=question['id'], expectedRev=current['rev'])
            self.write('claim.release', actor=AGENT, questionId=question['id'], claimToken=second['claimToken'], fence=second['fence'])
        self.assertEqual(self.read(question)['wait'], 'Owner decision')
        self.assertEqual(self.read(question)['state'], 'open')

    def test_agent_own_claim_can_resolve_and_claims_allow_maintenance(self):
        question = self.question()
        claim = self.write('claim.acquire', actor=AGENT, questionId=question['id'], expectedRev=question['rev'])
        resolved = self.resolve(question, actor=AGENT, claimToken=claim['claimToken'], fence=claim['fence'])
        self.assertEqual(resolved['state'], 'resolved')
        self.assertIsNone(resolved['claim'])
        claim = self.write('claim.acquire', actor=AGENT, questionId=question['id'], expectedRev=resolved['rev'])
        reopened = self.change('question.reopen', question, actor=AGENT, claimToken=claim['claimToken'], fence=claim['fence'])
        self.assertEqual(reopened['state'], 'open')
        self.assertIsNone(reopened['answer'])

    def test_resolved_content_requires_reopening_but_labels_remain_editable(self):
        question = self.resolve(self.question())
        self.error(self.call('question.update', {'questionId': question['id'], 'expectedRev': question['rev'], 'patch': {'body': 'Changed decision context'}}), 'not_ready')
        updated = self.change('question.update', question, patch={'labels': ['accepted'], 'priority': 1})
        self.assertEqual(updated['answer'], question['answer'])
        self.error(self.call('wait.set', {'questionId': question['id'], 'expectedRev': updated['rev'], 'reason': 'More work'}), 'not_ready')

    def test_search_matches_ids_labels_owner_and_full_graph_readiness(self):
        a, b = self.question('Alpha', labels=['storage']), self.question('Beta', body='Database choice')
        self.connect(a, b)
        result = self.call('question.search', {'text': 'database'})['value']['questions']
        self.assertEqual([q['id'] for q in result], [b['id']])
        self.assertFalse(result[0]['ready'])
        self.assertEqual(self.call('question.search', {'labels': ['storage']})['value']['questions'][0]['id'], a['id'])
        self.assertEqual(self.call('question.search', {'text': a['id']})['value']['questions'][0]['id'], a['id'])
        a = self.read(a)
        self.write('claim.acquire', actor=AGENT, questionId=a['id'], expectedRev=a['rev'])
        self.assertEqual([q['id'] for q in self.call('question.search', {'owner': 'worker'})['value']['questions']], [a['id']])

    def test_invalid_shapes_are_json_errors_without_changes(self):
        before = self.call('workspace.read')
        for document in [None, [], {'op': 'nope', 'input': {}}, {'op': 'map.create', 'input': {}},
                         {'op': 'question.search', 'input': {'ready': 'yes'}}, {'op': 'map.read', 'input': {'mapId': 12}}]:
            self.error(self.workspace.operate(document), 'validation')
        for data in [{'title': '', 'method': 'research'}, {'title': 'X', 'method': 'wrong'},
                     {'title': 'X', 'method': 'research', 'priority': True},
                     {'title': 'X', 'method': 'research', 'labels': ['one', 'one']}]:
            self.error(self.call('question.create', {'mapId': self.mapping['id'], **data}), 'validation')
        self.assertEqual(before, self.call('workspace.read'))

    def test_two_process_claim_race_has_one_winner(self):
        question = self.question()
        processes = []
        for name in ['racer-a', 'racer-b']:
            request = {'op': 'claim.acquire', 'input': {'questionId': question['id'], 'expectedRev': question['rev']},
                       'actor': {'kind': 'agent', 'id': name}, 'requestId': name}
            process = subprocess.Popen([sys.executable, str(CLI), '--project', str(self.project), 'call'],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            processes.append((process, request))
        for process, request in processes:
            process.stdin.write(json.dumps(request))
            process.stdin.close()
        results = []
        for process, _ in processes:
            process.wait(timeout=10)
            results.append(json.loads(process.stdout.read()))
            self.assertEqual(process.stderr.read(), '')
            process.stdout.close()
            process.stderr.close()
        self.assertEqual(sum(result['ok'] for result in results), 1, results)
        self.assertIn(next(result['error']['code'] for result in results if not result['ok']), ['conflict', 'claimed'])


class DiscoveryTests(unittest.TestCase):
    def git(self, path, *args):
        result = subprocess.run(['git', '-C', str(path), *args], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_git_worktrees_share_durable_metadata_separate_from_installer(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo, tree = base / 'repo', base / 'tree'
            repo.mkdir()
            self.git(repo, 'init')
            self.git(repo, '-c', 'user.name=Test', '-c', 'user.email=test@example.com', 'commit', '--allow-empty', '-m', 'init')
            self.git(repo, 'worktree', 'add', '-b', 'test-worktree', str(tree))
            workspace = Workspace.initialize(repo)
            self.assertEqual(Workspace.initialize(tree).info, workspace.info)
            self.assertEqual(Workspace.discover(tree).db_path, workspace.db_path)
            (repo / '.bstack/config.json').write_text('{"installer":"independent"}')
            (repo / '.bstack/config.json').unlink()
            self.assertEqual(Workspace.discover(tree).info, workspace.info)
            self.git(repo, 'check-ignore', '.bstack/workspace/metadata.json')
            metadata = repo / '.bstack/workspace/metadata.json'
            data = json.loads(metadata.read_text())
            data['id'] = 'wrong'
            metadata.write_text(json.dumps(data))
            with self.assertRaises(DomainError):
                Workspace.discover(tree)

    def test_missing_store_never_recreates_and_init_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            with self.assertRaises(DomainError):
                Workspace.discover(project)
            workspace = Workspace.initialize(project)
            self.assertEqual(Workspace.initialize(project).info, workspace.info)
            workspace.db_path.unlink()
            with self.assertRaises(DomainError):
                Workspace.initialize(project)
            self.assertFalse(workspace.db_path.exists())

    def test_non_git_works_without_git_executable_but_malformed_git_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            with patch('wayfinder.core.subprocess.run', side_effect=FileNotFoundError):
                workspace = Workspace.initialize(project)
                self.assertEqual(Workspace.discover(project).info, workspace.info)
            (project / '.git').mkdir()
            with self.assertRaises(DomainError):
                Workspace.discover(project)


if __name__ == '__main__':
    unittest.main()
