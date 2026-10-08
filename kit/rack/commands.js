// kit/rack/commands.js
// THE RACK COMMANDS.
// Every edit of a rack is one of these, run through apply(): the page's own
// controls and an agent alike. A command is pure - the rack, its arguments
// and {chassisOf} in, a new rack out - and says no with a sentence. One that
// changes nothing hands back the very rack it was given, so a caller can tell.

import {withItem, updateItem, withoutItem, withFrame, renamed, withDcim, detached, positionOf, isWaypoint} from './model.js';
import {fits, isRackFace, heightOf, shrinkRack} from './fit.js';
import {placement, moveItem, managersOf} from './managers.js';
import {canCable, withCable, updateCable, withoutCable, cablesOf, withoutCablesOf, cableName, endName, endKey,
        connectorOf, mediaKind, portPathOf, MEDIA, MEDIA_LABELS} from './cable-rules.js';
import {validate, same} from './validate.js';
import {withRoutedLengths, pathwaysOf, lanesOf} from './route.js';
import {slotsFor, slotEnv, resolverFor, holdsAt, partName, partOf} from './slots.js';
import {acceptSwaps, underCarrier} from '../swap.js';
import {fieldAccepts} from '../fields.js';

export const GONE = 'That device is no longer in the rack.';
export const CABLE_GONE = 'That cable is no longer in the rack.';
export const NOT_ADDED = 'The cable was not added because a device it ran to was removed.';
export const CLEARED = 'Your Explorer changes were for the old configuration, so they were cleared.';

const itemOf = (rack, id) => rack.items.find(i => i.id === id) || null;
const cableOf = (rack, id) => (rack.cables || []).find(c => c.id === id) || null;
const at = (rack, item, chassisOf) => `U${positionOf(rack.frame, item.ru, heightOf(chassisOf)(item))}`;
const done = (rack, summary, extra = {}) => ({rack, summary, findings: [], ...extra});
const unchanged = rack => done(rack, '');
const note = text => ({kind: 'note', text});
const count = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
// fits() measures a device against the top by the Us it has left there, which
// reads oddly for a U past the top altogether; an agent can ask for any U.
const pastTop = (rack, ru) => (ru != null && ru > rack.frame.heightRU
  ? {error: `U${ru} is past the top of this ${rack.frame.heightRU}U rack.`} : null);

// ── items ───────────────────────────────────────────────────────────────
// A CONFIGURATION THE DEVICE DOES NOT LIST is refused when its slots are
// loaded (`loadSlots` in `catalog.js`), naming the ones it does list.
function cfgRefused(ctx, ref, cfg, label) {
  const s = slotsFor(ctx, ref);
  if (!s) return null;
  if (s.error) return s;
  const names = (s.configs || []).map(k => k.name);
  return names.includes(cfg) ? null : {error: `${label} has no configuration ${cfg}. It has: ${names.join(', ') || 'none'}.`};
}

function place(rack, {ref, cfg, face, ru, label}, ctx) {
  const {chassisOf} = ctx;
  const top = pastTop(rack, ru);
  if (top) return top;
  const c = chassisOf(ref);
  if (cfg != null) { const bad = cfgRefused(ctx, ref, cfg, c?.model ?? ref); if (bad) return bad; }
  const spot = isRackFace(c) ? placement(rack, {face, ru}, chassisOf) : {face, ru};
  const f = fits(rack, {ref, ...spot}, chassisOf);
  if (!f.ok) return {error: f.reason};
  const name = label ?? c?.model ?? ref;
  const {rack: next, item} = withItem(rack, {ref, cfg: cfg ?? c?.default ?? '', ...spot, label: name});
  return done(next, `Placed ${name} at ${at(next, item, chassisOf)} on the ${item.face}.`, {created: {id: item.id}});
}

function move(rack, {id, ru, face}, {chassisOf}) {
  const it = itemOf(rack, id);
  if (!it) return {error: GONE};
  const top = pastTop(rack, ru);
  if (top) return top;
  const patch = {...(ru == null ? {} : {ru}), ...(face == null ? {} : {face})};
  if (Object.entries(patch).every(([k, v]) => it[k] === v)) return unchanged(rack);
  // Through managers.js: a manager is re-hosted by where it lands, and a host
  // takes its managers with it.
  const m = moveItem(rack, id, patch, chassisOf);
  if (!m.ok) return {error: m.reason};
  const now = itemOf(m.rack, id);
  return done(m.rack, `Moved ${it.label} to ${at(m.rack, now, chassisOf)} on the ${now.face}.`);
}

