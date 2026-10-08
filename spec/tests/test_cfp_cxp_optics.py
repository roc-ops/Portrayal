"""Generic optics for the CFP, CFP2, CFP4 and CXP cages (docs/pluggables-cfp-cxp-design.md).

    generic/cfp-lc@1, generic/cfp-mpo@1      a CFP with two LC bores, or one MPO-24
    generic/cfp-sc@1                         a CFP with two SC openings
    generic/cfp2-lc@1, generic/cfp2-mpo@1    a CFP2 with two LC bores, or one MPO-24
    generic/cfp4-lc@1, generic/cfp4-mpo@1    a CFP4 with two LC bores, or one MPO-12
    generic/cxp-mpo@1                        an optical CXP with one MPO-24
    common/cfp-thumbscrew@1                  the knob the two CFP parts compose twice
    std/mpo24-module-receptacle@1            the two-row MPO mouth on a module
    cfp-module, cfp2-module, cfp4-module, cxp-module   the envelopes, with their heads

What each is, that its head fits the envelope its standard gives (L121), that
its receptacle is the right part the right way up and is a slot offering the
right plugs and dust cap (from a components.json built here by the indexer),
that every cage of each family now offers exactly its own optics and no other
cage does, and that each optic seats in a real cage with a plug or a cap
chained in it. No device places one of these cages directly, so every seat is
on a card in a chassis: juniper/mx480 and nokia/sr-1e upright, and
juniper/mx960 and nokia/nfxs-e-bb for a quarter-turned cage of each family.

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

CFP_LC, CFP_MPO = "generic/cfp-lc@1", "generic/cfp-mpo@1"
CFP_SC = "generic/cfp-sc@1"
CFP2_LC, CFP2_MPO = "generic/cfp2-lc@1", "generic/cfp2-mpo@1"
CFP4_LC, CFP4_MPO = "generic/cfp4-lc@1", "generic/cfp4-mpo@1"
CXP_MPO = "generic/cxp-mpo@1"
SCREW = "common/cfp-thumbscrew@1"
REC12 = "std/mpo-module-receptacle@1"
REC24 = "std/mpo24-module-receptacle@1"
BORE = "std/lc-bore@3"
SC_BORE = "std/sc-bore@1"
MPO12, MPO24, MPO_CAP = "generic/mpo12-plug@1", "generic/mpo24-plug@1", "common/mpo-dust-cap@2"
MPO_OFFER = {MPO12, MPO24, MPO_CAP}
LC_OFFER = {"generic/lc-plug@2", "common/lc-dust-cap@1"}
SCP, SCC = "generic/sc-plug@1", "common/sc-dust-cap@1"
SC_OFFER = {SCP, SCC}
GREY = "#6f6f6f"
LC2 = {"tx": (BORE, 180), "rx": (BORE, 180)}

# optic -> (mates, conforms, {receptacle part id: (ref, rotate)}, interface
#           presented, what each slot offers)
OPTICS = {
    CFP_LC: ("cfp", "cfp-module", LC2, "lc", LC_OFFER),
    CFP_MPO: ("cfp", "cfp-module", {"mpo": (REC24, 0)}, "mpo", MPO_OFFER),
    CFP_SC: ("cfp", "cfp-module", {"tx": (SC_BORE, 90), "rx": (SC_BORE, 90)}, "sc", SC_OFFER),
    CFP2_LC: ("cfp2", "cfp2-module", LC2, "lc", LC_OFFER),
    CFP2_MPO: ("cfp2", "cfp2-module", {"mpo": (REC24, 0)}, "mpo", MPO_OFFER),
    CFP4_LC: ("cfp4", "cfp4-module", LC2, "lc", LC_OFFER),
    CFP4_MPO: ("cfp4", "cfp4-module", {"mpo": (REC12, 0)}, "mpo", MPO_OFFER),
    CXP_MPO: ("cxp", "cxp-module", {"mpo": (REC24, 0)}, "mpo", MPO_OFFER),
}
EACH = pytest.mark.parametrize("ref", sorted(OPTICS))
LC = (CFP_LC, CFP2_LC, CFP4_LC)
MPO = (CFP_MPO, CFP2_MPO, CFP4_MPO, CXP_MPO)
BAILED = (CFP2_LC, CFP2_MPO, CFP4_LC, CFP4_MPO)
PAIRS = ((CFP_LC, CFP_MPO), (CFP2_LC, CFP2_MPO), (CFP4_LC, CFP4_MPO))
CFP = (CFP_LC, CFP_MPO, CFP_SC)

# optic -> (above the body, below it, length outside the cage, width)
HEADS = {
    CFP_LC: (0.2, 0.2, 14.5, 82.0), CFP_MPO: (0.2, 0.2, 14.5, 82.0), CFP_SC: (0.2, 0.2, 14.5, 82.0),
    CFP2_LC: (2.7, 1.6, 16.0, 42.5), CFP2_MPO: (2.7, 1.6, 16.0, 42.5),
    CFP4_LC: (3.1, 1.5, 16.0, 21.9), CFP4_MPO: (3.1, 1.5, 16.0, 21.9),
    CXP_MPO: (2.58, 1.61, 33.55, 23.9),
}
# the four registry envelopes: (w, h, depth, head, the longest the module may be)
ENVELOPES = {
    "cfp-module": (77.2, 13.6, 130.25,
                   {"w-max": 82.0, "above-max": 0.2, "below-max": 0.2, "length-max": 14.5}, 144.75),
    "cfp2-module": (41.5, 12.4, 91.5,
                    {"w-max": 42.5, "above-max": 3.4, "below-max": 1.6, "length-max": 20.1}, 107.5 + 4.1),
    "cfp4-module": (21.5, 9.5, 76.0,
                    {"w-max": 22.1, "above-max": 3.4, "below-max": 1.6, "length-max": 20.1}, 92.0 + 4.1),
    "cxp-module": (21.2, 9.81, 28.45,
                   {"w-max": 24.05, "above-max": 4.79, "below-max": 1.61, "length-max": 33.55}, 62.0),
}
# where the optical axis is, below the module top
AXIS = {CFP_LC: 6.8, CFP_MPO: 6.8, CFP_SC: 6.8, CFP2_LC: 6.79, CFP2_MPO: 6.79, CFP4_LC: 4.95, CFP4_MPO: 4.95,
        CXP_MPO: 4.6}


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


def box(el):
    return [float(el.get(k)) for k in ("x", "y", "width", "height")]


# --- the registry ------------------------------------------------------------

@pytest.mark.parametrize("key", sorted(ENVELOPES))
def test_the_module_envelope_and_its_head_are_the_standards_figures(key):
    w, h, depth, head, longest = ENVELOPES[key]
    e = standards()[key]
    assert (e["w"], e["h"], e["depth"]) == (w, h, depth)
    assert {k: e["head"][k] for k in head} == head
    assert e["head"]["source"].strip() and "length-kind" not in e["head"]
    assert e["confidence"] == e["depth-confidence"] == "verified" and e["depth-notes"]
    # the inserted length plus the head is the longest module the standard allows
    assert depth + head["length-max"] == pytest.approx(longest)


def test_the_cfp2_and_cfp4_heads_are_the_enlarged_section_plus_the_receptacle():
    """Both baseline drawings give the enlarged front section as the overall
    length less a minimum (16.0) and let the connector receptacle stand 4.10
    in front of it. The optics draw the section and not the receptacle nose."""
    for key, overall, behind in (("cfp2-module", 107.5, 91.5), ("cfp4-module", 92.0, 76.0)):
        e = standards()[key]
        assert e["depth"] == behind and overall - behind == 16.0
        assert e["head"]["length-max"] == pytest.approx(16.0 + 4.1)
    for ref in BAILED:
        assert doc(ref)["head"]["size"]["d"] == 16.0


# each cage's second major is the panel opening its document prints (#802):
# (w, h, depth, the cavity behind the opening, the module entry the cavity is)
CAGES = {
    "cfp": (82.8, 14.8, 126.15, (77.2, 13.6), "cfp-module"),
    "cfp2": (41.5, 14.3, 87.5, (41.5, 12.4), "cfp2-module"),
    "cfp4": (22.1, 11.3, 67.9, (21.5, 9.5), "cfp4-module"),
    "cxp": (23.5, 12.1, 28.96, (21.6, 10.2), None),
}


def test_each_cage_is_the_panel_opening_with_the_module_behind_it():
    """The four cages draw what std/sfp@1 and std/qsfp28@1 draw: the box is the
    panel opening, `d` the bezel to the connector, `relief.size` the interior a
    module runs back into, and the one 1.0 collar. Each cage and its registry
    entry carry the same figures, and a CFP family cage's cavity is its module
    entry's body. The envelope outside the cage stays on the MODULE entry."""
    std = standards()
    for name, (w, h, depth, cavity, module) in CAGES.items():
        cage = doc(f"std/{name}@2")
        assert cage["version"].startswith("2.") and cage["conforms"] == cage["interface"] == name
        assert (cage["size"]["w"], cage["size"]["h"], cage["size"]["d"]) == (w, h, depth)
        assert (std[name]["w"], std[name]["h"], std[name]["depth"]) == (w, h, depth)
        assert "head" not in std[name]
        rel = cage["relief"]
        assert (rel["size"]["w"], rel["size"]["h"]) == cavity
        assert (std[name]["cavity"]["w"], std[name]["cavity"]["h"]) == cavity
        assert rel["cavity"] == "cavity" and node(f"std/{name}@2", "cavity") is not None
        assert [(f["node"], f["out"]) for f in rel["features"]] == [("collar", 1.0)]
        assert cage["connection-points"]["mate"]["at"] == [w / 2, h / 2]
        if module:
            assert cavity == (std[module]["w"], std[module]["h"])
        # the first major is gone once nothing names it (L89)
        assert not path(f"std/{name}@1").exists()
    # a CXP plug's snout enters the SFF-8642 snout opening and stops short of
    # the connector; F05 27.00 Min is the floor
    plug = std["cxp-module"]
    assert plug["w"] < std["cxp"]["cavity"]["w"] and plug["h"] < std["cxp"]["cavity"]["h"]
    assert plug["depth"] < std["cxp"]["depth"] and std["cxp"]["pitch"] == 27.0
    # two CFP2 modules share one 86.35 opening (Baseline Drawing sheets 13-14),
    # so the floor is the A01 42.50 faceplate and not the first entry's 45.0
    assert std["cfp2"]["pitch"] == std["cfp2-module"]["head"]["w-max"] == 42.5 <= 86.35 / 2


