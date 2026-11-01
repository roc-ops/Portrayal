// kit/rack/queries.js
// QUESTIONS ABOUT A RACK, for an agent deciding what to send and
// for a page that wants to ask before it acts. Pure; the two that read faces
// are handed their readers in `ctx`, since reading a face needs the network and
// a DOMParser, which this module never touches.

import {fits, isRackFace, heightOf, railOf, isZeroUPart, zeroUUnits, itemUnits, spanText, isHeld, isRackMount, isQuarter, zeroUTouched, spanOf} from './fit.js';
import {placement, managersOf} from './managers.js';
import {uLabel, zeroUOf, zeroUBottom, firstU, holderOf, rollOf, uText} from './model.js';
import {whereText, carriesLane} from './zero-u.js';
import {portFree, endKey, proposeMedia, mismatch, endName, carriedU, portPathOf, matches, lengthText, isElementId, addressFor, portLabel,
        takesCableEnd, receptacleOf, endKind, connectorName, endPlug, couplerRole} from './cable-rules.js';
import {seatedPort, settleEnds, shownEnv, cableEndPaths, zeroUEnds, backEnds, dcPortsOf, dcReader, dcEntryOf, dcCovered} from './ports.js';
import {zeroUById, zeroUBottomMm} from './model.js';
import {RU} from './rails.js';
import {configFacts} from './catalog.js';
import {settableOf} from './states.js';
import {waypointLanesOf, pathwaysOf, resolveRoute, pathLength, routePath, routeText, bendFindingsOf, coverFindingsOf, ringFindingsOf, ductsThrough,
  zeroUPathways, pathwaysAt, windowsOf} from './route.js';
import {catalogEntries} from './catalog.js';
import {slackOf, slackFindings, sparePlaces, holdsSpare, spareExports, trayText, mText, labelOf} from './slack.js';
import {GONE, CABLE_GONE, ZERO_GONE, BUNDLE_GONE} from './commands.js';
import {bundlesOf, bundleName} from './model.js';
import {bundleCheck, bundleOfCable, membersText, spacingText, strapSpacing, straps as strapsOf, trunkLength, straightText, fewText,
        layoutOf, isTie, ridersOf, waypointText} from './bundles.js';
import {slotEnv, slotTree, partName, partOf, resolverFor} from './slots.js';
import {auditRack, readAsTexts, unknownTexts} from '../redirects.js';
import {fieldRows} from '../fields.js';
import {displayList} from './displays.js';

export function fitsAt(rack, {ref, face, ru}, {chassisOf}) {
  const spot = isRackFace(chassisOf(ref)) ? placement(rack, {face, ru}, chassisOf) : {face, ru};
  return fits(rack, {ref, ...spot}, chassisOf);
}

// Every position the device fits at, in steps of 0.5: whole positions for a
// device of a whole number of units (fit refuses it a half), and both for any
// other.
export const freeUs = (rack, {ref, face}, ctx) =>
  Array.from({length: rack.frame.heightRU * 2}, (_, k) => 1 + k / 2).filter(ru => fitsAt(rack, {ref, face, ru}, ctx).ok);

// `text` matches the ref, maker and model, and what the device IS: its kind
// ("patch panel", "switch", "cable manager", from rack.json) and its family.
export function catalog(devices, {text, ru, family, mount, kind} = {}) {
  const t = text ? String(text).toLowerCase() : null;
  return catalogEntries(devices)
    .filter(e => !t || [e.name, e.manufacturer, e.model, e.kind, e.family].some(v => String(v ?? '').toLowerCase().includes(t)))
    .filter(e => ru == null || e.ru === ru)
    .filter(e => family == null || e.family === family)
    .filter(e => mount == null || (e.mount || 'rack') === mount)
    .filter(e => kind == null || e.kind === kind)
    .map(e => ({ref: e.name, manufacturer: e.manufacturer ?? null, model: e.model ?? null, ru: e.ru,
                mount: e.mount || 'rack', family: e.family ?? null, kind: e.kind ?? null, configs: e.configs ?? [], default: e.default ?? null}));
}

// A SHORT READING OF THE RACK for an agent: the ids it needs to address
// anything, in about 1.5K characters (WebMCP's guidance for tool output). A
// long rack loses its labels first, then its tail, and says so. The first line
// always gives the totals. A WINDOW (`section`, `offset`, `limit`) reads one
// stretch of a long rack in full instead, each line with the device's ref and
// configuration or the cable's purpose and length. A window is agent-sized
// too: `limit` defaults to WINDOW and is capped at MAX_WINDOW lines a section.
// A section other than `items` or `cables`, or an `offset` or `limit` that is
// not a whole number (from 0, and from 1), is refused as {error}.
const LIMIT = 1500;
export const WINDOW = 20;
export const MAX_WINDOW = 50;
const SECTIONS = ['items', 'zeroU', 'cables', 'bundles'];
const count = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const sideOf = e => `${e.item}/${e.path}${e.view === 'rear' ? ' (rear)' : ''}`;

// One line for a bundle (#921): its members, its size and warnings when the
// routes are known (`ctx.route`), its straps.
function bundleLine(rack, b, ctx) {
  const ids = b.members.map(m => m.cable);
  const head = `${b.id} ${bundleName(b)}: ${count(ids.length, 'cable')}${ids.length ? ` (${membersText(ids)})` : ''}`;
  // a tie (#1017): one strap at its one point; with fewer than two riding, none, and the reason
  let spacing = spacingText(strapSpacing(b));
  if (isTie(b)) spacing = `a tie at ${waypointText(rack, b.route[0])}`;
  if (ids.length < 2) return `${head}, not drawn.`;
  if (!ctx?.route) return `${head}, ${spacing}, not checked.`;
  const r = bundleCheck(rack, b, ctx);
  if (!r.checked) return `${head}, ${spacing}, not checked.`;
  // fewer than two riding: no strap (#1021), said after a tie's place and in place of a trunk's spacing
  if (r.layout && ridersOf(rack, r.layout).length < 2) {
    if (isTie(b)) spacing += ' with no strap, since fewer than two cables ride it';
    else if (spacing !== 'no straps') spacing = 'no strap, since fewer than two cables ride it';
  }
  const size = r.size ? `about ${Math.round(r.size.max_mm)} mm, ` : '';
  return `${head}, ${size}${spacing}, ${r.warnings.length ? count(r.warnings.length, 'warning') : 'no warnings'}.`;
}

