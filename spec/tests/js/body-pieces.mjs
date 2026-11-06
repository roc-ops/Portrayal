// What a body piece is built from, under node: the solid a round piece makes,
// the material a shown drawing paints, and when a piece falls back to a box.
//
// THREE is not a dependency of the tests (the kit takes it from the page), so
// this file hands the kit a small stand-in that records what it is asked for.
// That is enough for what is checked here - which constructor, with which
// options, and the scale and turn set on a mesh - and the extents it reports
// are worked out from those, not measured on a real geometry.
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });

const CLAMP = 1001, REPEAT = 1000;
class Pair { constructor() { this.x = 0; this.y = 0; } set(x, y) { this.x = x; this.y = y; return this; } }
class Triple { constructor() { this.x = 1; this.y = 1; this.z = 1; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; } }
class Texture {
  constructor(image) {
    this.image = image; this.wrapS = CLAMP; this.wrapT = CLAMP;
    this.repeat = new Pair().set(1, 1); this.offset = new Pair();
  }
  clone() {
    const t = new Texture(this.image);
    t.wrapS = this.wrapS; t.wrapT = this.wrapT;
    t.repeat.set(this.repeat.x, this.repeat.y); t.offset.set(this.offset.x, this.offset.y);
    t.cloned = true;
    return t;
  }
}
const mat = kind => class { constructor(o = {}) { this.kind = kind; Object.assign(this, o); } };
const geo = kind => class { constructor(...a) { this.kind = kind; this.args = a; }
  translate() { return this; } rotateX() { return this; } };
class Mesh {
  constructor(geometry, material) {
    this.geometry = geometry; this.material = material;
    this.rotation = {x: 0, y: 0, z: 0}; this.scale = new Triple();
  }
}
const THREE_STANDIN = {
  RepeatWrapping: REPEAT, ClampToEdgeWrapping: CLAMP,
  SRGBColorSpace: 'srgb', LinearFilter: 1006, LinearMipmapLinearFilter: 1008,
  CanvasTexture: class extends Texture { constructor(cv) { super(cv); this.canvas = cv; } },
  MeshBasicMaterial: mat('basic'), MeshLambertMaterial: mat('lambert'),
  BoxGeometry: geo('box'), CylinderGeometry: geo('cylinder'), ExtrudeGeometry: geo('extrude'),
  Shape: class { constructor() { this.holes = []; } absarc() { return this; } },
  Path: class { absarc() { return this; } },
  Mesh,
};

// a page that can rasterise: an Image that loads (or does not, on demand) and
// a canvas that holds a size
let loads = 0;
globalThis.failImages = false;
globalThis.Image = class {
  set src(_) {
    loads++;
    queueMicrotask(() => (globalThis.failImages ? this.onerror(new Error('no image')) : this.onload()));
  }
};
globalThis.document = {createElement: () => ({
  width: 0, height: 0,
  getContext: () => ({drawImage() {}, translate() {}, scale() {}, setTransform() {}})})};

const m = await import('../../../kit/relief.js');
const scope = m.createReliefScope({PXMM: 4});
m.configureRelief({THREE: THREE_STANDIN, renderer: {capabilities: {getMaxAnisotropy: () => 1}},
                   PXMM: 4, FRU_PATHS: {}}, scope);

// the world extents of a piece mesh, from its geometry's own size, scale and turn
const extents = mesh => {
  const g = mesh.geometry;
  let e = g.kind === 'box' ? [...g.args] : [1, 1, 1];
  e = [e[0] * mesh.scale.x, e[1] * mesh.scale.y, e[2] * mesh.scale.z];
  if (Math.abs(mesh.rotation.x - Math.PI / 2) < 1e-9) e = [e[0], e[2], e[1]];
  if (Math.abs(mesh.rotation.z - Math.PI / 2) < 1e-9) e = [e[1], e[0], e[2]];
  return e.map(v => +v.toFixed(6));
};

// THE SOLIDS: a cylinder and a ring on each axis, in one envelope; w x h x d
const round = (shape, axis) => {
  const b = {shape, axis, wall: 2, color: '#888'};
  const mesh = m.pieceMesh(b, 10, 20, 30);
  return {kind: mesh.geometry.kind, extents: extents(mesh), material: mesh.material.kind,
          single: !Array.isArray(mesh.material)};
};
const solids = {};
for (const shape of ['cylinder', 'ring']) for (const axis of ['x', 'y', 'z'])
  solids[`${shape}-${axis}`] = round(shape, axis);
