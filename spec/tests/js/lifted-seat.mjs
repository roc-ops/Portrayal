// An occupant the kit seats in a LIFTED slot must be the occupant the build
// seats there (B3 Task 9).
//
// A slot whose aperture stands off the face by L makes the build do two things
// to what it seats (render.py `_seat_nested_occupants` / draw_placement's seat
// trio): `data-z-lift` on the occupant group, and every descendant's absolute
// `data-z-out` moved by `_inset_feature(feat, back=-L, group_lift=L)`. The kit
// refused such a slot until it did both. test_lifted_seat_js.py renders REAL
// faces, takes EVERY occupant out of them (the build's stay behind as the
// answer) and hands this script the emptied face, the components.json entries
// and the compiled skins; what the kit seats back is compared with what
// render.py wrote.
//
// WHERE THE SLOT ENTRY COMES FROM: the kit's own nestedSlots (B3 Task 10a),
// which reads a slot off ANY carrier - a card (`<bay>/module`), an adapter
// placed on the device (`xc01/tx`), one composed on a card
// (`slot-1/module/edfa/tx`). Task 9 built those entries here, in
// `slotEntries` below, because nothing in the kit found them yet; the helper
// is kept as the reference the kit's entry is checked against, field for
// field, on every carrier the parity seats into.
//
// Cases, chosen by argv[2]:
//   parity - stdin JSON {cases: [{name, face, comps, skins, keys: [{key, ref,
//            carrier}]}]}; per key what the kit seated.
// SWAP_MODULE names the swap.js to load (the non-vacuity test hands a mutated
// copy); by default the kit's own.
import {pathToFileURL} from 'node:url';
import {build, install} from './fake-dom.mjs';

const m = await import(process.env.SWAP_MODULE
  ? pathToFileURL(process.env.SWAP_MODULE).href : '../../../kit/swap.js');
const mode = process.argv[2];
install();

const attrsOf = n => Object.fromEntries(n.attributes.map(x => [x.name, x.value]));
const byPath = (root, p) => root.querySelector(`[data-path="${p}"]`);
// by `data-for` and the build's `-occupant` name, not by data-behaviour: a
// plug carries none (test_lifted_seat_js.py `is_occupant`)
const occupantsOf = (root, key) => root.querySelectorAll(`[data-for="${key}"]`)
  .filter(n => (n.getAttribute('data-path') || '').endsWith('-occupant'));

// The entry Task 9 wrote, for a carrier group at any path - now only the
// reference nestedSlots is held to. The sum is seatDepth's: every
// `data-z-lift` from the carrier's group up.
function slotEntries(root, carrier, compByRef) {
  const mod = byPath(root, carrier);
  const ref = (mod?.getAttribute('data-ref') || '').split(':')[0];
  const comp = ref ? compByRef(ref) : null;
  let depth = 0;
  for (let n = mod; n && typeof n.getAttribute === 'function'; n = n.parentNode)
    depth += +(n.getAttribute('data-z-lift') || 0) || 0;
  const mirrored = /scale\(\s*-/.test(mod?.getAttribute('transform') || '');
  return (comp?.cages || []).map(c => ({
    ...c, id: `${carrier}/${c.id}`, cage: c.id, lift: (+c.lift || 0) + depth,
    'seat-depth': depth, mirror: !!c.mirror || mirrored, module: mod,
    modulePath: carrier, moduleId: mod.getAttribute('id') || '', carrier: ref}));
}

const plain = e => e && {id: e.id, cage: e.cage, lift: e.lift, 'seat-depth': e['seat-depth'],
                         mate: e.mate, rotate: e.rotate, mirror: e.mirror,
                         modulePath: e.modulePath, moduleId: e.moduleId, carrier: e.carrier};

if (mode === 'parity') {
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;
  const {cases} = JSON.parse(raw);
  const out = [];
  for (const {name, face, comps, skins, keys} of cases) {
    const root = build(face);
    const compByRef = ref => comps[ref] || null;
    const nested = m.nestedSlots(root, compByRef);
    const entries = [], helperVsKit = [];
    for (const carrier of [...new Set(keys.map(k => k.carrier))]) {
      const mine = slotEntries(root, carrier, compByRef);
      const kit = nested.filter(c => c.modulePath === carrier);
      helperVsKit.push({carrier, same: JSON.stringify(mine.map(plain)) === JSON.stringify(kit.map(plain)),
                        n: kit.length});
      entries.push(...kit);
    }
    const before = Object.fromEntries(keys.map(({key}) => [key, occupantsOf(root, key).length]));
    const loadSkin = async ref => comps[ref] && skins[ref] ? {comp: comps[ref], text: skins[ref]} : null;
    const overrides = Object.fromEntries(keys.map(({key, ref}) => [key, ref]));
    const result = await m.applyOccupantOverrides(root, entries, overrides, loadSkin);
    const empty = n => n.tagName === 'style' && !n.children.length;
    const seated = {};
    for (const {key} of keys) {
      const occ = occupantsOf(root, key);
      const [g] = occ;
      const e = entries.find(c => c.id === key);
      seated[key] = {
        count: occ.length,
        parent: g?.parentNode?.getAttribute('data-path') ?? null,
        transform: g?.getAttribute('transform') ?? null,
        attrs: g ? attrsOf(g) : null,
        children: g ? [...g.descendants()].filter(n => !empty(n))
          .map(n => ({t: n.tagName, a: attrsOf(n)})) : null,
        entry: plain(e),
        reason: e ? m.refusalReason(e) : 'no entry',
      };
    }
    out.push({name, before, result, helperVsKit, seated});
  }
  console.log(JSON.stringify(out));
}

// ---------------------------------------------------------------- inset
// stdin JSON [[feat, back, groupLift], ...] -> insetFeature of each (null for
// a dropped feature), compared in Python with render.py's _inset_feature.
if (mode === 'inset') {
  let raw = '';
  for await (const chunk of process.stdin) raw += chunk;
  console.log(JSON.stringify(JSON.parse(raw).map(([f, b, g]) => m.insetFeature(f, b, g))));
}
