// spec/tools/dev/part_conformance.mjs
// PART CONFORMANCE, THE PROTOTYPE (docs/part-conformance-design.md): two checks
// generated from a built part, with no line written per part.
//
//   cabling   every place a cable can end on the part, in each configuration,
//             placed in a frame the way a rack holds it (front and rear rail,
//             a setback): the end is offered to an agent, a cable to it is
//             accepted, lands (no loose end), routes, and the route's legs
//             stand on the end's mating point along its axis, in the points
//             both the 2-D panes and the 3-D scene are handed.
//   settings  every state the drawings declare (the Explorer reads these) is a
//             state the agent's tools take (`state.set`, `field`), and setting
//             it gives the document the page would write and a drawing that
//             paints it.
//
// It reads a built library (library/dist) and the kit, and nothing else. The
// reader of the drawings here is written from `<face>.elements.json` and the
// `<device>.configs.json` the site's own reader also uses; it is not the
// site's DOM reader, so where a verdict depends on the DOM (a side pane's
// drawing) the report says it was not judged.
//
// Imported by part_conformance.py's node entry (part_conformance_run.mjs).

import fs from 'node:fs';
import path from 'node:path';
import * as M from '../../../kit/rack/model.js';
import {apply} from '../../../kit/rack/commands.js';
import {configFacts} from '../../../kit/rack/catalog.js';
import {statesFor} from '../../../kit/rack/states.js';
import {freePorts} from '../../../kit/rack/queries.js';
import {settleEnd, zeroUEnds, cableEndPaths} from '../../../kit/rack/ports.js';
import {routePath, portPoint, endPane, PLUG_REACH} from '../../../kit/rack/route.js';
import {portPathOf, looseReason, connectorOf, proposeMedia} from '../../../kit/rack/cable-rules.js';
import {itemBox, setbackOf} from '../../../kit/rack/fit.js';
import {solidsOf, legCrossings} from '../../../kit/rack/solids.js';
import {redirectsOf} from '../../../kit/redirects.js';

const FACES = ['front', 'rear'];
const RAIL_DEPTH = 740;
const uniq = a => [...new Set(a)];
const finite = p => !!p && ['x', 'y', 'z'].every(k => Number.isFinite(p[k]));
const near = (a, b, tol) => Math.abs(a - b) <= tol;
const modelOf = (comp, ref) => comp?.attrs?.model || String(ref ?? '').split('/').pop().split('@')[0].toUpperCase();
const vocab = list => [...list].sort().join(' ');

// ── the library as the site reads it ────────────────────────────────────
export function openDist(dist) {
  const read = name => JSON.parse(fs.readFileSync(path.join(dist, name), 'utf8'));
  const list = read('components.json').components;
  const key = c => `${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`;
  const comps = new Map(list.map(c => [key(c), c]));
  const chassis = read('rack.json').devices;
  const slotMemo = new Map(), faceMemo = new Map(), textMemo = new Map();
  return {
    dist, chassis, comps, list,
    redirects: redirectsOf(list),
    compByRef: ref => (ref == null ? null : comps.get(String(ref).split(':')[0]) ?? null),
    chassisOf: ref => (Object.hasOwn(chassis, ref) ? chassis[ref] : null),
    slotsOf: ref => {
      if (!slotMemo.has(ref)) {
        let v = null;
        try {
          const j = read(`${ref}.configs.json`);
          v = {bays: j.bays || {}, cages: j.cages || {}, configs: j.configs || [], default: j.default ?? null, 'pdu-class': j['pdu-class'] ?? null};
        } catch { v = null; }
        slotMemo.set(ref, v);
      }
      return slotMemo.get(ref);
    },
    face: file => {
      if (!file) return null;
      if (!faceMemo.has(file)) {
        let v = null;
        try {
          v = read(file.replace(/\.svg$/, '.elements.json'));
          // the back of a part seated in a bay is drawn on the host's other panel with `of` for its address (a projection)
          v.elements = v.elements.map(e => (e.path == null && e.of != null ? {...e, path: e.of, projected: true} : e));
        } catch { v = null; }
        faceMemo.set(file, v);
      }
      return faceMemo.get(file);
    },
    svg: file => {
      if (!textMemo.has(file)) {
        let v = '';
        try { v = fs.readFileSync(path.join(dist, file), 'utf8'); } catch { v = ''; }
        textMemo.set(file, v);
      }
      return textMemo.get(file);
    },
  };
}

const ctxOf = W => ({chassisOf: W.chassisOf, slotsOf: W.slotsOf, compByRef: W.compByRef, redirects: W.redirects});
const newFrame = () => { const r = M.newRack(); return {...r, frame: {...r.frame, heightRU: 120, railDepth: RAIL_DEPTH}}; };   // tall enough for the tallest part and a copy of it above
const entryOf = rack => rack.items[0] ?? rack.zeroU[0];

