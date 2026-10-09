// spec/tests/js/rack-zero-u.mjs
// Zero-U parts beside the rack and narrow parts on one rail (#926), ported
// from portrayal-site's tests/rack/zero-u.test.mjs (#141), with the kit's own
// commands in place of the site's wrapper.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as F from '../../../kit/rack/fit.js';
import * as Z from '../../../kit/rack/zero-u.js';
import * as R from '../../../kit/rack/route.js';
import * as X from '../../../kit/rack/export-data.js';
import {apply, COMMANDS, ZERO_GONE} from '../../../kit/rack/commands.js';
import {createRackEditor} from '../../../kit/rack/editor.js';
import {describe, inspect} from '../../../kit/rack/queries.js';
import {validate} from '../../../kit/rack/validate.js';
import {OPENING, RAIL_W} from '../../../kit/rack/rails.js';

// rack.json as the build writes these (library/dist, 2026-10-08), trimmed.
const SIZES = {
  'cmv-sfd45u5w': {manufacturer: 'FS.com', model: 'CMV-SFD45U5W', mount: 'rack-side', ru: 45, h: 2108, w: 138.8, d: 165.1,
                   default: 'base', configs: ['base'], guides: {front: ['duct']}, capacity: {count: 2745}},
  'cmv-sfd42u9w': {manufacturer: 'FS.com', model: 'CMV-SFD42U9W', mount: 'rack-side', ru: 42, h: 1866.9, w: 88.9, d: 152.6,
                   default: 'base', configs: ['base'], guides: {front: ['duct']}},
  'cmv-5u3w': {manufacturer: 'FS.com', model: 'CMV-5U3W', mount: 'rack-face', ru: 5, h: 222, w: 26, d: 84,
               default: 'base', configs: ['base'], guides: {front: ['duct']}, capacity: {count: 188}},
  'fhd-cmp5dr': {manufacturer: 'FS.com', model: 'FHD-CMP5DR', mount: 'rack-face', ru: 1, h: 44, w: 483, d: 110,
                 default: 'base', configs: ['base'], guides: {front: ['guide-1']}},
  // a zero-U PDU: stands beside the rack, states no U and carries no lane
  'pdu-0u': {manufacturer: 'Acme', model: 'PDU-0U', mount: 'rack-side', ru: 0, h: 1730, w: 52, d: 53, default: 'base', configs: ['base']},
  'sw': {manufacturer: 'Acme', model: 'SW-1', ru: 1, h: 43.5, w: 438, d: 515, default: 'base', configs: ['base']},
};
const chassisOf = ref => SIZES[ref] ?? null;
const ctx = {chassisOf};
const DUCT = 'cmv-sfd45u5w', BRACKET = 'cmv-5u3w';
const rackOf = (kind = 'two-post', heightRU = 45) => M.withFrame(M.newDoc({kind}).racks[0], {heightRU});
const run = (rack, cmds) => apply(rack, cmds, ctx);
const SCHEMA = JSON.parse(readFileSync(new URL('../../schemas/rack.schema.json', import.meta.url)));

test('a narrow part is a rack-face part under the 450 mm opening; a zero-U part is a rack-side one', () => {
  assert.ok(F.isNarrow(chassisOf(BRACKET)));
  assert.ok(!F.isNarrow(chassisOf('fhd-cmp5dr')));
  assert.ok(F.isZeroUPart(chassisOf(DUCT)) && F.isZeroUPart(chassisOf('pdu-0u')));
  assert.ok(!F.isZeroUPart(chassisOf(BRACKET)));
  // by its stated U, else its height
  assert.equal(F.zeroUUnits(chassisOf(DUCT)), 45);
  assert.equal(F.zeroUUnits(chassisOf('pdu-0u')), 39);
});

