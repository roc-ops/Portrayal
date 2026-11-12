// The 3D body of a housing that states `chassis.section`: the end profile
// extruded along the width.
//
// `<device>.configs.json` carries `chassis.section` as it was written: a closed,
// axis-aligned polygon in the RIGHT end face's drawing frame, x across the depth
// growing toward the rear and y down the height, both in millimetres from the
// face's top-left corner (spec/tools/portrayal/section.py is the one place the
// compiler reads it). This module turns it, with the chassis width, height and
// depth, into indexed arrays like bevel.js's, so node can test them; viewer3d.js
// makes the BufferGeometry.
//
// THE FRAME. The viewer's box is centred on the origin, +x right, +y up, +z out
// of the front. A section point (sx, sy) is at z = D/2 - sx, y = H/2 - sy; the
// right cap is at x = W/2 and the left cap at x = -W/2. The left cap is
// therefore the right cap mirrored in x, which is what the compiler draws on the
// left face (section.outline), and its UVs follow without a rule of their own.
//
// THE TEXTURE MAPPING IS bevel.js's boxUV, ON PURPOSE: every face texture the
// kit rasterises (the relief punches, the flips, refineFace's sharper rasters)
// is prepared for BoxGeometry's layout, so a point takes the UV it would have on
// the full box face it looks toward. That is a planar projection: a facet looking
// up samples the top texture along its length and its depth, a facet looking
// toward the front or the rear samples that texture at its own height and
// length, and a cap samples its end face's texture at the polygon point. A facet
// is parallel to the face it samples, so the texture is not sheared on it.
//
// THE MATERIAL OF A TRIANGLE IS THE FACE IT LOOKS TOWARD, in FACE_INDEX order
// (right, left, top, bottom, front, rear), so picking, the face frames and
// level of detail read the section body as they read the box.
//
// THE RIBS (`chassis.fins`, read the same way: spec/tools/portrayal/fins.py is the
// one place the compiler reads it). With fins the body is the section CUT BACK to
// each inside field's core surface, along the whole width (the end margins carry no
// ribs), and the ribs are slabs standing on that surface up to their step height,
// merged into the SAME buffer, not a mesh each: five faces a rib (none against the
// core), four vertices a face, in the materials of the way each looks, so picking,
// the face frames and the planar UVs read them as they read the casting. An outside
// field's ribs stand out of the section's own edge, beyond the box, and cut nothing.
// A section with no fins builds exactly as it did.
//
// THE OPEN STATE (`chassis.halves`, spec/tools/portrayal/halves.py). A housing that opens is
// the same body in two parts. The seam is the plane `base.stands` from the base's `outer` face
// (`top` or `bottom`, so the seam is parallel to the extrusion and each part is a cut of the
// section), `splitSection` cuts the body of the arrays above at it, ribs included, and each
// part is its own arrays: the body's faces in materials 0-5 as before, and the cut face closed
// with a cap of its own, material SEAM_INDEX, planar at the seam. The cap is there so a part is
// a solid whose volume and area can be held; the viewer shows it as it shows the open face of a
// box half (housing.js, #1586): not drawn, the inside of the shell seen through it. The lid
// turns about the LINE where the seam plane meets the hinge face's outline: parallel to the
// extrusion, at the seam row, at the section's foremost (`front`) or rearmost (`rear`) x there.
// In a flange that is the flange's edge, the hinge-side edge the maker's hinge drawing shows;
// in a casting, its wall. A seam that divides nothing (outside the section, or exactly on a
// horizontal edge) cannot be split: lint refuses it (spec/tools/portrayal/lint.py) and the
// split here throws.
//
// No `three` in here.

import { boxUV, FACE_INDEX } from './bevel.js';

// the material of a part's cut face: after the six faces, the slot bevel.js gives its bevels
export const SEAM_INDEX = 6;

const EPS = 1e-9;
const FIN_TOL = 0.01;
const FIN_MAX_RIBS = 400;

const isNum = v => typeof v === 'number' && Number.isFinite(v);

