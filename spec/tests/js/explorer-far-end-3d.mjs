// Which projections the 3D path index records. A rear fibre is drawn only as a
// projection (`data-of`), so the scene's index must know it under the path it
// is of - but never in place of a part some face really draws.
import test from 'node:test';
import assert from 'node:assert/strict';

const { projectionRecords } = await import('../../../kit/path-index.js');

const proj = (view, of, extra = {}) => ({view, path: of, x0: 0, y0: 0, x1: 1, y1: 1, ...extra});

test('a projection of a path no face draws gets a record under that path', () => {
  const real = new Set(['m/lc01/1']);
  const out = projectionRecords(real, [proj('rear', 'm/mtp2/2')]);
  assert.equal(out.length, 1);
  assert.equal(out[0].view, 'rear');
  assert.equal(out[0].path, 'm/mtp2/2');
});

test('a path with a real node on any face gets no projection record', () => {
  const real = new Set(['m/lc01/1', 'm/mtp2/2']);
  const out = projectionRecords(real, [proj('rear', 'm/mtp2/2'), proj('rear', 'm/other/1')]);
  assert.deepEqual(out.map(r => r.path), ['m/other/1']);
});

test('two projections of one path on one face give one record', () => {
  const out = projectionRecords(new Set(), [proj('rear', 'm/mtp2/2', {x0: 5}), proj('rear', 'm/mtp2/2', {x0: 9})]);
  assert.equal(out.length, 1);
  assert.equal(out[0].x0, 5);
});

test('projections of one path on two faces give a record on each face', () => {
  const out = projectionRecords(new Set(), [proj('rear', 'm/mtp2/2'), proj('top', 'm/mtp2/2')]);
  assert.deepEqual(out.map(r => r.view).sort(), ['rear', 'top']);
});