test('a zero-U part fits on an upright of this frame, within its height by its ru, not its drawn height', () => {
  const r = rackOf();
  assert.deepEqual(F.fitsZeroU(r, {ref: DUCT, at: 'left', ru: 1}, chassisOf), {ok: true});
  assert.match(F.fitsZeroU(r, {ref: DUCT, at: 'left', ru: 2}, chassisOf).reason, /45U tall; 44U from U2/);
  assert.match(F.fitsZeroU(rackOf('two-post', 42), {ref: DUCT, at: 'left', ru: 1}, chassisOf).reason, /45U tall/);
  assert.match(F.fitsZeroU(r, {ref: DUCT, at: 'left-front', ru: 1}, chassisOf).reason, /not an attachment point of a two-post frame: use left, right/);
  assert.deepEqual(F.fitsZeroU(rackOf('four-post'), {ref: DUCT, at: 'left-rear', ru: 1}, chassisOf), {ok: true});
  assert.match(F.fitsZeroU(r, {ref: 'fhd-cmp5dr', at: 'left', ru: 1}, chassisOf).reason, /does not stand beside the rack/);
  assert.match(F.fitsZeroU(r, {ref: 'nope', at: 'left', ru: 1}, chassisOf).reason, /No size is known/);
  assert.match(F.fitsZeroU(r, {ref: DUCT, at: 'left', ru: 0}, chassisOf).reason, /Below U1/);
});

test('zerou.place puts the part in zeroU, never in items, at offsetMm from the bottom', () => {
  const r = rackOf();
  const res = run(r, {op: 'zerou.place', ref: DUCT, at: 'left', ru: 1});
  assert.ok(!res.error, res.error);
  assert.equal(res.rack.items.length, 0);
  assert.deepEqual(res.rack.zeroU, [{id: 'z1', ref: DUCT, cfg: 'base', label: 'CMV-SFD45U5W', at: 'left', offsetMm: 0}]);
  assert.equal(res.summary, 'Placed CMV-SFD45U5W beside the rack at left, U1-U45.');
  assert.deepEqual(res.created.ids, ['z1']);
  assert.ok(res.step);
  const two = run(res.rack, {op: 'zerou.place', ref: DUCT, at: 'right', ru: 1, between: true});
  assert.equal(two.rack.zeroU[1].id, 'z2');
  assert.equal(two.rack.zeroU[1].between, true);
  assert.match(two.summary, /between racks at right/);
  assert.match(run(res.rack, {op: 'zerou.place', ref: DUCT, at: 'left', ru: 1}).error, /Overlaps CMV-SFD45U5W at left/);
  assert.match(run(rackOf('two-post', 50), {op: 'zerou.place', ref: BRACKET, at: 'left', ru: 1}).error, /does not stand beside the rack/);
  // a zero-U PDU is placed the same way, and states its U from its height
  const pdu = run(rackOf('four-post', 42), {op: 'zerou.place', ref: 'pdu-0u', at: 'right-rear', ru: 2});
  assert.equal(pdu.summary, 'Placed PDU-0U beside the rack at right-rear, U2-U40.');
});

test('the kit place of a zero-U part is refused: it would land on the rails', () => {
  assert.equal(run(rackOf(), {op: 'place', ref: DUCT, face: 'front', ru: 1}).error,
    'CMV-SFD45U5W stands beside the rack, not on its rails: place it with zerou.place.');
});

test('zerou.update moves, renames and marks between; a no-op hands back the rack; remove takes it away', () => {
  const r = run(rackOf('two-post', 48), {op: 'zerou.place', ref: DUCT, at: 'left', ru: 1}).rack;
  const up = run(r, {op: 'zerou.update', id: 'z1', ru: 3, at: 'right', label: 'duct-A'});
  assert.ok(!up.error, up.error);
  assert.deepEqual(up.rack.zeroU[0], {id: 'z1', ref: DUCT, cfg: 'base', label: 'duct-A', at: 'right', offsetMm: M.zeroUOffset(3)});
  assert.equal(M.zeroUBottom(up.rack.zeroU[0]), 3);
  assert.deepEqual(F.zeroUSpan(up.rack.zeroU[0], chassisOf), [3, 47]);
  assert.match(run(r, {op: 'zerou.update', id: 'z1', ru: 5}).error, /45U tall/);
  const same = run(r, {op: 'zerou.update', id: 'z1', ru: 1});
  assert.ok(same.noop);
  assert.equal(same.rack, r);
  const between = run(r, {op: 'zerou.update', id: 'z1', between: true});
  assert.equal(between.rack.zeroU[0].between, true);
  assert.equal(between.summary, 'Changed CMV-SFD45U5W, between racks at left, U1-U45.');
  const back = run(between.rack, {op: 'zerou.update', id: 'z1', between: false});
  assert.ok(!('between' in back.rack.zeroU[0]));
  const gone = run(r, {op: 'zerou.remove', id: 'z1'});
  assert.deepEqual(gone.rack.zeroU, []);
  assert.equal(gone.summary, 'Removed CMV-SFD45U5W from beside the rack.');
  assert.equal(run(gone.rack, {op: 'zerou.remove', id: 'z1'}).error, ZERO_GONE);
  // an item command given a zero-U id says which command takes it
  assert.equal(run(r, {op: 'remove', id: 'z1'}).error, 'z1 stands beside the rack: use zerou.remove.');
  assert.equal(run(r, {op: 'move', id: 'z1', ru: 2}).error, 'z1 stands beside the rack: use zerou.update.');
});

