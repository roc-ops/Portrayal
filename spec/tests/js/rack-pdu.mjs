// spec/tests/js/rack-pdu.mjs
// ZERO-U PARTS IN VERSION 4 (docs/rack-file-v4-design.md sections 4 and 5,
// build part 6): `states` and `readings` on an item and on a part beside the
// rack, `swaps` and `fields` on a part beside the rack, a PDU hung on brackets
// (`heldBy: {parts}`), and zero-U overlap judged in millimetres.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import * as M from '../../../kit/rack/model.js';
import * as F from '../../../kit/rack/fit.js';
import * as Z from '../../../kit/rack/zero-u.js';
import * as ST from '../../../kit/rack/states.js';
import {configFacts} from '../../../kit/rack/catalog.js';
import {apply, COMMANDS} from '../../../kit/rack/commands.js';
import {RU} from '../../../kit/rack/rails.js';

// A 40U PDU with two buttons 1555.8 mm apart (the Eaton G4 pitch), a short one
// with one button, a bracket with one keyhole 26 mm up (10 mm on its side
// option), and a duct.
const SIZES = {
  pdu: {ru: 40, w: 55, h: 1778, d: 60, mount: 'rack-side', model: 'EVMA8365X'},
  basic: {ru: 40, w: 55, h: 1778, d: 60, mount: 'rack-side', model: 'BASIC-PDU'},
  stub: {ru: 10, w: 55, h: 440, d: 60, mount: 'rack-side', model: 'STUB-PDU'},
  bracket: {ru: 1, w: 40, h: 44, d: 20, mount: 'rack-side', model: 'FS-PDUBK'},
  duct: {ru: 2, w: 100, h: 88.9, d: 100, mount: 'rack-side', model: 'DUCT-2U'},
  sw: {ru: 1, w: 440, h: 43.6, d: 500, model: 'SW-1'},
};
const chassisOf = ref => SIZES[ref] || null;
const POINTS = [{mates: 'pdu-button', at: 72}, {mates: 'pdu-button', at: 1627.8}];
const OUTLETS = {'outlet-a1': ['on', 'off'], 'outlet-a2': ['on', 'off']};
const SLOTS = {
  pdu: {default: 'base', 'pdu-class': 'managed', configs: [{name: 'base', 'mount-points': POINTS, slots: [], states: OUTLETS}]},
  basic: {default: 'base', 'pdu-class': 'basic', configs: [{name: 'base', 'mount-points': POINTS, slots: [], states: {}}]},
  stub: {default: 'base', 'pdu-class': 'metered-branch', configs: [{name: 'base', 'mount-points': [POINTS[0]], slots: [], states: {}}]},
  bracket: {default: 'front', 'pdu-class': null, configs: [
    {name: 'front', 'mount-points': [], slots: [{interface: 'pdu-button', at: 26}], states: {}},
    {name: 'side', 'mount-points': [], slots: [{interface: 'pdu-button', at: 10}], states: {}}]},
  duct: {default: 'base', 'pdu-class': null, configs: [{name: 'base', 'mount-points': [], slots: [], states: {}}]},
  sw: {default: 'base', 'pdu-class': null, configs: [{name: 'base', 'mount-points': [], slots: [], states: {'psu-1': ['on', 'off']}}]},
};
const slotsOf = ref => SLOTS[ref] ?? null;
const ctx = {chassisOf, slotsOf};
const rackOf = () => ({...M.newRack(), frame: M.normalizeFrame({kind: 'four-post', heightRU: 45})});
const run = (rack, cmds, c = ctx) => apply(rack, cmds, c);
const zById = (rack, id) => rack.zeroU.find(z => z.id === id);
// two brackets at left-rear, `apart` units apart from U4, and a PDU beside them
function hung(apart = 35) {
  const r = run(rackOf(), [
    {op: 'zerou.place', ref: 'bracket', at: 'left-rear', ru: 4, label: 'Bracket'},
    {op: 'zerou.place', ref: 'bracket', at: 'left-rear', ru: 4 + apart, label: 'Bracket'},
    {op: 'zerou.place', ref: 'pdu', at: 'right-rear', ru: 1, label: 'PDU A'}]);
  assert.equal(r.error, undefined);
  return r.rack;
}

// ── hung on brackets ─────────────────────────────────────────────────────

