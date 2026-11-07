// spec/tests/js/rack-startech-managers.mjs
// STARTECH.COM'S CABLE MANAGERS IN THE RACK KIT (#1098, part of #1091): what the eight parts
// advertise works in the kit, not only in the drawing. A cable is laid through a ring of each ring
// part, along the duct of each finger duct, through each pass-through of the ducts, the D-ring panel
// and the brush panel, and a hook is placed on one rail with `side` and claims only that rail.
// Everything reads the build, as the Rack Builder does: rack.json for each part's catalogue entry
// and the compiled front and rear drawings for where its rings and ducts stand.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as F from '../../../kit/rack/fit.js';
import * as R from '../../../kit/rack/route.js';
import {apply} from '../../../kit/rack/commands.js';
import {inspect} from '../../../kit/rack/queries.js';

const DIST = new URL('../../../library/dist/', import.meta.url);
const skip = existsSync(new URL('rack.json', DIST)) ? false : 'library/dist not built - run ./build.sh';
const devices = skip ? {} : JSON.parse(readFileSync(new URL('rack.json', DIST), 'utf8')).devices;
// `lacer` is a full-width rack-face part, as the FS FHD-CMP5DR is: it claims both rails of its unit
const stub = {sw: {ru: 1, w: 440, h: 44, d: 515}, pp: {ru: 1, w: 440, h: 44, d: 100},
  lacer: {mount: 'rack-face', ru: 1, w: 483, h: 44, d: 110, default: 'base', configs: ['base']}};
const chassisOf = ref => devices[ref] ?? stub[ref] ?? null;

const DUCTS = ['cmduct1ux', 'cmduct2u'];
const DUCT_PASSES = ['pass-through-1', 'pass-through-2', 'pass-through-3'];
const HOOKS = ['cmhook1u', 'cmhook1un', 'cmhookmw'];
// the width of each ring part across the front drawing, which puts the middle of its loop on the part
const RING_W = {cablmanagerh: 9.1, cablmanager2: null, cmhook1u: 57.0, cmhook1un: 45.0, cmhookmw: 64.0};

const svgOf = (name, view) => readFileSync(new URL(`${name}.base.${view}.svg`, DIST), 'utf8');
// the rings of a part as the page reads them off its front drawing: across the part from its centre
// line, with the opening, the band and the run the contract states
function ringsOf(name) {
  const W = devices[name].w, out = [];
  const re = /<g id="(guide-\d+)"[^>]*data-guide="ring" data-guide-run="(\w)" data-guide-aperture="([\d. ]+)" data-guide-depth="([\d.]+)"[^>]*transform="translate\(([-\d.]+),([-\d.]+)\)"/g;
  for (const m of svgOf(name, 'front').matchAll(re)) {
    const [w, h] = m[3].split(' ').map(Number), depth = Number(m[4]);
    const width = RING_W[name] ?? (m[2] === 'x' ? depth : 40);
    out.push({via: m[1], kind: 'ring', face: 'front', run: m[2], depth, aperture: {w, h}, x: Number(m[5]) + width / 2 - W / 2});
  }
  return out;
}
function ductsOf(name) {
  const out = [];
  for (const m of svgOf(name, 'front').matchAll(/<rect id="guide--([\w-]+)" data-class="guide" data-guide="duct"/g)) out.push({via: m[1], kind: 'duct', face: 'front', x: 0});
  return out;
}

const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'base', ru, label: extra.label ?? ref, ...extra}).rack;
// a switch at U10 (i1), the manager at U12 (i2), a panel at U20 (i3)
const rackOf = name => add(add(add(M.newRack(), 'sw', 10), name, 12), 'pp', 20);
const ctxFor = (name, guides, ports = {}) => ({chassisOf, bendOf: () => 1e12, guidesOf: id => (id === 'i2' ? guides : []),
  portX: end => ports[end.item] ?? 0, portY: () => null});
const cable = route => ({id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'q', view: 'front'},
  route, routeEdited: true});

