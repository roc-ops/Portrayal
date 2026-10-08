// THE RACK CATALOGUE (rack.json, written by rack_index.py beside devices.json):
// every device's rack units, depth, mount, shell, stated cable capacity and the
// ids a cable route can pass through. Loaded once per page through `dist`, the
// same build every other kit module reads.

import {jdist} from '../dist.js';

const urlOf = (dist, path) => (typeof dist === 'function' ? dist(path) : `${String(dist).replace(/\/$/, '')}/${path}`);

export const chassisLookup = devices => ref => (Object.hasOwn(devices, ref) ? devices[ref] : null);

const cmp = (a, b) => String(a ?? '').localeCompare(String(b ?? ''));
export const catalogEntries = devices => Object.entries(devices)
  .map(([name, e]) => ({name, ...e}))
  .sort((a, b) => cmp(a.manufacturer, b.manufacturer) || cmp(a.model, b.model));

export async function loadCatalog(dist) {
  const j = await jdist(urlOf(dist, 'rack.json'));
  if (j?.format !== 1) throw new Error(`rack.json: format ${j?.format}; this kit reads format 1`);
  const devices = j.devices || {};
  return {chassisOf: chassisLookup(devices), entries: catalogEntries(devices), devices};
}

// THE PARTS OF THE DEVICES IN A RACK, for the commands that check a bay, a
// cage or a field (`fit`, `field`, and `place` and `patch` with a
// configuration). Each device's `<ref>.configs.json` is fetched once, through
// `jdist`, and `components.json` once; what comes back is a synchronous
// lookup, so the commands stay pure. A device whose file cannot be fetched is
// null, as an unknown one is, and the commands refuse it with a sentence;
// nothing here throws to the caller. A ref is a device's name in the build,
// which holds no dot or slash, so nothing else is fetched.
const DEVICE_NAME = /^[A-Za-z0-9][A-Za-z0-9_-]*$/;
const compKey = c => `${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}`;

export async function loadSlots(dist, refs = []) {
  const comps = new Map();
  try {
    for (const c of (await jdist(urlOf(dist, 'components.json')))?.components || []) comps.set(compKey(c), c);
  } catch { /* every part is unknown: compByRef answers null */ }
  const slots = new Map();
  await Promise.all([...new Set(refs)].filter(r => typeof r === 'string' && DEVICE_NAME.test(r)).map(async ref => {
    try {
      const j = await jdist(urlOf(dist, `${ref}.configs.json`));
      slots.set(ref, {bays: j?.bays || {}, cages: j?.cages || {}, configs: j?.configs || [], default: j?.default ?? null});
    } catch { slots.set(ref, null); }
  }));
  return {
    slotsOf: ref => slots.get(ref) ?? null,
    compByRef: ref => (ref == null ? null : comps.get(String(ref).split(':')[0]) ?? null),
  };
}
