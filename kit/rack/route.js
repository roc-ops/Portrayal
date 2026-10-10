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
import {throughRings, cornersOf, STRAIGHT_DEG} from './route-path.js';
import {zeroUOnLane, zeroUX, carriesLane, runsThrough, STANDOFF} from './zero-u.js';
import {isZeroUPart, zeroUSpan} from './fit.js';
import {solidsOf, traysOf, detour, legCrossings, CLEAR} from './solids.js';
import {surfacesOf, hang, heldStretch, drapeOf, bendOf, newCrossing} from './resting.js';

export const LANE_GAP = 40;          // mm: a lane runs in the middle of a 40 mm gutter outside each rail
const SHORT = 2;                     // U: a jumper this close, with no manager, just hangs

export const lanesOf = frame => (frame.kind === 'two-post'
  ? ['left', 'right'] : ['left-front', 'right-front', 'left-rear', 'right-rear']);
// The rings, ducts, pass-throughs and trays a device offers a route, as
// rack.json lists them (guides and passes per view, trays by id): one sorted
// list of ids, whatever the view. A tray's id shares the namespace of the
// others (docs/cable-lay-design.md section 2.1), so `{item, via}` names it.
export const pathwaysOf = chassis =>
  [...new Set([...['guides', 'passes'].flatMap(k => Object.values(chassis?.[k] || {}).flat()),
    ...(Array.isArray(chassis?.trays) ? chassis.trays.map(t => t?.id).filter(v => typeof v === 'string') : [])])].sort();
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
    // within a micron is a tie: a mirrored pair of paths that sag (#949 step
    // 3) can measure apart in the last bits of a float
    byCable.set(cable, la == null || lb == null || la <= lb + 1e-6 ? sA : sB);
  }
  return routes[byCable.get(cable)];
}
const sideMemo = new WeakMap();
// where each cable's turns were given room (routePath), per rack and context
const roomMemo = new WeakMap();

// Does a waypoint still stand for something in this rack? A guide the page
// reads off the drawings, or a tray the catalogue lists.
function resolves(rack, w, ctx) {
  if (w.lane) return lanesOf(rack.frame).includes(w.lane) && w.ru >= 1 && w.ru <= rack.frame.heightRU;
  return !!itemOf(rack, w.item) && (ctx.guidesOf(w.item).some(g => g.via === w.via) || !!trayOf(rack, w, ctx));
}

// THE TRAY A WAYPOINT NAMES (docs/cable-lay-design.md section 2.1), placed
// (solids.js traysOf), or null. A ring or a duct of the same id wins: the
// namespace is one, and lint holds an id to one pathway (L170).
export const trayOf = (rack, w, ctx) => (w?.item && !w.lane
  ? traysOf(rack, ctx).find(t => t.item === w.item && t.via === w.via) ?? null : null);

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
  if (!g) {
    // a tray: the middle of its largest floor rectangle, on its upward face
    const t = it && trayOf(rack, w, ctx);
    if (!t) return null;
    const f = t.floors.reduce((m, b) => ((b.x1 - b.x0) * (b.z1 - b.z0) > (m.x1 - m.x0) * (m.z1 - m.z0) ? b : m));
    return {x: (f.x0 + f.x1) / 2, y: t.top, z: (f.z0 + f.z1) / 2};
  }
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
//     common/rj45-boot@1 (26.4). It assumes the boot abuts the plug's rear;
//     an overlapping boot reaches less (the boot's 11.9 x 8.13 opening slides
//     over the 11.68 x 7.93 plug body, so this likely errs long by a few mm);
//   - a DAC or an AOC: 64.8, generic/qsfp-cable@1, whose cable point is the
//     far end of its stub (head 19.8, strain relief 15, stub 30: the straight
//     run before the first allowed bend), the stub from a drawing. Not
//     generic/sfp-cable@1's 68.7: its stub rests on an estimated reading;
//   - a cable whose media is not set, the copper figure, as its diameter takes
//     the copper one (UNSET_D).
// It does not see an optic in a cage: a port that holds one stands the plug
// further out, which only the page knows.
export const PLUG_REACH = {os2: 27.6, om3: 27.6, om4: 27.6, om5: 27.6, cat6: 39.4, cat6a: 39.4, dac: 64.8, aoc: 64.8};
const UNSET_REACH = 39.4;
function plugReach(cable, end, ctx) {
  let v = null;
  try { v = typeof ctx?.plugReachOf === 'function' ? ctx.plugReachOf(end, cable) : null; } catch { v = null; }
  if (typeof v === 'number' && Number.isFinite(v) && v >= 0) return v;
  return (typeof cable?.media === 'string' && Object.hasOwn(PLUG_REACH, cable.media)) ? PLUG_REACH[cable.media] : UNSET_REACH;
}
// The reach point of an end whose port is at `p`: out of the face its port is
// seen from, +z for the front, -z for the rear, by the plug's reach.
function reachPoint(rack, end, p, mm) {
  const out = endPane(rack, end) === 'rear' ? -1 : 1;
  return {x: p.x, y: p.y, z: p.z + out * mm};
}

// THE LARGEST RADIUS A LAY IS OPENED OUT FOR (#973), mm: approach points,
// lead points and detours are placed for a cable's installed bend radius up
// to this, twice a power cord's 42.6 and more than three times a Cat 6A
// cord's 30. It is a bound on what the kit moves, not on what it reports: a
// cable that needs more is laid as one of this radius, and every corner
// short of its own radius is still in `bends`.
const ROOM_MAX = 100;

