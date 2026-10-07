import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as C from '../../../kit/rack/cable-rules.js';

// A small rack: a switch and a router on the front, two identical demarcs on the rear.
function rack() {
  let r = M.newRack({name: 'Cable test'});
  for (const it of [
    {ref: 'asr-9006', cfg: 'base', ru: 2, label: 'core-1'},
    {ref: 'as7726-32x', cfg: 'ac-f2b', ru: 14, label: 'leaf-1'},
    {ref: 'tm-280', cfg: 'base', ru: 14, face: 'rear', label: 'demarc'},
    {ref: 'tm-280', cfg: 'base', ru: 20, face: 'rear', label: 'demarc'}]) r = M.withItem(r, it).rack;
  return r;
}
const end = (item, path, view = 'front') => ({item, path, view});

test('an end is {item, path, view}; its key tells apart two devices with one ref and two panels of one device', () => {
  assert.equal(C.endKey(end('i3', 'port-2-1')), 'i3|front|port-2-1');
  assert.notEqual(C.endKey(end('i3', 'port-2-1')), C.endKey(end('i4', 'port-2-1')));
  assert.notEqual(C.endKey(end('i3', 'port-1', 'front')), C.endKey(end('i3', 'port-1', 'rear')));
  assert.ok(C.sameEnd(end('i1', 'p'), {item: 'i1', path: 'p', view: 'front', extra: 1}));
});

test('paneOf is the inverse of panelFor, for every face and turn', () => {
  // elevation.js's rule, restated: which panel of the device faces a pane.
  const panelFor = (item, pane) => (((item.face === pane) !== !!item.turned) ? 'front' : 'rear');
  for (const face of ['front', 'rear']) for (const turned of [false, true]) {
    const item = {face, turned};
    for (const view of ['front', 'rear'])
      assert.equal(panelFor(item, C.paneOf(item, view)), view, JSON.stringify({face, turned, view}));
  }
  assert.equal(C.paneOf({face: 'front', turned: false}, 'front'), 'front');
  assert.equal(C.paneOf({face: 'rear', turned: false}, 'front'), 'rear', 'a rear-mounted device shows its front in the rear pane');
  assert.equal(C.paneOf({face: 'front', turned: true}, 'front'), 'rear', 'a turned device shows its front in the other pane');
  assert.equal(C.paneOf({face: 'rear', turned: true}, 'rear'), 'rear');
});

test('portPathOf drops the occupant and everything under it', () => {
  assert.equal(C.portPathOf('port-1'), 'port-1');
  assert.equal(C.portPathOf('port-1-occupant'), 'port-1');
  assert.equal(C.portPathOf('port-1-occupant/tx'), 'port-1');
  assert.equal(C.portPathOf('port-1-occupant/tx-occupant'), 'port-1');
  assert.equal(C.portPathOf('slot-2/module/p0-occupant/rx'), 'slot-2/module/p0');
  assert.equal(C.portPathOf('port-10'), 'port-10');
});

test('withCable allocates c ids, copies the ends, and omits an unset length', () => {
  const r0 = rack();
  const {rack: r1, cable: c1} = C.withCable(r0, {a: end('i2', 'port-1'), b: end('i1', 'slot-2/module/p0'),
    media: 'os2', purpose: 'uplink', label: 'A1', length: {value: 2, unit: 'm', source: 'entered'}});
  assert.deepEqual(c1, {id: 'c1', a: {item: 'i2', path: 'port-1', view: 'front'},
    b: {item: 'i1', path: 'slot-2/module/p0', view: 'front'}, media: 'os2', purpose: 'uplink', label: 'A1',
    length: {value: 2, unit: 'm', source: 'entered'}, route: []});
  assert.equal(r0.cables.length, 0, 'the original rack is untouched');
  const {rack: r2, cable: c2} = C.withCable(r1, {a: end('i2', 'mgmt-eth'), b: end('i3', 'port-2-1')});
  assert.equal(c2.id, 'c2');
  assert.ok(!('length' in c2));
  assert.deepEqual([c2.media, c2.purpose, c2.label, c2.route], ['', '', '', []]);
  assert.equal(r2.items, r0.items, 'a cable edit leaves the items array itself alone');
  assert.equal(C.updateCable(r2, 'c1', {media: 'om4', length: null}).cables[0].media, 'om4');
  assert.ok(!('length' in C.updateCable(r2, 'c1', {length: null}).cables[0]));
  assert.deepEqual(C.updateCable(r2, 'c2', {length: {value: 3, unit: 'ft', source: 'entered'}}).cables[1].length,
    {value: 3, unit: 'ft', source: 'entered'});
  assert.deepEqual(C.withoutCable(r2, 'c1').cables.map(c => c.id), ['c2']);
});

