// spec/tests/js/rack-capacity-basis.mjs
// A manager's stated cable count is a count of ONE KIND of cable (#1032).
// The count is compared with the cables at least as thick as that kind, and
// with no thinner one; how full a ring is stays the fill's to say; a warning
// says which manager it is about; the fill note cannot be read as a share of
// the opening; and a cross-face tag names a port in words. Every expected
// number below is worked by hand in its comment.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as X from '../../../kit/rack/export-data.js';
import * as C from '../../../kit/rack/cable-rules.js';
import {inspect, freePorts} from '../../../kit/rack/queries.js';

// A lacer panel of five rings, as rack.json states one: thirty cables, and
// the cable its maker counted with. `plain` states a count and that no source
// names the cable (`media: null`). `early` is the same part in a catalogue
// built before the key existed: a count and no `media` at all.
const LACER = {ru: 1, d: 110, mount: 'rack-face', shell: 'sheet', manufacturer: 'Acme', model: 'LACER-5'};
const SIZES = {sw: {ru: 1, d: 515}, pp: {ru: 1, d: 100},
  lacer: {...LACER, capacity: {count: 30, basis: 'Cat6 24AWG cables, theoretical', media: 'cat6'}},
  plain: {...LACER, capacity: {count: 30, basis: 'an estimate, not stated by its maker', media: null}},
  early: {...LACER, capacity: {count: 30, basis: 'Cat6 24AWG cables, theoretical'}},
  // the maker states none: the count is an estimate (P-0027)
  est: {...LACER, capacity: {count: 30, basis: 'ESTIMATE, not stated by its maker', media: 'cat6', estimated: true}},
  // a duct two units tall, on the rails
  duct2: {ru: 2, d: 80}};
const chassisOf = ref => SIZES[ref] || null;
const add = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: 'x', ru, label: extra.label ?? ref, ...extra}).rack;
// The rings at their x in the rack, each 32 mm by 29.5 mm: 944 mm2, of which
// the fill limit (40%) is 377.6 mm2.
const XS = [-205, -110, 0, 110, 205];
const RINGS = XS.map((x, i) => ({via: `guide-${i + 1}`, kind: 'ring', x, aperture: {w: 32, h: 29.5}}));
// `checkKept` lays each cable again beside the path the kit kept for it and
// throws where they differ: nothing here may be read by a kept answer.
const ctxOf = rack => ({chassisOf, checkKept: true,
  guidesOf: id => {
    const it = rack.items.find(i => i.id === id);
    return it && Object.hasOwn(LACERS, it.ref) ? RINGS.map(r => ({...r, face: it.face})) : [];
  },
  // a port stands under the ring its cable passes: `r1-...` under ring 1, to `r5-...` under ring 5
  portX: end => XS[Number(end.path[1]) - 1]});
const LACERS = {lacer: 1, plain: 1, early: 1, odd: 1, est: 1};
// A switch at U20 with a manager on it, and a panel at U30.
const rackOf = (manager = 'lacer') => {
  let r = add(M.newRack(), 'sw', 20, {label: 'switch'});
  r = add(r, manager, 20, {on: 'i1', unit: 1, label: 'LACER-5'});
  return add(r, 'pp', 30, {label: 'panel'});
};
// `n` cables of one kind, each through ring `k` of the manager and no other.
const cables = (n, media, k) => Array.from({length: n}, (_, j) => ({id: `${media || 'none'}-${k}-${j}`, media,
  route: [{item: 'i2', via: `guide-${k}`}], routeEdited: true, purpose: '', label: '',
  a: {item: 'i1', path: `r${k}-${media}-${j}`, view: 'front'}, b: {item: 'i3', path: `r${k}-${media}-${j}`, view: 'front'}}));
const spread = (each, media) => [1, 2, 3, 4, 5].flatMap(k => cables(each, media, k));
const notes = (r, ctx = ctxOf(r)) => X.fillNotes(r, {fill: R.fill(r, ctx), over: R.capacityOver(r, ctx), routes: new Map(), ctx},
  id => r.items.find(i => i.id === id)?.label ?? id);
const fills = r => R.fill(r, ctxOf(r)).map(f => [f.via, f.count, f.percent, f.over]);

