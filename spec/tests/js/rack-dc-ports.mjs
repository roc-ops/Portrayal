// spec/tests/js/rack-dc-ports.mjs
// A DC PORT IS SOMETHING A CABLE LANDS ON (docs/dc-power-design.md sections 5.2
// and 5.4): its address is the part's path and its id, a pole's is its slot, and
// the poles are taken together. The catalogue is dc-ports-fixture.mjs; the
// power-ends fixture is the catalogue that states no DC port at all.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as Q from '../../../kit/rack/queries.js';
import * as CR from '../../../kit/rack/cable-rules.js';
import * as P from '../../../kit/rack/ports.js';
import {configFacts} from '../../../kit/rack/catalog.js';
import {apply} from '../../../kit/rack/commands.js';
import {ctx, SLOTS, LUG, PSU_48, PSU_48B, PSU_Q, P40_PLUG, TWO_HOLE} from './dc-ports-fixture.mjs';
import * as PE from './power-ends-fixture.mjs';

const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'base', ru, label: extra.label ?? ref, ...extra}).rack;
const end = (item, path, view = 'rear') => ({item, path, view});
// dc-1 (i1) U30, panel-1 (i2) U25, split-1 (i3) U20, nest-1 (i4) U15, twin-1 (i5) U10, sw-1 (i6) U5, pdu-1 (i7) U40
let RACK = M.newRack();
for (const [ref, ru] of [['dc', 30], ['panel', 25], ['split', 20], ['nest', 15], ['twin', 10], ['sw', 5], ['pdu', 40]]) RACK = add(RACK, ref, ru, {label: `${ref}-1`});
const [DC, PANEL, SPLIT, NEST, TWIN, SW, PDU] = RACK.items;
const run = (rack, cmds, c = ctx) => apply(rack, cmds, c);
const cabled = (rack, ...cables) => run(rack, cables.map(c => ({op: 'cable.add', ...c}))).rack;
const full = rack => ({...ctx, cableFacts: PE.oldPage(), drawnAt: PE.drawnAt(rack)});
const loose = async (rack, c = full(rack)) => (await Q.looseEnds(rack, c)).ends.map(e => `${e.cable} ${e.side}: ${e.reason}`);
const OUT = end('i7', 'outlet-front-1', 'front'), OUT2 = end('i7', 'outlet-front-2', 'front'), PDU_IN = end('i7', 'input');
const PORT = end('i1', 'psu-0/module/input'), RTN = end('i1', 'psu-0/module/terminal-rtn'), BATT = end('i1', 'psu-0/module/terminal-48v');
const dcOf = (item, path) => P.dcPortsOf(item, ctx).find(p => p.path === path);
const slim = p => ({path: p.path, view: p.view, kind: p.kind, side: p.side, poles: p.poles.map(q => [q.role, q.path])});
const NO_DC = rack => ({...PE.ctx, cableFacts: PE.oldPage(), drawnAt: PE.drawnAt(rack)});

// ── 1: configFacts ───────────────────────────────────────────────────────
test('configFacts carries dcPorts for a configuration that states one, and no key for one that does not', () => {
  const stated = configFacts(SLOTS.panel, 'base'), none = configFacts(SLOTS.panel, 'bare');
  assert.deepEqual(stated.dcPorts.map(p => p.path), ['output-a1/output', 'output-b1/output', 'feed-a/input']);
  assert.equal(Object.hasOwn(none, 'dcPorts'), false, 'a configuration that states none has no key');
  assert.equal(Object.hasOwn(configFacts(PE.SLOTS.sw, 'base'), 'dcPorts'), false);
});

