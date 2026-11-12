// REDIRECTS FOR A REPLACED PART (#1049). A rack file names parts by ref, and a
// ref whose major was removed no longer resolves: the slot refuses it, the
// swap is ignored, and the next edit that writes back what a slot accepts drops
// it. The library therefore says, on the REPLACEMENT, which removed refs it
// stands in for (`supersedes`, published on its components.json entry with a
// signature that proves it a drop-in: same part ids, port paths and names).
// This module reads that list and follows it.
//
//   - READING follows a redirect and changes nothing: a swap that names the old
//     ref seats the new part, and the answer says the old ref was read as the
//     new one. A plain load and save is byte-identical.
//   - The first edit that LANDS rewrites every redirected ref in the rack and
//     says so (rewriteRack, called by commands.apply).
//   - A ref that is gone and redirected nowhere is KEPT as written and reported
//     by name, never replaced by the slot's default (unknownSwaps).
//
// Pure: a list of components.json entries in, a resolver out. No fetch, no DOM.

import {underCarrier} from './swap.js';

// A chain of redirects is followed at most this far. A catalogue read from
// components.json holds no chain (a claim is made by a part that is published,
// so what it names is the end), but a table built some other way might.
export const MAX_HOPS = 16;

const REF = /^[a-z0-9-]+\/[a-z0-9-]+@\d+$/;
const plain = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const keyOf = c => (plain(c) && typeof c.ns === 'string' && typeof c.name === 'string' && c.major != null
  ? `${c.ns}/${c.name}@${String(c.major).replace(/^v/, '')}` : null);
// `ns/name@major:suffix`: the suffix after the colon is not part of the ref
const split = ref => { const i = ref.indexOf(':'); return i < 0 ? [ref, ''] : [ref.slice(0, i), ref.slice(i)]; };

// ONE SPELLING of a redirect, in every sentence the kit says about one.
export const pairText = (from, to) => `${from} is now ${to}`;

// THE RESOLVER over a table {removed ref -> replacement}: `follow(ref)` is the
// ref to read, the ref itself when nothing redirects it; `trace(ref)` says how
// it got there. A loop, or a chain past MAX_HOPS, is never entered: the ref
// comes back as it was and `loop` is true.
export function resolverOf(table, {catalogued = 0} = {}) {
  const map = table instanceof Map ? table : new Map();
  const trace = ref => {
    if (typeof ref !== 'string' || !ref) return {ref, from: null, hops: 0, loop: false};
    const [base, suffix] = split(ref);
    const seen = new Set();
    let cur = base, hops = 0;
    while (map.has(cur)) {
      if (seen.has(cur) || hops >= MAX_HOPS) return {ref, from: null, hops: 0, loop: true};
      seen.add(cur);
      cur = map.get(cur);
      hops++;
    }
    return hops ? {ref: cur + suffix, from: ref, hops, loop: false} : {ref, from: null, hops: 0, loop: false};
  };
  return {size: map.size, catalogued, table: map, trace, follow: ref => trace(ref).ref};
}

// FROM components.json: the entries' `supersedes` lists. A claim on a ref that
// is still published is not a redirect (the part is there to be read), and a
// claim that is not a ref, or names its own part, is left out. Two parts that
// claim one ref: the first in ref order wins, so the answer does not depend on
// the file's order (the build refuses the pair).
export function redirectsOf(components) {
  const list = Array.isArray(components) ? components.filter(plain) : [];
  const live = new Set(list.map(keyOf).filter(Boolean));
  const table = new Map();
  for (const c of [...list].sort((a, b) => (keyOf(a) ?? '').localeCompare(keyOf(b) ?? ''))) {
    const to = keyOf(c);
    if (!to || !Array.isArray(c.supersedes)) continue;
    for (const claim of c.supersedes) {
      const from = plain(claim) ? claim.ref : null;
      if (typeof from === 'string' && REF.test(from) && from !== to && !live.has(from) && !table.has(from)) table.set(from, to);
    }
  }
  return resolverOf(table, {catalogued: live.size});
}

// THE SWAPS OF ONE MAP read through the table: values rewritten, keys and
// order kept. `moved` lists what changed; the map itself comes back when
// nothing did.
export function followSwaps(swaps, redirects) {
  if (!plain(swaps) || !redirects?.size) return {swaps, moved: []};
  const moved = [];
  const out = {};
  for (const [path, ref] of Object.entries(swaps)) {
    const to = typeof ref === 'string' && ref ? redirects.follow(ref) : ref;
    if (to !== ref) moved.push({path, from: ref, to});
    out[path] = to;
  }
  return moved.length ? {swaps: out, moved} : {swaps, moved};
}