def test_the_pluggables_rungs_name_what_they_rest_on():
    fam = yaml.safe_load((ROOT / "spec/schemas/pluggables.yaml").read_text())["families"]
    for name, needle in (("cfp", "Hardware Specification Rev 1.4"), ("cfp2", "Baseline Drawing Rev 1L"),
                         ("cfp4", "Baseline Drawing Rev R"), ("cxp", "SFF-8642 Rev 3.3")):
        assert fam[name]["interface"] == name and fam[name]["rates"] == [name]
        assert needle in fam[name]["source"] and "not held;" not in fam[name]["source"].split(needle)[0]
    text = (ROOT / "spec/schemas/pluggables.yaml").read_text()
    assert "working/" not in text


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
    assert d["unplaced"] and d["version"].startswith("1.0.") and d["skins"] == ["default"]
    # it seats centre on centre
    assert d["connection-points"]["mate"]["at"] == pytest.approx([d["size"]["w"] / 2, d["size"]["h"] / 2])
    assert doc(f"std/{mates}@2")["interface"] == mates


@EACH
def test_a_generic_states_no_rate_reach_wavelength_or_wattage(ref):
    d = doc(ref)
    assert not set(d["attrs"]) & set(lint.GENERIC_FORBIDDEN_ATTRS)
    assert d["attrs"]["form-factor"] == d["mates"]
    assert d["attrs"]["face"] == {BORE: "lc-duplex", SC_BORE: "sc-duplex", REC24: "mpo24", REC12: "mpo12"}[
        sorted(OPTICS[ref][2].values())[0][0]]
    with lint.collecting() as got:
        lint.lint_component_generic(path(ref) / "contract.yaml", d)
    assert not got.errors, got.errors


@EACH
def test_the_head_fits_the_envelope(ref):
    """L121, and the figures it is run on: above, below, length and width as
    the contract states them, measured the way the rule measures."""
    d = doc(ref)
    above, below, length, width = HEADS[ref]
    head = d["head"]
    assert max(0.0, -head["at"][1]) == pytest.approx(above)
    assert head["at"][1] + head["size"]["h"] - d["size"]["h"] == pytest.approx(below)
    assert head["size"]["d"] == pytest.approx(length)
    assert head["size"]["w"] == pytest.approx(width)
    assert not head.get("exceeds") and "type" not in head
    # centred on the body
    assert head["at"][0] == pytest.approx((d["size"]["w"] - width) / 2)
    env = standards()[d["conforms"]]["head"]
    assert width <= env["w-max"] and above <= env["above-max"] and below <= env["below-max"]
    assert length <= env["length-max"]
    with lint.collecting() as got:
        lint.lint_component_head(path(ref) / "contract.yaml", d)
    assert not [e for e in got.errors + got.warnings if "[L121]" in e], got.errors
    # the depth and the head are the whole module
    whole = {"cfp": 144.75, "cfp2": 107.5, "cfp4": 92.0, "cxp": 62.0}[d["mates"]]
    assert d["size"]["d"] + length == pytest.approx(whole)


