"""D-subminiature and VGA panel connectors are connector slots, and the hooded
cable plugs that seat on them (#787, docs/connectors-dsub-design.md).

The four cores (std/db9@1, std/vga@1, std/da15@1, std/db25@1) each present an
interface spec/schemas/connectors.yaml now lists, so every one of them is a
slot, bare or behind common/db9-receptacle@1 and common/vga-receptacle@1;
generic/db9-plug@1, generic/hd15-plug@1, generic/da15-plug@1 and
generic/db25-plug@1 mate them. These run against the real library, a
components.json the indexer builds here and device copies rendered here, never
a possibly stale dist.

GENDER IS PART OF THE INTERFACE. Each registry key names the panel connector
with the gender the library draws, each plug states the other gender, and the
DE-9 and VGA plugs, whose shells are one size, are not offered by each other's
slot.

THE SEATED DEPTH IS A RULING, and the tests below hold the parts to it: a plug
seats with its flange the mating dimension in front of the face its core
presents. Each core models its shell that same dimension tall, so the two agree
on the seat, and a test here fails by design when a core's depth is revised,
because the plug's own provenance quotes it.
"""
import json
import re
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
from test_coax_slots import _card_slot, _contract, _skin_path
from test_head_3d import apply, box, lift_of
from test_nested_occupants import (assert_same_turn, by_path, cage_mate, device_matrix,
                                   device_point, own_mate)

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
EPS = 1e-6
STUB = 30.0

DB9, HD15 = "generic/db9-plug@1", "generic/hd15-plug@1"
DA15, DB25 = "generic/da15-plug@1", "generic/db25-plug@1"

# interface -> (the core that presents it, the plug that mates it)
PAIRS = {
    "db9": ("std/db9@1", DB9),
    "hd15": ("std/vga@1", HD15),
    "da15": ("std/da15@1", DA15),
    "db25": ("std/db25@1", DB25),
}
CORE_OF = {plug: core for core, plug in PAIRS.values()}
IFACE_OF = {plug: iface for iface, (_core, plug) in PAIRS.items()}
CORE_IFACE = {core: iface for iface, (core, _plug) in PAIRS.items()}
PLUGS = sorted(CORE_OF)
EACH = pytest.mark.parametrize("ref", PLUGS)
# the two parts that frame a core with its jackscrew standoffs
WRAPPERS = {"common/db9-receptacle@1": "std/db9@1", "common/vga-receptacle@1": "std/vga@1"}
# the gender the library's PANEL connector has; the plug is the other one
PANEL_GENDER = {"db9": "male", "hd15": "female", "da15": "female", "db25": "female"}
OTHER = {"male": "female", "female": "male"}

# plug -> (the mating dimension: flange to flange when mated; the length of the
# plug's front shell; the depth the core MODELS; overall length; default
# cable-od; the centres of its two thumbscrews; the arithmetic its provenance
# prints). The first two are the drawings'; the third is the CORE's own
# `size.d`, pinned here so a change to it fails and the plug's provenance,
# which quotes it, is read again.
FIGURES = {
    DB9: (6.73, 6.18, 6.73, 51.14, 6.20, 24.99, "6.73 - 6.18 = 0.55"),
    HD15: (6.73, 5.94, 6.73, 47.5, 9.0, 24.99, "6.73 - 5.94 = 0.79"),
    DA15: (6.73, 5.94, 6.73, 51.84, 7.21, 33.32, "6.73 - 5.94 = 0.79"),
    DB25: (6.50, 5.94, 6.50, 52.94, 8.61, 47.04, "6.5 - 5.94 = 0.56"),
}
# the solids each plug builds end to end, panel side first, and the two
# thumbscrews, which start at the rear of the node named and run beside them
BACKSHELL = ["shell", "hood-front", "hood", "hood-rear", "stub"]
CHAIN = {DB9: BACKSHELL, DA15: BACKSHELL, DB25: BACKSHELL,
         HD15: ["shell", "hood", "relief-boot", "stub"]}
SCREWS = ["screw-l", "screw-r"]
SCREWS_FROM = {DB9: "hood-front", DA15: "hood-front", DB25: "hood-front", HD15: "hood"}


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


# --- 1. the registry -----------------------------------------------------------

@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_dsub_interface_is_a_connector_citing_its_standard(iface):
    reg = render_mod._connector_registry()
    assert iface in reg, iface
    core = _contract(PAIRS[iface][0])
    assert reg[iface]["standard"] in std(), reg[iface]
    assert reg[iface]["standard"] == core["conforms"]


@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_registry_note_states_the_panel_gender(iface):
    """The naming rule: a key names the connector with the gender the
    library's panel part has, and says the other gender is another interface."""
    note = render_mod._connector_registry()[iface]["note"]
    assert f"{PANEL_GENDER[iface].upper()} on the panel" in note, note
    assert f"{OTHER[PANEL_GENDER[iface]]} cable plug" in note, note
    assert "would be a different interface" in note, note
    assert PAIRS[iface][1] in note and PAIRS[iface][0] in note, note


