"""Five generic optics and the MPO-16 plug (docs/pluggables-mpo-bidi-pon-design.md).

    generic/qsfp-mpo@1         a QSFP with one MPO receptacle
    generic/qsfp-dd-mpo16@1    a QSFP-DD with one MPO-16 receptacle
    std/mpo-module-receptacle@1, std/mpo16-module-receptacle@1
                               the MPO mouth as a module carries it: a dark
                               cavity, pinned ferrule, key notch, fibre row
    generic/qsfp-lc-simplex@1  a QSFP with one LC bore in a duplex-shaped shell
    generic/sfp-sc@1           an SFP with one SC opening, long axis horizontal
    generic/sfp-sc-key-up@1    the same module with the SC key slot up
    common/qsfp-dd-pull-tab-type2@1   the handle of a Type 2 QSFP-DD module
    generic/mpo16-plug@1       the sixteen-fibre plug, key offset

What each is, that its head fits the MSA envelope (L121), that its receptacle
is the right part the right way up, that the receptacle is a slot offering the
right plug and dust cap (from a components.json built here by the indexer),
and that each optic seats in a real cage of its family with its plug chained
in it, on a build of a copy of edgecore/agr560.

Nothing here rasterises.
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
from portrayal import lint
from portrayal import render as render_mod
from portrayal.artifacts import face_file
from portrayal.manifest import presented_interface, seat_point
from test_nested_occupants import by_path, cage_mate, device_point, own_mate

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

QSFP_MPO = "generic/qsfp-mpo@1"
QDD_MPO16 = "generic/qsfp-dd-mpo16@1"
QSFP_BIDI = "generic/qsfp-lc-simplex@1"
SFP_SC = "generic/sfp-sc@1"
SFP_SC_UP = "generic/sfp-sc-key-up@1"
SC_BOTH = (SFP_SC, SFP_SC_UP)
TAB2 = "common/qsfp-dd-pull-tab-type2@1"
REC12 = "std/mpo-module-receptacle@1"
REC16 = "std/mpo16-module-receptacle@1"
MPO16 = "generic/mpo16-plug@1"

# optic -> (mates, conforms, receptacle part id, receptacle ref, its rotate,
#           interface presented, what its slot offers)
OPTICS = {
    QSFP_MPO: ("qsfp", "qsfp-module", "mpo", REC12, 0, "mpo",
               {"generic/mpo12-plug@1", "generic/mpo24-plug@1", "common/mpo-dust-cap@2"}),
    QDD_MPO16: ("qsfp-dd", "qsfp-dd-module", "mpo16", REC16, 0, "mpo16",
                {MPO16, "common/mpo16-dust-cap@1"}),
    QSFP_BIDI: ("qsfp", "qsfp-module", "bore", "std/lc-bore@3", 180, "lc",
                {"generic/lc-plug@2", "common/lc-dust-cap@1"}),
    SFP_SC: ("sfp", "sfp-module", "sc", "std/sc-bore@1", 270, "sc",
             {"generic/sc-plug@1", "common/sc-dust-cap@1"}),
    SFP_SC_UP: ("sfp", "sfp-module", "sc", "std/sc-bore@1", 90, "sc",
                {"generic/sc-plug@1", "common/sc-dust-cap@1"}),
}
EACH = pytest.mark.parametrize("ref", sorted(OPTICS))

# optic -> (above the body, below it, length outside the cage, width)
HEADS = {
    QSFP_MPO: (1.4, 1.4, 20.0, 18.35),
    QDD_MPO16: (3.13, 1.5, 31.9, 18.35),
    QSFP_BIDI: (2.2, 1.5, 19.2, 18.35),
    SFP_SC: (2.1, 1.4, 20.0, 14.0),
    SFP_SC_UP: (2.1, 1.4, 20.0, 14.0),
}
GREY = "#6f6f6f"

# optic -> (the agr560 cage it is seated in, the plug chained in it). Two of
# the cages are drawn at rotate 180 (the lower row of a stack), so the chain
# is held on a turned host as well as an upright one.
SEATS = {
    QSFP_MPO: ("qsfp28-0", "generic/mpo12-plug@1"),
    QDD_MPO16: ("qsfpdd-1", MPO16),
    QSFP_BIDI: ("qsfp28-3", "generic/lc-plug@2"),
    SFP_SC: ("port-0", "generic/sc-plug@1"),
    SFP_SC_UP: ("port-2", "generic/sc-plug@1"),
}
TURNED = {"qsfpdd-1", "qsfp28-3"}
DEVICE = "edgecore/agr560"


def path(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return LIB / f"components/{ns}/{name}/v{major}"


def doc(ref):
    return yaml.safe_load((path(ref) / "contract.yaml").read_text())


def skin(ref):
    return ET.parse(path(ref) / "skins/default.svg").getroot()


def node(ref, nid):
    hits = [e for e in skin(ref).iter() if e.get("id") == nid]
    assert len(hits) == 1, (ref, nid, len(hits))
    return hits[0]


def standards():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def part(ref, pid):
    return next(p for p in doc(ref)["parts"] if p["id"] == pid)


# --- what each optic is ------------------------------------------------------

@EACH
def test_it_is_a_generic_transceiver_of_its_family(ref):
    d = doc(ref)
    mates, conforms = OPTICS[ref][:2]
    assert (d["kind"], d["class"], d["behaviour"]) == ("component", "transceiver", "occupies")
    assert d["mates"] == mates and d["conforms"] == conforms
    std = standards()[conforms]
    assert (d["size"]["w"], d["size"]["h"], d["size"]["d"]) == (std["w"], std["h"], std["depth"])


@EACH
def test_a_generic_states_no_rate_reach_wavelength_or_wattage(ref):
    d = doc(ref)
    assert not set(d["attrs"]) & set(lint.GENERIC_FORBIDDEN_ATTRS)
    with lint.collecting() as got:
        lint.lint_component_generic(path(ref) / "contract.yaml", d)
    assert not got.errors, got.errors


@EACH
def test_the_head_fits_the_msa_envelope(ref):
    """L121, and the figures it is run on: above, below, length and width as
    the contract's `head` states them, measured the way the rule measures."""
    d = doc(ref)
    above, below, length, width = HEADS[ref]
    head = d["head"]
    assert -head["at"][1] == pytest.approx(above)
    assert head["at"][1] + head["size"]["h"] - d["size"]["h"] == pytest.approx(below)
    assert head["size"]["d"] == pytest.approx(length)
    assert head["size"]["w"] == pytest.approx(width)
    with lint.collecting() as got:
        lint.lint_component_head(path(ref) / "contract.yaml", d)
    assert not [e for e in got.errors + got.warnings if "[L121]" in e], got.errors


