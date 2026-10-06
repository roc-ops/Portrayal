"""Pluggable 5.08 mm terminal headers are connector slots, and the screw-clamp
plugs that seat in them (#789, docs/connectors-dc-terminal-design.md).

The three headers (common/terminal-header-508-2@1, common/terminal-header-508-5f@1
and common/dc-terminal-header-6@1) each present an interface
spec/schemas/connectors.yaml lists, so every one of them is a slot;
generic/terminal-508-2-plug@1, generic/terminal-508-5-plug@1 and
generic/terminal-508-6-plug@1 mate them. These run against the real library, a
components.json the indexer builds here and device copies rendered here, never
a possibly stale dist.

A TERMINAL PLUG CARRIES ONE WIRE PER POLE, NOT ONE CABLE, and most of what is
below holds the parts to that: a stub and a named point per pole, at the
header's pitch, numbered as the header numbers its contacts, every stub sized
by one `wire-od` field and painted by one `wire-color` field.

THE SEATED DEPTH IS A RULING: each plug stands 10 in front of the face its
header presents, the 22 less 12 of the manufacturer's mated figure. No plug
figure is derived from the depth a header MODELS; a test here fails by design
when one of those modelled figures is revised, because the plug's own
provenance quotes it.
"""
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild
import warmrender
from portrayal import render as render_mod
from portrayal.artifacts import face_file
from portrayal.manifest import presented_interface
from test_coax_slots import _contract, _skin_path
from test_head_3d import apply, box, lift_of
from test_nested_occupants import (assert_same_turn, by_path, cage_mate, device_matrix,
                                   device_point, own_mate)

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
EPS = 1e-6
STUB = 30.0
PITCH = 5.08
STANDS = 10.0       # 22 - 12, the mated figure
LENGTH = 18.2       # the plug, end to end
AXIS = 10.7         # the row of poles, below the top of the plug
WIRE_OD = 3.0       # H07V-K 1.5 mm2; 4.0, for 2.5 mm2, is the largest the plug takes
GREEN = "#4fb548"

P2 = "generic/terminal-508-2-plug@1"
P5F = "generic/terminal-508-5-plug@1"
P6 = "generic/terminal-508-6-plug@1"

# interface -> (the header that presents it, the plug that mates it, positions)
PAIRS = {
    "terminal-508-2": ("common/terminal-header-508-2@1", P2, 2),
    "terminal-508-5": ("common/terminal-header-508-5f@1", P5F, 5),
    "terminal-508-6": ("common/dc-terminal-header-6@1", P6, 6),
}
HEADER_OF = {plug: hdr for hdr, plug, _n in PAIRS.values()}
IFACE_OF = {plug: iface for iface, (_h, plug, _n) in PAIRS.items()}
POLES = {plug: n for _h, plug, n in PAIRS.values()}
PLUGS = sorted(HEADER_OF)
EACH = pytest.mark.parametrize("ref", PLUGS)
FLANGED = {P5F}

# header -> how far its presented face stands off the face it is placed on.
# The two AurCore headers build a housing 2.5 proud and present at its mouth;
# the ReadyLinks header is drawn flat.
PRESENTS = {
    "common/terminal-header-508-2@1": 2.5,
    "common/terminal-header-508-5f@1": 2.5,
    "common/dc-terminal-header-6@1": 0.0,
}
# What each header was before this work, and still is: size, class, attrs and
# elements. Giving it an interface changed none of them.
UNCHANGED = {
    "common/terminal-header-508-2@1": (
        {"w": 10.16, "h": 12.1}, "port",
        {"media": "terminal-block", "positions": 2, "pitch-mm": 5.08},
        {"body": {"at": [0.0, 0.0], "size": [10.16, 12.1], "class": "connector"}}),
    "common/terminal-header-508-5f@1": (
        {"w": 35.56, "h": 12.1, "d": 12.0}, "inlet",
        {"media": "dc-terminal", "positions": 5, "pitch-mm": 5.08},
        {"body": {"at": [0.0, 0.0], "size": [35.56, 12.1], "class": "connector"}}),
    "common/dc-terminal-header-6@1": (
        {"w": 32.4, "h": 11.1}, "inlet", {"media": "dc-terminal"},
        {"body": {"at": [0.0, 2.5], "size": [32.4, 8.6], "class": "connector"}}),
}


def std():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def feats(ref):
    return {f["node"]: f for f in _contract(ref)["relief"]["features"]}


