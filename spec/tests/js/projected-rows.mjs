// What a face lists, and what a click on it names, when part of the face is a
// PROJECTION (render.py's `rear:` and `plan:`, swap.js's applyRearOverrides).
// Modelled on fhd-1ufce's rear: a cassette's back drawn inside the panel
// cutout it is seen through, `data-of` in place of `data-path` throughout.
import {build, install} from './fake-dom.mjs';
install();
const {faceEntries, ownerPath, applyRearOverrides} = await import('../../../kit/swap.js');

const mtp = (n) => ({a: {'data-class': 'port', 'data-connector': 'mpo', 'data-of': `bay-1/module/mtp${n}`},
                     c: [{t: 'rect', a: {id: `plug-${n}`}}]});
const rear = build({t: 'svg', c: [
  {a: {'data-path': 'chassis', 'data-class': 'chassis'}},
  {a: {'data-path': 'cutout:back-1', 'data-class': 'cutout', 'data-rear-of': 'bay-1'}, c: [
    {t: 'rect', a: {id: 'hole'}},
    {a: {'data-projection': '1', 'data-of': 'bay-1/module', 'data-class': 'cassette'}, c: [
      {t: 'rect', a: {id: 'bezel'}},
      mtp(1), mtp(2),
    ]},
  ]},
  // a projection of a part this face ALSO draws is that part, listed once
  {a: {'data-path': 'psu-1'}},
  {a: {'data-projection': '1', 'data-of': 'psu-1'}},
]});

const entries = faceEntries(rear);
const at = (path) => entries.find(e => e.path === path);
const find = (pred) => [...rear.descendants()].find(pred);
const plug = find(n => n.getAttribute('id') === 'plug-2');
const bezel = find(n => n.getAttribute('id') === 'bezel');
const hole = find(n => n.getAttribute('id') === 'hole');
const root = entries.find(e => e.path === 'bay-1/module');

// A SWAP builds the same projection in the kit: the back of the cassette swapped
// in, from its components.json entry and published skin.
const swapped = build({t: 'svg', c: [
  {a: {'data-path': 'cutout:back-1', 'data-rear-of': 'bay-1', 'data-rear-at': '337.955,6.5'}},
]});
const skin = {t: 'svg', c: [{a: {id: 'rear-2', 'data-path': 'rear-2', 'data-class': 'cassette',
  'data-media': 'fiber', 'data-ref': 'fs/rear-2@1:1.0.0', transform: 'translate(0,0)'}, c: [
  {t: 'title', a: {}},
  {a: {id: 'rear-2--mtp1', 'data-path': 'rear-2/mtp1', 'data-class': 'port', 'data-ref': 'common/mpo@1'}},
  {a: {id: 'rear-2--mtp2', 'data-path': 'rear-2/mtp2', 'data-class': 'port', 'data-z-out': '3'}},
]}]};
const applied = await applyRearOverrides(swapped, {'bay-1': 'fs/cassette@1'},
  async () => ({text: JSON.stringify(skin), comp: {name: 'rear-2'}}),
  () => ({faces: {rear: 'fs/rear-2@1'}}));
const wrap = [...swapped.descendants()].find(n => n.getAttribute('data-projection'));
const swapEntries = faceEntries(swapped);

console.log(JSON.stringify({
  swap: {
    applied,
    wrap: Object.fromEntries(wrap.attributes.map(a => [a.name, a.value])),
    paths: swapEntries.map(e => e.path),
    leftover: [...wrap.descendants()].flatMap(n => n.attributes.map(a => a.name))
      .filter(k => ['data-path', 'data-ref'].includes(k) || k.startsWith('data-z-')),
  },
  paths: entries.map(e => e.path),
  projected: entries.filter(e => e.projected).map(e => e.path),
  psuFromPart: at('psu-1')?.el.getAttribute('data-path') === 'psu-1',
  moduleHost: root ? ownerPath(root.el.parentNode) : null,
  clickPlug: ownerPath(plug),
  clickBezel: ownerPath(bezel),
  clickHole: ownerPath(hole),
  clickNothing: ownerPath(rear),
  nul: ownerPath(null),
}));