const known = (ctx, ref) => {
  try { return !!ctx.compByRef(ref); } catch { return false; }
};

// WHAT A SWAPS MAP NAMES THAT THE LIBRARY NO LONGER HAS: a ref nothing
// redirects and the catalogue does not hold. Only when a catalogue was read at
// all (a failed components.json would make every part unknown).
export function unknownSwaps(swaps, ctx) {
  const r = ctx?.redirects;
  if (!plain(swaps) || !r?.catalogued || typeof ctx.compByRef !== 'function') return [];
  return Object.entries(swaps)
    .filter(([, ref]) => typeof ref === 'string' && ref && r.follow(ref) === ref && !known(ctx, ref))
    .map(([path, ref]) => ({path, ref}));
}

// WHAT A LOADER LEFT OUT, SAID. `acceptSwaps` returns the keys it ignored and
// nothing about why; a page that wants to tell the visitor asks here, with the
// map it gave and the keys that came back ignored. One row per ignored key
// that names a part: `why` is
//   gone     the ref is not in the library (and a catalogue was read), with
//            `replacedBy` when a published part stands in for it
//   under    its carrier was dropped as gone, so nothing could be seated in it
//   refused  the part is there but the slot does not exist or does not take it
// An entry that empties a slot names no part and gets no row. Reads only; the
// map is not changed, and nothing is followed (a replacement is named, not
// seated).
export function droppedSwaps(swaps, ignored, ctx = {}) {
  if (!plain(swaps) || !Array.isArray(ignored)) return [];
  const named = ignored.filter(path => typeof swaps[path] === 'string' && swaps[path]);
  // the loader does not follow a redirect, so a replaced ref is gone here too
  const read = ctx?.redirects?.catalogued && typeof ctx.compByRef === 'function';
  const gone = new Set(read ? named.filter(path => !known(ctx, swaps[path])) : []);
  const carriers = [...gone];
  const out = [];
  for (const path of named) {
    const ref = swaps[path];
    if (gone.has(path)) {
      const row = {path, ref, why: 'gone'};
      const to = ctx.redirects.follow(ref);   // read is true, so redirects exists
      if (to !== ref && known(ctx, to)) row.replacedBy = to;
      out.push(row);
      continue;
    }
    const carrier = carriers.find(c => underCarrier(path, c));
    out.push(carrier ? {path, ref, why: 'under', carrier} : {path, ref, why: 'refused'});
  }
  return out;
}

// The sentence for the parts the library no longer holds (`gone` rows); '' when
// there are none. A refused or sheltered entry is not a part the library lost.
export function droppedText(rows) {
  const gone = (Array.isArray(rows) ? rows : []).filter(r => r.why === 'gone');
  if (!gone.length) return '';
  const by = new Map();
  for (const r of gone) by.set(r.ref, {to: r.replacedBy, where: [...(by.get(r.ref)?.where ?? []), r.path]});
  return [...by].map(([ref, {to, where}]) => `${ref} (${where.length > 4 ? `${where.slice(0, 4).join(', ')} and ${where.length - 4} more` : where.join(', ')}) is no longer in the library${to ? `; ${pairText(ref, to)}` : ''}.`).join(' ');
}

// THE KEPT ENTRIES OF A MAP being written back whole (patch): every entry that
// names a gone ref on a slot that exists (`slotAt(path)` says), and everything
// seated under it, which no slot can be resolved for while its carrier is not
// in the catalogue. They are set aside from the accept check and put back.
export function keptSwaps(swaps, ctx, slotAt) {
  const gone = unknownSwaps(swaps, ctx).filter(u => slotAt(u.path));
  if (!gone.length) return {kept: {}, rest: swaps, gone};
  const carriers = gone.map(u => u.path);
  const kept = {}, rest = {};
  for (const [path, ref] of Object.entries(swaps)) {
    if (carriers.includes(path) || carriers.some(c => underCarrier(path, c))) kept[path] = ref; else rest[path] = ref;
  }
  return {kept, rest, gone};
}

