// The lug seats of a barrier terminal block, read and seated BY THE KIT
// (#789, docs/connectors-dc-terminal-design.md section 12), against REAL
// compiled faces. test_terminal_lugs.py renders the devices, builds
// components.json and the skins in tmp, and hands this script the bare faces
// (fake-dom form), the index and the skins. What the kit's own slot walk
// offers, and what it seats, is compared in Python with what render.py drew
// for a configuration that asks for the same lug.
//
// stdin JSON {components, faces, skins, cages, bays, asks}; one JSON object out, a
// key per face. A face that throws records {error} under its key.
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
const empty = n => n.tagName === 'style' && !n.children.length;
const occupantsAt = (root, key) => root.querySelectorAll(`[data-for="${key}"]`)
  .filter(n => (n.getAttribute('data-path') || '').endsWith('-occupant'));
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
                         accepts: e.accepts, default: e.default, lift: e.lift, mate: e.mate,
                         rotate: e.rotate, modulePath: e.modulePath, carrier: e.carrier};

const out = {};
for (const [name, ask] of Object.entries(input.asks)) {
  try {
    const root = build(input.faces[name]);
    const deviceCages = input.cages[name] || [];
    const walk = () => m.nestedSlots(root, compByRef, {deviceCages, all: true});
    const studs = walk().filter(e => e.interface === 'terminal-stud');
    const offered = m.faceCages(root, deviceCages, compByRef, {offered: true})
      .filter(e => e.interface === 'terminal-stud').map(e => e.id);
    const entry = walk().find(e => e.id === ask.slot);
    const result = entry
      ? await m.applyOccupantOverrides(root, [entry], {[ask.slot]: ask.ref}, loadSkin)
      : {error: `no slot ${ask.slot}`};
    const lug = seated(root, ask.slot);
    const occRef = entry ? m.occupantRef(root, walk().find(e => e.id === ask.slot)) : null;
    // a second swap replaces; it does not stack
    if (entry) await m.applyOccupantOverrides(root, [walk().find(e => e.id === ask.slot)],
                                              {[ask.slot]: ask.ref}, loadSkin);
    const again = occupantsAt(root, ask.slot).length;
    const others = studs.filter(e => e.id !== ask.slot).map(e => occupantsAt(root, e.id).length);
    if (entry) await m.applyOccupantOverrides(root, [walk().find(e => e.id === ask.slot)],
                                              {[ask.slot]: null}, loadSkin);
    // THE 3D PASS, on fresh copies of the face: which views the override map
    // is taken to touch (viewsToRewrite), what seatViews then seats, and what
    // the per-face pass seats when it is handed the face directly.
    const devIndex = {bays: {front: input.bays[name] || []}, cages: {front: deviceCages}};
    const map = {[ask.slot]: ask.ref};
    const named = m.viewsToRewrite(devIndex, map);
    const viaViews = build(input.faces[name]);
    const views = await m.seatViews({front: viaViews}, devIndex, map, loadSkin, compByRef);
    const direct = build(input.faces[name]);
    const face = await m.seatFace(direct, {bays: devIndex.bays.front, cages: deviceCages},
                                  map, loadSkin, compByRef);
    const threeD = {named, viewsSeated: occupantsAt(viaViews, ask.slot).length,
                    viewsApplied: views.front ? views.front.applied : null,
                    faceApplied: face.applied, faceRefused: face.refused, faceFailed: face.failed,
                    faceSeated: occupantsAt(direct, ask.slot).length};
    out[name] = {studs: studs.map(plain), offered, result, lug, occRef, again, others,
                 left: occupantsAt(root, ask.slot).length, threeD};
  } catch (e) { out[name] = {error: String(e && e.stack || e)}; }
}
console.log(JSON.stringify(out));
