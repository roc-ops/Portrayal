"""When a skin exists to repaint a node, relief must not overrule it.

A skin variant is usually a COLOUR that means something: std/db9@1's insert is
teal on a PowerEdge because Dell paints that connector so the two D-subs on a
crowded panel can be told apart, and std/usb-a@1's tongue is white for USB 2.0
and blue for 3.0 because USB-IF says the colour names the port.

`relief.features` can also fix a node's colour, and when it does the 3D body
ignores the skin. One part then draws two different claims - the right one flat
and the wrong one in the round - and nothing compares them, because the drawing
and the kit read different keys. std/db9@1 carries a comment saying exactly this;
std/usb-a@1 shipped the defect until a MaiaEdge PBC needed the white tongue.

So the rule is a sweep, not a comment: no relief feature may fix a colour on a
node the skins disagree about. It is checked STRUCTURALLY - resolve each skin,
read that node's own fill - because a sweep that searched the prose for the word
`color` would pass the one contract whose only use of it is inside its own
denial.
"""
import pathlib
import re

import pytest
import yaml

LIB = pathlib.Path(__file__).resolve().parents[2] / "library"
COMPONENTS = LIB / "components"


def _fills(svg_text):
    """Every id'd element's own fill, as the skin paints it."""
    out = {}
    for m in re.finditer(r"<[a-zA-Z]+\b([^>]*)>", svg_text):
        attrs = m.group(1)
        i = re.search(r'\bid="([^"]+)"', attrs)
        f = re.search(r'\bfill="([^"]+)"', attrs)
        if i and f:
            out[i.group(1)] = f.group(1)
    return out


def _multi_skin():
    for c in sorted(COMPONENTS.glob("*/*/*/contract.yaml")):
        d = yaml.safe_load(c.read_text()) or {}
        if len(d.get("skins") or []) > 1:
            yield c, d


def _conflicts(contract_path, contract):
    """(node, fixed colour, what the skins actually paint) for each clash."""
    art = {}
    for s in contract["skins"]:
        p = contract_path.parent / "skins" / f"{s}.svg"
        if p.exists():
            art[s] = _fills(p.read_text())
    found = []
    for feat in (contract.get("relief") or {}).get("features") or []:
        node, fixed = feat.get("node"), feat.get("color")
        if not node or not fixed:
            continue
        painted = {a.get(node) for a in art.values()} - {None}
        if len(painted) > 1:
            found.append((node, fixed, sorted(painted)))
    return found


def test_a_skin_that_repaints_a_node_is_not_overruled_by_relief():
    bad = []
    for path, contract in _multi_skin():
        for node, fixed, painted in _conflicts(path, contract):
            bad.append(
                f"{path.relative_to(LIB)}: relief fixes node {node!r} at {fixed}, "
                f"but its skins paint {painted}. Drop the feature's `color` and the "
                f"kit samples the node's own art, so the body follows the skin")
    assert not bad, "\n".join(bad)


def test_the_sweep_has_something_to_sweep():
    """A sweep over an empty set passes and proves nothing.

    A rule proposed here once returned a clean bill because the collection it
    walked was empty and nobody checked. This is the guard.
    """
    assert sum(1 for _ in _multi_skin()) >= 20


def test_the_sweep_would_catch_the_defect_it_exists_for():
    """THE NON-VACUITY CHECK, and it is not optional.

    Put std/usb-a@1's old hard-coded tongue colour back - in memory, not on disk
    - and the sweep must report it. A check that cannot fail is a check that
    measures the checker's expectations.
    """
    path = COMPONENTS / "std/usb-a/v1/contract.yaml"
    contract = yaml.safe_load(path.read_text())
    tongue = next(f for f in contract["relief"]["features"] if f["node"] == "tongue")
    assert "color" not in tongue, "the defect is back on disk; this test is now a tautology"
    tongue["color"] = "#2b6cb0"
    found = _conflicts(path, contract)
    assert found == [("tongue", "#2b6cb0", ["#2b6cb0", "#d5d9de"])], found


# --- the two USB-A skins ------------------------------------------------------

USB_A = COMPONENTS / "std/usb-a/v1"


@pytest.fixture(scope="module")
def usb_a():
    return yaml.safe_load((USB_A / "contract.yaml").read_text())


def test_usb_a_ships_a_skin_for_each_colour_the_standard_defines(usb_a):
    assert usb_a["skins"] == ["default", "usb2"]
    for s in usb_a["skins"]:
        assert (USB_A / "skins" / f"{s}.svg").exists(), s


def test_the_two_usb_skins_differ_in_the_tongue_AND_NOTHING_ELSE():
    """Only the fill may differ - the geometry is one part's, told twice.

    If a skin variant could drift in size, the aperture a device punches would
    depend on which colour it asked for, and `size` would be telling the truth
    for one of them.
    """
    def geometry(name):
        t = (USB_A / "skins" / f"{name}.svg").read_text()
        return re.sub(r'\s*fill="[^"]*"', "", re.sub(r"<!--.*?-->", "", t, flags=re.S))
    assert geometry("default").split() == geometry("usb2").split()

    a, b = _fills((USB_A / "skins" / "default.svg").read_text()), \
        _fills((USB_A / "skins" / "usb2.svg").read_text())
    assert a.keys() == b.keys()
    assert [k for k in a if a[k] != b[k]] == ["tongue"]


def test_the_usb2_tongue_is_not_the_usb3_blue():
    """The whole point: a datasheet that says 2.0 must not be drawn saying 3.0."""
    blue = _fills((USB_A / "skins" / "default.svg").read_text())["tongue"]
    white = _fills((USB_A / "skins" / "usb2.svg").read_text())["tongue"]
    assert blue.lower() == "#2b6cb0", "the USB 3.0 blue moved; check both skins"
    assert white.lower() != blue.lower()

    # WHITE IS A NEUTRAL, NOT A HUE. Checked as light-and-unsaturated rather
    # than by channel order: a white with a faint cool cast is still white, and
    # every colour the standard reserves - the 300C blue, the Gen-2 teal, the
    # yellow of a charging port - is far outside this.
    def spread(hexcol):
        ch = [int(hexcol[i:i + 2], 16) for i in (1, 3, 5)]
        return min(ch), max(ch) - min(ch)
    lo, sat = spread(white)
    assert lo >= 160 and sat <= 24, f"{white} does not read as a white insulator"
    assert spread(blue)[1] > 24, "the check cannot tell the two apart"


def test_the_maiaedge_pbc_asks_for_the_usb2_skin():
    """The device whose datasheet says USB 2.0 is the reason this skin exists."""
    d = yaml.safe_load((LIB / "devices/maiaedge/pbc/device.yaml").read_text())
    usb = next(p for p in d["views"]["front"]["components"]["placements"]
               if p["id"] == "usb")
    assert usb["ref"] == "std/usb-a@1"
    assert usb.get("skin") == "usb2", usb
