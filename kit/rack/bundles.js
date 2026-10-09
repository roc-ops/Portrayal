// kit/rack/bundles.js
// CABLE BUNDLES (#921, docs/cable-bundles-design.md). Cables that share part
// of their route, combed into one dressed run and held with hook-and-loop
// straps. The record and its repairs are model.js's (`bundles` on a rack,
// settleBundles); the trunk and a member's route along it are
// bundle-route.js's, and route.js resolveRoute follows them. This file holds
// the rest: what a bundle is called, which pathways its trunk passes, the size
// check, where its straps go, and the sentences the commands and queries use.
// Pure: what reads a drawing comes in on `ctx.route`, the routing context
// route.js takes (`{chassisOf, guidesOf, portX, portY?, zeroUAperture?}`).

import {bundlesOf, bundleName, isWaypoint, uLabel} from './model.js';
import {ownRoute, trunkRoute, pointOf, portPoint, routeText, DIAMETERS} from './route.js';
import {elementsOf, elementText, waypointKey, followTrunk, andList} from './bundle-route.js';
import {zeroUOnLane, carriesLane} from './zero-u.js';

export {bundlesOf, bundleName, settleBundles} from './model.js';
export {deriveTrunk, followTrunk, elementsOf} from './bundle-route.js';

// The share of a bundle's circle its cables fill: tightly combed, a little
// tighter than a perfect hexagonal pack of equal round cables (7/9 to 37/49).
export const BUNDLE_PACK = 0.8;
// The largest a bundle may be across anywhere: 2.5 in.
export const MAX_BUNDLE_MM = 63.5;
// A strap's width along the run, for keeping straps off rings: a drawing figure.
export const STRAP_W = 20;
export const DEFAULT_STRAPS = Object.freeze({value: 12, unit: 'in'});
// A member of no known type counts as fill's figure, and the result says so.
const UNSET_D = 6.0;
const MM = {in: 25.4, mm: 1};

const round1 = v => Math.round(v * 10) / 10;
const dist = (p, q) => Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);

export const bundleById = (rack, id) => bundlesOf(rack).find(b => b.id === id) ?? null;
// The bundle a cable is in, drawn or not.
export const bundleOfCable = (rack, cableId) => bundlesOf(rack).find(b => b.members.some(m => m.cable === cableId)) ?? null;
// The spacing of a bundle's straps: {value, unit}, or null for none.
export const strapSpacing = b => (b.straps && 'every' in b.straps ? b.straps.every : DEFAULT_STRAPS);
export const strapEveryMm = b => { const e = strapSpacing(b); return e ? e.value * MM[e.unit] : null; };
export const spacingText = e => (e ? `straps every ${e.value} ${e.unit}` : 'no straps');

// "c1-c12", "c1, c3 and c7-c9": the members' ids, runs of numbers joined.
export function membersText(ids) {
  const out = [];
  for (const id of ids) {
    const m = /^([a-z]+)(\d+)$/i.exec(id), last = out.at(-1);
    if (m && last?.p === m[1] && last.to + 1 === Number(m[2])) { last.to++; continue; }
    out.push(m ? {p: m[1], from: Number(m[2]), to: Number(m[2])} : {text: id});
  }
  return andList(out.map(r => (r.text ?? (r.from === r.to ? `${r.p}${r.from}` : `${r.p}${r.from}-${r.p}${r.to}`))));
}

const labelOf = rack => id => rack.items.find(i => i.id === id)?.label ?? id;
// The trunk in words, as stored: "mgr-1 ring 5 > left-front U20-U30 > pp-1 ring 1".
export const trunkText = (rack, b) => routeText(b.route || [], labelOf(rack), rack.frame) || 'nowhere yet';
export const waypointText = (rack, w) => (w.lane ? `${w.lane} U${uLabel(rack.frame, w.ru)}`
  : routeText([w], labelOf(rack), rack.frame));

// IS A WAYPOINT ON THE TRUNK, as stored (no drawing needed): a pathway the
// trunk names, or a lane U within one of its lane runs.
export function onTrunk(b, w) {
  const k = waypointKey(w);
  return k != null && elementsOf(b.route || []).some(e => e.key === k);
}