@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_core_states_the_gender_the_registry_gives_it(iface):
    """Read off the core, not assumed: the three female cores carry a
    `provenance.gender`, and the DE-9 says it under `pins`."""
    prov = _contract(PAIRS[iface][0])["provenance"]
    if iface == "db9":
        assert "gender" not in prov
        assert "a DE-9 on equipment is male" in flat(prov["pins"])
        stated = "male"
    else:
        text = flat(prov["gender"])
        # the first word after the optional confidence word is the gender
        m = re.match(r"(?:[a-z-]+ - )?(female|male)\b", text)
        assert m, text
        stated = m.group(1)
    assert stated == PANEL_GENDER[iface]


@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_core_presents_its_interface_at_its_face(iface):
    core = _contract(PAIRS[iface][0])
    assert core["class"] == "port" and core["interface"] == iface
    got, at, lift = presented_interface(core, lambda r: _contract(r))
    assert got == iface
    assert at == pytest.approx([core["size"]["w"] / 2, core["size"]["h"] / 2])
    assert at == pytest.approx(core["connection-points"]["mate"]["at"])
    # the slot is the panel plane the core stands on: the ruling stands the
    # plug off by its own relief, not by a lift the core states
    assert lift == 0.0


# --- 2. the slots --------------------------------------------------------------

@pytest.fixture(scope="module")
def comps():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


# A connector on a card that seats in a bay: a nested slot in the card's own
# components.json entry. (interface, card, part id, the part the card composes)
CARDS = [
    ("db9", "nokia/sfm4-12@1", "alarm", "common/db9-receptacle@1"),
    ("db9", "cisco/a9k-rsp440-se@2", "alarm-out", "common/db9-receptacle@1"),
    ("hd15", "dell/rear-io-board-16g@1", "video", "common/vga-receptacle@1"),
    ("da15", "nokia/lalm-f@1", "alm-up", "std/da15@1"),
    ("da15", "nokia/ccm-e@1", "alarms", "std/da15@1"),
    ("db25", "nokia/sr-12-pem-3@1", "status", "std/db25@1"),
]


@pytest.mark.parametrize("case", CARDS, ids=[f"{c[1].split('/')[1].split('@')[0]}-{c[2]}"
                                             for c in CARDS])
def test_a_cards_connector_is_a_nested_slot_that_offers_exactly_its_plug(case, comps):
    iface, ref, part_id, composed = case
    card = _contract(ref)
    assert card["kind"] == "module", ref
    part = [p for p in card["parts"] if p["id"] == part_id]
    assert len(part) == 1 and part[0]["ref"] == composed, part
    slot = _card_slot(comps, ref, part_id)
    assert slot["kind"] == "connector" and slot["interface"] == iface, slot
    assert slot["accepts"] == [PAIRS[iface][1]], slot
    assert slot["lift"] == 0.0, slot


def test_a_card_with_two_connectors_of_a_kind_publishes_both(comps):
    slots = {c["id"]: c for c in comps["nokia/lalm-f@1"]["cages"] if c["interface"] == "da15"}
    assert sorted(slots) == ["alm-down", "alm-up"]
    assert all(c["accepts"] == [DA15] for c in slots.values())
    # and its DE-9 beside them is its own slot, with its own plug
    craft = _card_slot(comps, "nokia/lalm-f@1", "craft")
    assert craft["interface"] == "db9" and craft["accepts"] == [DB9]


def test_the_de9_and_vga_shells_are_one_size_and_their_plugs_do_not_swap(comps):
    """The premise, then the consequence. std/db9@1 and std/vga@1 are the same
    opening and their two plugs have one front shell section apart from the
    0.6 a socket shell is smaller by; what keeps a VGA plug out of a serial
    port is the interface, and no slot of either offers the other's plug."""
    a, b = _contract("std/db9@1"), _contract("std/vga@1")
    assert a["size"] == b["size"] and a["interface"] != b["interface"]
    seen = {"db9": 0, "hd15": 0}
    for ref, e in comps.items():
        for c in e.get("cages") or []:
            if c.get("interface") in seen:
                seen[c["interface"]] += 1
                assert c["accepts"] == [PAIRS[c["interface"]][1]], (ref, c["id"])
    assert seen["db9"] > 0 and seen["hd15"] > 0, seen


@pytest.mark.parametrize("ref", sorted(WRAPPERS))
def test_a_wrapper_presents_the_core_it_composes_at_its_own_mate(ref, comps):
    """common/db9-receptacle@1 and common/vga-receptacle@1 each compose one
    core as `shell` and state no interface: each presents that core as its
    own. Unlike the USB bezels they already NAME a point `mate`; it is not
    what is read, because a part with no interface forwards the point of the
    core it composes, and the two coincide exactly - the core's own mate,
    through the part's `at`, is the wrapper's."""
    w = _contract(ref)
    core = _contract(WRAPPERS[ref])
    assert "interface" not in w and "interface-at" not in w and w["kind"] == "component"
    assert [(p["ref"], p["id"]) for p in w["parts"]] == [(WRAPPERS[ref], "shell")]
    part = w["parts"][0]
    assert not part.get("rotate") and not part.get("lift")
    got, at, lift = presented_interface(w, lambda r: _contract(r))
    assert got == core["interface"] and lift == 0.0
    forwarded = [part["at"][0] + core["connection-points"]["mate"]["at"][0],
                 part["at"][1] + core["connection-points"]["mate"]["at"][1]]
    assert at == pytest.approx(forwarded)
    assert at == pytest.approx([15.4, 6.25])
    assert at == pytest.approx(w["connection-points"]["mate"]["at"])
    # the slot is the wrapper's placement, not a second slot on the part
    assert not comps[ref].get("cages")


