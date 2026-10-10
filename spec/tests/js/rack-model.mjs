import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';

test('a new document is one 42U four-post rack with the spec defaults', () => {
  const d = M.newDoc();
  assert.equal(d.format, 'portrayal-rack');
  assert.equal(d.version, M.VERSION);
  assert.match(d.id, /^doc-/);
  assert.equal(d.racks.length, 1);
  assert.deepEqual(d.racks[0].frame, {kind: 'four-post', heightRU: 42, numbering: 'bottom-up',
    holes: {style: 'square', thread: null}, railDepth: 740, usableDepth: 1000, ref: null});
  assert.deepEqual([d.racks[0].items, d.racks[0].zeroU, d.racks[0].cables], [[], [], []]);
});

test('a two-post frame has no rail depth and a 1000 mm usable depth', () => {
  assert.deepEqual(M.defaultFrame('two-post'), {kind: 'two-post', heightRU: 42, numbering: 'bottom-up',
    holes: {style: 'square', thread: null}, railDepth: null, usableDepth: 1000, ref: null});
});

test('normalizeFrame keeps a thread only on a tapped rail, and only a known one', () => {
  const f = M.defaultFrame();
  assert.equal(M.normalizeFrame({...f, holes: {style: 'square', thread: 'M6'}}).holes.thread, null);
  assert.equal(M.normalizeFrame({...f, holes: {style: 'tapped', thread: 'M6'}}).holes.thread, 'M6');
  assert.equal(M.normalizeFrame({...f, holes: {style: 'tapped', thread: 'M5'}}).holes.thread, null);
  assert.equal(M.normalizeFrame({...f, heightRU: '24.4'}).heightRU, 24);
  assert.equal(M.normalizeFrame({...f, heightRU: 0}).heightRU, 42);
  assert.equal(M.normalizeFrame({...f, kind: 'two-post'}).railDepth, null);
  assert.equal(M.normalizeFrame({...M.defaultFrame('two-post'), kind: 'four-post'}).railDepth, 740);
});

test('items get stable, unique ids; edits return new racks', () => {
  const r0 = M.newRack();
  const {rack: r1, item: a} = M.withItem(r0, {ref: 'r740xd', cfg: 'sff24-rc5-1b2a3a', ru: 10});
  const {rack: r2, item: b} = M.withItem(r1, {ref: 'as7726-32x', cfg: 'ac-f2b', ru: 20, face: 'rear'});
  assert.deepEqual([a.id, b.id], ['i1', 'i2']);
  assert.equal(r0.items.length, 0, 'the original rack is untouched');
  assert.deepEqual(a, {id: 'i1', ref: 'r740xd', cfg: 'sff24-rc5-1b2a3a', label: 'r740xd', ru: 10,
    face: 'front', turned: false, swaps: {}, fields: {}});
  const r3 = M.withoutItem(r2, 'i1');
  const {item: c} = M.withItem(r3, {ref: 'tm-280', cfg: 'base', ru: 1});
  assert.equal(c.id, 'i3', 'a removed id is never reused');
  assert.equal(M.updateItem(r2, 'i2', {ru: 21}).items[1].ru, 21);
  assert.equal(M.renamed(r2, 'Lab').name, 'Lab');
});

test('uLabel counts from the top when the frame says so', () => {
  const f = M.defaultFrame();
  assert.equal(M.uLabel(f, 1), 1);
  assert.equal(M.uLabel({...f, numbering: 'top-down'}, 1), 42);
  assert.equal(M.uLabel({...f, numbering: 'top-down'}, 42), 1);
});

test('a document survives serialize and parse unchanged', () => {
  let d = M.newDoc({name: 'Lab rack'});
  const {rack} = M.withItem(d.racks[0], {ref: 'r740xd', cfg: 'sff24-rc5-1b2a3a', ru: 10,
    swaps: {'psu-2': 'common/psu-dc-650@2'}, fields: {'port-1-occupant': {label: 'LR4'}}});
  d = {...d, racks: [rack]};
  assert.deepEqual(M.parseDoc(M.serialize(d)), d);
});

