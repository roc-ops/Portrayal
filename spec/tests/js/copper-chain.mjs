// The copper SFP chain in the kit (#649), run against REAL compiled faces of
// the edgecore/agr560. test_copper_chain_js.py renders a tmp copy with
// configurations that stop at each link - generic/sfp-rj45@1 in `port-0`
// (upright) and `port-1` (drawn at rotate 180), then generic/rj45-plug@1 in
// each one's jack, then common/rj45-boot@1 on each plug - and hands this
// script the faces (fake-dom form), the index and the skins. What the kit
// does to a face here is compared, in Python, with what render.py drew for
// the configuration that asks for the same thing.
//
// Modes, by argv[2]:
//   scenarios - stdin JSON {components, faces, skins, cages, configs, link};
//               one JSON object out, a key per scenario. A scenario that
//               throws records {error} under its key and the rest still run.
// SWAP_MODULE names the swap.js to load; by default the kit's own.
import {pathToFileURL} from 'node:url';
import {build, install} from './fake-dom.mjs';

const m = await import(process.env.SWAP_MODULE
  ? pathToFileURL(process.env.SWAP_MODULE).href : '../../../kit/swap.js');
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
const face = name => build(input.faces[name]);
const attrsOf = n => Object.fromEntries(n.attributes.map(x => [x.name, x.value]));
// the test's own reading of what a slot holds: `data-for` it, at
// `<slot>-occupant` - not the kit's (a plug carries no data-behaviour)
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
const out = {};
async function scenario(name, fn) {
  try { out[name] = await fn(); } catch (e) { out[name] = {error: String(e && e.stack || e)}; }
}

const SFP = 'generic/sfp-rj45@1', PLUG = 'generic/rj45-plug@1', BOOT = 'common/rj45-boot@1';
const PORTS = ['port-0', 'port-1'];
// a link's key per port: the cage, the jack of what it holds, the plug's boot
const tiers = p => [p, `${p}-occupant`, `${p}-occupant-occupant`];
const REFS = [SFP, PLUG, BOOT];
// the configuration each link is seated FROM, and the one that asks for it
const FROM = ['base', 'sfp', 'plug'];
const TO = ['sfp', 'plug', 'boot'];
const dev = 'agr560';
const cages = input.cages[dev] || [];
const cfgOf = name => input.configs[dev].find(c => c.name === name);
const slotsOn = root => m.faceCages(root, cages, compByRef);
const plain = e => e && {id: e.id, key: e.key, interface: e.interface, accepts: e.accepts,
                         lift: e.lift, rotate: e.rotate, host: e.host ?? null, chained: !!e.chained};
const ALL = Object.fromEntries(PORTS.flatMap(p => tiers(p).map((k, i) => [k, REFS[i]])));

// ------------------------------------------------ what each face offers
await scenario('census', async () => Object.fromEntries(['base', ...TO].map(f => {
  const root = face(f);
  const mine = slotsOn(root).filter(e => PORTS.some(p => e.id === p || e.id.startsWith(`${p}-`)));
  return [f, Object.fromEntries(mine.map(e => [e.id, plain(e)]))];
})));

// ---------------------- one link at a time, the explorer's own path
// shell.js seat(): the entry read off the face on screen (cagesOnFace), one
// slot through applyOccupantOverrides - from the build of the link below
await scenario('links', async () => {
  const res = {}, seatedAt = {};
  for (const p of PORTS) {
    const keys = tiers(p);
    for (let i = 0; i < 3; i++) {
      const root = face(FROM[i]);
      const key = keys[i];
      const entry = slotsOn(root).find(s => s.id === key);
      if (!entry) { res[key] = {error: `no slot ${key} on ${FROM[i]}`}; continue; }
      const r = await m.applyOccupantOverrides(root, [entry], {[key]: REFS[i]}, loadSkin);
      res[key] = {applied: r.applied, refused: r.refused, failed: r.failed};
      seatedAt[key] = seated(root, key);
    }
  }
  return {res, seated: seatedAt};
});

// ----------------- the whole chain in one map, on the bare face (3D, detached)
await scenario('chain', async () => {
  const root = face('base');
  const r = await m.seatFace(root, {bays: [], cages}, ALL, loadSkin, compByRef);
  return {res: {applied: r.applied, refused: r.refused, failed: r.failed, dropped: r.dropped},
          seated: Object.fromEntries(Object.keys(ALL).map(k => [k, seated(root, k)]))};
});

// ------------------------------------------- a shared link: `swap=`
// shell.js's load: rawParam off the search, decodeSwaps, the gate
// (acceptSwaps against what the configuration built), then the seat - the
// pass a face not on screen and the 3D scene take with what the gate took
await scenario('link', async () => {
  const swaps = m.decodeSwaps(m.rawParam(input.link, 'swap'));
  const bo = m.builtOccupants(cfgOf('base'), cages, {bays: [], compByRef});
  const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  const gate = m.acceptSwaps(swaps, {bays: [], cages, compByRef, built: () => undefined,
    builtOcc: k => own(bo, k) ? bo[k] : undefined});
  const root = face('base');
  const r = await m.seatFace(root, {bays: [], cages}, gate.accepted, loadSkin, compByRef);
  return {swaps, accepted: gate.accepted, ignored: gate.ignored,
          res: {applied: r.applied, refused: r.refused, failed: r.failed},
          encoded: m.encodeSwaps(ALL),
          seated: Object.fromEntries(Object.keys(ALL).map(k => [k, seated(root, k)]))};
});

console.log(JSON.stringify(out));
