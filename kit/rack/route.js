// CABLE ROUTES.
// Pure: the rack, a cable, and a ctx the page fills from the drawings -
//   ctx.chassisOf(ref), ctx.guidesOf(itemId) -> [{via, kind, face, x}],
//   ctx.portX(end) -> x or null,
// with every x in RACK coordinates: mm from the rack's centre line, positive
// to the right as seen from the FRONT. This file imports no DOM and nothing of
// the site's pages, so the rack kit can take it as it is.

import {uLabel} from './model.js';
import {RU, OPENING, RAIL_W} from './rails.js';

export const LANE_GAP = 40;          // mm: a lane runs in the middle of a 40 mm gutter outside each rail
const SHORT = 2;                     // U: a jumper this close, with no manager, just hangs

export const lanesOf = frame => (frame.kind === 'two-post'
  ? ['left', 'right'] : ['left-front', 'right-front', 'left-rear', 'right-rear']);
// The rings, ducts and pass-throughs a device offers a route, as rack.json lists
// them per view: one sorted list of ids, whatever the view.
export const pathwaysOf = chassis =>
  [...new Set(['guides', 'passes'].flatMap(k => Object.values(chassis?.[k] || {}).flat()))].sort();
const laneFor = (frame, side, pane) => (frame.kind === 'two-post' ? side : `${side}-${pane}`);
const itemOf = (rack, id) => rack.items.find(i => i.id === id) || null;

// Which face an end's port is seen from: its item's face, or the other one
// for the panel that faces away (a turned item swaps the two).
// Mirrors cable-rules.js paneOf, duplicated so this file stays kit-ready.
export function endPane(rack, end) {
  const it = itemOf(rack, end.item);
  if (!it) return null;
  const outward = (end.view === 'rear') === !!it.turned;
  return outward ? it.face : (it.face === 'front' ? 'rear' : 'front');
}

const unitsOf = (ctx, it) => Math.max(1, ctx.chassisOf(it.ref)?.ru ?? 1);
const spans = (ctx, it, u) => u >= it.ru && u <= it.ru + unitsOf(ctx, it) - 1;

// The manager an end leaves through, in order: one hosted on its item on that
// face; else, of the 1U devices adjacent on that face (ABOVE first, then
// BELOW), the first with a manager hosted on it on that face, else itself if it
// declares guides on that face. A manager must declare guides on that face.
// null when there is none.
function managerOf(rack, it, pane, ctx) {
  const guided = m => ctx.guidesOf(m.id).some(g => g.face === pane);
  const hosted = rack.items.find(m => m.on === it.id && m.face === pane && guided(m));
  if (hosted) return hosted;
  for (const u of [it.ru + unitsOf(ctx, it), it.ru - 1]) {
    for (const o of rack.items.filter(o => o.id !== it.id && o.face === pane && !o.on
                                           && unitsOf(ctx, o) === 1 && spans(ctx, o, u))) {
      const carried = rack.items.find(m => m.on === o.id && m.face === pane && guided(m));
      if (carried) return carried;
      if (guided(o)) return o;
    }
  }
  return null;
}

// The waypoints through one end's manager, from the port out to `side`.
function through(m, pane, portX, side, crossing, ctx) {
  if (!m) return [];
  const gs = ctx.guidesOf(m.id).filter(g => g.face === pane);
  const rings = gs.filter(g => g.kind === 'ring');
  if (rings.length) {
    const near = rings.reduce((a, b) => (Math.abs(b.x - portX) < Math.abs(a.x - portX) ? b : a));
    const out = rings.filter(g => (side === 'left' ? g.x <= near.x : g.x >= near.x))
      .sort((a, b) => (side === 'left' ? b.x - a.x : a.x - b.x));
    return out.map(g => ({item: m.id, via: g.via}));
  }
  const duct = gs.find(g => g.kind === 'duct');
  if (duct) return [{item: m.id, via: duct.via}];
  const pass = crossing && gs.find(g => g.kind === 'pass');
  return pass ? [{item: m.id, via: pass.via}] : [];
}

const sameWp = (a, b) => (a.lane ? a.lane === b.lane && a.ru === b.ru : a.item === b.item && a.via === b.via);
const dedupe = list => list.filter((w, i) => i === 0 || !sameWp(w, list[i - 1]));

