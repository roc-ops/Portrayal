// CABLE ROUTES.
// Pure: the rack, a cable, and a ctx the page fills from the drawings -
//   ctx.chassisOf(ref), ctx.guidesOf(itemId) -> [{via, kind, face, x}],
//     a ring also with its `aperture`, and optionally its `run` ('x', 'y' or
//     'z'; 'x' when not given) and `depth` (mm along the run; RING_DEPTH when
//     not given, and then estimated),
//   ctx.portX(end) -> x or null,
// with every x in RACK coordinates: mm from the rack's centre line, positive
// to the right as seen from the FRONT. This file imports no DOM and nothing of
// the site's pages, so the rack kit can take it as it is.

import {uLabel, zeroUOf, bundlesOf} from './model.js';
import {followTrunk} from './bundle-route.js';
import {RU, OPENING, RAIL_W} from './rails.js';
import {throughRings} from './route-path.js';
import {zeroUOnLane, zeroUX, carriesLane, runsThrough, STANDOFF} from './zero-u.js';
import {isZeroUPart, zeroUSpan} from './fit.js';
import {solidsOf, detour, legCrossings} from './solids.js';

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

// A RING'S PASS (roc-ops/Portrayal#930): a cable goes through a D-ring along
// its run, entering one face and leaving the other, the ring's depth apart.
// RING_DEPTH is the depth taken when a ring states none: ESTIMATED, from the
// two FS rings measured so far, whose bands are 6.8 mm (fs/d-ring-snap-in)
// and 9.9 mm (fs/cmh-5dr1u-ring) thick along the run.
export const RING_DEPTH = 10;
export function ringOf(g) {
  if (g?.kind !== 'ring') return null;
  const stated = typeof g.depth === 'number' && g.depth > 0;
  return {run: ['x', 'y', 'z'].includes(g.run) ? g.run : 'x', depth: stated ? g.depth : RING_DEPTH, estimated: !stated};
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
    // The rings on the way out: from the port toward `side`. A ring behind
    // the port would have the cable enter and leave by one face (#930); a
    // port within half a ring's depth of its centre is under it, and goes
    // through. Stricter than throughRings' side test, which also calls a
    // point steeper than 45 degrees off the run neither side: that would
    // let the automatic route reach back for a ring up to the manager's
    // stand-off behind the port (55 mm on an FHD-CMP5DR), which is the
    // hook it must not draw; every route chosen here passes that test.
    // A ring that runs along x only: one that runs up or across the face is
    // not on the way along the tray.
    const half = g => ringOf(g).depth / 2;
    const out = rings.filter(g => ringOf(g).run === 'x'
                                  && (side === 'left' ? g.x <= portX + half(g) : g.x >= portX - half(g)))
      .sort((a, b) => (side === 'left' ? b.x - a.x : a.x - b.x));
    if (out.length) return out.map(g => ({item: m.id, via: g.via}));
  }
  const duct = gs.find(g => g.kind === 'duct');
  if (duct) return [{item: m.id, via: duct.via}];
  const pass = crossing && gs.find(g => g.kind === 'pass');
  return pass ? [{item: m.id, via: pass.via}] : [];
}

// A PATCH ALONG ONE MANAGER (#949, docs/cable-lay-design.md section 4.1,
// "Local patches"): both ends leave through the same manager on the same face,
// so the cable runs along it port to port, through the rings BETWEEN the two
// ports in order from end a, and never out to a gutter and back. A ring is
// between when its centre is, the ends included: not the half-depth reach of
// `through`, which takes a ring whose centre is just behind a port on the way
// out to a gutter. Here the cable turns toward the other port at once, and a
// ring behind it is a step back the patch does not need (on the owner's rack
// of #949, a leaf port 3.1 mm short of a ring's centre, cabled away from it,
// measured 5.5 cm longer through it, and a stock size). A ring outside the
// stretch is left alone; with no ring between, the cord goes through the one
// ring nearest the middle of its two ports (below), so a manager with a ring
// along x never gives an empty route. A manager with no ring that runs along
// x, but a duct, runs in the duct.
function along(m, pane, ax, bx, ctx, passes = null) {
  const gs = ctx.guidesOf(m.id).filter(g => g.face === pane);
  const rings = gs.filter(g => g.kind === 'ring' && ringOf(g).run === 'x');
  if (rings.length) {
    const lo = Math.min(ax, bx), hi = Math.max(ax, bx);
    const between = rings.filter(g => g.x >= lo && g.x <= hi)
      .sort((p, q) => (ax <= bx ? p.x - q.x : q.x - p.x));
    if (between.length) return between.map(g => ({item: m.id, via: g.via}));
    // NO RING BETWEEN (owner's decision, 2026-10-09): a ring holds the cord
    // even where it does not turn it, so the route is never direct: the ring
    // nearest the middle of the two ports, of two as near the one on end a's
    // side. A ring outside the stretch can be one the cord would enter and
    // leave by one face (#930: both ports on its one side, not steep enough
    // to be under it), which ringFindings reports; so the nearest ring the
    // cord passes through is taken (`passes`, the test routePath makes), and
    // only when none passes, the nearest.
    const mid = (ax + bx) / 2, aSide = Math.sign(ax - mid);
    const order = [...rings].sort((p, q) => Math.abs(p.x - mid) - Math.abs(q.x - mid)
      || aSide * (q.x - p.x));
    const near = order.find(g => passes?.(g)) ?? order[0];
    return [{item: m.id, via: near.via}];
  }
  const duct = gs.find(g => g.kind === 'duct');
  return duct ? [{item: m.id, via: duct.via}] : [];
}