// ── 2: the DC ports of a rack item ───────────────────────────────────────
test('a part in a bay: the seated component\'s ports, joined under <bay>/module, through the bay\'s default and the item\'s swaps', () => {
  assert.deepEqual(P.dcPortsOf(DC, ctx).map(slim), [
    {path: 'psu-0/module/input', view: 'rear', kind: 'slots', side: null, poles: [['rtn', 'psu-0/module/terminal-rtn'], ['batt', 'psu-0/module/terminal-48v']]},
    {path: 'psu-1/module/input', view: 'rear', kind: 'slots', side: null, poles: [['rtn', 'psu-1/module/terminal/lug-1'], ['batt', 'psu-1/module/terminal/lug-2']]},
    {path: 'psu-2/module/input', view: 'rear', kind: 'slots', side: null, poles: [['unstated', 'psu-2/module/t1'], ['unstated', 'psu-2/module/t2']]}],
  'psu-1 is left to its default, and psu-3 holds nothing');
  assert.equal(dcOf(DC, 'psu-2/module/input').poles[0]['stand-in'].order, 1);
  assert.deepEqual([dcOf(DC, 'psu-0/module/input').ref, dcOf(DC, 'psu-0/module/input')['rating-a']], [PSU_48, 18]);
  // a swap seats the other supply, whatever the configuration seats: its ports, its rating, its poles the other way about
  const swapped = add(M.newRack(), 'dc', 30, {swaps: {'psu-0': PSU_48B, 'psu-2': null}}).items[0];
  assert.deepEqual(P.dcPortsOf(swapped, ctx).map(slim)[0],
    {path: 'psu-0/module/input', view: 'rear', kind: 'slots', side: null, poles: [['batt', 'psu-0/module/post-a'], ['rtn', 'psu-0/module/post-b']]});
  assert.equal(dcOf(swapped, 'psu-0/module/input')['rating-a'], 40);
  assert.deepEqual(P.dcPortsOf(swapped, ctx).map(p => p.path), ['psu-0/module/input', 'psu-1/module/input'], 'a bay swapped empty has none');
  // a bay of a part in a bay
  assert.deepEqual(P.dcPortsOf(NEST, ctx).map(slim), [{path: 'carrier/module/sub/module/input', view: 'rear', kind: 'slots', side: null,
    poles: [['rtn', 'carrier/module/sub/module/terminal-rtn'], ['batt', 'carrier/module/sub/module/terminal-48v']]}]);
  assert.deepEqual(P.dcPortsOf(DC, {}), [], 'nothing without the catalogue');
  assert.deepEqual(P.dcPortsOf(DC, {slotsOf: ctx.slotsOf}), []);
});

test('a part placed on the device: the configuration\'s ports, the placement\'s override applied, and each port\'s kind and panel', () => {
  assert.deepEqual(P.dcPortsOf(PANEL, ctx).map(p => [p.path, p.kind, p.side, p.view, p.direction, p.part, p.connector]), [
    ['feed-a/input', 'slots', 'b', 'rear', 'input', 'feed-a', null],
    ['output-a1/output', 'points', 'a', 'rear', 'output', 'output-a1', 'output-a1'],
    ['output-b1/output', 'points', 'b', 'rear', 'output', 'output-b1', 'output-b1']]);
  assert.deepEqual(dcOf(PANEL, 'output-a1/output').poles.map(q => [q.role, q.path]), [['batt', 'output-a1/wire-1'], ['rtn', 'output-a1/wire-2']]);
  assert.deepEqual(P.dcPortsOf(add(M.newRack(), 'panel', 5, {cfg: 'bare'}).items[0], ctx), [], 'a configuration that presents none');
  // poles on two panels: the port is there, with no panel; nothing is guessed
  assert.deepEqual(P.dcPortsOf(SPLIT, ctx).map(p => [p.path, p.view, p.lands]), [['half/input', null, true]]);
  // a connector two ports share is kind points for both
  assert.deepEqual(P.dcPortsOf(TWIN, ctx).map(p => [p.path, p.kind]), [['shared/a', 'points'], ['shared/b', 'points']]);
  // neither kind: a pole that resolves to nothing, or some slots and some contacts, is left out
  const bad = {...SLOTS.panel, configs: [{...SLOTS.panel.configs[0], 'dc-ports': [
    {...SLOTS.panel.configs[0]['dc-ports'][2], poles: [{role: 'rtn', slot: 'feed-a/lug-1'}, {role: 'batt', slot: 'feed-a/nothing'}]},
    {...SLOTS.panel.configs[0]['dc-ports'][2], id: 'mixed', path: 'output-a1/mixed', poles: [{role: 'rtn', slot: 'feed-a/lug-1'}, {role: 'batt', slot: 'output-a1/wire-1'}]}]}]};
  assert.deepEqual(P.dcPortsOf(PANEL, {...ctx, slotsOf: ref => (ref === 'panel' ? bad : SLOTS[ref] ?? null)}), []);
});

