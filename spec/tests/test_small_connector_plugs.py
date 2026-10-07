"""MRJ21, VHDCI and RJ11 jacks are connector slots, and the cable plugs that
seat in them (#790, docs/connectors-mrj21-vhdci-rj11-design.md).

std/mrj21@1, common/vhdci-receptacle@1 and common/rj11-jack@1 each present an
interface spec/schemas/connectors.yaml now lists, so every one of them is a
slot; generic/mrj21-plug@1, generic/vhdci-plug@1 and generic/rj11-plug@1 mate
them. Every MRJ21 and VHDCI jack the library places is on a card, so those
seats are nested: the MRJ21 one two bays down, on an MDA in an IOM in a
chassis. These run against the real library, a components.json the indexer
builds here and device copies rendered here, never a possibly stale dist.
Nothing is rasterised.

THE SEATED DEPTH IS A RULING PER PLUG, and the tests below hold the parts to
it. The MRJ21 and VHDCI jacks model no depth, so there is no modelled floor to
compare; a test here fails by design when one gains a depth, because each
plug's provenance says it states none. The RJ11 jack gained its housing's
20.57 (#837), which is not a plug stop, and its plug says so.
"""
import json
import shutil
import subprocess
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
from test_coax_slots import _card_slot, _contract, _skin_path
from test_head_3d import apply, box, lift_of
from test_lifted_seat_js import build_components, mismatches, skin_file, spec_of
from test_nested_occupants import (assert_same_turn, by_path, cage_mate, device_matrix,
                                   device_point, own_mate)
from test_nested_slots_js import built_occupant

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
EPS = 1e-6
STUB = 30.0

MRJ21, VHDCI, RJ11 = "generic/mrj21-plug@1", "generic/vhdci-plug@1", "generic/rj11-plug@1"
# interface -> (the jack that presents it, the plug that mates it)
PAIRS = {
    "mrj21": ("std/mrj21@1", MRJ21),
    "vhdci": ("common/vhdci-receptacle@1", VHDCI),
    "rj11": ("common/rj11-jack@1", RJ11),
}
JACK_OF = {plug: jack for jack, plug in PAIRS.values()}
IFACE_OF = {plug: iface for iface, (_jack, plug) in PAIRS.items()}
JACK_IFACE = {jack: iface for iface, (jack, _plug) in PAIRS.items()}
PLUGS = sorted(JACK_OF)
EACH = pytest.mark.parametrize("ref", PLUGS)
EACH_IFACE = pytest.mark.parametrize("iface", sorted(PAIRS))

# plug -> the solids it builds end to end, jack side first; the screws that
# run beside them and the node whose rear each starts from; where the first
# solid starts and where the last one before the stub ends, both from the face
# the jack presents; its default cable-od and jacket colour.
SHAPE = {
    MRJ21: dict(chain=["hood", "relief-boot", "stub"], screws=["screw-a", "screw-b"],
                screws_from="hood", start=0.0, end=93.5, od=12.2, jacket="#9a9da1"),
    VHDCI: dict(chain=["shell", "hood", "hood-rear", "relief-boot", "stub"],
                screws=["screw-l", "screw-r"], screws_from="hood", start=0.34, end=55.44,
                od=10.0, jacket="#1c1c1c"),
    RJ11: dict(chain=["body", "stub"], screws=[], screws_from=None, start=0.0, end=4.5,
               od=2.9, jacket="#1c1c1c"),
}
# the three Oscilloquartz cards that compose the VHDCI receptacle, and its id
OSA_CARDS = {"oscilloquartz/btoh-16@1": "bits-out", "oscilloquartz/cpoh-16@1": "outputs",
             "oscilloquartz/ptoh-16@1": "outputs"}
MDA = "nokia/m48-1gb-xp-tx@1"


def std():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def feats(ref):
    return {f["node"]: f for f in _contract(ref)["relief"]["features"]}


def rear(f):
    """Where a relief feature ends, from the part's own face: an `out` is
    absolute, a `cyl` runs its length from its `lift`."""
    if f.get("out") is not None:
        return float(f["out"])
    return float(f.get("lift") or 0.0) + float(f["cyl"])


def flat(text):
    return " ".join(str(text).split())


def skin_nodes(ref):
    root = ET.parse(_skin_path(ref)).getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


# --- 1. the registry -----------------------------------------------------------

@EACH_IFACE
def test_each_interface_is_a_connector_citing_a_standard(iface):
    reg = render_mod._connector_registry()
    assert iface in reg, iface
    assert reg[iface]["standard"] in std(), reg[iface]
    jack, plug = PAIRS[iface]
    note = reg[iface]["note"]
    assert jack in note and plug in note, note


def test_the_mrj21_interface_cites_the_standard_its_jack_conforms_to():
    assert render_mod._connector_registry()["mrj21"]["standard"] == \
        _contract("std/mrj21@1")["conforms"] == "mrj21"


def test_the_vhdci_count_is_in_the_note_and_not_in_the_key():
    """SFF-8441 standardizes the 68 position connector only, so no other
    count of it could be on a panel and the key carries none."""
    reg = render_mod._connector_registry()
    assert not [k for k in reg if k.startswith("vhdci") and k != "vhdci"]
    assert "68-position" in reg["vhdci"]["note"]
    assert "only the 68 position version is standardized" in flat(std()["vhdci"]["source"])


def test_the_rj11_jack_is_the_six_position_body():
    """Not the four-position handset jack and not an RJ45: the registry says
    which, and the modelled jack is narrower than the RJ45 housing."""
    reg = render_mod._connector_registry()
    assert "six-position" in reg["rj11"]["note"]
    jack, rj45 = _contract("common/rj11-jack@1"), _contract("std/rj45@2")
    assert jack["size"]["w"] < rj45["size"]["w"]
    assert "six-position modular jack" in flat(std()["rj11"]["source"])
    assert reg["rj11"]["standard"] != reg["rj45"]["standard"]