test('a mount point that mates a list of interfaces hangs where one that mates one does', () => {
  // `mates` on a component is one interface or a list (#1045), and a mount
  // point publishes it as stated
  const listed = POINTS.map(m => ({...m, mates: ['other-button', m.mates]}));
  const c = {chassisOf, slotsOf: ref => (ref === 'pdu' ? {...SLOTS.pdu, configs: [{...SLOTS.pdu.configs[0], 'mount-points': listed}]} : slotsOf(ref))};
  const res = run(hung(35), {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}, c);
  assert.equal(res.error, undefined);
  const pdu = zById(res.rack, 'z3');
  assert.deepEqual(Z.fitsHang(res.rack, pdu, c), {ok: true, place: {at: 'left-rear', offsetMm: 87.35}});
  // a list that does not name what the brackets present still does not hang
  const none = {chassisOf, slotsOf: ref => (ref === 'pdu' ? {...SLOTS.pdu, configs: [{...SLOTS.pdu.configs[0], 'mount-points': POINTS.map(m => ({...m, mates: ['other-button']}))}]} : slotsOf(ref))};
  assert.equal(Z.fitsHang(res.rack, pdu, none).ok, false);
});

test('a PDU hung on two brackets 35U apart fits, and stands where they hold it', () => {
  const r = hung(35);
  const res = run(r, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']});
  assert.equal(res.error, undefined);
  const pdu = zById(res.rack, 'z3');
  // the lowest slot is 133.35 + 26 up, the lowest button 72 up the PDU: its bottom is 87.35 up
  assert.deepEqual([pdu.at, pdu.offsetMm, pdu.heldBy], ['left-rear', 87.35, {parts: ['z1', 'z2']}]);
  assert.equal(res.summary, 'Hung PDU A on z1, z2, beside the rack at left-rear, U3-U42.');
  // the buttons are 1555.8 apart and the slots 35 units, 1555.75: inside the 1 mm tolerance
  assert.deepEqual(Z.fitsHang(res.rack, pdu, ctx), {ok: true, place: {at: 'left-rear', offsetMm: 87.35}});
  // it does not overlap the brackets that hold it, though they are inside its span on one upright
  assert.deepEqual(F.fitsZeroU(res.rack, {...pdu}, chassisOf, {ignoreId: 'z3'}), {ok: true});
  assert.deepEqual(F.fitsZeroU(res.rack, zById(res.rack, 'z1'), chassisOf, {ignoreId: 'z1'}), {ok: true});
  // another part there still does
  assert.deepEqual(F.fitsZeroU(res.rack, {ref: 'duct', at: 'left-rear', ru: 10}, chassisOf), {ok: false, reason: 'Overlaps PDU A at left-rear.'});
  assert.deepEqual(Z.hangNotices(res.rack, ctx), []);
  // saved and opened again, it is as it was
  assert.deepEqual(M.parseDoc(M.serialize({...M.newDoc(), racks: [res.rack]})).racks[0].zeroU, res.rack.zeroU);
  // hung again on the same brackets, nothing changes
  assert.equal(run(res.rack, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}).noop, true);
});

test('34U apart it is refused, with the sentence and the distance', () => {
  const r = hung(34);
  assert.deepEqual(run(r, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}), {index: 0, error:
    'PDU A has mount points 1555.8 mm apart; brackets z1 and z2 are 1511.3 mm apart. Move z2 up 1U.'});
  assert.deepEqual(run(hung(37), {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}).error,
    'PDU A has mount points 1555.8 mm apart; brackets z1 and z2 are 1644.7 mm apart. Move z2 down 2U.');
  // each refusal of the design, in its order
  assert.equal(run(r, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z9']}).error, 'z9 is not a bracket in this rack.');
  const withDuct = run(r, {op: 'zerou.place', ref: 'duct', at: 'right-front', ru: 1}).rack;
  assert.equal(run(withDuct, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z4']}).error, 'z4 is not a bracket in this rack.',
    'a part that offers no slot for a button is no bracket');
  const across = run(hung(35), {op: 'zerou.update', id: 'z2', at: 'right-front'}).rack;
  assert.equal(run(across, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}).error,
    'z1 is at left-rear and z2 at right-front; a PDU hangs on one upright.');
  assert.equal(run(r, {op: 'zerou.hang', id: 'z3', on: ['z3']}).error, 'PDU A cannot hang on itself.');
  // a bracket is judged by the configuration it names: on its side option the slot is 16 mm lower, and both move alike
  const side = {...hung(35), zeroU: hung(35).zeroU.map(z => (z.ref === 'bracket' ? {...z, cfg: 'side'} : z))};
  assert.equal(zById(run(side, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}).rack, 'z3').offsetMm, 71.35);
  const mixed = {...side, zeroU: side.zeroU.map(z => (z.id === 'z2' ? {...z, cfg: 'front'} : z))};
  assert.match(run(mixed, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}).error, /brackets z1 and z2 are 1571\.8 mm apart\. Move z2 down 16 mm\./);
  // without the parts lists nothing can be judged, so nothing is hung
  assert.equal(run(r, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}, {chassisOf}).error,
    'zerou.hang needs the parts lists of the devices, which the caller has not loaded.');
  assert.deepEqual(COMMANDS['zerou.hang'].args.required, ['id', 'on']);
});