def wires(ref):
    return [f"wire-{k}" for k in range(1, POLES[ref] + 1)]


def entries(ref):
    return [f"entry-{k}" for k in range(1, POLES[ref] + 1)]


def rear(f):
    """Where a relief feature ends, from the part's own face: an `out` is
    absolute, a `cyl` runs its length from its `lift`."""
    if f.get("out") is not None:
        return float(f["out"])
    return float(f.get("lift") or 0.0) + float(f["cyl"])


def skin(ref):
    root = ET.parse(_skin_path(ref)).getroot()
    return {e.get("id"): e for e in root.iter() if e is not root}


def header_poles(hdr):
    """The x of each contact of a header, left to right, in the header's own
    frame, read off its skin: the `pin-N` nodes where the header names them,
    else the openings drawn inside its body."""
    nodes = skin(hdr)
    pins = sorted((int(i.split("-")[1]), e) for i, e in nodes.items()
                  if i and i.startswith("pin-"))
    if pins:
        assert [k for k, _e in pins] == list(range(1, len(pins) + 1))
        return [float(e.get("x")) + float(e.get("width")) / 2 for _k, e in pins]
    root = ET.parse(_skin_path(hdr)).getroot()
    body = next(e for e in root.iter() if e.get("id") == "body")
    slots = [e for e in list(body)[1:]]
    return sorted(float(e.get("x")) + float(e.get("width")) / 2 for e in slots)


# --- 1. the registry -----------------------------------------------------------

@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_terminal_interface_is_a_connector_citing_a_standard(iface):
    reg = render_mod._connector_registry()
    assert iface in reg, iface
    entry = std()[reg[iface]["standard"]]
    # the interface names the connector: its pitch and its positions
    assert iface.startswith("terminal-508-") and str(PAIRS[iface][2]) in iface
    assert entry["depth"] == pytest.approx(12.0)
    assert PAIRS[iface][1] in reg[iface]["note"]


def test_a_flange_is_not_part_of_the_interface():
    """One five-position interface: the mating face, which a flanged or a
    plain header presents and a flanged or a plain plug mates. The header
    part keeps its `-5f` name and the plug says it is the screw-flange form,
    because the interface does not."""
    reg = render_mod._connector_registry()
    keys = {k for k in reg if k.startswith("terminal-508-")}
    assert keys == set(PAIRS)
    assert "terminal-508-5f" not in reg
    note = reg["terminal-508-5"]["note"]
    assert "a flanged or a plain header presents" in note
    assert "a flanged or a plain plug mates" in note
    assert _contract("common/terminal-header-508-5f@1")["interface"] == "terminal-508-5"
    plug = _contract(P5F)
    assert "SCREW-FLANGE" in plug["description"]
    assert " ".join(plug["provenance"]["flanged"].split()).startswith("THE SCREW-FLANGE PLUG")


@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_header_presents_its_interface_at_its_face(iface):
    hdr, _plug, n = PAIRS[iface]
    c = _contract(hdr)
    assert c["interface"] == iface
    got, at, lift = presented_interface(c, lambda r: _contract(r))
    assert got == iface
    poles = header_poles(hdr)
    assert len(poles) == n
    # the mate is the middle of the row of contacts
    assert at[0] == pytest.approx((poles[0] + poles[-1]) / 2, abs=0.01)
    body = c["elements"]["body"]
    assert at[1] == pytest.approx(body["at"][1] + body["size"][1] / 2)
    assert lift == pytest.approx(PRESENTS[hdr])


@pytest.mark.parametrize("hdr", sorted(UNCHANGED))
def test_a_header_gained_its_interface_and_kept_its_drawing(hdr):
    size, cls, attrs, elements = UNCHANGED[hdr]
    c = _contract(hdr)
    assert c["size"] == size
    assert c["class"] == cls
    assert c["attrs"] == attrs
    assert c["elements"] == elements
    assert c["version"].split(".")[0] == "1"
    assert "conforms" not in c and "mates" not in c


@pytest.mark.parametrize("hdr", sorted(UNCHANGED))
def test_a_headers_contacts_are_on_the_pitch(hdr):
    poles = header_poles(hdr)
    for a, b in zip(poles, poles[1:]):
        assert b - a == pytest.approx(PITCH, abs=1e-6)


# --- 2. the slots --------------------------------------------------------------

@pytest.fixture(scope="module")
def comps():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


