// THE RACK FILE. Pure data: no DOM, no fetch, no rendering, so the
// page, the library, the exports and `node --test` all read one definition.
//
// A document holds an ARRAY of racks although the page edits one: rows of
// racks come later, and a file written today must still open then. Every
// edit here returns a new object - the page autosaves whatever it last
// committed, and a shared, mutated rack is how a save would catch half an edit.

import {RU} from './rails.js';
import {hexColor} from './cable-geometry.js';
import {shapeRefusal} from '../displays.js';

export const FORMAT = 'portrayal-rack';
// Zero-U parts and `side` (#926) did not raise it: both are optional keys a
// version-2 reader keeps (`zeroU` as written) or drops (`side`), and no reader
// older than this kit was ever published. Bundles (#921) did: a version-2
// reader would drop `bundles`, a rack key, and erase them on its next save.
// Version 4 (docs/rack-file-v4-design.md) is one bump for every key that
// needed one: a version-3 reader refuses `ru: 12.5` outright, and erases or
// misreads the others.
export const VERSION = 4;
export const THREADS = ['12-24', '10-32', 'M6'];
// MIGRATIONS[n - 1] takes a version-n document to version n + 1.
//   1 -> 2: rack-face managers (`on`, `unit` on an item). Nothing in a
//   version-1 file changes; the bump is so an older page refuses a file
//   holding a manager instead of drawing it as a 1U device over its host.
//   2 -> 3: cable bundles (`bundles` on a rack). Nothing in a version-2 file
//   changes; the bump is so an older page refuses a file holding bundles
//   instead of opening it, dropping them and erasing them on its next save
//   (docs/cable-bundles-design.md section 2.3).
//   3 -> 4: half-unit positions and the keys of docs/rack-file-v4-design.md
//   section 1.1. Nothing in a version-3 file changes shape or meaning; the
//   bump is so a version-3 page refuses a file it would erase keys from,
//   misplace or measure wrongly (section 8 of that note).
export const MIGRATIONS = [d => ({...d, version: 2}), d => ({...d, version: 3}), d => ({...d, version: 4})];

// WHAT A READER DOES NOT KNOW, IT KEEPS (version 4). An item, the frame, a rack
// and the document are each rebuilt from the keys this file knows; every other
// own key is carried over as written, as a cable, a zero-U entry and a bundle
// always carried theirs. So a later optional key that is safe to ignore needs
// no version bump, whichever level it sits at. A misspelt key is kept too, and
// not reported here: the schema reports it to anyone who validates.
const unknownOf = (o, known) => Object.fromEntries(Object.entries(o && typeof o === 'object' && !Array.isArray(o) ? o : {})
  .filter(([k]) => !known.includes(k)).map(([k, v]) => [k, structuredClone(v)]));
const FRAME_KEYS = ['kind', 'heightRU', 'numbering', 'holes', 'railDepth', 'usableDepth', 'ref', 'startU', 'setback', 'width'];
const ITEM_KEYS = ['id', 'ref', 'cfg', 'label', 'ru', 'face', 'turned', 'swaps', 'fields', 'on', 'unit', 'side', 'setback', 'roll',
                   'states', 'readings', 'readingsAsWritten', 'displays'];
const RACK_KEYS = ['id', 'name', 'frame', 'items', 'zeroU', 'cables', 'dcim', 'bundles'];
const DOC_KEYS = ['format', 'version', 'id', 'racks'];
// The rail hole styles. `round` (version 4) is an unthreaded round hole.
export const HOLE_STYLES = ['square', 'tapped', 'round'];
// THE OPTIONAL NUMBERS OF VERSION 4, each written only when it says something
// and left out otherwise, so a frame or an item never given one saves as it
// was. `startU`: the number of the first unit, a whole number from 1 (absent
// is 1). `setback`: millimetres a faceplate stands behind its rail, into the
// rack from the face it is on; negative is proud. `width`: the rail width in
// inches (absent is 19). A value that is none of these is dropped, as a bad
// thread is. `options` on a frame and `heldBy` on an item are kept as written.
const finite = v => typeof v === 'number' && Number.isFinite(v);
const startUOf = v => (Number.isInteger(v) && v >= 1 ? {startU: v} : {});
const setbackOf = v => (finite(v) ? {setback: v} : {});
const widthOf = v => (finite(v) && v > 0 ? {width: v} : {});
// ROLL (version 4): how an item is turned in the plane of its face, 90, 180 or
// 270 degrees clockwise as it is seen in the elevation of the face it is on,
// after `face` and `turned`. Absent is upright; 0 is never written.
export const ROLLS = [90, 180, 270];
export const rollOf = item => (ROLLS.includes(item?.roll) ? item.roll : 0);
const rollKey = v => (ROLLS.includes(v) ? {roll: v} : {});
export const firstU = frame => (Number.isInteger(frame?.startU) && frame.startU >= 1 ? frame.startU : 1);
export const RAIL_WIDTH_IN = 19;
export const railWidth = frame => (finite(frame?.width) && frame.width > 0 ? frame.width : RAIL_WIDTH_IN);
// WHAT HOLDS AN ITEM that is not bolted to the rails itself (`heldBy`): the id
// of its host item, or null. The key is kept whatever its shape; this is what
// the kit acts on.
export const holderOf = item => (item?.heldBy && typeof item.heldBy === 'object' && !Array.isArray(item.heldBy) && typeof item.heldBy.item === 'string' && item.heldBy.item
  ? item.heldBy.item : null);