export function autoRoute(rack, cable, ctx) {
  const ends = [cable.a, cable.b].map(e => {
    const it = itemOf(rack, e.item), pane = it && endPane(rack, e);
    // A port not found only defaults the SIDE (to the left, as a port at the centre does);
    // no length is ever measured from it (portPoint).
    return it && pane ? {e, it, pane, x: ctx.portX(e) ?? 0} : null;
  });
  if (ends.some(x => !x)) return [];
  const [A, B] = ends;
  const mA = managerOf(rack, A.it, A.pane, ctx), mB = managerOf(rack, B.it, B.pane, ctx);
  if (!mA && !mB && A.pane === B.pane && Math.abs(A.it.ru - B.it.ru) <= SHORT) return [];
  const side = A.x <= 0 ? 'left' : 'right';
  const crossing = A.pane !== B.pane;
  const f = rack.frame;
  const laneA = laneFor(f, side, A.pane), laneB = laneFor(f, side, B.pane);
  const lanes = laneA === laneB
    ? [{lane: laneA, ru: A.it.ru}, {lane: laneA, ru: B.it.ru}]
    : (() => { const top = Math.max(A.it.ru, B.it.ru);
        return [{lane: laneA, ru: A.it.ru}, {lane: laneA, ru: top}, {lane: laneB, ru: top}, {lane: laneB, ru: B.it.ru}]; })();
  const outA = through(mA, A.pane, A.x, side, crossing, ctx);
  const outB = through(mB, B.pane, B.x, side, crossing, ctx).reverse();
  return dedupe([...outA, ...lanes, ...outB]);
}

// Does a waypoint still stand for something in this rack?
function resolves(rack, w, ctx) {
  if (w.lane) return lanesOf(rack.frame).includes(w.lane) && w.ru >= 1 && w.ru <= rack.frame.heightRU;
  return !!itemOf(rack, w.item) && ctx.guidesOf(w.item).some(g => g.via === w.via);
}

// THE ROUTE A CABLE FOLLOWS: the stored one once edited, else the automatic
// one. A stored waypoint that no longer resolves is skipped, and reported.
export function resolveRoute(rack, cable, ctx) {
  const auto = cable.routeEdited !== true;
  const list = auto ? autoRoute(rack, cable, ctx) : (cable.route || []);
  const waypoints = [], gone = [];
  for (const w of list) (resolves(rack, w, ctx) ? waypoints : gone).push(w);
  return {waypoints, gone, auto};
}

// The route as a line of text: "mgr-1 ring 3 > left-front U12-U24 > ...".
// Consecutive points on one lane read as one run. `nameOf(itemId)` names an item.
// U's are as stored; pass `frame` to label them the way the rack counts.
export function routeText(route, nameOf = id => id, frame = null) {
  const u = n => (frame ? uLabel(frame, n) : n);
  const viaText = v => (/^guide-(\d+)$/.test(v) ? `ring ${v.slice(6)}` : v);
  const out = [];
  for (const w of route) {
    const last = out[out.length - 1];
    if (w.lane && last?.lane === w.lane) { last.to = w.ru; continue; }
    out.push(w.lane ? {lane: w.lane, from: w.ru, to: w.ru} : {text: `${nameOf(w.item)} ${viaText(w.via)}`});
  }
  return out.map(p => (p.lane ? `${p.lane} U${u(p.from)}${p.to !== p.from ? `-U${u(p.to)}` : ''}` : p.text)).join(' > ');
}

// ── geometry, in rack coordinates (mm) ────────────────────────────────────
// x from the centre line, right as seen from the front; y up from the floor of
// U1; z 0 on the front rail plane, negative toward the rear. The page's 2D and
// 3D draw from their own drawings; this is the rack's own measure, so the
// length is the same whatever is on screen.
const railDepthOf = f => (f.kind === 'two-post' ? 0 : f.railDepth);
export const laneX = side => (side === 'left' ? -1 : 1) * (OPENING / 2 + RAIL_W + LANE_GAP / 2);
const planeZ = (f, pane) => (pane === 'rear' ? -railDepthOf(f) : 0);

export function pointOf(rack, w, ctx) {
  const f = rack.frame;
  if (w.lane) {
    const [side, pane = 'front'] = w.lane.split('-');
    return {x: laneX(side), y: (w.ru - 0.5) * RU, z: planeZ(f, pane)};
  }
  const it = itemOf(rack, w.item), g = it && ctx.guidesOf(it.id).find(x => x.via === w.via);
  if (!g) return null;
  // A rack-face part stands out from its rail plane by half its depth; a rack
  // device's guide is on its face, at the rail plane.
  const c = ctx.chassisOf(it.ref) || {};
  // A guide on a rack device's FAR panel is the chassis depth in, as portPoint puts a port there.
  const out = c.mount === 'rack-face' ? (c.d ?? 0) / 2 : 0;
  const far = c.mount !== 'rack-face' && g.face !== it.face;
  const d = c.d ?? 0;
  const z = far ? (it.face === 'front' ? -d : -railDepthOf(f) + d)
    : g.face === 'rear' ? planeZ(f, 'rear') - out : planeZ(f, 'front') + out;
  return {x: g.x, y: (it.ru - 0.5) * RU, z};
}

