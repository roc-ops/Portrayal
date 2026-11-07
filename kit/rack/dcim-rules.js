// WHAT A DCIM IMPORT KIT SAYS, as data. Pure: no DOM,
// no fetch, so `node --test` covers every rule the NetBox and Nautobot kits
// follow: what a port is called in a type file, which rows a file may hold,
// and what the README says of the rest. The Rack Builder's exports
// (the page that builds the files) fetch the type files and the faces, and
// ask here.

import {endName, lengthParts, portPathOf} from './cable-rules.js';
import {hexColor} from './cable-geometry.js';
import {cableFindings, TARGET_NAME, DCIM_LIMITS, charCount, cutTo, isoDate, flat} from './export-data.js';
import {bundleOfCable, bundleName, bundlesOf} from './bundles.js';
import {andList} from './bundle-route.js';
import {fibrePorts} from './ports.js';
export {DCIM_LIMITS, flat};

// ── names a kit can write ───────────────────────────────────────────────
// A rack file is anyone's JSON: a name in it may hold a line break or another
// control character, which a text field on the page never gives. In a README
// such a name would start a line of its own ("Step 6: run this"), and in a CSV
// it would be a cell an importer may read as two rows. So a run of control
// characters (C0, DEL, C1, and the Unicode line and paragraph separators) is
// written as ONE space, in every name a kit writes (flat, export-data.js, which
// uniqueNames applies to a device's name too: its label and its id suffix).
// A name as it was, with what could not be shown spelled out ("R1\nStep 6").
const escaped = s => JSON.stringify(String(s)).replace(/[\u007f-\u009f\u2028\u2029]/g,
  c => `\\u${c.charCodeAt(0).toString(16).padStart(4, '0')}`);

// THE RACK AS A KIT NAMES IT: the rack's name, each device's label, each
// cable's label and the import settings, with flat() applied. Everything a kit
// writes is built from this rack, so the README, every CSV cell and the zip's
// own name agree. `notes` has one line for each name that changed, naming the
// original (escaped) and what is written; a rack with nothing to change comes
// back as it is, with no notes. (A cable with no label is named by its id,
// which cableImportRows cleans where it writes it; kitReadme flattens every
// paragraph it is handed, whatever is in it.)
export function kitNames(rack) {
  const notes = [];
  const fix = (what, v) => {
    if (typeof v !== 'string' || flat(v) === v) return v;
    notes.push(`${what} ${escaped(v)} is written as "${flat(v)}": a line break or another control character in a name is written as a space.`);
    return flat(v);
  };
  const same = (a, b, keys) => keys.every(k => a[k] === b[k]);
  const name = fix("The rack's name", rack.name);
  const had = rack.dcim && typeof rack.dcim === 'object' && !Array.isArray(rack.dcim) ? rack.dcim : null;
  const dcim = had && {...had, site: fix('The site or location', had.site), role: fix('The device role', had.role)};
  const items = (rack.items || []).map(i => { const label = fix('The device label', i.label); return label === i.label ? i : {...i, label}; });
  const cables = (rack.cables || []).map(c => { const label = fix('The cable label', c.label); return label === c.label ? c : {...c, label}; });
  if (!notes.length) return {rack, notes};
  return {rack: {...rack, name, ...(had ? {dcim: same(dcim, had, ['site', 'role']) ? had : dcim} : {}),
                 ...(rack.items ? {items} : {}), ...(rack.cables ? {cables} : {})}, notes};
}

// ── a type file's own names ─────────────────────────────────────────────
// The sections of a device-type or module-type YAML that hold cable ends, in
// the order a name is looked up, with the type a DCIM gives an end found there.
export const SECTIONS = [
  ['interfaces', 'dcim.interface'], ['front-ports', 'dcim.frontport'], ['rear-ports', 'dcim.rearport'],
  ['console-ports', 'dcim.consoleport'], ['console-server-ports', 'dcim.consoleserverport'],
  ['power-ports', 'dcim.powerport'], ['power-outlets', 'dcim.poweroutlet']];

// A double-quoted YAML value is read as JSON when it is JSON; a YAML-only
// escape (\e, \x1b, a line fold) is not, and one odd value must not fail a
// whole type read, so it falls back to the text between the quotes.
const unquote = v => {
  if (/^'.*'$/.test(v)) return v.slice(1, -1).replace(/''/g, "'");
  if (/^".*"$/.test(v)) {
    try { return JSON.parse(v); } catch { return v.slice(1, -1); }
  }
  return v;
};

// THE NAME LISTS OF ONE TYPE FILE, read as text: the exporter writes every
// component as "  - name: X" under a top-level "section:" line, with its other
// fields indented beneath, so no YAML library is needed (the site has none).
// `sections` holds each known section's names in file order; `bays` each
// module bay's name and position; `model` and `manufacturer` the identity
// lines, as the file writes them.
export function typeLists(text) {
  const sections = Object.fromEntries(SECTIONS.map(([s]) => [s, []]));
  const bays = [], head = {};
  let section = null, bay = null;
  for (const line of String(text ?? '').split(/\r?\n/)) {
    const top = line.match(/^([A-Za-z_][\w-]*):\s*(.*?)\s*$/);
    if (top) {
      section = top[2] === '' ? top[1] : null;
      bay = null;
      if ((top[1] === 'manufacturer' || top[1] === 'model') && !(top[1] in head)) head[top[1]] = unquote(top[2]);
      continue;
    }
    if (!section) continue;
    const item = line.match(/^  - name:\s*(.*?)\s*$/);
    if (item) {
      const name = unquote(item[1]);
      bay = null;
      if (section === 'module-bays') { bay = {name, position: ''}; bays.push(bay); }
      else if (Object.hasOwn(sections, section)) sections[section].push(name);
      continue;
    }
    const pos = bay && line.match(/^    position:\s*(.*?)\s*$/);
    if (pos) bay.position = unquote(pos[1]);
  }
  return {manufacturer: head.manufacturer ?? null, model: head.model ?? null, sections, bays};
}

const TYPE_OF = Object.fromEntries(SECTIONS);
// A name's section and end type in one type file, first section first.
function findName(lists, name) {
  for (const [section, type] of SECTIONS) if (lists.sections[section].includes(name)) return {section, type};
  return null;
}
// The module bay a drawing's bay id is: the one whose POSITION is that id. A
// bay's name is for display ("Fan 1", "Front 0"); its position is what a
// DCIM puts in place of {module}.
export const bayAt = (lists, position) => lists?.bays.find(b => b.position === position) ?? null;

const MODULE = '/module/';

// A MODULE'S BAY BY THE ID A DRAWING GIVES IT. The id is the last step of the
// position a type file writes: NetBox `{module}/slot-1`, Nautobot `drawer/slot-1`
// or a plain `mic0`. A bay with a blank position (Nautobot's pass-through) is
// found by its name.
const nestedBayAt = (lists, id) =>
  lists?.bays.find(b => b.position.split('/').pop() === id && b.position !== '')
  ?? lists?.bays.find(b => b.position === '' && b.name === id) ?? null;

