// spec/tests/js/rack-chatsworth-managers.mjs
// THE CHATSWORTH EVOLUTION HORIZONTAL MANAGERS IN THE RACK KIT (P-0126, #1093). What the maker
// advertises has to work in a rack and not only be drawn: a cable runs along the finger duct and
// its spare is stored there against the cable fill the maker states; a cable crosses the back
// plate through a pass-through port, a brush window or a grommet (a leg that runs front to rear
// through the middle of an opening is not a crossing, and is, with the opening shut); and the
// solid chassis styles have no opening to cross by. Reads the build's rack.json, as the Rack
// Builder does.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import * as R from '../../../kit/rack/route.js';
import * as S from '../../../kit/rack/solids.js';
import * as SL from '../../../kit/rack/slack.js';
import {apply} from '../../../kit/rack/commands.js';
import * as F from './cable-solids-fixture.mjs';

const BUILT = new URL('../../../library/dist/rack.json', import.meta.url);
const skip = existsSync(BUILT) ? false : 'library/dist not built - run ./build.sh';
const devices = skip ? {} : JSON.parse(readFileSync(BUILT, 'utf8')).devices;

// part -> [chassis style, rack units, the maker's Cat 6 maximum fill, the openings its back plate has]
const PARTS = {
  '35441-x01': ['solid', 1, 56, 0], '35441-x02': ['ports', 2, 173, 2], '35441-x03': ['ports', 3, 285, 2],
  '35441-x04': ['ports', 4, 403, 2], '35442-x02': ['solid', 2, 173, 0], '35442-x03': ['solid', 3, 285, 0],
  '35442-x04': ['solid', 4, 403, 0], '33548-x02': ['brush', 2, 173, 1], '33548-x03': ['brush', 3, 285, 1],
  '33548-x04': ['brush', 4, 403, 1], '33549-x02': ['grommet', 2, 173, 3], '33549-x03': ['grommet', 3, 285, 3],
  '33549-x04': ['grommet', 4, 403, 3],
};
const names = Object.keys(PARTS);
const CAT6 = 6;   // mm, the cord a leg is taken for

// the reference fixture rack of #949 with the manager at U8, below the switches
function rackWith(name, dev) {
  const sizes = {...F.SIZES, [name]: dev};
  const base = F.add(F.ownerRack(), name, 8, {label: 'mgr'});
  const mgr = base.items.at(-1).id;
  return {rack: base, mgr, sizes, ctx: {chassisOf: ref => sizes[ref] || null}};
}
// the plate of the manager as the kit places it, with its holes
const plateOf = ({rack, mgr, ctx}) => S.solidsOf(rack, ctx).filter(s => s.item === mgr);
// a straight leg from in front of the plate to behind it, at (x, y) in rack mm
const leg = (x, y, plate) => {
  const z0 = Math.min(...plate.map(s => s.box.z0)), z1 = Math.max(...plate.map(s => s.box.z1));
  return [{x, y, z: z1 + 30}, {x, y, z: z0 - 30}];
};
const crossings = (x, y, plate) => S.legCrossings(...leg(x, y, plate), plate, {diameter: CAT6});
const shut = plate => plate.map(s => ({...s, holes: []}));

test('every part is in the build, as a rack-face sheet part that states its duct and the maker\'s cable fill', {skip}, () => {
  for (const name of names) {
    const [, ru, count] = PARTS[name];
    const d = devices[name];
    assert.ok(d, `${name} is in rack.json`);
    assert.equal(d.manufacturer, 'Chatsworth Products');
    assert.deepEqual([d.ru, d.w, d.d, d.shell, d.mount], [ru, 482.6, 208, 'sheet', 'rack-face'], name);
    assert.deepEqual(d.guides.front, ['duct'], `${name} publishes its finger duct`);
    assert.deepEqual([d.capacity.count, d.capacity.media], [count, 'cat6'], name);
    assert.ok(!d.capacity.estimated, 'the maker states it');
  }
});