test('a batch mixes item and zero-U commands, binds @names across both, and refuses bad arguments with a sentence', () => {
  const r = rackOf();
  const res = run(r, [
    {op: 'zerou.place', ref: DUCT, at: 'left', ru: 1, as: 'duct'},
    {op: 'place', ref: 'fhd-cmp5dr', face: 'front', ru: 10, as: 'mgr'},
    {op: 'zerou.update', id: '@duct', label: 'vcm-1'}]);
  assert.ok(!res.error, res.error);
  assert.deepEqual(res.created, {duct: 'z1', mgr: 'i1', ids: ['z1', 'i1']});
  assert.equal(res.rack.zeroU[0].label, 'vcm-1');
  assert.match(res.summary, /Placed CMV-SFD45U5W .* Placed FHD-CMP5DR at U10 on the front\. Changed vcm-1/);
  assert.deepEqual(run(r, {op: 'zerou.place', ref: DUCT, ru: 1}), {error: 'zerou.place needs at, some text.', index: 0});
  assert.deepEqual(run(r, {op: 'zerou.place', ref: DUCT, at: 'left', ru: 1, side: 'left'}), {error: 'zerou.place does not take side.', index: 0});
  assert.equal(run(r, [{op: 'zerou.update', id: '@x'}]).error, 'Nothing earlier in this batch is called x.');
  for (const op of ['zerou.place', 'zerou.update', 'zerou.remove', 'side.place', 'side.set']) assert.ok(COMMANDS[op], op);
});

test('narrow rail parts: one on each rail at the same U, never two on one rail, and a full-width manager is refused there', () => {
  const r = rackOf('two-post', 42);
  const res = run(r, [{op: 'side.place', ref: BRACKET, face: 'front', ru: 10, side: 'left'},
                      {op: 'side.place', ref: BRACKET, face: 'front', ru: 10, side: 'right'}]);
  assert.ok(!res.error, res.error);
  assert.deepEqual(res.rack.items.map(i => [i.id, i.side, i.ru]), [['i1', 'left', 10], ['i2', 'right', 10]]);
  assert.equal(res.summary, 'Placed CMV-5U3W at U10 on the front, on the left rail. Placed CMV-5U3W at U10 on the front, on the right rail.');
  // The bracket is 5U: its upper units are taken on its side too.
  assert.equal(run(res.rack, {op: 'side.place', ref: BRACKET, face: 'front', ru: 13, side: 'left'}).error,
    'Taken by CMV-5U3W on the front, left rail.');
  assert.ok(!run(res.rack, {op: 'side.place', ref: BRACKET, face: 'front', ru: 15, side: 'left'}).error);
  // A full-width manager claims both sides; a wide part has no side.
  assert.match(run(res.rack, {op: 'place', ref: 'fhd-cmp5dr', face: 'front', ru: 12}).error, /Taken by/);
  assert.equal(run(r, {op: 'side.place', ref: 'fhd-cmp5dr', face: 'front', ru: 10, side: 'left'}).error,
    'FHD-CMP5DR spans the opening, so it has no side.');
  // The rear face is its own.
  assert.ok(!run(res.rack, {op: 'side.place', ref: BRACKET, face: 'rear', ru: 10, side: 'left'}).error);
  // A narrow part on one rail never bolts onto a device behind it.
  const host = M.withItem(r, {ref: 'sw', cfg: 'base', ru: 10, label: 'sw-1'}).rack;
  assert.ok(!('on' in run(host, {op: 'side.place', ref: BRACKET, face: 'front', ru: 10, side: 'left'}).rack.items[1]));
  // Each fits where it is, judged by its side.
  for (const it of res.rack.items) assert.deepEqual(F.fits(res.rack, it, chassisOf, {ignoreId: it.id}), {ok: true});
});

