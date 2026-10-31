// spec/tests/js/rack-zero-u-module-ends.mjs
// A CABLE ENDS ON A PORT OF A MODULE IN A BAY OF A PART BESIDE THE RACK
// (P-0038): a vertical PDU's network card, as a switch's supply has its inlet.
// The part's bay holds what it ships with (or what its entry swaps in), and
// the ports of that module are ends at `<bay>/module/<port>`, each placed on
// the part by the bay's `at` and the port's `mate` in the module's frame.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as Q from '../../../kit/rack/queries.js';
import * as R from '../../../kit/rack/route.js';
import * as P from '../../../kit/rack/ports.js';
import * as CR from '../../../kit/rack/cable-rules.js';
import * as S from '../../../kit/rack/solids.js';
import {apply} from '../../../kit/rack/commands.js';
import {compByRef as base, SLOTS, SIZES, oldPage, C14, RJ} from './power-ends-fixture.mjs';

const H = 1829, USB = 'generic/usb-c-plug@1';
const BAY_AT = [1.45, 761.65];
const comp = (ref, rest) => { const [ns, tail] = ref.split('/'), [name, major] = tail.split('@'); return {ns, name, major: `v${major}`, parts: [], cages: [], bays: {}, attrs: {}, ...rest}; };
const jack = (id, iface, accepts, mate) => ({id, kind: 'connector', interface: iface, media: null, bores: [], accepts, default: null, at: [mate[0] - 8, mate[1] - 6.6], mate, rotate: null});
// the eNMC as the build publishes it, cut down: two Ethernet jacks, the
// telemetry jacks (not Ethernet), two USB-C ports, a button no cable ends on
const ENMC = comp('eaton/g4-enmc@1', {class: 'nic', kind: 'module', attrs: {module: 'G4 eNMC'},
  parts: [
    {id: 'pdu-plus-1', ref: 'common/rj45-eth@1', at: [8.35, 144.6], attrs: {media: 'rj45-telemetry', function: 'power-redundancy'}},
    {id: 'sensor', ref: 'common/rj45-eth@1', at: [24.9, 144.6], attrs: {media: 'rj45-telemetry', function: 'environmental-probe'}},
    {id: 'eth0', ref: 'common/rj45-eth@1', at: [8.4, 120.05], attrs: {media: 'rj45', speed: '1g'}},
    {id: 'eth1', ref: 'common/rj45-eth@1', at: [24.85, 120.05], attrs: {media: 'rj45', speed: '1g'}},
    {id: 'usb-0', ref: 'std/usb-c@1', at: [7.98, 99.12], attrs: {role: 'console'}},
    {id: 'usb-1', ref: 'std/usb-c@1', at: [32.78, 99.12], attrs: {role: 'storage'}},
    {id: 'restart', ref: 'common/reset-button@1', at: [22.55, 161.5]}],
  cages: [jack('pdu-plus-1', 'rj45', [RJ], [16.25, 151.2]), jack('sensor', 'rj45', [RJ], [32.8, 151.2]),
          jack('eth0', 'rj45', [RJ], [16.3, 126.65]), jack('eth1', 'rj45', [RJ], [32.75, 126.65]),
          {...jack('usb-0', 'usb-c', [USB], [12.15, 100.4]), rotate: 90}, {...jack('usb-1', 'usb-c', [USB], [36.95, 100.4]), rotate: 90}]});
const COVER = comp('eaton/g4-cover@1', {class: 'mechanical', kind: 'module', attrs: {}});
const PLUG_USB = comp(USB, {class: 'port', mates: 'usb-c', attrs: {connector: 'usb-c', media: 'usb-c'}});
const compByRef = ref => ({[ENMC.ns + '/' + ENMC.name + '@1']: ENMC, 'eaton/g4-cover@1': COVER, [USB]: PLUG_USB})[ref] ?? base(ref);

