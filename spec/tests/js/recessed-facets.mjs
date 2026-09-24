// Recessed facets (docs/superpowers/specs/2026-09-24-tilted-facets-design.md,
// the addendum): a facet whose lift is negative stands in a pocket. Checked
// here: the pocket floor is cleared under it, facetZ and facetInfo read the
// sunk surface, and a sunk tooth's skirt ends at its own base.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
globalThis.CSS = {escape: s => s};
const m = await import('../../../kit/relief.js');
const {Node} = await import('./fake-dom.mjs');
const r3 = v => Math.round(v * 1000) / 1000;
const out = {};

// A 25 x 120 pocket 12 deep at y=60 on a plain face, a sunk up-facet 25 x 14
// at y=62 and its down return 25 x 8 at y=76, both rooted at -12 (the
// addendum's example). A proud facet elsewhere, and one sunk facet that runs
// out of the pocket.
const pocket = {x: 0, y: 60, w: 25, h: 120, lift: 0, d: 12};
const F = (x, y, w, h, lift, id, extra = {}) => ({x, y, w, h, lift, owner: 'dev',
  facet: {deg: 30, facing: 'up', id}, ...extra});
const face1 = F(0, 62, 25, 14, -12, 'c--face-1');
const ret1 = F(0, 76, 25, 8, -12, 'c--return-1');
const proud = F(0, 10, 25, 14, 0, 'c--proud');
const proudInPocket = F(0, 100, 25, 14, 0, 'c--proud-in-pocket');
const outside = F(0, 170, 25, 20, -12, 'c--spill');       // runs 10 past the pocket's end
const plain = {x: 0, y: 120, w: 25, h: 10, lift: -12, out: 3, owner: 'dev'};   // not a facet
const outs = [face1, ret1, proud, proudInPocket, outside, plain];

const clears = m.facetFloorClears(pocket, outs);
out.clears = clears.map(p => ({...p, x: r3(p.x), y: r3(p.y), w: r3(p.w), h: r3(p.h)}));
// a pocket that is itself lifted 10 (a composed part at lift 10): a facet at
// absolute -2 is below its mouth, one at absolute 10 is not
out.liftedPocket = m.facetFloorClears({...pocket, lift: 10},
  [F(0, 62, 25, 14, -2, 'a'), F(0, 80, 25, 14, 10, 'b')]).map(p => p.facet);
out.noFacets = m.facetFloorClears(pocket, [plain]).length;

// THE RASTER: the floor canvas of the pocket, 4 px/mm, cleared at each
// footprint in the floor's own pixels
{
  const calls = [];
  const cvs = {getContext: () => ({clearRect: (...a) => calls.push(a)})};
  const same = m.clearFloor(cvs, clears, pocket.x, pocket.y, 4);
  out.raster = {calls, returnsCanvas: same === cvs};
  const none = [];
  m.clearFloor({getContext: () => ({clearRect: (...a) => none.push(a)})}, [], 0, 0, 4);
  out.raster.noneCalls = none.length;
}

// facetZ with a negative lift: the sunk surface height
const tn = Math.tan(Math.PI / 6);
out.facetZ = {
  root: r3(m.facetZ({x: 0, y: 62, w: 25, h: 14}, {deg: 30, facing: 'up'}, -12, [5, 62])),
  mid: r3(m.facetZ({x: 0, y: 62, w: 25, h: 14}, {deg: 30, facing: 'up'}, -12, [5, 69])),
  proud: r3(m.facetZ({x: 0, y: 62, w: 25, h: 14}, {deg: 30, facing: 'up'}, -12, [5, 76])),
  expectProud: r3(-12 + 14 * tn),
};

