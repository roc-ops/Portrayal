// Where the Explorer's tree ranks a group by its role (#1042). The tree opens
// with what the box is for and ends with what it neither connects to nor reads;
// `stack-control` is the jacks that run a stacked pair, so it ranks with
// `management` and after the ports that carry traffic. A role the table does not
// know falls to rank 0, which is where `traffic` is - so a missing row would
// put the CSR310's STACK-CTRL back among the customer ports without a word.
import test from 'node:test';
import assert from 'node:assert/strict';
import { install, El } from './fake-shell-dom.mjs';

const part = (path, group, role) => ({attrs: {
  'data-path': path, 'data-class': 'port', 'data-group': group, 'data-group-role': role}});
// written in document order: the stack jacks FIRST, so only their rank moves them
const parts = [
  part('stack-ctrl', 'stack-signals', 'stack-control'),
  part('mgmt-eth', 'mgmt', 'management'),
  part('port-0', 'sfp', 'traffic'),
  part('fab-0', 'fab', 'fabric'),
  part('psu-0', 'psus', 'service'),
];
install({
  'devices.json': () => JSON.stringify({devices: [{name: 'a', ns: 'v'}]}),
  'components.json': () => JSON.stringify({components: []}),
  'a.configs.json': () => JSON.stringify({
    device: 'a', model: 'A', default: 'ac', views: ['front'], bays: {}, cages: {},
    configs: [{name: 'ac', files: {front: 'a.ac.front.svg'}}]}),
  'a.ac.front.svg': () => JSON.stringify({src: 'front', parts}),
});
// a row that keeps the markup it was given, so a group row can be read back
class Row extends El {
  set innerHTML(v) { this.html = v; }
  get innerHTML() { return this.html || ''; }
}
document.createElement = t => new Row(t);
globalThis.location.search = '?device=a&view=front';

const { createShell } = await import('../../../kit/shell.js');
const shell = createShell({dist: 'http://kit.test/dist'});
await shell.ready;

test('the tree lists the groups traffic, then the stack jacks with management, then service', () => {
  shell.refreshTree();
  const groups = shell.el.tree.children
    .filter(r => r.classList.contains('grp'))
    .map(r => /class="nm">([^<]*)</.exec(r.innerHTML)?.[1]);
  // fabric ranks with traffic; the stack jacks and management share a rank, and
  // document order puts the stack jacks first within it
  assert.deepEqual(groups, ['sfp', 'fab', 'stack-signals', 'mgmt', 'psus']);
});
