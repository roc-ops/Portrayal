// kit/rack/commands.js
// THE RACK COMMANDS.
// Every edit of a rack is one of these, run through apply(): the page's own
// controls and an agent alike. A command is pure - the rack, its arguments
// and {chassisOf} in, a new rack out - and says no with a sentence. One that
// changes nothing hands back the very rack it was given, so a caller can tell.

import {withItem, updateItem, withoutItem, withFrame, renamed, withDcim, detached, positionOf, isWaypoint, holderOf, firstU, rollOf,
        nextId, zeroUById, zeroUOffset, zeroUBottom, bundlesOf, bundleName, bundleIdFor, holdersOf, usableReadings,
        endHostOf, zeroUIdsInUse} from './model.js';
import {withoutCables, bundleOfCable, bundleCheck, layoutOf, onTrunk, trunkText, waypointText, strapEveryMm,
        spacingText, strapSpacing, strapKinds} from './bundles.js';
import {deriveTrunk, andList} from './bundle-route.js';
import {ownRoute, autoRoute, routedLength, pointOf, portPoint, routePath} from './route.js';
import {fits, fitsDepth, fitsZeroU, isRackFace, isNarrow, railOf, heightOf, shrinkRack, settleZeroU, setbackOf, isZeroUPart} from './fit.js';
import {whereText, zeroUName, fitsHang, hangingOn} from './zero-u.js';
import {stateRefusal} from './states.js';
import {displayRefusal, displaysOf} from './displays.js';
import {shapeRefusal, contentNotes, contentKind} from '../displays.js';
import {spareRefusal, amountRefusal, spareLoad, loadText, whereText as spareWhere, trayText, FORMS, mText} from './slack.js';
import {traysOf} from './solids.js';
import {configFacts} from './catalog.js';
import {placement, moveItem, managersOf} from './managers.js';
import {canCable, withCable, updateCable, cablesOf, cableName, endName, endKey, parseColor,
        connectorOf, mediaKind, portPathOf, isElementId, elementIdReason, MEDIA, MEDIA_LABELS} from './cable-rules.js';
import {portIdsOf, zeroUEnds, zeroUEndsText, seatedEndReason} from './ports.js';
import {validate, same} from './validate.js';
import {withRoutedLengths, pathwaysOf, waypointLanesOf, resolveRoute, pathwaysAt, zeroUPathways, pathwayId} from './route.js';
import {slotsFor, slotEnv, resolverFor, holdsAt, partName, partOf} from './slots.js';
import {acceptSwaps, underCarrier, spanWhy} from '../swap.js';
import {followSwaps, keptSwaps, unknownTexts, rewriteRack, rewroteText, pairText} from '../redirects.js';
import {fieldAccepts} from '../fields.js';

export const GONE = 'That device is no longer in the rack.';
export const CABLE_GONE = 'That cable is no longer in the rack.';
export const NOT_ADDED = 'The cable was not added because a device it ran to was removed.';
export const CLEARED = 'Its swaps and fields were for the old configuration, so they were cleared.';
export const ZERO_GONE = 'That part is no longer beside the rack.';
export const BUNDLE_GONE = 'That bundle is no longer in the rack.';
// A held item is kept and kept in step (docs/rack-file-v4-design.md 7.1), and
// a new one cannot be placed until the catalogue describes what holds one.
export const NO_HOSTS = 'The catalogue describes no host yet, so a device cannot be put on one; heldBy takes only null, which frees it.';

const itemOf = (rack, id) => rack.items.find(i => i.id === id) || null;
// An item command given the id of a part beside the rack: say which command
// takes it, rather than that no device has it.
const goneItem = (rack, id, op) => (zeroUById(rack, id)
  ? {error: `${id} stands beside the rack: use zerou.${op === 'remove' ? 'remove' : 'update'}.`} : {error: GONE});
const cableOf = (rack, id) => (rack.cables || []).find(c => c.id === id) || null;
const at = (rack, item, chassisOf) => `U${positionOf(rack.frame, item.ru, heightOf(chassisOf)(item))}`;
const done = (rack, summary, extra = {}) => ({rack, summary, findings: [], ...extra});
const unchanged = rack => done(rack, '');
const note = text => ({kind: 'note', text});
const count = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
// fits() measures a device against the top by the Us it has left there, which
// reads oddly for a U past the top altogether; an agent can ask for any U.
// The upper half of the top unit is in the rack; the unit after it is not.
const pastTop = (rack, ru) => (ru != null && ru >= rack.frame.heightRU + 1
  ? {error: `U${firstU(rack.frame) - 1 + ru} is past the top of this ${rack.frame.heightRU}U rack.`} : null);

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

// A file's empty cfg is the device's default configuration, so a patch to the
// default's own name is no change.
function cfgOf(ctx, it) {
  if (it.cfg) return it.cfg;
  const s = slotsFor(ctx, it.ref);
  return (s && !s.error ? s.default : null) ?? ctx.chassisOf?.(it.ref)?.default ?? '';
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
  if (!it) return goneItem(rack, id, 'move');
  const top = pastTop(rack, ru);
  if (top) return top;
  const patch = {...(ru == null ? {} : {ru}), ...(face == null ? {} : {face})};
  if (Object.entries(patch).every(([k, v]) => it[k] === v)) return unchanged(rack);
  if (holderOf(it) != null) return {error: `${it.id} is held by ${holderOf(it)}: move ${holderOf(it)}, or free it first.`};
  // Through managers.js: a manager is re-hosted by where it lands, and a host
  // takes its managers with it.
  const m = moveItem(rack, id, patch, chassisOf);
  if (!m.ok) return {error: m.reason};
  const now = itemOf(m.rack, id);
  return done(m.rack, `Moved ${it.label} to ${at(m.rack, now, chassisOf)} on the ${now.face}${railText(now, chassisOf)}.`);
}

// A configuration change is a delta against the OLD configuration: one that
// leaves an item with no swaps or fields to carry forward says they went.
// A NEW CONFIGURATION ALONE starts the device afresh: its swaps and fields
// were for the old one, so they go, as the site's inspector already clears
// them. Swaps or fields sent with it are kept as sent.
function patch(rack, {id, ...given}, ctx) {
  const it = itemOf(rack, id);
  if (!it) return {error: GONE};
  const newCfg = 'cfg' in given && given.cfg !== it.cfg && given.cfg !== cfgOf(ctx, it);
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
      // A REF THE LIBRARY HAS REPLACED IS WRITTEN AS ITS REPLACEMENT before the
      // slot is asked, and a ref it no longer has is kept, with what sits
      // under it, and named (kit/redirects.js): neither is dropped.
      p.swaps = followSwaps(p.swaps, ctx.redirects).swaps;
      const env = slotEnv({...it, cfg: p.cfg ?? it.cfg}, s, ctx.compByRef, ctx.redirects);
      const {kept, rest, gone} = keptSwaps(p.swaps, ctx, path => resolverFor(env, p.swaps).entryAt(path));
      const {accepted, ignored} = acceptSwaps(rest, env);
      // what sits under a carrier the slot refuses goes with it
      const orphan = path => ignored.some(c => underCarrier(path, c));
      const stays = Object.fromEntries(Object.entries(kept).filter(([path]) => !orphan(path)));
      const dropped = Object.keys(kept).filter(path => orphan(path));
      p.swaps = {...accepted, ...stays};
      const left = [...ignored, ...dropped];
      if (left.length) findings.push(note(`Left out ${left.join(', ')}: not a slot on ${it.label}, or a part that slot does not take.`));
      findings.push(...unknownTexts(gone.filter(u => !orphan(u.path)).map(u => ({...u, label: it.label}))).map(note));
    }
  }
  const changes = Object.fromEntries(['cfg', 'swaps', 'fields', 'label', 'turned']
    .filter(k => k in p && !same(p[k], it[k]) && !(k === 'cfg' && !newCfg)).map(k => [k, p[k]]));
  // SETBACK AND heldBy (version 4): null takes the key off the item. A larger
  // setback is checked against the rack; a smaller one is never refused.
  const drop = [];
  if ('heldBy' in given) {
    if (given.heldBy !== null) return {error: NO_HOSTS};
    if ('heldBy' in it) drop.push('heldBy');
  }
  if ('setback' in given && (given.setback ?? null) !== (it.setback ?? null)) {
    const c = ctx.chassisOf(it.ref);
    // a part on the rail face or beside the rack bolts to the rail: it has none
    if (given.setback != null && (isRackFace(c) || isZeroUPart(c)))
      return {error: `${it.label} bolts to the rail face, so it has no setback.`};
    const {setback: _was, ...bare} = it;
    const trial = given.setback == null ? bare : {...bare, setback: given.setback};
    if (setbackOf(rack, trial, ctx.chassisOf) > setbackOf(rack, it, ctx.chassisOf)) {
      const f = fitsDepth(rack, trial, ctx.chassisOf, {ignoreId: id});
      if (!f.ok) return {error: f.reason};
    }
    if (given.setback == null) drop.push('setback'); else changes.setback = given.setback;
  }
  // ROLL: 90, 180 or 270, or null for upright; refused where the rolled box does not fit
  if ('roll' in given && (given.roll ?? 0) !== rollOf(it)) {
    const {roll: _r, ...bare} = it;
    const trial = given.roll == null ? bare : {...bare, roll: given.roll};
    const f = fits(rack, trial, ctx.chassisOf, {ignoreId: id});
    if (!f.ok) return {error: f.reason};
    if (given.roll == null) drop.push('roll'); else changes.roll = given.roll;
  }
  if (!Object.keys(changes).length && !drop.length) return findings.length ? {...unchanged(rack), findings} : unchanged(rack);
  const next = {...it, ...changes};
  for (const k of drop) delete next[k];
  const had = Object.keys(it.swaps ?? {}).length || Object.keys(it.fields ?? {}).length;
  const has = Object.keys(next.swaps ?? {}).length || Object.keys(next.fields ?? {}).length;
  return {rack: {...rack, items: rack.items.map(i => (i.id === id ? next : i))}, summary: `Changed ${it.label}.`,
          findings: [...('cfg' in changes && had && !has ? [note(CLEARED)] : []), ...findings]};
}