// ── SETTINGS ────────────────────────────────────────────────────────────
// What the drawings declare for one configuration, over every face it draws
// (the lamps of the parts seated in its bays included): {path: [states]}.
export function drawnStates(W, cfg) {
  const out = {};
  for (const file of Object.values(cfg.files || {})) {
    for (const e of W.face(file)?.elements || [])
      if (Array.isArray(e.states) && e.states.length && e.path && !Object.hasOwn(out, e.path)) out[e.path] = e.states;
  }
  return out;
}
// a display's whole readings, off the drawing's text (they are not in the elements documents)
export function drawnMessages(W, cfg) {
  const out = {};
  for (const file of uniq(Object.values(cfg.files || {}))) {
    const text = W.svg(file);
    if (!text.includes('data-messages')) continue;
    for (const m of text.matchAll(/<[a-z]+\s[^>]*data-messages="[^>]*>/g)) {
      const p = /data-path="([^"]*)"/.exec(m[0]), msg = /data-messages="([^"]*)"/.exec(m[0]);
      if (p && msg) out[p[1]] = msg[1].split(/\s+/).filter(Boolean);
    }
  }
  return out;
}

// A placed copy of the part, in a frame (beside the rack when it stands there).
function placed(W, ref, cfgName, variant = {}) {
  const ctx = ctxOf(W);
  let rack = newFrame();
  if (W.chassisOf(ref)?.mount === 'rack-side') {
    const r = apply(rack, [{op: 'zerou.place', ref, cfg: cfgName, at: 'left-rear', ru: 1}], ctx);
    return r.error ? {error: r.error} : {rack: r.rack, id: r.rack.zeroU[0].id, zero: true, ctx};
  }
  const r = M.withItem(rack, {ref, cfg: cfgName, ru: 8, face: variant.face ?? 'front', label: ref});
  rack = r.rack;
  const id = rack.items[0].id;
  if (variant.setback) rack = {...rack, items: rack.items.map(i => (i.id === id ? {...i, setback: variant.setback} : i))};
  return {rack, id, zero: false, ctx};
}

export function checkSettings(W, ref, cfgName, {maxStates = 400} = {}) {
  const found = [], counts = {drawn: 0, declared: 0, set: 0, refused: 0};
  const slots = W.slotsOf(ref);
  const cfg = slots?.configs.find(c => c.name === cfgName);
  if (!cfg) return {found: [{code: 'S0', text: 'the configuration is not in configs.json'}], counts};
  const drawn = drawnStates(W, cfg), paths = Object.keys(drawn);
  const facts = configFacts(slots, cfgName), declared = facts?.states || {};
  counts.drawn = paths.length; counts.declared = Object.keys(declared).length;
  const unknown = paths.filter(p => !Object.hasOwn(declared, p));
  if (unknown.length) found.push({code: 'S1', n: unknown.length, of: paths.length,
    text: `${unknown.length} of ${paths.length} states the drawings declare are not in the agent's catalogue (configs.json states)`,
    examples: unknown.slice(0, 4).map(p => `${p} (${drawn[p].slice(0, 3).join('/')})`)});
  const phantom = Object.keys(declared).filter(p => !Object.hasOwn(drawn, p));
  if (phantom.length) found.push({code: 'S2', n: phantom.length, text: `${phantom.length} catalogue states have no drawn element`, examples: phantom.slice(0, 4)});
  const differ = paths.filter(p => Object.hasOwn(declared, p) && vocab(declared[p]) !== vocab(drawn[p]));
  if (differ.length) found.push({code: 'S3', n: differ.length, text: `${differ.length} paths have another vocabulary in the drawing than in the catalogue`,
    examples: differ.slice(0, 3).map(p => `${p}: drawing ${drawn[p].join('/')} vs catalogue ${declared[p].join('/')}`)});
  const at = placed(W, ref, cfgName);
  if (at.error) return {found: [...found, {code: 'S0', text: `could not place the part: ${at.error}`}], counts};
  const {rack, id, ctx} = at;
  const byVocab = new Map(), todo = [];
  for (const p of paths) {
    todo.push([p, drawn[p][0]]);                                   // every path takes a state
    const v = vocab(drawn[p]);
    if (!byVocab.has(v)) { byVocab.set(v, p); for (const s of drawn[p].slice(1)) todo.push([p, s]); }   // every state of a vocabulary, once
  }
  const refused = [], wrongDoc = [], okSets = [];
  for (const [p, s] of todo.slice(0, maxStates)) {
    const r = apply(rack, [{op: 'state.set', id, path: p, state: s}], ctx);
    if (r.error) { refused.push(`${p}=${s}: ${r.error}`); counts.refused++; continue; }
    counts.set++; okSets.push([p, s]);
    // the document a page writes is the entry with that one key more
    if (JSON.stringify(entryOf(r.rack).states) !== JSON.stringify({...(entryOf(rack).states || {}), [p]: s})) wrongDoc.push(`${p}=${s}`);
  }
  if (refused.length) found.push({code: 'S4', n: refused.length, text: `the agent's state.set refuses ${refused.length} of ${Math.min(todo.length, maxStates)} states the drawings declare`, examples: refused.slice(0, 2)});
  if (wrongDoc.length) found.push({code: 'S5', n: wrongDoc.length, text: `${wrongDoc.length} states set through the agent give another document than the page writes`, examples: wrongDoc.slice(0, 4)});
  if (okSets.length) {
    const entry = {...entryOf(rack), states: Object.fromEntries(okSets)};
    const kept = statesFor(entry, facts), lost = Object.keys(entry.states).filter(p => !Object.hasOwn(kept, p));
    if (lost.length) found.push({code: 'S6', n: lost.length, text: `statesFor drops ${lost.length} accepted states before the drawing`, examples: lost.slice(0, 4)});
  }
  const sheets = uniq(Object.values(cfg.files || {})).map(f => W.svg(f)).filter(Boolean), unpainted = [];
  for (const p of byVocab.values())
    for (const s of drawn[p]) {
      const rule = new RegExp(`\\.state-${s.replace(/[^\w-]/g, '\\$&')}(?![\\w-])`);
      if (!sheets.some(t => rule.test(t))) unpainted.push(`${p}:${s}`);
    }
  if (unpainted.length) found.push({code: 'S7', n: unpainted.length, text: `${unpainted.length} drawn states have no stylesheet rule that paints them`, examples: unpainted.slice(0, 4)});
  const msgs = drawnMessages(W, cfg);
  counts.messages = Object.keys(msgs).length;
  if (counts.messages) found.push({code: 'S8', n: counts.messages, level: 'gap',
    text: `${counts.messages} displays declare whole readings (data-messages) and no command sets one`, examples: Object.keys(msgs).slice(0, 3)});
  // fields: every field a drawn part declares is taken by `field`
  let nField = 0;
  const badField = [];
  const seen = new Set();
  for (const file of uniq(Object.values(cfg.files || {}))) for (const e of W.face(file)?.elements || []) {
    if (!e.ref || seen.has(e.path) || e.class === 'port') continue;
    const comp = W.compByRef(e.ref.split(':')[0]);
    const entries = Object.entries(comp?.fields || {}).filter(([k, f]) => f?.type === 'choice' && Array.isArray(f.options) && f.options.length > 1);
    if (!entries.length) continue;
    seen.add(e.path);
    const [k, f] = entries[0];
    nField++;
    if (nField > 25) break;
    const r = apply(rack, [{op: 'field', id, path: e.path, key: k, value: f.options.find(o => o !== f.default) ?? f.options[0]}], ctx);
    if (r.error) badField.push(`${e.path}.${k}: ${r.error}`);
  }
  counts.fields = nField;
  if (badField.length) found.push({code: 'S9', n: badField.length, text: `the agent's field refuses ${badField.length} of ${nField} fields the drawn parts declare`, examples: badField.slice(0, 2)});
  return {found, counts};
}

// ── CABLING ─────────────────────────────────────────────────────────────
// The tilted parts of a configuration's faces: {path: degrees}, from the drawing's text.
function tiltedPaths(W, cfg) {
  const out = {};
  for (const file of uniq(Object.values(cfg.files || {}))) {
    const text = W.svg(file);
    if (!text.includes('data-tilt=')) continue;
    for (const m of text.matchAll(/<g\s[^>]*data-tilt="([^"]*)"[^>]*>/g)) {
      const p = /data-path="([^"]*)"/.exec(m[0]);
      if (p) out[p[1]] = Number(m[1]);
    }
  }
  return out;
}
// the elements of one view a cable can land on: class port, outermost first, plus the slots the catalogue lists
function drawnEnds(W, cfg, view, slotPaths) {
  const doc = W.face(cfg.files?.[view]);
  if (!doc) return [];
  const out = [];
  for (const e of doc.elements) {
    if (!e.path || e.inner) continue;
    if (e.class === 'port' || (slotPaths.has(e.path) && e.class)) out.push({...e, view});
  }
  // an inner port is part of its outer one
  const outer = out.filter(e => !out.some(o => o !== e && e.path.startsWith(`${o.path}/`) && !o.path.includes('/module/')));
  return outer;
}

