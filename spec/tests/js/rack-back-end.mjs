// spec/tests/js/rack-back-end.mjs
// THE FAR END OF AN ADAPTER OF A PANEL MOUNTED ON THE REAR RAILS (roc-ops/Portrayal#1836).
// A holder in a drawer has an end on its face and an end on its back, one sleeve.
// The panel faces out of the back of the cabinet, so the back end faces into it
// and no drawing places it. Held here: the end stands where the other end of
// the same sleeve does, so the route, the length, the stock size and the spare
// are worked out; an end the catalogue accepts and nothing places is said to be
// out of reach, once for the cable, and never for a loose end or a placed one;
// a hand route that comes from behind the panel is stored and warned of, never
// refused; the automatic route leaves a cabinet-facing port toward the front
// rails; and a rack with no such end measures what it did.
//
// The catalogue is back-end-fixture.mjs. Where PORTRAYAL_DIST names a build
// (test_xcu_cables.py), the last tests read the Fibrain XCU10 and the Nokia MF-8
// from it, on the rack at spec/tests/fixtures/rear-panel-back-end/.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as P from '../../../kit/rack/ports.js';
import * as Q from '../../../kit/rack/queries.js';
import * as CR from '../../../kit/rack/cable-rules.js';
import {RU} from '../../../kit/rack/rails.js';
import {apply} from '../../../kit/rack/commands.js';
import {redirectsOf} from '../../../kit/redirects.js';
import {ctx, end, SLOT, BASE, withCables, routeCtx, chassisOf} from './back-end-fixture.mjs';
import * as F from './route-direct-fixture.mjs';
import {compByRef as powerComps, SLOTS as POWER_SLOTS, SIZES as POWER_SIZES, C14, C20} from './power-ends-fixture.mjs';

const B01 = end('i2', `${SLOT}/b01`, 'rear'), B99 = end('i2', `${SLOT}/b99`, 'rear');
const SC01 = end('i2', `${SLOT}/sc01`), PORT1 = end('i1', 'port-1'), PORT2 = end('i1', 'port-2');
const BARE_B01 = end('i3', `${SLOT}/b01`, 'rear');
const nameOf = id => ({i1: 'SW-1', i2: 'PNL-1', i3: 'PNL-2'})[id] ?? id;

const placed = withCables(BASE, ['c1', PORT1, B01]);
const unplaced = withCables(BASE, ['c2', PORT2, BARE_B01]);
const rc = routeCtx(BASE);
const full = rack => ({...ctx, route: routeCtx(rack)});

// ── the other end of the same sleeve ─────────────────────────────────────
test('twinEnd: the back end of an adapter is the other end of the sleeve whose face end the fibre map pairs it with', () => {
  const item = BASE.items.find(i => i.id === 'i2');
  assert.deepEqual(P.twinEnd(item, B01, ctx), {path: `${SLOT}/sc01`, view: 'front'});
  assert.deepEqual(P.twinEnd(item, end('i2', `${SLOT}/b02`, 'rear'), ctx), {path: `${SLOT}/sc02`, view: 'front'});
});

test('twinEnd: a front end, a made-up port, a holder with no fibre map and a port that is no coupler have none', () => {
  const item = BASE.items.find(i => i.id === 'i2'), bare = BASE.items.find(i => i.id === 'i3'), sw = BASE.items.find(i => i.id === 'i1');
  assert.equal(P.twinEnd(item, SC01, ctx), null, 'a front end is not a back end');
  assert.equal(P.twinEnd(item, B99, ctx), null, 'a made-up port');
  assert.equal(P.twinEnd(item, end('i2', `${SLOT}/b01`, 'front'), ctx), null, 'the wrong face');
  assert.equal(P.twinEnd(bare, BARE_B01, ctx), null, 'no fibre map');
  assert.equal(P.twinEnd(sw, PORT1, ctx), null, 'a cage of a switch');
  assert.equal(P.twinEnd(item, B01, {chassisOf}), null, 'no catalogue');
  assert.equal(P.twinEnd(undefined, B01, ctx), null, 'no item');
});

// ── a point, and what follows from it ────────────────────────────────────
test('the back end stands where the other end of its sleeve does, on the far side of the panel', () => {
  const b = R.portPoint(placed, B01, rc), face = R.portPoint(placed, SC01, rc);
  assert.ok(b, 'a point');
  assert.equal(b.x, face.x, 'across the panel as its twin');
  assert.equal(b.y, face.y, 'up the panel as its twin');
  // the panel is on the rear rails: its far side is its depth in from them
  assert.equal(b.z, -placed.frame.railDepth + 284, 'depth the far side, as for any rear port');
  assert.equal(face.z, -placed.frame.railDepth, 'its twin is on the rail');
});

