// spec/tests/js/rack-roll-elevation.mjs
// A device rolled a quarter turn (docs/rack-file-v4-design.md section 6) is
// fitted by its turned footprint and drawn turned in the elevation: 90 is
// clockwise as the face it is on shows it, 270 the other way.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as F from '../../../kit/rack/fit.js';
import {rolledTransform, rolledBracketShapes, drawRolledBrackets} from '../../../kit/rack/view/elevation.js';
import {RU, SIDES} from '../../../kit/rack/rails.js';

// the shelf: 446.5 mm wide, 355 mm high (3FE64936BB)
const SHELF = {ru: 8, w: 446.5, h: 355, d: 278.3, model: 'shelf'};
const chassisOf = ref => (ref === 'shelf' ? SHELF : null);
const item = (extra = {}) => ({id: 'i1', ref: 'shelf', cfg: '', ru: 3, label: 'Shelf', face: 'front', ...extra});

test('a quarter turn is drawn turned about the middle of its box, clockwise for 90', () => {
  assert.equal(rolledTransform(90, false, 225.5, 300), 'rotate(90 225.5 300) ');
  assert.equal(rolledTransform(270, false, 225.5, 300), 'rotate(270 225.5 300) ');
});

test('seen through to the other face the same turn runs the other way round', () => {
  assert.equal(rolledTransform(90, true, 10, 20), 'rotate(-90 10 20) ');
  assert.equal(rolledTransform(270, true, 10, 20), 'rotate(-270 10 20) ');
});

test('an upright or half-turned item gets no turn from this function', () => {
  for (const roll of [undefined, null, 0, 180, 45]) assert.equal(rolledTransform(roll, false, 1, 2), '', String(roll));
});

test('the 446.5 mm shelf rolled a quarter turn stands on its width and is 355 mm across', () => {
  const r = {items: [item({roll: 90})], frame: {heightRU: 42}};
  const box = F.itemBox(r, r.items[0], chassisOf);
  assert.equal(box.h, 446.5, 'its width stands up the rack');
  assert.equal(box.w, 355, 'its height lies across the opening');
  const [lo, hi] = F.spanOf(r.items[0], chassisOf);
  assert.equal(hi - lo, Math.ceil(446.5 / RU), 'whole units, rounded up from its width over one unit');
  assert.equal(box.hi - box.lo, (hi - lo) * RU);
  assert.ok(box.y0 >= box.lo && box.y1 <= box.hi, 'the body is inside its span');
});

test('a clockwise quarter turn carries the shelf bottom to the left of the elevation', () => {
  // the shelf bottom, its middle: the point turned by 90 clockwise from the front lies left of the middle
  const r = {items: [item({roll: 90})], frame: {heightRU: 42}};
  const bottom = {x: 0, y: F.itemBox(r, item(), chassisOf).y0};
  const turned = F.rollPoint(r, r.items[0], bottom, chassisOf);
  assert.ok(turned.x < 0, `clockwise puts the bottom edge on the left, at ${turned.x}`);
  const anti = F.rollPoint({...r, items: [item({roll: 270})]}, item({roll: 270}), bottom, chassisOf);
  assert.ok(anti.x > 0, `anticlockwise puts it on the right, at ${anti.x}`);
});

// ---- the brackets that hold a shelf stood on its side (`chassis.ears.rolled`) ----
// As the library states them for the shelf: a bar across the rack against one edge of
// the body and an ear on each post, rising from the bar's lower edge.
const BELOW = {id: 'below', side: 'below', 'bar-h': 25.4, length: 486.41, 'ear-h': 92.44, 'ear-w': 28, color: '#c8cacc'};
const ABOVE = {id: 'above', side: 'above', 'bar-h': 31.5, length: 486.75, 'ear-h': 62, 'ear-w': 28, color: '#c8cacc'};
const ROLLED = [BELOW, ABOVE];
const boxOf = it => F.itemBox({items: [it], frame: {heightRU: 42}}, it, chassisOf);
const shapesOf = (it, rolled = ROLLED) => rolledBracketShapes(it, rolled, boxOf(it));
const byId = (shapes, id) => shapes.find(s => s.id === id);
const HOLE_X = Math.abs(SIDES[0].hole);

test('a shelf rolled a quarter turn is drawn with both brackets, at 90 and at 270', () => {
  for (const roll of [90, 270]) {
    const shapes = shapesOf(item({roll}));
    assert.deepEqual(shapes.map(s => s.id).sort(), ['above', 'below'], `roll ${roll}`);
  }
});

