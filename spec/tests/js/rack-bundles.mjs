// spec/tests/js/rack-bundles.mjs
// Cable bundles (#921, docs/cable-bundles-design.md): the record and its
// repairs, the trunk worked out from the members' routes, a member's route
// along it, the commands, the size check and the straps.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as B from '../../../kit/rack/bundles.js';
import {apply, COMMANDS, BUNDLE_GONE, CABLE_GONE} from '../../../kit/rack/commands.js';
import {describe, inspect, selectCables} from '../../../kit/rack/queries.js';
import {createRackEditor} from '../../../kit/rack/editor.js';
import {fillNotes} from '../../../kit/rack/export-data.js';
import {validate} from '../../../kit/rack/validate.js';
import {RU} from '../../../kit/rack/rails.js';
import {withCable, withoutCable, withoutCablesOf} from '../../../kit/rack/cable-rules.js';

const SCHEMA = JSON.parse(readFileSync(new URL('../../schemas/rack.schema.json', import.meta.url)));
const RINGS = ['guide-1', 'guide-2', 'guide-3', 'guide-4', 'guide-5'];
const SIZES = {sw: {ru: 1, d: 515, model: 'SW'}, pp: {ru: 1, d: 100, model: 'PP'},
  mgr: {ru: 1, d: 110, mount: 'rack-face', model: 'MGR', guides: {front: RINGS}, default: 'x'},
  duct: {ru: 0, mount: 'rack-side', h: 2000, w: 140, d: 165, guides: {front: ['duct']}, model: 'DUCT'}};
const chassisOf = ref => SIZES[ref] || null;
// FS's D-ring opening, 32.0 x 29.5 mm, on ring 1 of every manager.
const ringsOf = (it, gx = {}) => RINGS.map((via, i) => ({via, kind: 'ring', face: it.face, x: gx[via] ?? -205 + i * 102.5,
  box: {x: 0, y: 0, w: 40, h: 30}, aperture: via === 'guide-1' ? {w: 32, h: 29.5} : null}));
const routeCtx = (rack, extra = {}) => ({chassisOf,
  guidesOf: id => { const it = rack.items.find(i => i.id === id); return it?.ref === 'mgr' ? ringsOf(it, extra.gx) : []; },
  portX: () => -150, ...extra});

const end = (item, path) => ({item, path, view: 'front'});
const RT = (...ws) => ws.map(w => (Array.isArray(w) ? {lane: w[0], ru: w[1]} : {item: w.split(':')[0], via: w.split(':')[1]}));
// A switch at U10 with a manager on it (i2), a patch panel at U30 with one (i4).
// Each cable runs out of the switch through the manager's rings, up the
// left-front lane and in through the panel's manager, as its own route by hand.
function rackWith(routes, media = 'cat6') {
  let r = M.newRack({name: 'Rack 1'});
  r = M.withItem(r, {ref: 'sw', cfg: 'x', ru: 10, label: 'sw-1'}).rack;
  r = M.withItem(r, {ref: 'mgr', cfg: 'x', ru: 10, label: 'mgr-1', on: 'i1', unit: 1}).rack;
  r = M.withItem(r, {ref: 'pp', cfg: 'x', ru: 30, label: 'pp-1'}).rack;
  r = M.withItem(r, {ref: 'mgr', cfg: 'x', ru: 30, label: 'mgr-2', on: 'i3', unit: 1}).rack;
  routes.forEach((route, k) => {
    r = withCable(r, {a: end('i1', `p${k + 1}`), b: end('i3', `q${k + 1}`), media: Array.isArray(media) ? media[k] : media}).rack;
    r = {...r, cables: r.cables.map(c => (c.id === `c${k + 1}` ? {...c, route, routeEdited: true} : c))};
  });
  return r;
}
const UP = RT('i2:guide-2', 'i2:guide-1', ['left-front', 10], ['left-front', 30], 'i4:guide-1', 'i4:guide-2');
const UP1 = RT('i2:guide-1', ['left-front', 10], ['left-front', 30], 'i4:guide-1');
const TRUNK = RT('i2:guide-1', ['left-front', 10], ['left-front', 30], 'i4:guide-1');
const run = (rack, cmds, ctx = {}) => apply(rack, cmds, {chassisOf, ...ctx});
// ctx.bendOf for a rack of Cat 6 only: 4 x 6 mm installed (#919)
const CAT6 = () => 24;

// ── the record ───────────────────────────────────────────────────────────

test('the rack file is version 3, and a version-2 file opens as it was', () => {
  assert.equal(M.VERSION, 3);
  assert.equal(M.newDoc().version, 3);
  const v2 = {format: 'portrayal-rack', version: 2, id: 'd', racks: [{id: 'r1', name: 'A', frame: {}, items: [], zeroU: [], cables: []}]};
  const d = M.parseDoc(v2);
  assert.equal(d.version, 3);
  assert.equal('bundles' in d.racks[0], false);          // a rack never given a bundle saves as it was
  assert.throws(() => M.parseDoc({...v2, version: 4}), /version 4; this page reads up to version 3/);
});

test('a rack with bundles reads back whole and validates; the schema refuses a malformed bundle', () => {
  let r = rackWith([UP, UP]);
  r = run(r, {op: 'bundle.create', cables: ['c1', 'c2'], route: TRUNK, label: 'uplinks', straps: {every: {value: 300, unit: 'mm'}}}).rack;
  r = run(r, {op: 'bundle.peel', id: 'b1', cable: 'c2', at: {lane: 'left-front', ru: 20}, end: 'b'}).rack;
  const doc = {...M.newDoc(), racks: [r]};
  const text = M.serialize(doc);
  assert.deepEqual(M.parseDoc(text).racks[0], r);
  assert.deepEqual(validate(SCHEMA, JSON.parse(text)), []);
  assert.equal(SCHEMA.$id, 'https://portrayal.dev/schemas/v2/rack.schema.json');
  const bad = JSON.parse(text);
  bad.racks[0].bundles[0].number = 0;
  bad.racks[0].bundles[0].straps = {every: {value: 12, unit: 'cm'}};
  bad.racks[0].bundles[0].members.push({b: {lane: 'left-front', ru: 3}});
  const errs = validate(SCHEMA, bad).map(e => `${e.keyword} ${e.path.join('/')}`);
  assert.ok(errs.includes('minimum racks/0/bundles/0/number'), errs);
  assert.ok(errs.includes('enum racks/0/bundles/0/straps/every/unit'), errs);
  assert.ok(errs.includes('required racks/0/bundles/0/members/2'), errs);
});