const RAIL_DEPTH = 740;        // mm between front and rear rails: a common 4-post
const USABLE_BEYOND = 260;     // mm a four-post allows past its rear rail by default
const TWO_POST_USABLE = 1000;  // mm a two-post allows, front rail to the deepest point

const token = () => Math.random().toString(36).slice(2, 10);

export function normalizeFrame(f = {}) {
  const four = f.kind !== 'two-post';
  const railDepth = four ? (Number(f.railDepth) > 0 ? Number(f.railDepth) : RAIL_DEPTH) : null;
  const style = HOLE_STYLES.includes(f.holes?.style) ? f.holes.style : 'square';
  const height = Math.round(Number(f.heightRU));
  return {
    ...unknownOf(f, FRAME_KEYS),
    kind: four ? 'four-post' : 'two-post',
    heightRU: height >= 1 ? height : 42,
    numbering: f.numbering === 'top-down' ? 'top-down' : 'bottom-up',
    holes: {style, thread: style === 'tapped' && THREADS.includes(f.holes?.thread) ? f.holes.thread : null},
    railDepth,
    usableDepth: Number(f.usableDepth) > 0 ? Number(f.usableDepth)
      : four ? railDepth + USABLE_BEYOND : TWO_POST_USABLE,
    ref: f.ref ?? null,
    ...startUOf(f.startU), ...setbackOf(f.setback), ...widthOf(f.width),
  };
}

export const defaultFrame = (kind = 'four-post') => normalizeFrame({kind});

export const newRack = ({name = 'Rack 1', kind = 'four-post'} = {}) =>
  ({id: 'r1', name, frame: defaultFrame(kind), items: [], zeroU: [], cables: []});

export const newDoc = ({name = 'Rack 1', kind = 'four-post'} = {}) =>
  ({format: FORMAT, version: VERSION, id: `doc-${token()}`, racks: [newRack({name, kind})]});

// The next id after the highest one in `list`. The list is everything that
// holds an id of this kind - see itemIdsInUse for what that means for items.
export function nextId(list, prefix) {
  const used = list.filter(x => String(x.id).startsWith(prefix))
    .map(x => Number(String(x.id).slice(prefix.length))).filter(Number.isInteger);
  return `${prefix}${Math.max(0, ...used) + 1}`;
}

// "Rack N" for a new rack: one past the highest N in use, so names never
// repeat - with or without a library to count.
export function nextRackName(names) {
  const used = names.map(n => /^Rack (\d+)$/.exec(String(n))?.[1]).filter(Boolean).map(Number);
  return `Rack ${Math.max(0, ...used) + 1}`;
}

// AN ITEM ID IS NEVER REUSED WHILE A CABLE END, A ROUTE WAYPOINT OR A HOLDER
// NAMES IT. A cable kept when its device was removed (or trimmed by a shrink)
// still names that device's id, and reads "the device was removed"; handing
// the id to the next device placed would land the cable on something
// unrelated. So the ids in use are the items' own and every id a cable end or
// a waypoint of its route names, and the holder an item says it hangs on.
// (model.js cannot import cable-rules.js, which imports this file: the two
// ends are read here.)
const endItems = cables => (Array.isArray(cables) ? cables : [])
  .flatMap(c => [c?.a?.item, c?.b?.item]).filter(id => id != null && id !== '').map(id => ({id: String(id)}));
const waypointItems = cables => (Array.isArray(cables) ? cables : []).flatMap(c => (Array.isArray(c?.route) ? c.route : []))
  .filter(w => !!w && typeof w === 'object' && !Array.isArray(w) && typeof w.item === 'string' && w.item).map(w => ({id: w.item}));
const holderItems = items => items.map(holderOf).filter(id => id !== null).map(id => ({id}));
// A BUNDLE'S TRUNK AND PEEL POINTS name items too (#921): a removed manager's
// id is not handed to the next device while a trunk still names it, so it can
// never resolve to something placed later.
const plainObj = v => !!v && typeof v === 'object' && !Array.isArray(v);
const bundleList = bundles => (Array.isArray(bundles) ? bundles : []).filter(plainObj);
const bundleItems = bundles => bundleList(bundles).flatMap(b => [
  ...(Array.isArray(b.route) ? b.route : []),
  ...(Array.isArray(b.members) ? b.members : []).flatMap(m => (plainObj(m) ? [m.a, m.b] : []))])
  .filter(w => plainObj(w) && typeof w.item === 'string' && w.item).map(w => ({id: w.item}));
export const itemIdsInUse = rack => [...rack.items, ...endItems(rack.cables), ...waypointItems(rack.cables),
  ...holderItems(rack.items), ...bundleItems(rack.bundles)];
// A ZERO-U ID THE SAME WAY (P-0019): a cord kept when its PDU was taken away
// still names the PDU's id, so the next part placed beside the rack is not
// handed it.
export const zeroUIdsInUse = rack => [...(Array.isArray(rack.zeroU) ? rack.zeroU : []).filter(z => typeof z?.id === 'string'),
  ...endItems(rack.cables)];
// A CABLE ID IS NEVER REUSED WHILE A BUNDLE NAMES IT: ids come one past the
// highest, so a removed c9 could be handed to the next cable, and a bundle
// still naming c9 would pick it up.
const memberCables = bundles => bundleList(bundles).flatMap(b => (Array.isArray(b.members) ? b.members : []))
  .filter(m => plainObj(m) && typeof m.cable === 'string' && m.cable).map(m => ({id: m.cable}));
export const cableIdsInUse = rack => [...(rack.cables || []), ...memberCables(rack.bundles)];