def test_only_the_sc_head_exceeds_and_only_in_length():
    """Width, above and below of the SC head sit AT the sfp-module maxima; its
    20.0 length is over the recommended 10.0 and is listed with its source.
    The three QSFP heads list nothing, and the QSFP-DD one is a Type 2."""
    env = standards()["sfp-module"]["head"]
    for ref in SC_BOTH:
        head = doc(ref)["head"]
        assert (head["size"]["w"], -head["at"][1]) == (env["w-max"], env["above-max"])
        assert [e["dimension"] for e in head["exceeds"]] == ["length"]
        assert head["exceeds"][0]["source"]
    for ref in (QSFP_MPO, QDD_MPO16, QSFP_BIDI):
        assert not doc(ref)["head"].get("exceeds"), ref
    assert doc(QDD_MPO16)["head"]["type"] == 2
    assert "type" not in doc(QSFP_MPO)["head"]


@EACH
def test_the_head_node_is_the_skins_first_child_and_draws_the_head(ref):
    """`body` carries the head's box, and it is the skin's FIRST drawing child:
    render.py never raises the first child, so the face art drawn after it is
    not buried under the nose in 2D or 3D."""
    d = doc(ref)
    assert d["head"]["node"] == "body"
    first = [c for c in skin(ref) if c.tag.rsplit("}", 1)[-1] not in ("title", "defs", "style")][0]
    assert first.get("id") == "body" and first.tag.endswith("rect")
    box = [float(first.get(k)) for k in ("x", "y", "width", "height")]
    want = [*d["head"]["at"], d["head"]["size"]["w"], d["head"]["size"]["h"]]
    assert all(abs(a - b) <= lint.HEAD_NODE_TOL for a, b in zip(box, want)), (box, want)


# --- the receptacle ----------------------------------------------------------

@EACH
def test_the_receptacle_is_the_right_part_the_right_way_up(ref):
    _, _, pid, want, rotate, iface, _ = OPTICS[ref]
    p = part(ref, pid)
    assert p["ref"] == want
    assert (p.get("rotate") or 0) == rotate
    core = doc(want)
    assert core["interface"] == iface
    # exactly one composed part presents an interface, so the optic forwards it
    assert [q["id"] for q in doc(ref)["parts"] if doc(q["ref"]).get("interface")] == [pid]


@EACH
def test_the_receptacle_stands_on_the_front_of_the_head(ref):
    """`out` is absolute and `lift` is summed: the nose stands `head.size.d`
    out, and every composed part is lifted to exactly that plane, so the
    opening's cavity is cut from the nose front and not from the cage face
    20 mm behind it. The module's only `out` is the nose itself."""
    d = doc(ref)
    depth = d["head"]["size"]["d"]
    feats = {f["node"]: f for f in d["relief"]["features"]}
    assert feats["body"]["out"] == depth
    assert [n for n, f in feats.items() if f.get("out") is not None] == ["body"]
    for p in d["parts"]:
        assert p["lift"] == depth, (ref, p["id"])


def test_the_mpo_receptacles_are_key_up():
    """Key-up is the placement: the receptacle unrotated, its key notch in the
    top wall, with the plugs' key ribs drawn on top unrotated (a seat turns
    an occupant by its host's turn and nothing else)."""
    for ref, pid in ((QSFP_MPO, "mpo"), (QDD_MPO16, "mpo16")):
        assert not part(ref, pid).get("rotate")
    for plug in ("generic/mpo12-plug@1", MPO16):
        key = node(plug, "key")
        assert float(key.get("y")) + float(key.get("height")) < doc(plug)["size"]["h"] / 2


