// spec/tests/js/rack-power-ends.mjs
// WHERE A CABLE CAN LAND (#1045, docs/cable-ends-design.md): on a part of
// class `port`, or on a connector slot that takes a cable end. A power inlet,
// an outlet, a DC terminal and a ground stud are such slots; a pluggable cage,
// a module bay, a guard seat and a blind slot are not.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {install, build} from './fake-dom.mjs';
import * as M from '../../../kit/rack/model.js';
import * as Q from '../../../kit/rack/queries.js';
import * as R from '../../../kit/rack/route.js';
import * as CR from '../../../kit/rack/cable-rules.js';
import * as G from '../../../kit/rack/cable-geometry.js';
import * as X from '../../../kit/rack/export-data.js';
import * as D from '../../../kit/rack/dcim-rules.js';
import * as P from '../../../kit/rack/ports.js';
import {validate} from '../../../kit/rack/validate.js';
import {apply, COMMANDS} from '../../../kit/rack/commands.js';
import {ctx, compByRef, chassisOf, SLOTS, COMPONENTS, oldPage, drawnAt, zonesOf, C13, C14, C19, C20, LUG, RJ, SFP, PSU_AC} from './power-ends-fixture.mjs';

install();
globalThis.DOMParser = class {
  parseFromString(text) {
    const give = n => { Object.defineProperty(n, 'id', {get() { return this.getAttribute('id') || ''; }}); n.children.forEach(give); return n; };
    const root = give(build(JSON.parse(text)));
    root.querySelector = () => null;
    return {documentElement: root};
  }
};
const Z = await import('../../../kit/zones.js');

const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'base', ru, label: extra.label ?? ref, ...extra}).rack;
const end = (item, path, view = 'rear') => ({item, path, view});
// sw-1 (i1) at U30, pdu-1 (i2) at U20, nema-1 (i3) at U10
const RACK = add(add(add(M.newRack(), 'sw', 30, {label: 'sw-1'}), 'pdu', 20, {label: 'pdu-1'}), 'nema', 10, {label: 'nema-1'});
const run = (rack, cmds) => apply(rack, cmds, ctx);
const cabled = (rack, ...cables) => run(rack, cables.map(c => ({op: 'cable.add', ...c}))).rack;
// the kit with a page that knows class `port` alone, and with one that also says what is drawn
const bare = rack => ({...ctx, cableFacts: oldPage()});
const full = rack => ({...ctx, cableFacts: oldPage(), drawnAt: drawnAt(rack)});
const loose = async (rack, c = bare(rack)) => (await Q.looseEnds(rack, c)).ends.map(e => `${e.cable} ${e.side}: ${e.reason}`);

const INLET = end('i1', 'psu-1/module/inlet'), LUG1 = end('i1', 'psu-2/module/terminal/lug-1');
const OUT_F1 = end('i2', 'outlet-front-1', 'front'), OUT_R1 = end('i2', 'outlet-rear-1'), PDU_IN = end('i2', 'input');

// ── the rule ─────────────────────────────────────────────────────────────
test('the rule: a part of class port, or a connector slot that accepts a cable end', () => {
  const sw = SLOTS.sw.cages, by = id => [...sw.front, ...sw.rear].find(g => g.id === id);
  const psu = compByRef(PSU_AC).cages[0];
  assert.equal(CR.cableLandsOn({cls: 'port'}), true, 'a port, as ever');
  assert.equal(CR.cableLandsOn({cls: 'inlet', slot: psu}, compByRef), true, 'a supply inlet: its slot takes a C13');
  assert.equal(CR.cableLandsOn({cls: 'ground', slot: by('ground')}, compByRef), true, 'a ground stud: its slot takes a lug');
  assert.equal(CR.cableLandsOn({cls: 'inlet', slot: null}, compByRef), false, 'an outlet with no interface is no slot');
  // what it must not admit, each by name
  assert.equal(CR.takesCableEnd(by('port-1'), compByRef), false, 'an SFP cage: it accepts optics, and is kind cage');
  assert.equal(CR.takesCableEnd(by('blind-1'), compByRef), false, 'a blind slot: it accepts nothing');
  assert.equal(CR.takesCableEnd(by('fibre-1'), compByRef), false, 'a slot that accepts only a dust cap');
  assert.equal(CR.takesCableEnd(compByRef('acme/breaker@1').cages[0], compByRef), false, 'a guard seat: it accepts a mechanical part');
  assert.equal(CR.takesCableEnd(SLOTS.sw.bays.rear[0], compByRef), false, 'a module bay is not a connector slot');
  assert.equal(CR.takesCableEnd({...by('port-1'), accepts: [RJ]}, compByRef), false, 'a cage is refused whatever it accepts');
  assert.equal(CR.takesCableEnd(psu, null), false, 'and nothing is admitted without the catalogue');
  assert.equal(CR.cableLandsOn({cls: 'port', slot: by('port-1')}, compByRef), true, 'the cage is still the port it always was');
});

test('what a receptacle is comes from its part: family, direction, AC or DC', () => {
  const of = ref => CR.receptacleOf(compByRef(ref));
  assert.deepEqual(of('std/c14-inlet@1'), {family: 'power', mode: 'ac', role: 'inlet'});
  assert.deepEqual(of('std/c13-outlet@1'), {family: 'power', mode: null, role: 'outlet'});
  assert.deepEqual(of('common/dc-terminal@1'), {family: 'power', mode: 'dc', role: 'inlet'});
  assert.deepEqual(of('common/ground-stud@1'), {family: 'ground', mode: null, role: null});
  assert.deepEqual(of(PSU_AC), {family: 'power', mode: 'ac', role: 'inlet'}, 'a placed supply that presents its inlet');
  assert.deepEqual(of('common/terminal-screw@1'), {family: null, mode: null, role: null}, 'a screw says nothing of itself');
  assert.deepEqual(CR.receptacleOf(null), {family: null, mode: null, role: null}, 'nothing known is no family, never a guess');
  const name = (iface, ref) => CR.connectorName({interface: iface}, of(ref));
  assert.deepEqual([name('iec-c13', 'std/c13-outlet@1'), name('iec-c20', 'std/c20-inlet@1'), name('terminal-stud', 'common/ground-stud@1'),
    name('p40', 'acme/fixed-cord@1'), name('terminal-stud', 'common/terminal-screw@1')],
    ['C13 outlet', 'C20 inlet', 'terminal-stud ground', 'p40 power connector', 'terminal-stud connector']);
});