export const STOCK_M = [0.5, 1, 1.5, 2, 3, 5, 7, 10, 15, 20, 30];
// THE END ALLOWANCE (#962, docs/cable-lay-design.md section 1.6). This
// table is its sourced part, in metres an end, by media: only what is
// physically there and not in the path.
// A routed path runs from port face to port face, the plug outside the face
// included (PLUG_REACH, above), while a stock cord's nominal length takes in
// its plugs, tip to tip, unless its maker measures it otherwise. So each end
// adds
//   - the part of the plug INSIDE the port, when the nominal length includes
//     it: the plug's length less its reach out of the face, from the library
//     parts PLUG_REACH reads; and
//   - half of how much SHORTER than its nominal length the maker allows a
//     cord to be (its minus tolerance). A plus tolerance only adds slack, so
//     it adds nothing here.
// Service loops and dressing slack are not in this table: they are explicit
// slack held in a tray (#949 step 4), where they can be seen. Until that is
// built, DRESSING_ALLOWANCE (below) stands in for them, apart from the table.
//   - LC fibre (os2, om3, om4, om5): 13.1 mm, the plug inside. generic/lc-plug@2:
//     its rear stands 25.6 behind the housing's front, 12.5 of it out of the
//     bore (an estimate in the bracket 12.2 to 13.97 that SENKO's
//     DS-LC-000004 drawing allows). Nothing short: FS's patch cable
//     datasheet for fibre cords, its Cable Length Tolerances table, states
//     every duplex and simplex length +x/-0 (+10 cm/-0 cm from 0.5 m, +15 cm/-0 cm from 5 m).
//   - copper (cat6, cat6a), and a cable with no media: 34.5 mm. 9.5 inside,
//     generic/rj45-plug@1 (22.48 long, CommScope 2843005, 13.0 of it out of
//     the jack, an estimate resting on the latch); plus 25, half of 1 per
//     cent of a 5 m cord. FS, Panduit and Siemon state no copper cord
//     tolerance; Belden's CAT6+ modular cord (C601106001, Overall Length
//     Tolerances) states +0.2/-0 m to 2 m, Brand-Rex's 10GPlus Cat6A
//     patchcord (GD056534v18) a bracketed length of +/- 1%. The two disagree,
//     and the one that allows a short cord is taken, at 5 m, the longest
//     cord a rack's own routes come to as a rule.
//   - DAC: 25 mm, half of the +/-5 cm the FS 10G SFP+ DAC datasheet states
//     for lengths to 5 m (section VII, the L / TOLERANCE table). Its drawing
//     dimensions L between the two heads, so the heads, the part in the cage
//     included, come with the cord and add nothing; the head's 19.8 out of
//     the cage, which the path counts, is left as margin.
//   - AOC: 52.4 mm, the plug inside: generic/qsfp-cable@1 (SFF-8661 Figure
//     5-1, the head's stop in the cage), the same head PLUG_REACH reads. No
//     maker held says how it measures an AOC (FS's AOC drawing gives no L),
//     so tip to tip is assumed; nothing short: L-com's AOCQSP28100 drawing,
//     OVERALL CABLE LENGTH TOLERANCE, is +x/-0 at every length.
// The kit does not know what a port holds: an LC cord into an optic's
// receptacle enters it as it would an adapter's, and an AOC's head enters
// the cage; an SFP head (47.5 inside, SFF-8432) is taken at the QSFP figure.
export const END_ALLOWANCE_BY_MEDIA = {os2: 0.0131, om3: 0.0131, om4: 0.0131, om5: 0.0131,
  cat6: 0.0345, cat6a: 0.0345, dac: 0.025, aoc: 0.0524};
