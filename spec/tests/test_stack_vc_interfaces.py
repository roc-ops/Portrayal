"""The stack and Virtual Chassis ports present their interfaces, and the cable
ends that mate them are in the library.

Four vendor connectors were registered in spec/schemas/connectors.yaml with no
part presenting them: `stackwise-480` and `stackpower` (the Catalyst 9300 rear),
`ex4200-vcp` (the EX4200 rear) and `flexstack` (the Catalyst 2960-S FlexStack
module). Each part that draws one now presents it with a `mate` point, and a
cable end of the same vendor mates it, so no port on those devices is a dead end.

These run against the real library, a components.json built here by the indexer
the build runs and device copies rendered here, never a possibly stale dist.
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

import onebuild
import warmrender
from test_coax_slots import _contract

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"

SW, PWR, VCP, FLEX = ("cisco/stackwise-480-port@1", "cisco/stackpower-port@1",
                      "juniper/ex4200-vcp-port@1", "cisco/flexstack-port@1")
SW_PLUG, PWR_PLUG, VCP_PLUG, FLEX_PLUG = ("cisco/stackwise-480-plug@1", "cisco/stackpower-plug@1",
                                          "juniper/ex4200-vcp-plug@1", "cisco/flexstack-plug@1")
SHARED_SENTENCE = ("seated by configurations downstream of this library; "
                   "see docs/pluggables-design.md decision 2")

# port -> (the key it presents, the cable end that mates it, its size as drawn,
# where its `mate` point is, its elements as drawn before this change)
PORTS = {
    SW: ("stackwise-480", SW_PLUG, {"w": 14.9, "h": 23.8, "d": 20.0}, [7.45, 11.9],
         {"opening-1": {"at": [0.0, 0.0], "size": [14.9, 5.2], "class": "mechanical"},
          "opening-2": {"at": [0.0, 9.3], "size": [14.9, 5.2], "class": "mechanical"},
          "opening-3": {"at": [0.0, 18.6], "size": [14.9, 5.2], "class": "mechanical"}}),
    PWR: ("stackpower", PWR_PLUG, {"w": 23.6, "h": 18.5, "d": 25.0}, [11.8, 9.25],
          {"opening": {"at": [0.0, 0.0], "size": [23.6, 18.5], "class": "mechanical"}}),
    VCP: ("ex4200-vcp", VCP_PLUG, {"w": 36.2, "h": 8.3}, [18.1, 4.15],
          {"opening": {"at": [1.6, 1.4], "size": [33.0, 5.5], "class": "window"}}),
}
PLUGS = {SW_PLUG: "stackwise-480", PWR_PLUG: "stackpower", VCP_PLUG: "ex4200-vcp",
         FLEX_PLUG: "flexstack"}

# The placements this change must not move, measured off origin/main at 212b50baa:
# every Catalyst 9300 and every EX4200 states the same ones.
C9300 = ["cisco/c9300-24p", "cisco/c9300-24u", "cisco/c9300-48p", "cisco/c9300-48t",
         "cisco/c9300-48u"]
EX4200 = [f"juniper/ex4200-{m}" for m in ("24f", "24p", "24px", "24t", "48p", "48px", "48t")]
DEVICES = C9300 + EX4200
PLACED = {
    "c9300": [("stack-1", SW, [94.35, 10.2], "stackwise", 1),
              ("stack-2", SW, [158.05, 10.2], "stackwise", 2),
              ("spwr-1", PWR, [233.0, 3.9], "stackpower", 1),
              ("spwr-2", PWR, [233.0, 24.0], "stackpower", 2)],
    "ex4200": [("vcp-0", VCP, [18.9, 29.6], "vcp", 0),
               ("vcp-1", VCP, [67.9, 29.6], "vcp", 1)],
}


def family(dev):
    return "c9300" if "c9300" in dev else "ex4200"


def key_of(ref):
    return PORTS[ref][0]


@pytest.fixture(scope="module")
def comps():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


# --- 1. the three ports --------------------------------------------------------

@pytest.mark.parametrize("ref", sorted(PORTS))
def test_a_stack_or_vcp_port_presents_its_key_at_a_mate_point(ref):
    key, _plug, _size, mate, _els = PORTS[ref]
    c = _contract(ref)
    assert c["interface"] == key
    assert c["connection-points"]["mate"]["at"] == pytest.approx(mate)
    assert c["connection-points"]["mate"]["direction"] == "front"


@pytest.mark.parametrize("ref", sorted(PORTS))
def test_a_stack_or_vcp_port_kept_its_size_and_elements(ref):
    _key, _plug, size, _mate, els = PORTS[ref]
    c = _contract(ref)
    assert c["class"] == "port"
    assert {k: c["size"][k] for k in size} == size
    assert c["elements"] == els
    assert c["skins"] == ["default"]


@pytest.mark.parametrize("ref", sorted(PORTS))
def test_a_stack_or_vcp_port_records_where_its_interface_comes_from(ref):
    c = _contract(ref)
    text = c["provenance"]["interface"]
    key = _contract(ref)["interface"]
    assert f"`{key}` key of spec/schemas/connectors.yaml" in text, text
    assert "Guide" in text, text


def test_the_ports_took_a_minor_each():
    assert _contract(SW)["version"] == "1.2.0"
    assert _contract(PWR)["version"] == "1.1.0"
    assert _contract(VCP)["version"] == "1.1.0"


# --- 2. the four cable ends ----------------------------------------------------

@pytest.mark.parametrize("ref", sorted(PLUGS))
def test_a_cable_end_mates_its_key_in_the_house_form(ref):
    c = _contract(ref)
    key = PLUGS[ref]
    assert c["class"] == "port" and c["mates"] == key
    assert c["attrs"] == {"media": key, "connector": key}
    assert c["unplaced"] == SHARED_SENTENCE
    assert {"cable-od", "jacket-color"} <= set(c["fields"])
    assert {"mate", "cable"} <= set(c["connection-points"])
    assert c["connection-points"]["cable"]["on"] == "stub"
    assert "conforms" not in c, "no standard is held for a vendor connector"


def test_the_shared_plug_sentence_is_the_usb_plugs():
    assert _contract("generic/usb-a-plug@1")["unplaced"] == SHARED_SENTENCE


@pytest.mark.parametrize("ref", sorted(PLUGS))
def test_a_cable_end_states_estimated_for_every_dimension_and_names_its_drawing(ref):
    c = _contract(ref)
    assert set(c["size-confidence"]) == {"w", "h"}
    assert set(c["size-confidence"].values()) == {"estimated"}
    assert "needs-drawing" in c["provenance"], "the drawing wanted is named under needs-drawing"
    assert "drawing" in c["provenance"]["needs-drawing"]
    assert "d" not in c["size"], "no size.d, as on the house plugs"


def test_a_cable_end_is_as_wide_as_its_receptacle_where_it_seats_in_it():
    for plug, port in ((FLEX_PLUG, FLEX), (VCP_PLUG, VCP), (PWR_PLUG, PWR)):
        p, r = _contract(plug), _contract(port)
        assert p["size"]["w"] >= r["size"]["w"] - 1e-9
        assert p["size"]["h"] >= r["size"]["h"] - 1e-9


@pytest.mark.parametrize("plug,port", [(SW_PLUG, SW), (PWR_PLUG, PWR), (VCP_PLUG, VCP),
                                       (FLEX_PLUG, FLEX)])
def test_each_cable_end_has_a_receptacle_that_presents_what_it_mates(plug, port):
    assert _contract(plug)["mates"] == _contract(port)["interface"]


# --- 3. the slots on the devices -----------------------------------------------

def _rear_cages(dev, tmp_path):
    src = LIB / f"devices/{dev}/device.yaml"
    r = warmrender.run([sys.executable, str(RENDER), str(src), "--library", str(LIB),
                        "--out", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    cfg = json.loads((tmp_path / f"{src.parent.name}.configs.json").read_text())
    return cfg["cages"]


@pytest.mark.parametrize("dev", DEVICES)
def test_each_stack_or_vcp_placement_is_a_connector_slot_of_its_key(dev, tmp_path):
    cages = _rear_cages(dev, tmp_path)
    got = {c["id"]: c for view in cages.values() for c in view}
    for pid, ref, _at, _group, _pos in PLACED[family(dev)]:
        slot = got.get(pid)
        assert slot is not None, f"{dev}: {pid} is not published as a slot"
        assert slot["kind"] == "connector" and slot["interface"] == key_of(ref), slot
        assert PORTS[ref][1] in slot["accepts"], slot
        assert slot["mate"] is not None, slot


# --- 4. the EX4500 module ------------------------------------------------------

def test_the_ex4500_virtual_chassis_module_composes_the_ex4200_port_at_each_vcp(comps):
    """The guide's Virtual Chassis cable ships with an EX4200 and joins EX4200, EX4500
    and EX4550 VCPs (pages 27, 129 and 137), so the module's two dedicated ports are
    the EX4200's part, put where the art was, centres kept."""
    c = _contract("juniper/ex4500-vc1@1")
    parts = {p["id"]: p for p in c["parts"]}
    assert set(parts) == {"vcp-0", "vcp-1"}
    assert {p["ref"] for p in parts.values()} == {VCP}
    # the centres the isometric art gave, [86.0, 7.4] and [150.0, 7.4] at 24.0 x 8.0
    for pid, cx in (("vcp-0", 98.0), ("vcp-1", 162.0)):
        w, h = _contract(VCP)["size"]["w"], _contract(VCP)["size"]["h"]
        at = parts[pid]["at"]
        assert (at[0] + w / 2, at[1] + h / 2) == pytest.approx((cx, 11.4))
    assert not [k for k, e in c["elements"].items() if e.get("class") == "port"]
    slots = {s["id"]: s for s in comps["juniper/ex4500-vc1@1"]["cages"]}
    assert set(slots) == {"vcp-0", "vcp-1"}
    assert all(s["interface"] == "ex4200-vcp" and VCP_PLUG in s["accepts"] for s in slots.values())