def test_each_interface_is_mated_by_exactly_its_plug(comps):
    """A two-position plug is not offered by the five- or six-position header
    and the reverse: one part mates each interface, and it is that header's
    plug."""
    mating = {}
    for ref in comps:
        m = _contract(ref).get("mates")
        if m in PAIRS:
            mating.setdefault(m, []).append(ref)
    assert mating == {iface: [plug] for iface, (_h, plug, _n) in PAIRS.items()}


def test_every_part_presenting_a_terminal_interface_is_one_of_the_three_headers():
    """The census on the component side, and it measured something."""
    presenting = {}
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        if c.get("interface") in PAIRS:
            presenting[f"{f.parts[-4]}/{c['name']}@{f.parts[-2][1:]}"] = c["interface"]
    assert presenting == {hdr: iface for iface, (hdr, _p, _n) in PAIRS.items()}


def test_every_header_a_device_places_is_counted():
    """The census on the device side: each header is placed, at least as often
    as when this was written, and nothing composes one inside another part."""
    placed = {hdr: 0 for hdr in HEADER_OF.values()}
    for f in sorted((LIB / "devices").glob("*/*/device.yaml")):
        d = yaml.safe_load(f.read_text())
        for view in (d.get("views") or {}).values():
            for p in ((view or {}).get("components") or {}).get("placements") or []:
                if p.get("ref") in placed:
                    placed[p["ref"]] += 1
    assert all(n > 0 for n in placed.values()), placed
    assert placed["common/terminal-header-508-5f@1"] >= 10, placed
    assert placed["common/terminal-header-508-2@1"] >= 10, placed
    assert placed["common/dc-terminal-header-6@1"] >= 2, placed
    composed = []
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        composed += [p["ref"] for p in c.get("parts") or [] if p.get("ref") in placed]
    assert composed == []


# --- 3. the plugs --------------------------------------------------------------

@EACH
def test_it_is_a_plug_that_mates_its_interface(ref):
    d = _contract(ref)
    assert d["class"] == "port" and "behaviour" not in d
    assert d["mates"] == IFACE_OF[ref] and "interface" not in d
    name = ref.split("/")[1].split("@")[0]
    assert name == f"{IFACE_OF[ref]}-plug"
    assert d["conforms"] == name and name in std()
    assert d["unplaced"]


@EACH
def test_it_states_its_connector_its_positions_and_its_pitch(ref):
    """The medium is the connector word, `terminal-block`, on all three: a
    `class: port` part's media is read as a connector word by lint L62, and
    `dc-terminal` there makes `dc` one and flags every `dc-in` placement id."""
    d = _contract(ref)
    assert d["attrs"] == {"media": "terminal-block", "connector": IFACE_OF[ref],
                          "positions": POLES[ref], "pitch-mm": PITCH}
    hdr = _contract(HEADER_OF[ref])
    if "positions" in hdr["attrs"]:
        assert hdr["attrs"]["positions"] == POLES[ref]
        assert hdr["attrs"]["pitch-mm"] == PITCH


@EACH
def test_it_states_no_depth_and_its_length_is_in_the_registry(ref):
    d = _contract(ref)
    assert "d" not in d["size"], "a behaviour-less part's size.d is built as a pit"
    entry = std()[d["conforms"]]
    assert entry["depth"] == pytest.approx(LENGTH)
    assert (entry["w"], entry["h"]) == (d["size"]["w"], d["size"]["h"])
    assert set(d["size-confidence"]) == {"w", "h"} and d["size-notes"]


@EACH
def test_its_width_is_the_drawings(ref):
    """a + 5.08 for a plain plug; a + 5.69 and two 4.7 flanges for the flanged
    one. a is the pitch times one less than the positions."""
    d = _contract(ref)
    a = (POLES[ref] - 1) * PITCH
    want = a + 5.69 + 2 * 4.7 if ref in FLANGED else a + PITCH
    assert d["size"] == {"w": pytest.approx(want), "h": 15.0}


@EACH
def test_its_fields_are_the_wire_and_the_body(ref):
    f = _contract(ref)["fields"]
    assert set(f) == {"wire-od", "wire-color", "body-color"}
    text = " ".join(_contract(ref)["provenance"]["wire-od"].split())
    assert "3 mm" in text and "1.5 mm2" in text and "THE LARGEST WIRE IT TAKES" in text
    assert f["wire-od"] == {"label": "Wire outside diameter", "type": "number",
                            "unit": "mm", "default": WIRE_OD}
    assert f["wire-color"]["default"] == "#1c1c1c"
    assert f["body-color"]["default"] == GREEN


