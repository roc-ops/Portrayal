// spec/tests/js/rack-belden-managers.mjs
// BELDEN'S HORIZONTAL MANAGERS IN THE RACK KIT (#1103, part of #1091): what the four BHH molded-finger
// managers, the 9512-1901 finger stock manager, the 9510-1901 ring panel and the 9511-1903 and
// 9511-1904 ring managers advertise works in the kit, not only in the drawing. A cable is laid along
// the duct of each finger part and through the rings of each ring part, in at one face and out at the
// other. Everything reads the build, as the Rack Builder does: rack.json for each part's catalogue
// entry, and the compiled front drawing for where its rings and ducts stand across the rack. Every
// part is a rack-face part, so the kit stands its rings half the part's depth out of the rail plane.
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

const RINGED = {'9510-1901': 6, '9511-1903': 8, '9511-1904': 8};
const DUCTED = ['bhh191ur', 'bhh192ur', 'bhh193ur', 'bhh194ur', '9512-1901'];
const APERTURE = [34, 68.7];
const BAND = 10;

const svgOf = (name, view) => readFileSync(new URL(`${name}.base.${view}.svg`, DIST), 'utf8');
// the rings of a part as the page reads them off its front drawing: across the rack from the centre
// line, with the opening and the band the contract states
function ringsOf(name) {
  const W = devices[name].w, out = [];
  const re = /<g id="(guide-\d+)"[^>]*data-guide="ring"[^>]*data-guide-aperture="([\d. ]+)"[^>]*data-guide-depth="([\d.]+)"[^>]*transform="translate\(([-\d.]+),([-\d.]+)\)"/g;
  for (const m of svgOf(name, 'front').matchAll(re)) {
    const [w, h] = m[2].split(' ').map(Number), depth = Number(m[3]);
    out.push({via: m[1], kind: 'ring', face: 'front', x: Number(m[4]) + depth / 2 - W / 2, y: Number(m[5]), aperture: {w, h}, depth});
  }
  return out;
}
function ductsOf(name) {
  return [...svgOf(name, 'front').matchAll(/<rect id="guide--([\w-]+)" data-class="guide" data-guide="duct"/g)]
    .map(m => ({via: m[1], kind: 'duct', face: 'front', x: 0}));
}

const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'base', ru, label: extra.label ?? ref, ...extra}).rack;
// a switch at U10 (i1), the manager at U12 (i2), a panel at U20 (i3)
const rackOf = name => add(add(add(M.newRack(), 'sw', 10), name, 12), 'pp', 20);
const ctxFor = (name, guides, ports = {}) => ({chassisOf, bendOf: () => 1e12,
  guidesOf: id => (id === 'i2' ? guides : []), portX: end => ports[end.item] ?? 0, portY: () => null});
const cable = route => ({id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'q', view: 'front'},
  route, routeEdited: true});

test('every part is in the build as a rack-face sheet part', {skip}, () => {
  for (const name of [...Object.keys(RINGED), ...DUCTED]) {
    const d = devices[name];
    assert.ok(d, `${name} is in rack.json`);
    assert.equal(d.manufacturer, 'Belden');
    assert.deepEqual([d.mount, d.shell, d.w], ['rack-face', 'sheet', 482.6], name);
  }
});

