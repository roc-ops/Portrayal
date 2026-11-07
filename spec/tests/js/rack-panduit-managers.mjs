// spec/tests/js/rack-panduit-managers.mjs
// PANDUIT'S MANAGERS IN THE RACK KIT (#1092): what the NetManager, PatchRunner 2 and NetRunner
// parts advertise works in the kit, not only in the drawing. A cable is laid through a ring of the
// NetManager High Capacity NM1 and NM2, along the duct of each horizontal manager and of each
// vertical one beside the rack, and through a pass-through of each. Everything reads the build, as the
// Rack Builder does: rack.json for each part's catalogue entry, and the compiled front and rear
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
const stub = {sw: {ru: 1, w: 440, h: 44, d: 515}, pp24: {ru: 1, w: 440, h: 44, d: 100}};
const chassisOf = ref => devices[ref] ?? stub[ref] ?? null;

const RINGED = ['nm1', 'nm2'];
const APERTURE = {nm1: [24, 110], nm2: [68, 105]};
const HORIZONTAL = {
  nmf1: ['duct'], nmf2: ['duct'], nmf3: ['duct'], nmf4: ['duct'], nm1: ['duct'], nm2: ['duct'],
  ncmh2: ['duct', 'rear-duct'], ncmhf2: ['duct'], pr2hf3wh: ['duct'], pr2hf4wh: ['duct'],
};
const VERTICAL = {pr2vsd06: ['duct', 'rear-duct'], pr2vd08: ['duct', 'rear-duct'], pr2vd10: ['duct', 'rear-duct'], wmpvhc45e: ['duct', 'rear-duct']};
const PASSES = {nmf1: 2, nmf2: 2, nmf3: 2, nmf4: 2, nm1: 2, nm2: 2, ncmh2: 2, ncmhf2: 2, pr2hf3wh: 2, pr2hf4wh: 2,
  pr2vsd06: 4, pr2vd08: 4, pr2vd10: 4, wmpvhc45e: 8};

const svgOf = (name, view) => readFileSync(new URL(`${name}.base.${view}.svg`, DIST), 'utf8');
// the rings of a manager as the page reads them off its rear drawing: across the rack from the
// centre line, with the opening and the band the contract states
function ringsOf(name) {
  const W = devices[name].w, out = [];
  const re = /<g id="(guide-\d+)"[^>]*data-guide="ring"[^>]*data-guide-aperture="([\d. ]+)"[^>]*data-guide-depth="([\d.]+)"[^>]*transform="translate\(([-\d.]+),([-\d.]+)\)"/g;
  for (const m of svgOf(name, 'rear').matchAll(re)) {
    const [w, h] = m[2].split(' ').map(Number), depth = Number(m[3]);
    out.push({via: m[1], kind: 'ring', face: 'rear', x: Number(m[4]) + depth / 2 - W / 2, aperture: {w, h}});
  }
  return out;
}
function ductsOf(name, ids) {
  const out = [];
  for (const [view, face] of [['front', 'front'], ['rear', 'rear']]) {
    for (const m of svgOf(name, view).matchAll(/<rect id="guide--([\w-]+)" data-class="guide" data-guide="duct"/g)) {
      if (ids.includes(m[1])) out.push({via: m[1], kind: 'duct', face, x: 0, run: name in VERTICAL ? 'y' : 'x'});
    }
  }
  return out;
}

const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'base', ru, label: extra.label ?? ref, ...extra}).rack;
// a switch at U10 (i1), the manager at U12 (i2), a 24-port patch panel at U20 (i3)
const rackOf = name => add(add(add(M.newRack(), 'sw', 10), name, 12), 'pp24', 20);
const ctxFor = (name, guides, ports = {}) => ({chassisOf, bendOf: () => 1e12, guidesOf: id => (id === 'i2' ? guides : []),
  portX: end => ports[end.item] ?? 0, portY: () => null});
const cable = route => ({id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'q', view: 'front'},
  route, routeEdited: true});

for (const name of RINGED) {
  test(`${name}: five rear rings, each a ring guide with the stated opening, 107 mm apart, the middle one on the centre line`, {skip}, () => {
    const rings = ringsOf(name);
    assert.deepEqual(rings.map(g => g.via), ['guide-1', 'guide-2', 'guide-3', 'guide-4', 'guide-5']);
    assert.deepEqual(devices[name].guides.rear, rings.map(g => g.via));
    for (const g of rings) assert.deepEqual([g.aperture.w, g.aperture.h], APERTURE[name]);
    assert.deepEqual(rings.map(g => Math.round(g.x * 10) / 10), [-214, -107, 0, 107, 214]);
    for (const g of rings) assert.equal(devices[name].rings[g.via].depth, 15);
  });

  test(`${name}: a cable laid in the kit runs through a rear ring, in at one face and out at the other, along the run`, {skip}, () => {
    const rings = ringsOf(name), r = rackOf(name);
    for (const g of rings) {
      // the cable's ports stand on the side of the ring they come from
      const ctx = ctxFor(name, rings, {i1: g.x - 80, i3: g.x - 80});
      const path = R.routePath(r, cable([{item: 'i2', via: g.via}]), ctx);
      assert.equal(path.rings.length, 1, `${name} ${g.via}: one ring passed`);
      const [pass] = path.rings;
      assert.equal(pass.depth, 15, 'the ring states its band: the part\'s, not the 10 mm estimate');
      assert.equal(pass.estimated, false);
      assert.ok(pass.sense === 1 || pass.sense === -1);
      const entry = path.points.find(p => p.at === 'entry'), exit = path.points.find(p => p.at === 'exit');
      assert.ok(entry && exit, 'an entry and an exit point');
      assert.ok(Math.abs(Math.abs(entry.x - exit.x) - 15) < 1e-9, 'the cable is 15 mm from entry to exit');
      assert.deepEqual([entry.y, entry.z], [exit.y, exit.z], 'straight along x inside the ring');
    }
  });

  test(`${name}: a cable through a rear ring counts in that ring's fill, against the stated opening`, {skip}, () => {
    const rings = ringsOf(name), r = rackOf(name), g = rings[2];
    const ctx = ctxFor(name, rings, {i1: g.x - 80, i3: g.x - 80});
    const c = cable([{item: 'i2', via: g.via}]);
    const fill = R.fill({...r, cables: [c]}, ctx).find(f => f.via === g.via);
    assert.ok(fill, 'the ring is in the fill');
    assert.equal(fill.count, 1);
    assert.ok(fill.percent > 0 && fill.percent < 100);
  });
}

