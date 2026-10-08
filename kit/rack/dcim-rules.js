// WHAT A DCIM IMPORT KIT SAYS, as data. Pure: no DOM,
// no fetch, so `node --test` covers every rule the NetBox and Nautobot kits
// follow: what a port is called in a type file, which rows a file may hold,
// and what the README says of the rest. The Rack Builder's exports
// (the page that builds the files) fetch the type files and the faces, and
// ask here.

import {endName, lengthParts} from './cable-rules.js';
import {cableFindings, TARGET_NAME, DCIM_LIMITS, charCount, cutTo, isoDate, flat} from './export-data.js';
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
// WHAT A CABLE END IS CALLED IN THE DCIM, and which kind of component it is.
// Never built by convention alone: the name must be in the matched type
// file's own lists, and the list it is in gives the type.
//   path      the end's port path on the drawing ("port-1", "slot-2/module/p0")
//   device    typeLists of the item's device type, or null when it has none
//   moduleAt  bay id -> typeLists of the module type seated there, or null
//   consoles  the paths of the console ports the device's drawing has
// Returns {ok: true, name, type}, or {ok: false, reason}: a phrase with no
// period, for "Cable X is not in this file: end A, <end>, <reason>."
export function resolveEnd({path, device, moduleAt = () => null, consoles = []}) {
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
  const bayId = p.slice(0, at), leaf = p.slice(at + MODULE.length);
  if (leaf.includes(MODULE))
    return {ok: false, reason: 'it is a port of a module inside a card, and the card has no module bay to import that module into'};
  const bay = bayAt(device, bayId);
  if (!bay) return {ok: false, reason: `the device type ${device.model} has no module bay at position ${bayId}`};
  const module = moduleAt(bayId);
  if (!module) return {ok: false, reason: `what is seated in ${bayId} has no module type`};
  const hit = findName(module, `{module}/${leaf}`);
  if (!hit) return {ok: false, reason: `the module type ${module.model} lists no port named {module}/${leaf}`};
  return {ok: true, name: `${bay.position}/${leaf}`, type: hit.type, bay};
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

// One row per part seated in a BAY (its path ends "/module") that has a module
// type, on a device the devices file holds, in a bay the device type has at
// that position. A part seated in a cage (an optic, a plug) is not a module:
// the cage is the interface. A module inside a card is not written: no module
// type here has a module bay of its own to import it into.
//   parts     [{itemId, path, ref}], what each device has seated (exports.js)
//   names     uniqueNames(items); kept: the ids of the devices in the devices file
//   deviceOf  item id -> typeLists of its device type, or null
//   moduleOf  part ref -> {manufacturer, model, lists} of its module type, or null
// `left` holds one sentence for each thing the file does not carry.
export function moduleImportRows({target = 'netbox', parts, names, kept, deviceOf, moduleOf}) {
  const rows = [], left = [], said = new Set();
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
    if (bayId.includes(MODULE)) {
      left.push(`${device} ${bayId}: ${type.model} is not in the modules file. It is a module inside a card, and no module type here has a module bay to import it into.`);
      continue;
    }
    const lists = deviceOf(p.itemId), bay = bayAt(lists, bayId);
    if (!bay) {
      left.push(`${device} ${bayId}: ${type.model} is not in the modules file. ` + (lists
        ? `The device type ${lists.model} has no module bay at position ${bayId}.`
        : `${device} has no device type, so it has no module bays.`));
      continue;
    }
    rows.push(target === 'nautobot'
      ? {module_type__manufacturer__name: type.manufacturer, module_type__model: type.model,
         parent_module_bay__parent_device__name: device, parent_module_bay__name: bay.name, status__name: 'Planned'}
      : {device, module_bay: bay.name, module_type: type.model, status: 'planned'});
  }
  return {columns: MODULE_COLUMNS[target === 'nautobot' ? 'nautobot' : 'netbox'], rows, left};
}