test('48 fibre cords through a manager that states 30 Cat6: no warning, and no ring is over its fill', () => {
  const r = {...rackOf(), cables: [...cables(24, 'os2', 1), ...cables(24, 'os2', 5)]};
  // 48 distinct cables pass the manager, 24 by ring 1 and 24 by ring 5. A
  // 3 mm cord is 7.069 mm2; 24 are 169.6 mm2, 45% of the 377.6 mm2 limit.
  assert.deepEqual(fills(r), [['guide-1', 24, 45, false], ['guide-5', 24, 45, false]]);
  assert.deepEqual(R.capacityOver(r, ctxOf(r)), []);
  assert.deepEqual(notes(r), []);
});

test('31 Cat6 through a manager that states 30 Cat6 warns, and names the kind', () => {
  const r = {...rackOf(), cables: [...cables(16, 'cat6', 1), ...cables(15, 'cat6', 5)]};
  assert.deepEqual(R.capacityOver(r, ctxOf(r)), [{item: 'i2', count: 31, through: 31, capacity: 30, media: 'cat6', diameter: 6}]);
  // a 6 mm cable is 28.27 mm2: 16 are 452.4 mm2, 120% of the limit, and 15 are 424.1 mm2, 112%
  assert.deepEqual(notes(r), [
    'ring 1 on LACER-5 (U20 front): 16 cables, 120% of its fill limit; the limit is 40% of the opening.',
    'ring 5 on LACER-5 (U20 front): 15 cables, 112% of its fill limit; the limit is 40% of the opening.',
    'LACER-5 (U20 front): 31 cables at least as thick as Cat 6 copper through it, more than the 30 Cat 6 copper cables its maker states.']);
  // exactly the stated count is not over it
  const even = {...r, cables: r.cables.slice(0, 30)};
  assert.deepEqual(R.capacityOver(even, ctxOf(even)), []);
});

test('31 Cat6 through a manager whose count is an estimate warns, and says it is one (P-0027)', () => {
  const r = {...rackOf('est'), cables: [...cables(16, 'cat6', 1), ...cables(15, 'cat6', 5)]};
  assert.deepEqual(R.capacityOver(r, ctxOf(r)), [{item: 'i2', count: 31, through: 31, capacity: 30, media: 'cat6', diameter: 6, estimated: true}]);
  assert.equal(notes(r).at(-1),
    'LACER-5 (U20 front): 31 cables at least as thick as Cat 6 copper through it, more than the estimated 30 Cat 6 copper cables (its maker states none).');
  // 30 is not over it
  const even = {...r, cables: r.cables.slice(0, 30)};
  assert.deepEqual(R.capacityOver(even, ctxOf(even)), []);
});

// FOUR LOADS NO RING REPORTS, each about twice the section the maker counted
// or more than its count of a thicker cable. Spread over the five rings, no
// ring is over its fill limit, so the count is the only thing that can say so.
test('40 Cat6A, eight a ring: no ring is over, and the count warns', () => {
  const r = {...rackOf(), cables: spread(8, 'cat6a')};
  // a 7.5 mm cable is 44.18 mm2; eight are 353.4 mm2, 94% of the limit
  assert.deepEqual(fills(r), [1, 2, 3, 4, 5].map(k => [`guide-${k}`, 8, 94, false]));
  assert.deepEqual(notes(r),
    ['LACER-5 (U20 front): 40 cables at least as thick as Cat 6 copper through it, more than the 30 Cat 6 copper cables its maker states.']);
});

test('65 cables of no stated kind, thirteen a ring: no ring is over, and the count warns', () => {
  const r = {...rackOf(), cables: spread(13, '')};
  // a cable of no stated kind is taken as 6 mm: thirteen are 367.6 mm2, 97% of the limit
  assert.deepEqual(fills(r), [1, 2, 3, 4, 5].map(k => [`guide-${k}`, 13, 97, false]));
  assert.deepEqual(R.capacityOver(r, ctxOf(r)), [{item: 'i2', count: 65, through: 65, capacity: 30, media: 'cat6', diameter: 6}]);
  // and a kind the kit has no diameter for is taken the same way
  const odd = {...r, cables: r.cables.map(c => ({...c, media: 'cat8'}))};
  assert.equal(R.capacityOver(odd, ctxOf(odd))[0].count, 65);
});