// A configuration change is a delta against the OLD configuration: one that
// leaves an item with no swaps or fields to carry forward says they went.
// A NEW CONFIGURATION ALONE starts the device afresh: its swaps and fields
// were for the old one, so they go, as the site's inspector already clears
// them. Swaps or fields sent with it are kept as sent.
function patch(rack, {id, ...given}, ctx) {
  const it = itemOf(rack, id);
  if (!it) return {error: GONE};
  const newCfg = 'cfg' in given && given.cfg !== it.cfg;
  if (newCfg) { const bad = cfgRefused(ctx, it.ref, given.cfg, it.label); if (bad) return bad; }
  // The rack keeps its own copy, as withItem does: a caller that goes on to
  // change the object it passed changes neither the rack nor its history.
  const p = {...given, ...('swaps' in given ? {swaps: {...given.swaps}} : newCfg ? {swaps: {}} : {}),
             ...('fields' in given ? {fields: structuredClone(given.fields)} : newCfg ? {fields: {}} : {})};
  // A WHOLE SWAPS MAP still replaces the item's, but with the slots loaded a
  // ref a slot does not take, or a key that is no slot, is left out and named.
  const findings = [];
  if ('swaps' in given) {
    const s = slotsFor(ctx, it.ref);
    if (s?.error) return s;
    if (s) {
      const {accepted, ignored} = acceptSwaps(p.swaps, slotEnv({...it, cfg: p.cfg ?? it.cfg}, s, ctx.compByRef));
      p.swaps = accepted;
      if (ignored.length) findings.push(note(`Left out ${ignored.join(', ')}: not a slot on ${it.label}, or a part that slot does not take.`));
    }
  }
  const changes = Object.fromEntries(['cfg', 'swaps', 'fields', 'label', 'turned']
    .filter(k => k in p && !same(p[k], it[k])).map(k => [k, p[k]]));
  if (!Object.keys(changes).length) return findings.length ? {...unchanged(rack), findings} : unchanged(rack);
  const next = {...it, ...changes};
  const had = Object.keys(it.swaps ?? {}).length || Object.keys(it.fields ?? {}).length;
  const has = Object.keys(next.swaps ?? {}).length || Object.keys(next.fields ?? {}).length;
  return {rack: updateItem(rack, id, changes), summary: `Changed ${it.label}.`,
          findings: [...('cfg' in changes && had && !has ? [note(CLEARED)] : []), ...findings]};
}

function remove(rack, {id, cables = 'keep'}) {
  const it = itemOf(rack, id);
  if (!it) return {error: GONE};
  const k = cablesOf(rack, id).length, n = count(k, 'cable');
  const ms = managersOf(rack, id);
  const stay = ms.length ? ` Its cable manager${ms.length === 1 ? '' : 's'} ${ms.map(m => m.label).join(', ')} stay${ms.length === 1 ? 's' : ''} on the rack.` : '';
  if (cables === 'remove')
    return done(withoutCablesOf(withoutItem(rack, id), id), (k ? `Removed ${it.label} and its ${n}.` : `Removed ${it.label}.`) + stay);
  return done(withoutItem(rack, id),
    (k ? `Removed ${it.label}. Its ${n} ${k === 1 ? 'is a loose end' : 'are loose ends'}.` : `Removed ${it.label}.`) + stay);
}

// Bolt an unhosted manager over the device at its own U.
function attach(rack, {id}, {chassisOf}) {
  const it = itemOf(rack, id);
  if (!it) return {error: GONE};
  if (!isRackFace(chassisOf(it.ref))) return {error: `${it.label} is not a cable manager.`};
  if (it.on) return unchanged(rack);
  const m = moveItem(rack, id, {ru: it.ru, face: it.face}, chassisOf);
  if (!m.ok) return {error: m.reason};
  const host = itemOf(m.rack, itemOf(m.rack, id).on);
  if (!host) return {error: `${it.label} is not over a device.`};
  return done(m.rack, `Attached ${it.label} to ${host.label}.`);
}

// The manager keeps its U and loses its host.
function detach(rack, {id}) {
  const it = itemOf(rack, id);
  if (!it) return {error: GONE};
  if (!('on' in it)) return unchanged(rack);
  return done({...rack, items: rack.items.map(i => (i.id === id ? detached(i) : i))}, `Detached ${it.label}.`);
}

// ── parts: one slot, one field (spec rack-agent-commands §5.1, §5.2) ─────
// A slot as a person lists it: the slots beside it, grouped, a long run of
// one group as its first and last.
const own = (o, k) => Object.prototype.hasOwnProperty.call(o || {}, k);
function slotList(env, R, path) {
  const cut = path.lastIndexOf('/module/');
  const carrier = cut < 0 ? null : path.slice(0, cut);
  const c = carrier == null ? null : partOf(env.compByRef, R.refAt(`${carrier}/module`));
  const slots = c
    ? [...Object.entries(c.bays || {}).map(([id, b]) => ({...b, id: `${carrier}/module/${id}`})),
       ...(Array.isArray(c.cages) ? c.cages : []).map(g => ({...g, id: `${carrier}/module/${g.id}`}))]
    : [...env.bays, ...env.cages];
  const groups = new Map();
  for (const sl of slots) {
    const g = sl.group || sl.interface || 'other';
    groups.set(g, [...(groups.get(g) || []), sl.id]);
  }
  return [...groups].map(([g, ids]) => `${g}: ${ids.length > 4 ? `${ids[0]} to ${ids.at(-1)} (${ids.length})` : ids.join(', ')}`).join('; ') || 'no bays or cages';
}
const firstEight = refs => (refs.length > 8 ? `${refs.slice(0, 8).join(', ')} and ${refs.length - 8} more` : refs.join(', ') || 'nothing');