// ── the cables file ─────────────────────────────────────────────────────
// The Rack Builder's media as a DCIM's cable type. Both targets accepted each
// of these and refused "os2". A media this page does not know, or none, is a
// blank type: the column is optional.
export const CABLE_TYPE = {os2: 'smf-os2', om3: 'mmf-om3', om4: 'mmf-om4', om5: 'mmf-om5', cat6: 'cat6', cat6a: 'cat6a',
                           dac: 'dac-passive', aoc: 'aoc'};
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
//   ends       cable-plugs.js cableFacts(rack).ends; unchecked: reading them failed
//   names      uniqueNames(items); kept: the ids of the devices in the devices file
//   resolve    end -> resolveEnd's answer for that end
//   uOf        endName's: how tall a device is
// `notes` are about rows that ARE written: a type left blank, a length changed.
export function cableImportRows({rack, target = 'netbox', names, kept, resolve, ends = new Map(), unchecked = false, uOf}) {
  const T = TARGET_NAME[target] || 'NetBox', nautobot = target === 'nautobot';
  const rows = [], left = [], notes = [], used = new Map();
  let dac = false;
  for (const f of cableFindings(rack, ends)) {
    const c = f.cable;
    let why = [], sides = [];
    if (unchecked || !f.checked) why = ['its ends could not be checked'];
    else if (f.loose.length)
      why = f.loose.map(l => `end ${l.side}, ${endName(rack, l.end, uOf)}, is not connected (${l.reason})`);
    else {
      sides = [['A', c.a], ['B', c.b]].map(([side, end]) => {
        const device = names.get(end.item)?.name ?? '';
        if (!kept.has(end.item)) return {why: `end ${side} is on ${device}, which is not in the devices file`};
        const r = resolve(end);
        if (!r.ok) return {why: `end ${side}, ${endName(rack, end, uOf)}: ${r.reason}`};
        const comma = [device, r.name].find(x => x.includes(','));
        if (!nautobot && comma != null) return {why: `end ${side}: NetBox reads a comma in a device or port name as a list, so "${comma}" cannot be written`};
        return {side, end, device, name: r.name, type: r.type, key: JSON.stringify([device, r.type, r.name])};
      });
      why = sides.filter(s => s.why).map(s => s.why);
      if (!why.length && !canMeet(sides[0].type, sides[1].type))
        why = [`${T} does not cable ${KIND[sides[0].type]} to ${KIND[sides[1].type]}`];
      if (!why.length && sides[0].key === sides[1].key)
        why = [`its two ends are the same port, ${sides[0].name} on ${sides[0].device}`];
      if (!why.length)
        why = sides.filter(s => used.has(s.key))
          .map(s => `end ${s.side}, ${endName(rack, s.end, uOf)}, already has cable ${used.get(s.key)} in this file`);
    }
    if (why.length) { left.push(`Cable ${f.name} is not in the cables file: ${why.join('; ')}.`); continue; }
    const [a, b] = sides;
    for (const s of sides) used.set(s.key, f.name);
    const type = cableType(c.media);
    if (c.media && !type) notes.push(`Cable ${f.name}: its media (${c.media}) has no ${T} cable type, so its type is blank.`);
    dac ||= c.media === 'dac';
    const len = importLength(c, target);
    if (len.note) notes.push(`Cable ${f.name}: ${len.note}.`);
    // A label or a description over the field's length is cut to it, not the cable dropped.
    const along = c.length?.source === 'routed' && len.value !== '';
    let label = flat(c.label || c.id), description = c.purpose || '';
    if (along && !nautobot) description = description ? `${description}. Length measured along its route.` : 'Length measured along its route.';
    else if (along) notes.push(`Cable ${f.name}: length measured along its route.`);
    if (charCount(label) > DCIM_LIMITS.cableLabel) {
      notes.push(`Cable ${f.name}: its label is ${charCount(label)} characters and ${T} takes ${DCIM_LIMITS.cableLabel}, so the label is shortened to that.`);
      label = cutTo(label, DCIM_LIMITS.cableLabel);
    }
    if (!nautobot && charCount(description) > DCIM_LIMITS.cableDescription) {
      notes.push(`Cable ${f.name}: its purpose is ${charCount(description)} characters and ${T} takes ${DCIM_LIMITS.cableDescription} in a description, so the description is shortened to that.`);
      description = cutTo(description, DCIM_LIMITS.cableDescription);
    }
    rows.push(nautobot
      ? {a_device: a.device, a_type: a.type, a_name: a.name, b_device: b.device, b_type: b.type, b_name: b.name, type,
         status: 'Planned', label, color: '', length: len.value, length_unit: len.unit}
      : {side_a_device: a.device, side_a_type: a.type, side_a_name: a.name, side_b_device: b.device, side_b_type: b.type,
         side_b_name: b.name, type, status: 'planned', label, color: '', length: len.value,
         length_unit: len.unit, description});
  }
  if (dac) notes.push('A DAC is written as dac-passive. Change the type of one that is active.');
  return {columns: CABLE_IMPORT_COLUMNS[nautobot ? 'nautobot' : 'netbox'], rows, left, notes};
}