const sameWp = (a, b) => (a.lane ? a.lane === b.lane && a.ru === b.ru : a.item === b.item && a.via === b.via);
const dedupe = list => list.filter((w, i) => i === 0 || !sameWp(w, list[i - 1]));

// The route by the gutter on `side`: out through end a's manager, along the
// lane (across the top when the ends are on two faces), in through end b's.
function byGutter(rack, A, B, mA, mB, side, ctx) {
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

// THE AUTOMATIC ROUTE. Two ends that leave through one manager on one face
// run along it (`along`). Any other route takes a gutter, chosen from BOTH
// ends (section 4.1, "Opposite ways"): when both ports stand on the same side
// of the centre line, that side (a port at the centre counts as left);
// when they stand on opposite sides, the side whose path (routePath, with its
// detours) is the shorter, end a's side on a tie or when either port is not
// found and so cannot be measured.
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
  if (mA && mA === mB && A.pane === B.pane) {
    // whether the cord goes through a ring from port to port, as routePath
    // decides it; unknown (a port not found) counts as through. From the
    // ports, not their plugs' reach points: a reach moves an end along z
    // only, which a ring that runs along x does not count (route-path.js)
    const pa = portPoint(rack, cable.a, ctx), pb = portPoint(rack, cable.b, ctx);
    const passes = g => {
      const p = pointOf(rack, {item: mA.id, via: g.via}, ctx);
      return !(pa && pb && p) || !throughRings([pa, p, pb],
        [null, {...ringOf(g), diameter: cableDiameter(cable, ctx), portBefore: true, portAfter: true}, null]).back.length;
    };
    return along(mA, A.pane, A.x, B.x, ctx, passes);
  }
  const sideOf = x => (x <= 0 ? 'left' : 'right');
  const sA = sideOf(A.x), sB = sideOf(B.x);
  if (sA === sB) return byGutter(rack, A, B, mA, mB, sA, ctx);
  const routes = {[sA]: byGutter(rack, A, B, mA, mB, sA, ctx), [sB]: byGutter(rack, A, B, mA, mB, sB, ctx)};
  // The detours are part of the path (a gutter beside a zero-U PDU can cost
  // the one side 25 cm round it), and measuring them is the dear part, so the
  // side is decided once per rack, context and cable, as solidsOf reads its
  // bodies once per rack and context.
  let per = sideMemo.get(rack);
  if (!per) sideMemo.set(rack, per = new WeakMap());
  let byCable = per.get(ctx);
  if (!byCable) per.set(ctx, byCable = new WeakMap());
  if (!byCable.has(cable)) {
    // Measured as a route edited by hand, so the measure does not come back
    // here; and under an id no bundle holds, so it is the cable's own path.
    const measure = route => pathLength(routePath(rack, {...cable, id: Symbol('side'), route, routeEdited: true}, ctx))?.measured;
    const la = measure(routes[sA]), lb = measure(routes[sB]);
    byCable.set(cable, la == null || lb == null || la <= lb ? sA : sB);
  }
  return routes[byCable.get(cable)];
}
const sideMemo = new WeakMap();