// ONE LINE OF TOTALS for what the routes find, or null when there is nothing,
// or when the routes cannot be read (no `ctx.route`, or a reader throws):
// "Findings: 2 cables cross a body; 3 cables have a tight bend (the worst c9,
// 10.8 mm short); 9 cables cross in front of other ports (the most c7, 5
// ports; only ports that hold a cable were judged)." Each part is there only
// when it counts something: the cables whose path still crosses a body
// (#949), those with a corner short of their bend radius and the cable
// shortest of it (#973, #1007), and those with a span in front of other
// ports and the cable that covers most (#1013), with what was judged when
// the page listed no ports (`ctx.route.portBoxesOf`). P-0018 adds the cables
// that would enter and leave a ring by one face ("3 cables enter and leave a
// ring by one face (c1, c2, c3)", up to three named) and the cords shorter
// than their route needs (a pinned length under the need, the worst named
// with its shortfall): a cable counts once, as one row of the page's Warnings
// panel does. Each cable's path is read once (slackOf reads the same kept path).
function findingsText(rack, ctx) {
  if (!ctx?.route) return null;
  let bodies = 0, bends = 0, covers = 0, worst = null, most = null, cabled = false;
  const rings = [], cords = [];
  try {
    for (const c of rack.cables || []) {
      const path = routePath(rack, c, ctx.route);
      if (!path) continue;
      if (path.crossings?.length) bodies++;
      // a ring a route would enter and leave by one face: the cable counts once, as a row of the Warnings panel does
      if (path.findings?.length) rings.push(c.id);
      // a cord shorter than its route needs (the pinned length under the need), the shortfall in metres
      if (c.length) {
        const s = slackOf(rack, c, ctx.route);
        if (s?.short) cords.push({id: c.id, short: s.spare.need_m - s.spare.stock_m});
      }
      if (path.bends?.length) {
        bends++;
        const short = Math.max(...path.bends.map(f => f.short_mm));
        if (!worst || short > worst.short) worst = {id: c.id, short};
      }
      if (path.covers?.length) {
        covers++;
        if (path.covers.some(f => f.judged !== 'all')) cabled = true;
        if (!most || path.covers.length > most.n) most = {id: c.id, n: path.covers.length};
      }
    }
  } catch { return null; }
  const worstCord = cords.reduce((m, x) => (!m || x.short > m.short ? x : m), null);
  const parts = [
    ...(bodies ? [`${count(bodies, 'cable')} cross${bodies === 1 ? 'es' : ''} a body`] : []),
    ...(rings.length ? [`${count(rings.length, 'cable')} ${rings.length === 1 ? 'enters' : 'enter'} and ${rings.length === 1 ? 'leaves' : 'leave'} a ring by one face (${
      rings.length > 3 ? `${rings.slice(0, 3).join(', ')} and ${rings.length - 3} more` : rings.join(', ')})`] : []),
    ...(bends ?[`${count(bends, 'cable')} ${bends === 1 ? 'has' : 'have'} a tight bend (${bends === 1 ? '' : 'the worst '}${worst.id}, ${worst.short} mm short)`] : []),
    ...(covers ? [`${count(covers, 'cable')} cross${covers === 1 ? 'es' : ''} in front of other ports (${covers === 1 ? '' : 'the most '}${most.id}, ${count(most.n, 'port')}${cabled ? '; only ports that hold a cable were judged' : ''})`] : []),
    ...(cords.length ? [`${count(cords.length, 'cord')} ${cords.length === 1 ? 'is' : 'are'} shorter than ${cords.length === 1 ? 'its' : 'their'} route needs (${cords.length === 1 ? '' : 'the worst '}${worstCord.id}, ${mText(worstCord.short)} short)`] : [])];
  return parts.length ? `Findings: ${parts.join('; ')}.` : null;
}

export function describe(rack, ctx, {section, offset, limit} = {}) {
  const {chassisOf} = ctx;
  const f = rack.frame;
  const holes = f.holes.style === 'tapped' ? `tapped${f.holes.thread ? ` ${f.holes.thread}` : ''} holes` : `${f.holes.style === 'round' ? 'round' : 'square'} holes`;
  const items = [...rack.items].sort((a, b) => b.ru - a.ru);
  const cables = rack.cables || [];
  // the parts beside the rack (#926), top down; counted only when there are any
  const beside = [...zeroUOf(rack)].sort((a, b) => zeroUBottom(b) - zeroUBottom(a));
  // the bundles (#921), in the rack's order; counted only when there are any
  const bundles = bundlesOf(rack);
  const totals = `${rack.name} (${rack.id}): ${count(items.length, 'item')}, ` +
    `${beside.length ? `${count(beside.length, 'part')} beside the rack, ` : ''}${count(cables.length, 'cable')}` +
    `${bundles.length ? `, ${count(bundles.length, 'bundle')}` : ''}.`;
  // the optional frame keys, each said only when the frame has it
  // a setback as fit says it: back into the rack, or forward of the rail
  const setText = s => `set ${s < 0 ? 'forward' : 'back'} ${Math.abs(s)} mm`;
  const optionText = o => (typeof o === 'string' ? o : o && typeof o === 'object' && typeof o.id === 'string' ? o.id : JSON.stringify(o));
  const options = f.options == null ? '' : ` Options: ${(Array.isArray(f.options) ? f.options : [f.options]).map(optionText).join(', ') || 'none'}.`;
  const frameLine = `${f.heightRU}U ${f.kind}, ${holes}, numbered ${f.numbering}${firstU(f) !== 1 ? ` from U${firstU(f)}` : ''}.`
    + (typeof f.setback === 'number' ? ` Faceplates ${setText(f.setback)}.` : '') + options;
  // ONE LINE OF TOTALS FOR THE FINDINGS (#949), when routes can be read and
  // there is any: an agent that only describes the rack still sees them.
  // and where each cable's spare is stored in a duct or on a tray, on its line
  let spare = '', byCable = new Map();
  if (ctx?.route) { try { const x = spareExports(rack, ctx.route); spare = x.line; byCable = x.byCable; } catch { spare = ''; } }
  const storedIn = c => (byCable.get(c.id)?.entries || []).filter(e => e.item && e.ok && e.metres > 0.005)
    .map(e => `${Math.round(e.metres * 100) / 100} m spare in ${trayText(rack, e)}`);
  const findingsLine = findingsText(rack, ctx);
  const span = i => spanText(f, i, chassisOf);
  // `full` is a window's line: the ref and configuration, the purpose and length
  const holds = i => rack.items.filter(o => holderOf(o) === i.id).map(o => o.id);
  const item = (i, short, full = false) => {
    const ms = managersOf(rack, i.id).map(m => m.id);
    const rail = railOf(i, chassisOf);
    // a span that names a half is a phrase, set off from the label by commas
    const where = span(i), plain = where.startsWith('U');
    const c = chassisOf(i.ref);
    return [`${i.id}${short ? '' : ` ${i.label}`}${plain ? ' ' : ', '}${where}${plain ? ' ' : ', '}${i.face}${rail ? ` ${rail} rail` : ''}${i.turned ? ' turned' : ''}${rollOf(i) ? ` rolled ${rollOf(i)}` : ''}`,
            ...(full ? [`${i.ref} ${i.cfg || '(no configuration)'}`] : []),
            ...(i.on ? [`on ${i.on} unit ${i.unit}`] : []), ...(ms.length ? [`carries ${ms.join(' ')}`] : []),
            ...(typeof i.setback === 'number' && !isRackFace(c) && !isZeroUPart(c) ? [setText(i.setback)] : []),
            ...(holderOf(i) != null ? [`held by ${holderOf(i)}${isHeld(i, chassisOf) ? ', not checked' : ''}`] : []),
            ...(holds(i).length ? [`holds ${holds(i).join(' ')}`] : [])].join(', ');
  };
  const part = (z, short, full = false) => [`${z.id}${short ? '' : ` ${z.label}`} ${whereText(rack, z, chassisOf)}`,
    ...(full ? [`${z.ref} ${z.cfg || '(no configuration)'}`] : [])].join(', ');
  // its own colour, when it states one, after its media
  const cable = (c, full = false) => [`${c.id}: ${sideOf(c.a)} <-> ${sideOf(c.b)}`, ...(c.media ? [c.media] : []),
    ...(typeof c.color === 'string' && c.color ? [c.color] : []),
    ...(full && c.purpose ? [c.purpose] : []), ...(full && lengthText(c.length) ? [lengthText(c.length)] : []), ...storedIn(c)].join(', ');

  if (section != null || offset != null || limit != null) {
    if (section != null && !SECTIONS.includes(section)) return {error: `There is no section ${section}. Ask for items, zeroU, cables or bundles, or leave it out for all of them.`};
    if (offset != null && !(Number.isInteger(offset) && offset >= 0)) return {error: 'An offset is a whole number from 0.'};
    if (limit != null && !(Number.isInteger(limit) && limit >= 1)) return {error: `A limit is a whole number from 1 to ${MAX_WINDOW}.`};
    const from = offset ?? 0;
    const n = Math.min(limit ?? WINDOW, MAX_WINDOW);
    const parts = [['items', 'Items', items, i => item(i, false, true)], ['zeroU', 'Beside the rack', beside, z => part(z, false, true)],
      ['cables', 'Cables', cables, c => cable(c, true)], ['bundles', 'Bundles', bundles, b => bundleLine(rack, b, ctx)]]
      .filter(([key]) => (section == null ? (key !== 'zeroU' || beside.length) && (key !== 'bundles' || bundles.length) : section === key));
    const shown = [], body = [];
    for (const [key, title, list, line] of parts) {
      if (!list.length) shown.push(`No ${key === 'zeroU' ? 'parts beside the rack' : title.toLowerCase()}.`);
      else if (from >= list.length) shown.push(`${title} past the end: there are ${list.length}.`);
      else {
        shown.push(`${title} ${from + 1}-${Math.min(list.length, from + n)} shown.`);
        body.push(`${title}:`, ...list.slice(from, from + n).map(line));
      }
    }
    return [`${totals} ${shown.join(' ')}`, frameLine, ...(findingsLine ? [findingsLine] : []), ...(spare ? [spare] : []), ...body].join('\n');
  }

  const bundleLines = bundles.map(b => bundleLine(rack, b, ctx));
  const build = (short, nItems, nCables, nBundles) => {
    const lines = [totals, frameLine, ...(findingsLine ? [findingsLine] : []), ...(spare ? [spare] : []), items.length ? 'Items:' : 'No items.', ...items.slice(0, nItems).map(i => item(i, short)),
                   ...(beside.length ? ['Beside the rack:', ...beside.map(z => part(z, short))] : []),
                   ...(cables.length ? ['Cables:', ...cables.slice(0, nCables).map(c => cable(c))] : []),
                   ...(bundles.length ? ['Bundles:', ...bundleLines.slice(0, nBundles)] : [])];
    const more = (items.length - nItems) + (cables.length - nCables) + (bundles.length - nBundles);
    if (short) lines.push(more ? `Shortened: labels left out, and ${more} more not listed; ask for them by id.` : 'Shortened: labels left out.');
    return lines.join('\n');
  };
  let out = build(false, items.length, cables.length, bundles.length);
  if (out.length <= LIMIT) return out;
  // the longest list loses its tail first; bundles, whose lines are longest, on a tie
  let ni = items.length, nc = cables.length, nb = bundles.length;
  out = build(true, ni, nc, nb);
  while (out.length > LIMIT && (ni || nc || nb)) {
    if (nb && nb >= nc && nb >= ni) nb--; else if (nc >= ni && nc) nc--; else ni--;
    out = build(true, ni, nc, nb);
  }
  return out;
}

