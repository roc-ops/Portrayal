// spec/tests/js/rack-narrow-device.mjs
// A RACK DEVICE OF HALF THE OPENING OR LESS (docs/half-width-devices-design.md
// sections 2 and 4.1): a `mount: rack` device whose stated width is at most half
// the 450 mm opening is narrow, as a finger bracket is, so one can stand on each
// rail at the same unit. The fraction is derived from the width the device
// already states; no key is added to a device.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as F from '../../../kit/rack/fit.js';
import {COMMANDS} from '../../../kit/rack/commands.js';

// A device states `mount` only when it is not "rack" (fit.js isRackMount).
const SIZES = {
  half: {model: 'HALF-200', ru: 1, h: 44, w: 200, d: 120},
  half2: {model: 'HALF-200-B', ru: 1, h: 44, w: 200, d: 120},
  edge: {model: 'EDGE-225', ru: 1, h: 44, w: 225, d: 120},
  over: {model: 'OVER-226', ru: 1, h: 44, w: 226, d: 120},
  full: {model: 'FULL-440', ru: 1, h: 44, w: 440, d: 300},
  tall: {model: 'TALL-200', ru: 2, h: 88, w: 200, d: 120},
  bracket: {model: 'BRACKET-60', ru: 1, h: 44, w: 60, d: 20, mount: 'rack-face'},
  wideface: {model: 'FACE-450', ru: 1, h: 44, w: 450, d: 20, mount: 'rack-face'},
};
const chassisOf = ref => SIZES[ref] || null;
const ctx = {chassisOf, slotsOf: () => null};
const sideOf = (rack, args) => COMMANDS['side.place'].run(rack, {face: 'front', ...args}, ctx);
const plain = (rack, args) => COMMANDS.place.run(rack, {face: 'front', ...args}, ctx);
const empty = () => M.newRack();

test('a rack device is narrow when twice its width fits the opening, and a rack-face part keeps its own rule', () => {
  assert.equal(F.isNarrow(SIZES.half), true);
  assert.equal(F.isNarrow(SIZES.edge), true, '225 mm: two of them make 450 mm, the opening');
  assert.equal(F.isNarrow(SIZES.over), false, '226 mm: two of them are wider than the opening');
  assert.equal(F.isNarrow(SIZES.full), false, 'an ordinary 440 mm device spans the opening');
  assert.equal(F.isNarrow({ru: 1, mount: undefined}), false, 'no stated width is never narrow');
  assert.equal(F.isNarrow(SIZES.bracket), true);
  assert.equal(F.isNarrow(SIZES.wideface), false, 'a rack-face part stays judged against 450 mm itself');
});

test('two 200 mm devices stand on the two rails of one unit', () => {
  const a = sideOf(empty(), {ref: 'half', ru: 5, side: 'left'});
  assert.equal(a.summary, 'Placed HALF-200 at U5 on the front, on the left rail.');
  const b = sideOf(a.rack, {ref: 'half2', ru: 5, side: 'right'});
  assert.equal(b.summary, 'Placed HALF-200-B at U5 on the front, on the right rail.');
  assert.deepEqual(b.rack.items.map(i => [i.ref, i.ru, i.side]), [['half', 5, 'left'], ['half2', 5, 'right']]);
});

test('a third device, or a second on one rail, is refused and names the rail', () => {
  const a = sideOf(empty(), {ref: 'half', ru: 5, side: 'left'}).rack;
  assert.equal(sideOf(a, {ref: 'half2', ru: 5, side: 'left'}).error, 'Taken by HALF-200 on the front, left rail.');
  const b = sideOf(a, {ref: 'half2', ru: 5, side: 'right'}).rack;
  assert.equal(sideOf(b, {ref: 'half2', ru: 5, side: 'right'}).error, 'Taken by HALF-200-B on the front, right rail.');
});

test('a 200 mm device with no side takes both rails, and a full-width device takes both', () => {
  const a = sideOf(empty(), {ref: 'half', ru: 5, side: 'left'}).rack;
  assert.equal(plain(a, {ref: 'half2', ru: 5}).error, 'Taken by HALF-200 on the front, left rail.');
  assert.equal(plain(a, {ref: 'full', ru: 5}).error, 'Taken by HALF-200 on the front, left rail.');
  const whole = plain(empty(), {ref: 'half', ru: 5}).rack;
  assert.equal(sideOf(whole, {ref: 'half2', ru: 5, side: 'right'}).error, 'Taken by HALF-200 on the front.');
});