test('moving a bracket moves the PDU, and a held PDU is not moved by hand', () => {
  // a short PDU on one bracket
  let r = run(rackOf(), [{op: 'zerou.place', ref: 'bracket', at: 'left-rear', ru: 4, label: 'Bracket'},
                         {op: 'zerou.place', ref: 'stub', at: 'right-rear', ru: 1, label: 'PDU S'},
                         {op: 'zerou.hang', id: 'z2', on: ['z1']}]).rack;
  assert.equal(zById(r, 'z2').offsetMm, 87.35);
  const up = run(r, {op: 'zerou.update', id: 'z1', ru: 6});
  assert.equal(up.error, undefined);
  assert.deepEqual([zById(up.rack, 'z1').offsetMm, zById(up.rack, 'z2').offsetMm], [222.25, 176.25], 'both 2U higher');
  assert.equal(up.summary, 'Moved FS-PDUBK to beside the rack at left-rear, U6. PDU S hangs on it and moved with it.'.replace('FS-PDUBK', 'Bracket'));
  const over = run(r, {op: 'zerou.update', id: 'z1', at: 'left-front'});
  assert.equal(zById(over.rack, 'z2').at, 'left-front', 'to another upright too');
  // where the PDU would then run past the top, the bracket is not moved
  assert.match(run(r, {op: 'zerou.update', id: 'z1', ru: 40}).error, /^PDU S hangs on it: 10U tall; /);
  // one of two brackets cannot move alone: the pitch would no longer be met
  const two = run(hung(35), {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}).rack;
  assert.equal(run(two, {op: 'zerou.update', id: 'z2', ru: 40}).error,
    'PDU A hangs on it: PDU A has mount points 1555.8 mm apart; brackets z1 and z2 are 1600.2 mm apart. Move z2 down 1U.');
  // by hand
  assert.equal(run(two, {op: 'zerou.update', id: 'z3', ru: 2}).error,
    'PDU A hangs on z1, z2: move a bracket, or take it off them with zerou.hang.');
  assert.equal(run(two, {op: 'zerou.update', id: 'z3', label: 'PDU B'}).rack.zeroU[2].label, 'PDU B', 'its label is still its own');
  // taken off, it stays where it was and is its own again
  const off = run(two, {op: 'zerou.hang', id: 'z3', on: null});
  assert.equal(off.summary, 'Took PDU A off its brackets; it stands beside the rack at left-rear, U3-U42.');
  assert.deepEqual(['heldBy' in zById(off.rack, 'z3'), zById(off.rack, 'z3').offsetMm], [false, 87.35]);
  assert.equal(run(off.rack, {op: 'zerou.hang', id: 'z3', on: null}).noop, true);
  // on its own it overlaps the brackets, as fit says of any two parts on one upright
  assert.equal(F.fitsZeroU(off.rack, zById(off.rack, 'z3'), chassisOf, {ignoreId: 'z3'}).reason, 'Overlaps Bracket at left-rear.');
});

test('a bracket removed leaves the PDU where it was, refused by fit and said, until it is hung again or freed', () => {
  const two = run(hung(35), {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}).rack;
  const gone = run(two, {op: 'zerou.remove', id: 'z2'});
  assert.equal(gone.summary, 'Removed Bracket from beside the rack. PDU A hung on it and stays where it was.');
  const pdu = zById(gone.rack, 'z3');
  assert.deepEqual([pdu.offsetMm, pdu.heldBy], [87.35, {parts: ['z1', 'z2']}], 'nothing is deleted with the bracket');
  assert.deepEqual(F.fitsZeroU(gone.rack, pdu, chassisOf, {ignoreId: 'z3'}), {ok: false, reason: 'z2 is not a bracket in this rack.'});
  assert.deepEqual(Z.fitsHang(gone.rack, pdu, ctx), {ok: false, reason: 'z2 is not a bracket in this rack.'});
  assert.deepEqual(Z.hangNotices(gone.rack, ctx), ['PDU A: z2 is not a bracket in this rack.']);
  // a frame change keeps it: it is judged for room alone while its bracket is gone
  assert.deepEqual(F.settleZeroU(gone.rack, chassisOf).removed, []);
  // A FRAME CHANGE NEVER MOVES A HUNG PART SILENTLY: 45U to 40U would bring the
  // PDU down from 87.35 mm, so it is refused, naming the part and its brackets
  assert.deepEqual(run(two, {op: 'frame', heightRU: 40}), {index: 0, error:
    'PDU A hangs on z1, z2, and this frame would move it: take it off its brackets first with zerou.hang.'});
  // and one that would move a bracket it hangs on (a two-post frame has no left-rear)
  assert.deepEqual(run(two, {op: 'frame', kind: 'two-post'}).error,
    'PDU A hangs on z1, z2, and this frame would move it: take it off its brackets first with zerou.hang.');
  const short = run(rackOf(), [{op: 'zerou.place', ref: 'bracket', at: 'left-rear', ru: 40, label: 'Bracket'},
                               {op: 'zerou.place', ref: 'duct', at: 'right-rear', ru: 1, label: 'Duct'}]).rack;
  const tip = {...short, zeroU: short.zeroU.map(z => (z.id === 'z2' ? {...z, at: 'left-rear', offsetMm: 1700, heldBy: {parts: ['z1']}} : z))};
  assert.equal(run(tip, {op: 'frame', heightRU: 39}).error,
    'Duct hangs on z1, and this frame would move it: take it off its brackets first with zerou.hang.');
  // a frame change that touches neither goes through, and the hung part is as it was
  const taller = run(two, {op: 'frame', heightRU: 44});
  assert.equal(taller.error, undefined);
  assert.deepEqual(taller.rack.zeroU, two.zeroU);
  assert.equal(run(two, {op: 'frame', numbering: 'top-down'}).rack.zeroU[2].offsetMm, 87.35);
  // taken off its brackets, the frame may change, and the parts settle each on its own
  const freed = run(two, {op: 'zerou.hang', id: 'z3', on: null}).rack;
  assert.equal(run(freed, {op: 'frame', heightRU: 40}).error, undefined);
  // a file whose PDU is not where its brackets hold it says so
  const off = {...two, zeroU: two.zeroU.map(z => (z.id === 'z3' ? {...z, offsetMm: 44.45} : z))};
  assert.deepEqual(Z.hangNotices(off, ctx), ['PDU A is not where its brackets hold it: it hangs at left-rear, 87.35 mm up.']);
});

