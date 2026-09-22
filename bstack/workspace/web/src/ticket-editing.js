import { lines } from './planning-values.js';

export function ticketMetadataChange(item, draft) {
  if (!draft) return { requiresReopen: false, patch: null };
  const requiresReopen = item.state === 'done' && (draft.progress !== (item.progress || '') || draft.references !== item.references.join('\n'));
  if (requiresReopen) return { requiresReopen: true, patch: null };
  return { requiresReopen: false, patch: {
    labels: draft.labels.split(',').map(label => label.trim()).filter(Boolean),
    priority: Number(draft.priority),
    ...(item.state !== 'done' ? { progress: draft.progress, references: lines(draft.references) } : {}),
  } };
}