// ── removing cables (section 2.2) ────────────────────────────────────────
// Every way a cable leaves the rack goes through here, so a bundle never names
// a cable that is gone: a later cable could be handed its id. Returns the rack
// and the sentence to add to the summary ('' when no bundle held them).
export function withoutCables(rack, ids) {
  const gone = new Set(ids);
  const next = {...rack, cables: (rack.cables || []).filter(c => !gone.has(c.id))};
  if (!Array.isArray(rack.bundles)) return {rack: next, said: ''};
  const left = [];
  next.bundles = rack.bundles.map(b => {
    const out = b.members.filter(m => !gone.has(m.cable));
    if (out.length === b.members.length) return b;
    left.push({b, ids: b.members.filter(m => gone.has(m.cable)).map(m => m.cable), n: out.length});
    return {...b, members: out};
  });
  const said = left.map(({b, ids, n}) => `${andList(ids)} ${ids.length === 1 ? 'is' : 'are'} out of ${bundleName(b)}${n < 2 ? `, which now holds ${n === 1 ? 'one cable' : 'no cables'}` : ''}.`);
  return {rack: next, said: said.join(' ')};
}

// ── the trunk as laid out today (needs ctx.route) ────────────────────────
// The trunk resolved, its elements, and each member's join and leave along
// it: `ji` and `li`, element indices into `T`, and `stale`, the peel ends it
// ignores. A reader that throws gives null: not measured, never an error.
export function layoutOf(rack, b, ctx) {
  const rc = ctx?.route;
  if (!rc) return null;
  try {
    const {waypoints: trunk, gone} = trunkRoute(rack, b, rc);
    const T = elementsOf(trunk);
    const at = new Map();
    T.forEach((e, i) => { if (!at.has(e.key)) at.set(e.key, i); });
    const members = b.members.map(m => {
      const cable = (rack.cables || []).find(c => c.id === m.cable);
      if (!cable) return null;
      const own = ownRoute(rack, cable, rc).waypoints;
      const aNearStart = () => {
        const p = portPoint(rack, cable.a, rc), s = trunk.length && pointOf(rack, trunk[0], rc), e = trunk.length && pointOf(rack, trunk.at(-1), rc);
        return !(p && s && e) || dist(p, s) <= dist(p, e);
      };
      const f = followTrunk(own, trunk, m, {aNearStart});
      const idx = w => (w ? at.get(waypointKey(w)) : undefined);
      return {cable: m.cable, member: m, join: f.join, leave: f.leave, ji: idx(f.join), li: idx(f.leave), met: f.met, stale: f.stale, own};
    }).filter(Boolean);
    return {trunk, gone, T, members};
  } catch { return null; }
}
const present = (L, i, {bend = false} = {}) => L.members.filter(m => m.ji != null && m.li != null
  && i >= Math.min(m.ji, m.li) && i <= Math.max(m.ji, m.li) && !(bend && (i === m.ji || i === m.li)));

