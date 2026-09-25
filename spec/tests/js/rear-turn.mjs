// A back seen through the rear cutout of a TURNED bay, as the kit places it.
// render.py's faces.rear_place has a twin in swap.js (`rearAt` with a turn),
// which a swap uses to put a new module's back in the hole; and relief.js
// turns the module's body with it (`bodyPose`). All three are checked here in
// node, on the fake DOM the other seating scripts use.
//
// argv[2] is a JSON object:
//   places: [{box, comp, turn, back}]  - rearAt(box, comp, turn, back) each
//   poses:  [{m, fp}]                  - bodyPose(m, fp) each
//   hole:   {box, turn, ref, comp, back} - one hole swapped to `ref`, whose
//           contract is `comp` and whose back drawing is `back` ({w, h})
globalThis.location = { search: '' };
globalThis.fetch = async () => ({ ok: true, text: async () => '<svg/>' });
import {Node, install} from './fake-dom.mjs';
install();
const swap = await import('../../../kit/swap.js');
const relief = await import('../../../kit/relief.js');

const inp = JSON.parse(process.argv[2]);
const out = {};
out.places = (inp.places || []).map(c => swap.rearAt(c.box, c.comp, c.turn, c.back));
out.poses = (inp.poses || []).map(c => relief.bodyPose(c.m, c.fp));

if (inp.hole) {
  const h = inp.hole;
  const BACK = `${h.ref.split('@')[0]}-rear@1`;
  const COMP = {[h.ref]: {name: 'mod', ...h.comp, faces: {rear: BACK}},
                [BACK]: {name: 'mod-rear', size: h.back}};
  const compByRef = ref => COMP[ref.split(':')[0]] || null;
  const loadSkin = async ref => {
    const c = compByRef(ref);
    return c ? {comp: c, text: JSON.stringify({a: {}, c: [{a: {id: c.name, 'data-class': 'cassette'}}]})}
             : null;
  };
  const attrs = {id: 'cutout--back-1', 'data-path': 'cutout:back-1', 'data-class': 'cutout',
                 'data-rear-of': 'bay-1', 'data-rear-bay': h.box};
  if (h.turn) attrs['data-rear-rotate'] = String(h.turn);
  const root = new Node({}, [new Node(attrs, [])]);
  await swap.applyRearOverrides(root, {'bay-1': h.ref}, loadSkin, compByRef);
  const hole = root.querySelector('[data-rear-of="bay-1"]');
  const back = hole.querySelector(':scope > [data-projection]');
  out.hole = {transform: back?.getAttribute('transform') ?? null,
              at: hole.getAttribute('data-rear-at')};
}
console.log(JSON.stringify(out));
