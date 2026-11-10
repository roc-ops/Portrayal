// WHAT AN INFRAHUB OBJECT LOAD TAKES FROM A RACK, as data. Pure: no DOM, no
// fetch, so `node --test` covers the rules. This module writes the rack's site
// (where the rack file names one), the rack and one device per placed item, as
// the object documents of docs/infrahub-export-design.md sections 3.3 and 3.4.
// Interfaces, modules and cables are not written here (the design note's 3.5 to
// 3.7): each needs a format fact no held document gives. The device types come
// from the device-side exporter (spec/tools/dev/infrahub_export.py), which
// writes where --out says.
//
// THE FORMAT IS NOT CONFIRMED AGAINST AN INFRAHUB INSTANCE. These are
// stand-ins, and the README text below says each to the user:
//   - a document is `apiVersion: infrahub.app/v1`, `kind: Object`,
//     `spec: {kind, data}`, the design note's reading of the schema library's own
//     object files. That `data` is a list, and that one file holds several
//     documents, are this module's own assumptions; the note does not give them.
//   - a file's body is JSON, which is YAML, one document after each `---` line.
//   - a site is written with its `name` alone, and a rack with `name`, `height`
//     and `site`, and no `status`: the note does not list their other fields.
//   - a rack's site, and a device's type, are written as the plain name string
//     (as the device-side files write a manufacturer).
//   - a device's rack is the design note's nested block,
//     `location: {kind: LocationRack, data: {name, site}}`. Whether the site and
//     the rack must be loaded before the devices, or may be inline, is open.
//   - `position` is a whole number, left out for a device with no U position;
//     `rack_face` is always written. Whether either may be absent is open.
//   - `status` is NOT written. The kit's NetBox files write `planned`, which a
//     device here has no value for; it is not chosen here, so the instance's
//     default applies.
//   - `numbering: top-down` has no field: positions are written
//     bottom-up (the note's 3.4), whatever the rack's labels say.
//   - the type name is `<manufacturer> <model>`, the rule of `type_name()` in
//     spec/tools/dev/infrahub_export.py (copied, not imported).
import {firstU, holderOf} from './model.js';
import {itemUnits, isZeroUPart} from './fit.js';
import {uniqueNames, flat} from './export-data.js';

export const API_VERSION = 'infrahub.app/v1';
// A file's name carries its place in the load order.
export const FILES = {sites: '1-sites.yml', racks: '2-racks.yml', devices: '3-devices.yml'};

export const typeName = t => `${flat(t.manufacturer).trim()} ${flat(t.model).trim()}`;
const objectDoc = (kind, data) => ({apiVersion: API_VERSION, kind: 'Object', spec: {kind, data}});

