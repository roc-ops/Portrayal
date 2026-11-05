// spec/tests/js/rack-roll-elevation.mjs
// A device rolled a quarter turn (docs/rack-file-v4-design.md section 6) is
// fitted by its turned footprint and drawn turned in the elevation: 90 is
// clockwise as the face it is on shows it, 270 the other way.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as F from '../../../kit/rack/fit.js';
import {rolledTransform} from '../../../kit/rack/view/elevation.js';
import {RU} from '../../../kit/rack/rails.js';

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
