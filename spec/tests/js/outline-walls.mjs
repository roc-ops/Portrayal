// A cavity that names its outline node is walled along that outline, not
// along the outline's bounding box (outlineWalls in kit/relief.js). An RJ45's
// box walls stood outside its stepped opening, so the face beside the latch
// slot had nothing behind it and the jack read as two stencils with air
// between them.
//
// The walls are a pure function of rings and a face-to-world map, so they are
// checked here without a browser: every triangle must face OUT of the cavity
// (as a BoxGeometry's do, which is what BackSide relies on), whichever way the
// outline was wound and whether or not the face is mirrored; an island's walls
// face into the island; and a finely sampled outline keeps its corners.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg id="FETCHED"/>' });

const { outlineWalls } = await import('../../../kit/relief.js');

// ringsOf samples a path at a fixed arc-length step; this does the same for a
// polygon, closing point included, so the walls see what the browser gives them
const sample = (poly, step) => {
  const pts = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i], b = poly[(i + 1) % poly.length];
    const n = Math.max(1, Math.ceil(Math.hypot(b[0] - a[0], b[1] - a[1]) / step));
    for (let k = 0; k < n; k++) pts.push([a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n]);
  }
  pts.push(poly[0].slice());
  return pts;
};

// the fraction of triangles whose normal points away from `centre` (in the
// mapped frame): 1 for walls facing out of a shell, 0 for walls facing into it
const outward = ({ pos, idx }, centre) => {
  let out = 0, n = 0;
  for (let t = 0; t < idx.length; t += 3) {
    const [a, b, c] = [idx[t], idx[t + 1], idx[t + 2]].map(i => pos.slice(3 * i, 3 * i + 3));
    const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    const nx = u[1] * v[2] - u[2] * v[1], ny = u[2] * v[0] - u[0] * v[2];
    if (Math.hypot(nx, ny) < 1e-12) continue;
    const mx = (a[0] + b[0] + c[0]) / 3 - centre[0], my = (a[1] + b[1] + c[1]) / 3 - centre[1];
    n++;
    if (nx * mx + ny * my > 0) out++;
  }
  return n ? out / n : null;
};

// std/rj45@2's opening (TE 1734264), in face mm: body, shoulder, latch slot
const RJ45 = [[1.945, 2.0], [13.855, 2.0], [13.855, 8.83], [11.05, 8.83], [11.05, 10.52],
              [9.93, 10.52], [9.93, 13.2], [5.87, 13.2], [5.87, 10.52], [4.75, 10.52],
              [4.75, 8.83], [1.945, 8.83]];
const CENTRE = [7.9, 6.0];
const face = (x, y) => [x - 7.9, 6.6 - y];            // LX/LY of a 15.8 x 13.2 face
const mirrored = (x, y) => [-(x - 7.9), 6.6 - y];     // the same face, flipLX
const ring = sample(RJ45, 0.05);

const plain = outlineWalls([{ shell: ring, holes: [] }], face, 0, -18.6);
const reversed = outlineWalls([{ shell: ring.slice().reverse(), holes: [] }], face, 0, -18.6);
const flipped = outlineWalls([{ shell: ring, holes: [] }], mirrored, 0, -18.6);

// a square pocket with a square island standing in it
const sq = (x0, y0, s) => sample([[x0, y0], [x0 + s, y0], [x0 + s, y0 + s], [x0, y0 + s]], 0.05);
const island = outlineWalls([{ shell: sq(0, 0, 10), holes: [sq(4, 4, 2)] }], (x, y) => [x, -y], 0, -5);
const shellOnly = { pos: island.pos, idx: island.idx.slice(0, 4 * 6) };
const holeOnly = { pos: island.pos, idx: island.idx.slice(4 * 6) };

const zs = new Set();
for (let i = 2; i < plain.pos.length; i += 3) zs.add(plain.pos[i]);

console.log(JSON.stringify({
  corners: plain.pos.length / 6,
  quads: plain.idx.length / 6,
  zs: [...zs].sort((a, b) => a - b),
  outward: outward(plain, face(...CENTRE)),
  reversedOutward: outward(reversed, face(...CENTRE)),
  mirroredOutward: outward(flipped, mirrored(...CENTRE)),
  islandQuads: island.idx.length / 6,
  shellOutward: outward(shellOnly, [5, -5]),
  holeOutward: outward(holeOnly, [5, -5]),
  empty: outlineWalls(null, face, 0, -1).idx.length,
}));
