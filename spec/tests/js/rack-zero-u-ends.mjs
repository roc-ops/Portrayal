// spec/tests/js/rack-zero-u-ends.mjs
// A CABLE ENDS ON A PART BESIDE THE RACK (P-0019): a power cord on an outlet
// of a zero-U PDU. The part is no rack item, and every place that resolves a
// cable end finds it as well: the commands, the settled facts, the route and
// its length, the free ports, inspect and describe, and the exports.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as Q from '../../../kit/rack/queries.js';
import * as R from '../../../kit/rack/route.js';
import * as P from '../../../kit/rack/ports.js';
import * as X from '../../../kit/rack/export-data.js';
import * as CR from '../../../kit/rack/cable-rules.js';
import * as S from '../../../kit/rack/solids.js';
import {apply, NOT_ADDED, GONE} from '../../../kit/rack/commands.js';
import {OPENING, RAIL_W} from '../../../kit/rack/rails.js';
import {compByRef, SLOTS, SIZES, oldPage, C13, C14, C19, C20} from './power-ends-fixture.mjs';

// A vertical PDU as the build writes one (an Eaton G4's shape, cut down): its
// outlets are top-level connector slots on its front panel, each with where
// a plug meets it (`mate`, mm from the top left of the 52 x 1829 panel). A1 is
// near the bottom, F42 near the top; a C39 takes a C14 or a C20.
const H = 1829;
const outlet = (id, iface, accepts, y) => ({id, kind: 'connector', interface: iface, media: null, bores: [], accepts, default: null,
                                            at: [9.1, y - 11], mate: [24.3, y]});
const VPDU = {default: 'base', 'pdu-class': 'managed', bays: {front: [], rear: []},
  cages: {front: [outlet('outlet-a1', 'iec-c13', [C14], 1619.67), outlet('outlet-a2', 'eaton-c39', [C14, C20], 1594.47),
                  outlet('outlet-c19', 'iec-c19', [C20], 900), outlet('outlet-f41', 'iec-c13', [C14], 60),
                  outlet('outlet-f42', 'eaton-c39', [C14, C20], 30)], rear: []},
  configs: [{name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {},
             names: {'outlet-a1': 'A1', 'outlet-a2': 'A2', 'outlet-c19': 'C19', 'outlet-f41': 'F41', 'outlet-f42': 'F42'}}]};
// a vertical cable manager: a part beside the rack with nothing a cable ends on
const DUCT = {default: 'base', 'pdu-class': null, bays: {}, cages: {}, configs: [{name: 'base', bays: {}, occupants: {}}]};
const SIZES2 = {...SIZES,
  vpdu: {manufacturer: 'Acme', model: 'VPDU', mount: 'rack-side', kind: 'pdu', ru: 41, h: H, w: 52, d: 65, default: 'base', configs: ['base']},
  duct: {manufacturer: 'Acme', model: 'DUCT', mount: 'rack-side', ru: 42, h: 1866, w: 88, d: 150, default: 'base', configs: ['base'], guides: {front: ['duct']}}};
const SLOTS2 = {...SLOTS, vpdu: VPDU, duct: DUCT};
const ctx = {chassisOf: ref => SIZES2[ref] ?? null, slotsOf: ref => SLOTS2[ref] ?? null, compByRef};
// the route context a page hands in, with the catalogue's lookups (the PSU's port is placed by the page)
const rc = {...ctx, guidesOf: () => [], portX: () => 150, bendOf: () => 1e12};

const run = (rack, cmds, c = ctx) => apply(rack, cmds, c);
const INLET = {item: 'i1', path: 'psu-1/module/inlet', view: 'rear'};
const at = (path, view = 'front') => ({item: 'z1', path, view});
// sw-1 (i1) at U35 of a 42U four-post; PDU-A (z1) at left-rear from U1
const BASE = run(M.withItem(M.newRack(), {ref: 'sw', cfg: 'base', ru: 35, label: 'sw-1'}).rack,
  {op: 'zerou.place', ref: 'vpdu', at: 'left-rear', ru: 1, label: 'PDU-A'}).rack;
const cord = (b, extra = {}) => run(BASE, {op: 'cable.add', a: INLET, b, media: 'power', purpose: 'power', ...extra});

