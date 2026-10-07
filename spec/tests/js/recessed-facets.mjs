// Recessed facets (docs/tilted-facets-design.md,
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
const pocket = {x: 0, y: 60, w: 25, h: 120, lift: 0, d: 12, owner: 'dev'};
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


// SKIRTS. A sunk tooth's skirt ends at its base, -12, not at the plate. Where
// no neighbour stands, what is beside the tooth depends on where: open pocket
// (its floor) inside the pocket's box, the solid plate outside it. The apex
// against the tooth's return is inside the tooth either way.
// A skirt segment is counted by the ring edge it lies on (`segs`).
const hF = 14.25;
const edgesOf = (sk, w, h) => {
  const n = sk.ring.length, e = {top: 0, right: 0, bottom: 0, left: 0};
  for (const {k} of sk.segs) {
    const [p, s] = [sk.ring[k], sk.ring[(k + 1) % n]];
    if (p[1] === 0 && s[1] === 0) e.top++;
    else if (p[0] === w && s[0] === w) e.right++;
    else if (p[1] === h && s[1] === h) e.bottom++;
    else if (p[0] === 0 && s[0] === 0) e.left++;
  }
  return e;
};
const TF = (extra = {}) => F(0, 0, 25, hF, -12, 'f', {facet: {deg: 45, facing: 'up', id: 'f'},
  profileY: [[0, -12], [hF, -12 + hF]], out: -12 + hF, ...extra});
const TR = (extra = {}) => F(0, hF, 25, hF, -12, 'r', {facet: {deg: 45, facing: 'down', id: 'r'},
  profileY: [[0, -12 + hF], [hF, -12]], out: -12 + hF, ...extra});
const depth = o => (x, y) => m.outHeightAt([o], o.x + x, o.y + y, 0.01, -Infinity);
const xs = [0, 5, 10, 15, 20, 25], ys = [0, 5, 10, hF];
const skirtCase = (fc, rt) => {
  const sk = m.profileSkirt(fc, xs, ys, depth(fc), m.skirtNeighbours(fc, [fc, rt]));
  return {sk, edges: edgesOf(sk, 25, hF),
          zmin: r3(Math.min(...sk.pts.map(p => p[2]))), zmax: r3(Math.max(...sk.pts.map(p => p[2])))};
};
{
  // narrower than its pocket: the pocket runs 5 past each side, so both sides
  // border open pocket and are built in full, down to the base
  const narrow = {x: -5, y: -2, w: 35, h: 40, floor: -12, mouth: 0};
  const n = skirtCase(TF({pocket: narrow}), TR({pocket: narrow}));
  out.skirtNarrow = {edges: n.edges, zmin: n.zmin, zmax: n.zmax,
                     basesAtLift: n.sk.segs.every(s => s.base === -12)};
  // as wide as its pocket (the addendum's window-1): beside each side is the
  // solid plate, down to the pocket's mouth. No skirt below the mouth - that
  // is the pocket wall's plane - and none at all where the tooth is below it.
  const span = {x: 0, y: -2, w: 25, h: 40, floor: -12, mouth: 0};
  const s = skirtCase(TF({pocket: span}), TR({pocket: span}));
  const sides = s.sk.segs.filter(g => { const [p, q] = [s.sk.ring[g.k], s.sk.ring[(g.k + 1) % s.sk.ring.length]];
                                        return p[0] === q[0] && (p[0] === 0 || p[0] === 25); });
  const sideZ = [];
  for (const g of sides) sideZ.push(g.base);
  out.skirtSpan = {edges: s.edges, sideBases: sideZ,
                   sideVertsAboveMouth: sides.length > 0 && s.sk.pts
                     .filter(p => p[0] === 0 || p[0] === 25).every(p => p[2] >= -1e-9)};
  // a sunk tooth with no pocket known reads the plate beside it
  const none = skirtCase(TF(), TR());
  out.skirtNoPocket = none.edges;
}
// the same tooth proud (lift 0): exactly the quads, and the vertex layout, it
// built before recessed facets - root edge's zero-height skirt skipped, apex
// skipped, both sides built, every ring point paired top/base
{
  const pf = TF({lift: 0, profileY: [[0, 0], [hF, hF]], out: hF});
  const pr = TR({lift: 0, profileY: [[0, hF], [hF, 0]], out: hF});
  const sk = m.profileSkirt(pf, xs, ys, (x, y) => m.outHeightAt([pf], x, y), m.skirtNeighbours(pf, [pf, pr]));
  const oldIdx = [];
  for (const {k} of sk.segs) {
    const a = 2 * k, b = a + 1, c = 2 * ((k + 1) % sk.ring.length), d = c + 1;
    oldIdx.push(a, b, c, b, d, c);
  }
  out.skirtProud = {edges: edgesOf(sk, 25, hF), paired: sk.pts.length === 2 * sk.ring.length,
                    idxAsBefore: JSON.stringify(oldIdx) === JSON.stringify(sk.idx),
                    allAtBase: sk.pts.filter((_, i) => i % 2 === 1).every(p => p[2] === 0)};
}
out.outHeightDefault = m.outHeightAt([TF()], 100, 100);
out.outHeightNone = m.outHeightAt([TF()], 100, 100, 0.01, -12);