test('parseDoc reads the shapes: ids, numbers, members and a trunk it cannot read', () => {
  const r = rackWith([UP, UP, UP]);
  const raw = {...M.newDoc(), racks: [{...r, bundles: [
    {number: 2, members: [{cable: 'c1'}, 'c2', {cable: 7}], route: TRUNK, straps: {every: {value: -1, unit: 'in'}}, note: 'kept'},
    {id: 'b9', number: 'two', label: 7, members: [{cable: 'c2'}], route: [...TRUNK, 'junk']},
    {id: 'b9', number: 5, members: [{cable: 'c3'}], route: [], straps: {every: null}},
    'junk']}]};
  const [a, b, c, ...rest] = M.parseDoc(raw).racks[0].bundles;
  assert.equal(rest.length, 0);                                    // not an object: no bundle
  assert.deepEqual([a.id, b.id, c.id], ['b10', 'b9', 'b11']);         // none, kept, repeated
  assert.deepEqual([a.number, b.number, c.number], [2, 6, 5]);      // 'two' goes past the highest
  assert.deepEqual(a.members, [{cable: 'c1'}]);
  assert.equal(a.note, 'kept');
  assert.equal('straps' in a, false);                                // an unusable spacing is the default
  assert.deepEqual(c.straps, {every: null});
  assert.equal(b.label, '7');
  assert.deepEqual(b.route, TRUNK);
  assert.deepEqual(b.routeAsWritten.at(-1), 'junk');
});

test('settleBundles repairs the references, naming the rack, and a second read says nothing', () => {
  let r = rackWith([UP, UP, UP]);
  r = M.withItem(r, {ref: 'sw', cfg: 'x', ru: 40, label: 'b3'}).rack;
  r = {...r, items: r.items.map(i => (i.label === 'b3' ? {...i, id: 'b3'} : i))};
  const doc = {...M.newDoc(), racks: [{...r, name: 'Rack 2', bundles: [
    {id: 'b1', number: 1, label: '', members: [{cable: 'c1'}, {cable: 'c9'}, {cable: 'c1'}], route: TRUNK},
    {id: 'b3', number: 1, label: 'spine', members: [{cable: 'c1'}, {cable: 'c2'}], route: TRUNK}]}]};
  const notes = [];
  const back = M.parseDoc(doc, {notes});
  assert.deepEqual(notes, [
    'Rack 2: Bundle 1 named c9, which is not a cable in the rack, so it was taken out.',
    'Rack 2: Bundle 1 named c1 twice; it is kept once.',
    'Rack 2: b3 is also the id of a device, a part or a cable, so spine is now b4.',
    'Rack 2: c1 is in Bundle 1 and spine, so it stays in Bundle 1.',
    'Rack 2: b1 and b4 were both Bundle 1, so b4 is now Bundle 2.']);
  const bs = back.racks[0].bundles;
  assert.deepEqual(bs.map(b => [b.id, b.number, b.members.map(m => m.cable)]), [['b1', 1, ['c1']], ['b4', 2, ['c2']]]);
  // Idempotent: what was written reads back with nothing to repair.
  const again = [];
  assert.deepEqual(M.parseDoc(M.serialize(back), {notes: again}).racks[0], back.racks[0]);
  assert.deepEqual(again, []);
  assert.deepEqual(M.settleBundles(back.racks[0]).notes, []);
  assert.equal(M.settleBundles(back.racks[0]).rack, back.racks[0]);
});

test('ids a bundle names are not handed out again', () => {
  let r = rackWith([UP, UP]);
  r = run(r, {op: 'bundle.create', cables: ['c1', 'c2'], route: TRUNK}).rack;
  // c2 removed by hand from the cables but still named: the next cable is c3
  const named = {...r, cables: r.cables.filter(c => c.id !== 'c2')};
  assert.equal(withCable(named, {a: end('i1', 'z1'), b: end('i3', 'z2')}).cable.id, 'c3');
  assert.deepEqual(M.cableIdsInUse(named).map(x => x.id), ['c1', 'c1', 'c2']);
  // the managers the trunk passes: removed, their ids stay taken
  const bare = {...r, items: r.items.filter(i => i.id !== 'i4')};
  assert.equal(M.withItem(bare, {ref: 'sw', ru: 40}).item.id, 'i5');
  // and the loader's repairs count them as written
  const raw = {...M.newDoc(), racks: [{...bare, items: [...bare.items, {ref: 'sw', ru: 40}],
    cables: [...r.cables, {a: end('i1', 'k'), b: end('i3', 'k')}]}]};
  const back = M.parseDoc(raw).racks[0];
  assert.equal(back.items.at(-1).id, 'i5');
  assert.equal(back.cables.at(-1).id, 'c3');
});

// ── the trunk ────────────────────────────────────────────────────────────

test('bundle.create works the trunk out from where the cables run together', () => {
  const r = rackWith([UP, UP1, UP]);
  const rc = routeCtx(r);
  const res = run(r, {op: 'bundle.create', cables: ['c1', 'c2', 'c3']}, {route: rc});
  assert.ok(!res.error, res.error);
  assert.equal(res.summary, 'Bundled 3 cables as Bundle 1.');
  assert.deepEqual(res.created.ids, ['b1']);
  const b = res.rack.bundles[0];
  // c1 and c3 share ring 2 as well: shared by two, so it is on the trunk
  assert.deepEqual(b.route, RT('i2:guide-2', 'i2:guide-1', ['left-front', 10], ['left-front', 30], 'i4:guide-1', 'i4:guide-2'));
  assert.deepEqual(b.members, [{cable: 'c1'}, {cable: 'c2'}, {cable: 'c3'}]);
  assert.equal(b.number, 1);
  // Lane runs that overlap in part share the overlap: one from U10, one from U14.
  const lanes = rackWith([RT(['left-front', 10], ['left-front', 30]), RT(['left-front', 14], ['left-front', 30], 'i4:guide-1')]);
  assert.deepEqual(run(lanes, {op: 'bundle.create', cables: ['c1', 'c2']}, {route: routeCtx(lanes)}).rack.bundles[0].route,
    RT(['left-front', 14], ['left-front', 30]));
  // It runs the way the first cable named runs.
  const down = rackWith([[...UP].reverse(), UP]);
  assert.deepEqual(run(down, {op: 'bundle.create', cables: ['c1', 'c2']}, {route: routeCtx(down)}).rack.bundles[0].route, [...UP].reverse());
});