// The page's reader, as site/rack/route-context.js builds it: where each port stands in rack mm.
function readerFor(W, rack) {
  const ports = new Map();
  for (const it of rack.items) {
    const slots = W.slotsOf(it.ref);
    const cfg = slots?.configs.find(c => c.name === it.cfg) ?? slots?.configs.find(c => c.name === slots.default);
    const facing = {front: it.turned ? (it.face === 'front' ? 'rear' : 'front') : it.face};
    facing.rear = facing.front === 'front' ? 'rear' : 'front';
    for (const view of FACES) {
      const doc = W.face(cfg?.files?.[view]);
      if (!doc) continue;
      const w = doc.viewBox?.[2] ?? 483, h = doc.viewBox?.[3] ?? 44.45;
      const slotPaths = new Set(cableEndPaths(it, view, ctxOf(W)));
      for (const e of doc.elements) {
        if (!e.path || e.inner || !(e.class === 'port' || (e.class && slotPaths.has(e.path)))) continue;
        const cx = e.box.x + e.box.w / 2;
        ports.set(`${it.id}|${view}|${e.path}`, {x: facing[view] === 'rear' ? -(cx - w / 2) : cx - w / 2, y: e.box.y + e.box.h / 2, faceH: h});
      }
    }
  }
  const keyOf = e => `${e.item}|${e.view === 'rear' ? 'rear' : 'front'}|${portPathOf(e.path)}`;
  const base = ctxOf(W);
  const routeCtx = r => ({
    ...base,
    guidesOf: () => [],
    portX: e => ports.get(keyOf(e))?.x ?? null,
    portY: e => { const p = ports.get(keyOf(e)), it = r.items.find(i => i.id === e.item); if (!p || !it) return null;
      const b = itemBox(r, it, W.chassisOf); return (b.lo + b.hi) / 2 + p.faceH / 2 - p.y; },
  });
  const portsOf = async (it, view) => {
    const slotPaths = new Set(cableEndPaths(it, view, base));
    const out = [];
    for (const [k, p] of ports) {
      const [id, v, ...rest] = k.split('|');
      if (id !== it.id || v !== view) continue;
      const path = rest.join('|');
      const cfg = W.slotsOf(it.ref)?.configs.find(c => c.name === it.cfg);
      const el = (W.face(cfg?.files?.[view])?.elements || []).find(e => e.path === path);
      out.push({path, cls: el?.class, ref: el?.ref ? el.ref.split(':')[0] : null, media: el?.media ?? null, speed: el?.speed ?? null, end: el?.class !== 'port' && slotPaths.has(path)});
    }
    return out;
  };
  return {ports, routeCtx, portsOf};
}

const POWER_FAR = 'pdu12iec';             // a rack PDU: its outlets are the far end of an inlet
const INLET_DEV = 'n9k-c93180yc-ex';      // a switch with supplies: its inlets are the far end of an outlet
// the cable type a matching far end suggests, from what the end is
export function mediaOfEnd(end, optic) {
  if (end.kind === 'power') return 'power';
  if (end.kind === 'ground') return 'ground';
  // a stack, USB or console end offers what connectorOf reads it as (the port's `role` tells a console from a USB link)
  const read = connectorOf({portMedia: end.media || '', iface: end.iface || end.connector || '', role: end.role || ''});
  if (['stack', 'usb', 'console'].includes(read.family)) return proposeMedia(read, read);
  if (optic?.kind === 'dac') return 'dac';
  if (optic) return 'os2';
  if (/^rj45/.test(end.media || '')) return 'cat6';
  if (/^(lc|sc|mpo|fiber|fibre)/.test(end.media || '')) return 'os2';
  return '';
}

