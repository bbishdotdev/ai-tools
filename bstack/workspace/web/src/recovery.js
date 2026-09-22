export function pendingRequest(envelope, completion = null) {
  return JSON.parse(JSON.stringify({ version: 2, envelope, completion }));
}

export function readPending(value) {
  if (!value) return null;
  if (value.version === 2 && value.envelope?.requestId) return value;
  return value.requestId ? pendingRequest(value) : null;
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  return value;
}
export function sameDraft(left, right) {
  return JSON.stringify(canonical(left)) === JSON.stringify(canonical(right));
}

export function recoveryDestination(pending, value) {
  const op = pending.envelope.op;
  if (value.ticket && op.startsWith('ticket.')) return { screen: 'board', ticketId: value.ticket.id };
  if (value.spec && op.startsWith('spec.')) return { screen: 'specs', specId: value.spec.id };
  if (op === 'map.create') return { mapId: value.map.id, questionId: '' };
  if (value.question && op.startsWith('question.')) return { mapId: value.question.mapId, questionId: value.question.id };
  return null;
}

const draftCache = new Map();
const undurableDrafts = new Set();
export const draftStorageFailed = key => undurableDrafts.has(key);
export const browserStorage = {
  getItem: key => sessionStorage.getItem(key),
  setItem: (key, value) => sessionStorage.setItem(key, value),
  removeItem: key => sessionStorage.removeItem(key),
};
export function loadDraft(key, storage = browserStorage, cache = draftCache) {
  if (cache.has(key)) return cache.get(key);
  let value = null;
  try { value = JSON.parse(storage.getItem(key)); } catch { undurableDrafts.add(key); }
  cache.set(key, value);
  return value;
}
export function saveDraft(key, value, storage = browserStorage, cache = draftCache) {
  cache.set(key, value);
  try {
    if (value === null) storage.removeItem(key);
    else storage.setItem(key, JSON.stringify(value));
    undurableDrafts.delete(key);
    return true;
  } catch { undurableDrafts.add(key); return false; }
}
export function finishDraft(pending, storage = browserStorage, cache = draftCache) {
  const draft = pending.completion?.draft;
  if (!draft) return { status: 'untracked', durable: true };
  const memory = cache.get(draft.key);
  if (memory != null && !sameDraft(memory, draft.submitted)) return { status: 'preserved', draft, durable: !undurableDrafts.has(draft.key) };
  let stored;
  let durable = true;
  try { stored = JSON.parse(storage.getItem(draft.key)); }
  catch { durable = false; }
  if (stored != null && !sameDraft(stored, draft.submitted)) {
    cache.set(draft.key, stored);
    return { status: 'preserved', draft, durable };
  }
  cache.set(draft.key, null);
  try { storage.removeItem(draft.key); } catch { durable = false; }
  if (durable) undurableDrafts.delete(draft.key); else undurableDrafts.add(draft.key);
  return { status: memory != null || stored != null ? 'cleared' : 'absent', draft, durable };
}
