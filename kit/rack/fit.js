// WHERE A DEVICE MAY GO (spec §6). Pure: the rack, the candidate, and a
// chassisOf(ref) -> {ru, h, d} that the page backs with rack.json, as the kit loads it.
// Every refusal is a sentence, because the catalogue shows it beside the device
// it grays out - "no" without a reason is a puzzle.
//
// Depth along the rack: a front-face device runs [0, d] back from the front
// rail; a rear-face one runs [railDepth - d, railDepth] forward from the rear
// rail. On four posts the two share a U when those do not overlap, which is
// dFront + dRear <= railDepth. Two-post rails are one plane that every body
// passes through, so there a U is never shared.

import {RU} from './rails.js';

export const REACH_MM = 50;   // within this of the far rail, a device's far panel is visible there

// A RACK-FACE PART (spec §5): bolted to the rail face at a U, projecting
// outward - forward of the front rails, or behind the rear ones. It takes no
// U, so rack devices never collide with it, except a device deep enough to
// come out through the far rail into a manager there.
export const isRackFace = c => c?.mount === 'rack-face';

// NOT RACK-MOUNT. The catalogue states `mount` only when it is not "rack".
export const isRackMount = chassis => !chassis?.mount || chassis.mount === 'rack';
// The depth between the rails a body must exceed to come out of the far one:
// two-post rails are one plane, so any body does.
const between = f => (f.kind === 'two-post' ? 0 : f.railDepth);

function fitsRackFace(rack, cand, c, chassisOf, {ignoreId = null} = {}) {
  const f = rack.frame, rd = between(f);
  if (cand.ru < 1) return {ok: false, reason: 'Below U1.'};
  if (cand.ru > f.heightRU) return {ok: false, reason: `U${cand.ru} is past the top of this ${f.heightRU}U rack.`};
  if (cand.face === 'rear' && rd + c.d > f.usableDepth)
    return {ok: false, reason: `${mm(c.d)} mm out from the rear rail; this rack allows ${mm(f.usableDepth - rd)} mm there.`};
  if (cand.on != null) {
    const host = rack.items.find(i => i.id === cand.on), hc = host && chassisOf(host.ref);
    if (!host || isRackFace(hc)) return {ok: false, reason: 'A cable manager goes on a rack device.'};
    const hu = Math.max(1, hc?.ru ?? 1);
    if (!(Number.isInteger(cand.unit) && cand.unit >= 1 && cand.unit <= hu))
      return {ok: false, reason: `${host.label} is ${hu}U; there is no unit ${cand.unit} on it.`};
    if (host.face !== cand.face)
      return {ok: false, reason: `${host.label} is on the ${host.face}; a manager on it goes on the ${host.face} too.`};
  }
  for (const o of rack.items) {
    if (o.id === ignoreId) continue;
    const oc = chassisOf(o.ref);
    if (!oc || !overlaps([cand.ru, cand.ru], span(o, chassisOf))) continue;
    if (isRackFace(oc)) {
      if (o.face === cand.face) return {ok: false, reason: `Taken by ${o.label} on the ${o.face}.`};
      continue;
    }
    if (o.face !== cand.face && oc.d > rd)
      return {ok: false, reason: `${o.label} is ${mm(oc.d)} mm deep and reaches past the ${cand.face} rail; ` +
                                 `a ${cand.face} manager here would hit it.`};
  }
  return {ok: true};
}

const mm = x => Math.round(x);
export function span(item, chassisOf) {
  const u = chassisOf(item.ref)?.ru ?? 1;
  return [item.ru, item.ru + Math.max(1, u) - 1];
}
const overlaps = (a, b) => a[0] <= b[1] && b[0] <= a[1];

