"""Nothing of a Dell R760 or R660 stands outside its chassis in 3D, except what Dell's documents say does.

The 3D builder extrudes each part by the heights its drawing carries (`data-z-out`, and a handle's, bar's or
cylinder's length from its `data-z-lift`), measured from the face the part is on: outward and positive, sunk and
negative. So a part on the rear face with a positive height stands past the rear wall, and one on the top face stands
above the lid. This reads every drawing of each server in `library/dist`, all faces and every configuration, and fails
on any part that stands out of its face further than a skin, or further than the document that lets it.

The first build had the riser cages' plates 20.0 mm past the rear wall (the R660's own figure from Dell's service model,
borrowed for the R760) and the lid's latch 2.0 mm above the top, 1.0 above the lid. The supplies' handles stand 35.6 mm
past the wall because Dell's tables say so. A seated card's bracket flange stands past the wall, and so does the part of
the riser that covers it (the cage's `flange-cover` node, and no other node of the cage). The R960's counterpart is
`test_dell_r960.py`.
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"

SKIN = 1.0   # a tab, a lamp or a pressed plate: the library's lids have stood 1.0 proud since the R760

# what may stand past a face, per server: (view, owner path, the most it may stand, why[, node id it is limited to])
_COMMON = (
    ("front", r"^vga(/|$)", 6.73, "the D-sub shell of std/vga@1 on the front panel, inside the bezel's 14 mm"),
    ("rear", r"/video(/|$)", 6.73, "the D-sub shell of std/vga@1 on the rear I/O board"),
    # NOT A DELL DOCUMENT, and the one thing here that is not: a seated card's bracket carries the return flange
    # std/pcie-bracket-lp@1 and -fh@2 draw 9.4 out of their face (PCIe CEM 5.0 figures 11-9 and 11-5; the contracts
    # record the operator's reading that it points out, and the owner has confirmed that a seated card's flange stands
    # past the wall). A bay cannot recess its occupant, so it stands past the wall in a configuration with a card
    # seated. Named so that it shows here and in each device's `card-bracket-flange-past-the-wall` gap.
    ("rear", r"/slot-\d+/module/bracket$", 9.4, "a seated card's bracket flange; see the gap"),
    # ALSO NOT A DELL DOCUMENT: the riser's metal over that flange stands past the wall with it. Dell's ISMs give no
    # depth for the flange or for the cover; the cages' `flange-cover` node is the CEM's 9.40 flange depth plus one
    # 0.86 sheet, an estimate (each cage's contract says so). Only that node, only in a riser cage, and only that far:
    # the rest of a riser stays inside, as the plates (1.0) do.
    ("rear", r"^riser-\d[a-z]?/module/plate$", 10.26, "the riser's metal over a seated card's flange", r"--flange-cover$"),
)
STANDS_PAST = {
    "r760": _COMMON + (
        ("front", r"^bezel/", 14.0, "the security bezel: ISM table 10 (PDF page 34), Za 35.84 mm with it and 22.0 without"),
        ("rear", r"^psu-\d/module/grip$", 35.6, "the supplies' handle: ISM table 10, Zc 736.29 less Zb 700.7 is 35.59"),
        ("rear", r"^psu-\d/module/latch$", 35.6, "the supply's latch stands inside the handle's reach"),
    ),
    "r660": _COMMON + (
        ("front", r"^bezel/", 14.0, "the security bezel: ISM table 12 (PDF page 27), Za 35.84 mm with it and 22 without"),
        ("rear", r"^psu-\d/module/grip$", 35.7,
         "the supplies' handle: ISM table 12, Zc less Zb is 35.57 (787.04 less 751.47), Dell's model has 35.7"),
        ("rear", r"^psu-\d/module/latch$", 35.7, "the supply's latch stands inside the handle's reach"),
    ),
}


def _reach(el, parent):
    """How far this node stands out of its face: its `out`, or a handle's/bar's/cylinder's length from its lift."""
    lift, p = 0.0, el
    while p is not None:
        lift += float(p.get("data-z-lift") or 0)
        p = parent.get(p)
    out = [float(el.get("data-z-out"))] if el.get("data-z-out") is not None else []
    out += [lift + float(el.get(k)) for k in ("data-z-uhandle", "data-z-bar", "data-z-cyl") if el.get(k) is not None]
    return max(out) if out else None


def _owner(el, parent):
    while el is not None and el.get("data-path") is None:
        el = parent.get(el)
    return el.get("data-path") if el is not None else ""


def _stands_past(device):
    """(drawing, view, owner, reach, allowed) for each node whose height is more than SKIN or than its allowance."""
    assert (DIST / f"{device}.configs.json").exists(), \
        f"library/dist has no {device} build: these read it, so run ./build.sh first"
    found = []
    for svg in sorted(DIST.glob(f"{device}.*.svg")):
        view = svg.name.removesuffix(".svg").rsplit(".", 1)[-1]
        root = ET.parse(svg).getroot()
        parent = {c: p for p in root.iter() for c in p}
        for el in root.iter():
            reach = _reach(el, parent)
            if reach is None or reach <= SKIN:
                continue
            p, projection = el, False
            while p is not None:
                projection = projection or p.get("data-projection") is not None
                p = parent.get(p)
            if projection:      # the plan of a seated part is texture only: its body is built from its own face
                continue
            owner = _owner(el, parent)
            node = el.get("id") or ""
            allowed = max((a for v, rx, a, _, *only in STANDS_PAST[device]
                           if v == view and re.search(rx, owner) and (not only or re.search(only[0], node))),
                          default=SKIN)
            if reach > allowed + 1e-6:
                found.append((svg.name, view, owner, reach, allowed))
    return found


@pytest.mark.parametrize("device", sorted(STANDS_PAST))
def test_no_part_stands_outside_the_chassis_in_any_drawing(device):
    over = sorted({(v, o, r, a) for _, v, o, r, a in _stands_past(device)})
    assert not over, f"parts the 3D builder stands outside the {device} chassis:\n" + "\n".join(
        f"  {o} stands {r:g} mm out of the {v}, at most {a:g}" for v, o, r, a in over)