test('bracketPositions: where the brackets go for a PDU, before any is placed', () => {
  assert.deepEqual(Z.bracketPositions(rackOf(), {ref: 'pdu', ru: 4}, ctx), {units: [0, 35], offsets: [133.35, 1689.1], exact: true});
  assert.deepEqual(Z.bracketPositions(rackOf(), {ref: 'pdu'}, ctx).offsets, [0, 1555.75]);
  assert.deepEqual(Z.bracketPositions(rackOf(), {ref: 'stub', ru: 2}, ctx), {units: [0], offsets: [44.45], exact: true});
  assert.equal(Z.bracketPositions(rackOf(), {ref: 'duct'}, ctx), null, 'a part with no mount point');
  assert.equal(Z.bracketPositions(rackOf(), {ref: 'pdu'}, {chassisOf}), null, 'the parts lists are not loaded');
  // brackets placed there do hold it
  const [a, b] = Z.bracketPositions(rackOf(), {ref: 'pdu', ru: 4}, ctx).offsets;
  const r = {...hung(20), zeroU: hung(20).zeroU.map(z => (z.id === 'z1' ? {...z, offsetMm: a} : z.id === 'z2' ? {...z, offsetMm: b} : z))};
  assert.equal(run(r, {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}).error, undefined);
});

// ── the library's own bracket (#939) ─────────────────────────────────────
// The tests above hang a PDU on a fixture bracket. These read the built facts of
// the real parts, as the Rack Builder does: the chassis sizes of rack.json and
// each device's configs.json, in the shape loadSlots answers.

const DIST = new URL('../../../library/dist/', import.meta.url);
const skip = existsSync(new URL('rack.json', DIST)) ? false : 'library/dist not built - run ./build.sh';
const built = skip ? {} : JSON.parse(readFileSync(new URL('rack.json', DIST), 'utf8')).devices;
const builtSlots = ref => {
  const f = new URL(`${ref}.configs.json`, DIST);
  if (!existsSync(f)) return null;
  const j = JSON.parse(readFileSync(f, 'utf8'));
  return {bays: j.bays || {}, cages: j.cages || {}, configs: j.configs || [], default: j.default ?? null, 'pdu-class': j['pdu-class'] ?? null};
};
const real = {chassisOf: ref => built[ref] || null, slotsOf: builtSlots};
// an EVMI2130X beside two FS-PDUBK brackets `apart` units apart from U4, both in the configuration `cfg`
function hungReal(apart, cfg) {
  const r = run(rackOf(), [
    {op: 'zerou.place', ref: 'fs-pdubk', cfg, at: 'left-rear', ru: 4, label: 'Bracket'},
    {op: 'zerou.place', ref: 'fs-pdubk', cfg, at: 'left-rear', ru: 4 + apart, label: 'Bracket'},
    {op: 'zerou.place', ref: 'evmi2130x', at: 'right-rear', ru: 1, label: 'PDU A'}], real);
  assert.equal(r.error, undefined);
  return r.rack;
}