// twice the signed area by the shoelace sum; positive is clockwise on the
// screen with y down (section.py area2)
function area2(pts) {
  let s = 0;
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
    s += x0 * y1 - x1 * y0;
  }
  return s;
}

const side = (a, b, p) => (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]);

// Triangles [i, j, k] of the polygon's vertex indices, by ear clipping. EXACT
// for any simple polygon (the two-ears theorem: it always has an ear to cut),
// and it creates no vertex, so a cap's boundary is made of the polygon's own
// vertices and meets each facet edge to edge with no T-junction to leave a
// hairline between them. (Horizontal bands would also cover a rectilinear polygon
// exactly, but they cut a band edge across a facet's end.) The polygon wound
// clockwise with y down has a positive area2; an ear is a convex corner with no
// other vertex in its triangle. A vertex lying exactly on an ear's diagonal
// would block it by a closed test, so a second pass counts only the interior.
function earClip(pts) {
  const idx = pts.map((_, i) => i), out = [];
  while (idx.length > 3) {
    let cut = -1;
    for (const closed of [true, false]) {
      for (let k = 0; k < idx.length && cut < 0; k++) {
        const a = idx[(k + idx.length - 1) % idx.length], b = idx[k], c = idx[(k + 1) % idx.length];
        if (side(pts[a], pts[b], pts[c]) <= EPS) continue;      // reflex or straight: not an ear
        const blocked = idx.some(j => {
          if (j === a || j === b || j === c) return false;
          const s = [side(pts[a], pts[b], pts[j]), side(pts[b], pts[c], pts[j]), side(pts[c], pts[a], pts[j])];
          return closed ? s.every(v => v >= -EPS) : s.every(v => v > EPS);
        });
        if (!blocked) cut = k;
      }
      if (cut >= 0) break;
    }
    if (cut < 0) throw new Error('chassis.section: no ear to cut, the polygon is not simple');
    const a = idx[(cut + idx.length - 1) % idx.length], b = idx[cut], c = idx[(cut + 1) % idx.length];
    out.push([a, b, c]);
    idx.splice(cut, 1);
  }
  out.push([idx[0], idx[1], idx[2]]);
  return out;
}

// ---- the fields of ribs, read as fins.py reads them ---------------------------------------

function finSpan(f) {
  const s = f && f.span;
  return Array.isArray(s) && s.length === 2 && s.every(isNum) ? [s[0], s[1]] : null;
}

function finSteps(f) {
  if (!Array.isArray(f.steps) || !f.steps.length) return null;
  const out = [];
  for (const s of f.steps) {
    if (!s || !Array.isArray(s.span) || s.span.length !== 2 || !s.span.every(isNum) || !isNum(s.height)) return null;
    out.push([s.span[0], s.span[1], s.height]);
  }
  return out;
}

const finOutside = f => f.outside === true;
const finLimit = f => { const v = finOutside(f) ? f.height : f.core; return isNum(v) ? v : null; };

// a field with the numbers the geometry needs; one that has not is skipped (lint refuses it)
function finUsable(f) {
  const sp = finSpan(f), lim = finLimit(f);
  return !!f && (f.on === 'top' || f.on === 'bottom') && !!sp && sp[0] < sp[1]
    && isNum(f.rib) && f.rib > 0 && isNum(f.gap) && f.gap > 0 && lim !== null && lim > 0;
}

function finRibCount(f) {
  const [a, b] = finSpan(f);
  return Math.max(0, Math.floor((b - a + f.gap + FIN_TOL) / (f.rib + f.gap)));
}

// the tips' height at x along the length: the step whose half-open span holds it
function finStepHeight(f, x) {
  const st = finSteps(f);
  if (st) for (const [a, b, h] of st) if (a <= x && x < b) return h;
  return finLimit(f);
}