export function fits(rack, cand, chassisOf, {ignoreId = null} = {}) {
  const f = rack.frame, c = chassisOf(cand.ref);
  if (!c) return {ok: false, reason: `No size is known for ${cand.ref}.`};
  if (isRackFace(c)) return fitsRackFace(rack, cand, c, chassisOf, {ignoreId});
  const lo = cand.ru, hi = cand.ru + Math.max(1, c.ru) - 1;
  if (lo < 1) return {ok: false, reason: 'Below U1.'};
  if (hi > f.heightRU)
    return {ok: false, reason: `${c.ru}U needed; ${f.heightRU - lo + 1}U free from U${lo} to the top.`};
  if (c.d > f.usableDepth) return {ok: false, reason: `${mm(c.d)} mm deep; this rack allows ${mm(f.usableDepth)} mm.`};
  for (const o of rack.items) {
    if (o.id === ignoreId) continue;
    const oc = chassisOf(o.ref);
    if (!oc || !overlaps([lo, hi], span(o, chassisOf))) continue;
    if (isRackFace(oc)) {
      if (o.face !== cand.face && c.d > between(f))
        return {ok: false, reason: `${mm(c.d)} mm deep; it would reach past the ${o.face} rail into ${o.label}.`};
      continue;
    }
    if (o.face === cand.face) return {ok: false, reason: `Taken by ${o.label} on the ${o.face}.`};
    if (f.kind === 'two-post')
      return {ok: false, reason: `Taken by ${o.label}; two-post rails are shared by front and rear.`};
    if (c.d + oc.d > f.railDepth)
      return {ok: false, reason: `${mm(c.d)} mm deep; ${Math.max(0, mm(f.railDepth - oc.d))} mm free behind ${o.label}.`};
  }
  return {ok: true};
}

// Does this item show its other panel on the other face's elevation, or only
// a ghost of the space it takes?
export function reaches(item, rack, chassisOf) {
  if (rack.frame.kind === 'two-post') return true;
  return (chassisOf(item.ref)?.d ?? 0) >= rack.frame.railDepth - REACH_MM;
}

// The depth this item could have where it stands: what the other face leaves
// on the U range it shares, or the rack's usable depth.
export function availableDepth(rack, item, chassisOf) {
  const f = rack.frame;
  if (f.kind === 'two-post') return f.usableDepth;
  const mine = span(item, chassisOf);
  const other = rack.items.filter(o => o.id !== item.id && o.face !== item.face
                                       && !isRackFace(chassisOf(o.ref))
                                       && overlaps(mine, span(o, chassisOf)));
  if (!other.length) return f.usableDepth;
  return Math.min(f.usableDepth, f.railDepth - Math.max(...other.map(o => chassisOf(o.ref)?.d ?? 0)));
}

// Every item with the U height its chassis entry gives it (or 1, unknown or
// not) - what the elevation, the 3D view and any export (Phase 1b) all need
// beside the item's own fields, so each draws the same rack.
// heightOf(chassisOf) is that height as a lookup by item: what names a device
// with its U (cable-rules.js endName) asks it.
export const heightOf = chassisOf => item => Math.max(1, chassisOf(item.ref)?.ru ?? 1);
export const itemsWithU = (rack, chassisOf) =>
  rack.items.map(i => {
    const mount = chassisOf(i.ref)?.mount;      // stated only when it is not a rack's
    return {...i, u: heightOf(chassisOf)(i), ...(isRackMount({mount}) ? {} : {mount})};
  });

export const attachPoints = kind => (kind === 'four-post'
  ? ['left-front', 'right-front', 'left-rear', 'right-rear'] : ['left', 'right']);