// ── 3 and 4: landing ─────────────────────────────────────────────────────
test('a feed to a port path lands, and the end is the power end it is, with its poles in order', async () => {
  const rack = cabled(RACK, {a: PORT, b: OUT, media: 'power'});
  assert.deepEqual(await loose(rack), []);
  const at = P.seatedPort(rack.items[0], PORT, ctx);
  assert.deepEqual([at.port, at.slot, at.cage, at.onView, at.holder.part, at.holder.path], [true, true, false, 'rear', 'PSU-48', 'psu-0']);
  assert.deepEqual(at.info, {family: 'power', mode: 'dc', role: 'inlet', plug: LUG, connector: 'input, RTN / BATT, -48 V, 18 A',
    dc: {path: 'psu-0/module/input', end: 'port', kind: 'slots', connector: null, direction: 'input', voltage: {nominal: -48, range: [-44, -65]}, 'rating-a': 18, awg: [12], side: null,
         poles: [{role: 'rtn', path: 'psu-0/module/terminal-rtn', plug: LUG}, {role: 'batt', path: 'psu-0/module/terminal-48v', plug: LUG}]}});
  // it is named on the other panel only by a sentence that says which
  const wrong = {...RACK, cables: [{id: 'c1', a: end('i1', 'psu-0/module/input', 'front'), b: OUT, media: 'power', purpose: '', label: '', route: []}]};
  assert.deepEqual(await loose(wrong), ['c1 a: psu-0/module/input is on the rear panel; give view "rear"']);
  assert.match(run(RACK, [{op: 'cable.add', a: end('i1', 'psu-0/module/input', 'front'), b: OUT}]).error, /is on the rear panel; give view "rear"/);
  // an empty bay and a port the part does not state are as they were
  assert.deepEqual(await loose(cabled(RACK, {a: end('i1', 'psu-3/module/input'), b: OUT})), ['c1 a: psu-3 is empty']);
  // a placed slots port lands from the configuration, with what the page read of the panel (nothing) and the placement's side
  const placed = cabled(RACK, {a: end('i2', 'feed-a/input'), b: OUT});
  assert.deepEqual(await loose(placed), []);
  const own = P.ownSlot(placed.items[1], end('i2', 'feed-a/input'), ctx);
  assert.deepEqual(own.facts, {port: true, slot: true, cage: false, occupied: false, onView: 'rear'});
  assert.deepEqual([own.info.role, own.info.mode, own.info.dc.side, own.info.dc.end, own.info.connector], ['inlet', 'dc', 'b', 'port', 'input, RTN / BATT, -48 V, 18 A, side B']);
  // the settled end is what the cable list reads
  const settled = P.settleEnds(rack, new Map(), ctx).get(CR.endKey(PORT));
  assert.equal(settled.reason, null);
  assert.equal(settled.info.dc.end, 'port');
});

test('a single conductor on a pole slot lands as it does today and reads as the pole it is', async () => {
  const rack = cabled(RACK, {a: RTN, b: OUT, media: 'power'});
  assert.deepEqual(await loose(rack), []);
  const info = P.seatedPort(rack.items[0], RTN, ctx).info;
  assert.deepEqual({...info, dc: undefined}, {family: 'power', mode: 'dc', role: 'inlet', plug: LUG, connector: 'terminal-stud inlet', dc: undefined},
    'the same family, direction, plug and words as before');
  assert.deepEqual([info.dc.end, info.dc.pole, info.dc.role, info.dc.path, info.dc.poles[info.dc.pole].role], ['pole', 0, 'rtn', 'psu-0/module/input', 'rtn']);
  assert.equal(P.seatedPort(rack.items[0], BATT, ctx).info.dc.pole, 1);
});