test('FS-PDUBK publishes three pdu-button slots, 26.3 mm up the plate, in each of its two mounting options', {skip}, () => {
  const j = JSON.parse(readFileSync(new URL('fs-pdubk.configs.json', DIST), 'utf8'));
  assert.deepEqual(j.configs.map(c => c.name), ['front', 'rear']);
  assert.equal(j.default, 'front');
  for (const c of j.configs) {
    assert.deepEqual(c.slots, [{interface: 'pdu-button', at: 26.3}, {interface: 'pdu-button', at: 26.3}, {interface: 'pdu-button', at: 26.3}], c.name);
    assert.deepEqual(c['mount-points'], [], 'a bracket hangs nothing');
  }
  // the PDU's side of the same interface
  assert.deepEqual(configFacts(builtSlots('evmi2130x'), '').mountPoints, [{mates: 'pdu-button', at: 72}, {mates: 'pdu-button', at: 1627.8}]);
  // a part that stands beside the rack, two units tall
  assert.deepEqual([built['fs-pdubk'].mount, built['fs-pdubk'].ru], ['rack-side', 2]);
});

for (const cfg of ['front', 'rear']) {
  test(`an EVMI2130X hung on two FS-PDUBK brackets 35U apart fits (option ${cfg}), and 34U apart is refused with the distance`, {skip}, () => {
    const res = run(hungReal(35, cfg), {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}, real);
    assert.equal(res.error, undefined);
    const pdu = zById(res.rack, 'z3');
    // the lowest slot is 133.35 + 26.3 up, the lowest button 72 up the PDU: its bottom is 87.65 up
    assert.deepEqual([pdu.at, pdu.offsetMm, pdu.heldBy], ['left-rear', 87.65, {parts: ['z1', 'z2']}]);
    assert.deepEqual(Z.fitsHang(res.rack, pdu, real), {ok: true, place: {at: 'left-rear', offsetMm: 87.65}});
    assert.deepEqual(F.fitsZeroU(res.rack, {...pdu}, real.chassisOf, {ignoreId: 'z3'}), {ok: true}, 'it does not overlap its brackets');
    assert.deepEqual(Z.hangNotices(res.rack, real), []);
    // one unit short: the buttons are 1555.8 apart and the brackets 1511.3
    assert.deepEqual(run(hungReal(34, cfg), {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}, real), {index: 0, error:
      'PDU A has mount points 1555.8 mm apart; brackets z1 and z2 are 1511.3 mm apart. Move z2 up 1U.'});
  });
}

test('the brackets for an EVMI2130X are 35 units apart, and placed there they hold it', {skip}, () => {
  const p = Z.bracketPositions(rackOf(), {ref: 'evmi2130x', ru: 4}, real);
  assert.deepEqual(p, {units: [0, 35], offsets: [133.35, 1689.1], exact: true});
  const r = run(rackOf(), [
    {op: 'zerou.place', ref: 'fs-pdubk', at: 'left-rear', ru: 4 + p.units[0], label: 'Bracket'},
    {op: 'zerou.place', ref: 'fs-pdubk', at: 'left-rear', ru: 4 + p.units[1], label: 'Bracket'},
    {op: 'zerou.place', ref: 'evmi2130x', at: 'right-rear', ru: 1, label: 'PDU A'},
    {op: 'zerou.hang', id: 'z3', on: ['z1', 'z2']}], real);
  assert.equal(r.error, undefined);
});

// ── overlap in millimetres ───────────────────────────────────────────────

