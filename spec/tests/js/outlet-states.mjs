// An outlet's state shown on its lamp (#934, docs/pdu-model-design.md 3.2).
//
// A switched PDU's outlet declares `[on, off]`; the lamp that shows it is a
// part of its own, placed beside it with `for:`. A state set on the outlet's
// path has to reach the lamp in the marks document (marks.js apply), the
// Explorer's chips (states.js offIsSet) and the 3D scene (relief.js
// applyNodeStates and applyNodeLampColors), through one rule in states.js
// (boundLamps, expandStates). Exercised on the fake DOM through the real
// modules; test_outlet_states_js.py reads the JSON this prints.
import { build, install, Node } from './fake-dom.mjs';

install();
globalThis.location = { search: '' };

// What the real modules ask of an element that the shared fake DOM leaves
// out: classList, an inline style, nodeType, and Element.matches for the two
// selector shapes render.py writes a declared colour as (`#id.state-x`,
// `#id .state-x`). Added here, for this script only.
Object.defineProperty(Node.prototype, 'nodeType', {get() { return 1; }});
Object.defineProperty(Node.prototype, 'isConnected', {get() { return false; }});
Object.defineProperty(Node.prototype, 'classList', {get() {
  const n = this;
  const list = () => (n.getAttribute('class') || '').split(/\s+/).filter(Boolean);
  const put = l => { if (l.length) n.setAttribute('class', l.join(' ')); else n.removeAttribute('class'); };
  return {
    contains: c => list().includes(c),
    add: (...cs) => put([...new Set([...list(), ...cs])]),
    remove: (...cs) => put(list().filter(c => !cs.includes(c))),
    [Symbol.iterator]: () => list()[Symbol.iterator](),
  };
}});
Object.defineProperty(Node.prototype, 'style', {get() {
  const n = this;
  const decls = () => Object.fromEntries((n.getAttribute('style') || '').split(';')
    .map(d => d.trim()).filter(Boolean).map(d => [d.slice(0, d.indexOf(':')).trim(), d.slice(d.indexOf(':') + 1).trim()]));
  const put = o => {
    const t = Object.entries(o).map(([k, v]) => `${k}:${v}`).join(';');
    n.setAttribute('style', t);
  };
  return {
    getPropertyValue: k => decls()[k] || '',
    setProperty: (k, v) => put({...decls(), [k]: v}),
    removeProperty: k => { const o = decls(); delete o[k]; put(o); },
  };
}});
Node.prototype.matches = function (sel) {
  const m = /^#([\w-]+)(\s+)?\.([\w-]+)$/.exec(sel.trim());
  if (!m) return false;
  const [, id, desc, cls] = m;
  if (!this.classList.contains(cls)) return false;
  if (!desc) return this.getAttribute('id') === id;
  for (let p = this.parentNode; p; p = p.parentNode) if (p.getAttribute('id') === id) return true;
  return false;
};

const S = await import('../../../kit/states.js');
const M = await import('../../../kit/marks.js');
const R = await import('../../../kit/relief.js');

