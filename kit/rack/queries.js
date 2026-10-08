// kit/rack/queries.js
// QUESTIONS ABOUT A RACK, for an agent deciding what to send and
// for a page that wants to ask before it acts. Pure; the two that read faces
// are handed their readers in `ctx`, since reading a face needs the network and
// a DOMParser, which this module never touches.

import {fits, isRackFace, heightOf} from './fit.js';
import {placement, managersOf} from './managers.js';
import {uLabel} from './model.js';
import {portFree, endKey, proposeMedia, mismatch, endName, carriedU, portPathOf, matches, lengthText} from './cable-rules.js';
import {lanesOf, pathwaysOf, resolveRoute, routedLength, routeText} from './route.js';
import {catalogEntries} from './catalog.js';
import {GONE, CABLE_GONE} from './commands.js';
import {slotEnv, slotTree, partName, partOf} from './slots.js';
import {fieldRows} from '../fields.js';

export function fitsAt(rack, {ref, face, ru}, {chassisOf}) {
  const spot = isRackFace(chassisOf(ref)) ? placement(rack, {face, ru}, chassisOf) : {face, ru};
  return fits(rack, {ref, ...spot}, chassisOf);
}

export const freeUs = (rack, {ref, face}, ctx) =>
  Array.from({length: rack.frame.heightRU}, (_, k) => k + 1).filter(ru => fitsAt(rack, {ref, face, ru}, ctx).ok);

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
const SECTIONS = ['items', 'cables'];
const count = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const sideOf = e => `${e.item}/${e.path}${e.view === 'rear' ? ' (rear)' : ''}`;

export function describe(rack, {chassisOf}, {section, offset, limit} = {}) {
  const f = rack.frame;
  const holes = f.holes.style === 'tapped' ? `tapped${f.holes.thread ? ` ${f.holes.thread}` : ''} holes` : 'square holes';
  const items = [...rack.items].sort((a, b) => b.ru - a.ru);
  const cables = rack.cables || [];
  const totals = `${rack.name} (${rack.id}): ${count(items.length, 'item')}, ${count(cables.length, 'cable')}.`;
  const frameLine = `${f.heightRU}U ${f.kind}, ${holes}, numbered ${f.numbering}.`;
  const uOf = heightOf(chassisOf);
  const span = i => {
    const [a, b] = [uLabel(f, i.ru), uLabel(f, i.ru + uOf(i) - 1)].sort((x, y) => x - y);
    return a === b ? `U${a}` : `U${a}-U${b}`;
  };
  // `full` is a window's line: the ref and configuration, the purpose and length
  const item = (i, short, full = false) => {
    const ms = managersOf(rack, i.id).map(m => m.id);
    return [`${i.id}${short ? '' : ` ${i.label}`} ${span(i)} ${i.face}${i.turned ? ' turned' : ''}`,
            ...(full ? [`${i.ref} ${i.cfg || '(no configuration)'}`] : []),
            ...(i.on ? [`on ${i.on} unit ${i.unit}`] : []), ...(ms.length ? [`carries ${ms.join(' ')}`] : [])].join(', ');
  };
  const cable = (c, full = false) => [`${c.id}: ${sideOf(c.a)} <-> ${sideOf(c.b)}`, ...(c.media ? [c.media] : []),
    ...(full && c.purpose ? [c.purpose] : []), ...(full && lengthText(c.length) ? [lengthText(c.length)] : [])].join(', ');

  if (section != null || offset != null || limit != null) {
    if (section != null && !SECTIONS.includes(section)) return {error: `There is no section ${section}. Ask for items or cables, or leave it out for both.`};
    if (offset != null && !(Number.isInteger(offset) && offset >= 0)) return {error: 'An offset is a whole number from 0.'};
    if (limit != null && !(Number.isInteger(limit) && limit >= 1)) return {error: `A limit is a whole number from 1 to ${MAX_WINDOW}.`};
    const from = offset ?? 0;
    const n = Math.min(limit ?? WINDOW, MAX_WINDOW);
    const parts = [['items', 'Items', items, i => item(i, false, true)], ['cables', 'Cables', cables, c => cable(c, true)]]
      .filter(([key]) => section == null || section === key);
    const shown = [], body = [];
    for (const [, title, list, line] of parts) {
      if (!list.length) shown.push(`No ${title.toLowerCase()}.`);
      else if (from >= list.length) shown.push(`${title} past the end: there are ${list.length}.`);
      else {
        shown.push(`${title} ${from + 1}-${Math.min(list.length, from + n)} shown.`);
        body.push(`${title}:`, ...list.slice(from, from + n).map(line));
      }
    }
    return [`${totals} ${shown.join(' ')}`, frameLine, ...body].join('\n');
  }

  const build = (short, nItems, nCables) => {
    const lines = [totals, frameLine, items.length ? 'Items:' : 'No items.', ...items.slice(0, nItems).map(i => item(i, short)),
                   ...(cables.length ? ['Cables:', ...cables.slice(0, nCables).map(c => cable(c))] : [])];
    const more = (items.length - nItems) + (cables.length - nCables);
    if (short) lines.push(more ? `Shortened: labels left out, and ${more} more not listed; ask for them by id.` : 'Shortened: labels left out.');
    return lines.join('\n');
  };
  let out = build(false, items.length, cables.length);
  if (out.length <= LIMIT) return out;
  let ni = items.length, nc = cables.length;
  out = build(true, ni, nc);
  while (out.length > LIMIT && (ni || nc)) {
    if (nc >= ni && nc) nc--; else ni--;
    out = build(true, ni, nc);
  }
  return out;
}

