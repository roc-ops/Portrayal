import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as F from '../../../kit/rack/fit.js';

// Real sizes (assets/dist configs.json, 2026-09-26).
const SIZES = {
  'r740xd': {ru: 2, h: 86.8, d: 737.5}, 'as7726-32x': {ru: 1, h: 43.5, d: 515.0},
  'fhd-1ufce': {ru: 1, h: 44.0, d: 432.8}, 'tm-280': {ru: 1, h: 43.6, d: 140.5},
  'mx10004': {ru: 7, h: 311, d: 932.0}, 'pdu-v': {ru: 0, h: 1200, d: 60, mount: 'rack-side'},
  'fhd-cmp5dr': {ru: 1, h: 44, d: 110, mount: 'rack-face', shell: 'sheet'}, 'deep-1u': {ru: 1, h: 44, d: 800},
};
const chassisOf = ref => SIZES[ref] || null;
const place = (rack, ref, ru, face = 'front', label = ref.toUpperCase()) =>
  M.withItem(rack, {ref, cfg: 'x', ru, face, label}).rack;

test('a device fits in an empty four-post rack', () => {
  assert.deepEqual(F.fits(M.newRack(), {ref: 'r740xd', ru: 10, face: 'front'}, chassisOf), {ok: true});
});

test('height: below U1 or past the top is refused', () => {
  const r = M.newRack();
  assert.equal(F.fits(r, {ref: 'tm-280', ru: 0, face: 'front'}, chassisOf).reason, 'Below U1.');
  assert.equal(F.fits(r, {ref: 'mx10004', ru: 40, face: 'front'}, chassisOf).reason,
    '7U needed; 3U free from U40 to the top.');
});

test('an unknown device is refused, not guessed at', () => {
  assert.equal(F.fits(M.newRack(), {ref: 'nope', ru: 1, face: 'front'}, chassisOf).reason,
    'No size is known for nope.');
});

test('the same face never shares a U', () => {
  const r = place(M.newRack(), 'r740xd', 10);       // U10-U11
  assert.equal(F.fits(r, {ref: 'tm-280', ru: 11, face: 'front'}, chassisOf).reason,
    'Taken by R740XD on the front.');
  assert.deepEqual(F.fits(r, {ref: 'tm-280', ru: 12, face: 'front'}, chassisOf), {ok: true});
});

test('four-post: opposite faces share a U when their depths fit the rail depth', () => {
  const r = place(M.newRack(), 'as7726-32x', 20);   // 515 mm, front
  assert.deepEqual(F.fits(r, {ref: 'tm-280', ru: 20, face: 'rear'}, chassisOf), {ok: true});   // 655.5 <= 740
  assert.equal(F.fits(r, {ref: 'fhd-1ufce', ru: 20, face: 'rear'}, chassisOf).reason,
    '433 mm deep; 225 mm free behind AS7726-32X.');                                         // 947.8 > 740
});

test('four-post: a boundary sum exactly equal to the rail depth fits', () => {
  const r = place(M.withFrame(M.newRack(), {railDepth: 655.5}), 'as7726-32x', 20);
  assert.deepEqual(F.fits(r, {ref: 'tm-280', ru: 20, face: 'rear'}, chassisOf), {ok: true});
});

test('two-post: front and rear never share a U', () => {
  const r = place(M.newRack({kind: 'two-post'}), 'tm-280', 5);
  assert.equal(F.fits(r, {ref: 'tm-280', ru: 5, face: 'rear'}, chassisOf).reason,
    'Taken by TM-280; two-post rails are shared by front and rear.');
});

test('usable depth caps any device, on either face', () => {
  const r = M.withFrame(M.newRack(), {usableDepth: 900});
  assert.equal(F.fits(r, {ref: 'mx10004', ru: 1, face: 'rear'}, chassisOf).reason,
    '932 mm deep; this rack allows 900 mm.');
});

test('ignoreId lets an item be checked against everything but itself (moves)', () => {
  const r = place(M.newRack(), 'r740xd', 10);
  assert.deepEqual(F.fits(r, {ref: 'r740xd', ru: 11, face: 'front'}, chassisOf, {ignoreId: 'i1'}), {ok: true});
});

