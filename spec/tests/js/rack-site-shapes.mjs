// spec/tests/js/rack-site-shapes.mjs
// The call shapes portrayal-site's own `patch` sends, with no ctx.slotsOf.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import {COMMANDS, CLEARED} from '../../../kit/rack/commands.js';
import {ctx, chassisOf} from './slot-fixtures.mjs';

const LEAF = M.withItem(M.newRack(), {ref: 'leaf', cfg: 'base', ru: 10, label: 'leaf-1',
  swaps: {'port-2': 'acme/lr@1'}, fields: {'port-2-occupant': {label: 'x'}}}).rack;
const bare = {chassisOf, compByRef: ctx.compByRef};
const snap = r => JSON.parse(JSON.stringify(r));

test('the inspector shape clears what the item had, and says so', () => {
  const before = snap(LEAF);
  const p = COMMANDS.patch.run(LEAF, {id: 'i1', cfg: 'dc', swaps: {}, fields: {}}, bare);
  assert.deepEqual([p.rack.items[0].cfg, p.rack.items[0].swaps, p.rack.items[0].fields], ['dc', {}, {}]);
  assert.deepEqual(p.findings, [{kind: 'note', text: CLEARED}]);
  assert.deepEqual(snap(LEAF), before);
});

test('the lens shape keeps what is sent', () => {
  const before = snap(LEAF);
  const swaps = {'port-1': 'acme/dac@1'}, fields = {'port-1-occupant': {label: 'y'}};
  const p = COMMANDS.patch.run(LEAF, {id: 'i1', cfg: 'dc', swaps, fields}, bare);
  assert.deepEqual([p.rack.items[0].swaps, p.rack.items[0].fields], [swaps, fields]);
  assert.deepEqual(p.findings, []);
  assert.deepEqual(snap(LEAF), before);
});

test('the same configuration is a no-op returning the very same rack', () => {
  const before = snap(LEAF);
  assert.equal(COMMANDS.patch.run(LEAF, {id: 'i1', cfg: 'base'}, bare).rack, LEAF);
  assert.deepEqual(snap(LEAF), before);
});