// The ports of a device with no cable, on either of its panels, each by its
// ADDRESS: {path, view}. A port on the back of what a bay holds is
// `<bay>/module/<part>` on the panel that shows the back (zones.js reads a
// projected part's path so). An element id is never offered: a reader that
// hands one in has it turned into the address it stands for where the
// catalogue (`slotsOf`, `compByRef`) knows a port there, and dropped otherwise.
//
// THE SLOTS A CABLE LANDS ON (cable-rules.js cableLandsOn: a power inlet, an
// outlet, a DC terminal, a ground stud) are listed where the reader hands
// them in (zones.js readSvg `ends`) and the catalogue has the slot. Each
// carries, beside what a port carries:
//   kind       'power', 'ground', or 'other' for a slot whose part says neither
//   connector  the end for a person: "C13 outlet", "C20 inlet"
//   plug       the plug or lug a cable is given there (endPlug)
//   of, first  where the slot is one of several under one part that is no
//              slot itself (the screws of a DC terminal), that part's path,
//              and `first: true` on the one to take: a feed is one cable, and
//              it lands on the first free screw of its terminal. A part that
//              states a DC port has neither (below).
// A PORT OF CLASS `port` IS LISTED EXACTLY AS BEFORE, with none of those keys.
//
// A DC PORT IS ONE ROW (docs/dc-power-design.md section 8), on its panel, with
// `dc` {direction, voltage, rating-a, awg, side, poles: [{role, path, plug}]}
// and the words and plug of the port (ports.js dcPortsOf). Its pole slots and a
// points port's connector slot are not rows of their own while it is free. A
// port is free when no cable is on it, on a pole or on its connector; a PARTLY
// USED port is no row, and each free pole is a row of its own for a single
// conductor, with `dc.pole` {port, role}. A DC row has no `of` or `first`.
// `kinds` narrows the list: any of 'data' (the ports), 'power', 'ground',
// 'other'. A picker for a data cable asks for ['data'].
// THE CATALOGUE'S ENDS TOO (P-0019): a slot that takes a cable end on a panel
// the item's configuration shows (ports.js cableEndPaths: a supply's C14 or
// C20 inlet, a DC terminal's screws, a ground stud) is listed whether or not
// the reader handed it in, so an agent is offered a device's power inlets
// beside its data ports. What it is comes from the part it is one piece of
// (a supply), else from the coupler it is (cable-rules.js couplerRole).
//
// A PART BESIDE THE RACK (a zero-U PDU, P-0019) has no panel a reader reads:
// its ends are its own connector slots, from the catalogue alone (ports.js
// zeroUEnds), each with `type` (C13, C19, C39), `name` (A2, as the device
// names the outlet), and `u`, the unit it stands at as the rack numbers them.
// `type` narrows the list to one coupler, on any part; `near`, a unit as the
// rack numbers them, orders a part's outlets nearest it first: "the free C39
// outlets on PDU-A nearest U35" is {kinds: ['power'], type: 'C39', near: 35}.
const FREE_KINDS = ['data', 'power', 'ground', 'other'];
const natural = new Intl.Collator('en', {numeric: true});
export async function freePorts(rack, itemId, ctx, {kinds = null, type = null, near = null} = {}) {
  const {portsOf, slotsOf, compByRef, redirects = null} = ctx;
  const item = rack.items.find(i => i.id === itemId);
  const z = item ? null : zeroUById(rack, itemId);
  if (!item && !z) return {error: GONE};
  if (kinds != null && !(Array.isArray(kinds) && kinds.every(k => FREE_KINDS.includes(k))))
    return {error: `kinds is a list of ${FREE_KINDS.join(', ')}.`};
  if (type != null && !(typeof type === 'string' && type)) return {error: 'type is a coupler, such as C13, C19 or C39.'};
  if (near != null && !(typeof near === 'number' && Number.isFinite(near))) return {error: 'near is a unit, as the rack numbers them (e.g. 35).'};
  const want = k => kinds == null || kinds.includes(k);
  const ofType = e => type == null || String(e.type ?? '').toLowerCase() === type.toLowerCase();
  if (z) return zeroUFree(rack, z, ctx, {want, ofType, near});
  const out = [], seen = new Set();
  // DC PORTS: the slots a port takes in its place are not rows of their own, and a cable is counted across them
  const dcCtx = {slotsOf, compByRef, redirects}, dc = dcReader(rack, dcCtx), covered = dcCovered(item, dcCtx);
  // the catalogue's slots of this device, read once and only when a slot is asked about
  let seats;
  const seatAt = path => {
    if (seats === undefined) {
      const slots = typeof slotsOf === 'function' && typeof compByRef === 'function' ? slotsOf(item.ref) : null;
      // the panels the item's configuration shows, and no other build's (ports.js shownEnv)
      seats = slots && !slots.error ? resolverFor(shownEnv(item, slots, compByRef, redirects), item.swaps || {}) : null;
    }
    const slot = seats?.entryAt(path) ?? null;
    return slot && takesCableEnd(slot, compByRef) ? slot : null;
  };
  for (const view of ['front', 'rear']) {
    for (const p of await portsOf(item, view)) {
      if (p.cls !== 'port') {
        // a slot a cable lands on: only where the reader says so and the catalogue has it
        const slot = p.end === true && !isElementId(p.path) && !covered.has(p.path) && (seen.has(`${view}|${p.path}`) ? null : seatAt(p.path));
        if (!slot || (slot.view && slot.view !== view)) continue;
        seen.add(`${view}|${p.path}`);
        // what it is: its own part says, else the part it is one piece of (a terminal's screw)
        let info = receptacleOf(partOf(compByRef, p.ref));
        for (let q = p.path; !info.family && q.lastIndexOf('/') > 0;) {
          q = q.slice(0, q.lastIndexOf('/'));
          info = receptacleOf(partOf(compByRef, seats?.refAt(q)));
        }
        if (!want(endKind(info)) || !portFree(rack, {item: itemId, path: p.path, view}).ok) continue;
        out.push({path: p.path, view, label: portLabel(p.path), media: p.media ?? null, speed: p.speed ?? null,
                  kind: endKind(info), connector: connectorName(slot, info), plug: endPlug(slot, compByRef).plug});
        continue;
      }
      if (!want('data')) continue;
      let path = p.path;
      if (isElementId(path)) {
        const to = addressFor(path);
        if ((to.view ?? view) !== view || !seatedPort(item, {path: to.path, view}, {slotsOf, compByRef})?.port) continue;
        path = to.path;
      }
      if (seen.has(`${view}|${path}`)) continue;
      seen.add(`${view}|${path}`);
      if (!portFree(rack, {item: itemId, path, view}).ok) continue;
      out.push({path, view, label: portLabel(path), media: p.media ?? null, speed: p.speed ?? null});
    }
    // the far ends of a passive panel's adapters, which no panel of the device
    // draws when the panel sits in a drawer (ports.js backEnds)
    if (want('data')) for (const e of backEnds(item, {slotsOf, compByRef, redirects}).filter(x => x.view === view)) {
      if (seen.has(`${view}|${e.path}`) || !portFree(rack, {item: itemId, path: e.path, view}).ok) continue;
      seen.add(`${view}|${e.path}`);
      out.push({path: e.path, view, label: portLabel(e.path), media: e.media ?? null, speed: null});
    }
    // the catalogue's ends the reader did not hand in (above)
    if (!(want('power') || want('ground') || want('other'))) continue;
    for (const e of slotEnds(item, {slotsOf, compByRef, redirects}).filter(x => x.view === view)) {
      if (seen.has(`${view}|${e.path}`)) continue;
      seen.add(`${view}|${e.path}`);
      if (!want(e.kind) || !portFree(rack, {item: itemId, path: e.path, view}, {dc}).ok) continue;
      out.push({path: e.path, view, label: portLabel(e.path), media: null, speed: null, kind: e.kind, connector: e.connector, plug: e.plug,
                ...(e.dc ? {dc: e.dc} : {})});
    }
    // a PARTLY USED slots port: each pole no cable is on is a row, for a single conductor
    if (want('power')) for (const port of dcPortsOf(item, dcCtx)) {
      if (port.kind !== 'slots' || !port.lands || port.view !== view || portFree(rack, {item: itemId, path: port.path, view}, {dc}).ok) continue;
      port.poles.forEach((q, i) => {
        if (!portFree(rack, {item: itemId, path: q.path, view}, {dc}).ok) return;
        const e = dcEntryOf(port, dcCtx, i);
        out.push({path: e.path, view, label: portLabel(e.path), media: null, speed: null, kind: e.kind, connector: e.connector, plug: e.plug, dc: e.dc});
      });
    }
  }
  // SEVERAL SLOTS UNDER ONE PART THAT IS NO SLOT ITSELF: grouped by that part,
  // the first in natural order marked as the one a cable takes. A DC port's own
  // rows are not: a part that states a port has its poles under it already.
  const under = e => { const cut = e.path.lastIndexOf('/'); return e.kind && !e.dc && cut > 0 && !e.path.slice(0, cut).endsWith('/module') ? e.path.slice(0, cut) : null; };
  const groups = new Map();
  for (const e of out) { const g = under(e); if (g) groups.set(`${e.view}|${g}`, [...(groups.get(`${e.view}|${g}`) || []), e]); }
  for (const [key, list] of groups) {
    const first = [...list].sort((a, b) => natural.compare(a.path, b.path))[0];
    for (const e of list) { e.of = key.slice(key.indexOf('|') + 1); if (e === first) e.first = true; }
  }
  // a coupler asked for: an end whose connector is one ("C14 inlet")
  // (a DC row is no coupler)
  return type == null ? out : out.filter(e => !e.dc && e.connector && ofType({type: String(e.connector).split(' ')[0]}));
}
// THE SLOTS OF A RACK ITEM A CABLE LANDS ON, from the catalogue alone (ports.js
// cableEndPaths) that are power or ground ends, front then rear: {path, view,
// kind, connector, plug}. What each is comes from the part it is one piece of
// (a supply says it is an AC inlet), else from the coupler it is; [] without
// the catalogue.
// A DC PORT IS ONE ENTRY, on its panel, with `dc` (ports.js dcEntryOf), after the
// device's other ends; the pole slots under a port and a points port's
// connector slot are not entries of their own.
export function slotEnds(item, {slotsOf, compByRef, redirects = null} = {}) {
  const slots = typeof slotsOf === 'function' && typeof compByRef === 'function' ? slotsOf(item.ref) : null;
  if (!slots || slots.error) return [];
  const seats = resolverFor(shownEnv(item, slots, compByRef, redirects), item.swaps || {});
  const dcCtx = {slotsOf, compByRef, redirects}, covered = dcCovered(item, dcCtx);
  const dcPorts = dcPortsOf(item, dcCtx).filter(q => q.lands && q.view);
  return ['front', 'rear'].flatMap(view => [...cableEndPaths(item, view, {slotsOf, compByRef, redirects}).filter(path => !covered.has(path)).flatMap(path => {
    const slot = seats.entryAt(path);
    if (!slot || !takesCableEnd(slot, compByRef) || (slot.view && slot.view !== view)) return [];
    let info = receptacleOf(null);
    for (let q = path; !info.family && q.lastIndexOf('/') > 0;) {
      q = q.slice(0, q.lastIndexOf('/'));
      info = receptacleOf(partOf(compByRef, seats.refAt(q)));
    }
    if (!info.family && couplerRole(slot.interface)) info = {family: 'power', mode: null, role: couplerRole(slot.interface)};
    // a power or ground end only: a slot whose part says neither (an RJ45
    // jack) is a data port, which the reader of the drawing lists
    if (endKind(info) === 'other') return [];
    return [{path, view, kind: endKind(info), connector: connectorName(slot, info), plug: endPlug(slot, compByRef).plug}];
  }), ...dcPorts.filter(q => q.view === view).map(q => dcEntryOf(q, dcCtx))]);
}
// The rack's unit a slot of a part beside the rack stands in, or null where
// the catalogue does not place it.
const slotRu = (rack, z, e) => (e.y == null ? null
  : Math.min(rack.frame.heightRU, Math.max(1, Math.floor((zeroUBottomMm(z) + e.y) / RU) + 1)));