test('a cord ends on an outlet of a zero-U PDU: added, moved and removed as on a device', () => {
  const r = cord(at('outlet-a2'));
  assert.equal(r.error, undefined);
  assert.deepEqual(r.rack.cables[0].b, at('outlet-a2'));
  const moved = run(r.rack, {op: 'cable.update', id: 'c1', b: at('outlet-f42')});
  assert.match(moved.summary, /Moved end B of cable c1 to PDU-A \(left-rear\) outlet-f42\./);
  // one cable an outlet, as one a port
  assert.match(run(r.rack, {op: 'cable.add', a: {item: 'i1', path: 'psu-3/module/inlet', view: 'rear'}, b: at('outlet-a2')}).error,
    /PDU-A \(left-rear\) outlet-a2 already has a cable \(c1\)/);
  assert.deepEqual(run(r.rack, {op: 'cable.remove', id: 'c1'}).rack.cables, []);
  // a part that is not there is still refused, with the sentences there were
  assert.equal(run(BASE, {op: 'cable.add', a: INLET, b: {item: 'z9', path: 'outlet-a1', view: 'front'}}).error, NOT_ADDED);
  assert.equal(run(r.rack, {op: 'cable.update', id: 'c1', b: {item: 'z9', path: 'outlet-a1', view: 'front'}}).error, GONE);
});

test('an end the part does not have is refused, with the ends it has by type', () => {
  const e = cord(at('zzz')).error;
  assert.equal(e, 'PDU-A has no zzz. It has C13 outlet-a1, outlet-f41; C39 outlet-a2, outlet-f42; C19 outlet-c19.');
  assert.equal(cord(at('outlet-a1', 'rear')).error, 'outlet-a1 is on the front panel of PDU-A: give view "front".');
  const duct = run(BASE, {op: 'zerou.place', ref: 'duct', at: 'right-rear', ru: 1, label: 'VCM'}).rack;
  assert.equal(run(duct, {op: 'cable.add', a: INLET, b: {item: 'z2', path: 'duct', view: 'front'}}).error, 'VCM has nothing a cable can end on.');
  // without the parts lists the end is kept as given, as a port of a device is
  assert.equal(run(BASE, {op: 'cable.add', a: INLET, b: at('zzz')}, {chassisOf: ctx.chassisOf}).error, undefined);
});

test('taking the PDU away keeps its cords as loose ends, and its id is not handed on', async () => {
  const r = cord(at('outlet-a2')).rack;
  const gone = run(r, {op: 'zerou.remove', id: 'z1'});
  assert.equal(gone.summary, 'Removed PDU-A from beside the rack. Its 1 cable is a loose end.');
  assert.equal(gone.rack.cables.length, 1);
  const loose = await Q.looseEnds(gone.rack, {...ctx, cableFacts: oldPage()});
  assert.deepEqual(loose.ends.map(e => [e.cable, e.side, e.reason]), [['c1', 'b', 'the device was removed']]);
  // the next part placed beside the rack is z2: the cord's end names z1 still
  assert.equal(run(gone.rack, {op: 'zerou.place', ref: 'vpdu', at: 'right-rear', ru: 1}).rack.zeroU.at(-1).id, 'z2');
  assert.deepEqual(run(r, {op: 'zerou.remove', id: 'z1', cables: 'remove'}).rack.cables, []);
});

