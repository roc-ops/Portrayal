// An optic seated by the kit must be the optic the build seats.
//
// `swap.js` repeats one formula from render.py - `seat_at`, as `occupantAt` -
// and assembles the occupant's attributes from three published sources. Both
// are held to a REAL build here: test_cage_seat_js.py renders a fitted copy of
// a device, reads what render.py actually wrote on every occupant, and hands it
// to this script with the bare build's `cages[]` and the components.json
// entries. Checking the formula against itself would prove nothing.
//
// Three cases, chosen by argv[2]:
//   parity   - stdin JSON; per port, the kit's transform and attribute set
//   overrides - applyOccupantOverrides on a fake DOM
//   rename   - `segment = ''` names an occupant's children as the build does
//
// jsdom is not a dependency here, so the DOM is the smallest one swap.js
// actually uses (the idiom of nested-bays.mjs).
const m = await import('../../../kit/swap.js');
const mode = process.argv[2];

// ---------------------------------------------------------------- fake DOM
class Node {
  constructor(attrs = {}, children = []) {
    this._attrs = {...attrs};
    this.parentNode = null;
    this.children = [];
    for (const c of children) this.appendChild(c);
  }
  get attributes() {
    return Object.entries(this._attrs).map(([name, value]) => ({name, value}));
  }
  get childNodes() { return [...this.children]; }
  get ownerDocument() { return DOC; }
  getAttribute(k) { return k in this._attrs ? this._attrs[k] : null; }
  setAttribute(k, v) { this._attrs[k] = String(v); }
  removeAttribute(k) { delete this._attrs[k]; }
  hasAttribute(k) { return k in this._attrs; }
  appendChild(c) {
    if (c.parentNode) c.remove();
    c.parentNode = this;
    this.children.push(c);
    return c;
  }
  remove() {
    const p = this.parentNode;
    if (!p) return;
    p.children.splice(p.children.indexOf(this), 1);
    this.parentNode = null;
  }
  after(n) {
    if (n.parentNode) n.remove();
    const p = this.parentNode;
    p.children.splice(p.children.indexOf(this) + 1, 0, n);
    n.parentNode = p;
  }
  *descendants() {
    for (const c of this.children) { yield c; yield* c.descendants(); }
  }
  querySelectorAll(sel) {
    const alts = sel.split(',').map(s => s.trim()).map(parseSel);
    return [...this.descendants()].filter(n => alts.some(a => a(n)));
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
  clone() {
    return new Node(this._attrs, this.children.map(c => c.clone()));
  }
}
function parseSel(s) {
  if (s === '*') return () => true;
  const parts = [...s.matchAll(/\[([\w-]+)(?:="([^"]*)")?\]/g)];
  if (!parts.length || parts.map(p => p[0]).join('') !== s)
    throw new Error('unexpected selector ' + s);
  return n => parts.every(([, k, v]) =>
    v === undefined ? n.hasAttribute(k) : n.getAttribute(k) === v);
}
function build(spec) {
  return new Node(spec.a || {}, (spec.c || []).map(build));
}
const DOC = {
  createElementNS: () => new Node(),
  importNode: n => n.clone(),
};
// A skin's "text" is a JSON tree here; DOMParser is the only thing that reads it.
globalThis.DOMParser = class {
  parseFromString(text) {
    const documentElement = build(JSON.parse(text));
    return {
      documentElement,
      getElementById: id => [documentElement, ...documentElement.descendants()]
        .find(n => n.getAttribute('id') === id) || null,
    };
  }
};
globalThis.CSS = {escape: s => s};

// ---------------------------------------------------------------- parity
if (mode === 'parity') {
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;
  const {ports} = JSON.parse(raw);
  const out = ports.map(({port, cage, ref, comp, skinRoot}) => {
    const tf = m.occupantTransform(cage, comp);
    const t = /^translate\(([^,]+),([^)]+)\)(?: rotate\(([^ ]+) ([^ ]+) ([^)]+)\))?$/.exec(tf);
    return {
      port,
      transformText: tf,
      transform: t ? {tx: +t[1], ty: +t[2],
                      rotate: t[3] ? [+t[3], +t[4], +t[5]] : null} : null,
      attrs: m.occupantAttrs(cage, ref, comp, skinRoot),
    };
  });
  console.log(JSON.stringify(out));
}

// ---------------------------------------------------------------- overrides
if (mode === 'overrides') {
  const COMP = {
    'generic/sfp-lc@1': {name: 'sfp-lc', version: '1.0.0',
                         size: {w: 13.55, h: 8.55, d: 47.5}, mate: [6.775, 4.275]},
    'generic/sfp-lc-simplex@1': {name: 'sfp-lc-simplex', version: '1.0.0',
                                 size: {w: 13.55, h: 8.55, d: 47.5}, mate: [6.775, 4.275]},
  };
  const skin = name => JSON.stringify({a: {}, c: [
    {a: {id: name, 'data-path': name, 'data-class': 'transceiver',
         'data-behaviour': 'occupies', 'data-media': 'fiber'}, c: [
      {a: {id: `${name}--body`}},
      {a: {id: `${name}--tx`, 'data-path': `${name}/tx`}},
    ]},
  ]});
  const loadSkin = async ref => COMP[ref]
    ? {comp: COMP[ref], text: skin(COMP[ref].name)} : null;
  const cage = id => ({id, mate: [10, 5], rotate: null, lift: 0,
                       'occupant-attrs': {'data-group': 'sfp28', 'data-media': 'sfp28'}});
  const cages = ['port-4', 'port-5', 'port-6', 'port-7', 'port-8'].map(cage);
  // a cage whose aperture stands off the face: the kit cannot seat into it
  // without also shifting every child's absolute out, so it refuses
  cages[4].lift = 3;

  const face = () => {
    const root = new Node({}, [
      ...cages.map(c => new Node({id: c.id, 'data-path': c.id, 'data-class': 'port'})),
      new Node({id: 'led-port-4', 'data-path': 'led-port-4', 'data-class': 'led',
                'data-for': 'port-4'}),
      // what the build seated, at the END of the drawing, as render.py puts it
      ...cages.map(c => new Node({id: `${c.id}-occupant`, 'data-path': `${c.id}-occupant`,
                                  'data-behaviour': 'occupies', 'data-for': c.id,
                                  'data-ref': 'generic/sfp-lc@1:1.0.0'})),
    ]);
    return root;
  };
  const occ = (root, id) => root.querySelectorAll(
    `[data-for="${id}"][data-behaviour="occupies"]`);

  const root = face();
  const before = Object.fromEntries(cages.map(c => [c.id, occ(root, c.id).length]));
  const {applied, refused} = await m.applyOccupantOverrides(root, cages, {
    'port-4': 'generic/sfp-lc-simplex@1',     // replaced
    'port-5': null,                           // emptied
    'port-6': 'nobody/nothing@9',             // unknown: left empty
    // port-7 absent: untouched
    'port-8': 'generic/sfp-lc@1',             // lifted: refused, left empty
  }, loadSkin);
  const after = Object.fromEntries(cages.map(c => [c.id, occ(root, c.id).map(n => ({
    ref: n.getAttribute('data-ref'), id: n.getAttribute('id'),
    path: n.getAttribute('data-path'), transform: n.getAttribute('transform'),
    media: n.getAttribute('data-media'), group: n.getAttribute('data-group'),
    children: n.children.map(k => [k.getAttribute('id'), k.getAttribute('data-path')]),
    // the next sibling of the host is where it went
    besideHost: root.children[root.children.indexOf(n) - 1]?.getAttribute('id'),
  }))]));
  // a second swap replaces the first swap's occupant, not stacks beside it
  const second = await m.applyOccupantOverrides(root, cages, {'port-4': 'generic/sfp-lc@1'}, loadSkin);
  const again = occ(root, 'port-4').map(n => n.getAttribute('data-ref'));
  console.log(JSON.stringify({
    applied, refused, before, after, again, second,
    // seatOccupant itself will not produce a half-lifted optic
    seatLifted: m.seatOccupant(DOC, cages[4], 'generic/sfp-lc@1',
                               COMP['generic/sfp-lc@1'], skin('sfp-lc')),
    led: root.querySelectorAll('[data-for="port-4"]')
      .filter(n => n.getAttribute('data-class') === 'led').length,
  }));
}

// ---------------------------------------------------------------- rename
if (mode === 'rename') {
  const mk = () => new Node({}, [
    new Node({id: 'sfp-lc', 'data-path': 'sfp-lc'}),
    new Node({id: 'sfp-lc--tx', 'data-path': 'sfp-lc/tx'}),
    new Node({id: 'sfp-lc--w0'}),
    new Node({'clip-path': 'url(#sfp-lc--w0)'}),
  ]);
  const read = w => w.children.map(n => [n.getAttribute('id'), n.getAttribute('data-path'),
                                         n.getAttribute('clip-path')]);
  const bare = mk();
  m.rename(bare, 'sfp-lc', 'port-4-occupant', 'port-4-occupant', '');
  const dflt = mk();
  m.rename(dflt, 'sfp-lc', 'front-0');
  console.log(JSON.stringify({bare: read(bare), dflt: read(dflt)}));
}
