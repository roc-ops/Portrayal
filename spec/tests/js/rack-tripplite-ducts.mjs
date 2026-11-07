// spec/tests/js/rack-tripplite-ducts.mjs
// THE TRIPP LITE SERIES SMARTRACK DUCTS IN THE RACK KIT (#1094): what the three 1U finger ducts
// advertise works in the kit, not only in the drawing. A cable is laid along the duct of each,
// the yellow SRCABLEDUCT1UFC takes a cable through a rear window and is placed on the REAR face
// of a rack as its maker says it mounts "on either the front or the rear", and no part claims a
// cable capacity its maker does not state. Everything reads the build, as the Rack Builder does:
// rack.json for each part's catalogue entry, and the compiled drawings for where its duct and
// its passes stand.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import {inspect} from '../../../kit/rack/queries.js';

const DIST = new URL('../../../library/dist/', import.meta.url);
const skip = existsSync(new URL('rack.json', DIST)) ? false : 'library/dist not built - run ./build.sh';
const devices = skip ? {} : JSON.parse(readFileSync(new URL('rack.json', DIST), 'utf8')).devices;
const stub = {sw: {ru: 1, w: 440, h: 44, d: 515}, pp: {ru: 1, w: 440, h: 44, d: 100}};
const chassisOf = ref => devices[ref] ?? stub[ref] ?? null;

const NAMES = ['srcableduct1u', 'srcableduct1uhd', 'srcableduct1ufc'];
const FC = 'srcableduct1ufc';
const WINDOWS = ['rear-window-1', 'rear-window-2'];

const svgOf = (name, view) => readFileSync(new URL(`${name}.base.${view}.svg`, DIST), 'utf8');
function ductsOf(name) {
  const out = [];
  for (const m of svgOf(name, 'front').matchAll(/<rect id="guide--([\w-]+)" data-class="guide" data-guide="duct"/g)) out.push({via: m[1], kind: 'duct', face: 'front', x: 0});
  return out;
}

const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'base', ru, label: extra.label ?? ref, ...extra}).rack;
// a switch at U10 (i1), the duct at U12 (i2), a panel at U20 (i3)
const rackOf = (name, extra = {}) => add(add(add(M.newRack(), 'sw', 10), name, 12, extra), 'pp', 20);
const ctxFor = (name, guides, ports = {}) => ({chassisOf, bendOf: () => 1e12, guidesOf: id => (id === 'i2' ? guides : []),
  portX: end => ports[end.item] ?? 0, portY: () => null});
const cable = route => ({id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'q', view: 'front'},
  route, routeEdited: true});

for (const name of NAMES) {
  test(`${name}: the catalogue lists one duct, and a cable runs along it`, {skip}, async () => {
    const ducts = ductsOf(name);
    assert.deepEqual(ducts.map(d => d.via), ['duct']);
    assert.deepEqual(devices[name].guides, {front: ['duct']});
    const r = rackOf(name);
    const ctx = ctxFor(name, ducts);
    const c = cable([{item: 'i2', via: 'duct'}]);
    const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
    assert.deepEqual(resolved.waypoints, [{item: 'i2', via: 'duct'}], 'the route keeps the duct');
    assert.deepEqual(resolved.gone ?? [], []);
    const len = R.routedLength({...r, cables: [c]}, c, ctx);
    assert.ok(len.measured > 0, 'the cable has a length through the duct');
    const hm = await inspect(r, 'i2', {chassisOf});
    const found = hm.pathways.filter(p => p.kind === 'duct');
    assert.deepEqual(found.map(p => p.via), ['duct']);
    assert.ok(found.every(p => p.holds_spare), 'a duct holds spare cable');
  });

  test(`${name}: the maker states no cable capacity, so none is shown or compared`, {skip}, async () => {
    assert.equal(devices[name].capacity ?? null, null);
    const hm = await inspect(rackOf(name), 'i2', {chassisOf});
    assert.ok(!hm.capacity || hm.capacity.count == null, `${name}: no stated count`);
  });
}

test('only the fibre duct has a pass-through, and a cable crosses through each of its two rear windows', {skip}, async () => {
  assert.equal(devices.srcableduct1u.passes, undefined);
  assert.equal(devices.srcableduct1uhd.passes, undefined);
  assert.deepEqual(devices[FC].passes.rear, WINDOWS);
  const r = rackOf(FC), ducts = ductsOf(FC);
  // the page hands the kit a pass-through as a guide of kind `pass`; the catalogue (rack.json)
  // already lists these two, drawn in the rear view, as pathways a route may name
  const guides = [...ducts, ...WINDOWS.map(via => ({via, kind: 'pass', face: 'rear', x: 0}))];
  for (const via of WINDOWS) {
    const c = cable([{item: 'i2', via}]);
    const ctx = ctxFor(FC, guides);
    const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
    assert.deepEqual(resolved.waypoints, [{item: 'i2', via}], `${via} is a way for a cable`);
    assert.deepEqual(resolved.gone ?? [], []);
    assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0);
  }
  // a cable laid along the duct and then out through a window to the rear: both are kept, in order
  const c = cable([{item: 'i2', via: 'duct'}, {item: 'i2', via: WINDOWS[0]}]);
  const resolved = R.resolveRoute({...r, cables: [c]}, c, ctxFor(FC, guides));
  assert.deepEqual(resolved.waypoints, [{item: 'i2', via: 'duct'}, {item: 'i2', via: WINDOWS[0]}]);
  const hm = await inspect(r, 'i2', {chassisOf});
  assert.deepEqual(hm.pathways.filter(p => p.kind === 'pass').map(p => [p.via, p.holds_spare]), WINDOWS.map(v => [v, false]));
});

test('the fibre duct is placed on the rear face of a rack, the same part and the same duct', {skip}, async () => {
  const r = rackOf(FC, {face: 'rear'});
  const item = r.items.find(i => i.ref === FC);
  assert.equal(item.face, 'rear', 'a rack-face part is placed on either face');
  assert.equal(devices[FC].mount, 'rack-face');
  const ducts = ductsOf(FC);
  const c = cable([{item: item.id, via: 'duct'}]);
  const ctx = {...ctxFor(FC, ducts), guidesOf: id => (id === item.id ? ducts : [])};
  const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
  assert.deepEqual(resolved.waypoints, [{item: item.id, via: 'duct'}], 'the route keeps the duct on the rear face');
  assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0);
  // and on the front the same part is front: the face is the placement's to say
  assert.equal(rackOf(FC).items.find(i => i.ref === FC).face, 'front');
});
