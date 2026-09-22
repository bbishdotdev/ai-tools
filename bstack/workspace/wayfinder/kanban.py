from collections import deque
import json

from .core import canonical, fail, fields, identity, integer, labels, new_id, text, KINDS

TICKET_STATES = {'backlog', 'ready', 'in-progress', 'review', 'done'}
TRANSITIONS = {'backlog': {'ready'}, 'ready': {'backlog', 'in-progress'},
               'in-progress': {'backlog', 'review'}, 'review': {'in-progress', 'done'}, 'done': {'backlog'}}


def authority(value, optional=False):
    if optional and value is None:
        return None
    if not isinstance(value, dict):
        fail('validation', 'An explicit human or delegated authority is required')
    required = {'kind', 'decider', 'confirmation'} if value.get('kind') == 'human' else {'kind', 'decider', 'scope', 'grantReference'}
    if value.get('kind') not in {'human', 'delegated'}:
        fail('validation', 'An explicit human or delegated authority is required')
    fields(value, required, required)
    return {key: text(item, 'authority.' + key, 4000, False) for key, item in value.items()}


def references(value):
    if not isinstance(value, list) or len(value) > 100:
        fail('validation', 'references must be an array of at most 100 strings')
    return [text(item, 'reference', 4000, False) for item in value]


def identifiers(value, name):
    if not isinstance(value, list) or len(value) > 100:
        fail('validation', name + ' must be an array of at most 100 unique IDs')
    result = [identity(item, name) for item in value]
    if len(set(result)) != len(result):
        fail('validation', name + ' must be unique')
    return sorted(result)


class Records:
    def __init__(self, board, kind):
        self.board, self.kind = board, kind

    def get(self, identifier):
        identity(identifier, self.kind + 'Id')
        collection = self.board.specs if self.kind == 'spec' else self.board.tickets
        if identifier not in collection:
            fail('not_found', self.kind.capitalize() + ' not found')
        return collection[identifier]

    def view(self, record):
        return self.board.spec_view(record) if self.kind == 'spec' else self.board.ticket_view(record)

    def touch(self, record):
        changed = self.board.changed_specs if self.kind == 'spec' else self.board.changed_tickets
        if record['id'] not in changed:
            record['rev'] += 1
            record['updatedAt'] = self.board.tx.now
            changed.add(record['id'])
        self.board._satisfaction = None

    def expected(self, record, revision):
        integer(revision, 'expectedRev', 1)
        if record['rev'] != revision:
            fail('conflict', self.kind.capitalize() + ' changed', currentRev=record['rev'], current=self.view(record))

    def authorize(self, record, actor, data):
        claim = self.board.tx.live_claim(record)
        supplied = 'claimToken' in data or 'fence' in data
        if actor['kind'] == 'agent' or supplied or (claim and claim['owner'] == actor['id']):
            if not claim or claim['owner'] != actor['id'] or not self.board.tx.credentials(claim, data):
                fail('stale_claim', 'A current claim owned by this actor is required')
        elif claim:
            fail('claimed', self.kind.capitalize() + ' has a live claim', currentRev=record['rev'], current=self.view(record))


