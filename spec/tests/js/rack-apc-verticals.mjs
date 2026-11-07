// spec/tests/js/rack-apc-verticals.mjs
// APC'S PERFORMANCE VERTICAL MANAGERS IN THE RACK KIT (#1097): what the six parts advertise works in the
// kit, not only in the drawing. Each stands beside a two-post rack (the AR201, 45U) and a four-post one
// (the AR203A, 44U), on either side, lists its duct or ducts, and a cable runs down the duct beside the
// rack. Everything reads the build, as the Rack Builder does: rack.json for each part's catalogue entry,
// and the compiled front and rear drawings for each duct.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as R from '../../../kit/rack/route.js';
import * as F from '../../../kit/rack/fit.js';
import {inspect} from '../../../kit/rack/queries.js';

const DIST = new URL('../../../library/dist/', import.meta.url);
const skip = existsSync(new URL('rack.json', DIST)) ? false : 'library/dist not built - run ./build.sh';
const devices = skip ? {} : JSON.parse(readFileSync(new URL('rack.json', DIST), 'utf8')).devices;
const stub = {sw: {ru: 1, w: 440, h: 44, d: 515}, pp24: {ru: 1, w: 440, h: 44, d: 100}};
const chassisOf = ref => devices[ref] ?? stub[ref] ?? null;

// name -> the guides it publishes by face: one working face on a single-sided part, two on a double-sided one
const PARTS = {
  ar8615: {front: ['duct']}, ar8635: {front: ['duct']}, ar8665: {front: ['duct']},
  ar8625: {front: ['duct'], rear: ['rear-duct']}, ar8645: {front: ['duct'], rear: ['rear-duct']}, ar8675: {front: ['duct'], rear: ['rear-duct']},
};
// the racks it pairs with: the AR201 two-post 45U (left, right) and the AR203A four-post 44U
const RACKS = {
  ar201: {kind: 'two-post', heightRU: 45, points: ['left', 'right']},
  ar203a: {kind: 'four-post', heightRU: 44, points: ['left-front', 'right-front', 'left-rear', 'right-rear']},
};

const svgOf = (name, view) => readFileSync(new URL(`${name}.base.${view}.svg`, DIST), 'utf8');
const add = (rack, ref, ru) => M.withItem(rack, {ref, cfg: 'base', ru, label: ref}).rack;
const frameOf = ({kind, heightRU}) => M.withFrame(M.newRack({kind}), {heightRU});
// a switch at U10 (i1) and a 24-port patch panel at U30 (i2) on the rails, and the manager beside them at `at`
const rackOf = (rk, name, at) => ({...add(add(frameOf(rk), 'sw', 10), 'pp24', 30),
  zeroU: [{id: 'z1', ref: name, cfg: 'base', label: 'vcm-1', at, offsetMm: 0}]});
const ductsOf = (name, ids) => {
  const out = [];
  for (const face of ['front', 'rear']) {
    for (const m of svgOf(name, face).matchAll(/<rect id="guide--([\w-]+)" data-class="guide" data-guide="duct"[^>]*data-guide-run="y"/g)) {
      if (ids.includes(m[1])) out.push({via: m[1], kind: 'duct', face, x: 0, run: 'y'});
    }
  }
  return out;
};

for (const [name, byFace] of Object.entries(PARTS)) {
  const ids = Object.values(byFace).flat();
  test(`${name}: a part beside the rack, 44 units, taking none, with its vertical duct${ids.length > 1 ? 's' : ''} in the catalogue`, {skip}, () => {
    assert.equal(devices[name].mount, 'rack-side');
    assert.equal(devices[name].ru, 44);
    assert.equal(F.isZeroUPart(devices[name]), true);
    assert.deepEqual(Object.values(devices[name].guides).flat().sort(), [...ids].sort());
    assert.equal(ductsOf(name, ids).length, ids.length, 'each duct runs down the height (run y)');
  });

  for (const [rname, rk] of Object.entries(RACKS)) {
    for (const at of rk.points.slice(0, 2)) {
      test(`${name}: fits beside the ${rname} (${rk.heightRU}U) at ${at}, and two on one point do not`, {skip}, () => {
        const r = frameOf(rk);
        assert.equal(F.fitsZeroU(r, {ref: name, at, ru: 1}, chassisOf).ok, true, `${name} at ${at}`);
        const one = {...r, zeroU: [{id: 'z1', ref: name, cfg: 'base', label: 'a', at, offsetMm: 0}]};
        const second = F.fitsZeroU(one, {ref: name, at}, chassisOf);
        assert.equal(second.ok, false, 'the second overlaps the first');
        const other = rk.points.find(p => p !== at);
        assert.equal(F.fitsZeroU(one, {ref: name, at: other, ru: 1}, chassisOf).ok, true, 'and the other point is free');
      });

      test(`${name}: a cable runs down each duct beside the ${rname} at ${at}, along its lane`, {skip}, async () => {
        const ducts = ductsOf(name, ids), r = rackOf(rk, name, at);
        const ctx = {chassisOf, bendOf: () => 1e12, guidesOf: id => (id === 'z1' ? ducts : []), portX: () => 0, portY: () => null};
        for (const d of ducts) {
          const c = {id: 'c1', media: 'cat6', a: {item: 'i1', path: 'p', view: 'front'}, b: {item: 'i2', path: 'q', view: 'front'},
            route: [{item: 'z1', via: d.via}], routeEdited: true};
          const resolved = R.resolveRoute({...r, cables: [c]}, c, ctx);
          assert.ok(resolved.waypoints.length > 0 && resolved.waypoints.every(w => w.lane === at), `${d.via} is a way down the ${at} lane`);
          assert.deepEqual(resolved.gone ?? [], []);
          assert.ok(R.routedLength({...r, cables: [c]}, c, ctx).measured > 0, `${d.via}: the cable has a length`);
        }
        const hm = await inspect(r, 'z1', {chassisOf});
        const found = hm.pathways.filter(p => p.kind === 'duct');
        assert.deepEqual(found.map(p => p.via).sort(), [...ids].sort());
        assert.ok(found.every(p => p.holds_spare), 'a duct holds spare cable');
      });
    }
  }
}

test('no APC vertical manager states a capacity, so the kit shows none', {skip}, () => {
  for (const name of Object.keys(PARTS)) assert.equal(devices[name].capacity, undefined, name);
});