// facetInfo: the root lift is the profile's minimum, below 0 too, and a part
// on the facet stands at the sunk surface
{
  const rects = new Map();
  const R = (n, r) => { rects.set(n, r); return n; };
  const fn = R(new Node({id: 'c--face-1', 'data-facet-deg': '30', 'data-facet-facing': 'up',
                         'data-z-lift': '-12', 'data-z-profile-y': `0:-12,14:${r3(-12 + 14 * tn)}`}),
               {x: 0, y: 62, w: 25, h: 14});
  const cage = R(new Node({'data-path': 'c/p1', 'data-tilt-on': 'c--face-1', 'data-tilt': '30',
                           'data-tilt-facing': 'up'}), {x: 3, y: 64, w: 19, h: 8});
  const sv = new Node({}, [new Node({id: 'c', 'data-path': 'c'}, [fn, cage])], 'svg');
  const lf = el => { let z = 0; for (let n = el; n && n !== sv; n = n.parentNode) z += +(n.getAttribute('data-z-lift') || 0); return z; };
  const T = m.tiltTools(sv, {mmRect: n => rects.get(n), liftOf: lf, ctmOf: () => ({a: 1, b: 0, c: 0, d: 1})});
  const rec = T.tiltRec(m.tiltOf(cage));
  out.facetInfo = {lift: T.facetInfo('c--face-1').lift, z0: r3(rec.tilt.z0), expectZ0: r3(-12 + 2 * tn),
                   base: rec.base};
}

// SKIRTS: a sunk tooth's skirt ends at its base, -12, not at the plate; its
// side walls, which border open pocket, are built; the apex against its
// return is still inside the tooth.
{
  const hF = 14.25;
  const fc = F(0, 0, 25, hF, -12, 'f', {profileY: [[0, -12], [hF, -12 + hF]], out: -12 + hF});
  const rt = F(0, hF, 25, hF, -12, 'r', {profileY: [[0, -12 + hF], [hF, -12]], out: -12 + hF,
                                          facet: {deg: 45, facing: 'down', id: 'r'}});
  const depth = o => (x, y) => m.outHeightAt([o], o.x + x, o.y + y, 0.01, -Infinity);
  const xs = [0, 5, 10, 15, 20, 25], ys = [0, 5, 10, hF];
  const sk = m.profileSkirt(fc, xs, ys, depth(fc), m.skirtNeighbours(fc, [fc, rt]));
  const bases = sk.pts.filter((_, i) => i % 2 === 1).map(p => p[2]);
  const tops = sk.pts.filter((_, i) => i % 2 === 0).map(p => r3(p[2]));
  // quads by which edge of the box they lie on
  const n = sk.ring.length, edges = {top: 0, right: 0, bottom: 0, left: 0};
  for (let q = 0; q < sk.idx.length; q += 6) {
    const k = sk.idx[q] / 2, [p, s] = [sk.ring[k], sk.ring[(k + 1) % n]];
    if (p[1] === 0 && s[1] === 0) edges.top++;
    else if (p[0] === 25 && s[0] === 25) edges.right++;
    else if (p[1] === hF && s[1] === hF) edges.bottom++;
    else if (p[0] === 0 && s[0] === 0) edges.left++;
  }
  out.skirt = {allAtBase: bases.every(z => z === -12), minTop: Math.min(...tops), maxTop: Math.max(...tops),
               edges, ringLen: n};
  // the same tooth proud (lift 0): exactly the quads it built before this
  // change - the root edge's zero-height skirt skipped, the apex skipped,
  // both sides built
  const pf = {...fc, lift: 0, profileY: [[0, 0], [hF, hF]], out: hF};
  const pr = {...rt, lift: 0, profileY: [[0, hF], [hF, 0]], out: hF};
  const skP = m.profileSkirt(pf, xs, ys, (x, y) => m.outHeightAt([pf], x, y),
                             m.skirtNeighbours(pf, [pf, pr]));
  const eP = {top: 0, right: 0, bottom: 0, left: 0};
  for (let q = 0; q < skP.idx.length; q += 6) {
    const k = skP.idx[q] / 2, [p, s] = [skP.ring[k], skP.ring[(k + 1) % n]];
    if (p[1] === 0 && s[1] === 0) eP.top++;
    else if (p[0] === 25 && s[0] === 25) eP.right++;
    else if (p[1] === hF && s[1] === hF) eP.bottom++;
    else if (p[0] === 0 && s[0] === 0) eP.left++;
  }
  out.skirtProud = {edges: eP, allAtBase: skP.pts.filter((_, i) => i % 2 === 1).every(p => p[2] === 0)};
  // outHeightAt's default is still 0 where nothing stands
  out.outHeightDefault = m.outHeightAt([fc], 100, 100);
  out.outHeightNone = m.outHeightAt([fc], 100, 100, 0.01, -12);
}

console.log(JSON.stringify(out));