def test_the_default_body_is_the_green_the_headers_are_drawn_in():
    for hdr in ("common/terminal-header-508-2@1", "common/terminal-header-508-5f@1"):
        assert skin(hdr)["body"].get("fill") == GREEN


# --- 4. one wire per pole --------------------------------------------------------

@EACH
def test_there_is_one_stub_and_one_point_per_pole(ref):
    d = _contract(ref)
    n = POLES[ref]
    nodes = skin(ref)
    assert sorted(i for i in nodes if i.startswith("wire-")) == sorted(wires(ref))
    cps = d["connection-points"]
    assert sorted(cps) == sorted(["mate"] + wires(ref))
    assert "cable" not in cps, "a terminal plug carries wires, not one cable"
    assert len(wires(ref)) == n > 0


@EACH
def test_the_wires_are_at_the_pitch_and_centred_on_the_mate(ref):
    d = _contract(ref)
    nodes = skin(ref)
    xs = [float(nodes[w].get("cx")) for w in wires(ref)]
    for a, b in zip(xs, xs[1:]):
        assert b - a == pytest.approx(PITCH, abs=1e-6)
    mate = d["connection-points"]["mate"]["at"]
    assert mate == pytest.approx([d["size"]["w"] / 2, AXIS])
    assert (xs[0] + xs[-1]) / 2 == pytest.approx(mate[0], abs=1e-6)
    assert all(float(nodes[w].get("cy")) == pytest.approx(AXIS) for w in wires(ref))


@EACH
def test_each_wire_point_is_on_its_own_stub(ref):
    d = _contract(ref)
    nodes = skin(ref)
    for w in wires(ref):
        cp = d["connection-points"][w]
        assert cp["on"] == w and cp["direction"] == "front"
        assert cp["at"] == pytest.approx([float(nodes[w].get("cx")), float(nodes[w].get("cy"))])


@EACH
def test_each_stub_is_bound_to_the_two_wire_fields(ref):
    nodes = skin(ref)
    f = feats(ref)
    for w in wires(ref):
        e = nodes[w]
        assert e.tag.endswith("circle")
        assert e.get("data-r-from") == "wire-od"
        assert e.get("data-fill-from") == "wire-color"
        assert float(e.get("r")) == pytest.approx(WIRE_OD / 2)
        # L73: the node a field paints states no relief colour
        assert "color" not in f[w]
    # and nothing else follows the wire
    others = [i for i, e in nodes.items() if e.get("data-r-from") and i not in wires(ref)]
    assert others == []


@EACH
def test_the_body_is_bound_to_the_body_field(ref):
    nodes = skin(ref)
    painted = sorted(i for i, e in nodes.items() if e.get("data-fill-from") == "body-color")
    want = ["body"] + (["flange-l", "flange-r"] if ref in FLANGED else [])
    assert painted == sorted(want)
    for i in painted:
        assert nodes[i].get("fill") == GREEN
        assert nodes[i].get("data-stroke-derive") == "body-color"
        assert nodes[i].get("stroke") == "#306e2c"   # the fixed shade of the default
        assert "color" not in feats(ref)[i]


@EACH
def test_the_poles_are_numbered_as_the_header_numbers_its_contacts(ref):
    """Seated mate on mate, `wire-k` is over the header's k-th contact from
    the left: the offset of each wire from the plug's mate is the offset of
    that contact from the header's mate."""
    d, hdr = _contract(ref), _contract(HEADER_OF[ref])
    poles = header_poles(HEADER_OF[ref])
    hm = hdr["connection-points"]["mate"]["at"][0]
    pm = d["connection-points"]["mate"]["at"][0]
    for k, w in enumerate(wires(ref)):
        off = d["connection-points"][w]["at"][0] - pm
        assert off == pytest.approx(poles[k] - hm, abs=0.01), (ref, w)
    text = " ".join(d["provenance"]["poles"].split())
    assert f"NUMBERED 1 TO {POLES[ref]} FROM THE LEFT" in text
    if HEADER_OF[ref] == "common/dc-terminal-header-6@1":
        assert "a convention" in text
    else:
        assert f"`pin-1` to `pin-{POLES[ref]}`" in text