test('parseDoc refuses what it cannot read, with a sentence', () => {
  assert.throws(() => M.parseDoc('{'), SyntaxError);
  assert.throws(() => M.parseDoc({format: 'other'}), /not a Portrayal rack file/);
  assert.throws(() => M.parseDoc({format: 'portrayal-rack', version: 4, racks: []}),
    /version 4; this reader supports up to version 3/);
  assert.throws(() => M.parseDoc({format: 'portrayal-rack', version: 1, racks: []}), /holds no rack/);
  assert.throws(() => M.parseDoc({format: 'portrayal-rack', version: 1,
    racks: [{frame: {}, items: [{ref: 'x'}]}]}), /Item 1 has no device or no U/);
});

test('parseDoc gives every item a distinct id, even a duplicated one', () => {
  const d = M.parseDoc({format: 'portrayal-rack', version: 1,
    racks: [{frame: {}, items: [{id: 'i2', ref: 'x', ru: 1}, {ref: 'x', ru: 2}, {ref: 'x', ru: 3}]}]});
  const ids = d.racks[0].items.map(i => i.id);
  assert.equal(new Set(ids).size, 3, 'all three ids are distinct');
  assert.equal(ids[0], 'i2', 'the first item keeps its declared id');
});

test('parseDoc gives a second item the same declared id a fresh one', () => {
  const d = M.parseDoc({format: 'portrayal-rack', version: 1,
    racks: [{frame: {}, items: [{id: 'i4', ref: 'x', ru: 1}, {id: 'i4', ref: 'x', ru: 2}]}]});
  const ids = d.racks[0].items.map(i => i.id);
  assert.equal(ids[0], 'i4');
  assert.notEqual(ids[1], 'i4', 'a repeated id is not kept twice');
  assert.equal(new Set(ids).size, 2);
});

test('parseDoc fills what an older writer left out, and keeps zeroU and cables', () => {
  const d = M.parseDoc({format: 'portrayal-rack', version: 1,
    racks: [{name: 'A', frame: {kind: 'two-post'}, items: [{id: 'i4', ref: 'tm-280', ru: 3}],
             zeroU: [{id: 'z1'}], cables: [{id: 'c1'}]}]});
  assert.match(d.id, /^doc-/);
  assert.equal(d.racks[0].frame.usableDepth, 1000);
  assert.deepEqual(d.racks[0].items[0], {id: 'i4', ref: 'tm-280', cfg: '', label: 'tm-280', ru: 3,
    face: 'front', turned: false, swaps: {}, fields: {}});
  assert.deepEqual(d.racks[0].zeroU, [{id: 'z1'}]);
  assert.deepEqual(d.racks[0].cables, [{id: 'c1', a: {item: '', path: '', view: 'front'},
    b: {item: '', path: '', view: 'front'}, media: '', purpose: '', label: '', route: []}]);
});

test('the DCIM import settings are optional: an old file opens unchanged, a new one keeps them', () => {
  const doc = extra => ({format: 'portrayal-rack', version: 1, id: 'doc-1',
    racks: [{id: 'r1', name: 'A', frame: {}, items: [], zeroU: [], cables: [], ...extra}]});
  // No `dcim` in the file: none in the rack, so saving it writes what was read.
  const old = M.parseDoc(doc({}));
  assert.equal('dcim' in old.racks[0], false);
  assert.deepEqual(M.parseDoc(M.serialize(old)), old);
  assert.deepEqual(M.dcimOf(old.racks[0]), {site: '', role: ''});
  // In the file: read as two trimmed strings, with anything else it holds kept.
  const kept = M.parseDoc(doc({dcim: {site: ' Lab 1 ', role: 7, tenant: 'acme'}})).racks[0];
  assert.deepEqual(kept.dcim, {site: 'Lab 1', role: '', tenant: 'acme'});
  // Only the keys the file has: `{}` and `{site}` open, and save, as they were.
  assert.deepEqual(M.parseDoc(doc({dcim: {}})).racks[0].dcim, {});
  assert.deepEqual(M.parseDoc(doc({dcim: {site: 'Lab 1'}})).racks[0].dcim, {site: 'Lab 1'});
  // Not an object: not settings.
  for (const bad of ['Lab 1', ['Lab 1'], null, 3]) assert.equal('dcim' in M.parseDoc(doc({dcim: bad})).racks[0], false);
  // The format's version did not change for it.
  assert.equal(M.VERSION, 3);   // 3 since bundles (#921), not for this
});