const outlet = (id, y) => ({id, kind: 'connector', interface: 'iec-c13', media: null, bores: [], accepts: [C14], default: null, at: [9.1, y - 11], mate: [24.3, y]});
const VPDU = {default: 'base', 'pdu-class': 'managed',
  bays: {front: [{id: 'network-module', at: BAY_AT, size: {w: 49.15, h: 187.9}, accepts: ['eaton/g4-enmc@1', 'eaton/g4-cover@1'], default: 'eaton/g4-enmc@1', rotate: null}], rear: []},
  cages: {front: [outlet('outlet-a1', 1619.67), outlet('outlet-f42', 30)], rear: []},
  configs: [{name: 'base', description: '', airflow: 'passive', bays: {'network-module': 'eaton/g4-enmc@1'}, occupants: {}, names: {'outlet-a1': 'A1', 'outlet-f42': 'F42'}}]};
const SIZES2 = {...SIZES, vpdu: {manufacturer: 'Acme', model: 'VPDU', mount: 'rack-side', kind: 'pdu', ru: 41, h: H, w: 52, d: 65, default: 'base', configs: ['base']}};
const SLOTS2 = {...SLOTS, vpdu: VPDU};
const ctx = {chassisOf: ref => SIZES2[ref] ?? null, slotsOf: ref => SLOTS2[ref] ?? null, compByRef};
const rc = {...ctx, guidesOf: () => [], portX: () => 150, bendOf: () => 1e12};

const run = (rack, cmds, c = ctx) => apply(rack, cmds, c);
const MGMT = {item: 'i1', path: 'psu-1/module/mgmt', view: 'rear'};
const at = (path, view = 'front') => ({item: 'z1', path, view});
const BASE = run(M.withItem(M.newRack(), {ref: 'sw', cfg: 'base', ru: 35, label: 'sw-1'}).rack,
  {op: 'zerou.place', ref: 'vpdu', at: 'left-rear', ru: 1, label: 'PDU-A'}).rack;
const cable = (b, extra = {}) => run(BASE, {op: 'cable.add', a: MGMT, b, media: 'cat6a', purpose: 'management', ...extra});
const near = (p, q) => ['x', 'y', 'z'].every(k => Math.abs(p[k] - q[k]) < 1e-6);

test('the module in the bay lists its ports, named as a rack device\'s are, each placed on the part', () => {
  const ends = P.zeroUEnds(BASE.zeroU[0], ctx);
  assert.deepEqual(ends.map(e => e.path), ['network-module/module/eth0', 'network-module/module/eth1', 'network-module/module/pdu-plus-1',
    'network-module/module/sensor', 'network-module/module/usb-0', 'network-module/module/usb-1', 'outlet-a1', 'outlet-f42']);
  const eth0 = ends[0];
  assert.deepEqual([eth0.view, eth0.type, eth0.connector, eth0.kind, eth0.plug, eth0.media, eth0.speed], ['front', null, 'RJ45 port', 'data', RJ, 'rj45', '1g']);
  assert.equal(eth0.info.family, 'copper');
  // the bay's `at` and the jack's `mate` in the module, y up from the part's bottom
  assert.ok(Math.abs(eth0.x - (1.45 + 16.3)) < 1e-9 && Math.abs(eth0.y - (H - (761.65 + 126.65))) < 1e-9, `${eth0.x} ${eth0.y}`);
  // PDU+1 and the probe jack are not Ethernet, and say so
  assert.deepEqual([ends[2], ends[3]].map(e => [e.kind, e.media]), [['data', 'rj45-telemetry'], ['data', 'rj45-telemetry']]);
  // the USB-C ports, the first the configuration port the console runs over: its placement states `role: console`
  assert.deepEqual([ends[4], ends[5]].map(e => [e.connector, e.plug, e.info.family, e.kind]), [['USB-C port', USB, 'console', 'data'], ['USB-C port', USB, 'usb', 'data']]);
  // the part's own outlets are unchanged
  assert.deepEqual(ends.slice(6).map(e => [e.path, e.type, e.kind, e.connector]), [['outlet-a1', 'C13', 'power', 'C13 outlet'], ['outlet-f42', 'C13', 'power', 'C13 outlet']]);
  // a button, and a part with no ports, add none
  assert.equal(ends.some(e => /restart/.test(e.path)), false);
});