test('each bracket reaches the post on both sides: its ear covers the hole column', () => {
  for (const roll of [90, 270]) {
    for (const s of shapesOf(item({roll}))) {
      const xs = s.outline.map(p => p[0]);
      assert.ok(Math.min(...xs) < -HOLE_X && Math.max(...xs) > HOLE_X, `${s.id} at ${roll} spans ${Math.min(...xs)}..${Math.max(...xs)}`);
      assert.ok(s.ears.left.x0 < -HOLE_X && s.ears.left.x1 > -HOLE_X, `${s.id} left ear over the left hole column`);
      assert.ok(s.ears.right.x1 > HOLE_X && s.ears.right.x0 < HOLE_X, `${s.id} right ear over the right hole column`);
      assert.ok(s.holes.length >= 2, `${s.id} is bolted at two holes at least`);
    }
  }
});

test('the bars lie against the body, one under it and one over it, and the ears rise from the bar', () => {
  for (const roll of [90, 270]) {
    const it = item({roll}), box = boxOf(it), shapes = shapesOf(it);
    const below = byId(shapes, 'below'), above = byId(shapes, 'above');
    assert.ok(Math.abs(below.bar.y1 - box.y0) < 1e-9, `the lower bar's top is the shelf's bottom edge at ${roll}`);
    assert.ok(Math.abs(below.bar.y1 - below.bar.y0 - 25.4) < 1e-9, 'its bar is the 25.4 mm the data sheet prints');
    assert.ok(Math.abs(above.bar.y0 - box.y1) < 1e-9, `the upper bar's bottom is the shelf's top edge at ${roll}`);
    for (const s of shapes) {
      assert.ok(Math.abs(s.ears.left.y1 - s.ears.left.y0 - (s.id === 'below' ? 92.44 : 62)) < 1e-9, `${s.id}: the ear is as tall as the data states`);
      assert.equal(s.ears.left.y0, s.bar.y0, `${s.id}: the ear stands on the bar's lower edge`);
      assert.ok(s.ears.left.y1 > s.bar.y1, `${s.id}: and rises past the bar`);
    }
    assert.ok(below.bar.y1 <= box.y0 + 1e-9 && above.bar.y0 >= box.y1 - 1e-9, 'neither bar is in front of the shelf');
  }
});

test('the brackets stand the same at 270 as at 90: they are the rack\'s, the drip tray stays under', () => {
  assert.deepEqual(shapesOf(item({roll: 270})), shapesOf(item({roll: 90})));
});

test('both ears of a bracket are mirror images about the centre line of the rack', () => {
  for (const s of shapesOf(item({roll: 90}))) {
    const {left, right} = s.ears;
    assert.ok(Math.abs(left.x0 + right.x1) < 1e-9 && Math.abs(left.x1 + right.x0) < 1e-9, s.id);
    assert.equal(left.y0, right.y0); assert.equal(left.y1, right.y1);
  }
});

test('an upright, half-turned or unstated device draws no bracket', () => {
  for (const roll of [undefined, 0, 180]) assert.deepEqual(shapesOf(item({roll})), [], `roll ${roll}`);
  const turned = item({roll: 90});
  for (const none of [undefined, null, []]) assert.deepEqual(rolledBracketShapes(turned, none, boxOf(turned)), [], String(none));
});

test('a bracket is drawn in the colour its data states, over the rails, with a screw at each of its holes', () => {
  const made = [];
  const svgEl = (tag, attrs) => { const e = {tag, attrs, kids: [], append(...k) { this.kids.push(...k); }}; made.push(e); return e; };
  const out = svgEl('svg', {});
  const it = item({roll: 90});
  drawRolledBrackets(svgEl, out, it, shapesOf(it), mm => 1000 - mm, {ear: '#000', earLine: '#111', earOpacity: 1, screw: '#222', screwLine: '#333'});
  const g = out.kids[0];
  assert.equal(g.attrs['data-brackets-for'], 'i1');
  const paths = g.kids.filter(k => k.tag === 'path');
  assert.deepEqual(paths.map(p => p.attrs['data-bracket']).sort(), ['above', 'below']);
  for (const p of paths) assert.equal(p.attrs.fill, '#c8cacc');
  const wanted = shapesOf(it).reduce((n, s) => n + 2 * s.holes.length, 0);
  assert.equal(g.kids.filter(k => k.tag === 'circle').length, wanted);
});
