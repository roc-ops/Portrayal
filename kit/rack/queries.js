// kit/rack/queries.js
// QUESTIONS ABOUT A RACK, for an agent deciding what to send and
// for a page that wants to ask before it acts. Pure; the two that read faces
// are handed their readers in `ctx`, since reading a face needs the network and
// a DOMParser, which this module never touches.

import {fits, isRackFace, heightOf, railOf, isZeroUPart, zeroUUnits} from './fit.js';
import {placement, managersOf} from './managers.js';
import {uLabel, zeroUOf, zeroUBottom} from './model.js';
import {whereText, carriesLane} from './zero-u.js';
import {portFree, endKey, proposeMedia, mismatch, endName, carriedU, portPathOf, matches, lengthText} from './cable-rules.js';
import {lanesOf, pathwaysOf, resolveRoute, pathLength, routePath, routeText} from './route.js';
import {catalogEntries} from './catalog.js';
import {GONE, CABLE_GONE, ZERO_GONE, BUNDLE_GONE} from './commands.js';
import {bundlesOf, bundleName} from './model.js';
import {bundleCheck, bundleOfCable, membersText, spacingText, strapSpacing, straps as strapsOf, trunkLength,
        layoutOf} from './bundles.js';
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
const SECTIONS = ['items', 'zeroU', 'cables', 'bundles'];
const count = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const sideOf = e => `${e.item}/${e.path}${e.view === 'rear' ? ' (rear)' : ''}`;

// One line for a bundle (#921): its members, its size and warnings when the
// routes are known (`ctx.route`), its straps.
function bundleLine(rack, b, ctx) {
  const ids = b.members.map(m => m.cable);
  const head = `${b.id} ${bundleName(b)}: ${count(ids.length, 'cable')}${ids.length ? ` (${membersText(ids)})` : ''}`;
  const spacing = spacingText(strapSpacing(b));
  if (ids.length < 2) return `${head}, not drawn.`;
  if (!ctx?.route) return `${head}, ${spacing}, not checked.`;
  const r = bundleCheck(rack, b, ctx);
  if (!r.checked) return `${head}, ${spacing}, not checked.`;
  const size = r.size ? `about ${Math.round(r.size.max_mm)} mm, ` : '';
  return `${head}, ${size}${spacing}, ${r.warnings.length ? count(r.warnings.length, 'warning') : 'no warnings'}.`;
}

