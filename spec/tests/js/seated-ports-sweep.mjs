// spec/tests/js/seated-ports-sweep.mjs
// rack/ports.js `seatedPort` against every face the build drew, both ways, as
// one line of JSON for test_seated_ports_sweep.py. Run: node <this> <dist>.
//
//   drawn -> kit   every port the build drew under a bay: the kit says yes, or
//                  says nothing (null, the drawing decides). It never says no.
//   kit -> drawn   every port the kit says yes to: the build drew it on that
//                  panel. The candidates are every part of what each bay could
//                  hold in the configuration - what it lists, and the bay's own
//                  default where it lists nothing - and of that part's back.
//                  A bay whose `only-in` leaves the configuration out is no
//                  bay of it (`absent`): the kit says nothing, and the build
//                  drew nothing there. A bay the configuration has and does
//                  not list holds its default and is answered for
//                  (`unspoken`).
//
// One kind of yes has no drawing and is right: the back of a part in a host
// that draws no back for that bay (an enclosure with a closed rear). The port
// is the part's all the same. Those are counted apart, as `closed`.
//
// A YES BY A SLOT (#1045) is counted apart too, as `slots`: a supply's inlet,
// a DC terminal's screw, a ground stud, which a cable lands on by the
// connector slot at its path and not as a part of class `port`. The build
// drew a part at that path on that panel, of whatever class, or it is a
// phantom like any other.
//
// A SLOT OF THE DEVICE ITSELF (an outlet, a chassis inlet, a ground stud) is
// settled from the catalogue where a page found no port at the path
// (ports.js ownSlot). A page that knows class `port` alone says that both of
// a drawn slot and of a path with nothing drawn, so every path the device
// lists as a slot ON ANY OF ITS PANELS, and every path cableEndPaths names,
// is asked about in every configuration, on the front and the rear: one that
// lands with no part drawn at it in that configuration is a phantom (port 29
// of a 48-port panel, on the 24-port build). `undrawn` counts those asked,
// `own` the slots that land with their part drawn.
import fs from 'node:fs';
import {seatedPort, settleEnd, cableEndPaths} from '../../../kit/rack/ports.js';

const D = process.argv[2];
const read = name => JSON.parse(fs.readFileSync(`${D}/${name}`, 'utf8'));
const comps = new Map(read('components.json').components.map(c => [`${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`, c]));
const compByRef = ref => (ref == null ? null : comps.get(String(ref).split(':')[0]) ?? null);
const faceRef = f => (typeof f === 'string' ? f : f?.ref) || null;
const attr = (tag, a) => (new RegExp(`\\s${a}="([^"]*)"`).exec(tag) || [])[1];

const out = {devices: 0, configs: 0, drawn: 0, yes: 0, unsaid: 0, denied: [], asked: 0, said: 0, shown: 0, closed: 0, closedOn: [], phantom: [], unspoken: 0, absent: 0, slots: 0, undrawn: 0, own: 0};
for (const f of fs.readdirSync(D).filter(n => n.endsWith('.configs.json')).sort()) {
  const ref = f.slice(0, -'.configs.json'.length), j = read(f);
  const slots = {bays: j.bays || {}, cages: j.cages || {}, configs: j.configs || [], default: j.default ?? null};
  const ctx = {slotsOf: () => slots, compByRef};
  out.devices++;
  for (const cfg of slots.configs) {
    out.configs++;
    const item = {id: 'i1', ref, cfg: cfg.name, swaps: {}};
    const ports = {}, backs = {}, parts = {};
    for (const view of ['front', 'rear']) {
      const file = cfg.files?.[view];
      if (!file || !fs.existsSync(`${D}/${file}`)) continue;
      ports[view] = new Set(); backs[view] = new Set();
      const text = fs.readFileSync(`${D}/${file}`, 'utf8');
      parts[view] = new Set([...text.matchAll(/<g\s[^>]*data-path="([^"]*)"[^>]*>/g)].map(m => m[1]));
      for (const m of text.matchAll(/<g\s[^>]*data-projection="1"[^>]*>/g)) if (attr(m[0], 'data-of')) backs[view].add(attr(m[0], 'data-of'));
      for (const m of text.matchAll(/<g\s[^>]*data-class="port"[^>]*>/g)) {
        const path = attr(m[0], 'data-path') ?? attr(m[0], 'data-of');
        if (path == null || !path.includes('/module/')) continue;
        ports[view].add(path);
        out.drawn++;
        const got = seatedPort(item, {path, view}, ctx);
        if (!got) out.unsaid++;
        else if (got.port) out.yes++;
        else out.denied.push(`${ref} ${cfg.name} ${view} ${path}`);
      }
    }
    // the device's own slots, and every path a page would be told to read as an end
    const everySlot = [...new Set(Object.values(slots.cages).flatMap(list => (list || []).map(g => g.id)))];
    for (const view of ['front', 'rear']) {
      if (!parts[view]) continue;
      for (const path of new Set([...everySlot, ...cableEndPaths(item, view, ctx)])) {
        // what a page that knows class port alone reads: a panel with a drawing, and no port at the path
        const page = {facts: {item: true, drawing: true, port: false, cage: false, occupied: false, holder: null}, info: null, reason: 'no port'};
        const lands = ports[view].has(path) ? false : settleEnd({items: [item], cables: []}, {item: 'i1', path, view}, page, ctx)?.facts?.port === true;
        if (parts[view].has(path)) { if (lands) out.own++; continue; }
        out.undrawn++;
        if (lands) out.phantom.push(`${ref} ${cfg.name} ${view} ${path}: lands with no part drawn`);
      }
    }
    // kit -> drawn
    for (const [bayView, bays] of Object.entries(slots.bays)) for (const bay of bays || []) {
      // a bay that states `only-in` is a bay of those configurations only (#1022)
      const has = !bay['only-in']?.length || bay['only-in'].includes(cfg.name);
      const listed = Object.hasOwn(cfg.bays || {}, bay.id);
      const held = compByRef(listed ? cfg.bays[bay.id] : bay.default);
      if (!held) continue;
      const ids = [...(held.parts || []), ...(compByRef(faceRef(held.faces?.rear))?.parts || [])].map(q => q.id);
      for (const id of new Set(ids)) for (const view of ['front', 'rear']) {
        if (!ports[view]) continue;
        const path = `${bay.id}/module/${id}`;
        out.asked++;
        const got = seatedPort(item, {path, view}, ctx);
        if (!has) {
          // no bay here: the kit says nothing, and the build drew nothing there
          out.absent++;
          if (got) out.phantom.push(`${ref} ${cfg.name} ${view} ${path}: answered for a bay the configuration does not have`);
          if (ports[view].has(path) || parts[view].has(path)) out.phantom.push(`${ref} ${cfg.name} ${view} ${path}: drawn in a bay its only-in leaves out`);
          continue;
        }
        // a bay the configuration has and does not list holds its default: answered for
        if (!listed) out.unspoken++;
        if (!got?.port) continue;
        if (got.slot) { if (parts[view].has(path)) out.slots++; else out.phantom.push(`${ref} ${cfg.name} ${view} ${path}: a slot with no part drawn`); continue; }
        out.said++;
        if (ports[view].has(path)) out.shown++;
        else if (got.back && !backs[view].has(`${bay.id}/module`)) { out.closed++; if (!out.closedOn.includes(ref)) out.closedOn.push(ref); }
        else out.phantom.push(`${ref} ${cfg.name} ${view} ${path}`);
      }
      void bayView;
    }
  }
}
console.log(JSON.stringify(out));
