# Device42 spreadsheet export: the mapping

What a Portrayal rack and the device types map to in Device42's spreadsheet
import, column by column, and what that import cannot take. Written
2026-11-05; checked against three pages of Device42's documentation on
2026-11-11.

## What this rests on, and what it does not

Three pages of Device42's documentation are read for this note, cited by title
as printed:

- **A.** "Importing Data from Existing Spreadsheets" (Steps 1 to 6).
- **B.** "Spreadsheet Imports and Exports".
- **C.** "Tutorial: Loading Data Using Spreadsheets".

They name the required fields of most sheets, the file formats, the shape of a
sample file and the order to load in. They do not hold the sample files, which
Device42 serves from an instance (Tools, Imports/Exports) and which carry each
sheet's endpoint, request method and column headings. Those files are not held
here, so most headings below stay stand-ins. Nothing has been loaded into a
Device42 instance.

### Lines the note uses

| Page | Line |
|---|---|
| A | "Name = building name is the only parameter required" (Step 1) |
| A | "Name = room name, and building name are both required" (Step 2) |
| A | "Name = rack name, size (u size), and room name are all required" (Step 3) |
| A | "Name = hardware model name is required." and, as Step 4's next line, "Type, size (u size)*, and manufacturer are optional" |
| A | "U Size is required for adding devices to racks." (note to Step 4) |
| A | "Name = hardware model name is required." (Step 5, devices) |
| A | "Device = device name and start_at are required." (Step 6) |
| A | "existing data in .xls format" (the opening paragraph) |
| B | "They contain the API endpoint, request method, and column headings." (the first three rows) |
| B | "Save the file as .xls or .xlsx." |
| B | A category that shows Create or Add, and not Modify or Update, "adds new records instead of updating existing ones". |
| C | "/api/1.0/buildings/ and POST" (rows 1 and 2 of the buildings sample) |
| C | "The third row contains the field names, such as name, address, and contact_name." |
| C | "A unique building name or building_id is required to add a new room record" |
| C | The order to load: Add Buildings, Add Rooms, Add Vendors, Add Racks, Add Hardware Models, Add Devices, Add Devices to Racks. |

### What the pages settle

- **The format.** The pages name `.xls` and `.xlsx` and no other format. The
  sheets this change writes are CSV. No page says CSV is refused, and none says
  it is taken.
- **The shape of a sample file.** Row 1 is the API endpoint, row 2 the request
  method, row 3 the column headings, data from row 4. The first three rows are
  not changed. The CSV sheets written here have the headings only.
- **The required fields**, as the pages word them: buildings `name`; rooms
  `name` and the building's name; racks `name`, `size` and the room's name;
  hardware models `name`, with `type`, `size` and `manufacturer` optional;
  devices to racks the device's name and `start_at`.
- **The size matters.** A hardware model's size in U is needed to put a device
  in a rack, so the hardware-model sheet always writes one.
- **The order.** The tutorial loads vendors between rooms and racks. Page A's
  steps leave vendors out.

### What the pages do not settle

- The endpoint and the headings of rooms, racks, hardware models, devices and
  devices to racks. Page C gives the buildings sheet's endpoint only. The
  spelling of row 3 is seen for the buildings sheet's `name` alone.
- Whether a headings cell is `building` or `building_id` on the rooms sheet
  (page C names `building_id`, a number a rack file does not hold), what the
  room, the hardware model of a device and the rack of a placement are called.
- Which of the two names the devices sheet's `name` is. Page A's Step 5 line
  repeats Step 4's words, "hardware model name".
- A vendors sheet: its headings, and whether a manufacturer must exist before a
  hardware model names it. Page A says "Vendor must already exist" only of
  assets.
- The values of `type`, whether `size` takes a fraction, and whether a hardware
  model's name is unique across manufacturers.
- Whether the CSV sheets load at all.

## The sheets, in import sequence

| # | Sheet | File | Written from |
|---|---|---|---|
| 1 | buildings | `1-buildings.csv` | a rack file's `dcim.site` |
| 2 | rooms | `2-rooms.csv` | a rack file's `dcim.site` |
| 3 | racks | `3-racks.csv` | a rack file's name and frame |
| 4 | hardware models | `hardware-models.csv` | the NetBox device types |
| 5 | devices | `5-devices.csv` | a rack file's items |
| 6 | devices to racks | `6-devices-to-racks.csv` | a rack file's items |

Sheets 1, 2, 3, 5 and 6 are written for one rack by `kit/rack/device42.js`
(`device42Sheets`, `sheetCsv`). Sheet 4 is written once for the library by
`spec/tools/dev/device42_export.py`. The vendors step of page C has no sheet
here; it would sit between 2 and 3.

## Each header: named on a page, or a stand-in

| Sheet | Header | Status | Page line |
|---|---|---|---|
| 1 buildings | `name` | named | A Step 1, and C row 3 |
| 2 rooms | `name` | named | A Step 2 |
| 2 rooms | `building` | stand-in | A says "building name"; C also names `building_id` |
| 3 racks | `name`, `size` | named | A Step 3 |
| 3 racks | `room` | stand-in | A says "room name" |
| 4 hardware models | `name`, `size`, `manufacturer` | named | A Step 4 |
| 4 hardware models | `type` | named, not written | A Step 4 (optional) |
| 5 devices | `name`, `hardware` | stand-in | A Step 5 repeats Step 4's "hardware model name"; no parameter is named for the model |
| 6 devices to racks | `device`, `start_at` | named | A Step 6 |
| 6 devices to racks | `rack` | stand-in | A Step 6 names no rack parameter |

