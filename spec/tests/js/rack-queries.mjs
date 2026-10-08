// spec/tests/js/rack-queries.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as Q from '../../../kit/rack/queries.js';

const SIZES = {'as7726-32x': {ru: 1, h: 43.5, d: 515, model: 'AS7726-32X', manufacturer: 'Accton', configs: ['ac-f2b'], default: 'ac-f2b', family: null},
               'r740xd': {ru: 2, h: 86.8, d: 737.5, model: 'R740xd', manufacturer: 'Dell', configs: ['a', 'b'], default: 'a', family: 'poweredge'},
               'fhd-cmp5dr': {ru: 1, h: 44, d: 110, mount: 'rack-face', model: 'FHD-CMP5DR', manufacturer: 'FS.com', configs: ['base'], default: 'base', family: null}};
const ctx = {chassisOf: ref => SIZES[ref] || null};
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'x', ru, label: extra.label ?? ref, ...extra}).rack;

test('fitsAt and freeUs', () => {
  const r = add(M.newRack(), 'r740xd', 10, {label: 'srv'});
  assert.deepEqual(Q.fitsAt(r, {ref: 'as7726-32x', face: 'front', ru: 11}, ctx), {ok: false, reason: 'Taken by srv on the front.'});
  const us = Q.freeUs(r, {ref: 'as7726-32x', face: 'front'}, ctx);
  assert.equal(us.includes(10) || us.includes(11), false);
  assert.equal(us.length, 40);
});

test('catalog filters by text, height, family and mount', () => {
  assert.deepEqual(Q.catalog(SIZES, {text: 'dell'}).map(e => e.ref), ['r740xd']);
  assert.deepEqual(Q.catalog(SIZES, {ru: 1}).map(e => e.ref), ['as7726-32x', 'fhd-cmp5dr']);
  assert.deepEqual(Q.catalog(SIZES, {mount: 'rack-face'}).map(e => e.ref), ['fhd-cmp5dr']);
  assert.deepEqual(Q.catalog(SIZES, {family: 'poweredge'})[0],
    {ref: 'r740xd', manufacturer: 'Dell', model: 'R740xd', ru: 2, mount: 'rack', family: 'poweredge', kind: null, configs: ['a', 'b'], default: 'a'});
});

test('describe: the frame, items with U ranges and managers, cables', () => {
  let r = add(M.newRack(), 'r740xd', 10, {label: 'srv'});
  r = add(r, 'fhd-cmp5dr', 11, {label: 'mgr', on: 'i1', unit: 2});
  r = {...r, cables: [{id: 'c1', a: {item: 'i1', path: 'port-1', view: 'rear'}, b: {item: 'i9', path: 'p', view: 'front'}, media: 'om4', purpose: '', label: '', route: []}]};
  const text = Q.describe(r, ctx);
  assert.match(text, /^Rack 1 \(r1\): 2 items, 1 cable\.\n42U four-post, square holes, numbered bottom-up\./);
  assert.match(text, /i1 srv U10-U11 front, carries i2/);
  assert.match(text, /i2 mgr U11 front, on i1 unit 2/);
  assert.match(text, /c1: i1\/port-1 \(rear\) <-> i9\/p, om4/);
});

test('describe stays under 1.5K characters for a full 42U rack, and says what it shortened', () => {
  let r = M.newRack();
  for (let u = 1; u <= 42; u++) r = add(r, 'as7726-32x', u, {label: `leaf-switch-number-${u}`});
  r = {...r, cables: Array.from({length: 30}, (_, k) => ({id: `c${k + 1}`, a: {item: `i${k + 1}`, path: 'port-12', view: 'front'},
    b: {item: `i${k + 2}`, path: 'port-12', view: 'front'}, media: 'om4', purpose: '', label: '', route: []}))};
  const text = Q.describe(r, ctx);
  assert.ok(text.length <= 1500, `${text.length} characters`);
  assert.match(text, /shortened|more/);
});

