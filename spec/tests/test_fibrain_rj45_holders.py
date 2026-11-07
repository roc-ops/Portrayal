"""The Fibrain HD copper slot parts: the six-way RJ45 holders XMU00 and XMS00 and the
twelve RJ45 connection modules that seat in them (#1041).

Where the figures come from:

  * THE HOLDER: the maker's 1:1 front elevation of XMS00 (AutoCAD DXF, units
    millimetres, no dimension entities). Extents 103.50 x 21.00; the moulding
    is 99.50 wide and 21.00 high with a latch tab 2.00 out at each end; six
    module windows 14.80 x 16.60 stand on a 16.02 pitch, the first 4.30 from
    the tab's outer edge and 2.20 from the top. The datasheets (XMU00 rev 0 and
    XMS00 rev 0, 11.09.2019) give the envelope 0.5U x 100 x 66, which is what
    one HD slot takes.
  * THE MODULE: the maker's 1:1 front elevation of XR200. Extents 14.818 x
    18.40 (the issue rounds the width to 14.83; the entities read 14.8183): the
    housing is 14.60 wide, a 0.22 clamp nub stands out of its right side, the
    front frame is 14.60 x 16.10 from 1.30 to 17.40, and the plug opening's
    body tier is 11.90 wide from the frame's x 1.35 and y 6.50. The same
    figures, 14.60 wide, 16.10 high and 38.00 long, are printed on each module
    datasheet's dimension drawing.
  * WHAT EACH PART NUMBER IS: each module datasheet's own title, ordering line
    and parameters. XE is Cat.5, XQ Cat.6, XR Cat.6A. The first digit after
    the letter is 1 for RJ45/u (unscreened) and 2 for RJ45/s (screened); the
    last digit is 0 for 'without adapters' and 1 for a keystone adapter. XR300
    and XR310 are FIELD CONNECTORS, plugs that end a cable (14.0 x 16.4 x 53.7
    and an angled one), and seat in no holder, so they are not here.

The drawings and datasheets are not committed; the numbers are.
"""
import pathlib
import re
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

HOLDERS = ("xmu00", "xms00")
# part -> (category as the datasheet prints it, screened, keystone adapter, cover colour name)
MODULES = {
    "xe100": ("5", False, False, "green"), "xe110": ("5", False, True, "green"),
    "xe200": ("5", True, False, "green"), "xe210": ("5", True, True, "green"),
    "xq100": ("6", False, False, "red"), "xq110": ("6", False, True, "red"),
    "xq200": ("6", True, False, "red"), "xq210": ("6", True, True, "red"),
    "xr100": ("6A", False, False, "aqua"), "xr110": ("6A", False, True, "aqua"),
    "xr200": ("6A", True, False, "aqua"), "xr210": ("6A", True, True, "aqua"),
}
# the dust-cover colour sampled off the maker's photographs of the three categories
COVER = {"green": "#479e35", "red": "#bf291d", "aqua": "#4cae91"}
FIELD_CONNECTORS = ("xr300", "xr310")

# THE HOLDER ELEVATION
FRONT = (103.50, 21.00)
MOULDING_W, TAB = 99.50, 2.00
WINDOW = (14.80, 16.60)
PITCH = 16.02
FIRST_WINDOW_X = 4.30           # from the tab's outer edge, as drawn
WINDOW_Y = 2.20
# THE MODULE ELEVATION
MODULE_EXTENT = (14.8183, 18.40)
MODULE_FACE = (14.60, 18.40)
FRAME = (14.60, 16.10, 1.30)    # w, h, y
JACK_BODY_X, JACK_BODY_Y = 1.35, 6.50