// the optic a cage is fitted with for the test: the first accepted part that is a transceiver, else the first
function opticFor(W, cage) {
  const parts = (cage?.accepts || []).map(r => [r, W.compByRef(r)]);
  const pick = parts.find(([, c]) => c?.class === 'transceiver') ?? parts.find(([, c]) => c?.class === 'port') ?? null;
  if (!pick) return null;
  return {ref: pick[0], kind: /cable|dac|aoc/.test(pick[0]) ? 'dac' : 'optic'};
}

// The cage at a path: the device's own, or one of the part seated in a bay (`bay/module/cage`).
function cageAt(W, slots, cfg, view, path) {
  const cut = path.indexOf('/module/');
  if (cut < 0) return (slots.cages[view] || []).find(c => c.id === path && c.kind === 'cage') ?? null;
  const ref = cfg.bays?.[path.slice(0, cut)];
  const leaf = path.slice(cut + '/module/'.length);
  return (W.compByRef(ref)?.cages || []).find(c => c.id === leaf && c.kind === 'cage') ?? null;
}

// A STRATIFIED SAMPLE of the ends: every distinct kind of end (view, kind, connector, group) first, twice,
// then spread evenly over the rest until `max`.
function sampleEnds(ends, max) {
  if (ends.length <= max) return ends;
  const sig = e => [e.view, e.kind, e.connector ?? e.media ?? '', e.group ?? ''].join('|');
  const by = new Map();
  for (const e of ends) { if (!by.has(sig(e))) by.set(sig(e), []); by.get(sig(e)).push(e); }
  const pick = new Set();
  for (const list of by.values()) { pick.add(list[0]); if (list.length > 1) pick.add(list.at(-1)); }
  const rest = ends.filter(e => !pick.has(e));
  const room = Math.max(0, max - pick.size);
  for (let i = 0; i < room && rest.length; i++) pick.add(rest[Math.floor(i * rest.length / room)]);
  return ends.filter(e => pick.has(e));
}

// The legs of a laid cable at one end, judged against that end's point and axis.
function landing(side, rack, cable, path, rc, W, out, solids) {
  const end = cable[side], pts = side === 'a' ? path.points : [...path.points].reverse();
  const pp = portPoint(rack, end, rc);
  if (!pp) { out.verdict.push({code: 'C4', text: `end ${side}: no point on any drawing (portX is null)`}); return; }
  const [first, second] = pts;
  const miss = Math.hypot(first.x - pp.x, first.y - pp.y, first.z - pp.z);
  if (miss > 1.5) out.verdict.push({code: 'C4', text: `end ${side}: the route starts ${miss.toFixed(1)} mm from the end's point`});
  const axis = endPane(rack, end) === 'rear' ? -1 : 1;
  const leg = {x: second.x - first.x, y: second.y - first.y, z: second.z - first.z}, len = Math.hypot(leg.x, leg.y, leg.z) || 1;
  const cos = (leg.z * axis) / len;
  out[`axis${side}`] = Math.round(cos * 1000) / 1000;
  if (cos < 0.97) out.verdict.push({code: 'C5', text: `end ${side}: the first leg leaves ${Math.round(Math.acos(Math.min(1, cos)) * 180 / Math.PI)} degrees off the end's axis`});
  const crosses = legCrossings(first, second, solids, {diameter: 0}).filter(c => c.t0 > 0.05 && c.solid.item === end.item);
  if (crosses.length) out.verdict.push({code: 'C13', text: `end ${side}: the plug's first leg runs inside the body of its own device (${crosses[0].solid.part})`});
  out[`reach${side}`] = Math.round(len * 10) / 10;
}