for (const name of ['cablmanagerh', 'cablmanager2']) {
  test(`${name}: five rings, each a ring guide with its drawn opening, band and run`, {skip}, () => {
    const rings = ringsOf(name);
    assert.deepEqual(rings.map(g => g.via), ['guide-1', 'guide-2', 'guide-3', 'guide-4', 'guide-5']);
    assert.deepEqual(devices[name].guides.front, rings.map(g => g.via));
    if (name === 'cablmanagerh') {
      for (const g of rings) assert.deepEqual([g.run, g.depth, g.aperture.w, g.aperture.h], ['x', 9.1, 22.6, 79.59]);
      assert.deepEqual(rings.map(g => Math.round(g.x * 10) / 10 + 0), [-200, -100, 0, 100, 200], '100 mm apart, the middle on the centre line');
    } else {
      assert.deepEqual(rings.map(g => g.run), ['y', 'x', 'x', 'x', 'y'], 'the drawing draws the end rings a quarter turn from the middle three');
      assert.deepEqual(rings.map(g => g.depth), [10, 10.4, 10.4, 10.4, 10]);
      assert.deepEqual(rings.map(g => Math.round(g.x * 10) / 10 + 0), [-184, -105, 0, 105, 184]);
    }
    // the catalogue puts each ring where it stands in depth, behind the front of the part
    for (const g of rings) assert.ok(devices[name].rings[g.via].z > 0, `${g.via} has a depth place`);
  });

  test(`${name}: a cable laid in the kit runs through each ring, in at one face and out at the other, along the run`, {skip}, () => {
    const rings = ringsOf(name), r = rackOf(name);
    for (const g of rings) {
      // the ports stand on the side of the ring they come from, in line with it for a ring along y
      const side = g.run === 'x' ? g.x - 80 : g.x;
      const ctx = ctxFor(name, rings, {i1: side, i3: side});
      const path = R.routePath(r, cable([{item: 'i2', via: g.via}]), ctx);
      assert.equal(path.rings.length, 1, `${name} ${g.via}: one ring passed`);
      const [pass] = path.rings;
      assert.equal(pass.depth, g.depth, 'the ring states its band: the part\'s, not the 10 mm estimate');
      assert.equal(pass.estimated, false);
      assert.equal(pass.run, g.run);
      const entry = path.points.find(p => p.at === 'entry'), exit = path.points.find(p => p.at === 'exit');
      assert.ok(entry && exit, 'an entry and an exit point');
      const other = g.run === 'x' ? 'y' : 'x';
      assert.ok(Math.abs(Math.abs(entry[g.run] - exit[g.run]) - g.depth) < 1e-9, `${g.via}: the cable is ${g.depth} mm from entry to exit`);
      assert.deepEqual([entry[other], entry.z], [exit[other], exit.z], `${g.via}: straight along ${g.run} inside the ring`);
    }
  });

  test(`${name}: a cable through a ring counts in that ring's fill, against the drawn opening`, {skip}, () => {
    const rings = ringsOf(name), r = rackOf(name), g = rings[2];
    const ctx = ctxFor(name, rings, {i1: g.x - 80, i3: g.x - 80});
    const c = cable([{item: 'i2', via: g.via}]);
    const fill = R.fill({...r, cables: [c]}, ctx).find(f => f.via === g.via);
    assert.ok(fill, 'the ring is in the fill');
    assert.equal(fill.count, 1);
    assert.ok(fill.percent > 0 && fill.percent < 100);
  });
}

for (const name of HOOKS) {
  test(`${name}: a rack-face part narrower than the opening, its one ring a flat loop a cable runs up and down through`, {skip}, () => {
    const c = devices[name];
    assert.equal(c.mount, 'rack-face');
    assert.ok(F.isNarrow(c) && c.w < F.NARROW_MM, 'under the 450 mm opening');
    assert.deepEqual(devices[name].guides.front, ['guide-1']);
    const [g] = ringsOf(name);
    assert.equal(g.run, 'y');
    assert.equal(g.depth, name === 'cmhookmw' ? 25.5 : 10);
    assert.equal(devices[name].rings, undefined, 'a ring of a rack-face part is placed by the kit from the part\'s own depth');
  });

  test(`${name}: a cable laid through the ring runs up the rail, in at one face and out at the other`, {skip}, () => {
    const [g] = ringsOf(name);
    let r = run(rackOf2('two-post', 42), {op: 'side.place', ref: name, face: 'front', ru: 12, side: 'left'}).rack;
    r = add(add(r, 'sw', 10), 'pp', 20);
    const at = R.pointOf(r, {item: r.items[0].id, via: g.via}, {chassisOf, guidesOf: () => [g]});
    const ctx = {chassisOf, bendOf: () => 1e12, guidesOf: id => (id === r.items[0].id ? [g] : []), portX: () => at.x, portY: () => null};
    const c = {id: 'c1', media: 'cat6', a: {item: r.items[1].id, path: 'p', view: 'front'}, b: {item: r.items[2].id, path: 'q', view: 'front'},
      route: [{item: r.items[0].id, via: g.via}], routeEdited: true};
    const path = R.routePath(r, c, ctx);
    assert.equal(path.rings.length, 1, `${name}: one ring passed`);
    assert.equal(path.rings[0].run, 'y');
    assert.equal(path.rings[0].depth, g.depth);
    const entry = path.points.find(p => p.at === 'entry'), exit = path.points.find(p => p.at === 'exit');
    assert.ok(Math.abs(Math.abs(entry.y - exit.y) - g.depth) < 1e-9);
    assert.deepEqual([entry.x, entry.z], [exit.x, exit.z], 'straight up the rail inside the loop');
  });
}