test('reaches: a full-depth device shows its other panel; a short one is a ghost', () => {
  const r = place(place(M.newRack(), 'r740xd', 10), 'tm-280', 20);
  assert.equal(F.reaches(r.items[0], r, chassisOf), true);     // 737.5 >= 740 - 50
  assert.equal(F.reaches(r.items[1], r, chassisOf), false);    // 140.5
  const two = place(M.newRack({kind: 'two-post'}), 'tm-280', 20);
  assert.equal(F.reaches(two.items[0], two, chassisOf), true, 'two-post has one plane');
});

test('availableDepth: what is left behind the other face, or the usable depth', () => {
  const r = place(place(M.newRack(), 'as7726-32x', 20), 'tm-280', 20, 'rear');
  assert.equal(F.availableDepth(r, r.items[1], chassisOf), 740 - 515);
  assert.equal(F.availableDepth(r, r.items[0], chassisOf), 740 - 140.5);
  const alone = place(M.newRack(), 'r740xd', 1);
  assert.equal(F.availableDepth(alone, alone.items[0], chassisOf), 1000);
});

test('itemsWithU: every item carries its chassis U height, or 1 when unknown', () => {
  const r = place(place(M.newRack(), 'r740xd', 10), 'unknown-ref', 20);
  const got = F.itemsWithU(r, chassisOf).map(i => [i.ref, i.u]);
  assert.deepEqual(got, [['r740xd', 2], ['unknown-ref', 1]]);
});

test('zero-U: only the frame\'s attachment points, and never overlapping', () => {
  assert.deepEqual(F.attachPoints('four-post'), ['left-front', 'right-front', 'left-rear', 'right-rear']);
  assert.deepEqual(F.attachPoints('two-post'), ['left', 'right']);
  let r = M.newRack();
  assert.equal(F.fitsZeroU(r, {ref: 'pdu-v', at: 'left', offsetMm: 0}, chassisOf).reason,
    'left is not an attachment point of a four-post frame: use left-front, right-front, left-rear, right-rear.');
  assert.deepEqual(F.fitsZeroU(r, {ref: 'pdu-v', at: 'left-rear', offsetMm: 0}, chassisOf), {ok: true});
  r = {...r, zeroU: [{id: 'z1', ref: 'pdu-v', at: 'left-rear', offsetMm: 0, label: 'PDU A'}]};
  assert.equal(F.fitsZeroU(r, {ref: 'pdu-v', at: 'left-rear', offsetMm: 600}, chassisOf).reason,
    'Overlaps PDU A at left-rear.');
  // A part that states no U is measured by its height: 1200 mm is 27U, from U21 of 42.
  assert.equal(F.fitsZeroU(r, {ref: 'pdu-v', at: 'right-rear', offsetMm: 900}, chassisOf).reason,
    '27U tall; 22U from U21 to the top of this 42U rack.');
  assert.equal(F.fitsZeroU(r, {ref: 'r740xd', at: 'right-rear', ru: 1}, chassisOf).reason,
    'r740xd does not stand beside the rack: it goes on the rails.');
});

// shrinkRack (feedback round 2 §2): compact, then trim from the bottom.

test('shrinkRack: nothing moves when everything already fits', () => {
  let r = place(M.newRack(), 'r740xd', 5);   // U5-U6
  r = place(r, 'tm-280', 20);                // U20
  const {rack: next, moved, removed} = F.shrinkRack(r, 25, chassisOf);
  assert.equal(next.frame.heightRU, 25);
  assert.deepEqual(moved, []);
  assert.deepEqual(removed, []);
  assert.deepEqual(next.items.map(i => i.ru), [5, 20]);
});

test('shrinkRack: gaps close in order, packing from U1', () => {
  let r = place(M.newRack(), 'tm-280', 5, 'front', 'A');
  r = place(r, 'as7726-32x', 20, 'front', 'B');
  r = place(r, 'fhd-1ufce', 30, 'front', 'C');
  const {rack: next, moved, removed} = F.shrinkRack(r, 12, chassisOf);
  assert.equal(next.frame.heightRU, 12);
  assert.deepEqual(next.items.map(i => [i.label, i.ru]), [['A', 1], ['B', 2], ['C', 3]]);
  assert.deepEqual(moved.slice().sort(), next.items.map(i => i.id).sort());
  assert.deepEqual(removed, []);
});