// ── landing ──────────────────────────────────────────────────────────────
test('a cable to a supply inlet lands by the path of its slot', async () => {
  const rack = cabled(RACK, {a: INLET, b: OUT_F1, media: 'power'});
  assert.deepEqual(await loose(rack), []);
  const at = P.seatedPort(rack.items[0], INLET, ctx);
  assert.deepEqual([at.port, at.slot, at.cage, at.onView, at.holder.part], [true, true, false, 'rear', 'PSU-AC']);
  assert.deepEqual(at.info, {family: 'power', mode: 'ac', role: 'inlet', plug: C13, connector: 'C14 inlet'});
  // the other panel does not show it, and a part that is no slot is named
  assert.equal(P.seatedPort(rack.items[0], end('i1', 'psu-1/module/inlet', 'front'), ctx), null);
  const led = cabled(RACK, {a: end('i1', 'psu-1/module/led'), b: OUT_F1});
  assert.deepEqual(await loose(led), ['c1 a: psu-1 holds PSU-AC, whose led takes no plug or lug the library knows']);
  const none = cabled(RACK, {a: end('i1', 'psu-1/module/nothing'), b: OUT_F1});
  assert.deepEqual(await loose(none), ['c1 a: psu-1 holds PSU-AC, which has no port nothing'], 'a path that names no part reads as it did');
});

test('a supply in a bay that only its default fills lands from the catalogue, with no page to see it', async () => {
  // no configuration and no swap names psu-3, and it states no only-in: it is a bay of every configuration
  // and holds what it ships with
  const D3 = end('i1', 'psu-3/module/inlet');
  assert.equal(P.seatedPort(RACK.items[0], D3, ctx).slot, true);
  const rack = cabled(RACK, {a: D3, b: OUT_F1, media: 'power'}, {a: end('i1', 'psu-3/module/led'), b: OUT_R1}, {a: end('i1', 'psu-3/module/gone'), b: PDU_IN});
  assert.deepEqual(await loose(rack), ['c2 a: psu-3 holds PSU-AC, whose led takes no plug or lug the library knows',
    'c3 a: psu-3 holds PSU-AC, which has no port gone']);
  assert.deepEqual((await Q.inspect(rack, 'c1', bare(rack))).mismatch, []);
  // a page that did not read the end is answered for all the same
  assert.equal(P.settleEnd(rack, D3, undefined, ctx).facts.port, true);
  // the catalogue's answer stands over a page that read the panel of another build: PSU-AC composes a jack
  // `mgmt`, of class port, which a page of class `port` alone found nothing at
  const MG = end('i1', 'psu-3/module/mgmt');
  assert.equal(P.seatedPort(RACK.items[0], MG, ctx).port, true);
  assert.deepEqual(await loose(cabled(RACK, {a: MG, b: OUT_F1})), []);
});

test('a slot of another build of the device is not a slot of this one', async () => {
  // `narrow` shows the panel front-narrow: rj-2 and out-2 are on the wide panel only. A page that knows class
  // port alone says "no port" of a path with nothing drawn, exactly as it does of a drawn slot.
  const narrow = add(M.newRack(), 'two', 5, {label: 'two-1', cfg: 'narrow'}), wide = add(M.newRack(), 'two', 5, {label: 'two-1', cfg: 'wide'});
  const f = path => end('i1', path, 'front');
  assert.equal(P.ownSlot(narrow.items[0], f('out-2'), ctx), null);
  assert.equal(P.ownSlot(narrow.items[0], f('rj-2'), ctx), null);
  assert.equal(P.ownSlot(narrow.items[0], f('out-1'), ctx).facts.port, true);
  assert.equal(P.ownSlot(wide.items[0], f('out-2'), ctx).facts.port, true);
  const rack = cabled(narrow, {a: f('rj-1'), b: f('rj-2'), media: 'cat6'}, {a: f('out-1'), b: f('out-2'), media: 'power'});
  for (const c of [bare(rack), full(rack)])
    assert.deepEqual(await loose(rack, c), ['c1 b: rj-2 is not on this panel', 'c2 b: out-2 is not on this panel']);
  const facts = await oldPage()(rack);
  assert.deepEqual(X.cableScheduleRows(rack, facts.ends, rack.items, null, {parts: full(rack)}).rows.map(r => r.status), ['loose end', 'loose end']);
  const names = X.uniqueNames(rack.items), kept = new Set(['i1']);
  assert.equal(D.cableImportRows({rack, names, kept, ends: facts.ends, uOf: () => 1, parts: full(rack),
    resolve: e => ({ok: true, name: e.path, type: 'dcim.interface'})}).rows.length, 0);
  // and nothing of the other build is offered
  assert.deepEqual(P.cableEndPaths(narrow.items[0], 'front', ctx), ['rj-1', 'out-1']);
  assert.deepEqual(P.cableEndPaths(wide.items[0], 'front', ctx), ['rj-1', 'rj-2', 'out-1', 'out-2']);
  assert.deepEqual(P.shownEnv(narrow.items[0], SLOTS.two, compByRef).cages.map(g => [g.id, g.view]), [['rj-1', 'front'], ['out-1', 'front']]);
  const stray = async (item, view) => (view === 'front' ? [...zonesOf('two', 'front', ['out-1']), {id: 'out-2', cls: 'inlet', path: 'out-2', end: true, ref: 'std/c13-outlet@1'}] : []);
  assert.deepEqual((await Q.freePorts(narrow, 'i1', {...ctx, portsOf: stray})).map(p => p.path), ['rj-1', 'out-1']);
});

