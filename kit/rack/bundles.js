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

import {bundlesOf, bundleName, isWaypoint, uLabel, withoutMembers, endHostOf} from './model.js';
import {ownRoute, resolveRoute, trunkRoute, trunkMeasures, pointOf, routePath, routeText, DIAMETERS} from './route.js';
import {traysOf} from './solids.js';
import {bendOf, bendIsDefault, defaultBecause} from './resting.js';
import {elementsOf, elementText, waypointKey, followTrunk, andList, bundleDiameter} from './bundle-route.js';
import {zeroUOnLane, carriesLane} from './zero-u.js';
import {cornersOf, STRAIGHT_DEG} from './route-path.js';

export {bundlesOf, bundleName, settleBundles} from './model.js';
export {deriveTrunk, followTrunk, elementsOf, BUNDLE_PACK, bundleDiameter} from './bundle-route.js';
// The largest a bundle may be across anywhere: 2.5 in.
export const MAX_BUNDLE_MM = 63.5;
// A strap's width along the run, for keeping straps off rings: a drawing figure.
export const STRAP_W = 20;
export const DEFAULT_STRAPS = Object.freeze({value: 12, unit: 'in'});
// A member of no known type counts as fill's figure, and the result says so.
const UNSET_D = 6.0;
const MM = {in: 25.4, mm: 1};

const round1 = v => Math.round(v * 10) / 10;
// A place along a trunk to a tenth of a millimetre. A sum of lengths carries the
// last bits of each, so a place that is 69.45 mm comes out a hair under or
// over it, and would round either way: it is taken to a nanometre first, and a
// half then always rounds up.
const mm1 = v => Math.round(Math.round(v * 1e6) / 1e5) / 10;
const dist = (p, q) => Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);

export const bundleById = (rack, id) => bundlesOf(rack).find(b => b.id === id) ?? null;
// The bundle a cable is in, drawn or not.
export const bundleOfCable = (rack, cableId) => bundlesOf(rack).find(b => b.members.some(m => m.cable === cableId)) ?? null;
// The spacing of a bundle's straps: {value, unit}, or null for none.
export const strapSpacing = b => (b.straps && 'every' in b.straps ? b.straps.every : DEFAULT_STRAPS);
export const strapEveryMm = b => { const e = strapSpacing(b); return e ? e.value * MM[e.unit] : null; };
export const spacingText = e => (e ? `straps every ${e.value} ${e.unit}` : 'no straps');
// A TIE (#1017): a bundle of two or more cables whose stored trunk is ONE
// waypoint, so the cables share a single point and nothing else. It has no
// length, and it is held by one strap round the pack at that point.
export const isTie = b => (b.members?.length ?? 0) >= 2 && (b.route || []).length === 1;
// A member is loose when the device at one of its ends is gone and the cable
// kept (#1021): it rides nothing, so it is not strapped with the others.
const isLoose = (rack, id) => { const c = (rack.cables || []).find(x => x.id === id); return !c || !endHostOf(rack, c.a?.item) || !endHostOf(rack, c.b?.item); };
// The members of a laid-out bundle that ride its trunk: they join and leave it
// and are not loose.
export const ridersOf = (rack, L) => L.members.filter(m => m.ji != null && m.li != null && !isLoose(rack, m.cable));
// WHICH KINDS OF STRAP A BUNDLE HAS (rack file version 4,
// docs/rack-file-v4-design.md section 3.10): beside the spacing straps,
// BREAKOUT straps, one beside each point where a cable joins or leaves, and
// ANCHOR straps, one at each tray tie slot the bundle is tied to. `breakout`
// and `anchors` on `straps` turn each on or off; left out, each is on where
// `every` is left out or a spacing, and off where `every` is null, so a
// bundle saved with no straps has none of any kind.
export function strapKinds(b) {
  const s = b?.straps && typeof b.straps === 'object' ? b.straps : {};
  const none = 'every' in s && s.every === null;
  return {breakout: typeof s.breakout === 'boolean' ? s.breakout : !none, anchors: typeof s.anchors === 'boolean' ? s.anchors : !none};
}
// THE STRAP WIDTHS A RACK MAY USE, mm: hook-and-loop strap is sold in narrower
// and wider rolls, and which one a strap is cut from is a choice. ESTIMATED:
// the three are the common inch sizes (1/2, 3/4 and 1 in) rounded to a whole
// millimetre; no maker's sheet is held for them. Each strap straps() returns
// carries its `width_mm`: STRAP_WIDE_MM for a pack WIDE_PACK_MM across or
// more, STRAP_BASE_MM otherwise, and the narrowest that fits where two peel
// points leave less room than that between them. An anchor is no wider than
// its tie slot is long (slotFit). WIDE_PACK_MM is a figure of this build.
export const STRAP_WIDTHS_MM = [12, 19, 25];
export const STRAP_BASE_MM = 19;
export const STRAP_WIDE_MM = 25;
export const WIDE_PACK_MM = 25;
// The gap a strap keeps from a peel point each side of it. ESTIMATED.
export const STRAP_CLEAR_MM = 5;
// BREAKOUT STRAPS (decided 2026-10-11, docs/rack-file-v4-design.md section
// 10, decision 14). A strap goes before each point where a cable leaves:
// - peel points are grouped only where no strap fits between them, which is
//   closer than BREAKOUT_GROUP_MM, the narrowest strap and its clearance each
//   side; the grouping chains;
// - between two groups, where two or more ride, a gap of BREAKOUT_TWO_MM or
//   more takes a strap BREAKOUT_MM in from each end of it; a shorter gap takes
//   ONE, BREAKOUT_MM from the end a riding member peels at (the middle of the
//   gap when members peel at both ends, or when that would leave the strap
//   less than its clearance), of the widest width that fits;
// - a spacing strap already in a short gap serves, and one within
//   BREAKOUT_MERGE_MM of where a breakout strap would go in a long gap, on
//   the same side, serves as it;
// - the gap at either end of the trunk, where the members fan out, is a gap
//   like any other: it takes a strap wherever one fits with its clearance.
// At a pitch of one unit (44.45 mm) every cable so gets a strap before it
// leaves; at two units and over, one each side of each peel point.
export const BREAKOUT_MM = 25;
export const BREAKOUT_MERGE_MM = 50;
export const BREAKOUT_GROUP_MM = STRAP_WIDTHS_MM[0] + 2 * STRAP_CLEAR_MM;
export const BREAKOUT_TWO_MM = 75;

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
      // as resolveRoute takes it: by the gutter where the bundle is drawn (#1012)
      const own = ownRoute(rack, cable, rc, {gutter: trunk.length > 0 && b.members.length >= 2}).waypoints;
      const f = followTrunk(own, trunk, m, trunkMeasures(rack, cable, trunk, rc));
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
  const m = typeof cable?.media === 'string' && Object.hasOwn(DIAMETERS, cable.media) ? DIAMETERS[cable.media] : null;
  return m ? [m, true] : [UNSET_D, false];
}

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
  // a member whose own route never meets the trunk (#1012): where it joins
  // and leaves, the elements nearest its ports (bundle-route.js followTrunk)
  for (const m of L.members) if (!m.met && L.T.length && b.members.length >= 2) {
    const [j, l] = [m.join, m.leave].map(w => (w ? waypointText(rack, w) : null));
    notes.push(`${m.cable} does not meet ${name}'s route, so it runs straight to it: ${!j || !l ? 'it rides all of it'
      : j === l ? `it joins and leaves at ${j}, the point nearest its ports`
      : `it joins at ${j} and leaves at ${l}, the points nearest its ports`}.`);
  }
  // a tie held by no strap says why (#1017), as a bundle of fewer than two says it is not drawn
  if (isTie(b) && L.trunk.length === 1 && ridersOf(rack, L).length < 2) {
    const n = ridersOf(rack, L).length;
    notes.push(`${name} is a tie at ${waypointText(rack, b.route[0])}, and ${n === 1 ? 'only one cable rides' : 'no cable rides'} there, so it has no strap.`);
  }
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
// The corners of a polyline and the room each has (`cornersOf`, with
// `STRAIGHT_DEG`) are route-path.js's since #973, where route.js reads them
// for a single cable's path too; they are exported from here as before.
export {cornersOf, STRAIGHT_DEG};