// [{on, outside, x0, x1, height, limit}] for every rib of the usable fields, from the left end
function finRibs(fins) {
  const out = [];
  for (const f of Array.isArray(fins) ? fins : []) {
    if (!finUsable(f)) continue;
    const a = finSpan(f)[0], pitch = f.rib + f.gap;
    for (let i = 0, n = finRibCount(f); i < n; i++) {
      const x0 = a + i * pitch, x1 = x0 + f.rib;
      out.push({on: f.on, outside: finOutside(f), x0, x1, height: finStepHeight(f, (x0 + x1) / 2), limit: finLimit(f)});
    }
  }
  return out;
}

// The section's one edge on the top or the bottom of the box: [x0, x1] across the depth, or null.
function edgeExtent(pts, side, H) {
  const y = side === 'top' ? 0 : H, runs = [];
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
    if (y0 === y1 && Math.abs(y0 - y) <= 0.005 && x0 !== x1) runs.push([Math.min(x0, x1), Math.max(x0, x1)]);
  }
  return runs.length === 1 ? runs[0] : null;
}

// How far the ribs of the outside fields stand beyond the box, above and below it: what the
// camera fit adds to the box. `chassis` is the published chassis or the device's own; zeros
// where there are no fins.
export function finReach(chassis) {
  const out = {top: 0, bottom: 0};
  for (const r of finRibs(chassis && chassis.fins)) if (r.outside) out[r.on] = Math.max(out[r.on], r.height);
  return out;
}

// The fields of a chassis that has to be seated or built from, or null when there are none.
function finsOf(fins) {
  return Array.isArray(fins) && fins.some(finUsable) ? fins.filter(finUsable) : null;
}

// THE BODY IS THE SECTION CUT BACK. Each inside field takes the rectangle from its edge in to its
// core out of the polygon, across the edge's whole extent. The polygon is rectilinear, so this is
// done on the grid its own x and y values and the cuts' make: a cell is solid when it is inside the
// polygon and in no cut, the boundary between solid and empty cells is chained into loops (solid on
// the right, clockwise with y down), and a vertex on a straight run is dropped. Normally one loop;
// a cut that parts the body gives two, and each is built by itself. With no inside field it is the
// polygon, untouched.
//
// `clip` ({lo, hi}, rows of the section's frame; either may be infinite) keeps only the body between
// those rows: the grid takes the finite ones as lines of its own, a cell outside them is empty, and the
// loops then have an edge on the clip row wherever the body crosses it.
export function bodyLoops(section, fins, H, clip) {
  const pts = section.map(p => [Number(p[0]), Number(p[1])]);
  const cuts = [];
  for (const f of finsOf(fins) || []) {
    if (finOutside(f)) continue;
    const ext = edgeExtent(pts, f.on, H);
    if (!ext) continue;
    cuts.push(f.on === 'top' ? [ext[0], 0, ext[1], f.core] : [ext[0], H - f.core, ext[1], H]);
  }
  if (!cuts.length && !clip) return [pts];
  const uniq = a => [...new Set(a)].sort((p, q) => p - q);
  const rows = clip ? [clip.lo, clip.hi].filter(Number.isFinite) : [];
  const xs = uniq([...pts.map(p => p[0]), ...cuts.flatMap(c => [c[0], c[2]])]);
  const ys = uniq([...pts.map(p => p[1]), ...cuts.flatMap(c => [c[1], c[3]]), ...rows]);
  const verticals = [];
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
    if (x0 === x1) verticals.push([x0, Math.min(y0, y1), Math.max(y0, y1)]);
  }
  const nx = xs.length - 1, ny = ys.length - 1;
  const cell = [];
  for (let i = 0; i < nx; i++) {
    cell.push([]);
    for (let j = 0; j < ny; j++) {
      const cx = (xs[i] + xs[i + 1]) / 2, cy = (ys[j] + ys[j + 1]) / 2;
      const inPoly = verticals.filter(([x, lo, hi]) => x > cx && lo < cy && cy < hi).length % 2 === 1;
      const inClip = !clip || (cy > clip.lo && cy < clip.hi);
      cell[i].push(inPoly && inClip && !cuts.some(c => cx > c[0] && cx < c[2] && cy > c[1] && cy < c[3]));
    }
  }
  const solid = (i, j) => i >= 0 && j >= 0 && i < nx && j < ny && cell[i][j];
  const out = new Map();                    // "i,j" of a start vertex -> [[i, j] of the vertices it leads to]
  const edge = (a, b) => { const k = a.join(','); if (!out.has(k)) out.set(k, []); out.get(k).push(b); };
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
    if (!cell[i][j]) continue;
    if (!solid(i, j - 1)) edge([i, j], [i + 1, j]);
    if (!solid(i + 1, j)) edge([i + 1, j], [i + 1, j + 1]);
    if (!solid(i, j + 1)) edge([i + 1, j + 1], [i, j + 1]);
    if (!solid(i - 1, j)) edge([i, j + 1], [i, j]);
  }
  const loops = [];
  for (const k0 of [...out.keys()]) {
    while (out.get(k0) && out.get(k0).length) {
      const loop = [];
      let k = k0;
      do {
        const nxt = out.get(k).shift();
        loop.push(k.split(',').map(Number));
        k = nxt.join(',');
      } while (k !== k0 && out.get(k) && out.get(k).length);
      const world = loop.map(([i, j]) => [xs[i], ys[j]]);
      // a vertex on a straight run is not a vertex
      const kept = world.filter((b, n) => {
        const a = world[(n + world.length - 1) % world.length], c = world[(n + 1) % world.length];
        return side(a, b, c) !== 0;
      });
      if (kept.length >= 4 && area2(kept) > 0) loops.push(kept);
    }
  }
  return loops;
}