test('the catalogue answers for an end on the PDU: it lands, an outlet, its plug derived and never stored', async () => {
  const r = cord(at('outlet-a2')).rack;
  // the page found no item z1 and says so; the catalogue answers over it
  const page = await oldPage()(r);
  assert.equal(page.ends.get(CR.endKey(at('outlet-a2'))).reason, 'the device was removed');
  const ends = P.settleEnds(r, page.ends, ctx);
  const b = ends.get(CR.endKey(at('outlet-a2')));
  assert.equal(b.reason, null);
  assert.deepEqual([b.info.family, b.info.role, b.info.connector, b.info.plug], ['power', 'outlet', 'C39 outlet', C14]);
  assert.equal(r.cables[0].b.plug, undefined, 'the plug is derived, not stored');
  // A C39 TAKES TWO PLUGS, and a cord set pairs its ends: the supply's C14
  // inlet takes a C13, so the C39 end is the C14, with nothing to set
  assert.deepEqual(CR.mismatch('power', ends.get(CR.endKey(INLET)).info, b.info), []);
  // from a C20 inlet (a rail PDU's input, which takes a C19) the C39 end is the C20
  const fed = run(M.withItem(BASE, {ref: 'pdu', cfg: 'base', ru: 20, label: 'pdu-1'}).rack,
    {op: 'cable.add', a: {item: 'i2', path: 'input', view: 'rear'}, b: at('outlet-a2'), media: 'power'}).rack;
  const fedEnds = P.settleEnds(fed, (await oldPage()(fed)).ends, ctx);
  assert.deepEqual([fedEnds.get('i2|rear|input').info.plug, fedEnds.get(CR.endKey(at('outlet-a2'))).info.plug], [C19, C20]);
  assert.equal(fedEnds.get(CR.endKey(at('outlet-a2'))).info.note, undefined);
  // psu-3 is filled by its default alone, and the catalogue knows what it holds: the far end is known
  const dflt = cord(at('outlet-a2'), {a: {item: 'i1', path: 'psu-3/module/inlet', view: 'rear'}}).rack;
  const known = P.settleEnds(dflt, new Map(), ctx).get(CR.endKey(at('outlet-a2'))).info;
  assert.deepEqual([known.plug, known.note], [C14, undefined]);
  // with the far end not known (a path under no bay), the first is drawn and the end says what to set
  const unknown = cord(at('outlet-a2'), {a: {item: 'i1', path: 'nowhere', view: 'rear'}}).rack;
  assert.equal(P.settleEnds(unknown, new Map(), ctx).get(CR.endKey(at('outlet-a2'))).info.note,
    `outlet-a2 takes more than one plug and ${C14} is drawn; set "plug" on the end to ${C14} or ${C20}`);
  // a stated plug is the one drawn, whatever the far end
  const c20 = cord({...at('outlet-a2'), plug: C20}).rack;
  assert.equal(P.settleEnds(c20, new Map(), ctx).get(CR.endKey(at('outlet-a2'))).info.plug, C20);
  // a mismatch warns, and never blocks
  const odd = cord(at('outlet-a1'), {media: 'cat6a'});
  assert.equal(odd.error, undefined);
  const said = await Q.suggestMedia(odd.rack, INLET, at('outlet-a1'), {...ctx, cableFacts: oldPage()});
  assert.equal(said.media, 'power');
  const warned = await Q.inspect(odd.rack, 'c1', {...ctx, cableFacts: oldPage()});
  assert.deepEqual(warned.mismatch, ['Cat 6A copper does not suit end A, which is power.', 'Cat 6A copper does not suit end B, which is power.']);
  // an end on a slot it does not have is loose, naming those it has
  const bad = {...r, cables: [{...r.cables[0], b: at('zzz')}]};
  assert.match(P.settleEnds(bad, new Map(), ctx).get(CR.endKey(at('zzz'))).reason, /^PDU-A has no zzz; it has C13 outlet-a1/);
  // without the catalogue it is not checked, never called removed
  assert.equal(P.settleEnds(r, page.ends, {}).has(CR.endKey(at('outlet-a2'))), false);
});

test('the paths a page asks zones for on a part beside the rack: its outlets', () => {
  assert.deepEqual(P.cableEndPaths(BASE.zeroU[0], 'front', ctx), ['outlet-a1', 'outlet-a2', 'outlet-c19', 'outlet-f41', 'outlet-f42']);
  assert.deepEqual(P.cableEndPaths(BASE.zeroU[0], 'rear', ctx), []);
});

test('the cord ends at the outlet: its place on the PDU, and the length to it, top and bottom', () => {
  const z = BASE.zeroU[0], d = BASE.frame.railDepth;
  // the PDU at left-rear looks rearward, so its panel is drawn mirrored from the front
  const cx = -(OPENING / 2 + RAIL_W + 26);
  const face = -d + 17 - 65 / 2;
  const near = (p, q) => ['x', 'y', 'z'].every(k => Math.abs(p[k] - q[k]) < 1e-6);
  const top = R.portPoint(BASE, at('outlet-f42'), rc), low = R.portPoint(BASE, at('outlet-a1'), rc);
  assert.ok(near(top, {x: cx - 26 + (52 - 24.3), y: H - 30, z: face}), JSON.stringify(top));
  assert.ok(near(low, {x: cx - 26 + (52 - 24.3), y: H - 1619.67, z: face}), JSON.stringify(low));
  assert.equal(M.zeroUPane(z), 'rear');
  // the route runs down the gutter beside the PDU to the outlet's unit, and the path ends on the outlet
  const hi = cord(at('outlet-f42')).rack, lo = cord(at('outlet-a1')).rack;
  assert.deepEqual(R.ownRoute(hi, hi.cables[0], rc).waypoints, [{lane: 'left-rear', ru: 35}, {lane: 'left-rear', ru: 41}]);
  assert.deepEqual(R.ownRoute(lo, lo.cables[0], rc).waypoints, [{lane: 'left-rear', ru: 35}, {lane: 'left-rear', ru: 5}]);
  const path = R.routePath(lo, lo.cables[0], rc);
  assert.ok(near(path.points.at(-1), low), JSON.stringify(path.points.at(-1)));
  // the outlet's plug stands 77 mm out of the PDU, rearward
  assert.ok(path.points.some(p => near(p, {...low, z: low.z - R.PLUG_REACH.power})));
  const lHi = R.routedLength(hi, hi.cables[0], rc).measured, lLo = R.routedLength(lo, lo.cables[0], rc).measured;
  // down the gutter 30 U to A1 against up it 6 U to F42: 24 U apart, and the
  // legs at each end alike to within where each outlet stands in its unit
  const apart = (lLo - lHi) * 1000;
  assert.ok(Math.abs(apart - 24 * 44.45) < 45, `${lHi} ${lLo} ${apart}`);
  // and withRoutedLengths gives the cord its stock length
  const sized = R.withRoutedLengths(lo, rc);
  assert.equal(sized.cables[0].length.source, 'routed');
});