// The ports a part in a bay has, by their ids on it: its cages, the parts it
// composes and its own bays.
const portIds = comp => new Set([...(Array.isArray(comp?.cages) ? comp.cages : []).map(g => g.id),
  ...(comp?.parts || []).map(q => q.id), ...Object.keys(comp?.bays || {})]);

function fit(rack, {id, path, ref}, ctx) {
  const it = itemOf(rack, id);
  if (!it) return {error: GONE};
  const was = it.swaps || {};
  const s = slotsFor(ctx, it.ref);
  if (s?.error) return s;
  // the swaps with only this slot changed: the map the slot is judged on
  const flat = {...was};
  if (ref === 'default') delete flat[path]; else flat[path] = ref;
  // SEATING WHAT THE SLOT ALREADY HOLDS CHANGES NOTHING, and so prunes nothing
  // of what sits inside that part
  if (!s && (ref === 'default' ? !own(was, path) : own(was, path) && was[path] === ref)) return unchanged(rack);
  let holds = ref === 'default' ? undefined : ref, isCage = false, view = null, next = flat;
  if (s) {
    const env = slotEnv(it, s, ctx.compByRef);
    const target = resolverFor(env, flat).entryAt(path);
    // a part the slot does not take is refused even when it is the one held
    if (target && ref && ref !== 'default' && !(target.accepts || []).includes(ref))
      return {error: `${path} does not take ${ref}. It takes: ${firstEight(target.accepts || [])}.`};
    if (target && holdsAt(env, was, path, target) === holdsAt(env, flat, path, target)) return unchanged(rack);
    // a different part in a carrier is a fresh seat: what was in it goes
    // (swap.js pruneCarrier, #484 R5), its fields with it
    next = Object.fromEntries(Object.entries(flat).filter(([k]) => k === path || !underCarrier(k, path)));
    const R = resolverFor(env, next);
    if (!target) return {error: `${path} is not a bay or cage on ${it.label}. It has: ${slotList(env, R, path)}.`};
    isCage = !!target.isCage;
    view = target.view ?? null;
    if (ref && ref !== 'default' && acceptSwaps(next, env).ignored.includes(path))
      return {error: `${path} cannot take ${ref} while the slot it shares a seat with holds something.`};
    holds = holdsAt(env, next, path, target);
  } else {
    next = Object.fromEntries(Object.entries(flat).filter(([k]) => k === path || !underCarrier(k, path)));
  }
  const fields = Object.fromEntries(Object.entries(it.fields || {})
    .filter(([k]) => k !== `${path}/module` && !underCarrier(k, path)));
  const name = holds === undefined ? null : partName(ctx.compByRef, holds);
  const findings = [];
  // A BAY'S PORTS GO WITH ITS PART: a cable on a port the new part does not
  // have is kept, as a loose end (remove's cables: 'keep').
  if (!isCage && holds !== undefined) {
    const comp = partOf(ctx.compByRef, holds);
    const known = holds === null || comp;
    const ports = portIds(comp), under = `${path}/module/`;
    const cut = known ? (rack.cables || []).flatMap(c => [c.a, c.b].filter(e => e.item === id && e.path.startsWith(under)
      && !ports.has(e.path.slice(under.length).split('/')[0])).map(e => ({c, e}))) : [];
    if (cut.length) {
      const paths = [...new Set(cut.map(x => x.e.path))], ids = [...new Set(cut.map(x => x.c.id))];
      findings.push(note(`Kept the cables on ${paths.join(', ')} as loose ends (${ids.join(', ')}): ${holds ? `${paths.length === 1 ? 'this port is' : 'these ports are'} not on ${name}` : `${path} is empty`}.`));
    }
  }
  // A CAGE'S NEW PART, against the media of the cables on its port.
  if (isCage && holds) {
    const comp = partOf(ctx.compByRef, holds);
    const conn = comp ? connectorOf({attrs: comp.attrs || {}}) : null;
    for (const c of (rack.cables || [])) {
      if (!conn?.family || ![c.a, c.b].some(e => e.item === id && portPathOf(e.path) === path && (view == null || e.view === view))) continue;
      const m = mediaKind(c.media);
      if ((m.family && m.family !== conn.family) || (m.family === 'fiber' && m.mode && conn.mode && m.mode !== conn.mode))
        findings.push(note(`${c.id} now runs ${MEDIA_LABELS[c.media] ?? c.media} into ${name}.`));
    }
  }
  const summary = holds === undefined ? `Put ${path} on ${it.label} back as its configuration builds it.`
    : holds ? `Fitted ${name} in ${path} on ${it.label}.` : `Emptied ${path} on ${it.label}.`;
  return {rack: updateItem(rack, id, {swaps: next, fields}), summary, findings};
}