// A RACK-FACE MANAGER'S HOST: `on` names the item it bolts over and
// `unit` which of that item's units, from 1 at its bottom. Both or neither;
// settleManagers (managers.js) is what checks them against the catalogue.
const hostOf = ({on, unit}) => (typeof on === 'string' && on && Number.isInteger(unit) && unit >= 1
  ? {on, unit} : {});
export const detached = ({on, unit, ...rest}) => rest;
// ONE RAIL (#926): `side: left | right` on a narrow rack-face part (a finger
// bracket narrower than the 450 mm opening) says which rail it is on, seen
// from its face. Without it the part is across both. fit.js railOf says
// whether the catalogue agrees the part is narrow; the file keeps what it has.
export const SIDES = ['left', 'right'];
const sideOf = side => (SIDES.includes(side) ? {side} : {});

export function withItem(rack, {ref, cfg, ru, face = 'front', turned = false, label = ref,
                                swaps = {}, fields = {}, on, unit, side}) {
  const item = {id: nextId(itemIdsInUse(rack), 'i'), ref, cfg, label, ru,
                face: face === 'rear' ? 'rear' : 'front', turned: !!turned,
                swaps: {...swaps}, fields: structuredClone(fields), ...hostOf({on, unit}), ...sideOf(side)};
  return {rack: {...rack, items: [...rack.items, item]}, item};
}

// ZERO-U PARTS (#926): what stands beside the rack and takes no rack unit (a
// vertical cable manager today, a zero-U PDU next) lives in `rack.zeroU`,
// never in `items`, as
//   {id: 'z1', ref, cfg, label, at, offsetMm, between?}
// `at` is an attachment point of the frame (fit.js attachPoints: left or right
// on a two-post, left-front ... right-rear on a four-post), and also names the
// cable lane beside that upright. `offsetMm` is its bottom, in mm above the
// bottom of the rails; the kit always writes a whole number of U. `between:
// true` says it stands between this rack and the next one, serving both; a
// document holds one rack, so it is drawn and exported beside this one.
// An entry of any other shape is kept as written and left alone: zeroUOf is
// what the kit places, moves, draws and exports.
const plainObject = v => !!v && typeof v === 'object' && !Array.isArray(v);
export const zeroUOf = rack => (Array.isArray(rack?.zeroU) ? rack.zeroU : []).filter(z => plainObject(z)
  && typeof z.id === 'string' && z.id && typeof z.ref === 'string' && z.ref && typeof z.at === 'string' && z.at);
export const zeroUById = (rack, id) => zeroUOf(rack).find(z => z.id === id) ?? null;
// WHAT A CABLE END IS ON (P-0019): a rack item, or a part beside the rack
// whose own slots take a cable end (the outlets of a zero-U PDU). An end is
// `{item, path, view}` either way: `item` is the id of whichever it is, and
// `view` the part's own panel, as on an item. null when neither is there.
export const endHostOf = (rack, id) => (rack?.items || []).find(i => i.id === id) ?? zeroUById(rack, id);
// The face of the rack a part beside it looks out of: a rear upright carries
// its part facing rearward (solids.js zeroUPlacer); a front upright, and
// either upright of a two-post, facing forward. Its own rear panel looks the
// other way.
export const zeroUPane = (z, view = 'front') => {
  const out = /-rear$/.test(String(z?.at)) ? 'rear' : 'front';
  return view === 'rear' ? (out === 'rear' ? 'front' : 'rear') : out;
};
// The pane an end's panel faces on whatever it is on, or null when it is on nothing.
export const endPaneIn = (rack, end) => {
  const it = (rack?.items || []).find(i => i.id === end?.item);
  if (it) return ((end.view === 'rear') === !!it.turned) ? it.face : (it.face === 'front' ? 'rear' : 'front');
  const z = zeroUById(rack, end?.item);
  return z ? zeroUPane(z, end.view === 'rear' ? 'rear' : 'front') : null;
};
// WHAT A ZERO-U PART HANGS ON (version 4, `heldBy: {parts: [id, ...]}`): the
// ids of the zero-U entries that hold it, such as the two brackets of a PDU;
// none for a part that stands on its own.
export const holdersOf = z => (plainObject(z?.heldBy) && Array.isArray(z.heldBy.parts)
  ? z.heldBy.parts.filter(id => typeof id === 'string' && id) : []);
// A part's bottom U and its offset, each from the other: U1 is offset 0.
export const zeroUOffset = ru => Math.round((ru - 1) * RU * 100) / 100;
// THE ONE OWNER OF A ZERO-U PART'S BOTTOM is `offsetMm`, in mm (version 4): fit,
// the solids and so the routes read it here. `zeroUBottom` is the nearest U to
// it, for a label or a lane waypoint, and is never drawn from.
export const zeroUBottomMm = z => Math.max(0, Number(z?.offsetMm) || 0);
export const zeroUBottom = z => Math.max(1, Math.round(zeroUBottomMm(z) / RU) + 1);

export const updateItem = (rack, id, patch) =>
  ({...rack, items: rack.items.map(i => (i.id === id ? {...i, ...patch} : i))});
// A manager on the removed item stays where it is, unhosted: it
// bolts to the rack, not to the device.
export const withoutItem = (rack, id) => ({...rack, items: rack.items.filter(i => i.id !== id)
  .map(i => (i.on === id ? detached(i) : i))});
export const withFrame = (rack, patch) => ({...rack, frame: normalizeFrame({...rack.frame, ...patch})});
export const renamed = (rack, name) => ({...rack, name: String(name)});