test('bundle.create refuses a shape that is not one run, naming the cables', () => {
  const refused = (routes, cables) => {
    const r = rackWith(routes);
    return run(r, {op: 'bundle.create', cables}, {route: routeCtx(r)}).error;
  };
  // a detour: c1 leaves at ring 3 and meets the others again on the lane
  const via345 = RT('i2:guide-3', 'i2:guide-4', 'i2:guide-5', ['left-front', 20], ['left-front', 30]);
  const via3x5 = RT('i2:guide-3', 'i2:guide-2', 'i2:guide-5', ['left-front', 20], ['left-front', 30]);
  assert.equal(refused([via3x5, via345, via345], ['c1', 'c2', 'c3']),
    'c1 parts from c2 and c3 at mgr-1 ring 3 and meets them again at mgr-1 ring 5. Bundle them separately, or give the bundle a route.');
  // a loop: c4 goes from ring 3 straight to the lane; blamed whichever is named first
  const direct = RT('i2:guide-3', ['left-front', 20], ['left-front', 30]);
  const loop = 'c4 parts from c1, c2 and c3 at mgr-1 ring 3 and meets them again at left-front U20. Bundle them separately, or give the bundle a route.';
  assert.equal(refused([via345, via345, via345, direct], ['c1', 'c2', 'c3', 'c4']), loop);
  assert.equal(refused([via345, via345, via345, direct], ['c4', 'c1', 'c2', 'c3']), loop);
  // a fork after the lane
  const toPanel = RT(['left-front', 10], ['left-front', 30], 'i4:guide-1');
  const toRear = RT(['left-front', 10], ['left-front', 30], ['left-rear', 30]);
  assert.equal(refused([toPanel, toPanel, toRear, toRear], ['c1', 'c2', 'c3', 'c4']),
    'Bundle members part after left-front U30: c1 and c2 go on to mgr-2 ring 1; c3 and c4 go on to left-rear U30. Bundle them separately, or give the bundle a route.');
  // two groups that share nothing
  const low = RT('i2:guide-5'), high = RT('i4:guide-5');
  assert.equal(refused([low, low, high, high], ['c1', 'c2', 'c3', 'c4']),
    'c1 and c2 share mgr-1 ring 5, and c3 and c4 share mgr-2 ring 5, but the two groups share nothing. Bundle them separately, or give the bundle a route.');
  // one cable that runs with none of the others
  assert.equal(refused([UP, UP, RT(['right-front', 3])], ['c1', 'c2', 'c3']),
    'c3 runs with none of the others. Leave it out, or give the bundle a route.');
  // fan-in at a lacer's successive rings is one run
  const r = rackWith([RT('i2:guide-3', 'i2:guide-2', 'i2:guide-1', ['left-front', 10]), RT('i2:guide-2', 'i2:guide-1', ['left-front', 10]),
                      RT('i2:guide-1', ['left-front', 10])]);
  assert.deepEqual(run(r, {op: 'bundle.create', cables: ['c1', 'c2', 'c3']}, {route: routeCtx(r)}).rack.bundles[0].route,
    RT('i2:guide-2', 'i2:guide-1', ['left-front', 10]));
});

test('bundle.create refuses what it cannot make, and makes what it is given without the routes', () => {
  const r = rackWith([UP, UP, UP]);
  assert.equal(run(r, {op: 'bundle.create', cables: ['c1', 'c2']}).error, "The cables' routes are not known here, so the bundle needs a route.");
  assert.equal(run(r, {op: 'bundle.create', cables: ['c1', 'c9'], route: TRUNK}).error, CABLE_GONE);
  assert.equal(run(r, {op: 'bundle.create', cables: ['c1', 'c1'], route: TRUNK}).error, 'c1 is named twice.');
  assert.equal(run(r, {op: 'bundle.create', cables: ['c1']}).error, 'bundle.create needs cables to list at least 2.');
  const made = run(r, {op: 'bundle.create', cables: ['c1', 'c2'], route: TRUNK, number: 4});
  assert.deepEqual(made.findings, [{kind: 'note', text: 'Bundle 4 is not checked for size or bend: the routes are not known here.'}]);
  assert.equal(run(made.rack, {op: 'bundle.create', cables: ['c2', 'c3'], route: TRUNK}).error, 'c2 is already in Bundle 4. Peel it off first.');
  const r3 = rackWith([UP, UP, UP, UP]);
  const two = run(r3, {op: 'bundle.create', cables: ['c1', 'c2'], route: TRUNK, number: 4}).rack;
  assert.equal(run(two, {op: 'bundle.create', cables: ['c3', 'c4'], route: TRUNK, number: 4}).error, "Bundle 4 is already b1's number.");
  // the next number is past the highest in use
  assert.equal(run(two, {op: 'bundle.create', cables: ['c3', 'c4'], route: TRUNK}).rack.bundles[1].number, 5);
  // a route by hand is checked as cable.route checks one
  assert.equal(run(r, {op: 'bundle.create', cables: ['c1', 'c2'], route: RT('i2:guide-9')}).error,
    'Waypoint 1: mgr-1 has no ring, duct, pass-through or tray called guide-9. It has: guide-1, guide-2, guide-3, guide-4, guide-5.');
  assert.equal(run(r, {op: 'bundle.create', cables: ['c1', 'c2'], route: RT('i2:guide-9')}, {route: routeCtx(r)}).error,
    'Waypoint 1: mgr-1 has no ring, duct, pass-through or tray called guide-9. It has: guide-1, guide-2, guide-3, guide-4, guide-5.');
  assert.equal(run(r, {op: 'bundle.create', cables: ['c1', 'c2'], route: []}).error, "A bundle's route needs at least one waypoint.");
});

// ── a member's route ─────────────────────────────────────────────────────

test('a member follows its own route to the trunk, the trunk, then its own route on', () => {
  // c3 comes in through ring 3 and goes on past the panel's ring 1 to ring 3
  const c3 = RT('i2:guide-3', 'i2:guide-2', 'i2:guide-1', ['left-front', 10], ['left-front', 30], 'i4:guide-1', 'i4:guide-3');
  let r = rackWith([UP, UP, c3]);
  r = run(r, {op: 'bundle.create', cables: ['c1', 'c2', 'c3'], route: TRUNK}).rack;
  const rc = routeCtx(r);
  const got = R.resolveRoute(r, r.cables[2], rc);
  assert.deepEqual(got.waypoints, c3);
  assert.deepEqual([got.bundle, got.join, got.leave], ['b1', TRUNK[0], TRUNK.at(-1)]);
  // peeled at U20 for its b end: off the trunk there, then to the next waypoint
  // of its own that is not on the trunk
  r = run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 20}, end: 'b'}).rack;
  const peeled = R.resolveRoute(r, r.cables[2], rc);
  assert.deepEqual(peeled.waypoints, RT('i2:guide-3', 'i2:guide-2', 'i2:guide-1', ['left-front', 10], ['left-front', 20], 'i4:guide-3'));
  assert.deepEqual(peeled.leave, {lane: 'left-front', ru: 20});
  // a cable in no bundle, and a bundle of one, follow their own routes
  const lone = run(r, {op: 'bundle.peel', id: 'b1', cable: 'c1'}).rack;
  assert.equal(R.resolveRoute(lone, lone.cables[0], rc).bundle, undefined);
  const one = run(run(lone, {op: 'bundle.peel', id: 'b1', cable: 'c2'}).rack, {op: 'bundle.peel', id: 'b1', cable: 'c3'});
  assert.equal(one.findings.at(-1).text, 'Bundle 1 now holds no cables.');
  assert.equal(one.rack.bundles.length, 1);
});