// A front face: two switched outlets, A1 with its lamp bound by `for:` and a
// C14 plug seated in it (data-for, no states), A2 with none; a silkscreen mark
// naming A1; a port whose lamp is bound to it but which declares no states of
// its own; and a lamp bound by a cross-view target. The `svg` root answers
// querySelectorAll('style') with the declared-colour rules render.py would
// write for lamp-a1 (on green, off red), for declaredHere.
const face = () => {
  const root = build({t: 'svg', a: {id: 'face'}, c: [
    {a: {'data-path': 'outlet-a1', id: 'outlet-a1', 'data-class': 'inlet', 'data-states': 'on off',
         'data-lamped': 'true'}},
    {a: {'data-path': 'lamp-a1', id: 'lamp-a1', 'data-class': 'led', 'data-states': 'on off',
         'data-for': 'outlet-a1'}, c: [
      {t: 'circle', a: {'data-path': 'lamp-a1/lamp', 'data-class': 'led', 'data-states': 'on off'}}]},
    {a: {'data-path': 'plug-a1', 'data-for': 'outlet-a1', 'data-behaviour': 'occupies'}},
    {a: {'data-path': 'silk-a1', 'data-for': 'outlet-a1'}},
    {a: {'data-path': 'outlet-a2', id: 'outlet-a2', 'data-class': 'inlet', 'data-states': 'on off'}},
    {a: {'data-path': 'eth0', 'data-class': 'port'}},
    {a: {'data-path': 'led-eth0', 'data-class': 'led', 'data-states': 'off link', 'data-for': 'eth0'}},
    {a: {'data-path': 'led-far', 'data-class': 'led', 'data-states': 'on off', 'data-for': '/rear/outlet-a2'}},
    {a: {'data-path': 'breaker-a/rocker', 'data-class': 'breaker', 'data-states': 'on off'}},
    {a: {'data-path': 'led-plain', 'data-class': 'led', 'data-states': 'off on'}},
    // a lamp whose states are prose is no lamp to bind
    {a: {'data-path': 'led-prose', 'data-class': 'led', 'data-states': 'Green = on', 'data-for': 'outlet-a2'}},
    // something switched that is not a power outlet, with a lamp bound to it
    {a: {'data-path': 'relay-1', 'data-class': 'relay', 'data-states': 'on off'}},
    {a: {'data-path': 'lamp-r1', 'data-class': 'led', 'data-states': 'off on', 'data-for': 'relay-1'}},
  ]});
  const rules = [{selectorText: '#lamp-a1.state-off, #lamp-a1 .state-off'},
                 {selectorText: '#lamp-a1.state-on, #lamp-a1 .state-on'}];
  const qsa = root.querySelectorAll.bind(root);
  root.querySelectorAll = sel => sel === 'style' ? [{sheet: {cssRules: rules}}] : qsa(sel);
  for (const n of root.descendants()) Object.defineProperty(n, 'ownerSVGElement', {value: root});
  return root;
};
const el = (root, path) => root.querySelectorAll(`[data-path="${path}"]`)[0];
const cls = (root, path) => el(root, path).getAttribute('class') || '';
const out = {};

// --- the binding --------------------------------------------------------------
{
  const f = face();
  const b = S.boundLamps(f);
  out.bound = Object.fromEntries([...b].map(([k, v]) => [k, v.map(l => l.getAttribute('data-path'))]));
}

// --- the map expansion --------------------------------------------------------
{
  const f = face();
  const b = S.boundLamps(f);
  out.expanded = S.expandStates({'outlet-a1': 'state-off', 'outlet-a2': 'state-on', eth0: 'state-up'}, b);
  // a lamp the map states itself wins over its outlet
  out.lampWins = S.expandStates({'outlet-a1': 'state-off', 'lamp-a1': 'state-on'}, b);
  // the same answer from path bindings, which is what the 3D scope keeps
  out.byPaths = S.expandStates(new Map([['outlet-a1', 'state-on']]),
                               new Map([['outlet-a1', new Set(['lamp-a1'])]]));
  out.empty = S.expandStates({'outlet-a1': ''}, b);
}

// --- the chip rule for `off` ------------------------------------------------
{
  const f = face();
  const b = S.boundLamps(f);
  const lampsOf = p => b.get(p) || [];
  out.offIsSet = Object.fromEntries(['outlet-a1', 'outlet-a2', 'lamp-a1', 'led-plain',
                                     'breaker-a/rocker', 'eth0', 'relay-1']
    .map(p => [p, S.offIsSet(el(f, p), lampsOf(p))]));
  // paints(): an undeclared off still paints (it is the unlit fill); a declared
  // one is measured rather than assumed
  out.paintsOff = {plain: S.paints(el(f, 'led-plain'), 'off')};
}