// ── a whole rack ────────────────────────────────────────────────────────
// Every placed device and every part beside the rack can hold swaps.
const holders = rack => [...(Array.isArray(rack?.items) ? rack.items : []).map(item => ['items', item]),
                         ...(Array.isArray(rack?.zeroU) ? rack.zeroU : []).map(item => ['zeroU', item])]
  .filter(([, item]) => plain(item));
const nameOf = item => (typeof item.label === 'string' && item.label ? item.label : String(item.id ?? ''));

// WHAT A RACK NAMES THAT HAS MOVED OR GONE, by device and slot path.
//   redirected  [{item, path, from, to}]  followed by `redirects`
//   unknown     [{item, label, path, ref}]  in the library no more, redirected nowhere
export function auditRack(rack, ctx = {}) {
  const redirected = [], unknown = [];
  for (const [, item] of holders(rack)) {
    if (!plain(item.swaps)) continue;
    for (const m of followSwaps(item.swaps, ctx.redirects).moved) redirected.push({item: item.id, ...m});
    for (const u of unknownSwaps(item.swaps, ctx)) unknown.push({item: item.id, label: nameOf(item), ...u});
  }
  return {redirected, unknown};
}

// THE RACK WITH EVERY REDIRECTED REF WRITTEN AS THE NEW ONE; the very rack when
// there is none, and the rack it was given is never changed.
export function rewriteRack(rack, redirects) {
  if (!redirects?.size || !plain(rack)) return {rack, changed: []};
  const changed = [];
  const lists = {};
  for (const key of ['items', 'zeroU']) {
    const list = Array.isArray(rack[key]) ? rack[key] : null;
    if (!list) continue;
    let touched = false;
    const next = list.map(item => {
      if (!plain(item) || !plain(item.swaps)) return item;
      const f = followSwaps(item.swaps, redirects);
      if (!f.moved.length) return item;
      touched = true;
      for (const m of f.moved) changed.push({item: item.id, ...m});
      return {...item, swaps: f.swaps};
    });
    if (touched) lists[key] = next;
  }
  return changed.length ? {rack: {...rack, ...lists}, changed} : {rack, changed};
}

// ── the sentences ───────────────────────────────────────────────────────
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
function pairsOf(changed) {
  const by = new Map();
  for (const c of changed) {
    const k = `${c.from}\u0000${c.to}`;
    const e = by.get(k) ?? {from: c.from, to: c.to, swaps: 0, items: new Set()};
    e.swaps++;
    e.items.add(c.item);
    by.set(k, e);
  }
  return [...by.values()].sort((a, b) => b.swaps - a.swaps || a.from.localeCompare(b.from));
}
const pairsText = changed => {
  const pairs = pairsOf(changed);
  const shown = pairs.slice(0, 3).map(p => `${pairText(p.from, p.to)} (${plural(p.swaps, 'swap')} on ${plural(p.items.size, 'device')})`);
  const more = pairs.length - shown.length;
  return shown.join('; ') + (more > 0 ? `; and ${plural(more, 'more ref')}` : '');
};

// said when the rack is loaded: nothing on disk has changed
export const loadedText = changed => (changed.length
  ? `This rack names refs the library has replaced: ${pairsText(changed)}. They are read as the new ones, and the file is not changed until it is next edited.` : '');
// said by the first edit that lands
export const rewroteText = changed => (changed.length
  ? `This rack named refs the library has replaced, and the edit wrote the new ones: ${pairsText(changed)}.` : '');
// said by inspect, of one device: where an old ref is read as the new one
export function readAsTexts(redirected) {
  const by = new Map();
  for (const r of redirected) by.set(`${r.from}\u0000${r.to}`, {...r, paths: [...(by.get(`${r.from}\u0000${r.to}`)?.paths ?? []), r.path]});
  return [...by.values()].map(r => `${pairText(r.from, r.to)} (${r.paths.join(', ')}): the old ref is read as the new one, and the file keeps it until it is next edited.`);
}
// a ref that is gone: one sentence for each, with where it is
export function unknownTexts(unknown) {
  const by = new Map();
  for (const u of unknown) by.set(u.ref, [...(by.get(u.ref) ?? []), `${u.path} on ${u.label}`]);
  return [...by].map(([ref, where]) => `${ref} (${where.length > 4 ? `${where.slice(0, 4).join(', ')} and ${where.length - 4} more` : where.join(', ')}) is no longer in the library; it is kept as written.`);
}
