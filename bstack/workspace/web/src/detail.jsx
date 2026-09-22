import React, { useEffect, useState } from 'react';
import { Editor, Icon, Markdown, Status } from './ui.jsx';
import { useDraft } from './client.js';

export const METHODS = { grilling: 'Grilling', research: 'Research', prototype: 'Prototype', 'prerequisite-task': 'Prerequisite task' };
function currentDraft(item) {
  return { baseRev: item.rev, title: item.title, body: item.body, method: item.method, priority: item.priority, progress: item.progress };
}
function Conflict({ draft, item, onReload, onMerge, answer = false }) {
  if (!draft || draft.baseRev === item.rev) return null;
  return <div className="conflict" role="alert"><h3>Saved work changed</h3><p>Your draft started at revision {draft.baseRev}. The saved question is now revision {item.rev}. Your draft is still here.</p><details><summary>Compare saved revision {item.rev}</summary><strong>{item.title}</strong><Markdown value={answer ? item.answer?.markdown || 'No accepted answer.' : item.body}/><p>Method: {METHODS[item.method]} · Priority: {item.priority} · Progress: {item.progress || 'None'}</p></details><p>Edit your draft to merge the changes, then use the current revision. Saving stays separate.</p><div className="editor-actions"><button className="button" type="button" onClick={onReload}>Reload saved text</button><button className="button" type="button" onClick={onMerge}>Use revision {item.rev} for my draft</button></div></div>;
}
function AnswerHistory({ item, query }) {
  const [open, setOpen] = useState(false);
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true); setError('');
    query('question.read', { questionId: item.id }).then(value => {
      if (active) setAnswers(value.answers);
    }).catch(problem => { if (active) setError(problem.message); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [open, item.id, item.rev, query, retry]);
  return <details className="answer-history" open={open} onToggle={event => setOpen(event.currentTarget.open)}><summary>Answer history</summary>{open ? <>
    {loading ? <p className="muted" role="status">Loading answer history…</p> : null}
    {error ? <div className="form-error" role="alert">{error}<button type="button" className="button" onClick={() => setRetry(value => value + 1)}>Retry history</button></div> : null}
    {!loading && !error && !answers.length ? <p className="muted">No answers have been accepted yet.</p> : null}
    {answers.toSorted((a, b) => b.revision - a.revision).map(answer => <article key={answer.id}><div className="section-heading"><h3>Answer revision {answer.revision}</h3><span>{answer.id === item.answer?.id && item.state === 'resolved' ? 'Currently accepted' : 'Previously accepted'}</span></div><Markdown value={answer.markdown}/><div className="authority"><span>Decider: {answer.authority.decider}</span><span>{answer.authority.kind === 'human' ? `Human confirmation: ${answer.authority.confirmation}` : `Delegated scope: ${answer.authority.scope}`}</span>{answer.authority.grantReference ? <span>Grant: {answer.authority.grantReference}</span> : null}{answer.references?.length ? <span>References: {answer.references.join(', ')}</span> : null}<span>Accepted {new Date(answer.acceptedAt * 1000).toLocaleString()}</span></div></article>)}
  </> : null}</details>;
}
export function Detail({ workspaceId, item, map, items, links, onSelect, mutate, query, busy, close, expanded, onExpand }) {
  const draftKey = `wayfinder:draft:${workspaceId}:${map.id}:${item.id}`;
  const [draft, setDraft, draftStorageFailed] = useDraft(draftKey);
  const [answerDraft, setAnswerDraft, answerStorageFailed] = useDraft(`${draftKey}:answer`);
  const [newLabel, setNewLabel] = useState('');
  const [waitReason, setWaitReason] = useState(item.wait || '');
  const [waitOpen, setWaitOpen] = useState(false);
  const [linkOpen, setLinkOpen] = useState(false);
  const [kind, setKind] = useState('blocks');
  const [target, setTarget] = useState('');
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState('');
  const editing = Boolean(draft);
  const blockers = (item.blockedBy || []).map(id => items.find(other => other.id === id)).filter(Boolean);
  const connections = links.filter(link => link.from === item.id || link.to === item.id);
  const resolved = item.state === 'resolved';
  async function act(op, input, done, completion) {
    setError(null); setSaved('');
    try { return await mutate(op, input, value => { done?.(value); setSaved('Saved'); }, completion); }
    catch (problem) { setError(problem); }
  }
  function update(patch, done) { return act('question.update', { questionId: item.id, expectedRev: item.rev, patch }, done); }
  function lifecycle(op) { return act(`question.${op}`, { questionId: item.id, expectedRev: item.rev }); }
  function changeDraft(patch) { setDraft({ ...draft, ...patch }); }
  function changeAnswer(patch) { setAnswerDraft({ ...answerDraft, ...patch }); }
  function newAnswer() { return { baseRev: item.rev, markdown: '', decider: '', confirmation: '', references: '' }; }
  return <section className="detail" aria-label={`Details for ${item.id}`}>
    <div className="detail-top">{expanded ? <button className="quiet-button" onClick={onExpand}><Icon name="arrow" className="back-arrow" size={14}/>Back to Wayfinder</button> : null}<span className="mono" title={item.id}>{item.id}</span><span className="muted">/ revision {item.rev}</span><span className="spacer"/>{!expanded ? <button className="icon-button" aria-label="Expand question" title="Expand question" onClick={onExpand}><Icon name="expand" size={16}/></button> : null}{close && !expanded ? <button className="icon-button" aria-label="Hide details" onClick={close}><Icon name="close" size={16}/></button> : null}</div>
    <div className="detail-content">
      <div className="detail-kicker"><span>{METHODS[item.method]} question</span><Status value={item.status}/></div>
      {editing ? <input disabled={busy} className="title-edit" aria-label="Question title" value={draft.title} onChange={event => changeDraft({title: event.target.value})}/> : <h2>{item.title}</h2>}
      <div className="metadata"><span>Revision {item.rev}</span><span>Priority {item.priority}</span><span>{item.progress || 'No progress note'}</span></div>
      {item.claim ? <div className="claim-notice"><h3>Claimed by {typeof item.claim.owner === 'object' ? item.claim.owner.id : item.claim.owner}</h3><p>Lease expires {new Date(typeof item.claim.expiresAt === 'number' ? item.claim.expiresAt * 1000 : item.claim.expiresAt).toLocaleString()}. Saving does not take over this claim.</p><button disabled={busy} className="button" onClick={() => act('claim.takeover', { questionId: item.id, expectedRev: item.rev })}>Revoke claim to edit as human</button></div> : null}
      {error ? <div className="form-error action-error" role="alert">{error.message}{error.code === 'claimed' ? ' Review the claim above before taking over.' : ''}</div> : null}
      {saved ? <p className="save-status" role="status">{saved}</p> : null}
      {draftStorageFailed || answerStorageFailed ? <p className="form-error" role="alert">Browser draft storage is unavailable. You can switch questions, but a page reload may lose this draft. Save or copy it before reloading.</p> : null}
      {blockers.length ? <div className="blocker-callout"><span className="small-label">Waiting on {blockers.length} {blockers.length === 1 ? 'answer' : 'answers'}</span>{blockers.map(blocker => <button key={blocker.id} onClick={() => onSelect(blocker.id)}><span>{blocker.title}</span><Icon name="arrow" size={15}/></button>)}</div> : null}
      {item.wait ? <div className="blocker-callout"><span className="small-label">Explicit wait</span><p>{item.wait}</p></div> : null}
      <div className="section-heading"><h3>Description</h3>{!editing ? <button disabled={busy || resolved} className="quiet-button" title={resolved ? 'Reopen before changing accepted question content' : undefined} onClick={() => setDraft(currentDraft(item))}><Icon name="edit" size={13}/>Edit</button> : <span className="draft-label">Draft · based on revision {draft.baseRev}</span>}</div>
      {editing ? <>
        <Editor value={draft.body} onChange={body => changeDraft({body})} disabled={busy}/>
        <div className="edit-metadata"><label>Method<select disabled={busy} value={draft.method} onChange={event => changeDraft({method: event.target.value})}>{Object.entries(METHODS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Priority<input disabled={busy} type="number" min="0" max="4" value={draft.priority} onChange={event => changeDraft({priority: Number(event.target.value)})}/></label><label className="wide">Progress note<input disabled={busy} value={draft.progress || ''} onChange={event => changeDraft({progress: event.target.value})}/></label></div>
        <Conflict draft={draft} item={item} onReload={() => setDraft(currentDraft(item))} onMerge={() => changeDraft({baseRev: item.rev})}/>
        <div className="editor-actions"><button disabled={busy} className="button" onClick={() => setDraft(null)}>Discard draft</button><button className="button primary" disabled={busy || resolved || !draft.title.trim() || draft.baseRev !== item.rev} onClick={() => act('question.update', { questionId: item.id, expectedRev: draft.baseRev, patch: { title: draft.title, body: draft.body, method: draft.method, priority: draft.priority, progress: draft.progress } }, undefined, { draft: { key: draftKey, submitted: draft } })}>Save changes</button></div>
      </> : <Markdown value={item.body || 'No description yet.'}/>}
      {resolved ? <p className="muted content-note">Reopen this question before editing its content. Dependent answers will need review.</p> : null}
      {item.answer ? <section className="accepted-answer"><div className="section-heading"><h3>{resolved ? 'Accepted answer' : 'Previous accepted answer'}</h3><span className="mono">answer revision {item.answer.revision}</span></div><Markdown value={item.answer.markdown}/><div className="authority"><span>Decider: {item.answer.authority.decider}</span><span>{item.answer.authority.kind === 'human' ? `Human confirmation: ${item.answer.authority.confirmation}` : `Delegated scope: ${item.answer.authority.scope}`}</span>{item.answer.authority.grantReference ? <span>Grant: {item.answer.authority.grantReference}</span> : null}{item.answer.references?.length ? <span>References: {item.answer.references.join(', ')}</span> : null}</div></section> : null}
      <AnswerHistory item={item} query={query}/>
      <div className="section-heading labels-heading"><h3>Labels</h3></div>
      <div className="labels">{item.labels.map(label => <span className="label" key={label}>{label}<button disabled={busy} aria-label={`Remove ${label} label`} onClick={() => update({ labels: item.labels.filter(value => value !== label) })}>×</button></span>)}</div>
      <form className="inline-form" onSubmit={event => { event.preventDefault(); if (newLabel.trim()) update({ labels: [...item.labels, newLabel.trim()] }, () => setNewLabel('')); }}><input disabled={busy} aria-label="New label" placeholder="Add a label…" value={newLabel} onChange={event => setNewLabel(event.target.value)}/><button disabled={busy || !newLabel.trim()} type="submit" className="icon-button" aria-label="Add label"><Icon name="plus" size={14}/></button></form>
      <div className="section-heading"><h3>Connections <span>{connections.length}</span></h3><button className="quiet-button" aria-expanded={linkOpen} onClick={() => setLinkOpen(!linkOpen)}><Icon name="plus" size={14}/>Connect</button></div>
      <div className="connections">{connections.map(link => {
        const other = items.find(value => value.id === (link.from === item.id ? link.to : link.from));
        if (!other) return null;
        const relationship = link.kind === 'related' ? 'Related to' : link.kind === 'parent' ? link.from === item.id ? 'Parent of' : 'Child of' : link.from === item.id ? 'Blocks' : 'Blocked by';
        return <div className="connection" key={`${link.from}-${link.kind}-${link.to}`}><button className="connection-main" onClick={() => onSelect(other.id)}><span className="relationship">{relationship}</span><span><Status value={other.status} text={false}/>{other.title}</span></button><button disabled={busy} className="remove-link" aria-label={`Remove ${relationship} connection to ${other.id}`} onClick={() => act('relationship.remove', { mapId: map.id, expectedMapRev: map.rev, ...link })}>×</button></div>;
      })}{!connections.length ? <p className="muted">No connections yet.</p> : null}</div>
      {linkOpen ? <form className="connection-form" onSubmit={event => { event.preventDefault(); act('relationship.add', { mapId: map.id, expectedMapRev: map.rev, from: item.id, to: target, kind }, () => setLinkOpen(false)); }}><select disabled={busy} aria-label="Connection type" value={kind} onChange={event => setKind(event.target.value)}><option value="blocks">This question blocks</option><option value="related">Related to</option><option value="parent">This question is parent of</option></select><select disabled={busy} required aria-label="Connect to item" value={target} onChange={event => setTarget(event.target.value)}><option value="">Choose a question</option>{items.filter(other => other.id !== item.id).map(other => <option key={other.id} value={other.id}>{other.title}</option>)}</select><button disabled={busy || !target} className="button" type="submit">Add connection</button></form> : null}
      <div className="detail-bottom">
        {resolved ? <button disabled={busy} className="button" onClick={() => lifecycle('reopen')}>Reopen question</button> : item.state === 'needs-review' ? <button disabled={busy} className="button primary" onClick={() => lifecycle('review')}>Review and return to open</button> : item.state === 'out-of-scope' ? <button disabled={busy} className="button" onClick={() => lifecycle('reopen')}>Return to open</button> : <button disabled={busy} className="button primary" onClick={() => setAnswerDraft(answerDraft || newAnswer())}><Icon name="check" size={15}/>Record answer</button>}
        {item.wait ? <button disabled={busy} className="quiet-button" onClick={() => act('wait.clear', { questionId: item.id, expectedRev: item.rev })}>Clear wait</button> : ['open', 'needs-review'].includes(item.state) ? <button disabled={busy} className="quiet-button" onClick={() => { setWaitReason(''); setWaitOpen(!waitOpen); }}>Set wait</button> : null}
        {item.state !== 'out-of-scope' ? <button disabled={busy} className="quiet-button" onClick={() => lifecycle('exclude')}>Mark out of scope</button> : null}
      </div>
      {waitOpen && ['open', 'needs-review'].includes(item.state) ? <form className="connection-form" onSubmit={event => { event.preventDefault(); act('wait.set', { questionId: item.id, expectedRev: item.rev, reason: waitReason }, () => setWaitOpen(false)); }}><label>Wait reason<input disabled={busy} required value={waitReason} onChange={event => setWaitReason(event.target.value)}/></label><button disabled={busy} type="submit" className="button">Save wait</button></form> : null}
      {answerDraft ? <form className="answer-form" onSubmit={event => { event.preventDefault(); act('question.resolve', { questionId: item.id, expectedRev: answerDraft.baseRev, answer: { markdown: answerDraft.markdown, authority: { kind: 'human', decider: answerDraft.decider, confirmation: answerDraft.confirmation }, references: answerDraft.references.split('\n').map(value => value.trim()).filter(Boolean) } }, undefined, { draft: { key: `${draftKey}:answer`, submitted: answerDraft } }); }}><div className="section-heading"><h3>Record an accepted answer</h3></div><p className="muted content-note">Record the decision and who confirmed it. The server checks prerequisites, waits, and claims before accepting.</p><Editor label="Answer Markdown" value={answerDraft.markdown} disabled={busy} onChange={markdown => changeAnswer({markdown})}/><label>Decider<input disabled={busy} required value={answerDraft.decider} onChange={event => changeAnswer({decider: event.target.value})} placeholder="Who made this decision?"/></label><label>Confirmation<input disabled={busy} required value={answerDraft.confirmation} onChange={event => changeAnswer({confirmation: event.target.value})} placeholder="How was this answer confirmed?"/></label><label>References, one per line<textarea disabled={busy} value={answerDraft.references} onChange={event => changeAnswer({references: event.target.value})}/></label><Conflict draft={answerDraft} item={item} answer onReload={() => setAnswerDraft({ ...newAnswer(), markdown: item.answer?.markdown || '' })} onMerge={() => changeAnswer({baseRev: item.rev})}/><div className="editor-actions"><button disabled={busy} className="button" type="button" onClick={() => setAnswerDraft(null)}>Discard answer draft</button><button className="button primary" type="submit" disabled={busy || !answerDraft.markdown.trim() || answerDraft.baseRev !== item.rev}>Accept answer and resolve</button></div></form> : null}
    </div>
  </section>;
}