OLD_ACCEPTS = [
    "fibrain/xbcs0@1", "fibrain/xmn1051gb@2", "fibrain/xmn1041gb@2", "fibrain/xmi1051ga@2",
    "fibrain/xmi1041ga@2", "fibrain/xmi1021ca@2", "fibrain/xmi1021da@2", "fibrain/xmi1021ha@2",
    "fibrain/xmi1021ga@2", "fibrain/xmi1031ga@2", "fibrain/xmi1041ca@2", "fibrain/xmi1041da@2",
    "fibrain/xmi1041ha@2", "fibrain/xmn1021cb@2", "fibrain/xmn1021db@2", "fibrain/xmn1021hb@2",
    "fibrain/xmn1021gb@2", "fibrain/xmn1031gb@2", "fibrain/xmn1041cb@2", "fibrain/xmn1041db@2",
    "fibrain/xmn1041hb@2",
]
NEW_HOLDER_REFS = [f"fibrain/{h}@1" for h in HOLDERS]
MODULE_REFS = sorted(f"fibrain/{m}@1" for m in MODULES)


def contract(name):
    return yaml.safe_load((LIB / "components/fibrain" / name / "v1/contract.yaml").read_text())


def skin(name):
    return ET.parse(LIB / "components/fibrain" / name / "v1/skins/default.svg").getroot()


def by_id(root, ident):
    for el in root.iter():
        if el.get("id") == ident:
            return el
    raise AssertionError(f"no element {ident}")


def num(el, key):
    return float(el.get(key))


def centres(c):
    return [b["at"][0] + b["size"][0] / 2 for _, b in sorted(c["bays"].items())]


# ---- the holder against the elevation ----------------------------------------------------

@pytest.mark.parametrize("h", HOLDERS)
def test_a_holder_fills_one_hd_slot_as_the_datasheets_give_it(h):
    c = contract(h)
    assert c["kind"] == "module" and c["behaviour"] == "fills"
    assert (c["size"]["w"], c["size"]["h"], c["size"]["d"]) == (100.0, 21.0, 66.0)
    assert c["size-confidence"] == {"w": "datasheet", "h": "datasheet", "d": "datasheet"}
    root = skin(h)
    assert root.get("viewBox") == "0 0 100.0 21.0"


@pytest.mark.parametrize("h", HOLDERS)
def test_the_holder_front_is_the_drawn_103_50_by_21_00(h):
    root = skin(h)
    m = by_id(root, "moulding")
    assert (num(m, "width"), num(m, "height")) == (MOULDING_W, 21.0)
    # the moulding with a latch tab out of each end is the drawn front, which the
    # 100 slot envelope does not hold: the tabs are inside the posts when seated
    assert round(MOULDING_W + 2 * TAB, 2) == FRONT[0]
    assert FRONT[1] == num(m, "height")


@pytest.mark.parametrize("h", HOLDERS)
def test_six_windows_stand_on_the_drawn_16_02_pitch(h):
    root = skin(h)
    wins = [by_id(root, f"window-{n}") for n in range(1, 7)]
    xs = [num(w, "x") for w in wins]
    # the skin is the 100 envelope with the tabs outside it: x counts from the envelope's edge
    off = TAB - (FRONT[0] - 100.0) / 2 + 0       # = 0.25: the moulding's left edge in the envelope
    first = FIRST_WINDOW_X - TAB + off           # the first window's left edge in the envelope
    assert xs == pytest.approx([round(first + PITCH * k, 3) for k in range(6)], abs=1e-3)
    for w in wins:
        assert (num(w, "width"), num(w, "height"), num(w, "y")) == (WINDOW[0], WINDOW[1], WINDOW_Y)
    assert [round(b - a, 3) for a, b in zip(xs, xs[1:])] == [PITCH] * 5