test('30 Cat6 and 20 Cat6A: fifty cables counted, and the count warns', () => {
  const r = {...rackOf(), cables: [...spread(6, 'cat6'), ...spread(4, 'cat6a')]};
  // a ring holds six of 28.27 mm2 and four of 44.18 mm2: 346.4 mm2, 92% of the limit
  assert.deepEqual(fills(r), [1, 2, 3, 4, 5].map(k => [`guide-${k}`, 10, 92, false]));
  assert.deepEqual(notes(r),
    ['LACER-5 (U20 front): 50 cables at least as thick as Cat 6 copper through it, more than the 30 Cat 6 copper cables its maker states.']);
});

test('31 Cat6A: the count warns', () => {
  const r = {...rackOf(), cables: [...spread(6, 'cat6a'), ...cables(1, 'cat6a', 3).map(c => ({...c, id: 'one-more', a: {...c.a, path: 'r3-more'}, b: {...c.b, path: 'r3-more'}}))]};
  // ring 3 holds seven of 44.18 mm2: 309.3 mm2, 82% of the limit; the others six, 70%
  assert.deepEqual(fills(r).map(f => f[2]), [70, 70, 82, 70, 70]);
  assert.deepEqual(R.capacityOver(r, ctxOf(r)), [{item: 'i2', count: 31, through: 31, capacity: 30, media: 'cat6', diameter: 6}]);
});

test('a thinner kind is never counted against the count, whatever it runs beside', () => {
  // 30 Cat6 and 20 fibre cords: fifty cables, thirty counted
  const under = {...rackOf(), cables: [...spread(6, 'cat6'), ...spread(4, 'os2')]};
  assert.deepEqual(R.capacityOver(under, ctxOf(under)), []);
  // 31 Cat6 and 5 fibre cords: the note says how many of how many
  const over = {...rackOf(), cables: [...cables(16, 'cat6', 1), ...cables(15, 'cat6', 5), ...cables(5, 'os2', 3)]};
  assert.deepEqual(R.capacityOver(over, ctxOf(over)), [{item: 'i2', count: 31, through: 36, capacity: 30, media: 'cat6', diameter: 6}]);
  assert.equal(notes(over).at(-1),
    'LACER-5 (U20 front): 31 of the 36 cables through it are at least as thick as Cat 6 copper, more than the 30 Cat 6 copper cables its maker states.');
  // every kind the kit gives a smaller diameter than Cat6: 3 mm fibre and AOC, 5 mm DAC
  for (const media of ['os2', 'om3', 'om4', 'om5', 'aoc', 'dac']) {
    const thin = {...rackOf(), cables: spread(8, media)};
    assert.deepEqual(R.capacityOver(thin, ctxOf(thin)), [], media);
  }
});

test('a count whose cable no source names is never compared', () => {
  const r = {...rackOf('plain'), cables: [...cables(40, 'cat6', 1), ...cables(40, 'cat6', 5)]};
  assert.deepEqual(R.capacityOver(r, ctxOf(r)), []);
  // the rings still say they are full: 40 Cat6 are 1131 mm2, 300% of the limit
  assert.deepEqual(notes(r), [
    'ring 1 on LACER-5 (U20 front): 40 cables, 300% of its fill limit; the limit is 40% of the opening.',
    'ring 5 on LACER-5 (U20 front): 40 cables, 300% of its fill limit; the limit is 40% of the opening.']);
});

test('a catalogue built before the kind was recorded does not go silent', () => {
  // no `media` key at all: the count is compared with the cables of 6 mm or more
  const copper = {...rackOf('early'), cables: spread(8, 'cat6a')};
  assert.deepEqual(R.capacityOver(copper, ctxOf(copper)), [{item: 'i2', count: 40, through: 40, capacity: 30, media: null, diameter: 6}]);
  assert.deepEqual(notes(copper), ['LACER-5 (U20 front): 40 cables of 6 mm or more through it, more than the 30 its maker states.']);
  // and the fibre cords of the issue are not counted there either
  const fibre = {...rackOf('early'), cables: [...cables(24, 'os2', 1), ...cables(24, 'os2', 5)]};
  assert.deepEqual(notes(fibre), []);
  // with thinner cables beside the copper, the note says how many of how many
  const mixed = {...rackOf('early'), cables: [...cables(16, 'cat6', 1), ...cables(15, 'cat6', 5), ...cables(5, 'os2', 3)]};
  assert.equal(notes(mixed).at(-1),
    'LACER-5 (U20 front): 31 of the 36 cables through it are of 6 mm or more, more than the 30 its maker states.');
});

