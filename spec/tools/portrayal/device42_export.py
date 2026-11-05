#!/usr/bin/env python3
"""Device42's hardware-model sheet, from the committed NetBox device types.

Device42's spreadsheet import loads buildings, rooms, racks, hardware models,
devices and devices-to-racks, in that sequence. A hardware model needs a name;
its type, size and manufacturer are optional. This tool writes the
hardware-model sheet, one row for each model a maker sells:

    python3 spec/tools/portrayal/device42_export.py            # library/exports/device42
    python3 spec/tools/portrayal/device42_export.py --out DIR

THE SOURCE IS THE FILES, not the exporter. It reads
`library/exports/netbox/device-types/<Maker>/<Model>.yaml` as text (the first
top-level keys and the first line of `comments`), so it needs no build and no
`library/dist`, and it touches nothing in `dcim_export.py`.

A MODEL IS LISTED ONCE, UNDER THE MAKER THAT BUILT IT. The NetBox tree files the
same box again under each NOS vendor that lists it (Arrcus, IP Infusion,
DriveNets, SONiC), and Device42's hardware model is the asset's real maker and
model. The exporter writes a relisting's first `comments` line as
"<NOS vendor> lists <maker> <model> (NOS: <nos>).", and a maker's own type has
no such line: that line is the mark, and a file carrying it is a relisting, not
a model. If the box it names has no file of its own under that maker, the
relisting is written once as that maker's model, with the model name the line
gives and the size of the file that carried it.

THE COLUMN HEADERS ARE STAND-INS: the issue's own field names, not read from the
import page. Nothing here is confirmed against it.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "library/exports/netbox/device-types"
OUT = ROOT / "library/exports/device42"

# STAND-INS, from the issue's report of the import page: `name` is required,
# `size` (in U) and `manufacturer` are optional. `type` is optional too and is
# not written: the device-type files hold no kind of device to take it from.
COLUMNS = ("name", "size", "manufacturer")
STAND_INS = ("name", "type", "size", "manufacturer", "building", "room", "hardware", "rack", "start_at")

LISTS = re.compile(r"^(?P<nos>.+?) lists (?P<hw>.+?)(?: \(NOS: [^)]*\))?\.?$")
KEYS = ("manufacturer", "model", "u_height")


def _scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1].replace("''", "'") if value[0] == "'" else value[1:-1]
    return value


def read_type(path):
    """manufacturer, model, u_height and the first `comments` line of one file."""
    doc, lines = {}, path.read_text(encoding="utf-8").splitlines()
    for n, line in enumerate(lines):
        m = re.match(r"^(manufacturer|model|u_height):\s*(.*?)\s*$", line)
        if m and m.group(1) not in doc:
            doc[m.group(1)] = _scalar(m.group(2))
        elif line.startswith("comments:"):
            rest = line[len("comments:"):].strip()
            if rest[:1] in "|>" and rest[:1]:
                rest = lines[n + 1].strip() if n + 1 < len(lines) else ""
            elif rest[:1] == '"':
                rest = re.split(r'\\n|"$', rest[1:])[0]
            doc["comments"] = rest
            break
    missing = [k for k in KEYS if k not in doc]
    if missing:
        raise SystemExit(f"{path}: no {', '.join(missing)}")
    return doc


def size_text(u_height):
    """The device type's u_height as a number: 1.0 is `1`, 0.5 is `0.5`."""
    n = float(u_height)
    return str(int(n)) if n == int(n) else repr(n)


def hardware_models(source=SOURCE):
    """(rows, report): one row per maker and model, sorted, and what was skipped."""
    source = Path(source)
    docs = [read_type(p) for p in sorted(source.glob("*/*.yaml"))]
    own = [d for d in docs if not LISTS.match(d.get("comments", ""))]
    listed = [d for d in docs if LISTS.match(d.get("comments", ""))]
    makers = sorted({d["manufacturer"] for d in own}, key=len, reverse=True)
    rows = {(d["manufacturer"], d["model"]): d["u_height"] for d in own}
    report = {"relistings": len(listed), "relisted_without_own": 0, "unresolved": 0}
    for d in listed:
        hw = LISTS.match(d["comments"]).group("hw")
        maker = next((m for m in makers if hw.startswith(m + " ")), None)
        if maker is None:
            # a maker with no type of its own: the NOS vendor is all the file says
            report["unresolved"] += 1
            rows.setdefault((d["manufacturer"], d["model"]), d["u_height"])
            continue
        key = (maker, hw[len(maker) + 1:])
        if key not in rows:
            rows[key] = d["u_height"]
            report["relisted_without_own"] += 1
    out = [{"name": model, "size": size_text(u), "manufacturer": maker}
           for (maker, model), u in rows.items()]
    out.sort(key=lambda r: (r["manufacturer"].casefold(), r["name"].casefold(), r["manufacturer"], r["name"]))
    names = {}
    for r in out:
        names.setdefault(r["name"], set()).add(r["manufacturer"])
    report["shared_names"] = sum(1 for makers_ in names.values() if len(makers_) > 1)
    report["half_units"] = sum(1 for r in out if float(r["size"]) % 1)
    report["rows"] = len(out)
    return out, report


README = """# Device42 sheets

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
"""


def write(out=OUT, source=SOURCE):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows, report = hardware_models(source)
    with open(out / "hardware-models.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(COLUMNS)
        w.writerows([[r[c] for c in COLUMNS] for r in rows])
    (out / "README.md").write_text(README, encoding="utf-8")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", default=str(SOURCE), help="the NetBox device-types folder")
    ap.add_argument("--out", default=str(OUT), help="the folder the sheets are written to")
    args = ap.parse_args(argv)
    report = write(args.out, args.source)
    print(", ".join(f"{k} {v}" for k, v in report.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