def test_the_flange_screws_land_on_the_headers_threaded_inserts():
    d, hdr = _contract(P5F), _contract(HEADER_OF[P5F])
    plug, head = skin(P5F), skin(HEADER_OF[P5F])
    hm = hdr["connection-points"]["mate"]["at"]
    pm = d["connection-points"]["mate"]["at"]
    for screw, insert in (("screw-l", "insert-1"), ("screw-r", "insert-2")):
        sx, sy = float(plug[screw].get("cx")), float(plug[screw].get("cy"))
        ix, iy = float(head[insert].get("cx")), float(head[insert].get("cy"))
        assert sx - pm[0] == pytest.approx(ix - hm[0], abs=0.01)
        assert sy - pm[1] == pytest.approx(iy - hm[1], abs=0.01)
    assert (float(plug["screw-r"].get("cx")) - float(plug["screw-l"].get("cx"))
            == pytest.approx(6 * PITCH))


@EACH
def test_no_mark_is_drawn_on_the_plug(ref):
    """No logo and no lettering: the skin is the outlines its relief builds
    from and nothing else, and none of it is text."""
    root = ET.parse(_skin_path(ref)).getroot()
    drawn = [e for e in root.iter() if e is not root]
    assert sorted(e.get("id") for e in drawn) == sorted(feats(ref))
    assert all(e.tag.split("}")[1] in ("rect", "path", "circle") for e in drawn)


# --- 5. the solids ---------------------------------------------------------------

@EACH
def test_the_solids_chain_from_the_header_face_to_the_stubs(ref):
    """The body starts on the face the header presents and stands 10; every
    wire starts where the body ends and runs 30; an entry floor is below the
    body's face; and nothing else is built but the flanges and their screws."""
    f = feats(ref)
    want = ["body"] + entries(ref) + wires(ref)
    if ref in FLANGED:
        want += ["flange-l", "flange-r", "screw-l", "screw-r"]
    assert sorted(f) == sorted(want)
    assert not f["body"].get("lift") and rear(f["body"]) == pytest.approx(STANDS)
    for w in wires(ref):
        assert float(f[w]["lift"]) == pytest.approx(rear(f["body"]))
        assert f[w]["cyl"] == pytest.approx(STUB)
    for e in entries(ref):
        assert not f[e].get("lift") and 0 < rear(f[e]) < rear(f["body"])
    if ref in FLANGED:
        for side in "lr":
            fl, sc = f[f"flange-{side}"], f[f"screw-{side}"]
            assert not fl.get("lift") and 0 < rear(fl) < rear(f["body"])
            assert float(sc["lift"]) == pytest.approx(rear(fl))
            assert rear(sc) < rear(f["body"])


@EACH
def test_the_plug_stands_the_mated_figure_less_the_header(ref):
    f = feats(ref)
    assert rear(f["body"]) == pytest.approx(22.0 - 12.0)
    # and what is inside the header is less than the nose
    assert LENGTH - rear(f["body"]) == pytest.approx(8.2) and 8.2 < 8.3


@EACH
def test_the_ruling_is_recorded_in_provenance(ref):
    text = " ".join(_contract(ref)["provenance"]["seated-depth"].split())
    assert "MEASURED FROM THE FACE THE HEADER PRESENTS" in text
    assert "22 - 12 = 10" in text and "18.2 - 10 = 8.2" in text
    assert HEADER_OF[ref] in text


@pytest.mark.parametrize("ref", [P2, P5F])
def test_the_header_models_a_well_the_drawing_does_not_give(ref):
    """Fails by design when the header's relief is revised: the plug's
    provenance.seated-depth quotes the two figures and is to be read again.
    Nothing the plug BUILDS follows them."""
    hf = {x["node"]: x for x in _contract(HEADER_OF[ref])["relief"]["features"]}
    assert hf["body"]["out"] == pytest.approx(2.5)
    assert hf["cell-1"]["out"] == pytest.approx(0.8)
    assert hf["body"]["confidence"] == "estimated"
    text = " ".join(_contract(ref)["provenance"]["seated-depth"].split())
    assert "THE HEADER AS MODELLED DISAGREES" in text and "REVISIT" in text
    assert "2.5 proud" in text and "0.8" in text and "1.7 deep" in text


def test_the_six_position_header_states_no_depth():
    """Fails by design when common/dc-terminal-header-6@1 gains a depth or a
    relief: the plug's provenance says it has neither."""
    hdr = _contract(HEADER_OF[P6])
    assert "d" not in hdr["size"] and "relief" not in hdr
    text = " ".join(_contract(P6)["provenance"]["seated-depth"].split())
    assert "THE HEADER AS MODELLED STATES NO DEPTH" in text and "0.3" in text