test('freePorts, suggestMedia and looseEnds read through ctx', async () => {
  let r = add(add(M.newRack(), 'as7726-32x', 10, {label: 'a'}), 'as7726-32x', 20, {label: 'b'});
  r = {...r, cables: [{id: 'c1', a: {item: 'i1', path: 'port-1', view: 'front'}, b: {item: 'i2', path: 'port-1', view: 'front'}, media: '', purpose: '', label: '', route: []}]};
  const portsOf = async (item, view) => (view === 'front'
    ? [{path: 'port-1', cls: 'port', media: 'lc', speed: '100G'}, {path: 'port-2', cls: 'port', media: 'lc', speed: '100G'}, {path: 'slot-1', cls: 'bay'}] : []);
  assert.deepEqual(await Q.freePorts(r, 'i1', {portsOf}), [{path: 'port-2', view: 'front', label: 'port 2', media: 'lc', speed: '100G'}]);
  assert.deepEqual(await Q.freePorts(r, 'i9', {portsOf}), {error: 'That device is no longer in the rack.'});
  const fiber = {family: 'fiber', mode: 'multimode'}, copper = {family: 'copper', mode: null};
  const cableFacts = async (_rack, extra = []) => ({seats: {}, ends: new Map([
    ['i1|front|port-1', {info: fiber, reason: null}], ['i2|front|port-1', {info: fiber, reason: 'port-1 holds no optic'}],
    ['i1|front|port-2', {info: fiber}], ['i2|front|port-2', {info: copper}]])});
  const s = await Q.suggestMedia(r, {item: 'i1', path: 'port-2', view: 'front'}, {item: 'i2', path: 'port-2', view: 'front'}, {cableFacts});
  assert.equal(s.media, 'om4');
  assert.equal(s.warnings[0], 'The ends differ: A is fiber, B is copper.');
  assert.deepEqual(await Q.looseEnds(r, {cableFacts}),
    {unchecked: false, ends: [{cable: 'c1', side: 'b', end: {item: 'i2', path: 'port-1', view: 'front'}, reason: 'port-1 holds no optic'}]});
});

const KINDS = {pp: {ru: 1, model: 'FHD-1UFCE', manufacturer: 'FS', family: null, kind: 'patch panel', configs: ['base'], default: 'base'},
               sw: {ru: 1, model: 'DS3000', manufacturer: 'Celestica', family: 'Data Center Switch', kind: 'switch', configs: ['base'], default: 'base'},
               cm: {ru: 1, mount: 'rack-face', model: 'CMP5DR', manufacturer: 'FS', family: null, kind: 'cable manager', configs: ['base'], default: 'base'}};

test('catalog: by kind, and text matches the kind and family words', () => {
  assert.deepEqual(Q.catalog(KINDS, {kind: 'patch panel'}).map(e => e.ref), ['pp']);
  assert.deepEqual(Q.catalog(KINDS, {text: 'patch panel'}).map(e => e.ref), ['pp']);
  assert.deepEqual(Q.catalog(KINDS, {text: 'Switch'}).map(e => e.ref), ['sw']);
  assert.deepEqual(Q.catalog(KINDS, {text: 'cable manager', mount: 'rack-face'}).map(e => e.ref), ['cm']);
  assert.equal(Q.catalog(KINDS, {kind: 'switch'})[0].kind, 'switch');
});