test('a port the drawing places is not moved by it, and an end with no twin has no point', () => {
  const a = R.portPoint(placed, PORT1, rc);
  assert.equal(a.x, 50);
  assert.equal(R.portPoint(unplaced, BARE_B01, rc), null);
  assert.equal(R.portPoint(placed, B99, rc), null, 'a made-up port');
  // without the catalogue the reader has nothing to find a twin from: as it was
  assert.equal(R.portPoint(placed, B01, {chassisOf, guidesOf: () => [], portX: rc.portX, portY: rc.portY}), null);
});

test('the cable to the back end has a path, a length, a stock size and a spare', () => {
  const c = placed.cables[0], path = R.routePath(placed, c, rc);
  assert.ok(path?.points?.length >= 2, 'a path');
  const len = R.routedLength(placed, c, rc);
  assert.ok(len.measured > 0 && len.need > 0, JSON.stringify(len));
  assert.ok(len.value >= len.need, 'a stock size that holds the need');
  const pinned = {...c, length: {value: 3, unit: 'm', source: 'entered'}};
  const s = R.spareOf({...placed, cables: [pinned]}, pinned, rc);
  assert.ok(s && s.spare_m > 0, 'a spare');
  assert.equal(s.stock_m, 3);
  assert.deepEqual(R.bodyFindings(placed, rc, nameOf), [], 'it comes to the far side of the panel and crosses nothing');
});

test('a routed length is written for it, and a length already written is never touched', () => {
  const made = R.withRoutedLengths(placed, rc).cables[0].length;
  assert.equal(made.source, 'routed');
  assert.ok(made.value > 0 && made.need > 0);
  const entered = {...placed.cables[0], length: {value: 2, unit: 'm', source: 'entered'}};
  assert.deepEqual(R.withRoutedLengths({...placed, cables: [entered]}, rc).cables[0].length, entered.length);
  const bought = {...placed.cables[0], length: {value: 5, unit: 'ft', source: 'ordered'}};
  assert.deepEqual(R.withRoutedLengths({...placed, cables: [bought]}, rc).cables[0].length, bought.length);
});

// ── "This end cannot be reached" ─────────────────────────────────────────
test('a back end the catalogue accepts and nothing places is said to be out of reach, once for the cable', () => {
  const found = R.unreachedFindings(unplaced, rc, nameOf);
  assert.equal(found.length, 1);
  assert.deepEqual(found[0], {kind: 'end-unreachable', cable: 'c2', ends: [{end: 'b', item: 'i3', path: `${SLOT}/b01`, view: 'rear'}],
    text: 'This end cannot be reached: no drawing places port b01 of PNL-2.'});
  assert.deepEqual(R.unreachedFindingsOf(unplaced, unplaced.cables[0], rc, nameOf), found);
  assert.match(R.unreachedFindings(unplaced, rc)[0].text, /port b01 of i3\.$/, 'the item by its id without a namer');
});

test('one finding for a cable whose two ends are out of reach, naming both', () => {
  const both = withCables(BASE, ['c3', BARE_B01, end('i3', `${SLOT}/b01`, 'rear')]);
  const found = R.unreachedFindings(both, rc, nameOf);
  assert.equal(found.length, 1);
  assert.deepEqual(found[0].ends.map(e => e.end), ['a', 'b']);
  assert.equal(found[0].text.match(/This end cannot be reached/g).length, 2);
});

test('no finding for a loose end, for an end that is placed, for a front end or without a catalogue', () => {
  const loose = withCables(BASE, ['c4', PORT1, B99], ['c5', PORT2, end('i2', `${SLOT}/b01`, 'front')]);
  assert.deepEqual(R.unreachedFindings(loose, rc, nameOf), [], 'a loose end is the loose-end finding\'s');
  assert.deepEqual(R.unreachedFindings(placed, rc, nameOf), [], 'its twin places it');
  const front = withCables(BASE, ['c6', PORT1, SC01]);
  assert.deepEqual(R.unreachedFindings(front, rc, nameOf), []);
  assert.deepEqual(R.unreachedFindings(unplaced, {chassisOf, guidesOf: () => [], portX: rc.portX}, nameOf), [], 'nothing is judged without the parts lists');
  assert.deepEqual(R.unreachedFindings({...BASE, cables: []}, rc, nameOf), []);
});

