// kit/rack/slack.js
// WHERE THE SPARE CABLE IS (docs/rack-file-v4-design.md sections 3.3 to 3.6).
// A cable carries `slack`, a list of where its spare is stored: {item, via,
// form?, value?, unit?} for a tray, a spool or a finger duct of a placed part
// or of a part beside the rack, {end: a | b, value?, unit?} for what is left
// at an end. No `slack` key means nothing has been said; an empty list means
// it is stored nowhere, by choice. Which pathways hold spare is SPARE_HOLDS.
//
// This module resolves the list against the route and says it in words, and
// gives the point a drawing puts each stored loop at (spareMarks); it draws
// nothing itself. It does not place spare on its own, or judge how much a
// tray holds; a duct's stated capacity is counted (spareLoad).
// Pure; `ctx` is the routing context route.js takes, and `rack.bundles` are
// read through bundles.js with it.

import {routePath, spareOf, toMetres, UNPLACED_WARN_M, BREAK_TOL_M, resolveRoute, pathwaysAt, zeroUPathways, cablesThrough,
  capacityBasis, pointOf, cableDiameter} from './route.js';
import {traysOf} from './solids.js';
import {cellsOf, cellNear, coilIn} from './coil.js';
import {bendOf, FAMILY} from './resting.js';
import {bundleOfCable, layoutOf} from './bundles.js';
import {bundleName, zeroUOf, zeroUById} from './model.js';
import {carriesLane, runsThrough} from './zero-u.js';
import {zeroUTouched} from './fit.js';

export const FORMS = ['coil', 'serpentine', 'spool'];
const plain = v => !!v && typeof v === 'object' && !Array.isArray(v);
// A length as the list says it: to a centimetre, with no trailing zero.
export const mText = m => `${Math.round(m * 100) / 100} m`;
// A part beside the rack whose label another part shares (two verticals of
// one model) is named with its id too: "CMV-SFD42U9W (z2)".
export const labelOf = (rack, id) => {
  const it = rack.items.find(i => i.id === id);
  if (it) return it.label ?? id;
  const zs = Array.isArray(rack.zeroU) ? rack.zeroU : [], z = zs.find(x => x?.id === id);
  if (!z?.label) return id;
  return zs.some(x => x !== z && x?.label === z.label) || rack.items.some(i => i.label === z.label) ? `${z.label} (${id})` : z.label;
};
export const trayText = (rack, e) => `${labelOf(rack, e.item)} ${e.via}`;

// ── WHICH PATHWAYS HOLD SPARE: THE ONE RULE ──────────────────────────────
// A tray holds a coil or a serpentine on its floor (trayRefusal judges it
// further). A finger duct the cable runs in holds a service loop, as a
// technician stores one: a horizontal manager's duct, a rack-face bracket's
// and a vertical manager's beside the rack. A ring (a lacer bar's rings
// included) and a pass-through hold none: a loop there blocks the opening.
// A guide whose kind the page does not give holds none. To change which
// pathways hold spare, change this table and nothing else.
export const SPARE_HOLDS = {tray: true, duct: true, ring: false, pass: false};
export const holdsSpare = kind => SPARE_HOLDS[kind] === true;
const KIND_TEXT = {ring: 'a ring', pass: 'a pass-through', duct: 'a duct', tray: 'a tray'};
// A duct's own default form: what a loop in it is called when none is given.
export const DUCT_FORM = 'loop';

