// WHAT A SUNBIRD DCTRACK FILE IMPORT TAKES FROM A RACK, as data. Pure: no DOM,
// no fetch, so `node --test` covers the rules. dcTrack's import template has one
// sheet for each step: locations, cabinets, rack PDUs, devices, then the power
// and data connections. This module writes the three a rack file has the facts
// for: locations, cabinets and devices. The models come from the device types
// (spec/tools/dev/dctrack_export.py, written where --out says).
//
// THE HEADERS ARE THE ONES THE GUIDES PRINT, except where this file says so.
// Source: Sunbird, dcTrack 6.0.3 User Guide, "Use File Import to Add, Edit and
// Delete Locations, Items and Connections", PDF pages 535 to 537 (the sample
// worksheets and their notes). The 8.0.0 Implementation Guide prints the same
// locations and rack PDU worksheets on PDF page 19. docs/dctrack-export-design.md
// lists each header with its page and what is still a stand-in.
import {positionOf, firstU, holderOf} from './model.js';
import {itemUnits, isZeroUPart} from './fit.js';
import {uniqueNames, flat, toCsv} from './export-data.js';

// Required fields (marked with an asterisk in the template) come first; the
// asterisk is the template's marking, and these headers are written without it.
export const COLUMNS = {
  locations: ['# Operation', 'Object', 'dcTrack Location Code', 'dcTrack Location Name', 'Data Center Area', 'Country', 'Units'],
  cabinets: ['# Operation', 'Object', 'Name', 'Make', 'Model', 'Location'],
  devices: ['# Operation', 'Object', 'Name', 'Make', 'Model', 'Location', 'Cabinet', 'U Position', 'Orientation'],
};
// A file's name carries its place in the import sequence ("Step 1 Add Locations",
// "Step 2 Add Cabinets", "Step 4 Add Devices"; step 3 is the rack PDUs and is
// not written). The model list is written from the library, not from a rack.
export const FILES = {locations: '1-locations.csv', cabinets: '2-cabinets.csv', devices: '4-devices.csv'};
// Named in the template's own notes ("U Position can be any unoccupied
// position...", "Orientation indicates how item is mounted...") and shown as
// columns of the Items List, but not as a header cell of a figure.
export const HEADERS_NOT_SHOWN_AS_CELLS = ['U Position', 'Orientation'];
// What no page prints. Each is a question in the note.
export const STAND_INS = [
  'every header: written without the asterisk that marks a required field',
  'devices.Object',
  'devices.Orientation values',
  'locations.dcTrack Location Code',
];
export const LEFT_OUT = [
  'data ports, power ports and port types: the vocabulary dcTrack allows is not held',
  'connections (cables) between ports',
  'model images',
  'the rack PDU sheet, and the Depth Position and Cabinet Side of a part beside the rack',
  "the cabinet's Front Faces, Row Label and Position in Row, and the item's Rails Used and Status (the rack file has no source; an item with no Status is imported as Planned)",
  "the cabinet's height, width and depth, and its numbering: dcTrack takes them from the cabinet model",
];

