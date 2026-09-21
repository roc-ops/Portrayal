// A depth that varies across a node, built inside the node's own OUTLINE.
//
// `profile` and `profile-y` built their height field over the node's bounding
// box, so a sloped moulding could only ever be a rectangle. The MaiaEdge
// PBC-2000's centre pane stands 15 proud between two octagonal windows and its
// ends ARE the windows' ends - chamfer, vertical, chamfer - so the rectangle
// either ran into the windows or stopped short of the chamfer corners.
//
// The geometry is a pure function of an outline, a grid and a depth, so it is
// checked here under node rather than in a browser, the way cavity-seats-on is.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg id="FETCHED"/>' });

const m = await import('../../../kit/relief.js');
const build = m.shapedHeightField;

const area2 = (P, I) => {
  let a = 0;
  for (let k = 0; k < I.length; k += 3) {
    const [p, q, r] = [I[k], I[k + 1], I[k + 2]].map(i => [P[3 * i], P[3 * i + 1]]);
    a += Math.abs((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1])) / 2;
  }
  return a;
};
const polyArea = r => {
  let a = 0;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++)
    a += (r[j][0] + r[i][0]) * (r[j][1] - r[i][1]);
  return Math.abs(a / 2);
};
const densify = (r, step) => {
  const out = [];
  for (let i = 0; i < r.length; i++) {
    const [a, b] = [r[i], r[(i + 1) % r.length]];
    const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / step));
    for (let k = 0; k < n; k++) out.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n]);
  }
  return out;
};

// the pane's shape: a bar whose two ends are notched by octagon ends - concave
// on both sides, which is what a convex-only builder gets wrong
const pane = [[0, 0], [100, 0], [100, 6], [92, 14], [92, 26], [100, 34], [100, 40],
              [0, 40], [0, 34], [8, 26], [8, 14], [0, 6]];
const ring = densify(pane, 0.25);
const flat = 15;
const px = [[0, flat], [100, flat]];
const py = [[0, 0], [7, flat], [33, flat], [40, 0]];
const interp = (pts, t) => {
  if (t <= pts[0][0]) return pts[0][1];
  for (let i = 0; i + 1 < pts.length; i++) {
    const [t0, v0] = pts[i], [t1, v1] = pts[i + 1];
    if (t <= t1) return v0 + (v1 - v0) * (t - t0) / (t1 - t0);
  }
  return pts[pts.length - 1][1];
};
const depthAt = (x, y) => Math.min(interp(px, x), interp(py, y));
const xs = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100];
const ys = [0, 5, 7, 10, 15, 20, 25, 30, 33, 35, 40];

const g = build([{shell: ring, holes: []}], xs, ys, depthAt, 0);
const P = g.top.pos, I = g.top.idx;

let worstZ = 0, outside = 0;
const inPoly = (pt, r) => {
  let hit = false;
  for (let i = 0, j = r.length - 1; i < r.length; j = i++) {
    const a = r[i], b = r[j];
    if ((a[1] > pt[1]) !== (b[1] > pt[1]) &&
        pt[0] < (b[0] - a[0]) * (pt[1] - a[1]) / (b[1] - a[1]) + a[0]) hit = !hit;
  }
  return hit;
};
for (let k = 0; k < I.length; k += 3) {
  const c = [0, 1].map(d => (P[3 * I[k] + d] + P[3 * I[k + 1] + d] + P[3 * I[k + 2] + d]) / 3);
  if (!inPoly(c, pane)) outside++;
}
for (let i = 0; i < P.length; i += 3)
  worstZ = Math.max(worstZ, Math.abs(P[i + 2] - depthAt(P[i], P[i + 1])));

// the skirt: one wall along the outline, from the surface down to the lift
const S = g.skirt.pos;
let skirtOff = 0;
for (let i = 0; i < S.length; i += 6) {
  skirtOff = Math.max(skirtOff, Math.abs(S[i + 2] - depthAt(S[i], S[i + 1])), Math.abs(S[i + 5] - 0));
}

// a rectangle with no notches must come out the same area as the box builder
const box = densify([[0, 0], [100, 0], [100, 40], [0, 40]], 0.25);
const gb = build([{shell: box, holes: []}], xs, ys, depthAt, 0);

// A BEZEL WITH WINDOWS CUT THROUGH IT - the PBC-2000 as it really is: one
// sloped plate across the face, the octagons holes in it. Holes are bridged
// into the shell before clipping; their walls come back separately so they can
// take their own colour (the amber bead).
const oct = (x, y, w, h) => { const c = Math.min(w, h) * 0.35;
  return [[x + c, y], [x + w - c, y], [x + w, y + c], [x + w, y + h - c],
          [x + w - c, y + h], [x + c, y + h], [x, y + h - c], [x, y + c]]; };
const bez = [[0, 0], [374, 0], [374, 41.27], [0, 41.27]];
const hA = oct(8, 6, 132, 29), hB = oct(232, 6, 132, 29);
const bpy = [[0, 0], [16.15, 11.25], [24.85, 11.25], [41.27, 0]];
const bdepth = (x, y) => interp(bpy, y);
const bxs = [], bys = [0, 5, 10, 15, 16.15, 20, 24.85, 25, 30, 35, 40, 41.27];
for (let x = 0; x < 374; x += 5) bxs.push(x); bxs.push(374);
const gh = build([{shell: densify(bez, 0.25), holes: [densify(hA, 0.25), densify(hB, 0.25)]}],
                 bxs, bys, bdepth, 0);
let inHole = 0, outOfShell = 0, worstHZ = 0;
for (let k = 0; k < gh.top.idx.length; k += 3) {
  const P2 = gh.top.pos, I2 = gh.top.idx;
  const c = [0, 1].map(d => (P2[3 * I2[k] + d] + P2[3 * I2[k + 1] + d] + P2[3 * I2[k + 2] + d]) / 3);
  if (inPoly(c, hA) || inPoly(c, hB)) inHole++;
  if (!inPoly(c, bez)) outOfShell++;
}
for (let i = 0; i < gh.top.pos.length; i += 3)
  worstHZ = Math.max(worstHZ, Math.abs(gh.top.pos[i + 2] - bdepth(gh.top.pos[i], gh.top.pos[i + 1])));

// a "hole" with nothing of the shell above it cannot be bridged, so it is not
// cut - and must not grow a wall standing on an uncut surface either
const stray = densify([[20, -10], [30, -10], [30, -2], [20, -2]], 0.25);
const gs = build([{shell: densify(bez, 0.25), holes: [stray]}], bxs, bys, bdepth, 0);

console.log(JSON.stringify({
  strayHoleWall: gs.holeSkirt.pos.length,
  strayArea: area2(gs.top.pos, gs.top.idx),
  bezelArea: area2(gh.top.pos, gh.top.idx),
  bezelWant: polyArea(bez) - polyArea(hA) - polyArea(hB),
  inHole, outOfShell, worstHZ,
  shellSkirtPairs: gh.skirt.pos.length / 6,
  holeSkirtPairs: gh.holeSkirt.pos.length / 6,
  holeRingPoints: densify(hA, 0.25).length + densify(hB, 0.25).length,
  shellRingPoints: densify(bez, 0.25).length,
  topArea: area2(P, I),
  paneArea: polyArea(pane),
  trianglesOutside: outside,
  worstZ,
  skirtPairs: S.length / 6,
  ringLength: ring.length,
  skirtOff,
  boxArea: area2(gb.top.pos, gb.top.idx),
  midDepth: depthAt(50, 20),
}));
