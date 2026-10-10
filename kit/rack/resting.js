// kit/rack/resting.js
// RESTING (docs/cable-lay-design.md section 3, #949). Pure, like solids.js.
//
// A supported cable lies on its support, lifted by its own radius: on a tray's
// floor, on the sill of a ring, on the top of a body it would otherwise sag
// into; on the held face of a tray it lies against the plate from below,
// strapped up to it through the tie slots. Only a FREE SPAN sags - a stretch
// between two supports, or between a port and a support - and it never sags
// below a surface under it: where its curve would pass below one, it lands
// there and is supported.
//
// HOW FAR A SPAN SAGS is the 3D drawing's catenary (cable-geometry.js: 20 mm
// plus 0.3 of the span), scaled by the DRAPE of the cable's family, and never
// so deep that its tightest corner is tighter than the bend radius it may
// take: the installed minimum bend radius of its type over its drape, so a
// stiff cable takes a wider curve and lands further along. DRAPE is a kit
// table and not a library key (decision 2 of the note), so it can be tuned
// without a door.
//
// Everything is worked in the rack's frame, with gravity down y, from the
// placed trays and bodies (solids.js traysOf and solidsOf), which are placed
// as the item is mounted: a ring in a part turned end over end hangs from
// the plate, and a cable in it rests on the band now below it (section 3.1).
//
// Internal to the kit: route.js routePath calls it, and what it decides is in
// the path's points and its `rests`.

import {solidsOf, traysOf, legCrossings} from './solids.js';

// How limp a cable is, by its family: 1 drapes onto a tray within a short
// span, less is stiffer and lands further along. The families are the cable
// types table's (#919).
export const DRAPE = {fiber: 1, aoc: 1, copper: 0.5, dac: 0.35, power: 0.35};
// A Rack Builder media's family, and its installed minimum bend radius in mm
// when the page gives none: spec/schemas/cable-types.yaml's figure for the
// bare type of that id (fibre cords 25, Cat 6 four times 6.0, Cat 6A four
// times 7.5, a DAC 23, an AOC ten times 3.0) and, for `power`, which no bare
// type is named, its power-c13 cord's six times 7.1. A cable whose media is
// not set is taken as copper, as its diameter is. test_rack_trays.py holds
// both tables to the yaml.
export const FAMILY = {os2: 'fiber', om3: 'fiber', om4: 'fiber', om5: 'fiber', cat6: 'copper', cat6a: 'copper',
  dac: 'dac', aoc: 'aoc', power: 'power'};
export const BEND = {os2: 25, om3: 25, om4: 25, om5: 25, cat6: 24, cat6a: 30, dac: 23, aoc: 30, power: 42.6};
const UNSET_BEND = 24;

// A cable's family: its type's in the cable types table when the page gives
// the table's lookup (`ctx.typeOf(id)`, cable-types.js loadCableTypes: its own
// `type` first, else its media), else its media's.
export function familyOf(cable, ctx) {
  let t = null;
  try {
    if (typeof ctx?.typeOf === 'function') t = ctx.typeOf(cable?.type) ?? ctx.typeOf(cable?.media) ?? null;
  } catch { t = null; }
  if (t && typeof t.family === 'string' && Object.hasOwn(DRAPE, t.family)) return t.family;
  return typeof cable?.media === 'string' && Object.hasOwn(FAMILY, cable.media) ? FAMILY[cable.media] : 'copper';
}
export const drapeOf = (cable, ctx) => DRAPE[familyOf(cable, ctx)];
export function bendOf(cable, ctx) {
  let r = null;
  try { r = typeof ctx?.bendOf === 'function' ? ctx.bendOf(cable) : null; } catch { r = null; }
  if (typeof r === 'number' && Number.isFinite(r) && r > 0) return r;
  return typeof cable?.media === 'string' && Object.hasOwn(BEND, cable.media) ? BEND[cable.media] : UNSET_BEND;
}