test('updateCable patching route drops routeAsWritten', () => {
  let r = rack();
  const cable = M.readCables([{id: 'c1', a: {item: 'i1', path: 'p'}, b: {item: 'i2', path: 'q'},
    route: [{item: 'i1', via: 'g1'}], routeAsWritten: [{item: 'i1', via: 'g1'}, {bad: 'x'}]}])[0];
  r = {...r, cables: [cable]};
  const updated = C.updateCable(r, 'c1', {route: [{item: 'i2', via: 'g2'}]}).cables[0];
  assert.deepEqual(updated.route, [{item: 'i2', via: 'g2'}]);
  assert.equal('routeAsWritten' in updated, false, 'patching route drops routeAsWritten');
  const unpatched = C.updateCable(r, 'c1', {label: 'new'}).cables[0];
  assert.deepEqual(unpatched.routeAsWritten, cable.routeAsWritten, 'not patching route leaves routeAsWritten alone');
});

test('one cable per port: a taken port is refused with a sentence that names the device, its U and the cable', () => {
  const {rack: r} = C.withCable(rack(), {a: end('i2', 'port-1'), b: end('i3', 'port-2-1'), label: 'A1'});
  assert.deepEqual(C.portFree(r, end('i2', 'port-2')), {ok: true});
  assert.deepEqual(C.portFree(r, end('i2', 'port-1')),
    {ok: false, reason: 'leaf-1 (U14) port-1 already has a cable (A1).'});
  assert.deepEqual(C.portFree(r, end('i3', 'port-2-1')),
    {ok: false, reason: 'demarc (U14) port-2-1 already has a cable (A1).'});
  assert.deepEqual(C.portFree(r, end('i4', 'port-2-1')), {ok: true}, 'the other demarc is another device');
  assert.deepEqual(C.portFree(r, end('i2', 'port-1', 'rear')), {ok: true}, 'the same path on the other panel is another port');
  assert.deepEqual(C.portFree(r, end('i2', 'port-1'), {ignoreId: 'c1'}), {ok: true}, 'editing a cable does not collide with itself');
  assert.deepEqual(C.canCable(r, end('i2', 'port-2'), end('i2', 'port-2')),
    {ok: false, reason: 'A cable needs two different ports.'});
  assert.deepEqual(C.canCable(r, end('i2', 'port-2'), end('i4', 'port-2-1')), {ok: true});
  assert.equal(C.canCable(r, end('i2', 'port-2'), end('i2', 'port-1')).ok, false);
  const unlabeled = C.withCable(rack(), {a: end('i2', 'port-1'), b: end('i3', 'port-2-1')}).rack;
  assert.match(C.portFree(unlabeled, end('i2', 'port-1')).reason, /\(c1\)\.$/, 'a cable with no label is named by its id');
});

test('endName and tagText say which device, and survive a removed one', () => {
  const r = rack();
  assert.equal(C.endName(r, end('i4', 'port-2-1')), 'demarc (U20) port-2-1');
  assert.equal(C.endName({...r, frame: {...r.frame, numbering: 'top-down'}}, end('i4', 'port-2-1')), 'demarc (U23) port-2-1');
  assert.equal(C.endName(r, end('i9', 'port-1')), "a removed device's port-1");
  assert.equal(C.tagText(r, end('i3', 'port-2-1')), '→ demarc port-2-1');
  assert.equal(C.tagText(r, end('i9', 'port-1')), '→ removed port-1');
  const long = C.tagText(r, end('i1', 'slot-2/module/a-very-long-port-name-indeed'));
  assert.equal(long.length, 32);
  assert.ok(long.endsWith('…'));
});

