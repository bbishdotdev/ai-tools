import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Icon, PanelHeading, ResizeHandle, Status, useWidth } from './ui.jsx';
import { Detail } from './detail.jsx';
import { Graph } from './graph.jsx';
import { CreateDialog } from './forms.jsx';
import { useWorkspace } from './client.js';
import { PlanningCreate, PlanningWorkspace } from './board.jsx';
function ItemRow({ item, items, links, selected, onSelect, dense = false }) {
  return <button className={`item-row ${selected === item.id ? 'selected' : ''} ${dense ? 'dense' : ''}`} onClick={() => onSelect(item.id)} aria-label={`Open ${item.id}: ${item.title}`} aria-pressed={selected === item.id}>
    <Status value={item.status} text={false}/><div className="row-main"><div className="row-title">{item.title}</div><div className="row-meta"><span className="mono">{item.id}</span><span>{item.method}</span>{item.labels.slice(0, 1).map(label => <span key={label} className="row-label">{label}</span>)}</div></div><Icon name="chevron" size={14}/>
  </button>;
}

function MapsOverview({ maps, query, filter, onFilter, onClear, onOpen, onCreate }) {
  const rows = maps.map(map => ({ map, counts: map.counts }));
  const readyMaps = rows.filter(row => row.counts.ready > 0).length;
  const waitingMaps = rows.filter(row => row.counts.waiting > 0).length;
  const visible = rows.filter(({map, counts}) => `${map.id} ${map.title} ${map.destination} ${map.scope}`.toLowerCase().includes(query.toLowerCase()) && (filter === 'ready' ? counts.ready > 0 : filter === 'waiting' ? counts.waiting > 0 : filter === 'empty' ? !counts.total : true));
  return <section className="maps-overview" aria-label="Wayfinder maps"><div className="maps-intro"><div><span className="eyebrow">LOCAL WORKSPACE</span><h1>Wayfinder</h1><p>Every effort has its own path. Pick up where you left off.</p></div><button className="button primary" onClick={onCreate}><Icon name="plus" size={16}/>New map</button></div><div className="maps-summary"><span><strong>{maps.length}</strong> maps</span><span><strong>{readyMaps}</strong> with ready work</span><span><strong>{waitingMaps}</strong> awaiting an answer</span></div><div className="maps-filters"><div className="status-filters">{[['all', 'All maps'], ['ready', 'Ready next'], ['waiting', 'Waiting'], ['empty', 'Not started']].map(([value, title]) => <button key={value} className={filter===value?'active':''} onClick={()=>onFilter(value)}>{title}</button>)}</div><span>{visible.length} {visible.length===1?'map':'maps'}</span></div><div className="maps-table"><div className="maps-table-heading"><span>Map / destination</span><span>Progress</span><span>Ready</span><span>Needs attention</span><span/></div>{visible.map(({map, counts}) => <button className="map-row" key={map.id} aria-label={`Open map: ${map.title}`} onClick={()=>onOpen(map.id)}><div className="map-identity"><span className="map-row-icon"><Icon name="map" size={19}/></span><div><span className="map-id">{map.id.toUpperCase()}</span><h2>{map.title}</h2><p>{map.destination}</p></div></div><div className="map-progress"><span className="map-state">{map.complete ? "Answers settled" : map.progress || "Planning"}</span><span>{counts.resolved} of {counts.total} answered</span><span className="progress-track"><i style={{width: `${counts.total ? counts.resolved/counts.total*100 : 0}%`}}/></span></div><div className="map-ready"><strong>{counts.ready}</strong><span>ready</span></div><div className="map-attention">{counts.waiting ? <span><Icon name="clock" size={13}/>{counts.waiting} waiting</span> : null}{counts.blocked ? <span>{counts.blocked} blocked</span> : null}{counts.reviewing ? <span>{counts.reviewing} need review</span> : null}{!counts.total ? <span>Add the first question</span> : !counts.blocked&&!counts.waiting&&!counts.reviewing ? <span>No blockers</span> : null}</div><Icon name="arrow" size={17}/></button>)}</div>{!visible.length ? <div className="empty"><Icon name="search" size={24}/><h3>{maps.length ? "No matching maps" : "Your first map starts here"}</h3><p>{maps.length ? "Try another name or clear the filters." : "Name the work, define its scope, then add the questions."}</p><button className="button" onClick={maps.length ? onClear : onCreate}>{maps.length ? "Clear map filters" : "Create a map"}</button></div> : null}<p className="maps-note">Open a map to see its question queue and decision tree, or explore its Atlas view.</p></section>;
}

