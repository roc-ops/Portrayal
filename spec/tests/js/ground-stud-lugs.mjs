// A ring lug on a ground stud, offered and seated BY THE KIT (#789,
// docs/connectors-dc-terminal-design.md section 13), against REAL compiled
// faces. test_ground_stud_lugs.py renders the devices, builds components.json
// and the skins in tmp, and hands this script each bare face (fake-dom form)
// with the device index of the same build: `bays` and `cages`, keyed by view.
//
// A ground stud placed on the chassis is a DEVICE cage - its entry is in the
// index's `cages[view]`, id = the placement id. A stud of the Casa terminal
// is a NESTED slot, read off the drawing and components.json. Both are asked
// for here, and what the kit seats is compared in Python with what render.py
// drew for a configuration that asks for the same lug.
//
// stdin JSON {components, skins, cases: {name: {face, view, slot, ref, bays,
// cages}}}; one JSON object out, a key per case. A case that throws records
// {error} under its key.
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
    // the interfaces this case is about: a single stud's, or (#828) a pair's
    // as well, which test_two_hole_lugs.py asks for
    const ifaces = c.ifaces || ['terminal-stud'];
    const studs = walk().filter(e => ifaces.includes(e.interface));
    const offered = m.faceCages(root, deviceCages, compByRef, {offered: true})
      .filter(e => ifaces.includes(e.interface)).map(e => e.id);
    const find = () => walk().find(e => e.id === c.slot);
    const entry = find();
    const result = entry
      ? await m.applyOccupantOverrides(root, [entry], {[c.slot]: c.ref}, loadSkin)
      : {error: `no slot ${c.slot}`};
    const lug = seated(root, c.slot);
    const occRef = entry ? m.occupantRef(root, find()) : null;
    // a second swap replaces; it does not stack
    if (entry) await m.applyOccupantOverrides(root, [find()], {[c.slot]: c.ref}, loadSkin);
    const again = occupantsAt(root, c.slot).length;
    const others = studs.filter(e => e.id !== c.slot).map(e => occupantsAt(root, e.id).length);
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
    out[name] = {studs: studs.map(plain), offered, result, lug, occRef, again, others,
                 left: occupantsAt(root, c.slot).length, threeD};
  } catch (e) { out[name] = {error: String(e && e.stack || e)}; }
}
console.log(JSON.stringify(out));