test('zero-U overlap is judged in millimetres: whole units as before, and an offset between units where it says', () => {
  let r = run(rackOf(), {op: 'zerou.place', ref: 'duct', at: 'left-front', ru: 1, label: 'Duct A'}).rack;   // 0 to 88.9 mm
  // by the unit, exactly as before
  assert.equal(F.fitsZeroU(r, {ref: 'duct', at: 'left-front', ru: 2}, chassisOf).reason, 'Overlaps Duct A at left-front.');
  assert.deepEqual(F.fitsZeroU(r, {ref: 'duct', at: 'left-front', ru: 3}, chassisOf), {ok: true});
  assert.deepEqual(F.fitsZeroU(r, {ref: 'duct', at: 'right-front', ru: 1}, chassisOf), {ok: true});
  // by its offset: 70 mm is inside Duct A, where rounding to a unit put it at U3, clear of it
  assert.equal(M.zeroUBottom({offsetMm: 70}), 3);
  assert.equal(F.fitsZeroU(r, {ref: 'duct', at: 'left-front', offsetMm: 70}, chassisOf).reason, 'Overlaps Duct A at left-front.');
  assert.deepEqual(F.fitsZeroU(r, {ref: 'duct', at: 'left-front', offsetMm: 88.9}, chassisOf), {ok: true});
  assert.deepEqual(F.fitsZeroU(r, {ref: 'duct', at: 'left-front', offsetMm: 88.5}, chassisOf).ok, false);
  // the top and the bottom, in mm: 45U is 2000.25 mm
  assert.deepEqual(F.fitsZeroU(rackOf(), {ref: 'duct', at: 'left-front', offsetMm: 2000.25 - 88.9}, chassisOf), {ok: true});
  assert.equal(F.fitsZeroU(rackOf(), {ref: 'duct', at: 'left-front', offsetMm: 1930}, chassisOf).reason, '2U tall; 2U from U44 to the top of this 45U rack.');
  assert.equal(F.fitsZeroU(rackOf(), {ref: 'duct', at: 'left-front', offsetMm: -5}, chassisOf).reason, 'Below U1.');
  assert.deepEqual(F.zeroUExtent({ref: 'duct', offsetMm: 120.65}, chassisOf), [120.65, 209.55]);
  // a frame change leaves a part between units where it is when it fits, and brings one past the top down
  const odd = {...r, zeroU: [...r.zeroU, {id: 'z2', ref: 'duct', at: 'right-front', offsetMm: 120.65}]};
  assert.equal(F.settleZeroU(odd, chassisOf).rack, odd);
  const low = F.settleZeroU({...odd, frame: {...odd.frame, heightRU: 4}}, chassisOf);
  assert.deepEqual(low.rack.zeroU.map(z => z.offsetMm), [0, 88.9]);
});

// ── states ───────────────────────────────────────────────────────────────

const doc = zeroU => ({format: 'portrayal-rack', version: 4, id: 'd', racks: [{id: 'r1', name: 'R1', frame: {kind: 'four-post', heightRU: 45},
  items: [], zeroU, cables: []}]});
const PDU = {id: 'z2', ref: 'pdu', cfg: '', label: 'PDU A', at: 'left-rear', offsetMm: 133.35};

test('a state the part does not declare is kept, not applied, and named', () => {
  const read = M.parseDoc(doc([{...PDU, states: {'outlet-a1': 'standby', 'outlet-a2': 'off', 'breaker-a': 'on'}}]));
  const pdu = read.racks[0].zeroU[0];
  assert.deepEqual(pdu.states, {'outlet-a1': 'standby', 'outlet-a2': 'off', 'breaker-a': 'on'}, 'kept as the file has it');
  const facts = configFacts(slotsOf('pdu'), pdu.cfg);
  assert.deepEqual(ST.statesFor(pdu, facts), {'outlet-a2': 'off'}, 'only what the part declares is handed to a drawing');
  assert.deepEqual(ST.stateNotices(read.racks[0], ctx), [
    'outlet-a1 on PDU A cannot be standby: it can be on or off.',
    'breaker-a on PDU A cannot be set: it declares no state. It declares: outlet-a1, outlet-a2 can be on or off.']);
  assert.deepEqual(JSON.parse(M.serialize(read)).racks[0].zeroU[0].states, pdu.states, 'and saved as it was');
  // with no facts nothing is checked, and nothing is applied or said
  assert.deepEqual(ST.statesFor(pdu, null), {});
  assert.deepEqual(ST.stateNotices(read.racks[0], {chassisOf}), []);
  // the command refuses what the loader keeps
  const r = read.racks[0];
  assert.deepEqual(run(r, {op: 'state.set', id: 'z2', path: 'outlet-a2', state: 'standby'}),
    {error: 'outlet-a2 on PDU A cannot be standby: it can be on or off.', index: 0});
  assert.deepEqual(run(r, {op: 'state.set', id: 'z2', path: 'breaker-b', state: 'on'}),
    {error: 'breaker-b on PDU A cannot be set: it declares no state. It declares: outlet-a1, outlet-a2 can be on or off.', index: 0});
  const on = run(r, {op: 'state.set', id: 'z2', path: 'outlet-a1', state: 'on'});
  assert.equal(on.summary, 'Set outlet-a1 on PDU A to on.');
  assert.equal(on.rack.zeroU[0].states['outlet-a1'], 'on');
  assert.equal(run(on.rack, {op: 'state.set', id: 'z2', path: 'outlet-a1', state: 'on'}).noop, true);
  // null clears one, and the key goes with the last
  let c = run(on.rack, {op: 'state.set', id: 'z2', path: 'outlet-a1', state: null}).rack;
  assert.deepEqual(Object.keys(c.zeroU[0].states), ['outlet-a2', 'breaker-a']);
  c = run(c, [{op: 'state.set', id: 'z2', path: 'outlet-a2', state: null}, {op: 'state.set', id: 'z2', path: 'breaker-a', state: null}]).rack;
  assert.equal('states' in c.zeroU[0], false);
  // on a device on the rails too
  const sw = M.withItem(rackOf(), {ref: 'sw', cfg: '', ru: 5, label: 'leaf'}).rack;
  assert.equal(run(sw, {op: 'state.set', id: 'i1', path: 'psu-1', state: 'off'}).rack.items[0].states['psu-1'], 'off');
  assert.equal(run(sw, {op: 'state.set', id: 'i1', path: 'psu-1', state: 'idle'}).error, 'psu-1 on leaf cannot be idle: it can be on or off.');
  assert.equal(run(sw, {op: 'state.set', id: 'i9', path: 'psu-1', state: 'off'}).error, 'That device is no longer in the rack.');
});