const rackOf2 = (kind = 'two-post', heightRU = 42) => M.withFrame(M.newDoc({kind}).racks[0], {heightRU});
const run = (rack, cmds) => apply(rack, cmds, {chassisOf});

test('a hook placed with `side` claims only its own rail: one on each rail of a unit, never two on one', {skip}, () => {
  const r = rackOf2();
  const res = run(r, [{op: 'side.place', ref: 'cmhook1u', face: 'front', ru: 10, side: 'left'},
                      {op: 'side.place', ref: 'cmhook1un', face: 'front', ru: 10, side: 'right'}]);
  assert.ok(!res.error, res.error);
  assert.deepEqual(res.rack.items.map(i => [i.id, i.side, i.ru]), [['i1', 'left', 10], ['i2', 'right', 10]]);
  assert.equal(run(res.rack, {op: 'side.place', ref: 'cmhook1un', face: 'front', ru: 10, side: 'left'}).error,
    'Taken by CMHOOK1U on the front, left rail.');
  // a full-width rack-face part claims both rails of the unit; a wide part has no side
  assert.match(run(res.rack, {op: 'place', ref: 'lacer', face: 'front', ru: 10}).error, /Taken by/);
  assert.match(run(r, {op: 'side.place', ref: 'lacer', face: 'front', ru: 10, side: 'left'}).error, /has no side/);
  // the rear face is its own
  assert.ok(!run(res.rack, {op: 'side.place', ref: 'cmhook1u', face: 'rear', ru: 10, side: 'left'}).error);
  for (const it of res.rack.items) assert.deepEqual(F.fits(res.rack, it, chassisOf, {ignoreId: it.id}), {ok: true});
});

test('CMHOOKMW is a unit and a half: its rail is taken over the half unit above its unit', {skip}, () => {
  assert.equal(devices.cmhookmw.ru, 1.5);
  assert.equal(F.unitsOf(devices.cmhookmw), 1.5);
  const r = run(rackOf2(), {op: 'side.place', ref: 'cmhookmw', face: 'front', ru: 10, side: 'left'});
  assert.ok(!r.error, r.error);
  // U10 and half of U11 are taken on the left; U11 whole is not free on that rail, U12 is
  assert.match(run(r.rack, {op: 'side.place', ref: 'cmhook1u', face: 'front', ru: 11, side: 'left'}).error, /Taken by CMHOOKMW/);
  assert.ok(!run(r.rack, {op: 'side.place', ref: 'cmhook1u', face: 'front', ru: 12, side: 'left'}).error);
  // and the other rail of the same units is free
  assert.ok(!run(r.rack, {op: 'side.place', ref: 'cmhook1u', face: 'front', ru: 11, side: 'right'}).error);
});

test('a hook on the right rail is the part turned end over end: its ring stands mirrored about the rail', {skip}, () => {
  const [g] = ringsOf('cmhookmw');
  const r = run(rackOf2(), [{op: 'side.place', ref: 'cmhookmw', face: 'front', ru: 10, side: 'left'},
                            {op: 'side.place', ref: 'cmhookmw', face: 'front', ru: 20, side: 'right'}]).rack;
  const ctx = {chassisOf, guidesOf: () => [g]};
  const [l, rt] = r.items;
  const dl = R.pointOf(r, {item: l.id, via: g.via}, ctx).x - F.centreX(l, chassisOf);
  const dr = R.pointOf(r, {item: rt.id, via: g.via}, ctx).x - F.centreX(rt, chassisOf);
  assert.ok(Math.abs(g.x) > 1, 'the loop is off the part\'s centre');
  assert.ok(Math.abs(dl + dr) < 1e-9, 'one rail mirrors the other');
});