def _standoff_centres(ref):
    """The two standoff centres a wrapper draws, off its skin: the bores
    behind the hex posts."""
    root = ET.parse(_skin_path(ref)).getroot()
    floor = [g for g in root.iter() if g.get("id") == "bore-floor"]
    assert len(floor) == 1
    pts = sorted((float(c.get("cx")), float(c.get("cy"))) for c in floor[0])
    assert len(pts) == 2
    return pts


@pytest.mark.parametrize("ref", sorted(WRAPPERS))
def test_a_wrappers_standoffs_are_on_the_size_e_mounting_centres(ref):
    """The premise of the thumbscrew test below: the standoffs are 24.99
    apart, level with the mate point and either side of it."""
    (lx, ly), (rx, ry) = _standoff_centres(ref)
    mx, my = _contract(ref)["connection-points"]["mate"]["at"]
    assert rx - lx == pytest.approx(24.99, abs=1e-6)
    assert ly == ry == my
    assert (lx + rx) / 2 == pytest.approx(mx, abs=1e-6)


def test_every_composed_dsub_core_is_a_slot_or_is_forwarded(comps):
    """The census: each `parts:` entry that is one of the four cores, or one
    of the two wrappers, is either published as a slot of the component that
    composes it, or is that component's one forwarded aperture (published
    where the component is placed). Only the two wrappers forward."""
    target = dict(CORE_IFACE)
    target.update({w: CORE_IFACE[core] for w, core in WRAPPERS.items()})
    seen = {r: 0 for r in target}
    forwarded = []
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        ref = f"{f.parts[-4]}/{c['name']}@{f.parts[-2][1:]}"
        for p in c.get("parts") or []:
            iface = target.get(p.get("ref"))
            if iface is None:
                continue
            seen[p["ref"]] += 1
            cages = {x["id"]: x for x in comps[ref].get("cages") or []}
            if p["id"] in cages:
                assert cages[p["id"]]["kind"] == "connector", (ref, p["id"])
                assert cages[p["id"]]["interface"] == iface, (ref, p["id"])
                assert cages[p["id"]]["accepts"] == [PAIRS[iface][1]], (ref, p["id"])
            else:
                got, _at, _lift = presented_interface(c, lambda r: _contract(r))
                assert got == iface and not c.get("interface"), (ref, p["id"])
                forwarded.append(ref)
    # the scan measured something: the counts the library held when this was
    # written, at least
    assert seen["std/db9@1"] >= 1 and seen["std/vga@1"] >= 1, seen
    assert seen["std/da15@1"] >= 3 and seen["std/db25@1"] >= 1, seen
    assert seen["common/db9-receptacle@1"] >= 26 and seen["common/vga-receptacle@1"] >= 1, seen
    # a forwarded core is published where its composer is PLACED, so its
    # composer has to be a part a face places: the two wrappers and nothing else
    assert sorted(forwarded) == sorted(WRAPPERS)


def test_every_dsub_connector_a_device_places_is_one_of_these_parts():
    """The other half of the census, on the device side: a device places a
    D-sub as one of the four bare cores or one of the two wrappers, and each
    of those is a slot where it is placed. A part that states a D-sub medium
    and is none of them is either a plug or a card that composes one."""
    known = set(CORE_IFACE) | set(WRAPPERS)
    media = {_contract(core)["attrs"]["media"] for core in CORE_IFACE}
    assert media == {"db9", "vga", "da15", "db25"}
    stating, cards = set(), set()
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        if (c.get("attrs") or {}).get("media") not in media or c.get("mates"):
            continue
        ref = f"{f.parts[-4]}/{c['name']}@{f.parts[-2][1:]}"
        if c.get("kind") == "module":
            assert any(p.get("ref") in known for p in c.get("parts") or []), ref
            cards.add(ref)
        else:
            stating.add(ref)
    assert stating == known, sorted(stating ^ known)
    assert cards, "no card states a D-sub medium; the module branch measured nothing"
    placed = {r: 0 for r in known}
    for f in sorted((LIB / "devices").glob("*/*/device.yaml")):
        d = yaml.safe_load(f.read_text())
        for view in (d.get("views") or {}).values():
            for p in ((view or {}).get("components") or {}).get("placements") or []:
                if p.get("ref") in placed:
                    placed[p["ref"]] += 1
    assert sum(placed.values()) >= 22, placed
    assert placed["common/db9-receptacle@1"] >= 8 and placed["common/vga-receptacle@1"] >= 6
    assert placed["std/vga@1"] >= 7 and placed["std/da15@1"] >= 1, placed


def test_each_interface_is_mated_by_its_one_plug(comps):
    """No gender changer, no adapter and no second hood: the one part in the
    library that mates each interface is its cable plug."""
    mating = {}
    for ref in comps:
        m = _contract(ref).get("mates")
        if m in PAIRS:
            mating.setdefault(m, []).append(ref)
    assert mating == {iface: [plug] for iface, (_core, plug) in PAIRS.items()}


# --- 3. the plugs --------------------------------------------------------------