// A member's bend radius in mm is resting.js's bendOf, the one a cable's own
// path is judged by (#1132): the type's installed radius (`ctx.bendOf`,
// cable-types.js bendLookup), else its media's, else the default a cable with
// no type is given. The bend is unchecked only where no types are loaded.
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
// - each corner of the trunk's own line (trunkLine, #1037): the members'
//   routed paths, which the straps and the length are measured along, so a
//   turn a path makes where the straight line between two waypoints does not
//   (round a duct) is found. The room r_max is from its legs (cornersOf), a
//   leg two corners share divided by what each turn needs of it (`share:
//   'need'`, #984), the rule a cable's own path is judged by. A corner within
//   CORNER_AT_MM along the line of a waypoint is that waypoint's, `at` it;
//   one between two places is said so ("A to B"); of several at one place the
//   tightest is the place's. That is the rack's own sketch of where things
//   are, not a measured bend, so it is `source: 'legs'`, `estimated: true`.
//   Where the line cannot be read, the straight lines from one resolved
//   waypoint to the next (pointOf at each) stand in.
//   A corner on a pathway that states a radius is the pathway's.
// A point is checked against the members present. A member with no cable type
// is given the default radius a cable alone is given (resting.js bendOf), and
// is listed in `defaulted`, which the note and a warning that it sets say. Only
// where no types are loaded is a point unchecked (`ok: null`), never a pass,
// the members listed in `unchecked`, at the point and for the bundle. Returns
//   {bend: {radius_mm, by, unchecked, defaulted, points, violations}, warnings, notes}
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
  const rOf = new Map(riding.map(m => [m.cable, loaded ? bendOf(byId.get(m.cable), ctx) : null]));
  // the members judged at the default for want of a cable type (#1132)
  const defaulted = loaded ? riding.map(m => m.cable).filter(id => bendIsDefault(byId.get(id), ctx)) : [];
  const needOf = ms => {
    let need = null, by = null;
    for (const m of ms) { const r = rOf.get(m.cable); if (r != null && (need == null || r > need)) { need = r; by = m.cable; } }
    return {need, by, unchecked: ms.filter(m => rOf.get(m.cable) == null).map(m => m.cable)};
  };
  const all = needOf(riding);
  const points = [];
  const judgeOn = (ms, head) => {
    if (!ms.length) return;
    const {need, by, unchecked} = needOf(ms);
    const ok = need == null ? null : need <= head.room_mm + 1e-9;
    points.push({...head, need_mm: need, by, members: ms.map(m => m.cable), unchecked, ok,
                 short_mm: ok === false ? round1(need - head.room_mm) : 0});
  };
  const judge = (i, head) => {
    if (present(L, i).length < 2) return;
    judgeOn(present(L, i, {bend: true}), head);
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
  // read along the trunk's own line (#1037), the members' routed paths, so a turn a
  // path makes where the straight line does not is found; a line that cannot be
  // read leaves the straight lines between the waypoints
  let line = null;
  try { line = trunkLine(rack, b, L, ctx.route); } catch { line = null; }
  const found = [];
  if (line) {
    const poly = line.polyline(), wps = [...elAt.values()];
    for (const c of cornersOf(poly, {share: 'need'})) {
      const a = poly[c.k].a;
      // at a waypoint when it is within a ring's depth of one, else between the two places it falls between
      const i = wps.find(x => Math.abs(line.cum[x] - a) <= CORNER_AT_MM);
      const piece = i == null ? line.pieces.find(x => a >= x.from - 1e-9 && a <= x.to + 1e-9) : null;
      if (i == null && !piece) continue;
      found.push({c, i, piece, key: i ?? `${piece.i}-${piece.j}`});
    }
  } else {
    const pts = L.trunk.map(w => pointOf(rack, w, ctx.route));
    for (const c of cornersOf(pts, {share: 'need'})) found.push({c, i: elAt.get(c.k), piece: null, key: elAt.get(c.k)});
  }
  // the tightest of the corners at one place is the place's
  const tightest = new Map();
  for (const f of found) if (!tightest.has(f.key) || f.c.room_mm < tightest.get(f.key).c.room_mm) tightest.set(f.key, f);
  for (const {c, i, piece} of tightest.values()) {
    if (piece) {
      // a turn between two places is the whole pack's: every member that rides the piece
      const ms = L.members.filter(m => m.ji != null && m.li != null && Math.min(m.ji, m.li) <= piece.i && Math.max(m.ji, m.li) >= piece.j);
      if (ms.length >= 2) judgeOn(ms, {kind: 'corner', at: `${txt(L.T[piece.i])} to ${txt(L.T[piece.j])}`, waypoint: L.trunk[L.T[piece.i].seg], angle_deg: c.angle_deg,
                   legs_mm: c.legs_mm, room_mm: c.room_mm, source: 'legs', estimated: true});
      continue;
    }
    if (i == null || stated.has(i)) continue;
    judge(i, {kind: 'corner', at: txt(L.T[i]), waypoint: L.trunk[L.T[i].seg], angle_deg: c.angle_deg, legs_mm: c.legs_mm,
              room_mm: c.room_mm, source: 'legs', estimated: true});
  }
  const violations = points.filter(p => p.ok === false);
  const kind = id => { const c = byId.get(id); const t = c?.type || c?.media; return t ? `${id} (${t})` : id; };
  const warnings = violations.map(p => {
    const needs = `${kind(p.by)} needs ${round1(p.need_mm)} mm${defaulted.includes(p.by) ? ` (the default, ${defaultBecause(byId.get(p.by))})` : ''}`;
    if (p.kind === 'pathway')
      return `${name} passes ${p.at}, which holds it to ${an(String(p.room_mm))} ${p.room_mm} mm bend; ${needs}, ${p.short_mm} mm short.`;
    if (p.room_mm === 0) return `${name} doubles back at ${p.at}, with no room for a bend; ${needs}.`;
    return `${name} turns at ${p.at} with room for ${an(String(p.room_mm))} ${p.room_mm} mm bend; ${needs}, ${p.short_mm} mm short.`;
  });
  const notes = [];
  if (!loaded && riding.length) notes.push(`${name}'s bend is not checked: the cable types are not loaded.`);
  else if (defaulted.length) notes.push(`${name}'s bend is checked at ${round1(rOf.get(defaulted[0]))} mm for ${andList(defaulted)}, the default for a cable with ${defaulted.some(id => byId.get(id)?.type) ? 'no known bend radius' : 'no cable type'}.`);
  return {bend: {radius_mm: all.need, by: all.by, unchecked: all.unchecked, defaulted, points, violations}, warnings, notes};
}