export async function checkCabling(W, ref, cfgName, opts = {}) {
  const maxEnds = opts.maxEnds ?? 12;
  const slots = W.slotsOf(ref), cfg = slots?.configs.find(c => c.name === cfgName);
  const chassis = W.chassisOf(ref) ?? {};
  const found = [], ends = [], counts = {drawn: 0, offered: 0, judged: 0, clean: 0, standins: 0};
  if (!cfg) return {found: [{code: 'C0', text: 'the configuration is not in configs.json'}], counts, ends};
  const zero = chassis.mount === 'rack-side';
  const base = ctxOf(W);
  const tilt = tiltedPaths(W, cfg);
  const variants = zero ? [{name: 'beside-rack'}] : opts.variants ?? [{name: 'front rail', face: 'front', setback: 0}, {name: 'rear rail, 30 mm setback', face: 'rear', setback: 30}];
  const flag = (code, text, n = 1, extra = {}) => { const f = found.find(x => x.code === code && x.text === text); if (f) f.n += n; else found.push({code, text, n, ...extra}); };
  for (const [vi, variant] of variants.entries()) {
    const at = placed(W, ref, cfgName, variant);
    if (at.error) { flag('C0', `could not place: ${at.error}`); continue; }
    let {rack, id} = at;
    const addFar = fr => { const r = M.withItem(rack, {ref: fr, cfg: fr === ref ? cfgName : W.slotsOf(fr)?.default ?? 'base', ru: fr === ref ? 9 + Math.ceil(chassis.ru || 1) : 14 + Math.ceil(chassis.ru || 1), face: 'front', label: 'far'}); rack = r.rack; return rack.items.at(-1).id; };
    const outletDev = ref === POWER_FAR ? 'pdumh20net' : POWER_FAR;
    const mirror = zero ? null : addFar(ref), pdu = zero || !W.slotsOf(outletDev) ? null : addFar(outletDev);
    const inletDev = zero && W.slotsOf(INLET_DEV) ? addFar(INLET_DEV) : null;
    const reader = readerFor(W, rack), pageCtx = {...base, portsOf: reader.portsOf};
    // the side panes' drawing of the device (the site's pure side-geometry, when a checkout of it is given): its faceplate where the kit puts the panel
    if (opts.side && !zero && (!chassis.mount || chassis.mount === 'rack')) {   // a part on the rack's face stands out from its rail by its depth
      const it = rack.items.find(i => i.id === id), set = setbackOf(rack, it, W.chassisOf);
      const want = it.face === 'front' ? -set : -RAIL_DEPTH + set;
      const d = opts.side.itemDepth(rack, it, chassis);
      counts.sidePanes = (counts.sidePanes ?? 0) + 1;
      if (!d || !near(d.zFront, want, 0.5)) flag('C7', `the side panes draw the faceplate at z ${d ? d.zFront.toFixed(1) : 'nowhere'} where the kit puts it at z ${want.toFixed(1)} (setback ${set} mm)`, 1, {examples: [variant.name]});
    }
    // what an agent is offered
    let offered;
    if (zero) offered = zeroUEnds(rack.zeroU[0], base).map(e => ({path: e.path, view: e.view, kind: e.kind, connector: e.connector, media: e.media, group: null}));
    else offered = (await freePorts(rack, id, pageCtx)).map(e => ({...e, group: null}));
    // what the drawing shows
    const drawn = [];
    if (!zero) {
      const it = rack.items.find(i => i.id === id);
      for (const view of FACES) drawn.push(...drawnEnds(W, cfg, view, new Set(cableEndPaths(it, view, base))));
    }
    // the back of a part seated in a bay: the catalogue has its ends whether or not the host draws them
    if (!zero) {
      const known = new Set(offered.map(e => `${e.view}|${e.path}`));
      const hidden = [];
      for (const [bayPath, r] of Object.entries(cfg.bays || {})) {
        // a nested bay is keyed `drawer/slot-1` in a configuration and addressed `drawer/module/slot-1`
        const view = Object.entries(slots.bays).find(([, list]) => list.some(b => b.id === bayPath.split('/')[0]))?.[0];
        const back = W.compByRef(faceRef(W.compByRef(r)?.faces?.rear));
        if (!OTHER[view] || !back) continue;
        for (const pid of endIdsOf(W, back)) {
          const e = {path: `${bayPath.split('/').join('/module/')}/module/${pid}`, view: OTHER[view], catalogue: true};
          if (!known.has(`${e.view}|${e.path}`)) { hidden.push(e); offered.push(e); }
        }
      }
      if (vi === 0 && hidden.length) flag('C18', `${hidden.length} ends on the back of seated parts are in the catalogue and not on the host's ${uniq(hidden.map(e => e.view)).join('/')} drawing: a cable is accepted there and has no point to be drawn to`, hidden.length, {examples: hidden.slice(0, 3).map(e => `${e.view}:${e.path}`)});
    }
    // a supply the drawing shows presents a way to power it (an inlet, a terminal, a lug), or says it is a fixed cord
    if (vi === 0 && !zero) {
      const supplies = [];
      for (const view of FACES) for (const e of W.face(cfg.files?.[view])?.elements || [])
        if (e.class === 'psu' && e.path && !e.inner && !supplies.some(s => s.path === e.path)) supplies.push({...e, view});
      const bare = supplies.filter(s => !offered.some(o => o.path === s.path || o.path.startsWith(`${s.path}/`)))
        .filter(s => !/fixed|cord/i.test(W.compByRef((s.ref || '').split(':')[0])?.attrs?.inlet ?? ''));
      counts.supplies = supplies.length;
      if (bare.length) flag('C19', `${bare.length} of ${supplies.length} supplies drawn present no cable end an agent is offered (no inlet, terminal or lug)`, bare.length,
        {examples: bare.slice(0, 3).map(s => `${s.view}:${s.path} ${modelOf(W.compByRef((s.ref || '').split(':')[0]), s.ref)}`)});
      if ((cfg.power || []).length && !offered.some(o => o.kind === 'power') && !bare.length && !supplies.length)
        flag('C19', `the configuration says it is powered (${cfg.power.join(', ')}) and no power end is offered`, 1);
    }
    // an inlet, terminal or stud the drawing shows (outside a supply, which is judged above) is a place to land a cord or a lug
    if (vi === 0) {
      const seen = new Set(), lone = [], landable = new Set(['inlet', 'terminal', 'ground', 'screw']);
      // a place a cord or lug lands is a part that is a registered connector (it presents a slot), outermost of its kind
      const isSlot = e => { const c = e.ref ? W.compByRef(e.ref.split(':')[0]) : null; return !c || c.interface || c.presents?.kind === 'connector' || (c.cages || []).length > 0 || (c.parts || []).length > 0; };
      for (const view of FACES) {
        const els = (W.face(cfg.files?.[view])?.elements || []).filter(e => e.path && landable.has(e.class) && !e.inner);
        for (const e of els) {
          if (seen.has(e.path) || e.path.includes('/module/')) continue;     // under a seated supply or card: judged with it
          if (els.some(o => o !== e && e.path.startsWith(`${o.path}/`))) continue;   // a part of a larger inlet
          seen.add(e.path);
          if (!isSlot(e)) continue;                                           // a marking, not a connector
          if (!offered.some(o => o.path === e.path || o.path.startsWith(`${e.path}/`))) lone.push({...e, view});
        }
      }
      if (lone.length) flag('C20', `${lone.length} drawn inlets, terminals or studs are not offered as a place to land a cord or lug`, lone.length,
        {examples: lone.slice(0, 4).map(e => `${e.view}:${e.path} (${e.class}${e.ref ? ` ${e.ref.split(':')[0]}` : ''})`)});
    }
    if (vi === 0) {
      counts.drawn = drawn.length; counts.offered = offered.length;
      const key = e => `${e.view}|${e.path}`;
      const have = new Set(offered.map(key));
      const missing = drawn.filter(e => !have.has(key(e)) && !have.has(`${e.view === 'front' ? 'rear' : 'front'}|${e.path}`));
      if (missing.length) flag('C8', `${missing.length} drawn ports are not offered to an agent (list_free_ports)`, missing.length, {examples: missing.slice(0, 4).map(e => `${e.view}:${e.path}`)});
      const dkeys = new Set(drawn.map(key));
      const phantoms = offered.filter(e => !e.catalogue && !dkeys.has(key(e)) && !e.kind);
      if (phantoms.length) flag('C9', `${phantoms.length} ports the agent is offered have no drawing on that panel`, phantoms.length, {examples: phantoms.slice(0, 4).map(e => `${e.view}:${e.path}`)});
      // an angled cage with no declared axis
      const tilted = drawn.filter(e => Object.entries(tilt).some(([p, d]) => d && (e.path === p || e.path.startsWith(`${p}/`))));
      if (tilted.length) flag('C10', `${tilted.length} ports sit on an angled facet (${uniq(Object.values(tilt)).join(', ')} degrees) and declare no axis: connection-points say only "${uniq(tilted.map(e => e['connection-points']?.mate?.dir)).join('/') || 'nothing'}"`, tilted.length, {examples: tilted.slice(0, 3).map(e => e.path)});
      // a coupler with one side
      for (const [bay, r] of Object.entries(cfg.bays || {})) {
        const comp = W.compByRef(r);
        if (!comp || !['adapter-panel', 'cassette', 'coupler'].includes(comp.class)) continue;
        const count = view => (W.face(cfg.files?.[view])?.elements || []).filter(e => e.path && e.class === 'port' && !e.inner && e.path.startsWith(`${bay}/module/`)).length;
        const f = count('front'), b = count('rear');
        if (f && !b && !/blank/.test(r)) flag('C11', `${modelOf(comp, r)} (a coupler) has cable ends on its front and none on its rear: two sides of one path need both`, 1, {examples: [`${bay}: ${r}`]});
        if (!f && b) flag('C11', `${modelOf(comp, r)} (a coupler) has cable ends on its rear and none on its front: two sides of one path need both`, 1, {examples: [`${bay}: ${r}`]});
      }
    }
    // judge a stratified sample of the offered ends
    // (a bay offered as a place a cable may be drawn to is the page's own design, not a cable end)
    const bayAt = new Set((W.face(cfg.files?.front)?.elements || []).concat(W.face(cfg.files?.rear)?.elements || []).filter(x => x.class === 'bay').map(x => x.path));
    for (const e of sampleEnds(offered.filter(x => !bayAt.has(x.path)), maxEnds)) {
      counts.judged++;
      const cage = cageAt(W, slots, cfg, e.view, e.path);
      const optic = cage ? opticFor(W, cage) : null;
      let r0 = rack;
      const fits = [];
      if (cage && !optic) { flag('C12', `the cage ${e.path} takes no part in the library: nothing can be fitted to cable it`); continue; }
      if (optic) {
        const a = apply(r0, [{op: 'fit', id, path: e.path, ref: optic.ref}, ...(mirror ? [{op: 'fit', id: mirror, path: e.path, ref: optic.ref}] : [])], base);
        if (a.error) { flag('C12', `an optic cannot be fitted in a cage to cable it: ${a.error}`); continue; }
        r0 = a.rack;
      }
      // the far end: the same end on a second copy (the same connector by construction), or an outlet for an inlet
      let far;
      if (e.kind === 'power' || zero) {
        const pid = zero ? inletDev : pdu;
        if (!pid) { flag('C12', 'no far end of a matching type to cable it to (power)'); continue; }
        const offeredFar = await freePorts(r0, pid, {...base, portsOf: readerFor(W, r0).portsOf}, {kinds: ['power']});
        if (!offeredFar.length) { flag('C12', 'no far power end'); continue; }
        far = {item: pid, path: offeredFar[0].path, view: offeredFar[0].view};
      } else far = {item: mirror, path: e.path, view: e.view};
      const media = mediaOfEnd(e, optic);
      const rec = {path: e.path, view: e.view, kind: e.kind ?? 'data', media, variant: variant.name, verdict: [], notes: []};
      const add = apply(r0, [{op: 'cable.add', a: {item: id, path: e.path, view: e.view}, b: far, media, purpose: 'conformance'}], base);
      if (add.error) { rec.verdict.push({code: 'C1', text: `the cable is refused at add time: ${add.error}`}); ends.push(rec); flag('C1', `a cable to an offered end is refused at add time: ${add.error}`, 1, {examples: [`${e.view}:${e.path}`]}); continue; }
      const r1 = add.rack, cable = r1.cables[0], rd = readerFor(W, r1), rc = rd.routeCtx(r1);
      // loose? the page's facts for the end (this drawing), settled with the catalogue as the page settles them
      const itm = r1.items.find(i => i.id === id);
      const settled = settleEnd(r1, cable.a, itm ? factsFor(W, r1, itm, cfg, cable.a, slots) : null, base);
      if (settled?.reason) rec.verdict.push({code: 'C2', text: `a loose end: ${settled.reason}`});
      else if (!settled) rec.notes.push('unchecked');
      let path;
      try { path = routePath(r1, cable, rc); } catch (err) { rec.verdict.push({code: 'C3', text: `the route throws: ${err.message}`}); }
      if (path && (!Array.isArray(path.points) || path.points.length < 2)) { rec.verdict.push({code: 'C3', text: 'the cable does not route (no path)'}); path = null; }
      if (path && !path.points.every(finite)) { rec.verdict.push({code: 'C3', text: 'the route has a point that is not a number'}); path = null; }
      if (path) {
        const solids = solidsOf(r1, rc);
        landing('a', r1, cable, path, rc, W, rec, solids);
        if (!zero && !(e.kind === 'power')) landing('b', r1, cable, path, rc, W, rec, solids);
        // the 2-D panes' view of the same end: inside the device in a face pane, on the panel's plane in a side pane
        const pp = portPoint(r1, cable.a, rc);
        if (pp && itm) {
          const c = W.chassisOf(itm.ref) ?? {}, b = itemBox(r1, itm, W.chassisOf), pane = endPane(r1, cable.a), set = setbackOf(r1, itm, W.chassisOf);
          if (Math.abs(pp.x) > (c.w ?? 483) / 2 + 40 || pp.y < b.lo - 40 || pp.y > b.hi + 40)
            rec.verdict.push({code: 'C6', text: `the end falls outside the device in the ${pane} pane (x ${pp.x.toFixed(0)}, y ${pp.y.toFixed(0)})`});
          const wantZ = pane === itm.face ? (itm.face === 'front' ? -set : -RAIL_DEPTH + set) : (itm.face === 'front' ? -set - (c.d ?? 0) : -RAIL_DEPTH + set + (c.d ?? 0));
          if (!near(pp.z, wantZ, 0.5)) rec.verdict.push({code: 'C7', text: `a side pane would draw the end at z ${pp.z.toFixed(1)}; its panel is at ${wantZ.toFixed(1)} (setback ${set})`});
          // both side panes, by the site's own projection: the end is on the device's outline there
          if (opts.side) {
            const d = opts.side.itemDepth(r1, itm, c);
            for (const sp of ['left', 'right']) {
              const [X, Y] = opts.side.project(sp, r1.frame, pp);
              const xa = opts.side.sideX(sp, d.z0), xb = opts.side.sideX(sp, d.z1);
              if (X < Math.min(xa, xb) - 1 || X > Math.max(xa, xb) + 1) rec.verdict.push({code: 'C7', text: `the ${sp} pane draws the end outside the device's depth (X ${X.toFixed(0)}, device ${Math.min(xa, xb).toFixed(0)} to ${Math.max(xa, xb).toFixed(0)})`});
            }
          }
        }
      }
      // a mating point declared, or a stand-in
      const el = drawn.find(d => d.view === e.view && d.path === e.path);
      if (el && !el['connection-points']) { rec.verdict.push({code: 'C14', level: 'standin', text: 'the drawing declares no mating point for this end (a stand-in)'}); counts.standins++; }
      if (!el && !zero) rec.notes.push('no drawn element at this path');
      if (!rec.verdict.length) counts.clean++;
      for (const v of rec.verdict) flag(v.code, v.text.replace(/\d+(\.\d+)? mm/g, 'N mm').replace(/\d+ degrees/, 'N degrees'), 1, {level: v.level, examples: [`${variant.name}: ${e.view}:${e.path}`]});
      ends.push(rec);
    }
    // a made-up end: refused at add time, or at least a loose end at once
    if (!zero && mirror) {
      const bogus = {item: id, path: 'no-such-port-9', view: 'front'};
      const add = apply(rack, [{op: 'cable.add', a: bogus, b: {item: mirror, path: offered[0]?.path ?? 'x', view: offered[0]?.view ?? 'front'}, media: '', purpose: 'conformance'}], base);
      if (!add.error) {
        const itm = add.rack.items.find(i => i.id === id);
        const settled = settleEnd(add.rack, add.rack.cables[0].a, factsFor(W, add.rack, itm, cfg, add.rack.cables[0].a, slots), base);
        flag('C15', settled?.reason ? 'a made-up end is accepted at add time and only flagged loose afterwards' : 'a made-up end is accepted at add time and is not flagged as loose',
          1);
      }
    }
  }
  return {found, counts, ends};
}