// DCIM IMPORT SETTINGS: the names a NetBox or Nautobot
// import needs and a rack does not otherwise know. `site` is NetBox's site and
// Nautobot's location; `role` is the device role. An OPTIONAL field of a rack:
// a rack that was never given them has no `dcim` key at all, so a file written
// before this field existed opens, and saves, exactly as it was. dcimOf reads
// it whatever is there: two trimmed strings.
const plain = v => (v && typeof v === 'object' && !Array.isArray(v) ? v : {});
const word = v => (typeof v === 'string' ? v.trim() : '');
// `netbox` (#945) is the version of NetBox the files are for; "4.6" or later
// writes NetBox's own cable bundles (dcim-rules.js netboxHasBundles). It is
// read only where the rack has it, so a rack without it reads as it did.
export const dcimOf = rack => {
  const had = plain(rack?.dcim);
  return {site: word(had.site), role: word(had.role), ...('netbox' in had ? {netbox: word(had.netbox)} : {})};
};
// Fields of `dcim` this page does not know are kept as they are.
// A key the rack did not have stays missing unless it is given a value: a blank
// site on a rack with no site adds nothing, so saving never invents a field.
export const withDcim = (rack, patch) => {
  const had = plain(rack.dcim), next = {...had};
  for (const key of ['site', 'role', 'netbox']) {
    if (!(key in patch)) continue;
    const v = word(patch[key]);
    if (v || key in had) next[key] = v;
  }
  return !rack.dcim && !Object.keys(next).length ? rack : {...rack, dcim: next};
};

// U numbers are stored bottom-up from 1 always; this is only what a label
// says: counted the way the frame counts, from the number its first unit has
// (`startU`, absent is 1).
export const uLabel = (frame, u) => firstU(frame) - 1 + (frame.numbering === 'top-down' ? frame.heightRU - u + 1 : u);
// A DEVICE'S U, wherever it is named with one: its POSITION, the lowest-numbered
// half unit it fills, counted the way this frame counts - what a DCIM calls a
// device's position, in steps of 0.5. `ru` is its bottom as stored and `units`
// its height in units (fit.js unitsOf); on a bottom-up frame that is the bottom
// itself, on a top-down one the half unit under its top edge. On a 42U top-down
// frame a 0.5U item stored at 12 is at 31.5, and one stored at 12.5 is at 31.
// A height that is missing (null, 0) counts as one unit, as it always did.
// With `startU` it counts from there: a frame that starts at 5 has its bottom
// unit at 5 bottom-up, and its top unit at 5 top-down.
export const positionOf = (frame, ru, units = 1) =>
  firstU(frame) - 1 + (frame.numbering === 'top-down' ? frame.heightRU + 2 - ru - (units > 0 ? units : 1) : ru);
// A position as a person reads it: "U12", "U12.5". It takes the height because
// a top-down label of a half depends on it. uLabel stays for whole units
// (lanes, managers, the rail numbers).
export const uText = (frame, ru, units = 1) => `U${positionOf(frame, ru, units)}`;

// STATES AND READINGS (version 4, docs/rack-file-v4-design.md section 4), on
// an item and on a zero-U entry alike.
// `states` is a map of part path to state name, both text. It is read entry
// by entry: one that is not text for text is dropped, and `said` is told.
// `readings` is {source, at, values} and is kept ONLY WHOLE: without a source
// that is text, a time `at` that can be read, or with `values` that are not a
// map of part path to an object, it moves as written to `readingsAsWritten`,
// as an unusable length moves to `lengthAsWritten`, and nothing draws it.
const isText = v => typeof v === 'string' && v !== '';
export const usableReadings = r => plainRecord(r) && isText(r.source) && isText(r.at) && !Number.isNaN(Date.parse(r.at))
  && (r.values === undefined || (plainRecord(r.values) && Object.values(r.values).every(plainRecord)));
const plainRecord = v => !!v && typeof v === 'object' && !Array.isArray(v);
function readSettings(src, who, said) {
  const out = {};
  if ('states' in src) {
    const kept = {}, dropped = [];
    for (const [k, v] of Object.entries(plainRecord(src.states) ? src.states : {})) (isText(v) ? kept : dropped)[k] = v;
    if (!plainRecord(src.states)) said?.(`The states of ${who} were not a map of part to state, so they were dropped.`);
    else if (Object.keys(dropped).length)
      said?.(`${Object.keys(dropped).join(', ')} on ${who} had a state that is not a name, so ${Object.keys(dropped).length === 1 ? 'it was' : 'they were'} dropped.`);
    if (plainRecord(src.states)) out.states = kept;
  }
  // WHAT A DISPLAY SHOWS (docs/display-content-design.md): a map of part path
  // to its content, read entry by entry as `states` is. An entry that is none
  // of {text: [lines]}, {digits: text}, {image: text} is dropped and said. Whether
  // the part is a display, and can show it, is for rack/displays.js, which can
  // see the device.
  if ('displays' in src) {
    const kept = {}, dropped = [];
    for (const [k, v] of Object.entries(plainRecord(src.displays) ? src.displays : {})) {
      if (k && !shapeRefusal(v)) kept[k] = v; else dropped.push(k);
    }
    if (!plainRecord(src.displays)) said?.(`The displays of ${who} were not a map of part to what it shows, so they were dropped.`);
    else if (dropped.length)
      said?.(`${dropped.join(', ')} on ${who} had content that is not text, digits or an image, so ${dropped.length === 1 ? 'it was' : 'they were'} dropped.`);
    if (plainRecord(src.displays) && Object.keys(kept).length) out.displays = structuredClone(kept);
  }
  // `readings: null` says there are none, and is no key at all
  if (src.readings != null) {
    const r = src.readings;
    if (usableReadings(r)) out.readings = structuredClone(r);
    else {
      out.readingsAsWritten = structuredClone(r);
      const sourced = plainRecord(r) && isText(r.source) && isText(r.at) && !Number.isNaN(Date.parse(r.at));
      said?.(sourced
        ? `The readings of ${who} have values that are not a map of part to what was read there, so they are kept as written and not shown.`
        : `The readings of ${who} have no source or no time that can be read, so they are kept as written and not shown.`);
    }
  } else if (src.readingsAsWritten != null) out.readingsAsWritten = structuredClone(src.readingsAsWritten);
  return out;
}

