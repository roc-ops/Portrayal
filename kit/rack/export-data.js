// WHAT AN EXPORT SAYS, as data. Pure: no DOM, no fetch - so
// `node --test` covers every rule an export follows: file names, CSV
// quoting, the title block, which cabinet draws which device, the notes,
// and (below) DCIM matching and the bill of materials.
// The Rack Builder's exports (the page that builds the files) do the
// fetching and drawing, and ask here.

import {positionOf, uLabel, zeroUOf, bundlesOf, bundleName} from './model.js';
import {routeText, trunkRoute} from './route.js';
import {isRackMount, isZeroUPart, railOf} from './fit.js';
import {zeroUEntries, whereText} from './zero-u.js';
import {bundleCheck, straps as strapsOf, trunkLength, strapSpacing, membersText, bundleOfCable} from './bundles.js';
export {positionOf};
import {endKey, endName, cableName, paneOf, mismatch, lengthText, lengthParts, MEDIA_LABELS} from './cable-rules.js';

export const uniq = list => [...new Set(list)];

// One stem for every file a rack exports - the one its .json already uses.
// Never a dotfile ("." and ".." are names a rack can have), never longer
// than 80 characters, and never a name Windows keeps for a device: CON.drawio
// cannot be opened there, whatever its extension.
const RESERVED = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i;
const trimEdges = s => s.replace(/^[.-]+|[.-]+$/g, '');
export function fileStem(name) {
  const stem = trimEdges(trimEdges(String(name ?? '').replace(/[^A-Za-z0-9._-]+/g, '-')).slice(0, 80));
  if (!stem) return 'rack';
  return RESERVED.test(stem.split('.')[0]) ? `rack-${stem}` : stem;
}

const pad = n => String(n).padStart(2, '0');
export const isoDate = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

