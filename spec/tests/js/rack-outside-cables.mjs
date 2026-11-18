// spec/tests/js/rack-outside-cables.mjs
// CABLES THAT LEAVE THE RACK (#1299, docs/rack-entries-design.md section 3).
// Held here are a route from a port to an exit of the product and the
// `outside` list that fill and the free-port queries read. So are the line a
// description says without `outside`, and a rack file that holds none of it.
// The four lines of the issue's "Done when" are the first four tests, in order.
// The rack is the library's AR203A frame with a patch panel and a cable
// manager, whose figures are written as rack.json carries them.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as Q from '../../../kit/rack/queries.js';
import * as CR from '../../../kit/rack/cable-rules.js';

// the row rack.json holds for the product: its entries as the product states them
const AR203A = {ref: 'apc/ar203a@1', form: '4-post-frame', ru: 44, outer: {w: 600, h: 2130, d: 747},
  enclosure: {entries: [{id: 'top', where: 'roof', kind: 'open'}]}};
// a product that is not in the library, with one entry of each kind that has a box
const MANY = {ref: 'test/many@1', form: '4-post-frame', ru: 44, outer: {w: 600, h: 2130, d: 747}, enclosure: {entries: [
  {id: 'knock', where: 'roof', kind: 'knockout', box: {x: 500, z: 600, w: 60, d: 60}},
  {id: 'far-brush', where: 'roof', kind: 'brush', box: {x: 400, z: 500, w: 100, d: 80}},
  {id: 'near-cutout', where: 'roof', kind: 'cutout', box: {x: 380, z: 100, w: 100, d: 80}}]}};
const BARE = {ref: 'test/bare@1', form: '4-post-frame', ru: 44, outer: {w: 600, h: 2130, d: 747}};
const ROWS = Object.fromEntries([AR203A, MANY, BARE].map(r => [r.ref, r]));
const frameOf = ref => (Object.hasOwn(ROWS, ref) ? ROWS[ref] : null);

const SIZES = {
  pp: {ru: 1, w: 482.6, h: 44, d: 100, model: 'PP'},
  mgr: {ru: 1, w: 430, h: 44, d: 97.7, model: 'MGR', guides: {rear: ['guide-1', 'guide-2']}},
};
const APERTURE = {w: 60, h: 30};
const GUIDES = {mgr: [{via: 'guide-1', kind: 'ring', face: 'rear', x: 150, depth: 10, aperture: APERTURE},
                      {via: 'guide-2', kind: 'ring', face: 'rear', x: 200, depth: 10, aperture: APERTURE}]};
const PORT_X = {'rear-1': 100, 'rear-2': 110};
const refOf = rack => Object.fromEntries(rack.items.map(i => [i.id, i.ref]));
const ctxFor = (rack, extra = {}) => {
  const refs = refOf(rack);
  return {chassisOf: ref => SIZES[ref] || null, frameOf, guidesOf: id => GUIDES[refs[id]] || [],
    portX: e => PORT_X[e.path] ?? 0, ...extra};
};

function build(ref = 'apc/ar203a@1') {
  let r = M.newRack();
  r = {...r, frame: M.normalizeFrame({...r.frame, heightRU: 44, railDepth: 740, usableDepth: 740, ref})};
  r = M.withItem(r, {ref: 'pp', cfg: 'x', ru: 30, label: 'pp-1'}).rack;
  r = M.withItem(r, {ref: 'mgr', cfg: 'x', ru: 31, face: 'rear', label: 'mgr-1'}).rack;
  return r;
}
const REAR_1 = {item: 'i1', path: 'rear-1', view: 'rear'};
const outside = (exit = 'top', near = REAR_1, extra = {}) =>
  ({id: 'run-17', a: near, b: {exit}, media: 'cat6a', purpose: 'Riser', label: 'R17', route: [], ...extra});

// ── the four lines of "Done when" ────────────────────────────────────────