// THE OBJECTS OF ONE RACK. `items` carry their height `u` (fit.js itemsWithU);
// one that does not is given it from `chassisOf` when that is passed, and counts
// as 1U otherwise. `types` maps an item's id to {manufacturer, model}: the device
// type it is. The rack file has one level of place, `dcim.site`; it is the
// LocationSite the rack stands in.
//
// A DEVICE IS NAMED AS THE NETBOX AND NAUTOBOT FILES NAME IT (uniqueNames), so
// the kits agree; Infrahub keeps a device name unique across the instance. A
// device with no type, or one whose type has no maker, is not an object: it is in
// `skipped` with the sentence the README carries. A device with no U position
// on the rails (a part beside the rack, a manager on the rail face, an item a
// shelf or rail holds) is written in the rack with no `position`.
export function infrahubObjects({rack, items: given, types, chassisOf = null}) {
  const items = given.map(it => (it.u != null ? it : {...it, u: chassisOf ? itemUnits(it, chassisOf) : 1}));
  const names = uniqueNames(items);
  const site = flat(rack.dcim?.site ?? '').trim(), rackName = flat(rack.name).trim();
  const notes = [], skipped = [], devices = [];
  if (!site) notes.push('The rack has no site. A rack needs one, so the rack and its devices are written without it and a load will be refused until the site is filled in; fill it in and export again.');
  const where = {kind: 'LocationRack', data: {name: rackName, ...(site ? {site} : {})}};
  let floored = 0, beside = 0;
  for (const it of items) {
    const name = names.get(it.id).name, t = types.get(it.id);
    if (!t || !t.model || !flat(t.manufacturer).trim()) {
      skipped.push({id: it.id, name, reason: `${name} has no device type with a maker, so it is not in the devices file. Add the type and the device by hand.`});
      continue;
    }
    const off = isZeroUPart({mount: it.mount}) || it.mount === 'rack-face' || (holderOf(it) != null && it.mount != null);
    const entry = {name, device_type: typeName(t), rack_face: it.face === 'rear' ? 'rear' : 'front', location: where};
    if (off) beside++;
    else {
      // bottom-up from 1 whatever the rack's labels are (the note's 3.4): `ru` is the bottom as stored
      if (!Number.isInteger(it.ru)) floored++;
      entry.position = Math.floor(it.ru);
    }
    devices.push(entry);
  }
  if (rack.frame.numbering === 'top-down')
    notes.push('The rack numbers its units from the top. Infrahub\'s rack has no field for that, so each position counts from the bottom, from 1; the labels on the physical rack differ.');
  if (firstU(rack.frame) !== 1)
    notes.push(`The rack numbers its units from ${firstU(rack.frame)}; each position counts from 1.`);
  if (floored)
    notes.push(`${floored} device${floored === 1 ? ' is' : 's are'} at a half unit. A position is a whole number here, so it is written rounded down, and the device then shares its lower unit.`);
  if (beside)
    notes.push(`${beside} device${beside === 1 ? ' has' : 's have'} no U position (0U, on a rail face, or held by another device), so ${beside === 1 ? 'it is' : 'they are'} in the rack with no position.`);
  notes.push('Status is not written, so the instance\'s default applies. The kit\'s NetBox and Nautobot files write planned; a device here has no such value.');
  const rackData = {name: rackName, height: rack.frame.heightRU, ...(site ? {site} : {})};
  const files = {
    ...(site ? {[FILES.sites]: [objectDoc('LocationSite', [{name: site}])]} : {}),
    [FILES.racks]: [objectDoc('LocationRack', [rackData])],
    [FILES.devices]: [objectDoc('DcimDevice', devices)],
  };
  return {files, devices, skipped, notes};
}

// One file as text: one YAML document per object document. JSON is YAML, so
// each is written as JSON, which needs no YAML writer in the kit.
export const fileText = docs => docs.map(d => `---\n${JSON.stringify(d, null, 2)}\n`).join('');

// THE README WRITTEN BESIDE THE FILES: the load order, what is left out, and
// what is not confirmed.
export function infrahubReadme({notes, skipped}) {
  const lines = [
    '# Infrahub objects for one rack',
    '',
    'Load the schema first: the schema library\'s DCIM schema with its rack, location_site and cable extensions, then the Portrayal overlay (see docs/infrahub-export-design.md). Then load the device types from the library export, then these files in file-name order:',
    '',
    ...Object.values(FILES).map(f => `- ${f}`),
    '',
    '## Not confirmed',
    '',
    'None of this was loaded into an Infrahub instance. Assumed:',
    '- the object file shape (`apiVersion: infrahub.app/v1`, `kind: Object`, `spec: {kind, data}`), with `data` a list and several documents in one file, each after a `---` line and written as JSON;',
    '- a site is written with its name alone, and a rack with its name, height and site and no status; their other fields are not listed in the design note;',
    '- a site and a device type are named by a plain string, and a device names its rack by a nested `location` block;',
    '- `position` may be absent for a device with no U position, and `rack_face` may be written for every device;',
    '- the site and the rack may need loading before the devices (the file order does that).',
    'Before relying on the files, run `infrahubctl object validate`, then `infrahubctl object load`.',
    '',
    '## Left out',
    '',
    'Interfaces, modules and module bays, cables, and the rack\'s kind, depth and numbering.',
    '',
    '## This rack',
    '',
    ...notes.map(n => `- ${n}`),
    ...skipped.map(s => `- ${s.reason}`),
  ];
  return lines.join('\n') + '\n';
}
