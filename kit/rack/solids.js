// kit/rack/solids.js
// SOLID BODIES (docs/cable-lay-design.md section 1, #949). Pure, like fit.js.
//
// Every body in the rack is solid to a route. A cable crosses one only through
// a declared opening: a ring (not solid at all), a duct (whose fingers and
// clips are not solid, so a cable enters its channel through a finger gap), or
// a pass-through whose smaller side fits the cable's diameter. A tie slot is
// never an opening: it is cut in a plate, and the plate stays whole.
//
// WHAT IS SOLID, per placed item or zero-U part, from its rack.json entry
// (`ctx.chassisOf(ref)`):
// - an entry that carries `solids` (rack_solids.py derives them from the
//   compiled faces; nothing states them) is those boxes: a sheet part's plates
//   or a vertical duct's walls and back, each box with the pass-throughs that
//   cut it as `holes` (a box device with cable space inside its envelope will
//   carry them the same way, with step 6 of the note);
// - a sheet part, or a zero-U part that carries a lane, without them (a
//   catalogue older than `solids`) is open, as every sheet part was before;
// - any other part with a width, height and depth is its envelope: a box
//   device, and a zero-U part that carries no lane (a PDU), as the fit check
//   takes it. The lane beside a PDU runs outboard of it (route.js laneXAt).
// The frame of an entry's `solids` is the one the rack products note gives
// hosts: x from the left of the part as seen from its front, y up from its
// bottom, z back from its front (for a rack-face part, its outward face). Here
// each is placed in rack coordinates as route.js measures them: x from the
// centre line, right as seen from the front; y up from the floor of U1; z 0 on
// the front rail plane, negative toward the rear.
//
// THE CHECK is on the kit path (route.js routePath), which both drawings
// follow: a leg of a cable's centre line crosses a solid when some stretch of
// it lies strictly inside the box. A centre line on a face, or one radius
// outside it (a cable lying against a plate, on either face), is not inside.
// A crossing whose stretch inside lies within a hole the cable fits is through
// that pass-through, and is no crossing.
//
// What a later step adds (the strapped stack under a held face, section 1.3
// rule 1 of the note) is one more solid in the list solidsOf returns: the
// check and the detours read only boxes.

import {RU, SIDES} from './rails.js';
import {zeroUOf, zeroUBottom} from './model.js';
import {isZeroUPart, railOf} from './fit.js';
import {zeroUX, faceOfAt, carriesLane} from './zero-u.js';

// mm a detour keeps clear of a body, beyond the cable's own radius: the figure
// cable-geometry.js clearOf pushes a point out by.
export const CLEAR = 5;
// The depth of an upright a zero-U part stands centred on, behind its
// mounting face: the site's 3D scene stands one so, and the kit takes the same
// place for it (no source dimensions the gap; zero-u.js STANDOFF).
const POST_D = 34;
// How many times a detour may itself be gone round, when its own legs meet a
// second body, before the leg is left as drawn and reported.
const DEPTH = 3;

const EPS = 1e-6;
const num = v => (typeof v === 'number' && Number.isFinite(v) ? v : Number(v));
const pos = v => Number.isFinite(num(v)) && num(v) > 0;
const railDepthOf = f => (f?.kind === 'two-post' ? 0 : Number(f?.railDepth) || 0);

// A part's own boxes: its `solids`, else its envelope, else none.
function ownBoxes(c) {
  if (!c) return [];
  if (Array.isArray(c.solids)) return c.solids.filter(s => s?.box);
  if (c.shell === 'sheet') return [];
  if (!(pos(c.w) && pos(c.h) && pos(c.d))) return [];
  return [{part: 'envelope', box: {x: 0, y: 0, z: 0, w: num(c.w), h: num(c.h), d: num(c.d)}}];
}

// Placing a part: its frame turned into the rack's. `place` maps a box in the
// part's frame to {x0, x1, y0, y1, z0, z1} in rack coordinates.
function placer({cx, w, y0, h, zFront, outward, mirror, flipY}) {
  // outward: +1 when the part's z (back from its front) runs toward -z in the
  // rack (a part looking out of the front), -1 when toward +z (one looking out
  // of the back)
  return b => {
    const bx0 = mirror ? w - b.x - b.w : b.x, by0 = flipY ? h - b.y - b.h : b.y;
    const za = zFront - outward * b.z, zb = zFront - outward * (b.z + b.d);
    return {x0: cx - w / 2 + bx0, x1: cx - w / 2 + bx0 + b.w, y0: y0 + by0, y1: y0 + by0 + b.h,
            z0: Math.min(za, zb), z1: Math.max(za, zb)};
  };
}

