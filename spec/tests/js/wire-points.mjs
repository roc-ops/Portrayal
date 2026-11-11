// A terminal plug leaves by one wire per pole, `wire-1` to `wire-N`, and
// `cablePoints(svg, 'wire')` (`wirePoints`) reads them. Without a DOM and
// without jsdom: a small element tree that answers the few selectors
// cablePoints asks.
import test from 'node:test';
import assert from 'node:assert/strict';

globalThis.location = {search: ''};
globalThis.fetch = async () => ({ok: true, text: async () => '<svg/>'});

const m = await import('../../../kit/relief.js');

const camel = k => k.replace(/^data-/, '').replace(/-([a-z])/g, (_, c) => c.toUpperCase());

function matcher(sel) {
  let r;
  if ((r = /^\[data-path\]$/.exec(sel))) return n => 'path' in n.dataset;
  if ((r = /^\[data-cp="cable"\]$/.exec(sel))) return n => n.dataset.cp === 'cable';
  if ((r = /^\[data-cp\^="wire-"\]$/.exec(sel))) return n => (n.dataset.cp || '').startsWith('wire-');
  if (sel === '[id]') return n => 'id' in n.attrs;
  if ((r = /^\[id="(.*)"\]$/.exec(sel))) return n => n.attrs.id === r[1];
  throw new Error('unexpected selector ' + sel);
}

function el(attrs, parent) {
  const dataset = {};
  for (const [k, v] of Object.entries(attrs)) if (k.startsWith('data-')) dataset[camel(k)] = v;
  const node = {attrs, dataset, parentElement: parent, children: []};
  node.getAttribute = k => (k in attrs ? attrs[k] : null);
  if (parent) parent.children.push(node);
  node.descendants = function* () { for (const c of node.children) { yield c; yield* c.descendants(); } };
  node.querySelectorAll = sel => { const f = matcher(sel); return [...node.descendants()].filter(f); };
  node.querySelector = sel => node.querySelectorAll(sel)[0] || null;
  node.closest = sel => {
    const f = matcher(sel);
    for (let n = node; n; n = n.parentElement) if (n.dataset && f(n)) return n;
    return null;
  };
  return node;
}

function quiet(fn) {
  const warned = [], warn = console.warn;
  console.warn = (...a) => warned.push(a.join(' '));
  try { return {out: fn(), warned}; } finally { console.warn = warn; }
}

// a plug as render.py writes it: one instance group, a stub per wire (a cyl at
// lift 10 for 30), and the markers last, sorted as text
function plug(svg, path, nWires, {lift = 0, names, forPath} = {}) {
  const g = el({id: path, 'data-path': path, 'data-z-lift': String(lift),
                ...(forPath ? {'data-for': forPath} : {})}, svg);
  const list = names || Array.from({length: nWires}, (_, i) => `wire-${i + 1}`);
  for (const n of list) el({id: `${path}--${n}`, 'data-z-cyl': '30', 'data-z-lift': '10'}, g);
  for (const n of [...list].sort())
    el({'data-cp': n, 'data-cp-at': `${(n.replace(/\D/g, '') * 2.54).toFixed(2)} 10.7`, 'data-cp-dir': 'front',
        'data-cp-on': `${path}--${n}`}, g);
  return g;
}

test('a plug with three wires gives three points, each on its own stub', () => {
  const svg = el({});
  plug(svg, 'p', 3);
  const {out, warned} = quiet(() => m.wirePoints(svg));
  assert.deepEqual(warned, []);
  assert.deepEqual(out.map(p => p.name), ['wire-1', 'wire-2', 'wire-3']);
  assert.deepEqual(out.map(p => p.wire), [1, 2, 3]);
  assert.deepEqual(out.map(p => p.at), [[2.54, 10.7], [5.08, 10.7], [7.62, 10.7]]);
  assert.ok(out.every(p => p.dir === 'front' && p.path === 'p'));
  // the far end of the stub: its own lift 10 plus its length 30
  assert.deepEqual(out.map(p => p.z), [40, 40, 40]);
  assert.ok(out.every(p => p.lift === 0));
});

test('cablePoints(svg, "wire") is wirePoints', () => {
  const svg = el({});
  plug(svg, 'p', 2);
  assert.deepEqual(m.cablePoints(svg, 'wire').map(p => p.name), m.wirePoints(svg).map(p => p.name));
});