// THE SHAPE OF A SPAN: the catenary of cable-geometry.js, f(t) = (cosh(K(2t-1))
// - cosh K) / (cosh K - 1), 0 at the ends and -1 mid-way.
const K = 1.2;
export const cat = t => (Math.cosh(K * (2 * t - 1)) - Math.cosh(K)) / (Math.cosh(K) - 1);
// Its tightest bend is at its ends: a span of horizontal length L sagging S
// bends there with a radius of at least CURVE * L^2 / S (the curvature of S
// cat(s / L), slope left out, which only widens it). So a span may sag at
// most CURVE * L^2 / R for a bend radius R.
const CURVE = (Math.cosh(K) - 1) / (4 * K * K * Math.cosh(K));
// The depth a span of horizontal length L takes: the drawing's catenary
// scaled by the drape, no deeper than its bend radius allows.
export const sagOf = (L, drape, radius) => Math.max(0, Math.min(drape * (20 + 0.3 * L), CURVE * L * L / radius));
// A span shorter than this, across the face, is a straight drop or rise.
const MIN_SPAN = 5;
const EPS = 1e-6;

// THE SURFACES a cable can come to rest on, placed: every tray's face that
// looks up, and the top of every solid body (a plate, a wall, a device's
// envelope). [{x0, x1, z0, z1, y, item, via?, part?}]. Read once per rack and
// context.
const memo = new WeakMap();
export function surfacesOf(rack, ctx) {
  let per = memo.get(rack);
  if (!per) memo.set(rack, per = new WeakMap());
  if (per.has(ctx)) return per.get(ctx);
  const out = [];
  for (const t of traysOf(rack, ctx)) {
    for (const f of t.floors) out.push({x0: f.x0, x1: f.x1, z0: f.z0, z1: f.z1, y: t.top, item: t.item, via: t.via, tray: true});
  }
  for (const s of solidsOf(rack, ctx)) {
    out.push({x0: s.box.x0, x1: s.box.x1, z0: s.box.z0, z1: s.box.z1, y: s.box.y1, item: s.item, part: s.part});
  }
  per.set(ctx, out);
  return out;
}

// The highest surface under (x, z) whose top is no higher than `y`: what a
// cable centred at height y + r there would land on. null when there is none.
export function groundAt(surfaces, x, z, y) {
  let best = null;
  for (const s of surfaces) {
    if (x < s.x0 - EPS || x > s.x1 + EPS || z < s.z0 - EPS || z > s.z1 + EPS) continue;
    if (s.y > y + 1e-3) continue;
    if (!best || s.y > best.y) best = s;
  }
  return best;
}

// THE DROP from a support onto a surface below it, h mm, as a cable lays it:
// leaving level, a bend down and a bend back to level, each of radius R, so
// it lands level; deeper than 2R, a straight fall between two quarter bends.
// It is laid as the TANGENT POLYGON of those bends (#973): the two points
// where the tangents at the bends' ends meet, so the line through them
// touches each arc and no corner of it has less room than R by the kit's own
// measure (route-path.js cornersOf). Returns its horizontal extent and the
// two points as [distance along, height down from the start].
function dropOf(h, R) {
  if (!(h > 0.01)) return {extent: 0, points: []};
  if (h <= 2 * R) {
    const th = Math.acos(1 - h / (2 * R)), e = 2 * R * Math.sin(th), T = R * Math.tan(th / 2);
    return {extent: e, points: [[T, 0], [e - T, h]]};
  }
  // two quarter bends with a straight fall between, at R along
  return {extent: 2 * R, points: [[R, 0], [R, h]]};
}