// THE PLACES ON A CABLE'S ROUTE THAT CAN HOLD ITS SPARE, [{item, via, kind}]:
// each duct its route names, each zero-U duct a lane run of it goes through,
// and each tray it rests on (not on a held face), in route order. [] without
// the routes.
export function sparePlaces(rack, cable, ctx, path = undefined) {
  if (!ctx) return [];
  let ws = [];
  try { ws = resolveRoute(rack, cable, ctx).waypoints; } catch { ws = []; }
  if (path === undefined) { try { path = routePath(rack, cable, ctx); } catch { path = null; } }
  const out = [], add = p => { if (!out.some(o => o.item === p.item && o.via === p.via)) out.push(p); };
  const zs = zeroUOf(rack).filter(z => carriesLane(ctx.chassisOf?.(z.ref)));
  for (const [k, w] of ws.entries()) {
    if (w.lane) {
      // a zero-U duct this lane point is in, or this run goes through
      for (const z of zs) if (runsThrough(ws.slice(k, k + 2).filter(x => x.lane), z, ctx.chassisOf)) {
        const d = zeroUPathways(rack, z, ctx).find(p => p.kind === 'duct');
        if (d) add({item: z.id, via: d.via, kind: 'duct'});
      }
      continue;
    }
    const kind = pathwaysAt(rack, w.item, ctx).find(p => p.via === w.via)?.kind ?? null;
    if (kind === 'tray') {
      const rest = (path?.rests || []).find(x => x.kind === 'tray' && x.item === w.item && x.via === w.via);
      if (rest && rest.role !== 'held') add({item: w.item, via: w.via, kind});
    } else if (holdsSpare(kind)) add({item: w.item, via: w.via, kind});
  }
  // a tray it rests on that the route does not name (one under a ring it names)
  for (const x of path?.rests || []) if (x.kind === 'tray' && x.role !== 'held') add({item: x.item, via: x.via, kind: 'tray'});
  return out;
}
// WHERE A CABLE'S SPARE CAN GO, as the sentence a refusal ends with.
export function whereText(rack, cable, ctx, path = undefined) {
  const places = sparePlaces(rack, cable, ctx, path).map(p => trayText(rack, p));
  const ends = 'at an end ({end: a} or {end: b})';
  return places.length ? `The spare of ${cable.id} can go in ${places.join(', ')}, or ${ends}.`
    : `The route of ${cable.id} has no tray or duct that holds spare, so its spare can go only ${ends}.`;
}

// WHY A CABLE CANNOT STORE THIS MUCH SPARE, as the sentence, or null when it
// can: a cable pinned under what its route needs has no spare to store
// anywhere, and the amounts stated (the others kept, with this one) cannot
// add up to more than the spare there is. A place that takes the rest asks
// for no amount, and is never past it. Not where the cable has no usable
// length or the routes are not known: then nothing is judged.
export function amountRefusal(rack, cable, entry, ctx, path) {
  if (!ctx) return null;
  const spare = spareOf(rack, cable, ctx, path);
  // a routed length grows by what is stored and may move up a stock size, so only a pinned length is a limit
  if (!spare || !spare.pinned) return null;
  if (spare.spare_m < -1e-9) return `${cable.id} is ${mText(-spare.spare_m)} short of what its route needs, so it has no spare to store.`;
  const value = toMetres(entry.value, entry.unit);
  if (entry.value == null || value == null) return null;
  const others = (Array.isArray(cable.slack) ? cable.slack : []).filter(e => plain(e) && e !== entry && !sameEntry(e, entry))
    .reduce((s, e) => s + (e.value == null ? 0 : toMetres(e.value, e.unit) ?? 0), 0);
  if (others + value <= spare.spare_m + 0.005) return null;
  return others > 0 ? `${cable.id} has only ${mText(spare.spare_m)} of spare and ${mText(others)} of it is stored already, so storing ${mText(value)} more is too much.`
    : `${cable.id} has only ${mText(spare.spare_m)} of spare, so storing ${mText(value)} is more than it has.`;
}
const sameEntry = (a, b) => ('end' in a || 'end' in b ? a.end === b.end : a.item === b.item && a.via === b.via);

// WHY A CABLE CANNOT STORE SPARE IN A PATHWAY, as the sentence, or null
// when it can. Not where the routes are not known (no `ctx` or no `path`):
// then nothing is judged and the answer is null.
// - there is no pathway of that name on the part;
// - its kind holds no spare (SPARE_HOLDS);
// - a duct its route does not use;
// - a spool in a duct;
// - a tray, as trayRefusal.
// Capacity is not judged here (spareLoad).
export function spareRefusal(rack, cable, entry, ctx, path) {
  if (!ctx || !path) return null;
  const kind = pathwaysAt(rack, entry.item, ctx).find(p => p.via === entry.via)?.kind;
  if (kind === undefined) return `${labelOf(rack, entry.item)} has no pathway called ${entry.via}.`;
  if (kind === 'tray') return trayRefusal(rack, cable, entry, ctx, path);
  const name = trayText(rack, entry);
  if (!holdsSpare(kind)) return `${name} is ${KIND_TEXT[kind] ?? 'no duct or tray'}, which holds no spare.`;
  if (!sparePlaces(rack, cable, ctx, path).some(p => p.item === entry.item && p.via === entry.via)) return `${name} is not on the route of ${cable.id}.`;
  if (entry.form === 'spool') return `${name} is a duct, which holds no spool.`;
  return null;
}