// Does a waypoint still stand for something in this rack?
function resolves(rack, w, ctx) {
  if (w.lane) return lanesOf(rack.frame).includes(w.lane) && w.ru >= 1 && w.ru <= rack.frame.heightRU;
  return !!itemOf(rack, w.item) && ctx.guidesOf(w.item).some(g => g.via === w.via);
}

// A CABLE'S OWN ROUTE: the stored one once edited, else the automatic one. A
// stored waypoint that no longer resolves is skipped, and reported.
export function ownRoute(rack, cable, ctx) {
  const auto = cable.routeEdited !== true;
  const list = auto ? autoRoute(rack, cable, ctx) : (cable.route || []);
  const waypoints = [], gone = [];
  for (const w of list) (resolves(rack, w, ctx) ? waypoints : gone).push(w);
  return {waypoints, gone, auto};
}

// A BUNDLE'S TRUNK as it resolves today: its stored waypoints, less those that
// no longer stand for anything (reported as `gone`, and skipped).
export function trunkRoute(rack, bundle, ctx) {
  const waypoints = [], gone = [];
  for (const w of bundle.route || []) (resolves(rack, w, ctx) ? waypoints : gone).push(w);
  return {waypoints, gone};
}

// The bundle a cable is drawn in: one holding it and at least one other cable
// (a bundle of fewer is kept and listed, but not drawn: #921 decision 5).
export function drawnBundleOf(rack, cableId) {
  return bundlesOf(rack).find(b => b.members.length >= 2 && b.members.some(m => m.cable === cableId)) ?? null;
}

