"""Four generic optics and the MPO-16 plug (docs/pluggables-mpo-bidi-pon-design.md).

    generic/qsfp-mpo@1         a QSFP with one MPO receptacle (std/mpo@2)
    generic/qsfp-dd-mpo16@1    a QSFP-DD with one MPO-16 receptacle (std/mpo16@1)
    generic/qsfp-lc-simplex@1  a QSFP with one LC bore in a duplex-shaped shell
    generic/sfp-sc@1           an SFP with one SC opening, long axis horizontal
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
MPO16 = "generic/mpo16-plug@1"

# optic -> (mates, conforms, receptacle part id, receptacle ref, its rotate,
#           interface presented, what its slot offers)
OPTICS = {
    QSFP_MPO: ("qsfp", "qsfp-module", "mpo", "std/mpo@2", 0, "mpo",
               {"generic/mpo12-plug@1", "generic/mpo24-plug@1", "common/mpo-dust-cap@2"}),
    QDD_MPO16: ("qsfp-dd", "qsfp-dd-module", "mpo16", "std/mpo16@1", 0, "mpo16",
                {MPO16, "common/mpo16-dust-cap@1"}),
    QSFP_BIDI: ("qsfp", "qsfp-module", "bore", "std/lc-bore@3", 180, "lc",
                {"generic/lc-plug@2", "common/lc-dust-cap@1"}),
    SFP_SC: ("sfp", "sfp-module", "sc", "std/sc-bore@1", 270, "sc",
             {"generic/sc-plug@1", "common/sc-dust-cap@1"}),
}
EACH = pytest.mark.parametrize("ref", sorted(OPTICS))

# optic -> (above the body, below it, length outside the cage, width)
HEADS = {
    QSFP_MPO: (1.4, 1.4, 20.0, 18.35),
    QDD_MPO16: (3.13, 1.5, 31.9, 18.35),
    QSFP_BIDI: (2.2, 1.5, 19.2, 18.35),
    SFP_SC: (2.1, 1.4, 20.0, 14.0),
}
BEIGE = "#d9cba3"
GREY = "#6f6f6f"

# optic -> (the agr560 cage it is seated in, the plug chained in it). Two of
# the cages are drawn at rotate 180 (the lower row of a stack), so the chain
# is held on a turned host as well as an upright one.
SEATS = {
    QSFP_MPO: ("qsfp28-0", "generic/mpo12-plug@1"),
    QDD_MPO16: ("qsfpdd-1", MPO16),
    QSFP_BIDI: ("qsfp28-3", "generic/lc-plug@2"),
    SFP_SC: ("port-0", "generic/sc-plug@1"),
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
    head = doc(SFP_SC)["head"]
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
    """Neither MPO aperture draws its keyway, so key-up is the placement: the
    aperture unrotated, with the plugs' key ribs drawn on top unrotated (a
    seat turns an occupant by its host's turn and nothing else)."""
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


def test_the_sc_opening_lies_across_with_its_key_slot_down():
    core = doc("std/sc-bore@1")
    p = part(SFP_SC, "sc")
    size = core["size"]
    mate = seat_point(p["at"], size, p["rotate"], core["connection-points"]["mate"]["at"])
    assert mate == pytest.approx(doc(SFP_SC)["connection-points"]["optical"]["at"])
    assert mate[0] == pytest.approx(doc(SFP_SC)["size"]["w"] / 2)
    # the 9.0 axis of the opening runs in x once turned
    a = seat_point(p["at"], size, p["rotate"], [4.64, 0.0])
    b = seat_point(p["at"], size, p["rotate"], [4.64, 9.0])
    assert abs(a[0] - b[0]) == pytest.approx(9.0) and a[1] == pytest.approx(b[1])
    # the key slot (the part's left wall unrotated) is at the bottom
    slot = seat_point(p["at"], size, p["rotate"], [0.0, 4.5])
    assert slot[0] == pytest.approx(mate[0]) and slot[1] > mate[1]
    # and the whole turned part is inside the head
    head = doc(SFP_SC)["head"]
    assert head["at"][1] <= min(a[1], slot[1] - 8.39) and slot[1] <= head["at"][1] + head["size"]["h"]


def test_the_sc_bail_is_a_field_painted_bar_at_the_bottom():
    d = doc(SFP_SC)
    bail = node(SFP_SC, "bail")
    assert bail.get("data-fill-from") == "latch-color"
    y, h = float(bail.get("y")), float(bail.get("height"))
    assert y > d["size"]["h"] and y + h <= d["head"]["at"][1] + d["head"]["size"]["h"]
    feat = next(f for f in d["relief"]["features"] if f["node"] == "bail")
    assert "color" not in feat                          # L73: a field paints it
    assert feat["lift"] == d["head"]["size"]["d"] and feat["bar"] == pytest.approx(h)


def test_the_mpo_faces_default_to_beige_and_the_others_to_grey():
    assert doc(QSFP_MPO)["fields"]["latch-color"]["default"] == BEIGE
    assert doc(QDD_MPO16)["fields"]["latch-color"]["default"] == BEIGE
    assert doc(QSFP_BIDI)["fields"]["latch-color"]["default"] == GREY
    assert doc(SFP_SC)["fields"]["latch-color"]["default"] == GREY


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


def test_the_seated_mpo_tabs_are_beige_and_the_bidi_tab_is_grey(seated):
    """A host's own default reaches the tab it composes: the pull tab's own
    default is grey, and nothing on the two MPO optics pins a colour."""
    root, _ = seated
    for ref, want in ((QSFP_MPO, BEIGE), (QDD_MPO16, BEIGE), (QSFP_BIDI, GREY)):
        tab = by_path(root, f"{SEATS[ref][0]}-occupant/tab")
        grip = [e for e in tab.iter() if (e.get("id") or "").endswith("--grip")]
        assert len(grip) == 1 and grip[0].get("fill") == want, (ref, grip[0].get("fill"))


def test_a_seated_plug_keeps_its_key_on_the_receptacles_key_side(seated):
    """The SC plug's key is drawn left, as the bore's slot is; seated in the
    turned bore both are at the module bottom. The MPO-16 plug's key stays on
    the pull-tab side, offset toward the same side in the module's own frame
    whichever way up the cage is drawn."""
    root, parents = seated
    sc = by_path(root, f"{SEATS[SFP_SC][0]}-occupant-occupant")
    ferrule = device_point(parents, sc, own_mate(sc))
    key = device_point(parents, sc, [0.45, 4.5])
    assert key[1] > ferrule[1] and abs(key[0] - ferrule[0]) < 1e-6
    cage = SEATS[QDD_MPO16][0]
    optic = by_path(root, f"{cage}-occupant")
    plug = by_path(root, f"{cage}-occupant-occupant")
    k = device_point(parents, plug, [6.25 + 1.12, 0.74])
    top = device_point(parents, optic, [9.175 + 1.12, 0.0])
    bottom = device_point(parents, optic, [9.175 + 1.12, 8.5])
    assert abs(k[0] - top[0]) < 1e-6
    assert abs(k[1] - top[1]) < abs(k[1] - bottom[1])
