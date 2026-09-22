import test from 'node:test';
import assert from 'node:assert/strict';
import { ticketMetadataChange } from '../src/ticket-editing.js';
import { pendingRequest, readPending, finishDraft, recoveryDestination, loadDraft, saveDraft } from '../src/recovery.js';

function storage(entries = []) {
  const values = new Map(entries.map(([key, value]) => [key, JSON.stringify(value)]));
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) };
}
const cases = [
  { op: 'map.create', key: 'wayfinder:create:workspace:map', draft: { title: 'Map', destination: 'Decision', scope: 'Local' }, input: { title: 'Map', destination: 'Decision', scope: 'Local' }, value: { map: { id: 'saved-map' } }, target: { mapId: 'saved-map', questionId: '' } },
  { op: 'question.create', key: 'wayfinder:create:workspace:saved-map', draft: { title: 'Question', method: 'research', body: 'Describe' }, input: { mapId: 'saved-map', title: 'Question', method: 'research', body: 'Describe' }, value: { question: { id: 'saved-question', mapId: 'saved-map' } }, target: { mapId: 'saved-map', questionId: 'saved-question' } },
  { op: 'question.update', key: 'wayfinder:draft:workspace:saved-map:saved-question', draft: { baseRev: 3, title: 'New title', body: 'New body', method: 'research', priority: 2, progress: '' }, input: { questionId: 'saved-question', expectedRev: 3, patch: { title: 'New title', body: 'New body', method: 'research', priority: 2, progress: '' } }, value: { question: { id: 'saved-question', mapId: 'saved-map', rev: 4 } }, target: { mapId: 'saved-map', questionId: 'saved-question' } },
  { op: 'question.resolve', key: 'wayfinder:draft:workspace:saved-map:saved-question:answer', draft: { baseRev: 4, markdown: 'Accepted', decider: 'Human', confirmation: 'Agreed', references: '' }, input: { questionId: 'saved-question', expectedRev: 4, answer: { markdown: 'Accepted', authority: { kind: 'human', decider: 'Human', confirmation: 'Agreed' }, references: [] } }, value: { question: { id: 'saved-question', mapId: 'saved-map', rev: 5 } }, target: { mapId: 'saved-map', questionId: 'saved-question' } },
  { op: 'ticket.create', key: 'wayfinder:create:workspace:ticket', draft: { title: 'Direct intake', body: 'Standalone', acceptanceCriteria: 'Works' }, input: { title: 'Direct intake', body: 'Standalone', acceptanceCriteria: 'Works' }, value: { ticket: { id: 'saved-ticket', mapId: null } }, target: { screen: 'board', ticketId: 'saved-ticket' } },
  { op: 'ticket.update', key: 'wayfinder:ticket:workspace:saved-ticket:content', draft: { baseRev: 3, title: 'Scope', body: 'Scoped work', acceptanceCriteria: 'Works' }, input: { ticketId: 'saved-ticket', expectedRev: 3, patch: { body: 'Scoped work' } }, value: { ticket: { id: 'saved-ticket', rev: 4 } }, target: { screen: 'board', ticketId: 'saved-ticket' } },
  { op: 'ticket.transition', key: 'wayfinder:ticket:workspace:saved-ticket:action', draft: { kind: 'transition', baseRev: 4, to: 'done', markdown: 'Review passed', references: 'report.md' }, input: { ticketId: 'saved-ticket', expectedRev: 4, to: 'done', completion: { markdown: 'Review passed', references: ['report.md'] } }, value: { ticket: { id: 'saved-ticket', rev: 5, state: 'done' } }, target: { screen: 'board', ticketId: 'saved-ticket' } },
  { op: 'spec.create', key: 'wayfinder:create:workspace:spec', draft: { title: 'Scope', markdown: 'Acceptance criteria' }, input: { title: 'Scope', markdown: 'Acceptance criteria' }, value: { spec: { id: 'saved-spec' } }, target: { screen: 'specs', specId: 'saved-spec' } },
  { op: 'spec.approve', key: 'wayfinder:spec:workspace:saved-spec:approval', draft: { baseRev: 2, authority: { kind: 'human', decider: 'Owner', confirmation: 'Accepted scope' }, questionSources: [{ questionId: 'question', answerId: 'answer', revision: 1 }] }, input: { specId: 'saved-spec', expectedRev: 2, questionSources: [{ questionId: 'question', answerId: 'answer', revision: 1 }], authority: { kind: 'human', decider: 'Owner', confirmation: 'Accepted scope' } }, value: { spec: { id: 'saved-spec', rev: 3, acceptedRevision: 1 } }, target: { screen: 'specs', specId: 'saved-spec' } },
];
for (const scenario of cases) {
  test(`${scenario.op} reload replay clears only its submitted draft and recovers destination`, () => {
    const envelope = { op: scenario.op, input: scenario.input, requestId: 'same-request-id', actor: { kind: 'human', id: 'local' } };
    const persisted = JSON.stringify(pendingRequest(envelope, { draft: { key: scenario.key, submitted: scenario.draft } }));
    const reloaded = readPending(JSON.parse(persisted));
    const local = storage([[scenario.key, scenario.draft], ['unrelated', { body: 'Leave this alone' }]]);
    const result = finishDraft(reloaded, local, new Map());
    assert.equal(result.status, 'cleared');
    assert.equal(local.getItem(scenario.key), null);
    assert.deepEqual(JSON.parse(local.getItem('unrelated')), { body: 'Leave this alone' });
    assert.deepEqual(reloaded.envelope, envelope);
    assert.deepEqual(recoveryDestination(reloaded, scenario.value), scenario.target);
    assert.equal(finishDraft(reloaded, local, new Map()).status, 'absent');
  });
}

