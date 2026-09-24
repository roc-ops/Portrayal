globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
const m = await import('../../../kit/relief.js');
const {Node} = await import('./fake-dom.mjs');
const apply = (e, [x, y, z]) => [e[0]*x + e[4]*y + e[8]*z + e[12],
                                 e[1]*x + e[5]*y + e[9]*z + e[13],
                                 e[2]*x + e[6]*y + e[10]*z + e[14]];
const r = v => v.map(n => Math.round(n * 1000) / 1000);

// Test all four facings
const testFacing = (deg, facing, anchor, z0) => {
  const mat = m.tiltFrame({deg, facing, anchor, z0});

  // Extract columns (column-major order in a 4x4)
  const col0 = [mat[0], mat[1], mat[2]];
  const col1 = [mat[4], mat[5], mat[6]];
  const col2 = [mat[8], mat[9], mat[10]];

  // Orthonormality checks
  const dot = (a, b) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
  const mag = (v) => Math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]);

  // Apply to three points: anchor at z=0, axis step at z=0, and local z component
  const anchorPt = r(apply(mat, [anchor[0], anchor[1], 0]));
  const axisStep = r(apply(mat, [anchor[0] + (facing === 'up' || facing === 'down' ? 0 : 10),
                                  anchor[1] + (facing === 'up' || facing === 'down' ? 10 : 0),
                                  0]));
  const localZ = r(apply(mat, [anchor[0], anchor[1], 1]));

  return {
    anchorPt,
    axisStep,
    localZ,
    col0Mag: Math.round(mag(col0) * 1000) / 1000,
    col1Mag: Math.round(mag(col1) * 1000) / 1000,
    col2Mag: Math.round(mag(col2) * 1000) / 1000,
    dot01: Math.round(dot(col0, col1) * 1000) / 1000,
    dot02: Math.round(dot(col0, col2) * 1000) / 1000,
    dot12: Math.round(dot(col1, col2) * 1000) / 1000,
  };
};

const anchor = [10, 50];
const deg30 = 30, deg45 = 45;

const out = {
  up: testFacing(deg30, 'up', anchor, 2),
  down: testFacing(deg30, 'down', anchor, 0),
  left: testFacing(deg45, 'left', anchor, 0),
  right: testFacing(deg45, 'right', anchor, 0),
  unprojUp: m.unproject({x: 12, y: 50 + 8.660254, w: 5, h: 8.660254},
                        {deg: 30, facing: 'up', anchor}),
  facetZUp: Math.round(m.facetZ({x: 0, y: 40, w: 25, h: 30}, {deg: 30, facing: 'up'}, 0, [5, 70]) * 1000) / 1000,
  facetZDown: {
    atProudEdge: Math.round(m.facetZ({x: 0, y: 40, w: 25, h: 30}, {deg: 30, facing: 'down'}, 0, [5, 40]) * 1000) / 1000,
    atRootEdge: Math.round(m.facetZ({x: 0, y: 40, w: 25, h: 30}, {deg: 30, facing: 'down'}, 0, [5, 70]) * 1000) / 1000,
  },
  facetZLeft: Math.round(m.facetZ({x: 0, y: 40, w: 25, h: 30}, {deg: 45, facing: 'left'}, 0, [25, 50]) * 1000) / 1000,
  facetZRight: Math.round(m.facetZ({x: 0, y: 40, w: 25, h: 30}, {deg: 45, facing: 'right'}, 0, [0, 50]) * 1000) / 1000,
};
// tiltOf: the nearest [data-tilt-on] at or above a node; null off a facet
const lamp = new Node({id: 'lamp'});
const optic = new Node({'data-tilt-on': 'card--housing', 'data-tilt': '30', 'data-tilt-facing': 'up'},
                       [new Node({}, [lamp])]);
new Node({id: 'card'}, [new Node({'data-tilt-on': 'card--other', 'data-tilt': '45',
                                  'data-tilt-facing': 'left'}, [optic])]);
