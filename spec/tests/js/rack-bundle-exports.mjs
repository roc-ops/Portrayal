// spec/tests/js/rack-bundle-exports.mjs
// Bundles in the exports (#923, docs/cable-bundles-design.md section 7): the
// per-bundle record and note, the cable schedule's bundle column, the BOM's
// strap line, and draw.io's note. The DCIM descriptions are tested with the
// rest of the cables file, in rack-dcim-import.mjs.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as B from '../../../kit/rack/bundles.js';
import * as X from '../../../kit/rack/export-data.js';
import {laneX} from '../../../kit/rack/route.js';
import {bendLookup, diameterLookup} from '../../../kit/rack/cable-types.js';
import {apply} from '../../../kit/rack/commands.js';
import {withCable} from '../../../kit/rack/cable-rules.js';

// The installed radii #919 publishes for these types: Cat 6 at 4 x its 6 mm,
// OM4 and OS2 a fixed 25 mm (TIA-568), a passive DAC 23 mm.
const src = ['s'];
const TYPES = {
  cat6: {od_mm: 6.0, min_bend_radius: {installed: {xOD: 4, basis: 'standard', sources: src}}},
  om4: {od_mm: 3.0, min_bend_radius: {installed: {mm: 25, basis: 'standard', sources: src}}},
  os2: {od_mm: 3.0, min_bend_radius: {installed: {mm: 25, basis: 'standard', sources: src}}},
  dac: {od_mm: 5.0, min_bend_radius: {installed: {mm: 23, basis: 'convention', sources: src}}},
};
const bendOf = bendLookup(TYPES);

const RINGS = ['guide-1', 'guide-2'];
// A tray on each device. Its d of 0 puts its rings on the rail plane, with the
// lanes, so a leg from a ring to the lane runs along x alone.
const SIZES = {sw: {ru: 1, d: 515, model: 'SW'}, pp: {ru: 1, d: 100, model: 'PP'},
  tray: {ru: 1, d: 0, mount: 'rack-face', model: 'TRAY', guides: {front: RINGS}, default: 'x'}};
const chassisOf = ref => SIZES[ref] || null;
const LANE = laneX('left');
// mgr-1's ring 1 stands 24.5 mm in from the left-front lane: the corner where
// the trunk turns up the lane has room for a 24.5 mm bend. mgr-2's stands
// 66.425 mm in (x -205), a gentle corner.
const TIGHT = 24.5, GENTLE = -205 - LANE;
const routeCtx = (rack, extra = {}) => ({chassisOf, portX: () => -150,
  guidesOf: id => {
    const it = rack.items.find(i => i.id === id);
    if (it?.ref !== 'tray') return [];
    const x0 = it.label === 'mgr-1' ? LANE + TIGHT : LANE + GENTLE;
    return RINGS.map((via, k) => ({via, kind: 'ring', face: 'front', x: x0 + k * 100, box: {x: 0, y: 0, w: 40, h: 30},
                                   aperture: null, ...(extra.radius?.[`${it.label}:${via}`] ? {radius: extra.radius[`${it.label}:${via}`]} : {})}));
  }});

const end = (item, path) => ({item, path, view: 'front'});
const RT = (...ws) => ws.map(w => (Array.isArray(w) ? {lane: w[0], ru: w[1]} : {item: w.split(':')[0], via: w.split(':')[1]}));
const TRUNK = RT('i2:guide-1', ['left-front', 10], ['left-front', 30], 'i4:guide-1');
function rackWith(media, route = TRUNK) {
  let r = M.newRack({name: 'Rack 1'});
  r = M.withItem(r, {ref: 'sw', cfg: 'x', ru: 10, label: 'sw-1'}).rack;
  r = M.withItem(r, {ref: 'tray', cfg: 'x', ru: 10, label: 'mgr-1', on: 'i1', unit: 1}).rack;
  r = M.withItem(r, {ref: 'pp', cfg: 'x', ru: 30, label: 'pp-1'}).rack;
  r = M.withItem(r, {ref: 'tray', cfg: 'x', ru: 30, label: 'mgr-2', on: 'i3', unit: 1}).rack;
  media.forEach((m, k) => {
    r = withCable(r, {a: end('i1', `p${k + 1}`), b: end('i3', `q${k + 1}`), media: m}).rack;
    r = {...r, cables: r.cables.map(c => (c.id === `c${k + 1}` ? {...c, route, routeEdited: true} : c))};
  });
  return apply(r, {op: 'bundle.create', cables: r.cables.map(c => c.id), route}, {chassisOf}).rack;
}
const diameterOf = diameterLookup(TYPES);
const ctxOf = r => ({route: routeCtx(r), bendOf, diameterOf});