test('withDcim sets one name and keeps the other, and returns a new rack', () => {
  const rack = M.newRack();
  assert.equal('dcim' in rack, false);
  const a = M.withDcim(rack, {site: ' Lab 1 '});
  assert.deepEqual(a.dcim, {site: 'Lab 1'});          // a key the rack never had stays missing
  assert.equal('dcim' in rack, false);
  const b = M.withDcim({...a, dcim: {...a.dcim, tenant: 'acme'}}, {role: 'Router'});
  assert.deepEqual(b.dcim, {site: 'Lab 1', role: 'Router', tenant: 'acme'});
  assert.deepEqual(M.dcimOf(M.withDcim(b, {site: ''})), {site: '', role: 'Router'});
  assert.deepEqual(M.withDcim(b, {site: ''}).dcim, {site: '', role: 'Router', tenant: 'acme'});   // a key it had is cleared, not dropped
  assert.equal(M.withDcim(rack, {site: '  ', role: ''}), rack);                                  // blanks on a rack with none: no field made
  assert.deepEqual(M.withDcim({...rack, dcim: {}}, {role: 'R'}).dcim, {role: 'R'});
  assert.deepEqual(M.dcimOf({dcim: 'nonsense'}), {site: '', role: ''});
  assert.deepEqual(M.dcimOf(undefined), {site: '', role: ''});
});

test('nextId counts only ids that carry its own prefix', () => {
  assert.equal(M.nextId([{id: 'z7'}, {id: 'i2'}], 'i'), 'i3');
});

test('nextRackName follows the highest "Rack N" in use', () => {
  assert.equal(M.nextRackName([]), 'Rack 1');
  assert.equal(M.nextRackName(['Rack 1']), 'Rack 2');
  assert.equal(M.nextRackName(['Lab', 'Rack 3', 'Rack 1']), 'Rack 4');
});

test('version 2: a version-1 file opens unchanged, and a manager keeps its host', () => {
  const v1 = {format: 'portrayal-rack', version: 1, racks: [{id: 'r1', name: 'A', frame: {kind: 'four-post'},
    items: [{id: 'i1', ref: 'as7726-32x', cfg: 'x', ru: 20, face: 'front'}], zeroU: [], cables: []}]};
  const d = M.parseDoc(v1);
  assert.equal(d.version, M.VERSION);
  assert.equal(d.racks[0].items[0].on, undefined);
  const v2 = {...v1, version: 2, racks: [{...v1.racks[0], items: [...v1.racks[0].items,
    {id: 'i2', ref: 'fhd-cmp5dr', cfg: 'x', ru: 20, face: 'front', on: 'i1', unit: 1}]}]};
  const m = M.parseDoc(v2).racks[0].items[1];
  assert.deepEqual([m.on, m.unit, m.ru], ['i1', 1, 20]);
});

test('a newer file than this page knows is refused with a sentence', () => {
  assert.throws(() => M.parseDoc({format: 'portrayal-rack', version: 4, racks: [{}]}),
    /version 4; this reader supports up to version 3/);
});

test('a malformed host or unit is dropped on load, not guessed at', () => {
  const d = M.parseDoc({format: 'portrayal-rack', version: 2, racks: [{frame: {}, items: [
    {id: 'i1', ref: 'fhd-cmp5dr', cfg: 'x', ru: 3, face: 'front', on: '', unit: 0}], cables: []}]});
  const it = d.racks[0].items[0];
  assert.equal('on' in it, false);
  assert.equal('unit' in it, false);
});