test('a kind this kit has no diameter for is compared as an older catalogue is, never dropped', () => {
  // a catalogue newer than the kit may state a kind the kit does not know; a
  // value that is no kind at all is taken the same way. Only null is "never".
  for (const media of ['cat8', '', undefined, 7]) {
    SIZES.odd = {...LACER, capacity: {count: 30, basis: 'eighty of something', media}};
    try {
      // 80 Cat6, sixteen a ring: 452.4 mm2, 120% of each ring's limit
      const r = {...rackOf('odd'), cables: spread(16, 'cat6')};
      assert.deepEqual(R.capacityOver(r, ctxOf(r)), [{item: 'i2', count: 80, through: 80, capacity: 30, media: null, diameter: 6}], String(media));
      assert.equal(notes(r).at(-1), 'LACER-5 (U20 front): 80 cables of 6 mm or more through it, more than the 30 its maker states.');
    } finally { delete SIZES.odd; }
  }
});

test('a count of one is one cable', () => {
  const facts = {fill: [], over: [{item: 'i2', count: 2, through: 2, capacity: 1, media: 'cat6', diameter: 6}], routes: new Map()};
  assert.deepEqual(X.fillNotes(rackOf(), facts, () => 'LACER-5'),
    ['LACER-5 (U20 front): 2 cables at least as thick as Cat 6 copper through it, more than the 1 Cat 6 copper cable its maker states.']);
});

test('a ring over its fill is named, with its share of the limit and what the limit is', () => {
  // 60 fibre cords by ring 1: 424.1 mm2, 112% of the 377.6 mm2 limit (45% of the opening)
  const r = {...rackOf(), cables: cables(60, 'os2', 1)};
  const got = notes(r);
  assert.deepEqual(got, ['ring 1 on LACER-5 (U20 front): 60 cables, 112% of its fill limit; the limit is 40% of the opening.']);
  // the one percentage beside "of the opening" is the limit, never the fill
  assert.deepEqual(got[0].match(/\d+% of the opening/g), ['40% of the opening']);
});

test('two managers of one model give two lines: each says its U and its face', () => {
  let r = rackOf();
  r = add(r, 'lacer', 30, {face: 'rear', label: 'LACER-5'});          // i4, on the rear at U30
  const facts = {fill: [{item: 'i2', via: 'guide-1', count: 60, percent: 112, over: true},
                        {item: 'i4', via: 'guide-1', count: 60, percent: 112, over: true}],
                 over: [{item: 'i2', count: 31, through: 31, capacity: 30, media: 'cat6', diameter: 6},
                        {item: 'i4', count: 31, through: 31, capacity: 30, media: 'cat6', diameter: 6}], routes: new Map()};
  const nameOf = id => r.items.find(i => i.id === id)?.label ?? id;
  const got = X.fillNotes(r, facts, nameOf);
  assert.equal(new Set(got).size, 4, got.join('\n'));
  assert.deepEqual(got.map(t => /\((U\d+ \w+)\)/.exec(t)?.[1]), ['U20 front', 'U30 rear', 'U20 front', 'U30 rear']);
  // on a frame numbered from the top, the U is the one the device import gives it: 42 + 1 - 20
  const down = X.fillNotes({...r, frame: {...r.frame, numbering: 'top-down'}}, facts, nameOf);
  assert.match(down[0], /^ring 1 on LACER-5 \(U23 front\):/);
});