const plainBox = m.pieceMesh({color: '#123456'}, 10, 20, 30);
const boxes = {kind: plainBox.geometry.kind, extents: extents(plainBox),
               color: plainBox.material.color, single: !Array.isArray(plainBox.material)};

// A PAINTED BOX: the plan on top, the rear behind, the rest the piece's colour
const painted = (art) => {
  const mesh = m.pieceMesh({color: '#123456', shows: Object.keys(art)}, 10, 20, 30, art);
  return mesh.material.map(x => x.kind === 'basic' ? 'art' : x.color);
};
const art = {plan: new THREE_STANDIN.MeshBasicMaterial({}), rear: new THREE_STANDIN.MeshBasicMaterial({})};
const faces = painted(art);

// THE ART A PIECE SHOWS. A part with a plan 200 x 100 and a rear 100 x 20, the
// face 100 wide; a piece with a plan crop inside the drawing and one that
// touches its edge; a drawing that will not load
const body = {drawings: {plan: {file: 'plan.svg', w: 200, h: 100},
                         rear: {file: 'rear.svg', w: 100, h: 20}},
              face: [100, 20], depth: 100};
const dist = f => `dist/${f}`;
for (const f of ['plan.svg', 'rear.svg'])
  m.setSvgOverride(`dist/${f}`, `<svg xmlns="http://www.w3.org/2000/svg" id="${f}"/>`, scope);
const inside = {x: 10, y: 2, w: 30, h: 10, z0: 20, z1: 60, color: '#123456', shows: ['plan', 'rear']};
const atEdge = {x: 0, y: 0, w: 100, h: 20, z0: 0, z1: 100, color: '#123456', shows: ['plan', 'rear']};
const cache = new Map();
const a1 = await m.pieceArt(body, inside, dist, scope, cache);
const a2 = await m.pieceArt(body, atEdge, dist, scope, cache);
const summary = (a) => Object.fromEntries(Object.entries(a).map(([k, v]) => [k, {
  kind: v.kind, transparent: v.transparent, alphaTest: v.alphaTest,
  wrapS: v.map.wrapS, wrapT: v.map.wrapT, cloned: !!v.map.cloned,
  repeat: [v.map.repeat.x, v.map.repeat.y], offset: [v.map.offset.x, v.map.offset.y]}]));
// the drawing is one texture per build, and each piece carries a clone of it
const sharedCanvas = a1.plan.map.image === a2.plan.map.image;
const loadsBefore = loads;
await m.pieceArt(body, inside, dist, scope, cache);
const reloaded = loads - loadsBefore;

// A DRAWING THAT WILL NOT LOAD costs the art, says so once, and leaves the piece plain
const warnings = [];
const warn = console.warn;
console.warn = (...a) => warnings.push(String(a[0]));
globalThis.failImages = true;
const failCache = new Map();
// (a size of its own, so no kept raster of the drawings above answers for it)
m.setSvgOverride('dist/plan-fail.svg', '<svg xmlns="http://www.w3.org/2000/svg" id="fail"/>', scope);
const failing = {drawings: {plan: {file: 'plan-fail.svg', w: 123, h: 77}}, face: [100, 20], depth: 100};
const sib = {x: 0, y: 0, w: 5, h: 5, z0: 0, z1: 5, color: '#123456', shows: ['plan']};
const failed = [];
for (let i = 0; i < 3; i++) failed.push(Object.keys(await m.pieceArt(failing, sib, dist, scope, failCache)));
const warned = warnings.length;
globalThis.failImages = false;
console.warn = warn;

// WHEN A PIECE FALLS BACK TO A BOX: a turned, mirrored or tilted host - and a
// face drawn flipped, which the host's own transform does not say
const ident = {a: 1, b: 0, c: 0, d: 1, e: 5, f: 5};
const flips = {
  none: m.pieceIsStraight(ident, null),
  noneExplicit: m.pieceIsStraight(ident, null, [false, false]),
  flipLX: m.pieceIsStraight(ident, null, [true, false]),
  flipLY: m.pieceIsStraight(ident, null, [false, true]),
  both: m.pieceIsStraight(ident, null, [true, true]),
  noHostFlipped: m.pieceIsStraight(null, null, [true, false]),
  bayMirror: m.pieceIsStraight({a: -1, b: 0, c: 0, d: 1, e: 0, f: 0}, null, [false, false]),
};

console.log(JSON.stringify({solids, boxes, faces, a1: summary(a1), a2: summary(a2), sharedCanvas, reloaded,
                            failed, warned, flips}));