// EVERY BUNDLE'S CHECKS, as findings {kind: 'warning' | 'note', bundle, text}.
export function bundleChecks(rack, ctx = {}) {
  return bundlesOf(rack).flatMap(b => {
    const r = bundleCheck(rack, b, ctx);
    return [...r.warnings.map(text => ({kind: 'warning', bundle: b.id, text})),
            ...r.notes.map(text => ({kind: 'note', bundle: b.id, text}))];
  });
}

// ── the trunk's own line (#1034) ─────────────────────────────────────────
// WHERE A TRUNK RUNS, AND HOW LONG IT IS. A trunk is a list of waypoints, but
// the cables of it do not run straight from one to the next: a member's path
// (route.js routePath) passes through a ring by its opening, lies along a
// tray, hangs between two pathways, and goes round a body by a detour point.
// So the trunk is measured, and its straps are placed, on the members' paths
// and never on the straight line between two waypoints.
// A PIECE AT A TIME. The trunk is cut at every element that is a place
// (bundle-route.js elementsOf: a pathway, and a lane at each unit), and each
// piece between two neighbours is taken from ONE member that rides both:
// - where a member's path is at a waypoint: a lane point is the point itself;
//   a pathway, a ring and a tray are the middle, by length, of the points the
//   path has there (a ring's entry and exit, a tray's stretch). A lane unit
//   between two lane waypoints is that share of the way along the path
//   between them;
// - the piece is that member's path between the two places, and its length
//   is the length of that path;
// - where several members ride a piece, it is THE MIDDLE ONE BY LENGTH: the
//   members whose paths can be read are put in order of how long each is on
//   the piece (to a micron), then of their ids (by number, so c2 before c10,
//   and by the plain text where the numbers are the same, so c02 before c2),
//   and the one in the middle is taken, the earlier of two middles. A strap
//   goes round the whole pack, so it belongs where most of the pack lies:
//   one limp cord among stiff ones hangs lower and longer than the rest, and
//   the middle one is never that cord while it is outnumbered. So one member
//   sets neither the length, nor the count, nor the place. Members of one
//   kind lie alike, tie, and the middle one by id is taken. The order the
//   cables are written in, in the file or in the bundle, plays no part.
// WHAT `on` THEN MEANS. Each cable is laid on its own, so two members of
// unlike kinds hang a little apart between the same two places where a real
// pack would hang as one. A strap's point is on the path of the member it
// names, exactly; the members that lie like it are there too, and one that
// hangs otherwise is off it by the difference of the two hangs.
// A piece no member's path can be read for is the straight line between the
// two places, as every piece was before #1034: one nobody rides (no strap
// goes there), and one whose riders have no path (a port not found on its
// drawing). The second is said: `straight` is true, and straps() and
// trunkLength pass it on, since the length and the count there are an
// estimate. An error a reader of the context throws is not caught here.
// A PIECE FEWER THAN HALF OF WHOSE RIDERS HAVE A PATH is taken from the
// middle one of those that have, which is then not the middle of the pack:
// one AOC with a path among three DACs with none sets the trunk. That is
// said too (`few`), in the same way.
// WHERE TWO KINDS RIDE IN EQUAL NUMBERS the earlier of the two middles is of
// the shorter kind, so the trunk follows the kind that hangs less and the
// other half of the pack is off every strap by the difference of the hangs.
// And where the member named changes kind from one piece to the next (at a
// ring, where the riders change), the line steps sideways there by the
// difference of where the two kinds stand in the ring, a few millimetres.
// Returns {pts, cum, wcum, length, straight, pointAt}, or null when a trunk
// waypoint has no point: `pts` is pointOf at each resolved waypoint; `cum[i]` is how
// far along the trunk element `i` of `L.T` is, mm; `wcum[k]` the same for
// resolved waypoint `k`; and `pointAt(a)` is the place `a` mm along, {point:
// {x, y, z}, dir: {x, y, z} | null, on}: rack coordinates, the way the trunk
// runs there as a unit vector, and the id of the cable whose path it is on
// (null on a straight piece).
const byNumber = (p, q) => String(p).localeCompare(String(q), 'en', {numeric: true}) || (String(p) < String(q) ? -1 : String(p) > String(q) ? 1 : 0);
const CORE = new Set(['entry', 'exit', 'face', 'pathway', 'tray']);
// How far along a path each waypoint of its route is: the arc length at each,
// null for one the path has no point of.
function stationsOf(P, arc, wps, pointAt) {
  const out = [];
  let n = 0;
  const same = (p, w) => p.item === w.item && p.via === w.via;
  for (const w of wps) {
    if (w.lane) {
      const q = pointAt(w);
      let k = n;
      while (q && k < P.length && !(P[k].at === 'lane' && dist(P[k], q) < 1e-6)) k++;
      if (!q || k >= P.length) { out.push(null); continue; }
      out.push(arc[k]); n = k + 1;
      continue;
    }
    let k = n;
    while (k < P.length && !same(P[k], w)) k++;
    if (k >= P.length) { out.push(null); continue; }
    // its points run on while they are its own, a detour between two of them counted in
    let e = k;
    for (let j = k + 1; j < P.length && (same(P[j], w) || P[j].at === 'detour'); j++) if (same(P[j], w)) e = j;
    const core = [];
    for (let j = k; j <= e; j++) if (same(P[j], w) && CORE.has(P[j].at)) core.push(j);
    out.push(core.length ? (arc[core[0]] + arc[core.at(-1)]) / 2 : null);
    n = e + 1;
  }
  return out;
}
// A member's path as a line to measure along: its points, the arc length at
// each, and how far along each element of its route is, by key. null when it
// is not laid as a member of this bundle, or has no path.
function memberLine(rack, b, cableId, rc) {
  const cable = (rack.cables || []).find(c => c.id === cableId);
  if (!cable) return null;
  // not caught: a reader that throws, or a path found changed (ctx.checkKept), is the caller's to hear of
  const route = resolveRoute(rack, cable, rc), path = route.bundle === b.id ? routePath(rack, cable, rc) : null;
  if (!path || path.points.length < 2) return null;
  const P = path.points, arc = [0];
  for (let k = 1; k < P.length; k++) arc.push(arc[k - 1] + dist(P[k - 1], P[k]));
  const st = stationsOf(P, arc, route.waypoints, w => pointOf(rack, w, rc));
  const pos = new Map();
  for (const e of elementsOf(route.waypoints)) {
    if (e.kind === 's' || pos.has(e.key)) continue;
    const c0 = st[e.seg], c1 = st[e.seg + 1];
    if (c0 == null || (e.t > 0 && c1 == null)) continue;
    pos.set(e.key, e.t > 0 ? c0 + e.t * (c1 - c0) : c0);
  }
  return {id: cableId, P, arc, pos};
}
// The point `s` mm along a line of points, and the way the line runs there
// (`sign` -1 for a member that rides the trunk the other way).
function onLine(P, arc, s, sign) {
  let k = 1;
  while (k + 1 < P.length && arc[k] < s) k++;
  // the way of the leg it is on; a leg of no length takes the nearest that has one
  let i = k;
  while (i + 1 < P.length && arc[i] - arc[i - 1] < 1e-9) i++;
  while (i > 1 && arc[i] - arc[i - 1] < 1e-9) i--;
  const len = arc[k] - arc[k - 1], f = len > 1e-9 ? Math.min(1, Math.max(0, (s - arc[k - 1]) / len)) : 0;
  const [p, q] = [P[k - 1], P[k]], [u, v] = [P[i - 1], P[i]], d = dist(u, v);
  return {point: {x: p.x + f * (q.x - p.x), y: p.y + f * (q.y - p.y), z: p.z + f * (q.z - p.z)},
          dir: d > 1e-9 ? {x: sign * (v.x - u.x) / d, y: sign * (v.y - u.y) / d, z: sign * (v.z - u.z) / d} : null};
}
function trunkLine(rack, b, L, rc) {
  const pts = L.trunk.map(w => pointOf(rack, w, rc));
  if (!pts.length || pts.some(p => !p)) return null;
  const T = L.T;
  // a place on the straight line: the waypoint an element is at, or its share of the way to the next
  const chordAt = e => { const p = pts[e.seg], q = pts[e.seg + 1];
    return e.t > 0 && q ? {x: p.x + e.t * (q.x - p.x), y: p.y + e.t * (q.y - p.y), z: p.z + e.t * (q.z - p.z)} : p; };
  const riding = L.members.filter(m => m.ji != null && m.li != null)
    .map(m => ({id: m.cable, lo: Math.min(m.ji, m.li), hi: Math.max(m.ji, m.li)})).sort((p, q) => byNumber(p.id, q.id));
  const lines = new Map();
  const lineOf = id => { if (!lines.has(id)) lines.set(id, memberLine(rack, b, id, rc)); return lines.get(id); };
  const nodes = T.map((e, i) => (e.kind === 's' ? -1 : i)).filter(i => i >= 0);
  const cum = new Array(T.length).fill(0), pieces = [];
  let straight = false, few = false;
  for (let n = 1; n < nodes.length; n++) {
    const i = nodes[n - 1], j = nodes[n];
    const read = [];
    let ridden = 0;
    for (const m of riding) {
      if (m.lo > i || m.hi < j) continue;
      ridden++;
      const line = lineOf(m.id), s0 = line?.pos.get(T[i].key), s1 = line?.pos.get(T[j].key);
      if (s0 != null && s1 != null) read.push({line, s0, s1, len: Math.abs(s1 - s0)});
    }
    // the middle one by length; `riding` is in id order and the sort keeps it, so two as long stay in id order
    read.sort((x, y) => Math.round(x.len * 1e3) - Math.round(y.len * 1e3));
    const best = read.length ? read[Math.floor((read.length - 1) / 2)] : null;
    if (ridden && !best) straight = true;
    // the middle of a minority is not the middle of the pack
    if (best && 2 * read.length < ridden) few = true;
    const p = chordAt(T[i]), q = chordAt(T[j]);
    const len = best ? best.len : dist(p, q);
    pieces.push({from: cum[i], to: cum[i] + len, ...(best ?? {}), p, q, i, j});
    cum[j] = cum[i] + len;
    // a lane segment between two units is half way
    for (let k = i + 1; k < j; k++) cum[k] = cum[i] + len / 2;
  }
  const wcum = [];
  L.trunk.forEach((w, k) => { const i = T.findIndex(e => e.kind !== 's' && e.seg === k && e.t === 0); wcum.push(i >= 0 ? cum[i] : wcum.at(-1) ?? 0); });
  const length = nodes.length ? cum[nodes.at(-1)] : 0;
  const pointAt = a => {
    const c = pieces.findLast(x => x.to - x.from > 1e-9 && a >= x.from - 1e-9) ?? pieces[0];
    if (!c) return {point: {...pts[0]}, dir: null, on: null};
    const f = c.to - c.from > 1e-9 ? Math.min(1, Math.max(0, (a - c.from) / (c.to - c.from))) : 0;
    if (c.line) { const sign = c.s1 >= c.s0 ? 1 : -1; return {...onLine(c.line.P, c.line.arc, c.s0 + sign * f * c.len, sign), on: c.line.id}; }
    const d = dist(c.p, c.q);
    return {point: {x: c.p.x + f * (c.q.x - c.p.x), y: c.p.y + f * (c.q.y - c.p.y), z: c.p.z + f * (c.q.z - c.p.z)},
            dir: d > 1e-9 ? {x: (c.q.x - c.p.x) / d, y: (c.q.y - c.p.y) / d, z: (c.q.z - c.p.z) / d} : null, on: null};
  };
  // THE LINE AS A POLYLINE, to read its corners from (#1037): the points of each
  // piece's path between its two places, then those of the next, each point
  // with `a`, how far along the trunk it is. A piece with no path is the straight line.
  // Where the next piece starts within JOG_MM of where the last ended (the members
  // change at a ring, a few millimetres apart) it is taken to start there.
  const polyline = () => {
    const out = [];
    for (const c of pieces) {
      let seq;
      if (c.line) {
        const {P, arc} = c.line, lo = Math.min(c.s0, c.s1), hi = Math.max(c.s0, c.s1);
        const mid = [];
        for (let k = 0; k < P.length; k++) if (arc[k] > lo + 1e-9 && arc[k] < hi - 1e-9) mid.push({...P[k], a: c.from + Math.abs(arc[k] - c.s0)});
        if (c.s1 < c.s0) mid.reverse();
        seq = [{...onLine(P, arc, c.s0, 1).point, a: c.from}, ...mid, {...onLine(P, arc, c.s1, 1).point, a: c.to}];
      } else seq = [{...c.p, a: c.from}, {...c.q, a: c.to}];
      if (out.length && dist(out.at(-1), seq[0]) <= JOG_MM) seq.shift();
      out.push(...seq);
    }
    return out;
  };
  return {pts, cum, wcum, length, straight, few, pointAt, pieces, polyline};
}
const JOG_MM = 25;
// A corner of the line this close along it to a waypoint is that waypoint's: a path turns
// at the mouth of a ring, not at the middle of it.
const CORNER_AT_MM = 15;

