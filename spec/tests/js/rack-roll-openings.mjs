// spec/tests/js/rack-roll-openings.mjs
// The row of holes or slots along a rolled bracket's bar (`strip`) and the slots in each
// ear (`ear-slots`): where they stand, what is drawn for them, and that a bracket that
// states neither is shaped and drawn exactly as before.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as F from '../../../kit/rack/fit.js';
import {rolledBracketShapes, drawRolledBrackets} from '../../../kit/rack/view/elevation.js';

globalThis.location = new URL('http://localhost/rack.html');

const SHELF = {ru: 8, w: 446.5, h: 355, d: 278.3, model: 'shelf'};
const chassisOf = ref => (ref === 'shelf' ? SHELF : null);
const it = {id: 'i1', ref: 'shelf', cfg: '', ru: 3, label: 'Shelf', face: 'front', roll: 90};
const box = F.itemBox({items: [it], frame: {heightRU: 42}}, it, chassisOf);
const PLAIN = {id: 'below', side: 'below', 'bar-h': 25.4, length: 486.41, 'ear-h': 92.44, 'ear-w': 28};
const ROUND = {count: 17, pitch: 25.4, size: [5, 5]};
const SLOTS = {count: 2, pitch: 60, size: [6, 14]};
const shape = b => rolledBracketShapes(it, [b], box)[0];

test('a bracket that states neither key has neither in its shape', () => {
  const s = shape(PLAIN);
  assert.equal('strip' in s, false);
  assert.equal('earSlots' in s, false);
});

test('the strip row has its count, is centred on the rack and stands pitch apart on the bar middle', () => {
  const s = shape({...PLAIN, strip: ROUND});
  assert.equal(s.strip.length, 17);
  assert.ok(Math.abs(s.strip[0].cx + s.strip[16].cx) < 1e-9, 'centred');
  assert.ok(Math.abs(s.strip[16].cx - 8 * 25.4) < 1e-9, 'the last is eight pitches from the middle');
  assert.ok(Math.abs(s.strip[1].cx - s.strip[0].cx - 25.4) < 1e-9, 'one pitch apart');
  for (const o of s.strip) assert.ok(Math.abs(o.cy - (s.bar.y0 + s.bar.y1) / 2) < 1e-9 && o.shape === 'round');
  for (const o of s.strip) assert.deepEqual([o.w, o.h], [5, 5], 'the round hole is the size the data states');
});

test('a row that is wider than the bar between the ears is still the row the data states', () => {
  const s = shape({...PLAIN, strip: {count: 11, pitch: 35, size: [30, 4], shape: 'slot'}});
  assert.equal(s.strip.length, 11);
  assert.ok(s.strip.every(o => o.shape === 'slot' && o.w === 30 && o.h === 4));
  assert.ok(Math.abs(s.strip[1].cx - s.strip[0].cx - 35) < 1e-9, 'the slots stand 35 mm apart');
  assert.ok(Math.abs(s.strip[10].cx + s.strip[0].cx) < 1e-9, 'centred');
});

test('each ear has its slots, the same on both, centred on the ear height', () => {
  const s = shape({...PLAIN, 'ear-slots': SLOTS});
  assert.equal(s.earSlots.length, 4);
  const left = s.earSlots.filter(o => o.cx < 0), right = s.earSlots.filter(o => o.cx > 0);
  assert.equal(left.length, 2);
  assert.deepEqual(left.map(o => o.cy), right.map(o => o.cy));
  const mid = (s.ears.left.y0 + s.ears.left.y1) / 2;
  assert.ok(Math.abs((left[0].cy + left[1].cy) / 2 - mid) < 1e-9);
  assert.ok(Math.abs(left[1].cy - left[0].cy - 60) < 1e-9);
  assert.ok(left.every(o => o.cx > s.ears.left.x0 && o.cx < s.ears.left.x1));
  assert.ok(s.earSlots.every(o => o.shape === 'slot' && o.w === 6 && o.h === 14), 'each slot is the size the data states');
  assert.ok(Math.abs(left[0].cx + right[0].cx) < 1e-9, 'mirror images about the centre line');
});

test('the drawing adds one opening for each, a rect for a slot and an ellipse for a hole', () => {
  const made = [];
  const svgEl = (tag, attrs) => { const e = {tag, attrs, kids: [], append(...k) { this.kids.push(...k); }}; made.push(e); return e; };
  const out = svgEl('svg', {});
  const C = {ear: '#000', earLine: '#111', earOpacity: 1, screw: '#222', screwLine: '#333'};
  const s = rolledBracketShapes(it, [{...PLAIN, strip: ROUND, 'ear-slots': SLOTS}], box);
  drawRolledBrackets(svgEl, out, it, s, mm => 1000 - mm, C);
  const kids = out.kids[0].kids;
  assert.equal(kids.filter(k => k.tag === 'ellipse').length, 17);
  assert.equal(kids.filter(k => k.tag === 'rect').length, 4);
  for (const e of kids.filter(k => k.tag === 'ellipse')) assert.deepEqual([e.attrs.rx, e.attrs.ry], [2.5, 2.5], 'a 5 mm hole');
  for (const r of kids.filter(k => k.tag === 'rect')) {
    assert.deepEqual([r.attrs.width, r.attrs.height, r.attrs.rx], [6, 14, 3], 'a 6 by 14 mm slot, ends rounded');
    assert.equal(r.attrs['data-opening'], 'slot');
  }
  const first = kids.filter(k => k.tag === 'ellipse')[0];
  const sh = s[0];
  assert.ok(Math.abs(first.attrs.cx - (225.425 + sh.strip[0].cx)) < 1e-6, 'drawn at its x on the centre line');
  assert.ok(Math.abs(first.attrs.cy - (1000 - sh.strip[0].cy)) < 1e-6, 'drawn at its y');
  const slotted = svgEl('svg', {});
  drawRolledBrackets(svgEl, slotted, it, rolledBracketShapes(it, [{...PLAIN, strip: {shape: 'slot', count: 3, pitch: 35, size: [30, 4]}}], box), mm => 1000 - mm, C);
  assert.equal(slotted.kids[0].kids.filter(k => k.tag === 'rect').length, 3, 'a strip of slots is drawn as rects');
  const plain = svgEl('svg', {});
  drawRolledBrackets(svgEl, plain, it, rolledBracketShapes(it, [PLAIN], box), mm => 1000 - mm, C);
  assert.equal(plain.kids[0].kids.filter(k => k.tag === 'ellipse' || k.tag === 'rect').length, 0, 'drawn as before');
});