// ── the pathways a trunk passes (section 4.4) ────────────────────────────
// Each ring, duct and pass-through on the trunk, and each zero-U duct a lane
// of the trunk runs through, as {item, via, kind, aperture: {w, h, estimated}
// | null, radius?, at: [element indices], zeroU?}. A stated aperture (one
// without `estimated`) wins over an estimate. A duct that runs along y, and a
// duct beside the rack, are estimated here: as wide as its channel across the
// run and as deep as the part's catalogue depth, fingers and cover included,
// so an upper bound.
const goodAp = a => a && a.w > 0 && a.h > 0;
export function pathwaysOn(rack, trunk, ctx) {
  const rc = ctx.route, out = [], T = elementsOf(trunk);
  const depthOf = ref => Number(rc.chassisOf(ref)?.d) || 0;
  T.forEach((e, i) => {
    if (e.kind !== 'p') return;
    const it = rack.items.find(x => x.id === e.item);
    const g = it && (rc.guidesOf(it.id) || []).find(x => x.via === e.via);
    if (!g) return;
    let aperture = null;
    if (goodAp(g.aperture) && !g.aperture.estimated) aperture = {w: g.aperture.w, h: g.aperture.h, estimated: false};
    else if (g.kind === 'duct' && g.run === 'y' && g.box?.w > 0 && depthOf(it.ref) > 0)
      aperture = {w: g.box.w, h: depthOf(it.ref), estimated: true};
    else if (goodAp(g.aperture)) aperture = {w: g.aperture.w, h: g.aperture.h, estimated: true};
    out.push({item: e.item, via: e.via, kind: g.kind ?? null, aperture,
              ...(typeof g.radius === 'number' && g.radius > 0 ? {radius: g.radius} : {}), at: [i]});
  });
  const beside = new Map();
  T.forEach((e, i) => {
    if (e.kind !== 'n') return;
    const z = zeroUOnLane(rack, e.lane, e.u, rc.chassisOf);
    if (!z || !carriesLane(rc.chassisOf(z.ref))) return;
    if (beside.has(z.id)) { beside.get(z.id).at.push(i); return; }
    const c = rc.chassisOf(z.ref);
    let channel = null;
    try { channel = typeof rc.zeroUAperture === 'function' ? rc.zeroUAperture(z) : null; } catch { channel = null; }
    const d = Number(c?.d) || 0;
    const via = Object.values(c?.guides || {}).flat()[0] ?? 'duct';
    beside.set(z.id, {item: z.id, via, kind: 'duct', aperture: channel?.w > 0 && d > 0 ? {w: channel.w, h: d, estimated: true} : null,
                      at: [i], zeroU: true, label: z.label || c?.model || z.ref});
  });
  return [...out, ...beside.values()];
}

// ── size (section 5.1) ───────────────────────────────────────────────────
// A member's outside diameter: its type's (`ctx.diameterOf`, cable-types.js
// over cable-types.json), else fill's figure for its media, else 6 mm and an
// estimate. Returns [mm, known].
function diameter(cable, ctx) {
  let d = null;
  try { d = typeof ctx.diameterOf === 'function' ? ctx.diameterOf(cable) : null; } catch { d = null; }
  if (typeof d === 'number' && d > 0) return [d, true];
  const m = DIAMETERS[cable?.media];
  return m ? [m, true] : [UNSET_D, false];
}
export const bundleDiameter = ds => Math.sqrt(ds.reduce((a, d) => a + d * d, 0) / BUNDLE_PACK);