// A NAME A TYPE FILE WRITES, with its tokens filled in. `{module}` is the
// position of the bay the module sits in, `{module.parent}` the position of the
// bay the module above it sits in, and so on up. `positions` are the bays'
// positions from the device's bay down, as they are installed; a blank one is
// skipped, as Nautobot skips it when it names a port (#917). Null when a token
// reaches above the device's bay.
const TOKEN = /\{module((?:\.parent)*)\}/g;
export function renderName(template, positions) {
  const kept = positions.filter(Boolean);
  let above = false;
  const name = String(template).replace(TOKEN, (_, up) => {
    const at = kept.length - 1 - up.length / '.parent'.length;
    if (at < 0) above = true;
    return kept[at] ?? '';
  });
  return above ? null : name;
}
// The name a type file lists for a port called `name` on the module, whatever
// chain of tokens it puts in front: `{module}/1`, `{module.parent}/{module}/1`.
const HEAD = /^(?:\{module(?:\.parent)*\}\/)+$/;
const listedAs = (listed, name) => listed.find(t => t.endsWith(`/${name}`) && HEAD.test(t.slice(0, -name.length)));

// WHAT IS SEATED AT A BAY PATH, level by level (#1024). `bayPath` is
// `<bay>` for a bay of the device and `<bay>/module/<bay>` for a bay of the
// module in it, to any depth. Each level's bay is found in the type file of
// the module installed one level up, and its position is worked out as the DCIM
// works it out: NetBox puts the parent's position in for `{module}`, Nautobot
// copies the position as written. Returns {ok: true, bay, positions, names,
// module}, the bay of the last level, every level's position and bay name and
// the module type seated at the last, or {ok: false, reason}.
function seatChain(bayPath, device, moduleAt) {
  const ids = bayPath.split(MODULE), positions = [], names = [];
  let lists = device, bay = null, path = '';
  for (const [k, id] of ids.entries()) {
    if (k) {
      lists = moduleAt(path);
      if (!lists) return {ok: false, reason: `what is seated in ${path} has no module type`};
    }
    bay = k ? nestedBayAt(lists, id) : bayAt(lists, id);
    if (!bay) return {ok: false, reason: `the ${k ? 'module' : 'device'} type ${lists.model} has no module bay at position ${id}`};
    positions.push(k ? bay.position.replaceAll('{module}', positions[k - 1]) : bay.position);
    names.push(bay.name);
    path = k ? `${path}${MODULE}${id}` : id;
  }
  const module = moduleAt(bayPath);
  if (!module) return {ok: false, reason: `what is seated in ${bayPath} has no module type`};
  return {ok: true, bay, positions, names, module};
}

// WHAT A CABLE END IS CALLED IN THE DCIM, and which kind of component it is.
// Never built by convention alone: the name must be in the matched type
// file's own lists, and the list it is in gives the type.
//   path      the end's port path on the drawing ("port-1", "slot-2/module/p0")
//   device    typeLists of the item's device type, or null when it has none
//   moduleAt  bay path -> typeLists of the module type seated there, or null:
//             the path of a bay of the device is its id (`drawer`), that of a
//             bay of a module in it the drawing's own (`drawer/module/slot-1`)
//   consoles  the paths of the console ports the device's drawing has
//   ports     ports.js fibrePorts for the end, or null: the fibre ports the
//             part at the path is in its module's type (below)
// Returns {ok: true, name, type}, or {ok: false, reason}: a phrase with no
// period, for "Cable X is not in this file: end A, <end>, <reason>."
//
// A FIBRE PORT OF A SEATED MODULE IS NOT NAMED BY ITS PART (#1020). A panel's
// duplex adapter lc01 is the front ports 1 and 2, one per fibre; its back b01
// is the rear port B01-1; a cassette's mtp is MTP-1. `ports` says which, from
// what the build published for the module (the exporter's own walk), and each
// name must still be in the matched type file's list of that kind, so a type
// file a target was given without those ports leaves the cable out, with the
// reason. Such an end answers `names` too: every port it lands on, in
// position order, `name` being the first. An end with no `ports` (a cage, a
// jack, a part the build published nothing for) is looked up by its own id.
//
// A MODULE INSIDE A MODULE (#1024) is named through every level. Its bay is
// found in the type file of the module one level up, its position is worked
// out as the DCIM works it out (seatChain), and the type file's own name for
// the port has its `{module}` and `{module.parent}` filled in (renderName): a
// Fibrain panel in the XCU10 drawer's slot-1, the drawer in the bay `drawer`,
// has its adapter's port `drawer/slot-1/1` on both targets.
export function resolveEnd({path, device, moduleAt = () => null, consoles = [], ports = null}) {
  if (!device) return {ok: false, reason: 'its device has no device type'};
  const p = String(path), at = p.indexOf(MODULE);
  if (at < 0) {
    const hit = findName(device, p);
    if (hit) return {ok: true, name: p, type: hit.type};
    if (consoles.includes(p)) {
      const listed = device.sections['console-ports'];
      if (listed.includes(`Console (${p})`)) return {ok: true, name: `Console (${p})`, type: 'dcim.consoleport'};
      if (listed.length === 1 && consoles.length === 1) return {ok: true, name: listed[0], type: 'dcim.consoleport'};
      return {ok: false, reason: `the device type ${device.model} does not say which of its console ports ${p} is`};
    }
    return {ok: false, reason: `the device type ${device.model} lists no port named ${p}`};
  }
  // THE LAST `/module/` ENDS THE BAY: a module inside a module is reached
  // through each level's installed module (#1024), not left out.
  const cut = p.lastIndexOf(MODULE), bayPath = p.slice(0, cut), leaf = p.slice(cut + MODULE.length);
  const seat = seatChain(bayPath, device, moduleAt);
  if (!seat.ok) return seat;
  const {bay, positions, module} = seat;
  // the name a port has once installed: the type file's own, its tokens filled in
  const named = (section, port) => {
    const listed = listedAs(module.sections[section], port);
    return listed == null ? null : renderName(listed, positions);
  };
  if (ports?.sections?.length) {
    if (ports.sections.length > 1)
      return {ok: false, reason: `${leaf} is ${andList(ports.sections.map(([s]) => KIND[TYPE_OF[s]] ?? s))} in the module type ${module.model}, and one end of a cable is one kind of port`};
    const [section, own] = ports.sections[0], type = TYPE_OF[section];
    const gone = type ? own.find(n => named(section, n) == null) : own[0];
    if (gone != null) return {ok: false, reason: `the module type ${module.model} lists no ${KIND[type] ? KIND[type].replace(/^an? /, '') : 'port'} named {module}/${gone}`};
    const names = own.map(n => named(section, n));
    return {ok: true, name: names[0], names, type, bay};
  }
  for (const [section, type] of SECTIONS) {
    const name = named(section, leaf);
    if (name != null) return {ok: true, name, type, bay};
  }
  return {ok: false, reason: `the module type ${module.model} lists no port named {module}/${leaf}`};
}