// WHY A CABLE CANNOT STORE SPARE IN A TRAY, as the sentence, or null when it
// can (section 3.5). `path` is the cable's routed path; without it, or with
// no routing context, nothing is judged and the answer is null.
// - the tray is not one the cable rests on;
// - the tray states no place for spare;
// - the cable lies on its held face there;
// - the cable rides a bundle trunk through it;
// - no turn of the cable can lie on its floor at all: twice its bend radius
//   and its diameter are more than the floor is deep. Necessary and not
//   sufficient; nothing finer is judged. For a coil and a serpentine, which
//   turn the cable on the floor; a spool is refused on a tray that states none.
export function trayRefusal(rack, cable, entry, ctx, path) {
  if (!ctx || !path) return null;
  const name = trayText(rack, entry);
  const rest = (path.rests || []).find(x => x.kind === 'tray' && x.item === entry.item && x.via === entry.via);
  if (!rest) return `${name} is not on the route of ${cable.id}.`;
  const tray = traysOf(rack, ctx).find(t => t.item === entry.item && t.via === entry.via);
  if (!tray?.slack) return `${name} states no place for spare cable.`;
  if (rest.role === 'held') return `${cable.id} lies on the held face of ${name}; slack is stored on the resting face.`;
  const b = bundleOfCable(rack, cable.id);
  if (b && ridesThrough(rack, b, cable.id, entry, ctx)) return `${cable.id} rides ${bundleName(b)} through ${name}: store its spare after it leaves the bundle.`;
  const form = entry.form ?? 'coil';
  if (form === 'spool') return tray.slack.kind === 'spool' ? null : `${name} states no spool.`;
  const d = typeof ctx.diameterOf === 'function' ? Number(ctx.diameterOf(cable)) : NaN;
  const across = 2 * bendOf(cable, ctx) + (Number.isFinite(d) ? d : 0);
  const deep = Math.max(...tray.floors.map(f => f.z1 - f.z0));
  return across > deep + 1e-9 ? `A turn of ${cable.id} is ${Math.round(across * 10) / 10} mm across, and the floor of ${name} is ${Math.round(deep * 10) / 10} mm deep.` : null;
}
// Does the cable ride its bundle's trunk through this tray: is the tray an
// element of the trunk between where the cable joins and leaves it?
function ridesThrough(rack, b, cableId, entry, ctx) {
  if (b.members.length < 2) return false;
  const L = layoutOf(rack, b, {route: ctx});
  const m = L?.members.find(x => x.cable === cableId);
  if (!m || m.ji == null || m.li == null) return false;
  const lo = Math.min(m.ji, m.li), hi = Math.max(m.ji, m.li);
  return L.T.some((e, i) => i >= lo && i <= hi && e.kind === 'p' && e.item === entry.item && e.via === entry.via);
}