test('a member whose route never meets the trunk rides all of it, and its length follows the bundle', () => {
  const away = RT(['right-front', 10], ['right-front', 30]);
  let r = rackWith([UP, UP, away]);
  const rc = routeCtx(r);
  const before = R.routedLength(r, r.cables[2], rc).measured;
  const made = run(r, [{op: 'bundle.create', cables: ['c1', 'c2'], route: TRUNK}, {op: 'bundle.add', id: 'b1', cables: ['c3']}], {route: rc});
  assert.ok(!made.error, made.error);
  assert.ok(made.findings.some(f => f.text === 'c3 does not meet Bundle 1\'s route, so it runs straight to it and rides all of it.'), made.findings);
  r = made.rack;
  const got = R.resolveRoute(r, r.cables[2], rc);
  assert.deepEqual(got.waypoints, TRUNK);
  assert.ok(R.routedLength(r, r.cables[2], rc).measured !== before);
});

// ── the commands ─────────────────────────────────────────────────────────

test('bundle.add, bundle.peel, bundle.update and bundle.remove, each one undo step', () => {
  const r0 = rackWith([UP, UP, UP, UP]);
  const doc = {...M.newDoc(), racks: [r0]};
  const ed = createRackEditor({doc, chassisOf});
  assert.ok(!ed.apply({op: 'bundle.create', cables: ['c1', 'c2'], route: TRUNK}).error);
  assert.equal(ed.apply({op: 'bundle.add', id: 'b1', cables: ['c3']}).summary, 'Added c3 to Bundle 1.');
  assert.equal(ed.apply({op: 'bundle.add', id: 'b1', cables: ['c3']}).noop, true);   // already in, no peel points: nothing changes
  assert.equal(ed.apply({op: 'bundle.add', id: 'b9', cables: ['c3']}).error, BUNDLE_GONE);
  assert.equal(ed.apply({op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 20}, end: 'b'}).summary,
    'c3 leaves Bundle 1 at left-front U20 for its b end.');
  assert.equal(ed.apply({op: 'bundle.add', id: 'b1', cables: ['c3']}).summary, 'c3 rides the whole of Bundle 1 again.');
  assert.deepEqual(ed.rack().bundles[0].members.at(-1), {cable: 'c3'});
  const make2 = ed.apply({op: 'bundle.create', cables: ['c4', 'c3'], route: TRUNK});
  assert.equal(make2.error, 'c3 is already in Bundle 1. Peel it off first.');
  assert.equal(ed.apply({op: 'bundle.update', id: 'b1', label: 'uplinks'}).summary, 'Renamed Bundle 1 to uplinks.');
  assert.equal(ed.apply({op: 'bundle.update', id: 'b1', label: 'uplinks'}).noop, true);
  const spaced = ed.apply({op: 'bundle.update', id: 'b1', straps: {every: {value: 1, unit: 'in'}}});
  assert.equal(spaced.summary, 'uplinks now has straps every 1 in.');
  assert.equal(spaced.findings[0].text, 'Straps every 1 in is under 50 mm apart; check the unit.');
  assert.equal(ed.apply({op: 'bundle.update', id: 'b1', straps: {every: {value: 2, unit: 'mm'}}}).findings[0].text.includes('under 50 mm'), true);
  assert.equal(ed.apply({op: 'bundle.update', id: 'b1', straps: {every: {value: 48, unit: 'in'}}}).findings[0].text, 'Straps every 48 in is over 1 m apart; check the unit.');
  assert.equal(ed.apply({op: 'bundle.update', id: 'b1', straps: {every: null}}).summary, 'uplinks now has no straps.');
  assert.equal(ed.apply({op: 'bundle.update', id: 'b1', straps: {every: {value: 'x', unit: 'in'}}}).error, 'bundle.update needs straps.every.value, a number above 0.');
  assert.equal(ed.apply({op: 'bundle.update', id: 'b1', number: 0}).error, 'bundle.update needs number, a whole number from 1.');
  assert.equal(ed.apply({op: 'bundle.update', id: 'b1', route: null}).error, "The cables' routes are not known here, so the bundle needs a route.");
  assert.equal(ed.undoSummary, 'uplinks now has no straps.');
  ed.undo();
  assert.deepEqual(ed.rack().bundles[0].straps, {every: {value: 48, unit: 'in'}});
  const gone = ed.apply({op: 'bundle.remove', id: 'b1'});
  assert.equal(gone.summary, 'Dissolved uplinks; its 3 cables follow their own routes again.');
  assert.deepEqual(ed.rack().bundles, []);
  assert.equal(ed.rack().cables.length, 4);
  ed.undo();
  assert.equal(ed.rack().bundles.length, 1);
});

test('bundle.peel: at must be on the trunk, and an end is needed without the routes', () => {
  let r = run(rackWith([UP, UP, UP]), {op: 'bundle.create', cables: ['c1', 'c2', 'c3'], route: TRUNK}).rack;
  assert.equal(run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 34}, end: 'b'}).error,
    "left-front U34 is not on Bundle 1's route, which runs mgr-1 ring 1 > left-front U10-U30 > mgr-2 ring 1.");
  assert.equal(run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {item: 'i2', via: 'guide-2'}, end: 'b'}).error,
    "mgr-1 ring 2 is not on Bundle 1's route, which runs mgr-1 ring 1 > left-front U10-U30 > mgr-2 ring 1.");
  assert.equal(run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 24}}).error,
    'Say which end c3 heads for, a or b: the routes are not known here.');
  assert.equal(run(r, {op: 'bundle.peel', id: 'b1', cable: 'c9'}).error, CABLE_GONE);
  r = run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 24}, end: 'b'}).rack;
  assert.equal(run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 12}, end: 'a'}).error,
    'c3 already leaves Bundle 1 at left-front U24 for its b end; the routes are not known here to check this against it.');
  const rc = routeCtx(r);
  // with the routes: the end is the nearer one, and a pair out of order is refused
  const near = run(r, {op: 'bundle.peel', id: 'b1', cable: 'c2', at: {lane: 'left-front', ru: 28}}, {route: rc});
  assert.equal(near.summary, 'c2 leaves Bundle 1 at left-front U28 for its b end.');
  assert.equal(run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 26}, end: 'a'}, {route: rc}).error,
    'left-front U26 is at or past where c3 leaves Bundle 1 for its b end, so it would have no run in the bundle.');
  const ok = run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 12}, end: 'a'}, {route: rc});
  assert.ok(!ok.error, ok.error);
  assert.deepEqual(ok.rack.bundles[0].members[2], {cable: 'c3', b: {lane: 'left-front', ru: 24}, a: {lane: 'left-front', ru: 12}});
  const out = run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3'});
  assert.equal(out.summary, 'Took c3 out of Bundle 1; it follows its own route again.');
  assert.equal(out.rack.bundles[0].members.length, 2);
});

