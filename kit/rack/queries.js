// kit/rack/queries.js
// QUESTIONS ABOUT A RACK, for an agent deciding what to send and
// for a page that wants to ask before it acts. Pure; the two that read faces
// are handed their readers in `ctx`, since reading a face needs the network and
// a DOMParser, which this module never touches.

import {fits, isRackFace, heightOf} from './fit.js';
import {placement, managersOf} from './managers.js';
import {uLabel} from './model.js';
import {portFree, endKey, proposeMedia, mismatch} from './cable-rules.js';
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

export function catalog(devices, {text, ru, family, mount} = {}) {
  const t = text ? String(text).toLowerCase() : null;
  return catalogEntries(devices)
    .filter(e => !t || [e.name, e.manufacturer, e.model].some(v => String(v ?? '').toLowerCase().includes(t)))
    .filter(e => ru == null || e.ru === ru)
    .filter(e => family == null || e.family === family)
    .filter(e => mount == null || (e.mount || 'rack') === mount)
    .map(e => ({ref: e.name, manufacturer: e.manufacturer ?? null, model: e.model ?? null, ru: e.ru,
                mount: e.mount || 'rack', family: e.family ?? null, configs: e.configs ?? [], default: e.default ?? null}));
}

// A SHORT READING OF THE RACK for an agent: the ids it needs to address
// anything, in about 1.5K characters (WebMCP's guidance for tool output). A
// long rack loses its labels first, then its tail, and says so.
const LIMIT = 1500;
export function describe(rack, {chassisOf}) {
  const f = rack.frame;
  const holes = f.holes.style === 'tapped' ? `tapped${f.holes.thread ? ` ${f.holes.thread}` : ''} holes` : 'square holes';
  const head = `${rack.name}: ${f.heightRU}U ${f.kind}, ${holes}, numbered ${f.numbering}.`;
  const uOf = heightOf(chassisOf);
  const span = i => {
    const [a, b] = [uLabel(f, i.ru), uLabel(f, i.ru + uOf(i) - 1)].sort((x, y) => x - y);
    return a === b ? `U${a}` : `U${a}-U${b}`;
  };
  const item = (i, short) => {
    const ms = managersOf(rack, i.id).map(m => m.id);
    return [`${i.id}${short ? '' : ` ${i.label}`} ${span(i)} ${i.face}${i.turned ? ' turned' : ''}`,
            ...(i.on ? [`on ${i.on} unit ${i.unit}`] : []), ...(ms.length ? [`carries ${ms.join(' ')}`] : [])].join(', ');
  };
  const side = e => `${e.item}/${e.path}${e.view === 'rear' ? ' (rear)' : ''}`;
  const cable = c => `${c.id}: ${side(c.a)} <-> ${side(c.b)}${c.media ? `, ${c.media}` : ''}`;
  const items = [...rack.items].sort((a, b) => b.ru - a.ru);
  const cables = rack.cables || [];
  const build = (short, nItems, nCables) => {
    const lines = [head, items.length ? 'Items:' : 'No items.', ...items.slice(0, nItems).map(i => item(i, short)),
                   ...(cables.length ? ['Cables:', ...cables.slice(0, nCables).map(cable)] : [])];
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

export async function inspect(rack, id, ctx = {}) {
  const item = rack.items.find(i => i.id === id);
  if (item) return itemFacts(rack, item, ctx);
  return {error: /^c\d+$/.test(String(id)) ? CABLE_GONE : GONE};
}