test('a swap on the entry decides what the bay holds', () => {
  const covered = {...BASE.zeroU[0], swaps: {'network-module': 'eaton/g4-cover@1'}};
  assert.deepEqual(P.zeroUEnds(covered, ctx).map(e => e.path), ['outlet-a1', 'outlet-f42']);
  const empty = {...BASE.zeroU[0], swaps: {'network-module': null}};
  assert.deepEqual(P.zeroUEnds(empty, ctx).map(e => e.path), ['outlet-a1', 'outlet-f42']);
});

test('a cable from the device ends on each port of the module: accepted, kept, and removable', () => {
  for (const port of ['eth0', 'eth1', 'usb-0', 'usb-1', 'pdu-plus-1', 'sensor']) {
    const r = cable(at(`network-module/module/${port}`));
    assert.equal(r.error, undefined, `${port}: ${r.error}`);
    assert.deepEqual(r.rack.cables[0].b, at(`network-module/module/${port}`));
    assert.deepEqual(run(r.rack, {op: 'cable.remove', id: 'c1'}).rack.cables, []);
  }
  const moved = run(cable(at('network-module/module/eth0')).rack, {op: 'cable.update', id: 'c1', b: at('network-module/module/eth1')});
  assert.match(moved.summary, /Moved end B of cable c1 to PDU-A \(left-rear\) network-module\/module\/eth1\./);
  // one cable a port
  assert.match(run(cable(at('network-module/module/eth0')).rack, {op: 'cable.add', a: {...MGMT, path: 'psu-3/module/mgmt'}, b: at('network-module/module/eth0')}).error,
    /already has a cable \(c1\)/);
});

test('a port the module does not have is refused, with the full list', () => {
  const e = cable(at('network-module/module/eth9')).error;
  assert.equal(e, 'PDU-A has no network-module/module/eth9. It has RJ45 port network-module/module/eth0, network-module/module/eth1, '
    + 'network-module/module/pdu-plus-1, network-module/module/sensor; USB-C port network-module/module/usb-0, network-module/module/usb-1; C13 outlet-a1, outlet-f42.');
  assert.equal(cable(at('network-module/module/eth0', 'rear')).error,
    'network-module/module/eth0 is on the front panel of PDU-A: give view "front".');
  // a bay's own id, or a part the module has that is no port, is no end
  assert.match(cable(at('network-module')).error, /^PDU-A has no network-module\./);
  assert.match(cable(at('network-module/module/restart')).error, /^PDU-A has no network-module\/module\/restart\./);
});

test('the catalogue answers for the end: it lands as a copper port with the plug the jack takes', async () => {
  const r = cable(at('network-module/module/eth0')).rack;
  const ends = P.settleEnds(r, (await oldPage()(r)).ends, ctx);
  const b = ends.get(CR.endKey(at('network-module/module/eth0')));
  assert.equal(b.reason, null);
  assert.deepEqual([b.info.family, b.info.plug, b.info.connector], ['copper', RJ, 'RJ45 port']);
  const usb = cable(at('network-module/module/usb-0'), {media: ''}).rack;
  assert.equal(P.settleEnds(usb, new Map(), ctx).get(CR.endKey(at('network-module/module/usb-0'))).reason, null);
  // a made-up port is loose, naming those the part has
  const bad = {...r, cables: [{...r.cables[0], b: at('network-module/module/eth9')}]};
  assert.match(P.settleEnds(bad, new Map(), ctx).get(CR.endKey(at('network-module/module/eth9'))).reason,
    /^PDU-A has no network-module\/module\/eth9; it has RJ45 port network-module\/module\/eth0/);
});