def test_the_single_lc_bore_is_in_the_left_bay_keyway_up():
    """The duplex TX position of generic/qsfp-lc@2, left of the module centre,
    with the right bay drawn empty."""
    tx = next(p for p in doc("generic/qsfp-lc@2")["parts"] if p["id"] == "tx")
    bore = part(QSFP_BIDI, "bore")
    assert (bore["at"], bore["rotate"]) == (tx["at"], 180)
    d = doc(QSFP_BIDI)
    centre = d["connection-points"]["optical"]["at"]
    assert centre == [6.05, 4.9] and centre[0] < d["size"]["w"] / 2
    # the keyway (tongue) end of the bore lands ABOVE the ferrule
    core = doc("std/lc-bore@3")
    tongue = seat_point(bore["at"], core["size"], 180, [2.35, core["size"]["h"]])
    assert tongue[1] < centre[1]
    assert len([p for p in d["parts"] if p["ref"].startswith("std/lc-bore")]) == 1
    empty = node(QSFP_BIDI, "empty-bay")
    assert empty.get("d").split()[1] == "10.98"      # the RX position, x 9.95 + 1.03


@pytest.mark.parametrize("ref,down", [(SFP_SC, True), (SFP_SC_UP, False)])
def test_the_sc_opening_lies_across_with_its_key_slot_on_its_side(ref, down):
    """Key slot at the bottom on generic/sfp-sc@1 (the 6COM end view) and at
    the top on generic/sfp-sc-key-up@1 (the Superxon end view); the opening
    itself is in the same place on both."""
    core = doc("std/sc-bore@1")
    p = part(ref, "sc")
    size = core["size"]
    mate = seat_point(p["at"], size, p["rotate"], core["connection-points"]["mate"]["at"])
    assert mate == pytest.approx(doc(ref)["connection-points"]["optical"]["at"])
    assert mate == pytest.approx([6.775, 3.7])
    # the 9.0 axis of the opening runs in x once turned
    a = seat_point(p["at"], size, p["rotate"], [4.64, 0.0])
    b = seat_point(p["at"], size, p["rotate"], [4.64, 9.0])
    assert abs(a[0] - b[0]) == pytest.approx(9.0) and a[1] == pytest.approx(b[1])
    # the key slot is the part's left wall unrotated
    slot = seat_point(p["at"], size, p["rotate"], [0.0, 4.5])
    assert slot[0] == pytest.approx(mate[0])
    assert (slot[1] > mate[1]) == down
    assert abs(slot[1] - mate[1]) == pytest.approx(4.64)
    # and the slot is inside the head
    head = doc(ref)["head"]
    assert head["at"][1] <= slot[1] <= head["at"][1] + head["size"]["h"]


def _strip(d):
    return {k: v for k, v in d.items() if k not in ("name", "description", "provenance")}


def test_the_two_sc_parts_differ_only_in_the_receptacles_rotation():
    """Two vendors draw the SC key on opposite sides, so there are two parts,
    and the key direction is the whole of the difference: the same head, the
    same bail, the same fields, the same opening centre. A quarter turn about
    the part's own centre moves its mate, so `at` follows the `rotate` - by
    exactly what keeps the opening where it was."""
    down, up = _strip(doc(SFP_SC)), _strip(doc(SFP_SC_UP))
    pd, pu = down.pop("parts"), up.pop("parts")
    assert down == up
    assert len(pd) == len(pu) == 1
    assert (pd[0]["rotate"], pu[0]["rotate"]) == (270, 90)
    rest = lambda q: {k: v for k, v in q.items() if k not in ("rotate", "at")}
    assert rest(pd[0]) == rest(pu[0])
    size = doc("std/sc-bore@1")["size"]
    centre = lambda q: seat_point(q["at"], size, q["rotate"], [4.64, 4.5])
    assert centre(pd[0]) == pytest.approx(centre(pu[0]))
    # each names the other, and the vendor its own key direction follows
    kd, ku = doc(SFP_SC)["provenance"]["key"], doc(SFP_SC_UP)["provenance"]["key"]
    assert "6COM END VIEW" in kd and SFP_SC_UP in kd
    assert "SUPERXON END VIEW" in ku and SFP_SC in ku
    # the skins differ only in where the label is printed: clear of the slot
    art = lambda ref: {e.get("id"): dict(e.attrib) for e in skin(ref).iter() if e.get("id")}
    ad, au = art(SFP_SC), art(SFP_SC_UP)
    assert set(ad) == set(au)
    assert [k for k in ad if ad[k] != au[k]] == ["label"]
    assert {k for k in ad["label"] if ad["label"][k] != au["label"][k]} == {"y"}


@pytest.mark.parametrize("ref", SC_BOTH)
def test_the_sc_bail_is_a_field_painted_bar_at_the_bottom(ref):
    d = doc(ref)
    bail = node(ref, "bail")
    assert bail.get("data-fill-from") == "latch-color"
    y, h = float(bail.get("y")), float(bail.get("height"))
    assert y > d["size"]["h"] and y + h <= d["head"]["at"][1] + d["head"]["size"]["h"]
    feat = next(f for f in d["relief"]["features"] if f["node"] == "bail")
    assert "color" not in feat                          # L73: a field paints it
    assert feat["lift"] == d["head"]["size"]["d"] and feat["bar"] == pytest.approx(h)


