// WHAT A DEVICE42 SPREADSHEET IMPORT TAKES FROM A RACK, as data. Pure: no DOM,
// no fetch, so `node --test` covers the rules. Device42's import loads
// buildings, rooms, racks, hardware models, devices and devices-to-racks, in
// that sequence; this module writes the five sheets a rack file has the facts
// for. The hardware models come from the device types
// (spec/tools/dev/device42_export.py, written where --out says).
//
// EACH HEADER IS NAMED ON A DEVICE42 PAGE OR IS A STAND-IN. Three pages of
// Device42's documentation name some parameters (NAMED) and not others
// (STAND_INS): `building`, `room`, `hardware` (the model a device is), `rack`
// and the devices sheet's `name` are guesses the pages do not settle. The
// sample files, which hold each sheet's row 3, are not held, so the spelling of
// row 3 is seen only for the buildings sheet's `name`.
// docs/device42-export-design.md quotes the line behind each header.
import {positionOf, firstU, holderOf} from './model.js';
import {itemUnits, isZeroUPart} from './fit.js';
import {uniqueNames, flat, toCsv} from './export-data.js';

export const COLUMNS = {
  buildings: ['name'],
  rooms: ['name', 'building'],
  racks: ['name', 'size', 'room'],
  devices: ['name', 'hardware'],
  'devices-to-racks': ['device', 'rack', 'start_at'],
};
export const NAMED = {
  buildings: ['name'],
  rooms: ['name'],
  racks: ['name', 'size'],
  'devices-to-racks': ['device', 'start_at'],
};
export const STAND_INS = {
  rooms: ['building'],
  racks: ['room'],
  devices: ['name', 'hardware'],
  'devices-to-racks': ['rack'],
};
// A file's name carries its place in the import sequence; 4 is the hardware
// models, written from the library and not from a rack.
export const FILES = {
  buildings: '1-buildings.csv', rooms: '2-rooms.csv', racks: '3-racks.csv',
  devices: '5-devices.csv', 'devices-to-racks': '6-devices-to-racks.csv',
};

// THE SHEETS OF ONE RACK. `items` carry their height `u` (fit.js itemsWithU); one
// that does not is given it from `chassisOf` when that is passed, and counts as
// 1U otherwise. `types` maps an item's id to {manufacturer, model}: the hardware
// model it is. The rack file has one level of place, `dcim.site`, so the site
// is written as the building and as the room in it.
//
// A DEVICE IS NAMED AS THE NETBOX AND NAUTOBOT FILES NAME IT (uniqueNames), so
// the three kits agree. `start_at` is the device's lowest U as the rack labels
// it, a half unit as it is; `auto` is not used, since a placement is a fact the
// rack file has. A device that has no model is not a device row. A device
// with no U position on the rails (a part beside the rack, a manager on the rail
// face, an item a shelf or rail holds) is a device row with no placement, and
// `skipped` names it and says why.
export function device42Sheets({rack, items: given, types, chassisOf = null}) {
  const items = given.map(it => (it.u != null ? it : {...it, u: chassisOf ? itemUnits(it, chassisOf) : 1}));
  const names = uniqueNames(items);
  const site = flat(rack.dcim?.site ?? '').trim(), rackName = flat(rack.name).trim();
  const notes = [], skipped = [];
  if (!site) notes.push(`The rack has no site, so its room is blank and there is no building or room row; fill the site in and export again.`);
  const devices = [], placed = [];
  for (const it of items) {
    const name = names.get(it.id).name, t = types.get(it.id);
    if (!t || !t.model) {
      skipped.push({id: it.id, name, reason: `${name} has no hardware model, so it is not in the devices sheet or placed in the rack.`});
      continue;
    }
    devices.push({name, hardware: t.model});
    const beside = isZeroUPart({mount: it.mount}) || it.mount === 'rack-face';
    if (beside || (holderOf(it) != null && it.mount != null)) {
      skipped.push({id: it.id, name, reason: `${name} has no U position on the rails (${beside ? 'a 0U part' : 'held by another device'}), so it is a device with no placement.`});
      continue;
    }
    placed.push({device: name, rack: rackName, start_at: positionOf({...rack.frame, startU: 1}, it.ru, it.u)});
  }
  if (firstU(rack.frame) !== 1)
    notes.push(`The rack numbers its units from ${firstU(rack.frame)}; start_at counts from 1.`);
  const sheets = {
    buildings: {columns: COLUMNS.buildings, rows: site ? [{name: site}] : []},
    rooms: {columns: COLUMNS.rooms, rows: site ? [{name: site, building: site}] : []},
    racks: {columns: COLUMNS.racks, rows: [{name: rackName, size: rack.frame.heightRU, room: site}]},
    devices: {columns: COLUMNS.devices, rows: devices},
    'devices-to-racks': {columns: COLUMNS['devices-to-racks'], rows: placed},
  };
  return {sheets, skipped, notes};
}

// One sheet as CSV text, as the NetBox kit writes its files (RFC 4180, CRLF).
export const sheetCsv = sheet => toCsv(sheet.columns, sheet.rows);
