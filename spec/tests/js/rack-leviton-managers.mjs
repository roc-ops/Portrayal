// spec/tests/js/rack-leviton-managers.mjs
// LEVITON'S HORIZONTAL MANAGERS IN THE RACK KIT (#1100): what the five 49253 five-ring
// managers and the three VERSI-DUCT slotted ducts advertise works in the kit, not only in the
// drawing. A cable is laid through a ring of each manager, along the duct of each duct, and
// through a pass-through where the drawing has one. Everything reads the build, as the Rack
// Builder does: rack.json for each part's catalogue entry, and the compiled front and rear
// drawings for where its rings and ducts stand across the rack.
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

const RINGED = ['49253-lpm', '49253-bcm', '49253-2cm', '49253-6pm', '49253-6mr'];
const DUCTED = {'491ru-hfr': ['front-duct', 'rear-duct'], '492ru-hfr': ['front-duct', 'rear-duct'], '492ru-hfo': ['duct']};
const PASSES = ['top-pass-1', 'top-pass-2', 'top-pass-3', 'top-pass-4'];
const APERTURE = {'49253-lpm': [31.75, 82.55], '49253-bcm': [69.85, 82.55], '49253-2cm': [69.85, 31.75],
  '49253-6pm': [31.75, 133.35], '49253-6mr': [69.85, 133.35]};

const svgOf = (name, view) => readFileSync(new URL(`${name}.base.${view}.svg`, DIST), 'utf8');
// the rings of a manager as the page reads them off its front drawing: across the rack from the
// centre line, with the opening and the band the contract states
function ringsOf(name) {
  const W = devices[name].w, out = [];
  const re = /<g id="(guide-\d+)"[^>]*data-guide="ring"[^>]*data-guide-aperture="([\d. ]+)"[^>]*data-guide-depth="([\d.]+)"[^>]*transform="translate\(([-\d.]+),([-\d.]+)\)"/g;
  for (const m of svgOf(name, 'front').matchAll(re)) {
    const [w, h] = m[2].split(' ').map(Number), depth = Number(m[3]);
    out.push({via: m[1], kind: 'ring', face: 'front', x: Number(m[4]) + depth / 2 - W / 2, aperture: {w, h}});
  }
  return out;
}
function ductsOf(name) {
  const out = [];
  for (const [view, face] of [['front', 'front'], ['rear', 'rear']]) {
    if (view === 'rear' && DUCTED[name].length < 2) continue;
    for (const m of svgOf(name, view).matchAll(/<rect id="guide--([\w-]+)" data-class="guide" data-guide="duct"/g)) out.push({via: m[1], kind: 'duct', face, x: 0});
  }
  return out;
}

const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'base', ru, label: extra.label ?? ref, ...extra}).rack;
// a switch at U10 (i1), the manager at U12 (i2), a panel at U20 (i3)
const rackOf = name => add(add(add(M.newRack(), 'sw', 10), name, 12), 'pp', 20);
const ctxFor = (name, guides, ports = {}) => ({chassisOf, bendOf: () => 1e12, guidesOf: id => (id === 'i2' ? guides : []),
  portX: end => ports[end.item] ?? 0, portY: () => null});
const cable = route => ({id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'q', view: 'front'},
  route, routeEdited: true});