@EACH
def test_it_is_a_plug_that_mates_its_interface(ref):
    d = _contract(ref)
    assert d["class"] == "port" and "behaviour" not in d
    assert d["mates"] == IFACE_OF[ref] and "interface" not in d
    name = ref.split("/")[1].split("@")[0]
    assert d["conforms"] == name and name in std()
    assert d["unplaced"] == _contract("generic/usb-a-plug@1")["unplaced"]


@EACH
def test_it_states_its_cores_medium_and_the_other_gender(ref):
    d = _contract(ref)
    core = _contract(CORE_OF[ref])
    gender = OTHER[PANEL_GENDER[IFACE_OF[ref]]]
    assert d["attrs"] == {"media": core["attrs"]["media"], "connector": IFACE_OF[ref],
                          "gender": gender}
    text = flat(d["provenance"]["gender"])
    assert text.startswith(f"{gender} - THE CORE IS {PANEL_GENDER[IFACE_OF[ref]].upper()}"), text
    assert CORE_OF[ref] in text


@EACH
def test_it_states_no_depth_and_its_length_is_in_the_registry(ref):
    d = _contract(ref)
    assert "d" not in d["size"], "a behaviour-less part's size.d is built as a pit"
    entry = std()[d["conforms"]]
    assert entry["depth"] == pytest.approx(FIGURES[ref][3])
    assert (entry["w"], entry["h"]) == (d["size"]["w"], d["size"]["h"])
    assert set(d["size-confidence"]) == {"w", "h"} and d["size-notes"]
    # the overall length is the front shell and everything behind the flange
    m, g = FIGURES[ref][0], FIGURES[ref][1]
    last = feats(ref)[CHAIN[ref][-2]]
    assert rear(last) - m + g == pytest.approx(FIGURES[ref][3])


@EACH
def test_its_box_is_the_widest_section_drawn(ref):
    """`size` is the end-on box of the widest drawn section, and nothing is
    drawn outside it: the thumbscrews sit inside the hood's own width."""
    d = _contract(ref)
    w, h = d["size"]["w"], d["size"]["h"]
    root = ET.parse(_skin_path(ref)).getroot()
    widest = 0.0
    for e in root.iter():
        tag = e.tag.split("}")[1]
        if tag == "rect":
            x, y, rw, rh = (float(e.get(k)) for k in ("x", "y", "width", "height"))
            assert x >= -EPS and y >= -EPS and x + rw <= w + EPS and y + rh <= h + EPS, e.get("id")
            widest = max(widest, rw)
        elif tag == "circle":
            cx, cy, r = (float(e.get(k)) for k in ("cx", "cy", "r"))
            assert cx - r >= -EPS and cx + r <= w + EPS and cy - r >= -EPS and cy + r <= h + EPS
    assert widest == pytest.approx(w)


@EACH
def test_its_fields_are_the_cable(ref):
    f = _contract(ref)["fields"]
    assert set(f) == {"cable-od", "jacket-color"}
    assert f["cable-od"]["default"] == pytest.approx(FIGURES[ref][4])
    assert f["jacket-color"]["default"] == "#1c1c1c"
    assert "jacket-colour" in _contract(ref)["provenance"]


@EACH
def test_the_stub_is_30_long_from_where_the_plug_ends(ref):
    f = feats(ref)
    last, stub = f[CHAIN[ref][-2]], f["stub"]
    assert stub["cyl"] == pytest.approx(STUB)
    assert stub["lift"] == pytest.approx(rear(last))


@EACH
def test_the_solids_chain_from_the_front_shell_to_the_stub(ref):
    """The front shell, then the hood in its steps, then (on the moulded VGA
    plug) the strain relief, then the stub: each starts where the one before
    it ends, with no gap and no overlap. The two thumbscrews start at the rear
    of the section that holds them. Nothing else is built."""
    f = feats(ref)
    names = CHAIN[ref]
    assert set(f) == set(names) | set(SCREWS)
    for a, b in zip(names, names[1:]):
        assert float(f[b]["lift"]) == pytest.approx(rear(f[a])), (ref, a, b)
    for s in SCREWS:
        assert float(f[s]["lift"]) == pytest.approx(rear(f[SCREWS_FROM[ref]])), (ref, s)
        assert f[s]["cyl"] > 0 and f[s]["cyl"] == f[SCREWS[0]]["cyl"]
        # a thumbscrew is reached from behind the plug: it ends in front of
        # the panel plane by more than the standoff it threads into
        assert rear(f[s]) > FIGURES[ref][0] + 10


@EACH
def test_the_cable_leaves_from_the_stub(ref):
    d = _contract(ref)
    cps = d["connection-points"]
    assert cps["cable"]["on"] == "stub"
    assert cps["cable"]["at"] == cps["mate"]["at"]
    assert cps["mate"]["at"] == pytest.approx([d["size"]["w"] / 2, d["size"]["h"] / 2])


@EACH
def test_the_stub_circle_is_bound_to_the_fields(ref):
    s = _skin_path(ref).read_text()
    for node in feats(ref):
        assert f'id="{node}"' in s, node
    stub = s[s.index('id="stub"'):].split("/>", 1)[0]
    assert 'data-r-from="cable-od"' in stub
    assert 'data-fill-from="jacket-color"' in stub
    assert s.count("data-fill-from") == 1 and s.count("data-r-from") == 1
    r = float(stub.split('r="', 1)[1].split('"', 1)[0])
    assert r == pytest.approx(FIGURES[ref][4] / 2, abs=0.005)
    # L73: the node a field paints states no relief colour
    assert "color" not in feats(ref)["stub"]


