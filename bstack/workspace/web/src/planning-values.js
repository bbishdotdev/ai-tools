export const lines = value => (value || '').split('\n').map(part => part.trim()).filter(Boolean);