// THE SLACK OF A CABLE, RESOLVED: null without a path or a usable length,
// else {spare, said, entries, at_ends_m, unplaced_m, over_m, short}.
// - `said` is false for no `slack` key and true for a list, empty or not;
// - `entries` are {item, via, form, metres, ok, why} for a tray (ok false with
//   the reason when the cable cannot store there) and {end, metres} for an
//   end; an entry with a value takes it, and the one without takes the rest;
// - `at_ends_m` is the end play, `unplaced_m` what is to store and has no
//   place, `over_m` how much the stated values are past what there is to
//   store; `short` is true for a pinned length under the need, and then
//   nothing is stored anywhere.
// - a duct entry also carries `kind: 'duct'` and `load`, spareLoad's answer
//   for the part, and its form is DUCT_FORM when none is given.
export function slackOf(rack, cable, ctx) {
  const s = ownSlack(rack, cable, ctx);
  if (!s) return s;
  for (const e of s.entries) if (e.kind === 'duct') e.load = spareLoad(rack, e.item, ctx, cable);
  return s;
}
// slackOf without the loads, which read every other cable's spare.
function ownSlack(rack, cable, ctx) {
  // the path is read once, for the spare and for where it can be stored
  let path = null;
  try { path = routePath(rack, cable, ctx); } catch { path = null; }
  const spare = spareOf(rack, cable, ctx, path);
  if (!spare) return null;
  const said = Array.isArray(cable.slack);
  if (spare.spare_m < -1e-9) return {spare, said, entries: [], at_ends_m: 0, unplaced_m: 0, over_m: 0, short: true};
  const list = said ? cable.slack.filter(plain) : [];
  const stated = list.reduce((s, e) => s + (toMetres(e.value, e.unit) ?? 0), 0);
  const rest = Math.max(0, spare.to_store_m - stated);
  const entries = list.map(e => {
    const metres = e.value == null ? rest : toMetres(e.value, e.unit);
    if (e.end === 'a' || e.end === 'b') return {end: e.end, metres};
    const why = spareRefusal(rack, cable, e, ctx, path);
    const duct = pathwaysAt(rack, e.item, ctx).find(p => p.via === e.via)?.kind === 'duct';
    return {item: e.item, via: e.via, form: e.form ?? (duct ? DUCT_FORM : 'coil'), metres, ok: !why, why, ...(duct ? {kind: 'duct'} : {})};
  });
  const placed = entries.reduce((s, e) => s + (e.metres ?? 0), 0);
  return {spare, said, entries, at_ends_m: spare.end_play_m, unplaced_m: Math.max(0, spare.to_store_m - placed),
          over_m: Math.max(0, stated - spare.to_store_m), short: false};
}