test('1. a cable from a patch panel\'s rear port to the top exit has an in-rack route and length', () => {
  const rack = build(), ctx = ctxFor(rack);
  const got = R.routeToExit(rack, outside('top'), ctx);
  assert.equal(got.reason, null);
  assert.equal(typeof got.inRack, 'number');
  assert.ok(got.inRack > 0);
  assert.equal(got.exit, 'top');
  assert.ok(got.waypoints.length >= 2, 'the route names its waypoints');
  assert.deepEqual(got.passes.map(p => `${p.item}|${p.via}`), ['i2|guide-1', 'i2|guide-2'].slice(0, got.passes.length));
  assert.ok(got.passes.length >= 1, 'it passes a ring of the manager');
  // {exit: any} takes the one open entry and says which
  const any = R.routeToExit(rack, outside('any'), ctx);
  assert.equal(any.exit, 'top');
  assert.equal(any.inRack, got.inRack);
  // the route ends on the roof's plane, over the envelope's plan, nearest the last waypoint
  assert.equal(got.at.y, 1955.8);
  assert.ok(got.at.x >= -300 && got.at.x <= 300 && got.at.z <= 0 && got.at.z >= -747);
  // the length is the route of the points: the port to the entry, and no lead out through it
  assert.ok(got.inRack >= got.at.y - 30 * 44.45,'it rises from U30 to the roof plane at least');
});

test('2. a manager\'s fill counts the outside cable that passes through it, once, by its media diameter', () => {
  const rack = build(), plain = ctxFor(rack);
  const none = R.fill(rack, plain);
  assert.deepEqual(none, [], 'with no outside, no ring is filled');
  const oc = outside('top');
  const withIt = R.fill(rack, ctxFor(rack, {outside: [oc]}));
  const first = R.routeToExit(rack, oc, plain).passes[0];
  const row = withIt.find(e => e.item === first.item && e.via === first.via);
  assert.ok(row, 'the ring the route passes is counted');
  assert.equal(row.count, 1);
  assert.deepEqual(row.cables, ['run-17']);
  const area = Math.PI * (R.DIAMETERS.cat6a / 2) ** 2;
  assert.equal(row.percent, Math.round(area / (R.FILL_LIMIT * APERTURE.w * APERTURE.h) * 100));
  // two outside cables are two areas; a cable that names the same ring twice is one
  const twice = R.fill(rack, ctxFor(rack, {outside: [oc, {...oc, id: 'run-18'}]})).find(e => e.via === first.via);
  assert.equal(twice.count, 2);
  assert.equal(twice.percent, Math.round(2 * area / (R.FILL_LIMIT * APERTURE.w * APERTURE.h) * 100));
  // the empty list adds nothing
  assert.deepEqual(R.fill(rack, ctxFor(rack, {outside: []})), none);
});

test('3. a rear port whose cable is stored outside reads taken when passed in, and free when it is not', async () => {
  const rack = build();
  const portsOf = async (item, view) => (item.ref === 'pp' && view === 'rear'
    ? [{path: 'rear-1', cls: 'port', media: 'copper'}, {path: 'rear-2', cls: 'port', media: 'copper'}] : []);
  const base = {chassisOf: ref => SIZES[ref] || null, portsOf};
  const free = async extra => (await Q.freePorts(rack, 'i1', {...base, ...extra})).map(p => p.path);
  assert.deepEqual(await free({}), ['rear-1', 'rear-2'], 'not passed in: the port reads free');
  assert.deepEqual(await free({outside: [outside('top')]}), ['rear-2'], 'passed in: the port is taken');
  assert.deepEqual(await free({outside: []}), await free({}), 'an empty list equals absent in the port result');
  const taken = CR.portFree(rack, REAR_1, {outside: [outside('top')]});
  assert.equal(taken.ok, false);
  assert.match(taken.reason, /already has a cable \(R17\)/);
  assert.equal(CR.portFree(rack, REAR_1, {}).ok, true);
  assert.equal(CR.portFree(rack, REAR_1, {outside: []}).ok, true);
  // the cable's own id is let through where the caller says it is the one being moved
  assert.equal(CR.portFree(rack, REAR_1, {outside: [outside('top')], ignoreId: 'run-17'}).ok, true);
  // a port is taken whichever end of the outside cable it is written on
  const flipped = {...outside('top'), a: {exit: 'top'}, b: REAR_1};
  assert.equal(CR.portFree(rack, REAR_1, {outside: [flipped]}).ok, false);
});

