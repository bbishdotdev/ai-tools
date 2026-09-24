import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Status } from "./ui.jsx";
import { edgePath, layoutGraph, NODE } from "./graph-layout.js";

export function Graph({ items, links, visible, selected, onSelect }) {
  const [zoom, setZoom] = useState(1);
  const [focus, setFocus] = useState(false);
  const [related, setRelated] = useState(false);
  const [hierarchy, setHierarchy] = useState(false);
  const [viewport, setViewport] = useState({ width: 0, height: 0 });
  const scrollRef = useRef(null);
  const pendingCenter = useRef(null);
  const fitting = useRef(false);
  const graphKey = JSON.stringify([items.map(item => item.id), links.map(link => [link.kind, link.from, link.to])]);
  const focusedId = focus ? selected : null;
  const layout = useMemo(() => layoutGraph(items.map(item => item.id), links, { selected: focusedId, focus, related, hierarchy }), [graphKey, focusedId, focus, related, hierarchy]);
  const shownIds = new Set(layout.ids);
  const nodes = items.filter(item => shownIds.has(item.id));
  const visibleIds = new Set(visible.map(item => item.id));
  const outsideCount = nodes.filter(item => !visibleIds.has(item.id)).length;
  const fitZoom = () => Math.min(1, Math.max(1, viewport.width - 24) / layout.width, Math.max(1, viewport.height - 24) / layout.height);
  const horizontalInset = (scale, width) => Math.max(0, (width - layout.width * scale) / 2);
  const scrollTo = ([x, y], scale = zoom) => {
    const scroller = scrollRef.current;
    if (!scroller) return;
    scroller.scrollLeft = Math.max(0, horizontalInset(scale, scroller.clientWidth) + x * scale - scroller.clientWidth / 2);
    scroller.scrollTop = Math.max(0, y * scale - scroller.clientHeight / 2);
  };
  function centerSelection() {
    const point = layout.positions.get(selected);
    if (point) scrollTo([point[0] + NODE.width / 2, point[1] + NODE.height / 2]);
  }
  function keepSelectionVisible() {
    const scroller = scrollRef.current, point = layout.positions.get(selected);
    if (!scroller || !point) return;
    const x = horizontalInset(zoom, scroller.clientWidth) + point[0] * zoom, y = point[1] * zoom;
    if (x < scroller.scrollLeft) scroller.scrollLeft = x;
    else if (x + NODE.width * zoom > scroller.scrollLeft + scroller.clientWidth) scroller.scrollLeft = x + NODE.width * zoom - scroller.clientWidth;
    if (y < scroller.scrollTop) scroller.scrollTop = y;
    else if (y + NODE.height * zoom > scroller.scrollTop + scroller.clientHeight) scroller.scrollTop = y + NODE.height * zoom - scroller.clientHeight;
  }
  function changeZoom(next) {
    const scroller = scrollRef.current;
    const bounded = Math.min(1.5, Math.max(.2, next));
    if (bounded === zoom) return;
    fitting.current = false;
    pendingCenter.current = [(scroller.scrollLeft + scroller.clientWidth / 2 - horizontalInset(zoom, scroller.clientWidth)) / zoom, (scroller.scrollTop + scroller.clientHeight / 2) / zoom];
    setZoom(bounded);
  }
  function fitMap() {
    if (!viewport.width || !viewport.height) return;
    fitting.current = true;
    const next = fitZoom();
    setZoom(next);
    scrollTo([layout.width / 2, layout.height / 2], next);
  }
  useEffect(() => {
    const scroller = scrollRef.current;
    const observer = new ResizeObserver(() => setViewport({ width: scroller.clientWidth, height: scroller.clientHeight }));
    observer.observe(scroller, { box: 'border-box' });
    return () => observer.disconnect();
  }, []);
  useLayoutEffect(() => {
    if (!viewport.width || !viewport.height) return;
    if (fitting.current) {
      const next = fitZoom();
      if (next !== zoom) setZoom(next);
      scrollTo([layout.width / 2, layout.height / 2], next);
    } else if (pendingCenter.current) {
      scrollTo(pendingCenter.current);
      pendingCenter.current = null;
    }
  }, [zoom, viewport, layout]);
  useLayoutEffect(() => {
    if (!fitting.current) centerSelection();
  }, [selected, layout]);
  useLayoutEffect(() => {
    if (!fitting.current) keepSelectionVisible();
  }, [viewport]);
  const orderedLinks = [...layout.links].sort((a, b) => Number(a.from === selected || a.to === selected) - Number(b.from === selected || b.to === selected));
  return <div className="graph-wrap">
    <div className="graph-heading"><div><span className="small-label">Relationship map</span><p>{focus ? 'Direct connections to the selected question.' : 'Questions flow from prerequisites to the work they unlock.'}</p><span className="graph-count" aria-live="polite">{nodes.length} of {items.length} questions · {layout.links.length} connections{outsideCount ? ` · ${outsideCount} outside filter` : ''}</span></div><button className={`button ${focus ? 'active' : ''}`} aria-pressed={focus} onClick={() => { fitting.current = false; setFocus(!focus); }}>{focus ? 'Show whole map' : 'Focus selection'}</button></div>
    <div ref={scrollRef} className="graph-scroll" tabIndex="0" aria-label="Scrollable relationship map">
      <div className="graph-surface" style={{ width: `${layout.width * zoom}px`, height: `${layout.height * zoom}px` }}>
        <div className="graph-plane" style={{ transform: `scale(${zoom})`, width: layout.width, height: layout.height }}>
          <svg className="graph-lines" width={layout.width} height={layout.height} aria-hidden="true"><defs><marker id="arrowhead" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto-start-reverse"><path d="M0 0 L7 3.5 L0 7" fill="context-stroke"/></marker></defs>
            {orderedLinks.map((link, index) => {
              const active = link.from === selected || link.to === selected;
              return <path key={`${link.from}-${link.kind}-${link.to}`} d={edgePath(link, layout.positions, index)} fill="none" stroke={active ? '#454545' : '#c7c7c7'} strokeWidth={active ? '1.7' : '1.1'} strokeDasharray={link.kind === 'related' ? '5 5' : link.kind === 'parent' ? '2 4' : undefined} strokeLinejoin="round" markerEnd={link.kind === 'blocks' ? 'url(#arrowhead)' : undefined}/>;
            })}
          </svg>
          {nodes.map(item => {
            const [left, top] = layout.positions.get(item.id), matched = visibleIds.has(item.id);
            const shortId = item.id.length > 16 ? `${item.id.slice(0, 10)}…${item.id.slice(-4)}` : item.id;
            return <button key={item.id} className={`map-node ${selected === item.id ? 'selected' : ''} ${!matched ? 'context-node' : ''}`} style={{ left, top, width: NODE.width, height: NODE.height }} onClick={() => onSelect(item.id)} aria-pressed={selected === item.id} aria-label={`${item.id} ${item.title}, ${item.status}${matched ? '' : ', outside current filter, retained for context'}`} title={`${item.title}\n${item.id}`}><span className="node-top"><Status value={item.status}/><span className="node-method">{item.method}</span></span><span className="node-title">{item.title}</span><span className="node-meta"><span className="mono">{shortId}</span>{!matched ? <span>Outside filter</span> : null}</span></button>;
          })}
        </div>
      </div>
    </div>
    <div className="graph-footer"><div className="graph-legend"><span><i className="legend-line"/> Blocks</span><button className={!related ? 'muted' : ''} onClick={() => setRelated(!related)} aria-pressed={related}><i className="legend-line dashed"/> Related</button><button className={!hierarchy ? 'muted' : ''} onClick={() => setHierarchy(!hierarchy)} aria-pressed={hierarchy}><i className="legend-line dotted"/> Parent / child</button></div><div className="graph-navigation"><button onClick={fitMap}>Fit map</button><button onClick={() => { fitting.current = false; centerSelection(); }}>Center selection</button><span className="graph-zoom"><button aria-label="Zoom out" disabled={zoom <= .2} onClick={() => changeZoom(zoom - .1)}>−</button><button onClick={() => changeZoom(1)} aria-label="Reset zoom">{Math.round(zoom * 100)}%</button><button aria-label="Zoom in" disabled={zoom >= 1.5} onClick={() => changeZoom(zoom + .1)}>+</button></span></div></div>
  </div>;
}