def test_every_generic_tab_defaults_to_grey():
    """#773: an MPO face is multimode SR4/SR8 AND single-mode PSM4/DR4/DR8,
    so beige (850 nm under SFF-8679 7.2) is a wrapper's claim, not a generic's."""
    assert doc(QSFP_MPO)["fields"]["latch-color"]["default"] == GREY
    assert doc(QDD_MPO16)["fields"]["latch-color"]["default"] == GREY
    assert doc(QSFP_BIDI)["fields"]["latch-color"]["default"] == GREY
    assert doc(SFP_SC)["fields"]["latch-color"]["default"] == GREY
    assert doc(SFP_SC_UP)["fields"]["latch-color"]["default"] == GREY
    assert doc(TAB2)["fields"]["latch-color"]["default"] == GREY


# --- the slots, from a components.json built here ----------------------------

@pytest.fixture(scope="module")
def comps():
    built = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in built["components"]}
    assert got, "the indexer published no component at all"
    return got


@EACH
def test_the_receptacle_is_a_slot_offering_its_plug_and_cap(comps, ref):
    _, _, pid, _, rotate, iface, accepts = OPTICS[ref]
    slot = comps[ref].get("presents")
    assert slot, f"{ref} presents nothing, so the explorer cannot plug it"
    assert (slot["kind"], slot["interface"]) == ("connector", iface)
    assert set(slot["accepts"]) == accepts, slot["accepts"]
    d = doc(ref)
    assert slot["lift"] == d["head"]["size"]["d"]
    assert slot["mate"] == pytest.approx(d["connection-points"]["optical"]["at"])
    assert (slot.get("rotate") or 0) == rotate
    assert comps[ref]["head"]["size"]["d"] == d["head"]["size"]["d"]


def _adapter_offers(ref):
    """What a placement of a panel adapter offers: a wrapper's aperture is the
    wrapper's slot (caps design, P2), published by whatever places it."""
    libs = [str(LIB)]
    slot = render_mod.slot_entry({"ref": ref, "id": "a", "at": [0, 0]},
                                 render_mod.Library(libs), render_mod._pluggable_families(),
                                 render_mod._connector_registry(),
                                 render_mod._pluggable_candidates(libs))
    assert slot is not None, f"{ref} is not a slot"
    return slot["interface"], set(slot["accepts"])


def test_the_mpo16_plug_is_offered_by_mpo16_openings_only(comps):
    """The offset key: an MPO-12 adapter does not offer the sixteen-fibre plug,
    and an MPO-16 one offers no twelve- or twenty-four-fibre plug."""
    assert doc(MPO16)["mates"] == "mpo16"
    iface, twelve = _adapter_offers("common/mpo-adapter@2")
    assert iface == "mpo" and "generic/mpo12-plug@1" in twelve
    assert MPO16 not in twelve
    assert MPO16 not in comps[QSFP_MPO]["presents"]["accepts"]
    iface, sixteen = _adapter_offers("common/mpo16-adapter@1")
    assert iface == "mpo16" and MPO16 in sixteen
    others = {"generic/mpo12-plug@1", "generic/mpo24-plug@1"}
    assert not others & (sixteen | set(comps[QDD_MPO16]["presents"]["accepts"]))
    # and across the whole index: every slot offering it presents mpo16
    seen = 0
    for ref, entry in comps.items():
        for slot in [entry.get("presents")] + (entry.get("cages") or []):
            if slot and MPO16 in slot["accepts"]:
                seen += 1
                assert slot["interface"] == "mpo16", (ref, slot["interface"])
    assert seen, "no published slot offers the MPO-16 plug"


# --- the MPO-16 plug ---------------------------------------------------------

def test_the_mpo16_plug_is_a_port_with_the_mpo12_envelope():
    d, twelve = doc(MPO16), doc("generic/mpo12-plug@1")
    assert d["class"] == "port" and "behaviour" not in d
    assert d["conforms"] == "mpo16-plug" and d["interface"] == "mpo16-plug"
    assert d["size"] == twelve["size"] == {"w": 12.5, "h": 7.6}
    assert "d" not in d["size"]
    std = standards()["mpo16-plug"]
    assert (std["w"], std["h"], std["confidence"]) == (12.5, 7.6, "drawing")
    assert d["optical"]["positions"] == 16


def test_the_mpo16_key_is_offset_and_the_mpo12_key_is_not():
    def key(ref):
        k = node(ref, "key")
        return float(k.get("x")), float(k.get("width")), float(k.get("y")), float(k.get("height"))
    x, w, y, h = key(MPO16)
    assert (w, h, y) == (3.65, 0.68, 0.4)
    assert x + w / 2 - 12.5 / 2 == pytest.approx(1.12)
    x12, w12, _, _ = key("generic/mpo12-plug@1")
    assert x12 + w12 / 2 - 12.5 / 2 == pytest.approx(0.0, abs=0.005)


