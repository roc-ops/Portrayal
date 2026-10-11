// A part that slides, on the documents the 3D scene is built from
// (docs/adjustable-positions-design.md section 6). relief.js keeps what a host
// has written in a per-viewer registry and applies it to a face before the face
// is measured (the rebuild path) and to a face's own last output when
// something else on it is repainted (the repaint path). A position is in that
// registry, as a field at the path of its carrier. Both paths are run here on
// the fake DOM, through the real modules.
import { build, toSpec, install } from './fake-dom.mjs';

install();
globalThis.location = { search: '' };
// restyleText parses a face's text into a <div> and serialises it back. The
// fake DOM's text is its JSON tree, so the div reads and writes that.
globalThis.document = {createElement: () => {
  const div = build({t: 'div', c: []});
  Object.defineProperty(div, 'innerHTML', {
    set(text) { for (const c of [...div.children]) c.remove(); div.appendChild(build(JSON.parse(text))); },
    get() { return JSON.stringify(toSpec(div.children[0])); }});
  return div;
}};
const R = await import('../../../kit/relief.js');
const F = await import('../../../kit/fields.js');

const DECL = {axis: 'z', carrier: 'panel', range: [20, 180], default: 60,
              stops: {front: 20, rear: 180}, label: 'Panel setback', datum: 'the panel face'};
const M = (by, a = {}) => ({'data-moves-with': 'panel-setback', 'data-moves-by': by, ...a});
// a front face as render.py writes it: a well, a rail standing in it, and a
// part with a colour field beside them
const front = (at = 60) => build({t: 'svg', a: {'data-adjustments': JSON.stringify({'panel-setback': {...DECL, at}})}, c: [
  {t: 'g', a: {id: 'panel', 'data-path': 'panel', 'data-depth': String(at), transform: 'translate(10.0,0.0)', ...M('0 0 1')}},
  {t: 'g', a: {id: 'rail', 'data-path': 'rail', 'data-z-lift': String(-at), transform: 'translate(20.0,15.0)', ...M('0 0 1')}, c: [
    {t: 'g', a: {id: 'rail--rail', 'data-z-out': String(7.5 - at)}}]},
  {t: 'g', a: {id: 'badge', 'data-path': 'badge'}, c: [
    {t: 'rect', a: {id: 'badge--face', fill: '#6f6f6f', 'data-fill-from': 'tint'}}]},
]});
// a side face: a stud that moves in the plane, with a field of its own
const side = () => build({t: 'svg', a: {'data-adjustments': JSON.stringify({'panel-setback': {...DECL, at: 60}})}, c: [
  {t: 'g', a: {id: 'stud', 'data-path': 'stud', 'data-z-lift': '1.5', transform: 'translate(63.0,17.0)', ...M('1 0 0')}, c: [
    {t: 'circle', a: {id: 'stud--head', fill: '#d0d3d6', 'data-fill-from': 'finish', 'data-z-cyl': '2'}}]},
]});
const find = (root, id) => [root, ...root.descendants()].find(n => n.getAttribute('id') === id);
const KEYS = ['transform', 'data-depth', 'data-z-lift', 'data-z-out', 'fill'];
const snap = root => Object.fromEntries([root, ...root.descendants()].filter(n => n.getAttribute('id'))
  .map(n => [n.getAttribute('id'), Object.fromEntries(KEYS.filter(k => n.hasAttribute(k)).map(k => [k, n.getAttribute(k)]))]));
const stashed = root => [root, ...root.descendants()].some(n =>
  n.attributes.some(a => a.name.startsWith('data-portrayal-adjust')));
// what extractRelief does to a face before it measures it
const extract = (doc, scope) => { R.applyNodeFields(doc, scope); R.applyNodeAdjustments(doc, scope); return doc; };
// A REPAINT IS relief.js's own restyleText, on the face's own last output:
// the text goes in and the repainted text comes out, as viewer3d.js calls it
const repaint = (doc, scope) => build(JSON.parse(R.restyleText(JSON.stringify(toSpec(doc)), scope)));

const out = {};
const scope = R.createReliefScope();

