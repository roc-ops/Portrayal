"""The connectors a GPU card needs: its power inlets and its NVLink bridge
connector, each a registry interface with a part that presents it and a part
that mates it (P-0028; docs/connectors-gpu-design.md).

Run against the real library and a components.json the indexer builds here.
The figures themselves are held by their sources in each contract's provenance;
these tests hold the shape: what mates what, what is exported, and that every
size is stated with a confidence.
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild
from portrayal import dcim_export as dx
from portrayal import render as render_mod
from test_coax_slots import _contract

ROOT = Path(__file__).resolve().parents[2]

# interface -> (the receptacle that presents it, the standard it conforms to)
HEADERS = {
    "eps12v-8pin": ("std/eps12v-header@1", "mini-fit-8-header"),
    "pcie-8pin": ("std/pcie-8pin-header@1", "mini-fit-8-header"),
    "pcie-12vhpwr": ("std/12vhpwr-header@1", "pcie-16pin-header"),
    "pcie-12v-2x6": ("std/12v-2x6-header@1", "pcie-16pin-header"),
}
PINS = {"eps12v-8pin": 8, "pcie-8pin": 8, "pcie-12vhpwr": 16, "pcie-12v-2x6": 16}
# plug -> the interfaces it mates, as a set
PLUGS = {
    "generic/eps12v-8pin-plug@1": {"eps12v-8pin"},
    "generic/pcie-8pin-plug@1": {"pcie-8pin"},
    "generic/pcie-16pin-plug@1": {"pcie-12vhpwr", "pcie-12v-2x6"},
}
EACH_HEADER = pytest.mark.parametrize("iface", sorted(HEADERS))
EACH_PLUG = pytest.mark.parametrize("ref", sorted(PLUGS))
NVLINK = "nvlink-a100-pcie"
BRIDGE = "nvidia/nvlink-bridge-a100-2slot@1"
NVLINK_CONNECTOR = "nvidia/nvlink-a100-connector@1"
# PCIe CEM slot pitch: a two-slot bridge spans two of them
SLOT_PITCH = 20.32


def standards():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def mates(contract):
    m = contract["mates"]
    return {m} if isinstance(m, str) else set(m)


@pytest.fixture(scope="module")
def comps():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}


# --- the registry ---------------------------------------------------------------

@pytest.mark.parametrize("iface", sorted(HEADERS) + [NVLINK])
def test_every_interface_is_registered_with_a_note(iface):
    reg = render_mod._connector_registry()
    assert iface in reg and reg[iface].get("note"), iface
    if "standard" in reg[iface]:
        assert reg[iface]["standard"] in standards()


@EACH_HEADER
def test_a_header_is_an_inlet_presenting_its_interface_at_the_centre_of_its_face(iface):
    ref, std_key = HEADERS[iface]
    c = _contract(ref)
    assert c["class"] == "inlet" and c["interface"] == iface
    assert c["conforms"] == std_key
    assert c["attrs"]["media"] in ("eps12v", "pcie-8pin", "pcie-12vhpwr", "pcie-12v-2x6")
    w, h = c["size"]["w"], c["size"]["h"]
    assert c["connection-points"]["mate"]["at"] == pytest.approx([w / 2, h / 2])
    s = standards()[std_key]
    assert (w, h) == (s["w"], s["h"])
    assert c["attrs"]["pins"] == PINS[iface]


@EACH_HEADER
def test_a_header_states_a_confidence_for_each_size_and_for_the_depth(iface):
    c = _contract(HEADERS[iface][0])
    assert set(c["size-confidence"]) >= {"w", "h"}
    s = standards()[HEADERS[iface][1]]
    assert s["confidence"] and s["depth-confidence"]
    assert c["provenance"]


def test_the_two_8_pin_headers_do_not_share_an_interface():
    """Molex lists the PCIe housing's polarisation as its own, 'for PCI Express
    applications only', so a PCIe plug is not offered to an EPS12V header."""
    assert HEADERS["eps12v-8pin"][0] != HEADERS["pcie-8pin"][0]
    assert mates(_contract("generic/pcie-8pin-plug@1")).isdisjoint({"eps12v-8pin"})
    assert mates(_contract("generic/eps12v-8pin-plug@1")).isdisjoint({"pcie-8pin"})


# --- the cable plugs ------------------------------------------------------------