// ── how full a duct is with the spare stored in it ───────────────────────
// A maker states a manager's capacity as a count of cables of one kind
// (rack.json `capacity`, route.js capacityBasis). A loop of spare lies along
// the duct, so each run of the duct's length it takes is one more cable
// there: a loop of `m` metres in a duct `run` long counts as ceil(m / run)
// cables. The run is the part's longer side (its width for a horizontal
// manager, its height for a vertical one). Counted as capacityOver counts:
// the cables at least as thick as the kind the count is of.
// {stated: false} where the part states no count, {stated: true, compared:
// false} where it states one of no named kind (never compared), else
// {stated: true, compared: true, count, capacity, media, over}. Never a
// capacity the data does not state. Kept per rack, context and part: every
// cable storing in one duct asks the same question.
// Given the `cable` that stores there, a cable the count does not take in (a
// fibre cord against a count of Cat6) is not counted: {stated: true, compared:
// false, notCounted: true, media, diameter, cableMedia}, and the duct's load
// from the other cables is not put on it.
const loadMemo = new WeakMap();
export function spareLoad(rack, id, ctx, cable = null) {
  const isObj = v => v !== null && typeof v === 'object';
  const b = cable ? basisOf(rack, id, ctx) : null;
  if (b && !b.counts(cable)) return {stated: true, compared: false, notCounted: true, media: b.media, diameter: b.diameter, cableMedia: cable.media ?? null};
  if (!isObj(rack) || !isObj(ctx)) return loadOf(rack, id, ctx);
  let per = loadMemo.get(rack);
  if (!per) loadMemo.set(rack, per = new WeakMap());
  let by = per.get(ctx);
  if (!by) per.set(ctx, by = new Map());
  if (!by.has(id)) by.set(id, loadOf(rack, id, ctx));
  return {...by.get(id)};
}
const chassisOfPart = (rack, id, ctx) => {
  const it = rack.items.find(i => i.id === id), z = it ? null : zeroUById(rack, id);
  return typeof ctx?.chassisOf === 'function' ? ctx.chassisOf((it || z)?.ref) : null;
};
const basisOf = (rack, id, ctx) => capacityBasis(chassisOfPart(rack, id, ctx)?.capacity);
function loadOf(rack, id, ctx) {
  const c = chassisOfPart(rack, id, ctx);
  if (!(c?.capacity?.count > 0)) return {stated: false};
  const b = capacityBasis(c.capacity);
  if (!b) return {stated: true, compared: false};
  const run = Math.max(Number(c.w) || 0, Number(c.h) || 0) / 1000;
  let count = 0;
  try { count = cablesThrough(rack, id, ctx).filter(b.counts).length; } catch { count = 0; }
  for (const cable of rack.cables || []) {
    if (!b.counts(cable) || !Array.isArray(cable.slack) || !cable.slack.some(e => e?.item === id)) continue;
    let s = null;
    try { s = ownSlack(rack, cable, ctx); } catch { s = null; }
    for (const e of s?.entries || []) if (e.item === id && e.ok && e.metres > 0 && run > 0) count += Math.ceil(e.metres / run - 1e-9);
  }
  return {stated: true, compared: true, ...(b.estimated ? {estimated: true} : {}), count, capacity: b.count, media: b.media, over: count > b.count};
}
// The sentence of a load: what the part holds against what its maker states.
// A count of one is "1 cat6 cable's worth". A cable the count does not take in
// says so, as capacityOver leaves it out: "fibre (om4) is not counted against
// a cat6 figure". Where the maker states none the wording is its own.
export const loadText = (rack, id, load) => {
  const name = labelOf(rack, id);
  if (load.compared) {
    const held = `${name} holds ${load.count} ${load.media ?? ''}${load.media ? ' ' : ''}${load.count === 1 ? "cable's" : "cables'"} worth with the spare stored in it, `;
    // an estimated count (P-0027) is said to be one, and the maker to state none
    return load.estimated
      ? `${held}${load.over ? 'past' : 'against'} an estimated ${load.capacity} ${load.media ?? ''}${load.media ? ' ' : ''}${load.capacity === 1 ? "cable's" : "cables'"} worth (its maker states none).`
      : `${held}past the ${load.capacity} its maker states.`;
  }
  if (load.notCounted) {
    const kind = load.cableMedia ? (FAMILY[load.cableMedia] === 'fiber' ? `fibre (${load.cableMedia})` : load.cableMedia) : 'a thinner cable';
    return load.media ? `${name} states its cable capacity for ${load.media} cables, and ${kind} is not counted against a ${load.media} figure, so the spare stored in it is not counted.`
      : `${name} states its cable capacity for cables of ${load.diameter} mm or more, and ${kind} is thinner, so the spare stored in it is not counted.`;
  }
  return `${name} states no cable capacity${load.stated ? ' for a named kind of cable' : ''}, so the spare stored in it is not counted.`;
};

// ── where a stored loop is, for a drawing ────────────────────────────────
// Each place a cable's spare is stored in a duct or on a tray, as a point in
// rack coordinates (route.js pointOf's frame, mm) a drawing puts the loop
// at, the axis the pathway runs along there, and how much is stored:
// [{item, via, kind, form, metres, at: {x, y, z}, run: 'x' | 'y' | 'z'}]. A
// rack item's pathway is at its own point; a zero-U duct at the middle of the
// cable's run inside it. An entry that cannot store there is left out, as is
// everything without the routes.
export function spareMarks(rack, cable, ctx) {
  let s = null;
  try { s = ownSlack(rack, cable, ctx); } catch { s = null; }
  if (!s || s.short) return [];
  const out = [];
  for (const e of s.entries) {
    if (!e.item || !e.ok || !(e.metres > 0)) continue;
    const it = rack.items.find(i => i.id === e.item);
    let at = null, run = 'x';
    if (it) {
      try { at = pointOf(rack, {item: e.item, via: e.via}, ctx); } catch { at = null; }
      const c = ctx.chassisOf(it.ref) || {};
      const t = traysOf(rack, ctx).find(x => x.item === e.item && x.via === e.via);
      run = t ? t.run : (Number(c.h) || 0) > (Number(c.w) || 0) ? 'y' : 'x';
    } else {
      const z = zeroUById(rack, e.item);
      const [lo, hi] = zeroUTouched(z, ctx.chassisOf);
      const us = resolveRoute(rack, cable, ctx).waypoints.filter(w => w.lane === z.at).map(w => Math.min(hi, Math.max(lo, w.ru)));
      if (us.length) at = pointOf(rack, {lane: z.at, ru: Math.round((Math.min(...us) + Math.max(...us)) / 2)}, ctx);
      run = 'y';
    }
    if (at) out.push({item: e.item, via: e.via, kind: e.kind ?? 'tray', form: e.form, metres: e.metres, at, run});
  }
  return out;
}