// THE ROUTE A CABLE FOLLOWS. A member of a bundle (#921) follows its own route
// up to where it joins the trunk, the trunk to where it leaves, then its own
// route on to its far port (bundle-route.js followTrunk); the result then also
// names its `bundle`, `join` and `leave`, so a drawing can tell the bundled
// part from the leads. `gone` is the cable's own; a trunk's is the bundle's
// (trunkRoute). Any other cable follows its own route.
export function resolveRoute(rack, cable, ctx) {
  const own = ownRoute(rack, cable, ctx);
  const b = drawnBundleOf(rack, cable.id);
  if (!b) return own;
  const trunk = trunkRoute(rack, b, ctx).waypoints;
  if (!trunk.length) return own;
  const aNearStart = () => {
    const p = portPoint(rack, cable.a, ctx), s = pointOf(rack, trunk[0], ctx), e = pointOf(rack, trunk.at(-1), ctx);
    return !(p && s && e) || dist(p, s) <= dist(p, e);
  };
  const f = followTrunk(own.waypoints, trunk, b.members.find(m => m.cable === cable.id), {aNearStart});
  return {...own, waypoints: f.waypoints, bundle: b.id, join: f.join, leave: f.leave};
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
// WHERE A LANE IS ACROSS THE RACK at a U (#926): the centre line of a zero-U
// part that carries the lane there (a duct standing at that upright); else,
// beside a zero-U part that stands in the gutter and carries no lane (a
// zero-U PDU, #949), the middle of a gutter as wide as the usual one just
// outboard of it; else the middle of the gutter. The route stays {lane, ru};
// only where the lane runs changes, so a length is measured where the cable
// runs.
// WHY OUTBOARD of a PDU, and not inboard or in front: inboard of it is the
// rail and the ears of every device fixed there, so there is no room; in
// front of it (along z) would take the lane off the rail plane every port
// leg and every front-to-back crossing is measured in, and out past the back
// of a rear PDU, outside the rack. Outboard keeps the lane in its own plane,
// beside the PDU, where a cable dresses down the side channel of a real rack.
// A zero-U part standing at that upright at that U that carries no lane: it
// stands in the gutter (against the upright's outer face, STANDOFF 0).
const besideLane = (rack, lane, ru, chassisOf) => zeroUOf(rack).find(z => {
  const c = chassisOf(z.ref);
  if (z.at !== lane || !isZeroUPart(c) || carriesLane(c) || !(Number(c.w) > 0)) return false;
  const [lo, hi] = zeroUSpan(z, chassisOf);
  return ru >= lo && ru <= hi;
}) ?? null;
export function laneXAt(rack, lane, ru, chassisOf) {
  if (typeof chassisOf !== 'function') return laneX(String(lane).split('-')[0]);
  const z = zeroUOnLane(rack, lane, ru, chassisOf);
  if (z) return zeroUX(z, chassisOf);
  const p = besideLane(rack, lane, ru, chassisOf);
  if (!p) return laneX(String(lane).split('-')[0]);
  const s = Math.sign(zeroUX(p, chassisOf)) || -1;
  return s * (OPENING / 2 + RAIL_W + STANDOFF + (Number(chassisOf(p.ref)?.w) || 0) + LANE_GAP / 2);
}
const planeZ = (f, pane) => (pane === 'rear' ? -railDepthOf(f) : 0);

export function pointOf(rack, w, ctx) {
  const f = rack.frame;
  if (w.lane) {
    const [, pane = 'front'] = w.lane.split('-');
    return {x: laneXAt(rack, w.lane, w.ru, ctx?.chassisOf), y: (w.ru - 0.5) * RU, z: planeZ(f, pane)};
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

// THE PLUG'S REACH (#960, docs/cable-lay-design.md section 1.5). A cable
// leaves the far end of its plug, not the port face, and runs straight out
// along the face's normal for the plug's depth before it can turn. So each
// route's first and last leg starts at the REACH POINT: the port's point moved
// out of its face by the plug's reach. The reach, in mm out of the face the
// port is on, is `ctx.plugReachOf(end, cable)` when the page gives a number
// (the far end of the plug seated there, with whatever it seats in: relief.js
// cablePoints' `z`, an optic's standing-out included); else PLUG_REACH by the
// cable's media, the cable's own plug and boot as the library models them
// standing out of the face they seat in:
//   - LC fibre (os2, om3, om4, om5): 27.6, generic/lc-plug@2 (relief `out`
//     12.5) and common/lc-boot@1 (15.1);
//   - copper (cat6, cat6a): 39.4, generic/rj45-plug@1 (13.0) and
//     common/rj45-boot@1 (26.4);
//   - a DAC or an AOC: 68.7, generic/sfp-cable@1, whose cable point is the far
//     end of its stub (head 10.8, strain relief 27.9, stub 30.0: the straight
//     run before the first allowed bend); the longer of the two generic cable
//     ends, generic/qsfp-cable@1 being 64.8, so a default errs long;
//   - a cable whose media is not set, the copper figure, as its diameter takes
//     the copper one (UNSET_D).
// It does not see an optic in a cage: a port that holds one stands the plug
// further out, which only the page knows.
export const PLUG_REACH = {os2: 27.6, om3: 27.6, om4: 27.6, om5: 27.6, cat6: 39.4, cat6a: 39.4, dac: 68.7, aoc: 68.7};
const UNSET_REACH = 39.4;
export function plugReach(cable, end, ctx) {
  let v = null;
  try { v = typeof ctx?.plugReachOf === 'function' ? ctx.plugReachOf(end, cable) : null; } catch { v = null; }
  if (typeof v === 'number' && Number.isFinite(v) && v >= 0) return v;
  return (typeof cable?.media === 'string' && Object.hasOwn(PLUG_REACH, cable.media)) ? PLUG_REACH[cable.media] : UNSET_REACH;
}
// The reach point of an end whose port is at `p`: out of the face its port is
// seen from, +z for the front, -z for the rear, by the plug's reach.
export function reachPoint(rack, end, p, mm) {
  const out = endPane(rack, end) === 'rear' ? -1 : 1;
  return {x: p.x, y: p.y, z: p.z + out * mm};
}

export const STOCK_M = [0.5, 1, 1.5, 2, 3, 5, 7, 10, 15, 20, 30];
// The allowance at each end is the dressing slack a cable is cut with, not
// its plug: the plug is in the path, from the port face to its reach point
// (above), and is counted there once (section 1.5).
export const END_ALLOWANCE_M = 0.15;
export const stockLength = m => STOCK_M.find(s => s >= m - 1e-9) ?? Math.ceil(m / 5) * 5;

// THE PATH A CABLE TAKES, in rack coordinates (mm): its a port, every
// waypoint's point, and its b port, each ring's centre expanded to where the
// cable enters it and where it leaves (throughRings, #930). Each ring's way
// through (`sense`), and whether the cable goes through it at all, is decided
// HERE, once, in the rack's frame. The routed length, fill, capacity, inspect
// and ringFindings read this path; the drawings, which place their points
// from their own pictures, are handed the same decisions (ringMarks) and
// obey them, so what is drawn is what is measured and counted.
// Returns
//   {points: [{x, y, z, at, item?, via?}], rings, findings, marks}
// - `at` is 'a' or 'b' (a port), 'reach' (the far end of that port's plug,
//   with `end` 'a' or 'b', section 1.5: the route's first and last legs start
//   there), 'entry', 'exit' or 'face' (a ring),
//   'pathway' (a duct or a pass-through) or 'lane';
// - `rings`: per ring on the route, {item, via, run, depth, estimated,
//   passed, sense, entry, exit} (sense +1 or -1 along the run; a ring not
//   passed has `face` instead of entry and exit; one that holds a cable
//   reaching just into it, route-path.js HELD, is passed and `held: true`);
// - `findings`: a ring the route would enter and leave by one face, as
//   {kind: 'doubles-back', cable, item, via};
// - `marks`: parallel to resolveRoute's waypoints, null for a lane, a duct or
//   a pass, and for a ring {run, depth, sense, back}: what a drawing passes
//   to routed2d or routePoints3d (ringMarks);
// - `crossings`: each solid body a leg of the path still crosses (#949,
//   docs/cable-lay-design.md section 1), as {kind: 'crosses-body', cable,
//   item, part, between: [from, to], at: [x, y, z]}: `from` and `to` are the
//   waypoints the leg lies between ({end: 'a'} or 'b' for a port), `at` where
//   it enters the body, in mm;
// - `detours`: per leg that was taken round a body, {between: [from, to],
//   points}.
// DETOURS (section 1.3): where a straight leg between two points would cross
// a solid (solids.js solidsOf), points are added that take it round, over the
// near edge first, then round the end, then by a side lane (solids.js
// detour). They are computed, never stored, and they are in `points`
// (`at: 'detour'`), so the length counts them. A leg the rules cannot clear
// is left as drawn and is in `crossings`. The cable's diameter, which a
// pass-through must fit and a detour keeps clear by, is `ctx.diameterOf(cable)`
// when the page gives it, else its media's typical one (DIAMETERS).
// null when either port is not found on its drawing, as for routedLength.
export function routePath(rack, cable, ctx) {
  const a = portPoint(rack, cable.a, ctx), b = portPoint(rack, cable.b, ctx);
  if (!a || !b) return null;
  // each port, then its plug's reach point (section 1.5): the first and last
  // legs of the route start there; a plug of no reach adds no point
  const ra = plugReach(cable, cable.a, ctx), rb = plugReach(cable, cable.b, ctx);
  const stops = [{p: a, at: 'a'}];
  if (ra > 0) stops.push({p: reachPoint(rack, cable.a, a, ra), at: 'reach', end: 'a'});
  const wps = resolveRoute(rack, cable, ctx).waypoints;
  const marks = wps.map(() => null);
  wps.forEach((w, i) => {
    const p = pointOf(rack, w, ctx);
    if (!p) return;
    const g = w.lane ? null : ctx.guidesOf(w.item).find(x => x.via === w.via);
    stops.push({p, w, i, ring: ringOf(g)});
  });
  if (rb > 0) stops.push({p: reachPoint(rack, cable.b, b, rb), at: 'reach', end: 'b'});
  stops.push({p: b, at: 'b'});
  // a ring holds a cable that reaches just into it (route-path.js, HELD):
  // how near depends on the cable's diameter, and it holds only from a port:
  // the port stops and their reach points are the only stops without `w`, so
  // `!stops[k ± 1].w` says the neighbour is a port's (a ring is never first or
  // last, so both neighbours exist)
  const held = cableDiameter(cable, ctx);
  const {points, passes, back} = throughRings(stops.map(s => s.p), stops.map((s, k) => (s.ring
    ? {...s.ring, diameter: held, portBefore: !stops[k - 1].w, portAfter: !stops[k + 1].w} : null)));
  // Label each point with what it is: walk the stops, a ring taking two points when passed.
  const passAt = new Map(passes.map(x => [x.index, x])), backAt = new Map(back.map(x => [x.index, x]));
  const out = [], rings = [], findings = [], from = [];
  let n = 0;
  stops.forEach((s, k) => {
    const tag = s.w ? (s.w.lane ? {at: 'lane'} : {item: s.w.item, via: s.w.via}) : {at: s.at, ...(s.end ? {end: s.end} : {})};
    if (!s.ring) { from.push(k); out.push({...points[n++], ...(s.w && !s.w.lane ? {at: 'pathway'} : {}), ...tag}); return; }
    const ring = {item: s.w.item, via: s.w.via, ...s.ring};
    const pass = passAt.get(k);
    if (pass) {
      from.push(k, k);
      out.push({...points[n++], ...tag, at: 'entry'}, {...points[n++], ...tag, at: 'exit'});
      rings.push({...ring, passed: true, ...(pass.held ? {held: true} : {}), sense: pass.sense, entry: pass.entry, exit: pass.exit});
      marks[s.i] = {run: s.ring.run, depth: s.ring.depth, sense: pass.sense, back: false};
    } else {
      const no = backAt.get(k);
      from.push(k);
      out.push({...points[n++], ...tag, at: 'face'});
      rings.push({...ring, passed: false, sense: no.sense, face: points[n - 1]});
      marks[s.i] = {run: s.ring.run, depth: s.ring.depth, sense: no.sense, back: true};
      findings.push({kind: 'doubles-back', cable: cable.id, item: s.w.item, via: s.w.via});
    }
  });
  // Round the solid bodies (section 1.3), then what still crosses one (1.4).
  const solids = solidsOf(rack, ctx);
  const diameter = cableDiameter(cable, ctx);
  // the side lanes at a height, where laneXAt puts them (rule 3 of 1.3)
  const lanesAt = y => {
    const ru = Math.max(1, Math.min(rack.frame.heightRU, Math.floor(y / RU) + 1));
    return [...new Set(lanesOf(rack.frame).map(l => laneXAt(rack, l, ru, ctx?.chassisOf)))];
  };
  const ref = k => (stops[k].w ? (stops[k].w.lane ? {lane: stops[k].w.lane, ru: stops[k].w.ru} : {item: stops[k].w.item, via: stops[k].w.via})
    : {end: stops[k].end ?? stops[k].at});
  const final = [out[0]], legs = [], detours = [];
  for (let k = 1; k < out.length; k++) {
    const between = [ref(from[k - 1]), ref(from[k])];
    const extra = solids.length ? detour(out[k - 1], out[k], solids, {diameter, lanes: lanesAt}) : [];
    if (extra?.length) {
      detours.push({between, points: extra.map(p => ({x: p.x, y: p.y, z: p.z}))});
      for (const p of extra) { legs.push(between); final.push({x: p.x, y: p.y, z: p.z, at: 'detour'}); }
    }
    legs.push(between);
    final.push(out[k]);
  }
  const crossings = [];
  const r1 = v => Math.round(v * 10) / 10;
  for (let k = 1; k < final.length && solids.length; k++) {
    for (const x of legCrossings(final[k - 1], final[k], solids, {diameter})) {
      const dup = crossings.some(c => c.item === x.solid.item && c.part === x.solid.part
        && JSON.stringify(c.between) === JSON.stringify(legs[k - 1]));
      if (!dup) crossings.push({kind: 'crosses-body', cable: cable.id, item: x.solid.item, part: x.solid.part,
        between: legs[k - 1], at: [r1(x.at.x), r1(x.at.y), r1(x.at.z)]});
    }
  }
  return {points: final, rings, findings, marks, crossings, detours};
}

// A cable's outside diameter in mm, for what it must fit and keep clear by:
// the page's `ctx.diameterOf(cable)` (the cable types table, #919: its
// diameterLookup), else its media's typical one.
const cableDiameter = (cable, ctx) => {
  const d = typeof ctx?.diameterOf === 'function' ? ctx.diameterOf(cable) : null;
  return typeof d === 'number' && d > 0 ? d : DIAMETERS[cable?.media] ?? UNSET_D;
};

// The marks of a path drawn from its other end, for its points reversed: the
// list reversed, and each ring passed turned to the other sense. A ring not
// passed keeps its sense, which names the face both its neighbours are on.
export const reverseMarks = marks => [...marks].reverse()
  .map(m => (m && (m.sense === 1 || m.sense === -1) && m.back !== true ? {...m, sense: -m.sense} : m));

// MARKS FOR A DRAWING'S OWN AXES. A mark's `sense` is along the rack's axes:
// x right as seen from the front, y up, z out of the front. A drawing whose
// axis runs the other way says so, and each ring on that axis, passed or
// doubled back, has its sense turned: an SVG elevation has y down ({y: -1});
// the rear pane is also seen mirrored ({x: -1, y: -1}); the 3D scene is in
// the rack's own axes and passes its marks unchanged.
export const orientMarks = (marks, flip = {}) => marks.map(m => (m && (m.sense === 1 || m.sense === -1)
  && flip[m.run] === -1 ? {...m, sense: -m.sense} : m));

// THE RING MARKS A DRAWING PASSES ON, parallel to resolveRoute(rack, cable,
// ctx).waypoints: null for a lane, a duct or a pass-through, and for a ring
// routePath's decision, {run, depth, sense, back}, in the rack's axes (a
// drawing that flips one passes them through orientMarks). Drop them in step
// with any waypoint the drawing cannot place. When a port is not found there is no
// decision, and a ring's mark is {run, depth} alone: the drawing then decides
// it from its own points.
export function ringMarks(rack, cable, ctx) {
  const path = routePath(rack, cable, ctx);
  if (path) return path.marks;
  return resolveRoute(rack, cable, ctx).waypoints.map(w => {
    const g = w.lane ? null : ringOf(ctx.guidesOf(w.item).find(x => x.via === w.via));
    return g ? {run: g.run, depth: g.depth} : null;
  });
}

// A path's length, as routedLength gives it: {measured, value} in metres.
export function pathLength(path) {
  if (!path) return null;
  const pts = path.points;
  let mm = 0;
  for (let k = 1; k < pts.length; k++) mm += dist(pts[k - 1], pts[k]);
  const measured = mm / 1000 + 2 * END_ALLOWANCE_M;
  return {measured, value: stockLength(measured)};
}
export const routedLength = (rack, cable, ctx) => pathLength(routePath(rack, cable, ctx));

// Every ring a cable's route would enter and leave by one face, rack-wide,
// with a sentence for each: what the page and an agent report. A cable whose
// port is not found is not judged.
export function ringFindings(rack, ctx, nameOf = id => id) {
  return (rack.cables || []).flatMap(c => (routePath(rack, c, ctx)?.findings || []).map(f => ({...f,
    text: `${c.id} would enter and leave ${nameOf(f.item)} ${/^guide-(\d+)$/.test(f.via) ? `ring ${f.via.slice(6)}` : f.via} by the same face: route it through the ring, or past it.`})));
}

// A word for a part of a body, as a finding names it.
function partText(part) {
  const p = String(part || '');
  if (p === 'envelope' || p === 'body' || !p) return '';
  return p.split('/')[0].replace(/--.*$/, '').replace(/-/g, ' ');
}
// A plate a cable meets from above or below: thinner in y than across.
const isFloor = box => (box.y1 - box.y0) <= Math.min(box.x1 - box.x0, box.z1 - box.z0);

// EVERY BODY A CABLE'S PATH STILL CROSSES (#949, docs/cable-lay-design.md
// section 1.4), rack-wide, after the detours: routePath's `crossings`, each
// with a sentence. It warns and never refuses, as fill, size and bend do: a
// device moving can make a route cross something without any cable command.
// A cable whose port is not found is not judged. `nameOf(itemId)` names an
// item or a zero-U part.
export function bodyFindings(rack, ctx, nameOf = id => id) {
  const solids = solidsOf(rack, ctx);
  const lab = (w, c) => (w.end ? `its port on ${nameOf((w.end === 'a' ? c.a : c.b).item)}`
    : w.lane ? `${w.lane} U${uLabel(rack.frame, w.ru)}`
    : `${nameOf(w.item)} ${/^guide-(\d+)$/.test(w.via) ? `ring ${w.via.slice(6)}` : w.via}`);
  return (rack.cables || []).flatMap(c => (routePath(rack, c, ctx)?.crossings || []).map(f => {
    const s = solids.find(x => x.item === f.item && x.part === f.part);
    const body = [nameOf(f.item), partText(f.part)].filter(Boolean).join(' ');
    const [a, b] = f.between.map(w => lab(w, c));
    const holes = (s?.holes || []).map(h => h.via);
    // a plate met from above or below: the way round is over its front edge,
    // onto the face the cable rests on
    const advice = s && isFloor(s.box) && f.part !== 'envelope'
      ? `route it over the front edge of the ${partText(f.part) || 'plate'}, or through a ring`
      : holes.length ? `route it round ${nameOf(f.item)}, or through ${holes.join(' or ')} if the cable fits`
      : `route it round ${nameOf(f.item)}, or through a ring or a pass-through it fits`;
    const where = a === b ? `at ${a}` : `between ${a} and ${b}`;
    return {...f, text: `${c.id} passes through ${body} ${where}: ${advice}.`};
  }));
}

// ── fill ──────────────────────────────────────────────────────────────────
// Typical outside diameters (mm): a sketch of fill, not a measurement.
export const DIAMETERS = {cat6: 6.0, cat6a: 7.5, os2: 3.0, om3: 3.0, om4: 3.0, om5: 3.0, dac: 5.0, aoc: 3.0};
const UNSET_D = 6.0;
export const FILL_LIMIT = 0.4;
const areaOf = media => Math.PI * ((DIAMETERS[media] ?? UNSET_D) / 2) ** 2;

// Every pathway with an aperture that a cable passes through, filled against
// FILL_LIMIT of its opening. Lanes have no limit and are not listed.
// A ring counts the cables that pass through it (routePath): one a route
// would take to its face and back is a finding (ringFindings), not a member.
// A ZERO-U PART that carries a lane (#926) is a pathway too: every cable
// whose route runs on its lane through a U it spans counts once, against
// FILL_LIMIT of its channel, `ctx.zeroUAperture(entry)` -> {w, h} mm, or null
// when the drawing does not say (and then it is not listed). Its entry has the
// part's id as `item`, its first guide as `via`, and `zeroU: true`.
export function fill(rack, ctx) {
  const at = new Map();
  for (const c of rack.cables || []) {
    const path = routePath(rack, c, ctx);
    const notThrough = new Set((path?.findings || []).map(f => `${f.item}|${f.via}`));
    for (const w of resolveRoute(rack, c, ctx).waypoints) {
      if (w.lane || notThrough.has(`${w.item}|${w.via}`)) continue;
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
  const filled = e => Math.round(e.area / (FILL_LIMIT * e.aperture.w * e.aperture.h) * 100);
  const items = [...at.values()].map(e => {
    const percent = filled(e);
    return {item: e.item, via: e.via, count: e.cables.length, percent, over: percent > 100, cables: e.cables};
  });
  const beside = zeroUThrough(rack, ctx).flatMap(({z, c, cables}) => {
    const ap = typeof ctx.zeroUAperture === 'function' ? ctx.zeroUAperture(z) : null;
    if (!(ap?.w > 0 && ap?.h > 0)) return [];
    const percent = filled({aperture: ap, area: cables.reduce((a, x) => a + areaOf(x.media), 0)});
    const via = Object.values(c.guides || {}).flat()[0] ?? 'duct';
    return [{item: z.id, via, count: cables.length, percent, over: percent > 100, cables: cables.map(x => x.id), zeroU: true}];
  });
  return [...items, ...beside];
}

// The zero-U parts that carry a lane, each with the cables whose routes run
// through it, in rack order; a part no cable runs through is left out.
function zeroUThrough(rack, ctx) {
  const parts = zeroUOf(rack).map(z => ({z, c: ctx.chassisOf(z.ref)})).filter(({c}) => carriesLane(c));
  if (!parts.length) return [];
  const routes = (rack.cables || []).map(c => [c, resolveRoute(rack, c, ctx).waypoints]);
  return parts
    .map(({z, c}) => ({z, c, cables: routes.filter(([, ws]) => runsThrough(ws, z, ctx.chassisOf)).map(([cable]) => cable)}))
    .filter(x => x.cables.length);
}

// Managers whose stated capacity the cables through them exceed. As in fill,
// a ring a cable only doubles back from does not carry it.
export function capacityOver(rack, ctx) {
  const by = new Map();
  for (const c of rack.cables || []) {
    const notThrough = new Set((routePath(rack, c, ctx)?.findings || []).map(f => `${f.item}|${f.via}`));
    for (const w of resolveRoute(rack, c, ctx).waypoints)
      if (w.item && !notThrough.has(`${w.item}|${w.via}`)) (by.get(w.item) || by.set(w.item, new Set()).get(w.item)).add(c.id);
  }
  const out = [];
  for (const [item, set] of by) {
    const cap = ctx.chassisOf(itemOf(rack, item)?.ref)?.capacity?.count;
    if (cap && set.size > cap) out.push({item, count: set.size, capacity: cap});
  }
  // a zero-U part that carries a lane, against its own stated capacity (#926)
  for (const {z, c, cables} of zeroUThrough(rack, ctx)) {
    const cap = c.capacity?.count;
    if (cap && cables.length > cap) out.push({item: z.id, count: cables.length, capacity: cap, zeroU: true});
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