export function portPoint(rack, end, ctx) {
  const it = itemOf(rack, end.item), pane = it && endPane(rack, end);
  if (!pane) return null;
  // No port found on the drawing: no point, and so no length - never an invented x of 0.
  const x = ctx.portX(end);
  if (x == null) return null;
  const f = rack.frame, d = ctx.chassisOf(it.ref)?.d ?? 0;
  // On its own face a panel is at that rail; the far panel is the chassis depth away.
  const z = pane === it.face ? planeZ(f, pane) : (it.face === 'front' ? -d : -railDepthOf(f) + d);
  return {x, y: ctx.portY?.(end) ?? (it.ru - 0.5) * RU, z};
}

const dist = (p, q) => Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);

export const STOCK_M = [0.5, 1, 1.5, 2, 3, 5, 7, 10, 15, 20, 30];
export const END_ALLOWANCE_M = 0.15;
export const stockLength = m => STOCK_M.find(s => s >= m - 1e-9) ?? Math.ceil(m / 5) * 5;

export function routedLength(rack, cable, ctx) {
  const a = portPoint(rack, cable.a, ctx), b = portPoint(rack, cable.b, ctx);
  if (!a || !b) return null;
  const mids = resolveRoute(rack, cable, ctx).waypoints.map(w => pointOf(rack, w, ctx)).filter(Boolean);
  const pts = [a, ...mids, b];
  let mm = 0;
  for (let k = 1; k < pts.length; k++) mm += dist(pts[k - 1], pts[k]);
  const measured = mm / 1000 + 2 * END_ALLOWANCE_M;
  return {measured, value: stockLength(measured)};
}

// ── fill ──────────────────────────────────────────────────────────────────
// Typical outside diameters (mm): a sketch of fill, not a measurement.
export const DIAMETERS = {cat6: 6.0, cat6a: 7.5, os2: 3.0, om3: 3.0, om4: 3.0, om5: 3.0, dac: 5.0, aoc: 3.0};
const UNSET_D = 6.0;
export const FILL_LIMIT = 0.4;
const areaOf = media => Math.PI * ((DIAMETERS[media] ?? UNSET_D) / 2) ** 2;

// Every pathway with an aperture that a cable passes through, filled against
// FILL_LIMIT of its opening. Lanes have no limit and are not listed.
export function fill(rack, ctx) {
  const at = new Map();
  for (const c of rack.cables || []) {
    for (const w of resolveRoute(rack, c, ctx).waypoints) {
      if (w.lane) continue;
      const g = ctx.guidesOf(w.item).find(x => x.via === w.via);
      if (!g?.aperture) continue;
      const key = `${w.item}|${w.via}`;
      const e = at.get(key) || {item: w.item, via: w.via, aperture: g.aperture, area: 0, cables: []};
      if (e.cables.includes(c.id)) continue;
      e.area += areaOf(c.media);
      e.cables.push(c.id);
      at.set(key, e);
    }
  }
  return [...at.values()].map(e => {
    const percent = Math.round(e.area / (FILL_LIMIT * e.aperture.w * e.aperture.h) * 100);
    return {item: e.item, via: e.via, count: e.cables.length, percent, over: percent > 100, cables: e.cables};
  });
}

// Managers whose stated capacity the cables through them exceed.
export function capacityOver(rack, ctx) {
  const by = new Map();
  for (const c of rack.cables || [])
    for (const w of resolveRoute(rack, c, ctx).waypoints)
      if (w.item) (by.get(w.item) || by.set(w.item, new Set()).get(w.item)).add(c.id);
  const out = [];
  for (const [item, set] of by) {
    const cap = ctx.chassisOf(itemOf(rack, item)?.ref)?.capacity?.count;
    if (cap && set.size > cap) out.push({item, count: set.size, capacity: cap});
  }
  return out;
}

// ── keeping routed lengths current ────────────────────────────────────────
// A cable with no length, or a routed one, gets the length its route measures;
// an entered length is the user's and is never touched, nor is one the user
// wrote that the page could not read (lengthAsWritten): that intent wins. Returns the same rack
// when nothing changed, so the page can tell whether to save.
export function withRoutedLengths(rack, ctx) {
  let changed = false;
  const cables = (rack.cables || []).map(c => {
    if (c.lengthAsWritten != null || (c.length && c.length.source !== 'routed')) return c;
    const got = routedLength(rack, c, ctx);
    if (!got) return c;
    const measured = Math.round(got.measured * 100) / 100;
    if (c.length?.value === got.value && c.length?.measured === measured) return c;
    changed = true;
    return {...c, length: {value: got.value, unit: 'm', source: 'routed', measured}};
  });
  return changed ? {...rack, cables} : rack;
}
