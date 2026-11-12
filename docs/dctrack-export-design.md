# Sunbird dcTrack export: the mapping

What the device types and a Portrayal rack map to in Sunbird dcTrack, field by
field, which headers a guide prints and which are still stand-ins, and what this
part leaves out. Written 2026-11-11. Issue #1112.

## What this rests on

Two Sunbird guides were read:

- **dcTrack 6.0.3 User Guide** (Sunbird Software). The chapter "Use File Import
  to Add, Edit and Delete Locations, Items and Connections" has its import
  template section on PDF pages 533 to 540 (printed 387 to 394). Its sample worksheets and their notes are the
  figures on PDF pages 535, 536 and 537 (printed 389 to 391). "Use File Import
  to Create Power and Data Connections" is on PDF page 553 (printed 407). The
  Models Library is on PDF pages 439 and 445 (printed 293 and 299).
- **dcTrack 8.0.0 Implementation Guide**. "High-Level Steps to Perform a File
  Import" is on PDF pages 17 to 22. The same sample worksheets are on PDF page
  19, and the Export menu with "Download Import Template" on PDF page 18.

Page numbers are PDF pages. The guides print their worksheets as screenshots,
so a header is cited to the figure it is read from.

Where the two guides differ, this note follows the newer (8.0.0) and says so.
They print the same locations and rack PDU worksheets. What they say alike, and
the differences found:

- Both guides say the Classic View import should be used for power outlet
  circuiting only (6.0.3 PDF page 533; 8.0.0 PDF page 17). Nothing here touches
  Classic View.
- 6.0.3 prints the rack PDU worksheet's `Location` header with an asterisk on PDF
  page 537 and without one on PDF page 535; 8.0.0 prints it without (PDF page
  19). The writer treats a location as required for every row.
- 6.0.3's text calls a location column "Locate Picture Path" and one of its
  figures prints "Location Picture Path" (PDF page 537). That column is not
  written.

The issue's other documents (the API help for version 9.1.1, a sample model
export, the list of port types) are not held.

## What the import takes

The import template is a workbook with a sheet for each step: "Step 1 Add
Locations", "Step 2 Add Cabinets", "Step 3 Add Rack PDUs", "Step 4 Add Devices",
"Step 5 Create Power Connections" and "Step 6 Create Data Connections" (the tabs
in the figure on PDF page 553). File Import takes `.XLS`, `.XLSX` and `.CSV`
(PDF page 534), imports the sheet that is open and ignores the others (PDF page
535), and wants the steps in order, since "you cannot reference items that are
not already imported" (PDF page 535). A cell that starts with `#` is ignored; the
first header, `# Operation`, keeps its `#` (PDF page 536). A required field is
marked with `*` and a field needed to put an item in the Installed status with
`**`. An item with no status is imported as Planned (PDF pages 536 and 537).
The model must already be in the Models Library: "Values provided for make, and
model must match an entry from the dcTrack Make and Model lists" (PDF page 536).

## The sheets, in load order

| # | Sheet | File | Written from |
|---|---|---|---|
| 0 | model list | `models.csv` | the NetBox device types |
| 1 | locations | `1-locations.csv` | a rack file's `dcim.site` |
| 2 | cabinets | `2-cabinets.csv` | a rack file's name |
| 4 | devices | `4-devices.csv` | a rack file's items |

Sheet 3, the rack PDUs, is not written (see "What is left out"). Sheet 0 is
written once for the library by `spec/tools/dev/dctrack_export.py`; the others
are written for one rack by `kit/rack/dctrack.js` (`dctrackSheets`, `sheetCsv`).
Nothing is published: the tool has no default folder, and publishing is a later
change.

```sh
python3 spec/tools/dev/dctrack_export.py --out <folder>
```

### Headers: what a guide prints, and what it does not

Each header is written without the asterisk that marks a required field. The
guides do not say whether the importer reads the asterisk as part of the name
(open question 1).

| Sheet | Header | Source |
|---|---|---|
| locations | `# Operation`, `Object`, `dcTrack Location Code`, `dcTrack Location Name`, `Data Center Area`, `Country` | printed, all required: 6.0.3 PDF pages 536 and 537; 8.0.0 PDF page 19 |
| locations | `Units` | printed, optional: 6.0.3 PDF page 537 (the worksheet whose second row reads `SI`) |
| cabinets | `# Operation`, `Object`, `Name`, `Make`, `Model`, `Location` | printed, all required: 6.0.3 PDF page 537 (the figure with the Status column) |
| devices | `# Operation`, `Object`, `Name`, `Make`, `Model`, `Location`, `Cabinet` | printed on the rack PDU worksheet, which shares them: 6.0.3 PDF pages 535 and 537; 8.0.0 PDF page 19 |
| devices | `U Position`, `Orientation` | named in the template's notes ("U Position can be any unoccupied position...", "Orientation indicates how item is mounted...", PDF page 536) and in the Items List; **not shown as a header cell** |
| model list | `Make`, `Model Name`, `Height (RUs)` | the Models Library's grid, 6.0.3 PDF page 439 |
| model list | `Weight (kg)` | **stand-in**: "Enter the model's weight", no unit (PDF page 445); the item form prints "Weight (lbs)" and "H x W x D (in.)" for a US-unit location (PDF page 584) |

Values the guides print:

- `# Operation`: `ADD`, `EDIT` or `DELETE` (PDF page 533). Only `ADD` is written.
- `Object`: `LOCATION` and `CABINET` (PDF page 537). The rack PDU worksheet
  prints `RACK PDU-ZERO U` (PDF page 535).
