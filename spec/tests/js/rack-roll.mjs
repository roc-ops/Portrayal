// spec/tests/js/rack-roll.mjs
// ROLL (docs/rack-file-v4-design.md section 6, build part 5): one item key,
// 90, 180 or 270 degrees clockwise as the item is seen in the elevation of
// the face it is on. `180` is the same box turned over, through the solids,
// the trays, the guides and the routes; a quarter turn is fitted by its
// rolled box and is an outline.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as F from '../../../kit/rack/fit.js';
import * as Q from '../../../kit/rack/queries.js';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import {apply, COMMANDS} from '../../../kit/rack/commands.js';
import {RU, SIDES} from '../../../kit/rack/rails.js';
import * as G from './cable-solids-fixture.mjs';

const near = (a, b, what, tol = 1e-6) => assert.ok(Math.abs(a - b) <= tol, `${what}: ${a}, want ${b}`);
const LIFT = (RU - 44) / 2;                       // the lacer is 44 mm, centred in its unit
const SIZES = {
  sw: {ru: 1, w: 440, h: 43.6, d: 500, model: 'SW-1'},
  fx: {ru: 2, w: 300, h: 88, d: 250, model: 'FX-8'},
  wide: {ru: 13, w: 440, h: 577, d: 300, model: 'WIDE-13'},
  half: {ru: 0.5, w: 482.6, h: 22.2, d: 284, model: 'XCU10'},
  bracket: {ru: 1, w: 60, h: 44, d: 110, mount: 'rack-face', model: 'Bracket'},
};
const chassisOf = ref => SIZES[ref] || null;
const rackOf = () => ({...M.newRack(), frame: M.normalizeFrame({kind: 'four-post', heightRU: 42})});
const put = (rack, ref, ru, extra = {}) => M.withItem(rack, {ref, cfg: '', ru, label: extra.label ?? SIZES[ref]?.model ?? ref, ...extra}).rack;
const roll = (rack, id, value) => M.updateItem(rack, id, {roll: value});
const run = (rack, cmds) => apply(rack, cmds, {chassisOf});

// ── the key ──────────────────────────────────────────────────────────────

test('roll is read as 90, 180 or 270, and anything else is upright and not written', () => {
  const doc = v => ({format: 'portrayal-rack', version: 4, racks: [{frame: {}, items: [{id: 'i1', ref: 'sw', ru: 1, ...(v === undefined ? {} : {roll: v})}]}]});
  for (const v of [90, 180, 270]) assert.equal(M.parseDoc(doc(v)).racks[0].items[0].roll, v);
  for (const v of [0, 360, 45, '180', null, true]) assert.equal('roll' in M.parseDoc(doc(v)).racks[0].items[0], false, String(v));
  assert.equal('roll' in M.parseDoc(doc(undefined)).racks[0].items[0], false);
  assert.deepEqual([{roll: 180}, {roll: 0}, {}, null].map(M.rollOf), [180, 0, 0, 0]);
  assert.deepEqual(COMMANDS.patch.args.properties.roll.enum, [90, 180, 270, null]);
});

// ── fixture 3 of the cable lay note: a manager pair back to back ─────────
// S-up at U14; an FHD-CMP5DR Mu at U13 mounted the usual way; a second, Md,
// at U12 with roll 180; S-dn at U11.
function fixture3() {
  let r = G.add({...M.newRack(), items: []}, 'sw', 14, {label: 'S-up'});
  r = G.add(r, 'fhd-cmp5dr', 13, {label: 'Mu'});
  r = roll(G.add(r, 'fhd-cmp5dr', 12, {label: 'Md'}), 'i3', 180);
  r = G.add(r, 'sw', 11, {label: 'S-dn'});
  const c = G.cable('m', G.end('i1', 'p'), G.end('i4', 'q'));
  r = {...r, cables: [c]};
  const ctx = {...G.ctxOf({ports: {i1: {p: -150}, i4: {q: -150}}}), guidesOf: id => (id === 'i2' || id === 'i3' ? G.RINGS : [])};
  return {r, c, ctx};
}