def test_the_mpo16_ferrule_has_sixteen_fibres_between_pins_5_3_apart():
    d = doc(MPO16)
    xs = [d["elements"][str(n)]["at"][0] + 0.075 for n in range(1, 17)]
    assert all(a - b == pytest.approx(0.25) for a, b in zip(xs, xs[1:]))    # fibre 1 at the right
    assert (xs[0] + xs[-1]) / 2 == pytest.approx(6.25) and xs[0] - xs[-1] == pytest.approx(3.75)
    left, right = node(MPO16, "pin-bore-l"), node(MPO16, "pin-bore-r")
    assert float(right.get("cx")) - float(left.get("cx")) == pytest.approx(5.3)
    assert (float(left.get("cx")) + float(right.get("cx"))) / 2 == pytest.approx(6.25)
    for n in range(1, 17):
        assert node(MPO16, str(n)).get("fill") == "none"


def test_the_mpo16_cable_point_is_the_mpo12_plugs():
    cps, twelve = doc(MPO16)["connection-points"], doc("generic/mpo12-plug@1")["connection-points"]
    assert cps == twelve
    assert cps["cable"] == {"at": [6.25, 3.8], "direction": "rear", "on": "body"}
    feats = doc(MPO16)["relief"]["features"]
    assert [f["node"] for f in feats] == ["body"] and "color" not in feats[0]
    assert doc(MPO16)["interface-at"] == "boot"


# --- seated in real cages, the plug chained in -------------------------------

@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    """edgecore/agr560, which has SFP, QSFP and QSFP-DD cages on one face,
    copied and rendered with each optic in a cage and its plug in the optic."""
    tmp = tmp_path_factory.mktemp("mpo-bidi-pon")
    name = DEVICE.split("/")[1]
    dev = tmp / name / "device.yaml"
    shutil.copytree(LIB / "devices" / DEVICE, dev.parent)
    d = yaml.safe_load(dev.read_text())
    occ = {}
    for ref, (cage, plug) in SEATS.items():
        occ[cage] = ref
        occ[f"{cage}-occupant"] = plug
    d["configurations"]["optics"] = {"kind": "example", "power": "ac",
                                     "description": "test", "occupants": occ}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / "out"
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(face_file(out, name, "optics", "front")).getroot()
    return root, {c: p for p in root.iter() for c in p}


@EACH
def test_it_seats_in_a_real_cage_with_its_plug_in_it(seated, ref):
    root, parents = seated
    cage_id, plug = SEATS[ref]
    cage = by_path(root, cage_id)
    optic = by_path(root, f"{cage_id}-occupant")
    occ = by_path(root, f"{cage_id}-occupant-occupant")
    assert optic.get("data-ref", "").startswith(ref)
    assert occ.get("data-ref", "").startswith(plug)
    assert occ.get("data-for") == f"{cage_id}-occupant"
    assert ("rotate(180" in (optic.get("transform") or "")) == (cage_id in TURNED)
    # the optic's mate is on the cage's
    cx, cy = device_point(parents, cage, cage_mate(cage))
    ox, oy = device_point(parents, optic, own_mate(optic))
    assert abs(cx - ox) < 1e-6 and abs(cy - oy) < 1e-6
    # the plug's mate is on the point the optic presents: its receptacle
    _, at, lift = presented_interface(doc(ref), doc)
    rx, ry = device_point(parents, optic, at)
    px, py = device_point(parents, occ, own_mate(occ))
    assert abs(rx - px) < 1e-6 and abs(ry - py) < 1e-6
    # and it stands on the front of the head, not on the cage face
    assert lift == doc(ref)["head"]["size"]["d"]
    assert float(occ.get("data-z-lift")) == pytest.approx(lift)


def test_the_seated_tabs_are_grey(seated):
    """No generic pins a colour, so every seated tab wears the neutral grey
    (#773); a wrapper that states a wavelength states its colour."""
    root, _ = seated
    for ref, want in ((QSFP_MPO, GREY), (QDD_MPO16, GREY), (QSFP_BIDI, GREY)):
        tab = by_path(root, f"{SEATS[ref][0]}-occupant/tab")
        grip = [e for e in tab.iter() if (e.get("id") or "").endswith("--grip")]
        assert len(grip) == 1 and grip[0].get("fill") == want, (ref, grip[0].get("fill"))


def test_a_seated_plug_keeps_its_key_on_the_receptacles_key_side(seated):
    """The SC plug's key is drawn left, as the bore's slot is; seated in the
    turned bore both are at the module bottom. The MPO-16 plug's key stays on
    the pull-tab side, offset toward the same side in the module's own frame
    whichever way up the cage is drawn."""
    root, parents = seated
    for ref, down in ((SFP_SC, True), (SFP_SC_UP, False)):
        sc = by_path(root, f"{SEATS[ref][0]}-occupant-occupant")
        ferrule = device_point(parents, sc, own_mate(sc))
        key = device_point(parents, sc, [0.45, 4.5])
        assert (key[1] > ferrule[1]) == down and abs(key[0] - ferrule[0]) < 1e-6
    cage = SEATS[QDD_MPO16][0]
    optic = by_path(root, f"{cage}-occupant")
    plug = by_path(root, f"{cage}-occupant-occupant")
    k = device_point(parents, plug, [6.25 + 1.12, 0.74])
    top = device_point(parents, optic, [9.175 + 1.12, 0.0])
    bottom = device_point(parents, optic, [9.175 + 1.12, 8.5])
    assert abs(k[0] - top[0]) < 1e-6
    assert abs(k[1] - top[1]) < abs(k[1] - bottom[1])