const LOCATION_CODE_MAX = 20, LOCATION_NAME_MAX = 50, ITEM_NAME_MAX = 64;
const ITEM_NAME_REFUSED = /[\\&?']/;
const ORIENTATION = {front: 'Item Front Faces Cabinet Front', rear: 'Item Rear Faces the Cabinet Front'};

// THE SHEETS OF ONE RACK. `items` carry their height `u` (fit.js itemsWithU); one
// that does not is given it from `chassisOf` when that is passed, and counts as
// 1U otherwise. `types` maps an item's id to {manufacturer, model}: the model it
// is. The rack file has one level of place, `dcim.site`, so the site is written
// as the location. An item's Location is the location's code, as the sample
// worksheets do (Location BDGWTR is the code of Bridgewater).
//
// AN ITEM IS NAMED AS THE NETBOX AND NAUTOBOT FILES NAME IT (uniqueNames), so the
// kits agree; the template says a name must be unique within its location.
// `U Position` is the item's lowest U as the rack labels it: the template says an
// item takes "this point and above". A half unit is written as it is. An item
// that has no model is not a row. An item with no U position on the rails (a
// part beside the rack, a manager on the rail face, an item a shelf or rail
// holds) is a row with a blank `U Position` and `Orientation`, and `skipped`
// names it and says why.
//
// A location's `Units` is `SI`, as the sample worksheet writes it for a metric
// location ("you must provide metric values in the spreadsheet for that
// location"): the library's sizes and weights are metric. The Data Center Area
// is blank, so no unit is yet at stake for it.
//
// A VALUE THE FILE CANNOT STATE IS BLANK AND NAMED IN `notes`: the location's
// Data Center Area and Country, and the cabinet's Make and Model, are required by
// the template and no rack field holds them. A name that is over a limit the
// guide prints, or has a character dcTrack refuses, is written as it is and noted.
export function dctrackSheets({rack, items: given, types, chassisOf = null}) {
  const items = given.map(it => (it.u != null ? it : {...it, u: chassisOf ? itemUnits(it, chassisOf) : 1}));
  const names = uniqueNames(items);
  const site = flat(rack.dcim?.site ?? '').trim(), cabinet = flat(rack.name).trim();
  const notes = [], skipped = [], rows = [];
  const code = site.length <= LOCATION_CODE_MAX ? site : '';
  if (!site) notes.push('The rack has no site, so its location is blank and there is no location row; fill the site in and export again.');
  else {
    if (!code) notes.push(`The site name is longer than a dcTrack Location Code takes (${LOCATION_CODE_MAX} characters at most), so the code is blank and so is the Location of each row; write a code.`);
    if (site.length > LOCATION_NAME_MAX) notes.push(`The site name is longer than a dcTrack Location Name takes (${LOCATION_NAME_MAX} characters at most).`);
    notes.push('The template requires a Data Center Area and a Country for a location, and a rack file has neither: both are blank.');
  }
  notes.push('The template requires a Make and Model for a cabinet, matching the Models Library, and a rack file names none: both are blank.');
  const refuse = (what, name) => {
    if (name.length > ITEM_NAME_MAX) notes.push(`${what} ${name} is longer than a dcTrack item name takes (${ITEM_NAME_MAX} characters at most).`);
    if (ITEM_NAME_REFUSED.test(name)) notes.push(`${what} ${name} has a character dcTrack refuses in an item name (\\ & ? ').`);
  };
  refuse('The cabinet', cabinet);
  for (const it of items) {
    const name = names.get(it.id).name, t = types.get(it.id);
    if (!t || !t.model) {
      skipped.push({id: it.id, name, reason: `${name} has no model, so it is not in the devices sheet.`});
      continue;
    }
    refuse('The item', name);
    const row = {
      '# Operation': 'ADD', Object: 'DEVICE', Name: name, Make: t.manufacturer ?? '', Model: t.model,
      Location: code, Cabinet: cabinet, 'U Position': '', Orientation: '',
    };
    const beside = isZeroUPart({mount: it.mount}) || it.mount === 'rack-face';
    if (beside || (holderOf(it) != null && it.mount != null))
      skipped.push({id: it.id, name, reason: `${name} has no U position on the rails (${beside ? 'a 0U part' : 'held by another device'}), so it is an item with no position.`});
    else {
      row['U Position'] = positionOf({...rack.frame, startU: 1}, it.ru, it.u);
      row.Orientation = ORIENTATION[it.face === 'rear' ? 'rear' : 'front'];
    }
    rows.push(row);
  }
  if (firstU(rack.frame) !== 1)
    notes.push(`The rack numbers its units from ${firstU(rack.frame)}; U Position counts from 1.`);
  const sheets = {
    locations: {
      columns: COLUMNS.locations,
      rows: site ? [{'# Operation': 'ADD', Object: 'LOCATION', 'dcTrack Location Code': code, 'dcTrack Location Name': site, 'Data Center Area': '', Country: '', Units: 'SI'}] : [],
    },
    cabinets: {
      columns: COLUMNS.cabinets,
      rows: [{'# Operation': 'ADD', Object: 'CABINET', Name: cabinet, Make: '', Model: '', Location: code}],
    },
    devices: {columns: COLUMNS.devices, rows},
  };
  return {sheets, skipped, notes};
}

// One sheet as CSV text, as the NetBox kit writes its files (RFC 4180, CRLF).
export const sheetCsv = sheet => toCsv(sheet.columns, sheet.rows);