for (const name of RINGED) {
  test(`${name}: five rings, each a ring guide with the drawn opening, standing at the middle of its loop`, {skip}, () => {
    const rings = ringsOf(name);
    assert.deepEqual(rings.map(g => g.via), ['guide-1', 'guide-2', 'guide-3', 'guide-4', 'guide-5']);
    assert.deepEqual(devices[name].guides.front, rings.map(g => g.via));
    for (const g of rings) assert.deepEqual([g.aperture.w, g.aperture.h], APERTURE[name]);
    // 107.6 mm apart, the middle on the centre line
    assert.deepEqual(rings.map(g => Math.round(g.x * 10) / 10), [-215.2, -107.6, 0, 107.6, 215.2]);
    // the plan gives each ring's depth and where it stands behind the front of the part
    const ear = devices[name].ears.default.at;
    for (const g of rings) assert.deepEqual(devices[name].rings[g.via], {z: Math.round((ear - 1.5) / 2 * 10) / 10, depth: 9.5});
  });

  test(`${name}: a cable laid in the kit runs through a ring, in at one face and out at the other, along the run`, {skip}, () => {
    const rings = ringsOf(name), r = rackOf(name);
    for (const g of rings) {
      // the cable's ports stand on the side of the ring they come from
      const ctx = ctxFor(name, rings, {i1: g.x - 80, i3: g.x - 80});
      const path = R.routePath(r, cable([{item: 'i2', via: g.via}]), ctx);
      assert.equal(path.rings.length, 1, `${name} ${g.via}: one ring passed`);
      const [pass] = path.rings;
      assert.equal(pass.depth, 9.5, 'the ring states its band: the part\'s, not the 10 mm estimate');
      assert.equal(pass.estimated, false);
      assert.ok(pass.sense === 1 || pass.sense === -1);
      const entry = path.points.find(p => p.at === 'entry'), exit = path.points.find(p => p.at === 'exit');
      assert.ok(entry && exit, 'an entry and an exit point');
      assert.ok(Math.abs(Math.abs(entry.x - exit.x) - 9.5) < 1e-9, 'the cable is 9.5 mm from entry to exit');
      assert.deepEqual([entry.y, entry.z], [exit.y, exit.z], 'straight along x inside the ring');
      // where the part says it stands: its front is `at` in front of the rail, the ring `z` behind that
      const ring = devices[name].rings[g.via];
      assert.ok(Math.abs(entry.z - (devices[name].ears.default.at - ring.z)) < 1e-6, `${name}: the ring is where the plan puts it`);
    }
  });

  test(`${name}: a cable through a ring counts in that ring's fill, against the drawn opening`, {skip}, () => {
    const rings = ringsOf(name), r = rackOf(name), g = rings[2];
    const ctx = ctxFor(name, rings, {i1: g.x - 80, i3: g.x - 80});
    const c = cable([{item: 'i2', via: g.via}]);
    const r1 = {...r, cables: [c]};
    const fill = R.fill(r1, ctx).find(f => f.via === g.via);
    assert.ok(fill, 'the ring is in the fill');
    assert.equal(fill.count, 1);
    assert.ok(fill.percent > 0 && fill.percent < 100);
  });
}

for (const [name, ids] of Object.entries(DUCTED)) {
  test(`${name}: the catalogue lists its duct${ids.length > 1 ? 's' : ''}, and a cable runs along each`, {skip}, async () => {
    const ducts = ductsOf(name);
    assert.deepEqual(ducts.map(d => d.via), ids);
    assert.deepEqual(Object.values(devices[name].guides).flat(), ids);
    const r = rackOf(name);
    for (const d of ducts) {
      const ctx = ctxFor(name, ducts);
      const c = cable([{item: 'i2', via: d.via}]);
      const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
      assert.deepEqual(resolved.waypoints, [{item: 'i2', via: d.via}], `${d.via}: the route keeps the duct`);
      const len = R.routedLength({...r, cables: [c]}, c, ctx);
      assert.ok(len.measured > 0, `${d.via}: the cable has a length`);
    }
    const hm = await inspect(r, 'i2', {chassisOf});
    const found = hm.pathways.filter(p => p.kind === 'duct');
    assert.deepEqual(found.map(p => p.via).sort(), [...ids].sort());
    assert.ok(found.every(p => p.holds_spare), 'a duct holds spare cable');
  });
}

for (const name of ['491ru-hfr', '492ru-hfr']) {
  test(`${name}: a cable crosses through a pass-through, where the drawing has one`, {skip}, async () => {
    assert.deepEqual(devices[name].passes.top, PASSES);
    const r = rackOf(name), ducts = ductsOf(name);
    // the page hands the kit a pass-through as a guide of kind `pass`; the catalogue (rack.json)
    // already lists these four, drawn in the top view, as pathways a route may name
    const guides = [...ducts, ...PASSES.map(via => ({via, kind: 'pass', face: 'front', x: 0}))];
    for (const via of PASSES) {
      const c = cable([{item: 'i2', via}]);
      const ctx = ctxFor(name, guides);
      const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
      assert.deepEqual(resolved.waypoints, [{item: 'i2', via}], `${via} is a way for a cable`);
      assert.deepEqual(resolved.gone ?? [], []);
      assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0);
    }
    const hm = await inspect(r, 'i2', {chassisOf});
    assert.deepEqual(hm.pathways.filter(p => p.kind === 'pass').map(p => [p.via, p.holds_spare]), PASSES.map(v => [v, false]));
  });
}

test('492ru-hfo: the front-only duct has no pass-through to cross', {skip}, () => {
  assert.equal(devices['492ru-hfo'].passes, undefined);
});

test('every Leviton part states its count, to be shown and never compared (the note names no kind)', {skip}, () => {
  for (const name of [...RINGED, ...Object.keys(DUCTED)]) {
    const cap = devices[name].capacity;
    assert.ok(cap.count > 0 && cap.media === null && cap.estimated === undefined, name);
    assert.match(cap.basis, /NS-AN-23-006-05-30-23/);
  }
});