@EACH_IFACE
def test_each_jack_presents_its_interface_at_the_centre_of_its_opening(iface):
    jack = _contract(PAIRS[iface][0])
    assert jack["class"] == "port" and jack["interface"] == iface
    got, at, lift = presented_interface(jack, lambda r: _contract(r))
    assert got == iface and lift == 0.0
    assert at == pytest.approx(jack["connection-points"]["mate"]["at"])
    el = jack["elements"]["jack" if iface == "rj11" else "opening"]
    centre = [el["at"][0] + el["size"][0] / 2, el["at"][1] + el["size"][1] / 2]
    if iface == "rj11":
        # the centre of the BODY TIER the plug's body fills (9.88 x 6.85 from
        # the top of the opening), not of the whole opening, whose lower 4.41
        # is the shoulder and latch slot: centred across, 6.85 / 2 down
        assert at == pytest.approx([centre[0], el["at"][1] + 6.85 / 2])
        plug = _contract(PAIRS[iface][1])
        ph = plug["size"]["h"]
        assert el["at"][1] <= at[1] - ph / 2 and at[1] + ph / 2 <= el["at"][1] + 6.85
        assert "BODY TIER" in flat(jack["provenance"]["mate"])
    elif iface == "vhdci":
        # the point the receptacle already had: midway between its two screw
        # locks, which is the middle of the part and 0.1 off the middle of the
        # slot as drawn. It is not moved; the plug's screws are symmetric
        # about it.
        locks = [jack["elements"][k]["at"][0] + jack["elements"][k]["size"][0] / 2
                 for k in ("screw-l", "screw-r")]
        assert at == pytest.approx([sum(locks) / 2, centre[1]])
        assert at[0] == pytest.approx(centre[0] - 0.1)
    else:
        assert at == pytest.approx(centre)
    mate = jack["connection-points"]["mate"]
    assert "on" not in mate and "seat-out" not in mate


@pytest.mark.parametrize("iface", ["mrj21", "vhdci"])
def test_no_jack_models_a_depth(iface):
    """Fails by design when a jack gains a depth or a cavity: each plug's
    provenance.seated-depth says its jack states none, and is to be read
    again."""
    jack = _contract(PAIRS[iface][0])
    assert "d" not in jack["size"] and "relief" not in jack, PAIRS[iface][0]
    text = flat(_contract(PAIRS[iface][1])["provenance"]["seated-depth"])
    assert PAIRS[iface][0] in text and "states no depth" in text.lower(), text


def test_the_rj11_jack_models_its_housing_depth_and_a_cavity():
    """#837: TE C-1775675 rev C's 20.57, the registry's figure, with the
    three-tier opening recessed as std/rj45@2 recesses its own. Fails by
    design when the depth moves: the plug's provenance.seated-depth cites it
    and says it is not a plug stop."""
    jack = _contract("common/rj11-jack@1")
    assert jack["size"]["d"] == pytest.approx(std()["rj11"]["depth"]) == pytest.approx(20.57)
    assert jack["relief"]["cavity"] == "cavity"
    assert jack["relief"]["size"] == {"w": 9.88, "h": 11.26}
    assert jack["elements"]["jack"]["size"] == [9.88, 11.26]
    text = flat(_contract(RJ11)["provenance"]["seated-depth"])
    assert "common/rj11-jack@1 is 20.57 deep" in text and "not a plug stop" in text, text


def test_the_rj11_jack_draws_the_six_position_tiers_and_two_contacts():
    """The cavity node is the opening's outline in three tiers (body 9.88 x
    6.85, shoulder 6.60 x 1.69, latch slot 4.04 x 2.72), and two contacts
    are loaded, positions 3 and 4 on the 1.02 pitch."""
    n = skin_nodes("common/rj11-jack@1")
    d = n["cavity"].get("d").split()
    assert d[:3] == ["M", "2.06", "1.5"]
    steps = [(d[i], float(d[i + 1])) for i in range(3, len(d) - 1, 2)]
    assert steps == [("h", 9.88), ("v", 6.85), ("h", -1.64), ("v", 1.69), ("h", -1.28),
                     ("v", 2.72), ("h", -4.04), ("v", -2.72), ("h", -1.28), ("v", -1.69),
                     ("h", -1.64)]
    pins = [e for e in n["jack-pins"] if e.tag.endswith("rect")]
    xs = [float(e.get("x")) + float(e.get("width")) / 2 for e in pins]
    assert xs == pytest.approx([6.49, 7.51])
    assert xs[1] - xs[0] == pytest.approx(1.02)


def test_the_edited_jacks_kept_their_bodies():
    v, r = _contract("common/vhdci-receptacle@1"), _contract("common/rj11-jack@1")
    assert v["version"] == "1.0.1" and r["version"] == "1.2.0"
    assert v["size"] == {"w": 40.4, "h": 5.2}
    assert r["size"] == {"w": 14.0, "h": 13.5, "d": 20.57}
    # `tel` moved with `mate` to the body tier's centre (#837): one place for both
    assert r["connection-points"]["tel"] == {"at": [7.0, 4.925], "direction": "front"}
    assert r["connection-points"]["tel"]["at"] == r["connection-points"]["mate"]["at"]
    assert _contract("std/mrj21@1")["version"] == "1.0.0"


# --- 2. the slots --------------------------------------------------------------

@pytest.fixture(scope="module")
def comps():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


def test_the_mda_publishes_its_eight_connectors_as_nested_slots(comps):
    card = _contract(MDA)
    assert card["kind"] == "module"
    ids = [p["id"] for p in card["parts"] if p["ref"] == "std/mrj21@1"]
    assert ids == [f"connector-{n}" for n in range(1, 9)]
    for pid in ids:
        slot = _card_slot(comps, MDA, pid)
        assert slot["kind"] == "connector" and slot["interface"] == "mrj21", slot
        assert slot["accepts"] == [MRJ21] and slot["lift"] == 0.0, slot


