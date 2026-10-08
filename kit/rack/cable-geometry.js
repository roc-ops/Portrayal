// CABLE GEOMETRY, as data. The colour, jacket and plug tables and
// the maths that decide where a cable runs: the 2D sag, and the 3D catenary,
// routed and dangling point lists. No DOM, no relief.js and no SVG: THREE is
// passed in where a vector is built, so this imports no three.js either.
// The site's cables.js draws with these.

import {throughRings} from './route-path.js';


// OS2 jackets are yellow; copper is coloured by what it is for.
export const COLORS = {os2: '#e8c547', copper: {server: '#5aa7ff', management: '#9aa3ad'},
  // The Rack Builder's media (cable-rules.js MEDIA), beside the showcase's
  // two: OM3 and OM4 aqua, OM5 lime green, Cat 6 and 6A blue, a DAC black, an
  // AOC dark grey, and a neutral grey for a cable whose media is not set.
  // Added keys only: colorOf, and every colour the showcase draws, are unchanged.
  om3: '#2bb3c8', om4: '#2bb3c8', om5: '#9acd32', cat6: '#5aa7ff', cat6a: '#5aa7ff',
  dac: '#15171a', aoc: '#3a3f45', unset: '#9aa3ad'};
// Own keys only: a hand-edited media or purpose named like something every
// object has (toString, constructor, __proto__) is unknown, not a colour.
const own = (o, k) => (Object.hasOwn(o, k) ? o[k] : undefined);
export const colorOf = l => l.media === 'copper'
  ? (own(COLORS.copper, l.purpose) || COLORS.copper.server) : (own(COLORS, l.media) || COLORS.os2);

// JACKETS: what a cable's outer sheath looks like, by what it is. Multimode
// fibre and AOCs are aqua, single-mode is yellow (the same yellow as os2), a
// twinax DAC is black, and copper patch leads are blue. The front-page hero
// colours its cables by these; the showcase's plan keeps colorOf.
export const JACKETS = {mm: '#2bb3c8', sm: COLORS.os2, dac: '#15171a', cu: COLORS.copper.server};
export const colorOfJacket = j => JACKETS[j] || JACKETS.sm;

// PLUGS: what an LC plug's plastic looks like, by the fibre it carries, as in
// a real rack - single-mode UPC is blue, OM3/OM4 multimode is aqua, the same
// aqua as its jacket. The library draws every lc-plug neutral grey; the
// front-page hero recolors the plugs it seats from this table. A jacket with
// no plug colour (a DAC, copper) has none to change.
export const PLUGS = {sm: '#2a6fd4', mm: JACKETS.mm};
export const plugColorOf = j => PLUGS[j] || null;

export const WIDTH = 3;          // mm: a patch lead, to scale
// How far a cable hangs below the lower of its two ends: a little always, more
// the farther apart they are, and a few mm more per cable already hung between
// the same two devices, so parallel runs fan out instead of stacking.
// A tag's pitch, in mm: its pill is 18 tall (patch-view.js), plus a gap.
export const TAG_H = 20;
export const sag2d = (dist, fan = 0) => 14 + 0.3 * dist + 5 * fan;

// AN UNPLUGGED LEAD. How far it hangs below its connector: the sag of a
// 140 mm run (56 mm), and LEAD_STEP more per lead already hung from the same
// device, so their open plugs do not sit on each other. It drifts LEAD_SIDE
// outboard as it falls. Its tag is not at its free end, over the devices
// below, but in the side column with the cross-face tags, a thin leader
// line running to it.
export const LEAD_DROP = sag2d(140);

// ── 3D ────────────────────────────────────────────────────────────────────
// The same cables as tubes in the mounted rack. Every end starts at the room
// points rack3d.js's cableAnchor finds for its connectors - LC, duplex LC or
// RJ45 plugs, the same cablePoints the 2D half reads.
export const LEAD = 40;           // mm straight out of a connector before it can bend
const REACH_STEP = 4;             // mm further out per row of cabled connectors below, on one face
const MERGE3D = 25;               // mm out from a duplex pair where the strands join
const SIDE_CLEAR = 45;            // mm outside the rack's right post, for front-rear runs
const CLEAR = 5;                  // mm a point pushed out of a chassis ends up past its face
const DANGLE = 150;               // mm an unplugged lead hangs below its connector
const ROW = 2;                    // mm: connectors this close in height are one row
const K = 1.2;                    // catenary shape: f(t) = (cosh(K(2t-1)) - cosh K)/(cosh K - 1)
const cat = t => (Math.cosh(K * (2 * t - 1)) - Math.cosh(K)) / (Math.cosh(K) - 1);
const sag3d = dist => 20 + 0.3 * dist;

// A hanging stretch from p to q: straight between them in x and z, and the
// catenary in y, dipping sag3d of the chord below the straight line mid-way.
function hangBetween(p, q, n = 24) {
  const s = sag3d(p.distanceTo(q));
  const out = [];
  for (let k = 0; k <= n; k++) {
    const t = k / n;
    const v = p.clone().lerp(q, t);
    v.y += s * cat(t);
    out.push(v);
  }
  return out;
}