// The free ends of a part beside the rack (freePorts, above).
function zeroUFree(rack, z, ctx, {want, ofType, near}) {
  const f = rack.frame, names = configFacts(ctx.slotsOf?.(z.ref), z.cfg)?.names || {};
  const ruOf = e => slotRu(rack, z, e);
  // `near` is a unit as the rack numbers them; the rack's own unit for it
  const at = near == null ? null : Array.from({length: f.heightRU}, (_, k) => k + 1).find(ru => uLabel(f, ru) === near) ?? null;
  if (near != null && at == null) return {error: `This rack has no U${near}.`};
  const out = zeroUEnds(z, ctx)
    .filter(e => want(e.kind) && ofType(e) && portFree(rack, {item: z.id, path: e.path, view: e.view}).ok)
    .map(e => { const ru = ruOf(e);
      return {path: e.path, view: e.view, label: names[e.path] ?? portLabel(e.path), media: e.media ?? null, speed: e.speed ?? null, kind: e.kind,
              connector: e.connector, plug: e.plug, type: e.type, u: ru == null ? null : uLabel(f, ru),
              mm: e.y == null ? null : zeroUBottomMm(z) + e.y}; });
  // nearest the middle of that unit first, by the mm between; one not placed last
  const off = e => Math.abs(e.mm - (at - 0.5) * RU);
  if (at != null) out.sort((a, b) => (a.mm == null) - (b.mm == null) || (a.mm == null ? 0 : off(a) - off(b)) || natural.compare(a.path, b.path));
  return out.map(({mm: _mm, ...e}) => e);
}

