// THE RACK FILE. Pure data: no DOM, no fetch, no rendering, so the
// page, the library, the exports and `node --test` all read one definition.
//
// A document holds an ARRAY of racks although the page edits one: rows of
// racks come later, and a file written today must still open then. Every
// edit here returns a new object - the page autosaves whatever it last
// committed, and a shared, mutated rack is how a save would catch half an edit.

export const FORMAT = 'portrayal-rack';
export const VERSION = 2;
export const THREADS = ['12-24', '10-32', 'M6'];
// MIGRATIONS[n - 1] takes a version-n document to version n + 1.
//   1 -> 2: rack-face managers (`on`, `unit` on an item). Nothing in a
//   version-1 file changes; the bump is so an older page refuses a file
//   holding a manager instead of drawing it as a 1U device over its host.
export const MIGRATIONS = [d => ({...d, version: 2})];

const RAIL_DEPTH = 740;        // mm between front and rear rails: a common 4-post
const USABLE_BEYOND = 260;     // mm a four-post allows past its rear rail by default
const TWO_POST_USABLE = 1000;  // mm a two-post allows, front rail to the deepest point

const token = () => Math.random().toString(36).slice(2, 10);

export function normalizeFrame(f = {}) {
  const four = f.kind !== 'two-post';
  const railDepth = four ? (Number(f.railDepth) > 0 ? Number(f.railDepth) : RAIL_DEPTH) : null;
  const style = f.holes?.style === 'tapped' ? 'tapped' : 'square';
  const height = Math.round(Number(f.heightRU));
  return {
    kind: four ? 'four-post' : 'two-post',
    heightRU: height >= 1 ? height : 42,
    numbering: f.numbering === 'top-down' ? 'top-down' : 'bottom-up',
    holes: {style, thread: style === 'tapped' && THREADS.includes(f.holes?.thread) ? f.holes.thread : null},
    railDepth,
    usableDepth: Number(f.usableDepth) > 0 ? Number(f.usableDepth)
      : four ? railDepth + USABLE_BEYOND : TWO_POST_USABLE,
    ref: f.ref ?? null,
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

// AN ITEM ID IS NEVER REUSED WHILE A CABLE END NAMES IT. A cable kept when its
// device was removed (or trimmed by a shrink) still names that device's id,
// and reads "the device was removed"; handing the id to the next device
// placed would land the cable on something unrelated. So the ids in use are
// the items' own and every id a cable end names. (model.js cannot import
// cable-rules.js, which imports this file: the two ends are read here.)
const endItems = cables => (Array.isArray(cables) ? cables : [])
  .flatMap(c => [c?.a?.item, c?.b?.item]).filter(id => id != null && id !== '').map(id => ({id: String(id)}));
export const itemIdsInUse = rack => [...rack.items, ...endItems(rack.cables)];

// A RACK-FACE MANAGER'S HOST: `on` names the item it bolts over and
// `unit` which of that item's units, from 1 at its bottom. Both or neither;
// settleManagers (managers.js) is what checks them against the catalogue.
const hostOf = ({on, unit}) => (typeof on === 'string' && on && Number.isInteger(unit) && unit >= 1
  ? {on, unit} : {});
export const detached = ({on, unit, ...rest}) => rest;

export function withItem(rack, {ref, cfg, ru, face = 'front', turned = false, label = ref,
                                swaps = {}, fields = {}, on, unit}) {
  const item = {id: nextId(itemIdsInUse(rack), 'i'), ref, cfg, label, ru,
                face: face === 'rear' ? 'rear' : 'front', turned: !!turned,
                swaps: {...swaps}, fields: structuredClone(fields), ...hostOf({on, unit})};
  return {rack: {...rack, items: [...rack.items, item]}, item};
}

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
export const dcimOf = rack => ({site: word(plain(rack?.dcim).site), role: word(plain(rack?.dcim).role)});
// Fields of `dcim` this page does not know are kept as they are.
// A key the rack did not have stays missing unless it is given a value: a blank
// site on a rack with no site adds nothing, so saving never invents a field.
export const withDcim = (rack, patch) => {
  const had = plain(rack.dcim), next = {...had};
  for (const key of ['site', 'role']) {
    if (!(key in patch)) continue;
    const v = word(patch[key]);
    if (v || key in had) next[key] = v;
  }
  return !rack.dcim && !Object.keys(next).length ? rack : {...rack, dcim: next};
};

// U numbers are stored bottom-up always; this is only what a label says.
export const uLabel = (frame, u) => (frame.numbering === 'top-down' ? frame.heightRU - u + 1 : u);
// A DEVICE'S U, wherever it is named with one: its POSITION, the lowest-numbered
// U it covers, counted the way this frame counts - what a DCIM calls a device's
// position. `ru` is its bottom U as stored and `u` its height; on a bottom-up
// frame that is the bottom U's own label, on a top-down one the top U's.
export const positionOf = (frame, ru, u = 1) => Math.min(uLabel(frame, ru), uLabel(frame, ru + Math.max(1, u) - 1));

function readItem(i, n) {
  if (!i || typeof i.ref !== 'string' || !i.ref || !Number.isInteger(i.ru))
    throw new Error(`Item ${n} has no device or no U.`);
  return {id: String(i.id ?? ''), ref: i.ref, cfg: String(i.cfg ?? ''), label: String(i.label ?? i.ref),
          ru: i.ru, face: i.face === 'rear' ? 'rear' : 'front', turned: !!i.turned,
          swaps: {...(i.swaps || {})}, fields: structuredClone(i.fields || {}),
          ...hostOf({on: i.on == null ? undefined : String(i.on), unit: i.unit})};
}

// Every item needs an id unique within its rack: a missing one (an older
// writer, or a hand-edited file) and a duplicate (two items sharing an id)
// are the same problem. The first item to declare an id keeps it, and the
// cable ends naming that id are its own; a repaired item gets a fresh id,
// past every id an item in the file declares and every id a cable end names
// (`cables`, as written) - so a repair never takes a later item's id, and
// never picks up a cable that was not this item's.
function readItems(list, cables) {
  const taken = [...list.map(i => ({id: String(i?.id ?? '')})), ...endItems(cables)];
  const items = [];
  const seen = new Set();
  list.forEach((i, n) => {
    const it = readItem(i, n + 1);
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
const readRoute = r => {
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
const readEnd = e => ({...(e && typeof e === 'object' && !Array.isArray(e) ? e : {}), item: String(e?.item ?? ''), path: String(e?.path ?? ''),
                       view: e?.view === 'rear' ? 'rear' : 'front'});
// A length is a number, or a string of plain decimal digits: Number() would
// also read "0x10" as 16, "1e3" as 1000 and true as 1. 0 means no usable length.
const lengthValue = v => {
  const n = typeof v === 'number' ? v : typeof v === 'string' && /^\d+(\.\d+)?$/.test(v) ? Number(v) : 0;
  return Number.isFinite(n) && n > 0 ? n : 0;
};
export function readCables(list) {
  const declared = list.map(c => ({id: String(c?.id ?? '')}));
  const out = [];
  const seen = new Set();
  for (const raw of list) {
    const {length: len, ...c} = raw && typeof raw === 'object' ? structuredClone(raw) : {};
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
              ...(routeEdited === true ? {routeEdited: true} : {}),
              ...(length ? {length} : len == null ? {} : {lengthAsWritten: len})});
  }
  return out;
}

// READ A FILE, OR REFUSE IT WITH A SENTENCE. A newer file than this page knows
// is refused whole: reading the parts it understands and dropping the rest
// would hand back a rack that looks complete and is not.
export function parseDoc(input) {
  let d = typeof input === 'string' ? JSON.parse(input) : input;
  if (!d || d.format !== FORMAT) throw new Error('This is not a Portrayal rack file.');
  if (!Number.isInteger(d.version) || d.version < 1) throw new Error('This rack file has no valid version.');
  if (d.version > VERSION)
    throw new Error(`This rack file is version ${d.version}; this page reads up to version ${VERSION}. Reload to get the newer page.`);
  for (let v = d.version; v < VERSION; v++) d = MIGRATIONS[v - 1](d);
  if (!Array.isArray(d.racks) || !d.racks.length) throw new Error('This rack file holds no rack.');
  return {
    format: FORMAT, version: VERSION,
    id: typeof d.id === 'string' && d.id ? d.id : `doc-${token()}`,
    racks: d.racks.map((r, k) => ({
      id: String(r.id ?? `r${k + 1}`), name: String(r.name ?? 'Rack'),
      frame: normalizeFrame(r.frame),
      items: readItems(r.items || [], r.cables),
      zeroU: Array.isArray(r.zeroU) ? structuredClone(r.zeroU) : [],
      cables: readCables(Array.isArray(r.cables) ? r.cables : []),
      // Optional, and only when the file has it (dcimOf): no version bump, since a
      // page that does not know the field reads the rack whole and loses two names.
      ...(r.dcim && typeof r.dcim === 'object' && !Array.isArray(r.dcim)
        ? {dcim: {...structuredClone(r.dcim), ...Object.fromEntries(Object.entries(dcimOf(r)).filter(([k]) => k in r.dcim))}} : {}),
    })),
  };
}

export const serialize = doc => JSON.stringify(doc, null, 2);