export function describe(rack, ctx, {section, offset, limit} = {}) {
  const {chassisOf} = ctx;
  const f = rack.frame;
  const holes = f.holes.style === 'tapped' ? `tapped${f.holes.thread ? ` ${f.holes.thread}` : ''} holes` : 'square holes';
  const items = [...rack.items].sort((a, b) => b.ru - a.ru);
  const cables = rack.cables || [];
  // the parts beside the rack (#926), top down; counted only when there are any
  const beside = [...zeroUOf(rack)].sort((a, b) => zeroUBottom(b) - zeroUBottom(a));
  // the bundles (#921), in the rack's order; counted only when there are any
  const bundles = bundlesOf(rack);
  const totals = `${rack.name} (${rack.id}): ${count(items.length, 'item')}, ` +
    `${beside.length ? `${count(beside.length, 'part')} beside the rack, ` : ''}${count(cables.length, 'cable')}` +
    `${bundles.length ? `, ${count(bundles.length, 'bundle')}` : ''}.`;
  const frameLine = `${f.heightRU}U ${f.kind}, ${holes}, numbered ${f.numbering}.`;
  const uOf = heightOf(chassisOf);
  const span = i => {
    const [a, b] = [uLabel(f, i.ru), uLabel(f, i.ru + uOf(i) - 1)].sort((x, y) => x - y);
    return a === b ? `U${a}` : `U${a}-U${b}`;
  };
  // `full` is a window's line: the ref and configuration, the purpose and length
  const item = (i, short, full = false) => {
    const ms = managersOf(rack, i.id).map(m => m.id);
    const rail = railOf(i, chassisOf);
    return [`${i.id}${short ? '' : ` ${i.label}`} ${span(i)} ${i.face}${rail ? ` ${rail} rail` : ''}${i.turned ? ' turned' : ''}`,
            ...(full ? [`${i.ref} ${i.cfg || '(no configuration)'}`] : []),
            ...(i.on ? [`on ${i.on} unit ${i.unit}`] : []), ...(ms.length ? [`carries ${ms.join(' ')}`] : [])].join(', ');
  };
  const part = (z, short, full = false) => [`${z.id}${short ? '' : ` ${z.label}`} ${whereText(rack, z, chassisOf)}`,
    ...(full ? [`${z.ref} ${z.cfg || '(no configuration)'}`] : [])].join(', ');
  const cable = (c, full = false) => [`${c.id}: ${sideOf(c.a)} <-> ${sideOf(c.b)}`, ...(c.media ? [c.media] : []),
    ...(full && c.purpose ? [c.purpose] : []), ...(full && lengthText(c.length) ? [lengthText(c.length)] : [])].join(', ');

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
    return [`${totals} ${shown.join(' ')}`, frameLine, ...body].join('\n');
  }

  const bundleLines = bundles.map(b => bundleLine(rack, b, ctx));
  const build = (short, nItems, nCables, nBundles) => {
    const lines = [totals, frameLine, items.length ? 'Items:' : 'No items.', ...items.slice(0, nItems).map(i => item(i, short)),
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
    on: item.on ?? null, unit: item.unit ?? null, side: railOf(item, ctx.chassisOf ?? (() => null)),
    managers: managersOf(rack, item.id).map(m => m.id)};
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
  let routed = null, waypoints = edited ? cable.route || [] : [], rings = null;
  if (ctx.route) {
    try {
      waypoints = resolveRoute(rack, cable, ctx.route).waypoints;
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
    } catch { routed = null; rings = null; }
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
    route: {edited, waypoints, text: routeText(waypoints, label, rack.frame), ...(rings ? {rings} : {})}, lanes: lanesOf(rack.frame), passes,
    loose, mismatch: warn, ...(unchecked ? {unchecked: true} : {})};
}

// A part beside the rack (#926): where it stands, and whether the lane beside
// that upright runs through it. `kind` is 'zeroU'.
function zeroUFacts(rack, z, ctx) {
  const c = ctx.chassisOf?.(z.ref) || null;
  return {kind: 'zeroU', id: z.id, ref: z.ref, model: c?.model ?? null, manufacturer: c?.manufacturer ?? null,
    label: z.label ?? null, cfg: z.cfg ?? '', at: z.at, ru: zeroUBottom(z), u: isZeroUPart(c) ? zeroUUnits(c) : null,
    between: z.between === true, mount: c?.mount ?? null, lane: carriesLane(c) ? z.at : null,
    where: c ? whereText(rack, z, ctx.chassisOf) : null};
}

// A BUNDLE (#921), `kind: 'bundle'`: its members with where each joins and
// leaves the trunk, the trunk in words and its length, its size against the
// pathways it passes, its straps, and its warnings. What needs the routes
// (`ctx.route`) is null without them, and `checked` is false: not measured,
// never a pass. The bend is #922's, and null until it lands.
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
    size: r.size, bend: null,
    straps: {every: strapSpacing(b), count: s ? s.count : null},
    gone: r.gone, warnings: r.warnings, notes: r.notes, checked: r.checked};
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
    const facts = await ctx.cableFacts(rack);
    list = list.filter(c => [c.a, c.b].some(e => facts.ends.get(endKey(e))?.reason));
    // some ends could not be checked: say so, as looseEnds does
    if (facts.unchecked) return {ids: list.map(c => c.id), unchecked: true};
  }
  return {ids: list.map(c => c.id)};
}