@EACH_PLUG
def test_a_plug_is_a_port_that_mates_exactly_its_interfaces(ref):
    c = _contract(ref)
    assert c["class"] == "port"
    assert mates(c) == PLUGS[ref]
    assert "d" not in c["size"], "a port's depth is carried by its relief"
    assert c["connection-points"]["mate"] and c["connection-points"]["cable"]
    assert c["fields"]["cable-od"]["default"] > 0


@EACH_PLUG
def test_a_plug_mate_lands_on_each_header_it_mates(ref):
    for iface in PLUGS[ref]:
        h = _contract(HEADERS[iface][0])
        c = _contract(ref)
        # the plug's mating face is the header's: one size, so the mate points
        # are the centres and a seated plug covers the opening
        assert c["size"]["w"] == pytest.approx(h["size"]["w"])
        assert c["size"]["h"] == pytest.approx(h["size"]["h"])


def test_the_slot_a_header_presents_offers_its_plug_and_no_other(comps):
    for iface, (ref, _std) in HEADERS.items():
        entry = comps[ref]
        assert entry["interface"] == iface
    for ref, ifaces in PLUGS.items():
        got = comps[ref]["mates"]
        assert set([got] if isinstance(got, str) else got) == ifaces


def test_the_16_pin_plug_has_twelve_power_and_four_sense_contacts():
    c = _contract("generic/pcie-16pin-plug@1")
    assert c["attrs"]["pins"] == 16 and c["attrs"]["pins-power"] == 12
    assert c["attrs"]["pins-sense"] == 4


def test_the_8_pin_plugs_state_their_12v_and_ground_split():
    """NVIDIA PB-10577 fig 7: the EPS side is 4 + 4, the PCIe side 3 + 5."""
    eps = _contract("generic/eps12v-8pin-plug@1")["attrs"]
    pcie = _contract("generic/pcie-8pin-plug@1")["attrs"]
    assert (eps["pins-12v"], eps["pins-ground"]) == (4, 4)
    assert (pcie["pins-12v"], pcie["pins-ground"]) == (3, 5)


# --- the exports ----------------------------------------------------------------

@EACH_HEADER
def test_a_card_with_a_power_inlet_exports_a_power_port(iface):
    ref = HEADERS[iface][0].split("@")[0]
    assert ref in dx.PART_POWER
    # no PowerPortTypeChoices value names these, in NetBox or Nautobot: `other`,
    # with the connector as its label
    assert dx.PART_POWER[ref] == "other" and ref in dx.POWER_LABEL
    card = {"name": "t", "attrs": {"model": "T"},
            "parts": [{"ref": HEADERS[iface][0], "id": "aux-power"}]}
    rows = dx.build_module(card, "X")["power-ports"]
    assert rows == [{"name": "aux-power", "type": "other", "label": dx.POWER_LABEL[ref]}]


def test_the_plugs_and_the_bridge_export_nothing():
    for ref in list(PLUGS) + [BRIDGE, NVLINK_CONNECTOR]:
        assert ref.split("@")[0] not in dx.PART_POWER


def test_the_power_labels_name_distinct_connectors():
    labels = [dx.POWER_LABEL[HEADERS[i][0].split("@")[0]] for i in HEADERS]
    assert len(set(labels)) == len(labels)


# --- NVLink ---------------------------------------------------------------------

def test_the_nvlink_connector_presents_the_bridge_interface():
    c = _contract(NVLINK_CONNECTOR)
    assert c["interface"] == NVLINK and c["class"] == "inlet"
    assert c["attrs"]["role"] == "nvlink"
    assert NVLINK_CONNECTOR.split("@")[0] not in dx.PART_POWER


def test_the_bridge_mates_the_nvlink_interface_at_both_ends_one_two_slot_pitch_apart():
    c = _contract(BRIDGE)
    assert c["class"] == "port" and mates(c) == {NVLINK}
    a, b = c["connection-points"]["mate"], c["connection-points"]["mate-b"]
    assert abs(b["at"][0] - a["at"][0]) == pytest.approx(2 * SLOT_PITCH)
    assert b["at"][1] == pytest.approx(a["at"][1])
    assert c["attrs"]["part-number"] == "900-53651-0000-000"
    assert c["attrs"]["per-card-pair"] == 3
    assert c["attrs"]["spans-slots"] == 2