test('bundle.update reroutes: by hand, clearing peel points off the new trunk, or worked out again', () => {
  let r = run(rackWith([UP, UP, UP]), [{op: 'bundle.create', cables: ['c1', 'c2', 'c3'], route: TRUNK},
    {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 24}, end: 'b'}]).rack;
  const hand = run(r, {op: 'bundle.update', id: 'b1', route: RT('i2:guide-1', ['left-front', 10], ['left-front', 20])});
  assert.equal(hand.summary, 'Rerouted Bundle 1.');
  assert.ok(hand.findings.some(f => f.text === 'Cleared the peel points of c3: they are not on the new route.'));
  assert.deepEqual(hand.rack.bundles[0].members[2], {cable: 'c3'});
  const again = run(hand.rack, {op: 'bundle.update', id: 'b1', route: null, summary: 'Bundle re-routed.'}, {route: routeCtx(r)});
  assert.equal(again.summary, 'Bundle re-routed.');
  assert.deepEqual(again.rack.bundles[0].route, UP);
  const taken = run(rackWith([UP, UP, UP, UP]), [{op: 'bundle.create', cables: ['c1', 'c2'], route: TRUNK},
    {op: 'bundle.create', cables: ['c3', 'c4'], route: TRUNK}]).rack;
  assert.equal(run(taken, {op: 'bundle.update', id: 'b2', number: 1}).error, "Bundle 1 is already b1's number.");
  assert.equal(run(taken, {op: 'bundle.update', id: 'b2', number: 7}).summary, 'Renamed Bundle 2 to Bundle 7.');
});

test('removing a cable takes it out of its bundle in the same step', () => {
  let r = run(rackWith([UP, UP, UP]), {op: 'bundle.create', cables: ['c1', 'c2', 'c3'], route: TRUNK}).rack;
  const one = run(r, {op: 'cable.remove', id: 'c2'});
  assert.equal(one.summary, 'Deleted cable c2. c2 is out of Bundle 1.');
  assert.deepEqual(one.rack.bundles[0].members.map(m => m.cable), ['c1', 'c3']);
  // a new cable is not handed c2's place
  assert.equal(run(one.rack, {op: 'cable.add', a: end('i1', 'n1'), b: end('i3', 'n1')}).created.ids[0], 'c4');
  const all = run(r, {op: 'remove', id: 'i1', cables: 'remove'});
  assert.equal(all.summary, 'Removed sw-1 and its 3 cables. Its cable manager mgr-1 stays on the rack. c1, c2 and c3 are out of Bundle 1, which now holds no cables.');
  assert.deepEqual(all.rack.bundles[0].members, []);
  // a member's own route applies outside the bundle; a moved end is said
  const routed = run(r, {op: 'cable.route', id: 'c1', route: UP1});
  assert.deepEqual(routed.findings, [{kind: 'note', text: 'c1 follows Bundle 1 from mgr-1 ring 1 to mgr-2 ring 1; this route applies outside it.'}]);
  const moved = run(r, {op: 'cable.update', id: 'c1', b: end('i1', 'p9')});
  assert.ok(moved.findings.some(f => f.text === 'c1 stays in Bundle 1; its b end is now on another device.'), moved.findings);
});

test('one batch places a manager, adds cables and bundles them through its rings', () => {
  let r = rackWith([]);
  r = M.withItem(r, {ref: 'sw', cfg: 'x', ru: 20, label: 'sw-2'}).rack;
  const res = run(r, [
    {op: 'place', ref: 'mgr', face: 'front', ru: 20, as: 'm'},
    {op: 'cable.add', a: end('i5', 'p1'), b: end('i3', 'q1'), as: 'x'},
    {op: 'cable.add', a: end('i5', 'p2'), b: end('i3', 'q2'), as: 'y'},
    {op: 'bundle.create', cables: ['@x', '@y'], route: [{item: '@m', via: 'guide-1'}, {lane: 'left-front', ru: 20}], as: 'b'},
    {op: 'bundle.peel', id: '@b', cable: '@y', at: {item: '@m', via: 'guide-1'}, end: 'a'}]);
  assert.ok(!res.error, res.error);
  const b = res.rack.bundles[0];
  assert.deepEqual(b.route[0], {item: 'i6', via: 'guide-1'});
  assert.deepEqual(b.members, [{cable: 'c1'}, {cable: 'c2', a: {item: 'i6', via: 'guide-1'}}]);
  assert.equal(res.created.b, 'b1');
});

// ── the checks ───────────────────────────────────────────────────────────

test('size: a bundle over a ring\'s opening, and over 2.5 in, warns and is never refused', async () => {
  // 25 Cat6 at 6 mm: sqrt(25 x 36 / 0.8) = 33.5 mm, through ring 1's 29.5 mm
  const many = Array.from({length: 25}, () => UP);
  let r = rackWith(many);
  const ids = r.cables.map(c => c.id);
  const rc = routeCtx(r);
  // with the cable types (Cat 6 at 4 x 6 mm), so the bend is checked too, and passes
  const res = run(r, {op: 'bundle.create', cables: ids, route: TRUNK}, {route: rc, bendOf: CAT6});
  assert.ok(!res.error);
  assert.deepEqual(res.findings, [
    {kind: 'warning', text: 'Bundle 1 is about 34 mm across at mgr-1 ring 1, whose opening is 29.5 mm across.'},
    {kind: 'warning', text: 'Bundle 1 is about 34 mm across at mgr-2 ring 1, whose opening is 29.5 mm across.'}]);
  r = res.rack;
  const f = await inspect(r, 'b1', {chassisOf, route: rc, bendOf: CAT6});
  assert.equal(f.kind, 'bundle');
  assert.equal(f.size.max_mm, 33.5);
  assert.equal(f.size.limit_mm, 29.5);
  assert.equal(f.size.limitBy.text, 'mgr-1 ring 1');
  assert.deepEqual([f.bend.radius_mm, f.bend.violations], [24, []]);
  assert.equal(f.checked, true);
  assert.deepEqual(f.warnings, res.findings.map(x => x.text));
  // 19 pass (29.5^2 x 0.8 / 36 = 19.3)
  const fits = rackWith(Array.from({length: 19}, () => UP));
  assert.deepEqual(run(fits, {op: 'bundle.create', cables: fits.cables.map(c => c.id), route: TRUNK}, {route: routeCtx(fits), bendOf: CAT6}).findings, []);
  // 100 Cat6A at 7.5 mm: about 84 mm, over 2.5 in anywhere
  const huge = rackWith(Array.from({length: 100}, () => UP), 'cat6a');
  const w = run(huge, {op: 'bundle.create', cables: huge.cables.map(c => c.id), route: TRUNK}, {route: routeCtx(huge)}).findings.map(x => x.text);
  assert.ok(w.includes('Bundle 1 is about 84 mm across at mgr-1 ring 1, more than the 63.5 mm (2.5 in) a bundle may be.'), w);
});