// ONE FIELD of the part drawn at `path` - its part path, `<bay>/module` or
// `<cage>-occupant`, the key item.fields uses and inspect lists. Merged: the
// part's other fields, and every other part's, stay as they are.
function field(rack, {id, path, key, value}, ctx) {
  const it = itemOf(rack, id);
  if (!it) return {error: GONE};
  const s = slotsFor(ctx, it.ref);
  if (s?.error) return s;
  if (s && typeof ctx.compByRef === 'function') {
    const env = slotEnv(it, s, ctx.compByRef);
    const R = resolverFor(env, it.swaps || {});
    const slot = R.entryAt(path);
    if (slot) return {error: `${path} is a ${slot.isCage ? 'cage' : 'bay'}; the part in it is ${path}${slot.isCage ? '-occupant' : '/module'}.`};
    const ref = R.refAt(path);
    if (!ref) return {error: `Nothing is seated at ${path} on ${it.label}.`};
    const name = partName(ctx.compByRef, ref);
    const decl = partOf(ctx.compByRef, ref)?.fields || {};
    if (!own(decl, key)) return {error: `${name} has no field ${key}. Its fields: ${Object.keys(decl).join(', ') || 'none'}.`};
    if (value != null && !fieldAccepts(decl[key], value)) {
      const f = decl[key];
      return {error: f.type === 'choice' && Array.isArray(f.options) ? `${key} on ${name} takes one of: ${f.options.join(', ')}.`
        : f.type === 'number' ? `${key} on ${name} takes a number.` : `${key} on ${name} does not take ${JSON.stringify(String(value))}.`};
    }
  }
  const fields = structuredClone(it.fields || {});
  const part = {...(own(fields, path) ? fields[path] : {})};
  if (value == null) delete part[key]; else part[key] = String(value);
  if (Object.keys(part).length) fields[path] = part; else delete fields[path];
  if (same(fields, it.fields || {})) return unchanged(rack);
  return done(updateItem(rack, id, {fields}),
    value == null ? `Reset ${key} on ${path} of ${it.label}.` : `Set ${key} on ${path} of ${it.label} to ${value}.`);
}

// ── the rack ────────────────────────────────────────────────────────────
// A lower height that leaves devices hanging past it packs them down, then
// trims from the bottom (fit.js shrinkRack); a trimmed device's cables stay,
// as loose ends. The form names only the part of `holes` it changed.
function frame(rack, p, {chassisOf}) {
  const want = p.holes ? {...p, holes: {...rack.frame.holes, ...p.holes}} : p;
  if ('heightRU' in want && want.heightRU < rack.frame.heightRU) {
    const {heightRU, ...rest} = want;
    const {rack: shrunk, moved, removed} = shrinkRack(rack, heightRU, chassisOf);
    const next = Object.keys(rest).length ? withFrame(shrunk, rest) : shrunk;
    if (!moved.length && !removed.length) return done(next, `Set the rack to ${heightRU}U.`);
    const dn = n => `device${n === 1 ? '' : 's'}`;
    const names = removed.map(i => i.label).join(', ');
    const text = moved.length && removed.length
      ? `Moved ${moved.length} ${dn(moved.length)} down and removed ${removed.length} from the bottom to fit ${heightRU}U: ${names}.`
      : moved.length
      ? `Moved ${moved.length} ${dn(moved.length)} down to fit ${heightRU}U.`
      : `Removed ${removed.length} ${dn(removed.length)} from the bottom to fit ${heightRU}U: ${names}.`;
    const cut = new Set(removed.flatMap(i => cablesOf(rack, i.id).map(c => c.id))).size;
    const kept = cut ? ` ${cut} ${cut === 1 ? 'cable is kept as a loose end' : 'cables are kept as loose ends'}.` : '';
    return {rack: next, summary: text + kept, findings: [note(text + kept)]};
  }
  const next = withFrame(rack, want);
  return same(next.frame, rack.frame) ? unchanged(rack) : done(next, 'Changed the rack frame.');
}

function rename(rack, {name}) {
  if (!String(name).trim()) return {error: 'A rack needs a name.'};
  return name === rack.name ? unchanged(rack) : done(renamed(rack, name), `Renamed the rack to ${name}.`);
}

function dcim(rack, p) {
  const next = withDcim(rack, p);
  return same(next.dcim, rack.dcim) ? unchanged(rack) : done(next, 'Saved the DCIM import settings.');
}

// ── cables ──────────────────────────────────────────────────────────────
const lengthOf = l => (l ? {value: l.value, unit: l.unit ?? 'm', source: l.source ?? 'entered'} : null);