// A POSITION is a whole unit or a half (version 4): `ru` in steps of 0.5.
export const isPosition = ru => typeof ru === 'number' && Number.isFinite(ru) && Number.isInteger(ru * 2);

function readItem(i, n, said) {
  if (!i || typeof i.ref !== 'string' || !i.ref || !isPosition(i.ru))
    throw new Error(`Item ${n} has no device or no U.`);
  return {...unknownOf(i, ITEM_KEYS), id: String(i.id ?? ''), ref: i.ref, cfg: String(i.cfg ?? ''), label: String(i.label ?? i.ref),
          ru: i.ru, face: i.face === 'rear' ? 'rear' : 'front', turned: !!i.turned,
          swaps: {...(i.swaps || {})}, fields: structuredClone(i.fields || {}),
          ...hostOf({on: i.on == null ? undefined : String(i.on), unit: i.unit}), ...sideOf(i.side), ...setbackOf(i.setback), ...rollKey(i.roll),
          ...readSettings(i, String(i.label ?? i.ref), said)};
}

// The zero-U record as written, with an id given to each object entry that
// has none, or one an earlier entry took (as items are repaired), past every
// id the record declares. Anything else is kept as it is.
function readZeroU(list, said) {
  const taken = list.filter(z => plainObject(z) && typeof z.id === 'string' && z.id).map(z => ({id: z.id}));
  const seen = new Set();
  return list.map(raw => {
    const z = structuredClone(raw);
    if (!plainObject(z)) return z;
    if (typeof z.id !== 'string' || !z.id || seen.has(z.id)) z.id = nextId([...taken, ...[...seen].map(id => ({id}))], 'z');
    seen.add(z.id);
    // what it is set to is read as on an item; where it stands is kept as written
    const {states: _s, readings: _r, readingsAsWritten: _w, displays: _d, ...rest} = z;
    return {...rest, ...readSettings(z, String(z.label ?? z.ref ?? z.id), said)};
  });
}

// Every item needs an id unique within its rack: a missing one (an older
// writer, or a hand-edited file) and a duplicate (two items sharing an id)
// are the same problem. The first item to declare an id keeps it, and the
// cable ends naming that id are its own; a repaired item gets a fresh id,
// past every id an item in the file declares and every id a cable end names
// (`cables`, as written) - so a repair never takes a later item's id, and
// never picks up a cable that was not this item's.
function readItems(list, cables, bundles, said) {
  const taken = [...list.map(i => ({id: String(i?.id ?? '')})), ...endItems(cables), ...bundleItems(bundles)];
  const items = [];
  const seen = new Set();
  list.forEach((i, n) => {
    const it = readItem(i, n + 1, said);
    if (!it.id || seen.has(it.id)) it.id = nextId([...taken, ...items], 'i');
    seen.add(it.id);
    items.push(it);
  });
  return items;
}

// A ROUTE is waypoints in order: {item, via}, an element of a placed device's drawing,
// or {lane, ru}, a lane beside the rails at a U. An entry of neither shape is
// not thrown away: the whole route as written moves to `routeAsWritten`, as a
// length this page cannot use moves to `lengthAsWritten`.
export const isWaypoint = w => w && typeof w === 'object' && !Array.isArray(w) && (
  (typeof w.item === 'string' && w.item && typeof w.via === 'string' && w.via) ||
  (typeof w.lane === 'string' && w.lane && Number.isInteger(w.ru)));
export const readRoute = r => {
  const list = Array.isArray(r) ? r : [];
  const kept = list.filter(isWaypoint).map(w => ('lane' in w ? {lane: w.lane, ru: w.ru} : {item: w.item, via: w.via}));
  return kept.length === list.length ? {route: kept} : {route: kept, routeAsWritten: structuredClone(list)};
};
// Extract readable waypoints from routeAsWritten: if they match the cleaned route,
// the routeAsWritten is still valid (nothing has been edited since it was written).
const readableFromRouteAsWritten = raw => {
  const list = Array.isArray(raw) ? raw : [];
  return list.filter(isWaypoint).map(w => ('lane' in w ? {lane: w.lane, ru: w.ru} : {item: w.item, via: w.via}));
};
const routesEqual = (a, b) => a.length === b.length && a.every((w, i) =>
  ('lane' in w ? 'lane' in b[i] && w.lane === b[i].lane && w.ru === b[i].ru
               : 'item' in b[i] && w.item === b[i].item && w.via === b[i].via));