@EACH
def test_no_mark_is_drawn_on_the_hood(ref):
    """No logo, no part number and no screw slot: the skin is the outlines
    its relief builds from and nothing else, and none of it is text."""
    root = ET.parse(_skin_path(ref)).getroot()
    drawn = [e for e in root.iter() if e is not root]
    assert sorted(e.get("id") for e in drawn) == sorted(feats(ref))
    assert all(e.tag.split("}")[1] in ("rect", "path", "circle") for e in drawn)


def _d_flats(path):
    """The two horizontal runs of a D outline, as (y, length), top first."""
    nums = [float(n) for n in re.findall(r"-?\d+\.\d+", path)]
    pts = []
    tokens = re.findall(r"[MLAZ]|-?\d+\.?\d*", path)
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in "ML":
            pts.append((float(tokens[i + 1]), float(tokens[i + 2])))
            i += 3
        elif t == "A":
            pts.append((float(tokens[i + 6]), float(tokens[i + 7])))
            i += 8
        else:
            i += 1
    assert nums and len(pts) == 8, pts
    runs = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        if abs(a[1] - b[1]) < 1e-6 and abs(a[0] - b[0]) > 1:
            runs.append((a[1], abs(a[0] - b[0])))
    assert len(runs) == 2, runs
    return sorted(runs)


@EACH
def test_the_front_shell_has_its_long_side_where_the_core_has_it(ref):
    """Which way is up. The core draws the long side of its D at the top; so
    does the plug, so a turned core carries the plug round the right way.
    The shell is centred on the mate point and is the only keyed outline."""
    def path_of(r, node):
        root = ET.parse(_skin_path(r)).getroot()
        return next(e for e in root.iter() if e.get("id") == node).get("d")
    core_d = path_of(CORE_OF[ref], "opening").split("Z")[0]
    (cy0, clong), (cy1, cshort) = _d_flats(core_d)
    assert cy0 < cy1 and clong > cshort, "the core no longer draws its long side up"
    (y0, long_), (y1, short) = _d_flats(path_of(ref, "shell"))
    assert y0 < y1 and long_ > short
    mx, my = _contract(ref)["connection-points"]["mate"]["at"]
    assert (y0 + y1) / 2 == pytest.approx(my, abs=1e-3)
    # the plug's shell passes into or over the core's: it is narrower than
    # the outline the core draws
    assert long_ < clong
    text = flat(_contract(ref)["provenance"]["orientation"])
    assert " UP" in text and CORE_OF[ref] in text
    assert "THE KEY IS NOT VISIBLE FROM THE CABLE END" in text


@EACH
def test_the_thumbscrews_are_on_the_mounting_centres_of_its_shell_size(ref):
    d = _contract(ref)
    root = ET.parse(_skin_path(ref)).getroot()
    got = {e.get("id"): e for e in root.iter() if e.get("id") in SCREWS}
    lx, rx = float(got["screw-l"].get("cx")), float(got["screw-r"].get("cx"))
    mx, my = d["connection-points"]["mate"]["at"]
    assert rx - lx == pytest.approx(FIGURES[ref][5], abs=1e-6)
    assert (lx + rx) / 2 == pytest.approx(mx, abs=1e-6)
    assert float(got["screw-l"].get("cy")) == float(got["screw-r"].get("cy")) == my
    assert got["screw-l"].get("r") == got["screw-r"].get("r")
    # the same figure the core's registry entry gives for its mounting holes
    notes = flat(std()[_contract(CORE_OF[ref])["conforms"]]["notes"])
    assert f"{FIGURES[ref][5]:g}" in notes, (ref, FIGURES[ref][5])


# --- 4. the seated depth, in the contracts --------------------------------------

@EACH
def test_the_flange_stands_the_mating_dimension_in_front_of_the_core_face(ref):
    m, g, _modelled, _overall, _od, _c, _text = FIGURES[ref]
    f = feats(ref)
    # the front shell ends at the flange face, and reaches back by its length
    assert rear(f["shell"]) == pytest.approx(m)
    assert float(f["shell"]["lift"]) == pytest.approx(m - g)
    assert 0 < m - g < 1.0
    # everything behind the shell starts on the flange face
    assert float(f[CHAIN[ref][1]]["lift"]) == pytest.approx(m)


@EACH
def test_the_core_models_the_mating_dimension(ref):
    """Fails by design when a core's depth is revised: the plug's
    provenance.seated-depth quotes the figure and says the two agree, and is
    to be read again. A plug's flange and its core's modelled lip are one
    plane, which is also where the wrappers end their standoffs."""
    m, _g, modelled, _overall, _od, _c, _text = FIGURES[ref]
    core = _contract(CORE_OF[ref])
    assert core["size"]["d"] == pytest.approx(modelled) == pytest.approx(m)
    lip = next(f for f in core["relief"]["features"] if f["node"] == "opening")
    assert float(lip["out"]) == pytest.approx(m)
    text = flat(_contract(ref)["provenance"]["seated-depth"])
    assert f"{CORE_OF[ref]} states its depth as {modelled:g}" in text, text