function cableAdd(rack, {a, b, media = '', purpose = '', label = '', length = null}, {chassisOf}) {
  if (!itemOf(rack, a.item) || !itemOf(rack, b.item)) return {error: NOT_ADDED};
  const can = canCable(rack, a, b, {uOf: heightOf(chassisOf)});
  if (!can.ok) return {error: can.reason};
  const {rack: next, cable} = withCable(rack, {a, b, media, purpose, label, length: lengthOf(length)});
  return done(next, `Added cable ${cableName(cable)}.`, {created: {id: cable.id}});
}

// RE-POINTING AN END (`a`, `b`) keeps the cable - its id, media, purpose,
// label and length - and checks the new port as cable.add would, with the
// cable itself out of the way. A route drawn by hand is kept, and said to be
// possibly stale.
const endOf = e => ({item: e.item, path: e.path, view: e.view === 'rear' ? 'rear' : 'front'});
function cableUpdate(rack, {id, a, b, ...p}, {chassisOf}) {
  const c = cableOf(rack, id);
  if (!c) return {error: CABLE_GONE};
  const ends = {a: a ? endOf(a) : c.a, b: b ? endOf(b) : c.b};
  const moved = ['a', 'b'].filter(k => endKey(ends[k]) !== endKey(c[k]));
  if (moved.some(k => !itemOf(rack, ends[k].item))) return {error: GONE};
  const uOf = heightOf(chassisOf);
  if (moved.length) {
    const can = canCable(rack, ends.a, ends.b, {ignoreId: id, uOf});
    if (!can.ok) return {error: can.reason};
  }
  const want = 'length' in p ? {...p, length: lengthOf(p.length)} : p;
  // A length named at all replaces one the loader kept as written.
  const changed = Object.keys(want).filter(k => !same(want[k], c[k] ?? null) || (k === 'length' && 'lengthAsWritten' in c));
  if (!changed.length && !moved.length) return unchanged(rack);
  const next = updateCable(rack, id, {...want, ...Object.fromEntries(moved.map(k => [k, ends[k]]))});
  const name = cableName(cableOf(next, id));
  const said = moved.map(k => `Moved end ${k.toUpperCase()} of cable ${name} to ${endName(next, ends[k], uOf)}.`);
  return {rack: next, summary: said.length ? said.join(' ') : `Edited cable ${name}.`,
          findings: moved.length && c.routeEdited === true ? [note(`${c.id}'s route was drawn for its old end.`)] : []};
}

function cableRemove(rack, {id}) {
  const c = cableOf(rack, id);
  return c ? done(withoutCable(rack, id), `Deleted cable ${cableName(c)}.`) : {error: CABLE_GONE};
}

// A waypoint must name something the rack has. Checked only when the catalogue
// is given; without it, a route is stored as written. A waypoint already in the
// cable's stored route is not judged again: the page resends the whole route on
// every edit, stale entries included.
function waypointError(rack, route, stored, {chassisOf, guidesOf} = {}) {
  if (typeof chassisOf !== 'function') return null;
  const lanes = lanesOf(rack.frame);
  for (const [k, w] of route.entries()) {
    const n = k + 1;
    if (stored.some(o => same(o, w))) continue;
    if ('lane' in w) {
      if (!lanes.includes(w.lane)) return `Waypoint ${n}: there is no gutter called ${w.lane}. This rack has: ${lanes.join(', ')}.`;
      if (!Number.isInteger(w.ru) || w.ru < 1 || w.ru > rack.frame.heightRU) return `Waypoint ${n}: U${w.ru} is not on this ${rack.frame.heightRU}U rack.`;
      continue;
    }
    const it = rack.items.find(i => i.id === w.item);
    if (!it) return `Waypoint ${n} names ${w.item}, which is not in the rack.`;
    let ids;
    if (typeof guidesOf === 'function') {
      // the configured face, as the page draws it
      ids = [...new Set(guidesOf(it.id).map(g => g.via))].sort();
    } else {
      const ch = chassisOf(it.ref);
      // rack.json lists the default configuration only: a configured item's pathways are unknown here
      if (!ch || it.cfg !== ch.default || Object.keys(it.swaps || {}).length) continue;
      ids = pathwaysOf(ch);
    }
    if (!ids.length) return `Waypoint ${n}: ${it.label} has no rings, ducts or pass-throughs.`;
    if (!ids.includes(w.via)) return `Waypoint ${n}: ${it.label} has no ring, duct or pass-through called ${w.via}. It has: ${ids.join(', ')}.`;
  }
  return null;
}
// A route by hand is the whole list of waypoints, in order, as route.js stores
// them. The page names each edit its own way ("Waypoint added."), so it may
// give the summary; an agent gets the plain one.
function cableRoute(rack, {id, route, summary}, ctx) {
  const c = cableOf(rack, id);
  if (!c) return {error: CABLE_GONE};
  const bad = route.findIndex(w => !isWaypoint(w));
  if (bad >= 0) return {error: `Waypoint ${bad + 1} is neither a pathway nor a gutter.`};
  const wrong = waypointError(rack, route, c.route ?? [], ctx);
  if (wrong) return {error: wrong};
  if (c.routeEdited === true && same(c.route ?? [], route) && !('routeAsWritten' in c)) return unchanged(rack);
  return done(updateCable(rack, id, {route: structuredClone(route), routeEdited: true}), summary ?? `Routed cable ${cableName(c)} by hand.`);
}
function cableRouteReset(rack, {id, summary}) {
  const c = cableOf(rack, id);
  if (!c) return {error: CABLE_GONE};
  if (!('routeEdited' in c) && !(c.route || []).length && !('routeAsWritten' in c)) return unchanged(rack);
  // updateCable drops a key patched to undefined.
  return done(updateCable(rack, id, {route: [], routeEdited: undefined}), summary ?? `Put cable ${cableName(c)} back on its own route.`);
}
// ROUTED LENGTHS ARE MEASURED, NOT EDITED: the page measures them after a
// render and stores them here, so this is not an undo step and is not offered
// to agents. `routeCtx` is that render's routing context (route-context.js
// routeFacts().ctx), whose readers are functions.
// A context that cannot measure (a reader missing or throwing) is refused, not
// thrown: the editor is the page's and an agent's alike.
function lengthsRouted(rack, {routeCtx}) {
  let next;
  try { next = withRoutedLengths(rack, routeCtx); } catch { return {error: 'The routed lengths could not be measured.'}; }
  return next === rack ? unchanged(rack) : done(next, 'Measured the routed lengths.');
}