test('4. the rack file is byte-identical with and without outside, before and after the queries', async () => {
  const rack = build();
  const before = M.serialize(rack);
  const oc = outside('any');
  const ocBefore = JSON.stringify(oc);
  const ctxs = [ctxFor(rack), ctxFor(rack, {outside: []}), ctxFor(rack, {outside: [oc]})];
  for (const ctx of ctxs) {
    R.routeToExit(rack, oc, ctx);
    R.fill(rack, ctx);
    Q.describe(rack, {...ctx, route: ctx});
    await Q.freePorts(rack, 'i1', {...ctx, portsOf: async () => []});
    assert.equal(M.serialize(rack), before);
  }
  assert.equal(JSON.stringify(rack.cables), '[]', 'the cable is never added to the rack');
  assert.equal(JSON.stringify(oc), ocBefore, 'and the caller\'s cable is not written to either');
  assert.equal(M.serialize(build()), before);
});

// ── no length, and a sentence saying why ─────────────────────────────────

test('inRack is null with one sentence for each reason, and nothing is estimated', () => {
  const rack = build();
  const reasons = [
    ['the product declares no entry', build('test/bare@1'), outside('top'), /declares no entry/],
    ['the named id is not in the product', rack, outside('side'), /no entry side/],
    ['the rack has no product ref', build(null), outside('top'), /no product ref/],
    ['the port is not on a device', rack, outside('top', {item: 'gone', path: 'rear-1', view: 'rear'}), /not on a device/],
  ];
  for (const [what, r, c, re] of reasons) {
    const got = R.routeToExit(r, c, ctxFor(r));
    assert.equal(got.inRack, null, what);
    assert.match(got.reason, re, what);
    assert.equal(got.reason.split('. ').length, 1, `${what}: one sentence`);
    assert.deepEqual(got.waypoints, [], what);
    assert.equal(got.at, null, what);
  }
  // a product the catalogue does not have, and a context with no catalogue at all
  const lost = build('test/lost@1');
  assert.equal(R.routeToExit(lost, outside('top'), ctxFor(lost)).inRack, null);
  assert.equal(R.routeToExit(rack, outside('top'), {...ctxFor(rack), frameOf: undefined}).inRack, null);
  // a product that states entries and no outer cannot place an open one
  const rowless = {...AR203A, ref: 'test/no-outer@1', outer: undefined};
  ROWS[rowless.ref] = rowless;
  const r2 = build('test/no-outer@1');
  assert.equal(R.routeToExit(r2, outside('top'), ctxFor(r2)).inRack, null);
});

test('a rack with no product ref answers inRack null, and queries still work', async () => {
  const rack = build(null);
  assert.equal(rack.frame.ref, null);
  const got = R.routeToExit(rack, outside('any'), ctxFor(rack));
  assert.equal(got.inRack, null);
  assert.match(got.reason, /no product ref/);
  assert.equal(R.fill(rack, ctxFor(rack, {outside: [outside('any')]})).length, 0, 'a cable with no length counts nowhere');
});

// ── which entry any takes ────────────────────────────────────────────────