test('a cable to a slotted outlet of a rail-mounted PDU lands, with a page that knows class port alone', async () => {
  const rack = cabled(RACK, {a: INLET, b: OUT_F1, media: 'power'}, {a: end('i1', 'psu-9/module/inlet'), b: OUT_R1}, {a: PDU_IN, b: end('i2', 'ground')});
  // c2's a end names a bay the device has not: the page's own words stand
  assert.deepEqual(await loose(rack), ['c2 a: psu-9 is empty']);
  const got = P.ownSlot(rack.items[1], OUT_F1, ctx);
  assert.deepEqual(got.facts, {port: true, slot: true, cage: false, occupied: false, onView: 'front'});
  assert.deepEqual(got.info, {family: null, mode: null, role: null, plug: C14, connector: 'C13 connector'}, 'no page word, no family: never a guess');
  // with what is drawn there, it says what it is
  assert.deepEqual(P.ownSlot(rack.items[1], OUT_F1, full(rack)).info, {family: 'power', mode: null, role: 'outlet', plug: C14, connector: 'C13 outlet'});
  assert.deepEqual(P.ownSlot(rack.items[1], PDU_IN, full(rack)).info, {family: 'power', mode: 'ac', role: 'inlet', plug: C19, connector: 'C20 inlet'});
  // the outlet is on the front: named on the rear, it is not there
  const wrong = cabled(RACK, {a: INLET, b: end('i2', 'outlet-front-1', 'rear')});
  assert.deepEqual(await loose(wrong), ['c1 b: outlet-front-1 is not on this panel']);
});

test('an end the page did not read, or read as a port, is left as the page had it', () => {
  const rack = cabled(RACK, {a: INLET, b: OUT_F1});
  const settle = got => P.settleEnd(rack, OUT_F1, got, ctx);
  assert.equal(settle(undefined), null, 'not read: not checked, as before');
  const noDrawing = {facts: {item: true, drawing: false}, reason: 'this panel has no drawing'};
  assert.equal(settle(noDrawing), noDrawing);
  const port = {facts: {item: true, drawing: true, port: true, cage: false, occupied: false, holder: null}, info: {family: 'copper', mode: null}, reason: null};
  assert.equal(settle(port), port);
  // and a device-own port of class port is never asked of the catalogue
  const rj = {facts: {item: true, drawing: true, port: true, cage: false, occupied: false, holder: null}, info: {family: 'copper', mode: null}, reason: null};
  assert.equal(P.settleEnd(rack, end('i1', 'rj-1', 'front'), rj, ctx), rj);
});

test('an outlet that is no slot is loose, with a true sentence', async () => {
  const rack = cabled(RACK, {a: INLET, b: end('i3', 'outlet-9'), media: 'power'}, {a: end('i1', 'psu-2/module/art'), b: end('i3', 'input')});
  assert.deepEqual(await loose(rack, full(rack)), [
    'c1 b: outlet-9 is NEMA 5-20R, which takes no plug or lug the library knows',
    'c2 a: psu-2 holds PSU-DC, whose art takes no plug or lug the library knows',
    'c2 b: input is FIXED CORD, which takes no plug or lug the library knows']);
  // a page that does not say what is drawn there: the sentence it always gave
  assert.deepEqual((await loose(rack))[0], 'c1 b: outlet-9 is not on this panel');
  // the schedule says it in the row, and the DCIM cables file leaves the cable out by name
  const facts = await oldPage()(rack);
  const rows = X.cableScheduleRows(rack, facts.ends, rack.items, null, {parts: full(rack)}).rows;
  assert.equal(rows[0].status, 'loose end');
  assert.equal(rows[0].notes, 'End B is not connected: outlet-9 is NEMA 5-20R, which takes no plug or lug the library knows.');
});

test('a slot on a side view is loose, and says an end is front or rear', async () => {
  const rack = cabled(RACK, {a: end('i1', 'ground-left', 'front'), b: end('i2', 'ground')});
  assert.deepEqual(await loose(rack), ['c1 a: ground-left is on the left of the device, and a cable end can be given on the front or rear only']);
});

test('an end saved to an -occupant path keeps working and is not rewritten', async () => {
  const saved = {format: 'portrayal-rack', version: 4, id: 'doc-occ', racks: [{...RACK, id: 'r1',
    cables: [{id: 'c1', a: end('i1', 'psu-1/module/inlet-occupant'), b: end('i2', 'outlet-front-1-occupant', 'front'), media: 'power', purpose: '', label: '', route: []}]}]};
  const rack = M.parseDoc(JSON.parse(JSON.stringify(saved))).racks[0];
  assert.deepEqual(rack.cables[0].a, end('i1', 'psu-1/module/inlet-occupant'), 'the address is kept as written');
  assert.deepEqual(await loose(rack), [], 'and lands, with nothing fitted there');
  // no command rewrites it: an edit of the cable, and a new cable given such a path, keep the address as given
  const OCC = end('i1', 'psu-1/module/inlet-occupant');
  const edited = run(rack, [{op: 'cable.update', id: 'c1', label: 'kept', media: 'power'}, {op: 'cable.update', id: 'c1', a: OCC}]).rack;
  assert.deepEqual([edited.cables[0].a, edited.cables[0].b.path, edited.cables[0].label], [OCC, 'outlet-front-1-occupant', 'kept']);
  const added = run(RACK, [{op: 'cable.add', a: OCC, b: OUT_R1, media: 'power'}]).rack;
  assert.deepEqual(added.cables[0].a, OCC);
  assert.deepEqual(await loose(added), []);
  // only a caller that names the slot's own path moves it there, and is told it moved
  const moved = run(rack, [{op: 'cable.update', id: 'c1', a: INLET}]);
  assert.deepEqual(moved.rack.cables[0].a, INLET);
  assert.match(moved.summary, /^Moved end A of cable c1 to /);
  // it is the same port: a second cable to the slot is refused
  assert.match(run(rack, [{op: 'cable.add', a: INLET, b: OUT_R1}]).error, /already has a cable/);
  assert.equal(CR.sameEnd(end('i1', 'psu-1/module/inlet-occupant'), INLET), true);
});