test('describe: a window reads one stretch in full, and the first line gives the totals and what is shown', () => {
  let r = M.newRack();
  for (let u = 1; u <= 6; u++) r = add(r, 'as7726-32x', u, {label: `leaf-${u}`, cfg: 'ac-f2b'});
  r = {...r, cables: Array.from({length: 40}, (_, k) => ({id: `c${k + 1}`, a: {item: 'i1', path: `port-${k + 1}`, view: 'front'},
    b: {item: 'i2', path: `port-${k + 1}`, view: 'front'}, media: 'om4', purpose: k % 2 ? 'uplink' : '', label: '', route: [],
    ...(k === 20 ? {length: {value: 3, unit: 'm', source: 'entered'}} : {})}))};
  const text = Q.describe(r, ctx, {section: 'cables', offset: 20, limit: 20});
  const lines = text.split('\n');
  assert.equal(lines[0], 'Rack 1 (r1): 6 items, 40 cables. Cables 21-40 shown.');
  assert.equal(lines[1], '42U four-post, square holes, numbered bottom-up.');
  assert.equal(lines[2], 'Cables:');
  assert.equal(lines[3], 'c21: i1/port-21 <-> i2/port-21, om4, 3 m');
  assert.equal(lines[4], 'c22: i1/port-22 <-> i2/port-22, om4, uplink');
  assert.equal(lines.length, 23);
  const items = Q.describe(r, ctx, {section: 'items', limit: 2}).split('\n');
  assert.deepEqual(items, ['Rack 1 (r1): 6 items, 40 cables. Items 1-2 shown.', '42U four-post, square holes, numbered bottom-up.',
    'Items:', 'i6 leaf-6 U6 front, as7726-32x ac-f2b', 'i5 leaf-5 U5 front, as7726-32x ac-f2b']);
  assert.equal(Q.describe(r, ctx, {section: 'cables', offset: 40}).split('\n')[0], 'Rack 1 (r1): 6 items, 40 cables. Cables past the end: there are 40.');
  assert.equal(Q.describe(M.newRack(), ctx, {offset: 0}).split('\n')[0], 'Rack 1 (r1): 0 items, 0 cables. No items. No cables.');
  assert.match(Q.describe(r, ctx, {offset: 0}), /^Rack 1 \(r1\): 6 items, 40 cables\. Items 1-6 shown\. Cables 1-20 shown\./);
});

test('describe: the totals line survives the shortening of a long rack', () => {
  let r = M.newRack();
  for (let u = 1; u <= 42; u++) r = add(r, 'as7726-32x', u, {label: `leaf-switch-number-${u}`});
  const text = Q.describe(r, ctx);
  assert.ok(text.length <= 1500);
  assert.match(text, /^Rack 1 \(r1\): 42 items, 0 cables\.\n/);
});

test('describe: a section, offset or limit it cannot read is refused, and a limit is capped', () => {
  let r = M.newRack();
  for (let u = 1; u <= 42; u++) r = add(r, 'as7726-32x', u, {label: `l${u}`});
  r = {...r, cables: Array.from({length: 60}, (_, k) => ({id: `c${k + 1}`, a: {item: 'i1', path: `port-${k + 1}`, view: 'front'},
    b: {item: 'i2', path: `port-${k + 1}`, view: 'front'}, media: '', purpose: '', label: '', route: []}))};
  assert.deepEqual(Q.describe(r, ctx, {section: 'item'}), {error: 'There is no section item. Ask for items or cables, or leave it out for both.'});
  for (const offset of [-3, 2.5, '3', NaN])
    assert.deepEqual(Q.describe(r, ctx, {section: 'items', offset}), {error: 'An offset is a whole number from 0.'}, String(offset));
  for (const limit of [0, -1, 2.5, 'all'])
    assert.deepEqual(Q.describe(r, ctx, {section: 'items', limit}), {error: `A limit is a whole number from 1 to ${Q.MAX_WINDOW}.`}, String(limit));
  assert.equal(Q.MAX_WINDOW, 50);
  assert.equal(Q.describe(r, ctx, {section: 'cables', limit: 1000}).split('\n')[0], 'Rack 1 (r1): 42 items, 60 cables. Cables 1-50 shown.');
  assert.equal(Q.describe(r, ctx, {section: 'items'}).split('\n')[0], 'Rack 1 (r1): 42 items, 60 cables. Items 1-20 shown.');
  assert.equal(Q.describe(r, ctx, {offset: 0}).split('\n')[0], 'Rack 1 (r1): 42 items, 60 cables. Items 1-20 shown. Cables 1-20 shown.');
});