@EACH
def test_the_head_node_is_the_skins_first_child_and_draws_the_head(ref):
    """`body` carries the box of the head and is the FIRST drawing child:
    render.py never raises the first child, so the face art drawn after it is
    not buried under the head in 2D or 3D."""
    d = doc(ref)
    assert d["head"]["node"] == "body"
    first = [c for c in skin(ref) if c.tag.rsplit("}", 1)[-1] not in ("title", "defs", "style")][0]
    assert first.get("id") == "body" and first.tag.endswith("rect")
    want = [*d["head"]["at"], d["head"]["size"]["w"], d["head"]["size"]["h"]]
    assert all(abs(a - b) <= lint.HEAD_NODE_TOL for a, b in zip(box(first), want)), (box(first), want)
    feats = {f["node"]: f for f in d["relief"]["features"]}
    assert feats["body"]["out"] == d["head"]["size"]["d"] and feats["body"]["confidence"] == "drawing"


@pytest.mark.parametrize("a,b", PAIRS + ((CFP_LC, CFP_SC),))
def test_the_two_faces_of_a_form_differ_only_in_the_face(a, b):
    da, db = doc(a), doc(b)
    same = ("size", "size-confidence", "head", "fields", "relief", "mates", "conforms", "class",
            "behaviour", "unplaced")
    assert {k: da[k] for k in same} == {k: db[k] for k in same}
    assert da["connection-points"]["mate"] == db["connection-points"]["mate"]
    art = lambda ref: {e.get("id"): dict(e.attrib) for e in skin(ref).iter()
                       if e.get("id") in ("body", "bail")}
    assert art(a) == art(b)
    other = lambda ref: [q for q in doc(ref)["parts"] if q["id"].startswith("screw")]
    assert other(a) == other(b)


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
        assert q["lift"] == depth, (ref, q["id"])       # all of it stands on the head front


@pytest.mark.parametrize("ref", LC)
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
    assert got["tx"][0] < got["rx"][0] and got["tx"][1] == got["rx"][1] == AXIS[ref]
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
    # the painted housing frames both openings
    x, y, w, h = box(node(ref, "opening"))
    assert x < part(ref, "tx")["at"][0] and part(ref, "rx")["at"][0] + core["size"]["w"] < x + w
    assert head["at"][1] <= y and y + h <= head["at"][1] + head["size"]["h"]


def test_the_two_sc_openings_lie_across_key_up_transmit_left_at_the_sc_duplex_pitch():
    """std/sc-bore@1 has its key slot on the left unrotated; at `rotate: 90`
    the 9.0 side lies across the module and the slot is in the top wall, as
    the MSA module drawing draws the face. The two are 12.7 apart, centred,
    on the line through the thumbscrew axes, with faceplate between them."""
    d = doc(CFP_SC)
    core = doc(SC_BORE)
    cps = d["connection-points"]
    got, spans = {}, {}
    for pid in ("tx", "rx"):
        p = part(CFP_SC, pid)
        assert (p["ref"], p["rotate"]) == (SC_BORE, 90)
        ferrule = seat_point(p["at"], core["size"], 90, core["connection-points"]["mate"]["at"])
        assert ferrule == pytest.approx(cps[f"optical-{pid}"]["at"])
        key = seat_point(p["at"], core["size"], 90, [0.0, core["size"]["h"] / 2])
        assert key[0] == pytest.approx(ferrule[0]) and key[1] < ferrule[1]       # the slot is above
        # the 7.5 x 9.0 opening itself, turned: 9.0 across, 7.5 up, centred on the ferrule
        a = seat_point(p["at"], core["size"], 90, [0.89, 0.0])
        b = seat_point(p["at"], core["size"], 90, [core["size"]["w"], core["size"]["h"]])
        xs, ys = sorted((a[0], b[0])), sorted((a[1], b[1]))
        assert xs[1] - xs[0] == pytest.approx(9.0) and ys[1] - ys[0] == pytest.approx(7.5)
        assert (xs[0] + xs[1]) / 2 == pytest.approx(ferrule[0])
        assert (ys[0] + ys[1]) / 2 == pytest.approx(ferrule[1])
        head = d["head"]
        assert head["at"][1] < key[1] and ys[1] < head["at"][1] + head["size"]["h"]
        got[pid], spans[pid] = ferrule, xs
    assert got["tx"][0] < got["rx"][0] and got["tx"][1] == got["rx"][1] == AXIS[CFP_SC]
    assert got["rx"][0] - got["tx"][0] == pytest.approx(12.7)
    assert (got["tx"][0] + got["rx"][0]) / 2 == pytest.approx(d["size"]["w"] / 2)
    assert spans["rx"][0] - spans["tx"][1] == pytest.approx(3.7)                 # faceplate between
    # clear of both knobs
    knob = doc(SCREW)["size"]["w"]
    left = part(CFP_SC, "screw-l")["at"][0] + knob
    right = part(CFP_SC, "screw-r")["at"][0]
    assert left < spans["tx"][0] and spans["rx"][1] < right
    letters = [t.text for t in skin(CFP_SC).iter() if t.tag.endswith("text") and t.text]
    assert letters == ["T", "R"]
    assert not [e for e in skin(CFP_SC).iter() if e.get("id") == "opening"]     # no painted housing
    prov = d["provenance"]
    assert "KEY SLOT UP" in prov["key"] and "TRANSMIT ON THE LEFT" in prov["sides"]
    assert "ESTIMATED" in prov["bores"] and "ESTIMATED" in prov["optical-axis"]