// ── 5, 6 and 7: the three readings of an end saved before a part states a port ──
test('compat 1: an end saved on a screw keeps its path, lands as before, reads as a pole, and its port is partly used', async () => {
  const LUG1 = end('i1', 'psu-1/module/terminal/lug-1');
  const saved = {format: 'portrayal-rack', version: 4, id: 'doc-dc', racks: [{...RACK, id: 'r1',
    cables: [{id: 'c1', a: LUG1, b: OUT, media: 'power', purpose: '', label: '', route: []}]}]};
  const text = M.serialize(M.parseDoc(JSON.parse(JSON.stringify(saved))));
  const rack = M.parseDoc(JSON.parse(text)).racks[0];
  assert.deepEqual(rack.cables[0].a, LUG1, 'the path is byte-identical after parseDoc and save');
  assert.equal(M.serialize({format: 'portrayal-rack', version: 4, id: 'doc-dc', racks: [rack]}), text);
  assert.deepEqual(await loose(rack), [], 'it lands');
  // no command that does not name the end moves it
  const edited = run(rack, [{op: 'cable.update', id: 'c1', label: 'kept', media: 'power'}]).rack;
  assert.deepEqual(edited.cables[0].a, LUG1);
  const info = P.seatedPort(rack.items[0], LUG1, ctx).info;
  assert.deepEqual([info.dc.end, info.dc.pole, info.dc.role, info.family, info.mode, info.plug], ['pole', 0, 'rtn', 'power', 'dc', LUG]);
  // the port is partly used: a feed to it is refused, naming the cable and its pole
  assert.equal(run(rack, [{op: 'cable.add', a: end('i1', 'psu-1/module/input'), b: OUT2, media: 'power'}]).error,
    'dc-1 (U30) psu-1/module/input already has a cable (c1 on its RTN pole).');
});

test('compat 2: an end saved on a connector slot is the part\'s one DC port on its contacts, and shares its occupancy', async () => {
  const A1 = end('i2', 'output-a1');
  const rack = cabled(RACK, {a: A1, b: PDU_IN, media: 'power'});
  assert.deepEqual(await loose(rack), [], 'it lands, as it did');
  const mine = P.ownSlot(rack.items[1], A1, ctx);
  assert.deepEqual(mine.facts, {port: true, slot: true, cage: false, occupied: false, onView: 'rear'});
  assert.deepEqual([mine.info.plug, mine.info.family, mine.info.connector], [P40_PLUG, null, 'p40 connector'], 'the slot rule\'s own answer, unchanged');
  assert.deepEqual([mine.info.dc.end, mine.info.dc.path, mine.info.dc.direction, mine.info.dc.side, mine.info.dc.kind], ['connector', 'output-a1/output', 'output', 'a', 'points']);
  assert.deepEqual(mine.info.dc.poles, [{role: 'batt', path: 'output-a1/wire-1', plug: P40_PLUG}, {role: 'rtn', path: 'output-a1/wire-2', plug: P40_PLUG}]);
  // a feed to the port is refused as taken, and the other connector is free
  assert.equal(run(rack, [{op: 'cable.add', a: end('i2', 'output-a1/output'), b: OUT}]).error, 'panel-1 (U25) output-a1/output already has a cable (c1).');
  assert.equal(run(rack, [{op: 'cable.add', a: end('i2', 'output-b1/output'), b: OUT}]).error, undefined);
  // a part with no DC port, and a connector with two on its contacts, land it as a plain slot with no `dc`
  const bare = add(M.newRack(), 'panel', 25, {cfg: 'bare'});
  assert.equal('dc' in P.ownSlot(bare.items[0], A1, ctx).info, false);
  const shared = P.ownSlot(TWIN, end('i5', 'shared'), ctx);
  assert.equal(shared.facts.port, true);
  assert.equal('dc' in shared.info, false);
});