function itemPlacer(rack, it, c) {
  const f = rack.frame, rear = it.face === 'rear', turned = !!it.turned;
  const w = num(c.w), h = num(c.h), d = num(c.d);
  const plane = rear ? -railDepthOf(f) : 0;
  // A rack-face part has its mounting face on the rail plane and its body
  // outward; a rack device's body runs between the rails (rack3d.js, route.js
  // pointOf).
  const rackFace = c.mount === 'rack-face';
  // where its front (z 0 of its frame) is, and which way its depth runs
  let zFront, outward;
  if (rackFace) { zFront = rear ? plane - d : plane + d; outward = rear ? -1 : 1; }
  else {
    // a rack device looks out of the face it is mounted on, or away from it
    // when turned: then its front is the far end of its depth
    outward = rear === turned ? 1 : -1;
    zFront = turned ? (rear ? plane + d : plane - d) : plane;
  }
  // seen from the rack's front, a part looking out of the back is mirrored
  const mirror = outward === -1;
  // a narrow rack-face part on one rail stands over its hole line, and on the
  // right rail is turned end over end (railOf, as the elevation and the 3D
  // scene place it)
  const rail = railOf(it, () => c);
  const left = rail ? (rail === 'left') === !rear : null;
  const cx = rail ? (left ? SIDES[0] : SIDES[1]).hole : 0;
  const flip = rail === 'right';
  return placer({cx, w, y0: (it.ru - 1) * RU, h, zFront, outward, mirror: flip ? !mirror : mirror, flipY: flip});
}

function zeroUPlacer(rack, z, c) {
  const f = rack.frame, rear = faceOfAt(z.at) === 'rear';
  const w = num(c.w), h = num(c.h), d = num(c.d);
  // centred on its upright's depth, behind the mounting face; a rear upright
  // carries its part facing rearward
  const zc = rear ? -railDepthOf(f) + POST_D / 2 : -POST_D / 2;
  return placer({cx: zeroUX(z, () => c), w, y0: (zeroUBottom(z) - 1) * RU, h,
                 zFront: rear ? zc - d / 2 : zc + d / 2, outward: rear ? -1 : 1, mirror: rear, flipY: false});
}

const memo = new WeakMap();

// EVERY SOLID IN THE RACK, placed: [{item, part, box, holes: [{via, box,
// size}], zeroU?}], each box {x0, x1, y0, y1, z0, z1} in rack mm. `item` is the
// rack item's or the zero-U part's id. Read once per rack and context.
export function solidsOf(rack, ctx) {
  const chassisOf = ctx?.chassisOf;
  if (typeof chassisOf !== 'function') return [];
  let per = memo.get(rack);
  if (!per) memo.set(rack, per = new WeakMap());
  if (per.has(ctx)) return per.get(ctx);
  const out = [];
  // `away`: +1 when the part's outward face (a tray's front edge, section 1.3
  // rule 1) looks toward +z, the front of the rack; -1 toward the rear
  const add = (id, list, place, extra = {}) => {
    for (const s of list) {
      out.push({item: id, part: s.part ?? 'body', box: place(s.box), ...extra,
                holes: (s.holes || []).filter(hl => hl?.box).map(hl => ({via: hl.via, box: place(hl.box),
                  size: Array.isArray(hl.size) ? hl.size : [hl.box.w, hl.box.h]}))});
    }
  };
  for (const it of rack.items || []) {
    const c = chassisOf(it.ref);
    if (!c || !(pos(c.w) && pos(c.h) && pos(c.d)) || isZeroUPart(c)) continue;
    add(it.id, ownBoxes(c), itemPlacer(rack, it, c), {away: it.face === 'rear' ? -1 : 1});
  }
  for (const z of zeroUOf(rack)) {
    const c = chassisOf(z.ref);
    if (!isZeroUPart(c) || !(pos(c.w) && pos(c.h) && pos(c.d))) continue;
    // a part that carries a lane is a pathway: its walls and back only, which
    // its `solids` give; without them it is open, never its envelope
    const list = carriesLane(c) && !Array.isArray(c.solids) ? [] : ownBoxes(c);
    add(z.id, list, zeroUPlacer(rack, z, c), {zeroU: true, away: faceOfAt(z.at) === 'rear' ? -1 : 1});
  }
  per.set(ctx, out);
  return out;
}