test('cablesOf and withoutCablesOf find a device\'s cables by its id, at either end', () => {
  let r = C.withCable(rack(), {a: end('i2', 'port-1'), b: end('i1', 'slot-2/module/p0')}).rack;
  r = C.withCable(r, {a: end('i2', 'mgmt-eth'), b: end('i3', 'port-2-1')}).rack;
  r = C.withCable(r, {a: end('i4', 'port-2-1'), b: end('i1', 'slot-2/module/p1')}).rack;
  assert.deepEqual(C.cablesOf(r, 'i2').map(c => c.id), ['c1', 'c2']);
  assert.deepEqual(C.cablesOf(r, 'i3').map(c => c.id), ['c2']);
  assert.deepEqual(C.cablesOf(r, 'i9'), []);
  assert.deepEqual(C.withoutCablesOf(r, 'i2').cables.map(c => c.id), ['c3']);
  // Removing the item alone keeps its cables: they become loose ends.
  assert.equal(M.withoutItem(r, 'i2').cables.length, 3);
  // Moving it keeps them too: a cable names the item's id, not its place.
  assert.deepEqual(M.updateItem(r, 'i2', {ru: 16, face: 'rear'}).cables, r.cables);
});

test('parseLength takes a positive number or nothing; lengthText prints it', () => {
  assert.deepEqual(C.parseLength('', 'm'), {ok: true, length: null});
  assert.deepEqual(C.parseLength('  ', 'ft'), {ok: true, length: null});
  assert.deepEqual(C.parseLength('2.5', 'm'), {ok: true, length: {value: 2.5, unit: 'm', source: 'entered'}});
  assert.deepEqual(C.parseLength('10', 'ft'), {ok: true, length: {value: 10, unit: 'ft', source: 'entered'}});
  assert.deepEqual(C.parseLength('3', 'yards'), {ok: true, length: {value: 3, unit: 'm', source: 'entered'}});
  for (const bad of ['0', '-1', 'abc', 'Infinity'])
    assert.deepEqual(C.parseLength(bad, 'm'), {ok: false, reason: 'Enter a length above 0, or leave it empty.'}, bad);
  assert.equal(C.lengthText({value: 2, unit: 'm'}), '2 m');
  assert.equal(C.lengthText({value: 10, unit: 'ft'}), '10 ft');
  assert.equal(C.lengthText(undefined), '');
});

test('cablePlan hands cables.js each end as [item id, path, pane]', () => {
  let r = rack();
  r = C.withCable(r, {a: end('i2', 'port-1'), b: end('i1', 'slot-2/module/p0'), media: 'os2', purpose: 'uplink'}).rack;
  r = C.withCable(r, {a: end('i2', 'mgmt-eth'), b: end('i3', 'port-2-1')}).rack;
  r = C.withCable(r, {a: end('i2', 'port-2'), b: end('i9', 'port-2-1')}).rack;
  assert.deepEqual(C.cablePlan(r).links, [
    {id: 'c1', media: 'os2', purpose: 'uplink', from: ['i2', 'port-1', 'front'], to: ['i1', 'slot-2/module/p0', 'front']},
    {id: 'c2', media: 'unset', purpose: '', from: ['i2', 'mgmt-eth', 'front'], to: ['i3', 'port-2-1', 'rear']},
    {id: 'c3', media: 'unset', purpose: '', from: ['i2', 'port-2', 'front'], to: ['i9', 'port-2-1', 'none']}]);
  assert.deepEqual(C.cablePlan(M.newRack()).links, []);
});