test('compat 3: an end on the terminal\'s own path names the DC port to give; a terminal with no DC port keeps the screws sentence', async () => {
  const T = end('i1', 'psu-1/module/terminal');
  assert.deepEqual(await loose(cabled(RACK, {a: T, b: OUT, media: 'power'})),
    ['c1 a: psu-1 holds PSU-TERM, whose terminal takes a cable on the port psu-1/module/input and not on itself; give the path psu-1/module/input']);
  const taken = cabled(RACK, {a: end('i1', 'psu-1/module/input'), b: OUT2, media: 'power'}, {a: T, b: OUT});
  assert.deepEqual(await loose(taken), ['c2 a: psu-1 holds PSU-TERM, whose terminal takes a cable on its ports and not on itself, and every port of its terminal has a cable']);
  const screws = cabled(RACK, {a: end('i6', 'psu-2/module/terminal'), b: OUT, media: 'power'});
  assert.deepEqual(await loose(screws),
    ['c1 a: psu-2 holds PSU-DC, whose terminal takes a cable on lug-1, lug-2, lug-10 and not on itself; give the path psu-2/module/terminal/lug-1']);
});

// ── 8: a contact is no end ───────────────────────────────────────────────
test('a contact of a points port is loose, and cable.add refuses it in the same words', async () => {
  const C = end('i2', 'output-a1/wire-1');
  const why = 'output-a1/wire-1 is a contact of output-a1, whose connector takes acme/p40-plug@1; give the path output-a1/output';
  const added = run(RACK, [{op: 'cable.add', a: C, b: OUT}]);
  assert.equal(added.error, `${why}.`);
  // a rack file that holds one is kept, and its end reads loose
  const held = {...RACK, cables: [{id: 'c1', a: C, b: OUT, media: 'power', purpose: '', label: '', route: []}]};
  assert.deepEqual(await loose(held), [`c1 a: ${why}`]);
});

// ── 9: one cable per port ────────────────────────────────────────────────
test('one cable per port, across the port, its poles and its connector', () => {
  const dc = P.dcReader(RACK, ctx);
  const on = (...cs) => ({...RACK, cables: cs.map(([id, a, b]) => ({id, a, b, media: 'power', purpose: '', label: '', route: []}))});
  const second = on(['c1', RTN, OUT]);
  const feed = CR.portFree(second, PORT, {dc: P.dcReader(second, ctx)});
  assert.equal(feed.ok, false);
  assert.match(feed.reason, /already has a cable \(c1 on its RTN pole\)/);
  assert.equal(CR.portFree(second, BATT, {dc: P.dcReader(second, ctx)}).ok, true, 'the other pole is free');
  assert.equal(CR.portFree(second, RTN, {dc: P.dcReader(second, ctx)}).ok, false, 'the pole that has a cable');
  // a pole of a cabled port is refused, naming that cable
  const whole = on(['c1', PORT, OUT]);
  assert.match(CR.portFree(whole, BATT, {dc: P.dcReader(whole, ctx)}).reason, /already has a cable \(c1\)/);
  assert.equal(CR.portFree(whole, BATT).ok, true, 'without the reader, as before');
  // two single-conductor runs to two poles of one port are both accepted
  const two = run(RACK, [{op: 'cable.add', a: RTN, b: OUT, media: 'power'}, {op: 'cable.add', a: BATT, b: OUT2, media: 'power'}]);
  assert.equal(two.error, undefined);
  assert.equal(two.rack.cables.length, 2);
  // a cable from a port to one of its own poles is refused
  assert.equal(CR.canCable(RACK, PORT, RTN, {dc}).reason, 'A cable needs two different ports.');
  assert.equal(CR.canCable(RACK, PORT, RTN).ok, true, 'and without the reader there is no such question');
  assert.equal(CR.canCable(RACK, PORT, OUT, {dc}).ok, true);
  // moving an end onto a port its own cable is on is not a conflict
  const moved = run(whole, [{op: 'cable.update', id: 'c1', a: end('i1', 'psu-0/module/input-occupant')}]);
  assert.equal(moved.error, undefined);
  // the reader answers for DC ends only, and an end named on the wrong panel is none
  assert.equal(dc(OUT), null);
  assert.equal(dc(end('i1', 'psu-0/module/input', 'front')), null);
  assert.equal(dc(end('i2', 'output-a1/wire-1')), null, 'a contact is no end');
});

