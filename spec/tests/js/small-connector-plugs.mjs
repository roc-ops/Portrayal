// A cable plug on an MRJ21 or VHDCI jack that is on a card in a bay, offered
// and seated BY THE KIT (#790, docs/connectors-mrj21-vhdci-rj11-design.md),
// against REAL compiled faces. test_small_connector_plugs.py renders the
// devices with the cards in their bays and the jacks empty, builds
// components.json and the skins in tmp, and hands this script each bare face
// (fake-dom form) with the device index of the same build: `bays` and
// `cages`, keyed by view.
//
// Every such jack is a NESTED slot, read off the drawing and components.json:
// one bay down on an Oscilloquartz card, two bays down on a Nokia MDA in its
// IOM. What the kit seats is compared in Python with what render.py drew for
// a configuration that asks for the same plug.
//
// stdin JSON {components, skins, cases: {name: {face, view, slot, ref,
// interface, bays, cages}}}; one JSON object out, a key per case. A case that
// throws records {error} under its key.
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
const plain = e => e && {id: e.id, key: e.key ?? null, kind: e.kind, interface: e.interface,
                         accepts: e.accepts, default: e.default, lift: e.lift, mate: e.mate,
                         rotate: e.rotate ?? null, modulePath: e.modulePath ?? null,
                         carrier: e.carrier ?? null};

const out = {};
for (const [name, c] of Object.entries(input.cases)) {
  try {
    const root = build(c.face);
    const deviceCages = c.cages[c.view] || [];
    // every slot of the face: the device's own cages and the nested ones
    const walk = () => m.faceCages(root, deviceCages, compByRef);
    const slots = walk().filter(e => e.interface === c.interface);
    const offered = m.faceCages(root, deviceCages, compByRef, {offered: true})
      .filter(e => e.interface === c.interface).map(e => e.id);
    const find = () => walk().find(e => e.id === c.slot);
    const entry = find();
    const result = entry
      ? await m.applyOccupantOverrides(root, [entry], {[c.slot]: c.ref}, loadSkin)
      : {error: `no slot ${c.slot}`};
    const plug = seated(root, c.slot);
    const occRef = entry ? m.occupantRef(root, find()) : null;
    // a second swap replaces; it does not stack
    if (entry) await m.applyOccupantOverrides(root, [find()], {[c.slot]: c.ref}, loadSkin);
    const again = occupantsAt(root, c.slot).length;
    const others = slots.filter(e => e.id !== c.slot).map(e => occupantsAt(root, e.id).length);
    if (entry) await m.applyOccupantOverrides(root, [find()], {[c.slot]: null}, loadSkin);
    // THE 3D PASS, on fresh copies of the face, with the device index as the
    // build published it for EVERY view: which views the override map is
    // taken to touch (viewsToRewrite), what seatViews then seats, and what
    // the per-face pass seats when it is handed the face directly.
    const devIndex = {bays: c.bays, cages: c.cages};
    const views = [...new Set([...Object.keys(c.bays || {}), ...Object.keys(c.cages || {})])];
    const map = {[c.slot]: c.ref};
    const named = m.viewsToRewrite(devIndex, map);
    const viaViews = build(c.face);
    const res = await m.seatViews({[c.view]: viaViews}, devIndex, map, loadSkin, compByRef);
    const direct = build(c.face);
    const face = await m.seatFace(direct, {bays: (c.bays || {})[c.view] || [], cages: deviceCages},
                                  map, loadSkin, compByRef);
    const threeD = {named, views, viewsSeated: occupantsAt(viaViews, c.slot).length,
                    viewsApplied: res[c.view] ? res[c.view].applied : null,
                    faceApplied: face.applied, faceRefused: face.refused, faceFailed: face.failed,
                    faceSeated: occupantsAt(direct, c.slot).length};
    out[name] = {slots: slots.map(plain), offered, result, plug, occRef, again, others,
                 left: occupantsAt(root, c.slot).length, threeD};
  } catch (e) { out[name] = {error: String(e && e.stack || e)}; }
}
console.log(JSON.stringify(out));
