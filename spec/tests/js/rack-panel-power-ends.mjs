// spec/tests/js/rack-panel-power-ends.mjs
// THE POWER, GROUND AND DC ENDS OF EVERY PANEL A DEVICE DRAWS: freePorts lists
// the power, ground and DC ends of the top, bottom, left and right panels as it
// lists those of the front and the rear, and a DC port whose poles are on one of
// those panels has that panel as its `view`. A panel the library never names
// (the six are front, rear, left, right, top and bottom: ports.js shownEnv) is
// not invented, a port whose poles are on two panels has no panel, and the front
// and the rear answer exactly as they did.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as Q from '../../../kit/rack/queries.js';
import * as P from '../../../kit/rack/ports.js';
import {apply} from '../../../kit/rack/commands.js';
import {ctx as DC_CTX, SLOTS as DC_SLOTS, SIZES as DC_SIZES, COMPONENTS, LUG, PSU_48} from './dc-ports-fixture.mjs';
import * as PE from './power-ends-fixture.mjs';

const {PSU_AC} = PE;

const slot = (id, iface, accepts) => ({id, kind: 'connector', interface: iface, media: null, bores: [], accepts, default: null});
const bay = (id, accepts, def = null) => ({id, group: 'bays', accepts, default: def});
const pole = (role, slotId) => ({role, slot: slotId});
const feed = (path, ref = 'common/dc-terminal@1') => ({id: 'input', path: `${path}/input`, ref, direction: 'input', voltage: null, 'rating-a': null, awg: null, side: null,
  poles: [pole('rtn', `${path}/lug-1`), pole('batt', `${path}/lug-2`)]});
const lugs = id => [slot(`${id}/lug-1`, 'terminal-stud', [LUG]), slot(`${id}/lug-2`, 'terminal-stud', [LUG])];
const config = (rest = {}) => ({name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {}, ...rest});

// the catalogue of the DC fixture, with a device for each panel the library draws, one panel it never does, and two that split a port
const SLOTS = {
  ...DC_SLOTS,
  // a DC terminal on the top, as ten switches draw their header
  topdc: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []}, cages: {front: [], rear: [], top: lugs('feed')},
          configs: [config({'dc-ports': [feed('feed')]})]},
  // the same on each of the other panels
  bottomdc: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []}, cages: {front: [], rear: [], bottom: lugs('feed')},
             configs: [config({'dc-ports': [feed('feed')]})]},
  leftdc: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []}, cages: {front: [], rear: [], left: lugs('feed')},
           configs: [config({'dc-ports': [feed('feed')]})]},
  rightdc: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []}, cages: {front: [], rear: [], right: lugs('feed')},
            configs: [config({'dc-ports': [feed('feed')]})]},
  // an AC inlet (a coupler) on the left, a supply in a bay on the top, a DC terminal at the rear
  mixed: {default: 'base', 'pdu-class': null, bays: {front: [], rear: [], top: [bay('psu-t', [PSU_AC], PSU_AC)]},
          cages: {front: [], rear: lugs('rear-feed'), left: [slot('ac-in', 'iec-c14', ['generic/c13-plug@1'])]},
          configs: [config({bays: {'psu-t': PSU_AC}, 'dc-ports': [feed('rear-feed')]})]},
  // a panel the library never names: nothing is offered from it
  attic: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []}, cages: {front: [], rear: [], attic: lugs('feed')},
          configs: [config({'dc-ports': [feed('feed')]})]},
  // one port on two panels: no panel, so neither offered nor landed, as before
  halves: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []}, cages: {front: [], rear: [], top: [slot('half/lug-1', 'terminal-stud', [LUG])],
           bottom: [slot('half/lug-2', 'terminal-stud', [LUG])]},
           configs: [config({'dc-ports': [feed('half')]})]},
  // slots a page reads on the side panels: a ground stud on the left, a coupler on the top, a blind slot and a jack at the bottom
  sides: {default: 'base', 'pdu-class': null, bays: {front: [], rear: []},
          cages: {front: [], rear: [], left: [slot('ground-left', 'terminal-stud', [LUG])], top: [slot('ac-top', 'iec-c14', ['generic/c13-plug@1'])],
                  bottom: [slot('blind-b', 'acme-blind', []), slot('rj-b', 'rj45', ['generic/rj45-plug@1'])]},
          configs: [config()]},
  // a supply on the top panel that states a port of its own
  roofpsu: {default: 'base', 'pdu-class': null, bays: {front: [], rear: [], top: [bay('psu-t', [PSU_48], PSU_48)]}, cages: {front: [], rear: []},
            configs: [config({bays: {'psu-t': PSU_48},
              'dc-ports': [{id: 'input', path: 'psu-t/module/input', ref: PSU_48, direction: 'input', voltage: null, 'rating-a': null, awg: null, side: null,
                            poles: [pole('rtn', 'psu-t/module/terminal-rtn'), pole('batt', 'psu-t/module/terminal-48v')]}]})]},
};
const SIZES = {...DC_SIZES};
for (const ref of ['topdc', 'bottomdc', 'leftdc', 'rightdc', 'mixed', 'attic', 'halves', 'roofpsu', 'sides'])
  SIZES[ref] = {ru: 1, w: 438, h: 43.6, d: 200, model: ref.toUpperCase(), manufacturer: 'Acme', kind: 'switch', configs: ['base'], default: 'base'};