// ── 10: the free-port rows ───────────────────────────────────────────────
const portsOf = async () => [];
const free = (rack, id, opts) => Q.freePorts(rack, id, {...ctx, portsOf}, opts);
test('free ports: one row per free DC port, with its poles under it; none for the screws or the connector while it is free', async () => {
  const all = await free(RACK, 'i1'), rows = all.filter(r => r.dc);
  assert.deepEqual(rows.map(r => r.path), ['psu-0/module/input', 'psu-1/module/input', 'psu-2/module/input']);
  // the screw of psu-1's terminal that is no pole of the port is a screw still, with its group
  assert.deepEqual(all.filter(r => !r.dc).map(r => [r.path, r.of, r.first]), [['psu-1/module/terminal/lug-10', 'psu-1/module/terminal', true]]);
  assert.deepEqual(rows[0], {path: 'psu-0/module/input', view: 'rear', label: 'psu 0 input', media: null, speed: null, kind: 'power',
    connector: 'input, RTN / BATT, -48 V, 18 A', plug: LUG,
    dc: {direction: 'input', voltage: {nominal: -48, range: [-44, -65]}, 'rating-a': 18, awg: [12], side: null,
         poles: [{role: 'rtn', path: 'psu-0/module/terminal-rtn', plug: LUG}, {role: 'batt', path: 'psu-0/module/terminal-48v', plug: LUG}]}});
  assert.equal(rows.some(r => 'of' in r || 'first' in r), false, 'no `of` or `first` on a DC row');
  assert.deepEqual(rows[2].dc.poles.map(q => q.role), ['unstated', 'unstated']);
  // a points port is one row, on its panel, and not its connector
  const panel = await free(RACK, 'i2');
  assert.deepEqual(panel.map(r => [r.path, r.view, r.plug, r.connector]), [
    ['feed-a/input', 'rear', LUG, 'input, RTN / BATT, -48 V, 18 A, side B'],
    ['output-a1/output', 'rear', P40_PLUG, 'output, BATT / RTN, -48 V, 30 A, side A'],
    ['output-b1/output', 'rear', P40_PLUG, 'output, BATT / RTN, -48 V, 30 A, side B']]);
  assert.equal(panel.some(r => r.path === 'output-a1' || r.path.endsWith('/wire-1')), false);
  // every row is an end cable.add takes and that lands
  for (const r of [...rows, ...panel]) {
    const id = rows.includes(r) ? 'i1' : 'i2';
    assert.equal(run(RACK, [{op: 'cable.add', a: end(id, r.path, r.view), b: OUT}]).error, undefined, r.path);
  }
  // a port with no panel is neither offered nor landed
  assert.deepEqual(await free(RACK, 'i3'), []);
  const half = {...RACK, cables: [{id: 'c1', a: end('i3', 'half/input'), b: OUT, media: 'power', purpose: '', label: '', route: []}]};
  assert.deepEqual(await loose(half), ['c1 a: half/input is not on this panel'], 'the page\'s own answer stands: the kit does not land it');
  // kinds and type
  assert.deepEqual(await free(RACK, 'i1', {kinds: ['data']}), []);
  assert.deepEqual((await free(RACK, 'i1', {kinds: ['power']})).filter(r => r.dc).map(r => r.path), rows.map(r => r.path));
  assert.deepEqual(await free(RACK, 'i1', {type: 'C13'}), []);
  // slotEnds agrees
  assert.deepEqual(Q.slotEnds(DC, ctx).map(e => [e.path, e.kind, e.connector, e.plug]),
    [['psu-1/module/terminal/lug-10', 'power', 'terminal-stud inlet', LUG], ...rows.map(r => [r.path, r.kind, r.connector, r.plug])]);
  assert.deepEqual(Q.slotEnds(PANEL, ctx).map(e => e.path), panel.map(r => r.path));
});

