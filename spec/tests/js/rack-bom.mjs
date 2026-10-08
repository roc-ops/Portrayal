import test from 'node:test';
import assert from 'node:assert/strict';
import * as X from '../../../kit/rack/export-data.js';
import * as M from '../../../kit/rack/model.js';

test('a seated part is a bay module or a cage occupant, nothing else', () => {
  for (const p of ['slot-2/module', 'port-1-occupant', 'slot-7/module/inp-com-occupant', 'slot-2/module/sub/module'])
    assert.equal(X.isSeatedPath(p), true, p);
  for (const p of ['fan-tray-door', 'port-1', 'slot-2/module/p0', 'esd-jack'])
    assert.equal(X.isSeatedPath(p), false, p);
});

test('parts are grouped by class', () => {
  assert.equal(X.sectionOf('line-card'), 'Line cards');
  assert.equal(X.sectionOf('transceiver'), 'Optics');
  assert.equal(X.sectionOf('port'), 'Plugs');
  assert.equal(X.sectionOf('led'), 'Other parts');
});

test('manufacturer and description come from the DCIM file and the component', () => {
  assert.equal(X.partManufacturer({ns: 'cisco'}, 'netbox/module-types/Cisco/A9K-3KW-AC.yaml'), 'Cisco');
  // The DIRECTORY the module type is filed under, and it is not turned back into
  // the name: a name holding a slash is filed with a hyphen (Portrayal #826) and
  // the hyphen form is all the BOM has, which export-data.js partManufacturer
  // explains. A real hyphen in a name reads the same way here, as it always did.
  assert.equal(X.partManufacturer({ns: 'telco-systems'}, 'netbox/module-types/BATM-Telco Systems/TM810x AC PSU.yaml'),
    'BATM-Telco Systems');
  assert.equal(X.partManufacturer({ns: 'telco-systems'}, null), 'Telco Systems');
  assert.equal(X.partManufacturer({ns: 'generic'}, null), '');
  assert.equal(X.partManufacturer(null, null), '');
  assert.equal(X.firstSentence('Cisco X Line Card, 4th generation. Ten ports.'), 'Cisco X Line Card, 4th generation.');
  assert.equal(X.firstSentence(undefined), '');
});

test('the BOM counts devices by configuration and parts by reference, hardware last', () => {
  const card = {ref: 'cisco/a9k-16x100ge-tr@1', cls: 'line-card', manufacturer: 'Cisco', model: 'A9K-16X100GE-TR', description: 'Card.'};
  const cover = {ref: 'cisco/a9k-slot-cover@1', cls: 'blank', manufacturer: 'Cisco', model: 'A9K Slot Cover', description: 'Blank.'};
  const optic = {ref: 'generic/qsfp-lc@2', cls: 'transceiver', manufacturer: '', model: '', description: 'An optic.'};
  const rivet = {ref: 'common/rivet@1', cls: 'mechanical', manufacturer: '', model: '', description: ''};
  const tm = {ref: 'tm-280', cfg: 'base', manufacturer: 'Telco Systems', model: 'TM-280'};
  const rows = X.bomRows({
    devices: [tm, tm, {ref: 'asr-9006', cfg: 'base', manufacturer: 'Cisco', model: 'ASR 9006'}],
    parts: [cover, optic, card, cover, rivet], frame: M.defaultFrame(), railUs: [1, 1, 10]});
  assert.deepEqual(rows.map(r => [r.section, r.model || r.ref, r.qty]), [
    ['Devices', 'ASR 9006', 1], ['Devices', 'TM-280', 2], ['Line cards', 'A9K-16X100GE-TR', 1],
    ['Blanks', 'A9K Slot Cover', 2], ['Optics', 'generic/qsfp-lc@2', 1], ['Other parts', 'common/rivet@1', 1],
    ['Mounting hardware', 'Cage nut, M6', 48], ['Mounting hardware', 'Screw, M6', 48]]);
  assert.equal(rows[0].description, 'Configuration base');
  assert.deepEqual(X.BOM_COLUMNS, ['section', 'qty', 'manufacturer', 'model', 'description', 'ref']);
});

test('a BOM cell that opens as a formula is guarded; the device-import CSV cell is not', () => {
  const label = '=HYPERLINK("x")';
  assert.equal(X.bomCell(label), '"\'=HYPERLINK(""x"")"');
  assert.equal(X.csvCell(label), '"=HYPERLINK(""x"")"');
  assert.equal(X.bomCell('+1'), "'+1");
  assert.equal(X.bomCell('-5'), "'-5");
  assert.equal(X.bomCell('@cmd'), "'@cmd");
  assert.equal(X.bomCell('plain'), 'plain');
  // A tab or carriage return ahead of a formula opens it too.
  assert.equal(X.bomCell('\t=1+1'), "'\t=1+1");
  assert.equal(X.bomCell('\r=1+1'), `"'\r=1+1"`);
  assert.equal(X.bomCell(null), '');
  const line = X.toCsv(X.BOM_COLUMNS, [{section: 'Devices', qty: 1, manufacturer: '', model: label,
    description: '', ref: 'r1'}], [], {cell: X.bomCell}).split('\r\n')[1];
  assert.equal(line, 'Devices,1,,"\'=HYPERLINK(""x"")",,r1');
});

test('mounting hardware is 4 per U: cage nuts and screws, or screws of the thread', () => {
  const tapped = M.normalizeFrame({holes: {style: 'tapped', thread: '12-24'}});
  assert.deepEqual(X.hardwareRows(tapped, [2]), [{section: 'Mounting hardware', qty: 8, manufacturer: '',
    model: 'Screw, 12-24', description: 'Two per ear for each U a device covers', ref: ''}]);
  assert.equal(X.hardwareRows(M.normalizeFrame({holes: {style: 'tapped'}}), [1])[0].model, 'Screw, thread not stated');
  assert.deepEqual(X.hardwareRows(M.defaultFrame(), []), []);
  assert.match(X.hardwareNotes(M.defaultFrame())[0], /M6/);
  assert.match(X.hardwareNotes(M.normalizeFrame({holes: {style: 'tapped'}}))[0], /thread is not set/);
  assert.deepEqual(X.hardwareNotes(tapped), []);
});

test('a seated part with no part number is listed by its reference', () => {
  const rows = X.bomRows({devices: [], parts: [{ref: 'no/such-part@1', cls: 'other'}], frame: M.normalizeFrame({heightRU: 4}), railUs: []});
  const row = rows.find(r => r.ref === 'no/such-part@1');
  assert.equal(row.model, 'no/such-part@1');
});

test('a hosted manager adds no rail hardware; an unhosted one counts its own U', () => {
  const frame = {holes: {style: 'square'}};
  const qty = railUs => X.bomRows({frame, railUs}).find(r => r.model === 'Cage nut, M6')?.qty ?? 0;
  assert.equal(qty([1]), 4);          // the host alone
  assert.equal(qty([1, 1]), 8);       // plus one unhosted manager
});

test('a routed cable length is marked as routed in the BOM', () => {
  const rack = {cables: [{id: 'c1', media: 'cat6', a: {item: 'i1'}, b: {item: 'i2'},
    length: {value: 2, unit: 'm', source: 'routed', measured: 1.62}}]};
  const [line] = X.cableBomRows(rack);
  assert.match(line.description, /^2 m \(routed\)/);
});