"Named" means a page prints the parameter; it is not the spelling of row 3,
which only the sample files hold. A stand-in is a guess no page confirms. A
real header that differs changes every file of that sheet.

`device` replaces the earlier `name` on sheet 6: Step 6 reads "Device = device
name", where Steps 1 to 3 read "Name = building name", "Name = room name" and
"Name = rack name".

## Running it, and why nothing is published yet

```sh
python3 spec/tools/dev/device42_export.py --out <folder>
```

The tool reads `library/exports/netbox/device-types/` and writes
`hardware-models.csv` and a `README.md` into `<folder>`; it has no default
folder. Nothing it writes is committed: the sheet is not published yet, and
publishing it with the other exports is a later change, which needs a
`publish.sh` line and a matching preflight change.

### 1. buildings: `name`

The rack's `dcim.site`. The rack file has one level of place, so the site is
the building. A rack with no site has no building row, and the export says so.

### 2. rooms: `name`, `building`

The same site, as the one room in that building. Device42 distinguishes a
building from a room and the rack file does not, so this is a stand-in for a
fact the file does not hold.

### 3. racks: `name`, `size`, `room`

`name` is the rack's name, `size` its `frame.heightRU`, `room` the site. The
rack's width, depth, hole style and whether its units count from the top are
not written. A rack that numbers its units from another start says so in the
export's notes; `start_at` counts from 1.

### 4. hardware models: `name`, `size`, `manufacturer`

One row for each model, sorted by maker then model. From the committed device
type: `name` is the model as the maker prints it (`model`), `size` is
`u_height` as written (`1.0` is `1`, `0.5` is `0.5`), `manufacturer` is the
maker.

- **Name rule.** The model as the maker prints it, under the real maker, not
  `<maker> <model>`. Device42 is reported to key a hardware model by name, and
  the maker already has a column. Cost: two makers that print one model name
  would write two rows with one name. The tree holds none today (the tool
  counts them).
- **NOS relistings.** The NetBox tree files a box again under each NOS vendor
  that lists it (Arrcus, IP Infusion, DriveNets, SONiC), often under the NOS
  vendor's own name for it. Device42's hardware model is the real maker and
  model, so a relisting is not a second model. The exporter writes a
  relisting's first `comments` line as "<vendor> lists <maker> <model> (NOS:
  <nos>)."; a maker's own type has no such line, so a file with that line is a
  relisting and a file without it is a model. A relisting whose maker has no
  file of its own is written once under that maker; none is today.
- **`type` is not written.** Page A names it as optional. A device type holds
  no kind of device (switch, server, patch panel), and no page gives the values
  the import allows.
- **Half units.** `u_height` is a multiple of 0.5. Whether Device42's size takes
  a fraction is not known; the number is written as it is. Six types have a
  fraction: Fibrain XCU10-21IC, XCU10-31IC, XCU10-41ID and XCU10-51ID (0.5),
  BATM/Telco Systems TM-7124S (1.5) and Juniper MX104 (3.5).
- **0U types.** 88 types have `u_height` 0 (not mounted in the rails). They are
  written with size `0`. Page A says a size is required to put a device in a
  rack; it does not say what a hardware model of size 0 is.

### 5. devices: `name`, `hardware`

`name` is the device's label, made unique as the NetBox and Nautobot files make
it (`uniqueNames`), so the three agree. `hardware` is the model name of its
hardware-model row. Both are stand-ins: see the table above. A device with no
device type is not a row; it is named in the export's `skipped` list.

### 6. devices to racks: `device`, `rack`, `start_at`

`device` is the name as in sheet 5, `rack` the rack's name, `start_at` the
lowest unit the device fills, as the rack labels it, counted from 1, a half
unit as it is (`10.5`). `auto` is not used: page A reports it only as available
since release 5.3.5, and a placement is a fact the rack file has. A device with
no U position (a part beside the rack, a manager on the rail face, an item a
shelf or rail holds) is a device row with no placement, and `skipped` names it.
Page A says `start_at` is the "starting U location of device"; whether that is
the lowest unit for a rack that counts its units downward is not stated.

## What the importer is reported not to take

- ports and interfaces, connections (cables), and model images: no import is
  described, so the sheets carry none of them. They are a later step.
- The device type's depth, weight, airflow, part number and description.
- Anything but the first six sheets; Device42's API is not used.

## Re-importing

Page B says a category that shows Create or Add, and not Modify or Update, adds
new records on every import. Page A names the rooms, racks and devices-to-racks
samples "Create Rooms", "Create Racks" and "Add devices to racks", so importing
the same rack twice is expected to repeat them. Buildings, hardware models and
devices are "Create or update". This is read from the sample names and not
tried.

## Left out of this change

`.xls` and `.xlsx` (the sheets are CSV), the three heading rows of a sample
file, a vendors sheet, ports, images, cables, and loading into a real instance.

## Open questions

1. The real headings of rooms, racks, hardware models, devices and devices to
   racks, and each sheet's endpoint: the sample files hold them and are not
   held. The headers marked stand-in above stay so until then.
2. Does a hardware model's size take a fraction, and does `0` mean "not in a
   rack"?
3. Is a hardware model's name unique across manufacturers? That decides the
   name rule above.
4. Does the importer accept CSV? Pages A and B name `.xls` and `.xlsx` only.
   Writing either needs a file-writing library, or a hand-built package for
   `.xlsx`, and the endpoint cells the pages do not give.
5. Which `type` values exist, and may the export write one?
6. Should the sheet be re-written by the publish step, as the NetBox and
   Nautobot trees are? It would change with every device change.
7. Does the vendors step need a sheet, and does a hardware model create its
   manufacturer or need it to exist?