test('a narrow part moves by its side, and side.set turns it across or onto a rail', () => {
  const r = run(rackOf('two-post', 42), [{op: 'side.place', ref: BRACKET, face: 'front', ru: 10, side: 'left'},
                                         {op: 'side.place', ref: BRACKET, face: 'front', ru: 20, side: 'right'}]).rack;
  const moved = run(r, {op: 'move', id: 'i2', ru: 10});
  assert.ok(!moved.error, moved.error);
  assert.equal(moved.rack.items[1].ru, 10);
  assert.equal(moved.rack.items[1].side, 'right');
  assert.equal(moved.summary, 'Moved CMV-5U3W to U10 on the front, on the right rail.');
  assert.match(run(moved.rack, {op: 'side.set', id: 'i2', side: null}).error, /Taken by/);
  assert.match(run(moved.rack, {op: 'side.set', id: 'i2', side: 'left'}).error, /Taken by/);
  const across = run(r, {op: 'side.set', id: 'i2', side: null});
  assert.ok(!('side' in across.rack.items[1]));
  assert.equal(across.summary, 'Put CMV-5U3W across both rails.');
  assert.ok(run(r, {op: 'side.set', id: 'i2', side: 'right'}).noop);
  assert.equal(run(rackOf(), {op: 'side.set', id: 'i9', side: 'left'}).error, 'That device is no longer in the rack.');
  // across both rails over a device, it bolts onto it, as place does
  const hosted = run(M.withItem(r, {ref: 'sw', cfg: 'base', ru: 30, label: 'sw-1'}).rack,
    [{op: 'move', id: 'i1', ru: 30}, {op: 'side.set', id: 'i1', side: null}]);
  assert.ok(!hosted.error, hosted.error);
  assert.deepEqual([hosted.rack.items[0].on, hosted.rack.items[0].unit], ['i3', 1]);
});

test('a narrow part with no side, placed or moved, is judged on every unit it spans', () => {
  const r = run(rackOf('two-post', 42), {op: 'side.place', ref: BRACKET, face: 'front', ru: 10, side: 'left'}).rack;
  // Its bottom unit is free; its fifth is the sided bracket's bottom.
  assert.match(run(r, {op: 'place', ref: BRACKET, face: 'front', ru: 6}).error, /Taken by CMV-5U3W/);
  const ok = run(r, {op: 'place', ref: BRACKET, face: 'front', ru: 20});
  assert.ok(!ok.error, ok.error);
  assert.match(run(ok.rack, {op: 'move', id: 'i2', ru: 7}).error, /Taken by CMV-5U3W/);
  assert.ok(!run(ok.rack, {op: 'move', id: 'i2', ru: 30}).error);
  // and within the rack's height
  assert.equal(run(r, {op: 'place', ref: BRACKET, face: 'front', ru: 40}).error, '5U tall; 3U from U40 to the top of this 42U rack.');
});

