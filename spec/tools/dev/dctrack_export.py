#!/usr/bin/env python3
"""Sunbird dcTrack's model list, from the committed NetBox device types.

dcTrack holds a model by its make and model name, and an item names one: the
import template says "Values provided for make, and model must match an entry
from the dcTrack Make and Model lists". This tool writes one row for each model
a maker sells, so the Models Library can be checked or filled before the items
are imported:

    python3 spec/tools/dev/dctrack_export.py --out DIR

The list is not published: nothing is written unless `--out` says where, and no
file it writes is committed.

THE SOURCE IS THE FILES, not the exporter. It reads
`library/exports/netbox/device-types/<Maker>/<Model>.yaml`, so it needs no build
and no `library/dist`, and it touches nothing in `dcim_export.py`.

A MODEL IS LISTED ONCE, UNDER THE MAKER THAT BUILT IT, by the rule
`device42_export.py` states: a file whose first `comments` line reads
"<NOS vendor> lists <maker> <model>" is a relisting, not a model. A relisting
whose maker has no file of its own is written once under that maker, with the
height and weight of the file that carried it.

THE HEADERS: `Make`, `Model Name` and `Height (RUs)` are the names the Models
Library prints for its grid (Sunbird, dcTrack 6.0.3 User Guide, PDF page 439).
`Weight (kg)` is a stand-in: the guide says "Enter the model's weight" (PDF page
445) and names no unit. No page prints a file shape for a model import, so this
is a list in the library's own field names, not an import template.
"""
import argparse
import csv
import sys
from pathlib import Path

import yaml

from portrayal_dev.device42_export import LISTS, read_type as read_head

_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "library/exports/netbox/device-types"

KEYS = ("make", "model", "u_height", "weight_kg")
PRINTED = ("Make", "Model Name", "Height (RUs)")
STAND_INS = ("Weight (kg)",)
HEADERS = PRINTED + STAND_INS
KG = {"kg": 1.0, "g": 0.001, "lb": 0.45359237, "oz": 0.028349523125}


def number_text(n):
    """A number as the files write it: 1.0 is `1`, 0.5 is `0.5`, 39.69 is `39.69`."""
    n = float(n)
    return str(int(n)) if n == int(n) else repr(n)


def weight_kg(doc, path):
    weight = doc.get("weight")
    if weight is None:
        return ""
    unit = doc.get("weight_unit", "kg")
    if unit not in KG:
        raise SystemExit(f"{path}: weight unit {unit!r} is not one this tool converts")
    return number_text(round(float(weight) * KG[unit], 4))


def read_type(path):
    doc = yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER) or {}
    missing = [k for k in ("manufacturer", "model", "u_height") if k not in doc]
    if missing:
        raise SystemExit(f"{path}: no {', '.join(missing)}")
    # the first `comments` line is read as `device42_export` reads it: a plain
    # scalar that wraps is one line to YAML and two to the file
    first = read_head(path).get("comments", "")
    return {"make": str(doc["manufacturer"]), "model": str(doc["model"]),
            "u_height": number_text(doc["u_height"]), "weight_kg": weight_kg(doc, path),
            "listing": LISTS.match(first)}


def models(source=SOURCE):
    """(rows, report): one row per maker and model, sorted, and what was skipped."""
    source = Path(source)
    docs = [read_type(p) for p in sorted(source.glob("*/*.yaml"))]
    own = [d for d in docs if not d["listing"]]
    listed = [d for d in docs if d["listing"]]
    makers = sorted({d["make"] for d in own}, key=len, reverse=True)
    rows = {(d["make"], d["model"]): d for d in own}
    report = {"relistings": len(listed), "relisted_without_own": 0, "unresolved": 0}
    for d in listed:
        hw = d["listing"].group("hw")
        maker = next((m for m in makers if hw.startswith(m + " ")), None)
        if maker is None:
            # a maker with no type of its own: the NOS vendor is all the file says
            report["unresolved"] += 1
            rows.setdefault((d["make"], d["model"]), d)
            continue
        key = (maker, hw[len(maker) + 1:])
        if key not in rows:
            rows[key] = {**d, "make": key[0], "model": key[1]}
            report["relisted_without_own"] += 1
    out = [{k: d[k] for k in KEYS} for d in rows.values()]
    out.sort(key=lambda r: (r["make"].casefold(), r["model"].casefold(), r["make"], r["model"]))
    report["half_units"] = sum(1 for r in out if float(r["u_height"]) % 1)
    report["zero_u"] = sum(1 for r in out if r["u_height"] == "0")
    report["no_weight"] = sum(1 for r in out if not r["weight_kg"])
    report["rows"] = len(out)
    return out, report


README = """# dcTrack model list

The models for Sunbird dcTrack, written by `spec/tools/dev/dctrack_export.py`
from the NetBox device types under `library/exports/netbox/device-types/`. The
rack side (locations, cabinets and devices) is written from a rack file by the
Rack Builder (`kit/rack/dctrack.js`).

| File | Rows |
|---|---|
| `models.csv` | one per model, sorted by make then model |

This is a list for checking or filling the Models Library: dcTrack's import
template says the make and model of an item must match an entry of the Models
Library. No page of Sunbird's guides prints a file shape for importing models,
so this is not an import template.

## The headers

Source: Sunbird, dcTrack 6.0.3 User Guide, PDF pages 439 and 445.

- `Make`: the maker that built the box. Printed in the Models Library grid.
- `Model Name`: the model as its maker prints it. Printed in the grid.
- `Height (RUs)`: the device type's `u_height`, as written. A half unit is `0.5`
  or `2.5`, and a box that is not in the rails is `0`. Printed in the grid.
  Whether dcTrack takes a fraction is not stated.
- `Weight (kg)`: a **stand-in**. The guide says "Enter the model's weight" and
  names no unit, and the item form prints "Weight (lbs)" for a location in US
  units (PDF page 584). The files hold kilograms, so the unit is in the header.
  Blank when the file states none.

## One model, once, under its real maker

The NetBox tree files a box again under each NOS vendor that lists it (Arrcus,
IP Infusion, DriveNets, SONiC). A model is the real maker and model, so a
relisting is not a second model. A relisting whose maker has no file of its own
is written once, under that maker.

## What is left out

- the part number: no field of the Models Library names one;
- Class, Mounting and Form Factor, which the Models Library requires for a
  model: the device type does not state them, and the values are not printed;
- ports and power ports, and port types: the vocabulary dcTrack allows is not
  held, so no port is written;
- images, and connections (cables);
- the device type's depth, airflow, description and comments;
- the rack PDU sheet, and the rack-side fields (a cabinet's geometry and
  numbering, an item's Rails Used and Status), which the rack-side sheets of
  the Rack Builder name;
- the REST calls, and any load into dcTrack.

Nothing here has been loaded into a dcTrack instance.
"""


def write(out, source=SOURCE):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows, report = models(source)
    with open(out / "models.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\r\n")
        w.writerow(HEADERS)
        w.writerows([[r[k] for k in KEYS] for r in rows])
    (out / "README.md").write_text(README, encoding="utf-8")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--source", default=str(SOURCE), help="the NetBox device-types folder")
    ap.add_argument("--out", required=True, help="the folder the list is written to")
    args = ap.parse_args(argv)
    report = write(args.out, args.source)
    print(", ".join(f"{k} {v}" for k, v in report.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
