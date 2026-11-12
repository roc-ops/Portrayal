// spec/tests/js/rack-navepoint-managers.mjs
// NAVEPOINT'S CABLE MANAGERS IN THE RACK KIT (#1099): what the seven parts advertise works in the kit, not only
// in the drawing. A cable runs along the duct of each raceway and each vertical manager, crosses the brush
// panel's slot, and a vertical manager is placed beside the rack and fitted by the rack units it states.
// Everything reads the build, as the Rack Builder does: rack.json for each part's catalogue entry.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import {apply} from '../../../kit/rack/commands.js';

const DIST = new URL('../../../library/dist/', import.meta.url);
const skip = existsSync(new URL('rack.json', DIST)) ? false : 'library/dist not built - run ./build.sh';
const devices = skip ? {} : JSON.parse(readFileSync(new URL('rack.json', DIST), 'utf8')).devices;
const stub = {sw: {ru: 1, w: 440, h: 44, d: 515}, pp: {ru: 1, w: 440, h: 44, d: 100}};
const chassisOf = ref => devices[ref] ?? stub[ref] ?? null;

const RACEWAYS = ['00404167', '00404169', '00404170'];
const VERTICALS = {'00407295': 24, '00407296': 40, '00407297': 44};
const svgOf = (name, view) => readFileSync(new URL(`${name}.base.${view}.svg`, DIST), 'utf8');
const ductsOf = (name, run) => [...svgOf(name, 'front').matchAll(/<rect id="guide--([\w-]+)" data-class="guide" data-guide="duct" data-guide-run="(\w)"/g)]
  .map(m => ({via: m[1], kind: 'duct', face: 'front', run: m[2], x: 0}));

const add = (rack, ref, ru) => M.withItem(rack, {ref, cfg: 'base', ru, label: ref}).rack;
const rackOf = name => add(add(add(M.newRack(), 'sw', 10), name, 12), 'pp', 20);
const ctxFor = (name, guides) => ({chassisOf, bendOf: () => 1e12, guidesOf: id => (id === 'i2' ? guides : []),
  portX: () => 0, portY: () => null});
const cable = route => ({id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'q', view: 'front'},
  route, routeEdited: true});

for (const name of RACEWAYS) {
  test(`${name}: the catalogue lists its duct, and a cable runs along it`, {skip}, () => {
    const ducts = ductsOf(name);
    assert.deepEqual(ducts.map(d => [d.via, d.run]), [['duct', 'x']]);
    assert.deepEqual(Object.values(devices[name].guides).flat(), ['duct']);
    assert.equal(devices[name].mount, 'rack-face');
    const r = rackOf(name), c = cable([{item: 'i2', via: 'duct'}]);
    const resolved = R.resolveRoute({...r, cables: [c]}, c, ctxFor(name, ducts));
    assert.deepEqual(resolved.waypoints, [{item: 'i2', via: 'duct'}], 'the route keeps the duct');
    assert.ok(R.routedLength({...r, cables: [c]}, c, ctxFor(name, ducts)).measured > 0, 'the cable has a length');
  });
}

test('00401654: a cable crosses through the brush slot', {skip}, () => {
  assert.deepEqual(devices['00401654'].passes.front, ['brush-window']);
  const r = rackOf('00401654'), c = cable([{item: 'i2', via: 'brush-window'}]);
  const ctx = ctxFor('00401654', [{via: 'brush-window', kind: 'pass', face: 'front', x: 0}]);
  const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
  assert.deepEqual(resolved.waypoints, [{item: 'i2', via: 'brush-window'}]);
  assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0);
});

const frame = heightRU => M.withFrame(M.newDoc({kind: 'two-post'}).racks[0], {heightRU});
const place = (rack, ref) => apply(rack, {op: 'zerou.place', ref, at: 'left', ru: 1}, {chassisOf});

for (const [name, ru] of Object.entries(VERTICALS)) {
  test(`${name}: a ${ru}U vertical manager runs its duct down the part and is fitted by its rack units`, {skip}, () => {
    assert.equal(devices[name].mount, 'rack-side');
    assert.equal(devices[name].ru, ru);
    assert.deepEqual(ductsOf(name).map(d => [d.via, d.run]), [['duct', 'y']]);
    const fits = place(frame(ru), name);
    assert.ok(!fits.error, `fits a rack of its own height: ${fits.error}`);
    if (ru > 24) assert.ok(place(frame(24), name).error, 'does not fit a 24U rack');
  });
}