// {positions, normals, uvs, indices, groups: [{start, count, materialIndex}]}.
// `section` is the published polygon, [[x, y], ...]; `fins` the published `chassis.fins`
// (or nothing). Indices, not a vertex per corner of every triangle: a cap shares its polygon's
// vertices, a facet has four of its own (each looks a different way, so no vertex is shared
// across the flat shading). Groups are in index units and ascend by material.
//
// `clip` ({lo, hi}, rows of the section's frame) builds only the part of the body between those rows,
// the ribs cropped to them; the faces the cut makes are one more group, SEAM_INDEX, a cap planar at the
// clip row, facing out of the part. Without it the arrays are the whole body, as they were.
export function sectionArrays(section, W, H, D, fins, clip) {
  if (!Array.isArray(section) || section.length < 4) {
    throw new Error('chassis.section: a polygon needs at least four points');
  }
  const pts = section.map(p => [Number(p[0]), Number(p[1])]);
  if (pts.some(p => !Number.isFinite(p[0]) || !Number.isFinite(p[1]))) {
    throw new Error('chassis.section: a point is not a pair of numbers');
  }
  if (area2(pts) <= 0) {
    throw new Error('chassis.section: the polygon is not clockwise with y down');
  }
  const ribs = finRibs(fins);
  if (ribs.length > FIN_MAX_RIBS) {
    throw new Error(`chassis.fins: ${ribs.length} ribs, at most ${FIN_MAX_RIBS} a device`);
  }
  const loops = bodyLoops(pts, fins, H, clip);
  const at = (sx, sy, half) => [half, H / 2 - sy, D / 2 - sx];
  const cutRow = y => !!clip && (y === clip.lo || y === clip.hi);
  const byMat = new Map();
  const add = (mi, quad) => {            // quad: {points: [[x,y,z]...], n}, as triangles
    if (!byMat.has(mi)) byMat.set(mi, []);
    byMat.get(mi).push(quad);
  };

  // the two caps: each loop's triangles, wound to face along their normal
  for (const [mi, half, n] of [[FACE_INDEX.right, W / 2, [1, 0, 0]], [FACE_INDEX.left, -W / 2, [-1, 0, 0]]]) {
    for (const loop of loops) {
      for (const t of earClip(loop)) add(mi, {points: t.map(i => at(loop[i][0], loop[i][1], half)), n});
    }
  }

  // the facets: a rectangle across the whole width for each edge, looking along
  // the edge's outward normal (dy, -dx) in the section frame
  for (const loop of loops) {
    for (let i = 0; i < loop.length; i++) {
      const [x0, y0] = loop[i], [x1, y1] = loop[(i + 1) % loop.length];
      const dx = x1 - x0, dy = y1 - y0;
      if ((dx !== 0 && dy !== 0) || (dx === 0 && dy === 0)) {
        throw new Error(`chassis.section: the edge from point ${i} is not a straight axis-aligned edge`);
      }
      const nx = Math.sign(dy), ny = -Math.sign(dx);
      // section frame to viewer frame: ny < 0 is toward +y (up); nx > 0 is toward the rear (-z)
      const mi = dy === 0 && cutRow(y0) ? SEAM_INDEX
        : ny < 0 ? FACE_INDEX.top : ny > 0 ? FACE_INDEX.bottom : nx > 0 ? FACE_INDEX.rear : FACE_INDEX.front;
      const n = [0, -ny, -nx];
      add(mi, {points: [at(x0, y0, -W / 2), at(x1, y1, -W / 2), at(x1, y1, W / 2), at(x0, y0, W / 2)], n, quad: true});
    }
  }

  // the ribs: a slab for each, the edge's whole extent across the depth, from its root on the
  // surface to its tip. Five faces; the sixth is against the surface and is never seen. In the
  // section frame y grows down: a top rib's tip is at the smaller y, a bottom rib's at the larger.
  for (const r of ribs) {
    const ext = edgeExtent(pts, r.on, H);
    if (!ext) continue;
    const top = r.on === 'top';
    const root = r.outside ? (top ? 0 : H) : (top ? r.limit : H - r.limit);
    const tip = top ? root - r.height : root + r.height;
    const [ra, rb] = [Math.min(root, tip), Math.max(root, tip)];
    // a part keeps the stretch of the rib between its rows; a rib the seam crosses is cut there and capped
    const lo = clip ? clip.lo : -Infinity, hi = clip ? clip.hi : Infinity;
    const ya = Math.max(ra, lo), yb = Math.min(rb, hi);
    if (yb - ya <= EPS) continue;
    const [e0, e1] = ext, hx0 = -W / 2 + r.x0, hx1 = -W / 2 + r.x1;
    const P = (sx, sy, hx) => at(sx, sy, hx);
    const tipY = tip;
    if (tip >= lo && tip <= hi) {
      add(top ? FACE_INDEX.top : FACE_INDEX.bottom,
          {points: [P(e0, tipY, hx0), P(e1, tipY, hx0), P(e1, tipY, hx1), P(e0, tipY, hx1)],
           n: [0, top ? 1 : -1, 0], quad: true});
    }
    for (const [row, cut, ny] of [[lo, ya > ra, 1], [hi, yb < rb, -1]]) {
      if (cut) add(SEAM_INDEX, {points: [P(e0, row, hx0), P(e1, row, hx0), P(e1, row, hx1), P(e0, row, hx1)],
                                n: [0, ny, 0], quad: true});
    }
    add(FACE_INDEX.right, {points: [P(e0, ya, hx1), P(e1, ya, hx1), P(e1, yb, hx1), P(e0, yb, hx1)], n: [1, 0, 0], quad: true});
    add(FACE_INDEX.left, {points: [P(e0, ya, hx0), P(e1, ya, hx0), P(e1, yb, hx0), P(e0, yb, hx0)], n: [-1, 0, 0], quad: true});
    add(FACE_INDEX.front, {points: [P(e0, ya, hx0), P(e0, ya, hx1), P(e0, yb, hx1), P(e0, yb, hx0)], n: [0, 0, 1], quad: true});
    add(FACE_INDEX.rear, {points: [P(e1, ya, hx0), P(e1, ya, hx1), P(e1, yb, hx1), P(e1, yb, hx0)], n: [0, 0, -1], quad: true});
  }

  const positions = [], normals = [], uvs = [], indices = [], groups = [];
  let vertex = 0;
  const key = p => p.map(v => v.toFixed(6)).join(',');
  for (const mi of [...byMat.keys()].sort((a, b) => a - b)) {
    const start = indices.length;
    const shared = new Map();            // a cap's vertices are shared within the cap
    const vert = (p, n, reuse) => {
      const k = key(p);
      if (reuse && shared.has(k)) return shared.get(k);
      positions.push(...p);
      normals.push(...n);
      // a cap has no drawing of its own; its UV is unused but present, as a bevel's is
      uvs.push(...(mi === SEAM_INDEX ? [0, 0] : boxUV(mi, p, W, H, D)));
      if (reuse) shared.set(k, vertex);
      return vertex++;
    };
    for (const q of byMat.get(mi)) {
      const v = q.points.map(p => vert(p, q.n, !q.quad));
      const tri = q.quad ? [[v[0], v[1], v[2]], [v[0], v[2], v[3]]] : [v];
      for (const t of tri) {
        // wind each triangle so its geometric normal agrees with the stored one
        const P = t.map(i => [positions[3 * i], positions[3 * i + 1], positions[3 * i + 2]]);
        const u = [P[1][0] - P[0][0], P[1][1] - P[0][1], P[1][2] - P[0][2]];
        const w = [P[2][0] - P[0][0], P[2][1] - P[0][1], P[2][2] - P[0][2]];
        const c = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]];
        const flip = c[0] * q.n[0] + c[1] * q.n[1] + c[2] * q.n[2] < 0;
        indices.push(t[0], flip ? t[2] : t[1], flip ? t[1] : t[2]);
      }
    }
    groups.push({start, count: indices.length - start, materialIndex: mi});
  }
  return {positions, normals, uvs, indices, groups};
}

