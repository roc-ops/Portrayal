// spec/tests/js/rack-hubbell-managers.mjs
// HUBBELL'S HORIZONTAL MANAGERS IN THE RACK KIT (P-0120, #1101, part of #1091).
// What each part advertises has to work in the kit as the build publishes it, not
// only be drawn: a cable is laid through a wire ring (M-Series), along a finger
// duct (S and SD series), and across the plate by a window (a "pass through
// hole"), with the cover on, as the part is built. Reads library/dist: rack.json
// for each part's entry and its compiled drawings for the guides, as the Rack
// Builder reads them.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';

const DIST = new URL('../../../library/dist/', import.meta.url);
const skip = existsSync(new URL('rack.json', DIST)) ? false : 'library/dist not built - run ./build.sh';
const CAT = skip ? {} : JSON.parse(readFileSync(new URL('rack.json', DIST), 'utf8')).devices;

const MSERIES = ['hm14c', 'hm24c', 'hm34c', 'hm144c'];
const FINGERED = ['hs23c', 'hsd13'];
const WINDOWED = [...MSERIES, 'hs23c'];

// a switch below and a patch panel above the manager, plain boxes
const BOXES = {sw: {ru: 1, w: 440, h: 44, d: 300}, pp: {ru: 1, w: 448, h: 44, d: 227}};
const sizes = name => ({...BOXES, [name]: CAT[name]});
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'base', ru, label: ref, ...extra}).rack;

