// A BOX THAT OPENS: what a viewer needs to show it open, with no three.js and no
// DOM, so a page, the 3D scene and the node tests read one definition.
//
// `chassis.halves` (configs.json) says a device is a base and a lid. The closed
// box is drawn from its six faces as for any device; the open state is these
// numbers. Everything is in the box's own frame, the one viewer3d.js builds in:
// x to the right, y up, z out of the front, the origin at the centre of the
// closed box. A device that states no halves gets `null` from every function
// here, and a page then does what it always did.

export const HOUSING = ['closed', 'open'];

// the outward normal of each face, as the views are named
const NORMAL = {
  front: [0, 0, 1], rear: [0, 0, -1], right: [1, 0, 0],
  left: [-1, 0, 0], top: [0, 1, 0], bottom: [0, -1, 0],
};
// BoxGeometry's material index for a face normal: +x -x +y -y +z -z
const INDEX_OF = {'1,0,0': 0, '-1,0,0': 1, '0,1,0': 2, '0,-1,0': 3, '0,0,1': 4, '0,0,-1': 5};
// the two directions a floor's drawing runs in, by the axis the halves stand
// along: u to the right and v up on the floor as seen from the seam
const PLATE_AXES = {x: [[0, 0, 1], [0, 1, 0]], y: [[1, 0, 0], [0, 0, 1]], z: [[1, 0, 0], [0, 1, 0]]};
// the angle the lid opens to when the device does not state one: laid flat
const DEFAULT_ANGLE = 180;

const num = v => (typeof v === 'number' && Number.isFinite(v) ? v : null);
const axisOf = n => (n[0] ? 'x' : n[1] ? 'y' : 'z');
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const scale = (a, k) => [a[0] * k, a[1] * k, a[2] * k];
const absv = a => a.map(Math.abs);

// 'open' or 'closed'; anything a caller sends that is not 'open' is closed
export const normalizeHousing = v => (String(v).toLowerCase() === 'open' ? 'open' : 'closed');

// `chassis.halves` as configs.json carries it, or null
export function halvesOf(meta) {
  const h = meta && meta.chassis && meta.chassis.halves;
  return h && h.base && h.lid ? h : null;
}

// the bays that are in a half: [{id, view, half}], in the order of the views
export function bayHalves(meta) {
  const out = [];
  for (const view of (meta && meta.views) || Object.keys((meta && meta.bays) || {}))
    for (const b of ((meta && meta.bays) || {})[view] || [])
      if (b.half) out.push({id: b.id, view, half: b.half});
  return out;
}

// The authored open drawing is found by what it holds, not by its name: the
// first view whose bays are in a half. null when the device has none.
export function openViewOf(meta) {
  if (!halvesOf(meta)) return null;
  const hit = bayHalves(meta)[0];
  if (hit) return hit.view;
  return ((meta.views || []).find(v => /(^|-)open$/.test(v))) || null;
}

// The view a 2D page shows for a housing state. Open selects the authored open
// drawing; closed leaves it for the first view that is not the open one (or
// keeps the view the reader is on, when that is not it). A box that does not
// open, or one whose open drawing is missing, keeps the current view.
export function viewFor(meta, housing, current) {
  const open = openViewOf(meta);
  if (!open) return current;
  if (normalizeHousing(housing) === 'open') return open;
  if (current !== open) return current;
  return (meta.views || []).find(v => v !== open) || current;
}

// What a page or a tool is told: the halves with their figures and the
// bays in each. null for a box that does not open.
export function describeHalves(meta) {
  const h = halvesOf(meta);
  if (!h) return null;
  const bays = bayHalves(meta);
  const of = name => bays.filter(b => b.half === name).map(b => b.id);
  return {
    view: openViewOf(meta),
    base: {outer: h.base.outer, stands: num(h.base.stands), bays: of('base')},
    lid: {hinge: h.lid.hinge, angle: num(h.lid.angle), stands: num(h.lid.stands), bays: of('lid')},
  };
}

function rotate(v, axis, angle) {            // Rodrigues, axis a unit vector
  const c = Math.cos(angle), s = Math.sin(angle), k = dot(axis, v);
  return add(add(scale(v, c), scale(cross(axis, v), s)), scale(axis, k * (1 - c)));
}