const loose = new Node({id: 'loose'});
new Node({id: 'plate'}, [loose]);
const t = m.tiltOf(lamp);
out.tiltOf = {deg: t.deg, facing: t.facing, on: t.on, hostIsOptic: t.host === optic};
out.tiltOfSelf = m.tiltOf(optic).on;
out.tiltOfNone = m.tiltOf(loose);
// faceFacing: a component turned rotate(90) (a=0 b=1 c=-1 d=0), and mirrored in x
const r90 = {a: 0, b: 1, c: -1, d: 0}, mx = {a: -1, b: 0, c: 0, d: 1};
out.faceFacing = {
  r90: ['up', 'down', 'left', 'right'].map(f => m.faceFacing(r90, f)),
  mirror: ['up', 'down', 'left', 'right'].map(f => m.faceFacing(mx, f)),
  identity: ['up', 'down', 'left', 'right'].map(f => m.faceFacing({a: 1, b: 0, c: 0, d: 1}, f)),
};

// tiltTools on the test DOM: a card (lift 5) with a facet (root lift 2), a cage
// on it, an optic nested in the card, and a mate-to optic drawn outside the card
// whose own lift is the host's whole chain (render.py `host-lift`)
globalThis.CSS = {escape: s => s};
const rects = new Map();
const R = (n, r) => { rects.set(n, r); return n; };
const facetNode = R(new Node({id: 'card--housing', 'data-facet-deg': '30', 'data-facet-facing': 'up',
                              'data-z-profile-y': '0:2,40:25.094'}), {x: 10, y: 20, w: 60, h: 40});
const cage = R(new Node({'data-path': 'card/cage', 'data-tilt-on': 'card--housing', 'data-tilt': '30',
                         'data-tilt-facing': 'up'}), {x: 20, y: 30, w: 20, h: 8.66});
const nested = R(new Node({'data-path': 'card/cage/optic', 'data-for': 'card/cage', 'data-z-lift': '1',
                           'data-tilt-on': 'card--housing', 'data-tilt': '30', 'data-tilt-facing': 'up'}),
                 {x: 21, y: 31, w: 18, h: 6.93});
const seat = R(new Node({'data-path': 'optic1', 'data-for': 'card/cage', 'data-z-lift': '6',
                         'data-tilt-on': 'card--housing', 'data-tilt': '30', 'data-tilt-facing': 'up'}),
               {x: 21, y: 31, w: 18, h: 6.93});
const cardG = new Node({id: 'card', 'data-z-lift': '5'}, [facetNode, cage, nested]);
const svgRoot = new Node({}, [cardG, seat], 'svg');
const liftOf = el => { let z = 0; for (let n = el; n && n !== svgRoot; n = n.parentNode) z += +(n.getAttribute('data-z-lift') || 0); return z; };
const tools = ctm => m.tiltTools(svgRoot, {mmRect: n => rects.get(n), liftOf, ctmOf: () => ctm});
const TT = tools({a: 1, b: 0, c: 0, d: 1});
const rr = r => r && JSON.parse(JSON.stringify(r, (k, v) => typeof v === 'number' ? Math.round(v * 1000) / 1000 : v));
out.tools = {
  facetLift: TT.facetInfo('card--housing').lift,
  cage: rr(TT.tiltRec(m.tiltOf(cage))),
  nested: rr(TT.tiltRec(m.tiltOf(nested))),
  seat: rr(TT.tiltRec(m.tiltOf(seat))),
  seatLiftFromFacet: liftOf(seat) - TT.tiltRec(m.tiltOf(seat)).base,
  nestedLiftFromFacet: liftOf(nested) - TT.tiltRec(m.tiltOf(nested)).base,
  r90Facing: tools({a: 0, b: 1, c: -1, d: 0}).tiltRec(m.tiltOf(cage)).tilt.facing,
  noFacet: (() => { const w = console.warn; console.warn = () => {};
                    const r = TT.tiltRec({deg: 30, facing: 'up', on: 'nope', host: cage});
                    console.warn = w; return r; })(),
};

