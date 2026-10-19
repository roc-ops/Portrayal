// kit/rack/solids.js
// SOLID BODIES (docs/cable-lay-design.md section 1, #949). Pure, like fit.js.
//
// Every body in the rack is solid to a route. A cable crosses one only through
// a declared opening: a ring (through its opening; since #968 a ring whose
// contract says what of its loop is solid is solid round it, its legs, bar
// and seat in rack.json's `solids` as `ring/<id>/<part>`), a duct (whose fingers and
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
import {zeroUOf, zeroUBottomMm} from './model.js';
import {isZeroUPart, railOf, itemBox, setbackOf, isQuarter} from './fit.js';
import {rollOf} from './model.js';
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
  // rolled a quarter turn (`roll`), its width stands up the rack and its
  // height lies across the opening: the box it is placed as
  const q = isQuarter(it);
  const w = num(q ? c.h : c.w), h = num(q ? c.w : c.h), d = num(c.d);
  // its faceplate stands its setback behind the rail, into the rack (0 for a
  // part on the rail face)
  const s = setbackOf(rack, it, () => c);
  const plane = rear ? -railDepthOf(f) + s : 0 - s;
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
  const rail = q ? null : railOf(it, () => c);
  const left = rail ? (rail === 'left') === !rear : null;
  const cx = rail ? (left ? SIDES[0] : SIDES[1]).hole : 0;
  // ... and so is any part rolled 180 degrees, so one that is both is upright again
  const flip = (rail === 'right') !== (rollOf(it) === 180);
  // where the body stands is fit.js itemBox's: centred in its span, always
  return placer({cx, w, y0: itemBox(rack, it, () => c).y0, h, zFront, outward, mirror: flip ? !mirror : mirror, flipY: flip});
}

function zeroUPlacer(rack, z, c) {
  const f = rack.frame, rear = faceOfAt(z.at) === 'rear';
  const w = num(c.w), h = num(c.h), d = num(c.d);
  // centred on its upright's depth, behind the mounting face; a rear upright
  // carries its part facing rearward
  const zc = rear ? -railDepthOf(f) + POST_D / 2 : -POST_D / 2;
  return placer({cx: zeroUX(z, () => c), w, y0: zeroUBottomMm(z), h,
                 zFront: rear ? zc - d / 2 : zc + d / 2, outward: rear ? -1 : 1, mirror: rear, flipY: false});
}