test('at a front upright the panel is not mirrored, a raised part carries its outlets up, and its back looks the other way', () => {
  const r = run(M.withItem(M.newRack(), {ref: 'sw', cfg: 'base', ru: 35, label: 'sw-1'}).rack,
    {op: 'zerou.place', ref: 'vpdu', at: 'left-front', ru: 2, label: 'PDU-F'}).rack;
  const z = r.zeroU[0], up = M.zeroUOffset(2), cx = -(OPENING / 2 + RAIL_W + 26);
  assert.deepEqual([M.zeroUPane(z), M.zeroUPane(z, 'rear')], ['front', 'rear']);
  const p = R.portPoint(r, at('outlet-a1'), rc);
  const near = (a, b) => ['x', 'y', 'z'].every(k => Math.abs(a[k] - b[k]) < 1e-6);
  // a front upright: the PDU looks forward, its panel as drawn, its face half its depth before the post's middle
  assert.ok(near(p, {x: cx - 26 + 24.3, y: up + H - 1619.67, z: -17 + 65 / 2}), JSON.stringify(p));
  // its back panel is the depth behind, and drawn from behind (x runs the other way)
  const b = S.zeroUPanelPoint(r, z, SIZES2.vpdu, {x: 10, y: 100}, 'rear');
  assert.ok(near(b, {x: cx - 26 + (52 - 10), y: up + 100, z: -17 - 65 / 2}), JSON.stringify(b));
  // with no catalogue in the context there is no point, and none is kept for a context that has one
  const bare = {chassisOf: ctx.chassisOf, guidesOf: () => [], portX: () => 0};
  assert.equal(R.portPoint(r, at('outlet-a1'), bare), null);
  bare.slotsOf = ctx.slotsOf; bare.compByRef = ctx.compByRef;
  assert.ok(near(R.portPoint(r, at('outlet-a1'), bare), p));
});

test('free ports: the PDU\'s outlets by type, nearest a unit, and a device\'s inlets beside its data ports', async () => {
  const r = cord(at('outlet-f42')).rack;
  const all = await Q.freePorts(r, 'z1', ctx);
  assert.deepEqual(all.map(p => [p.path, p.label, p.type, p.connector, p.u]), [
    ['outlet-a1', 'A1', 'C13', 'C13 outlet', 5], ['outlet-a2', 'A2', 'C39', 'C39 outlet', 6], ['outlet-c19', 'C19', 'C19', 'C19 outlet', 21],
    ['outlet-f41', 'F41', 'C13', 'C13 outlet', 40]]);
  assert.deepEqual(all[0], {path: 'outlet-a1', view: 'front', label: 'A1', media: null, speed: null, kind: 'power', connector: 'C13 outlet',
                            plug: C14, type: 'C13', u: 5});
  // the free C39 outlets nearest U35: F42 has the cord, so A2
  assert.deepEqual((await Q.freePorts(r, 'z1', ctx, {kinds: ['power'], type: 'C39', near: 35})).map(p => p.path), ['outlet-a2']);
  assert.deepEqual((await Q.freePorts(BASE, 'z1', ctx, {type: 'c39', near: 35})).map(p => p.path), ['outlet-f42', 'outlet-a2']);
  assert.deepEqual((await Q.freePorts(BASE, 'z1', ctx, {near: 20})).map(p => p.path).slice(0, 2), ['outlet-c19', 'outlet-a2']);
  assert.deepEqual(await Q.freePorts(BASE, 'z1', ctx, {kinds: ['data']}), []);
  assert.equal((await Q.freePorts(BASE, 'z1', ctx, {near: 99})).error, 'This rack has no U99.');
  // a device: its supplies' inlets beside its data ports, with no reader that hands them in
  const portsOf = async (item, view) => (view === 'front' ? [{path: 'rj-1', cls: 'port', media: 'rj45'}] : []);
  const sw = await Q.freePorts(r, 'i1', {...ctx, portsOf});
  assert.deepEqual(sw.map(p => [p.path, p.kind ?? 'data', p.connector ?? null]).filter(([, k]) => k !== 'other'), [
    ['rj-1', 'data', null], ['psu-2/module/terminal/lug-1', 'power', 'terminal-stud inlet'], ['psu-2/module/terminal/lug-2', 'power', 'terminal-stud inlet'],
    ['psu-2/module/terminal/lug-10', 'power', 'terminal-stud inlet'], ['psu-3/module/inlet', 'power', 'C14 inlet']], 'psu-1 has the cord');
  assert.deepEqual((await Q.freePorts(r, 'i1', {...ctx, portsOf}, {type: 'C14'})).map(p => p.path), ['psu-3/module/inlet']);
});

