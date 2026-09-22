import React, { useEffect, useRef, useState } from 'react';
import { Icon } from './ui.jsx';
import { METHODS } from './detail.jsx';
import { useDraft } from './client.js';

export function CreateDialog({ type, workspaceId, mapId, onClose, mutate, busy, onCreated }) {
  const ref = useRef(null);
  const isMap = type === 'map';
  const draftKey = `wayfinder:create:${workspaceId}:${isMap ? 'map' : mapId}`;
  const [draft, setDraft, storageFailed] = useDraft(draftKey);
  const values = draft || { title: '', destination: '', scope: '', method: 'grilling', body: '' };
  const [error, setError] = useState('');
  const change = (key, value) => setDraft({ ...values, [key]: value });
  useEffect(() => { const dialog = ref.current; if (!dialog.open) dialog.showModal(); return () => dialog.close(); }, []);
  async function submit(event) {
    event.preventDefault(); setError('');
    const input = isMap ? { title: values.title, destination: values.destination, scope: values.scope } : { mapId, title: values.title, method: values.method, body: values.body };
    try { await mutate(`${type}.create`, input, value => onCreated(isMap ? value.map : value.question), { draft: { key: draftKey, submitted: values } }); }
    catch (problem) { setError(problem.message); }
  }
  return <dialog ref={ref} className="new-dialog" onCancel={onClose} aria-labelledby="create-title"><form onSubmit={submit}><div className="section-heading"><h2 id="create-title">New {type}</h2><button type="button" className="icon-button" aria-label={`Close new ${type}`} onClick={onClose}><Icon name="close"/></button></div><p className="muted">{isMap ? 'Give this effort a name, a destination, and an explicit scope.' : 'What needs an answer before this work can move forward?'}</p><label>{isMap ? 'Map name' : 'Question'}<input autoFocus disabled={busy} required maxLength={300} value={values.title} onChange={event => change('title', event.target.value)}/></label>{isMap ? <><label>Destination<textarea disabled={busy} required value={values.destination} onChange={event => change('destination', event.target.value)}/></label><label>Scope<textarea disabled={busy} required value={values.scope} onChange={event => change('scope', event.target.value)} placeholder="What work does this map cover?"/></label></> : <><label>Method<select disabled={busy} value={values.method} onChange={event => change('method', event.target.value)}>{Object.entries(METHODS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Description<textarea disabled={busy} value={values.body} onChange={event => change('body', event.target.value)}/></label></>}{error ? <p className="form-error" role="alert">{error}</p> : null}{storageFailed ? <p className="form-error">Draft storage is unavailable. Closing this form keeps the draft for this page, but a page reload may lose it.</p> : null}<div className="editor-actions"><button type="button" className="button" onClick={onClose}>Keep draft and close</button><button disabled={busy} className="button primary" type="submit">Create {type}</button></div></form></dialog>;
}