// THE PAGE'S FACTS, SETTLED: what `ctx.cableFacts` read off the drawings, with
// what the catalogue knows of the parts in the bays laid over it (ports.js
// settleEnds). A reader that fails is the caller's to catch.
async function factsOf(rack, ctx, extra = []) {
  const facts = await ctx.cableFacts(rack, extra);
  return facts.unchecked ? facts : {...facts, ends: settleEnds(rack, facts.ends, ctx, extra)};
}

export async function suggestMedia(rack, a, b, ctx) {
  const facts = await factsOf(rack, ctx, [a, b]);
  const info = e => facts.ends?.get(endKey(e))?.info || null;
  const media = proposeMedia(info(a), info(b));
  return {media, warnings: mismatch(media, info(a), info(b))};
}

export async function looseEnds(rack, ctx) {
  const facts = await factsOf(rack, ctx);
  const ends = (rack.cables || []).flatMap(c => [['a', c.a], ['b', c.b]]
    .map(([side, end]) => ({cable: c.id, side, end, reason: facts.ends.get(endKey(end))?.reason ?? null})))
    .filter(x => x.reason);
  return {unchecked: !!facts.unchecked, ends};
}

// ── inspect (one item or one cable, whole) ──────────────────────────────
// What an agent needs before it fits a part, sets a field or re-points a
// cable, as a plain object for the caller to format. Async because a cable's
// loose ends and media are read through `ctx.cableFacts`, as looseEnds reads
// them; everything else is answered from the rack and what ctx hands in.
const offers = (ctx, refs) => refs.map(ref => ({ref, name: partName(ctx.compByRef, ref), kind: partOf(ctx.compByRef, ref)?.class ?? null}));

// THE CABLE COUNT A MAKER STATES FOR A MANAGER (#1032), as the catalogue
// holds it: the count, the basis in the words of the device file, and
// `media`, the kind of cable it counts (route.js capacityOver compares it
// with the cables at least that thick), or null where the catalogue names
// none.
const capacityFact = c => (c?.capacity?.count != null
  ? {capacity: {count: c.capacity.count, basis: c.capacity.basis ?? '', media: c.capacity.media ?? null,
                ...(c.capacity.estimated === true ? {estimated: true} : {})}} : {});

// WHAT AN ENTRY'S PARTS CAN BE SET TO, and what it is set to (P-0041), for
// `inspect` of a device or a part beside the rack: `settable` is
// `[{can: [names], paths: [...]}]`, the lamps, outlets and breakers its
// configuration declares grouped by vocabulary (`state.set` takes any path
// listed); `states` is what the entry is set to now. Each is left out when
// there is none, and `settable` when the parts list is not loaded.
function settableFacts(entry, ctx) {
  const facts = typeof ctx.slotsOf === 'function' ? configFacts(ctx.slotsOf(entry.ref), entry.cfg) : null;
  const settable = settableOf(facts);
  const set = entry.states && typeof entry.states === 'object' && Object.keys(entry.states).length ? entry.states : null;
  return {...(settable.length ? {settable} : {}), ...(set ? {states: {...set}} : {})};
}

function itemFacts(rack, item, ctx) {
  const c = ctx.chassisOf?.(item.ref) || null;
  const slots = typeof ctx.slotsOf === 'function' ? ctx.slotsOf(item.ref) : null;
  const configs = slots
    ? (slots.configs || []).map(k => ({name: k.name, description: k.description ?? '', airflow: k.airflow ?? null}))
    : (c?.configs || []).map(name => ({name, description: '', airflow: null}));
  const out = {kind: 'item', id: item.id, ref: item.ref, model: c?.model ?? null, manufacturer: c?.manufacturer ?? null,
    label: item.label, cfg: item.cfg, configs, ru: item.ru, u: ctx.chassisOf ? itemUnits(item, ctx.chassisOf) : 1, face: item.face, turned: !!item.turned,
    ...(rollOf(item) ? {roll: rollOf(item)} : {}),
    on: item.on ?? null, unit: item.unit ?? null, side: railOf(item, ctx.chassisOf ?? (() => null)),
    managers: managersOf(rack, item.id).map(m => m.id), ...capacityFact(c)};
  // its rings, ducts, pass-throughs and trays, and which hold spare (issue 1)
  const ways = pathwayFacts(rack, item.id, ctx);
  if (ways.length) out.pathways = ways;
  Object.assign(out, settableFacts(item, ctx));
  // A DEVICE OF A HEIGHT THAT IS NO WHOLE NUMBER OF UNITS may start on a
  // whole unit or on a half, and whether its ears meet the rail holes there
  // is checked only when the catalogue states its ear slot heights. None
  // does, so the check is silent and this says so, once for such a device.
  if (c && isRackMount(c) && !isQuarter(item) && !Number.isInteger(out.u))
    out.notes = [`The ear holes of ${c.model ?? item.ref} are not stated, so its holes at ${uText(rack.frame, item.ru, out.u)} are not checked.`];
  if (!slots) out.slots = 'not loaded';
  else {
    const env = slotEnv(item, slots, ctx.compByRef, ctx.redirects);
    const tree = slotTree(env, item.swaps || {});
    out.bays = tree.bays.map(b => ({...b, accepts: offers(ctx, b.accepts)}));
    out.cages = tree.cages.map(g => ({...g, accepts: offers(ctx, g.accepts)}));
    // the fields of every seated part that declares any, at the part's own
    // path - what the `field` command takes
    const parts = [...tree.bays.map(b => [`${b.path}/module`, b.holds]), ...tree.cages.map(g => [`${g.path}-occupant`, g.holds])];
    out.fields = parts.flatMap(([path, ref]) => fieldRows(partOf(ctx.compByRef, ref)?.fields, item.fields?.[path])
      .map(r => ({path, key: r.key, type: r.type, value: r.value, default: r.default, ...(r.type === 'choice' ? {choices: r.options} : {})})));
    // its displays and what each shows - what `display.set` takes
    const shown = displayList(rack, ctx, item.id);
    if (shown.length) out.displays = shown.map(({item: _i, ...d}) => d);
  }
  // A REF THE LIBRARY HAS REPLACED IS READ AS ITS REPLACEMENT, and a ref it no
  // longer has is kept and named (kit/redirects.js): the file is not changed
  // by either until it is next edited.
  const {redirected, unknown} = auditRack({items: [item]}, ctx);
  if (redirected.length) {
    out.redirected = redirected.map(({path, from, to}) => ({path, from, to}));
    out.notes = [...(out.notes || []), ...readAsTexts(redirected)];
  }
  if (unknown.length) {
    out.unknown = unknown.map(({path, ref}) => ({path, ref}));
    out.notes = [...(out.notes || []), ...unknownTexts(unknown)];
  }
  out.cables = (rack.cables || []).flatMap(cb => [['a', cb.a, cb.b], ['b', cb.b, cb.a]]
    .filter(([, e]) => e.item === item.id)
    .map(([end, e, o]) => ({id: cb.id, end, path: e.path, view: e.view, other: `${o.item}/${o.path}`})));
  // THE SLOTS A CABLE LANDS ON (P-0019): its power inlets, DC terminals and
  // ground studs, with the cable on each (null when free); its data ports are
  // the free-port answer's, which reads its drawing
  const ends = slotEnds(item, ctx);
  if (ends.length) out.ends = ends.map(e => ({...e, cable: cableAt(rack, item.id, e)}));
  return out;
}
// The id of the cable on an end, or null.
const cableAt = (rack, id, {path, view}) => (rack.cables || [])
  .find(c => [c.a, c.b].some(e => e.item === id && portPathOf(e.path) === path && (e.view === 'rear' ? 'rear' : 'front') === view))?.id ?? null;

