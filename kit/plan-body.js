// The closed body of a housing that states `chassis.plan-outline`: the faces of the section cut band
// by band. section.js `sectionArrays` calls this and turns the faces into indexed arrays (it owns the
// materials, the UVs and the winding); this module only says WHICH faces there are, as welded
// polygons in the viewer's frame. No `three`, and it imports nothing but plan.js, so node tests it.
//
// THE SOLID. What the plan leaves of the body is a stack of prisms: for each band and each row of the
// section (the section cut back to its core where it carries ribs) the band's polygon cut to the row's
// depth intervals (plan.js `bodyOf`), and for each rib the rib's rectangle cut to each band it stands
// in, each piece in its own band's polygon. Every height at which any of them begins or ends is a
// level; between two levels the solid is one region of the plan (the union of the pieces there).
//
// THE SURFACE is then what the region of each slab and the regions beside it leave open:
//   * a WALL for every edge of a slab's region (its loops, interior on the right), between the slab's
//     two levels. Where it comes from decides its slot: an edge of the section along the front or rear
//     (or a rib's own front or rear) keeps that face's art; an edge across the width at x = 0 or
//     x = width is an end cap, and a rib's own side keeps the end's art; a wall from a plan edge, a
//     slanted one or the end wall of an inset casting, is plain (PLAN_WALL_INDEX).
//   * a FACET at every level: the part of the region below that the region above does not cover faces
//     up (the top texture), the part of the region above that the one below does not cover faces down
//     (the bottom texture). Where the two are equal there is no facet.
//
// WATERTIGHT. The regions are cut by different sweeps, so one wall can meet several facets and a
// facet's edge be several walls' edges: the vertices are WELDED (two within 0.1 micrometre are one),
// then every vertex that lies inside the edge of a face is added to that edge, so two faces that
// share a stretch of edge share its vertices and every edge of the mesh belongs to two triangles.
import { rows, snapped, bandHeights, bodyOf, sweep, polygon, loops as loopsOf } from './plan.js';

const EPS = 1e-9;
const LEVEL = 1e-6;          // heights this close are one level
const WELD = 1e-4;           // mm
const SIDE = 1e-6;           // an edge this close to the direction of an axis runs along it
const LINE = 0.005;          // an edge this close to a wall of the section, or to an end of the box, is on it