test('free ports: a partly used port is no row, and each of its free poles is a row of its own', async () => {
  const one = cabled(RACK, {a: BATT, b: OUT, media: 'power'});
  const rows = (await free(one, 'i1')).filter(r => r.path !== 'psu-1/module/terminal/lug-10');
  assert.deepEqual(rows.map(r => r.path), ['psu-1/module/input', 'psu-2/module/input', 'psu-0/module/terminal-rtn'],
    'the free pole follows the whole ports of its panel, as a row of its own');
  assert.deepEqual(rows[2], {path: 'psu-0/module/terminal-rtn', view: 'rear', label: 'psu 0 terminal rtn', media: null, speed: null, kind: 'power',
    connector: 'input RTN pole', plug: LUG,
    dc: {direction: 'input', voltage: {nominal: -48, range: [-44, -65]}, 'rating-a': 18, awg: [12], side: null,
         poles: [{role: 'rtn', path: 'psu-0/module/terminal-rtn', plug: LUG}, {role: 'batt', path: 'psu-0/module/terminal-48v', plug: LUG}],
         pole: {port: 'psu-0/module/input', role: 'rtn'}}});
  assert.equal('of' in rows[2] || 'first' in rows[2], false);
  // a whole feed leaves neither the port nor a pole
  const whole = cabled(RACK, {a: PORT, b: OUT, media: 'power'});
  assert.deepEqual((await free(whole, 'i1')).filter(r => r.dc).map(r => r.path), ['psu-1/module/input', 'psu-2/module/input']);
  // a cable on a connector slot (the P40 form) takes the port
  const conn = cabled(RACK, {a: end('i2', 'output-a1'), b: OUT, media: 'power'});
  assert.deepEqual((await free(conn, 'i2')).map(r => r.path), ['feed-a/input', 'output-b1/output']);
});

// ── 11: the plug per pole ────────────────────────────────────────────────
test('the plug per pole: each slot\'s own, the connector\'s on every contact, and a stated plug a pole does not take says so', () => {
  const swapped = add(M.newRack(), 'dc', 30, {swaps: {'psu-0': PSU_48B}});
  const mixed = P.seatedPort(swapped.items[0], PORT, ctx).info;
  assert.equal(mixed.plug, null, 'poles that take different plugs give none for the end');
  assert.deepEqual(mixed.dc.poles.map(q => q.plug), [LUG, TWO_HOLE]);
  const points = P.ownSlot(PANEL, end('i2', 'output-a1/output'), ctx);
  assert.deepEqual([points.info.plug, points.info.dc.poles.map(q => q.plug)], [P40_PLUG, [P40_PLUG, P40_PLUG]]);
  // a plug the end states: read for every pole that takes it, a note for one that does not
  const asked = P.seatedPort(DC, {...PORT, plug: 'generic/c13-plug@1'}, ctx).info;
  assert.equal(asked.plug, LUG);
  assert.equal(asked.note, 'it states the plug generic/c13-plug@1, which psu-0/module/terminal-rtn does not take; set "plug" on the end to generic/ring-lug@1; '
    + 'it states the plug generic/c13-plug@1, which psu-0/module/terminal-48v does not take; set "plug" on the end to generic/ring-lug@1');
  assert.equal(P.seatedPort(DC, {...PORT, plug: LUG}, ctx).info.note, undefined);
  // plugSeats: a port end seats each pole's plug on its slot, or the connector's on the connector; a pole end as it was
  const slots = [{id: 'psu-0/module/terminal-rtn', kind: 'connector', interface: 'terminal-stud', accepts: [LUG], bores: []},
                 {id: 'psu-0/module/terminal-48v', kind: 'connector', interface: 'terminal-stud', accepts: [LUG], bores: []},
                 {id: 'output-a1', kind: 'connector', interface: 'p40', accepts: [P40_PLUG], bores: []}];
  const landed = (info, extra = {}) => ({cls: 'inlet', compByRef: ctx.compByRef, dc: info.dc, ...extra});
  const info = P.seatedPort(DC, PORT, ctx).info;
  assert.deepEqual(CR.plugSeats('psu-0/module/input', slots, {}, landed(info)), {'psu-0/module/terminal-rtn': LUG, 'psu-0/module/terminal-48v': LUG});
  assert.deepEqual(CR.plugSeats('psu-0/module/input', slots, {'psu-0/module/terminal-rtn': LUG}, landed(info)), {'psu-0/module/terminal-48v': LUG}, 'a slot the user spoke for is left alone');
  assert.deepEqual(CR.plugSeats('output-a1/output', slots, {}, landed(points.info)), {'output-a1': P40_PLUG});
  const pole = P.seatedPort(DC, RTN, ctx).info;
  assert.deepEqual(CR.plugSeats('psu-0/module/terminal-rtn', slots, {}, landed(pole)), {'psu-0/module/terminal-rtn': LUG});
});