// Three bundles over five cables on one trunk: b1 (c1, c2) at the default
// 12 in, b2 (c3, c4) at 300 mm and labelled, b3 holding c5 alone.
function threeBundles() {
  const r = rackWith(['cat6', 'om4', 'cat6', 'cat6', 'os2']);
  const one = r.bundles[0], mem = ids => ids.map(cable => ({cable}));
  return {...r, bundles: [
    {...one, members: mem(['c1', 'c2'])},
    {...one, id: 'b2', number: 2, label: 'uplinks', members: mem(['c3', 'c4']), straps: {every: {value: 300, unit: 'mm'}}},
    {...one, id: 'b3', number: 3, members: mem(['c5'])}]};
}

test('bundleExports: each bundle measured as the kit measures it, with its tag fields', () => {
  const r = rackWith(['cat6', 'om4', 'cat6']);
  const ctx = ctxOf(r);
  const [e] = X.bundleExports(r, ctx);
  const st = B.straps(r, r.bundles[0], ctx), check = B.bundleCheck(r, r.bundles[0], ctx);
  assert.ok(st.count > 0, 'the fixture must place straps');
  assert.deepEqual(e, {id: 'b1', number: 1, label: '', name: 'Bundle 1', members: ['c1', 'c2', 'c3'], drawn: true, checked: true,
    length_m: B.trunkLength(r, r.bundles[0], ctx).metres, every: {value: 12, unit: 'in'}, straps: st.count,
    size_mm: check.size.max_mm, limit_mm: 63.5, limit_at: null, limit_estimated: false,
    bend_mm: 25, bend_by: 'c2', bend_checked: true, warnings: check.warnings, notes: []});
  assert.deepEqual([e.length_m, e.straps, e.size_mm], [0.98, 4, 10.1]);
  // the bend warning comes through
  assert.deepEqual(e.warnings, ['Bundle 1 turns at left-front U10 with room for a 24.5 mm bend; c2 (om4) needs 25 mm, 0.5 mm short.']);
  // a label is the name a tag prints; a control character in it is a space
  const lab = {...r, bundles: [{...r.bundles[0], label: 'A\nB'}]};
  assert.deepEqual(X.bundleExports(lab, ctxOf(lab)).map(x => [x.number, x.label, x.name]), [[1, 'A\nB', 'A B']]);
});

test('bundleExports: without the routes nothing is measured and no strap is guessed', () => {
  const r = threeBundles();
  const got = X.bundleExports(r);
  assert.deepEqual(got.map(e => [e.id, e.checked, e.straps, e.length_m, e.size_mm, e.bend_mm]), [
    ['b1', false, null, null, null, null], ['b2', false, null, null, null, null], ['b3', false, null, null, null, null]]);
  assert.deepEqual(X.strapBomRows(got), []);
  assert.deepEqual(X.strapBomNotes(got), [
    'Bundle 1: its route could not be read, so its straps are not counted.',
    'uplinks: its route could not be read, so its straps are not counted.']);
  // a reader that throws is the same: not measured, never an error
  const bad = {...ctxOf(r), route: {...routeCtx(r), guidesOf: () => { throw new Error('x'); }}};
  assert.deepEqual(X.bundleExports(r, bad).map(e => e.straps), [null, null, null]);
});

test('the note per bundle: size, members, straps, length and bend, then its warnings and notes', () => {
  const r = threeBundles();
  const got = X.bundleExports(r, ctxOf(r));
  assert.deepEqual(X.bundleNotes(got), [
    'Bundle 1 (b1): 2 cables (c1-c2), 0.98 m, 4 straps every 12 in; 8 mm across, limit 63.5 mm; bend radius 25 mm (c2).',
    'Bundle 1 turns at left-front U10 with room for a 24.5 mm bend; c2 (om4) needs 25 mm, 0.5 mm short.',
    'uplinks (b2): 2 cables (c3-c4), 0.98 m, 4 straps every 300 mm; 10 mm across, limit 63.5 mm; bend radius 24 mm (c3).',
    'Bundle 3 (b3): 1 cable (c5), no straps.',
    'Bundle 3 holds one cable, so it is not drawn.']);
  assert.deepEqual(X.bundleNotes(X.bundleExports(r)).slice(0, 1),
    ['Bundle 1 (b1): 2 cables (c1-c2); its route could not be read, so its length, straps, size and bend are not given.']);
  // a bundle set to no straps, and one whose bend is unchecked, say so
  const none = {...r, bundles: [{...r.bundles[0], straps: {every: null}}]};
  const [n] = X.bundleExports(none, ctxOf(none));
  assert.deepEqual([n.every, n.straps], [null, 0]);
  assert.match(X.bundleNote(n), /, 0\.98 m, no straps; 8 mm across/);
  assert.deepEqual(X.strapBomNotes([n]), ['Bundle 1 is set to no straps, so none are counted for it.']);
  const [u] = X.bundleExports(r, {route: routeCtx(r)});
  assert.equal(u.bend_checked, false);
  assert.match(X.bundleNote(u), /; bend not checked\.$/);
});