// THE CHECKS FOR ONE BUNDLE. Warn, never refuse (decision 2). Returns
//   {checked, size: {max_mm, at, limit_mm, limitBy, estimated} | null,
//    bend: null, warnings: [text], notes: [text], gone: [waypoint], layout}
// `checked` is false without `ctx.route` (or when a reader throws): then
// nothing is measured and nothing is said to pass. The bend check is #922's;
// until it lands `bend` is null.
export function bundleCheck(rack, b, ctx = {}) {
  const name = bundleName(b);
  const notes = [], warnings = [];
  if (b.members.length < 2) notes.push(`${name} holds ${b.members.length === 1 ? 'one cable' : 'no cables'}, so it is not drawn.`);
  const L = layoutOf(rack, b, ctx);
  if (!L) return {checked: false, size: null, bend: null, warnings, notes, gone: [], layout: null};
  const nameOf = labelOf(rack), txt = e => elementText(e, nameOf, rack.frame);
  for (const m of L.members) for (const end of m.stale) {
    const w = m.member[end];
    notes.push(`${m.cable}'s peel point ${isWaypoint(w) ? waypointText(rack, w) : JSON.stringify(w)} ${isWaypoint(w) && onTrunk(b, w) ? `is out of order with its other end on ${name}` : `is not on ${name}'s route`}, so it rides to the end.`);
  }
  for (const m of L.members) if (!m.met && L.T.length && b.members.length >= 2)
    notes.push(`${m.cable} does not meet ${name}'s route, so it runs straight to it and rides all of it.`);
  if (b.members.length < 2 || !L.T.length) return {checked: true, size: null, bend: null, warnings, notes, gone: L.gone, layout: L};
  const byId = new Map((rack.cables || []).map(c => [c.id, c]));
  const unknown = new Set();
  const sizeAt = i => {
    const ds = present(L, i).map(m => { const [d, known] = diameter(byId.get(m.cable), ctx); if (!known) unknown.add(m.cable); return d; });
    return ds.length >= 2 ? bundleDiameter(ds) : 0;
  };
  let max = 0, maxAt = 0;
  L.T.forEach((e, i) => { if (e.kind === 's') return; const D = sizeAt(i); if (D > max) { max = D; maxAt = i; } });
  let limit = MAX_BUNDLE_MM, limitBy = null;
  for (const p of pathwaysOn(rack, L.trunk, ctx)) {
    const where = p.zeroU ? `${p.label} beside the rack` : `${nameOf(p.item)} ${/^guide-(\d+)$/.test(p.via) ? `ring ${p.via.slice(6)}` : p.via}`;
    const cap = p.aperture ? Math.min(MAX_BUNDLE_MM, p.aperture.w, p.aperture.h) : MAX_BUNDLE_MM;
    if (cap < limit) { limit = cap; limitBy = {item: p.item, via: p.via, text: where, estimated: !!p.aperture?.estimated}; }
    const D = Math.max(...p.at.map(sizeAt));
    if (p.aperture && D > cap && cap < MAX_BUNDLE_MM) {
      const open = round1(Math.min(p.aperture.w, p.aperture.h));
      warnings.push(`${name} is about ${Math.round(D)} mm across at ${where}, whose opening is ${p.aperture.estimated ? 'estimated at ' : ''}${open} mm across.`);
    }
  }
  if (max > MAX_BUNDLE_MM)
    warnings.push(`${name} is about ${Math.round(max)} mm across at ${txt(L.T[maxAt])}, more than the 63.5 mm (2.5 in) a bundle may be.`);
  const estimated = b.members.map(m => m.cable).filter(id => unknown.has(id));
  if (estimated.length)
    notes.push(`${name}'s size is an estimate: ${andList(estimated)} ${estimated.length === 1 ? 'has' : 'have'} no cable type, so ${estimated.length === 1 ? 'it counts' : 'each counts'} as 6 mm.`);
  return {checked: true, bend: null, warnings, notes, gone: L.gone, layout: L,
          size: {max_mm: round1(max), at: txt(L.T[maxAt]), limit_mm: round1(limit), limitBy, estimated}};
}

// EVERY BUNDLE'S CHECKS, as findings {kind: 'warning' | 'note', bundle, text}.
export function bundleChecks(rack, ctx = {}) {
  return bundlesOf(rack).flatMap(b => {
    const r = bundleCheck(rack, b, ctx);
    return [...r.warnings.map(text => ({kind: 'warning', bundle: b.id, text})),
            ...r.notes.map(text => ({kind: 'note', bundle: b.id, text}))];
  });
}

// ── straps (section 6) ───────────────────────────────────────────────────
// Along each RUN of the trunk (a longest stretch with two or more members
// riding together), n = ceil(L / every) straps, evenly at (k + 0.5) L / n, so
// none is more than the spacing apart and none sits on a run's end. A strap
// that falls on a ring or a pass-through (its extent along the run, widened by
// half a strap each side) moves to the stretch's nearer edge; one in a duct
// stays. The count is what the BOM buys and is never raised for a move.
// Returns {every, count, straps: [{segment, t, along_mm}], runs: [[from, to]]}
// (mm from the trunk's start), or null without `ctx.route`. A straps entry
// names its trunk segment (between resolved waypoints `segment` and
// `segment + 1`) and how far along it, since each view draws the waypoints at
// its own positions.
export function straps(rack, b, ctx = {}) {
  const every = strapSpacing(b), mm = strapEveryMm(b);
  const L = layoutOf(rack, b, ctx);
  if (!L) return null;
  const empty = {every, count: 0, straps: [], runs: []};
  if (b.members.length < 2 || L.trunk.length < 2) return empty;
  const pts = L.trunk.map(w => pointOf(rack, w, ctx.route));
  if (pts.some(p => !p)) return empty;
  const cum = [0];
  for (let k = 1; k < pts.length; k++) cum.push(cum[k - 1] + dist(pts[k - 1], pts[k]));
  const along = e => cum[e.seg] + (e.seg + 1 < cum.length ? e.t * (cum[e.seg + 1] - cum[e.seg]) : 0);
  // runs: where two or more members ride together
  const spans = L.members.filter(m => m.ji != null && m.li != null)
    .map(m => [along(L.T[Math.min(m.ji, m.li)]), along(L.T[Math.max(m.ji, m.li)])]);
  const cuts = [...new Set(spans.flat())].sort((x, y) => x - y);
  const runs = [];
  for (let k = 1; k < cuts.length; k++) {
    const [s, e] = [cuts[k - 1], cuts[k]];
    const n = spans.filter(([x, y]) => x <= s + 1e-9 && y >= e - 1e-9).length;
    if (n < 2 || e - s < 1e-9) continue;
    if (runs.length && Math.abs(runs.at(-1)[1] - s) < 1e-9) runs.at(-1)[1] = e; else runs.push([s, e]);
  }
  if (!mm) return {every, count: 0, straps: [], runs};
  // the stretches a ring or a pass-through takes
  const axis = (p, q) => { const d = [Math.abs(q.x - p.x), Math.abs(q.y - p.y), Math.abs(q.z - p.z)];
    const m = Math.max(...d); return m === 0 ? null : ['x', 'y', 'z'][d.indexOf(m)]; };
  const extent = (g, ax) => (ax === 'x' ? Number(g.box?.w) || 0 : ax === 'y' ? Number(g.box?.h) || 0 : 0);
  let stretches = [];
  L.trunk.forEach((w, k) => {
    if (w.lane) return;
    const g = (ctx.route.guidesOf(w.item) || []).find(x => x.via === w.via);
    if (!g || !['ring', 'pass'].includes(g.kind)) return;
    const eIn = k > 0 ? extent(g, axis(pts[k - 1], pts[k])) : 0;
    const eOut = k + 1 < pts.length ? extent(g, axis(pts[k], pts[k + 1])) : 0;
    if (eIn + eOut <= 0) return;
    stretches.push([cum[k] - eIn / 2 - STRAP_W / 2, cum[k] + eOut / 2 + STRAP_W / 2]);
  });
  stretches.sort((x, y) => x[0] - y[0]);
  stretches = stretches.reduce((acc, s) => { const l = acc.at(-1);
    if (l && s[0] <= l[1]) l[1] = Math.max(l[1], s[1]); else acc.push([...s]); return acc; }, []);
  const out = [];
  for (const [s, e] of runs) {
    const len = e - s, n = Math.ceil(len / mm - 1e-9);
    for (let k = 0; k < n; k++) {
      let a = s + ((k + 0.5) * len) / n;
      const hit = stretches.find(([x, y]) => a > x && a < y);
      if (hit) a = Math.min(e, Math.max(s, a - hit[0] <= hit[1] - a ? hit[0] : hit[1]));
      out.push(a);
    }
  }
  const place = a => {
    let k = 0;
    while (k + 2 < cum.length && a > cum[k + 1]) k++;
    const len = cum[k + 1] - cum[k];
    return {segment: k, t: len > 0 ? Math.round(((a - cum[k]) / len) * 1e4) / 1e4 : 0, along_mm: round1(a)};
  };
  return {every, count: out.length, straps: out.map(place), runs: runs.map(([s, e]) => [round1(s), round1(e)])};
}

// The trunk's length along the rack's own measure, in metres; null when it
// cannot be measured.
export function trunkLength(rack, b, ctx = {}) {
  const L = layoutOf(rack, b, ctx);
  if (!L || L.trunk.length < 2) return null;
  const pts = L.trunk.map(w => pointOf(rack, w, ctx.route));
  if (pts.some(p => !p)) return null;
  let mm = 0;
  for (let k = 1; k < pts.length; k++) mm += dist(pts[k - 1], pts[k]);
  return {metres: Math.round(mm / 10) / 100};
}
