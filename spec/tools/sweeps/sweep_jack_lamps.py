#!/usr/bin/env python3
"""Draw the lamps that live inside an RJ45, so the ports they belong to can be set.

A traffic or management RJ45 carries integrated link and activity lamps in the
corners of its own opening. Whether to DRAW them was decided two ways in this
library: twenty-two devices place them inside the jack's own box, and the S6301
pair and the MX150 deliberately do not, on the stated ground that
`std/rj45-ganged` draws the opening rather than the housing. The S6301's own
provenance cites the datasheet - 'Link and Activity LEDs per port' - and then
leaves them undrawn.

BOTH ARE DEFENSIBLE AND ONLY ONE IS USEFUL. An undrawn lamp cannot be set, and
being able to set it is what the state machinery is for; a drawing that knows a
lamp is there and will not say where is harder to use than one that is half a
millimetre out. L39 already sanctions the construction, exempting a lamp that
"sit[s] wholly inside the RJ45 - moulded into the jack housing", and L13 exempts
an indicator that declares its part with `for:`. So this draws them everywhere.

NO FIGURE IS READ. Two lamps at the corners of a jack is a fact about the jack,
so every position here comes from a port placement the file already carries. The
inset is the one the S9600-72XC uses on its own management RJ45 - 1.2mm from
each side, 0.27mm from the keyway edge - and the keyway side is what `rotate`
already says: a jack turned through 180 presents it at the top, an unturned one
at the bottom.

WHAT IS LEFT ALONE. A console or aux RJ45 is a serial port in an Ethernet
connector and carries no link lamp on any switch here. Neither does a timing
interface - ToD, BITS, 1PPS and sync jacks are RJ45-shaped and are not links.
Both are skipped, which is 96 of the 331 unlamped RJ45s in the corpus.

STATES ARE off/on. Where a guide tables a port's lamps - the S6301's management
port is green for 1G link and activity, amber for 10M/100M - that vocabulary
belongs on that placement and is not something this can know. The default is
the component's own, and a device that documents better can override it.

    sweep_jack_lamps.py --library library --schemas spec/schemas [device ...]
    sweep_jack_lamps.py --library library --schemas spec/schemas --apply
"""
import argparse
import collections
import glob
import pathlib
import re
import sys

