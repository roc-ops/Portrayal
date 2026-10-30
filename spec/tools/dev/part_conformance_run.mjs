// spec/tools/dev/part_conformance_run.mjs
// The node half of part_conformance.py: runs both checks over the devices it is
// given and prints one line of JSON. Run: node <this> <dist> '<options json>'
//   options: {refs: [...], maxConfigs, maxEnds, maxStates, skip: ['cabling'|'settings'],
//             scan: true (C19 to C22 only, every configuration),
//             usable: {parts: {ref: unmated}, connectors: {interface: {cover, unmated}}, families: {name: {interface, rates, unmated}}}}
import {openDist, checkSettings, checkCabling, checkOccupants, checkUsable} from './part_conformance.mjs';

const dist = process.argv[2];
const opts = JSON.parse(process.argv[3] || '{}');
const W = openDist(dist);
// the site's pure side-pane geometry, when a checkout of the site is given (--site)
let side = null;
if (opts.site) {
  const {pathToFileURL} = await import('node:url');
  const {join} = await import('node:path');
  side = await import(pathToFileURL(join(opts.site, 'site/rack/side-geometry.js')).href);
}
const now = () => Number(process.hrtime.bigint() / 1000n) / 1e6;
const out = {dist, parts: []};

// configurations worth running: the default, then one per distinct set of drawings, up to `maxConfigs`
function configsOf(ref) {
  const slots = W.slotsOf(ref);
  if (!slots) return [];
  const seen = new Set(), list = [];
  const order = [...slots.configs].sort((a, b) => (b.name === slots.default) - (a.name === slots.default));
  for (const c of order) {
    const k = JSON.stringify(c.files || {}) + JSON.stringify(c.bays || {}) + JSON.stringify(c.occupants || {});
    if (seen.has(k)) continue;
    seen.add(k); list.push(c.name);
    if (list.length >= (opts.maxConfigs ?? 3)) break;
  }
  return list;
}

for (const ref of opts.refs) {
  const part = {ref, kind: W.chassisOf(ref)?.kind ?? null, mount: W.chassisOf(ref)?.mount ?? null, configs: []};
  if (!W.slotsOf(ref)) { part.error = 'not in the build'; out.parts.push(part); continue; }
  if (opts.scan) {
    // the scan: C19 to C22 only, every configuration, no cable laid
    for (const cfg of W.slotsOf(ref).configs.map(c => c.name)) {
      const t = now(), row = {cfg};
      try { row.usable = await checkUsable(W, ref, cfg, {usable: opts.usable}); } catch (e) { row.usable = {found: [{code: 'C0', text: `the check threw: ${e.message}`, stack: String(e.stack).split('\n').slice(0, 3).join(' | ')}], counts: {}}; }
      row.usable.seconds = Math.round((now() - t) * 1000) / 1000;
      part.configs.push(row);
    }
    out.parts.push(part);
    continue;
  }
  if (!(opts.skip || []).includes('occupants')) {
    const t = now();
    try { part.occupants = checkOccupants(W, ref, {perBay: opts.perBay, perCage: opts.perCage}); } catch (e) { part.occupants = {found: [{code: 'C0', text: `the occupants check threw: ${e.message}`, stack: String(e.stack).split('\n').slice(0, 3).join(' | ')}], counts: {}}; }
    part.occupants.seconds = Math.round((now() - t) * 1000) / 1000;
  }
  for (const cfg of configsOf(ref)) {
    const row = {cfg};
    if (!(opts.skip || []).includes('settings')) {
      const t = now();
      try { row.settings = checkSettings(W, ref, cfg, {maxStates: opts.maxStates}); } catch (e) { row.settings = {found: [{code: 'S0', text: `the check threw: ${e.message}`}], counts: {}}; }
      row.settings.seconds = Math.round((now() - t) * 1000) / 1000;
    }
    if (!(opts.skip || []).includes('cabling')) {
      const t = now();
      try { row.cabling = await checkCabling(W, ref, cfg, {maxEnds: opts.maxEnds, side, usable: opts.usable}); } catch (e) { row.cabling = {found: [{code: 'C0', text: `the check threw: ${e.message}`, stack: String(e.stack).split('\n').slice(0, 3).join(' | ')}], counts: {}, ends: []}; }
      row.cabling.seconds = Math.round((now() - t) * 1000) / 1000;
    }
    part.configs.push(row);
  }
  out.parts.push(part);
}
process.stdout.write(`${JSON.stringify(out)}\n`);