// WHERE A PART STANDS ON A STEPPED HOUSING. A part is built on the flat plane of
// the bounding box's face; over a recessed casting that plane is in the air. This
// is how far, in millimetres along the face's outward normal, the section's OUTER
// surface under the part stands from that plane: 0 where the housing reaches the
// plane, negative where it is recessed.
//   front, rear   `at` is a row, mm down from the top; the surface is the
//                 outermost vertical facet that row crosses, its depth from the
//                 plane being the facet's x (front) or D - x (rear)
//   top, bottom   `at` is a column, mm back from the front; the surface is the
//                 outermost horizontal facet over that column
// The right and left faces are the caps, flat at the ends of the extrusion, and
// any other face (a part's own) has no section: 0. A row or column exactly on a
// step takes the outermost of the facets that meet there, and one outside the
// solid takes 0. The polygon touches all four sides of its box (section.py), so
// its x runs 0..D and its y 0..H.
//
// WITH FINS (`fins`, the published fields): lint refuses a part on the front or the
// rear over a field or above its tip line, so this is for one that slips through. The
// casting is cut back to its core along the whole length, so a row inside an inside
// field's zone, between its edge and its core, has no wall under it: it is read at the
// core line instead, the first row of the casting, and the part stands from that wall.
// A column on the top or the bottom is the polygon's, which is the tip plane the ribs
// reach: a part there stands on the ribs' tops (lint judges those by the section's rule).
export function surfaceUnder(section, face, at, W, H, D, fins) {
  const pts = section.map(p => [Number(p[0]), Number(p[1])]);
  const lone = face === 'front' || face === 'rear';
  if (!lone && face !== 'top' && face !== 'bottom') return 0;
  if (lone) {
    for (const f of finsOf(fins) || []) {
      if (finOutside(f)) continue;
      if (f.on === 'top') at = Math.max(at, f.core);
      else at = Math.min(at, H - f.core);
    }
  }
  const near = [];          // positions along the facet's axis of the facets facing this face
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
    if (lone && x0 === x1 && y0 !== y1) {
      const rearward = y1 > y0;           // the outward normal (dy, -dx): toward the rear for dy > 0
      if ((face === 'rear') === rearward && Math.min(y0, y1) - EPS <= at && at <= Math.max(y0, y1) + EPS) near.push(x0);
    } else if (!lone && y0 === y1 && x0 !== x1) {
      const up = x1 > x0;                 // ny = -sign(dx): up for dx > 0
      if ((face === 'top') === up && Math.min(x0, x1) - EPS <= at && at <= Math.max(x0, x1) + EPS) near.push(y0);
    }
  }
  if (!near.length) return 0;
  if (face === 'front') return -Math.min(...near);
  if (face === 'rear') return Math.max(...near) - D;
  if (face === 'top') return -Math.min(...near);
  return Math.max(...near) - H;
}

