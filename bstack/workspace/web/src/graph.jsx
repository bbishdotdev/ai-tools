import React, { useEffect, useMemo, useRef, useState } from "react";
import { Status } from "./ui.jsx";
function graphPositions(items, links) {
  const ids = new Set(items.map(item => item.id));
  const incoming = new Map(items.map(item => [item.id, 0]));
  const outgoing = new Map(items.map(item => [item.id, []]));
  for (const link of links) {
    if (link.kind !== 'blocks' || !ids.has(link.from) || !ids.has(link.to)) continue;
    incoming.set(link.to, incoming.get(link.to) + 1);
    outgoing.get(link.from).push(link.to);
  }
  const queue = items.filter(item => !incoming.get(item.id)).map(item => item.id);
  const levels = new Map(queue.map(id => [id, 0]));
  for (let index = 0; index < queue.length; index++) {
    const id = queue[index];
    for (const target of outgoing.get(id)) {
      levels.set(target, Math.max(levels.get(target) || 0, levels.get(id) + 1));
      incoming.set(target, incoming.get(target) - 1);
      if (!incoming.get(target)) queue.push(target);
    }
  }
  const rows = new Map();
  return new Map(items.map(item => {
    const level = levels.get(item.id) || 0;
    const row = rows.get(level) || 0;
    rows.set(level, row + 1);
    return [item.id, [24 + level * 270, 30 + row * 145]];
  }));
}
export function Graph({ items, links, visible, selected, onSelect }) {
  const [zoom, setZoom] = useState(1);
  const scrollRef = useRef(null);
  const [focus, setFocus] = useState(false);
  const [related, setRelated] = useState(true);
  const [hierarchy, setHierarchy] = useState(false);
  const nodeWidth = 204, nodeHeight = 101;
  const neighbors = new Set([selected, ...links.filter(link => link.from === selected || link.to === selected).flatMap(link => [link.from, link.to])]);
  const graphKey = JSON.stringify([items.map(item => item.id), links.map(link => [link.kind, link.from, link.to])]);
  const positions = useMemo(() => graphPositions(items, links), [graphKey]);
  const visibleIds = new Set(visible.map(item => item.id));
  const point = id => positions.get(id) || [20, 20];
  const maxY = Math.max(300, ...items.map(item => point(item.id)[1])) + 140;
  const graphWidth = Math.max(700, ...items.map(item => point(item.id)[0] + 244));
  useEffect(() => {
    const scroller = scrollRef.current;
    const [x, y] = point(selected);
    if (!scroller) return;
    if (x * zoom < scroller.scrollLeft || (x + nodeWidth) * zoom > scroller.scrollLeft + scroller.clientWidth) scroller.scrollLeft = Math.max(0, x * zoom - (scroller.clientWidth - nodeWidth * zoom) / 2);
    if (y * zoom < scroller.scrollTop || (y + nodeHeight) * zoom > scroller.scrollTop + scroller.clientHeight) scroller.scrollTop = Math.max(0, y * zoom - (scroller.clientHeight - nodeHeight * zoom) / 2);
  }, [selected, zoom, focus, positions]);
  const linkList = links.filter(link => link.kind === 'blocks' || (link.kind === 'related' && related) || (link.kind === 'parent' && hierarchy));
  return <div className="graph-wrap">
    <div className="graph-heading"><div><span className="small-label">Relationship map</span><p>Follow an answer. See what it unlocks.</p></div><button className={`button ${focus ? 'active' : ''}`} onClick={() => setFocus(!focus)}>{focus ? 'Show whole map' : 'Focus selection'}</button></div>
    <div ref={scrollRef} className="graph-scroll" tabIndex="0" aria-label="Scrollable relationship map">
      <div className="graph-surface" style={{ width: `${graphWidth * zoom}px`, height: `${maxY * zoom}px` }}>
        <div className="graph-plane" style={{ transform: `scale(${zoom})`, width: graphWidth, height: maxY }}>
          <svg className="graph-lines" width={graphWidth} height={maxY} aria-hidden="true"><defs><marker id="arrowhead" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7" fill="#9a9a9a"/></marker></defs>
            {linkList.map(link => {
              const [x1, y1] = point(link.from), [x2, y2] = point(link.to);
              const sx = x1 + nodeWidth, sy = y1 + nodeHeight / 2, ex = x2, ey = y2 + nodeHeight / 2;
              const sameColumn = x1 === x2;
              const path = sameColumn ? `M ${sx - 18} ${y1 + nodeHeight} C ${sx + 46} ${y1 + 150}, ${sx + 46} ${y2 - 40}, ${ex + nodeWidth - 18} ${y2}` : `M ${sx} ${sy} C ${sx + 45} ${sy}, ${ex - 45} ${ey}, ${ex - 3} ${ey}`;
              const active = link.from === selected || link.to === selected;
              return <path key={`${link.from}-${link.kind}-${link.to}`} d={path} fill="none" stroke={active ? '#3d3d3d' : '#c6c6c6'} strokeWidth={active ? '1.6' : '1.2'} strokeDasharray={link.kind === 'related' ? '5 5' : link.kind === 'parent' ? '2 4' : undefined} markerEnd={link.kind === 'blocks' ? 'url(#arrowhead)' : undefined} opacity={focus && !active ? .18 : 1}/>;
            })}
          </svg>
          {items.map(item => {
            const [left, top] = point(item.id), matched = visibleIds.has(item.id), dim = !matched || (focus && !neighbors.has(item.id));
            return <button key={item.id} className={`map-node ${selected === item.id ? 'selected' : ''} ${dim ? 'context-node' : ''}`} style={{ left, top, width: nodeWidth, height: nodeHeight }} onClick={() => onSelect(item.id)} aria-label={`${item.id} ${item.title}${matched ? '' : ', outside current filter'}`}><span className="node-top"><span className="mono">{item.id}</span><Status value={item.status} text={false}/></span><span className="node-title">{item.title}</span><span className="node-meta">{matched ? item.method : 'Outside filter · context'}</span></button>;
          })}
        </div>
      </div>
    </div>
    <div className="graph-footer"><span><i className="legend-line"/> Blocks</span><button className={!related ? 'muted' : ''} onClick={() => setRelated(!related)} aria-pressed={related}><i className="legend-line dashed"/> Related</button><button className={!hierarchy ? 'muted' : ''} onClick={() => setHierarchy(!hierarchy)} aria-pressed={hierarchy}><i className="legend-line dotted"/> Parent / child</button><span className="spacer"/><button aria-label="Zoom out" onClick={() => setZoom(Math.max(.5, zoom - .1))}>−</button><button onClick={() => setZoom(1)} aria-label="Reset zoom">{Math.round(zoom * 100)}%</button><button aria-label="Zoom in" onClick={() => setZoom(Math.min(1.5, zoom + .1))}>+</button></div>
  </div>;
}