// The pathway ids a route may name on a device: its rings and ducts
// (`guides`) and pass-throughs (`passes`), every view, from rack.json; on a
// part beside the rack, its duct and windows (route.js zeroUPathways).
const pathwayIds = pathwaysOf;
function partPathways(rack, id, ctx) {
  const it = rack.items.find(i => i.id === id);
  if (it) return pathwayIds(ctx.chassisOf?.(it.ref));
  const z = zeroUOf(rack).find(x => x.id === id);
  return z && ctx.chassisOf ? zeroUPathways(rack, z, ctx).map(p => p.via).sort() : [];
}
// THE PARTS WITH A PATHWAY NEAR A CABLE (issue 1): every rack item and part
// beside the rack with a pathway whose units come within two of the units of
// the cable's ends or of a lane point of its route. A standalone manager is
// no device's, so managersOf does not find it.
const NEAR_U = 2;
function nearRoute(rack, cable, waypoints, ctx) {
  if (!ctx.chassisOf) return [];
  // a span as fit.js gives it: from its unit to the one past its top
  const us = [...[cable.a, cable.b].map(e => rack.items.find(i => i.id === e?.item)).filter(Boolean)
    .flatMap(i => spanOf(i, ctx.chassisOf)), ...(waypoints || []).filter(w => w.lane).map(w => w.ru)];
  if (!us.length) return [];
  const lo = Math.min(...us) - NEAR_U, hi = Math.max(...us) + NEAR_U;
  const meets = ([from, past]) => from <= hi && past > lo;
  return [...rack.items.filter(i => meets(spanOf(i, ctx.chassisOf)) && partPathways(rack, i.id, ctx).length).map(i => i.id),
          ...zeroUOf(rack).filter(z => meets(zeroUTouched(z, ctx.chassisOf).map((u, k) => u + k)) && partPathways(rack, z.id, ctx).length).map(z => z.id)];
}
// A PART'S PATHWAYS, each with its kind and whether it holds spare (slack.js
// SPARE_HOLDS): as the routes know them when they are known, else as the
// catalogue lists them (a ring is a guide rack.json gives a depth, a duct a
// guide named one, a pass-through a `passes` id, a tray a `trays` id; any
// other guide is of no known kind). [] for a part with none.
function pathwayFacts(rack, id, ctx) {
  let ps = [];
  if (ctx.route) { try { ps = pathwaysAt(rack, id, ctx.route); } catch { ps = []; } }
  if (!ps.length) {
    const it = rack.items.find(i => i.id === id);
    const c = it ? ctx.chassisOf?.(it.ref) : null;
    if (it && c) {
      const kindOf = via => (Object.values(c.passes || {}).flat().includes(via) ? 'pass'
        : (Array.isArray(c.trays) && c.trays.some(t => t?.id === via)) ? 'tray'
        : c.rings && Object.hasOwn(c.rings, via) ? 'ring' : /duct/.test(via) ? 'duct' : /^guide-\d+$|ring/.test(via) ? 'ring' : null);
      ps = pathwayIds(c).map(via => ({via, kind: kindOf(via)}));
    } else {
      const z = zeroUOf(rack).find(x => x.id === id);
      ps = z && ctx.chassisOf ? zeroUPathways(rack, z, ctx) : [];
    }
  }
  return ps.map(p => ({via: p.via, kind: p.kind ?? null, holds_spare: holdsSpare(p.kind)}));
}