# --- the Type 2 QSFP-DD pull tab ---------------------------------------------

def test_the_type2_tab_is_a_latch_with_the_drawn_figures():
    """Reach 37.1 from the nose front (JPC p2: 117.6 less 80.5), 18.35 wide
    (printed), arms 2.25 wide at the side edges, a post 10.0 tall at each arm
    root, a 3.2 strap and an 8.7 grip plate (scaled)."""
    d = doc(TAB2)
    assert d["class"] == "latch" and "behaviour" not in d and "mates" not in d
    assert d["size"] == {"w": 18.35, "h": 10.0}
    assert d["size-confidence"] == {"w": "datasheet", "h": "estimated"}
    e = d["elements"]
    assert set(e) == {"grip"} | {f"{n}-{s}{k}" for s in "lr" for n, k in
                                 (("riser", ""), ("arm", ""), ("arm", "-2"), ("arm", "-3"))}
    assert e["grip"] == {"at": [0.0, 0.0], "size": [18.35, 3.2], "class": "latch"}
    for side, x in (("l", 0.0), ("r", 16.1)):
        for nid, h in ((f"riser-{side}", 10.0), (f"arm-{side}-2", 8.3),
                       (f"arm-{side}-3", 4.9), (f"arm-{side}", 3.2)):
            assert e[nid]["at"] == [x, 0.0] and e[nid]["size"] == [2.25, h], nid
    feats = {f["node"]: f for f in d["relief"]["features"]}
    assert set(feats) == set(e)
    assert feats["grip"]["out"] == 37.1 and feats["grip"]["lift"] == pytest.approx(37.1 - 8.7)
    assert feats["grip"]["confidence"] == "datasheet"
    assert max(f["out"] for f in feats.values()) == 37.1
    long_tab = doc("common/qsfp-pull-tab@2")
    assert max(f["out"] for f in long_tab["relief"]["features"]) == 49.8


def test_the_type2_tab_is_boxes_end_to_end_with_no_shared_volume():
    """Along each arm every box starts where the one before it ends (`lift`
    is where it starts, `out` where it ends), from the nose front to the tip:
    no gap, no overlap, nothing built inside out."""
    feats = {f["node"]: f for f in doc(TAB2)["relief"]["features"]}
    for side in "lr":
        chain = [f"riser-{side}", f"arm-{side}-2", f"arm-{side}-3", f"arm-{side}", "grip"]
        at = 0.0
        for nid in chain:
            f = feats[nid]
            assert (f.get("lift") or 0.0) == pytest.approx(at), nid
            assert f["out"] > at, nid
            at = f["out"]
        assert at == 37.1


def test_the_type2_tab_is_painted_by_its_field_and_states_no_relief_colour():
    d = doc(TAB2)
    for nid in d["elements"]:
        el = node(TAB2, nid)
        assert el.get("data-fill-from") == "latch-color", nid
        assert el.get("data-stroke-derive") == "latch-color", nid
    assert not [f["node"] for f in d["relief"]["features"] if "color" in f]     # L73
    # farthest from the viewer first, the grip last
    order = [c.get("id") for c in skin(TAB2) if c.get("id")]
    assert order[0].startswith("riser") and order[-1] == "grip"


def test_the_sr8_optic_composes_the_type2_tab_on_its_nose():
    tab = part(QDD_MPO16, "tab")
    assert tab == {"ref": TAB2, "id": "tab", "at": [0.0, -3.13], "lift": 31.9}
    d = doc(QDD_MPO16)
    assert tab["at"][1] == d["head"]["at"][1]                   # top level with the nose top
    assert doc(TAB2)["size"]["w"] == d["size"]["w"]             # arms on the side edges
    assert "known-wrong" not in json.dumps(d["provenance"]).lower()
    # the LC QSFP-DD keeps the Type 1 handle on its Type 1 head
    lc = doc("generic/qsfp-dd-lc@2")
    assert [p["ref"] for p in lc["parts"] if p["id"] == "tab"] == ["common/qsfp-pull-tab@2"]


def test_the_seated_sr8_stands_69_out_and_is_built_right_side_out(seated):
    """The 3D extents, read off the compiled relief: the nose front 31.9 from
    the cage face, the handle tip 69.0 (JPC p2: 117.6 to the hard stop less
    48.61), every box of the handle in front of the nose, each one's start
    behind its own end, and the receptacle cavity cut from the nose front."""
    root, parents = seated
    optic = by_path(root, f"{SEATS[QDD_MPO16][0]}-occupant")
    oid = optic.get("id")
    raised = {e.get("id")[len(oid) + 2:]: e for e in optic.iter()
              if e.get("data-z-out") and (e.get("id") or "").startswith(oid + "--")}
    assert float(raised["body"].get("data-z-out")) == pytest.approx(31.9)
    tab = {k: v for k, v in raised.items() if k.startswith("tab--")}
    assert len(tab) == 9
    assert max(float(e.get("data-z-out")) for e in raised.values()) == pytest.approx(69.0)
    assert float(tab["tab--grip"].get("data-z-out")) == pytest.approx(117.6 - 48.61, abs=0.05)
    group = by_path(root, f"{SEATS[QDD_MPO16][0]}-occupant/tab")
    assert float(group.get("data-z-lift")) == pytest.approx(31.9)
    for name, e in tab.items():
        start = 31.9 + float(e.get("data-z-lift") or 0)
        end = float(e.get("data-z-out"))
        assert 31.9 <= start < end <= 69.0 + 1e-6, (name, start, end)
        assert e.get("data-z-color") is None, name
    mouth = by_path(root, f"{SEATS[QDD_MPO16][0]}-occupant/mpo16")
    assert float(mouth.get("data-z-lift")) == pytest.approx(31.9)
    assert float(mouth.get("data-depth")) > 0