for (const [name, count] of Object.entries(RINGED)) {
  test(`${name}: ${count} rings, each a ring guide with the estimated opening, evenly across the panel`, {skip}, () => {
    const rings = ringsOf(name);
    assert.deepEqual(rings.map(g => g.via), Array.from({length: count}, (_, i) => `guide-${i + 1}`));
    assert.deepEqual(devices[name].guides.front, rings.map(g => g.via));
    for (const g of rings) {
      assert.deepEqual([g.aperture.w, g.aperture.h], APERTURE);
      assert.equal(g.depth, BAND);
    }
    // six columns 80 mm apart (the 9510-1901's six rings 78 apart), symmetric about the middle
    const columns = [...new Set(rings.map(g => Math.round(g.x * 10) / 10))].sort((a, b) => a - b);
    const pitch = name === '9510-1901' ? 78 : 80;
    assert.equal(columns.length, 6);
    columns.slice(1).forEach((x, k) => assert.ok(Math.abs(x - columns[k] - pitch) < 0.11, `${name}: ${x} - ${columns[k]}`));
    assert.ok(Math.abs(columns[0] + columns[5]) < 0.11, 'symmetric about the middle');
  });

  test(`${name}: a cable laid in the kit runs through each ring, in at one face and out at the other, along the run`, {skip}, () => {
    const rings = ringsOf(name), r = rackOf(name);
    for (const g of rings) {
      // the cable's ports stand on the side of the ring they come from
      const ctx = ctxFor(name, rings, {i1: g.x - 80, i3: g.x - 80});
      const path = R.routePath(r, cable([{item: 'i2', via: g.via}]), ctx);
      assert.equal(path.rings.length, 1, `${name} ${g.via}: one ring passed`);
      const [pass] = path.rings;
      assert.equal(pass.depth, BAND, 'the ring states its band: the part\'s, not the 10 mm estimate');
      assert.equal(pass.estimated, false);
      assert.ok(pass.sense === 1 || pass.sense === -1);
      const entry = path.points.find(p => p.at === 'entry'), exit = path.points.find(p => p.at === 'exit');
      assert.ok(entry && exit, 'an entry and an exit point');
      assert.ok(Math.abs(Math.abs(entry.x - exit.x) - BAND) < 1e-9, 'the cable is one band from entry to exit');
      assert.deepEqual([entry.y, entry.z], [exit.y, exit.z], 'straight along x inside the ring');
      // a rack-face part stands out from its rail plane by half its depth, and its ring is there
      assert.ok(Math.abs(entry.z - devices[name].d / 2) < 1e-6, `${name}: the ring stands half the part's depth out`);
      assert.deepEqual(path.findings, [], `${name} ${g.via}: nothing in the way`);
    }
  });

  test(`${name}: a cable through a ring counts in that ring's fill, against the estimated opening`, {skip}, () => {
    const rings = ringsOf(name), r = rackOf(name), g = rings[2];
    const ctx = ctxFor(name, rings, {i1: g.x - 80, i3: g.x - 80});
    const c = cable([{item: 'i2', via: g.via}]);
    const fill = R.fill({...r, cables: [c]}, ctx).find(f => f.via === g.via);
    assert.ok(fill, 'the ring is in the fill');
    assert.equal(fill.count, 1);
    assert.ok(fill.percent > 0 && fill.percent < 100);
  });

  test(`${name}: the rings in one row take one cable straight through them all`, {skip}, () => {
    // the rings that share a height (a panel's whole row; the four across a 9511's middle) are collinear
    const rings = ringsOf(name), r = rackOf(name);
    const y0 = rings[2].y, row = rings.filter(g => g.y === y0).sort((a, b) => b.x - a.x);
    assert.ok(row.length >= 4, `${name}: a row of ${row.length}`);
    // from a port right of the row to one left of it, so the cable never turns back at a ring
    const ctx = ctxFor(name, rings, {i1: row[0].x + 100, i3: row.at(-1).x - 100});
    const path = R.routePath(r, cable(row.map(g => ({item: 'i2', via: g.via}))), ctx);
    const inside = path.points.filter(p => p.at === 'entry' || p.at === 'exit');
    assert.equal(inside.length, 2 * row.length);
    assert.ok(inside.every(p => p.y === inside[0].y && p.z === inside[0].z), 'one line, the same y and z all the way');
    const xs = inside.map(p => p.x);
    assert.ok(xs.every((x, k) => k === 0 || x < xs[k - 1]), 'never turns back');
    assert.deepEqual(path.findings, []);
  });
}

for (const name of DUCTED) {
  test(`${name}: the catalogue lists its duct, and a cable runs along it`, {skip}, async () => {
    const ducts = ductsOf(name);
    assert.deepEqual(ducts.map(d => d.via), ['duct']);
    assert.deepEqual(Object.values(devices[name].guides).flat(), ['duct']);
    const r = rackOf(name), ctx = ctxFor(name, ducts);
    const c = cable([{item: 'i2', via: 'duct'}]);
    const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
    assert.deepEqual(resolved.waypoints, [{item: 'i2', via: 'duct'}], 'the route keeps the duct');
    const len = R.routedLength({...r, cables: [c]}, c, ctx);
    assert.ok(len.measured > 0, 'the cable has a length');
    const path = R.routePath({...r, cables: [c]}, c, ctx);
    assert.ok(path.points.some(p => p.at === 'pathway'), 'the cable passes the duct');
    assert.deepEqual(path.findings, []);
    const hm = await inspect(r, 'i2', {chassisOf});
    const found = hm.pathways.filter(p => p.kind === 'duct');
    assert.deepEqual(found.map(p => p.via), ['duct']);
    assert.ok(found.every(p => p.holds_spare), 'a duct holds spare cable');
  });
}

test('no Belden part states a cable capacity, so none is compared', {skip}, () => {
  for (const name of [...Object.keys(RINGED), ...DUCTED]) assert.equal(devices[name].capacity ?? null, null, name);
});