const lerp = (p, q, t) => ({x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t, z: p.z + (q.z - p.z) * t});
const gap3 = (p, q) => Math.hypot(p.x - q.x, p.y - q.y, p.z - q.z);
// Two points of a span nearer than this are one (mm): where a span lands, a
// sample and a break of the profile can fall a fraction of a millimetre
// apart, and any curve through both turns tighter than the span does.
const NEAR = 1;
// A span's points with every near-duplicate dropped, its ends p and q counted.
function apart(p, q, pts) {
  const out = [];
  for (const pt of pts) if (gap3(pt, out.length ? out[out.length - 1] : p) >= NEAR) out.push(pt);
  while (out.length && gap3(out[out.length - 1], q) < NEAR) out.pop();
  return out;
}
// How finely the curve is worked before it is sampled evenly along its arc.
const FINE = 48;
// A curve given as fine points from p to q, as n - 1 points evenly spaced
// along its arc (none for n < 2).
function evenly(fine, n) {
  if (n < 2) return [];
  const cum = [0];
  for (let i = 1; i < fine.length; i++) cum.push(cum[i - 1] + gap3(fine[i - 1], fine[i]));
  const total = cum[cum.length - 1], out = [];
  let i = 1;
  for (let k = 1; k < n; k++) {
    const want = (k / n) * total;
    while (i < fine.length - 1 && cum[i] < want) i++;
    const span = cum[i] - cum[i - 1];
    out.push(lerp(fine[i - 1], fine[i], span > 0 ? (want - cum[i - 1]) / span : 0));
  }
  return out;
}

