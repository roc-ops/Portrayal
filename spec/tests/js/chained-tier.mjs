// The chained tier in the kit (#611), run against REAL compiled faces.
// test_chained_tier_js.py renders tmp copies of two devices with
// configurations that stop at each tier - an optic, then a plug on it, then a
// boot on the plug - and hands this script the faces (fake-dom form), the
// index and the skins, with the scenarios to run. What the kit does to a face
// here is compared, in Python, with what render.py drew for the configuration
// that asks for the same thing.
//
// Modes, by argv[2]:
//   scenarios - stdin JSON {components, skins, devices: {dev: {faces, cages}},
//               scenarios: [{name, dev, from, overrides, keys, empty, click}]};
//               one JSON object out, a key per scenario. A scenario that
//               throws records {error} under its key and the rest still run.
import {build, install} from './fake-dom.mjs';

const m = await import('../../../kit/swap.js');
install();

let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const input = JSON.parse(raw);
const COMPS = new Map(input.components.map(c => [`${c.ns}/${c.name}@${c.major.slice(1)}`, c]));
const compByRef = ref => COMPS.get(String(ref).split(':')[0]) || null;
const loadSkin = async ref => {
  const comp = compByRef(ref);
  const text = input.skins[String(ref).split(':')[0]];
  return comp && text ? {comp, text} : null;
};
const attrsOf = n => Object.fromEntries(n.attributes.map(x => [x.name, x.value]));
const occupantsAt = (root, key) => root.querySelectorAll(`[data-for="${key}"]`)
  .filter(n => (n.getAttribute('data-path') || '').endsWith('-occupant'));
const empty = n => n.tagName === 'style' && !n.children.length;
function seated(root, key) {
  const occ = occupantsAt(root, key);
  const [g] = occ;
  return {
    count: occ.length,
    parent: g?.parentNode?.getAttribute('data-path') ?? null,
    transform: g?.getAttribute('transform') ?? null,
    attrs: g ? attrsOf(g) : null,
    children: g ? [...g.descendants()].filter(n => !empty(n)).map(n => ({t: n.tagName, a: attrsOf(n)})) : null,
    reason: null,
  };
}
const plain = e => e && {id: e.id, key: e.key, kind: e.kind, interface: e.interface,
                         accepts: e.accepts, lift: e.lift, rotate: e.rotate, host: e.host,
                         chained: !!e.chained, modulePath: e.modulePath ?? null};

const out = {};
for (const s of input.scenarios) {
  try {
    const dev = input.devices[s.dev];
    const cages = dev.cages;
    // THE RELOAD'S GATE, drawing-less: which keys of a swap= map survive
    if (s.accept) {
      const built = s.builtOcc || {};
      out[s.name] = m.acceptSwaps(s.accept, {bays: [], cages, compByRef,
        builtOcc: k => Object.prototype.hasOwnProperty.call(built, k) ? built[k] : undefined});
      continue;
    }
    const root = build(dev.faces[s.from]);
    const res = s.overrides
      ? await m.applyFaceOverrides(root, {bays: [], cages}, s.overrides, loadSkin, compByRef)
      : null;
    const slots = m.faceCages(root, cages, compByRef);
    out[s.name] = {
      res: res && {applied: res.applied, refused: res.refused, failed: res.failed},
      seated: Object.fromEntries((s.keys || []).map(k => [k, seated(root, k)])),
      chained: slots.filter(e => e.chained).map(plain),
      offered: m.faceCages(root, cages, compByRef, {offered: true}).map(e => e.id),
      clicks: Object.fromEntries((s.click || []).map(p => [p, m.cageAt(root, p, cages, compByRef)?.id ?? null])),
      gone: Object.fromEntries((s.empty || []).map(p => [p, root.querySelectorAll(`[data-path="${p}"]`).length])),
    };
  } catch (e) {
    out[s.name] = {error: String(e && e.stack || e)};
  }
}
console.log(JSON.stringify(out));