test('inspect and describe name the PDU end', async () => {
  const r = cord(at('outlet-a2'), {label: 'sw-1 PSU1'}).rack;
  const z = await Q.inspect(r, 'z1', ctx);
  assert.deepEqual(z.ends.find(e => e.path === 'outlet-a2'), {path: 'outlet-a2', view: 'front', name: 'A2', type: 'C39', connector: 'C39 outlet',
    kind: 'power', plug: C14, u: 6, cable: 'c1'});
  assert.equal(z.ends.find(e => e.path === 'outlet-a1').cable, null);
  assert.deepEqual(z.cables, [{id: 'c1', end: 'b', path: 'outlet-a2', view: 'front', other: 'i1/psu-1/module/inlet'}]);
  const sw = await Q.inspect(r, 'i1', ctx);
  assert.deepEqual(sw.ends.filter(e => e.kind === 'power' && /inlet$/.test(e.path)).map(e => [e.path, e.connector, e.plug, e.cable]),
    [['psu-1/module/inlet', 'C14 inlet', C13, 'c1'], ['psu-3/module/inlet', 'C14 inlet', C13, null]]);
  const c = await Q.inspect(r, 'c1', {...ctx, route: rc, cableFacts: oldPage()});
  assert.equal(c.b.name, 'PDU-A (left-rear) outlet-a2');
  assert.deepEqual(c.loose, []);
  assert.ok(c.routed && c.routed.metres > 1, JSON.stringify(c.routed));
  assert.match(c.route.text, /left-rear/);
  assert.match(Q.describe(r, ctx), /c1: i1\/psu-1\/module\/inlet \(rear\) <-> z1\/outlet-a2, power/);
});

test('the exports name the PDU end: the schedule, the bill of materials and the sheet', async () => {
  // the plug stated, as a C39 asks
  const r = cord({...at('outlet-a2'), plug: C14}, {label: 'PSU1', length: {value: 2, unit: 'm'}}).rack;
  const page = (await oldPage()(r)).ends;
  const {rows} = X.cableScheduleRows(r, page, r.items, null, {parts: ctx});
  assert.deepEqual(rows.map(x => [x.a_device, x.a_port, x.b_device, x.b_u, x.b_port, x.status, x.notes]),
    [['sw-1', 'psu-1/module/inlet', 'PDU-A', 6, 'outlet-a2', 'connected', '']]);
  // without the parts lists the PDU is still named, at no unit, and its end is not checked
  assert.deepEqual(X.cableScheduleRows(r, page, r.items).rows.map(x => [x.b_device, x.b_u, x.status]), [['PDU-A', '', 'not checked']]);
  assert.deepEqual(X.cableBomRows(r, page, {parts: ctx}).map(l => [l.qty, l.model, l.description]), [[1, 'Power cable', '2 m; power at both ends']]);
  // the sheet: the cord lands on the rear face at both ends, so it is on a rear sheet and not a front one
  assert.deepEqual(X.sheetCableNotes(r, page, {faces: ['front'], parts: ctx}), ['1 cable is on the rear face only and is not on this sheet.']);
  assert.deepEqual(X.sheetCableNotes(r, page, {faces: ['rear'], drawn: new Set(['c1']), parts: ctx}), []);
  assert.deepEqual(CR.cablePlan(r).links[0].to, ['z1', 'outlet-a2', 'rear']);
});
