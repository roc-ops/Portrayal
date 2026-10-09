// kit/rack/bundles.js
// CABLE BUNDLES (#921, docs/cable-bundles-design.md). Cables that share part
// of their route, combed into one dressed run and held with hook-and-loop
// straps. The record and its repairs are model.js's (`bundles` on a rack,
// settleBundles); the trunk and a member's route along it are
// bundle-route.js's, and route.js resolveRoute follows them. This file holds
// the rest: what a bundle is called, which pathways its trunk passes, the size
// and bend checks, where its straps go, and the sentences the commands and
// queries use.
// Pure: what reads a drawing comes in on `ctx.route`, the routing context
// route.js takes (`{chassisOf, guidesOf, portX, portY?, zeroUAperture?}`).

import {bundlesOf, bundleName, isWaypoint, uLabel, withoutMembers} from './model.js';
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
  const next = withoutMembers({...rack, cables: (rack.cables || []).filter(c => !gone.has(c.id))}, ids);
  const said = bundlesOf(rack).filter(b => b.members.some(m => gone.has(m.cable))).map(b => {
    const out = b.members.filter(m => gone.has(m.cable)).map(m => m.cable), n = b.members.length - out.length;
    return `${andList(out)} ${out.length === 1 ? 'is' : 'are'} out of ${bundleName(b)}${n < 2 ? `, which now holds ${n === 1 ? 'one cable' : 'no cables'}` : ''}.`;
  });
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
//    bend: {radius_mm, by, unchecked, points, violations} | null,
//    warnings: [text], notes: [text], gone: [waypoint], layout}
// `checked` is false without `ctx.route` (or when a reader throws): then
// nothing is measured and nothing is said to pass. `bend` is bendCheck's
// (#922), null when there is no bundle to bend (fewer than two cables, or no
// trunk).
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
  const pathways = pathwaysOn(rack, L.trunk, ctx);
  for (const p of pathways) {
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
  const bend = bendCheck(rack, b, L, pathways, ctx);
  warnings.push(...bend.warnings);
  notes.push(...bend.notes);
  return {checked: true, bend: bend.bend, warnings, notes, gone: L.gone, layout: L,
          size: {max_mm: round1(max), at: txt(L.T[maxAt]), limit_mm: round1(limit), limitBy, estimated}};
}

// ── bend radius (section 5.2) ────────────────────────────────────────────
// A waypoint is a straight pass, not a corner, when the next segment runs
// within this many degrees of the leg it is on.
export const STRAIGHT_DEG = 1;
const sub = (p, q) => ({x: p.x - q.x, y: p.y - q.y, z: p.z - q.z});
const norm = v => Math.hypot(v.x, v.y, v.z);
const turnDeg = (u, v) => {
  const c = (u.x * v.x + u.y * v.y + u.z * v.z) / (norm(u) * norm(v));
  return (Math.acos(Math.max(-1, Math.min(1, c))) * 180) / Math.PI;
};

// THE CORNERS OF A POLYLINE, in rack coordinates (mm), with the largest bend
// each has room for. A point is a straight pass when the next segment runs
// within STRAIGHT_DEG of the leg from the last corner (or the start), so many
// small turns add up to a corner. Each corner's legs run to the next corner
// on each side, through straight passes, or to the polyline's end; a leg
// between two corners is shared, so each may use half of it, and a leg to an
// end all of it. The room is
//   r_max = min(a_in, a_out) / tan(theta / 2),
// 0 for a polyline that doubles back on itself. A point on top of the one
// before it is skipped. Returns [{k, angle_deg, legs_mm: [in, out], room_mm}],
// `k` the index into `pts` of the corner.
export function cornersOf(pts) {
  const P = [];
  pts.forEach((p, k) => { if (p && (!P.length || norm(sub(p, P.at(-1).p)) > 1e-6)) P.push({p, k}); });
  const cum = [0];
  for (let i = 1; i < P.length; i++) cum.push(cum[i - 1] + norm(sub(P[i].p, P[i - 1].p)));
  const at = [];
  let last = 0;
  for (let i = 1; i + 1 < P.length; i++) {
    const theta = turnDeg(sub(P[i].p, P[last].p), sub(P[i + 1].p, P[i].p));
    if (theta <= STRAIGHT_DEG) continue;
    at.push({i, theta});
    last = i;
  }
  return at.map((c, j) => {
    const inMm = cum[c.i] - (j ? cum[at[j - 1].i] : 0);
    const outMm = (j + 1 < at.length ? cum[at[j + 1].i] : cum.at(-1)) - cum[c.i];
    const a = Math.min(j ? inMm / 2 : inMm, j + 1 < at.length ? outMm / 2 : outMm);
    const room = c.theta >= 180 - 1e-6 ? 0 : a / Math.tan((c.theta * Math.PI) / 360);
    return {k: P[c.i].k, angle_deg: round1(c.theta), legs_mm: [round1(inMm), round1(outMm)], room_mm: round1(room)};
  });
}

// A member's installed minimum bend radius in mm (`ctx.bendOf`, cable-types.js
// bendLookup), or null: no type, a type with no radius, no types loaded, or a
// reader that throws.
function bendMm(cable, ctx) {
  let r = null;
  try { r = typeof ctx.bendOf === 'function' ? ctx.bendOf(cable) : null; } catch { r = null; }
  return typeof r === 'number' && Number.isFinite(r) && r > 0 ? r : null;
}
// "an 18 mm bend", "a 25 mm bend": the article for a number said aloud.
const an = t => (/^(8|1[18](\.|$))/.test(t) ? 'an' : 'a');