test('the loader keeps every cable: it fixes the shape and never drops one', () => {
  const d = M.parseDoc({format: 'portrayal-rack', version: 1, racks: [{frame: {}, items: [{id: 'i1', ref: 'x', ru: 1}],
    cables: [
      {id: 'c1', a: {item: 'i1', path: 'port-1', view: 'front'}, b: {item: 'gone', path: 'port-2', view: 'rear'},
       media: 'os2', purpose: 'uplink', label: 'A1', length: {value: '2', unit: 'm', source: 'entered'},
       route: [{item: 'i1'}], color: 'red'},
      {id: 'c1', a: {item: 'i1', path: 'port-3'}, b: null, media: 'os1', length: {value: 0}},
      {},
      'nonsense',
      {id: 'c2', a: {item: 'i1', path: 'p', view: 'sideways'}, b: {item: 'i1', path: 'q'}, length: {value: 3, unit: 'ft', source: 'routed'}},
    ]}]});
  const cs = d.racks[0].cables;
  assert.equal(cs.length, 5, 'five in, five out');
  assert.deepEqual(cs[0], {id: 'c1', a: {item: 'i1', path: 'port-1', view: 'front'},
    b: {item: 'gone', path: 'port-2', view: 'rear'}, media: 'os2', purpose: 'uplink', label: 'A1',
    length: {value: 2, unit: 'm', source: 'entered'}, route: [], routeAsWritten: [{item: 'i1'}], color: 'red'},
    'a missing item is kept; route and unknown fields survive');
  assert.equal(new Set(cs.map(c => c.id)).size, 5, 'ids are unique');
  assert.equal(cs[4].id, 'c2', 'a declared id is not taken by a repaired one before it');
  assert.deepEqual(cs[1].b, {item: '', path: '', view: 'front'});
  assert.equal(cs[1].media, 'os1', 'an unknown media is kept as written');
  assert.ok(!('length' in cs[1]), 'a length that is not a positive number is dropped, the cable is not');
  assert.deepEqual(cs[2].a, {item: '', path: '', view: 'front'});
  assert.deepEqual([cs[3].media, cs[3].purpose, cs[3].label, cs[3].route], ['', '', '', []]);
  assert.equal(cs[4].a.view, 'front');
  assert.deepEqual(cs[4].length, {value: 3, unit: 'ft', source: 'routed'});
});

test('a cabled document survives serialize and parse unchanged', () => {
  let d = M.newDoc({name: 'Cabled'});
  let r = M.withItem(d.racks[0], {ref: 'as7726-32x', cfg: 'ac-f2b', ru: 14}).rack;
  r = M.withItem(r, {ref: 'tm-280', cfg: 'base', ru: 14, face: 'rear'}).rack;
  r = C.withCable(r, {a: end('i1', 'mgmt-eth'), b: end('i2', 'port-2-1'), media: 'cat6a', purpose: 'management',
    label: 'M1', length: {value: 3, unit: 'ft', source: 'entered'}}).rack;
  r = C.withCable(r, {a: end('i1', 'port-2'), b: end('i2', 'port-1-1')}).rack;
  d = {...d, racks: [r]};
  assert.deepEqual(M.parseDoc(M.serialize(d)), d);
});

test('one cable per PORT: another spelling of the path is the same port', () => {
  const {rack: r} = C.withCable(rack(), {a: end('i2', 'port-1'), b: end('i3', 'port-2-1'), label: 'A1'});
  assert.equal(C.portFree(r, end('i2', 'port-1-occupant/tx')).ok, false);
  assert.equal(C.portFree(r, end('i2', 'port-1-occupant/tx-occupant')).ok, false);
  assert.equal(C.portFree(r, end('i2', 'port-1-occupant/tx'), {ignoreId: 'c1'}).ok, true);
  assert.equal(C.portFree(r, end('i2', 'port-10')).ok, true);
  assert.equal(C.portFree(r, end('i2', 'port-1-occupant/tx', 'rear')).ok, true);
  const {rack: r2} = C.withCable(rack(), {a: end('i2', 'port-1-occupant/tx'), b: end('i3', 'port-2-1')});
  assert.equal(C.portFree(r2, end('i2', 'port-1')).ok, false);
  assert.deepEqual(C.canCable(r, end('i2', 'port-2'), end('i2', 'port-2-occupant/rx')),
    {ok: false, reason: 'A cable needs two different ports.'});
  assert.ok(C.sameEnd(end('i2', 'port-2'), end('i2', 'port-2-occupant/rx')));
  assert.notEqual(C.endKey(end('i2', 'port-2')), C.endKey(end('i2', 'port-2-occupant/rx')));
});

test('tagText clips by code point and never leaves a lone surrogate', () => {
  const r = rack();
  r.items[0].label = '😀'.repeat(40);
  const t = C.tagText(r, end('i1', 'p'));
  assert.ok(Array.from(t).length <= 32);
  assert.ok(!/[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]/.test(t));
  assert.ok(t.endsWith('…'));
});