@pytest.mark.parametrize("ref", MPO)
def test_the_mpo_receptacle_is_key_up_and_centred_on_the_module(ref):
    """Unrotated, so the key notch is in the top wall, toward the module top,
    and the mouth and its insert are inside the head."""
    d = doc(ref)
    p = part(ref, "mpo")
    assert not p.get("rotate")
    core = doc(p["ref"])
    mate = [p["at"][0] + core["connection-points"]["mate"]["at"][0],
            p["at"][1] + core["connection-points"]["mate"]["at"][1]]
    assert mate == pytest.approx(d["connection-points"]["optical"]["at"])
    assert mate[0] == pytest.approx(d["size"]["w"] / 2) and mate[1] == pytest.approx(AXIS[ref])
    key = node(p["ref"], "keyway")
    assert float(key.get("x")) + float(key.get("width")) / 2 == pytest.approx(core["size"]["w"] / 2)
    assert float(key.get("y")) < core["size"]["h"] / 4
    head = d["head"]
    assert head["at"][1] <= p["at"][1]
    assert p["at"][1] + core["size"]["h"] <= head["at"][1] + head["size"]["h"]
    x, y, w, h = box(node(ref, "insert"))
    assert x + w / 2 == pytest.approx(mate[0]) and y + h / 2 == pytest.approx(mate[1])
    assert x < p["at"][0] and p["at"][0] + core["size"]["w"] < x + w
    assert head["at"][1] <= y and y + h <= head["at"][1] + head["size"]["h"]
    assert core["optical"]["positions"] == (12 if ref == CFP4_MPO else 24)
    assert "PINNED" in d["provenance"]["gender"] and "KEY UP" in d["provenance"]["key"]


def test_an_lc_and_an_mpo_face_of_one_form_share_an_optical_axis_height():
    for a, b in PAIRS:
        assert doc(a)["connection-points"]["optical-tx"]["at"][1] == \
            doc(b)["connection-points"]["optical"]["at"][1] == AXIS[a]
    # on a CFP it is the line through the two thumbscrew axes, the body mid-height
    assert AXIS[CFP_LC] == doc(CFP_LC)["size"]["h"] / 2


# --- the two-row module receptacle --------------------------------------------

def test_the_mpo24_module_receptacle_is_the_mpo_mouth_with_a_two_row_ferrule():
    a, b = doc(REC12), doc(REC24)
    same = ("interface", "class", "conforms", "size", "size-confidence", "attrs", "connection-points")
    assert {k: a[k] for k in same} == {k: b[k] for k in same}
    assert b["interface"] == "mpo" and b["optical"] == {"positions": 24} and b["version"] == "1.0.0"
    assert a["relief"] == b["relief"]
    art = lambda ref: {e.get("id"): dict(e.attrib) for e in skin(ref).iter()
                       if e.get("id") in ("opening", "keyway", "ferrule", "pin-l", "pin-r")}
    assert art(REC12) == art(REC24)
    fibres = {k: v for k, v in b["elements"].items() if k != "opening"}
    assert sorted(fibres, key=int) == [str(i) for i in range(1, 25)]
    assert all(v["class"] == "fibre" and v["size"] == [0.125, 0.125] for v in fibres.values())
    centre = lambda n: (fibres[str(n)]["at"][0] + 0.0625, fibres[str(n)]["at"][1] + 0.0625)
    for row, first in ((0, 1), (1, 13)):
        xs = [centre(first + i)[0] for i in range(12)]
        assert all(a_ - b_ == pytest.approx(0.25) for a_, b_ in zip(xs, xs[1:]))    # 1 at the right
        assert {round(centre(first + i)[1], 4) for i in range(12)} == {3.75 + 0.5 * row}
        assert (xs[0] + xs[-1]) / 2 == pytest.approx(b["connection-points"]["mate"]["at"][0])
    # the rows straddle the ferrule centre, 0.50 apart, the key-side row first
    assert centre(13)[1] - centre(1)[1] == pytest.approx(0.5)
    assert (centre(1)[1] + centre(13)[1]) / 2 == b["connection-points"]["mate"]["at"][1]
    x, y, w, h = box(node(REC24, "ferrule"))
    for n in range(1, 25):
        el = node(REC24, str(n))
        assert (float(el.get("cx")), float(el.get("cy"))) == pytest.approx(centre(n))
        assert x < centre(n)[0] < x + w and y < centre(n)[1] < y + h
    assert "0.50mm between rows" in b["provenance"]["fibre-positions"]
    assert MPO12 in b["provenance"]["slot"] and MPO24 in b["provenance"]["slot"]


def test_position_n_of_the_two_row_receptacle_is_under_fibre_n_of_the_seated_plug():
    """Mate point on mate point, unturned: each of the twenty-four fibres of
    generic/mpo24-plug@1 lands on the receptacle position with its number."""
    rec, plug = doc(REC24), doc(MPO24)
    rm, pm = rec["connection-points"]["mate"]["at"], plug["connection-points"]["mate"]["at"]
    for n in range(1, 25):
        r, p = rec["elements"][str(n)], plug["elements"][str(n)]
        here = (r["at"][0] + r["size"][0] / 2 - rm[0], r["at"][1] + r["size"][1] / 2 - rm[1])
        there = (p["at"][0] + p["size"][0] / 2 - pm[0], p["at"][1] + p["size"][1] / 2 - pm[1])
        assert here == pytest.approx(there), n


# --- thumbscrews, bails and the tab -------------------------------------------

def test_the_cfp_thumbscrew_is_a_knurled_knob_painted_by_a_field():
    d = doc(SCREW)
    assert d["class"] == "screw" and "behaviour" not in d and "mates" not in d
    assert d["size"] == {"w": 9.2, "h": 9.2} and d["size-confidence"] == {"w": "estimated", "h": "estimated"}
    assert d["size-notes"] and d["elements"] == {"knob": {"at": [0.0, 0.0], "size": [9.2, 9.2], "class": "screw"}}
    (f,) = d["relief"]["features"]
    assert (f["node"], f["cyl"], f["knurl"], f["confidence"]) == ("knob", 9.5, True, "drawing")
    assert "color" not in f                                                  # L73: a field paints it
    knob = node(SCREW, "knob")
    assert knob.tag.endswith("circle") and float(knob.get("r")) == 4.6
    assert knob.get("data-fill-from") == knob.get("data-stroke-derive") == "latch-color"
    assert d["fields"]["latch-color"]["default"] == GREY and d["skins"] == ["default"]