@pytest.mark.parametrize("ref", sorted(WRAPPERS))
def test_a_wrappers_standoffs_end_where_the_plug_flange_is(ref):
    w = _contract(ref)
    post = next(f for f in w["relief"]["features"] if f["node"] == "standoffs")
    plug = PAIRS[_contract(WRAPPERS[ref])["interface"]][1]
    assert float(post["out"]) == pytest.approx(FIGURES[plug][0])


@EACH
def test_the_ruling_is_recorded_in_provenance(ref):
    text = flat(_contract(ref)["provenance"]["seated-depth"])
    assert "MEASURED FROM THE FACE THE CORE PRESENTS" in text
    assert "THE CORE AS MODELLED AGREES ON THE SEAT" in text
    assert "WHAT THE CORE DOES NOT AGREE WITH IS ITS OWN SHELL" in text
    assert "REVISIT" in text
    assert FIGURES[ref][6] in text, text


# --- 5. seated on real connectors -------------------------------------------------

# (plug, device, configuration, view, the host's data-path, the part the host
# IS). Each plug seats on a chassis connector where the library has one and on
# a card in a bay; the DE-9 and VGA plugs seat through their wrappers and the
# VGA plug on a bare core as well. Two of the hosts are turned.
SEATS = [
    (DB9, "dell/r740xd", "lff12-rc0-noriser", "rear", "serial", "common/db9-receptacle@1"),
    (DB9, "nokia/sr-12", "base", "front", "sfm-a/module/alarm", "common/db9-receptacle@1"),
    (HD15, "dell/r740xd", "lff12-rc0-noriser", "rear", "vga", "common/vga-receptacle@1"),
    (HD15, "dell/r740xd", "lff12-rc0-noriser", "front", "vga", "std/vga@1"),
    (HD15, "dell/r660", "sff10-rc1-2a3a", "rear", "rio/module/video", "common/vga-receptacle@1"),
    (DA15, "telco-systems/tm-7124s", "base", "front", "alarm-io", "std/da15@1"),
    (DA15, "nokia/lmfs-f", "base", "front", "alm/module/alm-up", "std/da15@1"),
    (DB25, "nokia/sr-12", "base", "rear", "pem-1/module/status", "std/db25@1"),
]
SEAT_IDS = [f"{s[0].split('/')[1].split('@')[0]}-in-{s[1].split('/')[1]}-{s[3]}-{s[4].split('/')[0]}"
            for s in SEATS]
EACH_SEAT = pytest.mark.parametrize("seat", SEATS, ids=SEAT_IDS)
# the seats whose slot is the device's own (a chassis placement, bare or wrapped)
CHASSIS_SEATS = [s for s in SEATS if "/" not in s[4]]
WRAPPED_SEATS = [s for s in SEATS if s[5] in WRAPPERS]


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
    tmp = tmp_path_factory.mktemp("dsubplugs")
    jobs = {}
    for ref, device, config, view, host, _is in SEATS:
        jobs.setdefault((device, config), {})[host.replace("/module/", "/")] = ref
    out = {}
    for (device, config), occupants in jobs.items():
        def edit(d, config=config, occupants=occupants):
            cfg = d["configurations"][config]
            cfg["occupants"] = {**(cfg.get("occupants") or {}), **occupants}
        name, o = _render(tmp, device, edit)
        configs = json.loads((o / f"{name}.configs.json").read_text())
        for view in {s[3] for s in SEATS if (s[1], s[2]) == (device, config)}:
            root = ET.parse(face_file(o, name, config, view)).getroot()
            out[(device, config, view)] = (root, {c: p for p in root.iter() for c in p}, configs)
    assert len(out) == len({(s[1], s[2], s[3]) for s in SEATS})
    return out


def _seat(seated, seat):
    ref, device, config, view, host_path, host_is = seat
    root, parents, configs = seated[(device, config, view)]
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
def test_it_seats_with_its_mate_on_the_connectors_mate(seated, seat):
    parents, host, occ, _ = _seat(seated, seat)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)


@pytest.mark.parametrize("seat", WRAPPED_SEATS,
                         ids=[SEAT_IDS[SEATS.index(s)] for s in WRAPPED_SEATS])
def test_through_a_wrapper_it_seats_on_the_core_itself(seated, seat):
    """The point a wrapper's slot seats on is the composed core's own mate,
    not merely a point the wrapper names: measured on the core's element in
    the compiled face."""
    parents, host, occ, _ = _seat(seated, seat)
    shells = [e for e in host.iter()
              if (e.get("data-ref") or "").startswith(WRAPPERS[seat[5]])]
    assert len(shells) == 1, [e.get("id") for e in shells]
    core_mate = _contract(WRAPPERS[seat[5]])["connection-points"]["mate"]["at"]
    cx, cy = device_point(parents, shells[0], core_mate)
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(cx - ox) < EPS and abs(cy - oy) < EPS, ((cx, cy), (ox, oy))


@pytest.mark.parametrize("seat", WRAPPED_SEATS,
                         ids=[SEAT_IDS[SEATS.index(s)] for s in WRAPPED_SEATS])