test('inspect and describe carry it', async () => {
  const c = full(unplaced);
  const seen = await Q.inspect(unplaced, 'c2', c);
  assert.equal(seen.route.unreached.text, 'This end cannot be reached: no drawing places port b01 of PNL-2.');
  assert.deepEqual(seen.route.unreached.ends, [{end: 'b', item: 'i3', path: `${SLOT}/b01`, view: 'rear'}]);
  const ok = await Q.inspect(placed, 'c1', full(placed));
  assert.equal(ok.route.unreached, undefined);
  assert.match(Q.describe(unplaced, c), /Findings: 1 cable has an end that cannot be reached \(c2\)\./);
  assert.doesNotMatch(Q.describe(placed, full(placed)), /cannot be reached/);
});

// ── a hand route is flagged, never refused ───────────────────────────────
const route = (rack, id, waypoints) => apply(rack, {op: 'cable.route', id, route: waypoints}, full(rack));
const BEHIND = [{lane: 'left-rear', ru: 30}];
const FROM_FRONT = [{lane: 'left-rear', ru: 30}, {lane: 'left-rear', ru: 36}, {lane: 'left-front', ru: 36}];

test('a hand route that ends behind the panel is accepted and stored, and warns that the last leg comes from the cabinet side', () => {
  const got = route(placed, 'c1', BEHIND);
  assert.equal(got.error, undefined);
  assert.deepEqual(got.rack.cables[0].route, BEHIND);
  assert.equal(got.rack.cables[0].routeEdited, true);
  const warned = got.findings.filter(f => f.kind === 'warning');
  assert.equal(warned.length, 1);
  assert.match(warned[0].text, /^c1 reaches port b01 of PNL-1 from behind the panel: the last leg must come from the cabinet side of the panel, the side of the front rails\.$/);
});

test('a hand route that arrives from the cabinet side is stored and not warned of, and neither is a route to a front end', () => {
  const ok = route(placed, 'c1', FROM_FRONT);
  assert.equal(ok.error, undefined);
  assert.deepEqual(ok.rack.cables[0].route, FROM_FRONT);
  assert.deepEqual(ok.findings, []);
  const faced = route(withCables(BASE, ['c6', PORT1, SC01]), 'c6', BEHIND);
  assert.equal(faced.error, undefined);
  assert.deepEqual(faced.findings, [], 'a route that passed is not warned of');
  // without the route readers nothing can be judged, and the route is stored all the same
  const bare = apply(placed, {op: 'cable.route', id: 'c1', route: BEHIND}, {chassisOf});
  assert.equal(bare.error, undefined);
  assert.deepEqual(bare.findings, []);
});

test('an end the drawing places gets no flag, and the first leg of an a end is judged as the last of a b end', () => {
  const swapped = withCables(BASE, ['c1', B01, PORT1]);
  const got = route(swapped, 'c1', BEHIND);
  assert.equal(got.error, undefined);
  assert.equal(got.findings.filter(f => f.kind === 'warning').length, 1);
  assert.equal(route(swapped, 'c1', [...FROM_FRONT].reverse()).findings.length, 0, 'the route runs from the back end, so it starts on the cabinet side');
});

// ── the automatic route leaves from the port's side ──────────────────────
test('the automatic route of a cabinet-facing port leaves toward the front rails, on the side its twin stands', () => {
  // the switch port stands just right of the centre line and the panel's sc01 well left of it: the left gutter is the shorter way
  // (a back end with no x stood at the centre line, which counts as left, and the two sides were never measured)
  const c = placed.cables[0];
  assert.deepEqual(R.autoRoute(placed, c, rc), [{lane: 'left-front', ru: 20}, {lane: 'left-front', ru: 30}]);
  const path = R.routePath({...placed, cables: [{...c, route: R.autoRoute(placed, c, rc)}]}, {...c, route: R.autoRoute(placed, c, rc)}, rc);
  const at = path.points, last = at.at(-1), before = at.at(-2);
  assert.ok(before.z >= last.z, `the lead leaves the port toward the front rails (z ${last.z} to ${before.z})`);
  assert.equal(last.z, -placed.frame.railDepth + 284);
});

test('a port on the far side of an end with no twin still routes by the side it always did', () => {
  assert.deepEqual(R.autoRoute(unplaced, unplaced.cables[0], rc), [{lane: 'right-front', ru: 20}, {lane: 'right-front', ru: 34}]);
  assert.equal(R.routePath(unplaced, unplaced.cables[0], rc), null);
});