const byRef = new Map(COMPONENTS.map(c => [`${c.ns}/${c.name}@${c.major.slice(1)}`, c]));
const ctx = {...DC_CTX, chassisOf: ref => SIZES[ref] ?? null, slotsOf: ref => SLOTS[ref] ?? null, compByRef: ref => (ref == null ? null : byRef.get(String(ref).split(':')[0]) ?? null)};
const portsOf = async () => [];
const free = (rack, id, opts) => Q.freePorts(rack, id, {...ctx, portsOf}, opts);
const rackOf = ref => M.withItem(M.newRack(), {ref, cfg: 'base', ru: 20, label: ref}).rack;
const slim = rows => rows.map(r => [r.path, r.view, r.kind]);

test('a DC terminal on the top panel is offered as one row on the top, with its poles, and its screws are no rows', async () => {
  const rack = rackOf('topdc'), item = rack.items[0];
  assert.deepEqual(P.dcPortsOf(item, ctx).map(p => [p.path, p.view, p.kind, p.lands]), [['feed/input', 'top', 'slots', true]]);
  const rows = await free(rack, item.id);
  assert.deepEqual(slim(rows), [['feed/input', 'top', 'power']]);
  assert.deepEqual(rows[0].dc.poles.map(q => [q.role, q.path]), [['rtn', 'feed/lug-1'], ['batt', 'feed/lug-2']]);
  assert.deepEqual(Q.slotEnds(item, ctx).map(e => [e.path, e.view]), [['feed/input', 'top']], 'slotEnds lists it too');
  assert.deepEqual(slim(await free(rack, item.id, {kinds: ['power']})), [['feed/input', 'top', 'power']]);
  assert.deepEqual(await free(rack, item.id, {kinds: ['data']}), []);
});

test('the bottom, left and right panels are offered the same way', async () => {
  for (const [ref, view] of [['bottomdc', 'bottom'], ['leftdc', 'left'], ['rightdc', 'right']]) {
    const rack = rackOf(ref);
    assert.deepEqual(slim(await free(rack, rack.items[0].id)), [['feed/input', view, 'power']], ref);
  }
});

test('an AC inlet on a side panel and a supply on the top are offered, beside the DC terminal at the rear', async () => {
  const rack = rackOf('mixed'), id = rack.items[0].id;
  const rows = await free(rack, id);
  assert.deepEqual(slim(rows), [['rear-feed/input', 'rear', 'power'], ['ac-in', 'left', 'power'], ['psu-t/module/inlet', 'top', 'power']],
    'the rear first, as it was, then the other panels in the order left, right, top, bottom');
  assert.equal(rows.every(r => !('of' in r && r.view !== 'rear' && r.dc)), true);
});

test('a power end on a panel is a row of a part in a bay on that panel, with the supply\'s DC port', async () => {
  const rack = rackOf('roofpsu');
  assert.deepEqual(slim(await free(rack, rack.items[0].id)), [['psu-t/module/input', 'top', 'power']]);
});

test('the slots a page reads on a side panel: its ground and power ends are offered, its jack and its blind slot are not', async () => {
  const rack = rackOf('sides'), id = rack.items[0].id;
  const read = {left: [{path: 'ground-left', cls: 'ground', ref: 'common/ground-stud@1', end: true}],
                top: [{path: 'ac-top', cls: 'inlet', ref: 'std/c14-inlet@1', end: true}],
                bottom: [{path: 'blind-b', cls: 'mechanical', ref: null, end: true}, {path: 'rj-b', cls: 'port', ref: 'std/rj45@1', media: 'rj45'}]};
  const page = async (_item, view) => read[view] ?? [];
  const rows = await Q.freePorts(rack, id, {...ctx, portsOf: page});
  assert.deepEqual(slim(rows), [['ground-left', 'left', 'ground'], ['ac-top', 'top', 'power']], 'no jack, no blind slot, and the coupler once');
  assert.deepEqual(slim(await Q.freePorts(rack, id, {...ctx, portsOf: page}, {kinds: ['power']})), [['ac-top', 'top', 'power']]);
  assert.deepEqual(slim(await Q.freePorts(rack, id, {...ctx, portsOf: page}, {kinds: ['data']})), [], 'a data picker gets nothing from a side panel');
  // a page that reads no such panel hands in nothing: the catalogue's own ends only (the coupler), and no ground stud, which no part of the catalogue says is one
  assert.deepEqual(slim(await free(rack, id)), [['ac-top', 'top', 'power']]);
});