@EACH
def test_it_says_which_way_is_up_and_which_way_the_wires_leave(ref):
    p = _contract(ref)["provenance"]
    up = " ".join(p["orientation"].split())
    assert "THE BOARD SIDE OF THE HEADER DOWN" in up and HEADER_OF[ref] in up
    assert " ".join(p["form"].split()).startswith("IN-LINE WIRE ENTRY")
    wires_text = " ".join(p["wires"].split())
    assert "ONE STUB OF WIRE PER POLE" in wires_text
    assert "an unwired pole is not expressible" in wires_text
    assert "A COLOUR PER POLE IS NOT EXPRESSIBLE" in " ".join(p["wire-colour"].split())


# --- 6. seated in real headers ------------------------------------------------------

# (plug, device, configuration, view, the host placement, the turn it is placed at)
SEATS = [
    (P5F, "aurcore/ais4001p", "base", "top", "power", 90),
    (P2, "aurcore/ais4001p", "base", "top", "relay", 0),
    (P5F, "aurcore/ais2001", "base", "top", "power", 90),
    (P2, "aurcore/ais2001", "base", "top", "relay", 0),
    (P6, "readylinks/gl-12xb-240d", "base", "rear", "dc-1", 0),
    (P6, "readylinks/gl-12xb-240d", "base", "rear", "dc-2", 0),
]
SEAT_IDS = [f"{s[0].split('/')[1].split('@')[0]}-in-{s[1].split('/')[1]}-{s[4]}" for s in SEATS]
EACH_SEAT = pytest.mark.parametrize("seat", SEATS, ids=SEAT_IDS)


def _render(tmp, device, edit):
    name = device.split("/")[1]
    dev = tmp / name / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    edit(d)
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    o = tmp / name / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB),
                        "--out", str(o)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    return name, o


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    """Every seat in SEATS, one render per device and configuration.

    Returns {(device, config, view): (svg root, parent map, configs.json)}."""
    tmp = tmp_path_factory.mktemp("terminalplugs")
    jobs = {}
    for ref, device, config, _view, host, _turn in SEATS:
        jobs.setdefault((device, config), {})[host] = ref
    out = {}
    for (device, config), occupants in jobs.items():
        def edit(d, config=config, occupants=occupants):
            d["configurations"][config]["occupants"] = dict(occupants)
        name, o = _render(tmp, device, edit)
        configs = json.loads((o / f"{name}.configs.json").read_text())
        for view in {s[3] for s in SEATS if (s[1], s[2]) == (device, config)}:
            root = ET.parse(face_file(o, name, config, view)).getroot()
            out[(device, config, view)] = (root, {c: p for p in root.iter() for c in p}, configs)
    assert len(out) == len({(s[1], s[2], s[3]) for s in SEATS})
    return out


def _seat(seated, seat):
    ref, device, config, view, host_path, _turn = seat
    root, parents, configs = seated[(device, config, view)]
    host = by_path(root, host_path)
    occ = by_path(root, f"{host_path}-occupant")
    assert occ.get("data-ref", "").startswith(ref), occ.get("data-ref")
    assert host.get("data-ref", "").startswith(HEADER_OF[ref]), host.get("data-ref")
    return parents, host, occ, configs


def _nodes(occ, ref):
    got = {}
    for e in occ.iter():
        eid = e.get("id") or ""
        for n in feats(ref):
            if eid == f"{occ.get('id')}--{n}":
                assert n not in got, eid
                got[n] = e
    assert set(got) == set(feats(ref)), sorted(got)
    return got


def _front(parents, el):
    """Where relief.js builds the node's face nearest the viewer: an ABSOLUTE
    `data-z-out`, or a `cyl`'s summed lift plus its length."""
    if el.get("data-z-out") is not None:
        return float(el.get("data-z-out"))
    return lift_of(parents, el) + float(el.get("data-z-cyl"))


def test_the_seats_are_the_placements_they_say_they_are():
    """The premise of the seats, read off the library: each host is that
    header, placed at that turn, and one of the three is placed turned."""
    for ref, device, _config, view, host, turn in SEATS:
        d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
        hit = [p for p in d["views"][view]["components"]["placements"] if p.get("id") == host]
        assert len(hit) == 1 and hit[0]["ref"] == HEADER_OF[ref], (device, host)
        assert int(hit[0].get("rotate") or 0) == turn, (device, host)
    assert {s[5] for s in SEATS} == {0, 90}
    assert {s[0] for s in SEATS} == set(PLUGS)