// CABLES ARE NEVER DROPPED ON LOAD (a cable is never silently
// deleted). A cable that names a missing item, an unknown media or no port at
// all is kept and shown as a loose end; what is normalized is only its shape:
// a unique id, two ends, strings where the page reads strings, a length that
// is a positive number, and a route array. Fields this page does not know are
// kept as they are.
//
// A LENGTH IS KEPT AS WRITTEN. Its unit is the file's own, whatever it is
// ({value: 30, unit: 'cm'} is 30 cm; rewriting the unit would change what the
// value means), and 'm' only when the file states none. A length this page
// cannot use - a value that is not a positive plain decimal, or not an object
// at all - is not thrown away: it moves, whole, to the cable's
// `lengthAsWritten`, so nothing downstream reads a bad number and the file
// still holds what was written. Loading what was saved changes nothing more.
//
// A COLOUR IS READ THE SAME WAY (#1028). `color` is the cable's own colour:
// `#rgb` or `#rrggbb`, kept as lower case `#rrggbb` (cable-geometry.js
// hexColor). A cable with no such key has none, and loads as it always did.
// A `color` that is no colour (a name, a number, an object) moves, whole, to
// `colorAsWritten`, and the cable has no `color`: it is drawn by its ends,
// its type or its media, never in a colour guessed from what was written.
const readEnd = e => ({...(e && typeof e === 'object' && !Array.isArray(e) ? e : {}), item: String(e?.item ?? ''), path: String(e?.path ?? ''),
                       view: e?.view === 'rear' ? 'rear' : 'front'});
// A length is a number, or a string of plain decimal digits: Number() would
// also read "0x10" as 16, "1e3" as 1000 and true as 1. 0 means no usable length.
const lengthValue = v => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && /^\d+(\.\d+)?$/.test(v) ? Number(v) : 0;
  return Number.isFinite(n) && n > 0 ? n : 0;
};
// A CABLE'S `slack` (version 4, docs/rack-file-v4-design.md section 3.3) is a
// list, read entry by entry. An entry is usable when it is an object naming a
// tray (`item` and `via`, non-empty text) or an end (`end`: a or b); `form`,
// when present, is coil, serpentine or spool; `value`, when present, is a
// number above 0 with a `unit` that is non-empty text or absent (metres). At
// most one entry has no value, since only one can take the rest: a second is
// not usable. When any entry is not usable, the usable ones stay in `slack`
// and the list as written moves to `slackAsWritten`; nothing is thrown away.
// A `slack` that is no list moves there whole, and the cable has no `slack`
// key: nothing has been said.
export const SLACK_FORMS = ['coil', 'serpentine', 'spool'];
function readSlack(raw) {
  if (raw === undefined) return {};
  if (!Array.isArray(raw)) return {slackAsWritten: structuredClone(raw)};
  let rest = false;
  const usable = e => {
    if (!plainObj(e)) return false;
    const tray = typeof e.item === 'string' && e.item && typeof e.via === 'string' && e.via;
    if (!tray && e.end !== 'a' && e.end !== 'b') return false;
    if ('form' in e && !SLACK_FORMS.includes(e.form)) return false;
    if ('unit' in e && e.unit != null && !(typeof e.unit === 'string' && e.unit.trim() !== '')) return false;
    if (e.value != null) return typeof e.value === 'number' && Number.isFinite(e.value) && e.value > 0;
    if ('value' in e || rest) return false;      // a value that is null, or a second entry for the rest
    rest = true;
    return true;
  };
  const kept = raw.filter(usable).map(e => structuredClone(e));
  return kept.length === raw.length ? {slack: kept} : {slack: kept, slackAsWritten: structuredClone(raw)};
}

// `bundles`, as written: a repaired cable's fresh id is past every id a bundle
// member names, so it cannot pick up another cable's membership.
export function readCables(list, bundles = []) {
  const declared = [...list.map(c => ({id: String(c?.id ?? '')})), ...memberCables(bundles)];
  const out = [];
  const seen = new Set();
  for (const raw of list) {
    const {length: len, slack: slackRaw, color: colorRaw, ...c} = raw && typeof raw === 'object' ? structuredClone(raw) : {};
    const color = hexColor(colorRaw);
    let id = c.id == null ? '' : String(c.id);
    if (!id || seen.has(id)) id = nextId([...declared, ...out], 'c');
    seen.add(id);
    // A unit is a non-blank string, kept exactly as written, or it is not
    // stated (metres). Anything else - an object, a number, blank - is not a
    // unit, and the length it came with is not usable.
    const unitOk = len?.unit == null || (typeof len.unit === 'string' && len.unit.trim() !== '');
    const value = len && typeof len === 'object' && !Array.isArray(len) && unitOk ? lengthValue(len.value) : 0;
    const length = value
      ? {...len, value, unit: len.unit ?? 'm', source: String(len.source ?? 'entered')}
      : null;
    const routeEdited = c.routeEdited;
    const incomingRouteAsWritten = c.routeAsWritten;
    delete c.routeEdited; delete c.routeAsWritten;

    // readRoute normalizes the route, potentially producing its own routeAsWritten.
    // If it does, use that. Otherwise, if the incoming routeAsWritten is an array
    // and its readable waypoints equal the normalized route, keep it (it's still valid).
    const {route, routeAsWritten: newRouteAsWritten} = readRoute(c.route);
    let routeAsWritten = newRouteAsWritten;
    if (!routeAsWritten && Array.isArray(incomingRouteAsWritten)) {
      const readable = readableFromRouteAsWritten(incomingRouteAsWritten);
      if (routesEqual(readable, route)) {
        routeAsWritten = structuredClone(incomingRouteAsWritten);
      }
    }

    out.push({...c, id, a: readEnd(c.a), b: readEnd(c.b), media: String(c.media ?? ''),
              purpose: String(c.purpose ?? ''), label: String(c.label ?? ''),
              route, ...(routeAsWritten ? {routeAsWritten} : {}),
              ...(routeEdited === true ? {routeEdited: true} : {}), ...readSlack(slackRaw),
              ...(color ? {color} : colorRaw == null ? {} : {colorAsWritten: colorRaw}),
              ...(length ? {length} : len == null ? {} : {lengthAsWritten: len})});
  }
  return out;
}

