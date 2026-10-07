import test from 'node:test';
import assert from 'node:assert/strict';
import * as X from '../../../kit/rack/export-data.js';
import * as M from '../../../kit/rack/model.js';
import {ITEMS} from './rack-export-data.mjs';

const DAY = new Date(2026, 8, 27);
const nb = (vendor, model) => `netbox/device-types/${vendor}/${model}.yaml`;

test('one file is certain; a manufacturer filter comes first', () => {
  assert.deepEqual(X.matchDeviceType({cfg: 'base', manufacturer: 'Telco Systems', paths: [nb('Telco Systems', 'TM-280')]}),
    {path: nb('Telco Systems', 'TM-280'), guess: false, candidates: 1});
  assert.equal(X.matchDeviceType({cfg: 'base', manufacturer: 'X', paths: []}), null);
});

test('a file naming the configuration wins, as a run of its words', () => {
  const paths = ['lff12-mlff4-rlff2-rc0-noriser', 'lff12-rc0-noriser', 'lff12-rc3-1a2a']
    .map(c => nb('Dell', `PowerEdge R740xd ${c}`));
  assert.deepEqual(X.matchDeviceType({cfg: 'lff12-rc0-noriser', manufacturer: 'Dell', paths}),
    {path: paths[1], guess: false, candidates: 3});
  const asr = [nb('Cisco', 'ASR-9006-AC-V2'), nb('Cisco', 'ASR-9006-DC-V2')];
  assert.deepEqual(X.matchDeviceType({cfg: 'dc', manufacturer: 'Cisco', paths: asr}),
    {path: asr[1], guess: false, candidates: 2});
});

test('otherwise the best token score, with airflow and DC aliases, is a guess', () => {
  const paths = ['ArcOS on 7726-32X-O-AC-F', 'ArcOS on 7726-32X-O-AC-B'].map(m => nb('Arrcus', m))
    .concat(['7726-32X-O-48V-B', '7726-32X-O-48V-F', '7726-32X-O-AC-B', '7726-32X-O-AC-F'].map(m => nb('Edgecore', m)));
  assert.deepEqual(X.matchDeviceType({cfg: 'ac-f2b', manufacturer: 'Edgecore', paths}),
    {path: nb('Edgecore', '7726-32X-O-AC-F'), guess: true, candidates: 4});
  assert.equal(X.matchDeviceType({cfg: 'dc-b2f', manufacturer: 'Edgecore', paths}).path, nb('Edgecore', '7726-32X-O-48V-B'));
  const asr = [nb('Cisco', 'ASR-9006-AC-V2'), nb('Cisco', 'ASR-9006-DC-V2')];
  assert.deepEqual(X.matchDeviceType({cfg: 'base', manufacturer: 'Cisco', paths: asr}),
    {path: asr[0], guess: true, candidates: 2});
});

test('falling back past the manufacturer filter is always a guess', () => {
  const arrcus = nb('Arrcus', '7726-32X-O-AC-F');
  assert.deepEqual(X.matchDeviceType({cfg: 'ac-f2b', manufacturer: 'Edgecore', paths: [arrcus]}),
    {path: arrcus, guess: true, candidates: 1});
});

