import assert from 'node:assert/strict';
import test from 'node:test';
import { layoutGraph, NODE } from '../src/graph-layout.js';

const blocks = (from, to) => ({ kind: 'blocks', from, to });
const related = (from, to) => ({ kind: 'related', from, to });
const parent = (from, to) => ({ kind: 'parent', from, to });
const positions = layout => Object.fromEntries(layout.positions);

test('overview retains every question and only enabled, valid connections', () => {
  const ids = ['a', 'b', 'c', 'isolated'];
  const links = [blocks('a', 'b'), related('b', 'c'), parent('a', 'c'), blocks('missing', 'a')];
  const overview = layoutGraph(ids, links);
  assert.deepEqual(new Set(overview.ids), new Set(ids));
  assert.deepEqual(overview.links, [blocks('a', 'b')]);
  assert.equal(layoutGraph(ids, links, { related: true, hierarchy: true }).links.length, 3);
});

test('focus retains all direct blockers and unlocks, without unrelated questions or second hops', () => {
  const ids = ['earlier', 'prerequisite', 'selected', 'next', 'later', 'related', 'parent', 'isolated'];
  const links = [blocks('earlier', 'prerequisite'), blocks('prerequisite', 'selected'), blocks('selected', 'next'), blocks('next', 'later'), related('selected', 'related'), parent('parent', 'selected')];
  const focused = layoutGraph(ids, links, { focus: true, selected: 'selected' });
  assert.deepEqual(new Set(focused.ids), new Set(['prerequisite', 'selected', 'next']));
  assert.equal(focused.links.length, 2);
  assert(focused.positions.get('prerequisite')[0] < focused.positions.get('selected')[0]);
  assert(focused.positions.get('selected')[0] < focused.positions.get('next')[0]);
  const expanded = layoutGraph(ids, links, { focus: true, selected: 'selected', related: true, hierarchy: true });
  assert.deepEqual(new Set(expanded.ids), new Set(['prerequisite', 'selected', 'next', 'related', 'parent']));
  assert.equal(expanded.links.length, 4);
  assert(focused.width < layoutGraph(ids, links).width);
});

test('focus centers the selected question vertically between uneven dependency columns', () => {
  const ids = ['a', 'b', 'c', 'selected', 'next'];
  const layout = layoutGraph(ids, [blocks('a', 'selected'), blocks('b', 'selected'), blocks('c', 'selected'), blocks('selected', 'next')], { focus: true, selected: 'selected' });
  const ys = ['a', 'b', 'c'].map(id => layout.positions.get(id)[1]);
  assert.equal(layout.positions.get('selected')[1], (Math.min(...ys) + Math.max(...ys)) / 2);
  assert.equal(layout.positions.get('next')[1], layout.positions.get('selected')[1]);
});

test('overview ordering follows connected branches and remains stable across input order', () => {
  const ids = ['a', 'b', 'c', 'd', 'e'];
  const links = [blocks('a', 'd'), blocks('b', 'c'), blocks('c', 'e'), blocks('d', 'e')];
  const layout = layoutGraph(ids, links);
  assert.deepEqual(positions(layoutGraph([...ids].reverse(), [...links].reverse())), positions(layout));
  assert(layout.positions.get('d')[1] < layout.positions.get('c')[1]);
  for (const { from, to } of links) assert(layout.positions.get(from)[0] < layout.positions.get(to)[0]);
});

test('all nodes remain in bounds and never overlap, including disconnected and single-question maps', () => {
  const ids = Array.from({ length: 36 }, (_, index) => `q-${index}`);
  for (const options of [{}, { focus: true, selected: 'q-0' }]) {
    const layout = layoutGraph(ids, [blocks('q-0', 'q-1'), blocks('q-1', 'q-2')], options);
    const points = [...layout.positions.values()];
    for (const [index, [x, y]] of points.entries()) {
      assert(x >= 0 && y >= 0 && x + NODE.width <= layout.width && y + NODE.height <= layout.height);
      for (const [ox, oy] of points.slice(index + 1)) assert(x + NODE.width <= ox || ox + NODE.width <= x || y + NODE.height <= oy || oy + NODE.height <= y);
    }
  }
  const single = layoutGraph(['only'], [], { focus: true, selected: 'only' });
  assert.deepEqual(single.ids, ['only']);
  assert.equal(single.links.length, 0);
  assert(single.width < layoutGraph(ids, [blocks('q-0', 'q-1')]).width);
});
