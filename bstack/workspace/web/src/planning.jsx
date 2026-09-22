import React, { useEffect, useState } from 'react';
import { Editor, Icon, Markdown } from './ui.jsx';

export const STATES = { backlog: 'Backlog', ready: 'Ready', 'in-progress': 'In progress', review: 'Review', done: 'Done' };
export const MOVES = { backlog: ['ready'], ready: ['backlog', 'in-progress'], 'in-progress': ['backlog', 'review'], review: ['in-progress', 'done'], done: ['backlog'] };
export { lines } from './planning-values.js';
export const authorityDraft = authority => authority || { kind: 'human', decider: '', confirmation: '' };
export function AuthorityFields({ value, onChange, disabled }) {
  return <fieldset className="planning-fields authority-fields" disabled={disabled}><legend>Authority</legend><p className="muted content-note">Record the approval that covers this scope.</p><label>Authority type<select value={value.kind} onChange={event => onChange({ kind: event.target.value, decider: value.decider || '', ...(event.target.value === 'human' ? { confirmation: '' } : { scope: '', grantReference: '' }) })}><option value="human">Human confirmation</option><option value="delegated">Explicit delegation</option></select></label><label>Decider<input required value={value.decider} onChange={event => onChange({ ...value, decider: event.target.value })}/></label>{value.kind === 'human' ? <label>Confirmation<input required value={value.confirmation || ''} onChange={event => onChange({ ...value, confirmation: event.target.value })}/></label> : <><label>Delegated scope<textarea required value={value.scope || ''} onChange={event => onChange({ ...value, scope: event.target.value })}/></label><label>Grant reference<input required value={value.grantReference || ''} onChange={event => onChange({ ...value, grantReference: event.target.value })}/></label></>}</fieldset>;
}
export function Authority({ value }) {
  return value ? <div className="authority"><span>Decider: {value.decider}</span><span>{value.kind === 'human' ? `Confirmation: ${value.confirmation}` : `Delegated scope: ${value.scope}`}</span>{value.grantReference ? <span>Grant: {value.grantReference}</span> : null}</div> : <p className="muted content-note">No authority recorded yet.</p>;
}
export function References({ values = [] }) {
  return values.length ? <ul className="artifact-references">{values.map((value, index) => <li key={`${index}:${value}`}><code>{value}</code></li>)}</ul> : <p className="muted content-note">No artifact references.</p>;
}
export function PlanningConflict({ draft, item, onReload, onMerge, mergeLabel }) {
  if (!draft || draft.baseRev === item.rev) return null;
  return <div className="conflict" role="alert"><h3>Saved work changed</h3><p>Your draft started at revision {draft.baseRev}. The saved record is now revision {item.rev}. Your draft is preserved.</p><details><summary>Compare saved revision {item.rev}</summary><h3>{item.title}</h3><Markdown value={item.body ?? item.markdown}/>{item.acceptanceCriteria ? <><h3>Acceptance criteria</h3><Markdown value={item.acceptanceCriteria}/></> : null}<p>State: {STATES[item.state] || item.state}. Progress: {item.progress || 'None'}.</p>{item.labels ? <p>Labels: {item.labels.join(', ') || 'None'} · Priority {item.priority}</p> : null}{item.questionIds ? <p>Map: {item.mapId || 'Workspace-wide'} · Source questions: {item.questionIds.join(', ') || 'None'}</p> : null}<Authority value={item.authority}/><References values={item.references}/></details><div className="editor-actions">{onReload ? <button type="button" className="button" onClick={onReload}>Reload saved text</button> : null}{onMerge ? <button type="button" className="button" onClick={onMerge}>{mergeLabel || `Use revision ${item.rev} for my draft`}</button> : null}</div></div>;
}
export function SourcePicker({ questions, maps, questionIds, onChange, mapId = null, disabled }) {
  const choices = questions.filter(question => !mapId || question.mapId === mapId || questionIds.includes(question.id));
  return <label>Planning questions<select multiple size={Math.min(6, Math.max(2, choices.length))} disabled={disabled} value={questionIds} onChange={event => onChange([...event.target.selectedOptions].map(option => option.value))}>{choices.map(question => <option key={question.id} value={question.id}>{maps.find(map => map.id === question.mapId)?.title || question.mapId} / {question.title}{mapId && question.mapId !== mapId ? ' · different map' : ''} ({question.state === 'resolved' ? `answer ${question.answer?.revision ?? '?'}` : question.state})</option>)}</select><span className="muted content-note">Optional. Select the decisions this work relies on. Use Ctrl or Command to select several.</span></label>;
}
export function currentSources(sources, specs, questions) {
  return { spec: sources.spec ? { specId: sources.spec.specId, revision: specs.find(spec => spec.id === sources.spec.specId)?.usableApproval ? specs.find(spec => spec.id === sources.spec.specId).acceptedRevision : null } : null,
    questions: sources.questions.map(source => { const question = questions.find(question => question.id === source.questionId); return { questionId: source.questionId, answerId: question?.state === 'resolved' ? question.answer?.id ?? null : null, revision: question?.state === 'resolved' ? question.answer?.revision ?? null : null }; }) };
}
function sourceVersion(value, kind) {
  const revision = typeof value === 'object' ? value?.revision : value;
  return revision == null ? kind === 'spec' ? 'No usable approval' : 'No accepted answer' : `${kind === 'spec' ? 'Approval' : 'Answer'} revision ${revision}`;
}
export function SourceVersions({ sources, questions = [], specs = [] }) {
  const entries = Array.isArray(sources) ? sources.map(source => ({ ...source, kind: 'question' })) : [...(sources.spec ? [{ ...sources.spec, kind: 'spec' }] : []), ...sources.questions.map(source => ({ ...source, kind: 'question' }))];
  return entries.length ? <ul className="source-versions">{entries.map(source => <li key={source.questionId || source.specId}><strong>{source.kind === 'spec' ? specs.find(spec => spec.id === source.specId)?.title || 'Linked spec' : questions.find(question => question.id === source.questionId)?.title || 'Source question'}</strong><span>{sourceVersion(source, source.kind)}</span><span className="mono">{source.questionId || source.specId}</span>{source.kind === 'question' && questions.some(question => question.id === source.questionId && question.state === 'resolved' && question.answer?.id === source.answerId && question.answer?.revision === source.revision) ? <details><summary>Read accepted answer</summary><Markdown value={questions.find(question => question.id === source.questionId).answer.markdown}/></details> : null}</li>)}</ul> : <p className="muted content-note">No planning sources linked.</p>;
}
export function SourceIssues({ issues = [] }) {
  return issues.length ? <div className="source-issues" role="status"><h3>Planning sources changed</h3>{issues.map((issue, index) => <div key={`${issue.id}:${index}`}><p>{issue.reason}</p><span>Linked: {sourceVersion(issue.expected, issue.kind)}</span><span>Current: {sourceVersion(issue.current, issue.kind)}</span><span className="mono">{issue.id}</span></div>)}</div> : null;
}
export function ClaimNotice({ item, type, busy, act }) {
  return item.claim ? <div className="claim-notice"><h3>Claimed by {typeof item.claim.owner === 'object' ? item.claim.owner.id : item.claim.owner}</h3><p>Lease expires {new Date(typeof item.claim.expiresAt === 'number' ? item.claim.expiresAt * 1000 : item.claim.expiresAt).toLocaleString()}.</p><button type="button" disabled={busy} className="button" onClick={() => act(`${type}.claim.takeover`, { [`${type}Id`]: item.id, expectedRev: item.rev })}>Revoke claim to edit as human</button></div> : null;
}
export function DetailTop({ item, expanded, onExpand, onClose, noun }) {
  return <div className="detail-top">{expanded ? <button className="quiet-button" onClick={onExpand}><Icon name="arrow" className="back-arrow" size={14}/>Back to {noun === 'ticket' ? 'Kanban' : 'specs'}</button> : null}<span className="mono" title={item.id}>{item.id}</span><span className="muted">/ revision {item.rev}</span><span className="spacer"/><button className="icon-button" aria-label={expanded ? `Restore ${noun} detail` : `Expand ${noun}`} title={expanded ? 'Restore detail' : 'Expand detail'} onClick={onExpand}><Icon name="expand" size={16}/></button>{!expanded ? <button className="icon-button" aria-label={`Close ${noun} detail`} onClick={onClose}><Icon name="close" size={16}/></button> : null}</div>;
}
export function TicketFlags({ ticket }) {
  return <div className="ticket-flags">{ticket.blockedBy?.length ? <span className="ticket-flag">Blocked · {ticket.blockedBy.length}</span> : null}{ticket.wait ? <span className="ticket-flag"><Icon name="clock" size={11}/>Waiting</span> : null}{ticket.sourceIssues?.length ? <span className="ticket-flag">Stale sources</span> : null}{ticket.needsSourceReview ? <span className="ticket-flag">Source review</span> : null}{ticket.claim ? <span className="ticket-flag">Claimed</span> : null}</div>;
}
export function TicketHistory({ item, query }) {
  const [open, setOpen] = useState(false), [history, setHistory] = useState([]), [error, setError] = useState(''), [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setError('');
    query('ticket.read', { ticketId: item.id }).then(value => { if (active) setHistory(value.history || []); }).catch(problem => { if (active) setError(problem.message); });
    return () => { active = false; };
  }, [open, item.id, item.rev, query, retry]);
  return <details className="answer-history" open={open} onToggle={event => setOpen(event.currentTarget.open)}><summary>Ticket history</summary>{error ? <p className="form-error" role="alert">{error}<button className="button" onClick={() => setRetry(value => value + 1)}>Retry history</button></p> : null}{open && history.toSorted((a, b) => b.rev - a.rev).map((entry, index) => <details className="history-record" key={entry.rev || index}><summary>Revision {entry.rev} · {STATES[entry.state] || entry.state}</summary><h3>{entry.title}</h3><Markdown value={entry.body}/>{entry.acceptanceCriteria ? <><h3>Acceptance criteria</h3><Markdown value={entry.acceptanceCriteria}/></> : null}{entry.progress ? <><h3>Progress</h3><Markdown value={entry.progress}/></> : null}<Authority value={entry.authority}/><References values={entry.references}/>{entry.completion ? <><h3>Completion evidence</h3><Markdown value={entry.completion.markdown}/><References values={entry.completion.references}/></> : null}{entry.sourceReview ? <><h3>Source review</h3><Markdown value={entry.sourceReview.note}/></> : null}<span className="muted">Saved {new Date(entry.updatedAt * 1000).toLocaleString()}</span></details>)}{open && !error && !history.length ? <p className="muted">No earlier changes.</p> : null}</details>;
}