// A MANUFACTURER WHOSE NAME HOLDS A SLASH is filed under the name with the
// slash written as a hyphen (dcim_export.py manufacturer_dir, Portrayal #826),
// so `BATM/Telco Systems` exports under `BATM-Telco Systems/` while the YAML
// inside keeps the real name. Its own types must read as its own: compared with
// the name as written, the filter found nothing and every one of its devices
// came out as another vendor's file, a best guess.
test('a manufacturer whose name holds a slash owns the files under its directory', () => {
  assert.equal(X.dirOf('BATM/Telco Systems'), 'BATM-Telco Systems');
  const batm = ['TM-8104', 'TM-8106'].map(m => nb('BATM-Telco Systems', m));
  assert.deepEqual(X.matchDeviceType({cfg: 'base', manufacturer: 'BATM/Telco Systems', paths: [batm[0]]}),
    {path: batm[0], guess: false, candidates: 1});
  // Two of its own, one naming the configuration: certain, as for any vendor.
  assert.deepEqual(X.matchDeviceType({cfg: '8104', manufacturer: 'BATM/Telco Systems', paths: batm}),
    {path: batm[0], guess: false, candidates: 2});
  // Another vendor's directory is still another vendor's: the filter finds none
  // of its own, so whatever wins is a guess.
  const asr = nb('Cisco', 'ASR-9006-AC-V2');
  assert.deepEqual(X.matchDeviceType({cfg: 'base', manufacturer: 'BATM/Telco Systems', paths: [asr]}),
    {path: asr, guess: true, candidates: 1});
  // The note names the file's folder, not the name in its YAML: with the stem it
  // says where in the kit a reader checking the guess finds the file.
  assert.equal(X.otherVendorNote({label: 'demarc', ref: 'tm-280', T: 'NetBox',
                                  manufacturer: 'BATM/Telco Systems', path: asr}),
    "demarc (tm-280): no NetBox device type from BATM/Telco Systems, so ASR-9006-AC-V2 is another vendor's (Cisco) file, a best guess.");
});

test('yamlHead reads the top-level identity, quoted or not', () => {
  const h = X.yamlHead('---\nmanufacturer: Cisco\nmodel: ASR 9901 Router, AC supplies\nslug: cisco-asr-9901\n' +
                       'u_height: 2.0\nis_full_depth: true\ninterfaces:\n  - name: x\n    model: nested\n');
  assert.deepEqual(h, {manufacturer: 'Cisco', model: 'ASR 9901 Router, AC supplies', slug: 'cisco-asr-9901',
                       uHeight: 2, isFullDepth: true});
  assert.equal(X.yamlHead("model: 'O''Brien 1'").model, "O'Brien 1");
  assert.equal(X.yamlHead('model: "A: B"').model, 'A: B');
  assert.equal(X.yamlHead('').model, null);
});

test('a module type is found by its part number, slashes as dashes', () => {
  const paths = ['netbox/module-types/Cisco/A9K Slot Cover.yaml', 'netbox/device-types/Cisco/X.yaml',
                 'netbox/module-types/Acme/A-B.yaml'];
  assert.equal(X.moduleTypePath(paths, 'A9K Slot Cover'), paths[0]);
  assert.equal(X.moduleTypePath(paths, 'A/B'), paths[2]);
  assert.equal(X.moduleTypePath(paths, 'X'), null);
  assert.equal(X.moduleTypePath(paths, ''), null);
  assert.equal(X.partNumber({attrs: {model: 'A9K-3KW-AC'}}), 'A9K-3KW-AC');
  assert.equal(X.partNumber({attrs: {'part-number': 'P1'}}), 'P1');
  assert.equal(X.partNumber(null), '');
});

test('a repeated label gets the item id, once per duplicate', () => {
  const n = X.uniqueNames(ITEMS);
  assert.deepEqual([...n.values()].map(v => v.name), ['core-1', 'leaf-1', 'demarc-i3', 'demarc-i4']);
  assert.equal(n.get('i3').renamed, true);
  assert.equal(n.get('i1').renamed, false);
});

test('a generated name never collides with another item\'s own label', () => {
  const items = [{id: 'i3', label: 'demarc', ref: 'tm-280'}, {id: 'i4', label: 'demarc', ref: 'tm-280'},
                 {id: 'i9', label: 'demarc-i3', ref: 'tm-280'}];
  const names = [...X.uniqueNames(items).values()].map(v => v.name);
  assert.equal(new Set(names).size, 3, names.join(', '));
  assert.equal(names[2], 'demarc-i3');           // an item's own label is kept
  assert.equal(names[1], 'demarc-i4');
  assert.notEqual(names[0], 'demarc-i3');
  assert.match(names[0], /^demarc-i3-/);
  // Two generated names cannot meet either.
  const twice = [{id: 'a', label: 'x', ref: 'r'}, {id: 'a-2', label: 'x', ref: 'r'}, {id: 'b', label: 'x-a', ref: 'r'},
                 {id: 'c', label: 'x-a-2', ref: 'r'}];
  const got = [...X.uniqueNames(twice).values()].map(v => v.name);
  assert.equal(new Set(got).size, 4, got.join(', '));
});

