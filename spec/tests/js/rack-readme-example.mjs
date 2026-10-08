// The example under "Racks" in kit/README.md, run as written: the README's
// own code block is read, its imports pointed at this checkout, and executed
// against a rack.json stand-in. If the example stops working, this fails.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

globalThis.location = {href: 'https://page.test/', search: ''};
const DEVICES = {
  'as7726-32x': {manufacturer: 'Edgecore', model: '7726-32X', ru: 1, h: 43.5, d: 515, w: 440},
  'fhd-cmp5dr': {manufacturer: 'FiberHD', model: 'CMP5DR', ru: 1, h: 44, d: 110, mount: 'rack-face', shell: 'sheet'}};
globalThis.fetch = async url => {
  assert.equal(url, 'https://page.test/portrayal/dist/rack.json');
  return {ok: true, json: async () => ({format: 1, devices: DEVICES})};
};

const readme = readFileSync(new URL('../../../kit/README.md', import.meta.url), 'utf8');
const racks = readme.slice(readme.indexOf('\n## Racks'));
const block = /```js\n([\s\S]*?)```/.exec(racks)?.[1];

test('the Racks example is in the README', () => assert.ok(block && block.includes('loadCatalog')));

test('the Racks example runs, and says what the README says', async () => {
  const kit = new URL('../../../kit/rack/', import.meta.url).href;
  // An import cannot sit in a function body: each becomes a dynamic import of this checkout's module.
  const code = block.replace(/import \{([^}]*)\} from '@portrayal\/kit\/rack\/([^']+)';/g,
    (_, names, mod) => `const {${names.trim()}} = await import('${kit}${mod}.js');`);
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  const out = await new AsyncFunction(`${code}\nreturn {rack, route, length, bom, schedule, where, manager};`)();
  assert.equal(out.rack.items.length, 3);
  assert.deepEqual([out.where.on, out.where.unit], ['i1', 1]);
  assert.equal(out.manager.item.on, 'i1');
  assert.equal(out.rack.cables.length, 1);
  assert.ok(out.route.waypoints.length > 0 && out.route.auto);
  assert.ok(out.length.measured > 0 && out.length.value >= out.length.measured);
  assert.ok(out.bom.some(r => r.model === '7726-32X' && r.qty === 2));
  assert.equal(out.schedule.rows.length, 1);
  assert.equal(out.schedule.rows[0].a_device, 'leaf-1');
});