// resolveEnd FOR EVERY END OF ONE RACK, with the catalogue asked for each
// end's fibre ports: what a page hands cableImportRows as `resolve`.
//   ctx        {slotsOf, compByRef}, what `catalog.js` loadSlots returns
//   deviceOf   item id -> typeLists of its device type, or null
//   moduleAt   (item id, bay path) -> typeLists of the module type seated there; the path
//              of a bay of a module is the drawing's (`drawer/module/slot-1`)
//   consolesOf item id -> the paths of the console ports its drawing has
export function endResolver({rack, ctx = null, deviceOf, moduleAt = () => null, consolesOf = () => []}) {
  const items = new Map((rack?.items || []).map(i => [i.id, i]));
  return end => resolveEnd({path: portPathOf(end.path), device: deviceOf(end.item), consoles: consolesOf(end.item) || [],
    moduleAt: bay => moduleAt(end.item, bay), ports: fibrePorts(items.get(end.item), end, ctx)});
}

// ── the modules file ────────────────────────────────────────────────────
// A card's ports exist in a DCIM only once a module of its type is in its bay,
// so the modules are imported before the cables. NetBox finds the bay by the
// device's name and the bay's NAME, and the module type by its model alone (a
// manufacturer column is refused); Nautobot by the lookups below. Both were
// accepted by the real instances (NetBox 4.7.2, Nautobot 3.2.6).
export const MODULE_COLUMNS = {
  netbox: ['device', 'module_bay', 'module_type', 'status'],
  nautobot: ['module_type__manufacturer__name', 'module_type__model', 'parent_module_bay__parent_device__name',
             'parent_module_bay__name', 'status__name']};

// The columns of a Nautobot module that sits `depth` modules down: the bay it
// is in is `parent_module_bay__name`, the bay of the module above it is
// reached through `parent_module`, and so on up to the device.
const UP = 'parent_module_bay__parent_module__';
const nautobotDeviceColumn = depth => `${UP.repeat(depth)}parent_module_bay__parent_device__name`;
const nautobotBayColumn = (depth, level) => `${UP.repeat(depth - level)}parent_module_bay__name`;
const nautobotModuleColumns = depth => ['module_type__manufacturer__name', 'module_type__model', nautobotDeviceColumn(depth),
  ...Array.from({length: depth + 1}, (_, level) => nautobotBayColumn(depth, level)), 'status__name'];

// One row per part seated in a BAY (its path ends "/module") that has a module
// type, on a device the devices file holds, in a bay the device type has at
// that position. A part seated in a cage (an optic, a plug) is not a module:
// the cage is the interface.
//
// A MODULE IN A BAY OF ANOTHER MODULE (#1024) is written after the modules in
// the device's bays, parents first, for NetBox: the cables on its ports name
// ports that exist only once it is installed, and a cables file is taken whole
// or not at all. Its `module_bay` is the bay's name as NetBox installs it
// (`drawer/slot-1`, the parent's position put in for `{module}`), which is
// unique on the device.
//
// Nautobot's module import names a bay of a module by lookups down through the
// parent module (#1127): the device and the bay of the outermost module, then
// the bay of each module below it, one `parent_module_bay__parent_module__`
// more for each level, so a module two levels down reads
// `parent_module_bay__parent_module__parent_module_bay__parent_module__parent_module_bay__parent_device__name`.
// A CSV has one header and rows of different depths name different columns,
// so the file is one SECTION PER DEPTH, each its own CSV: `columns` and `rows`
// are the modules in the device's bays, as before, and `deeper` is
// [{depth, columns, rows}] for depth 1 and below, outermost first. They are
// imported in that order, so a module is installed after the one it sits in.
//   parts     [{itemId, path, ref}], what each device has seated (exports.js)
//   names     uniqueNames(items); kept: the ids of the devices in the devices file
//   deviceOf  item id -> typeLists of its device type, or null
//   moduleOf  part ref -> {manufacturer, model, lists} of its module type, or null
// `left` holds one sentence for each thing the file does not carry.
export function moduleImportRows({target = 'netbox', parts, names, kept, deviceOf, moduleOf}) {
  const rows = [], left = [], said = new Set(), inside = [], written = new Set(), sections = [];
  const seated = new Map(parts.map(q => [`${q.itemId}\0${q.path}`, q]));
  for (const p of parts) {
    if (!String(p.path).endsWith('/module')) continue;
    const type = moduleOf(p.ref);
    if (!type) continue;                       // a part with no module type is already in the kit's notes
    const device = names.get(p.itemId)?.name ?? '';
    const bayId = p.path.slice(0, -'/module'.length);
    if (!kept.has(p.itemId)) {
      if (!said.has(p.itemId)) left.push(`The modules of ${device} are not in the modules file: ${device} is not in the devices file.`);
      said.add(p.itemId);
      continue;
    }
    if (bayId.includes(MODULE)) { inside.push({p, type, device, bayId}); continue; }
    const lists = deviceOf(p.itemId), bay = bayAt(lists, bayId);
    if (!bay) {
      left.push(`${device} ${bayId}: ${type.model} is not in the modules file. ` + (lists
        ? `The device type ${lists.model} has no module bay at position ${bayId}.`
        : `${device} has no device type, so it has no module bays.`));
      continue;
    }
    written.add(`${p.itemId}\0${p.path}`);
    rows.push(target === 'nautobot'
      ? {module_type__manufacturer__name: type.manufacturer, module_type__model: type.model,
         parent_module_bay__parent_device__name: device, parent_module_bay__name: bay.name, status__name: 'Planned'}
      : {device, module_bay: bay.name, module_type: type.model, status: 'planned'});
  }
  // outermost first, so that a module is installed before what sits in it
  const depth = x => x.bayId.split(MODULE).length;
  for (const {p, type, device, bayId} of inside.sort((a, b) => depth(a) - depth(b))) {
    const lead = `${device} ${bayId}: ${type.model} is not in the modules file.`;
    const above = bayId.slice(0, bayId.lastIndexOf(MODULE));
    if (!written.has(`${p.itemId}\0${above}/module`)) {
      left.push(`${lead} The module it sits in, at ${above}, is not in the modules file.`);
      continue;
    }
    const typeAt = path => { const q = seated.get(`${p.itemId}\0${path}/module`); return q ? moduleOf(q.ref)?.lists ?? null : null; };
    const at = seatChain(bayId, deviceOf(p.itemId), typeAt);
    if (!at.ok) { left.push(`${lead} ${at.reason[0].toUpperCase()}${at.reason.slice(1)}.`); continue; }
    written.add(`${p.itemId}\0${p.path}`);
    if (target === 'nautobot') {
      const d = at.names.length - 1;
      sections[d] ??= {depth: d, columns: nautobotModuleColumns(d), rows: []};
      const row = {module_type__manufacturer__name: type.manufacturer, module_type__model: type.model};
      row[nautobotDeviceColumn(d)] = device;
      at.names.forEach((name, j) => { row[nautobotBayColumn(d, j)] = name; });
      row.status__name = 'Planned';
      sections[d].rows.push(row);
      continue;
    }
    rows.push({device, module_bay: at.bay.name.replaceAll('{module}', at.positions.at(-2)), module_type: type.model, status: 'planned'});
  }
  if (target === 'nautobot') return {columns: MODULE_COLUMNS.nautobot, rows, left, deeper: sections.filter(Boolean)};
  return {columns: MODULE_COLUMNS.netbox, rows, left};
}