// `surfaceUnder` for a point of the face's flat plane in the viewer's frame
// (+x right, +y up, +z out of the front, the box centred on the origin): a
// front or rear part's row is its height below the top, a top or bottom part's
// column its distance behind the front.
export function seatPoint(section, face, p, W, H, D, fins) {
  if (face === 'front' || face === 'rear') return surfaceUnder(section, face, H / 2 - p[1], W, H, D, fins);
  if (face === 'top' || face === 'bottom') return surfaceUnder(section, face, D / 2 - p[2], W, H, D, fins);
  return 0;
}

// The fields of ribs a part is seated against: the published `chassis.fins` when the chassis
// builds as a stepped body and states usable ones, else null.
export function seatFins(chassis, W, H, D) {
  const b = sectionBody(chassis, W, H, D);
  return b && b.arrays && finsOf(chassis.fins) ? chassis.fins : null;
}

// The polygon relief seats parts on: the published section when the chassis
// builds as a stepped body (sectionBody has arrays), else null, so a device
// without one - or with one that is refused - is placed on the flat planes.
export function sectionSeat(chassis, W, H, D) {
  const b = sectionBody(chassis, W, H, D);
  return b && b.arrays ? chassis.section : null;
}

// What viewer3d.js asks about a chassis (the `chassis` of configs.json):
//   null                     the chassis states no section: build it as before
//   {arrays}                 the section extruded along the width
//   {refused: 'reason'}      a section that cannot be built, or that is stated
//                            with another body key; the caller warns and builds
//                            what it built before there was a section
// Lint refuses a section together with bevel, rounded and ears, and a sheet
// shell is no extrusion, so these are guards, not a feature. `halves` is no
// clash: the closed body of a housing that opens is this body; the open state
// is `sectionHalves`.
export function sectionBody(chassis, W, H, D) {
  if (!chassis || !Array.isArray(chassis.section) || !chassis.section.length) return null;
  const clash = ['solid', 'bevel', 'rounded'].filter(k => chassis[k]);
  if (chassis.shell === 'sheet') clash.push('shell: sheet');
  if (clash.length) return {refused: `chassis.section is stated with ${clash.join(', ')}`};
  try {
    return {arrays: sectionArrays(chassis.section, W, H, D, chassis.fins)};
  } catch (e) {
    return {refused: String(e.message || e)};
  }
}

