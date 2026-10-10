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
// Returns its horizontal extent and its height (down from the start) at a
// distance s along it.
function dropOf(h, R) {
  if (!(h > EPS)) return {extent: 0, at: () => 0, breaks: []};
  if (h <= 2 * R) {
    const th = Math.acos(1 - h / (2 * R)), e = 2 * R * Math.sin(th);
    return {extent: e, breaks: [e / 2],
      at: s => (s <= e / 2 ? R - Math.sqrt(Math.max(0, R * R - s * s))
        : h - (R - Math.sqrt(Math.max(0, R * R - (e - s) * (e - s)))))};
  }
  // two quarter bends with a straight fall between, at s = R
  return {extent: 2 * R, breaks: [R], fall: true,
    at: s => (s < R ? R - Math.sqrt(Math.max(0, R * R - s * s))
      : h - (R - Math.sqrt(Math.max(0, R * R - (2 * R - s) * (2 * R - s)))))};
}

const lerp = (p, q, t) => ({x: p.x + (q.x - p.x) * t, y: p.y + (q.y - p.y) * t, z: p.z + (q.z - p.z) * t});

// A FREE SPAN from p to q (rack mm, cable centres), as the points to add
// between them, and what it lands on: {points, lands}. `r` is the cable's
// radius, `drape` its family's, `bend` its installed bend radius; `surfaces`
// what it may rest on (surfacesOf). It hangs as the catenary of sagOf, and
// where that would pass below a surface under it, the cable drops onto the
// surface from each end (dropOf, at the bend radius over the drape) and lies
// on it between; a span too short to lay that way keeps the catenary, raised
// to the surface wherever it would pass below it. A span that is mostly a
// fall or a rise (less than MIN_SPAN across the face) is straight.
export function hang(p, q, {r = 0, drape = 1, bend = 25, surfaces = []} = {}) {
  const L = Math.hypot(q.x - p.x, q.z - p.z);
  if (L < MIN_SPAN) return {points: [], lands: []};
  const R = bend / Math.max(drape, EPS);
  const S = sagOf(L, drape, R);
  const n = Math.max(4, Math.min(24, Math.ceil(L / 15)));
  // the ground under each sample: surfaces no higher than the chord less the
  // cable's radius (a surface above the chord is a roof, not ground)
  const groundOf = (t, chordY) => {
    const c = lerp(p, q, t);
    return groundAt(surfaces, c.x, c.z, chordY - r);
  };
  const ts = Array.from({length: n - 1}, (_, k) => (k + 1) / n);
  const samples = ts.map(t => {
    const chord = lerp(p, q, t);
    const g = groundOf(t, Math.max(chord.y, p.y, q.y));
    return {t, chord, y: chord.y + S * cat(t), g};
  });
  const below = samples.filter(s => s.g && s.y < s.g.y + r - EPS);
  // a span that sags less than a hundredth of a millimetre and lands on
  // nothing is straight: there is nothing to lay
  if (!below.length) return {points: S < 0.01 ? [] : samples.map(s => ({...s.chord, y: s.y})), lands: []};
  // it lands: on the highest surface it would pass below
  const land = below.reduce((m, s) => (s.g.y > m.g.y ? s : m), below[0]).g;
  const G = land.y + r;
  const da = dropOf(p.y - G, R), db = dropOf(q.y - G, R);
  const fits = da.extent + db.extent <= L + EPS && p.y >= G - EPS && q.y >= G - EPS;
  const lands = [land];
  if (!fits) {
    // too short to lay down and pick up again: the catenary, raised onto
    // whatever it would pass below
    return {points: samples.map(s => ({...s.chord, y: s.g ? Math.max(s.y, s.g.y + r) : s.y})), lands};
  }
  // the profile: a drop from p, the surface, a rise to q; sampled on the grid
  // and at every break, and never below any surface under it
  const ss = new Set(ts.map(t => t * L));
  for (const b of [...da.breaks, da.extent]) if (b > EPS && b < L - EPS) ss.add(b);
  for (const b of [...db.breaks, db.extent]) if (b > EPS && b < L - EPS) ss.add(L - b);
  const yAt = s => (s <= da.extent ? p.y - da.at(s) : s >= L - db.extent ? q.y - db.at(L - s) : G);
  const out = [];
  for (const s of [...ss].sort((a, b) => a - b)) {
    const c = lerp(p, q, s / L);
    const fallA = da.fall && Math.abs(s - da.breaks[0]) < EPS, fallB = db.fall && Math.abs(L - s - db.breaks[0]) < EPS;
    // a straight fall: both ends of it, at the one distance along, a quarter
    // bend below the start and a quarter bend above the surface
    if (fallA) out.push({...c, y: p.y - R}, {...c, y: G + R});
    else if (fallB) out.push({...c, y: G + R}, {...c, y: q.y - R});
    else out.push({...c, y: yAt(s)});
  }
  for (const pt of out) {
    const g = groundAt(surfaces, pt.x, pt.z, pt.y - r);
    if (g && pt.y < g.y + r) pt.y = g.y + r;
  }
  return {points: out, lands};
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