// ── the cables file ─────────────────────────────────────────────────────
// The Rack Builder's media as a DCIM's cable type. Both targets accepted each
// of these and refused "os2". A media this page does not know, or none, is a
// blank type: the column is optional. `power` has no row yet: a power cable
// whose two ends the type files name is written with a blank type, and one
// whose ends they do not name is left out with that reason, as any cable is
// (docs/cable-ends-design.md section 7).
// `stack`, `usb` and `console` have a row, and it is BLANK. The cable-type
// choices of NetBox v4.7.2 and Nautobot v3.2.6 (the pins this file cites) were
// not read when these rows were written, so no value is written for them: a
// value is filled in only from those lists. CABLE_TYPE_NOTES says so.
export const CABLE_TYPE = {os2: 'smf-os2', om3: 'mmf-om3', om4: 'mmf-om4', om5: 'mmf-om5', cat6: 'cat6', cat6a: 'cat6a',
                           dac: 'dac-passive', aoc: 'aoc', stack: '', usb: '', console: ''};
export const CABLE_TYPE_NOTES = Object.fromEntries(['stack', 'usb', 'console'].map(m => [m, 'the DCIM cable-type choices were not read']));
export const cableType = media => (Object.hasOwn(CABLE_TYPE, media ?? '') ? CABLE_TYPE[media] : '');

// Which kinds of end a DCIM lets one cable join (NetBox and Nautobot share the
// table; both refused a console port to an interface).
const PORTS = ['dcim.frontport', 'dcim.rearport'];
const MEETS = {
  'dcim.interface': ['dcim.interface', ...PORTS],
  'dcim.frontport': ['dcim.interface', 'dcim.consoleport', 'dcim.consoleserverport', ...PORTS],
  'dcim.rearport': ['dcim.interface', 'dcim.consoleport', 'dcim.consoleserverport', ...PORTS],
  'dcim.consoleport': ['dcim.consoleserverport', ...PORTS],
  'dcim.consoleserverport': ['dcim.consoleport', ...PORTS],
  'dcim.powerport': ['dcim.poweroutlet'],
  'dcim.poweroutlet': ['dcim.powerport']};
export const canMeet = (a, b) => (MEETS[a] || []).includes(b);
const KIND = {'dcim.interface': 'an interface', 'dcim.frontport': 'a front port', 'dcim.rearport': 'a rear port',
              'dcim.consoleport': 'a console port', 'dcim.consoleserverport': 'a console server port',
              'dcim.powerport': 'a power port', 'dcim.poweroutlet': 'a power outlet'};

// A cable's length as a target takes it: {value, unit, note}. Only m and ft
// are written (the units the page offers). NetBox keeps two decimal places and
// refuses a third; Nautobot takes a whole number only. Either way a length is
// rounded UP, never down: a cable cut short does not reach.
export function importLength(cable, target = 'netbox') {
  const p = lengthParts(cable.length);
  if (!p) return {value: '', unit: '', note: cable.lengthAsWritten != null ? 'its length as written in the rack file is not carried' : null};
  if (p.unit !== 'm' && p.unit !== 'ft')
    return {value: '', unit: '', note: `its length (${p.value} ${p.unit}) is not carried: the kit writes lengths in m or ft only`};
  const value = target === 'nautobot' ? Math.ceil(p.value) : Math.ceil(p.value * 100 - 1e-9) / 100;
  const big = nautobot => (nautobot ? value > DCIM_LIMITS.nautobotLengthMax : value >= DCIM_LIMITS.netboxLengthBelow);
  if (big(target === 'nautobot'))
    return {value: '', unit: '', note: `its length (${p.value} ${p.unit}) is too large for ${target === 'nautobot'
      ? `Nautobot, which stores whole numbers up to ${DCIM_LIMITS.nautobotLengthMax.toLocaleString('en-US')}`
      : `NetBox, which stores less than ${DCIM_LIMITS.netboxLengthBelow.toLocaleString('en-US')}`}, so the row has no length`};
  const note = value === p.value ? null
    : `${p.value} ${p.unit} is written as ${value} ${p.unit}: ${target === 'nautobot' ? 'Nautobot takes whole numbers' : 'NetBox keeps two decimal places'}, and a length is rounded up`;
  return {value, unit: p.unit, note};
}

export const CABLE_IMPORT_COLUMNS = {
  netbox: ['side_a_device', 'side_a_type', 'side_a_name', 'side_b_device', 'side_b_type', 'side_b_name', 'type', 'status',
           'label', 'color', 'length', 'length_unit', 'description'],
  // Read by import_cables.py, NOT by Nautobot's own importer: Nautobot takes a cable's ends by id only.
  nautobot: ['a_device', 'a_type', 'a_name', 'b_device', 'b_type', 'b_name', 'type', 'status', 'label', 'color', 'length',
             'length_unit']};