// WELLS CROSS THE FLOOR WHERE THE SLOPE TAKES THEM, which for the apex-side
// wall is past the face's own footprint. An SFP (13.5 x 8.5 well, 41 deep) at
// rotate 90 on a 30-degree up face 14 tall, the aperture 0.72 below the root.
const c30 = Math.cos(Math.PI / 6);
const wellOn = (face, dx = 0) => {
  const anchor = [face.x + (face.w - 10) / 2 + dx, face.y + 0.72];
  const z0 = m.facetZ(face, {deg: 30, facing: 'up'}, face.lift, anchor);
  return {x: anchor[0] + 0.75, y: anchor[1] + 0.5, w: 8.5, h: 13.5, lift: 0, d: 41, owner: face.owner,
          tilt: {deg: 30, facing: 'up', on: face.facet.id, anchor, z0}};
};
// where each long edge of the well meets the plane z (face mm), independently
// of the clear: the edge p(t) = corner + t * inward normal
const crossings = (w, z) => {
  const M = m.tiltFrame(w.tilt);
  const ap = ([x, y, zz]) => [M[0] * x + M[4] * y + M[8] * zz + M[12],
                              M[1] * x + M[5] * y + M[9] * zz + M[13],
                              M[2] * x + M[6] * y + M[10] * zz + M[14]];
  const pts = [];
  for (const x of [w.x, w.x + w.w]) for (const y of [w.y, w.y + w.h]) {
    const a = ap([x, y, w.lift]), b = ap([x, y, w.lift - w.d]);
    if ((a[2] - z) * (b[2] - z) > 0) continue;
    const t = (z - a[2]) / (b[2] - a[2]);
    pts.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]);
  }
  return pts;
};
const covered = (pt, clears) => clears.some(c => pt[0] >= c.x - 1e-6 && pt[0] <= c.x + c.w + 1e-6
                                              && pt[1] >= c.y - 1e-6 && pt[1] <= c.y + c.h + 1e-6);
