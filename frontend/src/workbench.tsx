import React, { useMemo, useState } from 'react';
import type { Asset, DomainRecord, Evidence, Inventory, Job, Result, Scenario } from './types';
const date = (value: string) => new Date(value).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
const short = (value: string) => value.slice(0, 8);
const json = (value: unknown) => JSON.stringify(value, null, 2);
const paths: Record<string, string> = {
    Overview: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
    Inventory: 'M4 5h16v15H4z M8 5V3h8v2 M8 10h8 M8 14h8 M8 18h4',
    Topology: 'M8 5h8 M5 8v8 M19 8v8 M8 19h8 M3 3h5v5H3z M16 3h5v5h-5z M3 16h5v5H3z M16 16h5v5h-5z',
    Scenarios: 'M5 4h14v17H5z M9 4V2h6v2 M9 9h6 M9 13h6 M9 17h3',
    'Attack analysis': 'M12 3 3 20h18L12 3z M12 9v5 M12 17v.2',
    'Defence planner': 'M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3z M8 12l3 3 5-6',
    'Event replay': 'M4 7h10 M4 12h7 M4 17h7 M16 8l5 4-5 4V8z',
    Experiments: 'M9 3h6 M10 3v6L4 19q0 2 2 2h12q2 0 2-2l-6-10V3 M8 14h8',
    Reports: 'M5 3h10l4 4v14H5z M14 3v5h5 M9 12h6 M9 16h6',
    Settings: 'M4 7h16 M4 17h16 M8 4v6 M16 14v6',
    Evidence: 'M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3z M12 8v5 M12 16v.2',
    'Run comparison': 'M3 5h7v14H3z M14 5h7v14h-7z M7 9v6 M17 9v6',
    search: 'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6',
    arrow: 'M4 12h16 M15 7l5 5-5 5',
    clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 7v5l3 2',
    shield: 'M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6l-8-3z',
};
export function Icon({ name, size = 17 }: {
    name: string;
    size?: number;
}) {
    return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name] || paths.Inventory}/></svg>;
}
export function Empty({ title, children }: {
    title: string;
    children?: React.ReactNode;
}) {
    return <div className="empty-state"><Icon name="Inventory" size={28}/><h3>{title}</h3><p>{children}</p></div>;
}
function freshness(e: Evidence) { return e.expires_at && new Date(e.expires_at) <= new Date() ? 'stale' : e.confidence; }
export function Overview({ inventory, records, scenarios, jobs, onNavigate, onScenario, onSeed, onCancel, canWrite, busy }: {
    inventory?: Inventory;
    records: DomainRecord[];
    scenarios: DomainRecord[];
    jobs: Job[];
    onNavigate: (page: string) => void;
    onScenario: (id: string) => void;
    onSeed: () => void;
    onCancel: (id: string) => void;
    canWrite: boolean;
    busy: boolean;
}) {
    const analyses = records.filter(r => r.kind === 'analysis');
    const segments = (inventory?.assets || []).reduce<Record<string, Asset[]>>((groups, a) => { (groups[a.segment] ??= []).push(a); return groups; }, {});
    const network = inventory?.relationships.filter(e => e.kind === 'network') || [];
    const review = inventory?.evidence.filter(e => freshness(e) !== 'confirmed') || [];
    const latest = analyses.at(-1);
    const latestResult = latest?.data.result as Result | undefined;
    return <>
  <div className="page-intro"><div><span className="overline">WORKSPACE SUMMARY</span><h2>Lab posture</h2><p>{inventory ? inventory.name : 'Start with the bundled lab or import an inventory to build your model.'}</p></div>{canWrite && <button className={inventory ? 'secondary' : ''} disabled={busy} onClick={onSeed}>{inventory ? 'Reload bundled lab' : 'Load bundled lab'}<Icon name="arrow"/></button>}</div>
  <div className="stat-strip">{[
            { label: 'Modelled assets', value: inventory?.assets.length ?? 0, note: `${Object.keys(segments).length} network segments` },
            { label: 'Typed relationships', value: inventory?.relationships.length ?? 0, note: `${network.length} network connections` },
            { label: 'Critical assets', value: inventory?.assets.filter(a => a.critical).length ?? 0, note: 'Defined in the inventory' },
            { label: 'Evidence to review', value: review.length, note: inventory ? `${inventory.evidence.length} evidence records total` : 'No snapshot loaded' },
        ].map(s => <div className="stat" key={s.label}><span>{s.label}</span><strong>{s.value}</strong><small>{s.note}</small></div>)}</div>
  <div className="overview-grid">
   <section className="network-panel"><div className="section-heading"><div><span className="overline">NETWORK MODEL</span><h2>Segment inventory</h2></div><button className="text-button" onClick={() => onNavigate('Topology')}>Open topology<Icon name="arrow"/></button></div>
    {!inventory ? <Empty title="No network snapshot">Import an inventory or load the isolated lab.</Empty> : <><div className="segment-board">{Object.entries(segments).map(([segment, assets]) => <div className="segment-column" key={segment}><h3>{segment}<span>{assets?.length}</span></h3>{assets?.slice(0, 5).map(a => <button key={a.id} className={'asset-chip ' + (a.critical ? 'critical' : '')} onClick={() => onNavigate('Inventory')}><Icon name={a.kind === 'principal' ? 'Evidence' : 'Inventory'} size={14}/><span>{a.label}<small>{a.kind}</small></span>{a.critical && <span className="critical-mark" title="Critical asset">!</span>}</button>)}{(assets?.length || 0) > 5 && <small>+{assets!.length - 5} additional assets</small>}</div>)}</div><div className="network-footnote"><span className="legend-dot"/>Imported topology<span>{network.filter(e => e.essential).length} required network relationships</span></div></>}
   </section>
   <section className="review-panel"><div className="section-heading"><div><span className="overline">MODEL CONFIDENCE</span><h2>Evidence desk</h2></div><Icon name="Evidence"/></div><div className="review-count">{review.length}<span>records need attention</span></div><p>Expired or uncertain evidence can change which transitions the model supports.</p>{review.slice(0, 3).map(e => <div className="evidence-mini" key={e.id}><span className="status-pill warning">{freshness(e)}</span><code>{e.id}</code></div>)}{inventory && review.length === 0 && <div className="inline-note"><span className="legend-dot"/>No stale or uncertain evidence in this snapshot. Assertions remain labelled by collection method.</div>}<button className="secondary" onClick={() => onNavigate('Evidence')}>Review evidence<Icon name="arrow"/></button></section>
  </div>
  <section><div className="section-heading"><div><span className="overline">SCENARIO REGISTER</span><h2>Assumptions and outcomes</h2></div><span className="subtle">{scenarios.length} saved scenarios</span></div>{scenarios.length === 0 ? <Empty title="No scenarios yet">Load the lab to inspect the three predefined cases.</Empty> : <div className="table-scroll"><table><thead><tr><th>Scenario</th><th>Initial capabilities</th><th>Latest result</th><th>States / runtime</th><th /></tr></thead><tbody>{scenarios.map(s => { const scenario = s.data as unknown as Scenario; const run = analyses.filter(r => r.data.scenario_id === s.id).at(-1); const result = run?.data.result as Result | undefined; return <tr key={s.id}><td><b>{scenario.name}</b><small>{short(s.id)} / snapshot {short(scenario.snapshot_id)}</small></td><td><div className="compact-chips">{scenario.initial.map(c => <code key={c}>{c}</code>)}</div></td><td>{result ? <span className={'status-pill ' + (result.truncated ? 'warning' : result.targets.some(t => t.reachable) ? 'danger' : 'good')}>{result.truncated ? 'Search limited' : `${result.targets.filter(t => t.reachable).length} / ${result.targets.length} targets reached`}</span> : <span className="status-pill neutral">Not analysed</span>}</td><td>{result ? `${result.states_explored} / ${result.runtime_ms} ms` : '—'}</td><td><button className="text-button" onClick={() => onScenario(s.id)} aria-label={'Analyse ' + scenario.name}>Analyse<Icon name="arrow"/></button></td></tr>; })}</tbody></table></div>}</section>
  <div className="overview-grid bottom-grid"><section><div className="section-heading"><h2>Analysis queue</h2><Icon name="clock"/></div>{jobs.length === 0 ? <p className="subtle">No jobs submitted. Choose a scenario to begin.</p> : jobs.slice(0, 5).map(j => <div className="row" key={j.id}><div><b>{j.kind}</b><small>{short(j.id)}</small></div><span className={'status-pill ' + (j.status === 'failed' ? 'danger' : j.status === 'completed' ? 'good' : 'neutral')}>{j.status}</span>{j.error && <span role="alert">{j.error}</span>}{canWrite && ['queued', 'running'].includes(j.status) && <button className="text-button" onClick={() => onCancel(j.id)}>Cancel</button>}</div>)}</section><section><div className="section-heading"><h2>Latest completed analysis</h2><Icon name="Run comparison"/></div>{latestResult ? <><p><b>{latestResult.targets.filter(t => t.reachable).length} of {latestResult.targets.length}</b> critical targets reached within the configured search.</p><small>{date(latest!.created_at)} / {latestResult.runtime_ms} ms</small><button className="secondary" onClick={() => onNavigate('Run comparison')}>Compare saved runs<Icon name="arrow"/></button></> : <p className="subtle">Run a scenario to see its results here.</p>}</section></div>
 </>;
}
export function InventoryBrowser({ inventory, onOpenGraph }: {
    inventory: Inventory;
    onOpenGraph: () => void;
}) {
    const [sortBy, setSortBy] = useState('label');
    const [query, setQuery] = useState(''), [kind, setKind] = useState(''), [segment, setSegment] = useState(''), [critical, setCritical] = useState(false), [selected, setSelected] = useState<Asset | null>(null), [copied, setCopied] = useState(false);
    const assets = inventory.assets.filter(a => (a.label + ' ' + a.id).toLowerCase().includes(query.toLowerCase()) && (!kind || a.kind === kind) && (!segment || a.segment === segment) && (!critical || a.critical)).sort((a, b) => String(a[sortBy as 'label' | 'kind' | 'segment']).localeCompare(String(b[sortBy as 'label' | 'kind' | 'segment'])));
    const related = inventory.relationships.filter(e => e.source === selected?.id || e.target === selected?.id);
    const evIds = new Set(related.flatMap(e => e.evidence));
    function exportAssets() { const quote = (v: unknown) => '"' + String(v).replace(/^([\s]*[=+@-])/g, "'$1").replaceAll('"', '""') + '"'; const csv = [['id', 'label', 'type', 'segment', 'critical'], ...assets.map(a => [a.id, a.label, a.kind, a.segment, a.critical])].map(row => row.map(quote).join(',')).join('\r\n'); const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' })); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'aegistwin-filtered-assets.csv'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
    return <section><div className="section-heading"><div><span className="overline">ASSET REGISTER</span><h2>{inventory.name}</h2></div><button className="secondary" onClick={exportAssets} disabled={!assets.length}>Export filtered assets</button></div><div className="filter-bar"><label className="search-field"><Icon name="search"/><input aria-label="Search inventory" placeholder="Search assets or identifiers" value={query} onChange={e => setQuery(e.target.value)}/></label><label>Type<select value={kind} onChange={e => setKind(e.target.value)}><option value="">All types</option>{[...new Set(inventory.assets.map(a => a.kind))].map(k => <option key={k}>{k}</option>)}</select></label><label>Segment<select value={segment} onChange={e => setSegment(e.target.value)}><option value="">All segments</option>{[...new Set(inventory.assets.map(a => a.segment))].map(s => <option key={s}>{s}</option>)}</select></label><label>Sort by<select value={sortBy} onChange={e => setSortBy(e.target.value)}><option value="label">Asset name</option><option value="kind">Type</option><option value="segment">Segment</option></select></label><label className="check-label"><input type="checkbox" checked={critical} onChange={e => setCritical(e.target.checked)}/>Critical only</label></div><div className={'inventory-layout ' + (selected ? 'has-selection' : '')}><div><div className="list-caption">{assets.length} of {inventory.assets.length} assets</div><div className="table-scroll"><table><thead><tr><th>Asset</th><th>Type</th><th>Segment</th><th>Designation</th></tr></thead><tbody>{assets.map(a => <tr key={a.id} className={selected?.id === a.id ? 'selected-row' : ''}><td><button className="asset-link" onClick={() => { setSelected(a); setCopied(false); }}>{a.label}</button><small>{a.id}</small></td><td>{a.kind}</td><td><span className="segment-label">{a.segment}</span></td><td>{a.critical ? <span className="status-pill warning">Critical target</span> : <span className="subtle">Standard</span>}</td></tr>)}</tbody></table></div>{!assets.length && <Empty title="No matching assets">Try a different search or filter.</Empty>}</div>{selected && <div className="inspector"><div className="section-heading"><span className="overline">ASSET DETAILS</span><button className="text-button" onClick={() => setSelected(null)}>Close</button></div><h3>{selected.label}</h3><code>{selected.id}</code><dl><dt>Type</dt><dd>{selected.kind}</dd><dt>Segment</dt><dd>{selected.segment}</dd><dt>Critical target</dt><dd>{selected.critical ? 'Yes' : 'No'}</dd></dl><div className="button-row"><button className="secondary" onClick={async () => { try {
        await navigator.clipboard.writeText(selected.id);
        setCopied(true);
    }
    catch {
        setCopied(false);
    } }}>{copied ? 'Copied' : 'Copy ID'}</button><button className="secondary" onClick={onOpenGraph}>Open topology</button></div><h4>Relationships ({related.length})</h4>{related.map(e => <div className="relationship-detail" key={e.id}><span className="status-pill neutral">{e.kind}</span><p>{e.source} → {e.target}</p><small>{e.essential ? 'Required connectivity' : 'Not marked essential'} / {e.evidence.join(', ')}</small></div>)}<h4>Linked evidence</h4>{inventory.evidence.filter(e => evIds.has(e.id)).map(e => <details key={e.id}><summary>{e.id}</summary><p>{e.note}</p><small>{e.source} / {e.confidence}</small></details>)}</div>}</div></section>;
}
export function EvidenceDesk({ inventory, scenario, onCorrect }: {
    inventory?: Inventory;
    scenario?: Scenario;
    onCorrect: () => void;
}) {
    const [filter, setFilter] = useState('all'), [query, setQuery] = useState(''), [selected, setSelected] = useState<Evidence | null>(null);
    if (!inventory)
        return <section><Empty title="Choose a snapshot">Evidence belongs to an immutable inventory snapshot.</Empty></section>;
    const evidence = inventory.evidence.filter(e => (filter === 'all' || (filter === 'attention' ? freshness(e) !== 'confirmed' : e.method === filter)) && (e.id + ' ' + e.source + ' ' + e.note).toLowerCase().includes(query.toLowerCase()));
    return <section><div className="section-heading"><div><span className="overline">PROVENANCE & FRESHNESS</span><h2>Evidence desk</h2></div><span className="subtle">{inventory.evidence.length} records in selected snapshot</span></div><p>Inspect what supports the model. Confirmed assertions and direct observations have different collection methods; neither is an exploitability claim.</p><div className="filter-bar"><label className="search-field"><Icon name="search"/><input aria-label="Search evidence" placeholder="Search evidence, source or notes" value={query} onChange={e => setQuery(e.target.value)}/></label><label>Collection filter<select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All evidence</option><option value="attention">Needs attention</option><option value="observed">Directly observed</option><option value="asserted">Manually asserted</option><option value="imported">Imported</option></select></label></div><div className="table-scroll"><table><thead><tr><th>Evidence / source</th><th>Method</th><th>Confidence</th><th>Freshness</th><th>Supported relationships</th></tr></thead><tbody>{evidence.map(e => <tr key={e.id}><td><button className="asset-link" onClick={() => setSelected(e)}>{e.id}</button><small>{e.source}</small></td><td>{e.method || 'Unspecified'}</td><td><span className={'status-pill ' + (e.confidence === 'confirmed' ? 'good' : 'warning')}>{e.confidence}</span></td><td>{freshness(e) === 'stale' ? <span className="status-pill danger">Expired</span> : e.expires_at ? 'Until ' + date(e.expires_at) : 'No expiry supplied'}</td><td>{inventory.relationships.filter(r => r.evidence.includes(e.id)).length}</td></tr>)}</tbody></table></div>{!evidence.length && <Empty title="No matching evidence">No records match these filters.</Empty>}{selected && <div className="evidence-inspector"><div className="section-heading"><h3>{selected.id}</h3><button className="text-button" onClick={() => setSelected(null)}>Close</button></div><p>{selected.note}</p><dl><dt>Collected</dt><dd>{selected.collected_at ? date(selected.collected_at) : 'Not supplied'}</dd><dt>Source</dt><dd>{selected.source}</dd><dt>Supported rules</dt><dd>{scenario?.rules.filter(r => r.evidence.includes(selected.id) || r.relationships.some(id => inventory.relationships.find(e => e.id === id)?.evidence.includes(selected.id))).map(r => r.id).join(', ') || 'No linked rule in selected scenario'}</dd></dl><button className="secondary" onClick={onCorrect}>Open inventory corrections<Icon name="arrow"/></button></div>}</section>;
}
export function RunComparison({ records }: {
    records: DomainRecord[];
}) {
    const runs = records.filter(r => r.kind === 'analysis');
    const [left, setLeft] = useState(runs.at(-2)?.id || runs.at(-1)?.id || ''), [right, setRight] = useState(runs.at(-1)?.id || '');
    const a = runs.find(r => r.id === left), b = runs.find(r => r.id === right);
    const ar = a?.data.result as Result | undefined, br = b?.data.result as Result | undefined;
    const scenarioName = (r: DomainRecord) => String(records.find(s => s.id === r.data.scenario_id)?.data.name || r.data.scenario_id);
    const changes = useMemo(() => { if (!a || !b)
        return []; return ['snapshot_id', 'scenario_id'].filter(k => a.data[k] !== b.data[k]); }, [a, b]);
    const targetKey = (t: {
        asset_id: string;
        capability?: string;
    }) => t.asset_id + '|' + (t.capability || '');
    const keys = [...new Set([...(ar?.targets || []), ...(br?.targets || [])].map(targetKey))];
    const status = (result: Result | undefined, asset: string) => { const target = result?.targets.find(t => targetKey(t) === asset); return !target ? 'Not a target' : target.reachable ? 'Reachable' : result?.truncated ? 'Unknown: search limited' : 'Not reached'; };
    function options() { return runs.map(r => <option key={r.id} value={r.id}>{scenarioName(r)} / {short(r.id)} / {date(r.created_at)}</option>); }
    return <section><div className="section-heading"><div><span className="overline">REPRODUCIBLE COMPARISON</span><h2>Compare saved analyses</h2></div><span className="subtle">{runs.length} available runs</span></div>{!runs.length ? <Empty title="No completed analyses">Run a scenario first. Comparisons use saved results, never regenerated data.</Empty> : <><div className="compare-selectors"><label>Baseline run<select value={left} onChange={e => setLeft(e.target.value)}>{options()}</select></label><span className="versus">vs</span><label>Comparison run<select value={right} onChange={e => setRight(e.target.value)}>{options()}</select></label><button className="secondary" onClick={() => { setLeft(right); setRight(left); }}>Swap</button></div>{a && b && ar && br && <>{left === right && <div className="inline-note">The same run is selected on both sides. Choose another run to inspect differences.</div>}{(changes.length > 0 || json(ar.limits) !== json(br.limits)) && <div className="comparison-warning">Inputs differ: {[...changes, json(ar.limits) !== json(br.limits) ? 'algorithm configuration' : ''].filter(Boolean).join(', ')}. These results do not isolate the effect of a defensive change.</div>}<div className="comparison-chart" role="img" aria-label={`Reachable targets: baseline ${ar.targets.filter(t => t.reachable).length}, comparison ${br.targets.filter(t => t.reachable).length}`}><h3>Reachable critical targets</h3>{[{ name: 'Baseline', result: ar }, { name: 'Comparison', result: br }].map(row => <div className="bar-row" key={row.name}><span>{row.name}</span><div className="bar-track"><div style={{ width: (row.result.targets.filter(t => t.reachable).length / Math.max(1, ar.targets.length, br.targets.length) * 100) + '%' }}/></div><b>{row.result.targets.filter(t => t.reachable).length} / {row.result.targets.length}</b></div>)}{(ar.truncated || br.truncated) && <small>Bars count discovered reachability. A zero from a limited search does not establish unreachability.</small>}</div><table><thead><tr><th>Critical asset</th><th>Baseline</th><th>Comparison</th><th>Change</th></tr></thead><tbody>{keys.map(id => <tr key={id}><td><code>{id.split('|')[0]}</code><small>{id.split('|')[1]}</small></td><td>{status(ar, id)}</td><td>{status(br, id)}</td><td>{status(ar, id) === status(br, id) ? 'No change' : `${status(ar, id)} → ${status(br, id)}`}</td></tr>)}</tbody></table><div className="run-facts">{[{ record: a, result: ar, label: 'Baseline' }, { record: b, result: br, label: 'Comparison' }].map(row => <div key={row.label}><h3>{row.label} provenance</h3><dl><dt>Run</dt><dd>{row.record.id}</dd><dt>Snapshot</dt><dd>{String(row.record.data.snapshot_id)}</dd><dt>Engine</dt><dd>{row.result.engine_version || 'Recorded in run'}</dd><dt>States / runtime</dt><dd>{row.result.states_explored} / {row.result.runtime_ms} ms</dd><dt>Removed relationships</dt><dd>{((row.record.data.request as {
        removed?: string[];
    })?.removed || []).join(', ') || 'None'}</dd><dt>Search</dt><dd>{row.result.truncated ? 'Truncated: ' + row.result.warnings.join(', ') : 'Completed within limits'}</dd></dl></div>)}</div></>}</>}</section>;
}
export function ReportLibrary({ records, base }: {
    records: DomainRecord[];
    base: string;
}) {
    const [filter, setFilter] = useState('all'), [query, setQuery] = useState('');
    const reports = records.filter(r => ['analysis', 'optimisation', 'evaluation'].includes(r.kind) && (filter === 'all' || r.kind === filter) && (r.id + ' ' + r.kind + ' ' + String(records.find(s => s.id === r.data.scenario_id)?.data.name || '')).toLowerCase().includes(query.toLowerCase())).reverse();
    return <section><div className="section-heading"><div><span className="overline">EVIDENCE EXPORTS</span><h2>Report library</h2></div><span className="subtle">{reports.length} reports</span></div><p>Each export contains its exact snapshot, scenario, evidence and recorded limits.</p><div className="filter-bar"><label className="search-field"><Icon name="search"/><input aria-label="Search reports" placeholder="Search scenario or run identifier" value={query} onChange={e => setQuery(e.target.value)}/></label><label>Report type<select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All types</option><option value="analysis">Attack analysis</option><option value="optimisation">Defence plan</option><option value="evaluation">Evaluation</option></select></label></div>{!reports.length ? <Empty title="No matching reports">Completed analyses, plans and evaluations appear here.</Empty> : <div className="table-scroll"><table><thead><tr><th>Scenario / run</th><th>Type</th><th>Created</th><th>Snapshot</th><th>Export</th></tr></thead><tbody>{reports.map(r => <tr key={r.id}><td><b>{String(records.find(s => s.id === r.data.scenario_id)?.data.name || 'Saved run')}</b><small>{r.id}</small></td><td><span className="status-pill neutral">{r.kind}</span></td><td>{date(r.created_at)}</td><td><code>{short(String(r.data.snapshot_id))}</code></td><td><div className="button-row"><a className="download-link" href={'/api' + base + '/reports/' + r.id + '?format=html'}>HTML report<Icon name="arrow" size={13}/></a><a className="download-link" href={'/api' + base + '/reports/' + r.id + '?format=json'}>JSON</a></div></td></tr>)}</tbody></table></div>}</section>;
}