@pytest.mark.parametrize("card", sorted(OSA_CARDS))
def test_each_oscilloquartz_card_publishes_its_receptacle_as_a_nested_slot(card, comps):
    c = _contract(card)
    assert c["kind"] == "module" and c["version"] == "1.0.1"
    part = [p for p in c["parts"] if p["ref"] == "common/vhdci-receptacle@1"]
    assert [p["id"] for p in part] == [OSA_CARDS[card]]
    slot = _card_slot(comps, card, OSA_CARDS[card])
    assert slot["kind"] == "connector" and slot["interface"] == "vhdci", slot
    assert slot["accepts"] == [VHDCI] and slot["lift"] == 0.0, slot


def test_each_interface_is_mated_by_its_one_plug(comps):
    mating = {}
    for ref in comps:
        m = _contract(ref).get("mates")
        if m in PAIRS:
            mating.setdefault(m, []).append(ref)
    assert mating == {iface: [plug] for iface, (_jack, plug) in PAIRS.items()}


def test_the_census_of_composed_jacks_and_every_one_is_a_slot(comps):
    """Each `parts:` entry that is one of the three jacks is published as a
    slot of the component that composes it. None is forwarded: no part
    composes exactly one of them as its one aperture and is then placed."""
    seen = {r: 0 for r in JACK_IFACE}
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        ref = f"{f.parts[-4]}/{c['name']}@{f.parts[-2][1:]}"
        for p in c.get("parts") or []:
            iface = JACK_IFACE.get(p.get("ref"))
            if iface is None:
                continue
            seen[p["ref"]] += 1
            cages = {x["id"]: x for x in comps[ref].get("cages") or []}
            assert p["id"] in cages, (ref, p["id"])
            assert cages[p["id"]]["kind"] == "connector", (ref, p["id"])
            assert cages[p["id"]]["interface"] == iface, (ref, p["id"])
            assert cages[p["id"]]["accepts"] == [PAIRS[iface][1]], (ref, p["id"])
    assert seen == {"std/mrj21@1": 8, "common/vhdci-receptacle@1": 3, "common/rj11-jack@1": 0}


def test_the_census_of_placed_jacks_on_device_views():
    """The device side, walked off every view: the only one of the three a
    chassis places is the RJ11 jack, twice, both turned 180. A part that
    states one of the three media and is none of the jacks is a plug or a
    card that composes one."""
    placed = {r: [] for r in JACK_IFACE}
    for f in sorted((LIB / "devices").glob("*/*/device.yaml")):
        d = yaml.safe_load(f.read_text())
        for view in (d.get("views") or {}).values():
            for p in ((view or {}).get("components") or {}).get("placements") or []:
                if p.get("ref") in placed:
                    placed[p["ref"]].append((f"{f.parts[-3]}/{f.parts[-2]}", p["id"],
                                             p.get("rotate")))
    assert placed["common/rj11-jack@1"] == [("halny/hlx-tgv", "tel-2", 180),
                                            ("halny/hlx-tgv", "tel-1", 180)]
    assert placed["std/mrj21@1"] == [] and placed["common/vhdci-receptacle@1"] == []
    media = {_contract(j)["attrs"]["media"] for j in JACK_IFACE}
    assert media == {"mrj21", "vhdci", "rj11"}
    stating, cards = set(), set()
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        if (c.get("attrs") or {}).get("media") not in media or c.get("mates"):
            continue
        ref = f"{f.parts[-4]}/{c['name']}@{f.parts[-2][1:]}"
        (cards if c.get("kind") == "module" else stating).add(ref)
    assert stating == set(JACK_IFACE), sorted(stating ^ set(JACK_IFACE))
    for ref in cards:
        assert any(p.get("ref") in JACK_IFACE for p in _contract(ref).get("parts") or []), ref


# --- 3. the plugs --------------------------------------------------------------

@EACH
def test_it_is_a_plug_that_mates_its_interface(ref):
    d = _contract(ref)
    assert d["class"] == "port" and "behaviour" not in d
    assert d["mates"] == IFACE_OF[ref] and "interface" not in d
    name = ref.split("/")[1].split("@")[0]
    assert d["conforms"] == name and name in std()
    assert d["unplaced"] == _contract("generic/usb-a-plug@1")["unplaced"]
    # the RJ11 plug took a provenance patch when #837 redrew its jack
    assert d["skins"] == ["default"] and d["version"] == ("1.0.1" if ref == RJ11 else "1.0.0")


@EACH
def test_it_states_its_jacks_medium(ref):
    d = _contract(ref)
    jack = _contract(JACK_OF[ref])
    assert d["attrs"] == {"media": jack["attrs"]["media"], "connector": IFACE_OF[ref]}


@EACH
def test_its_size_is_its_registry_entry_and_says_how_sure_it_is(ref):
    d = _contract(ref)
    entry = std()[d["conforms"]]
    assert (entry["w"], entry["h"]) == (d["size"]["w"], d["size"]["h"])
    assert d["size-notes"]
    if ref == RJ11:
        # the sibling it follows, generic/rj45-plug@1, states a depth, and so
        # does this: both are the plain body length of a dimensioned drawing
        assert d["size"]["d"] == entry["depth"] == 12.43
        assert "d" in _contract("generic/rj45-plug@1")["size"]
        assert d["size-confidence"] == {"w": "drawing", "h": "drawing", "d": "drawing"}
        assert "followed" in d["provenance"]
    else:
        assert "d" not in d["size"], "a behaviour-less part's size.d is built as a pit"
        # a scaled figure is estimated everywhere it is stated
        assert d["size-confidence"] == {"w": "estimated", "h": "estimated"}
        assert entry["confidence"] == entry["depth-confidence"] == "estimated"
        assert "SCALED" in d["size-notes"] and "scale" in d["provenance"]


@pytest.mark.parametrize("ref", [MRJ21, VHDCI])
def test_the_overall_length_is_in_the_registry(ref):
    f, s = feats(ref), SHAPE[ref]
    last = f[s["chain"][-2]]
    first = f[s["chain"][0]]
    start = float(first.get("lift") or 0.0)
    assert start == pytest.approx(s["start"]) and rear(last) == pytest.approx(s["end"])
    assert std()[_contract(ref)["conforms"]]["depth"] == pytest.approx(s["end"] - s["start"])