test('edits treat a missing cable list as empty, and never touch a frozen input', () => {
  const bare = {frame: {}, items: []};
  assert.deepEqual(C.updateCable(bare, 'c1', {media: 'os2'}).cables, []);
  assert.deepEqual(C.withoutCable(bare, 'c1').cables, []);
  assert.deepEqual(C.withoutCablesOf(bare, 'i1').cables, []);
  assert.deepEqual(C.cablePlan(bare).links, []);
  assert.deepEqual(C.cablesOf(bare, 'i1'), []);
  const deep = o => { Object.values(o).forEach(v => v && typeof v === 'object' && deep(v)); return Object.freeze(o); };
  const {rack: r} = C.withCable(rack(), {a: end('i2', 'port-1'), b: end('i3', 'port-2-1'), length: {value: 1, unit: 'm', source: 'entered'}});
  deep(r);
  const before = JSON.stringify(r);
  const {rack: r2} = C.withCable(r, {a: end('i2', 'port-2'), b: end('i4', 'port-2-1')});
  C.updateCable(r2, 'c1', {media: 'os2', length: null});
  C.withoutCable(r2, 'c1');
  C.withoutCablesOf(r2, 'i2');
  assert.equal(JSON.stringify(r), before);
});

test('parseLength takes only a plain decimal', () => {
  for (const bad of ['0x10', '1.', '.5', '1e3', '+2', '1,5'])
    assert.deepEqual(C.parseLength(bad, 'm'), {ok: false, reason: 'Enter a length above 0, or leave it empty.'}, bad);
  assert.equal(C.parseLength(' 12.25 ', 'm').length.value, 12.25);
});

test('the loader keeps unknown fields on an end, and a malformed length never throws', () => {
  const d = M.parseDoc({format: 'portrayal-rack', version: 1, racks: [{frame: {}, items: [], cables: [
    {id: 'c1', a: {item: 'i1', path: 'p', view: 'rear', extra: 7}, b: {item: 'i2', path: 'q'}, length: {value: 'abc'}},
    {id: 'c2', a: {}, b: {}, length: 'long'},
    {id: 'c3', a: {}, b: {}, length: 5},
    {id: 'c4', a: 'x', b: ['y'], length: {value: -2}}]}]});
  const cs = d.racks[0].cables;
  assert.deepEqual(cs[0].a, {item: 'i1', path: 'p', view: 'rear', extra: 7});
  assert.equal(cs.length, 4);
  assert.ok(cs.every(c => !('length' in c)));
});

test('a loaded length is a number or a plain decimal string; anything else drops the length, not the cable', () => {
  const read = value => M.readCables([{id: 'c1', a: {item: 'i1', path: 'p'}, b: {item: 'i1', path: 'q'},
    length: {value, unit: 'm'}}])[0];
  assert.equal(read(16).length.value, 16);
  assert.equal(read('2.5').length.value, 2.5);
  assert.equal(read('2').length.value, 2);
  for (const bad of ['0x10', '1e3', ' 2', '2 ', '.5', '-1', '', '0', 'abc', null, true, [3], {}, Infinity, NaN, 0]) {
    const c = read(bad);
    assert.ok(!('length' in c), `${JSON.stringify(bad)} drops the length`);
    assert.equal(c.id, 'c1', 'the cable is kept');
  }
});

// ── an item id is never reused while a cable end names it ───────────────
test('a kept cable never re-attaches: a removed device\'s id is not handed to the next one placed', () => {
  let r = rack();                                     // i1..i4
  r = C.withCable(r, {a: end('i2', 'mgmt-eth'), b: end('i4', 'port-2-1')}).rack;
  r = M.withoutItem(r, 'i4');                         // the highest id goes; its cable is kept
  const {rack: r2, item} = M.withItem(r, {ref: 'tm-280', cfg: 'base', ru: 30});
  assert.notEqual(item.id, 'i4', 'the kept cable still names i4, so i4 is not free');
  assert.equal(item.id, 'i5');
  assert.equal(C.cablesOf(r2, item.id).length, 0, 'the new device has no cable');
  assert.equal(C.endName(r2, r2.cables[0].b), "a removed device's port-2-1");
  // Once no cable end names it, the id is only a number again.
  const freed = M.withItem(C.withoutCable(r, 'c1'), {ref: 'tm-280', cfg: 'base', ru: 30}).item;
  assert.equal(freed.id, 'i4');
});