test('a lane runs through a duct: its centre line where it stands, the gutter elsewhere; a PDU pushes it outboard (#949)', () => {
  const r = run(rackOf('two-post', 48), {op: 'zerou.place', ref: DUCT, at: 'left', ru: 2}).rack;
  const x = -(OPENING / 2 + RAIL_W + SIZES[DUCT].w / 2);
  assert.equal(Z.zeroUX(r.zeroU[0], chassisOf), x);
  assert.equal(R.laneXAt(r, 'left', 10, chassisOf), x);
  assert.equal(R.laneXAt(r, 'left', 1, chassisOf), R.laneX('left'));
  assert.equal(R.laneXAt(r, 'left', 47, chassisOf), R.laneX('left'));
  assert.equal(R.laneXAt(r, 'right', 10, chassisOf), R.laneX('right'));
  assert.equal(Z.zeroUOnLane(r, 'left', 46, chassisOf)?.id, 'z1');
  assert.equal(R.pointOf(r, {lane: 'left', ru: 10}, ctx).x, x);
  const pdu = run(rackOf('four-post', 42), {op: 'zerou.place', ref: 'pdu-0u', at: 'left-front', ru: 1}).rack;
  // a PDU stands in the gutter and carries no lane: the lane runs in a gutter
  // as wide as the usual one just outboard of it, where it stands, and in the
  // gutter above it (route.js laneXAt)
  const w = SIZES['pdu-0u'].w;
  assert.equal(R.laneXAt(pdu, 'left-front', 10, chassisOf), -(OPENING / 2 + RAIL_W + w + R.LANE_GAP / 2));
  assert.equal(R.laneXAt(pdu, 'right-front', 10, chassisOf), R.laneX('right'));
});

test('a routed length runs through the duct, about 49 mm further out at each end than the gutter', () => {
  let r = rackOf('two-post', 45);
  r = M.withItem(r, {ref: 'sw', cfg: 'base', ru: 5, label: 'a'}).rack;
  r = M.withItem(r, {ref: 'sw', cfg: 'base', ru: 30, label: 'b'}).rack;
  const cable = {id: 'c1', a: {item: 'i1', path: 'p1', view: 'front'}, b: {item: 'i2', path: 'p1', view: 'front'}, media: 'cat6',
                 route: [{lane: 'left', ru: 5}, {lane: 'left', ru: 30}], routeEdited: true};
  r = {...r, cables: [cable]};
  const rc = {chassisOf, guidesOf: () => [], portX: () => -150};
  const bare = R.routedLength(r, cable, rc).measured;
  const ducted = run(r, {op: 'zerou.place', ref: DUCT, at: 'left', ru: 1}).rack;
  const through = R.routedLength(ducted, cable, rc).measured;
  const out = Math.abs(Z.zeroUX(ducted.zeroU[0], chassisOf) - R.laneX('left'));
  assert.ok(Math.abs(out - 49.4) < 0.1, `${out}`);
  assert.ok(Math.abs((through - bare) * 1000 - 2 * out) < 0.5, `${through} ${bare}`);
});

test('fill: every cable whose lane run passes through the duct, once, against 40% of its channel and its capacity', () => {
  let r = run(rackOf('two-post', 45), {op: 'zerou.place', ref: DUCT, at: 'left', ru: 1}).rack;
  const lane = (id, media, route) => ({id, a: {item: 'x', path: 'p', view: 'front'}, b: {item: 'y', path: 'p', view: 'front'},
                                       media, route, routeEdited: true});
  r = {...r, cables: [lane('c1', 'cat6', [{lane: 'left', ru: 10}, {lane: 'left', ru: 30}]),
                      lane('c2', 'os2', [{lane: 'left', ru: 5}]),
                      lane('c3', 'cat6', [{lane: 'right', ru: 10}, {lane: 'right', ru: 30}])]};
  const rc = {chassisOf, guidesOf: () => [], portX: () => null, zeroUAperture: z => (z.id === 'z1' ? {w: 5, h: 5} : null)};
  const fill = R.fill(r, rc);
  assert.equal(fill.length, 1);
  const area = Math.PI * 9 + Math.PI * 2.25;
  assert.deepEqual(fill[0], {item: 'z1', via: 'duct', count: 2, percent: Math.round(area / 10 * 100), over: true,
                             cables: ['c1', 'c2'], zeroU: true});
  assert.deepEqual(R.capacityOver(r, rc), []);
  // No aperture: no fill entry, but the count still meets the stated capacity.
  const many = {...r, cables: Array.from({length: 2746}, (_, k) => lane(`c${k}`, 'cat6', [{lane: 'left', ru: 3}]))};
  assert.deepEqual(R.fill(many, {...rc, zeroUAperture: () => null}), []);
  assert.deepEqual(R.capacityOver(many, rc), [{item: 'z1', count: 2746, capacity: 2745, zeroU: true}]);
  // A run on the lane that only passes the duct's span still counts (its ends are outside it).
  const r48 = run(rackOf('two-post', 48), {op: 'zerou.place', ref: DUCT, at: 'left', ru: 2}).rack;
  const pass = R.fill({...r48, cables: [lane('c1', 'cat6', [{lane: 'left', ru: 1}, {lane: 'left', ru: 48}])]},
    {...rc, zeroUAperture: () => ({w: 93, h: 165})});
  assert.equal(pass[0].count, 1);
  // over its fill, it is named in the notes as any pathway is
  const nameOf = id => M.zeroUById(r, id)?.label ?? id;
  assert.deepEqual(X.fillNotes(r, {fill, over: [], routes: new Map()}, nameOf), [`duct on CMV-SFD45U5W: 2 cables, ${fill[0].percent}% of a 40% fill.`]);
});