test('an outlet state reaches its lamp path in the map handed to a drawing', () => {
  const pdu = {...PDU, states: {'outlet-a1': 'on', 'outlet-a2': 'off'}};
  // the lamps bound to each outlet by `for:`, as the drawing gives them (kit/states.js boundLamps)
  const bindings = new Map([['outlet-a1', ['led-a1']], ['outlet-a2', ['led-a2']]]);
  const facts = {...configFacts(slotsOf('pdu'), ''), bindings};
  assert.deepEqual(ST.statesFor(pdu, facts), {'outlet-a1': 'on', 'outlet-a2': 'off', 'led-a1': 'on', 'led-a2': 'off'});
  // a state that is not applied does not reach a lamp either
  assert.deepEqual(ST.statesFor({...PDU, states: {'outlet-a1': 'standby'}}, facts), {});
  // without bindings the map names the outlets, and a drawing that applies it expands it itself
  assert.deepEqual(ST.statesFor(pdu, configFacts(slotsOf('pdu'), '')), {'outlet-a1': 'on', 'outlet-a2': 'off'});
});

test('the loader reads states entry by entry: one that is no name is dropped, and said', () => {
  const notes = [];
  const read = M.parseDoc(doc([{...PDU, states: {'outlet-a1': 'on', 'outlet-a2': 1, 'outlet-a3': '', 'outlet-a4': null}},
                               {id: 'z3', ref: 'pdu', at: 'right-rear', offsetMm: 0, label: 'PDU B', states: ['on']}]), {notes});
  assert.deepEqual(read.racks[0].zeroU[0].states, {'outlet-a1': 'on'});
  assert.equal('states' in read.racks[0].zeroU[1], false);
  assert.deepEqual(notes, ['R1: outlet-a2, outlet-a3, outlet-a4 on PDU A had a state that is not a name, so they were dropped.',
                           'R1: The states of PDU B were not a map of part to state, so they were dropped.']);
  // on an item the same
  const d = doc([]);
  d.racks[0].items = [{id: 'i1', ref: 'sw', ru: 1, label: 'leaf', states: {'psu-1': 'off', 'psu-2': 7}}];
  const n2 = [];
  assert.deepEqual(M.parseDoc(d, {notes: n2}).racks[0].items[0].states, {'psu-1': 'off'});
  assert.deepEqual(n2, ['R1: psu-2 on leaf had a state that is not a name, so it was dropped.']);
  // an entry that carries none gains none
  assert.equal('states' in M.parseDoc(doc([PDU])).racks[0].zeroU[0], false);
});

// ── readings ─────────────────────────────────────────────────────────────

const READ = {source: 'SNMP poll of the PDU network module', at: '2026-10-08T14:05:00Z',
              values: {'outlet-a1': {'current-a': 1.8, 'power-w': 372}, input: {'current-a': 19.6}}};