async function cableInfo(rack, cable, ctx) {
  const uOf = ctx.chassisOf ? heightOf(ctx.chassisOf) : carriedU;
  const end = e => ({item: e.item, path: e.path, view: e.view, name: endName(rack, e, uOf)});
  const l = cable.length;
  // a part beside the rack is named as the page names it: its label, and its id too where another part has the label
  const label = id => labelOf(rack, id);
  const edited = cable.routeEdited === true;
  // A route context's readers come from the page's drawings and may throw; a
  // measure that fails is "not measured", never an error.
  let routed = null, waypoints = edited ? cable.route || [] : [], windows = [], rings = null, crosses = null, rests = null, bends = null, covers = null, ringNote = null;
  if (ctx.route) {
    try {
      waypoints = resolveRoute(rack, cable, ctx.route).waypoints;
      windows = windowsOf(rack, cable, ctx.route);
      // one path for the length and the rings (#930)
      const path = routePath(rack, cable, ctx.route);
      const r = pathLength(path);
      routed = r ? {metres: Math.round(r.measured * 100) / 100, stock: r.value} : null;
      // the rings it passes: which way through, the depth (and whether that
      // is estimated), and where it enters and leaves, in mm; a ring it would
      // enter and leave by one face is `passed: false`
      const at = p => [p.x, p.y, p.z].map(v => Math.round(v * 10) / 10);
      if (path?.rings.length) rings = path.rings.map(g => ({item: g.item, via: g.via, run: g.run, depth: g.depth,
        estimated: g.estimated, passed: g.passed, ...(g.passed ? {sense: g.sense, entry: at(g.entry), exit: at(g.exit)} : {face: at(g.face)})}));
      // each solid body it still crosses after the detours (#949): the part,
      // the two waypoints the leg lies between, and where it enters, in mm
      if (path?.crossings?.length) crosses = path.crossings.map(f => ({item: f.item, part: f.part, between: f.between, at: f.at}));
      // what it lies on (#949 step 3): each ring whose sill holds it, each
      // tray (the face it lies on, its role there, and on a held face the tie
      // slots it uses) and each body a free span comes to rest on
      if (path?.rests?.length) rests = path.rests.map(x => ({...x, ...(x.ties ? {ties: [...x.ties]} : {})}));
      // each corner with less room than its bend radius (#973, #1007): where,
      // the turn, the room and what the cable needs, with the sentence
      // bendFindings gives; and the ports a span of it passes in front of
      // (#1013), with coverFindings' sentence, how many, and whether every
      // port was there to judge or only the cabled ones (`judged`). Both follow the path, so a
      // cable is told them wherever it is given a routed length, a loose end
      // or not; a cable whose port is not found has no path and neither.
      const tight = bendFindingsOf(rack, cable, ctx.route, label, path);
      if (tight.length) bends = tight.map(f => ({point: f.point, between: f.between, at: f.at, angle_deg: f.angle_deg, legs_mm: f.legs_mm,
        room_mm: f.room_mm, need_mm: f.need_mm, short_mm: f.short_mm,
        ...(f.turns ? {apart_mm: f.apart_mm, turns: f.turns} : {}), ...(f.stop ? {stop: f.stop} : {}), ...(f.tooClose ? {tooClose: f.tooClose, advice: f.advice} : {}), text: f.text}));
      // each ring it would enter and leave by one face (P-0018), in the sentence the Warnings panel gives
      const doubled = ringFindingsOf(rack, cable, ctx.route, label, path);
      if (doubled.length) ringNote = doubled.map(f => ({item: f.item, via: f.via, text: f.text}));
      const over = coverFindingsOf(rack, cable, ctx.route, label, path)[0];
      if (over) covers = {count: over.count, ports: over.ports, between: over.between, judged: over.judged,
        ...(over.estimated ? {estimated: true} : {}), text: over.text};
    } catch { routed = null; rings = null; crosses = null; rests = null; bends = null; covers = null; ringNote = null; }
  }
  // slack: the cable's own length less the routed one, in metres
  // (only metres and feet convert; any other unit leaves slack unknown)
  // THE SPARE (version 4): the cable's length less what it needs, where it is
  // said to be stored, and what of it has no place. `said` is false when the
  // cable has no `slack` key and true for a list, empty or not. For a routed
  // length the stock size is the one the route gives now; for a pinned one it
  // is the pinned length. null where there is no path or no usable length.
  const r2 = v => Math.round(v * 100) / 100;
  let slack = null, need = null, spareNote = null;
  if (ctx.route && l) {
    try {
      const s = slackOf(rack, cable, ctx.route);
      if (s) {
        need = r2(s.spare.need_m);
        slack = {metres: r2(s.spare.spare_m), at_ends_m: r2(s.at_ends_m), said: s.said,
                 stored: s.entries.map(e => (e.end ? {end: e.end, metres: e.metres == null ? null : r2(e.metres)}
                   : {item: e.item, via: e.via, form: e.form, metres: e.metres == null ? null : r2(e.metres), ok: e.ok, ...(e.why ? {why: e.why} : {}),
                      // a duct: its kind, and how full it is against what its maker states (slack.js spareLoad)
                      ...(e.kind ? {kind: e.kind} : {}), ...(e.load ? {load: e.load} : {})})),
                 unplaced_m: r2(s.unplaced_m)};
        spareNote = slackFindings({...rack, cables: [cable]}, ctx.route, label).map(f => ({kind: f.kind, text: f.text}));
      }
    } catch { slack = null; }
  }
  // the devices a route through this cable's ends can name: its two, the
  // cable managers bolted on them, and every other part with a pathway that
  // stands within two units of its ends or its route, beside the rack too
  // (issue 1)
  const near = [...new Set([cable.a.item, cable.b.item])].filter(id => rack.items.some(i => i.id === id))
    .flatMap(id => [id, ...managersOf(rack, id).map(m => m.id)]);
  const passes = Object.fromEntries([...new Set([...near, ...nearRoute(rack, cable, waypoints, ctx)])]
    .map(id => [id, partPathways(rack, id, ctx)]).filter(([, ids]) => ids.length));
  // where its spare can go: the ducts and trays on its route (slack.js sparePlaces)
  let places = null;
  if (ctx.route) { try { places = sparePlaces(rack, cable, ctx.route).map(p => ({item: p.item, via: p.via, kind: p.kind})); } catch { places = null; } }
  // a reader that fails leaves the ends unchecked, never an error
  let loose = null, warn = null, unchecked = false;
  if (typeof ctx.cableFacts === 'function') {
    let facts;
    try { facts = await factsOf(rack, ctx, [cable.a, cable.b]); } catch { facts = {unchecked: true}; }
    unchecked = !!facts.unchecked;
    if (!facts.unchecked) {
      const at = e => facts.ends.get(endKey(e)) || {};
      loose = [['a', cable.a], ['b', cable.b]].map(([side, e]) => ({end: side, reason: at(e).reason ?? null})).filter(x => x.reason);
      warn = mismatch(cable.media, at(cable.a).info || null, at(cable.b).info || null);
    }
  }
  return {kind: 'cable', id: cable.id, a: end(cable.a), b: end(cable.b), media: cable.media, purpose: cable.purpose, label: cable.label,
    // its own colour (`cable.update` sets and clears it), when it states one
    ...(typeof cable.color === 'string' && cable.color ? {color: cable.color} : {}),
    length: l ? {value: l.value, unit: l.unit ?? 'm', source: l.source ?? 'entered', ...(need != null ? {need} : {})} : null, routed, slack,
    ...(spareNote?.length ? {spare_findings: spareNote} : {}), ...(places ? {spare_places: places} : {}),
    // how it was laid by hand in a pathway, as the file has it (`cable.lay`)
    ...(Array.isArray(cable.lay) && cable.lay.length ? {lay: cable.lay} : {}),
    route: {edited, waypoints, text: routeText(waypoints, label, rack.frame, ductsThrough(rack, ctx.chassisOf, label, windows)), ...(rings ? {rings} : {}), ...(crosses ? {crosses} : {}), ...(rests ? {rests} : {}),
            ...(bends ? {bends} : {}), ...(covers ? {covers} : {}), ...(ringNote ? {ring_findings: ringNote} : {})}, lanes: waypointLanesOf(rack.frame), passes,
    loose, mismatch: warn, ...(unchecked ? {unchecked: true} : {})};
}

// A part beside the rack (#926): where it stands, and whether the lane beside
// that upright runs through it. `kind` is 'zeroU'.
function zeroUFacts(rack, z, ctx) {
  const c = ctx.chassisOf?.(z.ref) || null;
  const on = (rack.cables || []).flatMap(cb => [['a', cb.a, cb.b], ['b', cb.b, cb.a]].filter(([, e]) => e.item === z.id)
    .map(([end, e, o]) => ({id: cb.id, end, path: e.path, view: e.view, other: `${o.item}/${o.path}`})));
  return {kind: 'zeroU', id: z.id, ref: z.ref, model: c?.model ?? null, manufacturer: c?.manufacturer ?? null,
    label: z.label ?? null, cfg: z.cfg ?? '', at: z.at, ru: zeroUBottom(z), u: isZeroUPart(c) ? zeroUUnits(c) : null,
    between: z.between === true, mount: c?.mount ?? null, lane: carriesLane(c) ? z.at : null,
    where: c ? whereText(rack, z, ctx.chassisOf) : null, ...capacityFact(c),
    // its duct and windows, which a route and cable.slack may name, and which hold spare
    ...(ctx.chassisOf && pathwayFacts(rack, z.id, ctx).length ? {pathways: pathwayFacts(rack, z.id, ctx)} : {}),
    // ITS ENDS (P-0019): each outlet a cable can end on, by type, the unit
    // it stands at and the cable on it (null when free), from the catalogue
    // and the cables on it, when there are any
    ...zeroUEndFacts(rack, z, ctx), ...(on.length ? {cables: on} : {}), ...settableFacts(z, ctx),
    ...(shownOn(rack, z, ctx).length ? {displays: shownOn(rack, z, ctx)} : {})};
}
const shownOn = (rack, z, ctx) => displayList(rack, ctx, z.id).map(({item: _i, ...d}) => d);