@EACH
def test_nothing_is_drawn_outside_its_box(ref):
    d = _contract(ref)
    w, h = d["size"]["w"], d["size"]["h"]
    widest = tallest = 0.0
    for e in ET.parse(_skin_path(ref)).getroot().iter():
        tag = e.tag.split("}")[1]
        if tag == "rect":
            x, y, rw, rh = (float(e.get(k)) for k in ("x", "y", "width", "height"))
            assert x >= -EPS and y >= -EPS and x + rw <= w + EPS and y + rh <= h + EPS, e.get("id")
            widest, tallest = max(widest, rw), max(tallest, rh)
        elif tag == "circle":
            cx, cy, r = (float(e.get(k)) for k in ("cx", "cy", "r"))
            assert cx - r >= -EPS and cx + r <= w + EPS, e.get("id")
            if ref == VHDCI and e.get("id") == "stub":
                # the one overhang: the stated 10.0 cable against a hood that
                # scales to 9.0, recorded in provenance.cable-od
                assert (cy - r, cy + r) == pytest.approx((-0.5, h + 0.5))
                assert "overhangs the box of the part by 0.5" in flat(
                    d["provenance"]["cable-od"])
                continue
            assert cy - r >= -EPS and cy + r <= h + EPS, e.get("id")
            tallest = max(tallest, 2 * r)
    # the box is the widest section drawn, each way
    assert widest == pytest.approx(w) and tallest == pytest.approx(h)


@EACH
def test_its_fields_are_the_cable(ref):
    d = _contract(ref)
    assert set(d["fields"]) == {"cable-od", "jacket-color"}
    assert d["fields"]["cable-od"]["default"] == pytest.approx(SHAPE[ref]["od"])
    assert d["fields"]["jacket-color"]["default"] == SHAPE[ref]["jacket"]
    assert "jacket-colour" in d["provenance"] and "cable-od" in d["provenance"]


@EACH
def test_the_stub_is_30_long_from_where_the_plug_ends(ref):
    f = feats(ref)
    last, stub = f[SHAPE[ref]["chain"][-2]], f["stub"]
    assert stub["cyl"] == pytest.approx(STUB)
    assert stub["lift"] == pytest.approx(rear(last)) == pytest.approx(SHAPE[ref]["end"])


@EACH
def test_the_solids_chain_from_the_jack_face_to_the_stub(ref):
    """Each solid starts where the one before it ends, with no gap and no
    overlap; the screws start at the rear of the section that holds them.
    Nothing else is built."""
    f, s = feats(ref), SHAPE[ref]
    assert set(f) == set(s["chain"]) | set(s["screws"])
    assert float(f[s["chain"][0]].get("lift") or 0.0) == pytest.approx(s["start"])
    for a, b in zip(s["chain"], s["chain"][1:]):
        assert float(f[b]["lift"]) == pytest.approx(rear(f[a])), (ref, a, b)
    for n in s["screws"]:
        assert float(f[n]["lift"]) == pytest.approx(rear(f[s["screws_from"]])), (ref, n)
        assert f[n]["cyl"] > 0 and f[n]["cyl"] == f[s["screws"][0]]["cyl"]


@EACH
def test_the_cable_leaves_from_the_stub_on_the_mating_axis(ref):
    """A straight exit: the stub stands out of the face, on the mate point."""
    d = _contract(ref)
    cps = d["connection-points"]
    assert cps["cable"]["on"] == "stub" and cps["cable"]["at"] == cps["mate"]["at"]
    assert cps["mate"]["at"] == pytest.approx([d["size"]["w"] / 2, d["size"]["h"] / 2])
    stub = skin_nodes(ref)["stub"]
    assert [float(stub.get("cx")), float(stub.get("cy"))] == pytest.approx(cps["mate"]["at"])
    if ref != RJ11:
        text = flat(d["provenance"]["exit"])
        assert text.startswith("STRAIGHT"), text


@EACH
def test_the_stub_circle_is_bound_to_the_fields(ref):
    s = _skin_path(ref).read_text()
    for node in feats(ref):
        assert f'id="{node}"' in s, node
    stub = s[s.index('id="stub"'):].split("/>", 1)[0]
    assert 'data-r-from="cable-od"' in stub and 'data-fill-from="jacket-color"' in stub
    assert s.count("data-fill-from") == 1 and s.count("data-r-from") == 1
    r = float(stub.split('r="', 1)[1].split('"', 1)[0])
    assert r == pytest.approx(SHAPE[ref]["od"] / 2, abs=0.005)
    assert f'fill="{SHAPE[ref]["jacket"]}"' in stub
    # L73: the node a field paints states no relief colour
    assert "color" not in feats(ref)["stub"]


@EACH
def test_no_mark_is_drawn(ref):
    """No logo, no lettering and no screw slot: nothing in a skin is text,
    and on the two hooded plugs every node is one its relief builds from."""
    root = ET.parse(_skin_path(ref)).getroot()
    drawn = [e for e in root.iter() if e is not root]
    assert all(e.tag.split("}")[1] in ("rect", "circle") for e in drawn)
    ids = sorted(e.get("id") for e in drawn)
    if ref == RJ11:
        # drawn as generic/rj45-plug@1 is: body, contacts and latch, and the cord
        assert ids == ["body", "contacts", "latch", "stub"]
        rj45 = sorted(skin_nodes("generic/rj45-plug@1"))
        assert rj45 == ["body", "contacts", "latch"]
    else:
        assert ids == sorted(feats(ref))
    assert "no-mark" in _contract(ref)["provenance"]