// ── the table an agent reads ────────────────────────────────────────────
const RACK = {type: 'string', description: 'The id of the rack to edit. Only the first rack can be edited today.'};
const AS = {type: 'string', minLength: 1, description: 'A name for what this creates; later commands in the same batch can use "@name" as its id.'};
const ID = what => ({type: 'string', minLength: 1, description: `The id of the ${what}, as describe() lists it, or "@name" from earlier in this batch.`});
const FACE = {enum: ['front', 'rear'], description: 'Which face of the rack: front or rear.'};
const RU = {type: 'integer', minimum: 1, description: 'The U its bottom sits in, counted from 1 at the bottom of the rails.'};
const END = {type: 'object', required: ['item', 'path', 'view'], additionalProperties: false,
  description: 'One end of a cable: a port on a device.',
  properties: {item: ID('device'), path: {type: 'string', minLength: 1, description: 'The port, as freePorts() names it (e.g. port-1).'},
               view: {enum: ['front', 'rear'], description: "Which of the device's own panels the port is on: front or rear."}}};
const LENGTH = {type: ['object', 'null'], required: ['value'], additionalProperties: false,
  description: 'How long the cable is, or null for not known.',
  properties: {value: {type: 'number', exclusiveMinimum: 0, description: 'The length, above 0.'},
               unit: {enum: ['m', 'ft'], description: 'Metres (m) or feet (ft); m when left out.'},
               source: {type: 'string', description: 'Where the length came from; "entered" when left out.'}}};
const CABLE_FIELDS = {
  media: {enum: ['', ...MEDIA], description: `The cable type: ${MEDIA.join(', ')}, or "" for not known.`},
  purpose: {type: 'string', description: 'What the cable is for, in a word or two (e.g. uplink, management).'},
  label: {type: 'string', description: 'The text on its tags. Its id is used when there is none.'},
  length: LENGTH};
const WAYPOINT = {type: 'object', additionalProperties: false,
  description: 'One waypoint: {item, via} for a pathway on a device, or {lane, ru} for a gutter at a U.',
  properties: {item: {type: 'string', minLength: 1, description: 'The device the pathway is on, with via.'},
               via: {type: 'string', minLength: 1, description: "The pathway on that device's drawing, such as a ring or a duct, with item."},
               lane: {type: 'string', minLength: 1, description: 'The gutter beside the rails, with ru.'},
               ru: {type: 'integer', description: 'The U the gutter is crossed at, with lane.'}},
  dependentRequired: {item: ['via'], via: ['item'], lane: ['ru'], ru: ['lane']}};
const SUMMARY = {type: 'string', description: 'How the step is described in Undo and the notice; the page sets it.'};
const args = (required, properties) => ({type: 'object', required, additionalProperties: false,
                                         properties: {...properties, rack: RACK}});