const UNSET_ALLOWANCE = 0.0345;
// TEMPORARY, until #949 step 4 (explicit tray slack) is built: a dressing
// allowance of 0.1 m an end, for every media, on top of the table. It is not
// a measured figure and has no maker's source: it is there by decision
// (2026-10-10, #962), so that a routed cord is not bought with nothing to
// dress it by while no tray can hold its slack. It is kept out of
// END_ALLOWANCE_BY_MEDIA so that the table stays what the sources say; step 4 removes
// this constant and its one use in endAllowance, and nothing else.
const DRESSING_ALLOWANCE = 0.1;
// What a routed length adds at each end of a cable: its media's figure from
// the table (the copper cord's for a cable with no media, or none the table
// knows) and, for now, the dressing allowance.
export const endAllowance = cable => ((typeof cable?.media === 'string'
  && Object.hasOwn(END_ALLOWANCE_BY_MEDIA, cable.media))
  ? END_ALLOWANCE_BY_MEDIA[cable.media] : UNSET_ALLOWANCE) + DRESSING_ALLOWANCE;
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
//   there), 'entry', 'exit' or 'face' (a ring), 'approach' (outside a ring
//   whose opening is placed, where a pass starts and ends, #968),
//   'lead' (a point a turn is given its room at, #973: beside a ring's
//   approach point, with the ring's `item` and `via`, where the cable is led
//   square to it; or straight out of a plug past its reach point, with its
//   `end`), 'pathway' (a duct or a pass-through), 'tray' (a point of a
//   tray's stretch, #949 step 3), 'lane', 'detour' or 'rest' (a point of a
//   free span as it hangs, or as it lands on a surface);
// - `rings`: per ring on the route, {item, via, run, depth, estimated,
//   passed, sense, entry, exit} (sense +1 or -1 along the run; a ring not
//   passed has `face` instead of entry and exit: the ring's own face, where
//   the path's `face` point of a ring whose opening is placed stands back
//   from it at its approach point, #968; one that holds a cable
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
//   points};
// - `bends`: each corner of the path with less room than the cable's
//   installed bend radius (#973, section 3.4), as {kind: 'tight-bend', cable,
//   point, between: [from, to], at: [x, y, z], angle_deg, legs_mm: [in, out],
//   room_mm, need_mm, short_mm}: `point` is the path point's `at`, `between`
//   the waypoints the corner lies between (as for a crossing), `room_mm` the
//   largest bend its legs leave it (route-path.js cornersOf, a leg between
//   two corners shared by what each needs of it), `need_mm` the cable's
//   radius (`ctx.bendOf(cable)`, else its media's) and `short_mm` the miss.
//   The path is laid to leave none (the approach points, lead points and
//   detours below, and no hang that would make one), so what is here is a
//   bend the kit's rules found no room for: often the parts leave none, but
//   a finding does not prove that no other lay would have it;
// - `rests`: what the cable lies on (docs/cable-lay-design.md section 3):
//   {kind: 'ring', item, via} for a ring on a tray whose sill holds it;
//   {kind: 'tray', item, via, face, role, ties?} for a tray it runs along or
//   lands on, `face` 'top' or 'underside' in the frame of the part, `role`
//   'resting' (the face that looks up) or 'held' (the face that looks down,
//   strapped: `ties`, the indices of the tie slots it uses); and {kind:
//   'body', item, part} for a body a free span comes to rest on.
// RESTING (section 3): a ring on a tray whose catalogue entry places its
// opening holds the cable on its sill, its centre the cable's radius above
// the opening's lowest inside edge, at the side of the opening nearer the
// rail (a cable on its own; the lay of several is step 5); a tray named as a
// waypoint is laid along its run between its neighbours, on the floor at the
// cable's radius, or on the held face where the page pins it there
// (`ctx.trayFaceOf(cable, {item, via})` gives the face, `top` or
// `underside`, and the tray offers it: it has tie slots); and every leg that
// is not held - not a plug, not inside a ring, not a lane's run along the
// frame, not a tray's stretch, not into or out of a detour - is a free span,
// and hangs by the drape of the cable's family (resting.js), landing on any
// surface it would otherwise pass below. `ctx.bendOf(cable)`, when the page
// gives it, is the installed bend radius no curve of a span is tighter than
// (over its drape), and the radius the path's turns are given room for
// (#973); else its media's (resting.js BEND). The drape is the
// family's: its type's when the page gives `ctx.typeOf(id)` (cable-types.js),
// else its media's.
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
  const diameter = cableDiameter(cable, ctx), r = diameter / 2;
  // each port, then its plug's reach point (section 1.5): the first and last
  // legs of the route start there; a plug of no reach adds no point. The leg
  // from a port to its reach point is the plug: straight, and not a span.
  const ra = plugReach(cable, cable.a, ctx), rb = plugReach(cable, cable.b, ctx);
  const stops = [{p: a, at: 'a'}];
  if (ra > 0) stops.push({p: reachPoint(rack, cable.a, a, ra), at: 'reach', end: 'a', hold: true});
  const wps = resolveRoute(rack, cable, ctx).waypoints;
  const marks = wps.map(() => null);
  const rests = [];
  const rested = (o) => { if (!rests.some(x => x.kind === o.kind && x.item === o.item && (x.via ?? x.part) === (o.via ?? o.part))) rests.push(o); };
  wps.forEach((w, i) => {
    let p = pointOf(rack, w, ctx);
    if (!p) return;
    const g = w.lane ? null : ctx.guidesOf(w.item).find(x => x.via === w.via);
    const tray = !w.lane && !g ? trayOf(rack, w, ctx) : null;
    if (tray) { stops.push({p, w, i, tray}); return; }
    const ring = ringOf(g);
    // A RING ON A TRAY HOLDS THE CABLE ON ITS SILL (section 3): its centre
    // comes down to the lowest inside edge of its opening as mounted, plus
    // the cable's radius, and across its run to the side of the opening
    // nearer the rail the part is fixed to, where a cable on its own lies
    // (position 1, section 4; the lay of several is step 5); a ring whose
    // contract does not place its opening stays where its drawing puts it.
    const open = ring && ringOpening(rack, w, ctx);
    if (open) {
      p = {...p, y: open.box.y0 + r, ...(open.run === 'x' ? {z: railSide(open.box.z0, open.box.z1, railZOf(rack, w.item), r)}
        : {x: (open.box.x0 + open.box.x1) / 2})};
      rested({kind: 'ring', item: w.item, via: w.via});
    }
    stops.push({p, w, i, ring, ...(open ? {open} : {}), ...(w.lane ? {lane: true} : {})});
  });
  if (rb > 0) stops.push({p: reachPoint(rack, cable.b, b, rb), at: 'reach', end: 'b'});
  stops.push({p: b, at: 'b', hold: rb > 0});
  // A TRAY a route names is laid along its run between its neighbours (section
  // 2.1): from where the point before it comes onto the tray to where the
  // point after it leaves, each taken square onto the floor. On the face that
  // looks up it lies on the floor and through the rings standing on it; on
  // the held face, strapped under the plate (heldStretch). The face is the
  // one the page pins (`ctx.trayFaceOf(cable, waypoint)`, `top` or
  // `underside`, named in the frame of the part), where the tray offers it;
  // otherwise the face that looks up. The automatic face is step 5.
  for (let k = stops.length - 1; k >= 0; k--) {
    const s = stops[k];
    if (!s.tray) continue;
    const prev = stops[k - 1]?.p ?? s.p, next = stops[k + 1]?.p ?? s.p;
    const laid = alongTray(rack, s.tray, prev, next, cable, ctx, r);
    rested({kind: 'tray', item: s.w.item, via: s.w.via, face: laid.face, role: laid.role, ...(laid.ties ? {ties: laid.ties} : {})});
    stops.splice(k, 1, ...laid.points.map((p, j) => ({p, w: s.w, i: s.i, trayAt: true, hold: j > 0 && laid.hold[j]})));
  }
  // a ring holds a cable that reaches just into it (route-path.js, HELD):
  // how near depends on the cable's diameter, and it holds only from a port:
  // the port stops and their reach points are the only stops without `w`, so
  // `!stops[k ± 1].w` says the neighbour is a port's (a ring is never first or
  // last, so both neighbours exist)
  const {points, passes, back} = throughRings(stops.map(s => s.p), stops.map((s, k) => (s.ring
    ? {...s.ring, diameter, portBefore: !stops[k - 1].w, portAfter: !stops[k + 1].w} : null)));
  // Label each point with what it is: walk the stops, a ring taking two points when passed.
  // `hold` on a point says the leg into it is not a free span: the plug, the
  // stretch inside a ring, a lane's run along the frame, a tray's stretch.
  const passAt = new Map(passes.map(x => [x.index, x])), backAt = new Map(back.map(x => [x.index, x]));
  // `need` is the cable's installed bend radius, what its corners are judged
  // against; `bend` is the radius the lay is opened out for (#973), the same
  // up to ROOM_MAX: a stiffer cable is laid as one of that radius, and its
  // corners are reported against its own.
  const need = bendOf(cable, ctx), bend = Math.min(need, ROOM_MAX), base = r + CLEAR;
  // the corners of a run of points short of the cable's installed bend
  // radius, a shared leg shared by need (route-path.js cornersOf)
  const tightOf = pts => cornersOf(pts, {share: 'need'}).filter(c => c.room_mm < need - 1e-9);
  // Round the solid bodies (section 1.3), then what still crosses one (1.4).
  // A ring's parts are met by the cable's tube (solids.js legCrossings, #968).
  const solids = solidsOf(rack, ctx);
  // the side lanes at a height, where laneXAt puts them (rule 3 of 1.3)
  const lanesAt = y => {
    const ru = Math.max(1, Math.min(rack.frame.heightRU, Math.floor(y / RU) + 1));
    return [...new Set(lanesOf(rack.frame).map(l => laneXAt(rack, l, ru, ctx?.chassisOf)))];
  };
  const ref = k => (stops[k].w ? (stops[k].w.lane ? {lane: stops[k].w.lane, ru: stops[k].w.ru} : {item: stops[k].w.item, via: stops[k].w.via})
    : {end: stops[k].end ?? stops[k].at});
  // IN FRONT OF A ZERO-U PART (section 1.3, rule 4): the space its outward
  // face looks into, where a PDU's plugs stand, is the last way round it. A
  // leg that would graze the part is taken behind it (solids.js detour), but
  // one that clears it by more than the tube is not a crossing, so nothing
  // there stops a point moved for a bend's room (#973) from freeing a leg to
  // run across that face. `aheadOf` gives the legs of a run of points that
  // pass through that space; no point moved for room may add one, and no
  // hang may: the space is as high as the part, so a span that passes just
  // over the part's top, in front of its face, would sag down into it.
  const fronts = solids.filter(x => x.zeroU === true).map(x => ({item: x.item, part: 'front', holes: [],
    box: {x0: x.box.x0 - r, x1: x.box.x1 + r, y0: x.box.y0 - r, y1: x.box.y1 + r,
      z0: x.away === -1 ? -1e6 : x.box.z1, z1: x.away === -1 ? x.box.z0 : 1e6}}));
  const aheadOf = pts => { const at = []; for (let k = 1; fronts.length && k < pts.length; k++) if (legCrossings(pts[k - 1], pts[k], fronts).length) at.push(k); return at; };
  // THE TAUT PATH for the approach offsets `offs` (stop index -> [before the
  // ring, after it], mm from its band along the run): every stop's points,
  // then the detours between them. `own[i]` is the stop a taut point is of
  // (-1 for a detour point); `stuck` counts the legs no detour clears.
  const lay = (offs, leads = new Map(), runs = {}) => {
    const out = [], rings = [], findings = [], from = [], marks = wps.map(() => null);
    let n = 0;
    stops.forEach((s, k) => {
      const tag = s.w ? (s.w.lane ? {at: 'lane'} : {item: s.w.item, via: s.w.via}) : {at: s.at, ...(s.end ? {end: s.end} : {})};
      const hold = s.hold === true || (s.lane && stops[k - 1]?.lane === true);
      if (!s.ring) {
        // a RUN-OUT (#973, below): the cable goes on straight out of its plug
        // past the reach point, to a lead point its first turn is made at
        const run = s.at === 'reach' ? runs[s.end] ?? 0 : 0, pt = points[n++];
        const port = run > 0 ? (s.end === 'a' ? a : b) : null;
        const lead = port ? {x: pt.x, y: pt.y, z: pt.z + Math.sign(pt.z - port.z) * run, at: 'lead', end: s.end} : null;
        if (lead && s.end === 'b') { from.push(k); out.push(lead); }
        from.push(k);
        out.push({...pt, ...(s.w && !s.w.lane ? {at: s.trayAt ? 'tray' : 'pathway'} : {}), ...tag, ...(hold || (lead && s.end === 'b') ? {hold: true} : {})});
        if (lead && s.end === 'a') { from.push(k); out.push({...lead, hold: true}); }
        return;
      }
      const ring = {item: s.w.item, via: s.w.via, ...s.ring};
      const pass = passAt.get(k);
      if (pass) {
        const entry = points[n++], exit = points[n++];
        // A RING WHOSE OPENING IS PLACED IS SOLID ROUND IT (#968): the cable
        // comes to it along its run from an APPROACH POINT outside the band, at
        // the opening's height and across position, and leaves to another past
        // its far face, each clear of the band by at least the cable's radius
        // and CLEAR (`offs`: further, where the route turns there, below), so
        // whatever reaches the ring (a detour, a hang, a leg from behind or
        // below) ends there and enters through the opening, never through a leg
        const a = s.ring.run, off = offs.get(k) ?? [base, base];
        const approach = s.open && a in entry ? [{...entry, [a]: entry[a] - pass.sense * off[0]}, {...exit, [a]: exit[a] + pass.sense * off[1]}] : null;
        // a LEAD POINT (#973, below): square to the approach point, where the
        // stop before the ring (or after it) stands along the run
        const lead = leads.get(k) ?? [false, false];
        const square = (nb, ap) => (nb && Math.abs(nb[a] - ap[a]) > 1e-6 ? {x: nb.x, y: nb.y, z: nb.z, [a]: ap[a], ...tag, at: 'lead'} : null);
        const before = approach && lead[0] ? square(out[out.length - 1], approach[0]) : null;
        const after = approach && lead[1] ? square(points[n], approach[1]) : null;
        if (before) { from.push(k); out.push(before); }
        if (approach) { from.push(k); out.push({...approach[0], ...tag, at: 'approach'}); }
        from.push(k, k);
        out.push({...entry, ...tag, at: 'entry', ...(approach ? {hold: true} : {})}, {...exit, ...tag, at: 'exit', hold: true});
        if (approach) { from.push(k); out.push({...approach[1], ...tag, at: 'approach', hold: true}); }
        if (after) { from.push(k); out.push(after); }
        rings.push({...ring, passed: true, ...(pass.held ? {held: true} : {}), sense: pass.sense, entry: pass.entry, exit: pass.exit});
        marks[s.i] = {run: s.ring.run, depth: s.ring.depth, sense: pass.sense, back: false};
      } else {
        const no = backAt.get(k);
        // a cable taken to a solid ring's face and back (a finding) stops at
        // the approach point before that face, not on it: the face is the
        // mouth of the opening, and a leg that turned there would graze the
        // ring's legs and seat (#968)
        const a = s.ring.run, at = points[n++];
        const face = s.open && a in at ? {...at, [a]: at[a] - no.sense * base} : at;
        from.push(k);
        out.push({...face, ...tag, at: 'face'});
        rings.push({...ring, passed: false, sense: no.sense, face: at});
        marks[s.i] = {run: s.ring.run, depth: s.ring.depth, sense: no.sense, back: true};
        findings.push({kind: 'doubles-back', cable: cable.id, item: s.w.item, via: s.w.via});
      }
    });
    // the detours leave each end's move to a plane room for two bends (#973,
    // solids.js detour): twice the installed bend radius, or `runs.room`
    // where two right angles' worth is not enough (below)
    const taut = [out[0]], tautLegs = [], detours = [], own = [from[0]];
    let stuck = 0;
    for (let k = 1; k < out.length; k++) {
      const between = [ref(from[k - 1]), ref(from[k])];
      const extra = solids.length ? detour(out[k - 1], out[k], solids, {diameter, lanes: lanesAt, room: runs.room ?? 2 * bend}) : [];
      if (extra === null) stuck++;
      if (extra?.length) {
        detours.push({between, points: extra.map(p => ({x: p.x, y: p.y, z: p.z}))});
        for (const p of extra) { tautLegs.push(between); own.push(-1); taut.push({x: p.x, y: p.y, z: p.z, at: 'detour'}); }
      }
      tautLegs.push(between);
      own.push(from[k]);
      taut.push(out[k]);
    }
    return {rings, findings, marks, taut, tautLegs, detours, own, stuck, ahead: aheadOf(taut)};
  };
  // ROOM AT A RING (#973, section 3.4). An approach point is where a cable
  // comes onto a ring's run, and where it turns onto it: the stretch from
  // there through the ring is the leg that turn bends in, and the radius
  // plus CLEAR of #968 left a right angle about a fifth of the leg its bend
  // radius needs. So, on each side of a ring where the route turns (the stop
  // before or after it does not stand on the run through the ring), the
  // approach point stands the installed bend radius from the band; where
  // two rings follow each other along one run, no further than half way
  // between their bands, and never in or past the band of another ring of
  // the same part. A side the route passes straight through keeps the
  // radius and CLEAR.
  // That is where every path starts. Where a corner between a ring and the
  // stop beside it is still short of room by the kit's own measure
  // (cornersOf, a leg shared by need), these are on offer, each tried by
  // laying the path with it (`offers`, below):
  // - the stop stands back along the run from the approach point, on the
  //   ring's side of it, so the cable turns back on itself to face the ring.
  //   That takes two bends, and two bends share a leg: the approach point
  //   moves out to stand two bend radii past that stop along the run;
  // - the same, and the cable LED SQUARE: along the run, level with that
  //   stop, to a lead point (`at: 'lead'`) beside the approach point, and
  //   from there square onto the run, so that one turn of more than a right
  //   angle is two of a right angle each;
  // - a detour between them comes back beside itself (out past a tray's
  //   edge, up and back in): the approach point stands just far enough along
  //   the run, to either side of the stop, for the leg between the detour's
  //   two turns, and there it may stand nearer the band than the bend radius
  //   (never nearer than the radius and CLEAR);
  // - the two turns at the ring need more of the stretch through it than it
  //   is: the other side's approach point moves out by what is missing;
  // - the approach point back at the radius and CLEAR: a stop that stands
  //   almost over it turns onto the run with its own leg for room.
  // What a ring has no room for (the stop less than two radii from the run,
  // across it; a plug that reaches almost to the run; the next ring in the
  // way) is left as it is, and the corner is in `bends`.
  const offs = new Map(), leads = new Map(), faces = new Map();
  const unit = (u, v) => { const d = Math.hypot(v.x - u.x, v.y - u.y, v.z - u.z); return d > 1e-9 ? {x: (v.x - u.x) / d, y: (v.y - u.y) / d, z: (v.z - u.z) / d} : null; };
  const turnsAt = (u, v, a, sn) => { const d = u && v && unit(u, v); return !!d && Math.acos(Math.max(-1, Math.min(1, sn * d[a]))) * 180 / Math.PI > STRAIGHT_DEG; };
  {
    let n = 0;
    stops.forEach((s, k) => {
      const pass = s.ring ? passAt.get(k) : null;
      if (!pass) { n++; return; }
      const entry = points[n++], exit = points[n++], a = s.ring.run;
      if (!s.open || !(a in entry)) return;
      // how far along the run an approach point may stand from each face: up
      // to the next ring of the same part that way, less the radius and
      // CLEAR, so it never stands in or past another ring's band
      const others = traysOf(rack, ctx).filter(t => t.item === s.w.item).flatMap(t => t.rings).filter(o => o.via !== s.w.via && o.run === a);
      const free = [-pass.sense, pass.sense].map((dir, sd) => {
        const face = (sd ? exit : entry)[a];
        const gaps = others.map(o => (dir > 0 ? o.box[`${a}0`] - face : face - o.box[`${a}1`])).filter(g => g > 0);
        return Math.max(base, Math.min(...gaps, Infinity) - base);
      });
      const side = (nb, turns, face, sd) => {
        if (!nb || !turns) return base;
        // a ring next along the same run: half the way between the two bands
        const cap = nb.ring && nb.ring.run === a ? (Math.abs(face[a] - nb.p[a]) - nb.ring.depth / 2) / 2 : Infinity;
        return Math.max(base, Math.min(bend, cap, free[sd]));
      };
      const before = stops[k - 1], after = stops[k + 1];
      offs.set(k, [side(before, turnsAt(before?.p, entry, a, pass.sense), entry, 0), side(after, turnsAt(exit, after?.p, a, pass.sense), exit, 1)]);
      faces.set(k, {a, out: [-pass.sense, pass.sense], face: [entry[a], exit[a]], free});
    });
  }
  const shortOf = pts => tightOf(pts).reduce((m, c) => m + (need - c.room_mm), 0);
  const lengthOf = pts => pts.reduce((m, p, i) => (i ? m + dist(pts[i - 1], p) : 0), 0);
  const runs = {};
  let L = null;
  // What is decided below is decided once per rack, context and cable, as
  // the side of a route is (autoRoute): every reader of a path asks for it
  // again, and the search is the dear part.
  let per = roomMemo.get(rack);
  if (!per) roomMemo.set(rack, per = new WeakMap());
  let byCable = per.get(ctx);
  if (!byCable) per.set(ctx, byCable = new WeakMap());
  const known = byCable.get(cable);
  if (known) {
    offs.clear(); for (const [k, v] of known.offs) offs.set(k, v);
    for (const [k, v] of known.leads) leads.set(k, v);
    Object.assign(runs, known.runs);
    L = lay(offs, leads, runs);
  } else {
    L = lay(offs, leads, runs);
    // an approach point that stands out at the bend radius must not free its
    // leg to run in front of a zero-U part (above): where it does, that side
    // of the ring keeps the radius and CLEAR, and its corner is in `bends`
    if (L.ahead.length) {
      const L0 = lay(new Map(), leads, runs);
      if (L.ahead.length > L0.ahead.length) {
        for (const i of L.ahead) for (const [k, side] of [[L.own[i - 1], 1], [L.own[i], 0]])
          if (offs.has(k)) { const o = [...offs.get(k)]; o[side] = base; offs.set(k, o); }
        L = lay(offs, leads, runs);
        if (L.ahead.length > L0.ahead.length) { offs.clear(); L = L0; }
      }
    }
    let short = shortOf(L.taut);
    // One change tried: laid, and kept (as the best so far) when it leaves
    // the path's corners less short of room in all, puts no leg newly through
    // a body or in front of a zero-U part, and either leaves no corner of
    // `region` (the stretch it is for) short or makes the path no longer: a
    // cable is not sent a longer way round to make a short corner less short.
    const better = ({o = offs, l = leads, r = runs, region}, best) => {
      const L2 = lay(o, l, r), s2 = shortOf(L2.taut), len = lengthOf(L2.taut);
      if (L2.stuck > L.stuck || L2.ahead.length > L.ahead.length || !(s2 < short - 1e-9) || (region(L2) && len > lengthOf(L.taut) + 1e-9)) return best;
      return !best || s2 < best.s - 1e-9 || (s2 < best.s + 1e-9 && len < best.len - 1e-9) ? {L: L2, s: s2, len, o, l, r} : best;
    };
    const put = (map, k, side, v) => { const m = new Map(map); const o = [...(m.get(k) ?? [false, false])]; o[side] = v; m.set(k, o); return m; };
    // Every change on offer for the path as it stands (the rules above and
    // ROOM AT A PLUG, below).
    const offers = () => {
      const list = [], tight = tightOf(L.taut);
      for (const k of offs.keys()) for (const side of [0, 1]) {
        const cur = offs.get(k)[side], f = faces.get(k);
        if (cur < bend - 1e-9) continue;
        // the stretch this approach point's leg is part of: from the stop
        // before the ring to the ring, or from the ring to the stop after it
        // (the approach point itself: the one before the ring's entry, or after its exit)
        const apOf = (T, sd) => T.taut.findIndex((p, i) => T.own[i] === k && p.at === (sd ? 'exit' : 'entry')) + (sd ? 1 : -1);
        const within = T => {
          const ap = apOf(T, side), lo = side ? ap : T.own.lastIndexOf(k - 1), hi = side ? T.own.indexOf(k + 1) : ap;
          return lo < 0 || hi < 0 ? null : [lo, hi];
        };
        const region = T => { const w = within(T); return !!w && tightOf(T.taut).some(c => c.k >= w[0] && c.k <= w[1]); };
        const w = within(L);
        if (!w || !tight.some(c => c.k >= w[0] && c.k <= w[1])) continue;
        const [lo, hi] = w;
        // how far out of the band, along the run, that stop stands
        const nb = L.taut[side ? hi : lo], d = f.out[side] * (nb[f.a] - f.face[side]);
        if (d < cur + 2 * bend - 1e-6 && d + 2 * bend <= f.free[side] + 1e-9) {
          const o2 = put(offs, k, side, Math.max(cur, d + 2 * bend));
          list.push({o: o2, region}, {o: o2, l: put(leads, k, side, true), region});
        }
        if (d < cur + 2 * bend - 1e-6) {
          // a detour that comes back beside itself there (out past a tray's
          // edge, up, and back in): the leg between its two turns is as long
          // as the stop and the approach point are apart, along the run and
          // across it, and needs two radii; so the approach point may stand
          // just far enough along the run to either side of the stop
          const t = tight.filter(c => c.k >= lo && c.k <= hi && L.taut[c.k].at === 'detour');
          const pair = t.find((c, i) => t[i + 1]?.k === c.k + 1);
          if (pair) {
            const p0 = L.taut[pair.k], p1 = L.taut[pair.k + 1], along = Math.abs(p1[f.a] - p0[f.a]), across2 = dist(p0, p1) ** 2 - along ** 2;
            const step = across2 < 4 * bend * bend ? Math.sqrt(4 * bend * bend - across2) + 0.5 : 0;
            for (const v of [d - step, d + step]) if (step > 0 && v >= base && v <= f.free[side] + 1e-9) list.push({o: put(offs, k, side, v), region});
          }
        }
        // the approach point back at the radius and CLEAR: a stop that stands
        // almost over it turns onto the run with its own leg for room, and a
        // point moved out past it would make the cable come back for it
        if (cur > base + 1e-9) list.push({o: put(offs, k, side, base), region});
        // the two turns' share of the stretch through the ring: what they
        // need of it over what it is, given to the other side
        const cs = cornersOf(L.taut, {share: 'need'}), tanAt = i => { const c = cs.find(x => x.k === i); return c ? Math.tan(c.angle_deg * Math.PI / 360) : 0; };
        const other = offs.get(k)[1 - side], lack = bend * (tanAt(apOf(L, 0)) + tanAt(apOf(L, 1))) - (cur + other + Math.abs(f.face[1] - f.face[0]));
        if (lack > 1e-6 && Number.isFinite(lack) && other + lack + 0.5 <= Math.min(2 * bend, f.free[1 - side])) list.push({o: put(offs, k, 1 - side, other + lack + 0.5), region});
      }
      // ROOM AT A PLUG (#973, section 3.4). A cable leaves its plug straight
      // (1.5), and the plug's reach is the leg its first turn has on that
      // side. Where that turn is short of room (a fibre cord's 27.6 mm plug,
      // turning back past a right angle to a lane on the rail plane), the
      // cable runs on straight out of the plug, half a bend radius, one or
      // one and a half further, to a lead point (`at: 'lead'`, with its
      // `end`), and turns there.
      for (const end of ['a', 'b']) {
        const region = T => { const t = tightOf(T.taut); return T.taut.some((p, i) => p.end === end && (p.at === 'reach' || p.at === 'lead') && t.some(c => c.k === i)); };
        if (!L.taut.some((p, i) => p.end === end && (p.at === 'reach' || p.at === 'lead') && tight.some(c => c.k === i))) continue;
        for (const m of [0.5, 1, 1.5]) if (m * bend > (runs[end] ?? 0) + 1e-9) list.push({r: {...runs, [end]: m * bend}, region});
      }
      // ROOM ROUND A BODY. A detour's planes stand two bend radii from each
      // end, the share of two right angles; where a detour is pulled taut its
      // turn can be wider than a right angle, and a corner at a detour point
      // still short of room is offered two and a half and three radii
      const atDetour = T => tightOf(T.taut).some(c => T.taut[c.k].at === 'detour');
      if (tight.some(c => L.taut[c.k].at === 'detour'))
        for (const m of [2.5, 3]) if (m * bend > (runs.room ?? 2 * bend) + 1e-9) list.push({r: {...runs, room: m * bend}, region: atDetour});
      return list;
    };
    // The best change on offer is made, and the offers are drawn up again,
    // until none helps or six have been made: the best of all of them each
    // time, whichever end of the cable they are nearer. That takes the order
    // of the ends out of the choice; it does not make a cable written the
    // other way round lay the same. What each offer is judged by still reads
    // the path from end a (cornersOf merges slight turns from its start, a
    // detour goes round the first body it meets), and two offers can differ
    // by less than that.
    for (let round = 0; round < 6 && short > 0; round++) {
      let best = null;
      for (const c of offers()) best = better(c, best);
      if (!best) break;
      const o = new Map(best.o), l = new Map(best.l);
      offs.clear(); for (const [k, v] of o) offs.set(k, v);
      leads.clear(); for (const [k, v] of l) leads.set(k, v);
      Object.assign(runs, best.r);
      L = best.L; short = best.s;
    }
    byCable.set(cable, {offs: new Map(offs), leads: new Map(leads), runs: {...runs}});
  }
  const {rings, findings, taut, tautLegs, detours} = L;
  for (let i = 0; i < marks.length; i++) marks[i] = L.marks[i];
  // RESTING (section 3): every leg that is not held is a free span, and hangs
  // by the drape of the cable's family, landing on whatever surface it would
  // otherwise pass below (resting.js hang). A leg into or out of a detour
  // point is not: a cable taken round an edge is dressed round it by hand
  // (section 1.3), taut, so it stays clear by what the detour keeps. A sag
  // that would carry the cable into a body its straight leg did not cross is
  // not laid, and nor is one that would leave a corner of the path, the
  // span's own or where it meets what holds it, less room than the straight
  // span leaves it (#973, resting.js hang `fits`). Each span is judged with
  // every other span straight, so no span's hang waits on another's; and
  // where two spans that meet at a point each fit alone and together leave
  // that point short, neither hangs. Which end the cable is read from can
  // still matter: the corners a hang is judged by are counted from end a
  // (cornersOf), so the same span can hang read one way and not the other.
  const surfaces = surfacesOf(rack, ctx);
  const drape = drapeOf(cable, ctx);
  const hung = taut.map(() => null);
  // the room each point of the taut path has as a corner (none: all it needs)
  const roomAt = new Map(cornersOf(taut, {share: 'need'}).map(c => [c.k, c.room_mm]));
  const kept = i => Math.min(roomAt.get(i) ?? Infinity, need);
  for (let k = 1; k < taut.length; k++) {
    const p = taut[k - 1], q = taut[k];
    if (q.hold || p.at === 'detour' || q.at === 'detour') continue;
    const head = taut.slice(0, k), tail = taut.slice(k);
    // no point of the hang is itself a corner short of room, and no corner
    // of the path is left less room than it has with the span straight (or
    // than it needs, where it has more)
    const fits = pts => {
      if (newCrossing(p, q, pts, solids, diameter)) return false;
      // nor may it sag into the space in front of a zero-U part that the
      // straight span passes over: that space ends at the part's top
      if (fronts.length && aheadOf([p, ...pts, q]).length && !aheadOf([p, q]).length) return false;
      const i0 = head.length, i1 = head.length + pts.length;
      return cornersOf([...head, ...pts, ...tail], {share: 'need'}).every(c => (c.k >= i0 && c.k < i1 ? c.room_mm >= need - 1e-9
        : c.room_mm >= kept(c.k < i0 ? c.k : c.k - pts.length) - 1e-9));
    };
    const h = hang(p, q, {r, drape, bend: need, surfaces, fits});
    if (h.points.length) hung[k] = h;
  }
  const strung = () => {
    const pts = [taut[0]], legOf = [], at = [0];
    for (let k = 1; k < taut.length; k++) {
      for (const pt of hung[k]?.points ?? []) { legOf.push(tautLegs[k - 1]); pts.push({x: pt.x, y: pt.y, z: pt.z, at: 'rest'}); }
      legOf.push(tautLegs[k - 1]);
      at.push(pts.length);
      pts.push(taut[k]);
    }
    return {pts, legOf, at};
  };
  let S = strung();
  for (let n = 0; n < taut.length; n++) {
    // the points left less room than that by two hangs together: the spans
    // either side of each go back to straight
    let cut = false;
    for (const c of cornersOf(S.pts, {share: 'need'})) {
      const k = S.at.indexOf(c.k);
      if (k < 0 ? c.room_mm >= need - 1e-9 : c.room_mm >= kept(k) - 1e-9) continue;
      for (const j of k < 0 ? S.at.map((v, i) => (v > c.k ? i : -1)).filter(i => i > 0).slice(0, 1) : [k, k + 1]) if (hung[j]) { hung[j] = null; cut = true; }
    }
    if (!cut) break;
    S = strung();
  }
  const final = S.pts, legs = S.legOf;
  for (const h of hung) for (const g of h?.lands ?? []) rested(g.tray ? {kind: 'tray', item: g.item, via: g.via, face: 'top', role: 'resting'}
    : {kind: 'body', item: g.item, part: g.part});
  for (const p of final) delete p.hold;
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
  // WHAT IS STILL TIGHT (#973, section 3.4): each corner of the path with
  // less room than the cable's installed bend radius, by the measure the
  // bundle check uses (cornersOf).
  const bends = tightOf(final).map(c => ({kind: 'tight-bend', cable: cable.id, point: final[c.k].at,
    between: [legs[c.k - 1][0], (legs[c.k] ?? legs[c.k - 1])[1]], at: [r1(final[c.k].x), r1(final[c.k].y), r1(final[c.k].z)],
    angle_deg: c.angle_deg, legs_mm: c.legs_mm, room_mm: c.room_mm, need_mm: need, short_mm: r1(need - c.room_mm)}));
  return {points: final, rings, findings, marks, crossings, detours, rests, bends, allowance: endAllowance(cable)};
}