test('a device a shrink trimmed keeps its id out of use while its cable is kept', async () => {
  const {shrinkRack} = await import('../../../kit/rack/fit.js');
  // Three 1U devices at U1, U2 and U3; the last placed (i3) is at the bottom.
  let r = M.newRack();
  for (const ru of [3, 2, 1]) r = M.withItem(r, {ref: 'x', cfg: '', ru}).rack;
  r = C.withCable(r, {a: end('i1', 'p1'), b: end('i3', 'p1')}).rack;
  const {rack: cut, removed} = shrinkRack(r, 2, () => ({ru: 1}));
  assert.deepEqual(removed.map(i => i.id), ['i3'], 'the shrink trims the bottom device');
  assert.equal(cut.cables.length, 1, 'and keeps its cable');
  const {item} = M.withItem(cut, {ref: 'y', cfg: '', ru: 1});
  assert.equal(item.id, 'i4');
});

test('the loader never repairs an item id into one a cable end names', () => {
  const d = M.parseDoc({format: 'portrayal-rack', version: 1, racks: [{frame: {}, items: [
    {id: 'i1', ref: 'x', ru: 1}, {id: 'i1', ref: 'y', ru: 2}, {ref: 'z', ru: 3}, {id: 'i3', ref: 'w', ru: 4}],
    cables: [{id: 'c1', a: {item: 'i1', path: 'p'}, b: {item: 'i2', path: 'q'}},
             {id: 'c2', a: {item: 'i3', path: 'p'}, b: {item: 'i4', path: 'q'}}]}]});
  const items = d.racks[0].items;
  assert.deepEqual(items.map(i => [i.id, i.ref]), [['i1', 'x'], ['i5', 'y'], ['i6', 'z'], ['i3', 'w']],
    'the first holder of an id keeps it; a repaired id is past every id an item declares or a cable names');
  assert.deepEqual(M.parseDoc(M.serialize(d)), d, 'and the repaired file is a fixed point');
});

// ── a length is kept as written ─────────────────────────────────────────
test('the loader keeps a length\'s unit as written, and lengthText prints it', () => {
  const read = length => M.readCables([{id: 'c1', a: {item: 'i1', path: 'p'}, b: {item: 'i1', path: 'q'}, length}])[0];
  assert.deepEqual(read({value: 30, unit: 'cm'}).length, {value: 30, unit: 'cm', source: 'entered'});
  assert.deepEqual(read({value: '3', unit: 'yd', source: 'routed'}).length, {value: 3, unit: 'yd', source: 'routed'});
  assert.equal(C.lengthText(read({value: 30, unit: 'cm'}).length), '30 cm');
  assert.equal(C.lengthText(read({value: 3, unit: 'yd'}).length), '3 yd');
  assert.equal(read({value: 2}).length.unit, 'm', 'a length that states no unit is in meters');
  assert.equal(C.lengthText({value: 'abc', unit: 'm'}), '', 'a value that is not a number prints nothing');
  assert.equal(C.lengthText({value: '1e3', unit: 'm'}), '');
});

test('a length the loader cannot use moves to lengthAsWritten: nothing is lost, nothing reads a bad number', () => {
  const read = length => M.readCables([{id: 'c1', a: {item: 'i1', path: 'p'}, b: {item: 'i1', path: 'q'}, length}])[0];
  for (const bad of [{value: 'abc', unit: 'm'}, {value: 0, unit: 'ft'}, {value: -2}, 'long', 5, {value: '1e3'}, [3], true]) {
    const c = read(bad);
    assert.ok(!('length' in c), `${JSON.stringify(bad)} is not a length`);
    assert.deepEqual(c.lengthAsWritten, bad, `${JSON.stringify(bad)} is kept as written`);
    assert.equal(C.lengthText(c.length), '');
    assert.deepEqual(M.readCables([JSON.parse(JSON.stringify(c))])[0], c, 'load, save, load is a fixed point');
  }
  for (const none of [undefined, null]) assert.ok(!('lengthAsWritten' in read(none)), 'no length is no length');
  // A good length beside an earlier lengthAsWritten: both are kept.
  const both = M.readCables([{id: 'c1', a: {}, b: {}, length: {value: 2, unit: 'm'}, lengthAsWritten: 'long'}])[0];
  assert.deepEqual([both.length.value, both.lengthAsWritten], [2, 'long']);
  const odd = read({value: 30, unit: 'cm'});
  assert.deepEqual(M.readCables([JSON.parse(JSON.stringify(odd))])[0], odd, 'an unknown unit is a fixed point too');
});