import yaml
from portrayal import lint as L
# A GUARD, for the reason sweep_ids.py gives: this file does its work at module
# scope, and importing it used to run it.
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--library", default="library")
    ap.add_argument("--schemas", default="spec/schemas")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("only", nargs="*")
    ARGS = ap.parse_args()
    LIB = ARGS.library

    if not L.STANDARDS:
        L.STANDARDS.update(yaml.safe_load(
            (pathlib.Path(ARGS.schemas) / "standards.yaml").read_text())['standards'])

    LAMP_REF, LAMP_W = "common/led-dot@1", 2.0
    MARGIN, KEYWAY_INSET = 1.20, 0.27
    # A TIMING JACK IS RJ45-SHAPED AND IS NOT A LINK. ToD, BITS, 1PPS and sync
    # carry no link lamp, and not every device files them under a `timing`
    # group - the S9502-12SM puts its ToD in with the ports - so match the name
    # as well as the group.
    SKIP = re.compile(r"console|aux|serial|ioioi|(^|-)tod($|-)|bits|pps|sync", re.I)
    CLS = {}


    def cls(ref):
        if ref not in CLS:
            cp = L.resolve_component(ref, [LIB]) if ref else None
            CLS[ref] = (L.load_yaml(cp) or {}).get("class") if cp else None
        return CLS[ref]


    NUMBERED = re.compile(r"(port|ge|xe|eth)-\d+")


    def lamp_group(data, target):
        """The group a lamp belongs in, chosen by WHAT IT NAMES.

        The first version of this took the first group it recognised out of
        port-leds, mgmt-leds and status-leds - so on a device with no `port-leds` at
        all, 146 lamps carrying `for: port-N` were filed under `status-leds`, which
        is where SYS, FAN and the PSU lamps live. No rule objects to that, which is
        why a reviewer had to catch it.

        A lamp on a numbered port goes in `port-leds` or nowhere. Returning None
        reports the device rather than putting it somewhere convenient: a group is a
        statement about what a thing IS, and the wrong one is worse than an absent
        one because it reads as deliberate.
        """
        groups = data.get("groups") or {}
        if NUMBERED.fullmatch(str(target) or ""):
            return "port-leds" if "port-leds" in groups else None
        for name in ("mgmt-leds", "port-leds", "status-leds"):
            if name in groups:
                return name
        for name, g in groups.items():
            if (g or {}).get("term") == "LED":
                return name
        return None


    total = collections.Counter()
    for path in sorted(glob.glob(f'{LIB}/devices/*/*/device.yaml')):
        if ARGS.only and not any(o in path for o in ARGS.only):
            continue
        dev = path.split('devices/')[1].replace('/device.yaml', '')
        data = yaml.safe_load(open(path))
        lines = pathlib.Path(path).read_text().split("\n")
        made = []

        for vname, view in (data.get("views") or {}).items():
            if not view:
                continue
            pl = ((view.get("components") or {}).get("placements")) or []
            lamped, rel = set(), 900
            for q in pl:
                if cls(str(q.get("ref") or "")) == "led":
                    f = q.get("for")
                    for t in (f if isinstance(f, list) else [f]):
                        if t:
                            lamped.add(str(t))
            for q in pl:
                ref = str(q.get("ref") or "")
                pid = str(q.get("id"))
                if "rj45" not in ref or cls(ref) != "port" or pid in lamped:
                    continue
                role = str((q.get("attrs") or {}).get("role") or "")
                if SKIP.search(pid) or SKIP.search(role) or q.get("group") == "timing":
                    continue
                sz = L.contract_size(ref, [LIB])
                if not sz or not q.get("at"):
                    continue
                w, h = sz["w"], sz["h"]
                if q.get("rotate") in (90, 270, -90):
                    w, h = h, w
                if w < 2 * MARGIN + 2 * LAMP_W:
                    continue
                x, y = q["at"]
                ly = (y + KEYWAY_INSET if q.get("rotate") == 180
                      else y + h - LAMP_W - KEYWAY_INSET)
                grp = lamp_group(data, pid)
                if grp is None:
                    print(f"  ! {dev}: {pid} wants a `port-leds` group and the device "
                          f"declares none - add it and re-run rather than filing "
                          f"a port lamp under a status group")
                    continue
                for side, lx in (("l", x + MARGIN), ("r", x + w - MARGIN - LAMP_W)):
                    rel += 1
                    g = f", group: {grp}"
                    made.append((vname, f"- {{ref: {LAMP_REF}, id: led-{pid}-{side}, "
                                 f"at: [{round(lx, 2)}, {round(ly, 2)}], for: {pid}"
                                 f"{g}, rel-pos: {rel}}}"))

        if not made:
            continue
        # splice each view's lamps in after that view's last placement line
        by_view = collections.defaultdict(list)
        for vname, line in made:
            by_view[vname].append(line)
        text = "\n".join(lines)
        for vname, block in by_view.items():
            view = (data.get("views") or {}).get(vname) or {}
            pl = ((view.get("components") or {}).get("placements")) or []
            last = str(pl[-1].get("id"))
            rows = text.split("\n")
            # A CUTOUT SHARES ITS OCCUPANT'S ID, by convention, and is written
            # earlier in the file - so matching the id alone anchors the block into
            # the cutout list, where `ref` and `group` are not allowed properties.
            # A placement is the line that carries a `ref:`.
            idx = next((i for i, l in enumerate(rows)
                        if re.search(rf"id: {re.escape(last)}[,}}]", l)
                        and "ref:" in l), None)
            if idx is None:
                print(f"  ! {dev}/{vname}: no anchor for {last}")
                continue
            # A PLACEMENT MAY RUN OVER SEVERAL LINES. Splicing after the first one
            # cuts the mapping in half and the file stops parsing, so follow the
            # continuation until the braces balance.
            end, depth = idx, 0
            for j in range(idx, len(rows)):
                depth += rows[j].count("{") - rows[j].count("}")
                end = j
                if depth <= 0:
                    break
            anchor = "\n".join(rows[idx:end + 1])
            # THE FILE'S OWN INDENT, not this tool's. Placements sit six spaces
            # deep in some devices and eight in others, and a block pasted at the
            # wrong depth is not a mis-formatted file, it is an unparseable one.
            pad = anchor[:len(anchor) - len(anchor.lstrip())]
            text = text.replace(anchor, anchor + "\n" +
                                "\n".join(pad + l for l in block), 1)
        total[dev] = len(made)
        if ARGS.apply:
            pathlib.Path(path).write_text(text)

    print(f"{sum(total.values())} lamps across {len(total)} devices "
          f"({'WRITTEN' if ARGS.apply else 'dry run'})")
    for dev, n in total.most_common(10):
        print(f"  {n:5d}  {dev}")