def test_the_mrj21_jackscrews_are_on_the_guide_holes_of_the_receptacle():
    """Which way round. std/mrj21@1 draws its guide holes at the upper left
    and the lower right; each jackscrew is over one when the mate points
    coincide."""
    jack = _contract("std/mrj21@1")
    holes = flat(jack["provenance"]["guide-holes"])
    assert "(3.02, 3.12) and (25.90, 10.32)" in holes
    jx, jy = jack["connection-points"]["mate"]["at"]
    px, py = _contract(MRJ21)["connection-points"]["mate"]["at"]
    n = skin_nodes(MRJ21)
    got = sorted((float(n[s].get("cx")) - px, float(n[s].get("cy")) - py)
                 for s in SHAPE[MRJ21]["screws"])
    want = sorted([(3.02 - jx, 3.12 - jy), (25.90 - jx, 10.32 - jy)])
    for g, w in zip(got, want):
        assert g == pytest.approx(w, abs=0.005), (got, want)
    assert got[0][1] < 0 < got[1][1], "upper left and lower right"


def test_the_vhdci_thumbscrews_are_on_the_screwlock_centres():
    n = skin_nodes(VHDCI)
    lx, rx = float(n["screw-l"].get("cx")), float(n["screw-r"].get("cx"))
    mx, my = _contract(VHDCI)["connection-points"]["mate"]["at"]
    assert rx - lx == pytest.approx(37.7) and (lx + rx) / 2 == pytest.approx(mx)
    assert float(n["screw-l"].get("cy")) == float(n["screw-r"].get("cy")) == my
    assert "37.7 +/-0.1 centres" in flat(std()["vhdci"]["source"])
    # the receptacle draws its two locks 37.2 apart, photo-measured: each
    # thumbscrew is a quarter of a millimetre outside the lock it is over
    jack = _contract("common/vhdci-receptacle@1")
    locks = [jack["elements"][k]["at"][0] + jack["elements"][k]["size"][0] / 2
             for k in ("screw-l", "screw-r")]
    assert locks[1] - locks[0] == pytest.approx(37.2)
    assert (37.7 - 37.2) / 2 == pytest.approx(0.25)
    assert "0.25" in flat(_contract(VHDCI)["provenance"]["thumbscrews"])


def test_the_rj11_plug_has_its_latch_where_the_jack_has_its_keyway():
    """Contacts at the top and the latch at the bottom, as the jack draws its
    pins and its keyway, and as generic/rj45-plug@1 is drawn."""
    for ref in (RJ11, "generic/rj45-plug@1"):
        n = skin_nodes(ref)
        h = _contract(ref)["size"]["h"]
        assert float(n["contacts"].get("y")) < h / 2 < float(n["latch"].get("y")), ref
    n = skin_nodes("common/rj11-jack@1")
    h = _contract("common/rj11-jack@1")["size"]["h"]
    pins = [e for e in n["jack-pins"] if e.tag.endswith("rect")]
    assert len(pins) == 2 and all(float(e.get("y")) < h / 2 for e in pins)
    # the latch slot is the cavity's lowest tier, below the middle
    d = n["cavity"].get("d").split()
    ys, y = [], float(d[2])
    for i in range(3, len(d) - 1, 2):
        if d[i] == "v":
            y += float(d[i + 1])
            ys.append(y)
    assert max(ys) > h / 2
    # the plug passes into the six-position opening
    assert _contract(RJ11)["size"]["w"] == 9.65 < 9.88
    assert "9.88" in flat(std()["rj11"]["source"])


# --- 4. the seated depth, in the contracts --------------------------------------

def test_the_mrj21_backshell_stands_on_the_receptacle_face():
    f = feats(MRJ21)
    assert "lift" not in f["hood"] and f["hood"]["out"] == 35.5
    text = flat(_contract(MRJ21)["provenance"]["seated-depth"])
    assert "THE PLUG SEATS WITH ITS BACKSHELL ON THE FACE THE RECEPTACLE PRESENTS" in text
    assert "5.6 (scaled)" in text and "assumption" in text


def test_the_vhdci_hood_starts_the_mated_gap_and_the_front_shell_out():
    f = feats(VHDCI)
    assert (f["shell"]["lift"], f["shell"]["out"]) == (0.34, 7.44)
    assert f["shell"]["out"] - f["shell"]["lift"] == pytest.approx(7.10)
    assert f["hood"]["lift"] == 7.44
    text = flat(_contract(VHDCI)["provenance"]["seated-depth"])
    assert "MEASURED FROM THE FACE THE RECEPTACLE PRESENTS" in text
    assert "0.34 + 7.1 = 7.44" in text and "5.2 +/-0.06" in text


def test_the_rj11_body_stands_its_length_less_an_estimated_insertion():
    d = _contract(RJ11)
    f = feats(RJ11)
    assert f["body"]["out"] == 4.5 and f["body"]["confidence"] == "estimated"
    text = flat(d["provenance"]["seated-depth"])
    assert text.startswith("estimated") and "12.43 - 7.9 = 4.53" in text
    assert round(d["size"]["d"] - 7.9, 2) == 4.53
    assert "NO HELD DOCUMENT GIVES THE INSERTION" in text


# --- 5. seated on real jacks -------------------------------------------------------

# (plug, device, configuration, view, the bays the copy fills, the occupant
# key, the host's data-path, the part the host IS). The MRJ21 seats are two
# bays down, flat on the SR-7 and a quarter turn round on the SR-12; the VHDCI
# seats are on a card in an expansion slot; the RJ11 jack is a chassis
# placement, and both are fitted at 180.
IOM = "nokia/iom3-xp@1"
SEATS = [
    (MRJ21, "nokia/sr-7", "base", "front", {"slot-1": IOM, "slot-1/mda-1": MDA},
     "slot-1/mda-1/connector-2", "slot-1/module/mda-1/module/connector-2", "std/mrj21@1"),
    (MRJ21, "nokia/sr-12", "base", "front", {"slot-1": IOM, "slot-1/mda-2": MDA},
     "slot-1/mda-2/connector-7", "slot-1/module/mda-2/module/connector-7", "std/mrj21@1"),
    (VHDCI, "oscilloquartz/osa-5420-quartz", "base", "front",
     {"lc-1": "oscilloquartz/btoh-16@1", "lc-2": "oscilloquartz/btoh-16@1"},
     "lc-1/bits-out", "lc-1/module/bits-out", "common/vhdci-receptacle@1"),
    (VHDCI, "oscilloquartz/osa-5421-rubidium", "base", "front",
     {"lc-1": "oscilloquartz/ptoh-16@1"},
     "lc-1/outputs", "lc-1/module/outputs", "common/vhdci-receptacle@1"),
    (RJ11, "halny/hlx-tgv", "eu", "rear", {}, "tel-1", "tel-1", "common/rj11-jack@1"),
]
SEAT_IDS = [f"{s[0].split('/')[1].split('@')[0]}-in-{s[1].split('/')[1]}" for s in SEATS]
EACH_SEAT = pytest.mark.parametrize("seat", SEATS, ids=SEAT_IDS)
NESTED = [s for s in SEATS if "/" in s[5]]


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