def test_its_thumbscrews_are_over_the_wrappers_standoffs(seated, seat):
    """Each thumbscrew centre lands on a standoff centre, in the device frame,
    within 0.01 mm: the screw threads into the post it is drawn over."""
    ref = seat[0]
    parents, host, occ, _ = _seat(seated, seat)
    posts = sorted(device_point(parents, host, p) for p in _standoff_centres(seat[5]))
    el = _nodes(occ, ref)
    screws = sorted(device_point(parents, el[s], (float(el[s].get("cx")), float(el[s].get("cy"))))
                    for s in SCREWS)
    assert len(posts) == len(screws) == 2
    for (px, py), (sx, sy) in zip(posts, screws):
        assert abs(px - sx) < 0.01 and abs(py - sy) < 0.01, (posts, screws)
    # and the posts end on the plane the screws' section starts from or behind
    assert lift_of(parents, el[SCREWS[0]]) >= FIGURES[ref][0] - EPS


@pytest.mark.parametrize("seat", [s for s in SEATS if s[5] not in WRAPPERS],
                         ids=[SEAT_IDS[SEATS.index(s)] for s in SEATS if s[5] not in WRAPPERS])
def test_on_a_bare_core_its_thumbscrews_are_either_side_of_the_shell(seated, seat):
    """A bare core draws no standoffs and the plug still shows its screws:
    each is half the mounting centres from the mate point, along the long axis
    of the core however it is turned."""
    ref = seat[0]
    parents, host, occ, _ = _seat(seated, seat)
    mx, my = device_point(parents, host, cage_mate(host))
    core = _contract(seat[5])
    ex, ey = device_point(parents, host, (core["size"]["w"], core["size"]["h"] / 2))
    el = _nodes(occ, ref)
    for s in SCREWS:
        sx, sy = device_point(parents, el[s], (float(el[s].get("cx")), float(el[s].get("cy"))))
        dist = ((sx - mx) ** 2 + (sy - my) ** 2) ** 0.5
        assert dist == pytest.approx(FIGURES[ref][5] / 2, abs=1e-6)
        # on the line through the mate point and the middle of the core's end
        cross = (sx - mx) * (ey - my) - (sy - my) * (ex - mx)
        assert abs(cross) < 1e-6, (s, cross)


def test_two_of_the_seats_are_turned():
    """The premise of the turned seats, read off the library: a Dell front
    panel places its bare VGA core at 270, and the SR-12 seats its SF/CPM in a
    bay at 90, which carries the card's DE-9 round with it."""
    d = yaml.safe_load((LIB / "devices/dell/r740xd/device.yaml").read_text())
    hit = [p for p in d["views"]["front"]["components"]["placements"] if p.get("id") == "vga"]
    assert len(hit) == 1 and hit[0]["ref"] == "std/vga@1" and hit[0]["rotate"] == 270
    d = yaml.safe_load((LIB / "devices/nokia/sr-12/device.yaml").read_text())
    bay = [b for b in d["views"]["front"]["components"]["bays"] if b["id"] == "sfm-a"]
    assert len(bay) == 1 and bay[0]["rotate"] == 90 and bay[0]["default"] == "nokia/sfm4-12@1"
    # and the fifteen Cisco route processors turn the wrapper itself
    rsp = _contract("cisco/a9k-rsp440-se@2")
    assert [p.get("rotate") for p in rsp["parts"] if p["id"] == "alarm-out"] == [90]


def test_the_turned_seats_are_measured_turned(seated):
    """Not a flat pass: two of the seats above are drawn turned in the
    compiled face, a quarter turn each way, so the turn is measured and not
    assumed."""
    turns = set()
    for seat in SEATS:
        parents, host, _occ, _ = _seat(seated, seat)
        m = device_matrix(parents, host)
        if abs(m[0][0]) < EPS and abs(m[1][1]) < EPS:
            turns.add(round(m[1][0]))
    assert turns == {1, -1}, turns


@EACH_SEAT
def test_the_seated_plug_stands_off_by_the_ruling(seated, seat):
    """The compiled depths, in the device frame: the front shell ends on the
    flange plane, the mating dimension in front of the face the core presents,
    and reaches back by its own length; the hood starts on that plane; the
    stub ends overall - shell + 30 beyond it."""
    ref = seat[0]
    parents, host, occ, _configs = _seat(seated, seat)
    m, g, _modelled, overall, _od, _c, _text = FIGURES[ref]
    el = _nodes(occ, ref)
    base = lift_of(parents, occ)
    assert base == pytest.approx(lift_of(parents, host), abs=EPS)
    assert lift_of(parents, el["shell"]) - base == pytest.approx(m - g, abs=EPS)
    assert _front(parents, el["shell"]) - base == pytest.approx(m, abs=EPS)
    assert lift_of(parents, el[CHAIN[ref][1]]) - base == pytest.approx(m, abs=EPS)
    assert _front(parents, el[CHAIN[ref][-2]]) - base == pytest.approx(m + overall - g, abs=EPS)
    assert _front(parents, el["stub"]) - base == pytest.approx(m + overall - g + STUB, abs=EPS)


@pytest.mark.parametrize("seat", CHASSIS_SEATS,
                         ids=[SEAT_IDS[SEATS.index(s)] for s in CHASSIS_SEATS])