// ── the coil a stored loop is, for a drawing ─────────────────────────────
// Each coil of the spare a cable stores on a tray with an entry of its own
// (docs/cable-spare-design.md section 5): spareMarks' tray loops in the form of
// a coil, each as coil.js coilIn gives it, with the `item` and `via` of the
// tray and the `metres` stored. The coil is in the cell nearest the loop's
// mark that takes a turn of the cable; a tray with no such cell gives none. The
// legs and turns are part of the spare: this reads the route and changes
// nothing in it. [] without the routes, for a cable with no entry, for an end
// and for a cable that cannot turn on the floor.
export function spareCoils(rack, cable, ctx) {
  const out = [];
  let path = null;
  try { path = routePath(rack, cable, ctx); } catch { path = null; }
  if (!path) return out;
  const c = {bend: bendOf(cable, ctx), diameter: cableDiameter(cable, ctx)};
  for (const m of spareMarks(rack, cable, ctx)) {
    if (m.kind !== 'tray' || m.form !== 'coil') continue;
    const tray = traysOf(rack, ctx).find(t => t.item === m.item && t.via === m.via);
    if (!tray) continue;
    const g = cellsOf(tray), cell = cellNear(g, c, g.run === 'x' ? m.at.x : m.at.z);
    // the cord's own point on the tray: its height and its lay line across it
    const lay = path.points.find(p => p.at === 'tray' && p.item === m.item && p.via === m.via);
    if (!cell || !lay) continue;
    const k = coilIn(g, cell, c, m.metres, lay);
    if (k) out.push({item: m.item, via: m.via, metres: m.metres, ...k});
  }
  return out;
}

// THE `stored` TEXT OF THE LIST (section 3.6), '' when there is nothing to
// say: no path, no usable length, or a pinned length under the need.
const offText = why => (/held face/.test(why) ? 'on the held face' : /rides (.+) through/.test(why) ? `in ${/rides (.+) through/.exec(why)[1]}`
  : /not on the route/.test(why) ? 'not on its route' : /holds no spare/.test(why) ? 'where no spare is held'
  : /has no pathway/.test(why) ? 'no such pathway' : null);
export function storedText(rack, cable, s) {
  if (!s || s.short || !cable.length) return '';
  const parts = s.entries.map(e => {
    const m = e.metres == null ? 'a length in a unit that does not convert' : mText(e.metres);
    if (e.end) return `${m} at the ${e.end.toUpperCase()} end`;
    const off = e.ok ? null : offText(e.why);
    return `${trayText(rack, e)}, ${e.form}, ${m}${off ? `, ${off}` : ''}`;
  });
  if (s.unplaced_m > 0.005) parts.push(`${mText(s.unplaced_m)} not placed${s.said && !s.entries.length ? ', by choice' : ''}`);
  return [...parts, `${mText(s.at_ends_m)} at the ends`].join('; ');
}