// ── a rack with no such end measures what it did ─────────────────────────
// the numbers are those of the same racks before this change
test('a rack of front ends only gives the routes, lengths and findings it gave', () => {
  const r = F.rack(), c = F.ctxOf(r);
  const want = [['c1', 'i4:guide-4', 0.5142, 1], ['c2', 'i4:guide-4', 0.4998, 0.5], ['c3', 'i4:guide-4', 0.5027, 0.5], ['c4', 'i4:guide-4', 0.4914, 0.5],
    ['c5', 'i4:guide-4', 0.522, 1], ['c6', 'i4:guide-4', 0.515, 1], ['c7', 'i4:guide-4', 0.5058, 0.5], ['c8', 'i4:guide-4', 0.547, 1],
    ['c9', 'i4:guide-3', 0.6112, 1], ['c10', 'i4:guide-3', 0.6132, 1], ['c11', 'i4:guide-3', 0.6161, 1], ['c12', 'i4:guide-3', 0.6234, 1],
    ['c13', 'i4:guide-4', 0.6455, 1], ['c14', 'i4:guide-4', 0.6169, 1], ['c15', 'i4:guide-4', 0.648, 1], ['c16', 'i4:guide-4', 0.5763, 1]];
  const got = r.cables.map(cb => {
    const wp = R.autoRoute(r, cb, c), laid = {...cb, route: wp};
    const len = R.routedLength({...r, cables: r.cables.map(x => (x.id === cb.id ? laid : x))}, laid, c);
    return [cb.id, wp.map(w => `${w.item}:${w.via}`).join(','), Math.round(len.measured * 1e4) / 1e4, len.value];
  });
  assert.deepEqual(got, want);
  assert.deepEqual(R.unreachedFindings(r, c), []);
});

test('a cord to an outlet of a zero-U PDU gives the route, length and findings it gave', () => {
  const H = 1829, outlet = (id, y) => ({id, kind: 'connector', interface: 'eaton-c39', media: null, bores: [], accepts: [C14, C20], default: null, at: [9.1, y - 11], mate: [24.3, y]});
  const vpdu = {default: 'base', 'pdu-class': 'managed', bays: {front: [], rear: []}, cages: {front: [outlet('outlet-a2', 1594.47)], rear: []},
    configs: [{name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {}, names: {'outlet-a2': 'A2'}}]};
  const sizes = {...POWER_SIZES, vpdu: {manufacturer: 'Acme', model: 'VPDU', mount: 'rack-side', kind: 'pdu', ru: 41, h: H, w: 52, d: 65, default: 'base', configs: ['base']}};
  const c2 = {chassisOf: ref => sizes[ref] ?? null, slotsOf: ref => ({...POWER_SLOTS, vpdu})[ref] ?? null, compByRef: powerComps};
  const rc2 = {...c2, guidesOf: () => [], portX: () => 150, bendOf: () => 1e12};
  const base = apply(M.withItem(M.newRack(), {ref: 'sw', cfg: 'base', ru: 35, label: 'sw-1'}).rack, {op: 'zerou.place', ref: 'vpdu', at: 'left-rear', ru: 1, label: 'PDU-A'}, c2).rack;
  const added = apply(base, {op: 'cable.add', a: {item: 'i1', path: 'psu-1/module/inlet', view: 'rear'}, b: {item: 'z1', path: 'outlet-a2', view: 'front'}, media: 'power', purpose: 'power'}, c2);
  assert.equal(added.error, undefined);
  const cb = added.rack.cables[0], wp = R.autoRoute(added.rack, cb, rc2), laid = {...cb, route: wp}, rack = {...added.rack, cables: [laid]};
  assert.deepEqual(wp, [{lane: 'left-rear', ru: 35}, {lane: 'left-rear', ru: 6}]);
  const len = R.routedLength(rack, laid, rc2);
  assert.equal(Math.round(len.measured * 1e4) / 1e4, 2.5092);
  assert.equal(len.value, 3);
  assert.deepEqual(R.bodyFindings(rack, rc2), []);
  assert.deepEqual(R.unreachedFindings(rack, rc2), []);
});