// The open state of a box. `size` is {w, h, d}, the closed box. Returns null
// when the device states no halves or a face the halves name is unknown.
//
//   s       the direction the halves stand along, from the base's outer face
//           toward the lid's: the base's outer normal, reversed
//   seam    where the halves meet, `base.stands` from the base's outer face
//   base    {size, center, seam, floor}   a shell standing `stands` from the seam
//   lid     {size, center, seam, floor, pivot, axis, angle, quaternion,
//            closedCenter}  turned about the hinge edge by `angle` (radians)
//
// `seam` and `floor` are the normals of the open face and of the outer face,
// in the half's own frame (before the lid turns). The lid turns the way that
// takes its outer face toward the hinge side, whatever the face it hinges on.
// A lid that states no angle opens to 180 degrees, laid flat.
//
// A HOUSING WITH A SECTION (`split`, section.js `sectionHalves`) is not two boxes. `size` is
// still the closed box; each half then takes the size and centre of its own part of the stepped
// body (ribs and ribs that stand outside the box included), the lid's closed centre is its
// part's, and the hinge edge is the line the split names: where the seam meets the hinge face's
// outline, not the box's edge. The plan carries `split` so the viewer builds the parts, and a
// call without one is the plan of two boxes, as it has always been.
export function housingPlan(halves, size, split) {
  if (!halves || !halves.base || !halves.lid || !size) return null;
  const outer = NORMAL[halves.base.outer], hinge = NORMAL[halves.lid.hinge];
  const bs = num(halves.base.stands), ls = num(halves.lid.stands);
  if (!outer || !hinge || bs == null || ls == null || bs <= 0 || ls <= 0) return null;
  const s = scale(outer, -1);
  if (dot(s, hinge) !== 0) return null;      // a hinge on the seam's own axis cannot swing
  const dims = {x: size.w, y: size.h, z: size.d};
  const ext = n => [Math.abs(n[0]) ? dims.x : 0, Math.abs(n[1]) ? dims.y : 0, Math.abs(n[2]) ? dims.z : 0];
  const along = axisOf(s);
  const dimAlong = dims[along];
  const half = (stands) => {
    const sz = [dims.x, dims.y, dims.z];
    sz[{x: 0, y: 1, z: 2}[along]] = stands;
    return sz;
  };
  // the coordinate along s of the base's outer face, then the seam
  const tOuter = -dimAlong / 2;
  const seamAt = scale(s, tOuter + bs);
  const baseCenter = scale(s, tOuter + bs / 2);
  const lidClosed = scale(s, tOuter + bs + ls / 2);
  // the hinge edge: on the seam, on the hinge face
  const hingeHalf = scale(hinge, (ext(hinge).reduce((a, b) => a + b, 0)) / 2);
  const boxPivot = add(seamAt, sub(hingeHalf, scale(s, dot(hingeHalf, s))));
  // the axis that turns s toward the hinge's normal: a = s x n
  const axis = cross(s, hinge);
  const angle = (num(halves.lid.angle) ?? DEFAULT_ANGLE) * Math.PI / 180;
  const parts = split && split.base && split.lid && split.pivot ? split : null;
  const pivot = parts ? parts.pivot : boxPivot;
  const closed = parts ? parts.lid.center : lidClosed;
  const lidCenter = add(pivot, rotate(sub(closed, pivot), axis, angle));
  const sh = Math.sin(angle / 2);
  const plan = {
    s, along,
    base: {size: parts ? parts.base.size : half(bs), center: parts ? parts.base.center : baseCenter,
           seam: s, floor: outer, stands: bs},
    lid: {size: parts ? parts.lid.size : half(ls), center: lidCenter, closedCenter: closed,
          seam: scale(s, -1), floor: s, stands: ls, pivot, axis, angle,
          quaternion: [axis[0] * sh, axis[1] * sh, axis[2] * sh, Math.cos(angle / 2)]},
  };
  if (parts) {
    plan.split = parts;
    // where a stand-in for a module is set: against the casting's own surface, the ribs left out
    for (const name of ['base', 'lid']) {
      const b = parts[name].body;
      if (b) plan[name].body = {size: b.size, offset: sub(b.center, parts[name].center)};
    }
  }
  return plan;
}

// a point of the lid's own frame, in the box frame once the lid is open
export function lidPoint(plan, local) {
  const l = plan.lid;
  return add(l.pivot, rotate(sub(add(l.closedCenter, local), l.pivot), l.axis, l.angle));
}

// The box the open state fills, in the box frame: {min, max, size, center}, the
// tightest axis-aligned box round the base and the turned lid. What a camera
// frames when the box is open; the closed box is no guide, a lid laid flat
// reaches a lid's depth past the hinge. null when there is no plan.
export function openBounds(plan) {
  if (!plan) return null;
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  const take = p => p.forEach((v, i) => { min[i] = Math.min(min[i], v); max[i] = Math.max(max[i], v); });
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) {
    const k = [sx, sy, sz];
    take(add(plan.base.center, plan.base.size.map((v, i) => k[i] * v / 2)));
    take(lidPoint(plan, plan.lid.size.map((v, i) => k[i] * v / 2)));
  }
  return {min, max, size: sub(max, min), center: scale(add(min, max), 0.5)};
}

export const faceIndexOf = n => INDEX_OF[n.join(',')];

// The bays of one half as plates on its floor, in the half's own frame. The
// open drawing's regions are not published, so the half's bays are placed by
// where they are to each other: the bounding box of the half's bays, kept at
// true size where it fits the floor and shrunk to fit where it does not, and
// centred. `bays` are configs.json's rows (`at`, `size` in the drawing's mm,
// y down). A stand-in for the drawing, never a measurement.
export function bayPlates(plan, name, bays, thickness = 1) {
  const half = plan && plan[name];
  const mine = (bays || []).filter(b => b.half === name && b.at && b.size);
  if (!half || !mine.length) return [];
  const [u, v] = PLATE_AXES[plan.along];
  const x0 = Math.min(...mine.map(b => b.at[0])), y0 = Math.min(...mine.map(b => b.at[1]));
  const x1 = Math.max(...mine.map(b => b.at[0] + b.size.w)), y1 = Math.max(...mine.map(b => b.at[1] + b.size.h));
  // a stepped half (`body`) is floored on its casting, not on the tips of its ribs
  const room = half.body ? half.body.size : half.size, off = half.body ? half.body.offset : [0, 0, 0];
  const fw = Math.abs(dot(u, room.map(Math.abs))), fh = Math.abs(dot(v, room.map(Math.abs)));
  const k = Math.min(1, (fw * 0.9) / (x1 - x0), (fh * 0.9) / (y1 - y0));
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const depth = add(off, scale(half.floor, (Math.abs(dot(half.floor, room)) - thickness) / 2));
  return mine.map(b => {
    const du = ((b.at[0] + b.size.w / 2) - cx) * k, dv = -((b.at[1] + b.size.h / 2) - cy) * k;
    const sz = add(add(scale(absv(u), b.size.w * k), scale(absv(v), b.size.h * k)),
                   scale(absv(half.floor), thickness));
    return {id: b.id, half: name, size: sz, center: add(depth, add(scale(u, du), scale(v, dv)))};
  });
}