// ── a DC terminal ────────────────────────────────────────────────────────
test('a DC feed lands on a screw of its terminal, and the terminal itself is named as no slot', async () => {
  const rack = cabled(RACK, {a: LUG1, b: OUT_R1, media: 'power'}, {a: end('i1', 'psu-2/module/terminal'), b: OUT_F1, media: 'power'});
  // the terminal is no slot and its screws are: the reason says which path to give
  // (lug-1 has the feed c1 on it, so it is not among the screws to give)
  assert.deepEqual(await loose(rack), ['c2 a: psu-2 holds PSU-DC, whose terminal takes a cable on lug-2, lug-10 and not on itself; give the path psu-2/module/terminal/lug-2']);
  const none = cabled(RACK, {a: end('i1', 'psu-2/module/terminal'), b: OUT_F1, media: 'power'});
  assert.deepEqual(await loose(none), ['c1 a: psu-2 holds PSU-DC, whose terminal takes a cable on lug-1, lug-2, lug-10 and not on itself; give the path psu-2/module/terminal/lug-1']);
  assert.deepEqual(P.seatedPort(rack.items[0], end('i1', 'psu-2/module/terminal'), ctx).under,
    ['psu-2/module/terminal/lug-1', 'psu-2/module/terminal/lug-2', 'psu-2/module/terminal/lug-10']);
  // a screw that has a cable is not the one to give: the first FREE one is, in natural order
  const T = end('i1', 'psu-2/module/terminal'), lug = n => end('i1', `psu-2/module/terminal/lug-${n}`);
  const one = cabled(RACK, {a: lug(1), b: OUT_R1, media: 'power'}, {a: T, b: OUT_F1, media: 'power'});
  assert.deepEqual(await loose(one), ['c2 a: psu-2 holds PSU-DC, whose terminal takes a cable on lug-2, lug-10 and not on itself; give the path psu-2/module/terminal/lug-2']);
  const two = cabled(RACK, {a: lug(1), b: OUT_R1, media: 'power'}, {a: lug(2), b: PDU_IN, media: 'power'}, {a: T, b: OUT_F1, media: 'power'});
  assert.deepEqual(await loose(two), ['c3 a: psu-2 holds PSU-DC, whose terminal takes a cable on lug-10 and not on itself; give the path psu-2/module/terminal/lug-10']);
  const all = cabled(RACK, {a: lug(1), b: OUT_R1, media: 'power'}, {a: lug(2), b: PDU_IN, media: 'power'},
    {a: lug(10), b: end('i2', 'outlet-front-2', 'front'), media: 'power'}, {a: T, b: OUT_F1, media: 'power'});
  assert.deepEqual(await loose(all), ['c4 a: psu-2 holds PSU-DC, whose terminal takes a cable on its screws and not on itself, and every screw of its terminal has a cable']);
  const at = P.seatedPort(rack.items[0], LUG1, ctx);
  // the screw says nothing of itself: the terminal it is part of does
  assert.deepEqual(at.info, {family: 'power', mode: 'dc', role: 'inlet', plug: LUG, connector: 'terminal-stud inlet'});
});

// ── the plug at an end ───────────────────────────────────────────────────
test('the plug is derived from the slot: one accepted, several, stated, not accepted', () => {
  const [one, , two] = [SLOTS.pdu.cages.front[0], null, SLOTS.pdu.cages.rear[2]];
  assert.deepEqual(CR.endPlug(one, compByRef), {plug: C14, choices: [C14], note: null});
  // several: the lowest rating first, whatever order the accept list is built in
  assert.deepEqual(two.accepts, ['acme/plug-20a@1', 'acme/plug-15a@1']);
  assert.deepEqual(CR.endPlug(two, compByRef), {plug: 'acme/plug-15a@1', choices: ['acme/plug-15a@1', 'acme/plug-20a@1'],
    note: 'outlet-rear-2 takes more than one plug and acme/plug-15a@1 is drawn; set "plug" on the end to acme/plug-15a@1 or acme/plug-20a@1'});
  assert.deepEqual(CR.endPlug(two, compByRef, 'acme/plug-20a@1:1.0.0'), {plug: 'acme/plug-20a@1', choices: ['acme/plug-15a@1', 'acme/plug-20a@1'], note: null});
  assert.equal(CR.endPlug(two, compByRef, C13).note,
    'it states the plug generic/c13-plug@1, which outlet-rear-2 does not take; set "plug" on the end to acme/plug-15a@1 or acme/plug-20a@1');
  // the rating decides before the ref does: a 15 A plug whose ref sorts after the 20 A one is still first
  const rated = ref => ({'acme/a-plug@1': {class: 'port', attrs: {'rating-a': 20}}, 'acme/z-plug@1': {class: 'port', attrs: {'rating-a': 15}},
    'acme/m-plug@1': {class: 'port', attrs: {}}})[ref] ?? null;
  assert.deepEqual(CR.cableEndsOf({kind: 'connector', accepts: ['acme/a-plug@1', 'acme/m-plug@1', 'acme/z-plug@1']}, rated),
    ['acme/z-plug@1', 'acme/a-plug@1', 'acme/m-plug@1'], 'and a part that states no rating comes after those that do');
  assert.equal(CR.endPlug({id: 's', kind: 'connector', accepts: ['acme/a-plug@1', 'acme/z-plug@1']}, rated).plug, 'acme/z-plug@1');
  // parts that state no rating are in the order of their refs
  assert.deepEqual(CR.cableEndsOf({kind: 'connector', accepts: [C20, C14, SFP]}, compByRef), [C14, C20]);
  assert.deepEqual(CR.endPlug(SLOTS.sw.cages.front[0], compByRef), {plug: null, choices: [], note: null}, 'a cage gives no plug');
});