// The rail plane an item is fixed to, as a z: the front rail's 0, or the
// rear rail's.
const railZOf = (rack, id) => planeZ(rack.frame, itemOf(rack, id)?.face === 'rear' ? 'rear' : 'front');
// A cable of radius r lying across [lo, hi] at the side nearer `rail`.
const railSide = (lo, hi, rail, r) => (Math.abs(lo - rail) <= Math.abs(hi - rail) ? lo + r : hi - r);

// The opening of a ring a waypoint names, where it stands on a tray whose
// catalogue entry places it ({run, box} in rack mm, solids.js traysOf), or null.
function ringOpening(rack, w, ctx) {
  for (const t of traysOf(rack, ctx)) {
    if (t.item !== w.item) continue;
    const o = t.rings.find(x => x.via === w.via);
    if (o) return o;
  }
  return null;
}

// A CABLE ALONG A TRAY (section 2.1), from `prev` to `next`: the points it is
// laid at, and which of them it reaches held (`hold[j]`: the leg into point j
// is part of the tray's stretch, not a free span), with the face it lies on.
// The stretch runs along the tray's run from the floor's square below `prev`
// to the square below `next`, each clamped to the floor.
function alongTray(rack, t, prev, next, cable, ctx, r) {
  const run = t.run, across = run === 'x' ? 'z' : 'x';
  const lo = Math.min(...t.floors.map(f => f[`${run}0`])), hi = Math.max(...t.floors.map(f => f[`${run}1`]));
  const clamp = v => Math.min(hi, Math.max(lo, v));
  const a = clamp(prev[run]), b = clamp(next[run]);
  // which face: the page's pin, where the tray offers it (a held face needs
  // tie slots along the stretch: heldStretch is null without one), else the
  // face that looks up
  let asked = null;
  try { asked = typeof ctx?.trayFaceOf === 'function' ? ctx.trayFaceOf(cable, {item: t.item, via: t.via}) : null; } catch { asked = null; }
  const heldName = t.flipped ? 'top' : 'underside', restName = t.flipped ? 'underside' : 'top';
  const rail = railZOf(rack, t.item);
  if (asked === heldName) {
    const opts = {r, drape: drapeOf(cable, ctx), bend: bendOf(cable, ctx), rail};
    const h = heldStretch(t, a, b, opts);
    if (h) return {points: h.points, hold: h.points.map(() => true), face: heldName, role: 'held', ties: h.ties};
  }
  // the face that looks up: on the floor at the cable's radius, across the
  // tray at the side nearer the rail (position 1) of its rings' openings,
  // else of its largest floor rectangle; and through each ring standing
  // between the two ends, on its sill
  const opens = t.rings.filter(o => o.run === run);
  const f0 = t.floors.reduce((m, f) => ((f.x1 - f.x0) * (f.z1 - f.z0) > (m.x1 - m.x0) * (m.z1 - m.z0) ? f : m));
  const span = opens.length ? [Math.max(...opens.map(o => o.box[`${across}0`])), Math.min(...opens.map(o => o.box[`${across}1`]))]
    : [f0[`${across}0`], f0[`${across}1`]];
  const at = across === 'z' ? railSide(span[0], span[1], rail, r) : (span[0] + span[1]) / 2;
  const pt = (v, y) => (run === 'x' ? {x: v, y, z: at} : {x: at, y, z: v});
  const floorY = t.top + r;
  const points = [pt(a, floorY)], hold = [false];
  const between = opens.filter(o => Math.min(o.box[`${run}1`], Math.max(a, b)) > Math.max(o.box[`${run}0`], Math.min(a, b)) + 1e-6)
    .sort((p, q) => (a <= b ? p.box[`${run}0`] - q.box[`${run}0`] : q.box[`${run}0`] - p.box[`${run}0`]));
  // each ring from its approach point, clear of its band (#968), through its
  // opening on its sill, to the approach point past its far face. The
  // approach points are not clamped to the floor: they stand at the sill,
  // and a ring at the floor's end would have one pulled back into its band
  const dir = a <= b ? 1 : -1, off = r + CLEAR;
  for (const o of between) {
    const [near, far] = a <= b ? [o.box[`${run}0`], o.box[`${run}1`]] : [o.box[`${run}1`], o.box[`${run}0`]];
    const y = o.box.y0 + r;
    points.push(pt(near - dir * off, y), pt(clamp(near), y), pt(clamp(far), y), pt(far + dir * off, y));
    hold.push(false, true, true, true);
  }
  if (Math.abs(b - a) > 1e-6 || points.length > 1) { points.push(pt(b, floorY)); hold.push(false); }
  return {points, hold, face: restName, role: 'resting'};
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

// A path's length, as routedLength gives it: {measured, value} in metres:
// its points and its cable's end allowance at each end (routePath's
// `allowance`, endAllowance's figure; a path built by hand without one takes
// a cable with no media's).
export function pathLength(path) {
  if (!path) return null;
  const pts = path.points;
  let mm = 0;
  for (let k = 1; k < pts.length; k++) mm += dist(pts[k - 1], pts[k]);
  const end = typeof path.allowance === 'number' ? path.allowance : endAllowance(null);
  const measured = mm / 1000 + 2 * end;
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

// EVERY CORNER OF A CABLE'S PATH WITH LESS ROOM THAN ITS BEND RADIUS (#973,
// docs/cable-lay-design.md section 3.4), rack-wide: routePath's `bends`, each
// with a sentence, in the words of the bundle bend check. It warns and never
// refuses. A cable whose port is not found is not judged. `nameOf(itemId)`
// names an item.
export function bendFindings(rack, ctx, nameOf = id => id) {
  const lab = (w, c) => (w.end ? `its port on ${nameOf((w.end === 'a' ? c.a : c.b).item)}`
    : w.lane ? `${w.lane} U${uLabel(rack.frame, w.ru)}`
    : `${nameOf(w.item)} ${/^guide-(\d+)$/.test(w.via) ? `ring ${w.via.slice(6)}` : w.via}`);
  const an = t => (/^(8|1[18](\.|$))/.test(t) ? 'an' : 'a');
  return (rack.cables || []).flatMap(c => (routePath(rack, c, ctx)?.bends || []).map(f => {
    const [a, b] = f.between.map(w => lab(w, c));
    const where = a === b ? `at ${a}` : `between ${a} and ${b}`;
    const kind = c.type || c.media;
    const needs = `${kind ? `the cable (${kind})` : 'the cable'} needs ${f.need_mm} mm`;
    return {...f, text: f.room_mm === 0 ? `${c.id} doubles back ${where}, with no room for a bend; ${needs}.`
      : `${c.id} turns ${f.angle_deg} degrees ${where} with room for ${an(String(f.room_mm))} ${f.room_mm} mm bend; ${needs}, ${f.short_mm} mm short.`};
  }));
}

// A word for a part of a body, as a finding names it.
function partText(part) {
  const p = String(part || '');
  if (p === 'envelope' || p === 'body' || !p) return '';
  // a part of a ring's solid loop (#968): `ring/guide-3/front-leg` is "ring 3 front leg"
  const ring = /^ring\/([^/]+)\/(.+)$/.exec(p);
  if (ring) return `${/^guide-(\d+)$/.test(ring[1]) ? `ring ${ring[1].slice(6)}` : ring[1]} ${ring[2].replace(/-/g, ' ')}`;
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
    const advice = /^ring\//.test(String(f.part)) ? 'route it into the ring along its run, through its opening'
      : s && isFloor(s.box) && f.part !== 'envelope'
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