function remove(rack, {id, cables = 'keep'}) {
  const it = itemOf(rack, id);
  if (!it) return goneItem(rack, id, 'remove');
  const k = cablesOf(rack, id).length, n = count(k, 'cable');
  const ms = managersOf(rack, id);
  // what it held stays where it was, naming a host that is gone, until it is
  // placed again or freed (fit refuses it meanwhile)
  const hs = rack.items.filter(i => holderOf(i) === id);
  const stay = (ms.length ? ` Its cable manager${ms.length === 1 ? '' : 's'} ${ms.map(m => m.label).join(', ')} stay${ms.length === 1 ? 's' : ''} on the rack.` : '')
    + (hs.length ? ` ${hs.map(h => h.label).join(', ')} ${hs.length === 1 ? 'was' : 'were'} held by it and stay${hs.length === 1 ? 's' : ''} where ${hs.length === 1 ? 'it was' : 'they were'}, held by nothing.` : '');
  if (cables === 'remove') {
    // through withoutCables, so a bundle never names a cable that is gone
    const {rack: next, said} = withoutCables(withoutItem(rack, id), cablesOf(rack, id).map(c => c.id));
    return done(next, (k ? `Removed ${it.label} and its ${n}.` : `Removed ${it.label}.`) + stay + (said ? ` ${said}` : ''));
  }
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
// composes and its own bays, and those of its back (a panel's rear adapters,
// a cassette's trunk connector), which a cable reaches from the host's other
// panel at the same `<bay>/module/<part>` (ports.js portIdsOf).
const portIds = (comp, compByRef) => portIdsOf(comp, compByRef);

function fit(rack, {id, path, ref: given}, ctx) {
  const it = itemOf(rack, id);
  if (!it) return {error: GONE};
  // A REF THE LIBRARY HAS REPLACED IS READ AS ITS REPLACEMENT, and so are the
  // ones already on the device, so the slot is judged on the parts that will
  // be written.
  const ref = given === 'default' ? given : ctx.redirects?.follow(given) ?? given;
  const was = followSwaps(it.swaps || {}, ctx.redirects).swaps;
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
    const env = slotEnv(it, s, ctx.compByRef, ctx.redirects);
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
    if (ref && ref !== 'default') {
      const {ignored, why} = acceptSwaps(next, env);
      // a two-slot card over a full bay, or a part into a covered one, says
      // which bay to empty (docs/pcie-two-slot-bays-design.md, R4)
      if (why?.[path]) return {error: why[path]};
      if (ignored.includes(path))
        return {error: `${path} cannot take ${ref} while the slot it shares a seat with holds something.`};
    } else if (ref === 'default') {
      // putting back a default can put a filler under a two-slot card
      const said = spanWhy(path, holdsAt(env, next, path, target),
        {holds: p => holdsAt(env, next, p, R.entryAt(p)), comp: r => partOf(ctx.compByRef, r)});
      if (said) return {error: said};
    }
    holds = holdsAt(env, next, path, target);
  } else {
    next = Object.fromEntries(Object.entries(flat).filter(([k]) => k === path || !underCarrier(k, path)));
  }
  const fields = Object.fromEntries(Object.entries(it.fields || {})
    .filter(([k]) => k !== `${path}/module` && !underCarrier(k, path)));
  const name = holds === undefined ? null : partName(ctx.compByRef, holds);
  const findings = [];
  if (ref !== given) findings.push(note(`${pairText(given, ref)}: ${ref} was fitted in ${path}.`));
  // A BAY'S PORTS GO WITH ITS PART: a cable on a port the new part does not
  // have is kept, as a loose end (remove's cables: 'keep').
  if (!isCage && holds !== undefined) {
    const comp = partOf(ctx.compByRef, holds);
    const known = holds === null || comp;
    const ports = portIds(comp, ctx.compByRef), under = `${path}/module/`;
    const cut = known ? (rack.cables || []).flatMap(c => [c.a, c.b].filter(e => e.item === id && e.path.startsWith(under)
      && !ports.has(portPathOf(e.path.slice(under.length)).split('/')[0])).map(e => ({c, e}))) : [];
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
        findings.push(note(`${c.id} now runs ${Object.hasOwn(MEDIA_LABELS, c.media) ? MEDIA_LABELS[c.media] : c.media} into ${name}.`));
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
    const env = slotEnv(it, s, ctx.compByRef, ctx.redirects);
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

// ── one rail (#926) ─────────────────────────────────────────────────────
// A narrow rack-face part (fit.js isNarrow: a finger bracket) on one rail
// takes its units on that face and rail only. It stands alone: bolting onto a
// device behind it (`on`) is what a part across both rails does.
const railText = (it, chassisOf) => { const rail = railOf(it, chassisOf); return rail ? `, on the ${rail} rail` : ''; };
const wide = (c, ref) => ({error: `${c?.model ?? ref} spans the opening, so it has no side.`});

function sidePlace(rack, {ref, cfg, face, ru, side, label}, ctx) {
  const {chassisOf} = ctx;
  const top = pastTop(rack, ru);
  if (top) return top;
  const c = chassisOf(ref);
  if (c && !isNarrow(c)) return wide(c, ref);
  if (cfg != null) { const bad = cfgRefused(ctx, ref, cfg, c?.model ?? ref); if (bad) return bad; }
  const f = fits(rack, {ref, face, ru, side}, chassisOf);
  if (!f.ok) return {error: f.reason};
  const name = label ?? c?.model ?? ref;
  const {rack: next, item} = withItem(rack, {ref, cfg: cfg ?? c?.default ?? '', face, ru, side, label: name});
  return done(next, `Placed ${name} at ${at(next, item, chassisOf)} on the ${item.face}${railText(item, chassisOf)}.`, {created: {id: item.id}});
}

function sideSet(rack, {id, side}, {chassisOf}) {
  const it = itemOf(rack, id);
  if (!it) return goneItem(rack, id, 'side.set');
  const want = side ?? null;
  if ((it.side ?? null) === want) return unchanged(rack);
  if (want && !isNarrow(chassisOf(it.ref))) return wide(chassisOf(it.ref), it.ref);
  const {side: _was, ...rest} = detached(it);
  // across both rails it is placed as any rack-face part, onto a device behind it
  const next = want ? {...rest, side: want} : {...rest, ...placement(rack, rest, chassisOf, {ignoreId: id})};
  const f = fits(rack, next, chassisOf, {ignoreId: id});
  if (!f.ok) return {error: f.reason};
  return done({...rack, items: rack.items.map(i => (i.id === id ? next : i))},
    want ? `Put ${it.label} on the ${want} rail.` : `Put ${it.label} across both rails.`);
}

// ── beside the rack (#926) ──────────────────────────────────────────────
// A zero-U part (fit.js isZeroUPart) stands at an attachment point of the
// frame, its bottom level with a U, and takes no rack unit: an entry of
// rack.zeroU (model.js), never an item. A cable ends on one of its own
// connector slots (the outlets of a zero-U PDU) as on a port of an item.
// Its id is never one a cable end still names (model.js zeroUIdsInUse).
function zeroUPlace(rack, {ref, cfg, at: where, ru, between = false, label}, ctx) {
  const {chassisOf} = ctx;
  const f = fitsZeroU(rack, {ref, at: where, ru}, chassisOf);
  if (!f.ok) return {error: f.reason};
  const c = chassisOf(ref);
  if (cfg != null) { const bad = cfgRefused(ctx, ref, cfg, c?.model ?? ref); if (bad) return bad; }
  const id = nextId(zeroUIdsInUse(rack), 'z');
  const z = {id, ref, cfg: cfg ?? c?.default ?? '', label: label ?? c?.model ?? ref, at: where, offsetMm: zeroUOffset(ru),
             ...(between ? {between: true} : {})};
  const next = {...rack, zeroU: [...(rack.zeroU || []), z]};
  return done(next, `Placed ${z.label} ${whereText(next, z, chassisOf)}.`, {created: {id}});
}

// A part hung on brackets (`heldBy`) stands where they hold it: it is not
// moved by hand, and a bracket that moves carries what hangs on it.
function zeroUUpdate(rack, {id, at: where, ru, between, label, swaps, fields}, ctx) {
  const {chassisOf} = ctx;
  const z = zeroUById(rack, id);
  if (!z) return {error: ZERO_GONE};
  const want = {at: where ?? z.at, ru: ru ?? zeroUBottom(z)};
  const moved = (where != null && where !== z.at) || (ru != null && ru !== zeroUBottom(z));
  if (moved && holdersOf(z).length)
    return {error: `${zeroUName(z, chassisOf)} hangs on ${holdersOf(z).join(', ')}: move a bracket, or take it off them with zerou.hang.`};
  const {between: _b, ...rest} = z;
  const now = between == null ? z.between === true : !!between;
  const next = {...rest, at: want.at, ...(moved ? {offsetMm: zeroUOffset(want.ru)} : {}),
                ...(label != null ? {label: String(label).trim() || chassisOf(z.ref)?.model || z.ref} : {}),
                // what is seated in it and its part settings, each map replaced whole, as patch does on a device
                ...(swaps !== undefined ? {swaps: {...swaps}} : {}), ...(fields !== undefined ? {fields: structuredClone(fields)} : {}),
                ...(now ? {between: true} : {})};
  if (same(next, z)) return unchanged(rack);
  if (moved) {
    const f = fitsZeroU(rack, {ref: z.ref, id, ...want}, chassisOf, {ignoreId: id});
    if (!f.ok) return {error: f.reason};
  }
  let out = {...rack, zeroU: rack.zeroU.map(o => (o === z ? next : o))};
  // what hangs on it goes with it, checked where it lands
  const carried = [];
  if (moved) for (const h of hangingOn(out, id)) {
    const f = fitsHang(out, h, ctx);
    if (!f.ok) return {error: `${zeroUName(h, chassisOf)} hangs on it: ${f.reason}`};
    if (!f.place) continue;
    const there = {...h, ...f.place};
    const g = fitsZeroU(out, {...there, ru: undefined}, chassisOf, {ignoreId: h.id});
    if (!g.ok) return {error: `${zeroUName(h, chassisOf)} hangs on it: ${g.reason}`};
    out = {...out, zeroU: out.zeroU.map(o => (o.id === h.id ? there : o))};
    carried.push(there);
  }
  const with_ = carried.length ? ` ${carried.map(h => zeroUName(h, chassisOf)).join(', ')} ${carried.length === 1 ? 'hangs' : 'hang'} on it and moved with it.` : '';
  return done(out, (moved ? `Moved ${zeroUName(next, chassisOf)} to ${whereText(out, next, chassisOf)}.`
    : `Changed ${zeroUName(next, chassisOf)}, ${whereText(out, next, chassisOf)}.`) + with_);
}

// ITS CORDS are kept as loose ends, or removed with it, as a device's are
// (`remove`).
function zeroURemove(rack, {id, cables = 'keep'}, {chassisOf}) {
  const z = zeroUById(rack, id);
  if (!z) return {error: ZERO_GONE};
  // what hung on it stays where it was, on a bracket that is gone, and fit
  // refuses it until it is hung again or taken off
  const hung = hangingOn(rack, id);
  const stay = hung.length ? ` ${hung.map(h => zeroUName(h, chassisOf)).join(', ')} hung on it and stay${hung.length === 1 ? 's' : ''} where ${hung.length === 1 ? 'it was' : 'they were'}.` : '';
  const name = zeroUName(z, chassisOf), k = cablesOf(rack, id).length, n = count(k, 'cable');
  const out = {...rack, zeroU: rack.zeroU.filter(o => o !== z)};
  if (cables === 'remove' && k) {
    const {rack: next, said} = withoutCables(out, cablesOf(rack, id).map(c => c.id));
    return done(next, `Removed ${name} and its ${n} from beside the rack.${stay}${said ? ` ${said}` : ''}`);
  }
  return done(out, `Removed ${name} from beside the rack.${k ? ` Its ${n} ${k === 1 ? 'is a loose end' : 'are loose ends'}.` : ''}${stay}`);
}

// HANG A PART ON BRACKETS (`on`: their ids), or take it off them (`on: null`).
// Hung, it stands where they hold it: the kit writes its `at` and `offsetMm`.
function zeroUHang(rack, {id, on}, ctx) {
  const {chassisOf} = ctx;
  const z = zeroUById(rack, id);
  if (!z) return {error: ZERO_GONE};
  if (on === null) {
    if (!('heldBy' in z)) return unchanged(rack);
    const {heldBy: _h, ...free} = z;
    return done({...rack, zeroU: rack.zeroU.map(o => (o === z ? free : o))},
      `Took ${zeroUName(z, chassisOf)} off its brackets; it stands ${whereText(rack, free, chassisOf)}.`);
  }
  const ids = [...new Set(on)];
  if (ids.includes(id)) return {error: `${zeroUName(z, chassisOf)} cannot hang on itself.`};
  const s = slotsFor(ctx, z.ref);
  if (!s) return {error: 'zerou.hang needs the parts lists of the devices, which the caller has not loaded.'};
  if (s.error) return s;
  const trial = {...z, heldBy: {...(z.heldBy && typeof z.heldBy === 'object' && !Array.isArray(z.heldBy) ? z.heldBy : {}), parts: ids}};
  const f = fitsHang(rack, trial, ctx);
  if (!f.ok) return {error: f.reason};
  if (!f.place) return {error: partsMissingFor(ids, ctx)};
  const next = {...trial, ...f.place};
  if (same(next, z)) return unchanged(rack);
  const g = fitsZeroU(rack, {...next, ru: undefined}, chassisOf, {ignoreId: id});
  if (!g.ok) return {error: g.reason};
  const out = {...rack, zeroU: rack.zeroU.map(o => (o === z ? next : o))};
  return done(out, `Hung ${zeroUName(next, chassisOf)} on ${ids.join(', ')}, ${whereText(out, next, chassisOf)}.`);
}
const partsMissingFor = (ids, ctx) => `The parts list of ${ids.find(i => !ctx.slotsOf(i)) ?? 'a bracket'} could not be loaded.`;

// ── states and readings (docs/rack-file-v4-design.md section 4) ──────────
// On a device or on a part beside the rack, by its id.
const entryOf = (rack, id) => itemOf(rack, id) ?? zeroUById(rack, id);
const withEntry = (rack, id, next) => (itemOf(rack, id)
  ? {...rack, items: rack.items.map(i => (i.id === id ? next : i))}
  : {...rack, zeroU: rack.zeroU.map(o => (o?.id === id ? next : o))});
const entryName = (e, chassisOf) => e.label || chassisOf(e.ref)?.model || e.ref;

function stateSet(rack, {id, path, state}, ctx) {
  const e = entryOf(rack, id);
  if (!e) return {error: GONE};
  const had = e.states && typeof e.states === 'object' ? e.states : {};
  if (state == null) {
    if (!Object.hasOwn(had, path)) return unchanged(rack);
    const {[path]: _was, ...rest} = had;
    const {states: _s, ...bare} = e;
    return done(withEntry(rack, id, Object.keys(rest).length ? {...e, states: rest} : bare), `Cleared the state of ${path} on ${entryName(e, ctx.chassisOf)}.`);
  }
  if (had[path] === state) return unchanged(rack);
  // checked against what the part declares, when the parts lists are loaded
  const s = slotsFor(ctx, e.ref);
  if (s?.error) return s;
  if (s) {
    const facts = configFacts(s, e.cfg);
    const no = facts ? stateRefusal({...e, label: entryName(e, ctx.chassisOf)}, path, state, facts) : null;
    if (no) return {error: no};
  }
  return done(withEntry(rack, id, {...e, states: {...had, [path]: state}}), `Set ${path} on ${entryName(e, ctx.chassisOf)} to ${state}.`);
}

function readingsSet(rack, {id, readings}, ctx) {
  const e = entryOf(rack, id);
  if (!e) return {error: GONE};
  const name = entryName(e, ctx.chassisOf);
  if (readings == null) {
    if (!('readings' in e) && !('readingsAsWritten' in e)) return unchanged(rack);
    const {readings: _r, readingsAsWritten: _w, ...bare} = e;
    return done(withEntry(rack, id, bare), `Cleared the readings of ${name}.`);
  }
  if (!usableReadings(readings)) return {error: 'readings.set needs readings with a source, a time (at) that can be read, and values by part.'};
  const s = slotsFor(ctx, e.ref);
  if (s?.error) return s;
  const facts = s ? configFacts(s, e.cfg) : null;
  if (facts?.metering === 'none')
    return {error: `${ctx.chassisOf(e.ref)?.model ?? e.ref} measures nothing, so there is no reading for ${Object.keys(readings.values || {}).join(', ') || 'it'}.`};
  if (same(readings, e.readings)) return unchanged(rack);
  const {readingsAsWritten: _w, ...rest} = e;
  return done(withEntry(rack, id, {...rest, readings: structuredClone(readings)}), `Stored the readings of ${name}.`);
}

// WHAT A DISPLAY SHOWS (docs/display-content-design.md), on a device or on a
// part beside the rack, by the path of the display. The content is checked
// against the display when the parts lists are loaded: a part that is no
// display, and content the display cannot take, are refused with a sentence;
// text longer than the display, or a picture that does not fill its window,
// is kept and said.
function displaySet(rack, {id, path, content}, ctx) {
  const e = entryOf(rack, id);
  if (!e) return {error: GONE};
  const had = e.displays && typeof e.displays === 'object' ? e.displays : {};
  const name = entryName(e, ctx.chassisOf);
  if (content == null) {
    if (!Object.hasOwn(had, path)) return unchanged(rack);
    const {[path]: _was, ...rest} = had;
    const {displays: _d, ...bare} = e;
    return done(withEntry(rack, id, Object.keys(rest).length ? {...e, displays: rest} : bare), `Cleared what ${path} on ${name} shows.`);
  }
  const bad = shapeRefusal(content);
  if (bad) return {error: bad};
  const s = slotsFor(ctx, e.ref);
  if (s?.error) return s;
  let notes = [];
  if (s) {
    const no = displayRefusal({...e, label: name}, path, content, ctx);
    if (no) return {error: no};
    const d = displaysOf(e, ctx)?.find(x => x.path === path);
    notes = d ? contentNotes(d, content, `${path} on ${name}`) : [];
  }
  if (same(had[path], content)) return unchanged(rack);
  const shown = {text: 'text', digits: `"${content.digits}"`, image: 'an image'}[contentKind(content)];
  return done(withEntry(rack, id, {...e, displays: {...had, [path]: structuredClone(content)}}),
    `${path} on ${name} now shows ${shown}.${notes.length ? ` ${notes.join(' ')}` : ''}`, {findings: notes.map(note)});
}

// What a frame change did to the parts beside the rack, as sentences.
function zeroUSaid({moved, removed}, chassisOf) {
  const names = list => list.map(z => zeroUName(z, chassisOf)).join(', ');
  return [moved.length ? `Moved ${names(moved)} beside the rack to fit the new frame.` : '',
          removed.length ? `Removed ${names(removed)} from beside the rack: ${removed.length === 1 ? 'it does' : 'they do'} not fit the new frame.` : '']
    .filter(Boolean).join(' ');
}

// ── the rack ────────────────────────────────────────────────────────────
// A lower height that leaves devices hanging past it packs them down, then
// trims from the bottom (fit.js shrinkRack); a trimmed device's cables stay,
// as loose ends. The form names only the part of `holes` it changed.
// The parts beside the rack follow (fit.js settleZeroU): to the attachment
// point on their own side when the kind changes, down when the rack is lower,
// and off it when they no longer fit; each is named.
function frame(rack, p, ctx) {
  const r = frameItems(rack, p, ctx);
  if (r.error || r.rack === rack) return r;
  const z = settleZeroU(r.rack, ctx.chassisOf);
  // A PART HUNG ON BRACKETS IS NEVER MOVED SILENTLY: the kit writes where it
  // stands from where its brackets are, so a frame that would move or remove
  // it, or one of the brackets it hangs on, is refused, naming them.
  const touched = new Set([...z.moved, ...z.removed].map(e => e.id));
  const hung = (r.rack.zeroU || []).find(e => holdersOf(e).length && (touched.has(e.id) || holdersOf(e).some(id => touched.has(id))));
  if (hung) return {error: `${zeroUName(hung, ctx.chassisOf)} hangs on ${holdersOf(hung).join(', ')}, and this frame would move ${touched.has(hung.id) ? 'it' : 'a bracket it hangs on'}: take it off its brackets first with zerou.hang.`};
  const said = zeroUSaid(z, ctx.chassisOf);
  return said ? {rack: z.rack, summary: `${r.summary} ${said}`, findings: [...r.findings, note(said)]} : r;
}

// A LARGER RACK SETBACK is checked for every device it moves back, on depth
// alone (fit.js fitsDepth), in the rack as the command leaves it; a smaller
// one is never refused.
function setbackRefused(rack, next, chassisOf) {
  if (!((next.frame.setback ?? 0) > (rack.frame.setback ?? 0))) return null;
  const was = new Map(rack.items.map(i => [i.id, setbackOf(rack, i, chassisOf)]));
  for (const it of next.items) {
    if (setbackOf(next, it, chassisOf) <= (was.get(it.id) ?? 0)) continue;
    const f = fitsDepth(next, it, chassisOf, {ignoreId: it.id});
    if (!f.ok) return {error: `${it.label}: ${f.reason}`};
  }
  return null;
}

function frameItems(rack, p, {chassisOf}) {
  const want = p.holes ? {...p, holes: {...rack.frame.holes, ...p.holes}} : p;
  if ('heightRU' in want && want.heightRU < rack.frame.heightRU) {
    const {heightRU, ...rest} = want;
    const {rack: shrunk, moved, removed, orphaned} = shrinkRack(rack, heightRU, chassisOf);
    const next = Object.keys(rest).length ? withFrame(shrunk, rest) : shrunk;
    const bad = setbackRefused(rack, next, chassisOf);
    if (bad) return bad;
    if (!moved.length && !removed.length) return done(next, `Set the rack to ${heightRU}U.`);
    const dn = n => `device${n === 1 ? '' : 's'}`;
    const names = removed.map(i => i.label).join(', ');
    const text = moved.length && removed.length
      ? `Moved ${moved.length} ${dn(moved.length)} down and removed ${removed.length} from the bottom to fit ${heightRU}U: ${names}.`
      : moved.length
      ? `Moved ${moved.length} ${dn(moved.length)} down to fit ${heightRU}U.`
      : `Removed ${removed.length} ${dn(removed.length)} from the bottom to fit ${heightRU}U: ${names}.`;
    const cut = new Set(removed.flatMap(i => cablesOf(rack, i.id).map(c => c.id))).size;
    const cables = cut ? ` ${cut} ${cut === 1 ? 'cable is kept as a loose end' : 'cables are kept as loose ends'}.` : '';
    // what a removed device held stays in the rack, held by nothing
    const one = orphaned.length === 1;
    const kept = cables + (orphaned.length ? ` ${orphaned.map(i => i.label).join(', ')} ${one ? 'was' : 'were'} held by a removed device and stay${one ? 's' : ''} in the rack, held by nothing.` : '');
    return {rack: next, summary: text + kept, findings: [note(text + kept)]};
  }
  const next = withFrame(rack, want);
  if (same(next.frame, rack.frame)) return unchanged(rack);
  const bad = setbackRefused(rack, next, chassisOf);
  if (bad) return bad;
  return done(next, 'Changed the rack frame.');
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

// AN END NAMES A PORT BY ITS PATH. An element id of a drawing is refused, with
// the address it stands for (cable-rules.js elementIdReason).
const endRefused = ends => { const e = ends.find(x => isElementId(x.path)); return e ? {error: `${elementIdReason(e.path)}.`} : null; };

// A CABLE'S OWN COLOUR (`color`, #1028) is `#rgb` or `#rrggbb`, stored as
// lower case `#rrggbb`; null or "" is none of its own. Anything else is
// refused with cable-rules.js COLOR_REFUSED, here and in cable.update.
// AN END ON A PART BESIDE THE RACK (P-0019): the part's own connector slots
// are the only ends it has, and the catalogue lists them all (ports.js
// zeroUEnds), so with the parts lists loaded an end on one it does not have is
// refused, naming those it has. Without them it is kept as given, as a port
// of an item is.
const hasEnd = (rack, id) => !!endHostOf(rack, id);
function zeroUEndRefused(rack, ends, ctx) {
  if (typeof ctx?.slotsOf !== 'function' || typeof ctx?.compByRef !== 'function') return null;
  for (const e of ends) {
    const z = zeroUById(rack, e.item);
    if (!z) continue;
    const name = zeroUName(z, ctx.chassisOf), all = zeroUEnds(z, ctx), view = e.view === 'rear' ? 'rear' : 'front';
    if (!all.length) return {error: `${name} has nothing a cable can end on.`};
    if (all.some(s => s.path === e.path && s.view === view)) continue;
    const other = all.find(s => s.path === e.path);
    return {error: other ? `${e.path} is on the ${other.view} panel of ${name}: give view "${other.view}".`
      : `${name} has no ${e.path}. It has ${zeroUEndsText(all)}.`};
  }
  return null;
}
// AN END ON A VIEW OR PORT THAT A SEATED PART DOES NOT HAVE is refused with the
// sentence the loose-end finding gives (ports.js seatedEndReason).
function seatedEndRefused(rack, ends, ctx) {
  const why = seatedEndReason(rack, ends, ctx);
  return why ? {error: `${why}.`} : null;
}
function cableAdd(rack, {a, b, media = '', purpose = '', label = '', length = null, color = null}, ctx) {
  const {chassisOf} = ctx;
  if (!hasEnd(rack, a.item) || !hasEnd(rack, b.item)) return {error: NOT_ADDED};
  const refused = endRefused([a, b]) ?? zeroUEndRefused(rack, [a, b], ctx) ?? seatedEndRefused(rack, [a, b], ctx);
  if (refused) return refused;
  const tint = parseColor(color);
  if (!tint.ok) return {error: tint.reason};
  const can = canCable(rack, a, b, {uOf: heightOf(chassisOf)});
  if (!can.ok) return {error: can.reason};
  const {rack: next, cable} = withCable(rack, {a, b, media, purpose, label, length: lengthOf(length), color: tint.color});
  return done(next, `Added cable ${cableName(cable)}.`, {created: {id: cable.id}});
}

// RE-POINTING AN END (`a`, `b`) keeps the cable - its id, media, purpose,
// label and length - and checks the new port as cable.add would, with the
// cable itself out of the way. A route drawn by hand is kept, and said to be
// possibly stale.
const endOf = e => ({item: e.item, path: e.path, view: e.view === 'rear' ? 'rear' : 'front',
  ...(typeof e.plug === 'string' && e.plug ? {plug: e.plug} : {})});
function cableUpdate(rack, {id, a, b, ...p}, ctx) {
  const {chassisOf} = ctx;
  const c = cableOf(rack, id);
  if (!c) return {error: CABLE_GONE};
  const ends = {a: a ? endOf(a) : c.a, b: b ? endOf(b) : c.b};
  const moved = ['a', 'b'].filter(k => endKey(ends[k]) !== endKey(c[k]));
  if (moved.some(k => !hasEnd(rack, ends[k].item))) return {error: GONE};
  const refused = endRefused(moved.map(k => ends[k])) ?? zeroUEndRefused(rack, moved.map(k => ends[k]), ctx)
    ?? seatedEndRefused(rack, moved.map(k => ends[k]), ctx);
  if (refused) return refused;
  const uOf = heightOf(chassisOf);
  if (moved.length) {
    const can = canCable(rack, ends.a, ends.b, {ignoreId: id, uOf});
    if (!can.ok) return {error: can.reason};
  }
  const {straps: tie, ...fields} = p;
  const want = 'length' in fields ? {...fields, length: lengthOf(fields.length)} : {...fields};
  // its own colour: a colour sets it, null or "" takes it off (updateCable)
  if ('color' in want) {
    const tint = parseColor(want.color);
    if (!tint.ok) return {error: tint.reason};
    want.color = tint.color;
  }
  // the straps of this cable alone: null takes the key off, which is the default
  const untie = tie === null && 'straps' in c;
  if (tie != null) want.straps = {...(c.straps && typeof c.straps === 'object' ? c.straps : {}), ...tie};
  // A length named at all replaces one the loader kept as written.
  // (and a colour named at all, one kept as written)
  const changed = Object.keys(want).filter(k => !same(want[k], c[k] ?? null) || (k === 'length' && 'lengthAsWritten' in c)
    || (k === 'color' && 'colorAsWritten' in c));
  // AN END NAMED AT THE PORT IT IS ON may still state another plug (`plug`,
  // cable-rules.js endPlug), or none where it stated one: that is an edit of
  // the cable and not a move.
  const plugged = ['a', 'b'].filter(k => !moved.includes(k) && (ends[k].plug ?? null) !== (c[k].plug ?? null));
  if (!changed.length && !moved.length && !plugged.length && !untie) return unchanged(rack);
  let next = updateCable(rack, id, {...want, ...Object.fromEntries([...moved, ...plugged].map(k => [k, ends[k]]))});
  if (untie) next = {...next, cables: next.cables.map(x => { if (x.id !== id) return x; const {straps: _s, ...rest} = x; return rest; })};
  const name = cableName(cableOf(next, id));
  const said = moved.map(k => `Moved end ${k.toUpperCase()} of cable ${name} to ${endName(next, ends[k], uOf)}.`);
  // A bundled cable stays in its bundle; an end now on another device is said.
  const bun = bundleOfCable(rack, id);
  const away = bun ? moved.filter(k => ends[k].item !== c[k].item) : [];
  return {rack: next, summary: said.length ? said.join(' ') : `Edited cable ${name}.`,
          findings: [...(moved.length && c.routeEdited === true ? [note(`${c.id}'s route was drawn for its old end.`)] : []),
                     ...away.map(k => note(`${c.id} stays in ${bundleName(bun)}; its ${k} end is now on another device.`))]};
}

// Through withoutCables: a cable leaves its bundle in the same step.
function cableRemove(rack, {id}) {
  const c = cableOf(rack, id);
  if (!c) return {error: CABLE_GONE};
  const {rack: next, said} = withoutCables(rack, [id]);
  return done(next, `Deleted cable ${cableName(c)}.${said ? ` ${said}` : ''}`);
}

// A waypoint must name something the rack has. Checked only when the catalogue
// is given; without it, a route is stored as written. A waypoint already in the
// cable's stored route is not judged again: the page resends the whole route on
// every edit, stale entries included.
// A PART BESIDE THE RACK (a zero-U duct) is named as a device is: its duct,
// and each window through its back, by the catalogue (route.js
// zeroUPathways; issue 13). A pathway may be named as the route summary says
// it ("ring 3", "left end ring": route.js pathwayId), and the route returned
// holds its id. {error} or {route}.
function waypointsChecked(rack, route, stored, {chassisOf, guidesOf} = {}) {
  if (typeof chassisOf !== 'function') return {route};
  const lanes = waypointLanesOf(rack.frame);
  const out = [];
  for (const [k, w] of route.entries()) {
    const n = k + 1;
    out.push(w);
    if (stored.some(o => same(o, w))) continue;
    if ('lane' in w) {
      if (!lanes.includes(w.lane)) return {error: `Waypoint ${n}: there is no gutter called ${w.lane}. This rack has: ${lanes.join(', ')}.`};
      if (!Number.isInteger(w.ru) || w.ru < 1 || w.ru > rack.frame.heightRU)
        // the stored ru, not a U label: past the frame there is no label to give
        return {error: `Waypoint ${n}: ru ${w.ru} is not on this ${rack.frame.heightRU}U rack, whose ru runs 1-${rack.frame.heightRU} from the bottom.`};
      continue;
    }
    const it = rack.items.find(i => i.id === w.item);
    const z = it ? null : zeroUById(rack, w.item);
    if (!it && !z) return {error: `Waypoint ${n} names ${w.item}, which is not in the rack.`};
    let ids, name;
    if (z) {
      name = zeroUName(z, chassisOf);
      ids = zeroUPathways(rack, z, {chassisOf}).map(p => p.via).sort();
      if (!ids.length) return {error: `Waypoint ${n}: ${name} has no duct or pass-through; it is no pathway.`};
    } else {
      name = it.label;
      const ch = typeof chassisOf === 'function' ? chassisOf(it.ref) : null;
      // rack.json lists the default configuration only: a configured item's pathways are unknown there
      const asListed = !!ch && (it.cfg || ch.default) === ch.default && !Object.keys(it.swaps || {}).length;
      if (typeof guidesOf === 'function') {
        // the configured face, as the page draws it, and the trays the
        // catalogue lists (docs/cable-lay-design.md section 8: a tray is named
        // as a ring is)
        const trays = asListed && Array.isArray(ch.trays) ? ch.trays.map(t => t?.id).filter(v => typeof v === 'string') : [];
        ids = [...new Set([...(guidesOf(it.id) || []).map(g => g.via), ...trays])].sort();
      } else {
        if (!asListed) continue;
        ids = pathwaysOf(ch);
      }
      if (!ids.length) return {error: `Waypoint ${n}: ${it.label} has no rings, ducts, pass-throughs or trays.`};
    }
    const via = pathwayId(ids, w.via);
    if (!via) return {error: `Waypoint ${n}: ${name} has no ring, duct, pass-through or tray called ${w.via}. It has: ${ids.join(', ')}.`};
    if (via !== w.via) out[out.length - 1] = {...w, via};
  }
  return {route: out};
}
// A route by hand is the whole list of waypoints, in order, as route.js stores
// them. The page names each edit its own way ("Waypoint added."), so it may
// give the summary; an agent gets the plain one.
// The readers a waypoint is checked against: the routing context's guides
// (`ctx.route.guidesOf`, as the bundle commands take them), else a flat
// `ctx.guidesOf` as 0.4.0's callers pass it, else the catalogue's pathways.
const wpCtx = ctx => ({chassisOf: ctx?.chassisOf, guidesOf: ctx?.route?.guidesOf ?? ctx?.guidesOf});
function cableRoute(rack, {id, route, summary}, ctx) {
  const c = cableOf(rack, id);
  if (!c) return {error: CABLE_GONE};
  const bad = route.findIndex(w => !isWaypoint(w));
  if (bad >= 0) return {error: `Waypoint ${bad + 1} is neither a pathway nor a gutter.`};
  const checked = waypointsChecked(rack, route, c.route ?? [], wpCtx(ctx));
  if (checked.error) return {error: checked.error};
  route = checked.route;
  if (c.routeEdited === true && same(c.route ?? [], route) && !('routeAsWritten' in c)) return unchanged(rack);
  const next = updateCable(rack, id, {route: structuredClone(route), routeEdited: true});
  // A member's own route decides only its lead-in and lead-out.
  const b = bundleOfCable(rack, id);
  const findings = [];
  if (b) {
    const m = layoutOf(next, b, ctx)?.members.find(x => x.cable === id);
    const [from, to] = m?.join && m?.leave ? [m.join, m.leave] : [b.route[0], b.route.at(-1)];
    findings.push(note(from && to ? `${id} follows ${bundleName(b)} from ${waypointText(rack, from)} to ${waypointText(rack, to)}; this route applies outside it.`
      : `${id} is in ${bundleName(b)}; this route applies outside it.`));
  }
  return {...done(next, summary ?? `Routed cable ${cableName(c)} by hand.`), findings};
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

// ── bundles (#921, docs/cable-bundles-design.md section 3) ──────────────
// Cables combed into one run along a stored trunk. Membership lives on the
// bundle (model.js); the trunk is worked out once, from the members' own
// routes, or given by hand, and kept. What needs the routing readers comes on
// `ctx.route` (route.js's context, from the page's last render); without it a
// bundle is made and changed but not measured, and a command that would need
// to measure is refused with the reason.
const NO_ROUTES = "The cables' routes are not known here, so the bundle needs a route.";
const bundleAt = (rack, id) => bundlesOf(rack).find(b => b.id === id) ?? null;
const putBundle = (rack, b) => ({...rack, bundles: bundlesOf(rack).map(x => (x.id === b.id ? b : x))});
const labelOf = rack => id => rack.items.find(i => i.id === id)?.label ?? id;
// A spacing under 50 mm or over 1 m is taken, and said: either is more likely
// a unit slip than intent.
// A bundle's straps in words: its spacing, and each kind that is not as the
// spacing alone would have it.
function strapsSaid(b) {
  const e = strapSpacing(b), k = strapKinds(b), on = e !== null;
  const extra = [k.breakout !== on ? (k.breakout ? 'breakout straps' : 'no breakout straps') : null,
                 k.anchors !== on ? (k.anchors ? 'anchor straps' : 'no anchor straps') : null].filter(Boolean);
  // with no spacing straps and another kind on, "no straps" would not be true
  return [e === null && extra.length ? 'no spacing straps' : spacingText(e), ...extra].join(', ');
}
function spacingNote(straps) {
  const e = straps?.every;
  if (!e) return [];
  const mm = strapEveryMm({straps});
  return mm < 50 ? [note(`Straps every ${e.value} ${e.unit} is under 50 mm apart; check the unit.`)]
    : mm > 1000 ? [note(`Straps every ${e.value} ${e.unit} is over 1 m apart; check the unit.`)] : [];
}
// The checks for the bundle a command changed (bundles.js bundleCheck), as
// findings; without the routes, one note in their place.
function checksOf(rack, b, ctx) {
  const name = bundleName(b);
  if (b.members.length < 2) return [note(`${name} now holds ${b.members.length === 1 ? 'one cable' : 'no cables'}.`)];
  if (!ctx?.route) return [note(`${name} is not checked for size or bend: the routes are not known here.`)];
  const r = bundleCheck(rack, b, ctx);
  if (!r.checked) return [note(`${name} is not checked for size or bend: the routes could not be read.`)];
  return [...r.warnings.map(text => ({kind: 'warning', text})), ...r.notes.map(note)];
}
// A trunk by hand: the shapes, then each waypoint as cable.route checks it.
// {error} or {route}, the route with each pathway by its id.
function trunkChecked(rack, route, stored, ctx) {
  if (!route.length) return {error: "A bundle's route needs at least one waypoint."};
  const bad = route.findIndex(w => !isWaypoint(w));
  if (bad >= 0) return {error: `Waypoint ${bad + 1} is neither a pathway nor a gutter.`};
  // a reader that throws counts as missing: checked against the catalogue
  try { return waypointsChecked(rack, route, stored, wpCtx(ctx)); } catch { return waypointsChecked(rack, route, stored, {chassisOf: ctx?.chassisOf}); }
}
// The trunk worked out from the cables' own routes (bundle-route.js).
function workedOut(rack, ids, ctx) {
  if (!ctx?.route) return {error: NO_ROUTES};
  let members;
  try {
    // each cable's route as a member takes it: by the gutter, where a short
    // jumper would hang on its own (#1012, route.js resolveRoute)
    members = ids.map(id => ({id, waypoints: ownRoute(rack, cableOf(rack, id), ctx.route, {gutter: true}).waypoints}));
  } catch { return {error: NO_ROUTES}; }
  return deriveTrunk(members, {nameOf: labelOf(rack), frame: rack.frame});
}
// Cables a bundle command is given: each in the rack, named once, and in no
// other bundle than `into`.
function cablesError(rack, ids, into = null) {
  for (const id of ids) if (!cableOf(rack, id)) return CABLE_GONE;
  const twice = ids.find((id, k) => ids.indexOf(id) !== k);
  if (twice) return `${twice} is named twice.`;
  for (const id of ids) {
    const b = bundleOfCable(rack, id);
    if (b && b.id !== into) return `${id} is already in ${bundleName(b)}. Peel it off first.`;
  }
  return null;
}
const numberTaken = (rack, n, self = null) => bundlesOf(rack).find(b => b.number === n && b.id !== self) ?? null;

function bundleCreate(rack, {cables, label = '', number, route, straps}, ctx) {
  const bad = cablesError(rack, cables);
  if (bad) return {error: bad};
  const taken = number != null ? numberTaken(rack, number) : null;
  if (taken) return {error: `Bundle ${number} is already ${taken.id}'s number.`};
  let trunk;
  if (route != null) {
    const checked = trunkChecked(rack, route, [], ctx);
    if (checked.error) return {error: checked.error};
    trunk = structuredClone(checked.route);
  } else {
    const t = workedOut(rack, cables, ctx);
    if (t.error) return {error: t.error};
    trunk = t.route;
  }
  const b = {id: bundleIdFor(rack), number: number ?? Math.max(0, ...bundlesOf(rack).map(x => x.number)) + 1,
             label: String(label), members: cables.map(cable => ({cable})), route: trunk,
             ...(straps ? {straps: structuredClone(straps)} : {})};
  const next = {...rack, bundles: [...bundlesOf(rack), b]};
  const longer = hungLonger(rack, next, cables, ctx);
  return {rack: next, summary: `Bundled ${cables.length} cables as ${bundleName(b)}.${longer ? ` ${longer}` : ''}`, created: {id: b.id},
          findings: [...spacingNote(straps), ...checksOf(next, b, ctx)]};
}

// WHAT BUNDLING COSTS A JUMPER THAT HUNG (#1012). A jumper within two units
// hangs from port to port on its own; in a bundle it is taken to the trunk
// and back, so it is longer: 0.60 m becomes 0.81 m for a one-unit hop to a
// lane beside it. The summary says so, cable by cable, so that whoever
// bundles it sees the length it buys. Each is a cable on its automatic
// route with no waypoint of its own, whose measured length grows by a
// centimetre or more. Nothing is said when the routes are not known, or a
// reader throws.
function hungLonger(before, after, ids, ctx) {
  if (!ctx?.route) return '';
  try {
    const m = v => `${v.toFixed(2)} m`;
    const grew = ids.flatMap(id => {
      const c = cableOf(before, id);
      if (!c || c.routeEdited === true || autoRoute(before, c, ctx.route).length) return [];
      const was = routedLength(before, c, ctx.route), is = routedLength(after, cableOf(after, id), ctx.route);
      return was && is && is.measured >= was.measured + 0.01 ? [{id, was: was.measured, is: is.measured}] : [];
    });
    if (!grew.length) return '';
    return grew.length === 1
      ? `${grew[0].id} hung on its own and now runs with the bundle: ${m(grew[0].was)} becomes ${m(grew[0].is)}.`
      : `${andList(grew.map(g => g.id))} hung on their own and now run with the bundle: ${grew.map(g => `${g.id} ${m(g.was)} to ${m(g.is)}`).join(', ')}.`;
  } catch { return ''; }
}

// A cable already in the bundle has its peel points cleared, and rides the
// whole trunk again. The trunk is not rerouted.
function bundleAdd(rack, {id, cables}, ctx) {
  const b = bundleAt(rack, id);
  if (!b) return {error: BUNDLE_GONE};
  const bad = cablesError(rack, cables, b.id);
  if (bad) return {error: bad};
  const named = new Set(cables);
  const again = b.members.filter(m => named.has(m.cable) && ('a' in m || 'b' in m)).map(m => m.cable);
  const fresh = cables.filter(c => !b.members.some(m => m.cable === c));
  if (!again.length && !fresh.length) return unchanged(rack);
  const members = [...b.members.map(m => { if (!named.has(m.cable)) return m; const {a: _a, b: _b, ...bare} = m; return bare; }),
                   ...fresh.map(cable => ({cable}))];
  const nb = {...b, members}, next = putBundle(rack, nb), name = bundleName(b);
  const said = [fresh.length ? `Added ${andList(fresh)} to ${name}.` : '',
                again.length ? `${andList(again)} ${again.length === 1 ? 'rides' : 'ride'} the whole of ${name} again.` : ''].filter(Boolean);
  return {rack: next, summary: said.join(' '), findings: checksOf(next, nb, ctx)};
}

// Out of the bundle (no `at`), or out from a waypoint on toward one end.
function bundlePeel(rack, {id, cable, at: where, end}, ctx) {
  const b = bundleAt(rack, id);
  if (!b) return {error: BUNDLE_GONE};
  const name = bundleName(b);
  const m = b.members.find(x => x.cable === cable);
  if (!m) return {error: cableOf(rack, cable) ? `${cable} is not in ${name}.` : CABLE_GONE};
  if (where == null) {
    const nb = {...b, members: b.members.filter(x => x !== m)}, next = putBundle(rack, nb);
    return {rack: next, summary: `Took ${cable} out of ${name}; it follows its own route again.`, findings: checksOf(next, nb, ctx)};
  }
  if (!isWaypoint(where)) return {error: 'at is neither a pathway nor a gutter.'};
  const w = 'lane' in where ? {lane: where.lane, ru: where.ru} : {item: where.item, via: where.via};
  if (!onTrunk(b, w)) return {error: `${waypointText(rack, w)} is not on ${name}'s route, which runs ${trunkText(rack, b)}.`};
  let toward = end;
  if (toward == null) {
    if (!ctx?.route) return {error: `Say which end ${cable} heads for, a or b: the routes are not known here.`};
    const c = cableOf(rack, cable);
    let pa = null, pb = null, pw = null;
    try { pa = portPoint(rack, c.a, ctx.route); pb = portPoint(rack, c.b, ctx.route); pw = pointOf(rack, w, ctx.route); } catch { /* not measured */ }
    if (!pa || !pb || !pw) return {error: `Say which end ${cable} heads for, a or b: its ports are not found on the drawings.`};
    const d = p => Math.hypot(p.x - pw.x, p.y - pw.y, p.z - pw.z);
    toward = d(pa) < d(pb) ? 'a' : 'b';
  }
  const other = toward === 'a' ? 'b' : 'a';
  if (!ctx?.route && m[other] != null)
    return {error: `${cable} already leaves ${name} at ${waypointText(rack, m[other])} for its ${other} end; the routes are not known here to check this against it.`};
  const nm = {...m, [toward]: w};
  if (same(nm, m)) return unchanged(rack);
  const nb = {...b, members: b.members.map(x => (x === m ? nm : x))}, next = putBundle(rack, nb);
  if (ctx?.route) {
    const L = layoutOf(next, nb, ctx);
    if (L?.members.find(x => x.cable === cable)?.stale.includes(toward))
      return {error: `${waypointText(rack, w)} is at or past where ${cable} leaves ${name} for its ${other} end, so it would have no run in the bundle.`};
  }
  return {rack: next, summary: `${cable} leaves ${name} at ${waypointText(rack, w)} for its ${toward} end.`, findings: checksOf(next, nb, ctx)};
}

function bundleUpdate(rack, {id, label, number, straps, summary, ...rest}, ctx) {
  const b = bundleAt(rack, id);
  if (!b) return {error: BUNDLE_GONE};
  const name = bundleName(b);
  const patch = {}, said = [], findings = [];
  if (label != null && String(label) !== b.label) patch.label = String(label);
  if (number != null && number !== b.number) {
    const taken = numberTaken(rack, number, b.id);
    if (taken) return {error: `Bundle ${number} is already ${taken.id}'s number.`};
    patch.number = number;
  }
  // STRAPS MERGE BY KEY (version 4): a key given replaces that key, a key
  // left out stays as it was, and `straps: null` takes the object off, which
  // is the defaults: every 12 in, with breakout and anchor straps.
  let unstrap = false;
  if (straps === null) unstrap = 'straps' in b;
  else if (straps !== undefined) {
    const merged = {...(b.straps || {}), ...structuredClone(straps)};
    if (!same(merged, b.straps ?? {})) {
      patch.straps = merged;
      findings.push(...spacingNote(straps));
    }
  }
  let cleared = [];
  if ('route' in rest) {
    let trunk;
    if (rest.route === null) {
      if (b.members.length < 2) return {error: `${name} needs two or more cables to work its route out from them.`};
      const t = workedOut(rack, b.members.map(m => m.cable), ctx);
      if (t.error) return {error: t.error};
      trunk = t.route;
    } else {
      const checked = trunkChecked(rack, rest.route, b.route || [], ctx);
      if (checked.error) return {error: checked.error};
      trunk = structuredClone(checked.route);
    }
    if (!same(trunk, b.route) || 'routeAsWritten' in b) {
      patch.route = trunk;
      // the peel points the new trunk does not hold go with the old trunk
      const nt = {route: trunk};
      const members = b.members.map(m => {
        const drop = ['a', 'b'].filter(k => k in m && !onTrunk(nt, m[k]));
        if (!drop.length) return m;
        cleared.push(m.cable);
        const out = {...m};
        for (const k of drop) delete out[k];
        return out;
      });
      if (cleared.length) patch.members = members;
    }
  }
  if (!Object.keys(patch).length && !unstrap) return unchanged(rack);
  const {routeAsWritten: _w, ...kept} = b;
  const nb = {...('route' in patch ? kept : b), ...patch};
  if (unstrap) delete nb.straps;
  const next = putBundle(rack, nb);
  if ('label' in patch || 'number' in patch) said.push(`Renamed ${name} to ${bundleName(nb)}.`);
  if ('straps' in patch || unstrap) said.push(`${bundleName(nb)} now has ${strapsSaid(nb)}.`);
  if ('route' in patch) said.push(`Rerouted ${bundleName(nb)}.`);
  if (cleared.length) findings.push(note(`Cleared the peel points of ${andList(cleared)}: they are not on the new route.`));
  return {rack: next, summary: summary ?? said.join(' '), findings: [...findings, ...checksOf(next, nb, ctx)]};
}

// The cables stay as they are, and follow their own routes again.
function bundleRemove(rack, {id}) {
  const b = bundleAt(rack, id);
  if (!b) return {error: BUNDLE_GONE};
  const n = b.members.length;
  return done({...rack, bundles: bundlesOf(rack).filter(x => x !== b)},
    `Dissolved ${bundleName(b)}${n ? `; ${n === 1 ? 'its cable follows its own route' : `its ${n} cables follow their own routes`} again` : ''}.`);
}

// ── spare cable (docs/rack-file-v4-design.md sections 3.3 and 3.5) ───────
// Where a cable's spare is stored: a duct or a tray on its route (slack.js
// SPARE_HOLDS says which), or one of its ends. It is recorded and listed, and
// the kit places none itself. A pathway may be named as the route summary
// says it (route.js pathwayId), and is stored by its id.
const sameAt = (e, at) => ('end' in at ? e.end === at.end : e.item === at.item && e.via === at.via);
function cableSlack(rack, {id, at: where, value, unit, form}, ctx) {
  const c = cableOf(rack, id);
  if (!c) return {error: CABLE_GONE};
  const isEnd = where.end != null, isTray = where.item != null && where.via != null;
  if (isEnd === isTray) return {error: 'cable.slack needs at as {item, via}, a duct or a tray, or {end}, a or b.'};
  if (isEnd && form != null) return {error: 'Spare left at an end has no form.'};
  // judged against the route when the routes are known; else recorded as given
  let path = null;
  if (ctx.route) { try { path = routePath(rack, c, ctx.route); } catch { path = null; } }
  const andWhere = () => (ctx.route ? ` ${spareWhere(rack, c, ctx.route, path ?? undefined)}` : '');
  let via = where.via;
  if (isTray) {
    if (!itemOf(rack, where.item) && !zeroUById(rack, where.item)) return {error: `${where.item} is not in the rack.${andWhere()}`};
    const ids = slackIds(rack, where.item, ctx);
    if (ids) {
      via = pathwayId(ids, where.via);
      if (!via) return {error: `${labelOfAny(rack, where.item)} has no pathway called ${where.via}.${andWhere()}`};
    }
  }
  const entry = {...(isEnd ? {end: where.end} : {item: where.item, via, ...(form != null ? {form} : {})}),
                 ...(value != null ? {value, unit: unit ?? 'm'} : {})};
  // a place that can never hold it says where the spare can go; a tray's own reasons stand alone
  const no = isTray ? spareRefusal(rack, c, entry, ctx.route, path) : null;
  if (no) return {error: /is not on the route|holds no spare|has no pathway/.test(no) ? `${no}${andWhere()}` : no};
  const had = Array.isArray(c.slack) ? c.slack : [];
  const others = had.filter(e => !sameAt(e, entry));
  // no more than the cable has to store, and nothing on a cable that is short
  const tooMuch = path ? amountRefusal(rack, {...c, slack: others}, entry, ctx.route, path) : null;
  if (tooMuch) return {error: tooMuch};
  if (value == null && others.some(e => e.value == null))
    return {error: `${c.id} already has an entry that takes the rest of its spare: give this one a value.`};
  const findings = [];
  const next = [...others, entry];
  if (isTray) {
    // a duct is counted against what its maker states, with this entry in it
    if (ctx.route && pathwaysAt(rack, entry.item, ctx.route).find(p => p.via === entry.via)?.kind === 'duct') {
      let load = null;
      try { load = spareLoad(updateCable(rack, id, {slack: next}), entry.item, ctx.route, c); } catch { load = null; }
      if (load?.over) return {error: `${loadText(rack, entry.item, load)} Store less there, or in another duct or tray. ${spareWhere(rack, c, ctx.route, path ?? undefined)}`};
      if (load && (!load.compared || load.estimated)) findings.push(note(loadText(rack, entry.item, load)));
    }
  }
  if (same(next, had) && Array.isArray(c.slack)) return unchanged(rack);
  const what = value != null ? `${mText(unit === 'ft' ? value * 0.3048 : value)} of the spare` : 'the spare';
  return {...done(updateCable(rack, id, {slack: next}),
    `Stored ${what} of ${cableName(c)} ${isEnd ? `at its ${where.end.toUpperCase()} end` : `in ${trayText(rack, entry)}`}.`), findings};
}
// The pathway ids a place for spare may name on a part, for its spoken name:
// what the routes know there, else the catalogue's for a part as listed;
// null where neither is known, and then the name is kept as given.
function slackIds(rack, id, ctx) {
  if (ctx.route) {
    let ps = [];
    try { ps = pathwaysAt(rack, id, ctx.route); } catch { ps = []; }
    if (ps.length) return ps.map(p => p.via);
  }
  if (typeof ctx.chassisOf !== 'function') return null;
  const z = zeroUById(rack, id);
  if (z) { const ps = zeroUPathways(rack, z, ctx); return ps.length ? ps.map(p => p.via) : null; }
  const it = itemOf(rack, id), ch = ctx.chassisOf(it.ref);
  const asListed = !!ch && (it.cfg || ch.default) === ch.default && !Object.keys(it.swaps || {}).length;
  const ids = asListed ? pathwaysOf(ch) : [];
  return ids.length ? ids : null;
}
const labelOfAny = (rack, id) => itemOf(rack, id)?.label || zeroUById(rack, id)?.label || id;

// Without `at`, nothing is said of the cable's spare any more (no `slack`
// key); with it, that one entry goes, and the key with the last of them.
function cableSlackClear(rack, {id, at: where}) {
  const c = cableOf(rack, id);
  if (!c) return {error: CABLE_GONE};
  if (!('slack' in c)) return unchanged(rack);
  const left = where ? c.slack.filter(e => !sameAt(e, where)) : [];
  if (where && left.length === c.slack.length) return unchanged(rack);
  const {slack: _s, ...bare} = c;
  const next = left.length ? {...c, slack: left} : bare;
  return done({...rack, cables: rack.cables.map(x => (x.id === id ? next : x))},
    left.length ? `Cleared one place for the spare of ${cableName(c)}.` : `Cleared where the spare of ${cableName(c)} is stored.`);
}

// `cable.lay`: pin how a cable lies in one pathway, `{item, via}`: its
// `face` on a tray (`top` or `underside`, named in the frame of the part)
// and its `position` across the pathway. A key left out is kept, null
// unpins it, and an entry with neither left is removed, the `lay` key with
// the last. `face` is acted on by the routes (route.js layFaceOf);
// `position` is kept and not acted on until lay order is built. What the
// file holds that is no usable entry is kept as it was written.
// A face is judged against the tray when the routes are known, and recorded
// as given when they are not, as `cable.slack` records a place.
const usableLay = e => !!e && typeof e === 'object' && !Array.isArray(e) && typeof e.item === 'string' && typeof e.via === 'string';
function cableLay(rack, args, ctx) {
  const {id, at: where} = args;
  const c = cableOf(rack, id);
  if (!c) return {error: CABLE_GONE};
  const hasPos = 'position' in args, hasFace = 'face' in args;
  if (!hasPos && !hasFace) return {error: 'cable.lay needs a position or a face: a value to pin it, or null to unpin it.'};
  const it = itemOf(rack, where.item);
  if (!it) return {error: `${where.item} is not in the rack.`};
  const name = `${it.label || it.id} ${where.via}`;
  // the pathway must be one the routes know on the device: a ring or a duct
  // the page draws, or a tray; with no routes known it is recorded as given
  const pinning = args.position != null || args.face != null;
  let trays = [], guides = [];
  if (ctx.route) { try { trays = traysOf(rack, ctx.route).filter(x => x.item === where.item); } catch { trays = []; } }
  if (pinning && ctx.route) {
    try { guides = typeof ctx.route.guidesOf === 'function' ? ctx.route.guidesOf(where.item) || [] : []; } catch { guides = []; }
    const ids = [...new Set([...guides.map(g => g.via), ...trays.map(t => t.via)])].sort();
    if (!ids.includes(where.via))
      return {error: ids.length ? `${it.label || it.id} has no ring, duct or tray called ${where.via}. It has: ${ids.join(', ')}.`
                                : `${it.label || it.id} has no rings, ducts or trays.`};
  }
  // A POSITION IS ONE OF THE CABLES THAT SHARE THE PATHWAY (P-0018): from 1 to
  // how many routes pass through it, this cable's among them. Judged when the
  // routes are known; with none, it is recorded as given.
  if (args.position != null && ctx.route) {
    let sharing = null;
    try {
      sharing = rack.cables.filter(x => resolveRoute(rack, x, ctx.route).waypoints.some(w => w.item === where.item && w.via === where.via)).map(x => x.id);
    } catch { sharing = null; }   // a route that cannot be read leaves the position unjudged, as a face is when no path is found
    if (sharing && !sharing.includes(c.id)) return {error: `${c.id} does not pass through ${name}, so it has no position there.`};
    if (sharing && args.position > sharing.length)
      return {error: `${name} carries ${sharing.length} cable${sharing.length === 1 ? '' : 's'}, so a position there runs from 1 to ${sharing.length}; ${args.position} is past it.`};
  }
  if (args.face != null && ctx.route) {
    const t = trays.find(x => x.via === where.via) || null;
    if (!t && guides.some(g => g.via === where.via)) return {error: `${name} is a ring or a duct, not a tray: a cable has no face to lie on there.`};
    if (!t) return {error: `${name} is no tray, so a cable has no face to lie on there.`};
    const held = t.flipped ? 'top' : 'underside';
    if (args.face === held && !t.ties.length)
      return {error: `${name} offers no held face: it states no tie slots, so nothing holds a cable to its ${held}.`};
  }
  const had = Array.isArray(c.lay) ? c.lay : [];
  const old = had.find(e => usableLay(e) && e.item === where.item && e.via === where.via) || null;
  const entry = {...(old || {item: where.item, via: where.via})};
  for (const [given, key] of [[hasPos, 'position'], [hasFace, 'face']]) {
    if (!given) continue;
    if (args[key] == null) delete entry[key]; else entry[key] = args[key];
  }
  const keep = entry.position != null || entry.face != null;
  const next = old ? had.flatMap(e => (e === old ? (keep ? [entry] : []) : [e])) : keep ? [...had, entry] : had;
  if (same(next, had)) return unchanged(rack);
  // A FACE THE ROUTE DOES NOT TAKE IS REFUSED, as cable.slack refuses a tray
  // that is not on the route: the cable must rest on the tray, and on the
  // face asked, once the entry is written.
  if (args.face != null && ctx.route) {
    const laid = {...c, lay: next};
    let path = null;
    try { path = routePath({...rack, cables: rack.cables.map(x => (x.id === id ? laid : x))}, laid, ctx.route); } catch { path = null; }
    if (path) {
      const rest = (path.rests || []).find(x => x.kind === 'tray' && x.item === where.item && x.via === where.via);
      if (!rest) return {error: `${name} is not on the route of ${c.id}.`};
      if (rest.face !== args.face) return {error: `${c.id} cannot be held to the ${args.face} of ${name} along its stretch there, so it stays on the ${rest.face}.`};
    }
  }
  const {lay: _l, ...bare} = c;
  const said = [entry.face != null ? `on the ${entry.face}` : null, entry.position != null ? `at position ${entry.position}` : null].filter(Boolean).join(', ');
  return done({...rack, cables: rack.cables.map(x => (x.id === id ? (next.length ? {...c, lay: next} : bare) : x))},
    keep ? `Laid ${cableName(c)} ${said} of ${name}.` : `${cableName(c)} is no longer pinned in ${name}.`);
}

// ── the table an agent reads ────────────────────────────────────────────
const RACK = {type: 'string', description: 'The id of the rack to edit. Only the first rack can be edited today.'};
const AS = {type: 'string', minLength: 1, description: 'A name for what this creates; later commands in the same batch can use "@name" as its id.'};
const ID = what => ({type: 'string', minLength: 1, description: `The id of the ${what}, as the rack's description lists it, or "@name" from earlier in this batch.`});
const FACE = {enum: ['front', 'rear'], description: 'Which face of the rack: front or rear.'};
const RU = {type: 'number', minimum: 1, multipleOf: 0.5,
  description: 'Its bottom, in units from 1 at the bottom of the rails, in steps of 0.5 (12.5 is the upper half of U12). A whole-unit device takes a whole unit.'};
// A part that bolts to the rail face stands at a whole unit.
const WHOLE_RU = {type: 'integer', minimum: 1, description: 'The U its bottom sits in, counted from 1 at the bottom of the rails.'};
const END = {type: 'object', required: ['item', 'path', 'view'], additionalProperties: false,
  description: 'One end of a cable: a port on a device, or an outlet of a part beside the rack (a zero-U PDU).',
  properties: {item: ID('device or part beside the rack'), path: {type: 'string', minLength: 1, description: "The port or outlet, as the free ports name it (e.g. port-1, outlet-a2)."},
               view: {enum: ['front', 'rear'], description: "Which of the device's own panels the port is on: front or rear."},
               plug: {type: 'string', minLength: 1, description: 'The plug or lug at this end, as a component ref (e.g. generic/c14-plug@1). Only for a port that takes more than one.'}}};
const LENGTH = {type: ['object', 'null'], required: ['value'], additionalProperties: false,
  description: 'How long the cable is, or null for not known.',
  properties: {value: {type: 'number', exclusiveMinimum: 0, description: 'The length, above 0.'},
               unit: {enum: ['m', 'ft'], description: 'Metres (m) or feet (ft); m when left out.'},
               source: {type: 'string', description: 'Where the length came from; "entered" when left out.'}}};
const CABLE_FIELDS = {
  media: {enum: ['', ...MEDIA], description: `The cable type: ${MEDIA.join(', ')}, or "" for not known.`},
  purpose: {type: 'string', description: 'What the cable is for, in a word or two (e.g. uplink, management).'},
  label: {type: 'string', description: 'The text on its tags. Its id is used when there is none.'},
  length: LENGTH,
  color: {type: ['string', 'null'], description: 'Its own color, as # and three or six hex digits (e.g. #2bb3c8); null for none of its own, so that its ends, its type or its media decide.'}};
const WAYPOINT = {type: 'object', additionalProperties: false,
  description: 'One waypoint: {item, via} for a pathway on a device, or {lane, ru} for a gutter at a U.',
  properties: {item: {type: 'string', minLength: 1, description: 'The device the pathway is on, with via.'},
               via: {type: 'string', minLength: 1, description: "The pathway on that device's drawing, such as a ring or a duct, with item."},
               lane: {type: 'string', minLength: 1, description: 'The gutter beside the rails, with ru. A four-post also has the lane between a rail and a part beside it, such as left-rear-inner.'},
               ru: {type: 'integer', description: 'The U the gutter is crossed at, with lane.'}},
  dependentRequired: {item: ['via'], via: ['item'], lane: ['ru'], ru: ['lane']}};
const SUMMARY = {type: 'string', description: 'How the step is described in Undo and the notice; set by the caller.'};
const AT = {type: 'string', minLength: 1, description: 'Its upright: left or right (two-post); left-front, right-front, left-rear or right-rear (four-post).'};
const BOTTOM = {type: 'integer', minimum: 1, description: 'The U its bottom is level with, counted from 1 at the bottom of the rails.'};
const BETWEEN = {type: 'boolean', description: 'true when it stands between this rack and the next one, serving both.'};
const BUNDLE_CABLES = (min, description) => ({type: 'array', minItems: min, description,
  items: {type: 'string', minLength: 1, description: 'A cable id, or "@name" from earlier in this batch.'}});
const STRAPS = {type: ['object', 'null'], additionalProperties: false,
  description: 'Its hook-and-loop straps: any of every, breakout and anchors; a key left out stays as it is. null for the defaults.',
  properties: {every: {type: ['object', 'null'], required: ['value', 'unit'], additionalProperties: false,
    description: 'The spacing, {value, unit}, or null for no spacing straps. Every 12 in when never set.',
    properties: {value: {type: 'number', exclusiveMinimum: 0, description: 'How far apart, above 0.'},
                 unit: {enum: ['in', 'mm'], description: 'Inches (in) or millimetres (mm).'}}},
    breakout: {type: 'boolean', description: 'A strap beside each point where a cable joins or leaves. On when never set, unless every is null.'},
    anchors: {type: 'boolean', description: 'A strap at each tray tie slot the bundle lies on. On when never set, unless every is null.'}}};
const CABLE_STRAPS = {type: ['object', 'null'], additionalProperties: false,
  description: 'The straps of this cable alone: {anchors: false} for none tying it to a tray it passes; null for the default.',
  properties: {anchors: {type: 'boolean', description: 'false for no strap tying it to a tray it lies on.'}}};
const args = (required, properties) => ({type: 'object', required, additionalProperties: false,
                                         properties: {...properties, rack: RACK}});

export const COMMANDS = {
  place: {run: place, description: 'Put a device in the rack with its bottom at a U on a face. A cable manager put over a device bolts onto it. Refused, with the reason, when it does not fit, or when the device has no such configuration.',
    args: args(['ref', 'face', 'ru'], {ref: {type: 'string', minLength: 1, description: 'The device, as the catalogue lists it (its ref).'},
      cfg: {type: 'string', description: "Which of the device's configurations; its default when left out."},
      face: FACE, ru: RU, label: {type: 'string', description: 'The name shown on the drawing; its model when left out.'}, as: AS})},
  move: {run: move, description: 'Move a device to another U and/or face. Its cable managers move with it; a cable manager moved onto a device bolts onto it.',
    args: args(['id'], {id: ID('device'), ru: RU, face: FACE})},
  patch: {run: patch, description: "Change a placed device's configuration, label, turned state, roll or setback, or replace all of what is seated in it and all of its part settings at once. A new configuration on its own clears what was seated and set; to change one slot or one setting, use fit or field.",
    args: args(['id'], {id: ID('device'), cfg: {type: 'string', description: 'Which of its configurations; it keeps its own when left out.'},
      swaps: {type: 'object', description: 'Every slot path to the part ref seated there, replacing the whole map. A slot left out holds what its configuration builds.'},
      fields: {type: 'object', description: 'Every part path to its settings ({key: value}), replacing the whole map.'},
      label: {type: 'string', description: 'The name shown on the drawing.'},
      turned: {type: 'boolean', description: 'true when mounted back to front.'},
      setback: {type: ['number', 'null'], description: 'Millimetres its faceplate stands behind its rail, into the rack; negative is proud. null for the default of the device or the rack.'},
      heldBy: {type: ['object', 'null'], description: 'null frees a device held on a shelf or a rail. Nothing else is taken yet.'},
      roll: {enum: [90, 180, 270, null], description: 'Degrees it is turned clockwise in its face, as seen from that face: 180 is upside down. null for upright.'}})},
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
        properties: {style: {enum: ['square', 'tapped', 'round'], description: 'square, tapped or round.'},
                     thread: {enum: ['12-24', '10-32', 'M6', null], description: 'The thread of tapped holes.'}}},
      railDepth: {type: 'number', exclusiveMinimum: 0, description: 'Millimetres between the front and rear rails (four-post).'},
      usableDepth: {type: 'number', exclusiveMinimum: 0, description: 'Millimetres from the front rail to the deepest point a device may reach.'},
      startU: {type: 'integer', minimum: 1, description: 'The number of the first unit, for a rack whose labels do not start at 1.'},
      setback: {type: ['number', 'null'], description: 'Millimetres a faceplate stands behind its rail in this rack, for a device that states none; null for flush.'}})},
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
  'side.place': {run: sidePlace, description: 'Put a narrow rail part (a finger bracket narrower than the opening) on one rail, its bottom at a U. It takes that rail only, so another can stand on the other rail at the same U.',
    args: args(['ref', 'face', 'ru', 'side'], {ref: {type: 'string', minLength: 1, description: 'The part, as the catalogue lists it (its ref).'},
      cfg: {type: 'string', description: "Which of the part's configurations; its default when left out."},
      face: FACE, ru: WHOLE_RU, side: {enum: ['left', 'right'], description: 'Which rail it is on, as seen from its face: left or right.'},
      label: {type: 'string', description: 'The name shown on the drawing; its model when left out.'}, as: AS})},
  'side.set': {run: sideSet, description: 'Put a narrow rail part on the left or right rail, or (side null) across both, where it bolts onto a device behind it.',
    args: args(['id', 'side'], {id: ID('rail part'), side: {enum: ['left', 'right', null], description: 'left, right, or null for across both rails.'}})},
  'zerou.place': {run: zeroUPlace, description: 'Stand a zero-U part (a vertical cable manager, or a zero-U PDU) beside the rack at an upright, its bottom level with a U. It takes no rack unit; the lane beside that upright runs through a duct. Refused, with the reason, when it does not fit.',
    args: args(['ref', 'at', 'ru'], {ref: {type: 'string', minLength: 1, description: 'The part, as the catalogue lists it (its ref); it stands beside the rack.'},
      cfg: {type: 'string', description: "Which of the part's configurations; its default when left out."},
      at: AT, ru: BOTTOM, between: BETWEEN, label: {type: 'string', description: 'The name shown on the drawing; its model when left out.'}, as: AS})},
  'zerou.update': {run: zeroUUpdate, description: 'Move a part beside the rack to another upright or U, say whether it stands between racks, or rename it.',
    args: args(['id'], {id: ID('part beside the rack'), at: AT, ru: BOTTOM, between: BETWEEN,
      label: {type: 'string', description: 'The name shown on the drawing.'},
      swaps: {type: 'object', description: 'Every slot path to the part ref seated there, replacing the whole map.'},
      fields: {type: 'object', description: 'Every part path to its settings ({key: value}), replacing the whole map.'}})},
  'zerou.hang': {run: zeroUHang, description: 'Hang a part beside the rack (a zero-U PDU) on brackets placed there, or take it off them. Hung, it stands where the brackets hold it, and moves when one moves. Refused, with the distance, when its mount points do not meet their slots.',
    args: args(['id', 'on'], {id: ID('part beside the rack'),
      on: {type: ['array', 'null'], minItems: 1, description: 'The ids of the brackets that hold it, or null to take it off them.',
        items: {type: 'string', minLength: 1, description: 'A bracket id, or "@name" from earlier in this batch.'}}})},
  'state.set': {run: stateSet, description: 'Set what one part of a placed device or of a part beside the rack is, such as a status lamp lit, a port lamp up, a PSU or fan lamp ok, or an outlet of a PDU on or off; null clears it. `inspect` of the device lists every path it can set and what each can be (`settable`). Refused, with what the device does declare, when the path or the state is not one of them.',
    args: args(['id', 'path', 'state'], {id: ID('device or part beside the rack'),
      path: {type: 'string', minLength: 1, description: 'The part, by its path on the device, as `inspect` lists it under settable (e.g. led-sys, led-port-3, outlet-a1).'},
      state: {type: ['string', 'null'], minLength: 1, description: 'The state name, as the part declares it (e.g. on, off); null to clear.'}})},
  'readings.set': {run: readingsSet, description: 'Store readings taken from a device or a part beside the rack, with where they came from and when; null clears them.',
    args: args(['id', 'readings'], {id: ID('device or part beside the rack'),
      readings: {type: ['object', 'null'], description: '{source, at, values}: where they came from, an RFC 3339 time, and part path to {current-a, power-w, energy-kwh}; null to clear.'}})},
  'display.set': {run: displaySet, description: 'Set what a display of a placed device or of a part beside the rack shows: text (lines, cut to its columns and rows), digits (a segment display) or an image (fitted to the window; a GIF shows its first frame); null clears it. Refused, with the displays it has, when the path is no display or the display cannot show that. The displays query lists them.',
    args: args(['id', 'path', 'content'], {id: ID('device or part beside the rack'),
      path: {type: 'string', minLength: 1, description: 'The display, by its path as the displays query lists it (e.g. network-module/module/lcd).'},
      content: {type: ['object', 'null'], additionalProperties: false, description: 'One of text, digits or image; null to clear.',
        properties: {text: {type: 'array', items: {type: 'string'}, description: 'The lines of text, for a pixel or character display.'},
                     digits: {type: 'string', description: 'The digits of a segment display: 0 to 9, a to f, a space for blank; right-aligned.'},
                     image: {type: 'string', minLength: 1, description: 'A data URL of an SVG, PNG, JPEG or GIF up to 512 KiB, or a library asset path.'}}}})},
  'zerou.remove': {run: zeroURemove, description: 'Take a part away from beside the rack. Its cables (the cords on a PDU\'s outlets) are kept as loose ends, or removed with it.',
    args: args(['id'], {id: ID('part beside the rack'), cables: {enum: ['keep', 'remove'], description: 'keep its cables as loose ends, or remove them; keep when left out.'}})},
  'cable.add': {run: cableAdd, description: 'Run a cable between two free ports. Refused when a port already has a cable or a device is gone.',
    args: args(['a', 'b'], {a: END, b: END, ...CABLE_FIELDS, as: AS})},
  'cable.update': {run: cableUpdate, description: "Change a cable's type, purpose, label, length or color, or move either end to another port. A moved end keeps the cable's id and everything else about it; refused when the new port already has a cable.",
    args: args(['id'], {id: ID('cable'), a: {...END, description: 'Move end A to this port; left where it is when left out.'},
      b: {...END, description: 'Move end B to this port; left where it is when left out.'}, ...CABLE_FIELDS, straps: CABLE_STRAPS})},
  'cable.remove': {run: cableRemove, description: 'Delete a cable.', args: args(['id'], {id: ID('cable')})},
  'cable.route': {run: cableRoute, description: 'Route a cable by hand through the waypoints given, in order. Its routed length follows. A waypoint may name a part beside the rack: its duct (the lane run through it) or a window such as pass-through-2. A pathway may be named as the route summary says it: "ring 3", "left end ring", "front-duct" for duct. Refused for a pathway or gutter the rack lacks; the refusal lists what exists.',
    args: args(['id', 'route'], {id: ID('cable'),
      route: {type: 'array', description: 'In order: {item, via} for a pathway on a device or a part beside the rack (its duct, a window), {lane, ru} for a gutter at a U.',
        items: WAYPOINT},
      summary: SUMMARY})},
  'cable.slack': {run: cableSlack, description: 'Say where the spare length of a cable is stored: in a finger duct its route uses (a horizontal manager, a vertical manager beside the rack, a rack-face bracket), on a tray it rests on, or at one of its ends. A ring, a pass-through and a pathway off its route hold none. With no value the place takes what is left. A duct is counted against its capacity, stated or estimated. Refused, with where spare can go, for a place that cannot hold it, for more spare than it has, and on a short cable.',
    args: args(['id', 'at'], {id: ID('cable'),
      at: {type: 'object', additionalProperties: false, description: 'The place: {item, via} for a duct or a tray on a device or on a part beside the rack, or {end} for an end of the cable.',
        properties: {item: {type: 'string', minLength: 1, description: 'The device or the part beside the rack the duct or tray is on, with via.'},
                     via: {type: 'string', minLength: 1, description: 'The duct or tray on it, with item: duct, front-duct, rear-duct, duct-rear or a tray id.'},
                     end: {enum: ['a', 'b'], description: 'The end of the cable the spare is left at: a or b.'}}},
      value: {type: 'number', exclusiveMinimum: 0, description: 'How much is stored there, above 0; the rest when left out.'},
      unit: {enum: ['m', 'ft'], description: 'Metres (m) or feet (ft); m when left out.'},
      form: {enum: FORMS, description: 'How it is stored: coil, serpentine or spool (a tray only); a coil on a tray and a loop in a duct when left out.'}})},
  'cable.slack.clear': {run: cableSlackClear, description: 'Take back where the spare of a cable is stored: one place, or with no place all of them, so that nothing is said of it.',
    args: args(['id'], {id: ID('cable'),
      at: {type: 'object', additionalProperties: false, description: 'The place to clear: {item, via} or {end}; all of them when left out.',
        properties: {item: {type: 'string', minLength: 1, description: 'The device the tray is on, with via.'},
                     via: {type: 'string', minLength: 1, description: 'The tray on that device, with item.'},
                     end: {enum: ['a', 'b'], description: 'The end of the cable: a or b.'}}}})},
  'cable.lay': {run: cableLay, description: 'Pin how a cable lies in one pathway: which face of a tray it lies on, and its place across the pathway. null unpins either; a key left out is kept. The face is acted on by the routes; the position is kept for when lay order is built.',
    args: args(['id', 'at'], {id: ID('cable'),
      at: {type: 'object', required: ['item', 'via'], additionalProperties: false, description: 'The pathway: {item, via}, a tray, ring or duct on a device.',
        properties: {item: {type: 'string', minLength: 1, description: 'The device the pathway is on.'},
                     via: {type: 'string', minLength: 1, description: 'The pathway on that device.'}}},
      position: {type: ['integer', 'null'], minimum: 1, description: 'Its place across the pathway, counted from 1; null to unpin it.'},
      face: {enum: ['top', 'underside', null], description: 'The face of a tray it lies on, as the part names its own: top or underside; null unpins it. Refused on a ring or a duct.'}})},
  'cable.route.reset': {run: cableRouteReset, description: 'Drop a hand-made route; the cable takes its own route again.',
    args: args(['id'], {id: ID('cable'), summary: SUMMARY})},
  'bundle.create': {run: bundleCreate, description: 'Bundle two or more cables sharing part of their route. It runs where they run together, unless given a route. A cable whose own route does not meet a given route joins and leaves it at the points nearest its two ports. Refused for a bundled cable.',
    args: args(['cables'], {cables: BUNDLE_CABLES(2, 'The cables to bundle, two or more, by id, in combing order.'),
      label: {type: 'string', description: 'The name on its tags; "Bundle <number>" is used when there is none. Empty when left out.'},
      number: {type: 'integer', minimum: 1, description: 'Its number, unique in the rack; one past the highest in use when left out.'},
      route: {type: 'array', description: 'Its route by hand, in order: {item, via} or {lane, ru}. Worked out from where its cables run together when left out.',
        items: WAYPOINT},
      straps: STRAPS, as: AS})},
  'bundle.add': {run: bundleAdd, description: 'Add cables to a bundle. A cable already in it rides the whole bundle again. Refused for a cable in another bundle.',
    args: args(['id', 'cables'], {id: ID('bundle'), cables: BUNDLE_CABLES(1, 'The cables to add, by id.')})},
  'bundle.peel': {run: bundlePeel, description: 'Take a cable out of a bundle. With at, it stays bundled up to that waypoint, then runs on its own to one end.',
    args: args(['id', 'cable'], {id: ID('bundle'), cable: ID('cable'),
      at: {...WAYPOINT, description: 'A waypoint on the bundle\'s route where the cable leaves it; when left out, the cable leaves the bundle altogether.'},
      end: {enum: ['a', 'b'], description: 'The end it heads for after it leaves at that waypoint; the end whose port is nearer when left out.'}})},
  'bundle.update': {run: bundleUpdate, description: "Change a bundle's label, number or strap spacing, or route it by hand. A cable whose own route does not meet a route given by hand joins and leaves it at the points nearest its two ports. A route of null works the route out again from its cables.",
    args: args(['id'], {id: ID('bundle'), label: {type: 'string', description: 'The name on its tags; empty for "Bundle <number>". Kept when left out.'},
      number: {type: 'integer', minimum: 1, description: 'Its number, unique in the rack. Kept when left out.'},
      straps: STRAPS,
      route: {type: ['array', 'null'], description: 'Its route by hand, in order, or null to work it out again from its cables. Kept when left out.', items: WAYPOINT},
      summary: SUMMARY})},
  'bundle.remove': {run: bundleRemove, description: 'Dissolve a bundle. Its cables are kept and follow their own routes again.',
    args: args(['id'], {id: ID('bundle')})},
  'lengths.routed': {run: lengthsRouted, step: false, system: true,
    description: 'Store the routed lengths the caller measured. Not an undo step; sent by the caller.',
    args: args(['routeCtx'], {routeCtx: {type: 'object', description: 'The routing context the last render measured with (route-context.js routeFacts().ctx).'}})},
};