test('a stated plug is saved on the end, round trips, and is said when the slot does not take it', async () => {
  const two = end('i2', 'outlet-rear-2');
  const res = run(RACK, [{op: 'cable.add', a: INLET, b: {...two, plug: 'acme/plug-20a@1'}, media: 'power'}]);
  assert.deepEqual(res.rack.cables[0].b, {...two, plug: 'acme/plug-20a@1'});
  assert.equal('plug' in res.rack.cables[0].a, false, 'an end that states none has no key');
  const doc = M.parseDoc(JSON.parse(M.serialize({format: 'portrayal-rack', version: 4, id: 'd', racks: [res.rack]})));
  assert.deepEqual(doc.racks[0].cables[0].b, {...two, plug: 'acme/plug-20a@1'});
  assert.deepEqual((await Q.inspect(res.rack, 'c1', full(res.rack))).mismatch, []);
  // none stated: the first is drawn, and the sentence says what to set
  const open = cabled(RACK, {a: INLET, b: two, media: 'power'});
  assert.deepEqual((await Q.inspect(open, 'c1', full(open))).mismatch,
    ['End B: outlet-rear-2 takes more than one plug and acme/plug-15a@1 is drawn; set "plug" on the end to acme/plug-15a@1 or acme/plug-20a@1.']);
  const set = run(open, [{op: 'cable.update', id: 'c1', b: {...two, plug: 'acme/plug-15a@1'}}]);
  assert.equal(set.summary, 'Edited cable c1.', 'stating a plug is an edit, not a move');
  assert.deepEqual((await Q.inspect(set.rack, 'c1', full(set.rack))).mismatch, []);
  // the end named again without one states none; named as it is, nothing changes
  assert.equal('plug' in run(set.rack, [{op: 'cable.update', id: 'c1', b: two}]).rack.cables[0].b, false);
  assert.equal(run(set.rack, [{op: 'cable.update', id: 'c1', b: {...two, plug: 'acme/plug-15a@1'}}]).rack, set.rack);
  assert.equal(run(open, [{op: 'cable.update', id: 'c1', b: two}]).rack, open);
});

test('plug seats: a slot end seats its derived plug; a port is read as it always was', () => {
  const slots = [...SLOTS.pdu.cages.front, ...SLOTS.pdu.cages.rear, ...SLOTS.sw.cages.front];
  const landed = {cls: 'inlet', compByRef};
  assert.deepEqual(CR.plugSeats('outlet-front-1', slots, {}, landed), {'outlet-front-1': C14});
  assert.deepEqual(CR.plugSeats('outlet-rear-2', slots, {}, {...landed, plug: 'acme/plug-20a@1'}), {'outlet-rear-2': 'acme/plug-20a@1'});
  assert.deepEqual(CR.plugSeats('outlet-front-1', slots, {'outlet-front-1': C14}, landed), {}, 'a slot the user spoke for is left alone');
  assert.deepEqual(CR.plugSeats('outlet-front-1', slots, {}), {}, 'nothing is derived unless the caller says the end landed by its slot');
  assert.deepEqual(CR.plugSeats('blind-1', slots, {}, landed), {});
  // class port: the table, and only the table
  assert.deepEqual(CR.plugSeats('rj-1', slots, {}), {'rj-1': RJ});
  assert.deepEqual(CR.plugSeats('rj-1', slots, {}, {cls: 'port', compByRef}), {'rj-1': RJ});
  const sc = [{id: 'sc-1', kind: 'connector', interface: 'sc', accepts: [RJ], bores: []}];
  assert.deepEqual(CR.plugSeats('sc-1', sc, {}, {cls: 'port', compByRef}), {}, 'a port with a connector the table does not know still derives none');
});

// ── media and mismatch ───────────────────────────────────────────────────
test('power and ground are media: proposed from the ends, and warned about where they do not suit', async () => {
  const P_ = {family: 'power', mode: null}, AC = {family: 'power', mode: 'ac', role: 'inlet'}, DC = {family: 'power', mode: 'dc', role: 'inlet'};
  const OUT = {family: 'power', mode: null, role: 'outlet'}, CU = {family: 'copper', mode: null}, GND = {family: 'ground', mode: null, role: null};
  assert.equal(CR.proposeMedia(AC, OUT), 'power');
  assert.equal(CR.proposeMedia(GND, GND), 'ground');
  assert.equal(CR.proposeMedia(CU, CU), 'cat6a', 'a data pair is offered what it was');
  // nothing is refused; each of these is a warning
  assert.deepEqual(CR.mismatch('power', OUT, AC), [], 'outlet to inlet: nothing to say');
  assert.deepEqual(CR.mismatch('cat6a', AC, CU), ['The ends differ: A is power, B is copper.', 'Cat 6A copper does not suit end A, which is power.']);
  assert.deepEqual(CR.mismatch('power', OUT, CU), ['The ends differ: A is power, B is copper.', 'Power cable does not suit end B, which is copper.']);
  assert.deepEqual(CR.mismatch('power', P_, GND), ['The ends differ: A is power, B is ground.', 'Power cable does not suit end B, which is ground.']);
  assert.deepEqual(CR.mismatch('ground', GND, DC), ['The ends differ: A is ground, B is power.', 'Ground wire does not suit end B, which is power.']);
  assert.deepEqual(CR.mismatch('power', AC, DC), ['The ends differ: A is AC power, B is DC power.', 'Both ends are inlets: a power cable runs from an outlet to an inlet.']);
  assert.deepEqual(CR.mismatch('power', OUT, OUT), ['Both ends are outlets: a power cable runs from an outlet to an inlet.']);
  assert.deepEqual(CR.mismatch('power', OUT, P_), [], 'a direction one end does not state is not judged');
  // through the rack: a power cord into an RJ45, and a data cable into an inlet
  const rj = end('i1', 'rj-1', 'front');
  const rack = cabled(RACK, {a: INLET, b: rj, media: 'power'}, {a: end('i1', 'psu-2/module/terminal/lug-1'), b: OUT_F1, media: 'cat6a'});
  assert.deepEqual(await loose(rack), [], 'both land: a mismatch is a warning');
  assert.deepEqual((await Q.inspect(rack, 'c1', full(rack))).mismatch, ['The ends differ: A is power, B is copper.', 'Power cable does not suit end B, which is copper.']);
  assert.deepEqual((await Q.inspect(rack, 'c2', full(rack))).mismatch, ['Cat 6A copper does not suit end A, which is power.', 'Cat 6A copper does not suit end B, which is power.']);
  assert.deepEqual(await Q.suggestMedia(RACK, INLET, OUT_F1, full(RACK)), {media: 'power', warnings: []});
  assert.deepEqual(await Q.suggestMedia(RACK, end('i1', 'ground'), end('i2', 'ground'), full(RACK)), {media: 'ground', warnings: []});
  assert.deepEqual((await Q.suggestMedia(RACK, INLET, rj, full(RACK))).media, 'power', 'the first end that knows decides, as it did');
});