def test_the_ex4500_module_records_that_the_port_is_borrowed():
    prov = _contract("juniper/ex4500-vc1@1")["provenance"]
    text = prov["ports"]
    assert "borrowed" in text and "36.2" in text and "24.0" in text
    assert all(f"PDF p.{page}" in text for page in ("27", "129", "137"))


# --- 5. the FlexStack port -----------------------------------------------------

def test_the_flexstack_port_presents_its_key_and_says_what_will_seat_it():
    c = _contract(FLEX)
    assert c["class"] == "port" and c["interface"] == "flexstack"
    assert c["connection-points"]["mate"]["direction"] == "front"
    assert c["unplaced"].startswith("seated by")
    assert "c2960s-stack" in c["unplaced"] and "#1322" in c["unplaced"]


def test_the_flexstack_ports_figures_equal_what_its_provenance_says_it_read():
    c = _contract(FLEX)
    # the module art #1322 measured: a cage 16.5 x 9.0, its opening the cage inset
    # 0.6 at the sides and 0.7 at the top and bottom, at 3.41 px per mm
    assert c["size"] == {"w": 16.5, "h": 9.0}
    assert set(c["size-confidence"].values()) == {"estimated"}
    op = c["elements"]["opening"]
    assert op["at"] == [0.6, 0.7] and op["size"] == [15.3, 7.6]
    assert c["connection-points"]["mate"]["at"] == pytest.approx([8.25, 4.5])
    text = c["provenance"]["size"]
    for token in ("16.5", "9.0", "15.3", "7.6", "3.41"):
        assert token in text, token


# --- 6. nothing moved (a guard: it passes before and after) ---------------------

@pytest.mark.parametrize("dev", DEVICES)
def test_no_stack_or_vcp_placement_changed_its_group_id_position_or_rotation(dev):
    layout = yaml.safe_load((LIB / f"devices/{dev}/layout.yaml").read_text())
    found = {}

    def walk(o):
        if isinstance(o, dict):
            if o.get("ref") in PORTS:
                found[o["id"]] = o
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(layout)
    want = PLACED[family(dev)]
    assert sorted(found) == sorted(w[0] for w in want)
    for pid, ref, at, group, pos in want:
        p = found[pid]
        assert p["ref"] == ref and p["at"] == at and p["group"] == group
        assert p["rel-pos"] == pos and not p.get("rotate")