@pytest.mark.parametrize("h", HOLDERS)
def test_six_module_positions_are_bays_centred_on_the_windows(h):
    c = contract(h)
    assert sorted(c["bays"]) == [f"pos-{n}" for n in range(1, 7)]
    root = skin(h)
    for n in range(1, 7):
        b, w = c["bays"][f"pos-{n}"], by_id(root, f"window-{n}")
        assert b["size"] == [MODULE_FACE[0], MODULE_FACE[1]]
        assert b["at"][0] + b["size"][0] / 2 == pytest.approx(num(w, "x") + num(w, "width") / 2, abs=1e-3)
        # the module's 16.10 frame sits in the 16.60 window with 0.25 each side
        assert b["at"][1] + FRAME[2] == pytest.approx(WINDOW_Y + (WINDOW[1] - FRAME[1]) / 2, abs=1e-3)
    cs = centres(c)
    assert [round(b - a, 3) for a, b in zip(cs, cs[1:])] == [PITCH] * 5
    assert (cs[0] + cs[-1]) / 2 == pytest.approx(50.0, abs=1e-3), "the row is centred on the 100 envelope"


@pytest.mark.parametrize("h", HOLDERS)
def test_every_position_takes_every_module_and_nothing_else(h):
    c = contract(h)
    for pos, b in c["bays"].items():
        assert sorted(b["accepts"]) == MODULE_REFS, pos


def test_screened_and_unscreened_holders_differ_in_the_springs_and_the_part_number():
    u, s = contract("xmu00"), contract("xms00")
    assert (u["attrs"]["model"], s["attrs"]["model"]) == ("XMU00", "XMS00")
    assert (u["attrs"]["screening"], s["attrs"]["screening"]) == ("unscreened", "screened")
    # the geometry, the bays and the envelope are the same
    for k in ("size", "bays", "body"):
        assert u[k] == s[k], k
    assert not [e for e in skin("xmu00").iter() if (e.get("id") or "").startswith("spring")]
    assert len([e for e in skin("xms00").iter() if (e.get("id") or "").startswith("spring")]) == 6


# ---- the modules against the elevation and their datasheets ------------------------------

@pytest.mark.parametrize("m", sorted(MODULES))
def test_a_module_face_is_the_drawn_14_6_by_18_4(m):
    c = contract(m)
    assert c["kind"] == "module" and c["behaviour"] == "fills"
    assert (c["size"]["w"], c["size"]["h"], c["size"]["d"]) == (MODULE_FACE[0], MODULE_FACE[1], 38.0)
    # only XR200 has an elevation; each other sheet prints 14.60 and 38.00 itself, and the 18.40 is
    # borrowed from XR200's housing
    assert c["size-confidence"] == ({"w": "drawing", "h": "drawing", "d": "datasheet"} if m == "xr200"
                                    else {"w": "datasheet", "h": "borrowed", "d": "datasheet"})
    # the drawn extents add the 0.22 clamp nub on the right side to the housing
    assert round(MODULE_EXTENT[0] - MODULE_FACE[0], 3) == 0.218
    root = skin(m)
    assert root.get("viewBox") == "0 0 14.6 18.4"
    f = by_id(root, "frame")
    assert (num(f, "width"), num(f, "height"), num(f, "y")) == FRAME


@pytest.mark.parametrize("m", sorted(MODULES))
def test_a_module_says_what_its_datasheet_says(m):
    cat, screened, keystone, cover = MODULES[m]
    c = contract(m)
    a = c["attrs"]
    assert a["model"] == m.upper()
    assert a["media"] == "rj45"
    assert (a["category"], a["screening"], a["keystone"]) == (
        cat, "screened" if screened else "unscreened", "adapter" if keystone else "none")
    assert a["cover"] == cover
    d = c["description"]
    assert f"kat.{cat}" in d or f"Cat.{cat}" in d
    assert ("screened" in d) and (("unscreened" in d) == (not screened))
    assert ("keystone" in d) == keystone
    # the cover colour is the photograph's, on the frame and on the jack's shell
    assert by_id(skin(m), "frame").get("fill") == COVER[cover]
    assert c["parts"][0]["attrs"]["finish"] == COVER[cover]