test('media power and ground go through the commands, the file and the schema', () => {
  assert.deepEqual(COMMANDS['cable.add'].args.properties.media.enum, ['', ...CR.MEDIA]);
  assert.match(run(RACK, [{op: 'cable.add', a: INLET, b: OUT_F1, media: 'mains'}]).error, /power, ground/);
  const rack = cabled(RACK, {a: INLET, b: OUT_F1, media: 'power', label: 'A feed'}, {a: end('i1', 'ground'), b: end('i2', 'ground'), media: 'ground'});
  assert.deepEqual(rack.cables.map(c => c.media), ['power', 'ground']);
  const text = M.serialize({format: 'portrayal-rack', version: 4, id: 'doc-power', racks: [rack]});
  const back = M.parseDoc(text);
  assert.deepEqual(back.racks[0].cables, rack.cables);
  assert.equal(M.serialize(back), text, 'saved, loaded and saved again is the same text');
  const schema = JSON.parse(readFileSync(new URL('../../schemas/rack.schema.json', import.meta.url)));
  assert.deepEqual(validate(schema, JSON.parse(text)), []);
  assert.deepEqual(run(rack, [{op: 'cable.update', id: 'c1', media: 'ground'}]).rack.cables[0].media, 'ground');
  assert.deepEqual(validate(schema, {...JSON.parse(text), racks: [{...JSON.parse(text).racks[0],
    cables: [{...JSON.parse(text).racks[0].cables[0], b: {item: 'i2', path: 'outlet-rear-2', view: 'rear', plug: 5}}]}]}).map(e => e.path.join('/')),
    ['racks/0/cables/0/b/plug'], 'a plug is a string');
  const blank = JSON.parse(text);
  blank.racks[0].cables[0].b.plug = '';
  assert.deepEqual(validate(schema, blank).map(e => e.keyword), ['minLength'], 'and not an empty one, as the command says');
  assert.equal(COMMANDS['cable.add'].args.properties.a.properties.plug.minLength, 1);
});

test('a version 4 file with no power in it loads and saves as it was', () => {
  const old = cabled(RACK, {a: end('i1', 'rj-1', 'front'), b: end('i1', 'port-1', 'front'), media: 'cat6a', label: 'old'});
  const text = M.serialize({format: 'portrayal-rack', version: 4, id: 'doc-old', racks: [old]});
  assert.equal(M.serialize(M.parseDoc(text)), text);
  assert.equal(/plug|power|ground/.test(JSON.stringify(JSON.parse(text).racks[0].cables)), false);
});

