import test from 'node:test';
import assert from 'node:assert/strict';
import * as D from '../../../kit/rack/device42.js';

// A small rack, written by hand: two devices on the rails, a power strip beside
// the rack (no U), a held shelf item (no U) and a device the library has no type for.
const frame = (numbering = 'bottom-up') => ({kind: 'four-post', heightRU: 42, numbering});
const rack = (numbering, site = 'Hall 1') => ({
  name: 'R1', frame: frame(numbering), dcim: {site, role: 'leaf'},
  items: [
    {id: 'a', ref: 'sw1', cfg: 'base', label: 'leaf-1', ru: 3, face: 'front'},
    {id: 'b', ref: 'srv', cfg: 'base', label: 'srv-1', ru: 10.5, face: 'front'},
    {id: 'p', ref: 'pdu', cfg: 'base', label: 'pdu-1', ru: 1, face: 'rear', mount: 'rack-face'},
    {id: 'h', ref: 'box', cfg: 'base', label: 'held-1', ru: 20, face: 'front', mount: 'shelf', heldBy: {item: 'b'}},
    {id: 'n', ref: 'nothing', cfg: 'base', label: 'mystery', ru: 30, face: 'front'},
  ],
});
const items = r => r.items.map(i => ({...i, u: i.id === 'a' ? 2 : 1}));
const types = new Map([
  ['a', {manufacturer: 'Acme', model: 'SW-1'}],
  ['b', {manufacturer: 'Acme', model: 'SRV-1'}],
  ['p', {manufacturer: 'Acme', model: 'PDU-1'}],
  ['h', {manufacturer: 'Acme', model: 'BOX-1'}],
]);
const sheets = (r = rack()) => D.device42Sheets({rack: r, items: items(r), types});
const rows = (s, name) => s.sheets[name].rows;

test('the sheets come in the import sequence, with the declared headers', () => {
  const s = sheets();
  assert.deepEqual(Object.keys(s.sheets), ['buildings', 'rooms', 'racks', 'devices', 'devices-to-racks']);
  assert.deepEqual(s.sheets.buildings.columns, ['name']);
  assert.deepEqual(s.sheets.rooms.columns, ['name', 'building']);
  assert.deepEqual(s.sheets.racks.columns, ['name', 'size', 'room']);
  assert.deepEqual(s.sheets.devices.columns, ['name', 'hardware']);
  assert.deepEqual(s.sheets['devices-to-racks'].columns, ['name', 'rack', 'start_at']);
  assert.deepEqual(D.FILES, {buildings: '1-buildings.csv', rooms: '2-rooms.csv', racks: '3-racks.csv',
    devices: '5-devices.csv', 'devices-to-racks': '6-devices-to-racks.csv'});
});

test('the racks sheet has the rack name, its U size and its room', () => {
  const s = sheets();
  assert.deepEqual(rows(s, 'buildings'), [{name: 'Hall 1'}]);
  assert.deepEqual(rows(s, 'rooms'), [{name: 'Hall 1', building: 'Hall 1'}]);
  assert.deepEqual(rows(s, 'racks'), [{name: 'R1', size: 42, room: 'Hall 1'}]);
});

test('every device row names its hardware model and every placement its rack', () => {
  const s = sheets();
  assert.deepEqual(rows(s, 'devices').map(r => [r.name, r.hardware]),
    [['leaf-1', 'SW-1'], ['srv-1', 'SRV-1'], ['pdu-1', 'PDU-1'], ['held-1', 'BOX-1']]);
  for (const r of rows(s, 'devices-to-racks')) assert.equal(r.rack, 'R1');
  for (const r of rows(s, 'devices-to-racks')) assert.ok(rows(s, 'devices').some(d => d.name === r.name));
});

test('start_at is the lowest U the device fills, a half unit as it is', () => {
  const s = sheets();
  assert.deepEqual(rows(s, 'devices-to-racks'),
    [{name: 'leaf-1', rack: 'R1', start_at: 3}, {name: 'srv-1', rack: 'R1', start_at: 10.5}]);
  assert.ok(rows(s, 'devices-to-racks').every(r => r.start_at !== 'auto'));
});

test('a top-down rack counts its lowest U from the top, as the rack labels it', () => {
  const s = sheets(rack('top-down'));
  // 42U, ru 3 and 2U high: its lowest label is 42 + 2 - 3 - 2 = 39
  assert.equal(rows(s, 'devices-to-racks')[0].start_at, 39);
});

test('a device with no U is listed with no position and named in skipped', () => {
  const s = sheets();
  assert.ok(!rows(s, 'devices-to-racks').some(r => ['pdu-1', 'held-1', 'mystery'].includes(r.name)));
  assert.ok(rows(s, 'devices').some(r => r.name === 'pdu-1'));
  const byId = Object.fromEntries(s.skipped.map(k => [k.id, k]));
  assert.deepEqual(Object.keys(byId).sort(), ['h', 'n', 'p']);
  assert.match(byId.p.reason, /no U position/);
  assert.match(byId.h.reason, /no U position/);
  assert.match(byId.n.reason, /no hardware model/);
  assert.equal(byId.n.name, 'mystery');
});

test('a rack with no site is written with a blank room, and says so', () => {
  const s = sheets(rack('bottom-up', ''));
  assert.deepEqual(rows(s, 'buildings'), []);
  assert.deepEqual(rows(s, 'racks'), [{name: 'R1', size: 42, room: ''}]);
  assert.ok(s.notes.some(n => /no site/.test(n)));
});

test('csv text quotes a cell with a comma and ends each line with CRLF', () => {
  const r = rack();
  r.items[0].label = 'leaf, 1';
  const s = D.device42Sheets({rack: r, items: items(r), types});
  const text = D.sheetCsv(s.sheets.devices);
  assert.equal(text.split('\r\n')[0], 'name,hardware');
  assert.ok(text.includes('"leaf, 1",SW-1'));
  assert.ok(text.endsWith('\r\n'));
});