@EACH_SEAT
def test_it_seats_with_its_mate_on_the_headers_mate(seated, seat):
    parents, host, occ, _ = _seat(seated, seat)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)


def test_the_turned_seats_are_measured_turned(seated):
    """Not a flat pass: the two flanged headers are drawn turned in the
    compiled face, so the turn is measured and not assumed."""
    turned = 0
    for seat in SEATS:
        parents, host, _occ, _ = _seat(seated, seat)
        m = device_matrix(parents, host)
        is_turned = abs(m[0][0] - 1) > EPS or abs(m[1][1] - 1) > EPS
        assert is_turned == (seat[5] != 0), seat
        turned += is_turned
    assert turned == 2


@EACH_SEAT
def test_each_wire_is_over_its_own_contact(seated, seat):
    """In the device frame, on a turned header as on a flat one: `wire-k` is
    centred where the header's k-th contact from its own left is drawn, one
    pitch from the next, on the line through the header's mate."""
    ref = seat[0]
    parents, host, occ, _ = _seat(seated, seat)
    el = _nodes(occ, ref)
    hdr = _contract(HEADER_OF[ref])
    poles = header_poles(HEADER_OF[ref])
    my = hdr["connection-points"]["mate"]["at"][1]
    assert len(poles) == POLES[ref]
    for k, w in enumerate(wires(ref)):
        c = el[w]
        got = device_point(parents, c, (float(c.get("cx")), float(c.get("cy"))))
        want = device_point(parents, host, (poles[k], my))
        assert got == pytest.approx(want, abs=0.01), (w, got, want)


@EACH_SEAT
def test_the_seated_plug_stands_off_by_the_ruling(seated, seat):
    """The compiled depths, in the device frame: the body starts on the face
    the header presents, stands 10 in front of it, and every stub ends 30
    beyond that."""
    ref = seat[0]
    parents, host, occ, _configs = _seat(seated, seat)
    el = _nodes(occ, ref)
    base = lift_of(parents, el["body"])
    assert base - lift_of(parents, host) == pytest.approx(PRESENTS[HEADER_OF[ref]], abs=EPS)
    assert _front(parents, el["body"]) - base == pytest.approx(STANDS, abs=EPS)
    for w in wires(ref):
        assert lift_of(parents, el[w]) - base == pytest.approx(STANDS, abs=EPS)
        assert _front(parents, el[w]) - base == pytest.approx(STANDS + STUB, abs=EPS)


@EACH_SEAT
def test_a_placed_header_publishes_a_slot_that_offers_exactly_its_plug(seated, seat):
    ref, _device, _config, view, pid, _turn = seat
    parents, host, occ, configs = _seat(seated, seat)
    slot = next(c for c in configs["cages"][view] if c["id"] == pid)
    assert slot["kind"] == "connector" and slot["interface"] == IFACE_OF[ref], slot
    assert slot["accepts"] == [ref], slot
    assert slot["default"] is None and slot["occupant"] == ref, slot
    base = lift_of(parents, _nodes(occ, ref)["body"])
    assert slot["lift"] == pytest.approx(base, abs=EPS)
    assert tuple(slot["mate"]) == pytest.approx(
        device_point(parents, host, cage_mate(host)), abs=1e-3)


def test_both_headers_of_a_device_are_slots_of_their_own_kind(seated):
    """One AurCore top face holds a five-position and a two-position header,
    and each offers only its own plug; the ReadyLinks rear holds two
    six-position headers and both are slots."""
    _root, _parents, configs = seated[("aurcore/ais4001p", "base", "top")]
    slots = {c["id"]: c for c in configs["cages"]["top"]}
    assert slots["power"]["accepts"] == [P5F] and slots["relay"]["accepts"] == [P2]
    _root, _parents, configs = seated[("readylinks/gl-12xb-240d", "base", "rear")]
    slots = {c["id"]: c for c in configs["cages"]["rear"]}
    assert slots["dc-1"]["accepts"] == [P6] and slots["dc-2"]["accepts"] == [P6]


@EACH_SEAT
def test_the_seated_plug_builds_right_side_out(seated, seat):
    ref = seat[0]
    parents, _host, occ, _ = _seat(seated, seat)
    el = _nodes(occ, ref)
    raised = 0
    for e in occ.iter():
        if e.get("data-z-out") is not None:
            raised += 1
            assert float(e.get("data-z-out")) - lift_of(parents, e) > EPS, e.get("id")
        elif e.get("data-z-cyl") is not None:
            raised += 1
            assert float(e.get("data-z-cyl")) > EPS, e.get("id")
    assert raised == len(el), (raised, sorted(el))
    # nothing of the plug is a pit or a cavity
    for e in occ.iter():
        assert e.get("data-depth") is None and e.get("data-cavity") is None, e.get("id")