test('a device with no type is left out of the file, and said; no configuration name leaves the parenthesis out', () => {
  const item = {id: 'i1', ref: 'mystery', cfg: '', label: 'm', ru: 2, u: 1, face: 'front', turned: false};
  const why = 'm is not in the devices file: there is no NetBox device type for mystery. Add the type and the device by hand.';
  const got = X.deviceImportRows({rack: RACK, items: [item], types: new Map([['i1', null]])});
  assert.deepEqual(got.rows, []);
  assert.deepEqual(got.left, [{id: 'i1', name: 'm', reason: why}]);
  const none = X.deviceImportRows({rack: RACK, items: [{...item, cfg: undefined}], types: new Map()});
  assert.deepEqual([none.rows, none.left[0].reason], [[], why]);
  assert.match(X.deviceImportRows({rack: RACK, items: [{...item, cfg: 'dc'}], types: new Map(), target: 'nautobot'}).left[0].reason,
    /there is no Nautobot device type for mystery \(dc\)\./);
});

const TYPES = new Map([
  ['i1', {manufacturer: 'Cisco', model: 'ASR-9006-AC-V2', isFullDepth: true, guess: true}],
  ['i2', {manufacturer: 'Edgecore', model: '7726-32X-O-AC-F', isFullDepth: true, guess: true}],
  ['i3', {manufacturer: 'Telco Systems', model: 'TM-280', isFullDepth: true, guess: false}],
  ['i4', {manufacturer: 'Telco Systems', model: 'TM-280', isFullDepth: true, guess: false}],
]);
const RACK = {name: 'Export test', frame: M.normalizeFrame({heightRU: 24})};

test('NetBox rows: top down, unique names, planned, notes in comments', () => {
  const {columns, rows, left} = X.deviceImportRows({rack: RACK, items: ITEMS, types: TYPES, target: 'netbox'});
  assert.deepEqual(columns, ['name', 'role', 'manufacturer', 'device_type', 'status', 'site', 'rack',
                             'position', 'face', 'comments']);
  // demarc-i3 shares U14 with leaf-1, which was placed first: NetBox would refuse it, and the file with it.
  assert.deepEqual(rows.map(r => [r.name, r.position, r.face, r.manufacturer, r.device_type]), [
    ['demarc-i4', 20, 'rear', 'Telco Systems', 'TM-280'], ['leaf-1', 14, 'front', 'Edgecore', '7726-32X-O-AC-F'],
    ['core-1', 2, 'front', 'Cisco', 'ASR-9006-AC-V2']]);
  assert.ok(rows.every(r => r.status === 'planned' && r.role === '' && r.site === '' && r.rack === 'Export test'));
  assert.equal(rows[0].comments, 'Named demarc-i4 because another device here is also demarc.');
  assert.equal(rows[1].comments, 'Device type 7726-32X-O-AC-F is a best guess for configuration ac-f2b.');
  assert.equal(rows[2].comments, 'Device type ASR-9006-AC-V2 is a best guess for configuration base.');
  assert.deepEqual(left, [{id: 'i3', name: 'demarc-i3', reason:
    'demarc-i3 is not in the devices file: it shares U14 with leaf-1 on the front, and NetBox refuses two devices in one U, ' +
    'front and rear, while either type is full depth. One refused row refuses the whole file. Import demarc-i3 by hand ' +
    "after changing the type's depth, or place it elsewhere."}]);
});