class Kanban:
    def __init__(self, tx):
        self.tx, self.db = tx, tx.db
        self.specs = {row[0]: json.loads(row[1]) for row in self.db.execute('SELECT id,data FROM specs')}
        self.revisions = {(row[0], row[1]): json.loads(row[2]) for row in self.db.execute('SELECT spec_id,revision,data FROM spec_revisions')}
        self.tickets = {row[0]: json.loads(row[1]) for row in self.db.execute('SELECT id,data FROM tickets')}
        self.edges = set(self.db.execute('SELECT kind,source,target FROM ticket_relationships'))
        self.changed_specs, self.changed_tickets, self.new_revisions = set(), set(), []
        self.spec, self.ticket = Records(self, 'spec'), Records(self, 'ticket')
        self.question_sources = {key: self.question_source(key) for key in tx.questions}
        self._satisfaction = None

    def question_source(self, identifier):
        question = self.tx.get_question(identifier)
        answer = question['answer'] if question['state'] == 'resolved' else None
        return {'questionId': identifier, 'answerId': answer['id'] if answer else None,
                'revision': answer['revision'] if answer else None}

    def question_issues(self, sources):
        issues = []
        for expected in sources:
            current = self.question_source(expected['questionId'])
            if current['answerId'] is None or current != expected:
                issues.append({'kind': 'question', 'id': expected['questionId'],
                               'reason': 'Question has no current accepted answer' if current['answerId'] is None else 'Accepted answer changed',
                               'expected': expected, 'current': current})
        return issues

    def spec_issues(self, spec):
        revision = self.revisions.get((spec['id'], spec['acceptedRevision']))
        sources = revision['questionSources'] if revision else [self.question_source(q) for q in spec['questionIds']]
        return self.question_issues(sources)

    def usable_spec(self, spec):
        return spec['state'] == 'approved' and spec['acceptedRevision'] is not None and not self.spec_issues(spec)

    def public(self, record):
        view = {key: value for key, value in record.items() if key not in {'lease', 'fence'}}
        claim = self.tx.live_claim(record)
        view['claim'] = {key: claim[key] for key in ('owner', 'expiresAt', 'fence')} if claim else None
        return view

    def spec_view(self, spec):
        return {**self.public(spec), 'sourceIssues': self.spec_issues(spec), 'usableApproval': self.usable_spec(spec)}

    def source_issues(self, ticket):
        issues = self.question_issues(ticket['sources']['questions'])
        expected = ticket['sources']['spec']
        if expected:
            spec = self.spec.get(expected['specId'])
            current = {'specId': spec['id'], 'revision': spec['acceptedRevision'] if self.usable_spec(spec) else None}
            if not self.usable_spec(spec) or current != expected:
                issues.append({'kind': 'spec', 'id': spec['id'], 'reason': 'Spec has no current usable approval' if not self.usable_spec(spec) else 'Accepted spec revision changed',
                               'expected': expected, 'current': current})
        return issues

    def predecessors(self, identifier):
        return sorted(source for kind, source, target in self.edges if kind == 'blocks' and target == identifier)

    def descendants(self, identifiers, kind='blocks'):
        return self.tx.descendants(identifiers, kind, self.edges)

    def satisfaction(self):
        if self._satisfaction is not None:
            return self._satisfaction
        incoming = {key: 0 for key in self.tickets}
        children = {key: [] for key in self.tickets}
        for kind, source, target in self.edges:
            if kind == 'blocks':
                incoming[target] += 1
                children[source].append(target)
        pending = deque(key for key, count in incoming.items() if not count)
        result, blocked = {}, set()
        while pending:
            key = pending.popleft()
            ticket = self.tickets[key]
            result[key] = (ticket['state'] == 'done' and bool(ticket['completion']) and not ticket['needsSourceReview']
                           and not self.source_issues(ticket) and key not in blocked)
            for child in children[key]:
                if not result[key]:
                    blocked.add(child)
                incoming[child] -= 1
                if not incoming[child]:
                    pending.append(child)
        self._satisfaction = result
        return result

    @staticmethod
    def content_ready(ticket):
        return bool(ticket['body'].strip() and ticket['acceptanceCriteria'].strip() and ticket['authority'])

    def ticket_view(self, ticket):
        view = self.public(ticket)
        satisfied = self.satisfaction()
        view['blockedBy'] = [key for key in self.predecessors(ticket['id']) if not satisfied.get(key, False)]
        view['sourceIssues'] = self.source_issues(ticket)
        view['satisfiesDependency'] = satisfied.get(ticket['id'], False)
        view['ready'] = (ticket['state'] == 'ready' and self.content_ready(ticket) and not view['blockedBy']
                         and not view['sourceIssues'] and not ticket['needsSourceReview'] and not ticket['wait'] and not view['claim'])
        return view

    @staticmethod
    def has_work(ticket):
        return (ticket.get('startedAt') is not None or ticket['state'] in {'in-progress', 'review', 'done'} or bool(ticket['progress'].strip())
                or ticket['completion'] is not None or ticket['sourceReview'] is not None)

    def invalidate_tickets(self, direct=(), dependency=()):
        direct = set(direct)
        affected = direct | set(dependency) | self.descendants(direct | set(dependency))
        for key in affected:
            ticket = self.tickets[key]
            if key in direct or self.has_work(ticket):
                ticket['needsSourceReview'] = True
            self.tx.revoke(ticket)
            self.ticket.touch(ticket)

    def invalidate_specs(self, identifiers, revoke_specs=True):
        identifiers = set(identifiers)
        for key in identifiers:
            if revoke_specs:
                self.tx.revoke(self.specs[key])
            self.spec.touch(self.specs[key])
        self.invalidate_tickets(direct={key for key, ticket in self.tickets.items()
                                       if ticket['sources']['spec'] and ticket['sources']['spec']['specId'] in identifiers})

    def invalidate_question_changes(self):
        changed = {key for key in self.tx.changed_questions if key in self.question_sources
                   and self.question_sources[key] != self.question_source(key)}
        if not changed:
            return
        specs = {key for key, spec in self.specs.items() if changed.intersection(spec['questionIds'])
                 or changed.intersection(source['questionId'] for source in self.revisions.get((key, spec['acceptedRevision']), {}).get('questionSources', []))}
        self.invalidate_specs(specs)
        self.invalidate_tickets(direct={key for key, ticket in self.tickets.items()
                                       if changed.intersection(source['questionId'] for source in ticket['sources']['questions'])})

    def map_id(self, value):
        return self.tx.get_map(value)['id'] if value is not None else None

    def declared_questions(self, values, map_id=None):
        values = identifiers(values, 'questionIds')
        for key in values:
            question = self.tx.get_question(key)
            if map_id is not None and question['mapId'] != map_id:
                fail('validation', 'Spec questions must belong to its map')
        return values

    def snapshot(self, spec_id, question_ids):
        spec = self.spec.get(spec_id) if spec_id is not None else None
        questions = self.declared_questions(question_ids)
        return {'spec': {'specId': spec['id'], 'revision': spec['acceptedRevision'] if self.usable_spec(spec) else None} if spec else None,
                'questions': [self.question_source(key) for key in questions]}

    def exact_question_sources(self, supplied, question_ids):
        if not isinstance(supplied, list) or len(supplied) > 100:
            fail('validation', 'questionSources must be an array of at most 100 sources')
        checked = []
        for item in supplied:
            fields(item, {'questionId', 'answerId', 'revision'}, {'questionId', 'answerId', 'revision'})
            identity(item['questionId'], 'questionId')
            identity(item['answerId'], 'answerId')
            integer(item['revision'], 'revision', 1)
            checked.append(item)
        if sorted(item['questionId'] for item in checked) != sorted(question_ids):
            fail('validation', 'Source snapshot must name exactly the declared questions')
        current = [self.question_source(key) for key in sorted(question_ids)]
        if any(item['answerId'] is None for item in current) or sorted(checked, key=lambda item: item['questionId']) != current:
            fail('not_ready', 'Question source snapshot is not currently accepted', current=current)
        return current

    def query(self, op, data):
        if op == 'spec.read':
            fields(data, {'specId'}, {'specId'})
            spec = self.spec.get(data['specId'])
            return {'spec': self.spec_view(spec), 'revisions': [revision for (key, number), revision in sorted(self.revisions.items()) if key == spec['id']]}
        if op == 'ticket.read':
            fields(data, {'ticketId'}, {'ticketId'})
            ticket = self.ticket.get(data['ticketId'])
            history = [json.loads(row[0]) for row in self.db.execute('SELECT data FROM history WHERE entity_id=? ORDER BY revision', (ticket['id'],))]
            return {'ticket': self.ticket_view(ticket), 'history': history}
        if op == 'spec.search':
            fields(data, {'mapId', 'text', 'state'})
            if 'mapId' in data:
                self.map_id(data['mapId'])
            needle = text(data.get('text', ''), 'text', 1000).casefold()
            if 'state' in data and data['state'] not in {'draft', 'approved'}:
                fail('validation', 'Unknown spec state')
            return {'specs': [self.spec_view(spec) for spec in self.specs.values()
                              if ('mapId' not in data or spec['mapId'] == data['mapId'])
                              and ('state' not in data or spec['state'] == data['state'])
                              and needle in ' '.join([spec['id'], spec['title'], spec['markdown']]).casefold()]}
        fields(data, {'mapId', 'specId', 'text', 'labels', 'state', 'owner', 'ready'})
        if 'mapId' in data:
            self.map_id(data['mapId'])
        if 'specId' in data:
            self.spec.get(data['specId'])
        needle = text(data.get('text', ''), 'text', 1000).casefold()
        wanted_labels = set(labels(data.get('labels', [])))
        if 'state' in data and data['state'] not in TICKET_STATES:
            fail('validation', 'Unknown ticket state')
        if 'owner' in data:
            identity(data['owner'], 'owner')
        if 'ready' in data and type(data['ready']) is not bool:
            fail('validation', 'ready must be a boolean')
        result = []
        for ticket in self.tickets.values():
            if 'mapId' in data and ticket['mapId'] != data['mapId']:
                continue
            if 'specId' in data and (not ticket['sources']['spec'] or ticket['sources']['spec']['specId'] != data['specId']):
                continue
            if needle not in ' '.join([ticket['id'], ticket['title'], ticket['body'], ticket['acceptanceCriteria'], *ticket['labels']]).casefold() or not wanted_labels.issubset(ticket['labels']):
                continue
            if 'state' in data and ticket['state'] != data['state']:
                continue
            view = self.ticket_view(ticket)
            if 'owner' in data and (not view['claim'] or view['claim']['owner'] != data['owner']):
                continue
            if 'ready' in data and view['ready'] != data['ready']:
                continue
            result.append(view)
        if op == 'ticket.search':
            return {'tickets': result}
        counts = {key: sum(ticket['state'] == state for ticket in result) for key, state in
                  [('backlog', 'backlog'), ('ready', 'ready'), ('inProgress', 'in-progress'), ('review', 'review'), ('done', 'done')]}
        counts.update(blocked=sum(bool(ticket['blockedBy']) for ticket in result), needsSourceReview=sum(ticket['needsSourceReview'] for ticket in result))
        return {'tickets': result, 'relationships': self.relationships(), 'counts': counts}

    def relationships(self):
        return [{'kind': kind, 'from': source, 'to': target} for kind, source, target in sorted(self.edges)]

    def new_record(self, kind):
        return {'id': new_id('s' if kind == 'spec' else 't'), 'rev': 1, 'lease': None, 'fence': 0,
                'createdAt': self.tx.now, 'updatedAt': self.tx.now}

    def mutate(self, op, data, actor):
        kind = op.split('.')[0]
        adapter = self.spec if kind == 'spec' else self.ticket
        if '.claim.' in op:
            return self.tx.mutate_claim(op[len(kind) + 1:], data, actor, adapter)
        if op.startswith('ticket.relationship.'):
            return self.mutate_relationship(op, data)
        if op == 'spec.create':
            fields(data, {'mapId', 'title', 'markdown', 'questionIds', 'references'}, {'title'})
            if len(self.specs) >= 500:
                fail('validation', 'Workspace spec limit reached')
            map_id = self.map_id(data.get('mapId'))
            record = {**self.new_record(kind), 'mapId': map_id, 'title': text(data['title'], 'title', 300, False),
                      'markdown': text(data.get('markdown', ''), 'markdown', 50000),
                      'questionIds': self.declared_questions(data.get('questionIds', []), map_id),
                      'references': references(data.get('references', [])), 'state': 'draft', 'acceptedRevision': None}
            self.specs[record['id']] = record
            self.changed_specs.add(record['id'])
            return {'spec': self.spec_view(record)}
        if op == 'ticket.create':
            fields(data, {'mapId', 'title', 'body', 'acceptanceCriteria', 'labels', 'priority', 'authority', 'references', 'specId', 'questionIds'}, {'title'})
            if len(self.tickets) >= 5000:
                fail('validation', 'Workspace ticket limit reached')
            record = {**self.new_record(kind), 'mapId': self.map_id(data.get('mapId')), 'title': '', 'body': '', 'acceptanceCriteria': '',
                      'labels': [], 'priority': 2, 'authority': None, 'references': [], 'progress': '', 'wait': '', 'state': 'backlog',
                      'sources': self.snapshot(data.get('specId'), data.get('questionIds', [])), 'needsSourceReview': False,
                      'sourceReview': None, 'completion': None, 'startedAt': None}
            record.update(self.ticket_patch({key: value for key, value in data.items() if key not in {'mapId', 'specId', 'questionIds'}}))
            self.tickets[record['id']] = record
            self.changed_tickets.add(record['id'])
            self._satisfaction = None
            return {'ticket': self.ticket_view(record)}
        extra, required = {
            'spec.update': ({'patch'}, {'patch'}), 'spec.approve': ({'questionSources', 'authority'}, {'questionSources', 'authority'}),
            'ticket.update': ({'patch'}, {'patch'}), 'ticket.link': ({'specId', 'questionIds', 'reason'}, {'specId', 'questionIds'}),
            'ticket.sources.acknowledge': ({'sources', 'note', 'authority'}, {'sources', 'note', 'authority'}),
            'ticket.transition': ({'to', 'reason', 'completion'}, {'to'}), 'ticket.wait.set': ({'reason'}, {'reason'}),
            'ticket.wait.clear': (set(), set()),
        }[op]
        fields(data, {kind + 'Id', 'expectedRev', 'claimToken', 'fence'} | extra, {kind + 'Id', 'expectedRev'} | required)
        record = adapter.get(data[kind + 'Id'])
        adapter.expected(record, data['expectedRev'])
        adapter.authorize(record, actor, data)
        if kind == 'spec':
            result = self.mutate_spec(op, record, data)
        else:
            result = self.mutate_ticket(op, record, data, actor)
        adapter.touch(record)
        return {kind: adapter.view(record), **result}

    def mutate_spec(self, op, spec, data):
        if op == 'spec.update':
            patch = fields(data['patch'], {'title', 'markdown', 'mapId', 'questionIds', 'references'})
            if not patch:
                fail('validation', 'Patch must not be empty')
            clean = {}
            for key, value in patch.items():
                if key in {'title', 'markdown'}:
                    clean[key] = text(value, key, 300 if key == 'title' else 50000, key != 'title')
                elif key == 'references':
                    clean[key] = references(value)
                elif key == 'mapId':
                    clean[key] = self.map_id(value)
            clean['questionIds'] = self.declared_questions(patch.get('questionIds', spec['questionIds']), clean.get('mapId', spec['mapId']))
            if any(spec[key] != value for key, value in clean.items()):
                spec.update(clean)
                spec['state'] = 'draft'
                self.invalidate_specs({spec['id']}, revoke_specs=False)
            return {}
        text(spec['title'], 'title', 300, False)
        text(spec['markdown'], 'markdown', 50000, False)
        sources = self.exact_question_sources(data['questionSources'], spec['questionIds'])
        accepted_authority = authority(data['authority'])
        number = max((number for key, number in self.revisions if key == spec['id']), default=0) + 1
        revision = {'specId': spec['id'], 'revision': number, 'title': spec['title'], 'markdown': spec['markdown'], 'mapId': spec['mapId'],
                    'questionSources': sources, 'references': spec['references'], 'authority': accepted_authority, 'acceptedAt': self.tx.now}
        self.revisions[(spec['id'], number)] = revision
        self.new_revisions.append(revision)
        spec.update(state='approved', acceptedRevision=number)
        self.invalidate_specs({spec['id']}, revoke_specs=False)
        return {'revision': revision}

    def ticket_patch(self, patch):
        fields(patch, {'title', 'body', 'acceptanceCriteria', 'labels', 'priority', 'progress', 'references', 'authority'})
        if not patch:
            fail('validation', 'Patch must not be empty')
        clean = {}
        for key, value in patch.items():
            if key in {'title', 'body', 'acceptanceCriteria', 'progress'}:
                clean[key] = text(value, key, 300 if key == 'title' else 30000, key != 'title')
            elif key == 'labels':
                clean[key] = labels(value)
            elif key == 'priority':
                clean[key] = integer(value, 'priority', 0, 4)
            elif key == 'references':
                clean[key] = references(value)
            else:
                clean[key] = authority(value, optional=True)
        return clean

    def require_ready(self, ticket):
        view = self.ticket_view(ticket)
        if not self.content_ready(ticket) or ticket['needsSourceReview'] or ticket['wait'] or view['sourceIssues'] or view['blockedBy']:
            fail('not_ready', 'Ticket needs body, acceptance criteria, authority, current sources, satisfied prerequisites, and no wait or pending source review', current=view)

    def mutate_ticket(self, op, ticket, data, actor):
        if op == 'ticket.update':
            patch = self.ticket_patch(data['patch'])
            substantive = any(key in {'title', 'body', 'acceptanceCriteria', 'authority'} and ticket[key] != value for key, value in patch.items())
            if ticket['state'] == 'done' and set(patch) - {'labels', 'priority'}:
                fail('not_ready', 'Reopen Done work before editing its content')
            if substantive and ticket['state'] in {'in-progress', 'review'}:
                fail('not_ready', 'Return the ticket to Backlog before changing execution scope')
            if substantive and ticket['state'] == 'ready':
                ticket['state'] = 'backlog'
            ticket.update(patch)
        elif op == 'ticket.link':
            if ticket['state'] == 'done':
                fail('not_ready', 'Reopen Done work before changing sources')
            if ticket['state'] in {'in-progress', 'review'}:
                text(data.get('reason'), 'reason', 4000, False)
            elif 'reason' in data:
                text(data['reason'], 'reason', 4000)
            sources = self.snapshot(data['specId'], data['questionIds'])
            if ticket['sources'] != sources:
                ticket['sources'] = sources
                if self.has_work(ticket):
                    ticket['needsSourceReview'] = True
                self.invalidate_tickets(dependency=self.descendants({ticket['id']}))
        elif op == 'ticket.sources.acknowledge':
            if ticket['state'] == 'done':
                fail('not_ready', 'Reopen Done work before reviewing sources')
            supplied = fields(data['sources'], {'spec', 'questions'}, {'spec', 'questions'})
            expected = ticket['sources']
            questions = self.exact_question_sources(supplied['questions'], [item['questionId'] for item in expected['questions']])
            spec_source = None
            if expected['spec']:
                fields(supplied['spec'], {'specId', 'revision'}, {'specId', 'revision'})
                identity(supplied['spec']['specId'], 'specId')
                integer(supplied['spec']['revision'], 'revision', 1)
                spec = self.spec.get(expected['spec']['specId'])
                spec_source = {'specId': spec['id'], 'revision': spec['acceptedRevision']}
                if not self.usable_spec(spec) or supplied['spec'] != spec_source:
                    fail('not_ready', 'Spec source snapshot is not currently approved')
            elif supplied['spec'] is not None:
                fail('validation', 'Source review cannot add a spec')
            if self.ticket_view(ticket)['blockedBy']:
                fail('not_ready', 'All prerequisites must satisfy their dependencies before source review')
            note = text(data['note'], 'note', 30000, False)
            reviewed_authority = authority(data['authority'])
            ticket['sources'] = {'spec': spec_source, 'questions': questions}
            ticket['sourceReview'] = {'note': note, 'authority': reviewed_authority, 'reviewedAt': self.tx.now}
            ticket['needsSourceReview'] = False
        elif op == 'ticket.transition':
            target = text(data['to'], 'to', 30, False)
            prior = ticket['state']
            if target not in TRANSITIONS[prior]:
                fail('not_ready', 'Illegal ticket transition')
            if prior == 'done' or (prior == 'review' and target == 'in-progress'):
                text(data.get('reason'), 'reason', 4000, False)
            elif 'reason' in data:
                text(data['reason'], 'reason', 4000)
            if target != 'backlog':
                self.require_ready(ticket)
            if target == 'done':
                evidence = fields(data.get('completion'), {'markdown', 'references'}, {'markdown', 'references'})
                ticket['completion'] = {'markdown': text(evidence['markdown'], 'completion.markdown', 50000, False),
                                        'references': references(evidence['references']), 'completedAt': self.tx.now, 'actor': actor}
            elif 'completion' in data:
                fail('validation', 'Completion evidence is only accepted when moving to Done')
            ticket['state'] = target
            if target == 'in-progress' and ticket.get('startedAt') is None:
                ticket['startedAt'] = self.tx.now
            if prior == 'done':
                ticket['completion'] = None
                self.invalidate_tickets(dependency=self.descendants({ticket['id']}))
            if target in {'review', 'done'}:
                self.tx.revoke(ticket)
        elif op == 'ticket.wait.set':
            if ticket['state'] == 'done':
                fail('not_ready', 'Reopen Done work before setting a wait')
            ticket['wait'] = text(data['reason'], 'reason', 2000, False)
        elif op == 'ticket.wait.clear':
            ticket['wait'] = ''
        return {}

    def mutate_relationship(self, op, data):
        required = {'kind', 'from', 'to', 'expectedFromRev', 'expectedToRev'}
        fields(data, required, required)
        source, target = self.ticket.get(data['from']), self.ticket.get(data['to'])
        self.ticket.expected(source, data['expectedFromRev'])
        self.ticket.expected(target, data['expectedToRev'])
        kind = data['kind']
        if kind not in KINDS:
            fail('validation', 'Unknown relationship kind')
        if source['id'] == target['id']:
            fail('validation', 'A ticket cannot link to itself')
        source_id, target_id = source['id'], target['id']
        if kind == 'related':
            source_id, target_id = sorted((source_id, target_id))
        edge = (kind, source_id, target_id)
        if op == 'ticket.relationship.add':
            if edge in self.edges:
                fail('validation', 'Relationship already exists')
            if kind in {'blocks', 'parent'} and source_id in self.descendants({target_id}, kind):
                fail('cycle', 'Relationship would create a cycle')
            if len(self.edges) + len(self.tx.edges) >= 50000:
                fail('validation', 'Workspace relationship limit reached')
            self.edges.add(edge)
            self.db.execute('INSERT INTO ticket_relationships VALUES (?,?,?)', edge)
        else:
            if edge not in self.edges:
                fail('not_found', 'Relationship not found')
            self.edges.remove(edge)
            self.db.execute('DELETE FROM ticket_relationships WHERE kind=? AND source=? AND target=?', edge)
        if kind == 'blocks':
            self.invalidate_tickets(dependency={target_id})
        self.ticket.touch(source)
        self.ticket.touch(target)
        return {'from': self.ticket_view(source), 'to': self.ticket_view(target), 'relationships': self.relationships()}

    def flush(self, actor):
        for key in self.changed_specs:
            record = self.specs[key]
            self.db.execute('INSERT INTO specs VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET map_id=excluded.map_id,data=excluded.data', (key, record['mapId'], canonical(record)))
            self.db.execute('INSERT INTO history VALUES (?,?,?,?)', (key, record['rev'], canonical(actor), canonical(self.spec_view(record))))
        for revision in self.new_revisions:
            self.db.execute('INSERT INTO spec_revisions VALUES (?,?,?)', (revision['specId'], revision['revision'], canonical(revision)))
        for key in self.changed_tickets:
            record = self.tickets[key]
            spec_id = record['sources']['spec']['specId'] if record['sources']['spec'] else None
            self.db.execute('INSERT INTO tickets VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET map_id=excluded.map_id,spec_id=excluded.spec_id,data=excluded.data', (key, record['mapId'], spec_id, canonical(record)))
            self.db.execute('INSERT INTO history VALUES (?,?,?,?)', (key, record['rev'], canonical(actor), canonical(self.ticket_view(record))))
