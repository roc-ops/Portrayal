"""Generic optics for the OSFP and XFP cages (docs/pluggables-osfp-xfp-design.md).

    generic/osfp-mpo16@1     an OSFP with one MPO-16 receptacle
    generic/osfp-lc@1        an OSFP with two LC bores
    generic/xfp-lc@1         an XFP with two LC bores and a bail
    common/osfp-pull-tab@1   the pull tab the two OSFP parts compose
    osfp-module, xfp-module  the two module envelopes, with their heads

What each is, that its head fits the MSA envelope (L121), that its receptacle
is the right part the right way up and is a slot offering the right plug and
dust cap (from a components.json built here by the indexer), that every OSFP
and XFP cage in the library now offers exactly these and no other cage does,
and that each optic seats in a real cage with a plug chained in it: the OSFP
parts in both rows of a stacked column of edgecore/ais800-32o, the XFP on
juniper/mx80 and in a quarter-turned cage of a card seated in juniper/mx960.

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
from portrayal import libwalk
from portrayal import lint
from portrayal import render as render_mod
from portrayal.artifacts import face_file
from portrayal.manifest import seat_point
from test_nested_occupants import by_path, cage_mate, device_point, own_mate

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

OSFP_MPO16 = "generic/osfp-mpo16@1"
OSFP_LC = "generic/osfp-lc@1"
XFP_LC = "generic/xfp-lc@1"
TAB = "common/osfp-pull-tab@1"
REC16 = "std/mpo16-module-receptacle@1"
BORE = "std/lc-bore@3"
MPO16_OFFER = {"generic/mpo16-plug@1", "common/mpo16-dust-cap@1"}
LC_OFFER = {"generic/lc-plug@2", "common/lc-dust-cap@1"}
GREY = "#6f6f6f"

# optic -> (mates, conforms, {receptacle part id: (ref, rotate)}, interface
#           presented, what each slot offers)
OPTICS = {
    OSFP_MPO16: ("osfp", "osfp-module", {"mpo16": (REC16, 0)}, "mpo16", MPO16_OFFER),
    OSFP_LC: ("osfp", "osfp-module", {"tx": (BORE, 180), "rx": (BORE, 180)}, "lc", LC_OFFER),
    XFP_LC: ("xfp", "xfp-module", {"tx": (BORE, 180), "rx": (BORE, 180)}, "lc", LC_OFFER),
}
EACH = pytest.mark.parametrize("ref", sorted(OPTICS))
OSFP = (OSFP_LC, OSFP_MPO16)

# optic -> (above the body, below it, length outside the cage, width)
HEADS = {
    OSFP_MPO16: (0.0, 1.6, 21.39, 22.93),
    OSFP_LC: (0.0, 1.6, 21.39, 22.93),
    XFP_LC: (2.85, 0.8, 9.0, 22.15),
}
# the two registry envelopes, as the MSAs print them
ENVELOPES = {
    "osfp-module": (22.58, 13.0, 79.01, {"w-max": 22.93, "above-max": 0.0, "below-max": 1.6,
                                         "length-max": {"type-1": 21.39, "type-2": 37.39}}),
    "xfp-module": (18.35, 8.5, 69.0, {"w-max": 22.35, "above-max": 3.0, "below-max": 2.0,
                                      "length-max": 9.0}),
}


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


# --- the registry ------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(ENVELOPES))
def test_the_module_envelope_and_its_head_are_the_msa_figures(key):
    w, h, depth, head = ENVELOPES[key]
    e = standards()[key]
    assert (e["w"], e["h"], e["depth"]) == (w, h, depth)
    assert {k: e["head"][k] for k in head} == head
    assert e["head"]["source"].strip() and "length-kind" not in e["head"]
    # the inserted length plus the head is the longest module the MSA allows
    longest = {"osfp-module": 100.40, "xfp-module": 78.0}[key]
    lmax = head["length-max"]
    assert depth + (lmax["type-1"] if isinstance(lmax, dict) else lmax) == pytest.approx(longest)


def test_no_cage_contract_changed_to_carry_a_head():
    """The envelope outside the cage is on the MODULE entry the optic conforms
    to, as for SFP and QSFP. The cages are as they were: std/osfp@1 still
    states an interface and no `conforms`, and there is no `osfp` cage entry."""
    osfp, xfp = doc("std/osfp@1"), doc("std/xfp@1")
    assert "conforms" not in osfp and osfp["interface"] == "osfp"
    assert xfp["conforms"] == "xfp" and "head" not in standards()["xfp"]
    assert "osfp" not in standards()
    assert (osfp["version"], xfp["version"]) == ("1.0.0", "1.0.0")


# --- what each optic is ------------------------------------------------------

@EACH
def test_it_is_a_generic_transceiver_of_its_family(ref):
    d = doc(ref)
    mates, conforms = OPTICS[ref][:2]
    assert (d["kind"], d["class"], d["behaviour"]) == ("component", "transceiver", "occupies")
    assert d["mates"] == mates and d["conforms"] == conforms
    std = standards()[conforms]
    assert (d["size"]["w"], d["size"]["h"], d["size"]["d"]) == (std["w"], std["h"], std["depth"])
    assert d["size-confidence"] == {"w": "registry", "h": "registry", "d": "registry"}
    assert d["unplaced"] and d["version"] == "1.0.0" and d["skins"] == ["default"]
    # it seats centre on centre
    assert d["connection-points"]["mate"]["at"] == [d["size"]["w"] / 2, d["size"]["h"] / 2]


@EACH
def test_a_generic_states_no_rate_reach_wavelength_or_wattage(ref):
    d = doc(ref)
    assert not set(d["attrs"]) & set(lint.GENERIC_FORBIDDEN_ATTRS)
    assert d["attrs"]["form-factor"] == d["mates"]
    with lint.collecting() as got:
        lint.lint_component_generic(path(ref) / "contract.yaml", d)
    assert not got.errors, got.errors


@EACH
def test_the_head_fits_the_msa_envelope(ref):
    """L121, and the figures it is run on: above, below, length and width as
    the contract states them, measured the way the rule measures."""
    d = doc(ref)
    above, below, length, width = HEADS[ref]
    head = d["head"]
    assert max(0.0, -head["at"][1]) == pytest.approx(above)
    assert head["at"][1] + head["size"]["h"] - d["size"]["h"] == pytest.approx(below)
    assert head["size"]["d"] == pytest.approx(length)
    assert head["size"]["w"] == pytest.approx(width)
    assert not head.get("exceeds")
    # centred on the body
    assert head["at"][0] == pytest.approx((d["size"]["w"] - width) / 2)
    with lint.collecting() as got:
        lint.lint_component_head(path(ref) / "contract.yaml", d)
    assert not [e for e in got.errors + got.warnings if "[L121]" in e], got.errors


def test_the_osfp_heads_sit_at_the_envelope_and_the_xfp_head_inside_it():
    env = standards()["osfp-module"]["head"]
    for ref in OSFP:
        head = doc(ref)["head"]
        assert head["type"] == 1 and head["size"]["d"] == env["length-max"]["type-1"]
        assert head["size"]["w"] == env["w-max"]
        # the nose begins below the heat sink: nothing of it is above the body
        assert head["at"][1] == 3.8
    env, head = standards()["xfp-module"]["head"], doc(XFP_LC)["head"]
    assert "type" not in head
    assert head["size"]["w"] < env["w-max"] and -head["at"][1] < env["above-max"]
    assert head["size"]["d"] == env["length-max"]


@EACH
def test_the_head_node_is_the_skins_first_child_and_draws_the_head(ref):
    """`body` carries the box of the head and is the FIRST drawing child:
    render.py never raises the first child, so the face art drawn after it is
    not buried under the nose in 2D or 3D."""
    d = doc(ref)
    assert d["head"]["node"] == "body"
    first = [c for c in skin(ref) if c.tag.rsplit("}", 1)[-1] not in ("title", "defs", "style")][0]
    assert first.get("id") == "body" and first.tag.endswith("rect")
    box = [float(first.get(k)) for k in ("x", "y", "width", "height")]
    want = [*d["head"]["at"], d["head"]["size"]["w"], d["head"]["size"]["h"]]
    assert all(abs(a - b) <= lint.HEAD_NODE_TOL for a, b in zip(box, want)), (box, want)


# --- the receptacles ---------------------------------------------------------

@EACH
def test_the_receptacles_are_the_right_parts_the_right_way_up(ref):
    want, iface = OPTICS[ref][2], OPTICS[ref][3]
    d = doc(ref)
    presenting = {q["id"]: q for q in d["parts"] if doc(q["ref"]).get("interface")}
    assert set(presenting) == set(want)
    for pid, (pref, rotate) in want.items():
        assert presenting[pid]["ref"] == pref and (presenting[pid].get("rotate") or 0) == rotate
        assert doc(pref)["interface"] == iface
    depth = d["head"]["size"]["d"]
    for q in d["parts"]:
        assert q["lift"] == depth, (ref, q["id"])       # all of it stands on the nose front


def test_the_mpo16_receptacle_is_key_up_and_centred_on_the_module():
    """Unrotated, so the key notch is in the top wall, toward the heat sink,
    and offset to the right looking in (the OSFP MSA figure for this face)."""
    d = doc(OSFP_MPO16)
    p = part(OSFP_MPO16, "mpo16")
    assert not p.get("rotate")
    core = doc(REC16)
    mate = [p["at"][0] + core["connection-points"]["mate"]["at"][0],
            p["at"][1] + core["connection-points"]["mate"]["at"][1]]
    assert mate == pytest.approx(d["connection-points"]["optical"]["at"])
    assert mate[0] == pytest.approx(d["size"]["w"] / 2)
    key = node(REC16, "keyway")
    centre = float(key.get("x")) + float(key.get("width")) / 2
    assert centre > core["connection-points"]["mate"]["at"][0]
    assert float(key.get("y")) < core["size"]["h"] / 4
    # the mouth is inside the nose
    head = d["head"]
    assert head["at"][1] <= p["at"][1]
    assert p["at"][1] + core["size"]["h"] <= head["at"][1] + head["size"]["h"]
    assert core["optical"]["positions"] == 16


@pytest.mark.parametrize("ref", [OSFP_LC, XFP_LC])
def test_the_two_lc_bores_are_latch_up_transmit_left_at_the_registry_pitch(ref):
    d = doc(ref)
    core = doc(BORE)
    cps = d["connection-points"]
    got = {}
    for pid in ("tx", "rx"):
        p = part(ref, pid)
        ferrule = seat_point(p["at"], core["size"], 180, core["connection-points"]["mate"]["at"])
        assert ferrule == pytest.approx(cps[f"optical-{pid}"]["at"])
        tongue = seat_point(p["at"], core["size"], 180, [2.35, core["size"]["h"]])
        assert tongue[1] < ferrule[1]                         # the latch slot is above
        got[pid] = ferrule
    assert got["tx"][0] < got["rx"][0] and got["tx"][1] == got["rx"][1]
    pitch = standards()["lc-duplex-receptacle"]["pitch"]
    assert got["rx"][0] - got["tx"][0] == pytest.approx(pitch) == 6.25
    assert (got["tx"][0] + got["rx"][0]) / 2 == pytest.approx(d["size"]["w"] / 2)
    # both openings are inside the head
    head = d["head"]
    for pid in ("tx", "rx"):
        y = part(ref, pid)["at"][1]
        assert head["at"][1] <= y and y + core["size"]["h"] <= head["at"][1] + head["size"]["h"]
    letters = [t.text for t in skin(ref).iter() if t.tag.endswith("text") and t.text]
    assert letters == ["T", "R"]


def test_the_xfp_bores_are_at_the_qsfp_positions_on_the_body_mid_height():
    q = {p["id"]: p["at"][0] for p in doc("generic/qsfp-lc@2")["parts"] if p["id"] in ("tx", "rx")}
    assert {p: part(XFP_LC, p)["at"][0] for p in ("tx", "rx")} == q
    d = doc(XFP_LC)
    assert d["connection-points"]["optical-tx"]["at"][1] == d["size"]["h"] / 2


# --- the heat sink, the tab and the bail --------------------------------------

@pytest.mark.parametrize("ref", OSFP)
def test_the_osfp_face_has_a_vented_heat_sink_above_the_nose(ref):
    """Ten vent holes 1.80 x 3.20 under a 0.30 skin (the closed-top example of
    the OSFP MSA), as holes in one evenodd path over a dark backing, filling
    the face above the nose. The band stands 1.39 out and the nose 21.39."""
    d = doc(ref)
    sink = node(ref, "sink")
    assert sink.get("fill-rule") == "evenodd"
    subs = [s.split() for s in sink.get("d").split("M")[1:]]
    holes = [(float(s[0]), float(s[1]), float(s[3]), float(s[5])) for s in subs[1:]]
    assert len(holes) == 10
    assert {(w, h, y) for _, y, w, h in holes} == {(1.8, 3.2, 0.3)}
    xs = [x for x, *_ in holes]
    assert all(b - a == pytest.approx(2.1) for a, b in zip(xs, xs[1:]))
    assert xs[0] + (xs[-1] + 1.8) == pytest.approx(d["size"]["w"])         # centred
    assert 0.3 + 3.2 < d["head"]["at"][1]
    back = node(ref, "sink-back")
    order = [c.get("id") for c in skin(ref) if c.get("id")]
    assert order.index("body") == 0 and order.index("sink-back") < order.index("sink")
    assert float(back.get("y")) + float(back.get("height")) <= d["head"]["at"][1]
    feats = {f["node"]: f for f in d["relief"]["features"]}
    assert set(feats) == {"body", "sink"}
    assert feats["body"]["out"] == d["head"]["size"]["d"] == 21.39
    assert feats["sink"]["out"] == pytest.approx(21.39 - 20.0)
    assert all(f["color"] and f["confidence"] == "drawing" and f["source"] for f in feats.values())


def test_the_two_osfp_parts_differ_only_in_the_face():
    a, b = doc(OSFP_MPO16), doc(OSFP_LC)
    same = ("size", "size-confidence", "head", "fields", "relief", "mates", "conforms", "class",
            "behaviour", "unplaced")
    assert {k: a[k] for k in same} == {k: b[k] for k in same}
    assert part(OSFP_MPO16, "tab") == part(OSFP_LC, "tab")
    assert (a["attrs"]["face"], b["attrs"]["face"]) == ("mpo16", "lc-duplex")
    art = lambda ref: {e.get("id"): dict(e.attrib) for e in skin(ref).iter()
                       if e.get("id") in ("body", "sink", "sink-back")}
    assert art(OSFP_MPO16) == art(OSFP_LC)


def test_the_osfp_tab_is_a_loop_with_the_msa_reach_and_a_raised_grip():
    """49.31 from the module front: the OSFP MSA prints (139.1) from the tab
    end to the forward stop, and the module front is 100.40 less 10.61 ahead
    of that stop. The strap leaves the nose 2.45 below the grip and climbs
    to it, as both vendor outlines draw (scaled)."""
    d = doc(TAB)
    assert d["class"] == "latch" and "behaviour" not in d and "mates" not in d
    assert d["size"] == {"w": 22.58, "h": 4.85}
    assert d["size-confidence"] == {"w": "estimated", "h": "estimated"} and d["size-notes"]
    e = d["elements"]
    tops = {"": 2.45, "-2": 2.04, "-3": 1.23, "-4": 0.41, "-5": 0.0}
    assert set(e) == {"grip"} | {f"arm-{s}{k}" for s in "lr" for k in tops}
    assert e["grip"] == {"at": [0.0, 0.0], "size": [22.58, 2.4], "class": "latch"}
    for side, x in (("l", 0.0), ("r", 20.18)):
        for k, y in tops.items():
            assert e[f"arm-{side}{k}"] == {"at": [x, y], "size": [2.4, 2.4], "class": "latch"}
    assert max(v["at"][1] + v["size"][1] for v in e.values()) == d["size"]["h"]
    feats = {f["node"]: f for f in d["relief"]["features"]}
    assert set(feats) == set(e)
    reach = 139.1 - (100.40 - 10.61)
    assert feats["grip"]["out"] == pytest.approx(reach) == 49.31
    assert feats["grip"]["confidence"] == "drawing"
    assert not [f["node"] for f in feats.values() if "color" in f]            # L73
    for nid in e:
        el = node(TAB, nid)
        assert el.get("data-fill-from") == el.get("data-stroke-derive") == "latch-color"
        assert [float(el.get(k)) for k in ("x", "y", "width", "height")] == [*e[nid]["at"], *e[nid]["size"]]
    order = [c.get("id") for c in skin(TAB) if c.get("id")]
    assert order[0] == "arm-l" and order[-1] == "grip"          # farthest first, nearest last


def test_the_osfp_tab_is_boxes_end_to_end_with_no_shared_volume():
    """Along each arm every box starts where the one before it ends (`lift`
    is where it starts, `out` where it ends), from the nose front to the tip,
    and each step of the climb is higher than the one before."""
    d = doc(TAB)
    feats = {f["node"]: f for f in d["relief"]["features"]}
    for side in "lr":
        chain = [f"arm-{side}{k}" for k in ("", "-2", "-3", "-4", "-5")] + ["grip"]
        at, top = 0.0, 99.0
        for nid in chain:
            f = feats[nid]
            assert (f.get("lift") or 0.0) == pytest.approx(at), nid
            assert f["out"] > at, nid
            at = f["out"]
            assert d["elements"][nid]["at"][1] <= top, nid
            top = d["elements"][nid]["at"][1]
        assert at == 49.31 and top == 0.0


@pytest.mark.parametrize("ref", OSFP)
def test_the_osfp_optics_compose_the_tab_on_the_nose_clear_of_the_face(ref):
    d = doc(ref)
    tab = part(ref, "tab")
    assert tab == {"ref": TAB, "id": "tab", "at": [0.0, 1.35], "lift": 21.39}
    t = doc(TAB)
    # the strap leaves the nose level with its top, and the grip is above the face
    assert tab["at"][1] + t["elements"]["arm-l"]["at"][1] == pytest.approx(d["head"]["at"][1])
    grip_bottom = tab["at"][1] + t["elements"]["grip"]["size"][1]
    assert 0 < tab["at"][1] and grip_bottom <= d["head"]["at"][1]
    for q in d["parts"]:
        assert q["id"] == "tab" or q["at"][1] >= grip_bottom
    assert doc(TAB)["size"]["w"] == d["size"]["w"]              # arms on the side edges
    arm = doc(TAB)["elements"]["arm-l"]["size"][0]
    core_w = {q["id"]: doc(q["ref"])["size"]["w"] for q in d["parts"] if q["id"] != "tab"}
    for q in d["parts"]:
        if q["id"] == "tab":
            continue
        assert arm < q["at"][0] and q["at"][0] + core_w[q["id"]] < d["size"]["w"] - arm
    with lint.collecting() as got:
        lint.lint_component_collisions(path(ref) / "contract.yaml", d, [str(LIB)])
    assert not got.warnings and not got.errors, got.warnings


def test_the_xfp_bail_is_a_field_painted_bar_across_the_top_of_the_head():
    d = doc(XFP_LC)
    bail = node(XFP_LC, "bail")
    assert bail.get("data-fill-from") == bail.get("data-stroke-derive") == "latch-color"
    y, h = float(bail.get("y")), float(bail.get("height"))
    head = d["head"]
    assert y == pytest.approx(head["at"][1] + 0.1) and y + h < 0          # above the body
    assert float(bail.get("width")) == pytest.approx(head["size"]["w"] - 0.2)
    feats = {f["node"]: f for f in d["relief"]["features"]}
    assert set(feats) == {"body", "bail"}
    assert feats["body"]["out"] == head["size"]["d"] == 9.0
    assert "color" not in feats["bail"]                                  # L73: a field paints it
    assert feats["bail"]["lift"] == 9.0 and feats["bail"]["bar"] == pytest.approx(h)
    assert "tab" not in [q["id"] for q in d["parts"]]


@EACH
def test_the_latch_colour_is_a_field_and_defaults_to_the_neutral_grey(ref):
    d = doc(ref)
    assert set(d["fields"]) == {"latch-color", "label"}
    assert d["fields"]["latch-color"]["default"] == GREY
    assert doc(TAB)["fields"]["latch-color"]["default"] == GREY
    assert d["skins"] == ["default"]                # a colour is a field, never a second skin
    assert node(ref, "label").get("data-from") == "label"
    note = d["provenance"].get("tab-colour") or d["provenance"]["bail-colour"]
    assert "A FIELD" in note and "wrapper" in note


# --- the slots, from a components.json built here ----------------------------

@pytest.fixture(scope="module")
def comps():
    built = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in built["components"]}
    assert got, "the indexer published no component at all"
    return got


def _slots(entry):
    return [s for s in [entry.get("presents")] + (entry.get("cages") or []) if s]


@EACH
def test_each_receptacle_is_a_slot_offering_its_plug_and_cap(comps, ref):
    want, iface, accepts = OPTICS[ref][2:]
    d = doc(ref)
    slots = _slots(comps[ref])
    assert len(slots) == len(want), f"{ref} publishes {len(slots)} slots"
    for slot in slots:
        assert (slot["kind"], slot["interface"]) == ("connector", iface)
        assert set(slot["accepts"]) == accepts, slot["accepts"]
        assert slot["lift"] == d["head"]["size"]["d"]
    if len(want) == 1:
        slot = comps[ref]["presents"]
        assert slot["mate"] == pytest.approx(d["connection-points"]["optical"]["at"])
        assert not slot.get("rotate")
    else:
        by_id = {s["id"]: s for s in comps[ref]["cages"]}
        assert set(by_id) == {"tx", "rx"}
        for pid, slot in by_id.items():
            assert slot["mate"] == pytest.approx(d["connection-points"][f"optical-{pid}"]["at"])
            assert slot["rotate"] == 180
    assert comps[ref]["head"]["size"]["d"] == d["head"]["size"]["d"]


def test_the_osfp_mpo16_slot_offers_no_twelve_or_twenty_four_fibre_plug(comps):
    offered = set(comps[OSFP_MPO16]["presents"]["accepts"])
    assert offered == MPO16_OFFER
    assert not offered & {"generic/mpo12-plug@1", "generic/mpo24-plug@1", "common/mpo-dust-cap@2"}
    assert doc("generic/mpo16-plug@1")["mates"] == "mpo16"


# --- what the cages offer, across the whole library ---------------------------

OFFERS = {"osfp": [OSFP_LC, OSFP_MPO16], "xfp": [XFP_LC]}
NEW = {OSFP_LC, OSFP_MPO16, XFP_LC}


@pytest.fixture(scope="module")
def device_cages():
    """Every cage entry of every device, computed by the function the build
    writes `cages[]` with."""
    lib = render_mod.Library([str(LIB)])
    families = render_mod._pluggable_families()
    candidates = render_mod._pluggable_candidates([LIB])
    got = []
    for man in libwalk.iter_devices([LIB]):
        d = render_mod.load_yaml(man)
        for v in d.get("views") or {}:
            for c in render_mod.cage_entries(d, v, lib, families, candidates, {}):
                if c["kind"] == "cage":
                    got.append((man.parent.name, c))
    assert len(got) >= 3000, len(got)
    return got


@pytest.mark.parametrize("family", sorted(OFFERS))
def test_every_cage_of_the_family_offers_exactly_the_new_optics(device_cages, comps, family):
    """On devices and on cards: an OSFP cage offers the two OSFP optics, an
    XFP cage the one XFP optic, generics in alphabetical order."""
    on_devices = [c for _, c in device_cages if c["interface"] == family]
    on_cards = [s for ref, e in comps.items() for s in (e.get("cages") or [])
                if s["interface"] == family and s["kind"] == "cage"]
    # 128 XFP cages on cards until #261 removed the MX960 vertical twins with eight of
    # them: dpc-r-4xge-xfp-v (4), dpce-2xge-xfp-v960 (2) and dpce-20ge-2xge-v960 (2)
    # #261 part 2 retired the vertical MIC twins and the MICs' previous majors but
    # kept them (`superseded-by`, #448); this walk counts them: 127 measured, of
    # which 113 are on live contracts.
    floor = {"osfp": (416, 4), "xfp": (4, 120)}[family]
    assert len(on_devices) >= floor[0] and len(on_cards) >= floor[1], (len(on_devices), len(on_cards))
    for c in on_devices + on_cards:
        assert c["accepts"] == OFFERS[family], (c["id"], c["accepts"])


def test_no_other_family_offers_them_and_the_pool_is_the_family(device_cages, comps):
    others = [c for _, c in device_cages if c["interface"] not in OFFERS]
    others += [s for e in comps.values() for s in _slots(e) if s["interface"] not in OFFERS]
    assert len(others) > 3000
    for c in others:
        assert not NEW & set(c["accepts"]), (c.get("id"), c["interface"])
    pool = render_mod._pluggable_candidates([LIB])
    assert sorted(r for r, _ in pool["osfp"]) == OFFERS["osfp"]
    assert [r for r, _ in pool["xfp"]] == OFFERS["xfp"]
    # and neither is in the pool of a family that got its optics later
    for family in ("cfp", "cfp2", "cfp4", "cxp"):
        assert not NEW & {r for r, _ in pool.get(family) or []}, family


# --- seated in real cages, a plug chained in ----------------------------------

AIS = "edgecore/ais800-32o"       # port-1 over port-2, both rotate 0 - the same way up (#799)
MX80 = "juniper/mx80"
MX960 = "juniper/mx960"           # fpc6 seats the horizontal card turned 90 by its bay (#261)
CARD = "juniper/dpc-r-4xge-xfp@2"
# the turn a cage inherits from its card's bay: on the MX960 the quarter turn is
# the card's, and its XFP cages are drawn upright inside it
CARD_TURN = {MX960: 90}
# (device, cage key, cage path, optic, {slot key suffix: occupant}, turn)
SEATS = [
    (AIS, "port-1", "port-1", OSFP_MPO16, {"": "generic/mpo16-plug@1"}, 0),
    (AIS, "port-2", "port-2", OSFP_LC, {"/tx": "generic/lc-plug@2", "/rx": "common/lc-dust-cap@1"}, 0),
    (AIS, "port-3", "port-3", OSFP_LC, {"/tx": "generic/lc-plug@2"}, 0),
    (AIS, "port-4", "port-4", OSFP_MPO16, {"": "common/mpo16-dust-cap@1"}, 0),
    (MX80, "xe-1", "xe-1", XFP_LC, {"/tx": "generic/lc-plug@2", "/rx": "common/lc-dust-cap@1"}, 0),
    (MX960, "fpc6/port-1", "fpc6/module/port-1", XFP_LC, {"/tx": "generic/lc-plug@2"}, 90),
]
EACH_SEAT = pytest.mark.parametrize("seat", SEATS, ids=[f"{s[0].split('/')[1]}:{s[1]}" for s in SEATS])


def _build(tmp, device, config, occupants, bays=None):
    name = device.split("/")[1]
    dev = tmp / name / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"][config]
    cfg["occupants"] = occupants
    if bays:
        cfg["bays"] = {**(cfg.get("bays") or {}), **bays}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / f"out-{name}"
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(face_file(out, name, config, "front")).getroot()
    return root, {c: p for p in root.iter() for c in p}


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    """One build per device, each a copy with the optics seated and their
    plugs and caps chained in."""
    tmp = tmp_path_factory.mktemp("osfp-xfp")
    occ = {}
    for device, key, _, optic, chain, _ in SEATS:
        occ.setdefault(device, {})[key] = optic
        for suffix, ref in chain.items():
            occ[device][f"{key}-occupant{suffix}"] = ref
    return {
        AIS: _build(tmp, AIS, "ac-f2b", occ[AIS]),
        MX80: _build(tmp, MX80, "mx80", occ[MX80]),
        MX960: _build(tmp, MX960, "base", occ[MX960], bays={"fpc6": CARD}),
    }


def _turn(el):
    t = el.get("transform") or ""
    return int(float(t.split("rotate(")[1].split(",")[0].split(")")[0].split()[0])) % 360 \
        if "rotate(" in t else 0


@EACH_SEAT
def test_it_seats_in_a_real_cage_with_its_plug_in_it(seated, seat):
    device, _, cpath, ref, chain, turn = seat
    root, parents = seated[device]
    cage = by_path(root, cpath)
    optic = by_path(root, f"{cpath}-occupant")
    assert cage.get("data-ref", "").startswith({"osfp": "std/osfp@1", "xfp": "std/xfp@1"}[doc(ref)["mates"]])
    assert optic.get("data-ref", "").startswith(ref)
    inherited = CARD_TURN.get(device, 0)
    assert _turn(optic) == _turn(cage) and (_turn(cage) + inherited) % 360 == turn
    if device in CARD_TURN:
        assert _turn(by_path(root, cpath.split("/")[0] + "/module")) == inherited
    # the optic is centred on the mate point of the cage
    cx, cy = device_point(parents, cage, cage_mate(cage))
    ox, oy = device_point(parents, optic, own_mate(optic))
    assert abs(cx - ox) < 1e-6 and abs(cy - oy) < 1e-6
    d = doc(ref)
    depth = d["head"]["size"]["d"]
    for suffix, want in chain.items():
        occ = by_path(root, f"{cpath}-occupant{suffix}-occupant")
        assert occ.get("data-ref", "").startswith(want)
        point = d["connection-points"]["optical" + suffix.replace("/", "-")]["at"]
        rx, ry = device_point(parents, optic, point)
        px, py = device_point(parents, occ, own_mate(occ))
        assert abs(rx - px) < 1e-6 and abs(ry - py) < 1e-6
        # and it stands on the front of the nose, not on the cage face
        assert float(occ.get("data-z-lift")) == pytest.approx(depth)


def test_the_lower_row_optic_is_the_upper_one_moved_down(seated):
    """A stacked OSFP column seats both modules heat sink up (OSFP MSA rev 5.22
    section 7.1, Figures 7-1 and 7-2), so since #799 the lower cage is drawn at
    rotate 0 like the upper and its optic is the upper one moved down a row:
    heat sink above the nose in both rows, transmit on the same side."""
    root, parents = seated[AIS]
    top, low = by_path(root, "port-3-occupant"), by_path(root, "port-2-occupant")
    assert doc(OSFP_LC)["connection-points"]["optical-tx"]["at"][0] < 11.29
    for optic in (top, low):
        sink = device_point(parents, optic, [11.29, 1.9])
        nose = device_point(parents, optic, [11.29, 9.2])
        mid = device_point(parents, optic, [11.29, 6.5])
        tx = device_point(parents, optic, [8.165, 8.7])
        assert nose[1] > sink[1] and tx[0] < mid[0]
    upper = by_path(root, "port-1-occupant")
    upper_sink = device_point(parents, upper, [11.29, 1.9])[1]
    upper_nose = device_point(parents, upper, [11.29, 9.2])[1]
    lower_sink = device_point(parents, low, [11.29, 1.9])[1]
    lower_nose = device_point(parents, low, [11.29, 9.2])[1]
    assert upper_sink < upper_nose < lower_sink < lower_nose


# THE NOSE OVERLAP #799 WAS FILED FOR. Turned belly-to-belly, the two noses -
# each reaching the MSA's 1.6 MAX below its module (Figure 3-3) - met in the band
# and overlapped by 1.66 on this 14.54 row pitch. The same way up, the upper nose
# reaches only toward the lower module's heat sink, and what is left is the row
# pitch less 14.6 (13.0 module + 1.6 nose): -0.06 here, because this face's
# drawn pitch is 0.36 under the MSA's 14.90 +/-0.10 (Figure 8-3), where it would
# clear by 0.30. It stays pinned so a change to either number is seen.
AIS_ROW_PITCH = 14.54


def _head_bottom(optic):
    h = doc(optic.get("data-ref").rsplit(":", 1)[0])["head"]
    return h["at"][1] + h["size"]["h"]


def test_the_stacked_noses_no_longer_meet_in_the_band(seated):
    root, parents = seated[AIS]
    upper, lower = by_path(root, "port-1-occupant"), by_path(root, "port-2-occupant")
    assert _head_bottom(upper) == pytest.approx(14.6) and _head_bottom(lower) == pytest.approx(14.6)
    upper_reach = device_point(parents, upper, [11.29, _head_bottom(upper)])[1]
    lower_top = device_point(parents, lower, [11.29, 0.0])[1]
    gap = lower_top - upper_reach
    assert gap == pytest.approx(AIS_ROW_PITCH - 14.6, abs=1e-6)
    # turned belly-to-belly, the lower nose came up to meet it
    lower_turned_reach = lower_top + 13.0 - 14.6
    assert upper_reach - lower_turned_reach == pytest.approx(1.66, abs=0.01)


def test_the_seated_mpo16_plug_keeps_its_key_toward_the_heat_sink(seated):
    root, parents = seated[AIS]
    optic = by_path(root, "port-1-occupant")
    plug = by_path(root, "port-1-occupant-occupant")
    k = device_point(parents, plug, [6.25 + 1.12, 0.74])
    sink = device_point(parents, optic, [11.29 + 1.12, 0.0])
    belly = device_point(parents, optic, [11.29 + 1.12, 13.0])
    assert abs(k[0] - sink[0]) < 1e-6
    assert abs(k[1] - sink[1]) < abs(k[1] - belly[1])
    # fibre n of the receptacle is addressable and lies under the plug fibre n
    pe = doc("generic/mpo16-plug@1")["elements"]
    for i in range(1, 17):
        f = by_path(root, f"port-1-occupant/mpo16/{i}")
        assert f.get("data-class") == "fibre"
        here = device_point(parents, f, [float(f.get("cx")), float(f.get("cy"))])
        a = pe[str(i)]
        there = device_point(parents, plug, [a["at"][0] + a["size"][0] / 2, a["at"][1] + a["size"][1] / 2])
        assert here == pytest.approx(there, abs=1e-6), i


def _raised(optic):
    oid = optic.get("id")
    return {e.get("id")[len(oid) + 2:]: e for e in optic.iter()
            if (e.get("id") or "").startswith(oid + "--")
            and "-occupant--" not in e.get("id")[len(oid):]         # a seated plug is its own part
            and any(e.get(k) for k in ("data-z-out", "data-z-bar"))}


@pytest.mark.parametrize("cage", ["port-1", "port-2"])
def test_the_seated_osfp_is_built_right_side_out_in_3d(seated, cage):
    """Read off the compiled relief, upright and turned: the heat sink front
    1.39 from the cage face, the nose front 21.39, the tab from there to
    70.70, each of its eleven boxes starting behind its own end, and the
    receptacle cavities cut from the nose front."""
    root, _ = seated[AIS]
    optic = by_path(root, f"{cage}-occupant")
    raised = _raised(optic)
    boxes = [f"tab--arm-{s}{k}" for s in "lr" for k in ("", "-2", "-3", "-4", "-5")] + ["tab--grip"]
    assert set(raised) == {"body", "sink", *boxes}
    assert float(raised["body"].get("data-z-out")) == pytest.approx(21.39)
    assert float(raised["sink"].get("data-z-out")) == pytest.approx(1.39)
    tab = by_path(root, f"{cage}-occupant/tab")
    assert float(tab.get("data-z-lift")) == pytest.approx(21.39)
    ends = {}
    for name in boxes:
        e = raised[name]
        start = 21.39 + float(e.get("data-z-lift") or 0)
        ends[name] = (start, float(e.get("data-z-out")))
        assert 21.39 <= start < ends[name][1], (name, ends[name])
        assert e.get("data-z-color") is None, name
    assert ends["tab--grip"][1] == pytest.approx(21.39 + 49.31)
    for k in ("", "-2", "-3", "-4", "-5"):
        assert ends[f"tab--arm-l{k}"] == ends[f"tab--arm-r{k}"]
    assert ends["tab--arm-l"][0] == pytest.approx(21.39)
    assert ends["tab--arm-l-5"][1] == pytest.approx(ends["tab--grip"][0])
    assert max(float(e.get("data-z-out")) for e in raised.values()) == pytest.approx(70.70)
    ref = optic.get("data-ref").rsplit(":", 1)[0]
    for pid in OPTICS[ref][2]:
        mouth = by_path(root, f"{cage}-occupant/{pid}")
        assert float(mouth.get("data-z-lift")) == pytest.approx(21.39)
        cavity = [e for e in mouth.iter() if e.get("data-depth")]
        assert cavity and all(float(e.get("data-depth")) > 0 for e in cavity)
        assert not [e.get("id") for e in mouth.iter() if e.get("data-z-out")]
    # the vents are holes in the raised band, with the dark behind them flat
    sink = raised["sink"]
    assert sink.get("fill-rule") == "evenodd"
    back = [e for e in optic.iter() if (e.get("id") or "").endswith("--sink-back")]
    assert len(back) == 1 and back[0].get("data-z-out") is None


@pytest.mark.parametrize("device,cpath", [(MX80, "xe-1"), (MX960, "fpc6/module/port-1")])
def test_the_seated_xfp_head_stands_9_out_with_its_bail_on_the_front(seated, device, cpath):
    root, _ = seated[device]
    optic = by_path(root, f"{cpath}-occupant")
    raised = _raised(optic)
    assert set(raised) == {"body", "bail"}
    assert float(raised["body"].get("data-z-out")) == pytest.approx(9.0)
    bail = raised["bail"]
    assert float(bail.get("data-z-lift")) == pytest.approx(9.0)
    assert float(bail.get("data-z-bar")) == pytest.approx(1.3)
    assert bail.get("data-z-out") is None and bail.get("data-z-color") is None
    for pid in ("tx", "rx"):
        mouth = by_path(root, f"{cpath}-occupant/{pid}")
        assert float(mouth.get("data-z-lift")) == pytest.approx(9.0)


def test_the_seated_latches_are_the_default_grey(seated):
    root, _ = seated[AIS]
    for cage in ("port-1", "port-2"):
        tab = by_path(root, f"{cage}-occupant/tab")
        grip = [e for e in tab.iter() if (e.get("id") or "").endswith("--grip")]
        assert len(grip) == 1 and grip[0].get("fill") == GREY
    for device, cpath in ((MX80, "xe-1"), (MX960, "fpc6/module/port-1")):
        optic = by_path(seated[device][0], f"{cpath}-occupant")
        bail = [e for e in optic.iter() if (e.get("id") or "").endswith("--bail")]
        assert len(bail) == 1 and bail[0].get("fill") == GREY


def test_a_set_latch_colour_repaints_the_tab_and_the_bail():
    """The field at work: instanced with `latch-color` set, as a vendor
    wrapper sets it, the composed tab takes the colour from its host and the
    bail from its own node, and each outline follows its fill."""
    lib = render_mod.Library([str(LIB)])
    blue = "#2f5fa8"
    for ref, suffix, n in ((OSFP_LC, "--tab--grip", 1), (OSFP_MPO16, "--tab--arm-l", 1),
                           (XFP_LC, "--bail", 1)):
        g, _ = render_mod.instance_group(lib, ref, "o", [0, 0], None, {"latch-color": blue}, None, None)
        hits = [e for e in g.iter() if (e.get("id") or "").endswith(suffix)]
        assert len(hits) == n, (ref, suffix)
        assert hits[0].get("fill") == blue
        assert hits[0].get("stroke") == render_mod.stroke_shade(blue)
        # nothing else took it: the nose keeps its metal
        body = next(e for e in g.iter() if e.get("id") == "o--body")
        assert body.get("fill") != blue