test('removing a host leaves its managers in place, unhosted', () => {
  let r = M.newRack();
  ({rack: r} = M.withItem(r, {ref: 'as7726-32x', cfg: 'x', ru: 20}));
  ({rack: r} = M.withItem(r, {ref: 'fhd-cmp5dr', cfg: 'x', ru: 20, on: 'i1', unit: 1}));
  const after = M.withoutItem(r, 'i1');
  assert.equal(after.items.length, 1);
  assert.deepEqual(after.items[0].ru, 20);
  assert.equal('on' in after.items[0], false);
  assert.equal('unit' in after.items[0], false);
});

test('a cable keeps its edited route; a malformed waypoint is kept aside, not dropped', () => {
  const [c] = M.readCables([{id: 'c1', a: {item: 'i1', path: 'p'}, b: {item: 'i2', path: 'q'}, routeEdited: true,
    route: [{item: 'i3', via: 'guide-2'}, {lane: 'left-front', ru: 12}, {lane: 'left-front'}, 'x']}]);
  assert.deepEqual(c.route, [{item: 'i3', via: 'guide-2'}, {lane: 'left-front', ru: 12}]);
  assert.deepEqual(c.routeAsWritten, [{item: 'i3', via: 'guide-2'}, {lane: 'left-front', ru: 12}, {lane: 'left-front'}, 'x']);
  assert.equal(c.routeEdited, true);
});

test('routeEdited is only ever true; an automatic cable has none', () => {
  const [c] = M.readCables([{id: 'c1', a: {}, b: {}, routeEdited: 'yes', route: []}]);
  assert.equal('routeEdited' in c, false);
  assert.equal('routeAsWritten' in c, false);
});

test('a routed length keeps its measurement', () => {
  const [c] = M.readCables([{id: 'c1', a: {}, b: {}, length: {value: 2, unit: 'm', source: 'routed', measured: 1.62}}]);
  assert.deepEqual(c.length, {value: 2, unit: 'm', source: 'routed', measured: 1.62});
});

test('parse → JSON.stringify → parse keeps routeAsWritten', () => {
  let d = M.newDoc();
  const {rack} = M.withItem(d.racks[0], {ref: 'r740xd', cfg: 'sff24-rc5-1b2a3a', ru: 10});
  const cable = M.readCables([{id: 'c1', a: {item: 'i1'}, b: {item: 'i2'},
    route: [{item: 'i1', via: 'g1'}, {bad: 'entry'}, {lane: 'L', ru: 5}]}])[0];
  d = {...d, racks: [{...rack, cables: [cable]}]};
  const restored = M.parseDoc(M.serialize(d)).racks[0].cables[0];
  assert.deepEqual(restored.route, cable.route);
  assert.deepEqual(restored.routeAsWritten, cable.routeAsWritten);
});

test('a file whose route differs from routeAsWritten readable entries drops it', () => {
  // The readable entries of routeAsWritten are {i2, g2} and {L, 6}, but route shows {i1, g1}.
  // Since they differ, routeAsWritten is stale and should be dropped.
  const [c] = M.readCables([{id: 'c1', a: {}, b: {},
    route: [{item: 'i1', via: 'g1'}],
    routeAsWritten: [{item: 'i2', via: 'g2'}, {bad: 'x'}, {lane: 'L', ru: 6}]}]);
  assert.equal('routeAsWritten' in c, false, 'stale routeAsWritten is dropped');
});

test('a file whose routeAsWritten readable entries match the route keeps it', () => {
  // The readable entries of routeAsWritten are {i1, g1} and {L, 5}, matching route.
  // It is kept because nothing has been edited since it was written.
  const [c] = M.readCables([{id: 'c1', a: {}, b: {},
    route: [{item: 'i1', via: 'g1'}, {lane: 'L', ru: 5}],
    routeAsWritten: [{item: 'i1', via: 'g1'}, {bad: 'x'}, {lane: 'L', ru: 5}]}]);
  assert.deepEqual(c.route, [{item: 'i1', via: 'g1'}, {lane: 'L', ru: 5}]);
  assert.deepEqual(c.routeAsWritten, [{item: 'i1', via: 'g1'}, {bad: 'x'}, {lane: 'L', ru: 5}]);
});