def test_the_bridge_is_wide_enough_to_reach_both_connectors():
    c = _contract(BRIDGE)
    conn = _contract(NVLINK_CONNECTOR)
    assert c["size"]["w"] == pytest.approx(2 * SLOT_PITCH + conn["size"]["w"])
    assert c["size"]["h"] == pytest.approx(conn["size"]["h"])


# --- the 3D form (P-0031) ---------------------------------------------------------
#
# Each part was a box with its 2D skin painted on one face. The form is built the
# way the library builds depth anywhere (docs/connectors-gpu-design.md section 8):
# a header's `relief.cavity` names ONE path of one subpath a cell, so each cell is
# its own recess walled in its own shape; its contacts are `top` features standing
# on the cavity floor; a plug is a `shape` tube whose holes are the cells, closed
# by a rear wall. These tests hold that shape; the heights are estimates and are
# not asserted beyond their order.

def _skin(ref):
    from test_coax_slots import _skin_path
    return ET.parse(_skin_path(ref)).getroot()


def _node(root, node_id):
    hits = [e for e in root.iter() if e.get("id") == node_id]
    assert len(hits) == 1, f"{node_id}: {len(hits)} nodes"
    return hits[0]


def _subpaths(path_el):
    return len(re.findall(r"[Mm]", path_el.get("d")))


def _features(ref):
    return {f["node"]: f for f in _contract(ref)["relief"]["features"]}


def _cell_boxes(path_el):
    """The bounding boxes of a cavity path's subpaths (H/V/L/Z, absolute)."""
    boxes = []
    for sub in re.findall(r"M[^M]*", path_el.get("d")):
        nums = [float(n) for n in re.findall(r"-?\d+\.?\d*", sub)]
        cmds = re.findall(r"[MHVLZ]", sub)
        x = y = None
        xs, ys, i = [], [], 0
        for c in cmds:
            if c in "ML":
                x, y = nums[i], nums[i + 1]; i += 2
            elif c == "H":
                x = nums[i]; i += 1
            elif c == "V":
                y = nums[i]; i += 1
            else:
                continue
            xs.append(x); ys.append(y)
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


@EACH_HEADER
def test_a_header_cavity_is_one_recess_a_cell(iface):
    ref = HEADERS[iface][0]
    c = _contract(ref)
    root = _skin(ref)
    cavity = _node(root, c["relief"]["cavity"])
    assert _subpaths(cavity) == PINS[iface]
    # the cells are separate: no two boxes overlap, so the housing top stands between
    boxes = _cell_boxes(cavity)
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[2] <= b[0] + 1e-9 or b[2] <= a[0] + 1e-9 or a[3] <= b[1] + 1e-9 or b[3] <= a[1] + 1e-9
    # and each is inside the opening
    w, h = c["size"]["w"], c["size"]["h"]
    assert all(b[0] > 0 and b[1] > 0 and b[2] < w and b[3] < h for b in boxes)


@EACH_HEADER
def test_a_header_has_a_contact_standing_in_each_cell_short_of_the_face(iface):
    ref = HEADERS[iface][0]
    c = _contract(ref)
    root = _skin(ref)
    feats = _features(ref)
    pins = [f for n, f in feats.items() if "top" in f]
    assert len(pins) == PINS[iface]
    boxes = _cell_boxes(_node(root, c["relief"]["cavity"]))
    for f in pins:
        el = _node(root, f["node"])
        assert 0 < f["top"] < c["size"]["d"], f["node"]
        assert f["confidence"] == "estimated" and f["source"]
        x, y = float(el.get("x")), float(el.get("y"))
        w, h = float(el.get("width")), float(el.get("height"))
        # the contact stands wholly inside one cell
        assert any(b[0] <= x and x + w <= b[2] and b[1] <= y and y + h <= b[3] for b in boxes), f["node"]