// ── README.txt ──────────────────────────────────────────────────────────
// What to do with each file, in order; what must already exist; and
// everything the kit could not carry. It replaces NOTES.txt and keeps its
// content (`notes`).
//   rows      how many rows each CSV holds: {rack, devices, modules, cables}
//   typeFiles how many YAML files are under types/
//   left      a sentence for each device, module and cable the files leave out
//   notes     what the types and the written rows need said (a best-guess type,
//             a length that was rounded)
//   script    whether import_cables.py is in the zip (Nautobot)
// Returns {text, notes}: `notes` are the lines the file carries beyond its
// instructions, which is what the page's status line counts.
export const KIT_FILES = {
  netbox: {rack: '1-rack.csv', devices: '2-devices.csv', modules: '3-modules.csv', cables: '4-cables.csv'},
  nautobot: {devices: '1-devices.csv', modules: '2-modules.csv', cables: '3-cables.csv'}};
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
                           left = [], notes = [], script = true, scriptUrl = null, width = README_WIDTH}) {
  const nautobot = target === 'nautobot', T = TARGET_NAME[nautobot ? 'nautobot' : 'netbox'];
  const F = KIT_FILES[nautobot ? 'nautobot' : 'netbox'];
  const site = String(dcim?.site ?? '').trim(), role = String(dcim?.role ?? '').trim();
  const place = nautobot ? 'location' : 'site', cols = nautobot ? ['location__name', 'role__name'] : ['site', 'role'];
  const blank = [!site && cols[0], !role && cols[1]].filter(Boolean);
  const warning = blank.length
    ? `${F.devices} will be refused as it is: its ${blank.join(' and ')} ${blank.length === 1 ? 'column is' : 'columns are'} blank, and ` +
      `${T} requires ${blank.length === 1 ? 'it' : 'both'}.${!nautobot && !site ? ` ${F.rack}'s site column is blank too.` : ''} ` +
      `Set the ${[!site && place, !role && 'device role'].filter(Boolean).join(' and the ')} under Export, DCIM import settings, ` +
      `and export again; or fill ${blank.length === 1 ? 'that column' : 'those columns'} in by hand.`
    : '';
  const numbered = rack.frame.numbering === 'top-down' ? 'numbered from the top' : 'numbered from the bottom';
  const out = [];
  // No paragraph holds a line break of its own, whatever it was handed (kitNames, above).
  const para = (text, first = '', hang = '  ') => out.push(...wrap(flat(text), first, hang, width));
  para(`${T} import kit for ${rack.name}, from the Portrayal Rack Builder, ${isoDate(date)}.`);
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
    step(5, `${F.cables} (${rowsText(rows.cables)}): Cables > Import.`);
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
    item('Steps 4 and 5 find a device by its name in every site, and step 4 finds a module type by its model in every manufacturer: ' +
         'a name NetBox already has twice is refused as not unique.');
  }
  out.push('');

  const missing = nautobot && !script
    ? [`${KIT_SCRIPT} could not be fetched, so it is not in this zip. It is at ${scriptUrl || `https://portrayal.dev/site/rack/nautobot/${KIT_SCRIPT}`}.`] : [];
  const gone = [...missing, ...left];
  out.push('Not in this kit:');
  if (gone.length) gone.forEach(item); else item('Nothing: every device, card and cable in this rack is in the files.');
  out.push('');
  if (notes.length) { out.push('Notes:'); notes.forEach(item); out.push(''); }
  return {text: `${out.join('\n').trimEnd()}\n`, notes: [...(warning ? [warning] : []), ...gone, ...notes]};
}