export const COMMANDS = {
  place: {run: place, description: 'Put a device in the rack with its bottom at a U on a face. A cable manager put over a device bolts onto it. Refused, with the reason, when it does not fit.',
    args: args(['ref', 'face', 'ru'], {ref: {type: 'string', minLength: 1, description: 'The device, as catalog() lists it (its ref).'},
      cfg: {type: 'string', description: "Which of the device's configurations; its default when left out."},
      face: FACE, ru: RU, label: {type: 'string', description: 'The name shown on the drawing; its model when left out.'}, as: AS})},
  move: {run: move, description: 'Move a device to another U and/or face. Its cable managers move with it; a cable manager moved onto a device bolts onto it.',
    args: args(['id'], {id: ID('device'), ru: RU, face: FACE})},
  patch: {run: patch, description: "Change a placed device's configuration, label, turned state, or its Explorer swaps and fields.",
    args: args(['id'], {id: ID('device'), cfg: {type: 'string', description: 'Which of its configurations.'},
      swaps: {type: 'object', description: 'What is seated where: slot path to part ref, as the Explorer writes it.'},
      fields: {type: 'object', description: 'Editable text on the device, as the Explorer writes it.'},
      label: {type: 'string', description: 'The name shown on the drawing.'},
      turned: {type: 'boolean', description: 'true when mounted back to front.'}})},
  remove: {run: remove, description: 'Take a device out of the rack. Its cables are kept as loose ends, or removed with it; its cable managers stay on the rack.',
    args: args(['id'], {id: ID('device'), cables: {enum: ['keep', 'remove'], description: 'keep its cables as loose ends, or remove them; keep when left out.'}})},
  attach: {run: attach, description: 'Bolt an unattached cable manager onto the device at its U.',
    args: args(['id'], {id: ID('cable manager')})},
  detach: {run: detach, description: 'Unbolt a cable manager from its device; it stays at its U on its own.',
    args: args(['id'], {id: ID('cable manager')})},
  frame: {run: frame, description: 'Change the rack frame. A lower height packs devices down and removes from the bottom what still does not fit; their cables are kept as loose ends.',
    args: args([], {kind: {enum: ['four-post', 'two-post'], description: 'four-post or two-post.'},
      heightRU: {type: 'integer', minimum: 1, maximum: 100, description: 'How many U tall, from 1 to 100.'},
      numbering: {enum: ['bottom-up', 'top-down'], description: 'Which way the U labels count.'},
      holes: {type: 'object', additionalProperties: false, description: 'The rail holes.',
        properties: {style: {enum: ['square', 'tapped'], description: 'square or tapped.'},
                     thread: {enum: ['12-24', '10-32', 'M6', null], description: 'The thread of tapped holes.'}}},
      railDepth: {type: 'number', exclusiveMinimum: 0, description: 'Millimetres between the front and rear rails (four-post).'},
      usableDepth: {type: 'number', exclusiveMinimum: 0, description: 'Millimetres from the front rail to the deepest point a device may reach.'}})},
  rename: {run: rename, description: 'Rename the rack.', args: args(['name'], {name: {type: 'string', description: 'The new name.'}})},
  dcim: {run: dcim, step: false, description: 'Set the names a NetBox or Nautobot import needs: the site (or location) and the device role. Not an undo step.',
    args: args([], {site: {type: 'string', description: "NetBox's site, Nautobot's location."}, role: {type: 'string', description: 'The device role.'}})},
  fit: {run: fit, description: 'Seat one part in one bay or cage of a placed device, empty it, or put back what its configuration builds there. Only that slot changes; a part taken out takes what was seated in it, and its settings, with it. Refused, with what the slot takes, when the part does not fit there.',
    args: args(['id', 'path', 'ref'], {id: ID('device'),
      path: {type: 'string', minLength: 1, description: 'The bay or cage, as inspecting the device lists it (e.g. port-1, bay-2/module/lc1).'},
      ref: {type: ['string', 'null'], minLength: 1, description: 'The part to seat, as the slot lists it; null to empty the slot; "default" for what the configuration builds.'}})},
  field: {run: field, description: "Set one setting of one part seated in a placed device, such as a cassette's latch colour or an optic's label; null puts it back to the part's default. Its other settings stay. Refused, with the part's settings or choices, when the part has no such setting or does not take the value.",
    args: args(['id', 'path', 'key', 'value'], {id: ID('device'),
      path: {type: 'string', minLength: 1, description: 'The part, as inspecting the device lists its fields (e.g. bay-1/module, port-1-occupant).'},
      key: {type: 'string', minLength: 1, description: "The setting, as the part's fields list it (e.g. latch-color)."},
      value: {type: ['string', 'number', 'null'], description: 'The new value; null for the default.'}})},
  'cable.add': {run: cableAdd, description: 'Run a cable between two free ports. Refused when a port already has a cable or a device is gone.',
    args: args(['a', 'b'], {a: END, b: END, ...CABLE_FIELDS, as: AS})},
  'cable.update': {run: cableUpdate, description: "Change a cable's type, purpose, label or length, or move either end to another port. A moved end keeps the cable's id and everything else about it; refused when the new port already has a cable.",
    args: args(['id'], {id: ID('cable'), a: {...END, description: 'Move end A to this port; left where it is when left out.'},
      b: {...END, description: 'Move end B to this port; left where it is when left out.'}, ...CABLE_FIELDS})},
  'cable.remove': {run: cableRemove, description: 'Delete a cable.', args: args(['id'], {id: ID('cable')})},
  'cable.route': {run: cableRoute, description: 'Route a cable by hand through the waypoints given, in order. Its routed length follows.',
    args: args(['id', 'route'], {id: ID('cable'),
      route: {type: 'array', description: 'The waypoints, in order: {item, via} for a pathway on a device, {lane, ru} for a gutter at a U.',
        items: WAYPOINT},
      summary: SUMMARY})},
  'cable.route.reset': {run: cableRouteReset, description: 'Drop a hand-made route; the cable takes its own route again.',
    args: args(['id'], {id: ID('cable'), summary: SUMMARY})},
  'lengths.routed': {run: lengthsRouted, step: false, system: true,
    description: 'Store the routed lengths the page measured. Not an undo step; the page sends it.',
    args: args(['routeCtx'], {routeCtx: {type: 'object', description: 'The routing context the last render measured with (route-context.js routeFacts().ctx).'}})},
};