@EACH_HEADER
def test_a_header_carries_a_latch_ramp_on_the_housing(iface):
    ref = HEADERS[iface][0]
    f = _features(ref)["latch"]
    assert f["out"] > 0 and (f.get("profile") or f.get("profile-y"))
    # a ramp rises: it ends higher than it starts
    prof = f.get("profile") or f["profile-y"]
    assert prof[-1][1] > prof[0][1] and f["out"] == pytest.approx(prof[-1][1])
    # it slopes along the mating axis: it starts behind the face (negative lift),
    # its profile runs from that depth at its outer edge up to the face at its
    # inner one, and its node is the wedge seen end on, outside the part's outline
    assert f["lift"] < 0 and prof[0][1] == pytest.approx(f["lift"])
    assert -f["lift"] <= _contract(ref)["size"]["d"]
    el = _node(_skin(ref), "latch")
    w, h = _contract(ref)["size"]["w"], _contract(ref)["size"]["h"]
    x, y = float(el.get("x")), float(el.get("y"))
    ew, eh = float(el.get("width")), float(el.get("height"))
    assert x + ew <= 0 or x >= w or y + eh <= 0 or y >= h
    # the profile spans the node across the wall (x for a side wall, y for the top)
    assert prof[-1][0] == pytest.approx(ew if f.get("profile") else eh)
    assert f["confidence"] == "estimated"
    assert "latch" in _contract(ref)["provenance"]


@pytest.mark.parametrize("iface", ["pcie-12vhpwr", "pcie-12v-2x6"])
def test_the_16_pin_headers_have_four_smaller_sense_cells(iface):
    ref = HEADERS[iface][0]
    boxes = _cell_boxes(_node(_skin(ref), _contract(ref)["relief"]["cavity"]))
    area = sorted((b[2] - b[0]) * (b[3] - b[1]) for b in boxes)
    assert len(boxes) == 16
    assert area[3] < area[4] and area[0] == pytest.approx(area[3])
    assert area[4] == pytest.approx(area[-1])


def test_the_12v_2x6_sense_contacts_stand_shorter_than_the_12vhpwr_s():
    h = _features(HEADERS["pcie-12vhpwr"][0])
    n = _features(HEADERS["pcie-12v-2x6"][0])
    for i in range(1, 5):
        assert n[f"sense-{i}"]["top"] < h[f"sense-{i}"]["top"]
        assert n[f"sense-{i}"]["top"] < n["pin-1"]["top"]
    assert h["sense-1"]["top"] == h["pin-1"]["top"]


@EACH_PLUG
def test_a_plug_is_a_tube_with_its_cells_open_and_a_rear_wall(ref):
    c = _contract(ref)
    root = _skin(ref)
    feats = _features(ref)
    pins = c["attrs"]["pins"]
    body = feats["body"]
    assert body["shape"] is True and "lift" not in body
    # the body outline plus one hole a cell
    assert _subpaths(_node(root, "body")) == 1 + pins
    assert _node(root, "body").get("fill-rule") == "evenodd"
    back = feats["back"]
    # the wall ends a hair short of the housing's rear face, so the two do not
    # share that plane (test_no_two_pieces_of_a_connector_share_a_plane)
    assert back["shape"] is True and back["out"] == pytest.approx(body["out"] - 0.05)
    assert 0 < back["lift"] < body["out"]
    assert _subpaths(_node(root, "back")) == 1


@EACH_PLUG
def test_a_plug_has_a_latch_arm_on_top_and_a_wire_at_each_cell(ref):
    c = _contract(ref)
    root = _skin(ref)
    feats = _features(ref)
    body_out = feats["body"]["out"]
    arm, hook = feats["latch-arm"], feats["latch-hook"]
    assert arm["lift"] < arm["out"] <= body_out
    # the hook is at the mating end, short of the arm's far end, and stands
    # 0.05 inside the arm's start and sides so they share no plane
    assert hook["lift"] == pytest.approx(arm["lift"] + 0.05) and hook["out"] < arm["out"]
    # the latch stands above the housing's top edge
    assert float(_node(root, "latch-arm").get("y")) < 0
    wires = [f for n, f in feats.items() if n.startswith(("wire-", "sense-wire-"))]
    assert len(wires) == c["attrs"]["pins"]
    back = feats["back"]
    for f in wires:
        # each wire starts inside the rear wall it leaves, not on the plane of its face
        assert back["lift"] < f["lift"] < back["out"] and f["cyl"] > 0
        _node(root, f["node"])


@EACH_PLUG
def test_a_plug_keeps_its_thirty_millimetre_stub_and_it_starts_after_the_comb(ref):
    feats = _features(ref)
    body_out = feats["body"]["out"]
    comb, stub = feats["comb"], feats["stub"]
    wire_end = max(f["lift"] + f["cyl"] for n, f in feats.items() if "wire-" in n)
    # the wires end inside the comb and the stub starts inside it, so neither
    # shares a plane with the comb's faces
    assert comb["lift"] < wire_end < comb["out"]
    assert comb["lift"] < stub["lift"] < comb["out"]
    # the cable still ends 30 from the body, as before the form was built
    assert stub["lift"] + stub["cyl"] == pytest.approx(body_out + 30)