test('a manager taller than one unit is named by the unit under its top edge, from the heights the facts carry', () => {
  // a 2U duct with its bottom at 20 fills 20 and 21; counted from the top of
  // 42 units those are 23 and 22, and its position is the lower number, 22
  let r = add(M.newRack(), 'duct2', 20, {label: 'DUCT'});
  r = {...r, frame: {...r.frame, numbering: 'top-down'}};
  const facts = {fill: [{item: 'i1', via: 'duct', count: 90, percent: 120, over: true}], over: [], routes: new Map(), ctx: {chassisOf}};
  assert.deepEqual(X.fillNotes(r, facts, () => 'DUCT'),
    ['duct on DUCT (U22 front): 90 cables, 120% of its fill limit; the limit is 40% of the opening.']);
  // counted from the bottom it is the unit it stands on
  assert.match(X.fillNotes({...r, frame: {...r.frame, numbering: 'bottom-up'}}, facts, () => 'DUCT')[0], /\(U20 front\)/);
});

test('a cross-face tag names the port in words, not by its path', () => {
  const r = add(rackOf(), 'pp', 42, {label: 'FHD-1UFCE'});            // i4
  assert.equal(C.tagText(r, {item: 'i4', path: 'bay-1/module/b09', view: 'rear'}), '→ FHD-1UFCE bay 1 b09');
  assert.equal(C.tagText(r, {item: 'i1', path: 'port-63', view: 'front'}), '→ switch port 63');
  // a click on a seated optic or its plug is a click on the port
  assert.equal(C.tagText(r, {item: 'i1', path: 'port-63-occupant/tx', view: 'front'}), '→ switch port 63');
  assert.equal(C.portLabel('slot-2/module/bay-1/module/lc01'), 'slot 2 bay 1 lc01');
});

test('freePorts labels a port the way a tag names it', async () => {
  const r = add(M.newRack(), 'pp', 10, {label: 'panel'});
  const portsOf = async (item, view) => (view === 'rear' ? [{cls: 'port', path: 'bay-1/module/b09'}] : [{cls: 'port', path: 'port-2'}]);
  const got = await freePorts(r, 'i1', {portsOf});
  assert.deepEqual(got.map(p => [p.path, p.label]), [['port-2', 'port 2'], ['bay-1/module/b09', 'bay 1 b09']]);
  assert.equal(C.tagText(r, {item: 'i1', path: got[1].path, view: 'rear'}), `→ panel ${got[1].label}`);
});

test('inspect states the count as its maker does: the count, the basis and the kind', async () => {
  let r = rackOf();
  r = add(r, 'plain', 31, {label: 'LACER-5'});                         // i4
  assert.deepEqual((await inspect(r, 'i2', {chassisOf})).capacity,
    {count: 30, basis: 'Cat6 24AWG cables, theoretical', media: 'cat6'});
  assert.deepEqual((await inspect(r, 'i4', {chassisOf})).capacity,
    {count: 30, basis: 'an estimate, not stated by its maker', media: null});
  assert.ok(!('capacity' in await inspect(r, 'i1', {chassisOf})), 'a device that states no count has none');
  // an estimate says so (P-0027); a stated count carries no such key
  r = add(r, 'est', 32, {label: 'LACER-5'});                           // i5
  assert.deepEqual((await inspect(r, 'i5', {chassisOf})).capacity,
    {count: 30, basis: 'ESTIMATE, not stated by its maker', media: 'cat6', estimated: true});
});

test('the device schema takes the kinds of cable a rack file names, and no other', () => {
  // a device states the kind in the words a cable's `media` uses, so the two lists are one.
  // A capacity is a count of data cords: no maker states one in power cables or ground
  // wires, and the device schema does not take those two words (#1045). Nor does
  // it take a stack, USB or console cable: none is a data cord a switch counts.
  const schema = JSON.parse(readFileSync(new URL('../../schemas/device.schema.json', import.meta.url), 'utf8'));
  const performance = schema.properties.attrs.properties.performance;
  assert.deepEqual(performance.properties['cable-capacity-media'].enum,
    C.MEDIA.filter(m => !['power', 'ground', 'stack', 'usb', 'console'].includes(m)));
  assert.deepEqual(performance.dependentRequired['cable-capacity-media'], ['cable-capacity']);
  // an estimate is marked, and only a count of a named kind can be one (P-0027)
  assert.equal(performance.properties['cable-capacity-estimated'].type, 'boolean');
  assert.deepEqual(performance.dependentRequired['cable-capacity-estimated'], ['cable-capacity', 'cable-capacity-media']);
  // and the kit has a diameter for each, which is what the count is compared by
  for (const m of C.MEDIA) assert.ok(R.DIAMETERS[m] > 0, m);
});
