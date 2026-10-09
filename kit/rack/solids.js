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
//   compiled faces; nothing states them) is those boxes: a sheet part's plates,
//   a vertical duct's walls and back, or a device with cable space inside its
//   envelope (its shell walls, its patch plate, its seated modules and what is
//   inside), each box with the pass-throughs that cut it as `holes`;
// - a sheet part without them (a catalogue older than `solids`) is open, as
//   every sheet part was before;
// - any other part with a width, height and depth is its envelope: a box
//   device, and a zero-U part that carries no lane (a PDU), as the fit check
//   takes it.
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
import {isZeroUPart, isNarrow, railOf} from './fit.js';
import {zeroUX, faceOfAt, carriesLane} from './zero-u.js';

// mm a detour keeps clear of a body, beyond the cable's own radius: the figure
// cable-geometry.js clearOf pushes a point out by.
export const CLEAR = 5;
// The depth of an upright a zero-U part stands centred on, behind its
// mounting face: the site's 3D scene stands one so, and the kit takes the same
// place for it (no source dimensions the gap; zero-u.js STANDOFF).
export const POST_D = 34;

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
    add(it.id, ownBoxes(c), itemPlacer(rack, it, c));
  }
  for (const z of zeroUOf(rack)) {
    const c = chassisOf(z.ref);
    if (!isZeroUPart(c) || !(pos(c.w) && pos(c.h) && pos(c.d))) continue;
    // a part that carries a lane is a pathway: its walls and back only, which
    // its `solids` give; without them it is open, never its envelope
    const list = carriesLane(c) && !Array.isArray(c.solids) ? [] : ownBoxes(c);
    add(z.id, list, zeroUPlacer(rack, z, c), {zeroU: true});
  }
  per.set(ctx, out);
  return out;
}

// ── a leg against a box ────────────────────────────────────────────────
const AX = ['x', 'y', 'z'];
const lerp = (a, b, t) => ({x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t});

// The stretch [t0, t1] of the leg a-b strictly inside the box, or null. A leg
// on a face, or outside it, is not inside.
export function inside(a, b, box, eps = EPS) {
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

// Every crossing of a path: per leg k (points[k] to points[k + 1]), each solid
// it crosses, as {leg: k, solid, at}.
export function pathCrossings(points, solids, opts = {}) {
  const out = [];
  for (let k = 1; k < points.length; k++)
    for (const x of legCrossings(points[k - 1], points[k], solids, opts)) out.push({leg: k - 1, solid: x.solid, at: x.at});
  return out;
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

// THE DETOUR for one leg a-b, as the points to add between them, or [] when it
// crosses nothing, or null when the rules cannot clear it (it is then left as
// drawn, and reported). In order of preference, each tried at both edges,
// nearer first, and taken when none of its three legs crosses any solid:
//   1. over the near edge: out past the body's front or back edge (for a
//      plate crossed top to bottom, a floor) or its top or bottom edge (for a
//      plate crossed front to back), clear by the cable's radius and CLEAR;
//   2. round the end: past its end along x, into the gutter;
//   3. front to back by a side lane: along `lanes` (the x of each lane),
//      when its ends are on opposite faces of the body.
// The detour moves each end straight along that axis to the plane, so the two
// moves never enter the body (each end is outside it on another axis) and the
// run between them is outside it on this one.
export function detour(a, b, solids, {diameter = 0, lanes = []} = {}) {
  const first = legCrossings(a, b, solids, {diameter})[0];
  if (!first) return [];
  const box = first.solid.box, m = diameter / 2 + CLEAR;
  const across = crossAxis(a, b, box);
  const edge = across === 'z' ? 'y' : 'z';
  const end = across === 'x' ? 'y' : 'x';
  const planes = k => [box[`${k}0`] - m, box[`${k}1`] + m]
    .sort((u, v) => Math.abs(a[k] - u) + Math.abs(b[k] - u) - Math.abs(a[k] - v) - Math.abs(b[k] - v));
  const opposite = (a.z <= box.z0 && b.z >= box.z1) || (b.z <= box.z0 && a.z >= box.z1);
  const tries = [...planes(edge).map(v => [edge, v]), ...planes(end).map(v => [end, v]),
    ...(opposite ? [...lanes].sort((u, v) => Math.abs(a.x - u) - Math.abs(a.x - v)).map(v => ['x', v]) : [])];
  const clear = (p, q) => gap(p, q) < 1e-9 || !legCrossings(p, q, solids, {diameter}).length;
  for (const [k, v] of tries) {
    const p1 = set(a, k, v), p2 = set(b, k, v);
    if (clear(a, p1) && clear(p1, p2) && clear(p2, b)) return [p1, p2].filter((p, i) => gap(p, i ? b : a) > 1e-9);
  }
  return null;
}

// A word for a part of a body, as a sentence names it.
const SHELL = {top: 'top', bottom: 'bottom', left: 'left side', right: 'right side', rear: 'rear wall'};
export function partText(part) {
  const p = String(part || '');
  if (p === 'envelope' || p === 'body' || !p) return '';
  if (p === 'plate') return 'patch plate';
  if (p.startsWith('shell/')) return SHELL[p.slice(6)] ?? p.slice(6);
  return p.split('/')[0].replace(/--.*$/, '').replace(/-/g, ' ');
}
// A plate a cable meets from above or below: thinner in y than across.
export const isFloor = box => (box.y1 - box.y0) <= Math.min(box.x1 - box.x0, box.z1 - box.z0);