// One row per cable the target will take. NetBox takes the file whole or not
// at all, so a cable it would refuse is left out and said, in `left`, with its
// reason. A row needs: its ends checked and both landed; both devices in the
// devices file; both ends named by the type files (`resolve`, resolveEnd over
// this rack); no comma in a device or port name (NetBox reads one as a list);
// two kinds of end a DCIM joins; and no port already used by an earlier row.
//
// AN END ON SEVERAL PORTS (#1020). A cord on a duplex adapter lands on two
// fibre ports of the panel (resolveEnd's `names`). NetBox's cable has any
// number of terminations a side, all of one kind, and its import form splits
// the name column on commas and asks no equal count of the two sides (NetBox
// v4.7.2 251458b8, dcim/forms/bulk_import.py CableImportForm._clean_side and
// dcim/models/cables.py Cable.clean), so the cord is ONE row naming them all.
// Nautobot's file is read by import_cables.py, which makes a cable of one
// termination a side, so the cord is one row for each fibre: port k of one
// end to port k of the other, each row with the cord's type, status and
// length, and its label with " (k/n)" after it, which is what ties the rows
// (and so is made unique among such cords, with the cable's id where needed).
// Where one end is a single port (an optic's interface, a rear connector) and
// the other is several, Nautobot gets one row, to the FIRST of them, and a
// note names the ports left without a cable. THAT ROW TRACES ONLY BETWEEN
// LIKE ENDS: a Type A cassette binds front port 1 to trunk position 1 and a
// Type AF one binds it to position 2 (FHD-1MTP6LCDOS2A and -AF, as committed),
// so across an A to AF pair the fibre arrives on the far end's second port,
// which has no cable. The note says so. Ends on two different counts of
// several ports have no such reading, and Nautobot's file leaves the cord out;
// no part of the library gives such an end today (a part is one port or two),
// and a test reaches the rule with a resolver of its own.
// (Nautobot v3.2.6 3dc554b4 can hold several connectors a side on a cable
// that names a cable type made for it: dcim/models/cables.py CableType. Such
// a type must exist before a cable names it, as a NetBox bundle must, so the
// kit writes none.)
//   ends       cable-plugs.js cableFacts(rack).ends; unchecked: reading them failed
//   names      uniqueNames(items); kept: the ids of the devices in the devices file
//   resolve    end -> resolveEnd's answer for that end
//   uOf        endName's: how tall a device is
//   parts      the parts lists, {slotsOf, compByRef}: cableFindings settles the ends with them
// `notes` are about rows that ARE written: a type left blank, a length changed.
//
// NETBOX 4.6 OR LATER (#945, decision 9 in docs/cable-bundles-design.md). When
// `dcim.netbox` names it and the rack has a site, the NetBox answer also
// carries `bundleFile` ({columns, rows}: the bundles file, imported before the
// cables file) and each row has a `bundle`, the same name; see bundleNames.
// Otherwise nothing is added. Nautobot has no bundle and ignores `dcim`.
//   dcim       the rack's import settings (model.js dcimOf): site, role, netbox
export function cableImportRows({rack, target = 'netbox', names, kept, resolve, ends = new Map(), unchecked = false, uOf, parts = null, dcim = {}}) {
  const T = TARGET_NAME[target] || 'NetBox', nautobot = target === 'nautobot';
  const native = !nautobot && bundlesFileOn(dcim), pending = [];
  const rows = [], left = [], notes = [], used = new Map(), inBundle = new Map();
  const several = [], perFibre = [], firstOnly = [], tied = new Set();
  let dac = false;
  for (const f of cableFindings(rack, ends, parts)) {
    const c = f.cable;
    let why = [], sides = [];
    if (unchecked || !f.checked) why = ['its ends could not be checked'];
    else if (f.loose.length)
      why = f.loose.map(l => `end ${l.side}, ${endName(rack, l.end, uOf)}, is not connected (${l.reason})`);
    // A GROUND WIRE IS NEVER A ROW: neither target has a termination for a
    // ground stud. It is left out by name, not by failing to find a port.
    else if (c.media === 'ground') why = ['it is a ground wire, and a DCIM has no termination for a ground stud'];
    else {
      sides = [['A', c.a], ['B', c.b]].map(([side, end]) => {
        const device = names.get(end.item)?.name ?? '';
        if (!kept.has(end.item)) return {why: `end ${side} is on ${device}, which is not in the devices file`};
        const r = resolve(end);
        if (!r.ok) return {why: `end ${side}, ${endName(rack, end, uOf)}: ${r.reason}`};
        const ports = r.names?.length ? r.names : [r.name];
        const comma = [device, ...ports].find(x => x.includes(','));
        if (!nautobot && comma != null) return {why: `end ${side}: NetBox reads a comma in a device or port name as a list, so "${comma}" cannot be written`};
        return {side, end, device, name: ports[0], ports, type: r.type, keys: ports.map(n => JSON.stringify([device, r.type, n]))};
      });
      why = sides.filter(s => s.why).map(s => s.why);
      if (!why.length && !canMeet(sides[0].type, sides[1].type))
        why = [`${T} does not cable ${KIND[sides[0].type]} to ${KIND[sides[1].type]}`];
      const shared = why.length ? -1 : sides[0].keys.findIndex(k => sides[1].keys.includes(k));
      if (shared >= 0)
        why = [`its two ends are the same port, ${sides[0].ports[shared]} on ${sides[0].device}`];
      if (!why.length)
        why = sides.filter(s => s.keys.some(k => used.has(k)))
          .map(s => `end ${s.side}, ${endName(rack, s.end, uOf)}, already has cable ${used.get(s.keys.find(k => used.has(k)))} in this file`);
      const [n, m] = sides.map(s => s.ports?.length ?? 0);
      if (!why.length && nautobot && n !== m && n > 1 && m > 1)
        why = [`its ends are on ${n} and ${m} ports, and Nautobot gives a cable one port at each end`];
    }
    if (why.length) { left.push(`Cable ${f.name} is not in the cables file: ${why.join('; ')}.`); continue; }
    const [a, b] = sides;
    for (const s of sides) for (const k of s.keys) used.set(k, f.name);
    const type = cableType(c.media);
    if (c.media && !type) notes.push(`Cable ${f.name}: its media (${c.media}) has no ${T} cable type, so its type is blank.`);
    dac ||= c.media === 'dac';
    const len = importLength(c, target);
    if (len.note) notes.push(`Cable ${f.name}: ${len.note}.`);
    // THE `color` COLUMN is the cable's OWN colour and nothing else (#1028):
    // six lower case hex digits with no `#`, which is what both take (NetBox
    // v4.7.2 251458b8, dcim/models/cables.py `Cable.color`, a ColorField whose
    // utilities/validators.py ColorValidator is ^[0-9a-f]{6}$, and `color` in
    // dcim/forms/bulk_import.py CableImportForm; Nautobot v3.2.6 3dc554b4,
    // dcim/models/cables.py `Cable.color`, the same ColorField and validator in
    // core/models/fields.py). A colour worked out from the ends, the type or
    // the media is how the cable is drawn, not a fact someone recorded of it,
    // so it is left blank, as every cable's was before.
    const color = hexColor(c.color)?.slice(1) ?? '';
    // A label or a description over the field's length is cut to it, not the cable dropped.
    const along = c.length?.source === 'routed' && len.value !== '';
    let label = flat(c.label || c.id);
    // NetBox's description: the bundle first (decision 9), so that a cut from
    // the end keeps it, then the purpose, then the length note.
    const bundle = bundleOfCable(rack, c.id);
    if (bundle) inBundle.set(bundle.id, [...(inBundle.get(bundle.id) || []), f.name]);
    const parts = nautobot ? [] : [['bundle', bundle ? flat(bundleName(bundle)) : ''], ['purpose', c.purpose || ''],
      ['length note', along ? 'Length measured along its route.' : '']].filter(([, t]) => t);
    // Each part but the last ends in a full stop: "Bundle 2. uplink. Length measured along its route."
    let description = parts.map(([, t], k) => (k + 1 < parts.length && !t.endsWith('.') ? `${t}.` : t)).join(' ');
    if (along && nautobot) notes.push(`Cable ${f.name}: length measured along its route.`);
    if (charCount(label) > DCIM_LIMITS.cableLabel) {
      notes.push(`Cable ${f.name}: its label is ${charCount(label)} characters and ${T} takes ${DCIM_LIMITS.cableLabel}, so the label is shortened to that.`);
      label = cutTo(label, DCIM_LIMITS.cableLabel);
    }
    if (!nautobot && charCount(description) > DCIM_LIMITS.cableDescription) {
      notes.push(`Cable ${f.name}: its description (${andList(parts.map(([k]) => k))}) is ${charCount(description)} characters and ${T} takes ${DCIM_LIMITS.cableDescription}, so the description is shortened to that.`);
      description = cutTo(description, DCIM_LIMITS.cableDescription);
    }
    if (!nautobot) {
      if (a.ports.length > 1 || b.ports.length > 1) several.push(f.name);
      const row = {side_a_device: a.device, side_a_type: a.type, side_a_name: a.ports.join(','), side_b_device: b.device,
                   side_b_type: b.type, side_b_name: b.ports.join(','), type, status: 'planned', label, color,
                   length: len.value, length_unit: len.unit, description};
      if (native) { row.bundle = ''; if (bundle) pending.push([row, bundle]); }
      rows.push(row);
      continue;
    }
    // Nautobot: a row for each fibre where both ends have as many; else one row, to the first port of the end with several.
    const count = a.ports.length === b.ports.length ? a.ports.length : 1;
    if (count > 1) perFibre.push(f.name);
    else for (const s of sides) if (s.ports.length > 1) firstOnly.push(`${f.name} (${s.device} ${s.ports.slice(1).join(', ')})`);
    // THE LABEL TIES THE ROWS OF ONE CORD, so no two cords may share it. A
    // label that fits and no earlier cord took is written whole. One that is
    // too long for " (k/n)" after it, or that another cord's rows already
    // carry (labels repeat, and two long ones may share all that is kept), is
    // cut to leave room for the cable's id, which no other cable has.
    const room = DCIM_LIMITS.cableLabel - charCount(` (${count}/${count})`);
    let stem = label;
    if (count > 1 && (charCount(stem) > room || tied.has(stem))) {
      const id = ` ${flat(c.id)}`, mark = charCount(id) <= room ? id : ` #${tied.size + 1}`;
      stem = cutTo(label, room - charCount(mark)) + mark;
      notes.push(`Cable ${f.name}: its ${count} rows are labelled ${stem}, the label ${charCount(label) > room ? 'shortened' : 'another cable has too'} ` +
                 'and the id of the cable after it, so that the rows of one cord are not taken for those of another.');
    }
    if (count > 1) tied.add(stem);
    for (let k = 0; k < count; k++) {
      const tail = count > 1 ? ` (${k + 1}/${count})` : '';
      rows.push({a_device: a.device, a_type: a.type, a_name: a.ports[k], b_device: b.device, b_type: b.type, b_name: b.ports[k], type,
                 status: 'Planned', label: stem + tail, color, length: len.value, length_unit: len.unit});
    }
  }
  if (dac) notes.push('A DAC is written as dac-passive. Change the type of one that is active.');
  // AN END ON SEVERAL PORTS: one note for each way it was written, naming the cables.
  if (several.length)
    notes.push(`A cord on a duplex adapter is on two fibre ports of its panel or cassette. Its row names both, separated by a comma, which NetBox's cable import reads as the ports of one end: ${andList(several)}.`);
  if (perFibre.length)
    notes.push('Nautobot gives a cable one port at each end, so a cord with two fibre ports at both ends is written as one row for each fibre, ' +
               `first port to first port, each with the cord's type and length and its label followed by which fibre it is, as (1/2). ` +
               `First to first is an order, not a polarity: the rack file does not say whether a cord is crossed. The cords: ${andList(perFibre)}.`);
  if (firstOnly.length)
    notes.push('Nautobot gives a cable one port at each end, so a cord from a single port (an interface, a rear connector) to two fibre ports ' +
               'is written to the first of the two. Nautobot then traces a link whose two ends bind that first port to the same trunk position ' +
               '(two cassettes of one type), and not one whose ends differ (a Type A cassette facing a Type AF one, which puts the fibre on the ' +
               `second port at the far end): cable that second port by hand there. These ports have no cable in this file: ${firstOnly.join('; ')}.`);
  // THE BUNDLES (#923, decision 9). NetBox: each cable names its bundle first
  // in its description. NetBox 4.6 and later also has cable bundles of its own
  // (dcim.CableBundle, and the cable import's `bundle` column, by name: NetBox
  // v4.7.2 251458b8, dcim/models/cables.py and dcim/forms/bulk_import.py), but
  // a bundle must exist before a cable can name it, as a tag must, and a name
  // is unique across an instance, which a rack's own bundle names are not. So
  // the column is written only with the option "NetBox 4.6 or later" (#945),
  // and a bundles file goes first; otherwise the kit leaves it out and says so.
  // Nautobot's cable has no description and no
  // bundle (v3.2.6 3dc554b4, dcim/models/cables.py), so membership is listed here and in the cable schedule.
  const held = bundlesOf(rack).filter(b => inBundle.has(b.id))
    .map(b => `${flat(bundleName(b))} holds ${andList(inBundle.get(b.id))}`);
  let bundleFile = null;
  if (native) {
    const made = bundleNames({rack, dcim, bundles: bundlesOf(rack).filter(b => inBundle.has(b.id))});
    left.push(...made.left);
    for (const [row, b] of pending) row.bundle = made.names.get(b.id) ?? '';
    bundleFile = {columns: NETBOX_BUNDLE_COLUMNS, rows: [...made.names.values()].map(name => ({name}))};
  }
  if (held.length && nautobot)
    notes.push(`Nautobot's cables have no description or bundle, so this file does not say which bundle a cable is in: ${held.join('; ')}. The cable schedule lists each cable's bundle.`);
  else if (held.length && native)
    notes.push(`Each cable in a bundle names its bundle first in its description, and fills the bundle column of this file with the name of its cable bundle, which ${NETBOX_BUNDLE_FILES.bundles} makes first.`);
  else if (held.length && netboxHasBundles(dcim))
    notes.push('The option for NetBox 4.6 or later is on, but no site is set, so a bundle cannot be given a name that is unique in a NetBox instance: ' +
               `this kit has no bundles file and the cables file has no bundle column. Each cable still names its bundle first in its description. Set the site and export again.`);
  else if (held.length)
    notes.push("Each cable in a bundle names its bundle first in its description. NetBox 4.6 and later also has cable bundles of its own, which must be made before a cable can name one, so this file does not fill a cable's bundle field.");
  return {columns: native ? NETBOX_CABLE_BUNDLE_COLUMNS : CABLE_IMPORT_COLUMNS[nautobot ? 'nautobot' : 'netbox'], rows, left, notes,
          ...(native ? {bundleFile} : {})};
}