test('a cable runs along the finger duct, and its spare is stored there against the maker\'s count', {skip}, () => {
  for (const name of names) {
    const dev = devices[name];
    assert.ok(dev, `${name} is in rack.json`);
    const {rack, mgr, ctx} = rackWith(name, dev);
    const c = F.cable('c1', F.end('i1', 'p140'), F.end('i4', 'p150'), 'cat6', {
      route: [{item: mgr, via: 'duct'}], routeEdited: true, length: {value: 2, unit: 'm', source: 'entered'}});
    const lay = {...rack, cables: [c]};
    const rctx = F.ctxOf({guides: {[mgr]: [{via: 'duct', kind: 'duct', face: 'front', run: 'x', x: 0}]},
      ctx: {chassisOf: ctx.chassisOf}});
    const p = R.routePath(lay, c, rctx);
    assert.deepEqual(p.crossings, [], `${name}: nothing in the duct's way`);
    assert.ok(p.points.some(q => q.at === 'pathway'), `${name}: the cable passes the duct`);
    const stored = apply(lay, {op: 'cable.slack', id: 'c1', at: {item: mgr, via: 'duct'}, value: 0.3},
      {chassisOf: ctx.chassisOf, route: rctx});
    assert.equal(stored.error, undefined, `${name}: ${stored.error}`);
    const s = SL.slackOf(stored.rack, stored.rack.cables[0], rctx);
    assert.equal(s.entries[0].kind, 'duct', `${name}: the spare lies in the duct`);
  }
});

test('a cord crosses the back plate through each port, brush window and grommet, and meets the plate beside it', {skip}, () => {
  for (const name of names.filter(n => PARTS[n][3] > 0)) {
    const style = PARTS[name][0];
    const plate = plateOf(rackWith(name, devices[name]));
    const holes = plate.flatMap(s => s.holes);
    assert.equal(holes.length, PARTS[name][3], `${name}: one hole for each opening`);
    for (const h of holes) {
      const cx = (h.box.x0 + h.box.x1) / 2, cy = (h.box.y0 + h.box.y1) / 2;
      assert.deepEqual(crossings(cx, cy, plate), [], `${name} ${h.via} (${style}): through the middle is no crossing`);
      assert.ok(crossings(cx, cy, shut(plate)).length, `${name} ${h.via}: with the opening shut it is`);
      // a cord that is thicker than the opening is never through it
      assert.ok(S.legCrossings(...leg(cx, cy, plate), plate, {diameter: Math.min(...h.size) + 1}).length, `${name} ${h.via}: too thick`);
    }
    // between the openings, on the plate, the cord meets it
    const y = (plate[0].box.y0 + plate[0].box.y1) / 2, last = Math.max(...holes.map(h => h.box.x1));
    assert.ok(crossings(Math.min(...holes.map(h => h.box.x0)) - 10, y, plate).length
      || crossings(last + 10, y, plate).length, `${name}: beside the openings the plate is in the way`);
  }
});

test('the openings are the passes the part declares: ports and grommets open, the brush a brush', {skip}, () => {
  const cover = {ports: 'open', grommet: 'open', brush: 'brush'};
  for (const name of names.filter(n => PARTS[n][3] > 0)) {
    const [style, , , n] = PARTS[name];
    const dev = devices[name];
    assert.equal(dev.passes.rear.length, n, name);
    assert.equal(dev.passes.front, undefined, name);
    assert.ok(cover[style], style);
    assert.equal(plateOf(rackWith(name, dev)).flatMap(s => s.holes).map(h => h.via).sort().join(), [...dev.passes.rear].sort().join());
  }
});

test('the solid managers have no opening: a cord at any height and across meets the plate', {skip}, () => {
  for (const name of names.filter(n => PARTS[n][3] === 0)) {
    const dev = devices[name];
    assert.equal(dev.passes, undefined, `${name} declares no pass`);
    const plate = plateOf(rackWith(name, dev));
    assert.equal(plate.length, 1, name);
    assert.deepEqual(plate[0].holes, [], `${name} has no hole`);
    const b = plate[0].box;
    for (const f of [0.1, 0.3, 0.5, 0.7, 0.9])
      assert.ok(crossings(b.x0 + f * (b.x1 - b.x0), b.y0 + 0.5 * (b.y1 - b.y0), plate).length, `${name} at ${f}`);
  }
});