@pytest.mark.parametrize("ref", CFP)
def test_a_cfp_has_two_thumbscrews_72_apart_on_the_faceplate_and_no_tab(ref):
    d = doc(ref)
    knob = doc(SCREW)["size"]
    screws = {q["id"]: q for q in d["parts"] if q["ref"] == SCREW}
    assert set(screws) == {"screw-l", "screw-r"}
    cx = {k: q["at"][0] + knob["w"] / 2 for k, q in screws.items()}
    cy = {q["at"][1] + knob["h"] / 2 for q in screws.values()}
    assert cx["screw-r"] - cx["screw-l"] == pytest.approx(72.0)
    assert (cx["screw-l"] + cx["screw-r"]) / 2 == pytest.approx(d["size"]["w"] / 2)
    assert all(y == pytest.approx(d["size"]["h"] / 2) for y in cy)    # M1 2.60 above datum A
    head = d["head"]
    for q in screws.values():
        assert q["lift"] == head["size"]["d"] == 14.5
        assert head["at"][0] <= q["at"][0] and q["at"][0] + knob["w"] <= head["at"][0] + head["size"]["w"]
        assert head["at"][1] <= q["at"][1] and q["at"][1] + knob["h"] <= head["at"][1] + head["size"]["h"]
    assert not [q for q in d["parts"] if "tab" in q["id"] or "tab" in q["ref"]]
    assert not [e.get("id") for e in skin(ref).iter() if e.get("id") in ("bail", "grip")]
    assert {f["node"] for f in d["relief"]["features"]} == {"body"}
    with lint.collecting() as got:
        lint.lint_component_collisions(path(ref) / "contract.yaml", d, [str(LIB)])
    assert not got.warnings and not got.errors, got.warnings


@pytest.mark.parametrize("ref", BAILED)
def test_the_bail_is_a_field_painted_bar_across_the_top_of_the_head(ref):
    d = doc(ref)
    bail = node(ref, "bail")
    assert bail.get("data-fill-from") == bail.get("data-stroke-derive") == "latch-color"
    x, y, w, h = box(bail)
    head = d["head"]
    assert y == pytest.approx(head["at"][1] + 0.1) and y + h < 0          # above the body
    assert w == pytest.approx(head["size"]["w"] - 0.2)
    assert h == {"cfp2": 1.9, "cfp4": 1.1}[d["mates"]]
    feats = {f["node"]: f for f in d["relief"]["features"]}
    assert set(feats) == {"body", "bail"}
    assert "color" not in feats["bail"]                                  # L73: a field paints it
    assert feats["bail"]["lift"] == head["size"]["d"] == 16.0 and feats["bail"]["bar"] == pytest.approx(h)
    assert feats["bail"]["confidence"] == "estimated"
    # the bar is clear of the receptacle
    for q in d["parts"]:
        assert q["at"][1] > y + h, q["id"]
    assert "tab" not in [q["id"] for q in d["parts"]]


def test_the_cxp_tab_is_a_loop_from_the_body_top_ending_where_the_vendor_prints_it():
    """Two arms and an end bar, nodes of the optic's own skin: each starts at
    or past the head front, so L121 leaves it alone, and each box starts where
    the one before it ends. The tip is 82.2 from the bezel plane."""
    d = doc(CXP_MPO)
    head = d["head"]
    feats = {f["node"]: f for f in d["relief"]["features"]}
    assert set(feats) == {"body", "arm-l", "arm-r", "grip"}
    for side in "lr":
        arm = feats[f"arm-{side}"]
        assert arm["lift"] == head["size"]["d"] and arm["out"] == feats["grip"]["lift"]
    assert feats["grip"]["out"] == 82.2 and feats["grip"]["confidence"] == "datasheet"
    assert not [n for n, f in feats.items() if n != "body" and "color" in f]          # L73
    al, ar, grip = box(node(CXP_MPO, "arm-l")), box(node(CXP_MPO, "arm-r")), box(node(CXP_MPO, "grip"))
    assert al[2] == ar[2] == 3.1 and grip[2] == 19.7 == pytest.approx(ar[0] + ar[2] - al[0])
    assert ar[0] - (al[0] + al[2]) == pytest.approx(13.5)                 # the printed opening
    assert grip[0] + grip[2] / 2 == pytest.approx(d["size"]["w"] / 2)
    for b in (al, ar, grip):
        assert b[1] == pytest.approx(head["at"][1] + 0.1) and b[3] == 1.5
        assert b[1] + b[3] < part(CXP_MPO, "mpo")["at"][1]                 # above the mouth
        assert b[1] + b[3] <= box(node(CXP_MPO, "insert"))[1]
    for nid in ("arm-l", "arm-r", "grip"):
        el = node(CXP_MPO, nid)
        assert el.get("data-fill-from") == el.get("data-stroke-derive") == "latch-color"
    order = [c.get("id") for c in skin(CXP_MPO) if c.get("id")]
    assert order[0] == "body" and order.index("arm-l") < order.index("grip")
    assert [q["id"] for q in d["parts"]] == ["mpo"]


@EACH
def test_the_latch_colour_is_a_field_and_defaults_to_the_neutral_grey(ref):
    d = doc(ref)
    assert set(d["fields"]) == {"latch-color", "label"}
    assert d["fields"]["latch-color"]["default"] == GREY
    assert d["skins"] == ["default"]                # a colour is a field, never a second skin
    assert node(ref, "label").get("data-from") == "label"
    prov = d["provenance"]
    note = prov.get("knob-colour") or prov.get("bail-colour") or prov["tab-colour"]
    assert "A FIELD" in note and "wrapper" in note
    # no logo, and no lettering but T and R
    texts = [t.text for t in skin(ref).iter() if t.tag.endswith("text") and t.text]
    assert texts in ([], ["T", "R"])


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
def test_each_receptacle_is_a_slot_offering_its_plugs_and_cap(comps, ref):
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
            assert slot["rotate"] == want[pid][1]
    assert comps[ref]["head"]["size"]["d"] == d["head"]["size"]["d"]


def test_an_mpo_slot_offers_both_centre_key_plugs_and_no_sixteen_fibre_one(comps):
    """The accept list is the interface's, and `mpo` is the housing and its
    centred key: the twelve- and the twenty-four-fibre plug and the one dust
    cap, on the one-row and the two-row receptacle alike. The offset-key
    MPO-16 parts are another interface."""
    for ref in MPO:
        offered = set(comps[ref]["presents"]["accepts"])
        assert offered == MPO_OFFER
        assert not offered & {"generic/mpo16-plug@1", "common/mpo16-dust-cap@1"}
    for plug in (MPO12, MPO24, MPO_CAP):
        assert doc(plug)["mates"] == "mpo"


# --- what the cages offer, across the whole library ---------------------------

OFFERS = {"cfp": [CFP_LC, CFP_MPO, CFP_SC], "cfp2": [CFP2_LC, CFP2_MPO], "cfp4": [CFP4_LC, CFP4_MPO],
          "cxp": [CXP_MPO]}