# --- the module-side MPO receptacles -----------------------------------------

# receptacle -> (interface, fibres, key offset from the centreline, pin pitch,
#                ferrule window, the panel opening it shares a mouth with,
#                the plug whose key and fibres it takes)
RECEPTACLES = {
    REC12: ("mpo", 12, 0.0, 4.6, (6.10, 2.50), "std/mpo@2", "generic/mpo12-plug@1"),
    REC16: ("mpo16", 16, 1.12, 5.3, (6.36, 2.46), "std/mpo16@1", MPO16),
}
EACH_REC = pytest.mark.parametrize("ref", sorted(RECEPTACLES))
CENTRE = (6.45, 4.0)


def _num(el, *keys):
    return [float(el.get(k)) for k in keys]


@EACH_REC
def test_a_module_receptacle_is_its_panel_openings_mouth_and_interface(ref):
    iface, _, _, _, _, twin, _ = RECEPTACLES[ref]
    d, t = doc(ref), doc(twin)
    assert (d["class"], d["interface"], d["conforms"]) == ("port", iface, "mpo-adapter")
    assert d["interface"] == t["interface"]
    assert d["size"] == t["size"]                       # the optics' layout does not move
    assert d["connection-points"] == t["connection-points"]
    assert d["connection-points"]["mate"]["at"] == list(CENTRE)
    assert "behaviour" not in d and "mates" not in d


@EACH_REC
def test_the_key_notch_is_at_the_top_centred_or_offset(ref):
    """Centred on the MPO-12 receptacle; 1.12 right of the centreline on the
    MPO-16 one, looking in - the same side the seated plug's key is drawn on,
    and wide enough to take that key with the opening's 0.2 a side."""
    _, _, offset, _, _, _, plug = RECEPTACLES[ref]
    x, y, w, h = _num(node(ref, "keyway"), "x", "y", "width", "height")
    assert x + w / 2 - CENTRE[0] == pytest.approx(offset)
    assert y + h < CENTRE[1] / 2                           # in the top wall
    kx, ky, kw, kh = _num(node(plug, "key"), "x", "y", "width", "height")
    # the plug seats centre on centre: its frame is 0.2 inside this one
    assert kx + 0.2 >= x and kx + kw + 0.2 <= x + w + 1e-9
    assert ky + 0.2 >= y and ky + kh + 0.2 <= y + h + 1e-9
    assert w == pytest.approx(kw + 0.4)


@EACH_REC
def test_the_fibres_are_inked_dots_at_true_pitch_numbered_as_the_seated_plug(ref):
    """One row of dots 0.125 across at 0.25 pitch, centred on the ferrule.
    Looking into the receptacle, position 1 is at the right: the mirror of a
    plug's own end face, and the side the library draws a seated plug's fibre
    1 on, so position n is under the seated plug's fibre n."""
    _, n, _, _, _, _, plug = RECEPTACLES[ref]
    d = doc(ref)
    assert d["optical"] == {"positions": n}
    fibres = {k: v for k, v in d["elements"].items() if v["class"] == "fibre"}
    assert sorted(fibres, key=int) == [str(i) for i in range(1, n + 1)]
    xs = []
    for i in range(1, n + 1):
        el = node(ref, str(i))
        cx, cy, r = _num(el, "cx", "cy", "r")
        assert el.tag.endswith("circle") and r == 0.0625 and cy == CENTRE[1]
        assert el.get("fill") not in (None, "none")                 # real ink
        assert fibres[str(i)]["at"] == pytest.approx([cx - r, cy - r])
        assert fibres[str(i)]["size"] == [0.125, 0.125]
        xs.append(cx)
    assert all(a - b == pytest.approx(0.25) for a, b in zip(xs, xs[1:]))
    assert (xs[0] + xs[-1]) / 2 == pytest.approx(CENTRE[0]) and xs[0] > xs[-1]
    pe = doc(plug)["elements"]
    for i in range(1, n + 1):
        px = pe[str(i)]["at"][0] + pe[str(i)]["size"][0] / 2 + 0.2
        assert px == pytest.approx(xs[i - 1]), i
    # no lane assignment: a generic states none
    assert not {"tx", "rx", "lanes", "unused"} & set(d["optical"])