// ── OCCUPANTS: every module a bay lists and every optic a cage lists ─────
// There is no drawing of a part in a bay it was never built into: the page composes it when it is
// fitted. So what is judged here is what the catalogue alone answers (the kit's seatedPort): the
// part's two sides, each end it presents, and whether a cable to it is accepted and lands.
const COUPLERS = new Set(['adapter-panel', 'cassette', 'coupler']);
const OTHER = {front: 'rear', rear: 'front'};
const faceRef = f => (typeof f === 'string' ? f : f?.ref) || null;
const endIdsOf = (W, comp) => (comp ? [...(comp.parts || []).filter(p => W.compByRef(p.ref)?.class === 'port').map(p => p.id),
  ...(comp.cages || []).filter(c => c.kind === 'cage').map(c => c.id)] : []);
function spread(list, n) { return list.length <= n ? list : Array.from({length: n}, (_, i) => list[Math.floor(i * (list.length - 1) / Math.max(1, n - 1))]); }
// accepted parts, spread over the classes they are (a sample of `n`)
function sampleAccepts(W, refs, n) {
  if (refs.length <= n) return refs;
  const by = new Map();
  for (const r of refs) { const k = W.compByRef(r)?.class ?? '?'; if (!by.has(k)) by.set(k, []); by.get(k).push(r); }
  const pick = [...by.values()].flatMap(l => spread(l, 2));
  return spread(pick, n);
}