test('shrinkRack: a front/rear pair sharing a U moves together', () => {
  let r = place(M.newRack(), 'r740xd', 3, 'front', 'BASE');    // U3-U4, its own cluster
  r = place(r, 'as7726-32x', 20, 'front', 'FRONT');
  r = place(r, 'tm-280', 20, 'rear', 'REAR');                  // shares U20 with FRONT
  const {rack: next} = F.shrinkRack(r, 10, chassisOf);
  const front = next.items.find(i => i.label === 'FRONT');
  const rear = next.items.find(i => i.label === 'REAR');
  assert.equal(front.ru, rear.ru);
});

test('shrinkRack: the bottom cluster is removed first, the rest re-packs from U1, both are reported', () => {
  let r = place(M.newRack(), 'tm-280', 5, 'front', 'A');       // 1U, lowest - goes first
  r = place(r, 'as7726-32x', 20, 'front', 'B');                // 1U
  r = place(r, 'r740xd', 30, 'front', 'C');                    // 2U
  const {rack: next, moved, removed} = F.shrinkRack(r, 3, chassisOf);
  assert.equal(next.frame.heightRU, 3);
  assert.deepEqual(removed.map(i => i.label), ['A']);
  assert.deepEqual(next.items.map(i => [i.label, i.ru]), [['B', 1], ['C', 2]]);
  assert.deepEqual(moved.slice().sort(), next.items.map(i => i.id).sort());
});

test('shrinkRack: shrinking to exactly the packed height removes nothing', () => {
  let r = place(M.newRack(), 'tm-280', 5, 'front', 'A');
  r = place(r, 'as7726-32x', 20, 'front', 'B');
  r = place(r, 'fhd-1ufce', 30, 'front', 'C');
  const {rack: next, removed} = F.shrinkRack(r, 3, chassisOf);
  assert.deepEqual(removed, []);
  assert.deepEqual(next.items.map(i => [i.label, i.ru]), [['A', 1], ['B', 2], ['C', 3]]);
});

test('shrinkRack: cluster membership is transitive - A overlaps B, B overlaps C, so all three pack together', () => {
  // A (2U, front, U10-11) overlaps B (2U, rear, U11-12); B overlaps C (1U,
  // front, U12) - A and C never touch directly, but share a cluster via B.
  let r = place(M.newRack(), 'r740xd', 10, 'front', 'A');
  r = place(r, 'r740xd', 11, 'rear', 'B');
  r = place(r, 'tm-280', 12, 'front', 'C');
  const {rack: next, moved} = F.shrinkRack(r, 5, chassisOf);
  const byLabel = label => next.items.find(i => i.label === label);
  assert.deepEqual(['A', 'B', 'C'].map(l => byLabel(l).ru), [1, 2, 3]);
  // Faces and each item's offset within the cluster are untouched - only the
  // whole cluster moved.
  assert.equal(byLabel('A').face, 'front');
  assert.equal(byLabel('B').face, 'rear');
  assert.equal(byLabel('C').face, 'front');
  assert.deepEqual(moved.slice().sort(), next.items.map(i => i.id).sort());
});

test('shrinkRack: rack.items keeps its original order - only positions (and membership) change', () => {
  // Placed out of U order: X at U30, Y at U5, Z at U20.
  let r = place(M.newRack(), 'tm-280', 30, 'front', 'X');
  r = place(r, 'as7726-32x', 5, 'front', 'Y');
  r = place(r, 'fhd-1ufce', 20, 'front', 'Z');
  const before = r.items.map(i => i.id);
  const {rack: next} = F.shrinkRack(r, 12, chassisOf);
  assert.deepEqual(next.items.map(i => i.id), before, 'shrinkRack must not reorder rack.items');
  assert.deepEqual(next.items.map(i => [i.label, i.ru]), [['X', 3], ['Y', 1], ['Z', 2]]);
});

const mgr = (rack, ru, face = 'front', extra = {}) =>
  M.withItem(rack, {ref: 'fhd-cmp5dr', cfg: 'x', ru, face, label: `MGR${ru}${face[0]}`, ...extra}).rack;