test('front and rear answer exactly as they did: the DC fixture\'s own ends, in their order, and no row of another panel', async () => {
  const rack = ['dc', 'panel', 'sw', 'pdu'].reduce((r, ref, i) => M.withItem(r, {ref, cfg: 'base', ru: 30 - i * 5, label: ref}).rack, M.newRack());
  const got = {};
  for (const it of rack.items) got[it.ref] = slim(await free(rack, it.id));
  assert.deepEqual(got.dc, [['psu-1/module/terminal/lug-10', 'rear', 'power'], ['psu-0/module/input', 'rear', 'power'], ['psu-1/module/input', 'rear', 'power'],
                            ['psu-2/module/input', 'rear', 'power']]);
  assert.deepEqual(got.panel, [['feed-a/input', 'rear', 'power'], ['output-a1/output', 'rear', 'power'], ['output-b1/output', 'rear', 'power']]);
  for (const rows of Object.values(got)) assert.equal(rows.every(r => r[1] === 'front' || r[1] === 'rear'), true);
});

test('a panel the library never names is not invented, and a port split across two panels has none', async () => {
  const attic = rackOf('attic'), halves = rackOf('halves');
  assert.deepEqual(await free(attic, attic.items[0].id), []);
  assert.deepEqual(P.dcPortsOf(attic.items[0], ctx), [], 'the slots of a panel no one names are not read, so the port has nothing to stand on');
  assert.deepEqual(P.dcPortsOf(halves.items[0], ctx).map(p => [p.path, p.view]), [['half/input', null]]);
  assert.deepEqual(await free(halves, halves.items[0].id), []);
});

test('how a cable lands is unchanged: an end is given on the front or the rear only, so cable.add still refuses a view of the top', async () => {
  const rack = ['topdc', 'sw'].reduce((r, ref, i) => M.withItem(r, {ref, cfg: 'base', ru: 20 - i * 5, label: ref}).rack, M.newRack());
  const [a, b] = rack.items;
  const row = (await free(rack, a.id))[0], far = {item: b.id, path: 'ground', view: 'rear'};
  assert.equal(row.view, 'top');
  assert.equal(apply(rack, [{op: 'cable.add', a: {item: a.id, path: row.path, view: row.view}, b: far}], ctx).error, 'cable.add needs a.view, one of front, rear.');
  // a cable saved on the front or rear to a path of the top panel is the loose end it was: the port stays offered
  const saved = {...rack, cables: [{id: 'c1', a: {item: a.id, path: 'feed/input', view: 'front'}, b: far, media: 'power', purpose: '', label: '', route: []}]};
  assert.deepEqual(slim(await free(saved, a.id)), [['feed/input', 'top', 'power']]);
  // ... and it says so in words a person can follow, not "give view top", which the kit refuses
  const page = {...ctx, cableFacts: PE.oldPage(), drawnAt: PE.drawnAt(saved)};
  assert.deepEqual((await Q.looseEnds(saved, page)).ends.map(e => `${e.cable} ${e.side}: ${e.reason}`),
    ['c1 a: feed/input is on the top of the device, and a cable end can be given on the front or rear only']);
  // a DC port on the other of front and rear is named as before
  const dcRack = ['dc', 'sw'].reduce((r, ref, i) => M.withItem(r, {ref, cfg: 'base', ru: 20 - i * 5, label: ref}).rack, M.newRack());
  const onFront = {...dcRack, cables: [{id: 'c1', a: {item: dcRack.items[0].id, path: 'psu-0/module/input', view: 'front'}, b: {item: dcRack.items[1].id, path: 'ground', view: 'rear'},
                                        media: 'power', purpose: '', label: '', route: []}]};
  assert.deepEqual((await Q.looseEnds(onFront, {...ctx, cableFacts: PE.oldPage(), drawnAt: PE.drawnAt(onFront)})).ends.map(e => e.reason),
    ['psu-0/module/input is on the rear panel; give view "rear"']);
});