// ── fix round 3 ─────────────────────────────────────────────────────────
test('a length the user sets or clears replaces the one kept as written; a patch that does not name the length keeps it', () => {
  const r = {...rack(), cables: M.readCables([
    {id: 'c1', a: end('i1', 'p'), b: end('i2', 'q'), length: {value: 'long'}}])};
  assert.deepEqual(r.cables[0].lengthAsWritten, {value: 'long'});
  const set = C.updateCable(r, 'c1', {length: {value: 2, unit: 'm', source: 'entered'}}).cables[0];
  assert.deepEqual(set.length, {value: 2, unit: 'm', source: 'entered'});
  assert.ok(!('lengthAsWritten' in set), 'a new length replaces what was kept as written');
  const cleared = C.updateCable(r, 'c1', {label: 'x', length: null}).cables[0];
  assert.ok(!('length' in cleared) && !('lengthAsWritten' in cleared), 'clearing the length clears both');
  const untouched = C.updateCable(r, 'c1', {label: 'x', media: 'os2'}).cables[0];
  assert.deepEqual(untouched.lengthAsWritten, {value: 'long'}, 'a patch with no length key keeps it exactly');
  assert.ok(!('length' in untouched));
  assert.equal(untouched.label, 'x');
  assert.deepEqual(r.cables[0].lengthAsWritten, {value: 'long'}, 'the input rack is untouched');
});

test('a unit that is not a non-blank string is not a unit: the length moves to lengthAsWritten', () => {
  const read = length => M.readCables([{id: 'c1', a: {item: 'i1', path: 'p'}, b: {item: 'i1', path: 'q'}, length}])[0];
  for (const unit of [{a: 1}, 5, true, ['m'], '', ' ', '\t\n']) {
    const c = read({value: 3, unit});
    assert.ok(!('length' in c), `unit ${JSON.stringify(unit)} is not a unit`);
    assert.deepEqual(c.lengthAsWritten, {value: 3, unit});
    assert.deepEqual(M.readCables([JSON.parse(JSON.stringify(c))])[0], c, 'a fixed point');
  }
  assert.equal(read({value: 3}).length.unit, 'm', 'no unit stated is meters');
  assert.equal(read({value: 3, unit: undefined}).length.unit, 'm');
  assert.equal(read({value: 3, unit: null}).length.unit, 'm', 'null states no unit');
  assert.equal(read({value: 3, unit: ' yd '}).length.unit, ' yd ', 'a non-blank string is kept exactly as written');
});

test('cablePlan3d hands the 3D scene each end as [item id, path, the device\'s own panel]', () => {
  let r = rack();
  // A turned device: its front panel is shown by the OTHER pane, and is still its front panel.
  r = M.updateItem(r, 'i2', {turned: true});
  r = C.withCable(r, {a: end('i2', 'port-1'), b: end('i1', 'slot-2/module/p0'), media: 'os2', purpose: 'uplink'}).rack;
  r = C.withCable(r, {a: end('i2', 'mgmt-eth'), b: end('i3', 'port-2-1', 'rear')}).rack;
  r = C.withCable(r, {a: end('i9', 'port-1'), b: end('i4', 'port-2-1')}).rack;
  assert.deepEqual(C.cablePlan3d(r).links, [
    {id: 'c1', media: 'os2', purpose: 'uplink', from: ['i2', 'port-1', 'front'], to: ['i1', 'slot-2/module/p0', 'front']},
    {id: 'c2', media: 'unset', purpose: '', from: ['i2', 'mgmt-eth', 'front'], to: ['i3', 'port-2-1', 'rear']},
    {id: 'c3', media: 'unset', purpose: '', from: ['i9', 'port-1', 'front'], to: ['i4', 'port-2-1', 'front']}]);
  // The 2D plan names the pane for the same end.
  assert.deepEqual(C.cablePlan(r).links[0].from, ['i2', 'port-1', 'rear']);
  assert.deepEqual(C.cablePlan3d(M.newRack()).links, []);
  assert.deepEqual(C.cablePlan3d({items: []}).links, []);
});