test('a rack file with zero-U parts and sided items reads back whole and validates, at version 3', () => {
  let r = rackOf('two-post', 45);
  r = run(r, [{op: 'zerou.place', ref: DUCT, at: 'left', ru: 1, between: true},
              {op: 'side.place', ref: BRACKET, face: 'front', ru: 10, side: 'right'}]).rack;
  const doc = {...M.newDoc(), racks: [r]};
  const text = M.serialize(doc);
  assert.deepEqual(M.parseDoc(text).racks[0], r);
  assert.equal(JSON.parse(text).version, 3);   // bundles raised it (#921); zero-U parts did not
  assert.deepEqual(validate(SCHEMA, JSON.parse(text)), []);
  // An entry with no id, or one an earlier entry took, gets one past the ids in use; other entries stay as written.
  const raw = JSON.parse(text);
  raw.racks[0].zeroU.push({ref: DUCT, at: 'right', offsetMm: 0}, {id: 'z1', ref: DUCT, at: 'right', offsetMm: 0}, 'junk', {id: 'z9'});
  raw.racks[0].items[0].side = 'middle';
  const back = M.parseDoc(raw).racks[0];
  assert.deepEqual(back.zeroU.map(z => z?.id ?? z), ['z1', 'z10', 'z11', 'junk', 'z9']);
  assert.deepEqual(M.zeroUOf(back).map(z => z.id), ['z1', 'z10', 'z11']);
  assert.ok(!('side' in back.items[0]));
  // What validated before the zero-U keys were described still does (an entry was always an object).
  raw.racks[0].zeroU = raw.racks[0].zeroU.filter(z => z !== 'junk');
  assert.deepEqual(validate(SCHEMA, raw), []);
  assert.deepEqual(validate(SCHEMA, JSON.parse(M.serialize({...doc, racks: [{...r, zeroU: [{id: 'z1'}, {at: 5, offsetMm: 'low'}]}]}))), []);
});

test('the site\'s zero-U data maps onto the kit\'s without loss', () => {
  // as portrayal-site #141 writes it: zeroU entries and an item's side
  const site = {format: 'portrayal-rack', version: 2, id: 'doc-site', racks: [{id: 'r1', name: 'Rack 1',
    frame: {kind: 'two-post', heightRU: 45, numbering: 'bottom-up', holes: {style: 'square', thread: null}, railDepth: null, usableDepth: 1000, ref: null},
    items: [{id: 'i1', ref: BRACKET, cfg: 'base', label: 'fb-1', ru: 10, face: 'front', turned: false, swaps: {}, fields: {}, side: 'left'}],
    zeroU: [{id: 'z1', ref: DUCT, cfg: 'base', label: 'vcm-1', at: 'right', offsetMm: 0, between: true},
            {id: 'z2', ref: 'cmv-sfd42u9w', cfg: 'base', label: 'vcm-2', at: 'left', offsetMm: 133.35}],
    cables: []}]};
  const doc = M.parseDoc(JSON.stringify(site));
  assert.deepEqual(JSON.parse(M.serialize(doc)), {...site, version: 3});   // migrated, nothing else changed
  assert.deepEqual(F.zeroUSpan(doc.racks[0].zeroU[1], chassisOf), [4, 45]);
});