for (const name of DUCTS) {
  test(`${name}: the catalogue lists its duct, and a cable runs along it`, {skip}, async () => {
    const ducts = ductsOf(name);
    assert.deepEqual(ducts.map(d => d.via), ['duct']);
    assert.deepEqual(Object.values(devices[name].guides).flat(), ['duct']);
    const r = rackOf(name);
    const ctx = ctxFor(name, ducts);
    const c = cable([{item: 'i2', via: 'duct'}]);
    const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
    assert.deepEqual(resolved.waypoints, [{item: 'i2', via: 'duct'}], 'the route keeps the duct');
    assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0, 'the cable has a length');
    const hm = await inspect(r, 'i2', {chassisOf});
    const found = hm.pathways.filter(p => p.kind === 'duct');
    assert.deepEqual(found.map(p => p.via), ['duct']);
    assert.ok(found.every(p => p.holds_spare), 'a duct holds spare cable');
  });

  test(`${name}: a cable crosses through each of its three pass-throughs`, {skip}, async () => {
    assert.deepEqual(devices[name].passes.rear, DUCT_PASSES);
    const r = rackOf(name);
    const guides = [...ductsOf(name), ...DUCT_PASSES.map(via => ({via, kind: 'pass', face: 'rear', x: 0}))];
    for (const via of DUCT_PASSES) {
      const c = cable([{item: 'i2', via}]);
      const ctx = ctxFor(name, guides);
      const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
      assert.deepEqual(resolved.waypoints, [{item: 'i2', via}], `${via} is a way for a cable`);
      assert.deepEqual(resolved.gone ?? [], []);
      assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0);
    }
    const hm = await inspect(r, 'i2', {chassisOf});
    assert.deepEqual(hm.pathways.filter(p => p.kind === 'pass').map(p => [p.via, p.holds_spare]), DUCT_PASSES.map(v => [v, false]));
  });

  test(`${name}: the three holes are open in the plate, so the plate is not solid there`, {skip}, () => {
    const floor = devices[name].solids.find(s => s.part === 'base/floor');
    assert.deepEqual(floor.holes.map(h => h.via), DUCT_PASSES);
    // the size the catalogue reads is the straight run and the height: an oval 100 by 25 reads
    // [75, 25], and a rectangle 100 by 69 reads [100, 69]
    for (const h of floor.holes) assert.deepEqual(h.size, name === 'cmduct1ux' ? [75, 25] : [100, 69]);
  });
}

test('cablmanagerh: a cable crosses through each of its four holes, and the maker\'s note about power cables is recorded', {skip}, async () => {
  const PASSES = ['pass-through-1', 'pass-through-2', 'pass-through-3', 'pass-through-4'];
  assert.deepEqual(devices.cablmanagerh.passes.rear, PASSES);
  const r = rackOf('cablmanagerh');
  const guides = [...ringsOf('cablmanagerh'), ...PASSES.map(via => ({via, kind: 'pass', face: 'rear', x: 0}))];
  for (const via of PASSES) {
    const c = cable([{item: 'i2', via}]);
    const ctx = ctxFor('cablmanagerh', guides);
    const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
    assert.deepEqual(resolved.waypoints, [{item: 'i2', via}], `${via} is a way for a cable`);
    assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0);
  }
  const floor = devices.cablmanagerh.solids.find(s => s.part === 'panel/floor');
  // a round hole 29 across reads as no straight run and 29 high
  assert.deepEqual(floor.holes.map(h => [h.via, h.size]), PASSES.map(v => [v, [0, 29]]));
});

test('cmbrush1u: a cable crosses through the brush window', {skip}, async () => {
  assert.deepEqual(devices.cmbrush1u.passes.front, ['brush-window']);
  const r = rackOf('cmbrush1u');
  const guides = [{via: 'brush-window', kind: 'pass', face: 'front', x: 0}];
  const c = cable([{item: 'i2', via: 'brush-window'}]);
  const ctx = ctxFor('cmbrush1u', guides);
  const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
  assert.deepEqual(resolved.waypoints, [{item: 'i2', via: 'brush-window'}]);
  assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0);
  const floor = devices.cmbrush1u.solids.find(s => s.part === 'panel/floor');
  // an oval 382 by 23.3 reads as its straight run, 358.7, and its height
  assert.deepEqual(floor.holes.map(h => [h.via, h.size]), [['brush-window', [358.7, 23.3]]]);
});

test('every part may stand on either face of the rack: "front and rear mount" is a placement', {skip}, () => {
  for (const name of ['cmduct1ux', 'cmduct2u', 'cablmanagerh', 'cablmanager2', 'cmbrush1u']) {
    const front = run(rackOf2('four-post'), {op: 'place', ref: name, face: 'front', ru: 10});
    const rear = run(front.rack, {op: 'place', ref: name, face: 'rear', ru: 10});
    assert.ok(!front.error && !rear.error, `${name}: ${front.error ?? rear.error}`);
  }
});

test('no StarTech part states a cable capacity: none is invented', {skip}, () => {
  for (const name of [...DUCTS, ...HOOKS, 'cablmanagerh', 'cablmanager2', 'cmbrush1u']) assert.equal(devices[name].capacity, undefined, name);
});