// ── straps (section 6; docs/rack-file-v4-design.md section 3.10) ─────────
// Three kinds, each entry with its `kind`:
// SPACING. Along each RUN of the trunk (a longest stretch with two or more
// members riding together), n = ceil(L / every) straps, evenly at
// (k + 0.5) L / n, so none is more than the spacing apart and none sits on a
// run's end.
// BREAKOUT. A PEEL POINT is a place along the trunk where at least one member
// joins or leaves it; the two ends of the trunk are peel points where members
// fan out. A strap goes BREAKOUT_MM from a peel point on each side on which
// two or more members ride, counting a member that peels there on the side it
// rides: so both sides where a cable leaves a bundle of four, and the one side
// where the last two part. The rule names sides by who rides, not by
// direction, so a bundle written end for end has the same straps. Peel points
// are grouped by chaining and a group is strapped on its outer sides only; a
// spacing strap near enough serves; a short side gets none (the constants
// above).
// ANCHOR. One at each tray with tie slots that the trunk lies on, at the slot
// nearest the middle of its stretch there (the lower index on a tie).
// A spacing or breakout strap that falls on a ring or a pass-through (its
// extent along the run, widened by half a strap each side) moves to the
// stretch's nearer edge; one in a duct stays. The count is what the BOM buys:
// the three kinds together, never raised for a move.
// ALL OF IT IS MEASURED ALONG THE TRUNK'S OWN LINE (trunkLine, above, #1034):
// the members' routed paths, not the straight line between two waypoints, so
// a run is as long as the cable strapped in it and a strap is on a cable.
// Returns {every, count, kinds: {spacing, breakout, anchor}, straps: [{kind,
// segment, t, along_mm, point, dir, on, item?, via?, tie?}], runs: [[from,
// to]]} (mm from the trunk's start), or null without `ctx.route`. A straps
// entry names its trunk segment (between resolved waypoints `segment` and
// `segment + 1`) and `t`, the share of that segment's routed length it is
// along, for a view that draws the waypoints at its own positions; and it
// carries its own place: `point`, {x, y, z} in rack coordinates (route.js)
// to a hundredth of a millimetre, `dir`, the way the trunk runs there as a
// unit vector (null where it has no length), and `on`, the id of the cable
// whose path the point is on (null where no member's path could be read and
// the straight line stands in; WHAT `on` THEN MEANS, above). An anchor also
// names its tray and the index of its tie slot. `straight` is true where a
// stretch that members ride was measured along the straight line, and `few`
// where one was measured on fewer than half of its riders; `notes` then says
// so.
export function straps(rack, b, ctx = {}) {
  const every = strapSpacing(b), mm = strapEveryMm(b), want = strapKinds(b);
  const L = layoutOf(rack, b, ctx);
  if (!L) return null;
  const empty = {every, count: 0, kinds: {spacing: 0, breakout: 0, anchor: 0}, widths: {}, straps: [], runs: [], straight: false, few: false};
  // a bundle is strapped where two or more members ride its trunk, and a loose member rides nothing (#1021)
  // (loose: the device at an end is gone and the cable kept)
  const rides = ridersOf(rack, L).length;
  const tie = isTie(b) && L.trunk.length === 1;
  if (b.members.length < 2 || rides < 2 || (L.trunk.length < 2 && !tie)) return empty;
  const line = trunkLine(rack, b, L, ctx.route);
  if (!line) return empty;
  if (tie) return tieStraps(rack, b, L, line, ctx, {every, mm, want, empty});
  // `cum` is by resolved waypoint, as the stretches and the anchors below read it
  const pts = line.pts, cum = line.wcum, alongAt = i => line.cum[i];
  // runs: where two or more members ride together
  const spans = L.members.filter(m => m.ji != null && m.li != null)
    .map(m => [alongAt(Math.min(m.ji, m.li)), alongAt(Math.max(m.ji, m.li))]);
  const cuts = [...new Set(spans.flat())].sort((x, y) => x - y);
  const runs = [];
  for (let k = 1; k < cuts.length; k++) {
    const [s, e] = [cuts[k - 1], cuts[k]];
    const n = spans.filter(([x, y]) => x <= s + 1e-9 && y >= e - 1e-9).length;
    if (n < 2 || e - s < 1e-9) continue;
    if (runs.length && Math.abs(runs.at(-1)[1] - s) < 1e-9) runs.at(-1)[1] = e; else runs.push([s, e]);
  }
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
  // off a ring, to the nearer edge of its stretch, and never out of [lo, hi]
  const clear = (a, lo, hi) => {
    const hit = stretches.find(([x, y]) => a > x && a < y);
    return hit ? Math.min(hi, Math.max(lo, a - hit[0] <= hit[1] - a ? hit[0] : hit[1])) : a;
  };
  const spacing = [];
  if (mm) for (const [s, e] of runs) {
    const len = e - s, n = Math.ceil(len / mm - 1e-9);
    for (let k = 0; k < n; k++) spacing.push(clear(s + ((k + 0.5) * len) / n, s, e));
  }
  // the pack at a place along the trunk: the members riding there, and how wide a strap it takes
  const riders = L.members.filter(m => m.ji != null && m.li != null).map(m => {
    const c = (rack.cables || []).find(x => x.id === m.cable);
    return {lo: alongAt(Math.min(m.ji, m.li)), hi: alongAt(Math.max(m.ji, m.li)), d: diameter(c, ctx.route)[0]};
  });
  const packAt = a => bundleDiameter(riders.filter(x => x.lo <= a + 1e-9 && x.hi >= a - 1e-9).map(x => x.d));
  const baseWidth = a => (packAt(a) >= WIDE_PACK_MM ? STRAP_WIDE_MM : STRAP_BASE_MM);
  // breakout straps: the peel points, grouped where no strap fits between, and the gaps between groups
  const breakout = [];
  if (want.breakout) {
    const groups = [];
    for (const p of cuts) { const g = groups.at(-1); if (g && p - g[1] < BREAKOUT_GROUP_MM - 1e-9) g[1] = p; else groups.push([p, p]); }
    const inGroup = (v, g) => v >= g[0] - 1e-9 && v <= g[1] + 1e-9;
    for (let k = 1; k < groups.length; k++) {
      const A = groups[k - 1], B = groups[k], lo = A[1], hi = B[0], gap = hi - lo;
      const ride = spans.filter(([x, y]) => x <= lo + 1e-9 && y >= hi - 1e-9);
      if (ride.length < 2) continue;
      const here = spacing.filter(a => a >= lo - 1e-9 && a <= hi + 1e-9);
      if (gap >= BREAKOUT_TWO_MM - 1e-9) {
        // room for one at each end, each unless a spacing strap is near it
        for (const at of [lo + BREAKOUT_MM, hi - BREAKOUT_MM])
          if (!here.some(a => Math.abs(a - at) <= BREAKOUT_MERGE_MM + 1e-9)) breakout.push({a: clear(at, lo, hi), w: baseWidth(at)});
        continue;
      }
      if (here.length) continue;                       // a spacing strap already in the gap serves
      // one strap: before the end a riding member peels at, or in the middle
      const atA = ride.some(([x, y]) => inGroup(x, A) || inGroup(y, A)), atB = ride.some(([x, y]) => inGroup(x, B) || inGroup(y, B));
      const mid = (lo + hi) / 2;
      let at = atA === atB ? mid : atB ? hi - BREAKOUT_MM : lo + BREAKOUT_MM;
      const fits = (w, where) => Math.min(where - lo, hi - where) >= w / 2 + STRAP_CLEAR_MM - 1e-9;
      const want_w = baseWidth(at);
      let w = [...STRAP_WIDTHS_MM].reverse().find(x => x <= want_w && fits(x, at));
      if (w == null) { at = mid; w = [...STRAP_WIDTHS_MM].reverse().find(x => x <= want_w && fits(x, at)); }
      if (w != null) breakout.push({a: clear(at, lo, hi), w});
    }
  }
  // anchor straps: each tray with tie slots the trunk lies on
  const anchors = [], misfits = [];
  if (want.anchors) {
    const trays = traysOf(rack, ctx.route);
    L.trunk.forEach((w, k) => {
      const t = w.lane ? null : trays.find(x => x.item === w.item && x.via === w.via);
      const tie = t ? nearestTie(t, stretchMiddle(t, pts[k - 1], pts[k], pts[k + 1])) : null;
      if (tie == null) return;
      // the strap goes through the slot, so it is no wider than the slot is long
      const fit = slotFit(t, tie, baseWidth(cum[k]));
      if (fit != null) anchors.push({a: cum[k], item: w.item, via: w.via, tie, w: fit});
      else misfits.push(`${bundleName(b)} is not tied at ${labelIn(rack, w.item)} ${w.via}: tie slot ${tie + 1} is ${round1(slotLong(t, tie))} mm long, and the narrowest strap is ${STRAP_WIDTHS_MM[0]} mm wide.`);
    });
  }
  const place = a => {
    let k = 0;
    while (k + 2 < cum.length && a > cum[k + 1]) k++;
    const len = cum[k + 1] - cum[k];
    const at = line.pointAt(a), r2 = v => Math.round(v * 100) / 100 || 0, r4 = v => Math.round(v * 1e4) / 1e4 || 0;
    return {segment: k, t: len > 0 ? Math.round(((a - cum[k]) / len) * 1e4) / 1e4 : 0, along_mm: mm1(a),
            point: {x: r2(at.point.x), y: r2(at.point.y), z: r2(at.point.z)},
            dir: at.dir ? {x: r4(at.dir.x), y: r4(at.dir.y), z: r4(at.dir.z)} : null, on: at.on};
  };
  const list = [...spacing.map(a => ({kind: 'spacing', ...place(a), width_mm: baseWidth(a)})),
                ...breakout.map(x => ({kind: 'breakout', ...place(x.a), width_mm: x.w})),
                ...anchors.map(x => ({kind: 'anchor', ...place(x.a), width_mm: x.w, item: x.item, via: x.via, tie: x.tie}))]
    .sort((p, q) => p.along_mm - q.along_mm);
  return {every, count: list.length, kinds: {spacing: spacing.length, breakout: breakout.length, anchor: anchors.length},
          widths: widthCounts(list.map(x => x.width_mm)), straps: list, runs: runs.map(([s, e]) => [mm1(s), mm1(e)]),
          // a tie slot too short for any strap: said, and no strap is counted there
          // where riders have no path the trunk is the straight line there: said, since the count is then an estimate
          straight: line.straight, few: line.few,
          notes: [...misfits, ...(line.straight ? [straightText(bundleName(b))] : []), ...(line.few ? [fewText(bundleName(b))] : [])]};
}

