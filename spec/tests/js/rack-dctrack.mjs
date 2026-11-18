import test from 'node:test';
import assert from 'node:assert/strict';
import * as D from '../../../kit/rack/dctrack.js';

// A small rack, written by hand: two devices on the rails (one on the rear face),
// a power strip beside the rack (no U), a held shelf item (no U) and a device the
// library has no type for.
const frame = (numbering = 'bottom-up') => ({kind: 'four-post', heightRU: 42, numbering});
const rack = (numbering, site = 'Hall 1') => ({
  name: 'R1', frame: frame(numbering), dcim: {site, role: 'leaf'},
  items: [
    {id: 'a', ref: 'sw1', cfg: 'base', label: 'leaf-1', ru: 3, face: 'front'},
    {id: 'b', ref: 'srv', cfg: 'base', label: 'srv-1', ru: 10.5, face: 'rear'},
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
const sheets = (r = rack()) => D.dctrackSheets({rack: r, items: items(r), types});
const rows = (s, name) => s.sheets[name].rows;

test('the sheets come in the template\'s order, with the names its figures print', () => {
  const s = sheets();
  assert.deepEqual(Object.keys(s.sheets), ['locations', 'cabinets', 'devices']);
  assert.deepEqual(s.sheets.locations.columns,
    ['# Operation', 'Object', 'dcTrack Location Code', 'dcTrack Location Name', 'Data Center Area', 'Country', 'Units']);
  assert.deepEqual(s.sheets.cabinets.columns, ['# Operation', 'Object', 'Name', 'Make', 'Model', 'Location']);
  assert.deepEqual(s.sheets.devices.columns,
    ['# Operation', 'Object', 'Name', 'Make', 'Model', 'Location', 'Cabinet', 'U Position', 'Orientation']);
  assert.deepEqual(D.FILES, {locations: '1-locations.csv', cabinets: '2-cabinets.csv', devices: '4-devices.csv'});
});

test('what is a stand-in is named, and every other header is one the guides print', () => {
  for (const stand of ['devices.Object', 'devices.Orientation values', 'locations.dcTrack Location Code'])
    assert.ok(D.STAND_INS.includes(stand), stand);
  assert.ok(D.STAND_INS.some(t => t.includes('asterisk')));
  assert.ok(D.HEADERS_NOT_SHOWN_AS_CELLS.includes('U Position') && D.HEADERS_NOT_SHOWN_AS_CELLS.includes('Orientation'));
});

test('every row asks for an ADD, and an object the template prints', () => {
  const s = sheets();
  for (const name of ['locations', 'cabinets', 'devices'])
    for (const r of rows(s, name)) assert.equal(r['# Operation'], 'ADD');
  assert.equal(rows(s, 'locations')[0].Object, 'LOCATION');
  assert.equal(rows(s, 'locations')[0].Units, 'SI');
  assert.equal(rows(s, 'cabinets')[0].Object, 'CABINET');
});

test('the site is the location, and the rack is a cabinet in it', () => {
  const s = sheets();
  const loc = rows(s, 'locations')[0];
  assert.equal(loc['dcTrack Location Name'], 'Hall 1');
  assert.equal(loc['dcTrack Location Code'], 'Hall 1');
  assert.equal(rows(s, 'cabinets')[0].Name, 'R1');
  assert.equal(rows(s, 'cabinets')[0].Location, 'Hall 1');
});

test('a field the template requires and a rack file has no source for is blank and named in notes', () => {
  const s = sheets();
  const loc = rows(s, 'locations')[0];
  assert.equal(loc['Data Center Area'], '');
  assert.equal(loc.Country, '');
  const cab = rows(s, 'cabinets')[0];
  assert.equal(cab.Make, '');
  assert.equal(cab.Model, '');
  for (const word of ['Data Center Area', 'Country', 'Make and Model'])
    assert.ok(s.notes.some(n => n.includes(word)), word);
});

test('every device row names its location, cabinet, make and model', () => {
  const s = sheets();
  assert.deepEqual(rows(s, 'devices').map(r => [r.Name, r.Make, r.Model]),
    [['leaf-1', 'Acme', 'SW-1'], ['srv-1', 'Acme', 'SRV-1'], ['pdu-1', 'Acme', 'PDU-1'], ['held-1', 'Acme', 'BOX-1']]);
  for (const r of rows(s, 'devices')) {
    assert.equal(r.Location, 'Hall 1');
    assert.equal(r.Cabinet, 'R1');
  }
});

test('U Position is the lowest U the item fills, a half unit as it is, and Orientation says which way it faces', () => {
  const s = sheets();
  const placed = rows(s, 'devices').filter(r => r['U Position'] !== '');
  assert.deepEqual(placed.map(r => [r.Name, r['U Position'], r.Orientation]),
    [['leaf-1', 3, 'Item Front Faces Cabinet Front'], ['srv-1', 10.5, 'Item Rear Faces the Cabinet Front']]);
});

test('a top-down rack counts its lowest U from the top, as the rack labels it', () => {
  const s = sheets(rack('top-down'));
  // 42U, ru 3 and 2U high: its lowest label is 42 + 2 - 3 - 2 = 39
  assert.equal(rows(s, 'devices')[0]['U Position'], 39);
});

test('an item with no U is a row with a blank position and orientation and is named in skipped', () => {
  const s = sheets();
  const byName = Object.fromEntries(rows(s, 'devices').map(r => [r.Name, r]));
  assert.equal(byName['pdu-1']['U Position'], '');
  assert.equal(byName['pdu-1'].Orientation, '');
  assert.equal(byName['held-1']['U Position'], '');
  assert.ok(!('mystery' in byName));
  const byId = Object.fromEntries(s.skipped.map(k => [k.id, k]));
  assert.deepEqual(Object.keys(byId).sort(), ['h', 'n', 'p']);
  assert.match(byId.p.reason, /no U position/);
  assert.match(byId.h.reason, /no U position/);
  assert.match(byId.n.reason, /no model/);
  assert.equal(byId.n.name, 'mystery');
});

test('a rack with no site is written with a blank location, and says so', () => {
  const s = sheets(rack('bottom-up', ''));
  assert.deepEqual(rows(s, 'locations'), []);
  assert.equal(rows(s, 'cabinets')[0].Location, '');
  assert.ok(s.notes.some(n => /no site/.test(n)));
});

test('a rack that numbers its units from another start says so', () => {
  const r = rack();
  r.frame.startU = 5;
  assert.ok(sheets(r).notes.some(n => /numbers its units from 5/.test(n)));
});

test('a name over the printed limits, or with a character dcTrack refuses, is written as it is and noted', () => {
  const r = rack('bottom-up', 'A site name that is longer than twenty characters');
  r.items[0].label = "leaf & 'one'";
  r.name = 'x'.repeat(65);
  const s = sheets(r);
  assert.equal(rows(s, 'locations')[0]['dcTrack Location Code'], '');
  assert.ok(s.notes.some(n => /Location Code.*20 characters/.test(n)));
  assert.ok(s.notes.some(n => /Location Name.*50 characters/.test(n)) === false);
  assert.ok(s.notes.some(n => /64 characters/.test(n)));
  assert.ok(s.notes.some(n => /\\ & \? '/.test(n)));
  assert.equal(rows(s, 'devices')[0].Name, "leaf & 'one'");
});

test('what the sheets leave out is stated', () => {
  const s = sheets();
  for (const word of ['connections', 'images', 'ports', 'Rails Used', 'Status'])
    assert.ok(D.LEFT_OUT.some(t => t.includes(word)), word);
  assert.ok(s.notes.every(n => typeof n === 'string'));
});

test('csv text quotes a cell with a comma and ends each line with CRLF', () => {
  const r = rack();
  r.items[0].label = 'leaf, 1';
  const s = D.dctrackSheets({rack: r, items: items(r), types});
  const text = D.sheetCsv(s.sheets.devices);
  assert.equal(text.split('\r\n')[0], '# Operation,Object,Name,Make,Model,Location,Cabinet,U Position,Orientation');
  assert.ok(text.includes('ADD,DEVICE,"leaf, 1",Acme,SW-1,Hall 1,R1,3,Item Front Faces Cabinet Front'));
  assert.ok(text.endsWith('\r\n'));
});