test('sameCables3d: the scene reads which cables there are, their ends and their media, and nothing else', () => {
  let r = rack();
  r = C.withCable(r, {a: end('i2', 'port-1'), b: end('i1', 'slot-2/module/p0'), media: 'os2', purpose: 'uplink'}).rack;
  r = C.withCable(r, {a: end('i2', 'mgmt-eth'), b: end('i3', 'port-2-1'), media: 'cat6a'}).rack;
  const same = next => C.sameCables3d(r, next);
  assert.equal(same(r), true);
  assert.equal(same({...r, name: 'other'}), true);
  // What the scene does not draw: a label, a purpose, a length, a route.
  assert.equal(same(C.updateCable(r, 'c1', {label: 'A1'})), true);
  assert.equal(same(C.updateCable(r, 'c1', {purpose: 'core'})), true);
  assert.equal(same(C.updateCable(r, 'c1', {length: {value: 2, unit: 'm', source: 'entered'}})), true);
  assert.equal(same(C.updateCable(r, 'c1', {route: [{item: 'i4'}]})), true);
  // What it does: the media (the color), an end (the tube and its plugs), a cable more or fewer, their order.
  assert.equal(same(C.updateCable(r, 'c1', {media: 'om4'})), false);
  assert.equal(same(C.updateCable(r, 'c1', {a: end('i2', 'port-3')})), false);
  assert.equal(same(C.updateCable(r, 'c2', {b: end('i4', 'port-2-1')})), false);
  assert.equal(same(C.updateCable(r, 'c2', {b: end('i3', 'port-2-1', 'rear')})), false);
  assert.equal(same(C.withoutCable(r, 'c2')), false);
  assert.equal(same(C.withCable(r, {a: end('i4', 'port-2-1'), b: end('i2', 'port-4')}).rack), false);
  assert.equal(same({...r, cables: [r.cables[1], r.cables[0]]}), false);
  assert.equal(same({...r, cables: [{...r.cables[0], id: 'c9'}, r.cables[1]]}), false);
  // The showcase's 'copper' is colored by its purpose.
  const cu = C.updateCable(r, 'c2', {media: 'copper', purpose: 'server'});
  assert.equal(C.sameCables3d(cu, C.updateCable(cu, 'c2', {purpose: 'management'})), false);
  assert.equal(C.sameCables3d({items: []}, {items: [], cables: []}), true);
});

// ── final fix wave: one U per device ───────────────────────────────────
test('endName names a device by its position: the lowest-numbered U it covers, whichever way the frame counts', () => {
  const heights = {i1: 10, i2: 2};
  const uOf = it => heights[it.id] ?? 1;
  const mk = numbering => ({frame: M.normalizeFrame({heightRU: 24, numbering}), cables: [], items: [
    {id: 'i1', label: 'core-1', ru: 2}, {id: 'i2', label: 'leaf-1', ru: 14}, {id: 'i3', label: 'demarc', ru: 20}]});
  const top = mk('top-down'), up = mk('bottom-up');
  for (const [r, want] of [[top, {i1: 14, i2: 10, i3: 5}], [up, {i1: 2, i2: 14, i3: 20}]])
    for (const it of r.items) {
      assert.equal(C.endName(r, end(it.id, 'p'), uOf), `${it.label} (U${want[it.id]}) p`);
      assert.equal(M.positionOf(r.frame, it.ru, uOf(it)), want[it.id]);
    }
  // Items that already carry their height (fit.js itemsWithU) need no lookup.
  const carried = {...top, items: top.items.map(it => ({...it, u: uOf(it)}))};
  assert.equal(C.endName(carried, end('i1', 'p')), 'core-1 (U14) p');
  // No height known: 1U, the bottom U's own label.
  assert.equal(C.endName(top, end('i1', 'p')), 'core-1 (U23) p');
  // The refusal that names an end names it the same way.
  const taken = {...top, cables: [{id: 'c1', label: '', a: end('i1', 'p'), b: end('i2', 'p')}]};
  assert.equal(C.portFree(taken, end('i1', 'p'), {uOf}).reason, 'core-1 (U14) p already has a cable (c1).');
  assert.equal(C.canCable(taken, end('i3', 'p'), end('i2', 'p'), {uOf}).reason, 'leaf-1 (U10) p already has a cable (c1).');
});

test('updateCable: a patch value of undefined removes the key', () => {
  const r = {cables: [{id: 'c1', a: {}, b: {}, route: [{lane: 'left', ru: 3}], routeEdited: true}]};
  const next = C.updateCable(r, 'c1', {route: [], routeEdited: undefined}).cables[0];
  assert.equal(Object.hasOwn(next, 'routeEdited'), false);
  assert.deepEqual(next.route, []);
});