// A TIE (#1017, decided 2026-10-16): the bundle's trunk is one waypoint, so it
// has no run to space straps along and no peel points to strap before. It has
// ONE strap, round the pack at that waypoint, and nothing else:
// - RIDING: the members that join and leave at the waypoint, which is what
//   riding a longer trunk means (a member whose route misses it runs to it, as
//   it does to a longer trunk's nearest element, and a loose member rides
//   nothing). Fewer than two riding: no strap (#1021), and bundleCheck says so.
// - WIDTH: as for any strap, by the pack there: STRAP_WIDE_MM for a pack
//   WIDE_PACK_MM across or more, else STRAP_BASE_MM. It is not moved off a ring
//   (the ring is where the cables are tied) and is not narrowed for peel points
//   (all of them are at this one place).
// - PLACE: on the path of the middle one by id of the members that have a path
//   through the waypoint (as the middle one sets a longer trunk's pieces), `dir`
//   the way that path runs there; the waypoint itself, with no `dir`, where
//   none has. `along_mm` is 0 and `segment` 0, `t` 0: the trunk has no length.
// - STRAPS SET TO NONE (`every: null` with no `breakout` or `anchors`) has none,
//   as a longer trunk has none of any kind. A spacing does not matter: there is
//   no length to space along.
// It is counted as its own kind, `tie`, in `kinds`, which gains that key only
// for a tie; a trunk of two or more nodes returns exactly what it did.
function tieStraps(rack, b, L, line, ctx, {every, mm, want, empty}) {
  if (mm == null && !want.breakout && !want.anchors) return empty;
  const riding = ridersOf(rack, L), T0 = L.T.find(e => e.kind !== 's');
  const ds = riding.map(m => diameter((rack.cables || []).find(x => x.id === m.cable), ctx.route)[0]);
  const width = bundleDiameter(ds) >= WIDE_PACK_MM ? STRAP_WIDE_MM : STRAP_BASE_MM;
  const ids = riding.map(m => m.cable).sort(byNumber);
  const lines = ids.map(id => memberLine(rack, b, id, ctx.route)).map((l, k) => ({id: ids[k], l, s: l?.pos.get(T0.key)})).filter(x => x.s != null);
  const mid = lines.length ? lines[Math.floor((lines.length - 1) / 2)] : null;
  const r2 = v => Math.round(v * 100) / 100 || 0, r4 = v => Math.round(v * 1e4) / 1e4 || 0;
  const at = mid ? onLine(mid.l.P, mid.l.arc, mid.s, 1) : {point: line.pts[0], dir: null};
  const w = L.trunk[0];
  const one = {kind: 'tie', segment: 0, t: 0, along_mm: 0, point: {x: r2(at.point.x), y: r2(at.point.y), z: r2(at.point.z)},
               dir: at.dir ? {x: r4(at.dir.x), y: r4(at.dir.y), z: r4(at.dir.z)} : null, on: mid ? mid.id : null, width_mm: width,
               ...(w.lane ? {lane: w.lane, ru: w.ru} : {item: w.item, via: w.via})};
  return {every, count: 1, kinds: {spacing: 0, breakout: 0, anchor: 0, tie: 1}, widths: widthCounts([width]), straps: [one], runs: [],
          straight: false, few: false, tie: true, notes: []};
}