// ── 12: dormancy ─────────────────────────────────────────────────────────
test('on a catalogue that states no DC port, no answer carries a dc key', async () => {
  const rack = M.newRack();
  let r = rack;
  for (const [ref, ru] of [['sw', 30], ['pdu', 20], ['nema', 10], ['two', 5]]) r = add(r, ref, ru, {label: ref});
  const INLET = end('i1', 'psu-1/module/inlet'), LUG1 = end('i1', 'psu-2/module/terminal/lug-1');
  r = cabled(r, {a: INLET, b: end('i2', 'outlet-front-1', 'front'), media: 'power'}, {a: LUG1, b: end('i2', 'outlet-rear-1'), media: 'power'},
    {a: end('i1', 'psu-2/module/terminal'), b: end('i2', 'outlet-front-2', 'front')}, {a: end('i1', 'ground'), b: end('i2', 'ground')});
  const c = NO_DC(r), portsOf0 = async (item, view) => PE.zonesOf(item.ref, view, P.cableEndPaths(item, view, PE.ctx));
  const dormant = (name, v) => assert.equal(/"dc":/.test(JSON.stringify(v)), false, name);
  dormant('freePorts', await Q.freePorts(r, 'i1', {...PE.ctx, portsOf: portsOf0}));
  dormant('freePorts of the pdu', await Q.freePorts(r, 'i2', {...PE.ctx, portsOf: portsOf0}));
  dormant('slotEnds', Q.slotEnds(r.items[0], PE.ctx));
  dormant('looseEnds', await Q.looseEnds(r, c));
  dormant('settleEnds', [...P.settleEnds(r, (await PE.oldPage()(r)).ends, c)]);
  dormant('seatedPort', [INLET, LUG1, end('i1', 'psu-2/module/terminal'), end('i1', 'psu-9/module/x')].map(e => P.seatedPort(r.items[0], e, PE.ctx)));
  dormant('ownSlot', [end('i2', 'outlet-front-1', 'front'), end('i2', 'ground'), end('i2', 'input')].map(e => P.ownSlot(r.items[1], e, PE.ctx)));
  assert.deepEqual(P.dcPortsOf(r.items[0], PE.ctx), []);
  assert.equal(P.dcReader(r, PE.ctx)(INLET), null);
  assert.deepEqual(await loose(r, c), ['c3 a: psu-2 holds PSU-DC, whose terminal takes a cable on lug-2, lug-10 and not on itself; give the path psu-2/module/terminal/lug-2']);
});