def test_the_field_connectors_are_not_modules():
    # XR300 and XR310 are plugs that end a cable, not modules that seat in a holder
    for f in FIELD_CONNECTORS:
        assert not (LIB / "components/fibrain" / f).exists(), f
    for m in MODULES:
        assert not m.endswith(("300", "310"))


@pytest.mark.parametrize("m", sorted(MODULES))
def test_a_module_carries_one_rj45_jack_of_the_family_on_the_drawn_opening(m):
    c = contract(m)
    # the lamp-less Ethernet member of the family, not the bare cell: the bare cell is a console jack
    assert [(p["id"], p["ref"]) for p in c["parts"]] == [("jack", "common/rj45-ganged-eth-plain@1")]
    assert "lamp-less" in c["provenance"]["jack"]
    x, y = c["parts"][0]["at"]
    # std/rj45-ganged@2 draws its body tier 0.395 in from its edge and 0.5 down: that lands on the
    # drawn opening, 1.35 across and 6.50 down
    assert x + 0.395 == pytest.approx(JACK_BODY_X, abs=0.01)
    assert y + 0.5 == pytest.approx(JACK_BODY_Y, abs=1e-3)
    # the jack is centred on the module, and inside its frame
    assert x + 12.7 / 2 == pytest.approx(MODULE_FACE[0] / 2, abs=0.01)
    assert y + 11.0 <= FRAME[2] + FRAME[1]


def test_no_two_modules_state_the_same_datasheet_figure_by_borrowing():
    # each module cites its own sheet: the part number is in its provenance
    for m in MODULES:
        text = yaml.safe_dump(contract(m)["provenance"])
        assert m.upper() in text, m


def test_the_keystone_variants_draw_no_geometry_the_datasheet_does_not_give():
    # the four sheets of one category print one drawing; the keystone adapter is a clear collar
    # and tab behind the face on the photographs and is not dimensioned, so it is not drawn
    for cat in ("xe", "xq", "xr"):
        for screen in ("1", "2"):
            plain, key = contract(f"{cat}{screen}00"), contract(f"{cat}{screen}10")
            assert plain["size"] == key["size"] and plain["parts"] == key["parts"]
            geometry = lambda c: [{k: v for k, v in b.items() if k != "source"} for b in c["body"]["boxes"]]
            assert geometry(plain) == geometry(key)


# ---- where they seat ---------------------------------------------------------------------

def _bays_accepting(ref):
    found = set()
    for p in sorted(LIB.rglob("*.yaml")):
        if p.name not in ("device.yaml", "contract.yaml"):
            continue
        if ref in p.read_text():
            found.add(str(p.relative_to(LIB)))
    return found


@pytest.mark.parametrize("ref", NEW_HOLDER_REFS)
def test_only_the_1u_frame_takes_the_rj45_holders(ref):
    # a holder's own contract names itself, and XMU00's names XMS00 as the elevation it borrows; every
    # other mention is a bay
    own = {f"components/fibrain/{h}/v1/contract.yaml" for h in HOLDERS}
    assert _bays_accepting(ref) - own == {"devices/fibrain/xpu/device.yaml"}


def test_every_slot_of_the_frame_takes_the_holders_and_keeps_what_it_took():
    d = yaml.safe_load((LIB / "devices/fibrain/xpu/device.yaml").read_text())
    bays = d["views"]["front"]["components"]["bays"]
    assert len(bays) == 8
    for b in bays:
        assert b["accepts"] == OLD_ACCEPTS + NEW_HOLDER_REFS, b["id"]


def test_the_xcu_drawer_is_unchanged_the_maker_lists_no_copper_for_it():
    # DSH XCU rev 1.1 lists 'LCdx, SC, E2000' as the range of connectors; XPU00 lists RJ45/u
    d = yaml.safe_load((LIB / "components/fibrain/xcu-drawer/v1/contract.yaml").read_text())
    for n in range(1, 5):
        assert d["bays"][f"slot-{n}"]["accepts"] == OLD_ACCEPTS, n