// A POINT ON A PANEL OF A PART BESIDE THE RACK (P-0019), in rack mm: `x`
// across its panel as drawn and `y` up from its bottom, on its front panel
// (`view` 'front', the face it looks out of) or its back. Placed as its body
// is, so an outlet is where the PDU drawn round it is. null for a part the
// catalogue gives no size.
export function zeroUPanelPoint(rack, z, c, {x, y}, view = 'front') {
  if (!(pos(c?.w) && pos(c?.h) && pos(c?.d))) return null;
  const back = view === 'rear';
  // the back panel is drawn as seen from behind: its x runs the other way
  const b = zeroUPlacer(rack, z, c)({x: back ? num(c.w) - x : x, y, z: back ? num(c.d) : 0, w: 0, h: 0, d: 0});
  return {x: b.x0, y: b.y0, z: b.z0};
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
    // ROLLED A QUARTER TURN it is an outline: one box, its height and width
    // swapped, centred across the opening, with none of its own parts
    const list = isQuarter(it) ? [{part: 'envelope', box: {x: 0, y: 0, z: 0, w: num(c.h), h: num(c.w), d: num(c.d)}}] : ownBoxes(c);
    add(it.id, list, itemPlacer(rack, it, c), {away: it.face === 'rear' ? -1 : 1});
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

// EVERY TRAY IN THE RACK, placed (docs/cable-lay-design.md sections 2 and 3):
// [{item, via, top, under, thickness, flipped, run, lip, slack?, floors,
// ties, rings}], from each item's rack.json `trays`, through the same placing
// as its solids. In rack mm:
// - `top` is the height of the face that looks up (the resting face) and
//   `under` of the face that looks down (the held face), so `top - under` is
//   the plate's thickness; `flipped` says the part's own top is the one that
//   looks down (a part turned end over end in its face, as a narrow part on
//   the right rail is), so the names `top` and `underside` of the part swap
//   roles;
// - `run` is the axis cables lie along, 'x' or 'z';
// - `floors` and `ties` are plan rectangles {x0, x1, z0, z1};
// - `rings` are the openings of the rings standing on the floor, {via, run,
//   box: {x0, x1, y0, y1, z0, z1}}: a cable resting in one lies on y0, the
//   inside edge that is lowest as mounted.
// A zero-U part carries no tray today; a catalogue without `trays` gives none.
const trayMemo = new WeakMap();
export function traysOf(rack, ctx) {
  const chassisOf = ctx?.chassisOf;
  if (typeof chassisOf !== 'function') return [];
  let per = trayMemo.get(rack);
  if (!per) trayMemo.set(rack, per = new WeakMap());
  if (per.has(ctx)) return per.get(ctx);
  const out = [];
  for (const it of rack.items || []) {
    const c = chassisOf(it.ref);
    if (!c || !Array.isArray(c.trays) || !(pos(c.w) && pos(c.h) && pos(c.d)) || isZeroUPart(c)) continue;
    if (isQuarter(it)) continue;             // an outline has no tray to lie on
    const place = itemPlacer(rack, it, c);
    const plan = b => { const p = place(b); return {x0: p.x0, x1: p.x1, z0: p.z0, z1: p.z1, y0: p.y0, y1: p.y1}; };
    for (const t of c.trays) {
      const floors = (t.floor || []).filter(b => b && pos(b.w) && pos(b.d)).map(plan);
      if (!floors.length) continue;
      const th = pos(t.thickness) ? num(t.thickness) : 1;
      // the plate, placed: its upper side rests, its lower side is held
      const plate = place({x: 0, y: num(t.top) - th, z: 0, w: 1, h: th, d: 1});
      // a part's own y up is down in the rack when its plate's own top is placed below its own bottom
      const probe = place({x: 0, y: 0, z: 0, w: 1, h: 1, d: 1}), up = place({x: 0, y: 1, z: 0, w: 1, h: 1, d: 1});
      const flipped = up.y0 < probe.y0;
      // the axis cables lie along, as placed: the part's x stays the rack's x
      // (a turn in the face of 180 degrees keeps it), its z is the rack's z
      const run = t.run === 'z' || t.run === 'y' ? 'z' : 'x';
      out.push({item: it.id, via: t.id, top: plate.y1, under: plate.y0, thickness: th, flipped, run,
        lip: Number(t.lip) || 0, ...(t.slack ? {slack: t.slack} : {}), floors,
        ties: (t.ties || []).filter(b => b && pos(b.w) && pos(b.d)).map(plan),
        rings: (t.rings || []).filter(r => r?.box).map(r => ({via: r.via, run: r.run === 'z' ? 'z' : 'x', box: place(r.box)}))});
    }
  }
  per.set(ctx, out);
  return out;
}

// ── a leg against a box ────────────────────────────────────────────────
const AX = ['x', 'y', 'z'];
const lerp = (a, b, t) => ({x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t, z: a.z + (b.z - a.z) * t});

// The stretch [t0, t1] of the leg a-b strictly inside the box, or null. A leg
// on a face, or outside it, is not inside. The box is given as its six
// numbers, so that a list of boxes can be read from one flat array (below).
function slab(t, p, dv, lo, hi) {
  if (!(hi > lo)) return false;
  if (Math.abs(dv) < 1e-12) return !(p <= lo || p >= hi);
  let u = (lo - p) / dv, v = (hi - p) / dv;
  if (u > v) { const w = u; u = v; v = w; }
  t[0] = Math.max(t[0], u); t[1] = Math.min(t[1], v);
  return !(t[1] - t[0] <= 1e-9);
}
function inside(a, b, x0, x1, y0, y1, z0, z1) {
  const t = [0, 1];
  return slab(t, a.x, b.x - a.x, x0 + EPS, x1 - EPS) && slab(t, a.y, b.y - a.y, y0 + EPS, y1 - EPS)
    && slab(t, a.z, b.z - a.z, z0 + EPS, z1 - EPS) ? t : null;
}

const within = (p, box) => AX.every(k => p[k] >= box[`${k}0`] - EPS && p[k] <= box[`${k}1`] + EPS);

// A PART OF A RING'S SOLID LOOP (#968, docs/cable-lay-design.md section 3.3):
// rack.json names each `ring/<id>/<part>`. A cable passes a ring close by on
// purpose, through its opening and on its sill, so a ring's parts are met by
// the cable's tube and not its centre line: each is taken grown by the
// cable's radius, and a leg that would graze one crosses it. A cable lying in
// the opening, on the sill and against a leg, runs along the faces of the
// grown parts and crosses nothing.
// A ZERO-U PART (`zeroU` on the solid, solidsOf) is met by the tube as well:
// a cable going to the lane beside a zero-U PDU passes its corner close by,
// and one whose centre line clears the corner by a fraction of a millimetre
// would otherwise run across the PDU's outlet face, which section 1.3 rule 4
// keeps for the last resort. Its pass-through holes are judged on the tube
// as well (#992, `legCrossings`). Every other plate or envelope is met by the
// centre line, as before: a cable lies against those at its radius, and a
// tube touching a plate the cable rests on is contact, not a fault. A plate
// it does not rest on is left to the lay work (#986).
const RING_PART = /^ring\/[^/]+\/./;
// The box of a solid as a cable of `diameter` meets it, kept for the solid
// and the diameter it was last asked for: a lay asks for the same few
// thousand times.
const metOf = new WeakMap();
const met = (s, diameter) => {
  const kept = metOf.get(s);
  if (kept && kept.diameter === diameter && kept.of === s.box) return kept.box;
  let box = s.box;
  if ((RING_PART.test(String(s?.part ?? '')) || s?.zeroU === true) && diameter > 0) {
    const r = diameter / 2, b = s.box;
    box = {x0: b.x0 - r, x1: b.x1 + r, y0: b.y0 - r, y1: b.y1 + r, z0: b.z0 - r, z1: b.z1 + r};
  }
  if (s !== null && typeof s === 'object') metOf.set(s, {diameter, of: s.box, box});
  return box;
};

// A hole's box less `r` on each side across the hole: the two axes other than
// the plate's thinnest, which is the way through it and is left as it is (the
// stretch is measured inside the true plate, its ends on the plate's faces). A
// side shorter than 2r closes to its middle.
function shrunk(hole, plate, r) {
  const thin = AX.reduce((m, k) => (plate[`${k}1`] - plate[`${k}0`] < plate[`${m}1`] - plate[`${m}0`] ? k : m), 'x');
  const out = {...hole};
  for (const k of AX) {
    if (k === thin) continue;
    const lo = hole[`${k}0`] + r, hi = hole[`${k}1`] - r, mid = (hole[`${k}0`] + hole[`${k}1`]) / 2;
    out[`${k}0`] = lo <= hi ? lo : mid;
    out[`${k}1`] = lo <= hi ? hi : mid;
  }
  return out;
}

// A LIST OF SOLIDS, READY TO BE CROSSED (kit 0.25.0). A lay asks which solids
// a leg crosses some thousands of times, of a list that is the same every
// time (solidsOf's, kept per rack and context), and almost every solid is
// nowhere near the leg. So for a list and a diameter the boxes are laid out
// once, flat, with the solids of one item (which follow each other in the
// list) under one box that holds them all: a leg that stays out of an item's
// box crosses none of its parts, and a part is passed over on the same test
// before its stretch is worked out. Nothing is decided here that `inside`
// would not decide: a leg wholly to one side of a box on an axis has no
// stretch inside it. The order of the list is kept, so the answer is the
// same list in the same order. A short list is read as it is.
// THE LIST IS NOT CHANGED IN PLACE: the boxes are laid out for the list as it
// was when first read, and found again by the list itself. A list of another
// length, or whose first or last solid or their boxes are other objects, is
// laid out again; a solid swapped or moved in the middle of a list is not
// seen (to look at every solid on every leg would cost what this saves), so
// a caller with other solids hands in another list, as solidsOf does.
const INDEX_FROM = 12;
const indexOf = new WeakMap();
function indexed(solids, diameter) {
  let per = indexOf.get(solids);
  if (!per) indexOf.set(solids, per = new Map());
  let ix = per.get(diameter);
  const n = solids.length, s0 = solids[0], s1 = solids[n - 1];
  if (ix && ix.n === n && ix.s0 === s0 && ix.s1 === s1 && ix.b0 === s0?.box && ix.b1 === s1?.box) return ix;
  const boxes = new Float64Array(6 * n), groups = [];
  let g = null;
  solids.forEach((s, i) => {
    const b = met(s, diameter);
    boxes.set([b.x0, b.x1, b.y0, b.y1, b.z0, b.z1], 6 * i);
    if (!g || g.item !== s.item) groups.push(g = {item: s.item, from: i, to: i, x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity, z0: Infinity, z1: -Infinity, all: false});
    g.to = i + 1;
    // a box with a number that is not one is never passed over
    if (![b.x0, b.x1, b.y0, b.y1, b.z0, b.z1].every(Number.isFinite)) g.all = true;
    g.x0 = Math.min(g.x0, b.x0); g.x1 = Math.max(g.x1, b.x1); g.y0 = Math.min(g.y0, b.y0); g.y1 = Math.max(g.y1, b.y1);
    g.z0 = Math.min(g.z0, b.z0); g.z1 = Math.max(g.z1, b.z1);
  });
  per.set(diameter, ix = {n, boxes, groups, s0, s1, b0: s0?.box, b1: s1?.box});
  return ix;
}

// Every solid the leg a-b crosses, in the order it meets them: [{solid, t0,
// t1, at}], `at` where it enters. A stretch that lies within a hole the
// cable's `diameter` (mm) fits is through that pass-through, and is left out.
// A ring's part is crossed where the cable's tube would touch it (`met`).
export function legCrossings(a, b, solids, {diameter = 0} = {}) {
  const out = [];
  const hit = (s, span) => {
    const p = lerp(a, b, span[0]), q = lerp(a, b, span[1]);
    // A hole is judged on the stretch inside the TRUE plate. A solid met grown
    // by the cable's radius (`met`: a zero-U part, a ring's part) has a stretch
    // that starts and ends up to r outside the plate, so outside the depth of
    // a hole cut through it, and no cable would pass any hole.
    const grown = met(s, diameter) !== s.box;
    const own = grown ? inside(a, b, s.box.x0, s.box.x1, s.box.y0, s.box.y1, s.box.z0, s.box.z1) : null;
    const [hp, hq] = own ? [lerp(a, b, own[0]), lerp(a, b, own[1])] : [p, q];
    // A ZERO-U PART's hole is judged on the tube too (#992): its box is taken
    // less the cable's radius across the hole, so the tube fits inside it and
    // does not lie a third in the wall. Not along the way through the plate.
    const through = (s.holes || []).some(h => {
      const box = s.zeroU === true && diameter > 0 ? shrunk(h.box, s.box, diameter / 2) : h.box;
      return within(hp, box) && within(hq, box) && diameter <= Math.min(...h.size) + 1e-9;
    });
    if (!through) out.push({solid: s, t0: span[0], t1: span[1], at: p});
  };
  if (!Array.isArray(solids) || solids.length < INDEX_FROM) {
    for (const s of solids) {
      const m = met(s, diameter), span = inside(a, b, m.x0, m.x1, m.y0, m.y1, m.z0, m.z1);
      if (span) hit(s, span);
    }
    return out.sort((x, y) => x.t0 - y.t0);
  }
  const {boxes: B, groups} = indexed(solids, diameter);
  // the leg's own box: a comparison with a number that is not one is false,
  // so such a leg is passed over by nothing
  const lx = Math.min(a.x, b.x), hx = Math.max(a.x, b.x), ly = Math.min(a.y, b.y), hy = Math.max(a.y, b.y),
    lz = Math.min(a.z, b.z), hz = Math.max(a.z, b.z);
  for (const g of groups) {
    if (!g.all && (hx < g.x0 || lx > g.x1 || hy < g.y0 || ly > g.y1 || hz < g.z0 || lz > g.z1)) continue;
    for (let i = g.from, o = 6 * g.from; i < g.to; i++, o += 6) {
      if (hx < B[o] || lx > B[o + 1] || hy < B[o + 2] || ly > B[o + 3] || hz < B[o + 4] || lz > B[o + 5]) continue;
      const span = inside(a, b, B[o], B[o + 1], B[o + 2], B[o + 3], B[o + 4], B[o + 5]);
      if (span) hit(solids[i], span);
    }
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
// ROOM FOR THE BENDS (#973): a way turns the cable where each end's move
// meets the plane, and where that move starts when the end is itself a
// corner, so a move shorter than `room` (route.js gives twice the cable's
// installed bend radius, the two corners' share of one leg) leaves neither
// turn its radius. With `room`, a plane that an end reaches by a shorter move
// stands further out, `room` from that end; an end that is already beyond the
// plane is left alone, and so is a plane a lane sets. The plane only moves
// away from the body, so what it cleared it still clears.
// BEHIND THE BACK EDGE (#1026). Rule 1 takes a floor's front edge first
// because a port at the rail plane ends its plug under the floor: the cable
// comes out past the front edge and back in over it. A device set back from
// its rails ends its plug behind the floor's BACK edge instead, and the near
// edge is then that one: the cable rises behind the plate and comes forward
// onto it, one slight turn where the other way is out, up and back in, three
// right angles. With `rear`, a floor one of whose ends stands at or behind
// its back plane (the back edge less the cable's radius and CLEAR) is gone
// round there first, by ONE point: on the back plane, on the far end's side
// of the plate and clear of it by the same, and along x where a taut line
// from end to end would cross that edge. route.js offers it only where the
// front edge leaves a corner short (ROOM ROUND A BODY), so a path with room
// is as it was.
const plane = (p, k, v) => set(p, k, v);
function waysRound(a, b, solid, {diameter, lanes, room = 0, rear = false}) {
  const box = met(solid, diameter), m = diameter / 2 + CLEAR;
  const out = (k, v) => {
    if (!(room > 0)) return v;
    const s = v >= (box[`${k}0`] + box[`${k}1`]) / 2 ? 1 : -1;
    for (const p of [a, b, a]) {
      const d = s * (v - p[k]);
      if (d > 1e-6 && d < room - 1e-6) v = p[k] + s * room;
    }
    return v;
  };
  const across = crossAxis(a, b, box);
  const edge = across === 'z' ? 'y' : 'z';
  const end = across === 'x' ? 'y' : 'x';
  const flat = (k, v, lane = false) => { const u = lane ? v : out(k, v); return [plane(a, k, u), plane(b, k, u)]; };
  const both = k => [flat(k, box[`${k}0`] - m), flat(k, box[`${k}1`] + m)];
  // the plane on a point's side of the body along an axis
  const near = (p, k) => (p[k] <= (box[`${k}0`] + box[`${k}1`]) / 2 ? box[`${k}0`] - m : box[`${k}1`] + m);
  const corner = (k, v) => { const pa = plane(a, across, near(a, across)), pb = plane(b, across, near(b, across));
    return [pa, plane(pa, k, v), plane(pb, k, v), pb]; };
  const front = solid.away === -1 ? box.z0 - m : box.z1 + m, back = solid.away === -1 ? box.z1 + m : box.z0 - m;
  const opposite = (a.z <= box.z0 && b.z >= box.z1) || (b.z <= box.z0 && a.z >= box.z1);
  const zeroU = solid.zeroU === true && edge === 'z';
  // behind the back edge (above): the end at or behind the back plane is
  // `q`, the other `p`; the one point stands on p's side of the plate
  const behind = p => (solid.away === -1 ? p.z >= back - 1e-9 : p.z <= back + 1e-9);
  const rearWay = () => {
    if (!rear || behind(a) === behind(b)) return null;
    const [p, q] = behind(a) ? [b, a] : [a, b];
    const y = p.y >= (box.y0 + box.y1) / 2 ? box.y1 + m : box.y0 - m;
    const dp = Math.hypot(p.z - back, p.y - y), dq = Math.hypot(q.z - back, q.y - y);
    return [{x: p.x + (q.x - p.x) * (dp + dq > 1e-9 ? dp / (dp + dq) : 0.5), y, z: back}];
  };
  const round = edge === 'z' && across === 'y' ? rearWay() : null;
  const tiers = edge === 'z' && across === 'y' ? [...(round ? [[round]] : []), [flat('z', front)], [flat('z', back)]]
    : zeroU ? [[flat('z', back), corner('z', back)]] : [both(edge)];
  tiers.push(both(end));
  // A CORD THAT LANDS ON A ZERO-U PART'S FACE (P-0037): an end of the leg
  // stands in front of the part's outward face (a PDU outlet's reach point),
  // level with some part of it, and the other end is inboard. The cord is
  // taken in past the part's side that faces the rails, at the height it is
  // at, and so arrives at the outlet from beside it; over the top or under
  // the foot of the part, a cord to an outlet near its end would run the
  // whole way up and back down.
  if (solid.zeroU === true && across === 'z' && edge === 'y') {
    const outer = p => (solid.away === -1 ? p.z < solid.box.z0 : p.z > solid.box.z1);
    const over = p => p.x > solid.box.x0 && p.x < solid.box.x1 && p.y > solid.box.y0 && p.y < solid.box.y1;
    const lands = [a, b].some(p => outer(p) && over(p));
    if (lands) {
      const inboard = (box.x0 + box.x1) / 2 < 0 ? box.x1 + m : box.x0 - m;
      tiers.unshift([flat('x', inboard)]);
    }
  }
  // A ZERO-U PART crossed front to back with pass-through holes (a vertical
  // duct's back): first through the nearest hole, along y to its middle on this
  // side, across, and along y on the far side; over its top or bottom edge only
  // when no hole clears. Horizontal managers keep the ways above.
  if (solid.zeroU === true && across === 'z' && edge === 'y' && Array.isArray(solid.holes)) {
    const at = (a.y + b.y) / 2;
    const ways = solid.holes.filter(h => diameter <= Math.min(...h.size) + 1e-9)
      .map(h => (h.box.y0 + h.box.y1) / 2).sort((p, q) => Math.abs(p - at) - Math.abs(q - at))
      .map(v => flat('y', v, true));
    if (ways.length) tiers.unshift(ways);
  }
  if (opposite) tiers.push([...new Set(lanes)].map(v => flat('x', v, true)));
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
// lane there (route.js laneXAt), or a list. `room` (mm, #973) asks for each
// end's move to a plane to be that long (waysRound): in each tier the ways
// with room are tried first, and the ways as they were without it only when
// none of those resolves, so a body that leaves no room is still gone round
// the same preferred way, and the short leg is left for the bend check.
export function detour(a, b, solids, {diameter = 0, lanes = [], room = 0, rear = false, loose = false} = {}) {
  const lanesAt = typeof lanes === 'function' ? lanes : () => lanes;
  const clear = (u, w, only = null) => gap(u, w) < 1e-9 || !legCrossings(u, w, only ? [only] : solids, {diameter}).length;
  const go = (p, q, depth) => {
    const first = legCrossings(p, q, solids, {diameter})[0];
    if (!first) return [];
    const opts = {diameter, lanes: lanesAt((p.y + q.y) / 2), rear};
    const plain = waysRound(p, q, first.solid, opts);
    const roomy = room > 0 ? waysRound(p, q, first.solid, {...opts, room}) : null;
    for (let t = 0; t < plain.length; t++) for (const tier of roomy ? [roomy[t], plain[t]] : [plain[t]]) {
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
  // NOT PULLED TAUT WHERE THAT TAKES A TURN'S ROOM (#1026, `loose`): a way
  // out past an edge, across and back in is three right angles, each with
  // its leg; without the point where it turns back in, the cable runs
  // straight from the first to its far end, and that one turn is wider than
  // a right angle on the same leg. With `loose` and `room`, a point stays
  // when the way without it would leave a turn less than half of `room`
  // (the bend radius) and less than the way with it does. Only round a plate
  // met from above or below, where the way is rule 1's (out past its edge
  // and back in, as a lead is dressed by hand): a way up over a ring's leg
  // and down again is no dressing, and stays taut and short of room.
  const all = [a, ...pts, b];
  const met0 = legCrossings(a, b, solids, {diameter})[0]?.solid;
  // (a ring's seat and bar are thin and level too, and are no plate: RING_PART)
  const plate = !!met0 && !RING_PART.test(String(met0.part ?? '')) && crossAxis(a, b, met(met0, diameter)) === 'y';
  const keeps = i => loose && plate && room > 0
    && leastRoom([...all.slice(0, i), ...all.slice(i + 1)]) < Math.min(leastRoom(all), room / 2) - 1e-6;
  for (let i = 1; i < all.length - 1;) {
    if (clear(all[i - 1], all[i + 1]) && !keeps(i)) all.splice(i, 1); else i++;
  }
  return all.slice(1, -1);
}
// The least room the turns of a way have for a bend, in mm, each leg shared
// by what its two turns need of it (route-path.js cornersOf, `share: 'need'`),
// and each END of the way taken as a right angle: an end's move is where the
// cable turns onto the way, which is what `room` is for (waysRound).
function leastRoom(chain) {
  const tan = chain.map((p, i) => {
    if (i === 0 || i === chain.length - 1) return 1;
    const u = [p.x - chain[i - 1].x, p.y - chain[i - 1].y, p.z - chain[i - 1].z], v = [chain[i + 1].x - p.x, chain[i + 1].y - p.y, chain[i + 1].z - p.z];
    const nu = Math.hypot(...u), nv = Math.hypot(...v);
    if (nu < 1e-9 || nv < 1e-9) return 0;
    const c = Math.max(-1, Math.min(1, (u[0] * v[0] + u[1] * v[1] + u[2] * v[2]) / (nu * nv)));
    return c <= -1 + 1e-12 ? Infinity : Math.tan(Math.acos(c) / 2);
  });
  let least = Infinity;
  for (let i = 1; i < chain.length; i++) {
    const sum = tan[i - 1] + tan[i];
    if (sum > 1e-9) least = Math.min(least, gap(chain[i - 1], chain[i]) / sum);
  }
  return least;
}