// ── the Fibrain XCU10 and the Nokia MF-8, from a build ───────────────────
// (the rack is the one a person would draw: an MF-8 with an optic in line card
// 1 on the front rails, an XCU10 on the rear rails, one cable)
const DIST = process.env.PORTRAYAL_DIST;
const real = {skip: DIST ? false : 'PORTRAYAL_DIST names no build (test_xcu_cables.py sets it)'};
function library() {
  const read = name => JSON.parse(fs.readFileSync(`${DIST}/${name}`, 'utf8'));
  const components = read('components.json').components;
  const comps = new Map(components.map(c => [`${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`, c]));
  const devices = read('rack.json').devices;
  const drawn = (item, view) => {
    const f = `${item.ref}.${item.cfg}.${view}.elements.json`;
    return fs.existsSync(`${DIST}/${f}`) ? read(f).elements : [];
  };
  const lib = {chassisOf: ref => devices[ref] ?? null, compByRef: ref => (ref == null ? null : comps.get(String(ref).split(':')[0]) ?? null),
    redirects: redirectsOf(components),
    slotsOf: ref => { if (!devices[ref]) return null; const c = read(`${ref}.configs.json`); return {default: c.default, 'pdu-class': c['pdu-class'], bays: c.bays, cages: c.cages, configs: c.configs}; }};
  // a port as the page reads it off the drawn face: its centre across the panel, up from the floor of its unit
  const box = (rack, e) => {
    const it = rack.items.find(i => i.id === e.item);
    const el = it && drawn(it, e.view === 'rear' ? 'rear' : 'front').find(p => p.path === e.path || p.path === CR.portPathOf(e.path));
    return el ? {it, x: el.box.x + el.box.w / 2 - lib.chassisOf(it.ref).w / 2, y: el.box.y + el.box.h / 2, h: lib.chassisOf(it.ref).h} : null;
  };
  const routeCtx = rack => ({...lib, guidesOf: () => [], portX: e => box(rack, e)?.x ?? null, portY: e => { const b = box(rack, e); return b ? b.it.ru * RU - ((RU - b.h) / 2 + b.y) : null; }});
  return {lib, routeCtx};
}
const repro = () => M.parseDoc(fs.readFileSync(new URL('../fixtures/rear-panel-back-end/rear-panel-back-end.rack.json', import.meta.url), 'utf8')).racks[0];

test('the XCU10 repro: the cable to the back end of the first adapter has a point, a path and a length', real, () => {
  const {routeCtx: make} = library(), rack = repro(), c = rack.cables[0], rcx = make(rack);
  assert.equal(c.b.path, 'drawer/module/slot-1/module/b01');
  const b = R.portPoint(rack, c.b, rcx), sc01 = R.portPoint(rack, {...c.b, path: 'drawer/module/slot-1/module/sc01', view: 'front'}, rcx);
  assert.ok(b, 'a point');
  assert.equal(b.x, sc01.x);
  assert.equal(b.z, -rack.frame.railDepth + 284);
  const len = R.routedLength(rack, c, rcx);
  assert.ok(len.measured > 0, JSON.stringify(len));
  assert.equal(R.withRoutedLengths(rack, rcx).cables[0].length.source, 'routed');
  assert.deepEqual(R.unreachedFindings(rack, rcx), []);
  assert.deepEqual(R.autoRoute(rack, c, rcx).map(w => w.lane), ['left-front', 'left-front']);
});

test('the same rack with the MF-8 in its base configuration has a loose end and no end out of reach', real, () => {
  const {routeCtx: make} = library(), rack = repro();
  const base = {...rack, items: rack.items.map(i => (i.id === 'i1' ? {...i, cfg: 'base', swaps: {}} : i))};
  assert.deepEqual(R.unreachedFindings(base, make(base)), []);
});

test('the XCU10: a hand route behind the panel is stored and warned of; one from the front gutter is not', real, () => {
  const {lib, routeCtx: make} = library(), rack = repro(), c = {...lib, route: make(rack)};
  const behind = apply(rack, {op: 'cable.route', id: 'c1', route: [{lane: 'left-rear', ru: 16}]}, c);
  assert.equal(behind.error, undefined);
  assert.equal(behind.rack.cables[0].routeEdited, true);
  assert.match(behind.findings.find(f => f.kind === 'warning')?.text ?? '', /last leg must come from the cabinet side of the panel/);
  const ok = apply(rack, {op: 'cable.route', id: 'c1', route: [{lane: 'left-rear', ru: 16}, {lane: 'left-rear', ru: 20}, {lane: 'left-front', ru: 20}]}, c);
  assert.deepEqual(ok.findings, []);
});