test('the tables every lay reads have a row for power, and a ground wire is marked where it is estimated', () => {
  assert.deepEqual([R.DIAMETERS.power, R.DIAMETERS.ground], [7.1, 6.3]);
  assert.deepEqual([R.PLUG_REACH.power, R.END_ALLOWANCE_BY_MEDIA.power, R.END_ALLOWANCE_BY_MEDIA.ground], [77.0, 0.017, 0]);
  assert.deepEqual([G.COLORS.power, G.COLORS.ground], ['#1c1c1c', '#3f9b4b']);
  assert.equal(G.colorOf({media: 'power'}), '#1c1c1c');
  for (const m of CR.MEDIA) assert.ok(R.DIAMETERS[m] > 0 && Object.hasOwn(R.END_ALLOWANCE_BY_MEDIA, m) && Object.hasOwn(G.COLORS, m), m);
  // the diameter and the radius are the cable types table's own (spec/schemas/cable-types.yaml)
  const yaml = readFileSync(new URL('../../schemas/cable-types.yaml', import.meta.url), 'utf8');
  const c13 = yaml.slice(yaml.indexOf('  power-c13:'), yaml.indexOf('  power-c19:'));
  assert.match(c13, /od_mm: 7\.1\n/);
  assert.match(c13, /installed: \{xOD: 6, basis: convention, sources: \[oznur-h05vv-f\], unverified: true/, 'the radius is unverified there, and the kit claims no more');
});

// ── free ports ───────────────────────────────────────────────────────────
const portsOf = async (item, view) => zonesOf(item.ref, view, P.cableEndPaths(item, view, ctx));
const before = async (item, view) => zonesOf(item.ref, view);

test('the paths a page asks zones for: every slot that takes a cable end, to any depth', () => {
  assert.deepEqual(P.cableEndPaths(RACK.items[0], 'rear', ctx).sort(),
    ['ground', 'psu-1/module/inlet', 'psu-2/module/terminal/lug-1', 'psu-2/module/terminal/lug-10', 'psu-2/module/terminal/lug-2', 'psu-3/module/inlet']);
  assert.deepEqual(P.cableEndPaths(RACK.items[0], 'front', ctx), ['rj-1'], 'the cage, the blind slot and the cap seat are not in it');
  assert.deepEqual(P.cableEndPaths(RACK.items[1], 'rear', ctx), ['input', 'outlet-rear-1', 'outlet-rear-2', 'ground']);
  assert.deepEqual(P.cableEndPaths(RACK.items[2], 'rear', ctx), []);
  assert.deepEqual(P.cableEndPaths(RACK.items[0], 'rear', {}), [], 'nothing without the catalogue');
});

test('free ports list power and ground ends with words a person reads, and the ports exactly as before', async () => {
  const old = await Q.freePorts(RACK, 'i1', {...ctx, portsOf: before});
  const was = old.filter(p => !p.kind);
  assert.deepEqual(was, [{path: 'port-1', view: 'front', label: 'port 1', media: 'sfp', speed: null},
                         {path: 'rj-1', view: 'front', label: 'rj 1', media: 'rj45', speed: null}]);
  // a reader that hands in no slot still has the catalogue's (P-0019): the supplies' inlets and terminals
  assert.deepEqual(old.filter(p => p.kind === 'power').map(p => [p.path, p.connector]), [
    ['psu-1/module/inlet', 'C14 inlet'], ['psu-2/module/terminal/lug-1', 'terminal-stud inlet'], ['psu-2/module/terminal/lug-2', 'terminal-stud inlet'],
    ['psu-2/module/terminal/lug-10', 'terminal-stud inlet'], ['psu-3/module/inlet', 'C14 inlet']]);
  // and never a data slot (rj-1 is the reader's to list) nor a slot whose part says nothing
  assert.deepEqual(old.filter(p => p.kind && p.kind !== 'power'), []);
  const now = await Q.freePorts(RACK, 'i1', {...ctx, portsOf});
  assert.deepEqual(now.filter(p => !p.kind), was, 'every port of class port is the same entry, key for key');
  assert.deepEqual(await Q.freePorts(RACK, 'i1', {...ctx, portsOf}, {kinds: ['data']}), was, 'and a data picker gets only those');
  assert.deepEqual(now.filter(p => p.kind).map(p => [p.path, p.view, p.kind, p.connector, p.plug]), [
    ['psu-1/module/inlet', 'rear', 'power', 'C14 inlet', C13],
    ['psu-2/module/terminal/lug-1', 'rear', 'power', 'terminal-stud inlet', LUG],
    ['psu-2/module/terminal/lug-2', 'rear', 'power', 'terminal-stud inlet', LUG],
    ['psu-2/module/terminal/lug-10', 'rear', 'power', 'terminal-stud inlet', LUG],
    ['psu-3/module/inlet', 'rear', 'power', 'C14 inlet', C13],
    ['ground', 'rear', 'ground', 'terminal-stud ground', LUG]]);
  // the screws of one terminal are one group, and the first is the one a feed takes
  assert.deepEqual(now.filter(p => p.of).map(p => [p.path.split('/').pop(), p.of, p.first ?? false]),
    [['lug-1', 'psu-2/module/terminal', true], ['lug-2', 'psu-2/module/terminal', false], ['lug-10', 'psu-2/module/terminal', false]]);
  assert.deepEqual(now.find(p => p.path === 'psu-1/module/inlet'),
    {path: 'psu-1/module/inlet', view: 'rear', label: 'psu 1 inlet', media: 'ac', speed: null, kind: 'power', connector: 'C14 inlet', plug: C13});
  // the PDU: outlets against its inlet, by what each part says
  const pdu = await Q.freePorts(RACK, 'i2', {...ctx, portsOf}, {kinds: ['power']});
  assert.deepEqual(pdu.map(p => [p.path, p.view, p.connector]), [['outlet-front-1', 'front', 'C13 outlet'], ['outlet-front-2', 'front', 'C13 outlet'],
    ['input', 'rear', 'C20 inlet'], ['outlet-rear-1', 'rear', 'C19 outlet'], ['outlet-rear-2', 'rear', 'acme-t-slot outlet']]);
  assert.deepEqual((await Q.freePorts(RACK, 'i2', {...ctx, portsOf}, {kinds: ['ground']})).map(p => p.path), ['ground']);
  // every offered end is one cable.add takes and that lands; a cabled one is no longer free
  for (const p of [...now, ...pdu]) {
    const r = cabled(RACK, {a: {item: p.kind && pdu.includes(p) ? 'i2' : 'i1', path: p.path, view: p.view}, b: end('i3', 'outlet-1')});
    assert.equal((await loose(r)).some(l => l.startsWith('c1 a')) && p.path !== 'port-1', false, p.path);
  }
  const used = cabled(RACK, {a: INLET, b: OUT_F1, media: 'power'});
  assert.equal((await Q.freePorts(used, 'i1', {...ctx, portsOf})).some(p => p.path === 'psu-1/module/inlet'), false);
  assert.equal((await Q.freePorts(used, 'i2', {...ctx, portsOf})).some(p => p.path === 'outlet-front-1'), false);
  // a slot the reader names and the catalogue does not have is not offered, and neither is one without the catalogue
  const stray = async (item, view) => [...(await portsOf(item, view)), {id: 'x', cls: 'inlet', path: 'outlet-9', end: true, ref: 'std/nema-5-20r@1'}];
  assert.equal((await Q.freePorts(RACK, 'i3', {...ctx, portsOf: stray})).length, 0);
  assert.deepEqual(await Q.freePorts(RACK, 'i1', {portsOf}), was);
  assert.match((await Q.freePorts(RACK, 'i1', {...ctx, portsOf}, {kinds: ['mains']})).error, /kinds is a list of data, power, ground, other/);
});

// ── zones ────────────────────────────────────────────────────────────────
const g = (a, c = []) => ({t: 'g', a, c});
const rect = (x, y, w, h) => ({t: 'rect', a: {x, y, width: w, height: h}, c: []});
const FACE = {t: 'svg', a: {viewBox: '0 0 440 44'}, c: [
  g({id: 'psu-2', 'data-class': 'bay', 'data-path': 'psu-2'}, [rect(300, 2, 70, 40),
    g({id: 'psu-2--module', 'data-class': 'psu', 'data-path': 'psu-2/module', 'data-ref': 'acme/psu-dc@1:1.0.0'}, [
      g({id: 'psu-2--module--terminal', 'data-class': 'inlet', 'data-path': 'psu-2/module/terminal', 'data-ref': 'common/dc-terminal@1:1.0.0', 'data-media': 'dc-terminal'}, [
        g({id: 'psu-2--module--terminal--lug-1', 'data-class': 'screw', 'data-path': 'psu-2/module/terminal/lug-1', 'data-ref': 'common/terminal-screw@1:1.0.0'}, [rect(310, 10, 6, 6)]),
        g({id: 'psu-2--module--terminal--lug-2', 'data-class': 'screw', 'data-path': 'psu-2/module/terminal/lug-2', 'data-ref': 'common/terminal-screw@1:1.0.0'}, [rect(320, 10, 6, 6)])])])]),
  g({id: 'input', 'data-class': 'inlet', 'data-path': 'input', 'data-ref': 'std/c20-inlet@1:1.4.0', 'data-media': 'ac'}, [rect(10, 10, 32, 24),
    g({id: 'input--pin', 'data-class': 'screw', 'data-path': 'input/pin'}, [rect(12, 12, 2, 2)])]),
  g({id: 'outlet-9', 'data-class': 'inlet', 'data-path': 'outlet-9', 'data-ref': 'std/nema-5-20r@1:1.0.1'}, [rect(60, 10, 27, 27)]),
  g({id: 'rj-1', 'data-class': 'port', 'data-path': 'rj-1', 'data-media': 'rj45'}, [rect(100, 10, 12, 10)])]};

test('zones: the slots a cable lands on are read where the caller names them, and nothing changes where it does not', () => {
  const plain = Z.readSvg(JSON.stringify(FACE), {layout: false}).zones;
  assert.deepEqual(plain.map(z => [z.id, z.cls]), [['psu-2', 'bay'], ['rj-1', 'port']], 'as it always was: ports and bays');
  const ends = ['input', 'input/pin', 'psu-2/module/terminal/lug-1', 'psu-2/module/terminal/lug-2', 'rj-1'];
  const zones = Z.readSvg(JSON.stringify(FACE), {layout: false, ends}).zones;
  assert.deepEqual(zones.map(z => [z.id, z.cls, z.end ?? false, z.ref ?? null]), [
    ['psu-2', 'bay', false, null],
    ['psu-2--module--terminal--lug-1', 'screw', true, 'common/terminal-screw@1'], ['psu-2--module--terminal--lug-2', 'screw', true, 'common/terminal-screw@1'],
    // the outermost wins: a slot inside a slot is part of it
    ['input', 'inlet', true, 'std/c20-inlet@1'],
    ['rj-1', 'port', false, null]]);
  assert.deepEqual(zones.filter(z => !z.end), plain, 'the ports and bays are the same objects, key for key');
  const input = zones.find(z => z.id === 'input');
  assert.deepEqual([input.path, input.media, input.x, input.y, input.w, input.h], ['input', 'ac', 10, 10, 32, 24]);
  assert.deepEqual(Z.portsOf(zones).map(z => z.id), ['rj-1', 'input', 'psu-2--module--terminal--lug-1', 'psu-2--module--terminal--lug-2']);
  assert.deepEqual(Z.portsOf(zones, {bays: true}).map(z => z.id)[0], 'psu-2', 'a bay is still first, under what it holds');
  assert.deepEqual(Z.portsOf(plain).map(z => z.id), ['rj-1']);
});

// ── the schedule, the bill of materials, the DCIM file ───────────────────
test('the schedule and the bill of materials read sensibly for a cord, and no plug is a line', async () => {
  const rack = cabled(RACK, {a: INLET, b: OUT_F1, media: 'power', label: 'PSU 1', length: {value: 2, unit: 'm'}},
    {a: end('i1', 'ground'), b: end('i2', 'ground'), media: 'ground'}, {a: LUG1, b: OUT_R1, media: 'power', length: {value: 2, unit: 'm'}});
  const facts = await oldPage()(rack);
  const {rows} = X.cableScheduleRows(rack, facts.ends, rack.items, null, {parts: full(rack)});
  assert.deepEqual(rows.map(r => [r.cable, r.a_port, r.b_port, r.media, r.status, r.notes]), [
    ['PSU 1', 'psu-1/module/inlet', 'outlet-front-1', 'Power cable', 'connected', ''],
    ['c2', 'ground', 'ground', 'Ground wire', 'connected', ''],
    ['c3', 'psu-2/module/terminal/lug-1', 'outlet-rear-1', 'Power cable', 'connected', '']]);
  const bom = X.cableBomRows(rack, facts.ends, {parts: full(rack)});
  assert.deepEqual(bom.map(l => [l.qty, l.model, l.description]), [
    [1, 'Ground wire', 'length not set; ground at both ends'], [2, 'Power cable', '2 m; power at both ends']]);
  assert.equal(bom.some(l => /plug|lug/i.test(`${l.model} ${l.ref}`)), false, 'a cord end is part of the cord');
  // a page that says nothing of what is drawn: the connector it knows of, never a wrong one
  assert.deepEqual(X.cableBomRows(rack, facts.ends, {parts: ctx}).map(l => l.description),
    ['length not set', '2 m; power at one end']);
});

test('the DCIM cables file never drops a power cable or a ground wire without saying so', async () => {
  const rack = cabled(RACK, {a: INLET, b: OUT_F1, media: 'power', label: 'PSU 1'}, {a: end('i1', 'ground'), b: end('i2', 'ground'), media: 'ground', label: 'bond'});
  const facts = await oldPage()(rack);
  const names = X.uniqueNames(rack.items), kept = new Set(rack.items.map(i => i.id));
  const args = {rack, names, kept, ends: facts.ends, uOf: () => 1, parts: full(rack)};
  // type files that name neither end, as the library's do today
  const none = D.cableImportRows({...args, resolve: e => ({ok: false, reason: `the device type lists no port named ${e.path}`})});
  assert.equal(none.rows.length, 0);
  assert.deepEqual(none.left, [
    'Cable PSU 1 is not in the cables file: end A, sw-1 (U30) psu-1/module/inlet: the device type lists no port named psu-1/module/inlet; end B, pdu-1 (U20) outlet-front-1: the device type lists no port named outlet-front-1.',
    'Cable bond is not in the cables file: it is a ground wire, and a DCIM has no termination for a ground stud.']);
  // type files that do name them: the row is written, and its blank type is said
  const named = D.cableImportRows({...args, resolve: e => ({ok: true, name: e.path, type: e.item === 'i1' ? 'dcim.powerport' : 'dcim.poweroutlet'})});
  assert.deepEqual(named.rows.map(r => [r.side_a_type, r.side_b_type, r.type]), [['dcim.powerport', 'dcim.poweroutlet', '']]);
  assert.deepEqual(named.notes, ['Cable PSU 1: its media (power) has no NetBox cable type, so its type is blank.']);
  assert.equal(named.left.length, 1);
});