// ── apply ───────────────────────────────────────────────────────────────
const typeWord = s => {
  if (s.enum) return `one of ${s.enum.filter(v => v !== null && v !== '').join(', ')}`;
  const t = [].concat(s.type ?? []).find(x => x !== 'null');
  return {integer: `a whole number${s.minimum != null ? ` from ${s.minimum}` : ''}${s.maximum != null ? ` to ${s.maximum}` : ''}`,
          number: `a number${s.exclusiveMinimum === 0 ? ' above 0' : ''}${s.multipleOf != null ? ` in steps of ${s.multipleOf}` : ''}` +
                  `${s.multipleOf != null && s.minimum != null ? ` from ${s.minimum}` : ''}`, string: 'some text',
          boolean: 'true or false', object: 'an object', array: 'a list'}[t] || 'a value';
};
function sentence(op, e) {
  if (e.keyword === 'required' || e.keyword === 'dependentRequired') {
    const s = e.schema.properties?.[e.missing] || {};
    return `${op} needs ${[...e.path, e.missing].join('.')}, ${typeWord(s)}.`;
  }
  if (e.keyword === 'additionalProperties') return `${op} does not take ${e.path.join('.')}.`;
  if (e.keyword === 'minItems') return `${op} needs ${e.path.join('.')} to list at least ${e.schema.minItems}.`;
  return `${op} needs ${e.path.join('.')}, ${typeWord(e.schema)}.`;
}