test('size: a member of no known type counts as 6 mm and is named; a type table wins over fill\'s figures', () => {
  const r = rackWith([UP, UP, UP], ['om4', '', 'cat6']);
  const rc = routeCtx(r);
  const made = run(r, {op: 'bundle.create', cables: ['c1', 'c2', 'c3'], route: TRUNK}, {route: rc});
  assert.ok(made.findings.some(f => f.text === "Bundle 1's size is an estimate: c2 has no cable type, so it counts as 6 mm."), made.findings);
  const b = made.rack.bundles[0];
  // 3 + 6 + 6: sqrt((9 + 36 + 36) / 0.8) = 10.06
  assert.equal(B.bundleCheck(made.rack, b, {route: rc}).size.max_mm, 10.1);
  // with the cable types: c1's OM4 at 2.0 mm
  assert.equal(B.bundleCheck(made.rack, b, {route: rc, diameterOf: c => (c.media === 'om4' ? 2.0 : null)}).size.max_mm, 9.7);
  // fewer than two present at a point is no bundle there
  assert.equal(B.bundleDiameter([6, 6, 6, 6, 6, 6, 6]).toFixed(1), '17.7');
});

test('size: a duct running up and a duct beside the rack are estimated from their channel and depth', () => {
  let r = rackWith(Array.from({length: 40}, () => RT(['left', 5], ['left', 30])));
  r = {...r, frame: M.normalizeFrame({kind: 'two-post', heightRU: 45})};
  r = {...r, zeroU: [{id: 'z1', ref: 'duct', cfg: '', label: 'vcm-1', at: 'left', offsetMm: 0}]};
  const trunk = RT(['left', 5], ['left', 30]);
  r = run(r, {op: 'bundle.create', cables: r.cables.map(c => c.id), route: trunk}).rack;
  const rc = routeCtx(r, {zeroUAperture: z => (z.id === 'z1' ? {w: 30, h: 165} : null)});
  const L = B.layoutOf(r, r.bundles[0], {route: rc});
  const ps = B.pathwaysOn(r, L.trunk, {route: rc});
  assert.deepEqual(ps.map(p => [p.item, p.kind, p.aperture, p.zeroU]), [['z1', 'duct', {w: 30, h: 165, estimated: true}, true]]);
  // 40 x 6 mm: about 42 mm in a 30 mm channel, said to be an estimate
  assert.ok(B.bundleCheck(r, r.bundles[0], {route: rc}).warnings.includes(
    'Bundle 1 is about 42 mm across at vcm-1 beside the rack, whose opening is estimated at 30 mm across.'));
  // without a channel the duct does not limit the bundle
  assert.deepEqual(B.pathwaysOn(r, L.trunk, {route: {...rc, zeroUAperture: () => null}})[0].aperture, null);
  // a duct on a rack-face part that runs along y: its guide's width and the part's depth
  const g = {via: 'duct', kind: 'duct', run: 'y', face: 'front', x: 0, box: {x: 0, y: 0, w: 25, h: 400}, aperture: {w: 400, h: 400, estimated: true}};
  let s = rackWith([RT('i2:duct'), RT('i2:duct')]);
  const sc = {...routeCtx(s), guidesOf: id => (id === 'i2' ? [g] : [])};
  s = run(s, {op: 'bundle.create', cables: ['c1', 'c2'], route: RT('i2:duct')}, {route: sc}).rack;
  assert.deepEqual(B.pathwaysOn(s, RT('i2:duct'), {route: sc})[0].aperture, {w: 25, h: 110, estimated: true});
  // a stated aperture wins over the estimate
  const stated = {...sc, guidesOf: id => (id === 'i2' ? [{...g, aperture: {w: 50, h: 60}}] : [])};
  assert.deepEqual(B.pathwaysOn(s, RT('i2:duct'), {route: stated})[0].aperture, {w: 50, h: 60, estimated: false});
});

// ── straps ───────────────────────────────────────────────────────────────

test('straps: ceil(L / every), evenly, none on a run\'s end; one in a ring moves to its nearer edge', () => {
  // ring 5 to ring 1 on one manager: 410 mm along x, rings every 102.5 mm, each 40 mm wide
  let r = rackWith([RT('i2:guide-5', 'i2:guide-1'), RT('i2:guide-5', 'i2:guide-1')]);
  r = run(r, {op: 'bundle.create', cables: ['c1', 'c2'], route: RT('i2:guide-5', 'i2:guide-4', 'i2:guide-3', 'i2:guide-2', 'i2:guide-1'),
              straps: {every: {value: 100, unit: 'mm'}}}).rack;
  const s = B.straps(r, r.bundles[0], {route: routeCtx(r)});
  assert.equal(s.count, 5);
  // evenly at 41, 123, 205, 287, 369; ring 2 at 307.5, 3 at 205, 4 at 102.5, each taking +/-30 mm with a strap's half width
  assert.deepEqual(s.straps.map(x => x.along_mm), [41, 132.5, 175, 277.5, 369]);
  assert.deepEqual(s.straps[1], {segment: 1, t: 0.2927, along_mm: 132.5});
  assert.deepEqual(s.runs, [[0, 410]]);
  // 30 in at 12 in: 3 straps, 10 in apart, through ducts (straps in a duct stay)
  const ducts = {'guide-1': 0, 'guide-2': 762};
  let d = rackWith([RT('i2:guide-1', 'i2:guide-2'), RT('i2:guide-1', 'i2:guide-2')]);
  d = run(d, {op: 'bundle.create', cables: ['c1', 'c2'], route: RT('i2:guide-1', 'i2:guide-2')}).rack;
  const dc = {...routeCtx(d), guidesOf: id => (id === 'i2' ? Object.entries(ducts).map(([via, x]) => ({via, kind: 'duct', face: 'front', x, box: {w: 40, h: 30}})) : [])};
  const ds = B.straps(d, d.bundles[0], {route: dc});
  assert.deepEqual(ds.straps.map(x => x.along_mm), [127, 381, 635]);
  assert.deepEqual(ds.every, {value: 12, unit: 'in'});
  // {every: null}: no straps, still runs
  const none = run(d, {op: 'bundle.update', id: 'b1', straps: {every: null}}).rack;
  assert.equal(B.straps(none, none.bundles[0], {route: dc}).count, 0);
  // without the routes: not placed
  assert.equal(B.straps(d, d.bundles[0], {}), null);
});