test('newer persisted draft survives successful replay', () => {
  const scenario = cases[0];
  const record = pendingRequest({ op: scenario.op, input: scenario.input, requestId: 'one' }, { draft: { key: scenario.key, submitted: scenario.draft } });
  const newer = { ...scenario.draft, title: 'A different map' };
  const local = storage([[scenario.key, newer]]);
  assert.equal(finishDraft(record, local, new Map()).status, 'preserved');
  assert.deepEqual(JSON.parse(local.getItem(scenario.key)), newer);
});

test('pending completion is an immutable snapshot of request and draft', () => {
  const envelope = { op: 'map.create', requestId: 'one', input: { title: 'Submitted' } };
  const draft = { title: 'Submitted' };
  const record = pendingRequest(envelope, { draft: { key: 'draft', submitted: draft } });
  envelope.input.title = 'Later'; draft.title = 'Later';
  assert.equal(record.envelope.input.title, 'Submitted');
  assert.equal(record.completion.draft.submitted.title, 'Submitted');
});

test('unavailable browser storage keeps drafts across remounts and can reconcile saved work', () => {
  const denied = { getItem() { throw Error('blocked'); }, setItem() { throw Error('blocked'); }, removeItem() { throw Error('blocked'); } };
  const memory = new Map();
  const draft = { body: 'Unsaved text', baseRev: 2 };
  assert.equal(saveDraft('question-a', draft, denied, memory), false);
  loadDraft('question-b', denied, memory);
  assert.deepEqual(loadDraft('question-a', denied, memory), draft);
  const record = pendingRequest({ op: 'question.update', requestId: 'one', input: {} }, { draft: { key: 'question-a', submitted: draft } });
  const result = finishDraft(record, denied, memory);
  assert.equal(result.status, 'cleared');
  assert.equal(result.durable, false);
  assert.equal(loadDraft('question-a', denied, memory), null);
});

test('newer in-memory edit survives completion when its persistence failed', () => {
  const submitted = { body: 'Submitted' };
  const newer = { body: 'Newer draft' };
  const local = storage([['draft', submitted]]);
  const record = pendingRequest({ op: 'question.update', requestId: 'one', input: {} }, { draft: { key: 'draft', submitted } });
  const memory = new Map([['draft', newer]]);
  assert.equal(finishDraft(record, local, memory).status, 'preserved');
  assert.deepEqual(loadDraft('draft', local, memory), newer);
});

test('old envelopes replay unchanged without guessing draft ownership', () => {
  const envelope = { op: 'map.create', requestId: 'legacy', input: { title: 'Older request' } };
  const record = readPending(envelope);
  const local = storage([['draft', { title: 'New work' }]]);
  assert.deepEqual(record.envelope, envelope);
  assert.equal(finishDraft(record, local, new Map()).status, 'untracked');
  assert.notEqual(local.getItem('draft'), null);
});

for (const scenario of cases.filter(value => value.op.startsWith('ticket.') || value.op.startsWith('spec.'))) {
  test(`${scenario.op} recovery preserves edits made after the submitted revision`, () => {
    const record = pendingRequest({ op: scenario.op, input: scenario.input, requestId: 'uncertain-save' }, { draft: { key: scenario.key, submitted: scenario.draft } });
    const newer = { ...scenario.draft, localNote: 'User continued editing after connection loss' };
    const local = storage([[scenario.key, newer]]);
    const result = finishDraft(record, local, new Map());
    assert.equal(result.status, 'preserved');
    assert.deepEqual(JSON.parse(local.getItem(scenario.key)), newer);
    assert.deepEqual(recoveryDestination(record, scenario.value), scenario.target);
  });
}

test('external completion never converts an unfinished progress draft into a labels-only save', () => {
  const saved = { rev: 3, state: 'review', progress: 'Earlier progress', references: ['earlier.md'] };
  const draft = { baseRev: 3, labels: 'reviewed', priority: 2, progress: 'Unsaved verification findings', references: 'new-evidence.md' };
  assert.equal(ticketMetadataChange(saved, draft).patch.progress, 'Unsaved verification findings');
  const completed = { ...saved, rev: 4, state: 'done' };
  const rebasedDraft = { ...draft, baseRev: completed.rev };
  assert.deepEqual(ticketMetadataChange(completed, rebasedDraft), { requiresReopen: true, patch: null });
  const reopened = { ...completed, rev: 5, state: 'backlog' };
  assert.deepEqual(ticketMetadataChange(reopened, { ...draft, baseRev: 5 }).patch, { labels: ['reviewed'], priority: 2, progress: 'Unsaved verification findings', references: ['new-evidence.md'] });
});

test('Done labels-only edits remain possible when the draft contains no unsaved progress', () => {
  const saved = { rev: 4, state: 'done', progress: 'Verification completed', references: ['review.md'] };
  const draft = { baseRev: 4, labels: 'accepted, shipped', priority: 1, progress: saved.progress, references: saved.references.join('\n') };
  assert.deepEqual(ticketMetadataChange(saved, draft), { requiresReopen: false, patch: { labels: ['accepted', 'shipped'], priority: 1 } });
});