// The guides of one part's drawing, as the page reads them: a ring's centre across the
// face from the part's own centre, its aperture, run and band; a duct's rectangle.
function guidesOf(name, view = 'front') {
  const svg = readFileSync(new URL(`${name}.base.${view}.svg`, DIST), 'utf8');
  const W = CAT[name].w, out = [];
  for (const m of svg.matchAll(/<g [^>]*data-guide="ring"[^>]*>/g)) {
    const a = k => new RegExp(`${k}="([^"]*)"`).exec(m[0])?.[1];
    const [w, h] = a('data-guide-aperture').split(' ').map(Number);
    // the part is 5.715 across: its translate is its left edge
    const tx = Number(/translate\(([-\d.]+)/.exec(a('transform'))[1]);
    out.push({via: a('id'), kind: 'ring', face: view, run: a('data-guide-run'), depth: Number(a('data-guide-depth')),
      x: tx + 5.715 / 2 - W / 2, aperture: {w, h}});
  }
  for (const m of svg.matchAll(/<rect [^>]*data-guide="duct"[^>]*>/g)) {
    const a = k => new RegExp(` ${k}="([^"]*)"`).exec(m[0])?.[1];
    out.push({via: 'duct', kind: 'duct', face: view, run: a('data-guide-run'), x: Number(a('x')) + Number(a('width')) / 2 - W / 2,
      fingerPitch: Number(a('data-guide-finger-pitch')), fingerGap: Number(a('data-guide-finger-gap'))});
  }
  return out;
}

// the switch below at U10 (i1), the manager at U11 (i2), the panel above it (i3)
function rackOf(name) {
  assert.ok(CAT[name], `${name} is not in library/dist/rack.json`);
  const ru = CAT[name].ru;
  return add(add(add(M.newRack(), 'sw', 10), name, 11), 'pp', 11 + ru);
}
function ctxOf(name, extra = {}) {
  const gs = [...guidesOf(name, 'front'), ...(MSERIES.includes(name) ? guidesOf(name, 'rear') : [])];
  return {chassisOf: ref => sizes(name)[ref] || null, bendOf: () => 1e12,
    guidesOf: id => (id === 'i2' ? gs : []),
    portX: end => extra.ports?.[end.item] ?? 100, portY: () => null, ...extra.ctx};
}
const cableOf = (name, route) => ({id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'},
  b: {item: 'i3', path: 'q', view: 'front'}, route, routeEdited: true});
const laneUp = name => [{lane: 'left-front', ru: 10}, {lane: 'left-front', ru: 11 + CAT[name].ru}];

for (const name of MSERIES) {
  test(`${name}: a cable laid through a ring runs straight along it, with nothing found`, {skip}, () => {
    // both ports stand right of the ring and the lane is left of it, so the cable goes through
    const r = rackOf(name), ctx = ctxOf(name, {ports: {i1: 100, i3: 100}});
    const c = cableOf(name, [{item: 'i2', via: 'guide-3'}, ...laneUp(name)]);
    const path = R.routePath({...r, cables: [c]}, c, ctx);
    assert.deepEqual(path.findings, []);
    assert.deepEqual(path.rings.map(g => [g.via, g.passed, g.estimated]), [['guide-3', true, false]]);
    // it enters one face and leaves the other, the wire's own 5.715 apart, level and at one depth
    const [entry, exit] = path.points.filter(p => p.at === 'entry' || p.at === 'exit');
    assert.ok(entry && exit, 'the path enters and leaves the ring');
    assert.ok(Math.abs(Math.abs(entry.x - exit.x) - 5.715) < 1e-9);
    assert.deepEqual([entry.y, entry.z], [exit.y, exit.z]);
    // the ring stands in front of the rail, half way out of the plate's 101.6 in front
    assert.ok(entry.z > 0 && entry.z < CAT[name].ears.default.at, `ring depth ${entry.z}`);
    assert.deepEqual(R.fill({...r, cables: [c]}, ctx).map(e => [e.via, e.count]), [['guide-3', 1]]);
  });

  test(`${name}: a cable runs along all five rings in a row, as the part is laid`, {skip}, () => {
    // from the right of the fifth ring, through each in turn, to the lane on the left
    const r = rackOf(name), ctx = ctxOf(name, {ports: {i1: 235, i3: 235}});
    const route = [5, 4, 3, 2, 1].map(i => ({item: 'i2', via: `guide-${i}`})).concat(laneUp(name));
    const c = cableOf(name, route);
    const path = R.routePath({...r, cables: [c]}, c, ctx);
    assert.deepEqual(path.findings, []);
    assert.equal(path.rings.filter(g => g.passed).length, 5);
    const run = path.points.filter(p => p.at === 'entry' || p.at === 'exit');
    assert.ok(run.every(p => p.y === run[0].y && p.z === run[0].z), 'one straight line through every ring');
  });

  test(`${name}: the rings behind the plate are rings a cable runs through too`, {skip}, () => {
    const r = rackOf(name), ctx = ctxOf(name);
    const c = cableOf(name, [{item: 'i2', via: 'rear-2'}, ...laneUp(name)]);
    const path = R.routePath({...r, cables: [c]}, c, ctx);
    assert.deepEqual(path.findings, []);
    assert.deepEqual(path.rings.map(g => [g.via, g.passed]), [['rear-2', true]]);
  });

  test(`${name}: the automatic route takes the manager's rings between a switch below and a panel above`, {skip}, () => {
    const r = rackOf(name), ctx = ctxOf(name);
    const route = R.autoRoute(r, {id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'},
      b: {item: 'i3', path: 'q', view: 'front'}, route: []}, ctx);
    assert.ok(route.some(w => w.item === 'i2' && /^guide-/.test(w.via)), `a ring of the manager: ${JSON.stringify(route)}`);
  });
}

for (const name of FINGERED) {
  test(`${name}: a cable runs along the duct, and its fingers are the way in`, {skip}, () => {
    const r = rackOf(name), ctx = ctxOf(name);
    const [duct] = guidesOf(name);
    assert.ok(duct && duct.fingerPitch > duct.fingerGap && duct.fingerGap > 0);
    const c = cableOf(name, [{item: 'i2', via: 'duct'}, ...laneUp(name)]);
    const path = R.routePath({...r, cables: [c]}, c, ctx);
    assert.deepEqual(path.findings, []);
    assert.deepEqual(path.crossings, []);
    assert.ok(path.points.some(p => p.at === 'pathway'), 'the path passes the duct');
    // and the automatic route takes the duct, the manager between the two
    const auto = R.autoRoute(r, {id: 'c2', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'},
      b: {item: 'i3', path: 'q', view: 'front'}, route: []}, ctx);
    assert.ok(auto.some(w => w.item === 'i2' && w.via === 'duct'), JSON.stringify(auto));
  });
}

// a leg from in front of the plate to behind it, at x, through the part's own solids
function legAt(name, x, y) {
  const r = rackOf(name), ctx = ctxOf(name);
  const mine = S.solidsOf(r, ctx).filter(s => s.item === 'i2');
  return {mine, r, cross: holes => S.legCrossings({x, y, z: 60}, {x, y, z: -60},
    holes ? mine : mine.map(s => ({...s, holes: []})), {diameter: 6.1})};
}

for (const name of WINDOWED) {
  test(`${name}: a cable crosses the plate through a window and is stopped by the plate beside it`, {skip}, () => {
    const {mine, cross} = legAt(name, 0, 0);
    // every plate of the part carries the four windows as its holes
    const plates = mine.filter(s => s.holes.length);
    assert.ok(plates.length, 'no plate of the part has a window');
    // (declared on the front and on the rear: one hole each, by its id)
    const byVia = new Map(plates[0].holes.map(h => [h.via, h.box]));
    const win = [...byVia.values()].sort((a, b) => a.x0 - b.x0);
    assert.equal(win.length, 4);
    // the middle of the second window, and a web between the second and third
    const wx = (win[1].x0 + win[1].x1) / 2, wy = (win[1].y0 + win[1].y1) / 2;
    const web = (win[1].x1 + win[2].x0) / 2;
    const through = legAt(name, wx, wy), beside = legAt(name, web, wy);
    assert.deepEqual(through.cross(true), [], 'a leg through a window crosses nothing');
    assert.ok(through.cross(false).length > 0, 'with the windows closed the plate is in the way');
    assert.ok(beside.cross(true).length > 0, 'a leg through the web between two windows meets the plate');
  });
}

// A cord from the switch below to a rear port of the panel above, laid in at x through a ring
// in front of the plate and one behind it, both at x: the cord has to cross the plate between
// them. With the windows in the plate it goes straight; with them shut it is gone round.
function crossingRack(name, x, shut) {
  const e = CAT[name], ent = shut ? {...e, solids: e.solids.map(s => ({...s, holes: []}))} : e;
  const r = rackOf(name);
  const ring = (via, face) => ({via, kind: 'ring', face, run: 'x', depth: 5.715, x, aperture: {w: 30, h: 80}});
  const ctx = {chassisOf: ref => ({...BOXES, [name]: ent})[ref] || null, bendOf: () => 1e12,
    guidesOf: id => (id === 'i2' ? [ring('front-window', 'front'), ring('rear-window', 'rear')] : []),
    portX: () => x, portY: () => null};
  const c = {id: 'c1', media: 'om4', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'q', view: 'rear'},
    route: [{item: 'i2', via: 'front-window'}, {item: 'i2', via: 'rear-window'}], routeEdited: true};
  return {r: {...r, cables: [c]}, c, ctx};
}
const between = p => p.detours.filter(d => d.between.length === 2 && d.between.every(w => w.item === 'i2'));
const lengthOf = pts => pts.slice(1).reduce((n, q, k) => n + Math.hypot(q.x - pts[k].x, q.y - pts[k].y, q.z - pts[k].z), 0);

