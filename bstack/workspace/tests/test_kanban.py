import contextlib
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
from wayfinder.core import Workspace, DomainError, LEASE_SECONDS, SCHEMA, SCHEMA_VERSION
from wayfinder import migration

CLI = Path(__file__).resolve().parents[1] / 'cli.py'
HUMAN = {'id': 'owner', 'kind': 'human'}
AGENT = {'id': 'worker', 'kind': 'agent'}
AUTHORITY = {'kind': 'human', 'decider': 'Owner', 'confirmation': 'Approved in fixture'}


class KanbanTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.workspace = Workspace.initialize(self.project)

    def tearDown(self):
        self.temporary.cleanup()

    def call(self, op, data=None, actor=HUMAN, request_id=None):
        envelope = {'op': op, 'input': data or {}}
        if not op.endswith(('.read', '.search')):
            envelope.update(actor=actor, requestId=request_id or str(uuid.uuid4()))
        return self.workspace.operate(envelope)

    def ok(self, op, actor=HUMAN, request_id=None, **data):
        result = self.call(op, data, actor, request_id)
        self.assertTrue(result['ok'], result)
        return result['value']

    def error(self, result, code):
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], code, result)

    def ticket(self, title='Ticket', **data):
        return self.ok('ticket.create', title=title, body='Implement bounded work', acceptanceCriteria='It survives restart', authority=AUTHORITY, **data)['ticket']

    def read(self, record):
        kind = 'spec' if record['id'].startswith('s_') else 'question' if record['id'].startswith('q_') else 'ticket'
        return self.ok(kind + '.read', **{kind + 'Id': record['id']})[kind]

    def edit(self, op, record, **data):
        kind = op.split('.')[0]
        return self.ok(op, **{kind + 'Id': record['id'], 'expectedRev': self.read(record)['rev']}, **data)[kind]

    def done(self, ticket):
        for state in ['ready', 'in-progress', 'review']:
            ticket = self.edit('ticket.transition', ticket, to=state)
        return self.edit('ticket.transition', ticket, to='done', completion={'markdown': 'Restart verified', 'references': ['run.txt']})

    def link(self, source, target, kind='blocks', remove=False):
        return self.ok('ticket.relationship.' + ('remove' if remove else 'add'), kind=kind,
                       **{'from': source['id'], 'to': target['id'], 'expectedFromRev': self.read(source)['rev'], 'expectedToRev': self.read(target)['rev']})

    def question(self):
        mapping = self.ok('map.create', title='Map', destination='Ship', scope='Bounded', unresolved='Unsettled map area')['map']
        question = self.ok('question.create', mapId=mapping['id'], title='Decision', method='research')['question']
        return self.resolve(question)

    def resolve(self, question):
        return self.edit('question.resolve', question, answer={'markdown': 'Accepted choice', 'authority': AUTHORITY, 'references': []})

    def source(self, question):
        question = self.read(question)
        return {'questionId': question['id'], 'answerId': question['answer']['id'], 'revision': question['answer']['revision']}

    def spec(self, question=None):
        data = {'questionIds': [question['id']], 'mapId': question['mapId']} if question else {}
        return self.ok('spec.create', title='Bounded spec', markdown='Behavior and acceptance', **data)['spec']

    def approve(self, spec, questions=(), **data):
        return self.edit('spec.approve', spec, questionSources=[self.source(q) for q in questions], authority=AUTHORITY, **data)

    def acknowledge(self, ticket, **data):
        ticket = self.read(ticket)
        spec = ticket['sources']['spec']
        sources = {'spec': {'specId': spec['specId'], 'revision': self.ok('spec.read', specId=spec['specId'])['spec']['acceptedRevision']} if spec else None,
                   'questions': [self.source({'id': q['questionId']}) for q in ticket['sources']['questions']]}
        return self.edit('ticket.sources.acknowledge', ticket, sources=sources, note='Checked current impact', authority=AUTHORITY, **data)

    def test_standalone_lifecycle_history_restart_and_map_counts(self):
        ticket = self.ticket()
        self.assertEqual(self.ok('workspace.read')['maps'], [])
        self.error(self.call('ticket.transition', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'to': 'done'}), 'not_ready')
        ticket = self.done(ticket)
        self.assertTrue(ticket['satisfiesDependency'])
        self.error(self.call('ticket.update', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'patch': {'progress': 'overwrite'}}), 'not_ready')
        self.error(self.call('ticket.transition', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'to': 'backlog'}), 'validation')
        ticket = self.edit('ticket.transition', ticket, to='backlog', reason='Revise scope')
        self.assertIsNone(ticket['completion'])
        history = self.ok('ticket.read', ticketId=ticket['id'])['history']
        self.assertEqual([row['completion']['markdown'] for row in history if row['completion']], ['Restart verified'])
        self.workspace = Workspace.discover(self.project)
        self.assertEqual(ticket, self.read(ticket))
        self.assertNotIn('tokenHash', json.dumps(history))
        self.assertNotIn('lease', json.dumps(history))

    def test_forward_content_authority_and_scope_changes(self):
        ticket = self.ok('ticket.create', title='Draft')['ticket']
        self.error(self.call('ticket.transition', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'to': 'ready'}), 'not_ready')
        ticket = self.edit('ticket.update', ticket, patch={'body': 'Do it', 'acceptanceCriteria': 'Verified', 'authority': AUTHORITY})
        ticket = self.edit('ticket.transition', ticket, to='ready')
        ticket = self.edit('ticket.update', ticket, patch={'body': 'Changed scope'})
        self.assertEqual(ticket['state'], 'backlog')
        ticket = self.edit('ticket.transition', ticket, to='ready')
        ticket = self.edit('ticket.transition', ticket, to='in-progress')
        self.error(self.call('ticket.update', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'patch': {'authority': None}}), 'not_ready')
        ticket = self.edit('ticket.update', ticket, patch={'progress': 'Half done', 'references': ['work.txt']})
        ticket = self.edit('ticket.transition', ticket, to='backlog')
        self.assertEqual(ticket['progress'], 'Half done')

    def test_spec_subset_approval_immutable_history_and_exact_sources(self):
        question = self.question()
        spec = self.spec(question)
        before = self.call('spec.read', {'specId': spec['id']})
        wrong = {**self.source(question), 'revision': 77}
        self.error(self.call('spec.approve', {'specId': spec['id'], 'expectedRev': spec['rev'], 'questionSources': [wrong], 'authority': AUTHORITY}), 'not_ready')
        self.assertEqual(before, self.call('spec.read', {'specId': spec['id']}))
        spec = self.approve(spec, [question])
        self.assertTrue(spec['usableApproval'])
        mapping = self.ok('map.read', mapId=question['mapId'])['map']
        self.assertFalse(mapping['complete'])
        first = self.ok('spec.read', specId=spec['id'])['revisions'][0]
        spec = self.edit('spec.update', spec, patch={'markdown': 'New behavior'})
        self.assertEqual(spec['state'], 'draft')
        self.assertEqual(spec['acceptedRevision'], 1)
        spec = self.approve(spec, [question])
        revisions = self.ok('spec.read', specId=spec['id'])['revisions']
        self.assertEqual(revisions[0], first)
        self.assertEqual(revisions[1]['markdown'], 'New behavior')
        self.assertEqual(spec['acceptedRevision'], 2)

    def test_diamond_sources_invalidate_done_and_claims_without_moving_columns(self):
        question = self.question()
        spec = self.approve(self.spec(question), [question])
        a = self.ticket('A', specId=spec['id'], questionIds=[question['id']])
        b, c, d = [self.ticket(title) for title in 'BCD']
        for source, target in [(a, b), (a, c), (b, d), (c, d)]:
            self.link(source, target)
        a = self.done(a)
        b, c = self.done(b), self.done(c)
        d = self.edit('ticket.transition', d, to='ready')
        d = self.edit('ticket.transition', d, to='in-progress')
        d = self.edit('ticket.update', d, patch={'progress': 'Preserved progress'})
        d = self.edit('ticket.wait.set', d, reason='Preserved wait')
        claim = self.ok('ticket.claim.acquire', actor=AGENT, ticketId=d['id'], expectedRev=d['rev'])
        spec_claim = self.ok('spec.claim.acquire', actor=AGENT, specId=spec['id'], expectedRev=spec['rev'])
        self.edit('question.reopen', question)
        for previous in [a, b, c, d]:
            current = self.read(previous)
            self.assertTrue(current['needsSourceReview'])
            self.assertGreater(current['rev'], previous['rev'])
            self.assertEqual(current['state'], previous['state'])
            self.assertFalse(current['satisfiesDependency'])
        current = self.read(d)
        self.assertEqual(current['progress'], 'Preserved progress')
        self.assertEqual(current['wait'], 'Preserved wait')
        self.assertIsNone(current['claim'])
        self.error(self.call('ticket.claim.renew', {'ticketId': d['id'], 'claimToken': claim['claimToken'], 'fence': claim['fence']}, AGENT), 'stale_claim')
        self.error(self.call('spec.claim.renew', {'specId': spec['id'], 'claimToken': spec_claim['claimToken'], 'fence': spec_claim['fence']}, AGENT), 'stale_claim')
        self.assertFalse(self.read(spec)['usableApproval'])
        self.error(self.call('ticket.sources.acknowledge', {'ticketId': a['id'], 'expectedRev': self.read(a)['rev'], 'sources': a['sources'], 'note': 'No', 'authority': AUTHORITY}), 'not_ready')

    def test_sources_acknowledge_cas_then_second_change_and_unresolved_rejection(self):
        question = self.question()
        spec = self.approve(self.spec(question), [question])
        ticket = self.ticket(specId=spec['id'], questionIds=[question['id']])
        ticket = self.edit('ticket.wait.set', ticket, reason='Keep waiting')
        self.edit('question.reopen', question)
        stale = self.read(ticket)
        self.error(self.call('ticket.sources.acknowledge', {'ticketId': ticket['id'], 'expectedRev': stale['rev'], 'sources': ticket['sources'], 'note': 'No accepted answer', 'authority': AUTHORITY}), 'not_ready')
        question = self.resolve(question)
        self.approve(spec, [question])
        ticket = self.acknowledge(ticket)
        self.assertFalse(ticket['needsSourceReview'])
        self.assertEqual(ticket['wait'], 'Keep waiting')
        self.assertEqual(ticket['state'], 'backlog')
        claim = self.ok('ticket.claim.acquire', actor=AGENT, ticketId=ticket['id'], expectedRev=ticket['rev'])
        self.edit('question.reopen', question)
        self.error(self.call('ticket.sources.acknowledge', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'sources': ticket['sources'], 'note': 'Old review', 'authority': AUTHORITY}), 'conflict')
        self.error(self.call('ticket.claim.renew', {'ticketId': ticket['id'], 'claimToken': claim['claimToken'], 'fence': claim['fence']}, AGENT), 'stale_claim')

    def test_question_metadata_and_claims_do_not_stale_accepted_sources(self):
        question = self.question()
        spec = self.approve(self.spec(question), [question])
        ticket = self.ticket(specId=spec['id'], questionIds=[question['id']])
        self.edit('question.update', question, patch={'labels': ['accepted'], 'priority': 4})
        question = self.read(question)
        claim = self.ok('claim.acquire', actor=AGENT, questionId=question['id'], expectedRev=question['rev'])
        self.ok('claim.renew', actor=AGENT, questionId=question['id'], claimToken=claim['claimToken'], fence=claim['fence'])
        self.assertEqual(ticket, self.read(ticket))
        self.assertEqual(spec, self.read(spec))

    def test_done_reopen_fences_live_dependent_claim_and_keeps_evidence(self):
        predecessor = self.done(self.ticket('Prerequisite'))
        dependent = self.ticket('Dependent')
        self.link(predecessor, dependent)
        dependent = self.edit('ticket.transition', dependent, to='ready')
        dependent = self.edit('ticket.transition', dependent, to='in-progress')
        claim = self.ok('ticket.claim.acquire', actor=AGENT, ticketId=dependent['id'], expectedRev=dependent['rev'])
        self.edit('ticket.transition', predecessor, to='backlog', reason='Need to revisit')
        current = self.read(dependent)
        self.assertTrue(current['needsSourceReview'])
        self.assertEqual(current['blockedBy'], [predecessor['id']])
        self.assertIsNone(current['claim'])
        self.assertGreater(current['rev'], claim['ticket']['rev'])
        self.error(self.call('ticket.transition', {'ticketId': dependent['id'], 'expectedRev': claim['ticket']['rev'], 'to': 'review', 'claimToken': claim['claimToken'], 'fence': claim['fence']}, AGENT), 'conflict')
        self.error(self.call('ticket.sources.acknowledge', {'ticketId': dependent['id'], 'expectedRev': current['rev'], 'sources': current['sources'], 'note': 'Still blocked', 'authority': AUTHORITY}), 'not_ready')

    def test_dependency_cycles_atomic_edges_and_filter_hidden_blocker(self):
        a, b, c = [self.ticket(title) for title in 'ABC']
        self.link(a, b)
        self.link(b, c)
        self.assertFalse(self.read(b)['needsSourceReview'])
        self.link(c, b, 'parent')
        self.link(c, a, 'related')
        for source, target, kind, code in [(c, a, 'blocks', 'cycle'), (b, c, 'parent', 'cycle'), (a, b, 'blocks', 'validation'), (a, a, 'related', 'validation')]:
            before = self.call('board.read')
            self.error(self.call('ticket.relationship.add', {'from': source['id'], 'to': target['id'], 'kind': kind, 'expectedFromRev': self.read(source)['rev'], 'expectedToRev': self.read(target)['rev']}), code)
            self.assertEqual(before, self.call('board.read'))
        filtered = self.ok('board.read', text=b['id'])
        self.assertEqual(filtered['tickets'][0]['blockedBy'], [a['id']])
        self.assertEqual(filtered['counts']['blocked'], 1)
        self.link(a, b, remove=True)
        self.assertFalse(self.read(b)['blockedBy'])
        self.assertFalse(self.read(b)['needsSourceReview'])

    def test_agent_claim_ownership_renewal_expiry_and_phase_release(self):
        for kind, record in [('ticket', self.ticket()), ('spec', self.spec())]:
            key = kind + 'Id'
            self.error(self.call(kind + '.update', {key: record['id'], 'expectedRev': record['rev'], 'patch': {'title': 'No claim'}}, AGENT), 'stale_claim')
            claim = self.ok(kind + '.claim.acquire', actor=AGENT, **{key: record['id'], 'expectedRev': record['rev']})
            credentials = {field: claim[field] for field in ['claimToken', 'fence']}
            self.error(self.call(kind + '.update', {key: record['id'], 'expectedRev': claim[kind]['rev'], 'patch': {'title': 'Human collision'}}), 'claimed')
            self.ok(kind + '.claim.renew', actor=AGENT, **{key: record['id']}, **credentials)
            self.assertNotIn('tokenHash', json.dumps(self.ok(kind + '.read', **{key: record['id']})))
            with patch('wayfinder.core.time.time', return_value=time.time() + LEASE_SECONDS + 1):
                self.assertIsNone(self.read(record)['claim'])
                self.error(self.call(kind + '.claim.renew', {key: record['id'], **credentials}, AGENT), 'stale_claim')
            self.error(self.call(kind + '.claim.takeover', {key: record['id'], 'expectedRev': self.read(record)['rev']}, AGENT), 'validation')
            self.edit(kind + '.claim.takeover', record)
        ticket = self.ticket('Phase ownership')
        ticket = self.edit('ticket.transition', ticket, to='ready')
        claim = self.ok('ticket.claim.acquire', actor=AGENT, ticketId=ticket['id'], expectedRev=ticket['rev'])
        credentials = {field: claim[field] for field in ['claimToken', 'fence']}
        ticket = self.edit('ticket.transition', ticket, to='in-progress', actor=AGENT, **credentials)
        ticket = self.edit('ticket.transition', ticket, to='review', actor=AGENT, **credentials)
        self.assertIsNone(ticket['claim'])
        self.error(self.call('ticket.transition', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'to': 'done', 'completion': {'markdown': 'No review claim', 'references': []}, **credentials}, AGENT), 'stale_claim')

    def test_two_process_claim_race_has_one_winner_and_replay_is_exact(self):
        ticket = self.ticket()
        processes = []
        for name in ['racer-a', 'racer-b']:
            envelope = {'op': 'ticket.claim.acquire', 'input': {'ticketId': ticket['id'], 'expectedRev': ticket['rev']}, 'actor': {'kind': 'agent', 'id': name}, 'requestId': name}
            process = subprocess.Popen([sys.executable, str(CLI), '--project', str(self.project), 'call'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            processes.append((process, envelope))
        for process, envelope in processes:
            process.stdin.write(json.dumps(envelope)); process.stdin.close()
        results = []
        for process, _ in processes:
            process.wait(timeout=10)
            results.append(json.loads(process.stdout.read()))
            self.assertEqual(process.stderr.read(), '')
            process.stdout.close(); process.stderr.close()
        self.assertEqual(sum(result['ok'] for result in results), 1, results)
        first = self.call('ticket.create', {'title': 'Replay'}, request_id='create-once')
        self.assertEqual(first, self.call('ticket.create', {'title': 'Replay'}, request_id='create-once'))
        self.error(self.call('ticket.create', {'title': 'Different'}, request_id='create-once'), 'request_reused')
        spec = self.spec()
        approve = {'specId': spec['id'], 'expectedRev': spec['rev'], 'questionSources': [], 'authority': AUTHORITY}
        first = self.call('spec.approve', approve, request_id='approve-once')
        self.assertEqual(first, self.call('spec.approve', approve, request_id='approve-once'))
        self.assertEqual(len(self.ok('spec.read', specId=spec['id'])['revisions']), 1)

    def test_link_set_and_source_acknowledgement_cannot_invent_scope(self):
        question = self.question()
        spec = self.spec(question)
        ticket = self.ticket(specId=spec['id'])
        self.assertIsNone(ticket['sources']['spec']['revision'])
        self.assertTrue(ticket['sourceIssues'])
        self.error(self.call('ticket.sources.acknowledge', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'sources': {'spec': None, 'questions': []}, 'note': 'Drop source', 'authority': AUTHORITY}), 'validation')
        self.approve(spec, [question])
        ticket = self.acknowledge(ticket)
        ticket = self.edit('ticket.transition', ticket, to='ready')
        ticket = self.edit('ticket.transition', ticket, to='in-progress')
        self.error(self.call('ticket.link', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'specId': None, 'questionIds': []}), 'validation')
        ticket = self.edit('ticket.link', ticket, specId=None, questionIds=[question['id']], reason='Use direct bounded source')
        self.assertTrue(ticket['needsSourceReview'])
        ticket = self.acknowledge(ticket)
        self.assertFalse(ticket['needsSourceReview'])
        self.assertEqual(ticket['state'], 'in-progress')

    def test_generic_patches_cannot_set_state_sources_claim_or_completion(self):
        ticket = self.ticket()
        for field, value in [('state', 'done'), ('sources', {}), ('lease', {}), ('completion', {}), ('needsSourceReview', False)]:
            self.error(self.call('ticket.update', {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'patch': {field: value}}), 'validation')
        self.error(self.call('ticket.create', {'title': 'X', 'questionIds': ['missing']}), 'not_found')
        self.error(self.call('ticket.create', {'title': 'X', 'references': [''] }), 'validation')
        self.error(self.call('ticket.create', {'title': 'X', 'priority': True}), 'validation')
        self.assertEqual(ticket, self.read(ticket))

    def test_started_work_retains_review_requirement_after_return_to_backlog(self):
        for complete in [False, True]:
            ticket = self.ticket('Already started')
            if complete:
                ticket = self.done(ticket)
                ticket = self.edit('ticket.transition', ticket, to='backlog', reason='Rework')
            else:
                ticket = self.edit('ticket.transition', ticket, to='ready')
                ticket = self.edit('ticket.transition', ticket, to='in-progress')
                ticket = self.edit('ticket.transition', ticket, to='backlog')
            self.assertIsNotNone(ticket['startedAt'])
            predecessor = self.done(self.ticket('New prerequisite'))
            self.link(predecessor, ticket)
            current = self.read(ticket)
            self.assertTrue(current['needsSourceReview'])
            self.error(self.call('ticket.transition', {'ticketId': ticket['id'], 'expectedRev': current['rev'], 'to': 'ready'}), 'not_ready')
            self.acknowledge(ticket)
            spec = self.approve(self.spec())
            ticket = self.edit('ticket.link', ticket, specId=spec['id'], questionIds=[])
            self.assertTrue(ticket['needsSourceReview'])

    def test_ready_claim_then_new_dependency_rejects_stale_start_and_bumps_every_time(self):
        ticket = self.edit('ticket.transition', self.ticket('Ready to start'), to='ready')
        claim = self.ok('ticket.claim.acquire', actor=AGENT, ticketId=ticket['id'], expectedRev=ticket['rev'])
        blocker = self.ticket('New blocker')
        self.link(blocker, ticket)
        current = self.read(ticket)
        self.assertEqual(current['state'], 'ready')
        self.assertFalse(current['needsSourceReview'])
        self.assertFalse(current['ready'])
        self.assertIsNone(current['claim'])
        self.error(self.call('ticket.transition', {'ticketId': ticket['id'], 'expectedRev': claim['ticket']['rev'], 'to': 'in-progress', 'claimToken': claim['claimToken'], 'fence': claim['fence']}, AGENT), 'conflict')
        self.link(blocker, ticket, remove=True)
        second = self.read(ticket)
        self.assertGreater(second['rev'], current['rev'])
        self.assertTrue(second['ready'])
        self.error(self.call('ticket.claim.renew', {'ticketId': ticket['id'], 'claimToken': claim['claimToken'], 'fence': claim['fence']}, AGENT), 'stale_claim')

    def test_spec_draft_changes_invalidate_linked_tickets_but_claim_renewals_do_not(self):
        spec = self.approve(self.spec())
        ticket = self.ticket(specId=spec['id'])
        claim = self.ok('spec.claim.acquire', actor=AGENT, specId=spec['id'], expectedRev=spec['rev'])
        credentials = {field: claim[field] for field in ['claimToken', 'fence']}
        spec = self.ok('spec.claim.renew', actor=AGENT, specId=spec['id'], **credentials)['spec']
        self.assertEqual(ticket, self.read(ticket))
        spec = self.edit('spec.update', spec, actor=AGENT, patch={'references': ['new-adr.md']}, **credentials)
        current = self.read(ticket)
        self.assertTrue(current['needsSourceReview'])
        self.assertTrue(current['sourceIssues'])
        self.assertGreater(current['rev'], ticket['rev'])
        self.assertEqual(spec['claim']['owner'], AGENT['id'])
        spec = self.approve(spec, actor=AGENT, **credentials)
        newer = self.read(ticket)
        self.assertGreater(newer['rev'], current['rev'])
        self.assertTrue(newer['needsSourceReview'])
        self.assertEqual(spec['acceptedRevision'], 2)

    def test_spec_map_boundary_and_cross_map_ticket_sources(self):
        first, second = self.question(), self.question()
        self.error(self.call('spec.create', {'title': 'Wrong map', 'mapId': first['mapId'], 'questionIds': [second['id']]}), 'validation')
        spec = self.ok('spec.create', title='Workspace spec', markdown='Two source maps', questionIds=[first['id'], second['id']])['spec']
        spec = self.approve(spec, [first, second])
        ticket = self.ticket(mapId=first['mapId'], questionIds=[second['id']], specId=spec['id'])
        self.assertFalse(ticket['sourceIssues'])
        self.assertEqual(ticket['sources']['questions'], [self.source(second)])
        mapping = self.ok('map.read', mapId=first['mapId'])['map']
        self.assertEqual(mapping['counts']['total'], 1)

    def test_two_process_edge_writers_compare_both_endpoint_revisions(self):
        a, b, target = [self.ticket(title) for title in ['First prerequisite', 'Second prerequisite', 'Target']]
        processes = []
        for source in [a, b]:
            envelope = {'op': 'ticket.relationship.add', 'input': {'kind': 'blocks', 'from': source['id'], 'to': target['id'], 'expectedFromRev': source['rev'], 'expectedToRev': target['rev']}, 'actor': HUMAN, 'requestId': source['id']}
            process = subprocess.Popen([sys.executable, str(CLI), '--project', str(self.project), 'call'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            processes.append((process, envelope))
        for process, envelope in processes:
            process.stdin.write(json.dumps(envelope)); process.stdin.close()
        results = []
        for process, _ in processes:
            process.wait(timeout=10)
            results.append(json.loads(process.stdout.read()))
            self.assertEqual(process.stderr.read(), '')
            process.stdout.close(); process.stderr.close()
        self.assertEqual(sum(result['ok'] for result in results), 1, results)
        self.assertEqual(next(result['error']['code'] for result in results if not result['ok']), 'conflict')
        self.assertEqual(len(self.ok('board.read')['relationships']), 1)

    def test_lost_transition_replay_and_expiration_preserve_execution_and_wait(self):
        ticket = self.ticket()
        data = {'ticketId': ticket['id'], 'expectedRev': ticket['rev'], 'to': 'ready'}
        first = self.call('ticket.transition', data, request_id='move-once')
        self.assertTrue(first['ok'], first)
        self.assertEqual(first, self.call('ticket.transition', data, request_id='move-once'))
        self.error(self.call('ticket.transition', {**data, 'to': 'in-progress'}, request_id='move-once'), 'request_reused')
        ticket = self.edit('ticket.transition', ticket, to='in-progress')
        ticket = self.edit('ticket.update', ticket, patch={'progress': 'Still executing'})
        ticket = self.edit('ticket.wait.set', ticket, reason='Need owner reply')
        claim = self.ok('ticket.claim.acquire', actor=AGENT, ticketId=ticket['id'], expectedRev=ticket['rev'])
        with patch('wayfinder.core.time.time', return_value=time.time() + LEASE_SECONDS + 1):
            current = self.read(ticket)
            self.assertEqual(current['state'], 'in-progress')
            self.assertEqual(current['progress'], 'Still executing')
            self.assertEqual(current['wait'], 'Need owner reply')
            self.assertIsNone(current['claim'])
            self.error(self.call('ticket.claim.renew', {'ticketId': ticket['id'], 'claimToken': claim['claimToken'], 'fence': claim['fence']}, AGENT), 'stale_claim')
        self.assertEqual(first, self.call('ticket.transition', data, request_id='move-once'))