NEW = set(OPTICS)
# how many cages of each family the library's cards carry today, as a floor
# #261 removed the MX960 vertical twins: mpc4e-3d-2cge-8xge-v960 took two CFP cages
# with it and mpc5e-100g10g-v960 two CFP2, and the MX960 now seats the horizontal cards.
ON_CARDS = {"cfp": 6, "cfp2": 14, "cfp4": 4, "cxp": 6}


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
def test_every_cage_of_the_family_offers_exactly_its_own_optics(device_cages, comps, family):
    """Every placement of these four cages is on a card, so the cages are
    read off the cards (and off any device that comes to place one)."""
    on_devices = [c for _, c in device_cages if c["interface"] == family]
    on_cards = [s for ref, e in comps.items() for s in (e.get("cages") or [])
                if s["interface"] == family and s["kind"] == "cage"]
    assert len(on_cards) >= ON_CARDS[family], (family, len(on_cards))
    for c in on_devices + on_cards:
        assert c["accepts"] == OFFERS[family], (c["id"], c["accepts"])


def test_no_other_family_offers_them_and_each_pool_is_its_family(device_cages, comps):
    others = [c for _, c in device_cages if c["interface"] not in OFFERS]
    others += [s for e in comps.values() for s in _slots(e) if s["interface"] not in OFFERS]
    assert len(others) > 3000
    for c in others:
        assert not NEW & set(c["accepts"]), (c.get("id"), c["interface"])
    pool = render_mod._pluggable_candidates([LIB])
    for family, want in OFFERS.items():
        assert sorted(r for r, _ in pool[family]) == want, family
    # a CFP2 optic is not offered to a CFP or a CFP4 cage: four interfaces, four rungs
    fam = render_mod._pluggable_families()
    for family in OFFERS:
        assert fam[family]["interface"] == family and not fam[family].get("also-accepts")


# --- seated in real cages on real cards, a plug or a cap chained in ------------

MX480, MX960, SR1E, NFXS = "juniper/mx480", "juniper/mx960", "nokia/sr-1e", "nokia/nfxs-e-bb"
LCP, LCC = "generic/lc-plug@2", "common/lc-dust-cap@1"
BAYS = {
    MX480: {"dpc5": "juniper/mpc4e-3d-2cge-8xge@2", "dpc2": "juniper/mpc4e-3d-2cge-8xge@2",
            "dpc3": "juniper/mpc5e-100g10g@2",
            "dpc4": "juniper/mpc3e-3d@3", "dpc4/mic0": "juniper/mic3-3d-1x100ge-cxp@2"},
    # the MX960 seats the SAME horizontal cards, turned 90 by the bay (#261): a
    # cage on them is drawn at rotate 0 and takes its quarter turn from its card
    MX960: {"fpc2": "juniper/mpc4e-3d-2cge-8xge@2", "fpc5": "juniper/mpc4e-3d-2cge-8xge@2",
            "fpc3": "juniper/mpc5e-100g10g@2",
            "fpc4": "juniper/mpc3e-3d@3", "fpc4/mic0": "juniper/mic3-3d-1x100ge-cxp@2"},
    SR1E: {"mda-1-1": "nokia/me2-100gb-cfp4@1"},
    # the one turned CFP4 cage in the library, on the tilted face of an NT card
    NFXS: {"nt-b": "nokia/fant-g-ba@1"},
}
CONFIG = {MX480: "base", MX960: "base", SR1E: "base", NFXS: "fant-h-simplex"}
# THE TURN A CAGE INHERITS FROM THE BAY ITS CARD SITS IN. The MX960's cards are
# the horizontal ones at `rotate: 90`, so the quarter turn is on the card and the
# cage is drawn upright inside it; the FANT-G's cage is turned on its own card.
# The last field of a seat is the turn the seat is exercised in, either way.
CARD_TURN = {MX960: 90}
# (device, cage key, cage path, optic, {slot key suffix: occupant}, the cage's turn)
SEATS = [
    (MX480, "dpc5/port-1-0", "dpc5/module/port-1-0", CFP_LC, {"/tx": LCP, "/rx": LCC}, 0),
    (MX480, "dpc5/port-3-0", "dpc5/module/port-3-0", CFP_MPO, {"": MPO24}, 0),
    (MX480, "dpc2/port-1-0", "dpc2/module/port-1-0", CFP_SC, {"/tx": SCP, "/rx": SCC}, 0),
    (MX480, "dpc3/port-1-0", "dpc3/module/port-1-0", CFP2_LC, {"/tx": LCP}, 0),
    (MX480, "dpc3/port-2-0", "dpc3/module/port-2-0", CFP2_MPO, {"": MPO_CAP}, 0),
    (MX480, "dpc4/mic0/port-0-0", "dpc4/module/mic0/module/port-0-0", CXP_MPO, {"": MPO24}, 0),
    (SR1E, "mda-1-1/port-1", "mda-1-1/module/port-1", CFP4_LC, {"/tx": LCP, "/rx": LCC}, 0),
    (SR1E, "mda-1-1/port-2", "mda-1-1/module/port-2", CFP4_MPO, {"": MPO12}, 0),
    (MX960, "fpc2/port-1-0", "fpc2/module/port-1-0", CFP_MPO, {"": MPO_CAP}, 90),
    (MX960, "fpc2/port-3-0", "fpc2/module/port-3-0", CFP_LC, {"/rx": LCP}, 90),
    (MX960, "fpc5/port-1-0", "fpc5/module/port-1-0", CFP_SC, {"/rx": SCP}, 90),
    (MX960, "fpc3/port-1-0", "fpc3/module/port-1-0", CFP2_MPO, {"": MPO24}, 90),
    (MX960, "fpc3/port-2-0", "fpc3/module/port-2-0", CFP2_LC, {"/tx": LCC}, 90),
    (MX960, "fpc4/mic0/port-0-0", "fpc4/module/mic0/module/port-0-0", CXP_MPO, {"": MPO_CAP}, 90),
    (NFXS, "nt-b/cfp4-1", "nt-b/module/cfp4-1", CFP4_MPO, {"": MPO_CAP}, 90),
]
EACH_SEAT = pytest.mark.parametrize(
    "seat", SEATS, ids=[f"{s[0].split('/')[1]}:{s[1]}:{s[3].split('/')[1][:-2]}" for s in SEATS])


def test_every_optic_is_seated_upright_and_every_family_turned():
    upright = {s[3] for s in SEATS if s[5] == 0}
    turned = {doc(s[3])["mates"] for s in SEATS if s[5] == 90}
    assert upright == set(OPTICS) and turned == set(OFFERS)


