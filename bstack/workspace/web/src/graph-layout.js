export const NODE = { width: 252, height: 152, columnGap: 96, rowGap: 36, padding: 28, top: 74 };
const columnStep = NODE.width + NODE.columnGap;
const rowStep = NODE.height + NODE.rowGap;
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;

export function layoutGraph(ids, relationships, { selected, focus = false, related = false, hierarchy = false } = {}) {
  const allIds = new Set(ids);
  let links = relationships.filter(link => allIds.has(link.from) && allIds.has(link.to) &&
    (link.kind === 'blocks' || (related && link.kind === 'related') || (hierarchy && link.kind === 'parent')));
  let shown = [...allIds].sort(compare);
  if (focus && allIds.has(selected)) {
    links = links.filter(link => link.from === selected || link.to === selected);
    shown = [...new Set([selected, ...links.flatMap(link => [link.from, link.to])])].sort(compare);
  }
  const positions = new Map();
  if (focus && allIds.has(selected)) {
    const before = new Set(links.filter(link => link.to === selected && link.kind !== 'related').map(link => link.from));
    const columns = [shown.filter(id => before.has(id)), [selected], shown.filter(id => id !== selected && !before.has(id))].filter(column => column.length);
    const rows = Math.max(...columns.map(column => column.length));
    columns.forEach((column, index) => column.forEach((id, row) => {
      positions.set(id, [NODE.padding + index * columnStep, NODE.top + ((rows - column.length) / 2 + row) * rowStep]);
    }));
  } else {
    const incoming = new Map(shown.map(id => [id, []]));
    const outgoing = new Map(shown.map(id => [id, []]));
    for (const link of links.filter(link => link.kind === 'blocks')) {
      incoming.get(link.to).push(link.from);
      outgoing.get(link.from).push(link.to);
    }
    const remaining = new Map(shown.map(id => [id, incoming.get(id).length]));
    const queue = shown.filter(id => !remaining.get(id));
    const levels = new Map(queue.map(id => [id, 0]));
    for (let index = 0; index < queue.length; index++) {
      const id = queue[index];
      for (const target of outgoing.get(id)) {
        levels.set(target, Math.max(levels.get(target) || 0, levels.get(id) + 1));
        remaining.set(target, remaining.get(target) - 1);
        if (!remaining.get(target)) queue.push(target);
      }
    }
    const columns = [];
    for (const id of shown) (columns[levels.get(id) || 0] ||= []).push(id);
    const rows = new Map();
    const originalOrder = new Map(shown.map((id, index) => [id, index]));
    for (const column of columns) {
      const score = id => {
        const parents = incoming.get(id).filter(parent => rows.has(parent));
        return parents.length ? parents.reduce((sum, parent) => sum + rows.get(parent), 0) / parents.length : originalOrder.get(id);
      };
      column.sort((a, b) => score(a) - score(b) || compare(a, b));
      column.forEach((id, row) => rows.set(id, row));
    }
    columns.forEach((column, level) => column.forEach((id, row) => positions.set(id, [NODE.padding + level * columnStep, NODE.top + row * rowStep])));
  }
  return {
    ids: shown, links, positions,
    width: Math.max(NODE.width + NODE.padding * 2, ...[...positions.values()].map(([x]) => x + NODE.width + NODE.padding)),
    height: Math.max(NODE.height + NODE.top + NODE.padding, ...[...positions.values()].map(([, y]) => y + NODE.height + NODE.padding)),
  };
}

export function edgePath(link, positions, index = 0) {
  const [x1, y1] = positions.get(link.from), [x2, y2] = positions.get(link.to);
  const sx = x1 + NODE.width, sy = y1 + NODE.height / 2, ey = y2 + NODE.height / 2;
  if (x2 > x1 && x2 - x1 <= columnStep) return `M ${sx} ${sy} C ${sx + 44} ${sy}, ${x2 - 44} ${ey}, ${x2 - 4} ${ey}`;
  const lane = 14 + index % 3 * 5;
  if (x1 === x2) {
    const x = sx + lane;
    return `M ${sx} ${sy} H ${x} V ${ey} H ${sx + 4}`;
  }
  const top = 14 + index % 5 * 9;
  return `M ${sx} ${sy} H ${sx + lane} V ${top} H ${x2 - lane} V ${ey} H ${x2 - 4}`;
}