// A FREE SPAN from p to q (rack mm, cable centres), as the points to add
// between them, and what it lands on: {points, lands}. `r` is the cable's
// radius, `drape` its family's, `bend` its installed bend radius; `surfaces`
// what it may rest on (surfacesOf). It hangs as the catenary of sagOf, and
// where that would pass below a surface under it, the cable drops onto the
// surface from each end (dropOf, at the bend radius over the drape) and lies
// on it between; a span too short to lay that way keeps the catenary, raised
// to the surface wherever it would pass below it. A span that is mostly a
// fall or a rise (less than MIN_SPAN across the face) is straight.
//
// NO SPAN IS LAID TIGHTER THAN IT MAY BEND (#973). The points are the hang's
// own corners and its ends are corners too, where the span meets what holds
// it, so whether a hang leaves every one of them room is not the span's alone
// to say: `fits(points)`, when given (route.js routePath), says whether the
// path with these points between p and q has no more corners short of the
// bend radius than the straight span has. The hang is offered from the
// fullest to the least, and the first that fits is laid:
//   - on a surface, the drops' tangent polygons with a level lead of nothing,
//     the bend radius or twice it before each (a span leaves a ring or a plug
//     along it, and the turn there needs its leg before the drop begins);
//   - the catenary at its full sag, at a half and at a quarter of it, each
//     sampled evenly along its arc (and not along the chord, which spaces the
//     samples of a steep end several times closer than the middle's), at 15
//     mm, at the bend radius and at twice it;
//   - straight, when nothing else fits: a cable with no room to turn where it
//     is held does not also sag.
// Near-duplicate points are dropped (NEAR). Without `fits` the first of each
// is laid, as before #973.
export function hang(p, q, {r = 0, drape = 1, bend = 25, surfaces = [], fits = null} = {}) {
  const L = Math.hypot(q.x - p.x, q.z - p.z);
  if (L < MIN_SPAN) return {points: [], lands: []};
  const ok = pts => typeof fits !== 'function' || fits(pts);
  const R = bend / Math.max(drape, EPS);
  const S = sagOf(L, drape, R);
  // the ground under a point of the chord: surfaces no higher than the chord
  // less the cable's radius (a surface above the chord is a roof, not ground)
  const top = Math.max(p.y, q.y);
  const fineOf = sag => Array.from({length: FINE + 1}, (_, k) => {
    const t = k / FINE, chord = lerp(p, q, t);
    return {t, chord, y: chord.y + sag * cat(t), g: groundAt(surfaces, chord.x, chord.z, Math.max(chord.y, top) - r)};
  });
  const full = fineOf(S);
  const below = full.filter(s => s.t > 0 && s.t < 1 && s.g && s.y < s.g.y + r - EPS);
  // a span that sags less than a hundredth of a millimetre and lands on
  // nothing is straight: there is nothing to lay
  if (!below.length && S < 0.01) return {points: [], lands: []};
  if (below.length) {
    // it lands: on the highest surface it would pass below
    const land = below.reduce((m, s) => (s.g.y > m.g.y ? s : m), below[0]).g;
    const G = land.y + r;
    const da = dropOf(p.y - G, R), db = dropOf(q.y - G, R);
    if (p.y >= G - EPS && q.y >= G - EPS) {
      // the profile: a level lead, a drop from p, the surface, a rise to q
      // and a level lead; never below any surface under it
      const leads = [0, R, 2 * R];
      const pairs = leads.flatMap(a => leads.map(b => [a, b])).sort((x, y) => (x[0] + x[1]) - (y[0] + y[1]));
      // where along the span that surface is under it: the stretch the cable
      // lies level must reach it, or it would be said to rest on what it
      // only passes over (a rib a few mm wide near one end)
      const under = full.filter(s => s.g === land).map(s => s.t * L);
      const [u0, u1] = [Math.min(...under), Math.max(...under)];
      for (const [la, lb] of pairs) {
        const s0 = (da.extent ? la : 0) + da.extent, s1 = L - (db.extent ? lb : 0) - db.extent;
        if (s0 > s1 + EPS || s0 > u1 + EPS || s1 < u0 - EPS) continue;
        const prof = [...da.points.map(([s, h]) => [la + s, p.y - h]),
          ...[...db.points].reverse().map(([s, h]) => [L - lb - s, q.y - h])];
        const pts = prof.map(([s, y]) => ({...lerp(p, q, s / L), y}));
        for (const pt of pts) {
          const g = groundAt(surfaces, pt.x, pt.z, pt.y - r);
          if (g && pt.y < g.y + r) pt.y = g.y + r;
        }
        const out = apart(p, q, pts);
        if (out.length && ok(out)) return {points: out, lands: [land]};
        if (typeof fits !== 'function') break;
      }
    }
  }
  // the catenary, raised onto whatever it would pass below (a span too short
  // to lay down and pick up again lands so), evenly along its arc
  // the spacings a hang is offered at, finest first: a sample's legs are the
  // room its neighbours have, so a span that turns sharply where it is held
  // needs them longer
  const steps = [15, Math.min(bend, 100), 2 * Math.min(bend, 100)];
  for (const sag of S < 0.01 ? [] : [S, S / 2, S / 4]) {
    const fine = sag === S ? full : fineOf(sag);
    const raised = fine.map(s => ({...s.chord, y: s.g ? Math.max(s.y, s.g.y + r) : s.y}));
    // what it lands on: each surface a point of it, as sampled, lies on
    const landsOf = pts => { const on = []; for (const pt of pts) { const g = groundAt(surfaces, pt.x, pt.z, pt.y - r + 1e-3);
      if (g && Math.abs(pt.y - (g.y + r)) < 1e-6 && !on.includes(g)) on.push(g); } return on; };
    const len = raised.reduce((m, pt, i) => (i ? m + gap3(raised[i - 1], pt) : 0), 0);
    let last = null;
    for (const step of steps) {
      const n = Math.min(24, Math.round(len / step));
      if (n < 2 || n === last) continue;
      last = n;
      const out = apart(p, q, evenly(raised, n));
      if (out.length && ok(out)) return {points: out, lands: landsOf(out)};
      if (typeof fits !== 'function') break;
    }
    if (typeof fits !== 'function') break;
  }
  return {points: [], lands: []};
}