def _build(tmp, device):
    name = device.split("/")[1]
    dev = tmp / name / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"][CONFIG[device]]
    occ = {}
    for dv, key, _, optic, chain, _ in SEATS:
        if dv != device:
            continue
        occ[key] = optic
        for suffix, ref in chain.items():
            occ[f"{key}-occupant{suffix}"] = ref
    cfg["occupants"] = occ
    cfg["bays"] = {**(cfg.get("bays") or {}), **BAYS[device]}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / f"out-{name}"
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(face_file(out, name, CONFIG[device], "front")).getroot()
    return root, {c: p for p in root.iter() for c in p}


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    """One build per chassis, each a copy with the cards in its bays, the
    optics in their cages and the plugs and caps chained in."""
    tmp = tmp_path_factory.mktemp("cfp-cxp")
    return {device: _build(tmp, device) for device in BAYS}


def _turn(el):
    t = el.get("transform") or ""
    return int(float(t.split("rotate(")[1].split(",")[0].split(")")[0].split()[0])) % 360 \
        if "rotate(" in t else 0


@EACH_SEAT
def test_it_seats_in_a_real_cage_on_a_real_card_with_its_plug_or_cap(seated, seat):
    device, _, cpath, ref, chain, turn = seat
    root, parents = seated[device]
    cage = by_path(root, cpath)
    optic = by_path(root, f"{cpath}-occupant")
    d = doc(ref)
    assert cage.get("data-ref", "").startswith(f"std/{d['mates']}@2")
    assert optic.get("data-ref", "").startswith(ref)
    # the optic takes its cage's turn, and the cage's turn plus its card's is the seat's
    inherited = CARD_TURN.get(device, 0)
    assert _turn(optic) == _turn(cage)
    assert (_turn(cage) + inherited) % 360 == turn
    if device in CARD_TURN:
        assert _turn(by_path(root, cpath.split("/")[0] + "/module")) == inherited
    # the card is a module seated in a bay of the chassis, and the cage is inside it
    card = by_path(root, cpath.rsplit("/module/", 1)[0] + "/module")
    assert BAYS[device][cpath.split("/module")[0] if cpath.count("/module/") == 1
                        else "/".join(cpath.replace("/module", "").split("/")[:2])] \
        .startswith(card.get("data-ref").rsplit(":", 1)[0].rsplit("@", 1)[0])
    # the optic is centred on the mate point of the cage - to the precision the
    # drawing is written at: a facet's foreshortening is written as
    # `scale(1, cos)` to six significant digits (facets.scale_transform), so
    # cos 45 reads 0.707107, 2.2e-7 off, and a point ~17 mm along the facet
    # carries ~4e-6 of it. The CFP4 on the FANT-G's 45 degree tooth (#802) is
    # the case; a seat that is truly off is off by tenths, not millionths.
    cx, cy = device_point(parents, cage, cage_mate(cage))
    ox, oy = device_point(parents, optic, own_mate(optic))
    assert abs(cx - ox) < 1e-5 and abs(cy - oy) < 1e-5
    depth = d["head"]["size"]["d"]
    for suffix, want in chain.items():
        occ = by_path(root, f"{cpath}-occupant{suffix}-occupant")
        assert occ.get("data-ref", "").startswith(want)
        point = d["connection-points"]["optical" + suffix.replace("/", "-")]["at"]
        rx, ry = device_point(parents, optic, point)
        px, py = device_point(parents, occ, own_mate(occ))
        # a tenth of a micron: the chain on the FANT-G goes through a bay
        # turned 270, a tilted facet and a cage turned 90, and the build
        # writes each transform to a fixed number of places
        assert abs(rx - px) < 1e-4 and abs(ry - py) < 1e-4
        # and it stands on the front of the head, not on the cage face
        assert float(occ.get("data-z-lift")) == pytest.approx(depth)


@EACH_SEAT
def test_the_seated_head_is_centred_on_its_opening_and_near_its_width(seated, seat):
    """The head is centred on the cage, and since the cages became the panel
    openings (#802) a head and its opening are within a millimetre of each
    other across: a CFP faceplate (82.0) and a CFP4 head (21.9) pass inside
    their openings (82.8, 22.1), and a CFP2 head (42.5) and a CXP plug body
    (23.9) stand over theirs (41.5, 23.5)."""
    device, _, cpath, ref, _, _ = seat
    d = doc(ref)
    cage = doc(f"std/{d['mates']}@2")["size"]
    head = d["head"]
    off = (cage["w"] - d["size"]["w"]) / 2          # the optic's x origin in the cage frame
    left, right = off + head["at"][0], off + head["at"][0] + head["size"]["w"]
    assert left + right == pytest.approx(cage["w"])
    assert abs((right - left) - cage["w"]) <= 1.0


def test_a_quarter_turned_seat_keeps_transmit_at_the_same_end_as_the_latch_side(seated):
    """A card standing upright turns its cage 90, and the optic takes the
    turn from the cage: the module top is toward one side of the slot and
    transmit toward the top of the chassis or the bottom, together."""
    root, parents = seated[MX960]
    for cpath, ref, pitch in (("fpc2/module/port-3-0", CFP_LC, 6.25), ("fpc3/module/port-2-0", CFP2_LC, 6.25),
                              ("fpc5/module/port-1-0", CFP_SC, 12.7)):
        d = doc(ref)
        optic = by_path(root, f"{cpath}-occupant")
        w, h = d["size"]["w"], d["size"]["h"]
        top, bottom = device_point(parents, optic, [w / 2, 0]), device_point(parents, optic, [w / 2, h])
        tx = device_point(parents, optic, d["connection-points"]["optical-tx"]["at"])
        rx = device_point(parents, optic, d["connection-points"]["optical-rx"]["at"])
        assert abs(top[1] - bottom[1]) < 1e-6 and abs(tx[0] - rx[0]) < 1e-6      # turned a quarter
        assert abs(abs(tx[1] - rx[1]) - pitch) < 1e-6
        # the same hand as upright: top, then transmit, turn the same way round
        cross = (top[0] - bottom[0]) * (rx[1] - tx[1]) - (top[1] - bottom[1]) * (rx[0] - tx[0])
        up = by_path(seated[MX480][0], {CFP_LC: "dpc5/module/port-1-0", CFP2_LC: "dpc3/module/port-1-0",
                                        CFP_SC: "dpc2/module/port-1-0"}[ref] + "-occupant")
        p = seated[MX480][1]
        t0, b0 = device_point(p, up, [w / 2, 0]), device_point(p, up, [w / 2, h])
        tx0 = device_point(p, up, d["connection-points"]["optical-tx"]["at"])
        rx0 = device_point(p, up, d["connection-points"]["optical-rx"]["at"])
        cross0 = (t0[0] - b0[0]) * (rx0[1] - tx0[1]) - (t0[1] - b0[1]) * (rx0[0] - tx0[0])
        assert cross * cross0 > 0 and t0[1] < b0[1] and tx0[0] < rx0[0]