function mapRoute(map) {
  return { screen: 'map', mapId: map.id, view: 'questions', selected: '', ticketId: '', specId: '', specFilter: '', expanded: false, query: '', label: '', status: '', error: '' };
}
function readRoute() {
  const params = new URLSearchParams(location.search);
  const screen = ['board', 'specs'].includes(params.get('screen')) ? params.get('screen') : params.get('map') ? 'map' : 'maps';
  return { screen, mapId: params.get('map') || '', view: params.get('view') === 'atlas' ? 'atlas' : 'questions', selected: params.get('item') || '', ticketId: params.get('ticket') || '', specId: screen === 'specs' ? params.get('spec') || '' : '', specFilter: screen === 'board' ? params.get('spec') || '' : '', expanded: params.get('full') === '1', query: params.get('q') || '', label: params.get('label') || '', status: params.get('status') || '', error: '' };
}
const emptyMap = { id: '', title: '', destination: '', scope: '', progress: '', counts: { total: 0, ready: 0, resolved: 0, blocked: 0, waiting: 0, reviewing: 0 } };
const incoming = (id, links, items) => links.filter(link => link.kind === 'blocks' && link.to === id).map(link => items.find(item => item.id === link.from)).filter(Boolean);
const defaults = { nav: 192, inspector: 400, queue: 220, context: 210, navHidden: false, detailsHidden: false, queueHidden: false, contextHidden: false };
const bounded = (value, min, max) => Math.min(Math.max(value, min), max);