// ── NETBOX'S OWN CABLE BUNDLES (#945) ──────────────────────────────────
// NetBox 4.6 added dcim.CableBundle. Read from v4.7.2 (251458b8):
//   dcim/models/cables.py       CableBundle.name: CharField(max_length=100, unique=True)
//   dcim/forms/bulk_import.py   CableBundleImportForm: name, description, owner, comments, tags
//                               CableImportForm.bundle: CSVModelChoiceField on CableBundle, to_field_name='name'
// So the bundles file has the one column `name` (the rest are optional), the
// cables file's `bundle` finds a bundle by that name, and the name must be
// unique across the whole instance: a rack's own "Bundle 1" repeats from rack to
// rack. A name is "<site> <rack> <bundle name>". With no site there is nothing
// to make it unique, so the option writes none. A name over the limit is left
// out, never cut: two cut names could be the same. A name in the instance
// already is something the kit cannot see (the README says so).
// The version is read from `dcim.netbox`: a string, "4.6" or later is on. A
// number, a blank, an older version or a string that is no version is off.
export const netboxHasBundles = dcim => {
  const m = typeof dcim?.netbox === 'string' ? /^v?(\d+)\.(\d+)/.exec(dcim.netbox.trim()) : null;
  return m != null && (Number(m[1]) > 4 || (Number(m[1]) === 4 && Number(m[2]) >= 6));
};
const siteOf = dcim => String(dcim?.site ?? '').trim();
// The files exist when the option is on AND a site is set.
export const bundlesFileOn = dcim => netboxHasBundles(dcim) && siteOf(dcim) !== '';
export const NETBOX_BUNDLE_COLUMNS = ['name'];
export const NETBOX_CABLE_BUNDLE_COLUMNS = [...CABLE_IMPORT_COLUMNS.netbox, 'bundle'];
// The NetBox kit's files with the option on: the bundles file comes before the cables file, which moves down one.
export const NETBOX_BUNDLE_FILES = {rack: '1-rack.csv', devices: '2-devices.csv', modules: '3-modules.csv', bundles: '4-bundles.csv', cables: '5-cables.csv'};
export const netboxFiles = dcim => (bundlesFileOn(dcim) ? NETBOX_BUNDLE_FILES : KIT_FILES.netbox);

