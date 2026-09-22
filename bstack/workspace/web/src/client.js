import { useCallback, useEffect, useRef, useState } from 'react';
import { draftStorageFailed, finishDraft, loadDraft, pendingRequest, readPending, recoveryDestination, sameDraft, saveDraft } from './recovery.js';

const DRAFT_FINISHED = 'wayfinder:draft-finished';

export function readLocal(key, fallback) {
  try { return JSON.parse(sessionStorage.getItem(key)) ?? fallback; } catch { return fallback; }
}
export function writeLocal(key, value) {
  try { if (value === null) sessionStorage.removeItem(key); else sessionStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; }
}
export function useDraft(key) {
  const [entry, setEntry] = useState(() => ({ key, value: loadDraft(key) }));
  const draft = entry.key === key ? entry.value : loadDraft(key);
  useEffect(() => {
    const finished = event => {
      const submitted = event.detail;
      if (submitted.key !== key) return;
      setEntry(current => current.key === key && sameDraft(current.value, submitted.submitted) ? { key, value: null } : current);
    };
    window.addEventListener(DRAFT_FINISHED, finished);
    return () => window.removeEventListener(DRAFT_FINISHED, finished);
  }, [key]);
  function update(value) {
    setEntry({ key, value });
    saveDraft(key, value);
  }
  return [draft, update, draftStorageFailed(key)];
}

class OperationError extends Error {
  constructor(error) { super(error.message); Object.assign(this, error); }
}
async function post(token, envelope) {
  let response;
  try {
    response = await fetch('/api/operation', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Wayfinder-Token': token },
      body: JSON.stringify(envelope), signal: AbortSignal.timeout(12000),
    });
  } catch { throw new OperationError({ code: 'transport', message: 'Connection interrupted. The request may have been saved. Retry this same request to check its result.' }); }
  let result;
  try { result = await response.json(); } catch { throw new OperationError({ code: 'transport', message: 'The server returned an unreadable response. Retry the same request to check whether it was saved.' }); }
  if (!result.ok) throw new OperationError({ ...(result.error || { code: 'server', message: `Request failed (${response.status}).` }), recoverable: response.status === 403 || response.status >= 500 });
  return result;
}