// The kit stands every guide of a part at the middle of its lowest rack unit (route.js
// pointOf, anchorY). On the 3 RU HM34C that is 0.7 mm under its windows, which stand higher in
// a plate centred in its three units, so a cord laid through its rings meets the plate and not a
// window; the crossing above is judged on the part's own solids, which have no such anchor.
for (const name of MSERIES.filter(n => n !== 'hm34c')) {
  test(`${name}: a cord from the front ring to the rear ring goes straight through a window, and round the plate with the windows shut`, {skip}, () => {
    const {mine} = legAt(name, 0, 0);
    const hole = mine.find(s => s.holes.length).holes[1].box;
    const x = (hole.x0 + hole.x1) / 2;
    const open = crossingRack(name, x, false), shut = crossingRack(name, x, true);
    const through = R.routePath(open.r, open.c, open.ctx), round = R.routePath(shut.r, shut.c, shut.ctx);
    assert.deepEqual(through.crossings, []);
    assert.deepEqual(between(through), [], 'no detour between the rings through a window');
    assert.ok(between(round).length > 0, 'with the windows shut the plate is gone round');
    // from the front ring's entry to the rear ring's exit
    const stretch = p => { const e = p.points.map(q => q.at); return p.points.slice(e.indexOf('entry'), e.lastIndexOf('exit') + 1); };
    const gain = lengthOf(stretch(round)) - lengthOf(stretch(through));
    assert.ok(gain > 40, `the way through is ${gain.toFixed(0)} mm shorter than round the plate`);
  });
}

test('hsd13: the SD-Series advertises no pass-through, so nothing of it is a hole', {skip}, () => {
  const mine = S.solidsOf(rackOf('hsd13'), ctxOf('hsd13')).filter(s => s.item === 'i2');
  assert.ok(mine.every(s => !s.holes.length));
});