// ── a leg against a box ────────────────────────────────────────────────
const AX = ['x', 'y', 'z'];
const lerp = (a, b, t) => ({x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t});

// The stretch [t0, t1] of the leg a-b strictly inside the box, or null. A leg
// on a face, or outside it, is not inside.
function inside(a, b, box, eps = EPS) {
  let t0 = 0, t1 = 1;
  for (const k of AX) {
    const lo = box[`${k}0`] + eps, hi = box[`${k}1`] - eps;
    if (!(hi > lo)) return null;
    const p = a[k], dv = b[k] - a[k];
    if (Math.abs(dv) < 1e-12) { if (p <= lo || p >= hi) return null; continue; }
    let u = (lo - p) / dv, v = (hi - p) / dv;
    if (u > v) [u, v] = [v, u];
    t0 = Math.max(t0, u); t1 = Math.min(t1, v);
    if (t1 - t0 <= 1e-9) return null;
  }
  return [t0, t1];
}

const within = (p, box) => AX.every(k => p[k] >= box[`${k}0`] - EPS && p[k] <= box[`${k}1`] + EPS);

// Every solid the leg a-b crosses, in the order it meets them: [{solid, t0,
// t1, at}], `at` where it enters. A stretch that lies within a hole the
// cable's `diameter` (mm) fits is through that pass-through, and is left out.
export function legCrossings(a, b, solids, {diameter = 0} = {}) {
  const out = [];
  for (const s of solids) {
    const span = inside(a, b, s.box);
    if (!span) continue;
    const p = lerp(a, b, span[0]), q = lerp(a, b, span[1]);
    const through = (s.holes || []).some(h => within(p, h.box) && within(q, h.box)
      && diameter <= Math.min(...h.size) + 1e-9);
    if (!through) out.push({solid: s, t0: span[0], t1: span[1], at: p});
  }
  return out.sort((x, y) => x.t0 - y.t0);
}

// ── going around (section 1.3) ─────────────────────────────────────────
// Which axis a leg crosses a box along: the one it goes from one side of the
// box to the other on, the thinnest such; else the box's thinnest axis.
function crossAxis(a, b, box) {
  const ext = k => box[`${k}1`] - box[`${k}0`];
  const across = AX.filter(k => (a[k] <= box[`${k}0`] && b[k] >= box[`${k}1`]) || (b[k] <= box[`${k}0`] && a[k] >= box[`${k}1`]));
  const pool = across.length ? across : AX;
  return pool.reduce((m, k) => (ext(k) < ext(m) ? k : m), pool[0]);
}
const set = (p, k, v) => ({...p, [k]: v});
const gap = (p, q) => Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);