// The name each bundle of `bundles` is given, {names: Map(id -> name), left}.
// A bundle whose name is over the limit, or that shares its name with another
// of the rack, is left out with its reason; nothing is cut.
function bundleNames({rack, dcim, bundles}) {
  const full = new Map(bundles.map(b => [b.id, [siteOf(dcim), flat(rack.name), flat(bundleName(b))].map(s => s.trim()).join(' ')]));
  const twice = name => [...full.values()].filter(n => n === name).length > 1;
  const names = new Map(), left = [];
  for (const b of bundles) {
    const name = full.get(b.id), own = flat(bundleName(b)).trim(), shown = charCount(own) > 24 ? `${cutTo(own, 24)}...` : own;
    if (charCount(name) > DCIM_LIMITS.cableBundleName)
      left.push(`Bundle ${shown} is not in the bundles file: its NetBox name, site, rack and bundle together, is ${charCount(name)} characters, and NetBox allows ${DCIM_LIMITS.cableBundleName}. ` +
                'The name is never shortened: two shortened names could be the same. Its cables are in the cables file with no bundle, and their descriptions still name it. ' +
                "Shorten the site, the rack or the bundle's name and export again.");
    else if (twice(name))
      left.push(`Bundle ${shown} is not in the bundles file: another bundle of this rack is also named "${name}", and NetBox needs each bundle name once. ` +
                'Its cables are in the cables file with no bundle, and their descriptions still name it. Give each bundle a label of its own and export again.');
    else names.set(b.id, name);
  }
  return {names, left};
}

// ── README.txt ──────────────────────────────────────────────────────────
// What to do with each file, in order; what must already exist; and
// everything the kit could not carry. It replaces NOTES.txt and keeps its
// content (`notes`).
//   rows      how many rows each CSV holds: {rack, devices, modules, cables}, and
//             for Nautobot `modulesIn`, the rows of each deeper modules file
//             (depth 1 first, from moduleImportRows' `deeper`)
//   typeFiles how many YAML files are under types/
//   left      a sentence for each device, module and cable the files leave out
//   notes     what the types and the written rows need said (a best-guess type,
//             a length that was rounded)
//   script    whether import_cables.py is in the zip (Nautobot)
//   scriptUrl where the script is when it is not; named only when given (#895)
//   source    what made the kit, as the first line names it: a host names
//             itself ("the Portrayal Rack Builder"); 'Portrayal' otherwise
//   settingsAt where the reader sets a blank site or role, after "Set the
//             site ..." - a host names its own control for it
// Returns {text, notes}: `notes` are the lines the file carries beyond its
// instructions, which is what the page's status line counts.
export const KIT_FILES = {
  netbox: {rack: '1-rack.csv', devices: '2-devices.csv', modules: '3-modules.csv', cables: '4-cables.csv'},
  nautobot: {devices: '1-devices.csv', modules: '2-modules.csv', cables: '3-cables.csv'}};
// The Nautobot modules in a bay of a module, a file for each depth (1 and below), imported after 2-modules.csv in order.
export const nautobotModuleFile = depth => (depth ? `2b-modules-depth-${depth}.csv` : KIT_FILES.nautobot.modules);
export const KIT_SCRIPT = 'import_cables.py';
const rowsText = n => (n ? `${n} ${n === 1 ? 'row' : 'rows'}` : 'no rows: it holds its header only, so skip it');

// The text is LF throughout (a comment, as asked): every modern editor on
// Windows, macOS and Linux opens it, and the page's other notes are LF. The CSVs
// stay CRLF because a CSV importer reads that. Lines are wrapped at WIDTH
// columns, with a hanging indent; a command line or a path longer than that
// is never broken. `width` is a parameter so a test can read a paragraph whole.
export const README_WIDTH = 78;
function wrap(text, first, hang, width) {
  const lines = [];
  let line = first, fresh = true;
  for (const word of text.split(' ')) {
    if (!fresh && line.length + 1 + word.length > width) { lines.push(line); line = hang + word; }
    else line += (fresh ? '' : ' ') + word;
    fresh = false;
  }
  lines.push(line);
  return lines;
}