test('the cable reaches the jack on the PDU\'s face, and the length is measured to it', () => {
  const z = BASE.zeroU[0];
  const jackAt = port => {
    const {x, y} = P.zeroUEnds(z, ctx).find(e => e.path === `network-module/module/${port}`);
    return S.zeroUPanelPoint(BASE, z, SIZES2.vpdu, {x, y}, 'front');
  };
  for (const port of ['eth0', 'eth1', 'usb-0']) {
    const rack = cable(at(`network-module/module/${port}`)).rack;
    const p = R.portPoint(rack, rack.cables[0].b, rc);
    assert.ok(near(p, jackAt(port)), `${port} ${JSON.stringify(p)}`);
    const path = R.routePath(rack, rack.cables[0], rc);
    assert.ok(near(path.points.at(-1), p), JSON.stringify(path.points.at(-1)));
    assert.ok(R.routedLength(rack, rack.cables[0], rc).measured > 1);
  }
  // on the same face as the outlets, 940.7 mm up the part (U22), and the route runs to that unit
  const rack = cable(at('network-module/module/eth0')).rack;
  const eth = R.portPoint(rack, at('network-module/module/eth0'), rc);
  assert.ok(Math.abs(eth.z - R.portPoint(BASE, at('outlet-a1'), rc).z) < 1e-6);
  assert.ok(Math.abs(eth.y - (H - (761.65 + 126.65))) < 1e-6, String(eth.y));
  assert.deepEqual(R.ownRoute(rack, rack.cables[0], rc).waypoints.at(-1), {lane: 'left-rear', ru: 22});
});

test('a module turned in its bay is an end with no point', () => {
  const turned = {...SLOTS2, vpdu: {...VPDU, bays: {front: [{...VPDU.bays.front[0], rotate: 180}], rear: []}}};
  const c2 = {...ctx, slotsOf: ref => turned[ref] ?? null};
  const e = P.zeroUEnds(BASE.zeroU[0], c2).find(x => x.path === 'network-module/module/eth0');
  assert.ok(e && e.x === undefined && e.y === undefined);
});

test('inspect, free ports and describe name the module\'s ports', async () => {
  const r = cable(at('network-module/module/eth0'), {label: 'mgmt'}).rack;
  const z = await Q.inspect(r, 'z1', ctx);
  assert.deepEqual(z.ends.find(e => e.path === 'network-module/module/eth0'), {path: 'network-module/module/eth0', view: 'front',
    name: 'network module eth0', type: null, connector: 'RJ45 port', kind: 'data', plug: RJ, u: z.ends.find(e => e.path === 'network-module/module/eth0').u, cable: 'c1'});
  assert.equal(z.ends.find(e => e.path === 'network-module/module/eth1').cable, null);
  const free = await Q.freePorts(r, 'z1', ctx, {kinds: ['data']});
  assert.deepEqual(free.map(p => p.path), ['network-module/module/eth1', 'network-module/module/pdu-plus-1', 'network-module/module/sensor',
    'network-module/module/usb-0', 'network-module/module/usb-1']);
  assert.deepEqual([free[0].media, free[0].speed, free[2].media], ['rj45', '1g', 'rj45-telemetry']);
  assert.deepEqual((await Q.freePorts(r, 'z1', ctx, {kinds: ['power']})).map(p => p.path), ['outlet-a1', 'outlet-f42']);
  assert.match(Q.describe(r, ctx), /c1: i1\/psu-1\/module\/mgmt \(rear\) <-> z1\/network-module\/module\/eth0/);
  const c = await Q.inspect(r, 'c1', {...ctx, route: rc, cableFacts: oldPage()});
  assert.deepEqual(c.loose, []);
  assert.ok(c.routed && c.routed.metres > 1, JSON.stringify(c.routed));
});

test('the ports of a rack device\'s module are unchanged', () => {
  const sw = BASE.items[0];
  assert.equal(P.seatedPort(sw, {path: 'psu-1/module/mgmt', view: 'rear'}, ctx)?.port, true);
  assert.equal(P.seatedPort(sw, {path: 'psu-1/module/inlet', view: 'rear'}, ctx)?.port, true);
  assert.notEqual(P.seatedPort(sw, {path: 'psu-1/module/eth9', view: 'rear'}, ctx)?.port, true);
});