@EACH_SEAT
def test_every_stub_is_the_default_wire_od_and_colour(seated, seat):
    ref = seat[0]
    parents, _host, occ, _ = _seat(seated, seat)
    el = _nodes(occ, ref)
    for w in wires(ref):
        assert _diameter(parents, el[w]) == pytest.approx(WIRE_OD, abs=EPS)
        assert el[w].get("fill") == "#1c1c1c"
    assert el["body"].get("fill") == GREEN


def _diameter(parents, stub):
    """relief.js builds a cyl at radius min(w, h) / 2 of the face box."""
    assert stub.tag.endswith("circle"), stub.tag
    cx, cy, r = (float(stub.get(k)) for k in ("cx", "cy", "r"))
    pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    x0, y0, x1, y1 = box(apply(device_matrix(parents, stub), pts))
    assert x1 - x0 == pytest.approx(y1 - y0, abs=EPS)
    return min(x1 - x0, y1 - y0)


# --- 7. the fields, from a placement ---------------------------------------------

# A placement's attrs set the fields (an occupant carries only a ref): each
# plug placed directly, `mate-to` a real header, with a wire and a body of its
# own. One device carries two of the three.
OVERRIDES = [
    (P5F, "aurcore/ais4001p", "base", "top", "power", 4.0, "#c0392b", "#2b2d30"),
    (P2, "aurcore/ais4001p", "base", "top", "relay", 2.4, "#2a5db0", "#d9822b"),
    (P6, "readylinks/gl-12xb-240d", "base", "rear", "dc-2", 3.4, "#b03a2e", "#1f2124"),
]


@pytest.fixture(scope="module")
def overridden(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("terminalplugfields")
    jobs = {}
    for case in OVERRIDES:
        jobs.setdefault((case[1], case[2], case[3]), []).append(case)
    out = {}
    for (device, config, view), cases in jobs.items():
        def edit(d, view=view, cases=cases):
            places = d["views"][view]["components"]["placements"]
            for ref, _device, _config, _view, host, od, wire, body in cases:
                hits = [p for p in places if p.get("id") == host]
                assert len(hits) == 1 and hits[0]["ref"] == HEADER_OF[ref], hits
                places.append({"ref": ref, "id": f"plug-{host}", "mate-to": host,
                               "attrs": {"wire-od": od, "wire-color": wire,
                                         "body-color": body}})
        name, o = _render(tmp, device, edit)
        root = ET.parse(face_file(o, name, config, view)).getroot()
        for case in cases:
            out[case[0]] = (root, {c: p for p in root.iter() for c in p})
    assert set(out) == set(PLUGS)
    return out


@pytest.mark.parametrize("case", OVERRIDES, ids=[c[0].split("/")[1] for c in OVERRIDES])
def test_a_placements_fields_set_every_wire_and_the_body(overridden, case):
    ref, _device, _config, _view, host_id, od, wire, body = case
    assert WIRE_OD != pytest.approx(od, abs=0.1)
    root, parents = overridden[ref]
    occ, host = by_path(root, f"plug-{host_id}"), by_path(root, host_id)
    assert occ.get("data-ref", "").startswith(ref)
    assert float(occ.get("data-wire-od")) == pytest.approx(od)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS
    assert_same_turn(parents, occ, host)
    el = _nodes(occ, ref)
    for w in wires(ref):
        assert float(el[w].get("r")) * 2 == pytest.approx(od, abs=EPS)
        assert _diameter(parents, el[w]) == pytest.approx(od, abs=EPS)
        assert el[w].get("fill") == wire
    # the body, and the flanges where it has them, take the body colour; the
    # outline follows it by the fixed shade
    painted = ["body"] + (["flange-l", "flange-r"] if ref in FLANGED else [])
    for n in painted:
        assert el[n].get("fill") == body
        assert el[n].get("stroke") == render_mod.stroke_shade(body)
    # and nothing else moved: an entry keeps its floor, a screw its head
    assert el["entry-1"].get("fill") == "#17191c"
    if ref in FLANGED:
        assert float(el["screw-l"].get("r")) == pytest.approx(2.0)
        assert el["screw-l"].get("fill") == "#c9cdd1"