test('the editor takes zero-U commands as undo steps, and a side survives undo', () => {
  const doc = {...M.newDoc({kind: 'two-post'}), racks: [rackOf('two-post', 45)]};
  const ed = createRackEditor({doc, chassisOf});
  const events = [];
  ed.on('change', ev => events.push(ev));
  const res = ed.apply([{op: 'zerou.place', ref: DUCT, at: 'right', ru: 1}], {origin: 'agent'});
  assert.ok(!res.error, res.error);
  assert.equal(ed.rack().zeroU.length, 1);
  assert.equal(ed.undoSummary, 'Placed CMV-SFD45U5W beside the rack at right, U1-U45.');
  assert.deepEqual(events.at(-1).commands, [{op: 'zerou.place', ref: DUCT, at: 'right', ru: 1}]);
  assert.equal(events.at(-1).origin, 'agent');
  ed.undo();
  assert.equal(ed.rack().zeroU.length, 0);
  ed.redo();
  assert.equal(ed.rack().zeroU.length, 1);
  assert.match(ed.apply({op: 'zerou.place', ref: DUCT, at: 'right', ru: 1}).error, /Overlaps/);
  assert.ok(!ed.preview({op: 'zerou.remove', id: 'z1'}).error);
  assert.equal(ed.rack().zeroU.length, 1);
  assert.match(ed.apply([{op: 'zerou.remove', id: 'z1'}, {op: 'lengths.routed', routeCtx: {}}]).error, /page's own command/);
  ed.apply({op: 'side.place', ref: BRACKET, face: 'front', ru: 4, side: 'right'});
  ed.apply({op: 'patch', id: 'i1', label: 'fb-1'});
  assert.deepEqual([ed.rack().items[0].side, ed.rack().items[0].label], ['right', 'fb-1']);
  ed.undo();
  assert.equal(ed.rack().items[0].side, 'right');
});

test('a frame change moves the parts beside the rack to their side of the new frame, down to fit, or off it', () => {
  let r = rackOf('four-post', 45);
  r = run(r, [{op: 'zerou.place', ref: DUCT, at: 'left-front', ru: 1, label: 'vcm-1'},
              {op: 'zerou.place', ref: 'cmv-sfd42u9w', at: 'right-rear', ru: 3, label: 'vcm-2'}]).rack;
  const two = run(r, {op: 'frame', kind: 'two-post'});
  assert.deepEqual(two.rack.zeroU.map(z => [z.id, z.at, M.zeroUBottom(z)]), [['z1', 'left', 1], ['z2', 'right', 3]]);
  assert.equal(two.summary, 'Changed the rack frame. Moved vcm-1, vcm-2 beside the rack to fit the new frame.');
  assert.deepEqual(two.findings, [{kind: 'note', text: 'Moved vcm-1, vcm-2 beside the rack to fit the new frame.'}]);
  const low = run(r, {op: 'frame', heightRU: 43});
  assert.deepEqual(low.rack.zeroU.map(z => [z.id, M.zeroUBottom(z)]), [['z2', 2]]);
  assert.equal(low.summary, 'Set the rack to 43U. Moved vcm-2 beside the rack to fit the new frame. ' +
    'Removed vcm-1 from beside the rack: it does not fit the new frame.');
  // a frame change that leaves them where they were says nothing of them
  assert.equal(run(r, {op: 'frame', numbering: 'top-down'}).summary, 'Changed the rack frame.');
  // two that land on one upright of a two-post and overlap: the later one goes
  const both = run(rackOf('four-post', 45), [{op: 'zerou.place', ref: DUCT, at: 'left-front', ru: 1, label: 'a'},
                                            {op: 'zerou.place', ref: DUCT, at: 'left-rear', ru: 1, label: 'b'}]).rack;
  assert.deepEqual(run(both, {op: 'frame', kind: 'two-post'}).rack.zeroU.map(z => z.label), ['a']);
});

test('describe and inspect know the parts beside the rack and the rail a part is on', async () => {
  let r = rackOf('two-post', 45);
  r = run(r, [{op: 'zerou.place', ref: DUCT, at: 'left', ru: 1, label: 'vcm-1', between: true},
              {op: 'side.place', ref: BRACKET, face: 'front', ru: 10, side: 'right', label: 'fb-1'}]).rack;
  const text = describe(r, ctx);
  assert.match(text, /^Rack 1 \(r1\): 1 item, 1 part beside the rack, 0 cables\./);
  assert.match(text, /\ni1 fb-1 U10-U14 front right rail\n/);
  assert.match(text, /\nBeside the rack:\nz1 vcm-1 between racks at left, U1-U45/);
  assert.match(describe(r, ctx, {section: 'zeroU'}), /Beside the rack 1-1 shown\.\n.*\nBeside the rack:\nz1 vcm-1 between racks at left, U1-U45, cmv-sfd45u5w base$/);
  assert.match(describe(rackOf(), ctx, {section: 'zeroU'}), /No parts beside the rack\./);
  // a rack with none reads as before
  assert.match(describe(rackOf(), ctx), /^Rack 1 \(r1\): 0 items, 0 cables\./);
  assert.deepEqual(await inspect(r, 'z1', ctx), {kind: 'zeroU', id: 'z1', ref: DUCT, model: 'CMV-SFD45U5W', manufacturer: 'FS.com',
    label: 'vcm-1', cfg: 'base', at: 'left', ru: 1, u: 45, between: true, mount: 'rack-side', lane: 'left',
    where: 'between racks at left, U1-U45'});
  assert.equal((await inspect(r, 'i1', ctx)).side, 'right');
  assert.deepEqual(await inspect(r, 'z7', ctx), {error: ZERO_GONE});
});

test('the exports: where each part stands, the rail a part is on, and a DCIM row with no position or face', () => {
  let r = rackOf('two-post', 45);
  r = run(r, [{op: 'zerou.place', ref: DUCT, at: 'right', ru: 1, label: 'vcm-1', between: true},
              {op: 'side.place', ref: BRACKET, face: 'front', ru: 20, side: 'left', label: 'fb-1'}]).rack;
  assert.deepEqual(X.zeroUNotes(r, chassisOf),
    ['vcm-1: FS.com CMV-SFD45U5W, 0U, between racks at right, U1-U45; it serves the next rack too, which this file does not hold.']);
  assert.deepEqual(X.managerNotes(r.items, chassisOf, r.frame), ['fb-1: FS.com CMV-5U3W, 0U, at U20, front, left rail.']);
  // an export that carries them says only an entry it cannot place is left out
  const odd = {...r, zeroU: [...r.zeroU, {id: 'z9', ref: 'fhd-cmp5dr', at: 'left', offsetMm: 0}, 'junk']};
  assert.deepEqual(X.rackNotes(odd, {cables: false, zeroU: false, chassisOf}), ['2 zero-U items are not in this export yet.']);
  assert.deepEqual(X.rackNotes(r, {cables: false, zeroU: false, chassisOf}), []);
  assert.deepEqual(X.rackNotes(r, {cables: false}), ['1 zero-U item is not in this export yet.']);
  const items = [...F.itemsWithU(r, chassisOf), ...X.zeroUImportItems(r, chassisOf)];
  const types = new Map(items.map(i => [i.id, {manufacturer: 'FS.com', model: i.ref, isFullDepth: false}]));
  const {rows} = X.deviceImportRows({rack: r, items, types, dcim: {site: 'HQ', role: 'cabling'}});
  const byName = Object.fromEntries(rows.map(x => [x.name, x]));
  assert.deepEqual([byName['vcm-1'].position, byName['vcm-1'].face], ['', '']);
  assert.equal(byName['vcm-1'].comments, '0U, between racks at right, U1-U45, serving the next rack too; NetBox has no field for that.');
  assert.equal(byName['fb-1'].comments, '0U cable manager on the front rail face at U20, left rail; NetBox has no field for that.');
  assert.equal(X.mountPick('rack-side').tag, '0U, stands beside the rack');
  assert.deepEqual(X.mountNotes([{label: 'vcm-1', ref: DUCT, ru: 1}], chassisOf, r.frame), []);
  assert.deepEqual(X.zeroUImportItems(r, chassisOf)[0], {id: 'z1', ref: DUCT, cfg: 'base', label: 'vcm-1', at: 'right', between: true,
    ru: 1, u: 45, w: 138.8, h: 2108, mount: 'rack-side', where: 'between racks at right, U1-U45'});
});