// Where a duplex end's strands join: MERGE3D out from the middle of the pair.
export const mergeOf = (THREE, e) => e.points.reduce((s, p) => s.add(p), new THREE.Vector3())
  .multiplyScalar(1 / e.points.length).addScaledVector(e.normal, MERGE3D);

// The main run between two ends, {points, normal} each: from each end's start
// (a duplex pair's merge, or the one point) LEAD straight out, then hanging
// between. Ends on opposite faces go round the rack's right-hand side,
// outside the posts.
// `reach` on an end, when set, replaces LEAD (see reaches).
const startOf = (THREE, e) => e.points.length > 1 ? mergeOf(THREE, e) : e.points[0].clone();
// A ROUTED RUN: straight out of each connector as a hang
// does, then taut through every waypoint, each corner rounded by easing r mm
// either side of it - the CatmullRom tube does the rest. THREE is passed in
// so this stays free of a three.js import.
// `rings`, when given, is parallel to `wps`: {run, depth} where a waypoint is
// a ring's centre, null elsewhere. The cable then passes through each ring
// straight along its run, entering from the side nearer the point before it
// (route-path.js throughRings), with its corners eased r outside the ring.
export function routePoints3d(THREE, A, B, wps, r = 30, rings = null) {
  const a = startOf(THREE, A), b = startOf(THREE, B);
  const outA = a.clone().addScaledVector(A.normal, A.reach ?? LEAD);
  const outB = b.clone().addScaledVector(B.normal, B.reach ?? LEAD);
  const path = rings ? throughRings([outA, ...wps, outB], [null, ...rings, null], {lead: r}).points
    : [outA, ...wps, outB];
  const pts = [a, outA];
  for (let k = 1; k < path.length - 1; k++) {
    const [p, q, s] = [path[k - 1], path[k], path[k + 1]];
    const ease = (from, to) => { const d = to.distanceTo(from); return to.clone().lerp(from, Math.min(r, d / 2) / (d || 1)); };
    pts.push(ease(p, q), q.clone(), ease(s, q));
  }
  pts.push(outB, b);
  return pts;
}

export function hangPoints3d(THREE, A, B, rackW) {
  const a = startOf(THREE, A), b = startOf(THREE, B);
  const outA = a.clone().addScaledVector(A.normal, A.reach ?? LEAD);
  const outB = b.clone().addScaledVector(B.normal, B.reach ?? LEAD);
  const pts = [a, outA];
  if (A.normal.dot(B.normal) < -0.5) {
    const x = rackW / 2 + SIDE_CLEAR;
    const sa = new THREE.Vector3(x, outA.y, outA.z), sb = new THREE.Vector3(x, outB.y, outB.z);
    pts.push(...hangBetween(outA, sa).slice(1), ...hangBetween(sa, sb).slice(1),
             ...hangBetween(sb, outB).slice(1));
  } else {
    pts.push(...hangBetween(outA, outB).slice(1));
  }
  pts.push(b);
  return pts;
}

// An unplugged lead from one end, {points, normal, reach}: straight out of
// the face as a run would, then curving down to hang DANGLE below, its free
// end a little further out still - in front of the rack, not in it.
export function danglePoints3d(THREE, E) {
  const a = startOf(THREE, E);
  const out = a.clone().addScaledVector(E.normal, E.reach ?? LEAD);
  const pts = [a, out];
  const n = 12;
  for (let k = 1; k <= n; k++) {
    const t = k / n;
    // Out a further 30 mm, easing off, while it falls ever faster.
    pts.push(out.clone().addScaledVector(E.normal, 30 * Math.sin(t * Math.PI / 2))
      .add(new THREE.Vector3(0, -DANGLE * t * t, 0)));
  }
  return pts;
}

// PART OF WHICH CABLE IS IN FRONT: on each device face, the cabled
// connectors' heights, lowest first, each row a REACH_STEP further out than
// the one below. Sets `reach` on every end ({points, normal, key}).
export function reaches(THREE, ends) {
  const rows = new Map();
  const y = e => startOf(THREE, e).y;
  for (const e of ends) {
    const ys = rows.get(e.key) || [];
    if (!ys.some(v => Math.abs(v - y(e)) < ROW)) ys.push(y(e));
    rows.set(e.key, ys);
  }
  for (const ys of rows.values()) ys.sort((a, b) => a - b);
  for (const e of ends) e.reach = LEAD + REACH_STEP * rows.get(e.key).findIndex(v => Math.abs(v - y(e)) < ROW);
}

// Keep a cable out of the metal: a point inside a chassis box is pushed along
// z to CLEAR past whichever of that box's front and rear faces is nearer.
export function clearOf(pts, boxes) {
  for (const p of pts) for (const {box} of boxes) {
    if (!box.containsPoint(p)) continue;
    p.z = box.max.z - p.z <= p.z - box.min.z ? box.max.z + CLEAR : box.min.z - CLEAR;
  }
  return pts;
}