test('straps: fan-out leaves fewer than two riding, which ends a run', () => {
  let r = rackWith([UP1, UP1, UP1]);
  r = run(r, [{op: 'bundle.create', cables: ['c1', 'c2', 'c3'], route: RT(['left-front', 10], ['left-front', 30])},
              {op: 'bundle.peel', id: 'b1', cable: 'c2', at: {lane: 'left-front', ru: 20}, end: 'b'},
              {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 20}, end: 'b'}]).rack;
  const s = B.straps(r, r.bundles[0], {route: routeCtx(r)});
  assert.deepEqual(s.runs, [[0, Math.round(10 * RU * 10) / 10]]);
  assert.equal(s.count, Math.ceil((10 * RU) / 304.8));
});

// ── what an agent reads ──────────────────────────────────────────────────

test('describe, inspect and selectCables know bundles', async () => {
  let r = run(rackWith([UP, UP, UP]), {op: 'bundle.create', cables: ['c1', 'c2', 'c3'], route: TRUNK, label: 'uplinks'}).rack;
  const rc = routeCtx(r);
  const text = describe(r, {chassisOf});
  assert.match(text.split('\n')[0], /: 4 items, 3 cables, 1 bundle\.$/);
  assert.ok(text.includes('Bundles:\nb1 uplinks: 3 cables (c1-c3), straps every 12 in, not checked.'), text);
  assert.ok(describe(r, {chassisOf, route: rc}).includes('b1 uplinks: 3 cables (c1-c3), about 12 mm, straps every 12 in, no warnings.'));
  assert.match(describe(r, {chassisOf}, {section: 'bundles'}), /Bundles 1-1 shown\.\n.*\nBundles:\nb1 uplinks/);
  assert.equal(describe(rackWith([]), {chassisOf}).includes('bundle'), false);
  const f = await inspect(r, 'b1', {chassisOf, route: rc});
  assert.deepEqual(Object.keys(f).sort(), ['bend', 'checked', 'gone', 'id', 'kind', 'label', 'length', 'members', 'name', 'notes', 'number',
    'route', 'size', 'straps', 'warnings'].sort());
  assert.deepEqual([f.name, f.number, f.route.text], ['uplinks', 1, 'mgr-1 ring 1 > left-front U10-U30 > mgr-2 ring 1']);
  assert.deepEqual(f.members[0], {cable: 'c1', join: TRUNK[0], leave: TRUNK.at(-1)});
  assert.ok(f.length.metres > 0.8);
  assert.ok(f.straps.count >= 3);
  const bare = await inspect(r, 'b1', {chassisOf});
  assert.deepEqual([bare.checked, bare.size, bare.length, bare.straps.count], [false, null, null, null]);
  assert.deepEqual((await inspect(r, 'c2', {chassisOf, route: rc})).bundle, {id: 'b1', join: TRUNK[0], leave: TRUNK.at(-1)});
  assert.equal('bundle' in await inspect(rackWith([UP]), 'c1', {chassisOf}), false);
  assert.deepEqual(await inspect(r, 'b7', {chassisOf}), {error: BUNDLE_GONE});
  assert.deepEqual(await selectCables(r, {bundle: 'b1'}), {ids: ['c1', 'c2', 'c3']});
  assert.deepEqual(await selectCables(r, {bundle: 'b1', item: 'i1', path: 'p2'}), {ids: ['c2']});
  assert.deepEqual(await selectCables(r, {bundle: 'b2'}), {error: BUNDLE_GONE});
  assert.deepEqual(await selectCables(r, {bundle: ''}), {error: 'A selector\'s bundle is a name; leave it out rather than send "".'});
  assert.deepEqual(await selectCables(r, {bundle: null}), {error: "A selector's bundle is a name; leave it out rather than send null."});
});

test('a trunk waypoint that is gone is skipped and said, in inspect and the export notes', async () => {
  let r = run(rackWith([UP, UP]), {op: 'bundle.create', cables: ['c1', 'c2'], route: [...TRUNK, {lane: 'left-front', ru: 41}]}).rack;
  r = run(r, {op: 'frame', heightRU: 40}).rack;
  const rc = routeCtx(r);
  assert.deepEqual((await inspect(r, 'b1', {chassisOf, route: rc})).gone, [{lane: 'left-front', ru: 41}]);
  assert.deepEqual(fillNotes(r, {fill: [], over: [], routes: new Map(), ctx: rc}),
    ['Bundle 1: waypoint left-front U41 is gone, so the route skips it.']);
});

test('the editor hands on the notes parseDoc gave, ahead of its own', () => {
  const notes = [];
  const doc = M.parseDoc({...M.newDoc(), racks: [{...rackWith([UP]), bundles: [{id: 'b1', number: 1, members: [{cable: 'c8'}], route: []}]}]}, {notes});
  const ed = createRackEditor({doc, chassisOf});
  assert.deepEqual(ed.loadDoc(doc, {notes}).findings[0], {kind: 'note', text: 'Rack 1: Bundle 1 named c8, which is not a cable in the rack, so it was taken out.'});
  assert.deepEqual(ed.loadDoc(doc).findings, []);
});

test('a routing reader that throws counts as missing: not measured, never an error', async () => {
  const r = rackWith([UP, UP]);
  const broken = {...routeCtx(r), guidesOf: () => { throw new Error('no face'); }};
  const made = run(r, {op: 'bundle.create', cables: ['c1', 'c2'], route: TRUNK}, {route: broken});
  assert.ok(!made.error, made.error);
  assert.deepEqual(made.findings, [{kind: 'note', text: 'Bundle 1 is not checked for size or bend: the routes could not be read.'}]);
  assert.equal(run(r, {op: 'bundle.create', cables: ['c1', 'c2']}, {route: broken}).error, "The cables' routes are not known here, so the bundle needs a route.");
  const f = await inspect(made.rack, 'b1', {chassisOf, route: broken});
  assert.deepEqual([f.checked, f.size, f.length], [false, null, null]);
  assert.match(describe(made.rack, {chassisOf, route: broken}), /b1 Bundle 1: 2 cables \(c1-c2\), straps every 12 in, not checked\./);
});

// ── round 1 review ───────────────────────────────────────────────────────