// What is said of a bundle measured, in part or whole, along the straight
// lines between its waypoints (the trunk's own line, above).
export const fewText = name => `${name} is measured in part on fewer than half of the cables that ride there, since no path could be read for the others (a port not found on its drawing), so its length and its straps are an estimate.`;
export const straightText = name => `${name} is measured along the straight line between its waypoints where no path could be read for its cables (a port not found on its drawing), so its length and its straps are an estimate.`;

// How many straps of each width: {19: 6, 12: 2}.
export const widthCounts = ws => ws.reduce((m, w) => { m[w] = (m[w] || 0) + 1; return m; }, {});

// WHERE ALONG A TRAY A STRETCH HAS ITS MIDDLE: the stretch is what lies over
// the tray's floors of the way from `prev` through `at` to `next` (rack
// points; either may be missing), measured along the axis cables lie on it.
function stretchMiddle(t, prev, at, next) {
  const ax = t.run === 'z' ? 'z' : 'x', [lo, hi] = t.run === 'z' ? ['z0', 'z1'] : ['x0', 'x1'];
  const from = Math.min(...t.floors.map(f => f[lo])), to = Math.max(...t.floors.map(f => f[hi]));
  const clamp = v => Math.min(to, Math.max(from, v));
  return (clamp((prev ?? at)[ax]) + clamp((next ?? at)[ax])) / 2;
}
// The tie slot of a tray nearest a place along it: its index in `ties`, the
// lower index where two are as near; null for a tray with none.
// A STRAP GOES THROUGH ITS TIE SLOT, so it is no wider than the slot is long:
// slotFit is the widest stock width that is neither over `want` nor over the
// long side of the slot, or null when even the narrowest does not go through.
const slotLong = (t, tie) => { const s = t.ties[tie]; return Math.max(s.x1 - s.x0, s.z1 - s.z0); };
const slotFit = (t, tie, want) => [...STRAP_WIDTHS_MM].reverse().find(w => w <= want && w <= slotLong(t, tie) + 1e-9) ?? null;
const labelIn = (rack, id) => (rack.items || []).find(i => i.id === id)?.label || id;
function nearestTie(t, where) {
  const [lo, hi] = t.run === 'z' ? ['z0', 'z1'] : ['x0', 'x1'];
  let best = null, gap = Infinity;
  t.ties.forEach((s, i) => { const d = Math.abs((s[lo] + s[hi]) / 2 - where); if (d < gap - 1e-9) { gap = d; best = i; } });
  return best;
}

