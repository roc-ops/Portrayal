// spec/tests/js/offered-ends-land.mjs
// WHAT THE RACK KIT OFFERS AS A POWER, GROUND OR OTHER CABLE END, A CABLE CAN BE GIVEN (#1045), against the rack
// kit, built from the real components.json, rack.json, configs.json and drawn faces under PORTRAYAL_DIST
// (library/dist).
//
// For every device of the library, in every configuration it has, one item is put in a rack beside a second of the
// same device, and every end `freePorts` lists for it (kinds power, ground and other) is taken as the end of a
// cable to the same path on the other item. The reader of the Rack Builder page is stood in for by the drawn faces:
// the paths `cableEndPaths` gives, each with the class and ref of the element drawn there.
//
// Held here: an end that is offered is either one `cable.add` accepts and that no panel reports as loose, or it
// says in the row itself that it cannot be given (`landable: false` and a `reason`); and no row on the front or
// the rear carries either key, so a row that could be given reads as it always did.
//
// Run by test_rack_offered_ends_land.py, which names the build in PORTRAYAL_DIST.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as Q from '../../../kit/rack/queries.js';
import * as P from '../../../kit/rack/ports.js';
import * as CR from '../../../kit/rack/cable-rules.js';
import {apply} from '../../../kit/rack/commands.js';

const DIST = process.env.PORTRAYAL_DIST;
assert.ok(DIST, 'PORTRAYAL_DIST names the build directory (library/dist)');
const read = name => JSON.parse(fs.readFileSync(`${DIST}/${name}`, 'utf8'));
const components = read('components.json').components;
const comps = new Map(components.map(c => [`${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`, c]));
const compByRef = ref => (ref == null ? null : comps.get(String(ref).split(':')[0]) ?? null);
const devices = read('rack.json').devices;
const slotsOf = ref => {
  if (!devices[ref]) return null;
  const c = read(`${ref}.configs.json`);
  return {default: c.default, 'pdu-class': c['pdu-class'], bays: c.bays, cages: c.cages, configs: c.configs};
};
const FACES = ['front', 'rear'];

// every offered end of every configuration: {ref, cfg, row, result} with result 'lands', 'refused' or 'loose'
async function sweep() {
  const out = [];
  for (const ref of Object.keys(devices)) {
    const slots = slotsOf(ref);
    if (!slots) continue;
    for (const cfg of (slots.configs || []).map(c => c.name)) {
      const cache = {};
      const faceEls = view => (cache[view] ??= (() => { try { return read(`${ref}.${cfg}.${view}.elements.json`).elements; } catch { return []; } })());
      const elAt = (view, path) => { const m = new Map(faceEls(view).map(e => [e.path, e])); return m.get(path) ?? m.get(path.replace(/\//g, '--')) ?? null; };
      const two = M.withItem(M.withItem(M.newRack(), {ref, cfg, ru: 1, label: 'one'}).rack, {ref, cfg, ru: 20, label: 'two'}).rack;
      const [one, other] = two.items;
      const ctx = {chassisOf: r => devices[r] ?? null, slotsOf, compByRef, redirects: null};
      ctx.drawnAt = end => elAt(end.view, end.path)?.ref ?? null;
      ctx.portsOf = async (item, view) => P.cableEndPaths(item, view, ctx)
        .map(p => { const e = elAt(view, p); return e ? {cls: e.class, path: p, end: true, ref: e.ref, media: e.media} : null; }).filter(Boolean);
      // a page that knows class `port` alone, as the Rack Builder's reader did before the slot ends
      ctx.cableFacts = async (rack, extra = []) => {
        const ends = new Map();
        for (const end of [...(rack.cables || []).flatMap(c => [c.a, c.b]), ...extra]) {
          const it = rack.items.find(i => i.id === end.item);
          const el = it ? elAt(end.view, end.path) : null;
          const facts = {item: !!it, drawing: !!it, port: el?.class === 'port', cage: false, occupied: false, holder: null};
          ends.set(`${end.item}|${end.view}|${end.path}`, {facts, info: {family: null, mode: null}, reason: it ? CR.looseReason(end, facts) : 'the device was removed'});
        }
        return {seats: {}, ends};
      };
      const rows = await Q.freePorts(two, one.id, ctx, {kinds: ['power', 'ground', 'other']});
      assert.ok(Array.isArray(rows), `${ref} ${cfg}: freePorts answered ${JSON.stringify(rows)}`);
      for (const row of rows) {
        const r = apply(two, {op: 'cable.add', a: {item: one.id, path: row.path, view: row.view}, b: {item: other.id, path: row.path, view: row.view},
                              media: row.kind === 'ground' ? 'ground' : 'power'}, ctx);
        if (r.error || (r.errors && r.errors.length)) { out.push({ref, cfg, row, result: 'refused', why: String(r.error ?? r.errors)}); continue; }
        const loose = (await Q.looseEnds(r.rack, ctx)).ends;
        out.push({ref, cfg, row, result: loose.length ? 'loose' : 'lands', why: loose[0]?.reason});
      }
    }
  }
  return out;
}
const SWEEP = await sweep();

test('the library offers power, ground and other ends to land a cable on', () => {
  assert.ok(SWEEP.length > 0, 'a built library offers some');
  assert.ok(SWEEP.some(x => x.result === 'lands'), 'and some of them are ones a cable lands on');
});

test('an end that is offered lands, or the row says it cannot be given', () => {
  const bad = SWEEP.filter(x => x.result !== 'lands' && x.row.landable !== false)
    .map(x => `${x.ref} ${x.cfg} ${x.row.view}:${x.row.path} ${x.result} ${x.why}`);
  assert.deepEqual(bad.slice(0, 20), [], `${bad.length} offered ends are refused or loose without saying so`);
});

test('a row that says it cannot be given says why, and is on a panel an end cannot be given on', () => {
  const said = SWEEP.filter(x => x.row.landable === false);
  for (const x of said) {
    assert.equal(FACES.includes(x.row.view), false, `${x.ref} ${x.cfg} ${x.row.path} is on the ${x.row.view}`);
    assert.equal(typeof x.row.reason, 'string', `${x.ref} ${x.cfg} ${x.row.path} states no reason`);
    assert.match(x.row.reason, new RegExp(x.row.view), 'the reason names the panel');
    assert.equal(x.result, 'refused', `${x.ref} ${x.cfg} ${x.row.path}: cable.add takes the end the row says it cannot`);
  }
});

test('a row on the front or the rear carries neither key', () => {
  const marked = SWEEP.filter(x => FACES.includes(x.row.view) && ('landable' in x.row || 'reason' in x.row))
    .map(x => `${x.ref} ${x.cfg} ${x.row.view}:${x.row.path}`);
  assert.deepEqual(marked.slice(0, 20), []);
});