test('rack-face: one manager per U per face; the other face is free', () => {
  const r = mgr(M.newRack(), 20);
  assert.equal(F.fits(r, {ref: 'fhd-cmp5dr', ru: 20, face: 'front'}, chassisOf).reason, 'Taken by MGR20f on the front.');
  assert.deepEqual(F.fits(r, {ref: 'fhd-cmp5dr', ru: 20, face: 'rear'}, chassisOf), {ok: true});
});

test('rack-face: a manager and a rack device share a U, either way round', () => {
  const r = place(M.newRack(), 'as7726-32x', 20);
  assert.deepEqual(F.fits(r, {ref: 'fhd-cmp5dr', ru: 20, face: 'front', on: 'i1', unit: 1}, chassisOf), {ok: true});
  assert.deepEqual(F.fits(mgr(M.newRack(), 20), {ref: 'as7726-32x', ru: 20, face: 'front'}, chassisOf), {ok: true});
});

test('rack-face: past the top is refused', () => {
  assert.equal(F.fits(M.newRack(), {ref: 'fhd-cmp5dr', ru: 43, face: 'front'}, chassisOf).reason,
    'U43 is past the top of this 42U rack.');
});

test('rack-face: a rear manager is refused where a front device reaches past the rear rail', () => {
  const r = place(M.newRack(), 'deep-1u', 10);     // 800 mm > 740 rail depth
  assert.equal(F.fits(r, {ref: 'fhd-cmp5dr', ru: 10, face: 'rear'}, chassisOf).reason,
    'DEEP-1U is 800 mm deep and reaches past the rear rail; a rear manager here would hit it.');
  assert.equal(F.fits(mgr(M.newRack(), 10, 'rear'), {ref: 'deep-1u', ru: 10, face: 'front'}, chassisOf).reason,
    '800 mm deep; it would reach past the rear rail into MGR10r.');
});

test('rack-face: two-post rails pass every body, so a rear manager needs an empty U', () => {
  const r = place(M.newRack({kind: 'two-post'}), 'tm-280', 5);
  assert.match(F.fits(r, {ref: 'fhd-cmp5dr', ru: 5, face: 'rear'}, chassisOf).reason, /reaches past the rear rail/);
  assert.deepEqual(F.fits(r, {ref: 'fhd-cmp5dr', ru: 6, face: 'rear'}, chassisOf), {ok: true});
});

test('rack-face: a host is a rack device on the same face, and the unit is within its height', () => {
  const r = place(M.newRack(), 'r740xd', 10);      // 2U, front
  assert.equal(F.fits(r, {ref: 'fhd-cmp5dr', ru: 12, face: 'front', on: 'i1', unit: 3}, chassisOf).reason,
    'R740XD is 2U; there is no unit 3 on it.');
  assert.equal(F.fits(r, {ref: 'fhd-cmp5dr', ru: 10, face: 'rear', on: 'i1', unit: 1}, chassisOf).reason,
    'R740XD is on the front; a manager on it goes on the front too.');
});

test('availableDepth ignores managers: they stand outside the rails', () => {
  const r = mgr(place(M.newRack(), 'as7726-32x', 20), 20, 'rear');
  assert.equal(F.availableDepth(r, r.items[0], chassisOf), r.frame.usableDepth);
});

test('shrinkRack moves a hosted manager with its host, and drops it with its host', () => {
  let r = place(M.newRack(), 'as7726-32x', 30);
  r = mgr(r, 30, 'front', {on: 'i1', unit: 1});
  const {rack: s} = F.shrinkRack(r, 10, chassisOf);
  assert.deepEqual(s.items.map(i => i.ru), [1, 1]);
  r = place(place(M.newRack(), 'tm-280', 1), 'as7726-32x', 2);
  r = mgr(r, 1, 'front', {on: 'i1', unit: 1});
  const {rack: t, removed} = F.shrinkRack(r, 1, chassisOf);
  assert.deepEqual(removed.map(i => i.id).sort(), ['i1', 'i3']);
  assert.deepEqual(t.items.map(i => i.id), ['i2']);
});