def _load(o, name, config, view):
    root = ET.parse(face_file(o, name, config, view)).getroot()
    return root, {c: p for p in root.iter() for c in p}


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    """Every seat in SEATS, built twice: with the cards in their bays and
    the jack empty, and with the plug seated.

    Returns {device: (bare (root, parents), seated (root, parents),
    configs.json of the seated build, configs.json of the bare build)}."""
    out = {}
    for ref, device, config, view, bays, key, _host, _is in SEATS:
        def fill(d, config=config, bays=bays):
            cfg = d["configurations"][config]
            cfg["bays"] = {**(cfg.get("bays") or {}), **bays}

        def seat(d, config=config, bays=bays, key=key, ref=ref):
            fill(d)
            cfg = d["configurations"][config]
            cfg["occupants"] = {**(cfg.get("occupants") or {}), key: ref}
        name, o = _render(tmp_path_factory.mktemp("smallbare"), device, fill)
        bare = _load(o, name, config, view)
        bare_index = json.loads((o / f"{name}.configs.json").read_text())
        name, o = _render(tmp_path_factory.mktemp("smallseated"), device, seat)
        out[device] = (bare, _load(o, name, config, view),
                       json.loads((o / f"{name}.configs.json").read_text()), bare_index)
    assert len(out) == len(SEATS)
    return out


def _seat(seated, seat):
    ref, device, _config, _view, _bays, _key, host_path, host_is = seat
    _bare, (root, parents), configs, _ = seated[device]
    host = by_path(root, host_path)
    occ = by_path(root, f"{host_path}-occupant")
    assert occ.get("data-ref", "").startswith(ref), occ.get("data-ref")
    assert host.get("data-ref", "").startswith(host_is), host.get("data-ref")
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


@EACH_SEAT
def test_the_bare_build_leaves_the_jack_empty(seated, seat):
    (root, _parents), _s, _c, _ = seated[seat[1]]
    assert by_path(root, seat[6]) is not None
    assert not [e for e in root.iter() if e.get("data-path") == f"{seat[6]}-occupant"]


@EACH_SEAT
def test_it_seats_with_its_mate_on_the_jacks_mate(seated, seat):
    parents, host, occ, _ = _seat(seated, seat)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)


def _turn(parents, el):
    """The quarter turns of `el` in the device frame, 0 to 3."""
    m = device_matrix(parents, el)
    a, b = round(m[0][0]), round(m[1][0])
    return {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}[(a, b)]


def test_the_seats_are_measured_at_three_different_turns(seated):
    """Not a flat pass. The MDA turns its connectors 270 and the SR-12 seats
    its cards in bays at 90, so the SR-7 seat is a quarter turn one way and
    the SR-12 seat is upright again; the Halny jacks are at 180; the
    Oscilloquartz cards are flat. Read off the library, then off the build."""
    card = _contract(MDA)
    assert {p.get("rotate") for p in card["parts"] if p["ref"] == "std/mrj21@1"} == {270}
    d = yaml.safe_load((LIB / "devices/nokia/sr-12/device.yaml").read_text())
    bay = [b for b in d["views"]["front"]["components"]["bays"] if b["id"] == "slot-1"]
    assert len(bay) == 1 and bay[0]["rotate"] == 90
    d = yaml.safe_load((LIB / "devices/nokia/sr-7/device.yaml").read_text())
    bay = [b for b in d["views"]["front"]["components"]["bays"] if b["id"] == "slot-1"]
    assert len(bay) == 1 and not bay[0].get("rotate")
    turns = {}
    for seat in SEATS:
        parents, host, occ, _ = _seat(seated, seat)
        turns[seat[1]] = _turn(parents, occ)
        assert _turn(parents, host) == turns[seat[1]]
    assert turns["nokia/sr-7"] == 3 and turns["nokia/sr-12"] == 0
    assert turns["halny/hlx-tgv"] == 2
    assert turns["oscilloquartz/osa-5420-quartz"] == 0
    assert len(set(turns.values())) == 3


@pytest.mark.parametrize("seat", [s for s in SEATS if s[0] == MRJ21],
                         ids=[SEAT_IDS[SEATS.index(s)] for s in SEATS if s[0] == MRJ21])
def test_the_seated_jackscrews_are_over_the_guide_holes_however_it_is_turned(seated, seat):
    """In the device frame, on a flat card and on a turned one: each
    jackscrew centre is on a guide hole of the receptacle it is seated in."""
    parents, host, occ, _ = _seat(seated, seat)
    holes = sorted(device_point(parents, host, p) for p in [(3.02, 3.12), (25.90, 10.32)])
    el = _nodes(occ, MRJ21)
    screws = sorted(device_point(parents, el[s], (float(el[s].get("cx")), float(el[s].get("cy"))))
                    for s in SHAPE[MRJ21]["screws"])
    for (hx, hy), (sx, sy) in zip(holes, screws):
        assert abs(hx - sx) < 0.01 and abs(hy - sy) < 0.01, (holes, screws)


@pytest.mark.parametrize("seat", [s for s in SEATS if s[0] == VHDCI],
                         ids=[SEAT_IDS[SEATS.index(s)] for s in SEATS if s[0] == VHDCI])