// the facet footprint punch, and a rect punch in a module plane's pixels
out.facetPunch = m.facetPunch({x: 10, y: 20, w: 60, h: 40, facet: {id: 'card--housing'}});
out.punchPx = m.punchRectPx({x: 10, y: 20, w: 60, h: 40}, 5, 15, 4);

// tiltGroupIn, against a minimal THREE (column-major Matrix4, Group)
class M4 {
  constructor() { this.elements = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]; }
  set(...r) { const e = this.elements; for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) e[j * 4 + i] = r[i * 4 + j]; return this; }
  fromArray(a) { this.elements = [...a]; return this; }
  copy(o) { this.elements = [...o.elements]; return this; }
  clone() { return new M4().copy(this); }
  multiply(o) { const a = this.elements, b = o.elements, r = new Array(16).fill(0);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) for (let k = 0; k < 4; k++) r[j * 4 + i] += a[k * 4 + i] * b[j * 4 + k];
    this.elements = r; return this; }
  invert() { const n = 4, A = []; for (let i = 0; i < n; i++) { A.push([]); for (let j = 0; j < n; j++) A[i].push(this.elements[j * 4 + i]); for (let j = 0; j < n; j++) A[i].push(i === j ? 1 : 0); }
    for (let c = 0; c < n; c++) { let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(A[r][c]) > Math.abs(A[p][c])) p = r;
      [A[c], A[p]] = [A[p], A[c]]; const d = A[c][c]; for (let j = 0; j < 2 * n; j++) A[c][j] /= d;
      for (let r = 0; r < n; r++) if (r !== c) { const f = A[r][c]; for (let j = 0; j < 2 * n; j++) A[r][j] -= f * A[c][j]; } }
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) this.elements[j * 4 + i] = A[i][j + n]; return this; }
}
class G { constructor() { this.parent = null; this.children = []; this.userData = {}; this.matrix = new M4(); }
          add(c) { c.parent = this; this.children.push(c); return this; } }
m.configureRelief({THREE: {Matrix4: M4, Group: G}});
const face = {fw: 200, fh: 100};
const tA = {deg: 30, facing: 'up', on: 'card--housing', anchor: [20, 30], z0: 5.774};
const tB = {...tA, anchor: [21, 31], z0: 6.351};
const root = new G(), fruCard = new G(); root.add(fruCard);
const gA = m.tiltGroupIn(fruCard, tA, face);
const opticG = new G(); gA.add(opticG);
const gB = m.tiltGroupIn(opticG, tB, face);
// the face-group-local point a true-frame point lands at, through a group chain
const through = (gs, p) => gs.reduce((v, g) => { const e = g.matrix.elements;
  return [e[0]*v[0]+e[4]*v[1]+e[8]*v[2]+e[12], e[1]*v[0]+e[5]*v[1]+e[9]*v[2]+e[13], e[2]*v[0]+e[6]*v[1]+e[10]*v[2]+e[14]]; }, p);
const L = ([x, y]) => [x - face.fw / 2, face.fh / 2 - y, 0];     // LX/LY of a face-mm point
const alone = new G(); const gBalone = m.tiltGroupIn(alone, tB, face);
out.group = {
  memo: m.tiltGroupIn(fruCard, tA, face) === gA,
  sameKeyInside: m.tiltGroupIn(opticG, tA, face) === opticG,
  userData: gA.userData.tilt,
  autoOff: gA.matrixAutoUpdate === false,
  // B nested under A lands where B alone does (matrices apply innermost first)
  nestedB: rr(through([gB, gA], L([25, 35]))),
  aloneB: rr(through([gBalone], L([25, 35]))),
};
console.log(JSON.stringify(out));
