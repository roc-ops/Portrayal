// kit/rack/slots.js
// WHAT A PLACED DEVICE HOLDS, read without a drawing: its bays and cages from
// `<ref>.configs.json`, what its configuration builds in them, and what the
// item's own swaps change. The commands that check a slot (`fit`, `field`,
// `patch`) and the query that lists them (`inspect`) read it here, so the two
// cannot disagree. Pure: `slots` and `compByRef` are what `loadSlots` in `catalog.js`
// returns, handed in by the caller.

import {slotResolver, builtBays, builtOccupants, underCarrier} from '../swap.js';

const own = (o, k) => Object.prototype.hasOwnProperty.call(o || {}, k);

// The sentence for a device whose parts list the caller could not load.
export const partsMissing = ref => `The parts list for ${ref} could not be loaded.`;

// What the commands need of ctx for one device: null when the caller loaded no
// slots at all (today's behaviour: nothing is checked), {error} when it loaded
// them and this device's are missing, else the device's slots.
export function slotsFor(ctx, ref) {
  if (typeof ctx?.slotsOf !== 'function') return null;
  return ctx.slotsOf(ref) || {error: partsMissing(ref)};
}

// The components.json entry for a part, or null: no ref, no lookup, or a
// lookup that throws on a ref it cannot read.
export const partOf = (compByRef, ref) => {
  if (!ref || typeof compByRef !== 'function') return null;
  try { return compByRef(ref) || null; } catch { return null; }
};

// A part as a person reads it: the first clause of its description ("FS
// FHD-1MTP6LCDOS2A", "A generic QSFP with an LC duplex face"), else its ref.
export function partName(compByRef, ref) {
  if (!ref) return 'nothing';
  const c = partOf(compByRef, ref);
  const first = String(c?.description || '').split(/\s[-–]\s|\.\s|\.$/)[0].trim();
  return first && first.length <= 60 ? first : ref;
}

// The device's own bays and cages, every view, each carrying its view; the
// configuration the item is built as (its own, else the device's default);
// and what that configuration seats, by the drawing's path.
export function slotEnv(item, slots, compByRef = null) {
  const flat = by => Object.entries(by || {}).flatMap(([view, list]) => (list || []).map(s => ({...s, view})));
  const bays = flat(slots.bays), cages = flat(slots.cages);
  const configs = slots.configs || [];
  const cfg = configs.find(c => c.name === item.cfg) || configs.find(c => c.name === slots.default) || null;
  const cb = builtBays(cfg);
  const occ = builtOccupants(cfg, cages, compByRef ? {bays, compByRef} : null);
  return {bays, cages, cfg, compByRef,
          built: p => (own(cb, p) ? cb[p] || null : undefined),
          builtOcc: p => (own(occ, p) ? occ[p] || null : undefined)};
}

// What a slot holds under the swaps map `swaps`: the map's answer; else the
// configuration's, unless a carrier above it was swapped (a fresh seat holds
// its defaults); else what the slot ships with.
export function holdsAt(env, swaps, path, slot) {
  if (own(swaps, path)) return swaps[path] || null;
  const reseated = Object.keys(swaps || {}).some(k => k !== path && underCarrier(path, k));
  const was = reseated ? undefined : (slot?.isCage ? env.builtOcc(path) : env.built(path));
  return was !== undefined ? was : slot?.default ?? null;
}

// swap.js slotResolver over this device, with `swaps` deciding what each
// carrier holds: `entryAt(path)` is the bay or cage at a path, nested ones
// included, and `refAt(path)` the part drawn at a part path (`<bay>/module`,
// `<cage>-occupant`).
export function resolverFor(env, swaps) {
  return slotResolver({bays: env.bays, cages: env.cages, compByRef: env.compByRef,
    bayRef: (p, bay) => holdsAt(env, swaps, p, bay),
    occRef: (p, slot) => holdsAt(env, swaps, p, {...slot, isCage: true})});
}

// Every bay and cage, the device's own and those on what its bays hold, in
// order, each with what it holds now. A cage's own bores (an adapter's two
// fibres) are not listed: a path reaches them all the same.
export function slotTree(env, swaps) {
  const bays = [], cages = [];
  const seen = new Set();
  const addBay = (path, view, b) => {
    const holds = holdsAt(env, swaps, path, b);
    bays.push({path, view, group: b.group ?? null, holds, default: b.default ?? null, accepts: b.accepts || []});
    const c = partOf(env.compByRef, holds);
    if (!c || seen.has(path)) return;
    seen.add(path);
    for (const [id, nb] of Object.entries(c.bays || {})) addBay(`${path}/module/${id}`, view, nb);
    for (const g of Array.isArray(c.cages) ? c.cages : []) addCage(`${path}/module/${g.id}`, view, g);
  };
  const addCage = (path, view, g) => cages.push({path, view, interface: g.interface ?? null, media: g.media ?? null,
    holds: holdsAt(env, swaps, path, {...g, isCage: true}), default: g.default ?? null, accepts: g.accepts || []});
  for (const b of env.bays) addBay(b.id, b.view, b);
  for (const g of env.cages) addCage(g.id, g.view, g);
  return {bays, cages};
}