def test_the_fibre_holders_gain_no_bays():
    # the LC and SC holders are fibre parts: they carry parts, not module bays
    for p in sorted((LIB / "components/fibrain").glob("xm[in]*/v2/contract.yaml")):
        assert "bays" not in yaml.safe_load(p.read_text()), p


def _cfg(name):
    d = yaml.safe_load((LIB / "devices/fibrain/xpu/device.yaml").read_text())
    return d["configurations"][name]


def _name(ref):
    return ref.split("/")[1].split("@")[0]


# DSH XPU00 rev 2: "48 ports per 1U for copper" = 8 slots x 6 ways
COPPER_EXAMPLES = {
    # name -> holders its eight slots may seat
    "copper-mixed": {"fibrain/xms00@1", "fibrain/xmu00@1"},
    "xpu00-copper": {"fibrain/xmu00@1"},
    "xps00-copper": {"fibrain/xms00@1"},
}
SCREENED_OF = {"fibrain/xms00@1": "screened", "fibrain/xmu00@1": "unscreened"}


@pytest.mark.parametrize("name", COPPER_EXAMPLES)
def test_a_copper_example_fills_all_eight_slots_with_six_modules_each(name):
    cfg = _cfg(name)
    assert cfg["kind"] == "example"
    assert "part-numbers" not in cfg
    bays = cfg["bays"]
    assert {k for k in bays if "/" not in k} == {f"slot-{n}" for n in range(1, 9)}
    assert {k for k in bays if "/" in k} == {f"slot-{n}/pos-{p}" for n in range(1, 9) for p in range(1, 7)}
    assert len(bays) == 8 + 48
    assert set(bays[f"slot-{n}"] for n in range(1, 9)) <= COPPER_EXAMPLES[name]
    for n in range(1, 9):
        holder = bays[f"slot-{n}"]
        # a screened holder takes screened modules and an unscreened one unscreened, as the datasheets pair them
        for p in range(1, 7):
            m = bays[f"slot-{n}/pos-{p}"]
            assert m in MODULE_REFS, m
            assert contract(_name(m))["attrs"]["screening"] == SCREENED_OF[holder], (n, p)


def test_copper_mixed_alternates_the_holders_and_mixes_categories_and_keystone():
    bays = _cfg("copper-mixed")["bays"]
    assert [bays[f"slot-{n}"] for n in range(1, 9)] == ["fibrain/xms00@1", "fibrain/xmu00@1"] * 4
    for n in range(1, 9):
        mods = [_name(bays[f"slot-{n}/pos-{p}"]) for p in range(1, 7)]
        assert {MODULES[m][0] for m in mods} == {"5", "6", "6A"}, n
        assert any(MODULES[m][2] for m in mods), f"slot-{n} has a keystone module"


@pytest.mark.parametrize("name,holder", [("xpu00-copper", "fibrain/xmu00@1"), ("xps00-copper", "fibrain/xms00@1")])
def test_the_part_number_copper_examples_say_illustrative_and_ordered_separately(name, holder):
    cfg = _cfg(name)
    assert all(cfg["bays"][f"slot-{n}"] == holder for n in range(1, 9))
    text = " ".join(cfg["description"].split()).lower()
    assert "illustrative" in text and "ordered separately" in text
    if name == "xps00-copper":
        assert cfg["component-attrs"]["grounding-bar"] == _cfg("xps00")["component-attrs"]["grounding-bar"]


def test_the_orderable_frames_and_base_still_ship_empty():
    # DSH XPU00 rev 2 is titled 'empty' and the XPS00 sheet says the same: no holder in either SKU
    for name in ("base", "xpu00", "xps00"):
        assert "bays" not in _cfg(name), name
    assert _cfg("xpu00")["kind"] == "orderable" and _cfg("xps00")["kind"] == "orderable"
    assert _cfg("base")["kind"] == "base"