// The ways round one body, as tiers in order of preference, each way [axis,
// plane]:
//   1. over the near edge: for a plate crossed top to bottom (a floor), out
//      past its FRONT edge, the one facing away from the rail it is fixed to
//      (`away`), and only then its back edge; for a body crossed front to
//      back, its top or bottom edge;
//   2. round the end: past either end along x, into the gutter;
//   3. front to back by a side lane (`lanes`, the x of each lane at that
//      height), when the leg's ends are on opposite faces of the body.
// A ZERO-U PART is gone round on the side that faces into the rack first (its
// back, toward the rails: the side channel a cable runs down), and over its
// outward face, where a PDU's plugs stand outside the frame, only when
// nothing else clears it. Going round its back, a cable from a port inboard
// of it turns the corner: along x to the gap beside the part, into the rack
// past its back, across, and out again on the far side (a corner way).
// Every plane is clear of the body by the cable's radius and CLEAR. Each way
// is the list of points it adds between a and b.
const plane = (p, k, v) => set(p, k, v);
function waysRound(a, b, solid, {diameter, lanes}) {
  const box = solid.box, m = diameter / 2 + CLEAR;
  const across = crossAxis(a, b, box);
  const edge = across === 'z' ? 'y' : 'z';
  const end = across === 'x' ? 'y' : 'x';
  const flat = (k, v) => [plane(a, k, v), plane(b, k, v)];
  const both = k => [flat(k, box[`${k}0`] - m), flat(k, box[`${k}1`] + m)];
  // the plane on a point's side of the body along an axis
  const near = (p, k) => (p[k] <= (box[`${k}0`] + box[`${k}1`]) / 2 ? box[`${k}0`] - m : box[`${k}1`] + m);
  const corner = (k, v) => { const pa = plane(a, across, near(a, across)), pb = plane(b, across, near(b, across));
    return [pa, plane(pa, k, v), plane(pb, k, v), pb]; };
  const front = solid.away === -1 ? box.z0 - m : box.z1 + m, back = solid.away === -1 ? box.z1 + m : box.z0 - m;
  const opposite = (a.z <= box.z0 && b.z >= box.z1) || (b.z <= box.z0 && a.z >= box.z1);
  const zeroU = solid.zeroU === true && edge === 'z';
  const tiers = edge === 'z' && across === 'y' ? [[flat('z', front)], [flat('z', back)]]
    : zeroU ? [[flat('z', back), corner('z', back)]] : [both(edge)];
  tiers.push(both(end));
  if (opposite) tiers.push([...new Set(lanes)].map(v => flat('x', v)));
  if (zeroU) tiers.push([flat('z', front), corner('z', front)]);
  return tiers;
}

const lengthOf = pts => pts.reduce((s, p, i) => (i ? s + gap(pts[i - 1], p) : 0), 0);

// THE DETOUR for one leg a-b, as the points to add between them: [] when it
// crosses nothing, null when the rules cannot clear it (it is then left as
// drawn, and reported). The first body the leg meets is gone round by the
// ways of waysRound, tier by tier: a way whose three legs cross nothing, or
// whose legs clear that body and meet others that can be gone round in turn
// (at most DEPTH deep), resolves; of the ways that resolve in the first tier
// that has any, the shortest is taken. Each end moves straight along one axis
// to the plane, so the two moves never enter the body (each end is outside it
// on another axis) and the run between them is outside it on this one.
// `lanes` is a function of the leg's height, y, giving the x of each side
// lane there (route.js laneXAt), or a list.
export function detour(a, b, solids, {diameter = 0, lanes = []} = {}) {
  const lanesAt = typeof lanes === 'function' ? lanes : () => lanes;
  const clear = (u, w, only = null) => gap(u, w) < 1e-9 || !legCrossings(u, w, only ? [only] : solids, {diameter}).length;
  const go = (p, q, depth) => {
    const first = legCrossings(p, q, solids, {diameter})[0];
    if (!first) return [];
    for (const tier of waysRound(p, q, first.solid, {diameter, lanes: lanesAt((p.y + q.y) / 2)})) {
      let best = null;
      for (const way of tier) {
        const chain = [p, ...way, q], legs = chain.slice(1).map((w, i) => [chain[i], w]);
        let pts = null;
        if (legs.every(([u, w]) => clear(u, w))) pts = way;
        else if (depth > 0 && legs.every(([u, w]) => clear(u, w, first.solid))) {
          const parts = legs.map(([u, w]) => (gap(u, w) < 1e-9 ? [] : go(u, w, depth - 1)));
          if (!parts.some(x => x === null)) pts = parts.flatMap((part, i) => (i < way.length ? [...part, way[i]] : part));
        }
        if (!pts) continue;
        pts = pts.filter((x, i, all) => gap(x, i ? all[i - 1] : p) > 1e-9 && gap(x, q) > 1e-9);
        const len = lengthOf([p, ...pts, q]);
        if (!best || len < best.len - 1e-9) best = {pts, len};
      }
      if (best) return best.pts;
    }
    return null;
  };
  const pts = go(a, b, DEPTH);
  if (!pts?.length) return pts;
  // A point whose neighbours see each other clear is not needed: a way round
  // one body and then another can step back on itself, and is pulled taut.
  const all = [a, ...pts, b];
  for (let i = 1; i < all.length - 1;) {
    if (clear(all[i - 1], all[i + 1])) all.splice(i, 1); else i++;
  }
  return all.slice(1, -1);
}