test('a trunk kept as written survives a save and a reload; a junk peel point is dropped', () => {
  const r = rackWith([UP, UP]);
  const raw = {...M.newDoc(), racks: [{...r, bundles: [{id: 'b1', number: 1, label: '',
    members: [{cable: 'c1', a: 'garbage', b: {lane: 'left-front', ru: 20, extra: 1}}, {cable: 'c2'}],
    route: [{lane: 'left-front', ru: 10}, 'bad']}]}]};
  const once = M.parseDoc(raw);
  const b = once.racks[0].bundles[0];
  assert.deepEqual(b.routeAsWritten, [{lane: 'left-front', ru: 10}, 'bad']);
  assert.deepEqual(b.members[0], {cable: 'c1', b: {lane: 'left-front', ru: 20}});
  const twice = M.parseDoc(M.serialize(once));
  assert.deepEqual(twice.racks[0], once.racks[0]);
  assert.deepEqual(M.parseDoc(M.serialize(twice)).racks[0], once.racks[0]);
  // the readable part no longer the trunk: the old writing goes
  const edited = JSON.parse(M.serialize(once));
  edited.racks[0].bundles[0].route = [{lane: 'left-front', ru: 12}];
  assert.equal('routeAsWritten' in M.parseDoc(edited).racks[0].bundles[0], false);
  // what is written validates, the junk peel point dropped
  assert.deepEqual(validate(SCHEMA, JSON.parse(M.serialize(M.parseDoc(raw)))), []);
});

test('every way a cable leaves the rack takes it out of its bundle', () => {
  const r = run(rackWith([UP, UP, UP]), {op: 'bundle.create', cables: ['c1', 'c2', 'c3'], route: TRUNK}).rack;
  assert.deepEqual(withoutCable(r, 'c2').bundles[0].members.map(m => m.cable), ['c1', 'c3']);
  assert.deepEqual(withoutCablesOf(r, 'i1').bundles[0].members, []);
  assert.equal(withoutCable(rackWith([UP]), 'c1').bundles, undefined);
});

test('a peel point that leaves no run is refused, and one in a file rides to the end', () => {
  let r = run(rackWith([UP, UP, UP]), [{op: 'bundle.create', cables: ['c1', 'c2', 'c3'], route: TRUNK},
    {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 24}, end: 'b'}]).rack;
  const rc = routeCtx(r);
  // a and b at one point: no run
  assert.equal(run(r, {op: 'bundle.peel', id: 'b1', cable: 'c3', at: {lane: 'left-front', ru: 24}, end: 'a'}, {route: rc}).error,
    'left-front U24 is at or past where c3 leaves Bundle 1 for its b end, so it would have no run in the bundle.');
  // b at the far end of its run (where it joins): no run
  assert.equal(run(r, {op: 'bundle.peel', id: 'b1', cable: 'c2', at: TRUNK[0], end: 'b'}, {route: rc}).error,
    'mgr-1 ring 1 is at or past where c2 leaves Bundle 1 for its a end, so it would have no run in the bundle.');
  // the same from a file: stale, ignored with a note, and it rides to the end
  const file = {...r, bundles: [{...r.bundles[0], members: [{cable: 'c1', b: TRUNK[0]}, {cable: 'c2'}, {cable: 'c3'}]}]};
  const L = B.layoutOf(file, file.bundles[0], {route: rc});
  assert.deepEqual(L.members[0].stale, ['b']);
  assert.deepEqual(R.resolveRoute(file, file.cables[0], rc).leave, TRUNK.at(-1));
  assert.ok(B.bundleCheck(file, file.bundles[0], {route: rc}).notes.includes(
    "c1's peel point mgr-1 ring 1 is out of order with its other end on Bundle 1, so it rides to the end."));
});

test('a bundle of one is not drawn: its cable follows its own route, and joins nothing', async () => {
  const away = RT(['right-front', 10], ['right-front', 30]);
  let r = run(rackWith([away, UP]), {op: 'bundle.create', cables: ['c1', 'c2'], route: TRUNK}).rack;
  const rc = routeCtx(r);
  assert.deepEqual(R.resolveRoute(r, r.cables[0], rc).waypoints, TRUNK);     // two: drawn, along the trunk
  r = run(r, {op: 'bundle.peel', id: 'b1', cable: 'c2'}).rack;
  const got = R.resolveRoute(r, r.cables[0], rc);
  assert.deepEqual([got.waypoints, got.bundle], [away, undefined]);
  const f = await inspect(r, 'b1', {chassisOf, route: rc});
  assert.deepEqual(f.members, [{cable: 'c1', join: null, leave: null}]);
  assert.deepEqual((await inspect(r, 'c1', {chassisOf, route: rc})).bundle, {id: 'b1', join: null, leave: null});
});

test('size: over 2.5 in with no opening on the way warns at 63.5 mm, not past it', () => {
  const lane = RT(['left-front', 10], ['left-front', 30]);
  const big = rackWith(Array.from({length: 100}, () => lane));        // sqrt(100 x 36 / 0.8) = 67.1 mm
  const w = run(big, {op: 'bundle.create', cables: big.cables.map(c => c.id), route: lane}, {route: routeCtx(big), bendOf: CAT6}).findings;
  assert.deepEqual(w, [{kind: 'warning', text: 'Bundle 1 is about 67 mm across at left-front U10, more than the 63.5 mm (2.5 in) a bundle may be.'}]);
  const ok = rackWith(Array.from({length: 80}, () => lane));          // 60 mm
  assert.deepEqual(run(ok, {op: 'bundle.create', cables: ok.cables.map(c => c.id), route: lane}, {route: routeCtx(ok), bendOf: CAT6}).findings, []);
  assert.equal(B.MAX_BUNDLE_MM, 63.5);
});

test('cables that run together at two places and apart between are refused in words', () => {
  const r = rackWith([RT('i2:guide-1', 'i2:guide-2', 'i2:guide-5'), RT('i2:guide-1', 'i2:guide-3', 'i2:guide-5')]);
  assert.equal(run(r, {op: 'bundle.create', cables: ['c1', 'c2']}, {route: routeCtx(r)}).error,
    'c1 and c2 run together at mgr-1 ring 1 and mgr-1 ring 5, but apart between them. Bundle them separately, or give the bundle a route.');
});

test('a shortened reading trims bundle lines and counts them', () => {
  let r = rackWith(Array.from({length: 40}, () => UP));
  for (let k = 0; k < 20; k++)
    r = run(r, {op: 'bundle.create', cables: [`c${2 * k + 1}`, `c${2 * k + 2}`], route: TRUNK, label: `a fairly long bundle label ${k}`}).rack;
  const text = describe(r, {chassisOf});
  assert.ok(text.length <= 1500, text.length);
  const shown = text.split('\n').filter(l => /^b\d+ /.test(l)).length;
  assert.ok(shown < 20, `${shown} bundle lines`);
  const more = Number(/and (\d+) more not listed/.exec(text)[1]);
  const listedCables = text.split('\n').filter(l => /^c\d+: /.test(l)).length;
  assert.equal(more, (40 - listedCables) + (20 - shown));
});

test('the five commands are in the table, described as the design says', () => {
  for (const op of ['bundle.create', 'bundle.add', 'bundle.peel', 'bundle.update', 'bundle.remove']) assert.ok(COMMANDS[op], op);
  assert.equal(COMMANDS['bundle.create'].description, 'Bundle two or more cables sharing part of their route. It runs where they run together, unless given a route. Refused for a bundled cable.');
});
