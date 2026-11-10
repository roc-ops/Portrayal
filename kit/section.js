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
// No `three` in here.

import { boxUV, FACE_INDEX } from './bevel.js';

const EPS = 1e-9;

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

// {positions, normals, uvs, indices, groups: [{start, count, materialIndex}]}.
// `section` is the published polygon, [[x, y], ...]. Indices, not a vertex per
// corner of every triangle: a cap shares its polygon's vertices, a facet has
// four of its own (each looks a different way, so no vertex is shared across
// the flat shading). Groups are in index units and ascend by material.
export function sectionArrays(section, W, H, D) {
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
  const at = (sx, sy, half) => [half, H / 2 - sy, D / 2 - sx];
  const byMat = new Map();
  const add = (mi, quad) => {            // quad: {points: [[x,y,z]...], n}, as triangles
    if (!byMat.has(mi)) byMat.set(mi, []);
    byMat.get(mi).push(quad);
  };

  // the two caps: the polygon's triangles, wound to face along their normal
  for (const [mi, half, n] of [[FACE_INDEX.right, W / 2, [1, 0, 0]], [FACE_INDEX.left, -W / 2, [-1, 0, 0]]]) {
    for (const t of earClip(pts)) add(mi, {points: t.map(i => at(pts[i][0], pts[i][1], half)), n});
  }

  // the facets: a rectangle across the whole width for each edge, looking along
  // the edge's outward normal (dy, -dx) in the section frame
  for (let i = 0; i < pts.length; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[(i + 1) % pts.length];
    const dx = x1 - x0, dy = y1 - y0;
    if ((dx !== 0 && dy !== 0) || (dx === 0 && dy === 0)) {
      throw new Error(`chassis.section: the edge from point ${i} is not a straight axis-aligned edge`);
    }
    const nx = Math.sign(dy), ny = -Math.sign(dx);
    // section frame to viewer frame: ny < 0 is toward +y (up); nx > 0 is toward the rear (-z)
    const mi = ny < 0 ? FACE_INDEX.top : ny > 0 ? FACE_INDEX.bottom : nx > 0 ? FACE_INDEX.rear : FACE_INDEX.front;
    const n = [0, -ny, -nx];
    add(mi, {points: [at(x0, y0, -W / 2), at(x1, y1, -W / 2), at(x1, y1, W / 2), at(x0, y0, W / 2)], n, quad: true});
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
      uvs.push(...boxUV(mi, p, W, H, D));
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
export function surfaceUnder(section, face, at, W, H, D) {
  const pts = section.map(p => [Number(p[0]), Number(p[1])]);
  const lone = face === 'front' || face === 'rear';
  if (!lone && face !== 'top' && face !== 'bottom') return 0;
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
export function seatPoint(section, face, p, W, H, D) {
  if (face === 'front' || face === 'rear') return surfaceUnder(section, face, H / 2 - p[1], W, H, D);
  if (face === 'top' || face === 'bottom') return surfaceUnder(section, face, D / 2 - p[2], W, H, D);
  return 0;
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
// Lint refuses a section together with bevel, rounded, ears and halves, and a
// sheet shell is no extrusion, so these are guards, not a feature.
export function sectionBody(chassis, W, H, D) {
  if (!chassis || !Array.isArray(chassis.section) || !chassis.section.length) return null;
  const clash = ['solid', 'bevel', 'rounded', 'halves'].filter(k => chassis[k]);
  if (chassis.shell === 'sheet') clash.push('shell: sheet');
  if (clash.length) return {refused: `chassis.section is stated with ${clash.join(', ')}`};
  try {
    return {arrays: sectionArrays(chassis.section, W, H, D)};
  } catch (e) {
    return {refused: String(e.message || e)};
  }
}
