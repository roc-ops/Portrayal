// A bevelled chassis body, built from the polygons render.py publishes (#735).
//
// `<device>.configs.json` carries `chassis.solid.polygons` for a device whose
// edges are bevelled: each polygon tagged with the face it lies in, or `bevel`,
// wound counter-clockwise seen from outside, in the viewer's frame (box centred
// on the origin, +x right, +y up, +z out of the front). spec/tools/portrayal/
// bevel.py builds them, and the 2D drawings are projections of the same ones,
// so nothing here decides geometry: it only triangulates and maps textures.
//
// THE TEXTURE MAPPING IS BoxGeometry's, ON PURPOSE. Every face texture the kit
// rasterises - the relief punches, the flips, refineFace's sharper rasters -
// is prepared for the UV layout three.js gives a box, so a face polygon takes
// the UV that point would have had on the full box face. The flat front of an
// AIS switch then shows exactly the part of the front drawing that lies on the
// flat, and the drawing's bevel strips fall on the bevel polygons instead, which
// are plain lit metal. The table is BoxGeometry.buildPlane's (three r161):
// [u axis, u dir, v axis, v dir] per material index.
//
// Pure arrays and no `three` import, so node can test it; viewer3d.js turns the
// result into a BufferGeometry.

export const FACE_INDEX = {right: 0, left: 1, top: 2, bottom: 3, front: 4, rear: 5};
export const BEVEL_INDEX = 6;

const PLANE = [
  ['z', -1, 'y', -1],   // 0 +x right
  ['z',  1, 'y', -1],   // 1 -x left
  ['x',  1, 'z',  1],   // 2 +y top
  ['x',  1, 'z', -1],   // 3 -y bottom
  ['x',  1, 'y', -1],   // 4 +z front
  ['x', -1, 'y', -1],   // 5 -z rear
];
const AXIS = {x: 0, y: 1, z: 2};

function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }
function cross(a, b) {
  return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
}
function unit(a) { const n = Math.hypot(...a) || 1; return [a[0] / n, a[1] / n, a[2] / n]; }

// The UV a point on box face `index` takes - BoxGeometry's own formula.
export function boxUV(index, p, W, H, D) {
  const size = {x: W, y: H, z: D};
  const [ua, ud, va, vd] = PLANE[index];
  const u = (p[AXIS[ua]] * ud + size[ua] / 2) / size[ua];
  const v = 1 - (p[AXIS[va]] * vd + size[va] / 2) / size[va];
  return [u, v];
}

// {positions, normals, uvs, groups: [{start, count, materialIndex}]}: one fan of
// triangles per polygon, flat-shaded, grouped by material so the six face
// textures stay at indices 0-5 and every bevel shares index 6.
export function bevelledArrays(polygons, W, H, D) {
  const byMat = new Map();
  for (const poly of polygons) {
    const mi = poly.face === 'bevel' ? BEVEL_INDEX : FACE_INDEX[poly.face];
    if (mi === undefined) throw new Error(`unknown face ${poly.face}`);
    if (!byMat.has(mi)) byMat.set(mi, []);
    byMat.get(mi).push(poly.points);
  }
  const positions = [], normals = [], uvs = [], groups = [];
  let vertex = 0;
  for (const mi of [...byMat.keys()].sort((a, b) => a - b)) {
    const start = vertex;
    for (const pts of byMat.get(mi)) {
      const n = unit(cross(sub(pts[1], pts[0]), sub(pts[2], pts[0])));
      for (let i = 1; i + 1 < pts.length; i++) {
        for (const p of [pts[0], pts[i], pts[i + 1]]) {
          positions.push(...p);
          normals.push(...n);
          // a bevel has no drawing of its own; its UV is unused but present,
          // because a BufferGeometry with uvs needs one per vertex
          uvs.push(...(mi === BEVEL_INDEX ? [0, 0] : boxUV(mi, p, W, H, D)));
          vertex++;
        }
      }
    }
    groups.push({start, count: vertex - start, materialIndex: mi});
  }
  return {positions, normals, uvs, groups};
}