// Only ids are names: `id`, `cable` and each of `cables`, the item of a cable
// end, and the item of each waypoint of a `route` and of `at`. So one batch can
// place a manager, add cables and bundle them through its rings. A label that
// reads "@srv" is a label.
function resolve(cmd, bound) {
  const name = v => (typeof v === 'string' && v.startsWith('@') ? v.slice(1) : null);
  const swap = v => {
    const n = name(v);
    if (n == null) return {v};
    return bound.has(n) ? {v: bound.get(n)} : {error: `Nothing earlier in this batch is called ${n}.`};
  };
  const out = {...cmd};
  for (const k of ['id', 'cable']) if (k in out) { const s = swap(out[k]); if (s.error) return s; out[k] = s.v; }
  for (const k of ['cables', 'on']) if (Array.isArray(out[k])) {
    const list = [];
    for (const v of out[k]) { const s = swap(v); if (s.error) return s; list.push(s.v); }
    out[k] = list;
  }
  for (const k of ['a', 'b', 'at']) if (out[k]?.item != null) {
    const s = swap(out[k].item); if (s.error) return s; out[k] = {...out[k], item: s.v};
  }
  if (Array.isArray(out.route)) {
    const list = [];
    for (const w of out.route) {
      if (w?.item == null) { list.push(w); continue; }
      const s = swap(w.item); if (s.error) return s; list.push({...w, item: s.v});
    }
    out.route = list;
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
  // WHAT THIS RACK SAYS THAT THE LIBRARY HAS REPLACED, as the file has it
  const said = ctx?.redirects?.size ? rewriteRack(rack, ctx.redirects).changed : [];
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
  // THE FIRST EDIT THAT LANDS WRITES THE NEW REFS (kit/redirects.js), in the
  // same step, so one undo takes both back; a plain load, a no-op, a refused
  // edit and a command that is no step leave the rack as the file has it.
  if (step && ctx?.redirects?.size) {
    const out = rewriteRack(cur, ctx.redirects);
    if (out.changed.length) {
      cur = out.rack;
      const there = new Set([...cur.items, ...(cur.zeroU || [])].map(i => i.id));
      const all = said.filter(a => there.has(a.item));
      for (const c of out.changed) if (!all.some(a => a.item === c.item && a.path === c.path && a.from === c.from)) all.push(c);
      findings.unshift(note(rewroteText(all)));
    } else if (said.length) {
      const there = new Set([...cur.items, ...(cur.zeroU || [])].map(i => i.id));
      const still = said.filter(a => there.has(a.item));
      if (still.length) findings.unshift(note(rewroteText(still)));
    }
  }
  return {rack: cur, summary: summaries.join(' '), findings, created: {...created, ids}, noop: cur === rack, step};
}