export function checkOccupants(W, ref, {perBay = 60, perCage = 8} = {}) {
  const slots = W.slotsOf(ref), found = [], counts = {bays: 0, occupants: 0, ends: 0, cages: 0, optics: 0};
  if (!slots) return {found, counts};
  const chassis = W.chassisOf(ref) ?? {};
  if (chassis.mount === 'rack-side') return {found, counts};
  const cfgName = slots.default, cfg = slots.configs.find(c => c.name === cfgName) ?? slots.configs[0];
  const base = ctxOf(W);
  const flag = (code, text, example) => { const f = found.find(x => x.code === code && x.text === text); if (f) { f.n++; if (f.examples.length < 3) f.examples.push(example); } else found.push({code, text, n: 1, examples: [example]}); };
  const place = swaps => {
    const r = M.withItem(newFrame(), {ref, cfg: cfgName, ru: 8, face: 'front', label: ref});
    return {...r.rack, items: r.rack.items.map(i => ({...i, swaps}))};
  };
  const done = new Set();
  for (const [view, bays] of Object.entries(slots.bays)) for (const bay of bays) {
    if (!OTHER[view] || !(bay.accepts || []).length) continue;
    counts.bays++;
    for (const r of sampleAccepts(W, bay.accepts, perBay)) {
      const comp = W.compByRef(r), tag = `${bay.id}: ${r}`;
      if (!comp) { flag('O1', 'a bay lists a part the library does not hold', tag); continue; }
      if (done.has(`${view}|${r}`)) continue; done.add(`${view}|${r}`);
      counts.occupants++;
      const faces = endIdsOf(W, comp), rearComp = W.compByRef(faceRef(comp.faces?.rear)), backs = endIdsOf(W, rearComp);
      if (COUPLERS.has(comp.class) && !/blank/.test(r) && faces.length && !backs.length)
        flag('C11', `${modelOf(comp, r)} (a coupler) has cable ends on its front and none on its rear: two sides of one path need both`, tag);
      if (COUPLERS.has(comp.class) && !faces.length && backs.length) flag('C11', `${modelOf(comp, r)} (a coupler) has cable ends on its rear and none on its front: two sides of one path need both`, tag);
      let rack = place({[bay.id]: r});
      const mirror = M.withItem(rack, {ref, cfg: cfgName, ru: 24, face: 'front', label: 'far'});
      rack = {...mirror.rack, items: mirror.rack.items.map(i => ({...i, swaps: {[bay.id]: r}}))};
      const id = rack.items[0].id, far = rack.items.at(-1).id;
      const want = [...spread(faces, 2).map(p => [p, view]), ...spread(backs, 2).map(p => [p, OTHER[view]])];
      for (const [p, v] of want) {
        const path = `${bay.id}/module/${p}`;
        counts.ends++;
        let r1 = rack;
        // a cage of the part takes an optic before it takes a cable
        const cageOf = [...(comp.cages || []), ...(rearComp?.cages || [])].find(c => c.id === p && c.kind === 'cage');
        if (cageOf) {
          const o = opticFor(W, cageOf);
          if (!o) { flag('C12', 'a cage of a listed part takes no part in the library', `${tag} ${path}`); continue; }
          const fit = apply(rack, [{op: 'fit', id, path, ref: o.ref}, {op: 'fit', id: far, path, ref: o.ref}], base);
          if (fit.error) { flag('C17', `a part a cage lists cannot be fitted to it: ${fit.error.slice(0, 120)}`, `${tag} ${path}: ${o.ref}`); continue; }
          r1 = fit.rack;
        }
        const add = apply(r1, [{op: 'cable.add', a: {item: id, path, view: v}, b: {item: far, path, view: v}, media: '', purpose: 'conformance'}], base);
        if (add.error) { flag('C1', `a cable to an end of a listed part is refused at add time: ${add.error}`, `${tag} ${v}:${path}`); continue; }
        const got = settleEnd(add.rack, add.rack.cables[0].a, null, base);
        if (got?.reason) flag('C2', `a loose end: ${got.reason.replace(/^\S+\/module\/\S+ /, '').replace(/ ?\S+\/module\/\S+/g, ' <port>')}`.slice(0, 160), `${tag} ${v}:${path}`);
        else if (!got) flag('C16', 'the catalogue does not answer for an end of a listed part (only a drawing would)', `${tag} ${v}:${path}`);
      }
    }
  }
  // cages: each optic or cable a cage lists
  for (const view of FACES) {
    const cages = (slots.cages[view] || []).filter(c => c.kind === 'cage' && (c.accepts || []).length);
    for (const cage of spread(cages, 3)) {
      counts.cages++;
      for (const r of sampleAccepts(W, cage.accepts, perCage)) {
        counts.optics++;
        let rack = place({});
        const m = M.withItem(rack, {ref, cfg: cfgName, ru: 24, face: 'front', label: 'far'});
        rack = m.rack;
        const id = rack.items[0].id, far = rack.items.at(-1).id;
        const fit = apply(rack, [{op: 'fit', id, path: cage.id, ref: r}, {op: 'fit', id: far, path: cage.id, ref: r}], base);
        if (fit.error) { flag('C17', `a part a cage lists cannot be fitted to it: ${fit.error.slice(0, 120)}`, `${cage.id}: ${r}`); continue; }
        const add = apply(fit.rack, [{op: 'cable.add', a: {item: id, path: cage.id, view}, b: {item: far, path: cage.id, view}, media: '', purpose: 'conformance'}], base);
        if (add.error) { flag('C1', `a cable to a cage with a listed part is refused at add time: ${add.error}`, `${cage.id}: ${r}`); continue; }
        const cageHere = W.slotsOf(ref).cages[view].find(c => c.id === cage.id);
        const settled = settleEnd(add.rack, add.rack.cables[0].a, factsFor(W, add.rack, add.rack.items[0], cfg, add.rack.cables[0].a, slots), base);
        if (settled?.reason) flag('C2', `a loose end: ${settled.reason.replace(/\S+ holds no optic/, '<cage> holds no optic')}`, `${cage.id}: ${r}${cageHere ? '' : ' (?)'}`);
      }
    }
  }
  return {found, counts};
}

// What the page reads of an end on this drawing, as cable-plugs.js hands it to looseReason.
function factsFor(W, rack, item, cfg, end, slots) {
  const doc = W.face(cfg.files?.[end.view]);
  const path = portPathOf(end.path);
  const slotPaths = new Set(cableEndPaths(item, end.view, ctxOf(W)));
  const el = (doc?.elements || []).find(e => e.path === path && !e.inner && (e.class === 'port' || (e.class && slotPaths.has(path))));
  const cage = !!cageAt(W, slots, cfg, end.view, path);
  const cut = path.indexOf('/module/'), bay = cut > 0 ? path.slice(0, cut) : null;
  const ref = bay ? (item.swaps?.[bay] ?? cfg.bays?.[bay] ?? null) : null;
  const facts = {item: true, drawing: !!doc, port: !!el, cage, occupied: cage && !!item.swaps?.[path],
    holder: bay ? {path: bay, part: ref ? modelOf(W.compByRef(ref), ref) : null} : null};
  return {facts, reason: looseReason(end, facts)};
}

export const _internal = {sampleEnds, drawnEnds, tiltedPaths};
