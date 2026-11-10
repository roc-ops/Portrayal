import test from 'node:test';
import assert from 'node:assert/strict';
import * as I from '../../../kit/rack/infrahub.js';

// A small rack, written by hand: a device on the rails, one at a half unit, a
// power strip on the rack face (0U), a held shelf item and a device with no type.
const rack = (numbering = 'bottom-up', site = 'Hall 1') => ({
  name: 'R1', frame: {kind: 'four-post', heightRU: 42, numbering}, dcim: {site, role: 'leaf'},
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
const out = (r = rack()) => I.infrahubObjects({rack: r, items: items(r), types});
const docOf = (o, file) => o.files[file][0].spec.data;

// The type name rule of `type_name()` in spec/tools/dev/infrahub_export.py:
//   return f"{doc['manufacturer']} {doc['model']}"
// copied here, since the python and the kit import nothing of each other.
const pyTypeName = doc => `${doc.manufacturer} ${doc.model}`;

test('the files come in load order, each document an Object with its kind and a data list', () => {
  const o = out();
  assert.deepEqual(Object.keys(o.files), ['1-sites.yml', '2-racks.yml', '3-devices.yml']);
  const kinds = ['LocationSite', 'LocationRack', 'DcimDevice'];
  Object.values(o.files).forEach((docs, k) => {
    assert.equal(docs.length, 1);
    assert.equal(docs[0].apiVersion, 'infrahub.app/v1');
    assert.equal(docs[0].kind, 'Object');
    assert.equal(docs[0].spec.kind, kinds[k]);
    assert.ok(Array.isArray(docs[0].spec.data));
  });
});

test('the rack is written with its name, height and site, and the site beside it', () => {
  const o = out();
  assert.deepEqual(docOf(o, '1-sites.yml'), [{name: 'Hall 1'}]);
  assert.deepEqual(docOf(o, '2-racks.yml'), [{name: 'R1', height: 42, site: 'Hall 1'}]);
});

test('every device has a location naming a rack in the output, a face, and a position inside the height', () => {
  const o = out();
  const racks = docOf(o, '2-racks.yml');
  const devs = docOf(o, '3-devices.yml');
  assert.ok(devs.length > 0);
  for (const d of devs) {
    assert.equal(d.location.kind, 'LocationRack');
    const r = racks.find(x => x.name === d.location.data.name && x.site === d.location.data.site);
    assert.ok(r, `${d.name}: its location is a rack in the output`);
    assert.ok(['front', 'rear'].includes(d.rack_face));
    if ('position' in d) {
      assert.ok(Number.isInteger(d.position));
      assert.ok(d.position >= 1 && d.position <= r.height);
    }
  }
});

test('a half unit is written rounded down and a zero-U or held part has no position', () => {
  const byName = Object.fromEntries(docOf(out(), '3-devices.yml').map(d => [d.name, d]));
  assert.equal(byName['leaf-1'].position, 3);
  assert.equal(byName['srv-1'].position, 10);
  assert.equal(byName['srv-1'].rack_face, 'rear');
  assert.ok(!('position' in byName['pdu-1']));
  assert.ok(!('position' in byName['held-1']));
});

test('device names are unique, and the kit names a clash as the other kits do', () => {
  const r = rack();
  r.items[1].label = 'leaf-1';
  const names = docOf(out(r), '3-devices.yml').map(d => d.name);
  assert.equal(new Set(names.map(n => n.toLowerCase())).size, names.length);
  assert.ok(names.includes('leaf-1-a') && names.includes('leaf-1-b'));
});

test('a device type is named <manufacturer> <model>, as the device-side exporter names it', () => {
  const byName = Object.fromEntries(docOf(out(), '3-devices.yml').map(d => [d.name, d]));
  assert.equal(byName['leaf-1'].device_type, pyTypeName({manufacturer: 'Acme', model: 'SW-1'}));
  assert.equal(byName['srv-1'].device_type, 'Acme SRV-1');
  assert.equal(I.typeName({manufacturer: 'Acme', model: 'X'}), 'Acme X');
});

test('a device with no type is not an object and is named in skipped', () => {
  const o = out();
  assert.ok(!docOf(o, '3-devices.yml').some(d => d.name === 'mystery'));
  assert.deepEqual(o.skipped.map(s => [s.id, s.name]), [['n', 'mystery']]);
  assert.match(o.skipped[0].reason, /no device type/);
});

test('a rack with no site is written without one, and says so', () => {
  const o = out(rack('bottom-up', ''));
  assert.ok(!('1-sites.yml' in o.files));
  assert.deepEqual(docOf(o, '2-racks.yml'), [{name: 'R1', height: 42}]);
  assert.ok(docOf(o, '3-devices.yml').every(d => !('site' in d.location.data)));
  assert.ok(o.notes.some(n => /no site/.test(n)));
});

test('the lossy steps are named in the notes', () => {
  const text = out(rack('top-down')).notes.join('\n');
  assert.match(text, /from the top/);
  assert.match(text, /half unit/);
  assert.match(text, /planned/);
  assert.match(text, /no U position/);
});

test('a top-down rack writes its positions bottom-up', () => {
  const byName = Object.fromEntries(docOf(out(rack('top-down')), '3-devices.yml').map(d => [d.name, d]));
  assert.equal(byName['leaf-1'].position, 3);
});

test('the readme names the load order, what is not confirmed and what is left out', () => {
  const o = out();
  const text = I.infrahubReadme(o);
  for (const f of Object.values(I.FILES)) assert.ok(text.includes(f));
  assert.match(text, /Not confirmed/);
  assert.match(text, /Left out/);
  assert.ok(text.includes('mystery'));
});

test('file text is one YAML document per object document', () => {
  const o = out();
  const text = I.fileText(o.files['3-devices.yml']);
  assert.ok(text.startsWith('---\n'));
  assert.deepEqual(JSON.parse(text.slice(4)), o.files['3-devices.yml'][0]);
});