// THE HELD FACE OF A TRAY (section 2.3): a cable strapped up against the
// plate from below runs at the plate less its radius under each tie slot it
// uses, and between two of them sags by its drape over that span, never below
// the strap line, the bottom of the strapped stack: the plate less the
// cable's diameter, for a cable on its own (the stack of several is the lay
// of step 5). From x0 to x1 along a tray that runs along x (or z), at the
// across position `across`, returns {points, ties, line, strap}: the points
// (both ends of each used slot and the sag between), the indices of the tie
// slots used, the line it is strapped at and the strap line. null when no
// tie slot lies along the stretch: a stretch no strap holds is not held.
// The slots that hold a cable along the run are the ones long along it, in
// pairs across it (a strap goes down one and up the other, round the cable);
// the cable lies within the strapped width, at its edge nearer the rail.
export function heldStretch(tray, a, b, {r = 0, drape = 1, bend = 25, rail = 0} = {}) {
  const run = tray.run === 'z' ? 'z' : 'x', across = run === 'x' ? 'z' : 'x';
  const lo = Math.min(a, b), hi = Math.max(a, b);
  const len = (t, k) => t[`${k}1`] - t[`${k}0`];
  const used = tray.ties.map((t, i) => ({t, i}))
    .filter(({t}) => len(t, run) >= len(t, across) && t[`${run}1`] > lo + EPS && t[`${run}0`] < hi - EPS);
  if (!used.length) return null;
  // group the slots into straps: slots that overlap along the run are one pair
  const straps = [];
  for (const u of [...used].sort((p, q) => p.t[`${run}0`] - q.t[`${run}0`])) {
    const s = straps.find(g => u.t[`${run}0`] < g.hi - EPS && u.t[`${run}1`] > g.lo + EPS);
    if (s) { s.lo = Math.min(s.lo, u.t[`${run}0`]); s.hi = Math.max(s.hi, u.t[`${run}1`]); s.cross.push(u.t); s.ties.push(u.i); }
    else straps.push({lo: u.t[`${run}0`], hi: u.t[`${run}1`], cross: [u.t], ties: [u.i]});
  }
  const line = tray.under - r, strap = tray.under - 2 * r;
  // the edge of the strapped width nearer the rail plane the part is fixed
  // to (`rail`, its z), where position 1 is (section 4); across x, its low edge
  const all = straps.flatMap(s => s.cross);
  const c0 = Math.min(...all.map(t => t[`${across}0`])), c1 = Math.max(...all.map(t => t[`${across}1`]));
  const railLow = across !== 'z' || Math.abs(c0 - rail) <= Math.abs(c1 - rail);
  const at = railLow ? c0 + r : c1 - r;
  const R = bend / Math.max(drape, EPS);
  const pt = v => (run === 'x' ? {x: v, y: line, z: at} : {x: at, y: line, z: v});
  const ordered = a <= b ? straps : [...straps].reverse();
  const points = [];
  ordered.forEach((s, k) => {
    const [first, last] = a <= b ? [s.lo, s.hi] : [s.hi, s.lo];
    if (k) {
      // the span from the last strap to this one: it sags, no lower than the strap line
      const from = points[points.length - 1], to = pt(first);
      const L = Math.abs(first - (a <= b ? ordered[k - 1].hi : ordered[k - 1].lo));
      const S = Math.min(sagOf(L, drape, R), line - strap);
      const n = Math.max(2, Math.min(24, Math.ceil(L / 15)));
      for (let j = 1; j < n; j++) { const q = lerp(from, to, j / n); points.push({...q, y: line + S * cat(j / n)}); }
    }
    points.push(pt(first), pt(last));
  });
  return {points, ties: straps.flatMap(s => s.ties).sort((p, q) => p - q), line, strap, across: at};
}

// Whether a run of points crosses a body its straight chord did not: a sag
// that would take a cable into metal is not laid (the chord is kept).
export function newCrossing(p, q, pts, solids, diameter) {
  if (!solids.length || !pts.length) return false;
  const before = new Set(legCrossings(p, q, solids, {diameter}).map(c => c.solid));
  const chain = [p, ...pts, q];
  for (let k = 1; k < chain.length; k++) {
    for (const c of legCrossings(chain[k - 1], chain[k], solids, {diameter})) if (!before.has(c.solid)) return true;
  }
  return false;
}