@pytest.mark.parametrize("device,cpath,ref,plug", [
    (MX480, "dpc5/module/port-3-0", CFP_MPO, MPO24),
    (MX480, "dpc4/module/mic0/module/port-0-0", CXP_MPO, MPO24),
    (MX960, "fpc3/module/port-1-0", CFP2_MPO, MPO24),
])
def test_the_seated_mpo24_plug_has_its_key_up_and_its_fibres_on_the_receptacles(seated, device, cpath, ref, plug):
    root, parents = seated[device]
    optic = by_path(root, f"{cpath}-occupant")
    occ = by_path(root, f"{cpath}-occupant-occupant")
    d, pd = doc(ref), doc(plug)
    # the plug's key rib is on its top, toward the module top
    k = device_point(parents, occ, [pd["size"]["w"] / 2, 0.0])
    top = device_point(parents, optic, [d["size"]["w"] / 2, d["head"]["at"][1]])
    belly = device_point(parents, optic, [d["size"]["w"] / 2, d["head"]["at"][1] + d["head"]["size"]["h"]])
    dist = lambda a, b: ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
    assert dist(k, top) < dist(k, belly)
    for i in range(1, 25):
        f = by_path(root, f"{cpath}-occupant/mpo/{i}")
        assert f.get("data-class") == "fibre"
        here = device_point(parents, f, [float(f.get("cx")), float(f.get("cy"))])
        a = pd["elements"][str(i)]
        there = device_point(parents, occ, [a["at"][0] + a["size"][0] / 2, a["at"][1] + a["size"][1] / 2])
        assert here == pytest.approx(there, abs=1e-6), i


def _raised(optic):
    oid = optic.get("id")
    keys = ("data-z-out", "data-z-bar", "data-z-cyl")
    return {e.get("id")[len(oid) + 2:]: e for e in optic.iter()
            if (e.get("id") or "").startswith(oid + "--")
            and "-occupant--" not in e.get("id")[len(oid):]         # a seated plug is its own part
            and any(e.get(k) for k in keys)}


@EACH_SEAT
def test_the_seated_optic_is_built_right_side_out_in_3d(seated, seat):
    """Read off the compiled relief, upright and turned: the head front the
    head's length from the cage face, the receptacle cavities cut from that
    front, and whatever a hand takes hold of standing on it - the two knobs
    of a CFP, the bail bar of a CFP2 or CFP4, the loop of a CXP."""
    device, _, cpath, ref, _, _ = seat
    root, _ = seated[device]
    optic = by_path(root, f"{cpath}-occupant")
    d = doc(ref)
    depth = d["head"]["size"]["d"]
    raised = _raised(optic)
    assert float(raised["body"].get("data-z-out")) == pytest.approx(depth)
    for pid in OPTICS[ref][2]:
        mouth = by_path(root, f"{cpath}-occupant/{pid}")
        assert float(mouth.get("data-z-lift")) == pytest.approx(depth)
        cavity = [e for e in mouth.iter() if e.get("data-depth")]
        assert cavity and all(float(e.get("data-depth")) > 0 for e in cavity)
        assert not [e.get("id") for e in mouth.iter() if e.get("data-z-out")]
    family = d["mates"]
    if family == "cfp":
        assert set(raised) == {"body", "screw-l--knob", "screw-r--knob"}
        for side in "lr":
            screw = by_path(root, f"{cpath}-occupant/screw-{side}")
            assert float(screw.get("data-z-lift")) == pytest.approx(14.5)
            knob = raised[f"screw-{side}--knob"]
            assert float(knob.get("data-z-cyl")) == pytest.approx(9.5) and knob.get("data-z-knurl")
            assert knob.get("data-z-color") is None and knob.get("fill") == GREY
    elif family in ("cfp2", "cfp4"):
        assert set(raised) == {"body", "bail"}
        bail = raised["bail"]
        assert float(bail.get("data-z-lift")) == pytest.approx(16.0)
        assert float(bail.get("data-z-bar")) == pytest.approx({"cfp2": 1.9, "cfp4": 1.1}[family])
        assert bail.get("data-z-out") is None and bail.get("data-z-color") is None
        assert bail.get("fill") == GREY
    else:
        assert set(raised) == {"body", "arm-l", "arm-r", "grip"}
        for side in "lr":
            arm = raised[f"arm-{side}"]
            assert float(arm.get("data-z-lift")) == pytest.approx(33.55)
            assert float(arm.get("data-z-out")) == pytest.approx(79.1)
        grip = raised["grip"]
        assert float(grip.get("data-z-lift")) == pytest.approx(79.1)
        assert float(grip.get("data-z-out")) == pytest.approx(82.2)
        assert max(float(e.get("data-z-out")) for e in raised.values()) == pytest.approx(82.2)
        assert all(raised[n].get("data-z-color") is None and raised[n].get("fill") == GREY
                   for n in ("arm-l", "arm-r", "grip"))


def test_a_set_latch_colour_repaints_the_knobs_the_bail_and_the_tab():
    """The field at work: instanced with `latch-color` set, as a vendor
    wrapper sets it, the composed thumbscrews take the colour from their
    host and the bail and the tab from their own nodes, and each outline
    follows its fill. The head keeps its metal."""
    lib = render_mod.Library([str(LIB)])
    blue = "#2f5fa8"
    cases = [(CFP_LC, ("--screw-l--knob", "--screw-r--knob")), (CFP_MPO, ("--screw-l--knob",)),
             (CFP_SC, ("--screw-l--knob", "--screw-r--knob")),
             (CFP2_LC, ("--bail",)), (CFP2_MPO, ("--bail",)), (CFP4_LC, ("--bail",)),
             (CFP4_MPO, ("--bail",)), (CXP_MPO, ("--arm-l", "--arm-r", "--grip"))]
    assert {c[0] for c in cases} == set(OPTICS)
    for ref, suffixes in cases:
        g, _ = render_mod.instance_group(lib, ref, "o", [0, 0], None, {"latch-color": blue}, None, None)
        for suffix in suffixes:
            hits = [e for e in g.iter() if (e.get("id") or "").endswith(suffix)]
            assert len(hits) == 1, (ref, suffix)
            assert hits[0].get("fill") == blue
            assert hits[0].get("stroke") == render_mod.stroke_shade(blue)
        body = next(e for e in g.iter() if e.get("id") == "o--body")
        assert body.get("fill") != blue