def test_the_nvlink_connector_is_a_slot_with_a_rim_and_two_contact_rows():
    c = _contract(NVLINK_CONNECTOR)
    root = _skin(NVLINK_CONNECTOR)
    feats = _features(NVLINK_CONNECTOR)
    assert c["relief"]["cavity"] == "inlet-face"
    rim = feats["rim"]
    assert rim["shape"] is True and rim["out"] > 0
    # the rim is a ring with the well cut out of it
    assert _subpaths(_node(root, "rim")) == 2
    rows = [f for n, f in feats.items() if n.startswith("contact-")]
    assert len(rows) == 2
    assert all(0 < f["top"] < c["size"]["d"] for f in rows)
    # the rows stand inside the well
    well = _node(root, "inlet-face")
    x0, x1 = float(well.get("x")), float(well.get("x")) + float(well.get("width"))
    for f in rows:
        el = _node(root, f["node"])
        assert x0 < float(el.get("x")) and float(el.get("x")) + float(el.get("width")) < x1


def test_the_bridge_is_stepped_up_from_its_plate_to_its_raised_centre():
    c = _contract(BRIDGE)
    root = _skin(BRIDGE)
    feats = _features(BRIDGE)
    order = ["body", "end-a", "cover", "cover-top", "ridge-1"]
    heights = [feats[n]["out"] for n in order]
    assert heights == sorted(heights) and len(set(heights)) == len(heights)
    assert feats["end-a"]["out"] == feats["end-b"]["out"]
    assert all(f["confidence"] == "estimated" for f in feats.values())
    # the two ends are the connector's width less 0.05 a side (so they do not
    # share a plane with the plate's edge), one two-slot pitch apart, and the
    # `mate` points land at their centres
    conn = _contract(NVLINK_CONNECTOR)["size"]["w"]
    a, b = _node(root, "end-a"), _node(root, "end-b")
    assert float(a.get("width")) == pytest.approx(conn - 0.1) == pytest.approx(float(b.get("width")))
    assert float(b.get("x")) - float(a.get("x")) == pytest.approx(2 * SLOT_PITCH)
    cp = c["connection-points"]
    assert cp["mate"]["at"][0] == pytest.approx(float(a.get("x")) + float(a.get("width")) / 2)
    assert cp["mate-b"]["at"][0] == pytest.approx(float(b.get("x")) + float(b.get("width")) / 2)
    # the cover sits between the ends and the centre inside the cover
    cov, top = _node(root, "cover"), _node(root, "cover-top")
    assert float(a.get("x")) + conn <= float(cov.get("x"))
    assert float(cov.get("x")) + float(cov.get("width")) <= float(b.get("x"))
    assert float(cov.get("x")) < float(top.get("x"))
    assert float(top.get("x")) + float(top.get("width")) < float(cov.get("x")) + float(cov.get("width"))
    assert "form-3d" in c["provenance"] and c["provenance"]["form-3d"].startswith("estimated")


def test_every_3d_feature_of_every_part_says_how_sure_it_is_and_every_node_exists():
    refs = [h[0] for h in HEADERS.values()] + list(PLUGS) + [NVLINK_CONNECTOR, BRIDGE]
    for ref in refs:
        root = _skin(ref)
        for f in _contract(ref)["relief"]["features"]:
            assert f["confidence"] in ("estimated", "drawing"), (ref, f["node"])
            assert f["source"], (ref, f["node"])
            _node(root, f["node"])