const wellCase = (pocketBox, facets, wells) => {
  const floorZ = pocketBox.lift - pocketBox.d + 0.1, backZ = pocketBox.lift - pocketBox.d - 0.15;
  const all = m.facetFloorClears(pocketBox, facets, {cavities: wells, floorZ, backZ});
  const feet = m.facetFloorClears(pocketBox, facets, {floorZ, backZ});
  const xs = wells.flatMap(w => [...crossings(w, floorZ), ...crossings(w, backZ)]);
  return {n: xs.length, covered: xs.every(p => covered(p, all)),
          byFootprintsAlone: xs.every(p => covered(p, feet)),
          inPocket: all.every(c => c.x >= pocketBox.x - 1e-9 && c.y >= pocketBox.y - 1e-9
                              && c.x + c.w <= pocketBox.x + pocketBox.w + 1e-9
                              && c.y + c.h <= pocketBox.y + pocketBox.h + 1e-9),
          wellClears: all.filter(c => c.well).length};
};
{
  // a pocket DEEPER than the lift (30 for -12), one tooth, and window margin
  // below it: the far wall meets the floor ~27 mm down-card from the root
  const deep = {x: 0, y: 60, w: 25, h: 60, lift: 0, d: 30, owner: 'dev'};
  const f = F(0, 62, 25, 14, -12, 'd--face'), r = F(0, 76, 25, 8.083, -12, 'd--ret');
  out.wellDeep = wellCase(deep, [f, r], [wellOn(f)]);
  // a single sunk face with no return (a housing whose face starts in a pocket)
  const p12 = {x: 0, y: 60, w: 25, h: 40, lift: 0, d: 12, owner: 'dev'};
  const lone = F(0, 62, 25, 14, -12, 'l--face');
  out.wellLone = wellCase(p12, [lone], [wellOn(lone)]);
  // teeth narrower than the window, with gaps between them
  const wide = {x: 0, y: 60, w: 40, h: 80, lift: 0, d: 12, owner: 'dev'};
  const n1 = F(5, 62, 25, 14, -12, 'n--f1'), n2 = F(5, 90, 25, 14, -12, 'n--f2');
  out.wellNarrow = wellCase(wide, [n1, n2], [wellOn(n1), wellOn(n2)]);
  // a well on a facet this pocket does not hold clears nothing here
  out.wellElsewhere = m.facetFloorClears(p12, [lone], {cavities: [wellOn(F(0, 150, 25, 14, -12, 'x'))],
                                                        floorZ: -11.9, backZ: -12.15})
    .filter(c => c.well).length;
  // a proud facet's well, in a pocket, clears nothing: no negative lift, no-op
  const pf = F(0, 62, 25, 14, 0, 'p--face');
  out.wellProud = m.facetFloorClears(p12, [pf], {cavities: [wellOn(pf)], floorZ: -11.9, backZ: -12.15}).length;
}

// M3: A POCKET CLEARS ONLY UNDER ITS OWN PART'S FACETS. A device well holding
// a whole card is not cleared under that card's teeth; the card's own pocket
// is, and so is a pocket whose owner the facet's owner lies under.
{
  const well = {x: 0, y: 0, w: 25, h: 200, lift: 0, d: 40, owner: null};
  const cardPocket = {x: 0, y: 60, w: 25, h: 40, lift: 0, d: 12, owner: 'card'};
  const tooth = F(0, 62, 25, 14, -12, 'card--face', {owner: 'card'});
  const sub = F(0, 62, 25, 14, -12, 'card--sub--face', {owner: 'card/sub'});
  out.owner = {deviceWell: m.facetFloorClears(well, [tooth]).length,
               ownPocket: m.facetFloorClears(cardPocket, [tooth]).length,
               nested: m.facetFloorClears(cardPocket, [sub]).length,
               otherCard: m.facetFloorClears(cardPocket, [F(0, 62, 25, 14, -12, 'x', {owner: 'card2'})]).length};
}

// M4: THE FLOOR RASTER IS NOT FLIPPED, so on a flipped face a clear is
// mirrored within the cavity to land under the tooth
{
  const pc = {x: 10, y: 60, w: 40, h: 80};
  const cl = [{kind: 'rect', x: 15, y: 62, w: 10, h: 14, facet: 'a'}];
  out.mirror = {none: m.mirrorClears(cl, pc, false, false),
                x: m.mirrorClears(cl, pc, true, false),
                y: m.mirrorClears(cl, pc, false, true),
                both: m.mirrorClears(cl, pc, true, true)};
}

console.log(JSON.stringify(out));