test('the import settings fill role and site, or role and location; blank ones stay blank', () => {
  const dcim = {site: ' Lab 1 ', role: 'Router'};
  const nb = X.deviceImportRows({rack: RACK, items: ITEMS, types: TYPES, target: 'netbox', dcim}).rows;
  assert.ok(nb.every(r => r.site === 'Lab 1' && r.role === 'Router'));
  const nt = X.deviceImportRows({rack: RACK, items: ITEMS, types: TYPES, target: 'nautobot', dcim}).rows;
  assert.ok(nt.every(r => r.location__name === 'Lab 1' && r.role__name === 'Router'));
  const blank = X.deviceImportRows({rack: RACK, items: ITEMS, types: TYPES, target: 'netbox', dcim: {site: null}}).rows;
  assert.ok(blank.every(r => r.site === '' && r.role === ''));
});

test('the rack row is written from the frame: 19 inch, its height, planned, and whether U1 is at the top', () => {
  assert.deepEqual(X.rackImportRows({rack: RACK, dcim: {site: 'Lab 1', role: 'Router'}}), {
    columns: ['site', 'name', 'status', 'width', 'u_height', 'desc_units'],
    rows: [{site: 'Lab 1', name: 'Export test', status: 'planned', width: 19, u_height: 24, desc_units: 'false'}]});
  const down = {...RACK, frame: {...RACK.frame, numbering: 'top-down'}};
  assert.deepEqual(X.rackImportRows({rack: down}).rows[0], {site: '', name: 'Export test', status: 'planned', width: 19,
    u_height: 24, desc_units: 'true'});
  assert.equal(X.toCsv(...Object.values(X.rackImportRows({rack: down, dcim: {site: 'A, B'}}))),
    'site,name,status,width,u_height,desc_units\r\n"A, B",Export test,planned,19,24,true\r\n');
});

test('rows sort by each item\'s top U, not where it starts', () => {
  const tall = {id: 't1', ref: 'asr-9006', cfg: 'base', label: 'tall', ru: 2, u: 10, face: 'front', turned: false};
  const short = {id: 't2', ref: 'tm-280', cfg: 'base', label: 'short', ru: 5, u: 1, face: 'front', turned: false};
  const types = new Map([['t1', {manufacturer: 'Cisco', model: 'ASR-9006-AC-V2', isFullDepth: false, guess: false}],
                          ['t2', {manufacturer: 'Telco Systems', model: 'TM-280', isFullDepth: false, guess: false}]]);
  const {rows} = X.deviceImportRows({rack: RACK, items: [short, tall], types, target: 'netbox'});
  assert.deepEqual(rows.map(r => r.name), ['tall', 'short']);
});

test('positions follow a top-down frame', () => {
  const rack = {...RACK, frame: {...RACK.frame, numbering: 'top-down'}};
  assert.deepEqual(X.deviceImportRows({rack, items: ITEMS, types: TYPES}).rows.map(r => r.position), [5, 11, 14]);
  assert.deepEqual(X.deviceImportRows({rack, items: ITEMS, types: TYPES, target: 'nautobot'}).rows.map(r => r.position), [5, 11, 11, 14]);
  assert.match(X.deviceImportRows({rack, items: ITEMS, types: TYPES}).left[0].reason, /^demarc-i3 is not in the devices file: it shares U11 with leaf-1/);
});

test('Nautobot rows use natural-key columns, keep two devices that share a U, and leave out a device with no type', () => {
  const types = new Map([...TYPES, ['i1', null]]);
  const {columns, rows, left} = X.deviceImportRows({rack: RACK, items: ITEMS, types, target: 'nautobot', dcim: {site: ' Lab 1 ', role: 'R'}});
  assert.deepEqual(columns, ['name', 'role__name', 'device_type__manufacturer__name', 'device_type__model',
    'status__name', 'location__name', 'rack__name', 'rack__location__name', 'position', 'face', 'comments']);
  assert.deepEqual([rows[1].device_type__manufacturer__name, rows[1].device_type__model, rows[1].status__name,
                    rows[1].rack__name], ['Edgecore', '7726-32X-O-AC-F', 'Planned', 'Export test']);
  // The rack is found by its name AND its location: rack names repeat from one location to the next. The
  // column holds the device's own location, on every row.
  assert.ok(rows.every(r => r.location__name === 'Lab 1' && r.rack__location__name === 'Lab 1'));
  assert.ok(X.deviceImportRows({rack: RACK, items: ITEMS, types, target: 'nautobot'}).rows.every(r => r.rack__location__name === ''));
  assert.ok(!X.deviceImportRows({rack: RACK, items: ITEMS, types}).columns.some(c => c.includes('location')), 'NetBox has no such column');
  // Nautobot 3.2.6 accepted leaf-1 and demarc-i3 at U14, front and rear: both rows stay, and neither is called refused.
  assert.deepEqual(rows.map(r => r.name), ['demarc-i4', 'leaf-1', 'demarc-i3']);
  assert.ok(rows.every(r => !/refuses/.test(r.comments)));
  assert.deepEqual(left, [{id: 'i1', name: 'core-1', reason:
    'core-1 is not in the devices file: there is no Nautobot device type for asr-9006 (base). Add the type and the device by hand.'}]);
});