test('fixture 3: the rolled manager fits in its one unit, floor down and rings hanging', () => {
  const {r, ctx} = fixture3();
  const md = r.items[2];
  assert.equal(md.roll, 180);
  assert.deepEqual(F.fits(r, md, G.chassisOf, {ignoreId: 'i3'}), {ok: true});
  assert.deepEqual(F.spanOf(md, G.chassisOf), [12, 13], 'the same box: one unit, and only it');
  assert.deepEqual(F.itemBox(r, md, G.chassisOf), F.itemBox(r, {...md, roll: undefined}, G.chassisOf));
  const [mu, dn] = S.traysOf(r, ctx);
  assert.deepEqual([mu.item, dn.item, mu.flipped, dn.flipped], ['i2', 'i3', false, true]);
  // Mu: its floor 3 mm above the bottom of its body in U13, rings standing up
  near(mu.top, 12 * RU + LIFT + 3, 'Mu floor');
  assert.ok(mu.rings.every(o => o.box.y0 > mu.top), 'the rings of Mu stand on its floor');
  // Md: its floor 3 mm below the top of its body in U12, facing down, rings hanging below it
  near(dn.under, 11 * RU + LIFT + 44 - 3, 'Md floor, the face that looks down');
  near(dn.top, dn.under + 1.5, 'its own underside looks up, a plain floor');
  assert.ok(dn.rings.every(o => o.box.y1 < dn.under), 'the rings of Md hang below its plate');
  // the two plates are back to back across the line between the units
  assert.ok(dn.top < 12 * RU && mu.under > 12 * RU && mu.under - dn.top < 4);
  // a ring of Md is across the centre line from the same ring of Mu, and as far below the line as that one is above
  const [a, b] = [mu, dn].map(t => t.rings.find(o => o.via === 'guide-1').box);
  near(b.x0, -a.x1, 'mirrored across'); near(b.x1, -a.x0, 'mirrored across');
  near(12 * RU - b.y1, a.y0 - 12 * RU, 'mirrored about the line between the units');
  // and the solids of Md are those of Mu turned over
  const solids = S.solidsOf(r, ctx);
  const plate = id => solids.find(s => s.item === id && s.part === 'tray/floor' && s.box.x1 - s.box.x0 > 400).box;
  near(plate('i3').y1, dn.top, 'the plate of Md'); near(plate('i2').y1, mu.top, 'the plate of Mu');
});

test('fixture 3: each switch takes its own manager, and the cord of S-dn rests in a hanging ring', () => {
  const {r, c, ctx} = fixture3();
  const route = R.autoRoute(r, c, ctx);
  // S-up at x -150 leaves through ring 1 of Mu; S-dn through the ring of Md that is on that side as mounted, its ring 5
  assert.deepEqual(route.filter(w => w.item).map(w => [w.item, w.via]), [['i2', 'guide-1'], ['i3', 'guide-5']]);
  // the ring as mounted: where pointOf puts it, and where its solid opening is
  const [dn] = S.traysOf(r, ctx).filter(t => t.item === 'i3');
  const ring5 = dn.rings.find(o => o.via === 'guide-5').box;
  const at = R.pointOf(r, {item: 'i3', via: 'guide-5'}, ctx);
  near(at.x, 205.8 * -1, 'ring 5 of the rolled manager is on the left');
  assert.ok(at.x > ring5.x0 && at.x < ring5.x1);
  near(R.pointOf(r, {item: 'i2', via: 'guide-5'}, ctx).x, 205.8, 'and of the upright one on the right');
  const p = R.routePath(r, c, ctx);
  assert.deepEqual(p.crossings, []);
  assert.deepEqual(p.rings.map(g => [g.item, g.via, g.passed]), [['i2', 'guide-1', true], ['i3', 'guide-5', true]]);
  assert.deepEqual(p.rests.filter(x => x.kind === 'ring').map(x => [x.item, x.via]), [['i2', 'guide-1'], ['i3', 'guide-5']]);
  // in the hanging ring it lies on the inside edge that is lowest as mounted, a radius up
  const inside = p.points.filter(q => q.via === 'guide-5' && (q.at === 'entry' || q.at === 'exit'));
  assert.equal(inside.length, 2);
  for (const q of inside) { near(q.y, ring5.y0 + 1.5, 'on the hanging ring'); assert.ok(q.y < dn.under); }
  // upright in the same place, the cord of S-dn would go through ring 1 on the sill above the plate
  const up = {...r, items: r.items.map(i => (i.id === 'i3' ? {...i, roll: undefined} : i))};
  assert.deepEqual(R.autoRoute(up, c, ctx).filter(w => w.item).map(w => w.via), ['guide-1', 'guide-1']);
});