test('the BOM: one hook-and-loop strap line, every bundle summed, no manufacturer', () => {
  const r = threeBundles();
  const got = X.bundleExports(r, ctxOf(r));
  const each = r.bundles.map(b => B.straps(r, b, ctxOf(r)).count);
  assert.deepEqual(each, [4, 4, 0]);
  assert.deepEqual(X.strapBomRows(got), [{section: 'Cables', qty: 8, manufacturer: '', model: 'Hook-and-loop cable strap',
    description: 'For 2 bundles, one strap every 12 in or 300 mm along each; length and width to suit', ref: ''}]);
  assert.deepEqual(X.strapBomNotes(got), []);
  // one spacing, one bundle
  assert.equal(X.strapBomRows(got.slice(0, 1))[0].description, 'For 1 bundle, one strap every 12 in along each; length and width to suit');
  assert.equal(X.strapBomRows(got.slice(0, 1))[0].qty, 4);
  // the line goes in the file like any other, through bomCell
  const csv = X.toCsv(X.BOM_COLUMNS, X.strapBomRows(got), [], {cell: X.bomCell});
  assert.match(csv, /\r\nCables,8,,Hook-and-loop cable strap,"For 2 bundles, one strap every 12 in or 300 mm along each; length and width to suit",\r\n$/);
  // no bundle, no line
  assert.deepEqual(X.strapBomRows(X.bundleExports({...r, bundles: []}, ctxOf(r))), []);
});

test("the cable schedule: a bundle column straight after route, and each bundle's note", () => {
  const r = threeBundles();
  const routes = new Map(r.cables.map(c => [c.id, {waypoints: []}]));
  const bundles = X.bundleExports(r, ctxOf(r));
  const {columns, rows, notes} = X.cableScheduleRows(r, new Map(), r.items, routes, {bundles});
  assert.equal(columns.indexOf('bundle'), columns.indexOf('route') + 1);
  assert.deepEqual(rows.map(x => [x.id, x.bundle]), [['c1', 'Bundle 1'], ['c2', 'Bundle 1'], ['c3', 'uplinks'], ['c4', 'uplinks'], ['c5', 'Bundle 3']]);
  for (const line of X.bundleNotes(bundles)) assert.ok(notes.includes(line), line);
  // a cable in no bundle has a blank cell
  const out = {...r, bundles: r.bundles.slice(1)};
  assert.deepEqual(X.cableScheduleRows(out, new Map(), out.items).rows.map(x => x.bundle), ['', '', 'uplinks', 'uplinks', 'Bundle 3']);
  // without bundleExports' answer the notes say the routes were not read
  assert.ok(X.cableScheduleRows(r).notes.includes(
    'Bundle 1 (b1): 2 cables (c1-c2); its route could not be read, so its length, straps, size and bend are not given.'));
  // a rack with no bundles adds no bundle notes
  const plain = {...r, bundles: []};
  assert.ok(!X.cableScheduleRows(plain).notes.some(n => /Bundle|bundle/.test(n)));
});

test('draw.io says its cables are drawn one by one, not as bundles', () => {
  const r = threeBundles();
  const {notes} = X.drawioCables(r, {ends: new Map(), idOf: id => id, drawn: () => true});
  assert.ok(notes.includes('Bundles are not drawn in draw.io, so their cables are drawn one by one: ' +
    'Bundle 1 holds c1-c2; uplinks holds c3-c4.'), notes);
  assert.ok(!X.drawioCables({...r, bundles: []}, {ends: new Map(), idOf: id => id, drawn: () => true}).notes.some(n => /Bundle/.test(n)));
});