function App() {
  const [route, setRoute] = useState(readRoute);
  const data = useWorkspace(route);
  const planning = route.screen === 'board' || route.screen === 'specs';
  const { maps, loading, busy: saving, pending, mutate } = data;
  const busy = saving || Boolean(pending);
  const [retryError, setRetryError] = useState("");
  const [newOpen, setNewOpen] = useState(false);
  const [newMapOpen, setNewMapOpen] = useState(false);
  const [newPlanning, setNewPlanning] = useState(null);
  const [prefs, setPrefs] = useState(defaults);
  const [mapQuery, setMapQuery] = useState('');
  const [mapFilter, setMapFilter] = useState('all');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [notification, setNotification] = useState('');
  const visits = useRef({});
  const search = useRef(null);
  const shell = useRef(null);
  const content = useRef(null);
  const shellWidth = useWidth(shell);
  const contentWidth = useWidth(content);
  const compact = shellWidth > 0 && shellWidth < 980;
  const narrow = contentWidth > 0 && contentWidth < 760;
  const active = data.snapshot?.map?.id === route.mapId ? data.snapshot : null;
  const map = active?.map || maps.find(map => map.id === route.mapId) || emptyMap;
  const items = active?.questions || [];
  const links = active?.relationships || [];
  const {query, label, status} = route;
  const mapsView = route.screen === 'maps';
  const selected = items.find(item => item.id === route.selected) || items.find(item => item.state !== 'resolved') || items[0];
  const atlas = route.view === 'atlas';
  const focus = !atlas;
  const full = route.expanded && (planning ? Boolean(route.screen === 'board' ? data.snapshot?.tickets?.some(ticket => ticket.id === route.ticketId) : data.snapshot?.spec?.id === route.specId) : !mapsView && Boolean(selected));
  const navVisible = !full && (compact ? mobileNavOpen : !prefs.navHidden);
  const detailVisible = Boolean(selected) && (full || focus || !prefs.detailsHidden);
  const navMax = compact ? 280 : Math.max(160, Math.min(280, shellWidth - 760));
  const navWidth = bounded(prefs.nav, 160, navMax);
  const inspectorMax = Math.max(340, Math.min(720, contentWidth - 266));
  const inspectorWidth = bounded(prefs.inspector, 340, inspectorMax);
  const queueLimit = Math.max(180, Math.min(360, contentWidth - 332 - (prefs.contextHidden ? 0 : 186)));
  const queueWidth = bounded(prefs.queue, 180, queueLimit);
  const contextMax = Math.max(180, Math.min(400, contentWidth - 332 - (prefs.queueHidden ? 0 : queueWidth + 6)));
  const contextWidth = bounded(prefs.context, 180, contextMax);
  const queueMax = Math.max(180, Math.min(360, contentWidth - 332 - (prefs.contextHidden ? 0 : contextWidth + 6)));
  const labels = [...new Set(items.flatMap(item => item.labels))].sort();
  const visible = items.filter(item => (!label || item.labels.includes(label)) && (!status || item.status === status) && `${item.id} ${item.title} ${item.body} ${item.labels.join(' ')}`.toLowerCase().includes(query.toLowerCase()));
  const counts = map.counts;
  function configure(patch) { setPrefs(values => ({ ...values, ...patch })); }
  function clearFilters() { navigate({ query: '', label: '', status: '' }, true); }
  useEffect(() => {
    const listener = () => { const next = readRoute(); if (next.screen==='map') visits.current[next.mapId]=next; setRoute(next); };
    window.addEventListener('popstate', listener);
    return () => window.removeEventListener('popstate', listener);
  }, [maps]);
  useEffect(() => {
    const listener = event => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') { event.preventDefault(); search.current?.focus(); }
      if (event.key === 'Escape' && event.target === search.current) { if (mapsView) setMapQuery(''); else navigate({query:''},true); search.current.blur(); }
      else if (event.key === 'Escape' && !newOpen && !newMapOpen && !newPlanning) {
        if (mobileNavOpen) setMobileNavOpen(false);
        else if (route.expanded) navigate({ expanded: false });
      }
    };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, [route, newOpen, newMapOpen, newPlanning, mobileNavOpen]);
  useEffect(() => { if (notification) { const timer = setTimeout(() => setNotification(''), 2500); return () => clearTimeout(timer); } }, [notification]);
  function navigate(next, replace = false) {
    if (route.screen==='map') visits.current[route.mapId]=route;
    if (planning) visits.current[route.screen]=route;
    const updated = { ...route, ...next, error: '' };
    const params = new URLSearchParams();
    if (updated.screen==='map') {
      visits.current[updated.mapId]=updated;
      params.set('map',updated.mapId); params.set('view',updated.view);
      if (updated.selected) params.set('item',updated.selected);
      if (updated.expanded) params.set('full','1');
      if (updated.query) params.set('q',updated.query);
      if (updated.label) params.set('label',updated.label);
      if (updated.status) params.set('status',updated.status);
    }
    if (updated.screen === 'board' || updated.screen === 'specs') {
      visits.current[updated.screen] = updated;
      params.set('screen', updated.screen);
      if (updated.mapId) params.set('map', updated.mapId);
      if (updated.screen === 'board' && updated.ticketId) params.set('ticket', updated.ticketId);
      if (updated.screen === 'board' && updated.specFilter) params.set('spec', updated.specFilter);
      if (updated.screen === 'specs' && updated.specId) params.set('spec', updated.specId);
      if (updated.expanded) params.set('full', '1');
      if (updated.query) params.set('q', updated.query);
      if (updated.label) params.set('label', updated.label);
      if (updated.status) params.set('status', updated.status);
    }
    history[replace?'replaceState':'pushState']({},'',params.size?`?${params}`:location.pathname);
    setRoute(updated);
  }
  function openMap(id) { const target=maps.find(map=>map.id===id); if(!target)return; setMobileNavOpen(false); configure({detailsHidden:false}); navigate(visits.current[id] || mapRoute(target)); }
  function showPlanning(screen) { setMobileNavOpen(false); navigate(visits.current[screen] || { ...mapRoute({ id: '' }), screen }); }
  function openQuestion(question) { navigate({ ...mapRoute({ id: question.mapId }), selected: question.id }); }
  function showMaps() { setMobileNavOpen(false); navigate({screen:'maps',expanded:false}); }
  function select(id) { if (!items.some(item=>item.id===id)) return; configure({ detailsHidden: false }); navigate({ selected: id }); }
  function switchView(view) { configure({ detailsHidden: view === 'atlas' }); navigate({ view }); }
  const rowProps = { items, links, selected: selected?.id, onSelect: select };
  const empty = <div className="empty"><Icon name="search" size={24}/><h3>No matching questions</h3><p>Try another search or clear your filters.</p><button className="button" onClick={clearFilters}>Clear filters</button></div>;
  let columns = 'minmax(0, 1fr)', areas = '"detail"';
  if (!full && !narrow && selected) {
    if (focus) {
      columns = `${prefs.queueHidden ? '' : `${queueWidth}px 6px `}minmax(320px, 1fr)${prefs.contextHidden ? '' : ` 6px ${contextWidth}px`}`;
      areas = `"${prefs.queueHidden ? '' : 'queue queue-resize '}detail${prefs.contextHidden ? '' : ' context-resize context'}"`;
    } else {
      columns = detailVisible ? `minmax(260px, 1fr) 6px ${inspectorWidth}px` : 'minmax(0, 1fr)';
      areas = `"graph${detailVisible ? ' inspector-resize detail' : ''}"`;
    }
  }
  const handle = (name, controls, key, min, max, value, direction, area, hidden) => <ResizeHandle name={name} controls={controls} value={value} min={min} max={max} direction={direction} onChange={next => configure({ [key]: next })} onReset={() => configure({ [key]: defaults[key] })} area={area} hidden={hidden}/>;
  return <>
    <div className="study-bar"><button onClick={showMaps} className="study-brand">bstack <span>/ Wayfinder</span></button><span className="workspace-badge">Local workspace</span><span className="study-note" title={data.bootstrap?.workspace.root}>{data.bootstrap?.workspace.root || 'Connecting…'}</span><span role="status">{saving ? 'Saving…' : pending ? 'Request needs recovery' : data.error ? 'Connection needs attention' : loading ? 'Refreshing…' : 'Saved workspace'}</span></div>
    {pending && !saving ? <div className="sync-notice" role="alert"><span>An interrupted request needs its saved result checked. Drafts are preserved.</span><button className="button" onClick={async () => { setRetryError(''); try { const recovered = await data.retryPending();
      if (recovered?.destination) {
        setNewOpen(false); setNewMapOpen(false); setNewPlanning(null); configure({detailsHidden:false});
        navigate(recovered.destination.screen ? { ...mapRoute({id: ''}), ...recovered.destination } : { ...mapRoute({id: recovered.destination.mapId}), selected: recovered.destination.questionId });
      }
      setNotification(recovered?.draftStatus === 'preserved' ? 'Saved request recovered. Your newer draft is preserved.' : 'Saved request recovered.'); } catch (problem) { setRetryError(problem.message); } }}>Retry original request</button>{retryError ? <span>{retryError}</span> : null}</div> : null}
    {data.storageWarning ? <div className="sync-notice" role="alert">{data.storageWarning}</div> : null}
    {data.error ? <div className="sync-notice" role="alert"><span>{data.error}</span><button className="button" onClick={data.reconnect}>Reconnect workspace</button></div> : null}
    <div ref={shell} className={`app-shell variant-focus ${compact ? 'is-compact' : ''} ${full ? 'is-expanded' : ''}`}>
      {compact && navVisible ? <button className="nav-backdrop" aria-label="Dismiss navigation" onClick={() => setMobileNavOpen(false)}/> : null}
      <aside id="workspace-navigation" className="sidebar" aria-label="Workspace navigation" hidden={!navVisible} style={{ width: navWidth }}><div className="workspace-brand"><span className="brand-mark"><Icon name="layers" size={18}/></span><span>bstack<span className="workspace-caption">Local workspace</span></span><button className="icon-button nav-close" aria-label="Hide navigation" title="Hide navigation" onClick={() => compact ? setMobileNavOpen(false) : configure({ navHidden: true })}><Icon name="close" size={14}/></button></div><div className="sidebar-section">Workspace</div><button className={`nav-button ${!planning ? 'active' : ''}`} onClick={showMaps}><Icon name="map"/>Wayfinder<span className="count">{maps.length}</span></button><button className={`nav-button ${route.screen === 'board' ? 'active' : ''}`} onClick={() => showPlanning('board')}><Icon name="grid"/>Kanban</button><button className={`nav-button ${route.screen === 'specs' ? 'active' : ''}`} onClick={() => showPlanning('specs')}><Icon name="list"/>Specs</button><div className="sidebar-section">Maps</div><div className="map-nav-list">{maps.map(value=><button key={value.id} className={`map-nav ${route.screen==='map'&&map.id===value.id?'selected-map':''}`} aria-current={route.screen==='map'&&map.id===value.id?'page':undefined} aria-label={`Switch to map: ${value.title}`} onClick={()=>openMap(value.id)}><span className="small-square"/><span>{value.title}</span></button>)}</div><div className="sidebar-bottom"><span className="local-dot"/>Local only<span className="muted">No services connected</span></div></aside>
      {handle('navigation', 'workspace-navigation', 'nav', 160, navMax, navWidth, 1, undefined, !navVisible || compact)}
      <main className="main">
        <header className="topbar"><button hidden={full} className="icon-button" aria-label={navVisible ? 'Hide navigation' : 'Show navigation'} title={navVisible ? 'Hide navigation' : 'Show navigation'} aria-expanded={navVisible} aria-controls="workspace-navigation" onClick={() => compact ? setMobileNavOpen(!mobileNavOpen) : configure({ navHidden: !prefs.navHidden })}><Icon name="panel" size={17}/></button><div className="breadcrumb"><button onClick={planning ? () => showPlanning(route.screen) : showMaps}>{planning ? 'Workspace' : 'Wayfinder'}</button><Icon name="chevron" size={12}/><span>{planning ? route.screen === 'board' ? 'Kanban' : 'Specs' : mapsView?'All maps':map.title}</span>{full ? <span>/ {planning ? route.ticketId || route.specId : selected.id}</span> : null}</div><div className="search-box" hidden={full}><Icon name="search" size={16}/><input ref={search} aria-label={planning ? route.screen === 'board' ? 'Search tickets' : 'Search specs' : mapsView?'Search maps':'Search this map'} placeholder={planning ? 'Search saved work…' : mapsView?'Search maps…':'Search this map…'} value={mapsView?mapQuery:query} onChange={event=>mapsView?setMapQuery(event.target.value):navigate({query:event.target.value},true)}/><kbd>⌘ K</kbd></div><span className="spacer" hidden={!full}/><span className="avatar" title="Local human session">H</span></header>
        {planning && data.bootstrap ? <PlanningWorkspace route={route} navigate={navigate} data={data} busy={busy} onNew={setNewPlanning} onQuestion={openQuestion}/> : null}
        {route.error ? <p className="route-notice" role="status">{route.error}</p> : null}
        {mapsView && data.bootstrap ? <MapsOverview maps={maps} query={mapQuery} filter={mapFilter} onFilter={setMapFilter} onClear={()=>{setMapQuery('');setMapFilter('all');}} onOpen={openMap} onCreate={()=>setNewMapOpen(true)}/> : null}
        <section className="page-heading" hidden={planning||full||mapsView||!map.id}><div><div className="eyebrow">{map.id.toUpperCase()} <span>·</span> {(map.progress || 'Planning').toUpperCase()}</div><h1>{map.title}</h1><p>{map.destination}</p></div><div className="heading-actions"><button disabled={busy || !active} className="button primary" onClick={() => setNewOpen(true)}><Icon name="plus" size={16}/>New question</button><div className="progress-caption"><span>{counts.resolved} of {counts.total} answered</span><span className="progress-track"><i style={{ width: `${counts.total?counts.resolved/counts.total*100:0}%` }}/></span></div></div></section>
        <div className="map-location" hidden={planning||full||mapsView}><button className="quiet-button" onClick={showMaps}><Icon name="arrow" className="back-arrow" size={13}/>All maps</button><span className="location-divider"/><label htmlFor="map-switch">Map</label><select id="map-switch" aria-label="Switch map" value={map.id} onChange={event=>openMap(event.target.value)}>{maps.map(value=><option value={value.id} key={value.id}>{value.title}</option>)}</select><span className="map-scope-note">Scope: {map.scope}</span></div>
        <div className="view-toolbar" hidden={planning||full||mapsView}><div className="view-switch" role="group" aria-label="Wayfinder view"><button aria-pressed={!atlas} onClick={() => switchView('questions')}><Icon name="list" size={14}/>Focus view</button><button aria-pressed={atlas} onClick={() => switchView('atlas')}><Icon name="map" size={14}/>Atlas view</button></div><div className="panel-controls" hidden={!selected}>{focus ? <><button className="quiet-button" aria-pressed={!prefs.queueHidden} aria-controls="question-queue" onClick={() => configure({ queueHidden: !prefs.queueHidden })}>{prefs.queueHidden ? 'Show queue' : 'Hide queue'}</button><button className="quiet-button" aria-pressed={!prefs.contextHidden} aria-controls="decision-context" onClick={() => configure({ contextHidden: !prefs.contextHidden })}>{prefs.contextHidden ? 'Show decision map' : 'Hide decision map'}</button></> : <button className="quiet-button" aria-pressed={detailVisible} aria-controls="question-detail" onClick={() => configure({ detailsHidden: !prefs.detailsHidden })}>{detailVisible ? 'Hide details' : 'Show details'}</button>}</div></div>
        <div className="filter-bar" hidden={planning||full||mapsView||!items.length}><div className="status-filters"><button className={!status ? 'active' : ''} onClick={() => navigate({status:''},true)}>All work <span>{items.length}</span></button><button className={status === 'Ready' ? 'active' : ''} onClick={() => navigate({status:'Ready'},true)}>Ready next <span>{counts.ready}</span></button><button className={status === 'Blocked' ? 'active' : ''} onClick={() => navigate({status:'Blocked'},true)}>Blocked <span>{counts.blocked}</span></button></div><div className="filter-right"><select aria-label="Filter by status" value={status} onChange={event => navigate({status:event.target.value},true)}><option value="">All statuses</option>{["Ready","Blocked","Waiting","In progress","Resolved","Needs review","Out of scope"].map(value => <option key={value}>{value}</option>)}</select><select aria-label="Filter by label" value={label} onChange={event => navigate({label:event.target.value},true)}><option value="">All labels</option>{labels.map(value => <option key={value}>{value}</option>)}</select>{query || label || status ? <button className="quiet-button" onClick={clearFilters}>Clear</button> : null}<span className="result-count">{visible.length} {visible.length === 1 ? 'item' : 'items'}</span></div></div>
        <div ref={content} hidden={planning||mapsView} className={`workspace-content ${full ? 'full-question' : ''} ${narrow && !full ? 'narrow-content' : ''}`} style={{ gridTemplateColumns: columns, gridTemplateAreas: areas }}>
          {loading && !active ? <div className="empty" role="status">Loading saved questions…</div> : null}
          {!selected && !loading && active ? <section className="empty-map"><span className="empty-map-icon"><Icon name="map" size={29}/></span><h2>A destination. Now the first question.</h2><p>{map.destination}</p><p className="muted">{map.unresolved || 'What needs an answer before this work can move forward?'}</p><button className="button primary" onClick={()=>setNewOpen(true)}><Icon name="plus" size={15}/>Add the first question</button></section> : null}
          <section id="question-queue" className="focus-queue" hidden={full || !focus || prefs.queueHidden || !selected}><PanelHeading title="Question queue" onHide={() => configure({ queueHidden: true })}/><p className="focus-caption">One question at a time.</p>{visible.toSorted((a, b) => Number(a.state === 'resolved') - Number(b.state === 'resolved')).map(item => <ItemRow key={item.id} item={item} {...rowProps} dense/>)}{!visible.length ? empty : null}</section>
          {handle('question queue', 'question-queue', 'queue', 180, queueMax, queueWidth, 1, 'queue-resize', full || !focus || prefs.queueHidden || narrow || !selected)}
          {atlas && !full && selected ? <Graph key={map.id} items={items} links={links} visible={visible} selected={selected.id} onSelect={select}/> : null}
          {handle('details', 'question-detail', 'inspector', 340, inspectorMax, inspectorWidth, -1, 'inspector-resize', full || focus || !detailVisible || narrow)}
          <div id="question-detail" className="detail-slot" hidden={!detailVisible}>{selected ? <Detail key={`${data.bootstrap.workspace.id}:${map.id}:${selected.id}`} workspaceId={data.bootstrap.workspace.id} item={selected} map={map} items={items} links={links} onSelect={select} mutate={mutate} query={data.query} busy={busy} close={!focus ? () => configure({ detailsHidden: true }) : undefined} expanded={full} onExpand={() => navigate({ expanded: !full })}/> : null}</div>
          {handle('decision map', 'decision-context', 'context', 180, contextMax, contextWidth, -1, 'context-resize', full || !focus || prefs.contextHidden || narrow || !selected)}
          <aside id="decision-context" className="focus-context" aria-label="Decision map" hidden={full || !focus || prefs.contextHidden || !selected}><PanelHeading title="Decision map" onHide={() => configure({ contextHidden: true })}/><span className="small-label">Before this</span>{incoming(selected?.id, links, items).map(item => <button className="context-card" key={item.id} onClick={() => select(item.id)}><Status value={item.status}/><span>{item.title}</span><span className="mono">{item.id}</span></button>)}{!incoming(selected?.id, links, items).length ? <p className="muted">No prerequisites.</p> : null}<div className="context-line"/><div className="context-current"><span className="small-label">Current question</span><span>{selected?.title}</span><span className="mono">{selected?.id}</span></div><div className="context-line"/><span className="small-label">This unlocks</span>{links.filter(link => link.kind === 'blocks' && link.from === selected?.id).map(link => { const item = items.find(item => item.id === link.to); return <button className="context-card" key={item.id} onClick={() => select(item.id)}><span>{item.title}</span><span className="mono">{item.id} <Icon name="arrow" size={14}/></span></button>; })}{!links.some(link => link.kind === 'blocks' && link.from === selected?.id) ? <p className="muted">No dependent questions.</p> : null}</aside>
        </div>
      </main>
    </div>
    {newPlanning && data.bootstrap ? <PlanningCreate key={newPlanning} type={newPlanning} workspaceId={data.bootstrap.workspace.id} maps={maps} specs={data.snapshot?.specs || []} questions={data.snapshot?.questions || []} initialMap={route.mapId} initialSpec={route.specFilter} busy={busy} mutate={mutate} onClose={() => setNewPlanning(null)} onCreated={record => { const type = newPlanning; setNewPlanning(null); navigate(type === 'ticket' ? { screen: 'board', ticketId: record.id, expanded: false, query: '', label: '', status: '', mapId: '', specFilter: '' } : { screen: 'specs', specId: record.id, expanded: false, query: '', mapId: '' }); setNotification(`${type === 'ticket' ? 'Ticket' : 'Spec'} saved`); }}/> : null}
    {notification ? <div className="toast" role="status"><Icon name="check" size={15}/>{notification}</div> : null}
    {newOpen && data.bootstrap ? <CreateDialog key={`new-question:${map.id}`} type="question" workspaceId={data.bootstrap.workspace.id} mapId={map.id} onClose={() => setNewOpen(false)} mutate={mutate} busy={busy} onCreated={question => { setNewOpen(false); configure({detailsHidden:false}); navigate({selected:question.id,query:'',label:'',status:''}); setNotification('Question saved'); }}/> : null}
    {newMapOpen && data.bootstrap ? <CreateDialog type="map" workspaceId={data.bootstrap.workspace.id} onClose={() => setNewMapOpen(false)} mutate={mutate} busy={busy} onCreated={created => { setNewMapOpen(false); configure({detailsHidden:false}); navigate(mapRoute(created)); setNotification('Map saved'); }}/> : null}
  </>;
}

createRoot(document.getElementById('root')).render(<App/>);