// ── a port on a rolled item ──────────────────────────────────────────────

test('a port on an item rolled 180 is at the mirrored point, on the box itemBox gives', () => {
  let r = put(rackOf(), 'fx', 10, {label: 'fx'});
  const rc = {chassisOf, guidesOf: () => [], portX: () => 100, portY: () => 9 * RU + 60};
  const end = {item: 'i1', path: 'p', view: 'front'};
  const box = F.itemBox(r, r.items[0], chassisOf), cy = (box.y0 + box.y1) / 2;
  assert.deepEqual(R.portPoint(r, end, rc), {x: 100, y: 9 * RU + 60, z: 0});
  const over = roll(r, 'i1', 180);
  const p = R.portPoint(over, end, rc);
  assert.equal(p.x, -100);
  near(p.y, 2 * cy - (9 * RU + 60), 'as far below the middle of the box as it was above');
  assert.equal(p.z, 0);
  // a narrow part on one rail turns about its own hole line, not the centre of the rack
  let b = put(rackOf(), 'bracket', 10, {side: 'left'});
  const hole = SIDES[0].hole;
  assert.equal(F.centreX(b.items[0], chassisOf), hole);
  assert.equal(F.rollPoint(roll(b, 'i1', 180), {...b.items[0], roll: 180}, {x: hole + 10, y: 9.5 * RU}, chassisOf).x, hole - 10);
  // an item with no roll is answered with the very point
  const pt = {x: 5, y: 7};
  assert.equal(F.rollPoint(r, r.items[0], pt, chassisOf), pt);
});

test('facePoint: a point of the face as drawn, through face, turned and roll', () => {
  const r = put(rackOf(), 'fx', 10);
  const it = r.items[0], box = F.itemBox(r, it, chassisOf);
  // 300 wide: 20 from the left and 10 down from the top of its front panel
  const p = F.facePoint(r, it, {x: 20, y: 10}, chassisOf);
  assert.equal(p.x, -130); near(p.y, box.y1 - 10, 'down from the top of the body');
  // on the rear of the rack its front panel looks out of the back, so it is mirrored
  assert.equal(F.facePoint(r, {...it, face: 'rear'}, {x: 20, y: 10}, chassisOf).x, 130);
  // turned, its rear panel faces out of the front, and its front panel out of the back
  assert.equal(F.facePoint(r, {...it, turned: true}, {x: 20, y: 10}, chassisOf).x, 130);
  assert.equal(F.facePoint(r, {...it, turned: true}, {x: 20, y: 10, view: 'rear'}, chassisOf).x, -130);
  assert.equal(F.facePoint(r, it, {x: 20, y: 10, view: 'rear'}, chassisOf).x, 130);
  // rolled 180: the same point, turned about the centre of the box
  const o = F.facePoint(r, {...it, roll: 180}, {x: 20, y: 10}, chassisOf);
  assert.equal(o.x, 130); near(o.y, box.y0 + 10, 'up from the bottom of the body');
  // rolled 90 clockwise on the front: the top-left corner goes to the top-right
  const q = {...it, roll: 90}, qb = F.itemBox(r, q, chassisOf);
  const tl = F.facePoint(r, q, {x: 0, y: 0}, chassisOf);
  near(tl.x, 44, 'the right edge of a box 88 across'); near(tl.y, qb.y1, 'its top');
  const tr = F.facePoint(r, q, {x: 300, y: 0}, chassisOf);
  near(tr.x, 44, 'right edge'); near(tr.y, qb.y0, 'the top-right corner goes to the bottom-right');
  // 270 is the other way, and on the rear the sense is as that face is seen
  near(F.facePoint(r, {...it, roll: 270}, {x: 0, y: 0}, chassisOf).x, -44, 'left edge');
  near(F.facePoint(r, {...it, roll: 90, face: 'rear'}, {x: 0, y: 0}, chassisOf).x, -44, 'top-left, seen from the rear, goes to its top-right');
});