def test_a_chassis_connector_publishes_a_slot_that_offers_exactly_its_plug(seated, seat):
    """A bare core and a wrapper alike: the slot is the placement, it offers
    its one plug and nothing else, and it is published at the lift and the
    point the build seated the plug at."""
    ref, device, _config, view, pid, host_is = seat
    d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
    hits = [p for p in d["views"][view]["components"]["placements"] if p.get("id") == pid]
    assert len(hits) == 1 and hits[0]["ref"] == host_is, hits
    parents, host, occ, configs = _seat(seated, seat)
    slot = next(c for c in configs["cages"][view] if c["id"] == pid)
    assert slot["kind"] == "connector" and slot["interface"] == IFACE_OF[ref], slot
    assert slot["accepts"] == [ref], slot
    assert slot["default"] is None, slot
    # `cages` describes the default configuration; the seat itself is in the
    # entry of the configuration it was written on
    entry = [c for c in configs["configs"] if c["name"] == _config]
    assert len(entry) == 1 and entry[0]["occupants"][pid] == ref, entry
    if configs["default"] == _config:
        assert slot["occupant"] == ref, slot
    assert slot["lift"] == pytest.approx(lift_of(parents, occ), abs=EPS)
    assert tuple(slot["mate"]) == pytest.approx(
        device_point(parents, host, cage_mate(host)), abs=1e-3)


# --- 6. 3D solids ----------------------------------------------------------------

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
    # end to end in the compiled drawing, as in the contract
    names = CHAIN[ref]
    for a, b in zip(names, names[1:]):
        assert lift_of(parents, el[b]) == pytest.approx(_front(parents, el[a]), abs=EPS), (a, b)
    for s in SCREWS:
        assert lift_of(parents, el[s]) == pytest.approx(
            _front(parents, el[SCREWS_FROM[ref]]), abs=EPS), s


# --- 7. the stub's diameter -------------------------------------------------------

def _diameter(parents, circle):
    """relief.js builds a cyl at radius min(w, h) / 2 of the face box."""
    assert circle.tag.endswith("circle"), circle.tag
    cx, cy, r = (float(circle.get(k)) for k in ("cx", "cy", "r"))
    pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    x0, y0, x1, y1 = box(apply(device_matrix(parents, circle), pts))
    assert x1 - x0 == pytest.approx(y1 - y0, abs=EPS)
    return min(x1 - x0, y1 - y0)


@EACH_SEAT
def test_the_stub_is_the_default_cable_od(seated, seat):
    ref = seat[0]
    parents, host, occ, _ = _seat(seated, seat)
    stub = _nodes(occ, ref)["stub"]
    assert _diameter(parents, stub) == pytest.approx(FIGURES[ref][4], abs=EPS)
    # and it is centred on the seat
    cx, cy = device_point(parents, stub, (float(stub.get("cx")), float(stub.get("cy"))))
    assert (cx, cy) == pytest.approx(device_point(parents, host, cage_mate(host)), abs=EPS)


# A placement's attrs set the field (an occupant carries only a ref): each
# plug placed directly, `mate-to` a real connector, with a cable-od of its own.
# The library places no bare DB-25 on a chassis, so the copy of the one device
# that takes the DA-15 plug is given a std/db25@1 placement to carry it.
OVERRIDES = [
    (DB9, "supermicro/sys-111e-wr", "base", "rear", "serial", 5.0),
    (HD15, "supermicro/sys-111e-wr", "base", "rear", "vga", 5.0),
    (DA15, "telco-systems/tm-7124s", "base", "front", "alarm-io", 5.5),
    (DB25, "telco-systems/tm-7124s", "base", "front", "added-db25", 10.0),
]


@pytest.fixture(scope="module")
def overridden(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("dsubplugod")
    jobs = {}
    for case in OVERRIDES:
        jobs.setdefault((case[1], case[2], case[3]), []).append(case)
    out = {}
    for (device, config, view), cases in jobs.items():
        def edit(d, view=view, cases=cases):
            places = d["views"][view]["components"]["placements"]
            for ref, _device, _config, _view, host, od in cases:
                hits = [p for p in places if p.get("id") == host]
                if host == "added-db25":
                    assert not hits
                    # clear of the face: nothing here measures where it is
                    places.append({"ref": CORE_OF[ref], "id": host, "at": [0.0, 0.0]})
                else:
                    assert len(hits) == 1, hits
                    assert CORE_IFACE.get(hits[0]["ref"], CORE_IFACE.get(
                        WRAPPERS.get(hits[0]["ref"]))) == IFACE_OF[ref], hits
                places.append({"ref": ref, "id": f"cable-{host}", "mate-to": host,
                               "attrs": {"cable-od": od}})
        name, o = _render(tmp, device, edit)
        root = ET.parse(face_file(o, name, config, view)).getroot()
        for case in cases:
            out[case[0]] = (root, {c: p for p in root.iter() for c in p})
    assert set(out) == set(PLUGS)
    return out


@pytest.mark.parametrize("case", OVERRIDES, ids=[c[0].split("/")[1] for c in OVERRIDES])
def test_a_placements_cable_od_sets_the_stub(overridden, case):
    ref, _device, _config, _view, host_id, od = case
    assert FIGURES[ref][4] != pytest.approx(od, abs=0.1)
    root, parents = overridden[ref]
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
    # only the stub follows the cable: the thumbscrews keep their drawn size
    for s in SCREWS:
        assert float(el[s].get("r")) * 2 != pytest.approx(od, abs=0.01)
        assert _diameter(parents, el[s]) == pytest.approx(
            2 * float(ET.parse(_skin_path(ref)).getroot().find(
                f".//*[@id='{s}']").get("r")), abs=EPS)
