// LAMPS, DIGITS, OUTLETS, BREAKERS AND DISPLAYS IN A RACK, with the real library
// (kit/rack/view/settable.js paintMaps): the maps a drawing is handed for the
// public test racks. The rules are the kit's and are tested there. The cases of
// portrayal-site's tests/rack/lamps-displays.test.mjs (5dbbd41bd3) that read
// settable.js, moved with it; the ones that read the agent's tools stay in the
// site. Reads the real build (library/dist).
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {test, finish} from './view-cases.mjs';
import {parseDoc} from '../../../kit/rack/model.js';
import {paints, paintMaps} from '../../../kit/rack/view/settable.js';

const DIST = new URL('../../../library/dist/', import.meta.url);
assert.ok(existsSync(new URL('rack.json', DIST)), 'no library/dist: run ./build.sh first (the suite reads the build)');
const dist = f => JSON.parse(readFileSync(new URL(f, DIST)));
const fixture = f => JSON.parse(readFileSync(new URL(`../fixtures/rack-view-site/${f}`, import.meta.url)));
const devices = dist('rack.json').devices;
const comps = new Map(dist('components.json').components.map(c => [`${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`, c]));
const cache = new Map();
const slotsOf = ref => {
  if (!cache.has(ref)) {
    const j = dist(`${ref}.configs.json`);
    cache.set(ref, {bays: j.bays || {}, cages: j.cages || {}, configs: j.configs || [], default: j.default ?? null, 'pdu-class': j['pdu-class'] ?? null});
  }
  return cache.get(ref);
};
const compByRef = ref => (ref == null ? null : comps.get(String(ref).split(':')[0]) ?? null);
const chassisOf = ref => devices[ref] ?? null;
const ctx = {chassisOf, slotsOf, compByRef};
const rackOf = name => parseDoc(fixture(name)).racks[0];

test('the test racks open with nothing said against them', () => {
  for (const f of ['lamps-displays.rack.json', 'keystone-rear.rack.json']) {
    const doc = parseDoc(fixture(f));
    assert.ok(doc.racks[0].items.length >= 2, f);
  }
});

test('a rack that sets nothing paints nothing, and reads no parts list for it', async () => {
  const r = rackOf('keystone-rear.rack.json');
  assert.equal(paints(r), false);
  assert.equal((await paintMaps(r, {}, async () => null)).size, 0);
});

test('every lamp, digit, outlet, breaker and display the test rack sets is handed to its drawing', async () => {
  const r = rackOf('lamps-displays.rack.json');
  assert.equal(paints(r), true);
  const maps = await paintMaps(r, ctx, async () => null);
  const sw = maps.get('i1').states;
  assert.equal(sw['led-sys'], 'ok');
  assert.equal(sw['led-port-4/lamp'], 'on');
  assert.equal(sw['status-display/digit-2'], '4');
  assert.equal(maps.get('i2').displays.beacon.digits, '1f');
  const pdu = maps.get('z1');
  assert.equal(pdu.states['led-a1'], 'on');
  assert.equal(pdu.states['breaker-a/rocker'], 'on');
  assert.equal(pdu.states['outlet-b8'], 'off');
  assert.deepEqual(pdu.displays['network-module/module/lcd'].text.slice(0, 2), ['PDU A', '192.0.2.17']);
  assert.match(maps.get('z2').displays['network-module/module/lcd'].image, /^data:image\/svg\+xml;utf8,/);
});

test('what the device does not declare is kept in the file and not handed to a drawing', async () => {
  const r = structuredClone(rackOf('lamps-displays.rack.json'));
  r.items[0].states['led-nonsense'] = 'on';
  r.items[0].states['led-sys'] = 'purple';
  r.zeroU[0].displays['status-display'] = {digits: '12'};
  const maps = await paintMaps(r, ctx, async () => null);
  assert.equal(maps.get('i1').states['led-nonsense'], undefined);
  assert.equal(maps.get('i1').states['led-sys'], undefined);
  assert.equal(maps.get('z1').displays['status-display'], undefined);
});

test('a picture that is a library asset is read and handed on as a data URL', async () => {
  const r = structuredClone(rackOf('lamps-displays.rack.json'));
  r.zeroU[1].displays = {'network-module/module/lcd': {image: 'img/logo.svg'}};
  const svg = new TextEncoder().encode('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8"><rect width="8" height="8"/></svg>');
  const asked = [];
  const maps = await paintMaps(r, ctx, async p => { asked.push(p); return svg; });
  assert.deepEqual(asked, ['img/logo.svg']);
  assert.match(maps.get('z2').displays['network-module/module/lcd'].image, /^data:image\/svg\+xml;base64,/);
});

await finish();