test('a reading with no source moves to readingsAsWritten, and nothing draws it', () => {
  const bad = {at: READ.at, values: READ.values};
  const notes = [];
  const read = M.parseDoc(doc([{...PDU, readings: bad}]), {notes});
  const pdu = read.racks[0].zeroU[0];
  assert.equal('readings' in pdu, false);
  assert.deepEqual(pdu.readingsAsWritten, bad);
  assert.deepEqual(notes, ['R1: The readings of PDU A have no source or no time that can be read, so they are kept as written and not shown.']);
  assert.equal(ST.readingsFor(pdu, configFacts(slotsOf('pdu'), '')), null);
  // saved and opened again it is still kept, and not said twice over as a fault of the file
  const again = M.parseDoc(M.serialize(read));
  assert.deepEqual(again.racks[0].zeroU[0], pdu);
  // a time that cannot be read, values that are no map, and a list, go the same way
  for (const r of [{...READ, at: 'yesterday'}, {...READ, at: 5}, {...READ, source: ''}, {...READ, values: [1]}, {...READ, values: {a: 2}}, 'none', []])
    assert.deepEqual(M.parseDoc(doc([{...PDU, readings: r}])).racks[0].zeroU[0].readingsAsWritten, r, JSON.stringify(r));
  // each with the reason that applies: values that are no map are not a missing source
  const n2 = [];
  M.parseDoc(doc([{...PDU, readings: {...READ, values: [1]}}]), {notes: n2});
  assert.deepEqual(n2, ['R1: The readings of PDU A have values that are not a map of part to what was read there, so they are kept as written and not shown.']);
  // `readings: null` is no key at all, and neither is a null kept as written
  for (const entry of [{...PDU, readings: null}, {...PDU, readingsAsWritten: null}, {...PDU, readings: undefined}]) {
    const n3 = [], z = M.parseDoc(doc([entry]), {notes: n3}).racks[0].zeroU[0];
    assert.deepEqual(['readings' in z, 'readingsAsWritten' in z, n3], [false, false, []]);
  }
  // whole readings are kept as readings, with or without values, on an item too
  assert.deepEqual(M.parseDoc(doc([{...PDU, readings: READ}])).racks[0].zeroU[0].readings, READ);
  const bare = {source: 'poll', at: '2026-10-08T14:05:00Z'};
  assert.deepEqual(M.parseDoc(doc([{...PDU, readings: bare}])).racks[0].zeroU[0].readings, bare);
  const d = doc([]);
  d.racks[0].items = [{id: 'i1', ref: 'sw', ru: 1, readings: bad}];
  assert.deepEqual(M.parseDoc(d).racks[0].items[0].readingsAsWritten, bad);
});

test('readings are shown with their source and time, and not for a PDU that measures nothing', () => {
  const pdu = {...PDU, readings: READ};
  assert.deepEqual(ST.readingsFor(pdu, configFacts(slotsOf('pdu'), '')), {source: READ.source, at: READ.at,
    badges: [{path: 'outlet-a1', 'current-a': 1.8, 'power-w': 372}, {path: 'input', 'current-a': 19.6}]});
  assert.equal(ST.readingsFor(pdu, null), null);
  const basic = {...pdu, ref: 'basic', label: 'PDU B'};
  assert.equal(ST.readingsFor(basic, configFacts(slotsOf('basic'), '')), null);
  assert.deepEqual(ST.stateNotices({items: [], zeroU: [basic]}, ctx), ['BASIC-PDU measures nothing, so there is no reading for outlet-a1, input.']);
  // the commands
  const r = {...rackOf(), zeroU: [PDU, {...PDU, id: 'z3', ref: 'basic', at: 'right-rear', label: 'PDU B'}]};
  const set = run(r, {op: 'readings.set', id: 'z2', readings: READ});
  assert.equal(set.summary, 'Stored the readings of PDU A.');
  assert.deepEqual(set.rack.zeroU[0].readings, READ);
  assert.equal(run(set.rack, {op: 'readings.set', id: 'z2', readings: READ}).noop, true);
  assert.equal(run(r, {op: 'readings.set', id: 'z2', readings: {at: READ.at}}).error,
    'readings.set needs readings with a source, a time (at) that can be read, and values by part.');
  assert.equal(run(r, {op: 'readings.set', id: 'z3', readings: READ}).error, 'BASIC-PDU measures nothing, so there is no reading for outlet-a1, input.');
  const cleared = run(set.rack, {op: 'readings.set', id: 'z2', readings: null});
  assert.equal('readings' in cleared.rack.zeroU[0], false);
  assert.equal(run(cleared.rack, {op: 'readings.set', id: 'z2', readings: null}).noop, true);
});

// ── swaps and fields beside the rack ─────────────────────────────────────

test('a part beside the rack takes swaps and fields, each map replaced whole, and keeps them', () => {
  const r = {...rackOf(), zeroU: [PDU]};
  const res = run(r, {op: 'zerou.update', id: 'z2', swaps: {'bay-1': 'eaton/network-module@1'}, fields: {'section-a-label': {text: 'Row 4 A'}}});
  assert.equal(res.error, undefined);
  assert.deepEqual([res.rack.zeroU[0].swaps, res.rack.zeroU[0].fields], [{'bay-1': 'eaton/network-module@1'}, {'section-a-label': {text: 'Row 4 A'}}]);
  assert.equal(res.rack.zeroU[0].offsetMm, 133.35, 'it does not move');
  assert.equal(run(res.rack, {op: 'zerou.update', id: 'z2', swaps: {'bay-1': 'eaton/network-module@1'}}).noop, true);
  assert.deepEqual(run(res.rack, {op: 'zerou.update', id: 'z2', swaps: {}}).rack.zeroU[0].swaps, {});
  assert.deepEqual(M.parseDoc(M.serialize({...M.newDoc(), racks: [res.rack]})).racks[0].zeroU[0], res.rack.zeroU[0]);
  // an entry never given them has neither key
  assert.deepEqual(['swaps' in r.zeroU[0], 'fields' in r.zeroU[0]], [false, false]);
});