@EACH_REC
def test_the_ferrule_and_its_two_pins_are_drawn(ref):
    _, n, _, pitch, (fw, fh), _, _ = RECEPTACLES[ref]
    x, y, w, h = _num(node(ref, "ferrule"), "x", "y", "width", "height")
    assert (w, h) == (fw, fh)
    assert (x + w / 2, y + h / 2) == pytest.approx(CENTRE)
    left, right = node(ref, "pin-l"), node(ref, "pin-r")
    lx, rx = float(left.get("cx")), float(right.get("cx"))
    assert rx - lx == pytest.approx(pitch) and (lx + rx) / 2 == pytest.approx(CENTRE[0])
    for pin in (left, right):
        assert pin.tag.endswith("circle") and float(pin.get("cy")) == CENTRE[1]
        assert x < float(pin.get("cx")) - float(pin.get("r"))
        assert float(pin.get("cx")) + float(pin.get("r")) < x + w
    # the pins flank the fibre row
    assert lx < CENTRE[0] - (n - 1) * 0.125 and rx > CENTRE[0] + (n - 1) * 0.125


@EACH_REC
def test_the_cavity_is_a_recess_with_the_ferrule_standing_in_it(ref):
    """A cavity, not a slab: `relief.cavity` on the opening, no `out` anywhere,
    the ferrule a `top` standing up from the floor short of the mouth and the
    pins proud of the ferrule by the printed figure, still inside the mouth."""
    d = doc(ref)
    rel = d["relief"]
    assert rel["cavity"] == "opening" and d["elements"]["opening"]["class"] == "cutout"
    feats = {f["node"]: f for f in rel["features"]}
    assert set(feats) == {"ferrule", "pin-l", "pin-r"}
    assert not [f for f in feats.values() if set(f) & {"out", "lift", "cyl", "bar"}]
    depth = d["size"]["d"]
    assert 0 < feats["ferrule"]["top"] < feats["pin-l"]["top"] == feats["pin-r"]["top"] < depth
    proud = {REC12: 1.9, REC16: 1.8}[ref]
    assert feats["pin-l"]["top"] - feats["ferrule"]["top"] == pytest.approx(proud)
    # the opening is the skin's first child, so nothing it draws is under it
    first = [c for c in skin(ref) if c.get("id")][0]
    assert first.get("id") == "opening"


def test_the_panel_adapters_keep_the_open_sleeve():
    assert [q["ref"] for q in doc("common/mpo-adapter@2")["parts"]] == ["std/mpo@2"]
    assert [q["ref"] for q in doc("common/mpo16-adapter@1")["parts"]] == ["std/mpo16@1"]
    for ref in (REC12, REC16):
        assert "sleeve" not in (path(ref) / "skins/default.svg").read_text().split("-->", 1)[1]


def test_the_module_receptacles_offer_what_the_panel_openings_offer(comps):
    """The slots did not change: the optic's accept list is the panel
    adapter's for the same interface."""
    for optic, adapter in ((QSFP_MPO, "common/mpo-adapter@2"), (QDD_MPO16, "common/mpo16-adapter@1")):
        iface, offers = _adapter_offers(adapter)
        slot = comps[optic]["presents"]
        assert slot["interface"] == iface
        assert set(slot["accepts"]) == offers == OPTICS[optic][6]


@pytest.mark.parametrize("ref", [QSFP_MPO, QDD_MPO16])
def test_a_seated_optics_fibres_are_addressable_and_its_cavity_is_right_side_out(seated, ref):
    """Fibre n of the receptacle is at `<cage>-occupant/<part>/n`. The cavity
    is cut from the nose front (its lift is the head's length), the ferrule
    and pins stand up from its floor without reaching the mouth, and nothing
    in the receptacle stands out over it. A seated plug's fibre n lies on
    receptacle position n."""
    root, parents = seated
    cage, _ = SEATS[ref]
    pid, n = OPTICS[ref][2], doc(OPTICS[ref][3])["optical"]["positions"]
    mouth = by_path(root, f"{cage}-occupant/{pid}")
    depth = float(mouth.get("data-depth"))
    assert mouth.get("data-cavity") == "opening" and depth == 9.0
    assert float(mouth.get("data-z-lift")) == doc(ref)["head"]["size"]["d"]
    inside = list(mouth.iter())
    assert not [e.get("id") for e in inside if e.get("data-z-out")]
    tops = {e.get("id").rsplit("--", 1)[1]: float(e.get("data-z-top"))
            for e in inside if e.get("data-z-top")}
    assert set(tops) == {"ferrule", "pin-l", "pin-r"}
    assert 0 < tops["ferrule"] < tops["pin-l"] < depth
    plug = by_path(root, f"{cage}-occupant-occupant")
    pe = doc(SEATS[ref][1])["elements"]
    for i in range(1, n + 1):
        f = by_path(root, f"{cage}-occupant/{pid}/{i}")
        assert f.get("data-class") == "fibre"
        here = device_point(parents, f, _num(f, "cx", "cy"))
        if str(i) in pe:
            a = pe[str(i)]
            there = device_point(parents, plug, [a["at"][0] + a["size"][0] / 2,
                                                 a["at"][1] + a["size"][1] / 2])
            assert here == pytest.approx(there, abs=1e-6), i