export function useWorkspace(route) {
  const screen = route.screen;
  const mapId = screen === 'map' ? route.mapId : '';
  const specId = screen === 'specs' ? route.specId : '';
  const selection = `${screen}:${mapId}:${specId}`;
  const [bootstrap, setBootstrap] = useState(null);
  const [maps, setMaps] = useState([]);
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(null);
  const [storageWarning, setStorageWarning] = useState('');
  const mutation = useRef(false);
  const pendingRef = useRef(null);
  const generation = useRef(0);
  const refreshFlight = useRef(null);
  const workspaceRef = useRef(null);
  const activeSelection = useRef(selection);
  activeSelection.current = selection;
  const init = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/bootstrap', { signal: AbortSignal.timeout(12000), cache: 'no-store' });
      const value = await response.json();
      if (!response.ok || !value.token || !value.workspace?.id) throw new Error(value.error?.message || 'Could not open the workspace.');
      const saved = workspaceRef.current === value.workspace.id && pendingRef.current ? pendingRef.current : readPending(readLocal(`wayfinder:pending:${value.workspace.id}`, null));
      if (workspaceRef.current !== value.workspace.id) { setMaps([]); setSnapshot(null); }
      workspaceRef.current = value.workspace.id;
      pendingRef.current = saved;
      setPending(saved);
      setBootstrap(value);
      setError('');
    } catch (problem) { setError(problem.message || 'Could not connect to Wayfinder.'); setLoading(false); }
  }, []);
  useEffect(() => { init(); }, [init]);
  const refresh = useCallback(async (foreground = false, force = false) => {
    if (!bootstrap) return;
    const key = `${bootstrap.token}:${selection}`;
    if (!force && refreshFlight.current?.key === key) return refreshFlight.current.promise;
    const ticket = ++generation.current;
    if (foreground) setLoading(true);
    const promise = (async () => {
      try {
        const planning = screen === 'board' || screen === 'specs';
        const operation = screen === 'board' ? { op: 'board.read', input: {} }
          : screen === 'specs' && specId ? { op: 'spec.read', input: { specId } }
          : mapId ? { op: 'map.read', input: { mapId } } : null;
        const [workspaceResult, selectedResult, specsResult, questionsResult] = await Promise.all([
          post(bootstrap.token, { op: 'workspace.read', input: {} }),
          operation ? post(bootstrap.token, operation) : Promise.resolve(null),
          planning ? post(bootstrap.token, { op: 'spec.search', input: {} }) : Promise.resolve(null),
          planning ? post(bootstrap.token, { op: 'question.search', input: {} }) : Promise.resolve(null),
        ]);
        if (ticket !== generation.current || selection !== activeSelection.current) return;
        setMaps(workspaceResult.value.maps);
        setSnapshot(planning ? { ...selectedResult?.value, screen, specs: specsResult.value.specs, questions: questionsResult.value.questions } : selectedResult?.value || null);
        setError('');
      } catch (problem) { if (ticket === generation.current) setError(problem.message); }
      finally { if (ticket === generation.current) setLoading(false); }
    })();
    refreshFlight.current = { key, ticket, promise };
    await promise;
    if (refreshFlight.current?.ticket === ticket) refreshFlight.current = null;
  }, [bootstrap, selection, screen, mapId, specId]);
  const query = useCallback(async (op, input) => {
    if (!bootstrap) throw new Error('The workspace is still connecting.');
    return (await post(bootstrap.token, { op, input })).value;
  }, [bootstrap]);
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useEffect(() => {
    refresh(true);
    const poll = setInterval(() => { if (!document.hidden) refresh(); }, 4000);
    const focus = () => refresh();
    window.addEventListener('focus', focus);
    return () => { clearInterval(poll); window.removeEventListener('focus', focus); generation.current++; };
  }, [refresh]);
  function persistPendingRequest(value) {
    pendingRef.current = value;
    setPending(value);
    if (bootstrap && !writeLocal(`wayfinder:pending:${bootstrap.workspace.id}`, value)) setStorageWarning('Browser recovery storage is unavailable. Keep this page open until the request result is confirmed.');
  }
  function confirmSavedRequest(record) {
    const draftResult = finishDraft(record);
    if (!draftResult.durable) setStorageWarning('The request was saved. Browser recovery storage is unavailable, so local draft recovery after reload cannot be guaranteed.');
    if (draftResult.draft && ['cleared', 'absent'].includes(draftResult.status)) window.dispatchEvent(new CustomEvent(DRAFT_FINISHED, { detail: draftResult.draft }));
    persistPendingRequest(null);
    return draftResult;
  }
  async function execute(record, onSuccess) {
    const { envelope } = record;
    mutation.current = true;
    setBusy(true);
    try {
      let result;
      try { result = await post(bootstrap.token, envelope); }
      catch (problem) { if (problem.code !== 'transport') throw problem; result = await post(bootstrap.token, envelope); }
      const draftResult = confirmSavedRequest(record);
      await refreshRef.current(false, true);
      onSuccess?.(result.value);
      return { value: result.value, destination: recoveryDestination(record, result.value), draftStatus: draftResult.status, op: envelope.op };
    } catch (problem) {
      if (problem.code === 'transport' || problem.recoverable) { persistPendingRequest(record); if (problem.recoverable) setError('Reconnect to the workspace, then retry the original request. Its request ID is preserved.'); }
      else { persistPendingRequest(null); await refreshRef.current(false, true); }
      throw problem;
    } finally { mutation.current = false; setBusy(false); }
  }
  async function mutate(op, input, onSuccess, completion = null) {
    if (!bootstrap) throw new Error('The workspace is still connecting.');
    if (mutation.current) throw new Error('Another save is still in progress.');
    if (pendingRef.current) throw new Error('Retry the interrupted request above before making another change.');
    const actorKey = `wayfinder:actor:${bootstrap.workspace.id}`;
    let actorId = readLocal(actorKey, null);
    if (!actorId) { actorId = `browser-${crypto.randomUUID()}`; writeLocal(actorKey, actorId); }
    const envelope = { op, input, requestId: crypto.randomUUID(), actor: { id: actorId, kind: 'human' } };
    const record = pendingRequest(envelope, completion);
    persistPendingRequest(record);
    return (await execute(record, onSuccess)).value;
  }
  async function retryPending() {
    if (!pendingRef.current || mutation.current) return;
    return execute(pendingRef.current);
  }
  return { bootstrap, maps, snapshot, loading, error, busy, pending, mutate, query, retryPending, storageWarning, reconnect: init, refresh: () => bootstrap ? refresh(true) : init() };
}