// ── a quarter turn ───────────────────────────────────────────────────────

test('a quarter-turned item takes its rolled units and refuses a neighbour', () => {
  // 300 mm wide and 2U: rolled a quarter turn it is 300 / 44.45 = 6.75, so 7 units, and 88 mm across
  let r = put(rackOf(), 'fx', 10, {label: 'fx'});
  assert.deepEqual(F.spanOf(r.items[0], chassisOf), [10, 12]);
  const turned = run(r, {op: 'patch', id: 'i1', roll: 90});
  assert.equal(turned.error, undefined);
  r = turned.rack;
  assert.equal(r.items[0].roll, 90);
  assert.equal(F.itemUnits(r.items[0], chassisOf), 7);
  assert.deepEqual(F.spanOf(r.items[0], chassisOf), [10, 17]);
  assert.deepEqual(F.itemsWithU(r, chassisOf).map(i => i.u), [7]);
  const box = F.itemBox(r, r.items[0], chassisOf);
  assert.deepEqual([box.h, box.w, box.lo, box.hi], [300, 88, 9 * RU, 16 * RU]);
  near(box.y0 - box.lo, box.hi - box.y1, 'centred up its seven units');
  // a neighbour in a unit it now fills is refused, and the unit above it is free
  assert.deepEqual(F.fits(r, {ref: 'sw', ru: 16, face: 'front'}, chassisOf), {ok: false, reason: 'Taken by fx on the front.'});
  assert.deepEqual(F.fits(r, {ref: 'sw', ru: 17, face: 'front'}, chassisOf), {ok: true});
  assert.deepEqual(F.fits(rackOf(), {ref: 'sw', ru: 16, face: 'front'}, chassisOf), {ok: true});
  assert.ok(Q.describe(r, {chassisOf}).split('\n').includes('i1 fx U10-U16 front rolled 90'));
  // refused where the rolled box does not fit: a device in a unit it would take
  const tight = put(put(rackOf(), 'fx', 10, {label: 'fx'}), 'sw', 14, {label: 'leaf'});
  assert.deepEqual(run(tight, {op: 'patch', id: 'i1', roll: 270}), {error: 'Taken by leaf on the front.', index: 0});
  assert.equal(run(tight, {op: 'patch', id: 'i1', roll: 180}).rack.items[0].roll, 180, 'a half turn is the same box');
  // past the top of the rack
  assert.deepEqual(run(put(rackOf(), 'fx', 40), {op: 'patch', id: 'i1', roll: 90}), {error: '7U needed; 3U free from U40 to the top.', index: 0});
  // its height has to pass between the rails
  assert.deepEqual(run(put(rackOf(), 'wide', 1), {op: 'patch', id: 'i1', roll: 90}), {index: 0, error:
    'WIDE-13 is 577 mm high; rolled a quarter turn that is across the opening, which is 451 mm.'});
  // a part on the rail face is refused a quarter turn, across both rails or on one; a half turn it takes
  const face = put(put(rackOf(), 'bracket', 5, {side: 'left', label: 'fb'}), 'bracket', 8, {label: 'wide'});
  for (const id of ['i1', 'i2']) for (const q of [90, 270])
    assert.deepEqual(run(face, {op: 'patch', id, roll: q}), {error: 'Bracket bolts to the rail face, so it cannot be rolled a quarter turn.', index: 0});
  assert.equal(run(face, {op: 'patch', id: 'i1', roll: 180}).rack.items[0].roll, 180);
  // null puts it upright again, and the key goes
  const back = run(r, {op: 'patch', id: 'i1', roll: null});
  assert.equal('roll' in back.rack.items[0], false);
  assert.equal(run(back.rack, {op: 'patch', id: 'i1', roll: null}).noop, true);
});

