// The 3D viewer's opening view, fitted to the whole box it opens on.
//
// No THREE in here, so it runs under node and the test can hold it to the
// numbers: viewer3d.js hands it the box, the lens and the frame's aspect and
// applies what comes back.
//
// WHY THIS IS NOT `span * k`. The opening view used to be the direction
// (0.9, 0.8, 1.6) at `span` times its length, which is two spans out. That
// frames anything about as tall as it is deep. A 7 ft vertical manager is 2130
// tall and 203 wide: the eye was put 4260 mm away and OrbitControls then
// pulled it back to its 2500 mm maxDistance on the first update, where a 40
// degree lens sees 1820 mm top to bottom, so the part was cut off at both ends
// and the far plane at 3000 clipped what the frame still held. The distance
// has to come from the box, the lens and the aspect, and the limits that
// follow the camera (maxDistance, far) have to move with it.
//
// The distance is the SMALLEST one at which all eight corners of the box
// project inside `fill` of the frame, and never less than the old two spans,
// so a box that was framed well keeps the opening view it always had.

export const OPENING_DIR = [0.9, 0.8, 1.6];
const BASE_MAX_DISTANCE = 2500;
const BASE_FAR = 3000;

const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const unit = a => { const n = Math.hypot(...a); return a.map(v => v / n); };

// The camera's own axes for an eye on `dir` looking at the origin, y up: what
// THREE's lookAt builds.
function basis(dir) {
  const fwd = unit(dir.map(v => -v));
  const right = unit(cross(fwd, [0, 1, 0]));
  return {fwd, right, up: cross(right, fwd)};
}

// Where the eight corners of a W x H x D box centred on the origin land in the
// frame (x, y in -1..1 when inside it), for an eye `dist` out along `dir`.
// `depth` is each corner's distance in front of the lens; a corner at or behind
// it is not in the frame at all.
export function projectCorners({W, H, D}, dir, dist, fov, aspect) {
  const d = unit(dir), {fwd, right, up} = basis(d);
  const eye = d.map(v => v * dist);
  const tv = Math.tan(fov * Math.PI / 360), th = tv * aspect;
  const out = [];
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) for (const sz of [-1, 1]) {
    const v = [sx * W / 2 - eye[0], sy * H / 2 - eye[1], sz * D / 2 - eye[2]];
    const depth = dot(v, fwd);
    out.push({depth, x: dot(v, right) / (depth * th), y: dot(v, up) / (depth * tv)});
  }
  return out;
}

const inside = (corners, fill) => corners.every(c => c.depth > 0 && Math.abs(c.x) <= fill && Math.abs(c.y) <= fill);

// {position, distance, maxDistance, far} for a box of W x H x D, a lens of
// `fov` degrees (vertical) and a frame `aspect` wide per high.
export function openingView({W, H, D, fov = 40, aspect = 1, fill = 0.92, dir = OPENING_DIR,
                             span = Math.max(W, H, D)}) {
  const old = span * Math.hypot(...dir);          // two spans, as it always was
  let dist = old;
  if (!inside(projectCorners({W, H, D}, dir, old, fov, aspect), fill)) {
    // monotone: the further out, the smaller everything is. Bracket, then bisect.
    let lo = old, hi = old * 2;
    while (!inside(projectCorners({W, H, D}, dir, hi, fov, aspect), fill) && hi < old * 64) { lo = hi; hi *= 2; }
    for (let i = 0; i < 48; i++) {
      const mid = (lo + hi) / 2;
      if (inside(projectCorners({W, H, D}, dir, mid, fov, aspect), fill)) hi = mid; else lo = mid;
    }
    dist = hi;
  }
  const u = unit(dir);
  return {
    position: u.map(v => v * dist),
    distance: dist,
    // room to dolly back out past the opening view, and a far plane behind the
    // whole box from there; never below what a 1U box has always had
    maxDistance: Math.max(BASE_MAX_DISTANCE, dist * 1.25),
    far: Math.max(BASE_FAR, (dist + Math.hypot(W, H, D) / 2) * 1.1),
  };
}