// READ A FILE, OR REFUSE IT WITH A SENTENCE. A newer file than this page knows
// is refused whole: reading the parts it understands and dropping the rest
// would hand back a rack that looks complete and is not.
// `notes`, when given, is an array each repair settleBundles makes is pushed
// onto, one sentence each, naming its rack. None is kept in the document.
export function parseDoc(input, {notes} = {}) {
  let d = typeof input === 'string' ? JSON.parse(input) : input;
  if (!d || d.format !== FORMAT) throw new Error('This is not a Portrayal rack file.');
  if (!Number.isInteger(d.version) || d.version < 1) throw new Error('This rack file has no valid version.');
  if (d.version > VERSION)
    throw new Error(`This rack file is version ${d.version}; this reader supports up to version ${VERSION}.`);
  for (let v = d.version; v < VERSION; v++) d = MIGRATIONS[v - 1](d);
  if (!Array.isArray(d.racks) || !d.racks.length) throw new Error('This rack file holds no rack.');
  return {
    ...unknownOf(d, DOC_KEYS),
    format: FORMAT, version: VERSION,
    id: typeof d.id === 'string' && d.id ? d.id : `doc-${token()}`,
    racks: d.racks.map((r, k) => {
      const bundles = Array.isArray(r.bundles) ? r.bundles : null;
      const said = text => { if (Array.isArray(notes)) notes.push(`${String(r.name ?? 'Rack')}: ${text}`); };
      const items = readItems(r.items || [], r.cables, bundles, said);
      const zeroU = readZeroU(Array.isArray(r.zeroU) ? r.zeroU : [], said);
      const cables = readCables(Array.isArray(r.cables) ? r.cables : [], bundles ?? []);
      const rack = {
        ...unknownOf(r, RACK_KEYS),
        id: String(r.id ?? `r${k + 1}`), name: String(r.name ?? 'Rack'),
        frame: normalizeFrame(r.frame), items, zeroU, cables,
        // Optional, and only when the file has it (dcimOf): no version bump, since a
        // page that does not know the field reads the rack whole and loses two names.
        ...(r.dcim && typeof r.dcim === 'object' && !Array.isArray(r.dcim)
          ? {dcim: {...structuredClone(r.dcim), ...Object.fromEntries(Object.entries(dcimOf(r)).filter(([k]) => k in r.dcim))}} : {}),
        // Optional too (#921), and only when the file has it: a rack that was
        // never given a bundle saves as it was.
        ...(bundles ? {bundles: readBundles(bundles, [...items, ...cables, ...zeroU.filter(plainObj)], said)} : {}),
      };
      // The references are checked here, so a reader that only parses gets
      // the same consistent rack as the editor.
      const s = settleBundles(rack);
      if (Array.isArray(notes)) notes.push(...s.notes.map(t => `${rack.name}: ${t}`));
      return s.rack;
    }),
  };
}

// ── bundles (#921, docs/cable-bundles-design.md) ─────────────────────────
// A rack's optional `bundles`, each
//   {id, number, label, members: [{cable, a?, b?}], route: [waypoint], straps?}
// Membership lives on the bundle and only there: a cable carries no `bundle`
// key, so the two can never disagree. bundles.js has the rules; the record and
// its repairs are here, because parseDoc runs them and they need no catalogue.
export const bundlesOf = rack => (Array.isArray(rack?.bundles) ? rack.bundles : []);
export const bundleName = b => (b.label ? b.label : `Bundle ${b.number}`);
export const STRAP_UNITS = ['in', 'mm'];
export const isStrapSpacing = e => plainObj(e) && typeof e.value === 'number' && Number.isFinite(e.value)
  && e.value > 0 && STRAP_UNITS.includes(e.unit);
// A FRESH BUNDLE ID is past every id in the rack - the items', the cables', the
// parts' beside it and the bundles' - so a new bundle never takes an id
// another thing has, and an id names one thing.
export const freshBundleId = list => nextId(list.map(x => ({id: String(x.id)})), 'b');
const rackIds = rack => [...rack.items, ...(rack.cables || []), ...(Array.isArray(rack.zeroU) ? rack.zeroU : []).filter(plainObj)];
export const bundleIdFor = rack => freshBundleId([...rackIds(rack), ...bundlesOf(rack)]);

// THE SHAPES, as for cables: an entry that is not an object is no bundle; one
// with no usable id or a repeated one gets a fresh id; a member that is not
// {cable: <string>} is dropped; a number that is not a whole number from 1
// goes past the highest in use; the trunk is read as a cable's route is, so an
// unreadable entry keeps the trunk as written in `routeAsWritten`. A `straps`
// is kept when it has a key that says something: `every` (null, or {value
// above 0, unit in or mm}), or `breakout` or `anchors` (true or false, version
// 4). One of those three that is not valid is left out of it, and a `straps`
// left with none of them says nothing the defaults do not, and is dropped.
// Unknown fields are kept.
const STRAP_KINDS = ['breakout', 'anchors'];
function readStraps(straps) {
  if (!plainObj(straps)) return null;
  const out = {...straps};
  if ('every' in out && !(out.every === null || isStrapSpacing(out.every))) delete out.every;
  for (const k of STRAP_KINDS) if (k in out && typeof out[k] !== 'boolean') delete out[k];
  return ['every', ...STRAP_KINDS].some(k => k in out) ? out : null;
}