test('the rails are judged by the units each device fills', () => {
  const a = sideOf(empty(), {ref: 'tall', ru: 5, side: 'left'}).rack;                // U5-U6, left
  assert.equal(sideOf(a, {ref: 'half2', ru: 6, side: 'right'}).error, undefined, 'the right rail of U6 is free');
  assert.equal(sideOf(a, {ref: 'half2', ru: 6, side: 'left'}).error, 'Taken by TALL-200 on the front, left rail.');
});

test('a device wider than half the opening has no side', () => {
  assert.equal(sideOf(empty(), {ref: 'full', ru: 5, side: 'left'}).error, 'FULL-440 spans the opening, so it has no side.');
  assert.equal(sideOf(empty(), {ref: 'over', ru: 5, side: 'left'}).error, 'OVER-226 spans the opening, so it has no side.');
});

test('side.set moves a 200 mm device across, refuses a taken rail, and frees it', () => {
  const a = sideOf(empty(), {ref: 'half', ru: 5, side: 'left'}).rack;
  const b = sideOf(a, {ref: 'half2', ru: 5, side: 'right'}).rack;
  assert.equal(COMMANDS['side.set'].run(b, {id: 'i1', side: 'right'}, ctx).error, 'Taken by HALF-200-B on the front, right rail.');
  const moved = COMMANDS['side.set'].run(a, {id: 'i1', side: 'right'}, ctx);
  assert.equal(moved.summary, 'Put HALF-200 on the right rail.');
  assert.equal(COMMANDS['side.set'].run(b, {id: 'i1', side: null}, ctx).error, 'Taken by HALF-200-B on the front, right rail.');
  assert.equal(COMMANDS['side.set'].run(a, {id: 'i1', side: null}, ctx).summary, 'Put HALF-200 across both rails.');
});

test('a 200 mm device rolled a quarter turn cannot be on one rail', () => {
  const rolled = {...empty(), items: [{id: 'i1', ref: 'half', cfg: '', ru: 5, face: 'front', label: 'a', side: 'left', roll: 90}]};
  assert.equal(F.fits(rolled, {id: 'i2', ref: 'half2', cfg: '', ru: 5, face: 'front', label: 'b', side: 'right'}, chassisOf).ok, false,
    'rolled, it stands across the unit: no side is read for it');
});

test('the rail of a rack device is read as a rail, and a side on a wide one is dropped as before', () => {
  const rack = {...empty(), items: [
    {id: 'i1', ref: 'half', cfg: '', ru: 5, face: 'front', label: 'a', side: 'left'},
    {id: 'i2', ref: 'half2', cfg: '', ru: 5, face: 'front', label: 'b', side: 'right'},
    {id: 'i3', ref: 'full', cfg: '', ru: 9, face: 'front', label: 'c', side: 'left'}]};
  assert.equal(F.railOf(rack.items[0], chassisOf), 'left');
  assert.equal(F.railOf(rack.items[1], chassisOf), 'right');
  assert.equal(F.railOf(rack.items[2], chassisOf), null);
  assert.deepEqual(F.itemsWithU(rack, chassisOf).map(i => [i.id, i.side ?? null]), [['i1', 'left'], ['i2', 'right'], ['i3', null]]);
  assert.equal(F.fits(rack, rack.items[1], chassisOf, {ignoreId: 'i2'}).ok, true);
});

test('a rack device on a rail is named in the frame notices, because its drawing does not follow yet', () => {
  const on = side => ({...empty(), items: [{id: 'i1', ref: 'half', cfg: '', ru: 5, face: 'front', label: 'left-box', side}]});
  assert.deepEqual(F.frameNotices(on('left'), chassisOf),
    ['left-box is on the left rail and fitted by it. Its elevation, 3D view and DCIM files do not stand it there yet.']);
  assert.deepEqual(F.frameNotices(on('right'), chassisOf),
    ['left-box is on the right rail and fitted by it. Its elevation, 3D view and DCIM files do not stand it there yet.']);
  assert.deepEqual(F.frameNotices(on(undefined), chassisOf), [], 'a device with no side says nothing');
  const bracket = {...empty(), items: [{id: 'i1', ref: 'bracket', cfg: '', ru: 5, face: 'front', label: 'br', side: 'left'}]};
  assert.deepEqual(F.frameNotices(bracket, chassisOf), [], 'a rack-face part on a rail is drawn and says nothing');
});