- Location Code: a user-defined label, unique within dcTrack for a data center,
  "Maximum of 20 characters". Location Name: unique within dcTrack, "Maximum of
  50 characters" (6.0.3 PDF page 250). Data Center Area and Country are required
  (the same page and the figure on PDF page 536).
- `Units`: `SI` for a metric location; "If you configure a location to use SI
  (metric) units, you must provide metric values in the spreadsheet for that
  location" (PDF pages 536 and 537). The writer gives every location `SI`, since
  the library's sizes and weights are metric.
- An item's `Location` is the location's code: the sample's location `BDGWTR` is
  named by its cabinets (PDF page 537).
- An item name: "up to 64 alphanumeric characters" and none of `\ & ? '` (PDF
  page 584). The template says it must be unique within its location (PDF page
  536).
- `U Position`: "any unoccupied position on Both, Front, or Back rails as needed
  to accommodate the RU size of the item from this point and above" (PDF page
  536). That is the item's lowest unit, counted upward.
- Orientation, for a rackable item: "Item Front Faces Cabinet Front" or "Item
  Rear Faces the Cabinet Front" (the Cabinet Legend, PDF pages 111 and 112).

Stand-ins, which no page prints and which are open questions: the asterisk-less
headers; the `Object` value for a device (`DEVICE` is the class name, PDF page
62); the exact spelling an `Orientation` cell takes (the two phrases above are
the legend's description of the choice); and a location code taken from the
site (the guide says the code is user-defined). The file names and the sheet
numbers follow the template's tabs and are the tool's own.

## Rules

### 0. model list

One row for each model, sorted by make, then model.

- `Make` is the maker that built the box, from `manufacturer`. `Model Name` is the
  model as the maker prints it. `Height (RUs)` is `u_height` as written (`1.0`
  is `1`, `0.5` is `0.5`). The guide says a cabinet model "can be defined to be
  Zero U height" (PDF page 447); whether a fraction is taken is not stated.
- `Weight (kg)` is the file's `weight` in kilograms, blank when the file states
  none. The tool converts any other unit it meets.
- **NOS relistings.** The NetBox tree files a box again under each NOS vendor
  that lists it. A model is the real maker and model, so a relisting is not a
  second model: the rule of `docs/device42-export-design.md`. A relisting whose
  maker has no file of its own is written once, under that maker.
- **Part number.** None is written: no field of the Models Library names one
  (PDF pages 439 and 445). The issue asks for it; it is left out and listed here.

### 1. locations

The rack's `dcim.site`, as `dcTrack Location Name`, and as `dcTrack Location Code`
when it is 20 characters or fewer, with `Units` `SI`. A longer site leaves the code blank, and so
the `Location` of every later row, and the export says so. `Data Center Area` and
`Country` are required and no rack field holds them: both are blank and the
export says so. A rack with no site has no location row.

### 2. cabinets

The rack's name, in the location. `Make` and `Model` are required and must match
a cabinet model of the Models Library; a rack file names none, so both are blank
and the export says so. The rack's height, width, depth and numbering are not
written: dcTrack takes them from the cabinet model.

### 4. devices

One row for each item with a model: `Name` (the item's label, made unique as the
NetBox and Nautobot files make it), `Make` and `Model` (those of its row in the
model list), the location's code, the cabinet's name, `U Position` and
`Orientation`.

- `U Position` is the lowest unit the item fills, as the rack labels it, counted
  from 1. A half unit is written as it is.
- `Orientation` is "Item Front Faces Cabinet Front" for an item on the front
  face and "Item Rear Faces the Cabinet Front" for one on the rear face.
- An item with no model is not a row; an item with no U position is a row with a
  blank `U Position` and `Orientation` (a part beside the rack, a manager on the
  rail face, an item a shelf or rail holds). The export names each in `skipped`.
- A name over 64 characters, or with `\ & ? '`, is written as it is and noted.

## What is left out

| Left out | Why |
|---|---|
| data ports, power ports and port types | the list of port types dcTrack allows is not held |
| connections (cables) | the issue calls them a separate step; the guide's connection sheets (PDF page 553) are not written |
| model images | the issue calls them a separate step |
| the REST calls | the API help is not held; this part writes files only |
| the rack PDU sheet; Depth Position and Cabinet Side of a part beside the rack | a rack file does not say which item is a rack PDU, and holds no side or depth for a 0U part |
| the cabinet's Front Faces, Row Label, Position in Row; an item's Rails Used and Status | no rack field holds them; an item with no status is imported as Planned |
| Class, Mounting and Form Factor of a model; the model's part number, depth, airflow, description and comments | the device type does not state them, or no field is named |
| the cabinet's height, width, depth and numbering | dcTrack takes them from the cabinet model |
| facts with no field: datasheet, maturity, power envelope | no notes field is confirmed |
| a load into a dcTrack instance | none was available |

## Open questions

1. Does the importer read the asterisk as part of a header, or does it match the
   name without it? The guides show the asterisk in the header cell.
2. The `Object` value of a device, and the spelling of an `Orientation` cell.
3. Is a fractional or zero `Height (RUs)` taken? Is a model's weight in the unit
   of the location that holds the item (pounds for a US location, as the item
   form prints), so that `Weight (kg)` needs a conversion?
4. How is a model brought in: only by the Sunbird Master Models Library file
   and the Models Library page (PDF pages 445 and 439), or is there an import
   file? That decides the shape of the model list.
5. A location's Data Center Area and Country, and a cabinet's make and model:
   where do they come from for a rack file?
6. Which port types exist, and how does a NetBox port type map to one?
7. Does a notes field exist for a fact with no field?