function readBundles(list, others, said) {
  const objs = list.filter(plainObj);
  const declared = objs.filter(b => typeof b.id === 'string' && b.id).map(b => ({id: b.id}));
  const whole = n => Number.isInteger(n) && n >= 1;
  let top = Math.max(0, ...objs.map(b => b.number).filter(whole));
  const seen = new Set(), out = [];
  for (const raw of objs) {
    const {straps, routeAsWritten: incoming, ...b} = structuredClone(raw);
    let id = typeof b.id === 'string' && b.id ? b.id : '';
    if (!id || seen.has(id)) id = freshBundleId([...others, ...declared, ...out]);
    seen.add(id);
    // A peel point that is no waypoint is dropped: the member then rides to
    // that end, as it does past a stale one.
    const members = (Array.isArray(b.members) ? b.members : []).filter(m => plainObj(m) && typeof m.cable === 'string' && m.cable)
      .map(m => { const out = {...m}; for (const k of ['a', 'b']) if (k in out && !isWaypoint(out[k])) delete out[k];
        else if (k in out) out[k] = 'lane' in out[k] ? {lane: out[k].lane, ru: out[k].ru} : {item: out[k].item, via: out[k].via};
        return out; });
    const r = readRoute(b.route);
    // A trunk kept as written stays kept while its readable waypoints are
    // still the trunk, as a cable's route does, so a save and a reload keep it.
    const asWritten = r.routeAsWritten
      ?? (Array.isArray(incoming) && routesEqual(readableFromRouteAsWritten(incoming), r.route) ? incoming : null);
    const kept = readStraps(straps);
    // what of its straps said nothing usable is dropped, and said
    if (straps !== undefined) {
      const lost = !plainObj(straps) ? ['straps'] : ['every', ...STRAP_KINDS].filter(k => k in straps && !(kept && k in kept));
      if (lost.length) said?.(`${b.label ? b.label : `Bundle ${whole(b.number) ? b.number : id}`} had ${lost.join(', ')} that could not be read, so ${lost.length === 1 ? 'it was' : 'they were'} dropped.`);
    }
    out.push({...b, id, number: whole(b.number) ? b.number : ++top, label: String(b.label ?? ''), members, route: r.route,
              ...(asWritten ? {routeAsWritten: asWritten} : {}), ...(kept ? {straps: kept} : {})});
  }
  return out;
}

// THE ONE WAY A CABLE LEAVES ITS BUNDLE when the cable leaves the rack: every
// edit that drops cables (cable-rules.js withoutCable, withoutCablesOf, and
// bundles.js withoutCables, which also says so) takes them out of their
// bundles here, so a bundle never names a cable that is gone and a later cable
// handed its id never picks up its membership.
export function withoutMembers(rack, ids) {
  if (!Array.isArray(rack.bundles)) return rack;
  const gone = new Set(ids);
  let changed = false;
  const bundles = rack.bundles.map(b => {
    if (!b.members.some(m => gone.has(m.cable))) return b;
    changed = true;
    return {...b, members: b.members.filter(m => !gone.has(m.cable))};
  });
  return changed ? {...rack, bundles} : rack;
}

// THE REFERENCES. Pure and idempotent; it reads only the rack's own items,
// cables, parts and bundles, so it needs no catalogue. Each repair gives a
// sentence, and a second run finds nothing to repair:
// - a bundle whose id is also an item's, a cable's or a part's gets a fresh one;
// - a member naming no cable is dropped, and a cable named twice in one bundle
//   is kept once;
// - a cable named by two bundles stays in the first;
// - a number used twice stays with the first, and the second is renumbered.
// Nothing else is dropped, and a bundle left with no members is kept.
export function settleBundles(rack) {
  if (!Array.isArray(rack?.bundles)) return {rack, notes: []};
  const notes = [];
  const others = rackIds(rack), otherIds = new Set(others.map(x => String(x.id)));
  const cableIds = new Set((rack.cables || []).map(c => c.id));
  const owner = new Map(), numbers = new Map(), out = [];
  let top = Math.max(0, ...rack.bundles.map(b => b.number).filter(Number.isInteger));
  let changed = false;
  for (const b0 of rack.bundles) {
    let b = b0;
    if (otherIds.has(b.id)) {
      const id = freshBundleId([...others, ...rack.bundles, ...out]);
      notes.push(`${b.id} is also the id of a device, a part or a cable, so ${bundleName(b)} is now ${id}.`);
      b = {...b, id};
    }
    const kept = [], here = new Set();
    for (const m of b.members) {
      if (!cableIds.has(m.cable)) notes.push(`${bundleName(b)} named ${m.cable}, which is not a cable in the rack, so it was taken out.`);
      else if (here.has(m.cable)) notes.push(`${bundleName(b)} named ${m.cable} twice; it is kept once.`);
      else if (owner.has(m.cable)) {
        const first = bundleName(owner.get(m.cable));
        notes.push(`${m.cable} is in ${first} and ${bundleName(b)}, so it stays in ${first}.`);
      } else { here.add(m.cable); kept.push(m); }
    }
    if (kept.length !== b.members.length) b = {...b, members: kept};
    if (numbers.has(b.number)) {
      const n = b.number;
      b = {...b, number: ++top};
      notes.push(`${numbers.get(n).id} and ${b.id} were both Bundle ${n}, so ${b.id} is now Bundle ${b.number}.`);
    }
    numbers.set(b.number, b);
    for (const m of b.members) owner.set(m.cable, b);
    if (b !== b0) changed = true;
    out.push(b);
  }
  return {rack: changed ? {...rack, bundles: out} : rack, notes};
}

export const serialize = doc => JSON.stringify(doc, null, 2);