def test_the_seated_thumbscrews_are_over_the_screw_locks(seated, seat):
    parents, host, occ, _ = _seat(seated, seat)
    jack = _contract("common/vhdci-receptacle@1")["elements"]
    locks = sorted(device_point(parents, host, (jack[k]["at"][0] + 1.4, jack[k]["at"][1] + 1.4))
                   for k in ("screw-l", "screw-r"))
    el = _nodes(occ, VHDCI)
    screws = sorted(device_point(parents, el[s], (float(el[s].get("cx")), float(el[s].get("cy"))))
                    for s in SHAPE[VHDCI]["screws"])
    for (lx, ly), (sx, sy) in zip(locks, screws):
        assert abs(abs(lx - sx) - 0.25) < 0.01 and abs(ly - sy) < 0.01, (locks, screws)


def test_the_seated_rj11_latch_is_up_on_the_halny(seated):
    """Both jacks are fitted at 180, so the latch, drawn at the bottom of the
    plug, is at the top of the seated one, over the keyway of the jack."""
    seat = SEATS[-1]
    parents, host, occ, _ = _seat(seated, seat)
    latch = next(e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--latch")
    contacts = next(e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--contacts")
    ly = device_point(parents, latch, (float(latch.get("x")), float(latch.get("y"))))[1]
    cy = device_point(parents, contacts, (float(contacts.get("x")), float(contacts.get("y"))))[1]
    my = device_point(parents, host, cage_mate(host))[1]
    assert ly < my < cy
    # the keyway of the jack, drawn from y 8.8 down, is on the same side
    ky = device_point(parents, host, (7.0, 10.0))[1]
    assert ky < my


@EACH_SEAT
def test_the_seated_plug_stands_off_by_the_ruling(seated, seat):
    """The compiled depths, in the device frame: the first solid starts where
    the ruling puts it in front of the face the jack presents, the last ends
    where the plug does, and the stub ends 30 beyond."""
    ref = seat[0]
    parents, host, occ, _configs = _seat(seated, seat)
    s = SHAPE[ref]
    el = _nodes(occ, ref)
    base = lift_of(parents, occ)
    assert base == pytest.approx(lift_of(parents, host), abs=EPS)
    assert lift_of(parents, el[s["chain"][0]]) - base == pytest.approx(s["start"], abs=EPS)
    assert _front(parents, el[s["chain"][-2]]) - base == pytest.approx(s["end"], abs=EPS)
    assert _front(parents, el["stub"]) - base == pytest.approx(s["end"] + STUB, abs=EPS)


@EACH_SEAT
def test_the_seated_plug_builds_right_side_out_and_end_to_end(seated, seat):
    ref = seat[0]
    parents, _host, occ, _ = _seat(seated, seat)
    s = SHAPE[ref]
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
    for a, b in zip(s["chain"], s["chain"][1:]):
        assert lift_of(parents, el[b]) == pytest.approx(_front(parents, el[a]), abs=EPS), (a, b)
    for n in s["screws"]:
        assert lift_of(parents, el[n]) == pytest.approx(
            _front(parents, el[s["screws_from"]]), abs=EPS), n
    assert all(e.get("data-cavity") is None for e in occ.iter())
    if ref == RJ11:
        # the depth it states, as generic/rj45-plug@1 states its own
        assert occ.get("data-depth") == "12.43"
    else:
        assert all(e.get("data-depth") is None for e in occ.iter())


def test_the_halny_slot_is_the_placement_and_offers_exactly_the_plug(seated):
    seat = SEATS[-1]
    ref, device, config, view, _bays, key, _host, host_is = seat
    parents, host, occ, configs = _seat(seated, seat)
    slots = {c["id"]: c for c in configs["cages"][view] if c.get("interface") == "rj11"}
    assert sorted(slots) == ["tel-1", "tel-2"]
    for c in slots.values():
        assert c["kind"] == "connector" and c["accepts"] == [RJ11] and c["default"] is None
        assert c["rotate"] == 180
    entry = [c for c in configs["configs"] if c["name"] == config]
    assert len(entry) == 1 and entry[0]["occupants"][key] == ref
    assert slots[key]["lift"] == pytest.approx(lift_of(parents, occ), abs=EPS)
    assert tuple(slots[key]["mate"]) == pytest.approx(
        device_point(parents, host, cage_mate(host)), abs=1e-3)


# --- 6. the stub's diameter -------------------------------------------------------

def _diameter(parents, circle):
    """relief.js builds a cyl at radius min(w, h) / 2 of the face box."""
    assert circle.tag.endswith("circle"), circle.tag
    cx, cy, r = (float(circle.get(k)) for k in ("cx", "cy", "r"))
    pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    x0, y0, x1, y1 = box(apply(device_matrix(parents, circle), pts))
    assert x1 - x0 == pytest.approx(y1 - y0, abs=EPS)
    return min(x1 - x0, y1 - y0)


@EACH_SEAT
def test_the_stub_is_the_default_cable_od_on_the_seat(seated, seat):
    ref = seat[0]
    parents, host, occ, _ = _seat(seated, seat)
    stub = _nodes(occ, ref)["stub"]
    assert _diameter(parents, stub) == pytest.approx(SHAPE[ref]["od"], abs=EPS)
    cx, cy = device_point(parents, stub, (float(stub.get("cx")), float(stub.get("cy"))))
    assert (cx, cy) == pytest.approx(device_point(parents, host, cage_mate(host)), abs=EPS)


# A placement's attrs set the field (an occupant carries only a ref): each
# plug placed directly, `mate-to` a jack on the chassis, with a cable-od of
# its own. The library places no MRJ21 or VHDCI jack on a chassis, so the copy
# of the one device that has the RJ11 jack is given one of each to carry them.
OVERRIDES = [(MRJ21, "added-mrj21", 9.0), (VHDCI, "added-vhdci", 7.5), (RJ11, "tel-2", 4.0)]


@pytest.fixture(scope="module")
def overridden(tmp_path_factory):
    def edit(d):
        places = d["views"]["rear"]["components"]["placements"]
        for ref, host, od in OVERRIDES:
            hits = [p for p in places if p.get("id") == host]
            if host.startswith("added-"):
                assert not hits
                # clear of the face: nothing here measures where it is
                places.append({"ref": JACK_OF[ref], "id": host, "at": [0.0, 0.0]})
            else:
                assert len(hits) == 1 and hits[0]["ref"] == JACK_OF[ref], hits
            places.append({"ref": ref, "id": f"cable-{host}", "mate-to": host,
                           "attrs": {"cable-od": od}})
    name, o = _render(tmp_path_factory.mktemp("smallod"), "halny/hlx-tgv", edit)
    return _load(o, name, "eu", "rear")


@pytest.mark.parametrize("case", OVERRIDES, ids=[c[0].split("/")[1] for c in OVERRIDES])
def test_a_placements_cable_od_sets_the_stub(overridden, case):
    ref, host_id, od = case
    assert SHAPE[ref]["od"] != pytest.approx(od, abs=0.1)
    root, parents = overridden
    occ, host = by_path(root, f"cable-{host_id}"), by_path(root, host_id)
    assert occ.get("data-ref", "").startswith(ref)
    assert float(occ.get("data-cable-od")) == pytest.approx(od)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS
    assert_same_turn(parents, occ, host)
    el = _nodes(occ, ref)
    assert float(el["stub"].get("r")) * 2 == pytest.approx(od, abs=EPS)
    assert _diameter(parents, el["stub"]) == pytest.approx(od, abs=EPS)
    # only the stub follows the cable: the screws keep their drawn size
    for n in SHAPE[ref]["screws"]:
        assert float(el[n].get("r")) == float(skin_nodes(ref)[n].get("r"))


# --- 7. the kit: it offers the nested seats, and seats a plug as the build does ----

KIT_SCRIPT = ROOT / "spec/tests/js/small-connector-plugs.mjs"
# device -> the nested seat the kit is asked to fill: one on a card in a bay,
# and one two bays down
KIT_SEATS = [SEATS[0], SEATS[2]]
KIT_IDS = [s[1] for s in KIT_SEATS]


@pytest.fixture(scope="module")
def kit(seated, tmp_path_factory):
    """kit/swap.js run under node against the BARE compiled faces (cards in
    their bays, jacks empty), with the device index of the same build and the
    component index and skins built here. No skip: a machine without node
    fails."""
    assert shutil.which("node"), "node is needed to run the kit's slot walk"
    dist = tmp_path_factory.mktemp("small-dist")
    comps = build_components(dist)
    cases = {}
    for ref, device, _config, view, _bays, _key, host, _is in KIT_SEATS:
        (root, _), _s, _c, index = seated[device]
        cases[device] = {"face": spec_of(root), "view": view, "slot": host, "ref": ref,
                         "interface": IFACE_OF[ref], "bays": index["bays"],
                         "cages": index["cages"]}
    payload = {"components": list(comps.values()), "cases": cases,
               "skins": {r: json.dumps(spec_of(ET.parse(skin_file(dist, comps[r])).getroot()))
                         for r in (*PLUGS, *JACK_IFACE)}}
    p = subprocess.run(["node", str(KIT_SCRIPT)], input=json.dumps(payload),
                       capture_output=True, text=True, cwd=str(KIT_SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout.strip().splitlines()[-1])
    assert set(got) == set(KIT_IDS)
    for g in got.values():
        assert "error" not in g, g.get("error")
    return got


@pytest.mark.parametrize("seat", KIT_SEATS, ids=KIT_IDS)
def test_the_kits_slot_walk_offers_the_nested_seat(kit, seated, seat):
    ref, device, _config, _view, _bays, key, host_path, host_is = seat
    g = kit[device]
    slots = {e["id"]: e for e in g["slots"]}
    # every jack of the kind on the face: eight on the one MDA, one on each card
    assert len(slots) == (8 if ref == MRJ21 else 2), sorted(slots)
    assert sorted(g["offered"]) == sorted(slots)
    one = slots[host_path]
    # the configuration key is the drawing path less each bay's `module` segment
    assert one["key"] == key
    assert one["kind"] == "connector" and one["interface"] == IFACE_OF[ref]
    assert one["accepts"] == [ref] and one["default"] is None
    assert one["modulePath"] == host_path.rsplit("/", 1)[0]
    (root, parents), _s, _c, _ = seated[device]
    assert one["lift"] == pytest.approx(lift_of(parents, by_path(root, host_path)))


@pytest.mark.parametrize("seat", KIT_SEATS, ids=KIT_IDS)
def test_the_kit_seats_the_plug_exactly_as_the_build_does(kit, seated, seat):
    ref, device, _config, _view, _bays, _key, host_path, _is = seat
    _bare, (wired, _), _c, _ = seated[device]
    want = built_occupant(wired, host_path)
    assert want["ref"] == ref
    g = kit[device]
    bad = mismatches([{"name": device, "built": {host_path: want}}],
                     [{"name": device, "seated": {host_path: g["plug"]}}])
    assert not bad, "\n".join(bad)
    assert g["occRef"] and g["occRef"].startswith(ref)
    assert g["again"] == 1, "a second swap stacked a second plug"
    assert g["others"] and set(g["others"]) == {0}, "a neighbouring jack was given a plug"
    assert g["left"] == 0, "emptying the jack left a plug"


@pytest.mark.parametrize("seat", KIT_SEATS, ids=KIT_IDS)
def test_the_3d_pass_seats_the_plug_on_the_nested_seat(kit, seat):
    t = kit[seat[1]]["threeD"]
    # a key that holds `/module/` names every view that has bays
    # (kit/swap.js viewsToRewrite); the SR-7 has bays on its rear as well
    assert t["named"] == (["front", "rear"] if seat[1] == "nokia/sr-7" else ["front"])
    assert t["viewsApplied"] == 1 and t["viewsSeated"] == 1
    assert t["faceApplied"] == 1 and t["faceSeated"] == 1
    assert not t["faceRefused"] and not t["faceFailed"]