// the faces of the body as [{points: [[x, y, z], ...], n: [nx, ny, nz], mi}] in the viewer's frame
// (x right, y up, z out of the front, the box centred on the origin).
//   bands     the published `plan-outline`, [{heights: [from, to], points: [[x, y], ...]}]
//   section   the section polygon; cutLoops the loops of the section cut back to its ribs' cores
//   ribs      [{x0, x1, e0, e1, lo, hi}]: along the width, across the depth, and the heights it spans
//   mat       the slots {top, bottom, front, rear, right, left, plan}, and for a part (below) {cap, seam}
//   clip      {lo, hi}, rows of the section's frame (either may be infinite): the part of the body
//             between them, as one half of an opened housing is. Everything is cut to those rows before
//             the levels are found, so the walls end at them, and the faces the cut leaves open at a
//             clip row are the CAP: one face for the polygon of the band on the part's own side (half-open
//             bands: a band edge exactly on the row belongs to the band below it for the part above the
//             row, and to the band above it for the part below), in slot `mat.cap`; where a rib is cut
//             there its section is the rib's own, in `mat.seam`. Without a clip the faces are the whole
//             body's, as they always were.
export function planPolygons({bands, section, cutLoops, ribs, W, H, D, mat, clip}) {
  const plainRows = rows(section, D), cutRows = rows(cutLoops, D);
  const edgeRows = [...plainRows, ...cutRows];
  const snappedBands = snapped(bands, plainRows, W, D).bands
    .map(b => ({heights: bandHeights(b.heights, edgeRows), points: b.points}));
  const clipLo = clip ? clip.lo : -Infinity, clipHi = clip ? clip.hi : Infinity;

  const entries = [];
  for (const e of bodyOf(snappedBands, cutRows, W)) {
    const h0 = Math.max(e.heights[0], clipLo), h1 = Math.min(e.heights[1], clipHi);
    if (e.pieces.length && h1 - h0 > EPS) entries.push({h0, h1, pieces: e.pieces, rib: null});
  }
  const last = snappedBands.length - 1;
  for (const rb of ribs) {
    const rect = [[rb.x0, D - rb.e1], [rb.x1, D - rb.e1], [rb.x1, D - rb.e0], [rb.x0, D - rb.e0]];
    snappedBands.forEach((b, i) => {
      // a rib standing out of the box, above the first band or below the last, belongs to that band
      const lo = Math.max(rb.lo, i === 0 ? -Infinity : b.heights[0], clipLo);
      const hi = Math.min(rb.hi, i === last ? Infinity : b.heights[1], clipHi);
      if (hi - lo <= EPS) return;
      const pieces = sweep([[b.points], [rect]]);
      if (pieces.length) entries.push({h0: lo, h1: hi, pieces, rib: rb});
    });
  }
  if (!entries.length) throw new Error('chassis.plan-outline: nothing is left of the body');

  // the levels, and for each entry the slabs it covers
  const raw = [...new Set(entries.flatMap(e => [e.h0, e.h1]))].sort((a, b) => a - b);
  const S = [];
  for (const h of raw) if (!S.length || h - S[S.length - 1] > LEVEL) S.push(h);
  const levelOf = h => { let k = 0; for (let i = 1; i < S.length; i++) if (Math.abs(S[i] - h) < Math.abs(S[k] - h)) k = i; return k; };
  for (const e of entries) { e.c0 = levelOf(e.h0); e.c1 = levelOf(e.h1); }

  const slabs = [];                     // per slab: {pieces, ribs}
  for (let k = 0; k + 1 < S.length; k++) {
    const here = entries.filter(e => e.c0 <= k && k < e.c1);
    slabs.push({pieces: here.length ? sweep([here.flatMap(e => e.pieces.map(polygon))]) : [],
                ribs: here.filter(e => e.rib).map(e => e.rib), k});
  }

  const toV = (x, y, h) => [x - W / 2, H / 2 - h, y - D / 2];
  const faces = [];

  // ---- the walls
  for (const slab of slabs) {
    if (!slab.pieces.length) continue;
    const s0 = S[slab.k], s1 = S[slab.k + 1];
    const row = cutRows.find(([y0, y1]) => y0 <= s0 + LEVEL && y1 >= s1 - LEVEL);
    const front = [], rear = [];
    if (row) for (const [lo, hi] of row[2]) { rear.push(lo); front.push(hi); }
    for (const rb of slab.ribs) { rear.push(D - rb.e1); front.push(D - rb.e0); }
    const on = (lines, y) => lines.some(l => Math.abs(l - y) <= LINE);
    for (const lp of loopsOf(slab.pieces)) {
      for (let i = 0; i < lp.length; i++) {
        const a = lp[i], b = lp[(i + 1) % lp.length];
        const dx = b[0] - a[0], dy = b[1] - a[1], len = Math.hypot(dx, dy);
        if (len <= EPS) continue;
        let mi = mat.plan;
        if (Math.abs(dx) < SIDE) {
          const x = a[0], lo = Math.min(a[1], b[1]), hi = Math.max(a[1], b[1]);
          const ribSide = slab.ribs.some(rb => Math.abs((dy > 0 ? rb.x1 : rb.x0) - x) < SIDE
            && Math.min(hi, D - rb.e0) - Math.max(lo, D - rb.e1) > EPS);
          if (dy > 0) { if (ribSide || Math.abs(x - W) < LINE) mi = mat.right; }
          else if (ribSide || Math.abs(x) < LINE) mi = mat.left;
        } else if (Math.abs(dy) < SIDE) {
          if (dx < 0) { if (on(front, a[1])) mi = mat.front; }
          else if (on(rear, a[1])) mi = mat.rear;
        }
        faces.push({points: [toV(a[0], a[1], s0), toV(b[0], b[1], s0), toV(b[0], b[1], s1), toV(a[0], a[1], s1)],
                    n: [dy / len, 0, -dx / len], mi});
      }
    }
  }

  // ---- the facets, at every level
  const diff = (a, b) => {
    if (!a.length) return [];
    if (!b.length) return a;
    return sweep([a.map(polygon)], [b.map(polygon)]);
  };
  const onRow = (h, row) => Number.isFinite(row) && Math.abs(h - row) <= LEVEL;
  for (let i = 0; i < S.length; i++) {
    const above = i > 0 ? slabs[i - 1].pieces : [], below = i < slabs.length ? slabs[i].pieces : [];
    if (clip && (onRow(S[i], clipLo) || onRow(S[i], clipHi))) {
      // a clip row: the body is on one side only, so the whole region is the cap
      const up = below.length > 0, all = up ? below : above;
      const slab = slabs[up ? i : i - 1];
      const here = entries.filter(e => e.c0 <= slab.k && slab.k < e.c1);
      const body = here.filter(e => !e.rib);
      const bodyPieces = here.length === body.length ? all : sweep([body.flatMap(e => e.pieces.map(polygon))]);
      const parts = [[bodyPieces, mat.cap]];
      if (here.length !== body.length) parts.push([diff(all, bodyPieces), mat.seam]);
      for (const [pieces, mi] of parts) {
        for (const p of pieces) {
          const pts = polygon(p);
          if (pts.length >= 3) faces.push({points: pts.map(([x, y]) => toV(x, y, S[i])), n: [0, up ? 1 : -1, 0], mi});
        }
      }
      continue;
    }
    if (JSON.stringify(above) === JSON.stringify(below)) continue;
    for (const [pieces, n, mi] of [[diff(below, above), [0, 1, 0], mat.top], [diff(above, below), [0, -1, 0], mat.bottom]]) {
      for (const p of pieces) {
        const pts = polygon(p);
        if (pts.length >= 3) faces.push({points: pts.map(([x, y]) => toV(x, y, S[i])), n, mi});
      }
    }
  }
  return watertight(faces);
}