// --- the rebuild path: a fresh document, measured where the registry puts it ---------------
out.rebuild = {};
for (const [name, fields] of [['default', {}], ['min', {panel: {'panel-setback': '20'}}],
                              ['max', {panel: {'panel-setback': '180'}}],
                              ['stop', {panel: {'panel-setback': 'rear'}}],
                              ['refused', {panel: {'panel-setback': '300'}}]]) {
  R.setNodeFields(fields, scope);
  out.rebuild[name] = {front: snap(extract(front(), scope)), side: snap(extract(side(), scope))};
}
// a face a configuration built at 20, with 60 in the registry
R.setNodeFields({panel: {'panel-setback': '60'}}, scope);
out.rebuildFromBuilt20 = snap(extract(front(20), scope));

// --- the repaint path: the same document, repainted from its own last output ------------
R.setNodeFields({panel: {'panel-setback': '180'}}, scope);
let f = extract(front(), scope), s = extract(side(), scope);
const at180 = {front: snap(f), side: snap(s)};
// another part's field changes, and the position does not
R.setNodeFields({panel: {'panel-setback': '180'}, badge: {tint: '#c22f2f'}, stud: {finish: '#101010'}}, scope);
f = repaint(f, scope); s = repaint(s, scope);
out.repaint = {front: snap(f), side: snap(s), at180};
// and again, twice more: a move that added on each repaint would walk away
f = repaint(repaint(f, scope), scope); s = repaint(repaint(s, scope), scope);
out.repaintThrice = {front: snap(f), side: snap(s)};
// the position changes on a document that was already moved
R.setNodeFields({panel: {'panel-setback': '20'}, badge: {tint: '#c22f2f'}}, scope);
f = repaint(f, scope); s = repaint(s, scope);
out.repaintTo20 = {front: snap(f), side: snap(s)};
// the position leaves the registry: as built, with nothing remembered
R.setNodeFields({}, scope);
f = repaint(f, scope); s = repaint(s, scope);
out.repaintCleared = {front: snap(f), side: snap(s), stash: stashed(f) || stashed(s)};
out.built = {front: snap(front()), side: snap(side())};

// --- a fragment cut from a face has no root, and is left where it was built --------------
R.setNodeFields({panel: {'panel-setback': '180'}}, scope);
const whole = extract(side(), scope);
const piece = build({t: 'g', a: {}, c: [toSpec(find(whole, 'stud'))]});
const before = JSON.stringify(toSpec(piece));
R.applyNodeAdjustments(piece, scope);
out.fragmentUntouched = JSON.stringify(toSpec(piece)) === before;

// --- two viewers, two positions ----------------------------------------------------------
const other = R.createReliefScope();
R.setNodeFields({panel: {'panel-setback': '20'}}, other);
out.scopes = [find(extract(front(), scope), 'panel').getAttribute('data-depth'),
              find(extract(front(), other), 'panel').getAttribute('data-depth')];

// --- does a change of fields move a part that slides? -------------------------------------
// What viewer3d.js asks to tell a rebuild from a repaint. `A` is the
// adjustments of a device's configs.json.
const A = {'panel-setback': DECL, 'shelf-height': {...DECL, carrier: 'shelf'}};
const P = v => ({panel: {'panel-setback': v}});
out.changed = {
  set: F.positionsChanged(A, {}, P('20')),
  moved: F.positionsChanged(A, P('20'), P('180')),
  cleared: F.positionsChanged(A, P('20'), {}),
  same: F.positionsChanged(A, P('20'), P('20')),
  sameWithOthers: F.positionsChanged(A, {...P('20'), stud: {finish: '#111'}}, {...P('20'), stud: {finish: '#222'}}),
  otherPart: F.positionsChanged(A, {}, {stud: {finish: '#222'}}),
  // the id at a path that is not its carrier is an ordinary key
  notTheCarrier: F.positionsChanged(A, {}, {rail: {'panel-setback': '20'}}),
  // a field of the carrier that is no position
  carrierOtherKey: F.positionsChanged(A, {}, {panel: {tint: '#222'}}),
  second: F.positionsChanged(A, P('20'), {...P('20'), shelf: {'shelf-height': '5'}}),
  noAdjustments: [F.positionsChanged(undefined, {}, P('20')), F.positionsChanged({}, {}, P('20')),
                  F.positionsChanged(null, P('1'), {})],
  emptyMaps: F.positionsChanged(A, undefined, null),
};

console.log(JSON.stringify(out));