for (const [name, ids] of Object.entries(HORIZONTAL)) {
  test(`${name}: the catalogue lists its duct${ids.length > 1 ? 's' : ''}, and a cable runs along each`, {skip}, async () => {
    const ducts = ductsOf(name, ids);
    assert.deepEqual(ducts.map(d => d.via).sort(), [...ids].sort());
    assert.ok(ids.every(i => Object.values(devices[name].guides).flat().includes(i)));
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

for (const [name, n] of Object.entries(PASSES)) {
  if (name in VERTICAL) continue;
  test(`${name}: a cable crosses through a pass-through, the ${n} windows its drawing shows`, {skip}, async () => {
    const ids = Array.from({length: n}, (_, k) => `pass-through-${k + 1}`);
    assert.deepEqual(devices[name].passes.front, ids);
    const r = rackOf(name), ducts = ductsOf(name, HORIZONTAL[name]);
    // the page hands the kit a pass-through as a guide of kind `pass`; the catalogue (rack.json)
    // already lists these windows as pathways a route may name
    const guides = [...ducts, ...ids.map(via => ({via, kind: 'pass', face: 'front', x: 0}))];
    for (const via of ids) {
      const c = cable([{item: 'i2', via}]);
      const ctx = ctxFor(name, guides);
      const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
      assert.deepEqual(resolved.waypoints, [{item: 'i2', via}], `${via} is a way for a cable`);
      assert.deepEqual(resolved.gone ?? [], []);
      assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0);
    }
    const hm = await inspect(r, 'i2', {chassisOf});
    assert.deepEqual(hm.pathways.filter(p => p.kind === 'pass').map(p => [p.via, p.holds_spare]), ids.map(v => [v, false]));
  });
}

// ── the verticals stand beside the rack: a zero-U part, its duct a lane a cable runs down ──────────────
const zrack = name => ({...add(add(M.newRack(), 'sw', 30), 'sw', 26), zeroU: [{id: 'z1', ref: name, cfg: 'base', label: 'vcm-1', at: 'right-front', offsetMm: 0}]});
for (const [name, ids] of Object.entries(VERTICAL)) {
  test(`${name}: a vertical manager beside the rack lists its ducts, holds a cable down its lane and states its holes`, {skip}, async () => {
    assert.equal(devices[name].mount, 'rack-side');
    assert.deepEqual(Object.values(devices[name].guides).flat().sort(), [...ids].sort());
    const n = PASSES[name];
    assert.deepEqual(devices[name].passes.front, Array.from({length: n}, (_, k) => `pass-through-${k + 1}`));
    const r = zrack(name);
    const hm = await inspect(r, 'z1', {chassisOf});
    assert.deepEqual(hm.pathways.filter(p => p.kind === 'duct').map(p => p.via).sort(), [...ids].sort());
    assert.ok(hm.pathways.filter(p => p.kind === 'duct').every(p => p.holds_spare));
    assert.deepEqual(hm.pathways.filter(p => p.kind === 'pass').map(p => p.via), Array.from({length: n}, (_, k) => `pass-through-${k + 1}`));
  });

  test(`${name}: a cable runs down the front and the rear duct beside the rack, and across a hole to the other`, {skip}, () => {
    const r = zrack(name);
    const guides = ids.map(via => ({via, kind: 'duct', face: via.startsWith('rear') ? 'rear' : 'front', x: 0, run: 'y'}));
    const holes = Array.from({length: PASSES[name]}, (_, k) => ({via: `pass-through-${k + 1}`, kind: 'pass', face: 'front', x: 0}));
    const ctx = {chassisOf, bendOf: () => 1e12, guidesOf: id => (id === 'z1' ? [...guides, ...holes] : []), portX: () => 0, portY: () => null};
    const lane = {id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i2', path: 'q', view: 'front'}};
    for (const via of [...ids, 'pass-through-1']) {
      const c = {...lane, route: [{item: 'z1', via}], routeEdited: true};
      const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
      // a part beside the rack carries a lane (zero-u.js): its duct is the lane its cable runs down, at the
      // units of the ports it joins, and a window of it is a way across that lane
      assert.ok(resolved.waypoints.length > 0 && resolved.waypoints.every(w => w.lane === 'right-front'), `${via} is a way down the lane`);
      assert.deepEqual(resolved.gone ?? [], []);
      assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0, `${via}: the cable has a length`);
    }
  });
}

test('every Panduit part states its count, to be shown, and the cat6 ones to be compared', {skip}, () => {
  for (const name of [...Object.keys(HORIZONTAL), ...Object.keys(VERTICAL)]) {
    if (name === 'pr2vsd06') { assert.equal(devices[name].capacity, undefined); continue; }
    const cap = devices[name].capacity;
    assert.ok(cap.count > 0 && cap.estimated === undefined, name);
    assert.match(cap.basis, /Panduit/);
    assert.ok(cap.media === 'cat6' || cap.media === null, name);
  }
});