test('a quarter-turned item is an outline: one solid, no tray, no ring, and a notice', () => {
  let r = G.add({...M.newRack(), items: []}, 'fhd-cmp5dr', 12, {label: 'Mq'});
  const ctx = {...G.ctxOf(), guidesOf: id => (id === 'i1' ? G.RINGS : [])};
  assert.ok(S.solidsOf(r, ctx).length > 10 && S.traysOf(r, ctx).length === 1);
  r = roll(r, 'i1', 90);
  const solids = S.solidsOf(r, ctx);
  assert.deepEqual(solids.map(s => s.part), ['envelope']);
  const c = G.chassisOf('fhd-cmp5dr'), box = F.itemBox(r, r.items[0], G.chassisOf);
  near(solids[0].box.x1 - solids[0].box.x0, c.h, 'its height lies across');
  near(solids[0].box.x0, -c.h / 2, 'centred across the opening');
  near(solids[0].box.y0, box.y0, 'on the rolled box'); near(solids[0].box.y1, box.y1, 'on the rolled box');
  assert.deepEqual(S.traysOf(r, ctx), []);
  assert.deepEqual(F.frameNotices(r, G.chassisOf), ['Mq is rolled a quarter turn: it is fitted by its rolled box and drawn turned in the elevation; its 3D solid and its cables are an outline, since how it mounts that way is not described yet.']);
  assert.deepEqual(F.frameNotices(roll(r, 'i1', 180), G.chassisOf), []);
});

test('a port box stands where the body does: a span covers the port of a rolled item where the roll puts it', () => {
  // three switches; a cord from the lowest to the highest runs up in front of
  // the middle one at x -100. Its one listed port is at x +100 upright.
  let r = rackOf();
  for (const ru of [10, 11, 12]) r = put(r, 'sw', ru, {label: `s${ru}`});
  const c = {id: 'c1', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i3', path: 'p', view: 'front'}, media: 'om4', route: []};
  r = {...r, cables: [c]};
  const ctxOf = rr => ({chassisOf, guidesOf: () => [], portX: () => -100,
    portY: e => (rr.items.find(i => i.id === e.item).ru - 0.5) * RU,
    portBoxesOf: id => (id === 'i2' ? [{path: 'q', view: 'front', x: 100, y: 10.5 * RU + 5, w: 12, h: 10}] : [])});
  assert.deepEqual(R.routePath(r, c, ctxOf(r)).covers, [], 'upright, the port is 200 mm from the span');
  const over = roll(r, 'i2', 180);
  const covers = R.routePath(over, c, ctxOf(over)).covers;
  assert.deepEqual(covers.map(f => [f.kind, f.item, f.path]), [['port-behind-span', 'i2', 'q']], 'turned over, it is behind the span');
  // and the path itself is the same: the ends are not on the rolled item
  assert.deepEqual(R.routePath(over, c, ctxOf(over)).points.map(q => q.x), R.routePath(r, c, ctxOf(r)).points.map(q => q.x));
});

test('an upright rack is untouched by any of it', () => {
  const r = put(put(rackOf(), 'sw', 10), 'half', 12.5);
  for (const it of r.items) {
    assert.equal(F.itemUnits(it, chassisOf), F.unitsOf(chassisOf(it.ref)));
    assert.deepEqual(Object.keys(F.itemBox(r, it, chassisOf)), ['y0', 'y1', 'h', 'lo', 'hi']);
  }
});