def test_every_estimated_bridge_figure_says_so():
    c = _contract(BRIDGE)
    assert c["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert c["provenance"]["size"].startswith("estimated")
    assert c["provenance"]["height"].startswith("estimated")


# --- no two faces share a plane (P-0034) -----------------------------------------
# Two faces on one plane where they overlap are drawn by whichever the depth
# buffer happens to prefer, pixel by pixel, and the choice changes when the camera
# moves: a flicker. A browser scan (each box drawn in a flat colour, the camera
# nudged 0.05 mm) found it between a plug's housing and its rear wall, between
# its wires and the housing, and between the bridge's plate and its ends. The
# lint rule for it (L71 on PR #1070) is not on this branch, so the nine parts are
# held here the same way: every box a part builds, its faces compared in pairs.

ALL_NINE = [h[0] for h in HEADERS.values()] + sorted(PLUGS) + [NVLINK_CONNECTOR, BRIDGE]


def _bbox(el):
    tag = el.tag.split("}")[-1]
    if tag == "rect":
        x, y = float(el.get("x", 0)), float(el.get("y", 0))
        return x, y, x + float(el.get("width")), y + float(el.get("height"))
    if tag == "circle":
        cx, cy, r = float(el.get("cx")), float(el.get("cy")), float(el.get("r"))
        return cx - r, cy - r, cx + r, cy + r
    assert tag == "path", tag
    xs, ys, x, y = [], [], 0.0, 0.0
    for cmd, args in re.findall(r"([MLHVAQZ])([^MLHVAQZ]*)", el.get("d")):
        n = [float(v) for v in re.findall(r"-?\d*\.?\d+", args)]
        if cmd in "ML":
            x, y = n[0], n[1]
        elif cmd == "H":
            x = n[0]
        elif cmd == "V":
            y = n[0]
        elif cmd == "A":
            x, y = n[5], n[6]
        elif cmd == "Q":
            x, y = n[2], n[3]
        else:
            continue
        xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def _boxes(ref):
    """Each feature that builds a solid: (node, x range, y range, z range, flat),
    `flat` when its sides are planes. A cylinder and a sloped wedge have only the
    planes of their ends. A `top` feature stands on a cavity floor and is left out."""
    root = _skin(ref)
    out = []
    for f in _contract(ref)["relief"]["features"]:
        if "top" in f or "sink" in f:
            continue
        lift = f.get("lift", 0.0)
        z1 = lift + f["cyl"] if "cyl" in f else f.get("out")
        if z1 is None:
            continue
        x0, y0, x1, y1 = _bbox(_node(root, f["node"]))
        flat = "cyl" not in f and not (f.get("profile") or f.get("profile-y"))
        out.append((f["node"], (x0, x1), (y0, y1), (lift, z1), flat))
    return out


def _overlap(a, b):
    return min(a[1], b[1]) - max(a[0], b[0])


@pytest.mark.parametrize("ref", ALL_NINE)
def test_no_two_pieces_of_a_connector_share_a_plane(ref):
    boxes = _boxes(ref)
    assert boxes, ref
    bad = []
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            for axis in range(3):          # 0: x planes, 1: y planes, 2: z planes
                if axis < 2 and not (a[4] and b[4]):
                    continue
                others = [k for k in range(3) if k != axis]
                if any(_overlap(a[1 + k], b[1 + k]) <= 1e-9 for k in others):
                    continue
                for pa in a[1 + axis]:
                    for pb in b[1 + axis]:
                        if abs(pa - pb) < 1e-6:
                            bad.append((a[0], b[0], "xyz"[axis], pa))
    assert not bad, f"{ref}: faces on one plane where they overlap: {bad}"


@EACH_HEADER
def test_a_header_has_a_plate_over_its_face_that_overhangs_every_cell_wall(iface):
    """The face is a raster whose cell openings are punched at 4 px/mm and land up
    to a pixel off the exact cell walls, which left a sliver of the dark behind
    between a wall and the face. An exact skin 0.05 proud of the face, its cells
    cut slightly smaller, covers the walls' top edges."""
    ref = HEADERS[iface][0]
    c = _contract(ref)
    root = _skin(ref)
    f = _features(ref)["plate"]
    assert f["shape"] is True and 0 < f["out"] <= 0.1 and "lift" not in f
    plate = _node(root, "plate")
    assert plate.get("fill-rule") == "evenodd"
    assert _subpaths(plate) == 1 + PINS[iface]
    holes = ET.Element("path", d=" ".join(re.findall(r"M[^M]*", plate.get("d"))[1:]))
    cells = _cell_boxes(_node(root, c["relief"]["cavity"]))
    cut = _cell_boxes(holes)
    assert len(cut) == len(cells)
    for cell, hole in zip(cells, cut):
        # inside the cell, by about 0.03 on every side: more than the raster's
        # fraction of a texel at the base density, little enough to see
        for k in (0, 1):
            assert 0.02 <= hole[k] - cell[k] <= 0.05, (cell, hole)
            assert 0.02 <= cell[k + 2] - hole[k + 2] <= 0.05, (cell, hole)