// ── apply ───────────────────────────────────────────────────────────────
const typeWord = s => {
  if (s.enum) return `one of ${s.enum.filter(v => v !== null && v !== '').join(', ')}`;
  const t = [].concat(s.type ?? []).find(x => x !== 'null');
  return {integer: `a whole number${s.minimum != null ? ` from ${s.minimum}` : ''}${s.maximum != null ? ` to ${s.maximum}` : ''}`,
          number: `a number${s.exclusiveMinimum === 0 ? ' above 0' : ''}`, string: 'some text',
          boolean: 'true or false', object: 'an object', array: 'a list'}[t] || 'a value';
};
function sentence(op, e) {
  if (e.keyword === 'required' || e.keyword === 'dependentRequired') {
    const s = e.schema.properties?.[e.missing] || {};
    return `${op} needs ${[...e.path, e.missing].join('.')}, ${typeWord(s)}.`;
  }
  if (e.keyword === 'additionalProperties') return `${op} does not take ${e.path.join('.')}.`;
  return `${op} needs ${e.path.join('.')}, ${typeWord(e.schema)}.`;
}

// Only ids are names: `id`, and the item of a cable end. A label that reads
// "@srv" is a label.
function resolve(cmd, bound) {
  const name = v => (typeof v === 'string' && v.startsWith('@') ? v.slice(1) : null);
  const swap = v => {
    const n = name(v);
    if (n == null) return {v};
    return bound.has(n) ? {v: bound.get(n)} : {error: `Nothing earlier in this batch is called ${n}.`};
  };
  const out = {...cmd};
  for (const k of ['id']) if (k in out) { const s = swap(out[k]); if (s.error) return s; out[k] = s.v; }
  for (const k of ['a', 'b']) if (out[k]?.item != null) {
    const s = swap(out[k].item); if (s.error) return s; out[k] = {...out[k], item: s.v};
  }
  return {cmd: out};
}

export function apply(rack, cmds, ctx) {
  const list = Array.isArray(cmds) ? cmds : [cmds];
  const seen = new Set();
  for (const [index, c] of list.entries()) {
    if (c?.as == null) continue;
    if (seen.has(c.as)) return {error: `Two commands in this batch are called ${c.as}.`, index};
    seen.add(c.as);
  }
  const bound = new Map(), created = {}, ids = [], summaries = [], findings = [];
  let cur = rack, step = false;
  for (const [index, raw] of list.entries()) {
    if (!raw || typeof raw !== 'object' || Array.isArray(raw) || typeof raw.op !== 'string')
      return {error: 'A command is an object with an op.', index};
    const def = Object.hasOwn(COMMANDS, raw.op) ? COMMANDS[raw.op] : null;
    if (!def) return {error: `There is no command called '${raw.op}'.`, index};
    const {op, ...given} = raw;
    const bad = validate(def.args, given)[0];
    if (bad) return {error: sentence(op, bad), index};
    if (given.rack != null && given.rack !== rack.id) return {error: `Only rack ${rack.id} can be edited here.`, index};
    const r = resolve(given, bound);
    if (r.error) return {error: r.error, index};
    const {as, rack: _which, ...a} = r.cmd;
    const res = def.run(cur, a, ctx);
    if (res.error) return {error: res.error, index};
    // Undo describes the step, and Undo keeps what is not a step (the DCIM
    // settings), so only a step's summary is part of it.
    if (res.rack !== cur && def.step !== false) {
      step = true;
      if (res.summary) summaries.push(res.summary);
    }
    findings.push(...res.findings);
    if (res.created) {
      ids.push(res.created.id);
      if (as != null) { bound.set(as, res.created.id); created[as] = res.created.id; }
    }
    cur = res.rack;
  }
  return {rack: cur, summary: summaries.join(' '), findings, created: {...created, ids}, noop: cur === rack, step};
}