test('a type from another vendor says so in the row\'s comments, as the README does', () => {
  const types = new Map([['i1', {manufacturer: 'Cisco', model: 'ASR-9006-AC-V2', isFullDepth: false, guess: true,
    otherVendor: true, chassisManufacturer: 'Nobody Inc', path: nb('Cisco', 'ASR-9006-AC-V2')}]]);
  const item = {id: 'i1', ref: 'asr-9006', cfg: 'base', label: 'core-1', ru: 2, u: 4, face: 'front', turned: false};
  const {rows} = X.deviceImportRows({rack: RACK, items: [item], types, target: 'netbox'});
  assert.equal(rows[0].comments, 'core-1 (asr-9006): no NetBox device type from Nobody Inc, so ' +
    "ASR-9006-AC-V2 is another vendor's (Cisco) file, a best guess.");
});

test('NetBox: of two devices sharing a U front and rear, the later-placed is left out while either type is full depth', () => {
  const full = {manufacturer: 'M', model: 'X', isFullDepth: true, guess: false}, half = {...full, isFullDepth: false};
  const items = [
    {id: 'a', ref: 'r', cfg: 'base', label: 'tall', ru: 10, u: 6, face: 'front', turned: false},
    {id: 'b', ref: 'r', cfg: 'base', label: 'one', ru: 11, u: 1, face: 'rear', turned: false},
    {id: 'c', ref: 'r', cfg: 'base', label: 'two', ru: 13, u: 1, face: 'rear', turned: false},
    {id: 'd', ref: 'r', cfg: 'base', label: 'three', ru: 20, u: 1, face: 'rear', turned: false}];
  const all = new Map(items.map(i => [i.id, full]));
  const got = X.deviceImportRows({rack: RACK, items, types: all, target: 'netbox'});
  assert.deepEqual(got.rows.map(r => r.name), ['three', 'tall']);
  assert.deepEqual(got.left.map(l => l.id), ['b', 'c']);
  assert.match(got.left[0].reason, /^one is not in the devices file: it shares U11 with tall on the front, and NetBox refuses/);
  // The rack's own order is the order they were placed: placed first, kept.
  const rearFirst = X.deviceImportRows({rack: RACK, items: [items[1], items[0]], types: all, target: 'netbox'});
  assert.deepEqual([rearFirst.rows.map(r => r.name), rearFirst.left.map(l => l.name)], [['one'], ['tall']]);
  assert.match(rearFirst.left[0].reason, /it shares U10 with one on the rear/);
  // A device left out takes no room: the next one is judged against what is in the file.
  const chain = [items[1], items[0], {...items[2], ru: 12}];
  assert.deepEqual(X.deviceImportRows({rack: RACK, items: chain, types: all, target: 'netbox'}).left.map(l => l.name), ['tall']);
  // Neither type full depth: NetBox takes both. Either one: it does not.
  assert.deepEqual(X.deviceImportRows({rack: RACK, items, types: new Map(items.map(i => [i.id, half])), target: 'netbox'}).left, []);
  assert.deepEqual(X.deviceImportRows({rack: RACK, items, types: new Map([...all, ['a', half]]), target: 'netbox'}).left.map(l => l.id), ['b', 'c']);
  // The same face is the page's own rule (fit.js), not this one; Nautobot keeps every pair.
  assert.deepEqual(X.deviceImportRows({rack: RACK, items, types: all, target: 'nautobot'}).left, []);
});