// A part: its arrays, their bounds, and `body`, the bounds of the casting alone, the ribs left out
// (the loops of the cut-back section, in the box frame): where a stand-in for a module can be set
// against the casting's own surface rather than the rib tips.
const partOf = (arrays, loops, W, H, D) => {
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < arrays.positions.length; i++) {
    const k = i % 3, v = arrays.positions[i];
    if (v < min[k]) min[k] = v;
    if (v > max[k]) max[k] = v;
  }
  const pts = loops.flat();
  const bmin = [-W / 2, H / 2 - Math.max(...pts.map(p => p[1])), D / 2 - Math.max(...pts.map(p => p[0]))];
  const bmax = [W / 2, H / 2 - Math.min(...pts.map(p => p[1])), D / 2 - Math.min(...pts.map(p => p[0]))];
  return {arrays, min, max, size: max.map((v, i) => v - min[i]), center: max.map((v, i) => (v + min[i]) / 2),
          body: {min: bmin, max: bmax, size: bmax.map((v, i) => v - bmin[i]),
                 center: bmax.map((v, i) => (v + bmin[i]) / 2)}};
};

// THE BODY CUT AT THE SEAM. `halves` is the published `chassis.halves`. The seam is the row
// `base.stands` from the base's `outer` face (spec/tools/portrayal/section.py seam_row reads the same
// rule): that many rows down from the top for `top`, up from the bottom for `bottom`. The base is the
// body on the `outer` side of it, the lid the rest, each its own `sectionArrays` with the cap
// (SEAM_INDEX). Returns
//   {seam, pivot, base, lid}   base and lid: {arrays, min, max, size, center, body} in the box frame,
//                              `body` the bounds of the casting without its ribs
// `seam` is the row in the section's frame; `pivot` a point of the line the lid turns about, in the
// box frame: x = 0, the seam's height, and z at the hinge face's outline in the seam's row, the
// foremost x of the body there for `front` and the rearmost for `rear`. Throws where the seam cannot
// divide the body: a face that does not open a section, a seam outside it or on a horizontal edge.
export function splitSection(section, W, H, D, fins, halves) {
  const base = halves && halves.base, lid = halves && halves.lid;
  const outer = base && base.outer, hinge = lid && lid.hinge;
  if (outer !== 'top' && outer !== 'bottom') {
    throw new Error(`chassis.halves: a housing with a section opens from its top or bottom, not '${outer}'`);
  }
  if (hinge !== 'front' && hinge !== 'rear') {
    throw new Error(`chassis.halves: a housing with a section is hinged on its front or rear, not '${hinge}'`);
  }
  if (!isNum(base.stands) || base.stands <= 0) throw new Error('chassis.halves.base.stands is not a positive number');
  const pts = section.map(p => [Number(p[0]), Number(p[1])]);
  const seam = outer === 'top' ? base.stands : H - base.stands;
  const rows = pts.map(p => p[1]);
  if (!(seam > Math.min(...rows) + 0.005 && seam < Math.max(...rows) - 0.005)) {
    throw new Error(`chassis.halves: the seam, ${seam} mm down the section, is outside it: one half would be empty`);
  }
  if (rows.some(y => Math.abs(y - seam) <= 0.005)) {
    throw new Error(`chassis.halves: the seam, ${seam} mm down the section, is on a horizontal edge of it`);
  }
  const upper = {lo: -Infinity, hi: seam}, lower = {lo: seam, hi: Infinity};
  const clips = outer === 'top' ? {base: upper, lid: lower} : {base: lower, lid: upper};
  const out = {seam};
  for (const name of ['base', 'lid']) {
    out[name] = partOf(sectionArrays(pts, W, H, D, fins, clips[name]), bodyLoops(pts, fins, H, clips[name]), W, H, D);
  }
  const xs = bodyLoops(pts, fins, H, clips.base).flat().filter(p => p[1] === seam).map(p => p[0]);
  if (!xs.length) throw new Error('chassis.halves: the body has no outline at the seam');
  const x = hinge === 'front' ? Math.min(...xs) : Math.max(...xs);
  out.pivot = [0, H / 2 - seam, D / 2 - x];
  return out;
}

// What viewer3d.js asks about a chassis that opens (the `chassis` of configs.json):
//   null                 no section or no halves: the halves are boxes, as housing.js builds them
//   {split}              splitSection of the body, for housingPlan and the open state
//   {refused: 'reason'}  halves the body cannot be split at; the caller warns and builds the boxes
export function sectionHalves(chassis, W, H, D) {
  if (!chassis || !Array.isArray(chassis.section) || !chassis.section.length || !chassis.halves) return null;
  const body = sectionBody(chassis, W, H, D);
  if (!body || body.refused) return body && {refused: body.refused};
  try {
    return {split: splitSection(chassis.section, W, H, D, chassis.fins, chassis.halves)};
  } catch (e) {
    return {refused: String(e.message || e)};
  }
}