export function kitReadme({target = 'netbox', rack, date, dcim = {}, typeFiles = 0, manufacturers = [], rows = {},
                           left = [], notes = [], script = true, scriptUrl = null, width = README_WIDTH,
                           source = 'Portrayal', settingsAt = "in the rack's DCIM import settings (dcim.site, dcim.role)"}) {
  const nautobot = target === 'nautobot', T = TARGET_NAME[nautobot ? 'nautobot' : 'netbox'];
  // With NetBox 4.6 or later on (#945) the bundles file is step 5 and the cables file step 6; Nautobot has neither.
  const F = nautobot ? KIT_FILES.nautobot : netboxFiles(dcim), bundled = !nautobot && bundlesFileOn(dcim);
  const site =String(dcim?.site ?? '').trim(), role = String(dcim?.role ?? '').trim();
  const place = nautobot ? 'location' : 'site', cols = nautobot ? ['location__name', 'role__name'] : ['site', 'role'];
  const blank = [!site && cols[0], !role && cols[1]].filter(Boolean);
  const warning = blank.length
    ? `${F.devices} will be refused as it is: its ${blank.join(' and ')} ${blank.length === 1 ? 'column is' : 'columns are'} blank, and ` +
      `${T} requires ${blank.length === 1 ? 'it' : 'both'}.${!nautobot && !site ? ` ${F.rack}'s site column is blank too.` : ''} ` +
      `Set the ${[!site && place, !role && 'device role'].filter(Boolean).join(' and the ')} ${settingsAt}, ` +
      `and export again; or fill ${blank.length === 1 ? 'that column' : 'those columns'} in by hand.`
    : '';
  const numbered = rack.frame.numbering === 'top-down' ? 'numbered from the top' : 'numbered from the bottom';
  const out = [];
  // No paragraph holds a line break of its own, whatever it was handed (kitNames, above).
  const para = (text, first = '', hang = '  ') => out.push(...wrap(flat(text), first, hang, width));
  para(`${T} import kit for ${rack.name}, from ${source}, ${isoDate(date)}.`);
  out.push('');
  const item = text => para(text, '- ', '  ');
  if (warning) { para(warning, 'Read this first: '); out.push(''); }

  out.push(`Before you import, ${T} must already have:`);
  item(site ? `the ${place} "${site}"${nautobot ? ', of a location type that allows devices and racks' : ''}`
            : `a ${place}${nautobot ? ', of a location type that allows devices and racks' : ''} (none is set in this kit)`);
  item(role ? `the ${nautobot ? 'role' : 'device role'} "${role}"${nautobot ? ', for devices' : ''}`
            : `a ${nautobot ? 'role for devices' : 'device role'} (none is set in this kit)`);
  if (nautobot) item('a status named Planned, for devices, modules and cables');
  if (manufacturers.length) item(`these manufacturers: ${manufacturers.join(', ')}`);
  if (nautobot)
    item(`the rack "${rack.name}" in that location: ${rack.frame.heightRU}U, ${numbered}` +
         `${rack.frame.numbering === 'top-down' ? ' (descending units)' : ''}. This kit has no rack file for Nautobot.`);
  out.push('');

  const types = `types/device-types/, then types/module-types/ (${typeFiles} ${typeFiles === 1 ? 'file' : 'files'})`;
  const step = (n, text) => para(text, `Step ${n}: `, '        ');
  const sub = text => para(text, '        ', '        ');
  if (nautobot) {
    para('Import in this order. Nautobot takes each CSV file whole or not at all.');
    step(1, typeFiles ? `${types}: Device Types > Import and Module Types > Import, one YAML file per import.`
                      : 'types/: no files, so there is nothing to import.');
    step(2, `${F.devices} (${rowsText(rows.devices)}): Devices > Import, or POST it to /api/dcim/devices/ as text/csv. Every device is planned.`);
    step(3, `${F.modules} (${rowsText(rows.modules)}): Modules > Import, or POST it to /api/dcim/modules/ as text/csv. ` +
            "This creates each card's ports, so it comes before the cables.");
    // A module in a bay of another module is a file of its own for each depth: one header cannot name rows of two depths (#1127).
    (rows.modulesIn ?? []).forEach((n, k) => {
      if (n) sub(`Then ${nautobotModuleFile(k + 1)} (${rowsText(n)}), the same way: ${k ? 'modules in a bay of a module of the file before' : 'modules in a bay of a module of that file'}.`);
    });
    // With no cable rows there is nothing to run: no commands, and no warning about a file nobody will use.
    if (!rows.cables) step(4, `${F.cables} (${rowsText(rows.cables)}).`);
    else {
      step(4, `${F.cables} (${rowsText(rows.cables)}), with ${KIT_SCRIPT}. Warning: do not give ${F.cables} to Nautobot's own importer. ` +
              "Nautobot takes a cable's ends by id only, and from a file that names them it creates cables with no ends.");
      if (script) {
        out.push('        export NAUTOBOT_URL=https://nautobot.example.com',
          '        export NAUTOBOT_TOKEN=...     (an API token; the script never prints it)',
          `        python3 ${KIT_SCRIPT} ${F.cables}             (a dry run: what it would create, and what it cannot find)`,
          `        python3 ${KIT_SCRIPT} ${F.cables} --apply     (creates the cables)`);
        sub("Python 3, standard library only. It talks to that URL's host and no other. Run it again after a failure: " +
            'a cable it already made is reported as already connected, and left alone.');
      }
      sub("A cable's purpose is not carried into Nautobot by this kit.");
    }
    out.push('');
  } else {
    para('Import in this order. NetBox takes each CSV file whole or not at all: one refused row refuses the file.');
    step(1, typeFiles ? `${types}: Device Types > Import and Module Types > Import, format YAML, one file at a time. ` +
                        'The module types must be in before step 4.'
                      : 'types/: no files, so there is nothing to import.');
    step(2, `${F.rack} (${rowsText(rows.rack)}): Racks > Import. Creates the rack "${rack.name}", ${rack.frame.heightRU}U, ${numbered}.`);
    step(3, `${F.devices} (${rowsText(rows.devices)}): Devices > Import. Every device is planned.`);
    step(4, `${F.modules} (${rowsText(rows.modules)}): Modules > Import. This creates each card's ports, so it comes before the cables.`);
    if (bundled) {
      step(5, `${F.bundles} (${rowsText(rows.bundles)}): the cable bundles, imported with the CableBundle import form. Each bundle is named "${site} ${flat(rack.name)} <bundle name>", ` +
              'so that its name is unique in the whole instance. It comes before the cables, which name them.');
    }
    step(bundled ? 6 : 5, `${F.cables} (${rowsText(rows.cables)}): Cables > Import.${bundled ? " Its bundle column names a bundle of step 5, by name." : ''}`);
    out.push('');
  }
  // What a kit made for an empty instance meets on one that is not: a rack that is already there, and names
  // the instance has more than once. For NetBox the second covers the modules step and the cables step alike.
  out.push(`If ${T} is not empty:`);
  if (nautobot) {
    item(`If a rack named "${rack.name}" is in another location too, that one is not used: ${F.devices} finds the rack by its name and its location ` +
         `together (rack__name, rack__location__name), so the rack must be the one in the location ${site ? `"${site}"` : 'the devices are in'}.`);
    item(rows.cables
      ? `Step 3 and ${KIT_SCRIPT} find a device by its name in every location: a device name Nautobot already has twice is refused, ` +
        'and the script says so for each row that names it.'
      : 'Step 3 finds a device by its name in every location: a device name Nautobot already has twice is refused.');
  } else {
    item(`If the rack "${rack.name}" is already in ${site ? 'that' : 'its'} site, skip step 2 and check that it is ${rack.frame.heightRU}U, ` +
         `${numbered}. Step 3 puts the devices in it.`);
    item(`Steps 4 and ${bundled ? 6 : 5} find a device by its name in every site, and step 4 finds a module type by its model in every manufacturer: ` +
         'a name NetBox already has twice is refused as not unique.');
    if (bundled)
      item('This kit cannot see the cable bundles an instance already has. A bundle name must be unique in NetBox, and NetBox refuses the whole of ' +
           `${F.bundles} if any bundle in it already exists: nothing in the file is created. Look in the instance's cable bundles before step 5, ` +
           'and remove the rows of the bundles that already exist. Step 6 finds a bundle by its name, so a cable naming a bundle that already exists joins it, ' +
           `with the cables already in it. When you import this rack again, skip ${F.bundles} and import ${F.cables} alone.`);
  }
  out.push('');

  const missing = nautobot && !script
    ? [`${KIT_SCRIPT} could not be fetched, so it is not in this zip.${scriptUrl ? ` It is at ${scriptUrl}.` : ''}`] : [];
  const gone = [...missing, ...left];
  out.push('Not in this kit:');
  if (gone.length) gone.forEach(item); else item('Nothing: every device, card and cable in this rack is in the files.');
  out.push('');
  if (notes.length) { out.push('Notes:'); notes.forEach(item); out.push(''); }
  return {text: `${out.join('\n').trimEnd()}\n`, notes: [...(warning ? [warning] : []), ...gone, ...notes]};
}
