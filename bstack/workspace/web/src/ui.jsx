import React, { useEffect, useId, useRef, useState } from "react";
import { marked } from "marked";
import DOMPurify from "dompurify";
import "@github/markdown-toolbar-element";
export function Icon({ name, size = 18, ...props }) {
  const paths = {
    search: <><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></>,
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    map: <><rect x="2" y="8" width="5" height="7" rx="1"/><rect x="17" y="2" width="5" height="7" rx="1"/><rect x="17" y="15" width="5" height="7" rx="1"/><path d="M7 11h5V5h5M12 11v8h5"/></>,
    list: <><path d="M8 5h13M8 12h13M8 19h13"/><path d="M3 5h.01M3 12h.01M3 19h.01" strokeWidth="3"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
    arrow: <path d="M5 12h14m-5-5 5 5-5 5"/>,
    chevron: <path d="m9 5 7 7-7 7"/>,
    check: <path d="m5 12 4 4L19 6"/>,
    close: <path d="m6 6 12 12M18 6 6 18"/>,
    link: <><path d="m9 15 6-6M8 16l-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0M16 8l1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0" transform="translate(1 0) scale(.9)"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/></>,
    edit: <><path d="m15 4 5 5M4 20l5-1L21 7a2 2 0 0 0-5-5L4 14Z"/></>,
    layers: <><path d="m12 3 10 6-10 6L2 9Z"/><path d="m2 14 10 6 10-6M2 18l10 6 10-6" transform="translate(0 -2)"/></>,
    expand: <path d="M9 3H3v6M15 3h6v6M21 15v6h-6M3 15v6h6"/>,
    panel: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.grid}</svg>;
}

export function useWidth(ref) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref]);
  return width;
}

export function ResizeHandle({ name, controls, value, min, max, direction = 1, onChange, onReset, area, hidden }) {
  const drag = useRef(null);
  const clamp = next => Math.round(Math.max(min, Math.min(max, next)));
  function finish(event) {
    if (!drag.current) return;
    drag.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }
  return <div className="resize-handle" hidden={hidden} style={{ gridArea: area }} role="separator" tabIndex={0} aria-label={`Resize ${name}`} aria-controls={controls} aria-orientation="vertical" aria-valuemin={min} aria-valuemax={max} aria-valuenow={Math.round(value)} aria-valuetext={`${Math.round(value)} pixels`} title={`Drag to resize ${name}. Arrow keys adjust width. Double-click to reset.`}
    onPointerDown={event => { if (event.button !== 0) return; event.preventDefault(); event.currentTarget.focus(); event.currentTarget.setPointerCapture(event.pointerId); drag.current = { x: event.clientX, value }; }}
    onPointerMove={event => { if (drag.current) onChange(clamp(drag.current.value + (event.clientX - drag.current.x) * direction)); }}
    onPointerUp={finish} onPointerCancel={finish} onLostPointerCapture={() => { drag.current = null; }}
    onDoubleClick={onReset}
    onKeyDown={event => { const step = event.shiftKey ? 40 : 10; const next = event.key === 'ArrowRight' ? value + step * direction : event.key === 'ArrowLeft' ? value - step * direction : event.key === 'Home' ? min : event.key === 'End' ? max : null; if (next !== null) { event.preventDefault(); onChange(clamp(next)); } }}><span/></div>;
}

export function PanelHeading({ title, onHide }) {
  return <div className="panel-heading"><span className="small-label">{title}</span><button className="icon-button" aria-label={`Hide ${title.toLowerCase()}`} title={`Hide ${title.toLowerCase()}`} onClick={onHide}><Icon name="close" size={14}/></button></div>;
}

export function Status({ value, text = true }) {
  return <span className={`status status-${value.toLowerCase().replaceAll(' ', '-')}`}><span className="status-dot">{value === 'Resolved' ? <Icon name="check" size={9}/> : null}</span>{text ? value : null}</span>;
}

export function Markdown({ value }) {
  return <div className="markdown" dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(marked.parse(value || '', { gfm: true })) }}/>;
}

export function Editor({ value, onChange, label = "Description Markdown", disabled = false }) {
  const [preview, setPreview] = useState(false);
  const id = useId();
  return <div className="editor">
    <div className="editor-head"><div className="segmented"><button type="button" className={!preview ? 'active' : ''} onClick={() => setPreview(false)}>Write</button><button type="button" className={preview ? 'active' : ''} onClick={() => setPreview(true)}>Preview</button></div><span>Markdown</span></div>
    {preview ? <div className="editor-preview"><Markdown value={value}/></div> : <>
      <markdown-toolbar for={id} class="md-toolbar" aria-label="Markdown formatting">
        <md-header role="button" aria-label="Heading" title="Heading">H</md-header><md-bold role="button" aria-label="Bold" title="Bold">B</md-bold><md-italic role="button" aria-label="Italic" title="Italic">I</md-italic><md-quote role="button" aria-label="Quote" title="Quote">❞</md-quote><md-code role="button" aria-label="Code" title="Code">&lt;/&gt;</md-code><md-link role="button" aria-label="Link" title="Link">↗</md-link><md-unordered-list role="button" aria-label="Bulleted list" title="Bulleted list">≡</md-unordered-list><md-task-list role="button" aria-label="Task list" title="Task list">☑</md-task-list>
      </markdown-toolbar>
      <textarea id={id} aria-label={label} disabled={disabled} value={value} onChange={event => onChange(event.target.value)} spellCheck="false"/>
    </>}
  </div>;
}