test('{exit: any} takes the nearest brush, cutout or open entry and skips a knockout; a named knockout is taken', () => {
  const rack = build('test/many@1'), ctx = ctxFor(rack);
  const any = R.routeToExit(rack, outside('any'), ctx);
  // the knockout is the nearest to the port, the cutout the nearest of the rest
  const knock = R.routeToExit(rack, outside('knock'), ctx), cut = R.routeToExit(rack, outside('near-cutout'), ctx),
    brush = R.routeToExit(rack, outside('far-brush'), ctx);
  assert.equal(knock.exit, 'knock');
  assert.equal(typeof knock.inRack, 'number');
  assert.ok(knock.inRack < cut.inRack, 'the knockout is nearer than the cutout');
  assert.equal(any.exit, cut.inRack <= brush.inRack ? 'near-cutout' : 'far-brush');
  assert.equal(any.inRack, Math.min(cut.inRack, brush.inRack));
  assert.notEqual(any.exit, 'knock');
  // the point of the entry's box nearest the last waypoint, on the plane of the roof
  assert.equal(any.at.y, 1955.8);
  const box = ROWS['test/many@1'].enclosure.entries.find(e => e.id === any.exit).box;
  assert.ok(any.at.x >= box.x - 300 && any.at.x <= box.x - 300 + box.w);
  assert.ok(any.at.z <= -box.z && any.at.z >= -(box.z + box.d));
});

test('{exit: any} with only a knockout in the product answers null with a sentence', () => {
  ROWS['test/knock-only@1'] = {...MANY, ref: 'test/knock-only@1', enclosure: {entries: [MANY.enclosure.entries[0]]}};
  const rack = build('test/knock-only@1');
  const got = R.routeToExit(rack, outside('any'), ctxFor(rack));
  assert.equal(got.inRack, null);
  assert.match(got.reason, /brush, cutout or open/);
});

test('an outside cable with a length keeps it for the caller: the in-rack figure does not use it', () => {
  const rack = build(), ctx = ctxFor(rack);
  const plain = R.routeToExit(rack, outside('top'), ctx);
  const held = R.routeToExit(rack, outside('top', REAR_1, {length: {value: 40, unit: 'm', source: 'entered'}}), ctx);
  assert.equal(held.inRack, plain.inRack);
});

// ── the line a description says ──────────────────────────────────────────

const LINE = 'Cables stored outside the rack are not passed in, and the ports they use read free.';

test('the description ends with one line when outside is absent, and has none when it is given', () => {
  const rack = build(), ctx = ctxFor(rack);
  const absent = Q.describe(rack, ctx);
  assert.equal(absent.split('\n').at(-1), LINE);
  assert.equal(absent.split('\n').filter(l => l === LINE).length, 1);
  const empty = Q.describe(rack, {...ctx, outside: []});
  const given = Q.describe(rack, {...ctx, outside: [outside('top')]});
  assert.equal(empty.split('\n').includes(LINE), false);
  assert.equal(given.split('\n').includes(LINE), false);
  assert.equal(`${empty}\n${LINE}`, absent, 'only the last line differs');
  assert.equal(empty, given);
  // a window says it too, and an error does not
  const win = Q.describe(rack, ctx, {section: 'items', limit: 1});
  assert.equal(win.split('\n').at(-1), LINE);
  assert.deepEqual(Q.describe(rack, ctx, {section: 'nope'}), {error: 'There is no section nope. Ask for items, zeroU, cables or bundles, or leave it out for all of them.'});
});

test('outside absent is not outside empty: only the description tells them apart', async () => {
  const rack = build();
  const portsOf = async (item, view) => (item.ref === 'pp' && view === 'rear' ? [{path: 'rear-1', cls: 'port'}] : []);
  const ports = async extra => await Q.freePorts(rack, 'i1', {chassisOf: ref => SIZES[ref], portsOf, ...extra});
  assert.deepEqual(await ports({outside: []}), await ports({}));
  assert.notEqual(Q.describe(rack, ctxFor(rack, {outside: []})), Q.describe(rack, ctxFor(rack)));
});