// The ports of a device with no cable, on either of its panels.
export async function freePorts(rack, itemId, {portsOf}) {
  const item = rack.items.find(i => i.id === itemId);
  if (!item) return {error: GONE};
  const out = [];
  for (const view of ['front', 'rear']) {
    for (const p of await portsOf(item, view)) {
      if (p.cls !== 'port') continue;
      if (!portFree(rack, {item: itemId, path: p.path, view}).ok) continue;
      out.push({path: p.path, view, label: p.path.replace(/-/g, ' '), media: p.media ?? null, speed: p.speed ?? null});
    }
  }
  return out;
}

export async function suggestMedia(rack, a, b, {cableFacts}) {
  const facts = await cableFacts(rack, [a, b]);
  const info = e => facts.ends.get(endKey(e))?.info || null;
  const media = proposeMedia(info(a), info(b));
  return {media, warnings: mismatch(media, info(a), info(b))};
}

export async function looseEnds(rack, {cableFacts}) {
  const facts = await cableFacts(rack);
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

function itemFacts(rack, item, ctx) {
  const c = ctx.chassisOf?.(item.ref) || null;
  const slots = typeof ctx.slotsOf === 'function' ? ctx.slotsOf(item.ref) : null;
  const configs = slots
    ? (slots.configs || []).map(k => ({name: k.name, description: k.description ?? '', airflow: k.airflow ?? null}))
    : (c?.configs || []).map(name => ({name, description: '', airflow: null}));
  const out = {kind: 'item', id: item.id, ref: item.ref, model: c?.model ?? null, manufacturer: c?.manufacturer ?? null,
    label: item.label, cfg: item.cfg, configs, ru: item.ru, u: Math.max(1, c?.ru ?? 1), face: item.face, turned: !!item.turned,
    on: item.on ?? null, unit: item.unit ?? null, managers: managersOf(rack, item.id).map(m => m.id)};
  if (!slots) out.slots = 'not loaded';
  else {
    const env = slotEnv(item, slots, ctx.compByRef);
    const tree = slotTree(env, item.swaps || {});
    out.bays = tree.bays.map(b => ({...b, accepts: offers(ctx, b.accepts)}));
    out.cages = tree.cages.map(g => ({...g, accepts: offers(ctx, g.accepts)}));
    // the fields of every seated part that declares any, at the part's own
    // path - what the `field` command takes
    const parts = [...tree.bays.map(b => [`${b.path}/module`, b.holds]), ...tree.cages.map(g => [`${g.path}-occupant`, g.holds])];
    out.fields = parts.flatMap(([path, ref]) => fieldRows(partOf(ctx.compByRef, ref)?.fields, item.fields?.[path])
      .map(r => ({path, key: r.key, type: r.type, value: r.value, default: r.default, ...(r.type === 'choice' ? {choices: r.options} : {})})));
  }
  out.cables = (rack.cables || []).flatMap(cb => [['a', cb.a, cb.b], ['b', cb.b, cb.a]]
    .filter(([, e]) => e.item === item.id)
    .map(([end, e, o]) => ({id: cb.id, end, path: e.path, view: e.view, other: `${o.item}/${o.path}`})));
  return out;
}

// The pathway ids a route may name on a device: its rings and ducts
// (`guides`) and pass-throughs (`passes`), every view, from rack.json.
const pathwayIds = pathwaysOf;

async function cableInfo(rack, cable, ctx) {
  const uOf = ctx.chassisOf ? heightOf(ctx.chassisOf) : carriedU;
  const end = e => ({item: e.item, path: e.path, view: e.view, name: endName(rack, e, uOf)});
  const l = cable.length;
  const label = id => rack.items.find(i => i.id === id)?.label ?? id;
  const edited = cable.routeEdited === true;
  // A route context's readers come from the page's drawings and may throw; a
  // measure that fails is "not measured", never an error.
  let routed = null, waypoints = edited ? cable.route || [] : [];
  if (ctx.route) {
    try {
      waypoints = resolveRoute(rack, cable, ctx.route).waypoints;
      const r = routedLength(rack, cable, ctx.route);
      routed = r ? {metres: Math.round(r.measured * 100) / 100, stock: r.value} : null;
    } catch { routed = null; }
  }
  // slack: the cable's own length less the routed one, in metres
  // (only metres and feet convert; any other unit leaves slack unknown)
  const own = l && l.source !== 'routed' && typeof l.value === 'number' && ['m', 'ft'].includes(l.unit ?? 'm')
    ? l.value * ((l.unit ?? 'm') === 'ft' ? 0.3048 : 1) : null;
  const slack = own != null && routed ? {metres: Math.round((own - routed.metres) * 100) / 100} : null;
  // the devices a route through this cable's ends can name: its two, and the
  // cable managers bolted on them
  const near = [...new Set([cable.a.item, cable.b.item])].filter(id => rack.items.some(i => i.id === id))
    .flatMap(id => [id, ...managersOf(rack, id).map(m => m.id)]);
  const passes = Object.fromEntries(near.map(id => [id, pathwayIds(ctx.chassisOf?.(rack.items.find(i => i.id === id).ref))])
    .filter(([, ids]) => ids.length));
  // a reader that fails leaves the ends unchecked, never an error
  let loose = null, warn = null, unchecked = false;
  if (typeof ctx.cableFacts === 'function') {
    let facts;
    try { facts = await ctx.cableFacts(rack, [cable.a, cable.b]); } catch { facts = {unchecked: true}; }
    unchecked = !!facts.unchecked;
    if (!facts.unchecked) {
      const at = e => facts.ends.get(endKey(e)) || {};
      loose = [['a', cable.a], ['b', cable.b]].map(([side, e]) => ({end: side, reason: at(e).reason ?? null})).filter(x => x.reason);
      warn = mismatch(cable.media, at(cable.a).info || null, at(cable.b).info || null);
    }
  }
  return {kind: 'cable', id: cable.id, a: end(cable.a), b: end(cable.b), media: cable.media, purpose: cable.purpose, label: cable.label,
    length: l ? {value: l.value, unit: l.unit ?? 'm', source: l.source ?? 'entered'} : null, routed, slack,
    route: {edited, waypoints, text: routeText(waypoints, label, rack.frame)}, lanes: lanesOf(rack.frame), passes,
    loose, mismatch: warn, ...(unchecked ? {unchecked: true} : {})};
}

export async function inspect(rack, id, ctx = {}) {
  const item = rack.items.find(i => i.id === id);
  if (item) return itemFacts(rack, item, ctx);
  const cable = (rack.cables || []).find(c => c.id === id);
  if (cable) return cableInfo(rack, cable, ctx);
  return {error: /^c\d+$/.test(String(id)) ? CABLE_GONE : GONE};
}

// ── selectCables (D5: a query, not a command argument) ──────────────────
// The ids of the cables a selector names, for a caller to expand into plain
// `cable.remove` or `cable.update` commands, so a batch stays one an agent can
// read back. Every key given narrows: {item, purpose} is that device's cables
// of that purpose. An empty result is {ids: []}.
const SELECTOR_KEYS = ['item', 'path', 'view', 'loose', 'purpose', 'media'];
export const NO_FACTS = 'Which cables are loose is only known once the devices have been read.';

export async function selectCables(rack, selector, ctx = {}) {
  const s = selector && typeof selector === 'object' && !Array.isArray(selector) ? selector : {};
  const keys = Object.keys(s);
  const odd = keys.find(k => !SELECTOR_KEYS.includes(k));
  if (odd) return {error: `A selector does not take ${odd}.`};
  if (('path' in s || 'view' in s) && !('item' in s)) return {error: 'A selector with a path needs its item.'};
  if ('loose' in s && s.loose !== true) return {error: 'A selector takes loose: true, or leaves it out.'};
  if (!keys.some(k => ['item', 'loose', 'purpose', 'media'].includes(k)))
    return {error: 'A selector names an item, loose: true, a purpose or a media.'};
  // null or a non-string would match every cable: "no media" is not a selector
  const bad = ['item', 'path', 'view', 'purpose', 'media'].find(k => k in s && (typeof s[k] !== 'string' || !s[k]));
  if (bad) return {error: `A selector's ${bad} is a name; leave it out rather than send ${JSON.stringify(s[bad]) ?? String(s[bad])}.`};
  let list = rack.cables || [];
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
    const facts = await ctx.cableFacts(rack);
    list = list.filter(c => [c.a, c.b].some(e => facts.ends.get(endKey(e))?.reason));
    // some ends could not be checked: say so, as looseEnds does
    if (facts.unchecked) return {ids: list.map(c => c.id), unchecked: true};
  }
  return {ids: list.map(c => c.id)};
}