// THE FINDINGS OF THE SPARE, rack-wide: [{kind, cable, text}], one for
// - `spare-unplaced`: more than UNPLACED_WARN_M to store and no `slack` key
//   (an empty list is a choice, and gives none);
// - `spare-short`: a pinned length under the need;
// - `spare-over`: values that add up to more than there is to store, by more
//   than the stock break tolerance (BREAK_TOL_M);
// - `spare-off-route`: an entry on a tray the cable cannot store in, kept.
export function slackFindings(rack, ctx, nameOf = id => id) {
  const out = [];
  for (const c of rack.cables || []) {
    let s = null;
    if (!c.length) continue;                     // nothing is bought yet, so nothing is spare
    try { s = slackOf(rack, c, ctx); } catch { s = null; }
    if (!s) continue;
    if (s.short) { out.push({kind: 'spare-short', cable: c.id, text: `${c.id} is ${mText(s.spare.stock_m)} and needs ${mText(s.spare.need_m)}.`}); continue; }
    if (!s.said && s.spare.to_store_m > UNPLACED_WARN_M)
      out.push({kind: 'spare-unplaced', cable: c.id, text: `${c.id} has ${mText(s.spare.to_store_m)} to store and no place for it.`});
    if (s.over_m > BREAK_TOL_M) {
      const where = s.entries.filter(e => e.item && e.metres != null);
      const stated = s.entries.reduce((n, e) => n + (e.metres ?? 0), 0);
      out.push({kind: 'spare-over', cable: c.id, text: `${c.id} stores ${mText(stated)}${where.length === 1 && s.entries.length === 1 ? ` in ${nameOf(where[0].item)} ${where[0].via}` : ''} and has ${mText(s.spare.to_store_m)} to store.`});
    }
    for (const e of s.entries) if (e.item && !e.ok) out.push({kind: 'spare-off-route', cable: c.id, text: e.why});
    // a duct past what its maker states, or one that states nothing to count this cable against
    for (const e of s.entries) {
      if (!e.ok || !e.load) continue;
      if (e.load.over) out.push({kind: 'spare-over-capacity', cable: c.id, text: loadText(rack, e.item, e.load)});
      else if (!e.load.compared) out.push({kind: 'spare-capacity-unstated', cable: c.id, text: loadText(rack, e.item, e.load)});
      else if (e.load.estimated) out.push({kind: 'spare-capacity-estimated', cable: c.id, text: loadText(rack, e.item, e.load)});
    }
  }
  return out;
}
// One line for the rack: "Spare: 14.2 m; 41 cords not placed." '' when no
// cable has a path and a usable length.
export const spareLine = (rack, ctx) => lineOf(rack, c => slackTry(rack, c, ctx));
// A cable's slack, or null where it cannot be read.
function slackTry(rack, c, ctx) { try { return slackOf(rack, c, ctx); } catch { return null; } }
// The two lines from each cable's slack, `slackFor(cable)`: spareExports
// reads every cable's once and says both lines from that one reading.
function lineOf(rack, slackFor) {
  let total = 0, unplaced = 0, n = 0;
  for (const c of rack.cables || []) {
    const s = slackFor(c);
    if (!s || s.short || !c.length) continue;    // a cable with no length has no spare to count
    n++; total += s.spare.spare_m;
    if (!s.said && s.unplaced_m > 0.005) unplaced++;
  }
  return n ? `Spare: ${mText(total)}; ${unplaced} cord${unplaced === 1 ? '' : 's'} not placed.` : '';
}
// The one line of the BOM notes: "Spare cable: 14.2 m of 31 m bought; 41
// cords have spare that is not placed." '' as spareLine is.
export const spareBomLine = (rack, ctx) => bomLineOf(rack, c => slackTry(rack, c, ctx));
function bomLineOf(rack, slackFor) {
  let total = 0, bought = 0, unplaced = 0, n = 0;
  for (const c of rack.cables || []) {
    const s = slackFor(c);
    if (!s || s.short || !c.length) continue;
    n++; total += s.spare.spare_m; bought += s.spare.stock_m;
    if (!s.said && s.unplaced_m > 0.005) unplaced++;
  }
  return n ? `Spare cable: ${mText(total)} of ${mText(bought)} bought; ${unplaced} cord${unplaced === 1 ? ' has' : 's have'} spare that is not placed.` : '';
}
// What the exports take (export-data.js cableScheduleRows, cableBomNotes and
// drawioCables, `spare`): each cable's resolved slack by id, the one line of
// the schedule for the rack, and the one line of the BOM.
export function spareExports(rack, ctx) {
  const byCable = new Map(), read = new Map();
  for (const c of rack.cables || []) {
    const s = slackTry(rack, c, ctx);
    read.set(c, s);
    if (s) byCable.set(c.id, s);
  }
  return {byCable, line: lineOf(rack, c => read.get(c)), bom: bomLineOf(rack, c => read.get(c))};
}