test('the lift of the group is summed under each wire', () => {
  const svg = el({});
  plug(svg, 'p', 2, {lift: 7});
  const out = m.wirePoints(svg);
  assert.deepEqual(out.map(p => p.z), [47, 47]);
  assert.deepEqual(out.map(p => p.lift), [7, 7]);
});

test('wires come in number order, not text order, and a plug stays together', () => {
  const svg = el({});
  plug(svg, 'a', 11);
  plug(svg, 'b', 2);
  const out = m.wirePoints(svg);
  assert.deepEqual(out.map(p => `${p.path}:${p.wire}`),
    [...Array.from({length: 11}, (_, i) => `a:${i + 1}`), 'b:1', 'b:2']);
});

test('cablePoints without a kind is unchanged: wires are not cable ends', () => {
  const svg = el({});
  plug(svg, 'p', 3);
  const cable = el({'data-path': 'c', id: 'c'}, svg);
  el({'data-cp': 'cable', 'data-cp-at': '1 2'}, cable);
  const only = m.cablePoints(svg);
  assert.deepEqual(only.map(p => p.name), ['cable']);
  assert.ok(!('wire' in only[0]));
  assert.deepEqual(m.wirePoints(svg).map(p => p.path), ['p', 'p', 'p'], 'a cable point is not a wire');
});

test('only wire- and a number from 1 is a wire', () => {
  const svg = el({});
  plug(svg, 'p', 0, {names: ['wire-1', 'wire-0', 'wire-01', 'wire-x', 'wire-', 'wire-2a', 'wire-2']});
  assert.deepEqual(m.wirePoints(svg).map(p => p.name), ['wire-1', 'wire-2']);
});

test('a plug seated on a port is one owner of its own and its wires survive', () => {
  const svg = el({});
  const port = el({id: 'port', 'data-path': 'port'}, svg);
  el({'data-cp': 'mate', 'data-cp-at': '1 1'}, port);
  plug(svg, 'port-occupant', 2, {forPath: 'port'});
  const out = m.wirePoints(svg);
  assert.deepEqual(out.map(p => `${p.path}:${p.wire}`), ['port-occupant:1', 'port-occupant:2']);
});

test('a part deeper on the chain with wires of its own shadows the plug, as for a cable', () => {
  const svg = el({});
  plug(svg, 'host', 2);
  plug(svg, 'host/inner', 2);
  const out = m.wirePoints(svg);
  assert.deepEqual([...new Set(out.map(p => p.path))], ['host/inner']);
  assert.equal(out.length, 2);
});

test('a plug and a boot-like occupant seated on it: the outermost wires win', () => {
  const svg = el({});
  plug(svg, 'cage', 2);
  plug(svg, 'cage-plug', 2, {forPath: 'cage'});
  const out = m.wirePoints(svg);
  assert.deepEqual([...new Set(out.map(p => p.path))], ['cage-plug']);
});

test('an unreadable position is null, said once per wire, and the others are read', () => {
  const svg = el({});
  const g = plug(svg, 'p', 2);
  g.children.find(c => c.dataset.cp === 'wire-2').dataset.cpAt = 'banana';
  const {out, warned} = quiet(() => m.wirePoints(svg));
  assert.deepEqual(out.map(p => p.at), [[2.54, 10.7], null]);
  assert.equal(warned.length, 1);
  assert.match(warned[0], /unreadable data-cp-at/);
});

test('a feature the wire names but the host lacks falls back to the face, and says so', () => {
  const svg = el({});
  const g = el({id: 'p', 'data-path': 'p', 'data-z-lift': '3'}, svg);
  el({'data-cp': 'wire-1', 'data-cp-at': '1 1', 'data-cp-on': 'nope'}, g);
  const {out, warned} = quiet(() => m.wirePoints(svg));
  assert.equal(out[0].z, 3);
  assert.equal(warned.length, 1);
  assert.match(warned[0], /declares its wire point on "nope"/);
});

test('a wire with no `on:` takes the lift of its group', () => {
  const svg = el({});
  const g = el({id: 'p', 'data-path': 'p', 'data-z-lift': '4'}, svg);
  el({'data-cp': 'wire-1', 'data-cp-at': '1 1'}, g);
  assert.equal(m.wirePoints(svg)[0].z, 4);
});

test('an empty drawing gives an empty list, and a kind that is neither is refused', () => {
  const svg = el({});
  assert.deepEqual(m.wirePoints(svg), []);
  assert.throws(() => m.cablePoints(svg, 'wires'), /kind is 'cable' or 'wire'/);
});
