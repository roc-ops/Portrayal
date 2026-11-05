# Device42 spreadsheet export: the mapping

What a Portrayal rack and the device types map to in Device42's spreadsheet
import, column by column, and what that import cannot take. Written 2026-11-05.

## What this rests on, and what it does not

Device42's import page was **not read** for this note and is not held. What is
known of it is the issue's report of it ("DCIM export: Device42"):

- the spreadsheet import loads, in this sequence: buildings, rooms, racks
  (name, U size, room), hardware models (name required; type, size and
  manufacturer optional), devices, devices to racks (name and `start_at`);
- `start_at` can be `auto` since release 5.3.5;
- the page reads `.xls` files, and a newer generic importer is reported to take
  `.xls`, `.xlsx` and `.csv`;
- the page does not describe importing connections or model images.

Every column header below is therefore a **stand-in**: the issue's own field
name, "from the issue's report, not confirmed against the import page". A real
header that differs changes every file written, which is why the format is
published only with that stated. Nothing has been loaded into a Device42
instance.

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
`spec/tools/portrayal/device42_export.py`.

## Running it, and why nothing is published yet

```sh
python3 spec/tools/portrayal/device42_export.py --out <folder>
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
- **`type` is not written.** A device type holds no kind of device (switch,
  server, patch panel), and the values the import allows are not held.
- **Half units.** `u_height` is a multiple of 0.5. Whether Device42's size takes
  a fraction is not known; the number is written as it is. Six types have a
  fraction: Fibrain XCU10-21IC, XCU10-31IC, XCU10-41ID and XCU10-51ID (0.5),
  BATM/Telco Systems TM-7124S (1.5) and Juniper MX104 (3.5).
- **0U types.** 88 types have `u_height` 0 (not mounted in the rails). They are
  written with size `0`.

### 5. devices: `name`, `hardware`

`name` is the device's label, made unique as the NetBox and Nautobot files make
it (`uniqueNames`), so the three agree. `hardware` is the model name of its
hardware-model row. The issue does not name the devices sheet's columns, so
`hardware` is the least certain header here. A device with no device type is
not a row; it is named in the export's `skipped` list.

### 6. devices to racks: `name`, `rack`, `start_at`

`name` as in sheet 5, `rack` the rack's name, `start_at` the lowest unit the
device fills, as the rack labels it, counted from 1, a half unit as it is
(`10.5`). `auto` is not used: it is reported only as available since release
5.3.5, and a placement is a fact the rack file has. A device with no U
position (a part beside the rack, a manager on the rail face, an item a shelf
or rail holds) is a device row with no placement, and `skipped` names it.

## What the importer is reported not to take

- ports and interfaces, connections (cables), and model images: no import is
  described, so the sheets carry none of them. They are a later step.
- The device type's depth, weight, airflow, part number and description.
- Anything but the first six sheets; Device42's API is not used.

## Left out of this change

`.xls` and `.xlsx` (the sheets are CSV, the format the issue reports the newer
importer takes, which is a stand-in too), ports, images, cables, and loading
into a real instance.

## Open questions

1. The import page's real headers and allowed values: all of section "The
   sheets" is a stand-in until it is read.
2. Does a hardware model's size take a fraction, and does `0` mean "not in a
   rack"?
3. Is a hardware model's name unique across manufacturers? That decides the
   name rule above.
4. Does the importer accept CSV for each of the six sheets, or only `.xls`?
5. Which `type` values exist, and may the export write one?
6. Should the sheet be re-written by the publish step, as the NetBox and
   Nautobot trees are? It would change with every device change.