// EVERY TIE SLOT A STRAP ANCHORS AT, rack-wide: [{item, via, tie, bundles:
// [ids], cables: [ids]}], one entry a slot however many pass it, since one
// strap at a slot serves every cable and bundle there. The count is by slot,
// never by cable.
// - a bundle (drawn, with anchors on): the slot straps() gives it at each tray
//   its trunk lies on, on either face;
// - a single cable on the HELD face of a tray: each tie slot it uses there;
// - a single cable on the RESTING face of a tray that states tie slots: the
//   slot nearest the middle of its stretch there. `straps: {anchors: false}`
//   on a cable turns its own off; a member of a drawn bundle is not counted
//   again at a tray its bundle's trunk lies on.
// Nothing anchors to a ring or to a part beside the rack: none states a tie
// point. [] without `ctx.route`.
const ON_TRAY_MM = 12;   // a cable this close over a tray floor lies on it, or on a ring sill of it
export function anchorsOf(rack, ctx = {}) {
  const rc = ctx?.route;
  if (!rc) return [];
  const out = new Map();
  const at = (item, via, tie) => {
    const key = `${item}|${via}|${tie}`;
    if (!out.has(key)) out.set(key, {item, via, tie, width_mm: STRAP_BASE_MM, bundles: [], cables: []});
    return out.get(key);
  };
  const trunkTrays = new Map();
  for (const b of bundlesOf(rack)) {
    let st = null;
    try { st = straps(rack, b, ctx); } catch { st = null; }
    for (const s of st?.straps || []) if (s.kind === 'anchor') {
      const slot = at(s.item, s.via, s.tie);
      slot.bundles.push(b.id);
      slot.width_mm = Math.max(slot.width_mm, s.width_mm);
    }
    if (b.members.length >= 2 && strapKinds(b).anchors)
      for (const m of b.members) trunkTrays.set(m.cable, (b.route || []).filter(w => w.item).map(w => `${w.item}|${w.via}`));
  }
  let trays = [];
  try { trays = traysOf(rack, rc); } catch { trays = []; }
  for (const s of cableSlots(rack, rc, trunkTrays)) for (const i of s.ties) {
    // a slot no strap goes through ties nothing, unless a bundle is tied there
    const t = trays.find(x => x.item === s.item && x.via === s.via);
    const fit = t ? slotFit(t, i, STRAP_BASE_MM) : STRAP_BASE_MM;
    const key = `${s.item}|${s.via}|${i}`;
    if (fit == null && !out.has(key)) continue;
    const slot = at(s.item, s.via, i);
    if (!slot.bundles.length && fit != null) slot.width_mm = fit;
    slot.cables.push(s.cable);
  }
  return [...out.values()];
}
// The tie slots each single cable is strapped at, a tray at a time:
// [{cable, item, via, role, face, ties: [index]}]. `role` is where the cable
// is in the rack (`held` or `resting`) and `face` which side of the part
// (`top` or `underside`), as route.js names both. `skip` is the trays a
// cable's bundle already anchors at, by cable id.
function cableSlots(rack, rc, skip = new Map()) {
  const out = [];
  let trays = [];
  try { trays = traysOf(rack, rc); } catch { trays = []; }
  for (const c of rack.cables || []) {
    if (c.straps && c.straps.anchors === false) continue;
    let path = null;
    try { path = routePath(rack, c, rc); } catch { path = null; }
    for (const r of path?.rests || []) {
      if (r.kind !== 'tray' || (skip.get(c.id) || []).includes(`${r.item}|${r.via}`)) continue;
      const t = trays.find(x => x.item === r.item && x.via === r.via);
      if (!t?.ties.length) continue;
      const lies = {cable: c.id, item: r.item, via: r.via, role: r.role, face: r.face};
      if (r.role === 'held') { if (r.ties?.length) out.push({...lies, ties: [...r.ties]}); continue; }
      // its stretch there: the points of its path over a floor of the tray, on
      // it or on the sill of a ring that stands on it
      const ax = t.run === 'z' ? 'z' : 'x';
      const on = path.points.filter(q => q.y > t.top - 1e-6 && q.y < t.top + ON_TRAY_MM
        && t.floors.some(f => q.x >= f.x0 - 1e-6 && q.x <= f.x1 + 1e-6 && q.z >= f.z0 - 1e-6 && q.z <= f.z1 + 1e-6)).map(q => q[ax]);
      if (!on.length) continue;
      const tie = nearestTie(t, (Math.min(...on) + Math.max(...on)) / 2);
      if (tie != null) out.push({...lies, ties: [tie]});
    }
  }
  return out;
}
// THE `straps` TEXT OF THE CABLE SCHEDULE, by cable id: for each tray a
// single cable is strapped at, the tray, the face it lies on by role and by
// name, and the tie slots it passes, counted from 1 ("mgr-1 tray, held face
// (underside), ties 1 to 3"; on a tray turned over, "held face (top)"). It
// names slots and not a count, since one strap at a slot serves every cable
// there. A cable strapped nowhere has no entry; an empty Map without
// `ctx.route`. `nameOf` gives an item's name in the file.
const tiesText = ties => {
  const n = [...new Set(ties)].sort((a, b) => a - b).map(i => i + 1);
  if (n.length === 1) return `tie ${n[0]}`;
  return n.at(-1) - n[0] === n.length - 1 ? `ties ${n[0]} to ${n.at(-1)}` : `ties ${andList(n)}`;
};
export function strapTexts(rack, ctx = {}, nameOf = null) {
  const out = new Map(), rc = ctx?.route;
  if (!rc) return out;
  const label = nameOf || (id => (rack.items || []).find(i => i.id === id)?.label || id);
  const trunk = new Map();
  for (const b of bundlesOf(rack)) if (b.members.length >= 2 && strapKinds(b).anchors)
    for (const m of b.members) trunk.set(m.cable, (b.route || []).filter(w => w.item).map(w => `${w.item}|${w.via}`));
  for (const s of cableSlots(rack, rc, trunk)) {
    const text = `${label(s.item)} ${s.via}, ${s.role === 'held' ? 'held' : 'resting'} face (${s.face}), ${tiesText(s.ties)}`;
    out.set(s.cable, [...(out.get(s.cable) || []), text]);
  }
  return new Map([...out].map(([id, parts]) => [id, parts.join('; ')]));
}
// THE STRAPS A RACK BUYS: {spacing, breakout, anchor, total, widths}. Spacing
// and breakout straps are each bundle's own; anchors are counted by slot.
// `widths` is how many of each width, {19: 12, 12: 2}.
// A DRAWN BUNDLE WHOSE STRAPS COULD NOT BE READ (a reader of the context
// threw, or there are no routes) is left out, never guessed, here and in
// anchorsOf; so the totals can be short of what the rack needs. Then, and only
// then, the result also has `unread`, how many such bundles there are, and
// `unreadBundles`, their ids: a caller that shows the total can say so.
export function strapTotals(rack, ctx = {}) {
  let spacing = 0, breakout = 0, tie = 0;
  const ws = [], unread = [];
  for (const b of bundlesOf(rack)) {
    let st = null;
    try { st = straps(rack, b, ctx); } catch { st = null; }
    if (!st && b.members.length >= 2) unread.push(b.id);
    spacing += st?.kinds.spacing ?? 0; breakout += st?.kinds.breakout ?? 0; tie += st?.kinds.tie ?? 0;
    for (const x of st?.straps || []) if (x.kind !== 'anchor') ws.push(x.width_mm);
  }
  const slots = anchorsOf(rack, ctx);
  for (const x of slots) ws.push(x.width_mm);
  // `tie` (#1017) is there only when a rack has one
  return {spacing, breakout, anchor: slots.length, ...(tie ? {tie} : {}), total: spacing + breakout + tie + slots.length, widths: widthCounts(ws),
          ...(unread.length ? {unread: unread.length, unreadBundles: unread} : {})};
}

// The trunk's length along the rack's own measure, in metres; null when it
// cannot be measured. It is the length of the trunk's own line (trunkLine,
// #1034): the members' routed paths from its first waypoint to its last, as
// the straps are counted along. `straight: true` is added where riders had no
// path and the straight line stood in, and `few: true` where fewer than half
// of a stretch's riders had one: the figure is then an estimate.
export function trunkLength(rack, b, ctx = {}) {
  const L = layoutOf(rack, b, ctx);
  // a tie (#1017) has a trunk of no length: `tie: true`, so a list says "a tie" and not "0 m"
  if (L && isTie(b) && L.trunk.length === 1) return trunkLine(rack, b, L, ctx.route) ? {metres: 0, tie: true} : null;
  if (!L || L.trunk.length < 2) return null;
  const line = trunkLine(rack, b, L, ctx.route);
  return line ? {metres: Math.round(line.length / 10) / 100, ...(line.straight ? {straight: true} : {}), ...(line.few ? {few: true} : {})} : null;
}