// SHRINK THE FRAME (feedback round 2 §2): a lower height that leaves devices
// hanging past it is no longer refused - it packs them down instead.
//
// Items whose U spans overlap (on either face - a front/rear pair sharing a
// U is one cluster) move together, keeping their offsets, faces and turned
// state. Clusters close their gaps by packing upward from U1 in their
// original bottom-to-top order; if the packed top still overshoots the new
// height, whole clusters are dropped from the bottom - lowest first - until
// the rest fits, then the remainder is packed again from U1.
export function shrinkRack(rack, newHeight, chassisOf) {
  const heightOf = item => Math.max(1, chassisOf(item.ref)?.ru ?? 1);
  const topOf = item => item.ru + heightOf(item) - 1;
  const withFrameHeight = items => ({...rack, frame: {...rack.frame, heightRU: newHeight}, items});

  if (rack.items.every(i => topOf(i) <= newHeight))
    return {rack: withFrameHeight(rack.items), moved: [], removed: []};

  // Group items into clusters by overlapping U spans (union-find), face
  // ignored - that is exactly what keeps a front/rear pair together.
  const items = rack.items;
  const n = items.length;
  const parent = items.map((_, i) => i);
  const find = x => (parent[x] === x ? x : (parent[x] = find(parent[x])));
  for (let i = 0; i < n; i++)
    for (let j = i + 1; j < n; j++)
      if (overlaps(span(items[i], chassisOf), span(items[j], chassisOf))) {
        const a = find(i), b = find(j);
        if (a !== b) parent[a] = b;
      }
  const groups = new Map();
  items.forEach((it, i) => {
    const r = find(i);
    if (!groups.has(r)) groups.set(r, []);
    groups.get(r).push(it);
  });
  const clusters = [...groups.values()]
    .map(list => {
      const lo = Math.min(...list.map(i => i.ru));
      const hi = Math.max(...list.map(topOf));
      return {items: list, lo, height: hi - lo + 1};
    })
    .sort((a, b) => a.lo - b.lo); // original bottom-to-top order

  // A shift per surviving item, not a repacked list: the returned rack keeps
  // rack.items in its ORIGINAL order (only positions change), so nothing
  // downstream that assumes item order is stable sees them shuffled by
  // cluster.
  const pack = clusterList => {
    let cursor = 1;
    const shiftById = new Map();
    const moved = [];
    for (const c of clusterList) {
      const shift = cursor - c.lo;
      for (const it of c.items) {
        shiftById.set(it.id, shift);
        if (shift !== 0) moved.push(it.id);
      }
      cursor += c.height;
    }
    return {shiftById, moved};
  };

  let survivors = clusters;
  let removed = [];
  if (clusters.reduce((h, c) => h + c.height, 0) > newHeight) {
    survivors = clusters.slice();
    while (survivors.length && survivors.reduce((h, c) => h + c.height, 0) > newHeight) {
      const [gone, ...rest] = survivors;
      removed.push(...gone.items);
      survivors = rest;
    }
  }
  const {shiftById, moved} = pack(survivors);
  const removedIds = new Set(removed.map(i => i.id));
  const packedItems = items
    .filter(it => !removedIds.has(it.id))
    .map(it => (shiftById.get(it.id) ? {...it, ru: it.ru + shiftById.get(it.id)} : it));
  return {rack: withFrameHeight(packedItems), moved, removed};
}

// ZERO-U (spec §5.3): along an attachment point, by offset in mm from the
// bottom of the rails. The catalogue has none yet; the rules are here so the
// day it does, placing one is data, not a change to this file.
export function fitsZeroU(rack, cand, chassisOf, {ignoreId = null} = {}) {
  const f = rack.frame;
  if (!attachPoints(f.kind).includes(cand.at))
    return {ok: false, reason: `${cand.at} is not an attachment point of a ${f.kind} frame.`};
  const len = chassisOf(cand.ref)?.h;
  if (!len) return {ok: false, reason: `No size is known for ${cand.ref}.`};
  if (cand.offsetMm < 0 || cand.offsetMm + len > f.heightRU * RU)
    return {ok: false, reason: `${mm(len)} mm long; it runs past the top of the rack.`};
  for (const o of rack.zeroU) {
    if (o.id === ignoreId || o.at !== cand.at) continue;
    const ol = chassisOf(o.ref)?.h ?? 0;
    if (cand.offsetMm < o.offsetMm + ol && o.offsetMm < cand.offsetMm + len)
      return {ok: false, reason: `Overlaps ${o.label ?? o.ref} at ${o.at}.`};
  }
  return {ok: true};
}