// --- 2D: a marks document ---------------------------------------------------
{
  const f = face();
  const before = JSON.stringify(f, (k, v) => (k === 'parentNode' ? undefined : v));
  const rep = M.apply(f, {v: 1, marks: [{select: '[data-path="outlet-a1"]', state: 'off'},
                                        {select: '[data-path="outlet-a2"]', state: 'on'},
                                        {select: '[data-path="eth0"]', state: 'up'}]},
                      {legend: false, behavior: false});
  out.marks = {a1: cls(f, 'outlet-a1'), lamp: cls(f, 'lamp-a1'), plug: cls(f, 'plug-a1'),
               silk: cls(f, 'silk-a1'), a2: cls(f, 'outlet-a2'), ethLamp: cls(f, 'led-eth0'),
               far: cls(f, 'led-far'), counts: rep.map(r => r.count)};
  M.clear(f);
  out.marksClearExact = JSON.stringify(f, (k, v) => (k === 'parentNode' ? undefined : v)) === before;

  // a later mark naming the lamp itself wins, by order
  const g = face();
  M.apply(g, {v: 1, marks: [{select: '[data-path="outlet-a1"]', state: 'off'},
                            {select: '[data-path="lamp-a1"]', state: 'on'}]},
          {legend: false, behavior: false});
  out.marksLater = cls(g, 'lamp-a1');

  // a custom lamp colour from one mark is not shown while another mark - here
  // the outlet's state reaching it - has the lamp off; on, it is
  const h = face();
  M.apply(h, {v: 1, marks: [{select: '[data-path="lamp-a1"]', lamp: '#ff00ff'},
                            {select: '[data-path="outlet-a1"]', state: 'off'}]},
          {legend: false, behavior: false});
  out.marksOffColour = el(h, 'lamp-a1').getAttribute('style');
  M.apply(h, {v: 1, marks: [{select: '[data-path="lamp-a1"]', lamp: '#ff00ff'},
                            {select: '[data-path="outlet-a1"]', state: 'on'}]},
          {legend: false, behavior: false});
  out.marksOnColour = el(h, 'lamp-a1').getAttribute('style');
}

// --- 3D: the registry applied to a parsed face, and to a relief piece --------
{
  const scope = R.createReliefScope();
  R.setNodeStates({'outlet-a1': 'state-off', 'outlet-a2': 'state-on'}, scope);
  const f = face();
  R.applyNodeStates(f, scope);
  out.three = {a1: cls(f, 'outlet-a1'), lamp: cls(f, 'lamp-a1'), plug: cls(f, 'plug-a1'),
               a2: cls(f, 'outlet-a2')};
  out.threeBindings = Object.fromEntries([...R.lampBindings(scope)].map(([k, v]) => [k, [...v]]));
  // a relief piece cut from the face holds the lamp and not the outlet: it is
  // lit from the bindings the whole face left in the scope
  const piece = build({c: [{a: {'data-path': 'lamp-a1', 'data-class': 'led', 'data-states': 'on off',
                                'data-for': 'outlet-a1'}}]});
  R.applyNodeStates(piece, scope);
  out.threePiece = cls(piece, 'lamp-a1');
  // and with the bindings forgotten (a new build), a piece alone does not
  const fresh = R.createReliefScope();
  R.setNodeStates({'outlet-a1': 'state-off'}, fresh);
  const piece2 = build({c: [{a: {'data-path': 'lamp-a1', 'data-states': 'on off', 'data-for': 'outlet-a1'}}]});
  R.applyNodeStates(piece2, fresh);
  out.threePieceUnbound = cls(piece2, 'lamp-a1');
  R.clearLampBindings(scope);
  out.threeCleared = R.lampBindings(scope).size;

  // a custom lamp colour stays off while the lamp's OUTLET is off
  const s2 = R.createReliefScope();
  R.setNodeStates({'outlet-a1': 'state-off'}, s2);
  R.setNodeLampColors({'lamp-a1': '#ff00ff', 'led-plain': '#00ff00'}, s2);
  const g = face();
  R.applyNodeStates(g, s2);
  R.applyNodeLampColors(g, s2);
  out.threeOffColour = {lamp: el(g, 'lamp-a1').getAttribute('style'),
                        plain: el(g, 'led-plain').getAttribute('style')};
}

console.log(JSON.stringify(out));
