// spec/tests/js/rack-port-role.mjs
// THE KIT'S OWN READERS PASS A PORT'S ROLE to connectorOf: a USB receptacle is a
// console end where the placement of the port in its module states
// `role: console`, or the port's own component does, and a USB end where
// neither does. A port of a module in a bay is read by seatedPort.
import test from 'node:test';
import assert from 'node:assert/strict';
import * as M from '../../../kit/rack/model.js';
import * as P from '../../../kit/rack/ports.js';

const comp = (ref, rest) => { const [ns, tail] = ref.split('/'), [name, major] = tail.split('@'); return {ns, name, major: `v${major}`, parts: [], cages: [], bays: {}, attrs: {}, ...rest}; };
const USB = 'generic/usb-c-plug@1';
const jack = id => ({id, kind: 'connector', interface: 'usb-c', media: null, bores: [], accepts: [USB], default: null});
const PLAIN = comp('acme/usb-c@1', {class: 'port', attrs: {media: 'usb-c'}});
const CONSOLE = comp('acme/usb-c-console@1', {class: 'port', attrs: {media: 'usb-c', role: 'console'}});
const CARD = comp('acme/card@1', {class: 'nic', kind: 'module', attrs: {model: 'CARD'},
  parts: [{id: 'placed', ref: 'acme/usb-c@1', attrs: {role: 'console'}}, {id: 'own', ref: 'acme/usb-c-console@1'}, {id: 'none', ref: 'acme/usb-c@1'},
          {id: 'other', ref: 'acme/usb-c@1', attrs: {role: 'storage'}}],
  cages: ['placed', 'own', 'none', 'other'].map(jack)});
const BYREF = {'acme/usb-c@1': PLAIN, 'acme/usb-c-console@1': CONSOLE, 'acme/card@1': CARD, [USB]: comp(USB, {class: 'port', attrs: {connector: 'usb-c'}})};
const compByRef = ref => (ref == null ? null : BYREF[String(ref).split(':')[0]] ?? null);
const SLOTS = {box: {default: 'base', 'pdu-class': null, bays: {front: [], rear: [{id: 'slot-1', group: 'bays', accepts: ['acme/card@1'], default: 'acme/card@1'}]},
  cages: {front: [], rear: []}, configs: [{name: 'base', description: '', airflow: 'passive', bays: {}, occupants: {}}]}};
const ctx = {slotsOf: ref => SLOTS[ref] ?? null, compByRef};
const item = M.withItem(M.newRack(), {ref: 'box', cfg: 'base', ru: 5, label: 'box-1'}).rack.items[0];
const read = id => P.seatedPort(item, {item: item.id, path: `slot-1/module/${id}`, view: 'rear'}, ctx);

test('a port of a module in a bay reads the role its placement states, then its own component\'s, else its connector', () => {
  assert.equal(read('placed').port, true);
  assert.equal(read('placed').info.family, 'console', 'the placement in the module states it');
  assert.equal(read('own').info.family, 'console', 'the port\'s own component states it');
  assert.equal(read('none').info.family, 'usb', 'no role: its connector');
  assert.equal(read('other').info.family, 'usb', 'a role that is not console');
});