// RFC 4180: a cell with a comma, a quote, a line break or an edge space is
// quoted, its quotes doubled. Nothing else is touched - a part number that
// starts with "-" is a part number, not a formula to defuse. NetBox and
// Nautobot read this literally on import, so a guard prefix here would
// corrupt a name; the BOM's spreadsheet-safe variant is `bomCell`, below.
export const csvCell = v => {
  const s = v == null ? '' : String(v);
  return /[",\r\n]|^\s|\s$/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};
export function toCsv(columns, rows, notes = [], {cell = csvCell} = {}) {
  const line = cells => cells.map(cell).join(',');
  const out = [line(columns), ...rows.map(r => line(columns.map(c => r[c])))];
  if (notes.length) out.push('', line(['Notes']), ...notes.map(n => line([n])));
  return `${out.join('\r\n')}\r\n`;
}

export function holesText(frame) {
  if (frame.holes?.style !== 'tapped') return 'Square holes (cage nuts)';
  return `Tapped holes, ${frame.holes.thread || 'thread not stated'}`;
}

// The sheet's title block: rack name, frame, depths, holes, date, and what it
// was drawn with - `source`, which a host names itself by (#895).
export function titleLines(rack, date, {source = 'Portrayal'} = {}) {
  const f = rack.frame;
  const kind = f.kind === 'two-post' ? 'Two-post' : 'Four-post';
  const numbering = f.numbering === 'top-down' ? 'U1 at the top' : 'U1 at the bottom';
  const depth = f.kind === 'two-post'
    ? `Usable depth ${Math.round(f.usableDepth)} mm`
    : `Rail depth ${Math.round(f.railDepth)} mm · usable depth ${Math.round(f.usableDepth)} mm`;
  return [rack.name, `${kind} frame, ${f.heightRU}U, ${numbering}`, depth, holesText(f),
          `Drawn ${isoDate(date)} with ${source}`];
}

export function wrapText(text, width) {
  const lines = [];
  let cur = '';
  for (const w of String(text).split(/\s+/).filter(Boolean)) {
    if (cur && cur.length + 1 + w.length > width) { lines.push(cur); cur = w; }
    else cur = cur ? `${cur} ${w}` : w;
  }
  if (cur) lines.push(cur);
  return lines;
}

// draw.io reads a label cell as HTML (vendor/drawio.js writes html=1 and
// escapes for XML only), so text handed to it is escaped for HTML first:
// "R&D <core>" then shows as typed instead of losing its tag.
export const htmlText = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// A swap the face did not take, said two ways: `drawn` for a file that shows
// the face (the sheet, draw.io), `listed` for one that lists its parts (the
// BOM, the DCIM types). A refused bay is left empty; a part that could not be
// loaded leaves the configuration's own part in place.
const SEAT_TAIL = {
  drawn: {refused: n => `${n === 1 ? 'is' : 'are'} shown empty.`,
          failed: 'so the drawing shows what the configuration seats there.'},
  listed: {refused: n => `${n === 1 ? 'is' : 'are'} empty, so no part is listed there.`,
           failed: 'so the part the configuration seats there is listed instead.'}};
function seatNotesAs(tail, {label, u, face}) {
  const at = `${label} at U${u}`;
  const {refused = [], failed = []} = face?.seat || {};
  const out = [];
  if (refused.length)
    out.push(`${at}: ${refused.join(', ')} refused the part chosen and ${tail.refused(refused.length)}`);
  if (failed.length)
    out.push(`${at}: the part chosen for ${failed.join(', ')} couldn't be loaded, ${tail.failed}`);
  return out;
}
export const seatNotes = arg => seatNotesAs(SEAT_TAIL.listed, arg);

// What one pane could not show of one item. `u` is the device's position
// (uOfItem); `panel` is the device's own panel facing `pane`.
export function faceNotes({label, u, pane, panel, face}) {
  if (!face) return [`${label} at U${u}: no ${panel} drawing, so the ${pane} shows an outline.`];
  return seatNotesAs(SEAT_TAIL.drawn, {label, u, face});
}

const count = (n, one, many) => `${n} ${n === 1 ? one : many}`;

// THE STATUS LINE after a download. `notes` are the ones the file carries;
// `left` are the ones it has no place for (a USDZ has none at all), said
// rather than counted as "in the file".
export function exportStatus({notes = [], left = [], leftText = ''} = {}) {
  const head = notes.length ? `Downloaded, with ${count(notes.length, 'note', 'notes')} in the file.` : 'Downloaded.';
  return left.length ? `${head} ${leftText || `Not in the file: ${left.join(' ')}`}` : head;
}
// What a rack holds that an export leaves out. An export that carries the
// cables passes {cables: false}, and today every export does: the
// sheet, draw.io, the 3D model, the BOM, the cable schedule and both DCIM
// import kits. The line is kept for an export that one day does not.
// An export that carries the parts beside the rack (#926) passes
// {zeroU: false, chassisOf}: then only an entry it cannot place (a shape the
// kit does not read, or a part the catalogue does not know as zero-U) is
// counted as left out, and zeroUNotes says where each one it carries stands.
export function rackNotes(rack, {cables = true, zeroU = true, chassisOf = null} = {}) {
  const out = [];
  const placed = zeroU || typeof chassisOf !== 'function' ? new Set() : new Set(zeroUEntries(rack, chassisOf).map(e => e.id));
  const z = (rack.zeroU || []).filter(e => !placed.has(e?.id)).length, c = rack.cables?.length || 0;
  if (z) out.push(`${count(z, 'zero-U item is', 'zero-U items are')} not in this export yet.`);
  if (cables && c) out.push(`${count(c, 'cable is', 'cables are')} not in this export yet.`);
  return out;
}

// ── CABLES IN THE EXPORTS ───────────────────────────────────────────────
// Every export that carries cables reads them through these, so a loose end
// or a mismatch is worded once. `ends` is cable-plugs.js cableFacts(rack).ends:
// Map(endKey -> {info, reason}), reason null when the end lands. A cable
// whose ends are not in the map was not checked (reading the faces failed).
export const UNCHECKED_NOTE = 'Cable ends could not be checked, so loose ends are not marked.';
// A CABLE'S NAME IN A NOTE: its label, as the page lists it - with its id after
// it when another cable would read the same (a shared label, or a label that
// is another cable's id), so two notes never name two cables alike. A cable
// with no label is its id. The schedule's `id` column is how to find either.
export function cableNames(rack) {
  const cables = rack.cables || [], seen = new Map();
  for (const c of cables) seen.set(cableName(c), (seen.get(cableName(c)) || 0) + 1);
  return new Map(cables.map(c => [c.id, c.label && seen.get(c.label) > 1 ? `${c.label} (${c.id})` : cableName(c)]));
}
export function cableFindings(rack, ends = new Map()) {
  const names = cableNames(rack);
  return (rack.cables || []).map(cable => {
    const got = s => ends.get(endKey(cable[s]));
    const loose = [['A', 'a'], ['B', 'b']].filter(([, s]) => got(s)?.reason != null)
      .map(([side, s]) => ({side, end: cable[s], reason: got(s).reason}));
    return {cable, name: names.get(cable.id), loose, checked: !!got('a') && !!got('b'),
            warnings: mismatch(cable.media, got('a')?.info, got('b')?.info)};
  });
}
// The notes a drawn export carries: each loose end with its reason, each
// media mismatch. `undrawn` is for a file that leaves a cable with a loose
// end out altogether (draw.io) where the others draw its unplugged lead: true
// for every cable, or a test of one (the sheet and the 3D model leave out only
// some).
// `uOf` is endName's (how tall a device is), for a rack whose items do not
// carry their height.
export function cableNotes(rack, ends = new Map(), {undrawn = false, uOf} = {}) {
  const out = [], gone = typeof undrawn === 'function' ? undrawn : () => undrawn;
  for (const f of cableFindings(rack, ends)) {
    if (f.loose.length) {
      const why = f.loose.map(l => `end ${l.side}, ${endName(rack, l.end, uOf)}, is not connected (${l.reason})`);
      out.push(`Cable ${f.name}${gone(f.cable) ? ' is not drawn' : ''}: ${why.join('; ')}.`);
    }
    for (const w of f.warnings) out.push(`Cable ${f.name}: ${w}`);
  }
  return out;
}

// THE SHEET'S CABLE NOTES. `drawn` holds the ids of the cables that have a
// group on the sheet (a run, a lead, or a tag), `faces` the faces the sheet
// shows, `failed` the faces whose cables could not be drawn (the sheet says
// that itself). A cable is drawn where an end of it LANDS: a run between two,
// a lead hanging from one. A cable the sheet does not hold is said to be
// missing, never only implied:
//   - no end lands anywhere (both loose, both devices gone): it "is not
//     drawn", in the words the 3D model and draw.io use;
//   - its landed ends are all on the other face of a single-face sheet: it is
//     simply not on this sheet, and one line counts those. (A cross-face cable
//     is on both: its tag names the far end.)
export function sheetCableNotes(rack, ends = new Map(), {faces = ['front', 'rear'], drawn = new Set(), failed = [], uOf} = {}) {
  const byId = new Map(rack.items.map(i => [i.id, i]));
  const lands = e => byId.has(e.item) && ends.get(endKey(e))?.reason == null;
  const panes = c => [c.a, c.b].filter(lands).map(e => paneOf(byId.get(e.item), e.view));
  const undrawn = new Set(), elsewhere = new Map();
  for (const c of rack.cables || []) {
    if (drawn.has(c.id)) continue;
    const on = panes(c), here = on.filter(p => faces.includes(p));
    if (here.some(p => failed.includes(p))) continue;
    if (on.length && !here.length) elsewhere.set(on[0], (elsewhere.get(on[0]) || 0) + 1);
    else undrawn.add(c.id);
  }
  const out = cableNotes(rack, ends, {undrawn: c => undrawn.has(c.id), uOf});
  for (const [face, n] of elsewhere)
    out.push(`${count(n, 'cable is', 'cables are')} on the ${face} face only and ${n === 1 ? 'is' : 'are'} not on this sheet.`);
  return out;
}

// Own keys only: a hand-edited media named like something every object has
// (toString) is its own name, not a label.
const mediaLabel = m => (Object.hasOwn(MEDIA_LABELS, m) ? MEDIA_LABELS[m] : String(m ?? ''));
const asWritten = v => (typeof v === 'string' ? v : JSON.stringify(v));
// A length the page could not use (model.js lengthAsWritten), said once for
// the schedule and the BOM: neither counts it, and both quote it.
const asWrittenNote = c => (c.lengthAsWritten != null ? `Length as written in the file: ${asWritten(c.lengthAsWritten)}.` : null);

// THE CABLE SCHEDULE: one row per cable, in the rack's own order. A device is
// named as the device import names it (uniqueNames over the same items), so
// the two files agree. A length the page could not use (model.js
// lengthAsWritten) is quoted in the notes, never put in the numeric column.
// `id` is the cable's own id, which the 3D model's nodes and draw.io's edges
// carry; `cable` is its label, or its id when it has none.
// `bundle` (#923) is the name of the bundle the cable is in, as its tag prints
// it (model.js bundleName: its label, else "Bundle N"), blank for none.
export const CABLE_COLUMNS = ['id', 'cable', 'a_device', 'a_u', 'a_port', 'b_device', 'b_u', 'b_port', 'media', 'purpose',
  'length', 'length_unit', 'route', 'bundle', 'length_source', 'status', 'notes'];
// `items` are the rack's items with their height `u` (fit.js itemsWithU), so a
// device's U is the device import's position (positionOf). Without a height an
// item counts as 1U.
// `routes` is route-context.js's Map<cableId, {waypoints}>; without it no route is written.
// `bodies` is route.js bodyFindings(rack, ctx, nameOf) for the same render:
// each finding's sentence joins its cable's notes. Without it none is written.
// `bundles` is bundleExports(rack, ctx) for the same render: each bundle's note
// and its warnings join the file's notes. Without it the bundles are read
// with no routing context, so each is listed as not measured.
export function cableScheduleRows(rack, ends = new Map(), items = rack.items, routes = null, {bundles = null, bodies = null} = {}) {
  const names = uniqueNames(rack.items);
  const byId = new Map(items.map(i => [i.id, i]));
  const named = new Set();
  const side = e => {
    const it = byId.get(e.item);
    if (!it) return ['', '', e.path];
    if (names.get(it.id).renamed) named.add(names.get(it.id).name);
    return [names.get(it.id).name, uOfItem(rack.frame, it), e.path];
  };
  const findings = cableFindings(rack, ends);
  const rows = findings.map(f => {
    const c = f.cable, len = lengthParts(c.length), [aDev, aU, aPort] = side(c.a), [bDev, bU, bPort] = side(c.b);
    const notes = [...f.loose.map(l => `End ${l.side} is not connected: ${l.reason}.`), ...f.warnings];
    if (asWrittenNote(c)) notes.push(asWrittenNote(c));
    // each solid body its route still crosses (route.js bodyFindings, #949)
    for (const x of bodies || []) if (x.cable === c.id && x.text) notes.push(x.text);
    return {id: c.id, cable: cableName(c), a_device: aDev, a_u: aU, a_port: aPort, b_device: bDev, b_u: bU, b_port: bPort,
            media: mediaLabel(c.media), purpose: c.purpose, length: len ? len.value : '',
            length_unit: len ? len.unit : '',
            route: routes?.get(c.id) ? routeText(routes.get(c.id).waypoints, id => names.get(id)?.name ?? id, rack.frame) : '',
            bundle: bundleOfCable(rack, c.id) ? flat(bundleName(bundleOfCable(rack, c.id))) : '',
            length_source: c.length ? (c.length.source || 'entered') : '',
            status: !f.checked ? 'not checked' : f.loose.length ? 'loose end' : 'connected', notes: notes.join(' ')};
  });
  const notes = [];
  if (!rows.length) notes.push('This rack has no cables, so there is nothing to list.');
  if (findings.some(f => !f.checked)) notes.push(UNCHECKED_NOTE);
  if (named.size) notes.push(`Devices that share a label are named as the device import names them: ${[...named].join(', ')}.`);
  notes.push(...bundleNotes(bundles ?? bundleExports(rack)));
  return {columns: CABLE_COLUMNS, rows, notes};
}

// ── BUNDLES IN THE EXPORTS (#923, docs/cable-bundles-design.md section 7) ─
// Each bundle as the exports read it, measured once with the routing context
// of the render (`ctx`: {route, diameterOf?, bendOf?}, as bundleCheck takes
// it). One record per bundle, in the rack's order:
//   {id, number, label, name, members: [cable ids], drawn, checked,
//    length_m, every: {value, unit} | null, straps, size_mm, limit_mm,
//    limit_at, limit_estimated, bend_mm, bend_by, bend_checked, warnings, notes}
// `name` is what a tag prints (the label, else "Bundle N"), with control
// characters as spaces; `number` and `label` are the bundle's own, for label
// software to lay out as it likes. `straps` is the count the BOM buys
// (straps()), 0 for a bundle that is not drawn or has no spacing, and null
// when the route could not be read: never a guess. `length_m`, the size and
// the bend are null when not measured. `bend_checked` is false when the bend
// was not checked for every member (the notes say which).
export function bundleExports(rack, ctx = {}) {
  return bundlesOf(rack).map(b => {
    let check, st = null, len = null;
    try { check = bundleCheck(rack, b, ctx); } catch { check = {checked: false, size: null, bend: null, warnings: [], notes: []}; }
    const drawn = b.members.length >= 2;
    try { st = check.checked ? strapsOf(rack, b, ctx) : null; } catch { st = null; }
    try { len = check.checked && drawn ? trunkLength(rack, b, ctx) : null; } catch { len = null; }
    const size = check.size, bend = check.bend;
    return {id: b.id, number: b.number, label: b.label || '', name: flat(bundleName(b)),
            members: b.members.map(m => m.cable), drawn, checked: !!check.checked,
            length_m: len ? len.metres : null, every: strapSpacing(b),
            straps: !check.checked ? null : drawn ? (st ? st.count : null) : 0,
            size_mm: size && size.max_mm > 0 ? size.max_mm : null, limit_mm: size ? size.limit_mm : null,
            limit_at: size?.limitBy?.text ?? null, limit_estimated: !!size?.limitBy?.estimated,
            bend_mm: bend?.radius_mm ?? null, bend_by: bend?.by ?? null,
            bend_checked: !!bend && !bend.unchecked?.length,
            warnings: [...check.warnings], notes: [...check.notes]};
  });
}

const strapsText = (n, e) => (e ? `${count(n, 'strap', 'straps')} every ${e.value} ${e.unit}` : 'no straps');
// ONE LINE PER BUNDLE, then its warnings and its notes, for the cable
// schedule and any other export that lists the bundles: "Bundle 2 (b1): 12
// cables (c1-c12), 2.4 m, 8 straps every 12 in; 23 mm across, limit 29.5 mm
// at mgr-1 ring 5; bend radius 25 mm (c7)." `bundles` is bundleExports'.
export function bundleNote(e) {
  const n = e.members.length;
  const head = `${e.name} (${e.id}): ${count(n, 'cable', 'cables')}${n ? ` (${membersText(e.members)})` : ''}`;
  if (!e.drawn) return `${head}, no straps.`;
  if (!e.checked) return `${head}; its route could not be read, so its length, straps, size and bend are not given.`;
  const run = [e.length_m != null ? `${e.length_m} m` : null,
               e.straps != null ? strapsText(e.straps, e.every) : 'straps not counted'].filter(Boolean).join(', ');
  const size = e.size_mm != null ? `${Math.round(e.size_mm)} mm across, limit ${e.limit_mm} mm${e.limit_at ? ` at ${e.limit_at}${e.limit_estimated ? ' (estimated)' : ''}` : ''}` : null;
  const bend = e.bend_mm != null ? `bend radius ${e.bend_mm} mm (${e.bend_by})` : 'bend not checked';
  return `${head}, ${[run, size, bend].filter(Boolean).join('; ')}.`;
}
export const bundleNotes = (bundles = []) => bundles.flatMap(e => [bundleNote(e), ...e.warnings, ...e.notes]);

// THE BOM'S STRAP LINE (decision 6): one generic hook-and-loop strap line,
// its quantity every bundle's straps added up; no manufacturer, and length and
// width left to the buyer. No line when no bundle has a strap. `bundles` is
// bundleExports'.
export function strapBomRows(bundles = []) {
  const qty = bundles.reduce((a, e) => a + (e.straps || 0), 0);
  if (!qty) return [];
  const used = bundles.filter(e => e.straps > 0);
  const every = uniq(used.map(e => `${e.every.value} ${e.every.unit}`));
  return [{section: 'Cables', qty, manufacturer: '', model: 'Hook-and-loop cable strap',
           description: `For ${count(used.length, 'bundle', 'bundles')}, one strap every ${andWords(every)} along each; length and width to suit`,
           ref: ''}];
}
const andWords = xs => (xs.length < 2 ? xs.join('') : `${xs.slice(0, -1).join(', ')} or ${xs.at(-1)}`);
// What the strap line cannot count: a drawn bundle whose route could not be
// read (its straps are left out, never guessed), and one set to no straps.
export function strapBomNotes(bundles = []) {
  const out = [];
  for (const e of bundles) {
    if (!e.drawn) continue;
    if (e.straps == null) out.push(`${e.name}: its route could not be read, so its straps are not counted.`);
    else if (!e.every) out.push(`${e.name} is set to no straps, so none are counted for it.`);
  }
  return out;
}

// NOT RACK-MOUNT. The chassis index states `mount` only when it is not
// "rack"; such a device stays placeable, and everything says what it needs.
// ONE table, so the picker and the notes cannot word it differently.
export {isRackMount} from './fit.js';
const MOUNTS = {
  'din-rail': {tag: 'DIN rail', what: 'a DIN-rail device', where: 'a shelf or DIN-rail bracket'},
  desktop: {tag: 'desktop', what: 'a desktop device', where: 'a shelf'},
  wall: {tag: 'wall mount', what: 'a wall-mount device', where: 'a shelf or bracket'}};
// A rack-face part (a 0U cable manager) bolts to the rails like a rack device:
// it needs no shelf, so it has no "needs" sentence - managerNotes says where it is.
// A zero-U part stands beside the rack and needs none either: zeroUNotes says where.
const mountOf = mount => isRackMount({mount}) || mount === 'rack-face' || isZeroUPart({mount}) ? null
  : MOUNTS[mount] ?? {tag: mount, what: `not a rack-mount device (${mount})`, where: 'a shelf or bracket'};
export const mountText = mount => { const m = mountOf(mount); return m && `${m.what}, so it needs ${m.where}`; };
// The picker's words: the list row's tag and the fit line.
export function mountPick(mount) {
  if (mount === 'rack-face')
    return {tag: '0U, mounts on the rail face', fit: 'Fits here: it mounts on the rail face and takes no U of its own.'};
  if (isZeroUPart({mount}))
    return {tag: '0U, stands beside the rack', fit: 'Stands beside the rack at an upright and takes no U of its own.'};
  const m = mountOf(mount);
  return m && {tag: m.tag, fit: `Fits here, on ${m.where}: this is ${m.what}.`};
}
export function mountNotes(items, chassisOf, frame) {
  const out = [];
  for (const it of items) {
    const t = mountText(chassisOf(it.ref)?.mount);
    if (t) out.push(`${it.label} at U${frame ? uOfItem(frame, it, chassisOf) : it.ru}: ${t}.`);
  }
  return out;
}

// WHERE EACH MANAGER IS, for the sheets, draw.io and the BOM; a narrow part
// on one rail names its rail (#926).
export function managerNotes(items, chassisOf, frame) {
  const byId = new Map(items.map(i => [i.id, i]));
  return items.filter(i => chassisOf(i.ref)?.mount === 'rack-face').map(i => {
    const c = chassisOf(i.ref), host = i.on ? byId.get(i.on) : null, rail = railOf(i, chassisOf);
    const what = [c.manufacturer, c.model].filter(Boolean).join(' ') || i.ref;
    return `${i.label}: ${what}, 0U, ${host ? `on ${host.label} ` : ''}at U${positionOf(frame, i.ru, 1)}, ${i.face}${rail ? `, ${rail} rail` : ''}.`;
  });
}

// WHERE EACH PART BESIDE THE RACK STANDS (#926), for the sheets, the BOM and
// the 3D model: one sentence each, for every part zeroUEntries lists.
export function zeroUNotes(rack, chassisOf) {
  const byId = new Map(zeroUOf(rack).map(z => [z.id, z]));
  return zeroUEntries(rack, chassisOf).map(e => {
    const c = chassisOf(e.ref);
    const what = [c.manufacturer, c.model].filter(Boolean).join(' ') || e.ref;
    return `${e.label}: ${what}, 0U, ${whereText(rack, byId.get(e.id), chassisOf)}` +
      `${e.between ? '; it serves the next rack too, which this file does not hold' : ''}.`;
  });
}

// THE PARTS BESIDE THE RACK AS IMPORT ITEMS (#926): what deviceImportRows
// takes beside the rack's own items, one per part zeroUEntries lists, with
// `mount` (rack-side), `at`, `between`, `ru` and `u`, and the text of where
// it stands. A caller looks its device type up by ref as it does an item's.
export const zeroUImportItems = (rack, chassisOf) => zeroUEntries(rack, chassisOf).map(e =>
  ({...e, where: whereText(rack, zeroUOf(rack).find(z => z.id === e.id), chassisOf)}));

// createRackScene has no fields input yet (the Rack Builder's 3D scene).
export function threeDNotes(rack) {
  const withFields = rack.items.filter(i => Object.keys(i.fields || {}).length).map(i => i.label);
  return withFields.length ? [`Optic labels and colors are not in the 3D model yet: ${withFields.join(', ')}.`] : [];
}

// THE U A DEVICE IS NAMED WITH, in every note, row and column: its position
// (model.js positionOf - the lowest-numbered U it covers, counted the way this
// frame counts; what a DCIM calls a device's position). The height is the
// item's own `u` when it carries one (fit.js itemsWithU), else its chassis's.
export const uOfItem = (frame, item, chassisOf = () => null) =>
  positionOf(frame, item.ru, item.u ?? Math.max(1, chassisOf(item.ref)?.ru ?? 1));

// draw.io's cabinet counts from 1 at the TOP, and its `u` is the device's top U.
export const drawioU = (heightRU, ru, u) => heightRU - (ru + u - 1) + 1;

const overlaps = (a, b) => a.ru <= b.ru + b.u - 1 && b.ru <= a.ru + a.u - 1;
// ONE CABINET PER FACE. What you see from a side is what is mounted there,
// plus the far panel of anything that nothing mounted on this side covers.
// Behind a mounted device, the other side's device is hidden - two pictures
// in one U of a draw.io cabinet overlap, and the 2D pane already draws the
// mounted one on top.
export function perFaceItems(items) {
  // A rack-face manager is drawn last on its own face, never hides
  // anything, and on the other face is hidden by any device spanning its U.
  const isFace = it => it.mount === 'rack-face';
  const out = {front: [], rear: [], hidden: []};
  for (const pane of ['front', 'rear']) {
    for (const it of items) {
      if (it.face === pane) { out[pane].push(it); continue; }
      const by = items.find(o => !isFace(o) && (isFace(it) || o.face === pane) && overlaps(o, it));
      if (by) out.hidden.push({item: it, pane, by});
      else out[pane].push(it);
    }
    out[pane].sort((a, b) => isFace(a) - isFace(b));      // stable: managers last
  }
  return out;
}

// DRAW.IO, ONE PAGE. Both cabinets stand on one page so
// a front-to-rear cable is one edge, not two stubs on two tabs. vendor/drawio.js
// lays the racks of ONE group side by side, each drawn once per face the group
// names; so the group names one face, 'front', and holds two racks: rack 0 is
// what the front pane shows, rack 1 what the rear pane shows. 'front' is only
// the key each mounted entry's drawing is filed under.
//
// The vendor finds a cable's port by the mounted entry's id, and an item is
// in both cabinets, so the rear cabinet's entries get the id plus a suffix.
// The suffix is one no item id ends with: a rear id then never equals an item
// id, and two items never share one.
export function rearSuffix(items) {
  let s = '@rear';
  while (items.some(i => String(i.id).endsWith(s))) s += '@';
  return s;
}
export const drawioId = (id, pane, suffix) => (pane === 'rear' ? `${id}${suffix}` : String(id));

// The vendor labels every cabinet "<rack label> · <face key>", so both read
// "· front". The second cabinet's value is put right by ONE exact replace on
// its own cell (id g0r1-front), escaped as the vendor's cell() writes it. If
// that cell is not there the file is wrong, and this throws: the export fails
// where it can be seen, and never ships two "front" cabinets.
const xmlAttr = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
export function rearCabinetLabel(xml, label) {
  const cellOf = face => `id="g0r1-front" value="${xmlAttr(label ? `${label} · ${face}` : face)}"`;
  const was = cellOf('front');
  // Past the notes comment (a note can hold any text, but never "-->": the vendor
  // writes "--" as "-"): inside a <diagram> every attribute value is escaped,
  // so this text is the cell's own.
  const from = afterNotes(xml);
  const at = xml.indexOf(was, from);
  if (at < 0) throw new Error("draw.io: the rear cabinet's label cell was not found");
  return xml.slice(0, at) + cellOf('rear') + xml.slice(at + was.length);
}
const afterNotes = xml => { const end = xml.indexOf('-->'); return end < 0 ? 0 : end + 3; };

// The vendor writes a dashed box "no <face> drawing" for a device with nothing
// drawn on a side, and every entry is filed under the face 'front'. In the
// rear cabinet (cells whose parent is g0r1-front, ids ending -none) the box is
// reworded, tag by tag: nothing else in the file is touched.
export function rearNoDrawing(xml) {
  const text = 'value="no front drawing"';
  let out = '', pos = afterNotes(xml), at;
  out = xml.slice(0, pos);
  while ((at = xml.indexOf(text, pos)) >= 0) {
    const open = xml.lastIndexOf('<mxCell ', at), close = xml.indexOf('>', at);
    const tag = xml.slice(open, close + 1);
    const mine = open >= pos && /^<mxCell id="[^"]*-none" /.test(tag) && tag.endsWith(' parent="g0r1-front">');
    out += xml.slice(pos, at) + (mine ? 'value="no rear drawing"' : text);
    pos = at + text.length;
  }
  out += xml.slice(pos);
  // LOUD, like the label: a box of the rear cabinet (a cell whose id ends -none
  // and whose parent is g0r1-front, wherever the vendor puts those attributes)
  // that still does not read "no rear drawing" means the vendor's wording or
  // layout changed under the rewrite above. The export fails where it can be
  // seen, and never ships "no front drawing" in the rear cabinet.
  for (const [tag] of out.slice(afterNotes(out)).matchAll(/<mxCell\b[^>]*>/g))
    if (/\sid="[^"]*-none"/.test(tag) && /\sparent="g0r1-front"/.test(tag) && !tag.includes(' value="no rear drawing"'))
      throw new Error("draw.io: a rear cabinet's \"no drawing\" box was not reworded");
  return out;
}

// THE VENDOR'S CELL IDS. vendor/drawio.js slugs each entry's id into its cell
// ids, and a cell id that repeats is silently dropped by draw.io, so two ids
// that slug alike would put two devices' cables on one cell. vendorSlug is a
// copy of its rule (a test builds a diagram and compares them, so a vendor
// refresh that changes it fails); uniqueEntryIds gives the later of two alike
// in a cabinet an alias that slugs to something no entry in it has.
export const vendorSlug = s => String(s).replace(/[^A-Za-z0-9._-]+/g, '-').replace(/^-|-$/g, '');
export function uniqueEntryIds(entries) {
  const natural = {front: new Set(entries.filter(e => e.pane === 'front').map(e => vendorSlug(e.id))),
                   rear: new Set(entries.filter(e => e.pane === 'rear').map(e => vendorSlug(e.id)))};
  const raw = new Set(entries.map(e => e.id)), seen = {front: new Set(), rear: new Set()};
  return entries.map(({pane, id}) => {
    const s = vendorSlug(id);
    if (!seen[pane].has(s)) { seen[pane].add(s); return id; }
    let n = 2, alias;
    do alias = `${s || 'item'}-${n++}`;
    while (natural[pane].has(vendorSlug(alias)) || seen[pane].has(vendorSlug(alias)) || raw.has(alias));
    seen[pane].add(vendorSlug(alias)); raw.add(alias);
    return alias;
  });
}

// DRAW.IO CABLES. The vendor colours an edge by looking
// its cable's `media` up in a table, so the media handed to it is the key the
// colour is filed under: the cable's own media, except the showcase's
// 'copper', which is coloured by purpose and so is keyed with it.
export const drawioMedia = l => (l.media === 'copper' ? `copper-${l.purpose || 'server'}` : String(l.media || ''));

// The rack's cables as vendor/drawio.js rackDiagram takes them, and the notes
// for the ones it is not given. An end names the mounted entry of the CABINET
// that shows its panel (paneOf), by that cabinet's id for the item (`idOf`),
// and carries no `view`: every drawing is filed under one face key.
//   - A cable with a loose end is not an edge: an empty cage is still a port
//     cell, and an edge to it would say "connected". cableNotes says why.
//   - A cable whose port has no cell in its cabinet (`drawn(itemId, pane,
//     path)` is false: the device is hidden behind another there, or the port
//     is not in the drawing) is not an edge either, and is noted here, in
//     words - the vendor's own note would print the cabinet ids.
// The key as the vendor's colour table can take it: its lookup is a plain
// object, so a hand-edited media called __proto__, constructor or default would
// read another entry (or the whole table). Such a media takes the neutral colour.
export function drawioMediaKey(l) {
  const k = drawioMedia(l).toLowerCase();
  return /^[a-z0-9][a-z0-9-]*$/.test(k) && !(k in {}) && k !== 'default' ? k : '';
}

// A cable edge's whole style, for the vendor's cableStyle hook: its own edge
// (vendor/drawio.js CABLE_EDGE, which a test holds this to) with the label's
// text colour stated. The vendor gives a label a white background and leaves
// its text to draw.io, whose dark editor draws unstyled text light: white on
// white, an empty box on the device. A stated pair reads in either theme.
export const drawioCableStyle = color =>
  'edgeStyle=orthogonalEdgeStyle;rounded=1;endArrow=none;startArrow=none;strokeWidth=2;fontSize=8;' +
  `labelBackgroundColor=#FFFFFF;fontColor=#15171a;strokeColor=${color};`;

export function drawioCables(rack, {ends = new Map(), idOf, drawn, hiddenBy = () => null, unchecked = false, uOf}) {
  const byId = new Map(rack.items.map(i => [i.id, i]));
  // Ends that could not be checked: an edge may run to an empty cage, which
  // says "connected" where nothing is. None is drawn, and the file says so.
  const n = (rack.cables || []).length;
  if (unchecked && n) return {cables: [], notes: [`${count(n, 'cable is', 'cables are')} not drawn because ${n === 1 ? 'its' : 'their'} ends could not be checked.`]};
  const cables = [], notes = cableNotes(rack, ends, {undrawn: true, uOf});
  for (const f of cableFindings(rack, ends)) {
    if (f.loose.length) continue;
    const c = f.cable;
    const sides = [['A', c.a], ['B', c.b]].map(([side, end]) => {
      const it = byId.get(end.item) || null, pane = it ? paneOf(it, end.view) : null;
      return {side, end, it, pane, ok: !!it && drawn(it.id, pane, end.path)};
    });
    const missing = sides.filter(s => !s.ok);
    if (missing.length) {
      const why = missing.map(s => `end ${s.side}, ${endName(rack, s.end, uOf)}, ` +
        (s.it ? (hiddenBy(s.it.id, s.pane) ? `is hidden behind ${hiddenBy(s.it.id, s.pane)} in the ${s.pane} cabinet`
                                           : `has no port drawn in the ${s.pane} cabinet`)
              : 'names a device that is not in the rack'));
      notes.push(`Cable ${f.name} is not drawn: ${why.join('; ')}.`);
      continue;
    }
    const [a, b] = sides.map(s => ({item: idOf(s.it.id, s.pane), path: s.end.path}));
    cables.push({id: c.id, a, b, media: drawioMediaKey(c), purpose: c.purpose, label: c.label,
                 ...(c.length ? {length: c.length} : {})});
  }
  // draw.io draws each cable as its own edge, as it draws no routes (#923).
  const drawnBundles = bundlesOf(rack).filter(b => b.members.length >= 2);
  if (drawnBundles.length)
    notes.push(`Bundles are not drawn in draw.io, so their cables are drawn one by one: ${
      drawnBundles.map(b => `${flat(bundleName(b))} holds ${membersText(b.members.map(m => m.cable))}`).join('; ')}.`);
  return {cables, notes};
}

// ── DCIM ────────────────────────────────────────────────────────────────
export const stemOf = path => String(path).split('/').pop().replace(/\.ya?ml$/i, '');
export const vendorOf = path => String(path).split('/').at(-2) ?? '';
// THE DIRECTORY A MANUFACTURER'S FILES ARE UNDER is not always its name: the
// exporter writes a slash as a hyphen (dcim_export.py manufacturer_dir,
// Portrayal #826), so `BATM/Telco Systems` exports under `BATM-Telco Systems/`
// while the YAML inside keeps the real name. Every comparison of a path's
// vendor segment with a device's manufacturer goes through this, or that
// vendor's own device types read as another vendor's and every one of its
// devices is exported as a best guess. A part number is written the same way
// in a module type's file name (moduleTypePath below).
export const dirOf = man => String(man ?? '').replace(/\//g, '-');
export const tokens = s => String(s ?? '').toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);

// How a configuration's words are also spelled in vendor part numbers:
// Edgecore writes front-to-back airflow as -F, back-to-front as -B, and
// 48 V DC as 48V.
const ALIAS = {f2b: ['f'], b2f: ['b'], dc: ['48v']};
const runIn = (hay, needle) => needle.length > 0 && hay.some((_, i) =>
  i + needle.length <= hay.length && needle.every((t, k) => hay[i + k] === t));

// WHICH DEVICE TYPE IS THIS ITEM. index.json lists every type a device ref
// exports - one per SKU, often one per configuration - and nothing names
// which configuration each is. So: the chassis manufacturer's own files
// first; one file is certain; a file whose name carries the configuration's
// words as a run is certain when it is the only one; otherwise the best
// match on words and aliases is a GUESS, and the caller lists it in notes.
export function matchDeviceType({cfg, manufacturer, paths}) {
  if (!paths?.length) return null;
  const own = paths.filter(p => vendorOf(p) === dirOf(manufacturer));
  // No file of the chassis's own manufacturer: the match falls back to every
  // file, so whatever wins is still someone else's part - a guess even when
  // it is the only file, or the only one naming the configuration.
  const fallback = !own.length;
  const pool = fallback ? [...paths] : own;
  if (pool.length === 1) return {path: pool[0], guess: fallback, candidates: 1};
  const want = tokens(cfg);
  const exact = pool.filter(p => runIn(tokens(stemOf(p)), want));
  if (exact.length) {
    const best = [...exact].sort((a, b) => tokens(stemOf(a)).length - tokens(stemOf(b)).length)[0];
    return {path: best, guess: fallback || exact.length > 1, candidates: pool.length};
  }
  const wanted = want.flatMap(t => [t, ...(ALIAS[t] || [])]);
  let best = pool[0], score = -1;
  for (const p of pool) {
    const have = new Set(tokens(stemOf(p)));
    const s = wanted.filter(t => have.has(t)).length;
    if (s > score) { best = p; score = s; }
  }
  return {path: best, guess: true, candidates: pool.length};
}

// The identity lines at the top of a device-type YAML - enough for a CSV to
// name the type exactly as the YAML does. Top level only: an indented
// `model:` belongs to a component, not the type.
export function yamlHead(text) {
  const out = {};
  for (const line of String(text).split(/\r?\n/)) {
    const m = line.match(/^(manufacturer|model|slug|u_height|is_full_depth):\s*(.*?)\s*$/);
    if (!m || m[1] in out) continue;
    let v = m[2];
    if (/^'.*'$/.test(v)) v = v.slice(1, -1).replace(/''/g, "'");
    else if (/^".*"$/.test(v)) v = JSON.parse(v);
    out[m[1]] = v;
  }
  return {manufacturer: out.manufacturer ?? null, model: out.model ?? null, slug: out.slug ?? null,
          uHeight: out.u_height != null ? Number(out.u_height) : null,
          isFullDepth: out.is_full_depth === 'true'};
}

// A module type's file is named for the part number (attrs.model), a "/"
// in it written "-" (exporter.html reads it the same way).
export function moduleTypePath(paths, model) {
  if (!model) return null;
  const want = [model, model.replace(/\//g, '-')];
  return paths.find(p => p.includes('/module-types/') && want.includes(stemOf(p))) ?? null;
}
export const partNumber = comp => comp?.attrs?.model ?? comp?.attrs?.part ?? comp?.attrs?.['part-number']
  ?? comp?.attrs?.['vendor-sku'] ?? '';

// A DCIM wants unique device names, and NetBox's are unique IGNORING CASE
// ("Leaf" and "leaf" are one name): two items may share a label, or differ
// only by case. Every item whose label has a twin, case aside, gets the
// item's id - and a counter after it for as long as that name is some other
// item's own label (in any case), or one already generated here. This is the
// ONE place device names are decided: the devices, modules and cables files,
// the cable schedule and every note use these names.
//
// A NAME IS CLEAN HERE, whoever asks (the kits, the cable schedule): a rack
// file is anyone's JSON, so a label, a ref or an id may hold a line break or
// another control character, and the id is what tells twins apart. Each run of
// them is one space (flat), in the label and in the id suffix alike; a label
// of nothing else is not an empty name but the item's id. Ordinary labels and
// ids give exactly the names they always did.
const CONTROLS = /[\u0000-\u001f\u007f-\u009f\u2028\u2029]+/g;
export const flat = s => String(s ?? '').replace(CONTROLS, ' ');
export function uniqueNames(items) {
  const idOf = i => flat(i.id).trim();
  const base = i => flat(i.label || i.ref).trim() || idOf(i);
  const key = i => base(i).toLowerCase();
  const seen = new Map();
  for (const i of items) seen.set(key(i), (seen.get(key(i)) || 0) + 1);
  const taken = new Set(seen.keys());
  return new Map(items.map(i => {
    if (seen.get(key(i)) === 1) return [i.id, {name: base(i), renamed: false}];
    let name = `${base(i)}-${flat(i.id)}`;
    for (let k = 2; taken.has(name.toLowerCase()); k++) name = `${base(i)}-${flat(i.id)}-${k}`;
    taken.add(name.toLowerCase());
    return [i.id, {name, renamed: true}];
  }));
}

// WHAT A DCIM STORES, one table. Only the values a row
// builder must screen. A value over a limit makes a real instance refuse the
// row, and NetBox refuses the whole file for one bad row.
//   Where each comes from: "facts" is the model field as read from the
//   NetBox 4.7 and Nautobot 3.2 source; "believed" is the model field as
//   remembered, confirmed at the boundary by the acceptance run.
export const DCIM_LIMITS = {
  // NetBox Device.name is a 64-character field, unique ignoring case (believed;
  // the model source says only "unique per site and tenant"). Nautobot's own limit
  // is not stated in its model source, so this NetBox limit is applied to both.
  deviceName: 64,
  // Cable.label (100) and Cable.description (200, PrimaryModel), NetBox v4.7.2
  // (facts: 251458b8, dcim/models/cables.py and netbox/models/__init__.py).
  // Nautobot's label is held to the same 100 here; its cable has no
  // description (v3.2.6, 3dc554b4), so its cable file carries none.
  cableLabel: 100,
  cableDescription: 200,
  // NetBox Cable.length: a decimal of 8 digits and 2 places, so below 1,000,000
  // (the two places are facts; the 8 digits are believed).
  netboxLengthBelow: 1000000,
  // Nautobot Cable.length: a PositiveSmallIntegerField (facts: Nautobot's cables.py).
  nautobotLengthMax: 32767};
// What a database counts: characters, not UTF-16 units.
export const charCount = s => Array.from(String(s)).length;
export const cutTo = (s, n) => Array.from(String(s)).slice(0, n).join('');

export const NETBOX_COLUMNS = ['name', 'role', 'manufacturer', 'device_type', 'status', 'site', 'rack',
  'position', 'face', 'comments'];
// rack__location__name pins the rack to the device's own location: rack__name
// alone matches a rack of that name in ANY location, and rack names repeat
// from one location to the next.
export const NAUTOBOT_COLUMNS = ['name', 'role__name', 'device_type__manufacturer__name', 'device_type__model',
  'status__name', 'location__name', 'rack__name', 'rack__location__name', 'position', 'face', 'comments'];
export const TARGET_NAME = {netbox: 'NetBox', nautobot: 'Nautobot'};

// The one wording for "this type is another vendor's file", shared by a
// kit's README and its devices file's comments column.
//
// The other vendor is named by its DIRECTORY, not by the name in its YAML: with
// the file's stem it says exactly where the file is in the kit, which is what a
// reader checking the guess needs. The two differ for a name holding a slash
// (dirOf above), and only there.
export const otherVendorNote = ({label, ref, T, manufacturer, path}) =>
  `${label} (${ref}): no ${T} device type from ${manufacturer || 'its manufacturer'}, so ` +
  `${stemOf(path)} is another vendor's (${vendorOf(path)}) file, a best guess.`;

// THE DEVICE IMPORT: one row per rail item the target will take, top down.
// `dcim` is the rack's import settings ({site, role}, model.js dcimOf): NetBox's
// site and role, Nautobot's location and role. Both are required by both
// targets and are written as given; blank ones stay blank, and the kit's
// README says the file will be refused until they are filled in.
//
// A ROW THE TARGET WOULD REFUSE IS NOT WRITTEN. Both
// targets take a device file whole or not at all, so one such row would
// refuse every device. `left` lists each device left out, with the sentence
// the README carries:
//   - a device with no device type (the type is a required column), on both;
//   - on NetBox only, the later-placed of two devices that share a U front
//     and rear while either type is full depth. The rack's own order is the
//     order they were placed. Nautobot 3.2 accepts such a pair, so its file
//     keeps both.
export function deviceImportRows({rack, items, types, target = 'netbox', dcim = {}, why = new Map()}) {
  const T = TARGET_NAME[target] || 'NetBox';
  const names = uniqueNames(items);
  const site = String(dcim?.site ?? '').trim(), role = String(dcim?.role ?? '').trim();
  const kept = [], left = [];
  for (const it of items) {
    const t = types.get(it.id) || null, name = names.get(it.id).name;
    if (!t) {
      // `why` is the real cause when it is not "there is none" (a type file or the index could not be read).
      left.push({id: it.id, name, reason: `${name} is not in the devices file: ` + (why.get(it.id) ??
        `there is no ${T} device type for ${it.ref}${it.cfg ? ` (${it.cfg})` : ''}`) + '. Add the type and the device by hand.'});
      continue;
    }
    if (charCount(name) > DCIM_LIMITS.deviceName) {
      left.push({id: it.id, name, reason: `${cutTo(name, 24)}... is not in the devices file: its name is ${charCount(name)} characters, ` +
        `and NetBox allows ${DCIM_LIMITS.deviceName}${target === 'nautobot' ? ' (a NetBox limit, applied to Nautobot too)' : ''}. ` +
        'Shorten its label and export again.'});
      continue;
    }
    const offRails = m => m === 'rack-face' || isZeroUPart({mount: m});
    const clash = target === 'nautobot' || offRails(it.mount) ? null
      : kept.find(o => !offRails(o.mount) && o.face !== it.face && overlaps(o, it) && (t.isFullDepth || types.get(o.id).isFullDepth));
    if (clash) {
      left.push({id: it.id, name, reason: `${name} is not in the devices file: it shares U${positionOf(rack.frame, it.ru, it.u)} ` +
        `with ${names.get(clash.id).name} on the ${clash.face}, and ${T} refuses two devices in one U, front and rear, while ` +
        `either type is full depth. One refused row refuses the whole file. Import ${name} by hand after changing the ` +
        `type's depth, or place it elsewhere.`});
      continue;
    }
    kept.push(it);
  }
  // Top down by the U a device's TOP occupies, not where it starts (ru is
  // its bottom): a tall device reaches higher than its ru alone would say.
  const topU = it => it.ru + it.u - 1;
  const sorted = [...kept].sort((a, b) => topU(b) - topU(a) || (a.face === b.face ? 0 : a.face === 'front' ? -1 : 1));
  const rows = sorted.map(it => {
    const t = types.get(it.id);
    const n = names.get(it.id);
    const notes = [];
    if (t.otherVendor)
      notes.push(otherVendorNote({label: it.label, ref: it.ref, T, manufacturer: t.chassisManufacturer, path: t.path}));
    else if (t.guess) notes.push(`Device type ${t.model} is a best guess for configuration ${it.cfg}.`);
    if (n.renamed) notes.push(`Named ${n.name} because another device here is also ${flat(it.label || it.ref).trim()}.`);
    const mt = mountText(it.mount);
    if (mt) notes.push(`${mt[0].toUpperCase()}${mt.slice(1)}.`);
    if (it.turned) notes.push('Mounted turned: its rear panel faces out.');
    // A part beside the rack (zeroUImportItems) and a manager on the rail face
    // take no position and no face: where each is goes in the comment.
    const beside = isZeroUPart({mount: it.mount});
    const zeroU = it.mount === 'rack-face' || beside;
    if (beside) {
      notes.push(`0U, ${it.where}${it.between ? ', serving the next rack too' : ''}; ${T} has no field for that.`);
    } else if (zeroU) {
      const host = it.on ? items.find(o => o.id === it.on) : null;
      notes.push(`0U cable manager on the ${it.face} rail face at U${positionOf(rack.frame, it.ru, 1)}` +
                 `${it.side === 'left' || it.side === 'right' ? `, ${it.side} rail` : ''}` +
                 `${host ? `, over ${names.get(host.id)?.name ?? host.label}` : ''}; ${T} has no field for that.`);
    }
    const position = positionOf(rack.frame, it.ru, it.u);
    const comments = notes.join(' ');
    return target === 'nautobot'
      ? {name: n.name, role__name: role, device_type__manufacturer__name: t.manufacturer ?? '',
         device_type__model: t.model ?? '', status__name: 'Planned', location__name: site,
         rack__name: rack.name, rack__location__name: site, position: zeroU ? '' : position, face: zeroU ? '' : it.face, comments}
      : {name: n.name, role, manufacturer: t.manufacturer ?? '', device_type: t.model ?? '',
         status: 'planned', site, rack: rack.name, position: zeroU ? '' : position, face: zeroU ? '' : it.face, comments};
  });
  return {columns: target === 'nautobot' ? NAUTOBOT_COLUMNS : NETBOX_COLUMNS, rows, left};
}

// THE RACK, as NetBox imports one: written from the frame.
// A device row names its rack, and the device import does not create it.
// desc_units is NetBox's "units are numbered top-to-bottom".
export const NETBOX_RACK_COLUMNS = ['site', 'name', 'status', 'width', 'u_height', 'desc_units'];
export function rackImportRows({rack, dcim = {}}) {
  return {columns: NETBOX_RACK_COLUMNS, rows: [{site: String(dcim?.site ?? '').trim(), name: rack.name, status: 'planned',
    width: 19, u_height: rack.frame.heightRU, desc_units: rack.frame.numbering === 'top-down' ? 'true' : 'false'}]};
}

// ── THE BILL OF MATERIALS ───────────────────────────────────────────────
// A part counts when it is SEATED: a bay's module (`…/module`) or a cage's
// occupant (`…-occupant` - an optic, a cap, a plug). Everything else in a
// face that carries data-ref is the chassis itself (a door, a jack, every
// port shape) and is already the device's line.
export const isSeatedPath = path => /\/module$|-occupant$/.test(String(path));

export const SECTIONS = [
  ['device', 'Devices'], ['supervisor', 'Supervisors'], ['line-card', 'Line cards'], ['fabric', 'Fabric cards'],
  ['expansion-card', 'Expansion cards'], ['nic', 'Network cards'], ['riser', 'Risers'], ['drive', 'Drives'],
  ['psu', 'Power supplies'], ['fan', 'Fans'], ['filter', 'Filters'], ['cassette', 'Cassettes'],
  ['adapter-panel', 'Adapter panels'], ['blank', 'Blanks'], ['transceiver', 'Optics'], ['port', 'Plugs'],
  ['cap', 'Dust caps'], ['other', 'Other parts'], ['hardware', 'Mounting hardware']];
const SECTION = new Map(SECTIONS);
export const sectionOf = cls => SECTION.get(cls) ?? 'Other parts';
const sectionOrder = label => SECTIONS.findIndex(([, l]) => l === label);

export const firstSentence = text => String(text ?? '').split(/(?<=\.)\s/)[0];
const titled = ns => ns.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
// A seated part's maker: the directory its module type is filed under, or, with
// no module type, the component's own namespace titled.
//
// THE DIRECTORY IS NOT TURNED BACK INTO A NAME. dirOf is not invertible - from
// `BATM-Telco Systems` there is no telling whether the name held a slash or a
// real hyphen - and the real name is only in the YAML, which the BOM never
// fetches: it reads files.json, a list of paths, and nothing else (bomCsv says
// so). Reading every seated module's file to recover one vendor's punctuation
// would make the BOM as many requests as the rack has distinct modules, and
// give it a per-part failure mode it does not have today. So the one vendor
// whose name holds a slash reads `BATM-Telco Systems` in this column while its
// chassis line, which comes from the device catalogue, reads `BATM/Telco
// Systems`; both name the same maker, and the directory is where its files are.
export function partManufacturer(comp, path) {
  if (path) return vendorOf(path);
  if (!comp || ['generic', 'std', 'common'].includes(comp.ns)) return '';
  return titled(comp.ns);
}

export const BOM_COLUMNS = ['section', 'qty', 'manufacturer', 'model', 'description', 'ref'];

// The BOM is meant to open in a spreadsheet, unlike the device-import CSVs
// (an importer reads those literally). A cell that OPENS as a formula -
// starts with =, +, - or @, or with the tab or carriage return a spreadsheet
// skips on its way to one - gets a leading apostrophe first, so the
// spreadsheet keeps it as text; csvCell then quotes it as any such text needs.
const FORMULA_START = /^[=+\-@\t\r]/;
export const bomCell = v => csvCell(FORMULA_START.test(String(v ?? '')) ? `'${v}` : v);

export function bomRows({devices = [], parts = [], frame, railUs = []}) {
  const lines = new Map();
  const add = (key, row) => { const l = lines.get(key); if (l) l.qty++; else lines.set(key, {...row, qty: 1}); };
  for (const d of devices)
    add(`device|${d.ref}|${d.cfg}`, {section: 'Devices', manufacturer: d.manufacturer ?? '', model: d.model ?? d.ref,
      description: d.cfg ? `Configuration ${d.cfg}` : '', ref: d.ref});
  for (const p of parts)
    add(`part|${p.ref}`, {section: sectionOf(p.cls), manufacturer: p.manufacturer ?? '', model: p.model || p.ref,
      description: p.description ?? '', ref: p.ref});
  const rows = [...lines.values()].sort((a, b) => sectionOrder(a.section) - sectionOrder(b.section)
    || String(a.model).localeCompare(String(b.model)) || String(a.ref).localeCompare(String(b.ref)));
  return [...rows, ...hardwareRows(frame, railUs)];
}

// 2 ears x 2 screws x each U a rail item covers.
export function hardwareRows(frame, railUs) {
  const qty = 4 * railUs.reduce((s, u) => s + Math.max(1, u), 0);
  if (!qty) return [];
  const row = model => ({section: 'Mounting hardware', qty, manufacturer: '', model,
    description: 'Two per ear for each U a device covers', ref: ''});
  if (frame.holes?.style === 'tapped') return [row(`Screw, ${frame.holes.thread || 'thread not stated'}`)];
  return [row('Cage nut, M6'), row('Screw, M6')];
}
export function hardwareNotes(frame) {
  if (frame.holes?.style !== 'tapped')
    return ["Cage nuts and screws are counted as M6, the usual size for square-hole rails; check your rack's own."];
  return frame.holes.thread ? [] : ['The rail thread is not set under Frame, so the screws are listed without one.'];
}

// CABLES IN THE BOM: one line per media, length and connector, with
// a quantity. A cable with no length - or one whose length the page could not
// use - is "length not set". The connector is what each end's port takes, as
// cable-plugs.js read it (`ends`, as for cableFindings); the two ends are
// said in one order, so A-to-B and B-to-A are one line. The plugs a cable is
// drawn with are part of the cable: they are never lines of their own.
const FAMILY = {fiber: 'fiber', copper: 'copper', dac: 'DAC', aoc: 'AOC'};
const familyOf = info => (info && Object.hasOwn(FAMILY, info.family ?? '') ? FAMILY[info.family] : null);
function connectorText(a, b) {
  const known = [familyOf(a), familyOf(b)].filter(Boolean).sort();
  if (known.length === 2) return known[0] === known[1] ? `${known[0]} at both ends` : `${known[0]} at one end, ${known[1]} at the other`;
  return known.length ? `${known[0]} at one end` : '';
}
// A panel with no drawing leaves its cables' connectors blank: said once per
// device panel, not once per cable. A length kept as written is listed as
// "length not set": said once per such cable, as the schedule says it.
export function cableBomNotes(rack, ends = new Map()) {
  const byId = new Map(rack.items.map(i => [i.id, i])), seen = new Set(), out = [];
  const names = cableNames(rack);
  for (const c of rack.cables || []) if (asWrittenNote(c)) out.push(`Cable ${names.get(c.id)}: ${asWrittenNote(c)}`);
  for (const c of rack.cables || []) for (const e of [c.a, c.b]) {
    const it = byId.get(e.item), k = `${e.item}|${e.view}`;
    if (!it || seen.has(k) || ends.get(endKey(e))?.facts?.drawing !== false) continue;
    seen.add(k);
    out.push(`${it.label}: its ${e.view} panel had no drawing, so the cable lines do not state its connectors.`);
  }
  return out;
}
// What the routes add to an export's notes: a pathway filled past its limit, a
// manager with more cables through it than it states, and a stored waypoint
// that no longer resolves. `facts` is route-context.js routeFacts (or null).
export function fillNotes(rack, facts, nameOf = id => id) {
  if (!facts) return [];
  const out = [];
  for (const f of facts.fill || [])
    if (f.over) out.push(`${f.via} on ${nameOf(f.item)}: ${f.count} cables, ${f.percent}% of a 40% fill.`);
  for (const o of facts.over || [])
    out.push(`${nameOf(o.item)}: ${o.count} cables through it, more than its stated ${o.capacity}.`);
  for (const c of rack.cables || [])
    for (const w of facts.routes?.get(c.id)?.gone || [])
      out.push(`Cable ${cableName(c)}: waypoint ${w.lane ? `${w.lane} U${uLabel(rack.frame, w.ru)}` : `${w.via} on ${nameOf(w.item)}`} is gone, so the route skips it.`);
  // A bundle's trunk (#921), read with the routing context the facts came
  // from: a trunk waypoint past a lower top, or on a removed device, is skipped.
  if (facts.ctx) for (const b of bundlesOf(rack)) {
    let gone = [];
    try { gone = trunkRoute(rack, b, facts.ctx).gone; } catch { gone = []; }
    for (const w of gone)
      out.push(`${bundleName(b)}: waypoint ${w.lane ? `${w.lane} U${uLabel(rack.frame, w.ru)}` : `${w.via} on ${nameOf(w.item)}`} is gone, so the route skips it.`);
  }
  return out;
}
export function cableBomRows(rack, ends = new Map()) {
  const lines = new Map();
  for (const c of rack.cables || []) {
    const info = s => ends.get(endKey(c[s]))?.info;
    const length = lengthText(c.length)
      ? `${lengthText(c.length)}${c.length.source === 'routed' ? ' (routed)' : ''}` : 'length not set';
    const connector = connectorText(info('a'), info('b'));
    const key = JSON.stringify([c.media ?? '', length, connector]);
    const l = lines.get(key);
    if (l) l.qty++;
    else lines.set(key, {section: 'Cables', qty: 1, manufacturer: '', model: mediaLabel(c.media) || 'Media not set',
                         description: [length, connector].filter(Boolean).join('; '), ref: ''});
  }
  return [...lines.values()].sort((a, b) => a.model.localeCompare(b.model) || a.description.localeCompare(b.description));
}