// WHICH PARTS ARE DISPLAYS, and what each shows: every display of every device
// and part beside the rack (or those of `item`) that says what kind it is, as
// {item, path, kind, columns, rows, takes, text, shows}. A device whose parts
// list is not loaded is skipped. What `display.set` takes the path from.
export const displays = (rack, ctx = {}, {item} = {}) => displayList(rack, ctx, item ?? null);
function zeroUEndFacts(rack, z, ctx) {
  if (typeof ctx.slotsOf !== 'function' || typeof ctx.compByRef !== 'function') return {};
  const ends = zeroUEnds(z, ctx);
  if (!ends.length) return {};
  const names = configFacts(ctx.slotsOf(z.ref), z.cfg)?.names || {};
  const f = rack.frame, ruOf = e => slotRu(rack, z, e);
  return {ends: ends.map(e => ({path: e.path, view: e.view, name: names[e.path] ?? portLabel(e.path), type: e.type, connector: e.connector,
    kind: e.kind, plug: e.plug, u: ruOf(e) == null ? null : uLabel(f, ruOf(e)),
    cable: cableAt(rack, z.id, e)}))};
}

// A BUNDLE (#921), `kind: 'bundle'`: its members with where each joins and
// leaves the trunk, the trunk in words and its length, its size against the
// pathways it passes, its straps, and its warnings. What needs the routes
// (`ctx.route`) is null without them, and `checked` is false: not measured,
// never a pass. `bend` is the bend check's (#922, bundles.js bendCheck): the
// bundle's radius and the cable that sets it, the members with no radius, and
// each corner and stated-radius pathway with the room there and what it needs;
// null when the routes are not known or there is no bundle to bend. `length`
// and `straps` carry `straight: true`, and `notes` a sentence, where the trunk
// was measured along the straight line for want of a cable's path (#1034).
function bundleFacts(rack, b, ctx) {
  const label = id => rack.items.find(i => i.id === id)?.label ?? id;
  const r = bundleCheck(rack, b, ctx);
  const L = r.layout;
  // a bundle of fewer than two is not drawn: no member joins or leaves it
  const at = id => (b.members.length >= 2 ? L?.members.find(m => m.cable === id) : null);
  const s = r.checked ? strapsOf(rack, b, ctx) : null;
  return {kind: 'bundle', id: b.id, number: b.number, label: b.label, name: bundleName(b),
    members: b.members.map(m => ({cable: m.cable, ...('a' in m ? {a: m.a} : {}), ...('b' in m ? {b: m.b} : {}),
                                  join: at(m.cable)?.join ?? null, leave: at(m.cable)?.leave ?? null})),
    route: {waypoints: b.route || [], text: routeText(b.route || [], label, rack.frame)},
    length: r.checked ? trunkLength(rack, b, ctx) : null,
    size: r.size, bend: r.bend,
    straps: {every: strapSpacing(b), count: s ? s.count : null, kinds: s ? s.kinds : null, ...(s?.straight ? {straight: true} : {}), ...(s?.few ? {few: true} : {})},
    // measured along the straight line where its cables have no path (bundles.js): said, since it is then an estimate
    gone: r.gone, warnings: r.warnings, notes: [...r.notes, ...(s?.straight ? [straightText(bundleName(b))] : []), ...(s?.few ? [fewText(bundleName(b))] : [])], checked: r.checked};
}

// inspect looks an id up as an item, a cable, a part beside the rack, then a
// bundle: a bundle's id is never another thing's (model.js settleBundles), so
// only one can match.
export async function inspect(rack, id, ctx = {}) {
  const item = rack.items.find(i => i.id === id);
  if (item) return itemFacts(rack, item, ctx);
  const cable = (rack.cables || []).find(c => c.id === id);
  if (cable) {
    const out = await cableInfo(rack, cable, ctx);
    const b = bundleOfCable(rack, id);
    if (!b) return out;
    const m = b.members.length >= 2 ? layoutOf(rack, b, ctx)?.members.find(x => x.cable === id) : null;
    return {...out, bundle: {id: b.id, join: m?.join ?? null, leave: m?.leave ?? null}};
  }
  const z = zeroUOf(rack).find(x => x.id === id);
  if (z) return zeroUFacts(rack, z, ctx);
  const b = bundlesOf(rack).find(x => x.id === id);
  if (b) return bundleFacts(rack, b, ctx);
  const s = String(id);
  return {error: /^c\d+$/.test(s) ? CABLE_GONE : /^z\d+$/.test(s) ? ZERO_GONE : /^b\d+$/.test(s) ? BUNDLE_GONE : GONE};
}

// ── selectCables (D5: a query, not a command argument) ──────────────────
// The ids of the cables a selector names, for a caller to expand into plain
// `cable.remove` or `cable.update` commands, so a batch stays one an agent can
// read back. Every key given narrows: {item, purpose} is that device's cables
// of that purpose. An empty result is {ids: []}.
const SELECTOR_KEYS = ['item', 'path', 'view', 'loose', 'purpose', 'media', 'bundle'];
export const NO_FACTS = 'Which cables are loose is only known once the devices have been read.';

export async function selectCables(rack, selector, ctx = {}) {
  const s = selector && typeof selector === 'object' && !Array.isArray(selector) ? selector : {};
  const keys = Object.keys(s);
  const odd = keys.find(k => !SELECTOR_KEYS.includes(k));
  if (odd) return {error: `A selector does not take ${odd}.`};
  if (('path' in s || 'view' in s) && !('item' in s)) return {error: 'A selector with a path needs its item.'};
  if ('loose' in s && s.loose !== true) return {error: 'A selector takes loose: true, or leaves it out.'};
  if (!keys.some(k => ['item', 'loose', 'purpose', 'media', 'bundle'].includes(k)))
    return {error: 'A selector names an item, loose: true, a purpose, a media or a bundle.'};
  // null or a non-string would match every cable: "no media" is not a selector
  const bad = ['item', 'path', 'view', 'purpose', 'media', 'bundle'].find(k => k in s && (typeof s[k] !== 'string' || !s[k]));
  if (bad) return {error: `A selector's ${bad} is a name; leave it out rather than send ${JSON.stringify(s[bad]) ?? String(s[bad])}.`};
  let list = rack.cables || [];
  // a bundle's members, in combing order (#921)
  if ('bundle' in s) {
    const b = bundlesOf(rack).find(x => x.id === s.bundle);
    if (!b) return {error: BUNDLE_GONE};
    const byId = new Map(list.map(c => [c.id, c]));
    list = b.members.map(m => byId.get(m.cable)).filter(Boolean);
  }
  if ('item' in s) {
    const ends = c => [c.a, c.b].filter(e => e.item === s.item);
    if (!rack.items.some(i => i.id === s.item) && !list.some(c => ends(c).length)) return {error: GONE};
    // a port however its path is spelled (a click on a seated optic is a click
    // on its port: cable-rules.js portPathOf), on one panel or on either
    const port = e => ('path' in s ? portPathOf(e.path) === portPathOf(s.path) : true) && ('view' in s ? e.view === s.view : true);
    list = list.filter(c => ends(c).some(port));
  }
  if ('purpose' in s || 'media' in s) list = list.filter(c => matches(c, {purpose: s.purpose ?? null, media: s.media ?? null}));
  if (s.loose === true) {
    if (typeof ctx.cableFacts !== 'function') return {error: NO_FACTS};
    const facts = await factsOf(rack, ctx);
    list = list.filter(c => [c.a, c.b].some(e => facts.ends.get(endKey(e))?.reason));
    // some ends could not be checked: say so, as looseEnds does
    if (facts.unchecked) return {ids: list.map(c => c.id), unchecked: true};
  }
  return {ids: list.map(c => c.id)};
}
