// THE RACK CATALOGUE (rack.json, written by rack_index.py beside devices.json):
// every device's rack units, depth, mount, shell, stated cable capacity and the
// ids a cable route can pass through. Loaded once per page through `dist`, the
// same build every other kit module reads.

import {jdist} from '../dist.js';

const urlOf = (dist, path) => (typeof dist === 'function' ? dist(path) : `${String(dist).replace(/\/$/, '')}/${path}`);

export const chassisLookup = devices => ref => devices[ref] || null;

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