// THE BEND CHECK (#922). A bundle needs, at each point, the largest installed
// radius among the members present there, so one fibre makes it as strict as
// fibre; a member at its own join or peel point makes its own turn there and
// does not count (section 4.3). The points are:
// - each pathway on the trunk that states a radius (`radius` on its guide,
//   pathwaysOn): it holds the bundle to that radius, so that is the room, and
//   it is the part's own figure (`source: 'guide'`). No guide states one yet
//   (decision 8);
// - each corner of the trunk, measured as routed length and the straps
//   measure the trunk (pointOf at each resolved waypoint), the room r_max
//   from its legs (cornersOf). That is the rack's own sketch of where things
//   are, not a measured bend, so it is `source: 'legs'`, `estimated: true`.
//   A corner on a pathway that states a radius is the pathway's.
// A point is checked against the members present that have a radius. One
// where none has is unchecked (`ok: null`), never a pass; the members with no
// radius are listed, at the point and for the bundle. Returns
//   {bend: {radius_mm, by, unchecked, points, violations}, warnings, notes}
// where each point (and each violation, a point with `ok: false`) is
//   {kind: 'corner' | 'pathway', at, waypoint, angle_deg?, legs_mm?,
//    room_mm, source, estimated, need_mm, by, members, unchecked, ok,
//    short_mm}
// with `at` the point in words, `waypoint` the trunk waypoint it is at,
// `need_mm` and `by` the largest radius present and the cable that sets it
// (null when none is known), and `short_mm` how far the room misses (0 when
// it does not).
export function bendCheck(rack, b, L, pathways, ctx = {}) {
  const name = bundleName(b), nameOf = labelOf(rack), txt = e => elementText(e, nameOf, rack.frame);
  const byId = new Map((rack.cables || []).map(c => [c.id, c]));
  const loaded = typeof ctx.bendOf === 'function';
  const riding = L.members.filter(m => m.ji != null && m.li != null);
  const rOf = new Map(riding.map(m => [m.cable, loaded ? bendMm(byId.get(m.cable), ctx) : null]));
  const needOf = ms => {
    let need = null, by = null;
    for (const m of ms) { const r = rOf.get(m.cable); if (r != null && (need == null || r > need)) { need = r; by = m.cable; } }
    return {need, by, unchecked: ms.filter(m => rOf.get(m.cable) == null).map(m => m.cable)};
  };
  const all = needOf(riding);
  const points = [];
  const judge = (i, head) => {
    if (present(L, i).length < 2) return;
    const ms = present(L, i, {bend: true});
    if (!ms.length) return;
    const {need, by, unchecked} = needOf(ms);
    const ok = need == null ? null : need <= head.room_mm + 1e-9;
    points.push({...head, need_mm: need, by, members: ms.map(m => m.cable), unchecked, ok,
                 short_mm: ok === false ? round1(need - head.room_mm) : 0});
  };
  // the pathways that state a radius
  const stated = new Set();
  for (const p of pathways) {
    if (!(typeof p.radius === 'number' && p.radius > 0)) continue;
    for (const i of p.at) stated.add(i);
    judge(p.at[0], {kind: 'pathway', at: txt(L.T[p.at[0]]), waypoint: {item: p.item, via: p.via},
                    room_mm: round1(p.radius), source: 'guide', estimated: false});
  }
  // the corners: each at a resolved trunk waypoint, element `seg` with t 0
  const elAt = new Map();
  L.T.forEach((e, i) => { if (e.kind !== 's' && e.t === 0 && !elAt.has(e.seg)) elAt.set(e.seg, i); });
  const pts = L.trunk.map(w => pointOf(rack, w, ctx.route));
  for (const c of cornersOf(pts)) {
    const i = elAt.get(c.k);
    if (i == null || stated.has(i)) continue;
    judge(i, {kind: 'corner', at: txt(L.T[i]), waypoint: L.trunk[c.k], angle_deg: c.angle_deg, legs_mm: c.legs_mm,
              room_mm: c.room_mm, source: 'legs', estimated: true});
  }
  const violations = points.filter(p => p.ok === false);
  const kind = id => { const c = byId.get(id); const t = c?.type || c?.media; return t ? `${id} (${t})` : id; };
  const warnings = violations.map(p => {
    const needs = `${kind(p.by)} needs ${round1(p.need_mm)} mm`;
    if (p.kind === 'pathway')
      return `${name} passes ${p.at}, which holds it to ${an(String(p.room_mm))} ${p.room_mm} mm bend; ${needs}, ${p.short_mm} mm short.`;
    if (p.room_mm === 0) return `${name} doubles back at ${p.at}, with no room for a bend; ${needs}.`;
    return `${name} turns at ${p.at} with room for ${an(String(p.room_mm))} ${p.room_mm} mm bend; ${needs}, ${p.short_mm} mm short.`;
  });
  const notes = [];
  const un = all.unchecked, has = un.length === 1 ? 'has' : 'have';
  if (!loaded && riding.length) notes.push(`${name}'s bend is not checked: the cable types are not loaded.`);
  else if (un.length && un.length === riding.length)
    notes.push(`${name}'s bend is not checked: ${andList(un)} ${has} no cable type with a bend radius.`);
  else if (un.length) notes.push(`${name}'s bend is not checked for ${andList(un)}, which ${has} no cable type with a bend radius.`);
  return {bend: {radius_mm: all.need, by: all.by, unchecked: un, points, violations}, warnings, notes};
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
