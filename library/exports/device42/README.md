# Device42 sheets

The hardware-model sheet for Device42's spreadsheet import, written by
`spec/tools/portrayal/device42_export.py` from the NetBox device types under
`library/exports/netbox/device-types/`. The rack side (buildings, rooms, racks,
devices and devices-to-racks) is written from a rack file by the Rack Builder
(`kit/rack/device42.js`) and is numbered `1-` to `6-` in the import sequence;
this sheet is the fourth.

| File | Rows |
|---|---|
| `hardware-models.csv` | one per model, sorted by maker then model |

## The headers are stand-ins

Device42's import page was not read for this sheet. Every header below is the
issue's own field name, from the issue's report of the page, and is
**not confirmed against the import page**. A real header that differs changes
every file.

- `name` (required): the model as its maker prints it, for example `S8901-54XC`.
- `size`: the device type's `u_height`, written as it is. A half unit is `0.5`
  or `2.5`; whether the import takes a fraction is not confirmed.
- `manufacturer`: the maker that built the box.
- `type`: not written. The device-type files hold no kind of device to take it
  from, and the values the import allows are not confirmed.
- `building`, `room`, `hardware` (the model a device is), `rack` and `start_at`
  belong to the rack-side sheets and are stand-ins too. The issue names `name`,
  `type`, `size`, `manufacturer`, `room` and `start_at`; `building`, `hardware`
  and `rack` are the least certain, since the issue names the sheets and not
  their columns.

## One model, once, under its real maker

The NetBox tree files a box again under each NOS vendor that lists it (Arrcus,
IP Infusion, DriveNets, SONiC). Device42's hardware model is the real maker and
model, so a relisting is not a second model. A file whose first `comments` line
reads "<vendor> lists <maker> <model>" is a relisting and is not written; the
maker's own file is. A relisting whose maker has no file of its own is written
once, under that maker, with the model name that line gives.

Two makers can print the same model name. The sheet lists both, each under its
own manufacturer; whether Device42 keeps a hardware model's name unique across
manufacturers is not confirmed.

## What is left out

- ports and interfaces, images and cables: no import is described for them;
- the device type's depth, weight, airflow and part number;
- `.xls` and `.xlsx`: the sheets are CSV, which the issue reports a newer
  generic importer takes.

Nothing here has been loaded into a Device42 instance.