// ---- welding and the repair of T-junctions -------------------------------------------------------

function watertight(faces) {
  const cells = new Map();
  const cellKey = (x, y, z) => `${Math.floor(x * 1000)},${Math.floor(y * 1000)},${Math.floor(z * 1000)}`;
  const verts = [];
  const weld = p => {
    const cx = Math.floor(p[0] * 1000), cy = Math.floor(p[1] * 1000), cz = Math.floor(p[2] * 1000);
    for (let i = -1; i <= 1; i++) for (let j = -1; j <= 1; j++) for (let k = -1; k <= 1; k++) {
      for (const v of cells.get(`${cx + i},${cy + j},${cz + k}`) || []) {
        if (Math.abs(v[0] - p[0]) <= WELD && Math.abs(v[1] - p[1]) <= WELD && Math.abs(v[2] - p[2]) <= WELD) return v;
      }
    }
    const v = [p[0], p[1], p[2]];
    const key = cellKey(...v);
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(v);
    verts.push(v);
    return v;
  };
  const rings = [];
  for (const f of faces) {
    const ring = [];
    for (const p of f.points) {
      const v = weld(p);
      if (ring[ring.length - 1] !== v) ring.push(v);
    }
    if (ring.length > 1 && ring[0] === ring[ring.length - 1]) ring.pop();
    if (ring.length >= 3) rings.push({ring, n: f.n, mi: f.mi});
  }

  // vertices by the height they stand at, and by where they stand across the plan
  const level = new Map(), column = new Map();
  const add = (m, k, v) => { if (!m.has(k)) m.set(k, []); m.get(k).push(v); };
  for (const v of verts) {
    add(level, Math.round(v[1] * 1000), v);
    add(column, `${Math.round(v[0] * 100)},${Math.round(v[2] * 100)}`, v);
  }
  const near = (p, q) => Math.abs(p[0] - q[0]) <= WELD && Math.abs(p[1] - q[1]) <= WELD && Math.abs(p[2] - q[2]) <= WELD;
  // the vertices strictly inside the edge p -> q, in order from p
  const inside = (p, q) => {
    let cands = [];
    if (Math.abs(p[1] - q[1]) < 1e-7) {                       // across: every vertex at that height
      const k = Math.round(p[1] * 1000);
      for (const d of [-1, 0, 1]) cands = cands.concat(level.get(k + d) || []);
    } else if (Math.abs(p[0] - q[0]) < WELD && Math.abs(p[2] - q[2]) < WELD) {      // up or down
      const cx = Math.round(p[0] * 100), cz = Math.round(p[2] * 100);
      for (const i of [-1, 0, 1]) for (const j of [-1, 0, 1]) cands = cands.concat(column.get(`${cx + i},${cz + j}`) || []);
    } else return [];
    const d = [q[0] - p[0], q[1] - p[1], q[2] - p[2]];
    const len2 = d[0] * d[0] + d[1] * d[1] + d[2] * d[2];
    const found = [];
    for (const v of new Set(cands)) {
      if (near(v, p) || near(v, q)) continue;
      const t = ((v[0] - p[0]) * d[0] + (v[1] - p[1]) * d[1] + (v[2] - p[2]) * d[2]) / len2;
      if (t <= 0 || t >= 1) continue;
      const off = Math.hypot(v[0] - (p[0] + t * d[0]), v[1] - (p[1] + t * d[1]), v[2] - (p[2] + t * d[2]));
      if (off <= 2 * WELD) found.push([t, v]);
    }
    return found.sort((a, b) => a[0] - b[0]).map(f => f[1]);
  };
  const out = [];
  for (const {ring, n, mi} of rings) {
    const full = [];
    ring.forEach((p, i) => { full.push(p, ...inside(p, ring[(i + 1) % ring.length])); });
    out.push({points: full, n, mi});
  }
  return out;
}