test('the other-vendor comment wins over a certain match (guess: false)', () => {
  const types = new Map([['i1', {manufacturer: 'Cisco', model: 'ASR-9006-AC-V2', isFullDepth: false, guess: false,
    otherVendor: true, chassisManufacturer: 'Nobody Inc', path: nb('Cisco', 'ASR-9006-AC-V2')}]]);
  const item = {id: 'i1', ref: 'asr-9006', cfg: 'base', label: 'core-1', ru: 2, u: 4, face: 'front', turned: false};
  const {rows} = X.deviceImportRows({rack: RACK, items: [item], types, target: 'netbox'});
  assert.match(rows[0].comments, /another vendor's \(Cisco\) file/);
  assert.doesNotMatch(rows[0].comments, /best guess for configuration/);
});

test('a device label that starts with = stays verbatim in the DCIM CSV (only the BOM guards it)', () => {
  const item = {id: 'i1', ref: 'asr-9006', cfg: 'base', label: '=core', ru: 2, u: 4, face: 'front', turned: false};
  const types = new Map([['i1', {manufacturer: 'Cisco', model: 'ASR-9006-AC-V2', isFullDepth: false, guess: false}]]);
  const {columns, rows} = X.deviceImportRows({rack: RACK, items: [item], types, target: 'netbox'});
  const csv = X.toCsv(columns, rows);
  assert.ok(csv.split('\r\n')[1].startsWith('=core,'), csv);
  assert.ok(!csv.includes("'=core"));
});

test('a device that is not rack-mount says so in its own comments', () => {
  const rack = {name: 'r', frame: M.normalizeFrame({heightRU: 4})};
  const items = [{id: 'a', ref: 'hlx-tgv', cfg: '', label: 'tgv', ru: 1, u: 1, face: 'front', mount: 'desktop'}];
  const types = new Map([['a', {manufacturer: 'M', model: 'X', isFullDepth: false, guess: false}]]);
  const {rows} = X.deviceImportRows({rack, items, types, target: 'netbox'});
  assert.match(rows[0].comments, /A desktop device, so it needs a shelf\./);
});

test('a manager is a device row with no position and no face, and never knocks out its host', () => {
  const host = {id: 'i1', ref: 'as7726-32x', cfg: 'x', label: 'leaf-1', ru: 12, u: 1, face: 'front'};
  const mgr = {id: 'i2', ref: 'fhd-cmp5dr', cfg: 'x', label: 'mgr-1', ru: 12, u: 1, face: 'front', mount: 'rack-face', on: 'i1', unit: 1};
  const rack = {name: 'R', frame: {heightRU: 42, numbering: 'bottom-up'}};
  const rearDeep = {id: 'i3', ref: 'tm-280', cfg: 'x', label: 'demarc', ru: 12, u: 1, face: 'rear'};
  const types = new Map([['i1', {model: 'AS7726', manufacturer: 'Edgecore', isFullDepth: true}],
                         ['i2', {model: 'FHD-CMP5DR', manufacturer: 'FS.com', isFullDepth: false}],
                         ['i3', {model: 'TM-280', manufacturer: 'Telco', isFullDepth: true}]]);
  const {rows, left} = X.deviceImportRows({rack, items: [host, mgr], types, dcim: {site: 's', role: 'r'}});
  const m = rows.find(r => r.name === 'mgr-1');
  assert.deepEqual([m.position, m.face], ['', '']);
  assert.match(m.comments, /0U cable manager on the front rail face at U12, over leaf-1; NetBox has no field for that\./);
  assert.equal(left.length, 0);
  const two = X.deviceImportRows({rack, items: [rearDeep, mgr], types, dcim: {site: 's', role: 'r'}});
  assert.equal(two.left.length, 0);
});
