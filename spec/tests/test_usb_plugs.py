"""USB receptacles are connector slots, and the cable plugs that seat in them
(#786, docs/connectors-usb-design.md).

The three receptacles (std/usb-a@1, std/micro-usb@1, std/usb-c@1) each present
an interface spec/schemas/connectors.yaml now lists, so every one of them is a
slot; generic/usb-a-plug@1, generic/micro-usb-b-plug@1 and
generic/usb-c-plug@1 mate them. These run against the real library, a
components.json the indexer builds here and device copies rendered here, never
a possibly stale dist.

THE SEATED DEPTH IS A RULING, and the tests below hold the parts to it: each
plug seats to the depth the USB drawing gives for its shell, measured from the
face the receptacle presents, so it leaves its shell length less that
insertion in front of the face. No plug figure is derived from the depth a
receptacle MODELS; all three modelled depths disagree with the drawing, each
plug records by how much, and a test here fails by design when one of them is
revised, because the plug's own provenance quotes it.
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
from portrayal import components_index
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

A, MICRO, C = "generic/usb-a-plug@1", "generic/micro-usb-b-plug@1", "generic/usb-c-plug@1"

# interface -> (the receptacle that presents it, the plug that mates it)
PAIRS = {
    "usb-a": ("std/usb-a@1", A),
    "micro-usb-b": ("std/micro-usb@1", MICRO),
    "usb-c": ("std/usb-c@1", C),
}
JACK_OF = {plug: jack for jack, plug in PAIRS.values()}
IFACE_OF = {plug: iface for iface, (_jack, plug) in PAIRS.items()}
PLUGS = sorted(JACK_OF)
EACH = pytest.mark.parametrize("ref", PLUGS)

# plug -> (shell length, how far the USB drawing lets the shell in, the depth
# the receptacle MODELS, overall length, default cable-od, the arithmetic its
# provenance prints). The first two are the USB drawings'; the third is the
# RECEPTACLE's own `size.d`, pinned here so a change to it fails and the
# plug's provenance, which quotes it, is read again. No plug figure is derived
# from it.
FIGURES = {
    A: (11.75, 8.88, 13.7, 47.75, 4.06, "11.75 - 8.88 = 2.87"),
    MICRO: (5.4, 3.5, 5.9, 32.5, 4.06, "5.4 - 3.5 = 1.9"),
    C: (6.65, 6.20, 6.5, 50.85, 5.2, "6.65 - 6.20 = 0.45"),
}
# the overmould steps each plug builds, in order, between `shell` and the
# strain relief
BODY = {A: ["body", "body-rear"], MICRO: ["body"], C: ["body"]}
WRAPPERS = ["common/usb-a@2", "common/usb-a-bezel@1"]


def std():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


def feats(ref):
    return {f["node"]: f for f in _contract(ref)["relief"]["features"]}


def chain(ref):
    return ["shell"] + BODY[ref] + ["relief-boot", "stub"]


def rear(f):
    """Where a relief feature ends, from the part's own face: an `out` is
    absolute, a `cyl` runs its length from its `lift`."""
    if f.get("out") is not None:
        return float(f["out"])
    return float(f.get("lift") or 0.0) + float(f["cyl"])


# --- 1. the registry -----------------------------------------------------------

@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_usb_interface_is_a_connector_citing_its_standard(iface):
    reg = render_mod._connector_registry()
    assert iface in reg, iface
    jack = _contract(PAIRS[iface][0])
    assert reg[iface]["standard"] in std(), reg[iface]
    assert reg[iface]["standard"] == jack["conforms"]


@pytest.mark.parametrize("iface", sorted(PAIRS))
def test_each_receptacle_presents_its_interface_at_its_face(iface):
    jack = _contract(PAIRS[iface][0])
    assert jack["class"] == "port" and jack["interface"] == iface
    got, at, lift = presented_interface(jack, lambda r: _contract(r))
    assert got == iface
    op = jack["elements"]["opening"]
    assert at == pytest.approx([op["at"][0] + op["size"][0] / 2, op["at"][1] + op["size"][1] / 2])
    # the slot is the receptacle's own face: the ruling stands the plug off by
    # its own relief, not by a lift the receptacle states
    assert lift == 0.0


def test_the_micro_usb_jack_gained_its_interface_and_kept_its_drawing():
    """The one receptacle this work touched: an interface and a mate point,
    and nothing a device placed against."""
    jack = _contract("std/micro-usb@1")
    assert jack["size"] == {"w": 7.5, "h": 2.75, "d": 5.9}
    assert jack["elements"] == {"opening": {"at": [0.33, 0.48], "size": [6.85, 1.8],
                                            "class": "cutout"}}
    assert jack["version"].split(".")[0] == "1"
    assert jack["attrs"]["media"] == "micro-usb-b" == jack["conforms"]


# --- 2. the slots --------------------------------------------------------------

@pytest.fixture(scope="module")
def comps():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


# A receptacle on a card that seats in a bay: a nested slot in the card's own
# components.json entry.
CARD = {
    "usb-a": ("juniper/jnp304-re@1", "usb"),
    "micro-usb-b": ("commscope/ar3002e@1", "usb"),
    "usb-c": ("nokia/lbnt-a@1", "usb"),
}


@pytest.mark.parametrize("iface", sorted(CARD))
def test_a_cards_receptacle_is_a_nested_slot_that_offers_its_plug(iface, comps):
    ref, part_id = CARD[iface]
    card = _contract(ref)
    assert card["kind"] == "module", ref
    part = [p for p in card["parts"] if p["id"] == part_id]
    assert len(part) == 1 and part[0]["ref"] == PAIRS[iface][0], part
    slot = _card_slot(comps, ref, part_id)
    assert slot["kind"] == "connector" and slot["interface"] == iface, slot
    assert slot["accepts"] == [PAIRS[iface][1]], slot
    assert slot["lift"] == 0.0, slot


def test_a_card_with_two_receptacles_publishes_both(comps):
    slots = {c["id"]: c for c in comps["nokia/lbnt-a@1"]["cages"] if c["interface"] == "usb-c"}
    assert sorted(slots) == ["debug", "usb"]
    assert all(c["accepts"] == [C] for c in slots.values())


def test_a_card_seated_in_another_card_does_not_publish_its_lone_receptacle(comps):
    """THE ONE KNOWN GAP, held here so it cannot widen and so closing it fails
    this test. commscope/cc3008@1 seats in the `cc` bay of a CA3008 carrier,
    which is itself a card, and composes one interface-bearing part: its
    Micro-USB jack. A card writes its bays as a mapping, the indexer's
    `seated_in_bays` reads only a device view's list, so the CC3008 is taken
    for a placed wrapper that forwards its one aperture and components.json
    lists no slot for it. The BUILD still seats a plug there by its deep key
    (SEATS below). docs/connectors-usb-design.md section 3."""
    carrier = _contract("commscope/ca3008@1")
    assert isinstance(carrier["bays"], dict)
    assert "commscope/cc3008@1" in carrier["bays"]["cc"]["accepts"]
    assert "commscope/cc3008@1" not in components_index.seated_in_bays([str(LIB)])
    cc = _contract("commscope/cc3008@1")
    assert cc["kind"] == "module"
    assert [p["id"] for p in cc["parts"] if p["ref"] == "std/micro-usb@1"] == ["usb"]
    got, _at, _lift = presented_interface(cc, lambda r: _contract(r))
    assert got == "micro-usb-b" and "interface" not in cc
    assert not comps["commscope/cc3008@1"].get("cages")


@pytest.mark.parametrize("ref", WRAPPERS)
def test_a_bezel_presents_the_receptacle_it_composes(ref, comps):
    """common/usb-a@2 and common/usb-a-bezel@1 each compose one std/usb-a@1 and
    state no interface: each presents that receptacle as its own, at the point
    its own `usb` connection point already named, so the slot is the bezel's
    placement and not a second slot on the part."""
    w = _contract(ref)
    assert "interface" not in w and w["kind"] == "component"
    assert [p["ref"] for p in w["parts"]] == ["std/usb-a@1"]
    got, at, lift = presented_interface(w, lambda r: _contract(r))
    assert got == "usb-a" and lift == 0.0
    assert at == pytest.approx(w["connection-points"]["usb"]["at"])
    assert not comps[ref].get("cages")


def test_every_composed_usb_receptacle_is_a_slot_or_is_forwarded(comps):
    """The census: each `parts:` entry that is one of the three receptacles is
    either published as a slot of the component that composes it, or is that
    component's one forwarded aperture (published where the component is
    placed). One card in a card is the exception, and it is named."""
    jack_iface = {jack: iface for iface, (jack, _plug) in PAIRS.items()}
    seen = {iface: 0 for iface in PAIRS}
    forwarded = []
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        ref = f"{f.parts[-4]}/{c['name']}@{f.parts[-2][1:]}"
        for p in c.get("parts") or []:
            iface = jack_iface.get(p.get("ref"))
            if iface is None:
                continue
            seen[iface] += 1
            cages = {x["id"]: x for x in comps[ref].get("cages") or []}
            if p["id"] in cages:
                assert cages[p["id"]]["kind"] == "connector", (ref, p["id"])
                assert cages[p["id"]]["interface"] == iface, (ref, p["id"])
                assert cages[p["id"]]["accepts"] == [PAIRS[iface][1]], (ref, p["id"])
            else:
                got, _at, _lift = presented_interface(c, lambda r: _contract(r))
                assert got == iface and not c.get("interface"), (ref, p["id"])
                forwarded.append((ref, c["kind"]))
    # the scan measured something: the counts the library held when this was
    # written, at least - less re-s-1300-v's one USB-A, removed with the MX960
    # vertical twins in #261 (the MX960's SCB seats juniper/re-s-1300@1 now)
    assert seen["usb-a"] >= 31 and seen["micro-usb-b"] >= 18 and seen["usb-c"] >= 2, seen
    # A forwarded receptacle is published where its composer is PLACED, so
    # its composer has to be a part a face places: the two bezels. The third
    # is a card a card holds, which nothing places - the known gap the test
    # above describes, named here and nowhere waived.
    assert sorted(forwarded) == sorted([(w, "component") for w in WRAPPERS]
                                       + [("commscope/cc3008@1", "module")])


def test_every_usb_receptacle_a_device_places_is_one_of_these_parts():
    """The other half of the census, on the device side: a device places a USB
    receptacle as one of the three bare parts or one of the two bezels, and
    each of those five is a slot where it is placed (the tests above and the
    seats below). A sixth part that states a USB medium would be a receptacle
    nothing here covers."""
    known = set(JACK_OF.values()) | set(WRAPPERS)
    usb_media = {"usb-a", "usb-c", "micro-usb-b"}
    stating = set()
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(f.read_text())
        if (c.get("attrs") or {}).get("media") in usb_media and not c.get("mates"):
            stating.add(f"{f.parts[-4]}/{c['name']}@{f.parts[-2][1:]}")
    assert stating == known, sorted(stating ^ known)
    placed = {r: 0 for r in known}
    for f in sorted((LIB / "devices").glob("*/*/device.yaml")):
        d = yaml.safe_load(f.read_text())
        for view in (d.get("views") or {}).values():
            for p in ((view or {}).get("components") or {}).get("placements") or []:
                if p.get("ref") in placed:
                    placed[p["ref"]] += 1
    assert all(n > 0 for n in placed.values()), placed
    assert placed["std/usb-a@1"] >= 137 and placed["std/micro-usb@1"] >= 40, placed
    assert placed["std/usb-c@1"] >= 9, placed


# --- 3. the plugs --------------------------------------------------------------

@EACH
def test_it_is_a_plug_that_mates_its_interface(ref):
    d = _contract(ref)
    assert d["class"] == "port" and "behaviour" not in d
    assert d["mates"] == IFACE_OF[ref] and "interface" not in d
    name = ref.split("/")[1].split("@")[0]
    assert d["conforms"] == name and name in std()
    assert d["unplaced"]


@EACH
def test_it_states_its_connector_and_no_generation(ref):
    """A generic plug is the connector, not the bus: its media is the key its
    receptacle states, and it claims no speed and no USB generation."""
    d = _contract(ref)
    jack = _contract(JACK_OF[ref])
    assert d["attrs"] == {"media": jack["attrs"]["media"], "connector": IFACE_OF[ref]}
    assert not {"speed", "usb", "generation"} & set(d["attrs"])


@EACH
def test_it_states_no_depth_and_its_length_is_in_the_registry(ref):
    d = _contract(ref)
    assert "d" not in d["size"], "a behaviour-less part's size.d is built as a pit"
    entry = std()[d["conforms"]]
    assert entry["depth"] == pytest.approx(FIGURES[ref][3])
    assert (entry["w"], entry["h"]) == (d["size"]["w"], d["size"]["h"])
    assert set(d["size-confidence"]) == {"w", "h"} and d["size-notes"]


@EACH
def test_its_fields_are_the_cable(ref):
    f = _contract(ref)["fields"]
    assert set(f) == {"cable-od", "jacket-color"}
    assert f["cable-od"]["default"] == pytest.approx(FIGURES[ref][4])
    assert f["jacket-color"]["default"] == "#1c1c1c"


@EACH
def test_the_stub_is_30_long_from_the_end_of_the_strain_relief(ref):
    f = feats(ref)
    boot, stub = f["relief-boot"], f["stub"]
    assert stub["cyl"] == pytest.approx(STUB)
    assert stub["lift"] == pytest.approx(rear(boot))
    assert "cyl" in boot


@EACH
def test_the_solids_chain_from_the_receptacle_face_to_the_stub(ref):
    """shell, then the overmould (in one or two steps), then the strain
    relief, then the stub: each starts where the one before it ends, with no
    gap and no overlap, and nothing else is built."""
    f = feats(ref)
    names = chain(ref)
    assert set(f) == set(names)
    assert not f["shell"].get("lift")
    for a, b in zip(names, names[1:]):
        assert float(f[b]["lift"]) == pytest.approx(rear(f[a])), (ref, a, b)


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
    r = float(stub.split('r="', 1)[1].split('"', 1)[0])
    assert r == pytest.approx(FIGURES[ref][4] / 2, abs=0.005)
    # L73: the node a field paints states no relief colour
    assert "color" not in feats(ref)["stub"]


@EACH
def test_no_mark_is_drawn_on_the_overmould(ref):
    """No logo and no USB trident: the skin is the five or so outlines its
    relief builds from and nothing else, and none of it is text."""
    root = ET.parse(_skin_path(ref)).getroot()
    drawn = [e for e in root.iter() if e is not root]
    assert sorted(e.get("id") for e in drawn) == sorted(feats(ref))
    assert all(e.tag.split("}")[1] in ("rect", "path", "circle") for e in drawn)


# --- 4. the seated depth, in the contracts --------------------------------------

@EACH
def test_the_plug_leaves_its_shell_less_the_drawn_insertion(ref):
    shell, inserted, _modelled, overall, _od, _text = FIGURES[ref]
    f = feats(ref)
    assert shell > inserted
    assert rear(f["shell"]) == pytest.approx(shell - inserted)
    # and the strain relief ends overall - inserted in front of the face
    assert rear(f["relief-boot"]) == pytest.approx(overall - inserted)


@EACH
def test_the_receptacle_models_a_depth_the_drawing_does_not_give(ref):
    """Fails by design when a receptacle's depth is revised: the plug's
    provenance.seated-depth quotes the figure and the size of the mismatch,
    and is to be read again. Nothing the plug BUILDS follows it."""
    shell, inserted, modelled, _overall, _od, _text = FIGURES[ref]
    jack = _contract(JACK_OF[ref])
    assert jack["size"]["d"] == pytest.approx(modelled)
    assert modelled > inserted + 0.25
    text = " ".join(_contract(ref)["provenance"]["seated-depth"].split())
    assert f"{modelled:g}" in text
    assert f"{modelled - inserted:.2f}".rstrip("0") in text or f"{modelled - inserted:.2f}" in text


@EACH
def test_the_ruling_is_recorded_in_provenance(ref):
    text = " ".join(_contract(ref)["provenance"]["seated-depth"].split())
    assert "MEASURED FROM THE FACE THE RECEPTACLE PRESENTS" in text
    assert "THE RECEPTACLE AS MODELLED DISAGREES" in text
    assert "REVISIT" in text
    assert FIGURES[ref][5] in text, text


@EACH
def test_a_keyed_plug_says_which_way_is_up(ref):
    text = " ".join(_contract(ref)["provenance"]["orientation"].split())
    if ref == C:
        assert text.startswith("SYMMETRIC")
    else:
        assert " UP" in text and JACK_OF[ref] in text


# --- 5. seated in real receptacles ------------------------------------------------

# (plug, device, configuration, view, the host's data-path, the part the host
# IS). Each plug seats in a bare receptacle on a chassis and in one on a card
# in a bay; USB-A also seats through each bezel. Four of the hosts are turned.
SEATS = [
    (A, "ufispace/s9500-30xs", "base", "front", "usb", "std/usb-a@1"),
    (A, "ufispace/s9300-32d", "ac", "front", "usb", "common/usb-a-bezel@1"),
    (A, "edgecore/as7726-32x", "ac-f2b", "front", "usb", "common/usb-a@2"),
    (A, "juniper/mx304", "dual-re-ac", "front", "re0/module/usb", "std/usb-a@1"),
    (MICRO, "ufispace/s9500-30xs", "base", "front", "console-usb", "std/micro-usb@1"),
    (MICRO, "commscope/ch3000", "ht3584h-x48", "front", "slot-3-4/module/cc/module/usb",
     "std/micro-usb@1"),
    (C, "readylinks/gl-8xep", "base", "front", "usb1", "std/usb-c@1"),
    (C, "celestica/ds6000", "ac-f2b", "front", "usb-c", "std/usb-c@1"),
]
SEAT_IDS = [f"{s[0].split('/')[1].split('@')[0]}-in-{s[1].split('/')[1]}-{s[4].split('/')[0]}"
            for s in SEATS]
EACH_SEAT = pytest.mark.parametrize("seat", SEATS, ids=SEAT_IDS)
# the seats whose slot is the device's own (a chassis placement, bare or bezel)
CHASSIS_SEATS = [s for s in SEATS if "/" not in s[4]]


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
    tmp = tmp_path_factory.mktemp("usbplugs")
    jobs = {}
    for ref, device, config, view, host, _is in SEATS:
        jobs.setdefault((device, config), {})[host.replace("/module/", "/")] = ref
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
def test_it_seats_with_its_mate_on_the_receptacles_mate(seated, seat):
    parents, host, occ, _ = _seat(seated, seat)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < EPS and abs(hy - oy) < EPS, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)


def test_the_seats_cover_every_turn():
    """The premise of the turned seats, read off the library: the hosts above
    are placed at 0, 90, 180 and 270, so a plug is carried round every way a
    receptacle is drawn."""
    turns = set()
    for _ref, device, _config, view, host, _is in SEATS:
        d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
        if "/" in host:
            continue
        hit = [p for p in d["views"][view]["components"]["placements"] if p.get("id") == host]
        assert len(hit) == 1, (device, host)
        turns.add(int(hit[0].get("rotate") or 0))
    assert {0, 90, 180, 270} <= turns, turns
    re = _contract("juniper/jnp304-re@1")
    assert [p.get("rotate") for p in re["parts"] if p["id"] == "usb"] == [90]


def test_the_turned_seats_are_measured_turned(seated):
    """Not a flat pass: at least four of the seats above are drawn turned in
    the compiled face, so the turn is measured and not assumed."""
    turned = 0
    for seat in SEATS:
        parents, host, _occ, _ = _seat(seated, seat)
        m = device_matrix(parents, host)
        if abs(m[0][0] - 1) > EPS or abs(m[1][1] - 1) > EPS:
            turned += 1
    assert turned >= 4, turned


@EACH_SEAT
def test_the_seated_plug_stands_off_by_the_ruling(seated, seat):
    """The compiled depths, in the device frame: the shell starts on the face
    the receptacle presents, the overmould shell - insertion in front of it,
    the strain relief ends overall - insertion in front of it, and the stub 30
    beyond that."""
    ref = seat[0]
    parents, host, occ, _configs = _seat(seated, seat)
    shell, inserted, _modelled, overall, _od, _text = FIGURES[ref]
    el = _nodes(occ, ref)
    base = lift_of(parents, el["shell"])
    assert base == pytest.approx(lift_of(parents, host), abs=EPS)
    assert _front(parents, el["shell"]) - base == pytest.approx(shell - inserted, abs=EPS)
    assert lift_of(parents, el["body"]) - base == pytest.approx(shell - inserted, abs=EPS)
    assert _front(parents, el["relief-boot"]) - base == pytest.approx(overall - inserted, abs=EPS)
    assert _front(parents, el["stub"]) - base == pytest.approx(overall - inserted + STUB, abs=EPS)


@pytest.mark.parametrize("seat", CHASSIS_SEATS,
                         ids=[SEAT_IDS[SEATS.index(s)] for s in CHASSIS_SEATS])
def test_a_chassis_receptacle_publishes_a_slot_that_offers_exactly_its_plug(seated, seat):
    """A bare receptacle and a bezel alike: the slot is the placement, it
    offers its one plug and nothing else, and it is published at the lift and
    the point the build seated the plug at."""
    ref, device, _config, view, pid, host_is = seat
    d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
    hits = [p for p in d["views"][view]["components"]["placements"] if p.get("id") == pid]
    assert len(hits) == 1 and hits[0]["ref"] == host_is, hits
    parents, host, occ, configs = _seat(seated, seat)
    slot = next(c for c in configs["cages"][view] if c["id"] == pid)
    assert slot["kind"] == "connector" and slot["interface"] == IFACE_OF[ref], slot
    assert slot["accepts"] == [ref], slot
    assert slot["default"] is None and slot["occupant"] == ref, slot
    base = lift_of(parents, _nodes(occ, ref)["shell"])
    assert slot["lift"] == pytest.approx(base, abs=EPS)
    assert tuple(slot["mate"]) == pytest.approx(
        device_point(parents, host, cage_mate(host)), abs=1e-3)


def test_usb_a_offers_the_cable_plug_and_nothing_else(comps):
    """No storage stick and no console dongle: the one part in the library
    that mates `usb-a` is the cable plug."""
    mating = sorted(ref for ref, e in comps.items()
                    if _contract(ref).get("mates") in PAIRS)
    assert mating == PLUGS


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
    names = chain(ref)
    for a, b in zip(names, names[1:]):
        assert lift_of(parents, el[b]) == pytest.approx(_front(parents, el[a]), abs=EPS), (a, b)


# --- 7. the stub's diameter -------------------------------------------------------

def _stub_diameter(parents, stub):
    """relief.js builds a cyl at radius min(w, h) / 2 of the face box."""
    assert stub.tag.endswith("circle"), stub.tag
    cx, cy, r = (float(stub.get(k)) for k in ("cx", "cy", "r"))
    pts = [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    x0, y0, x1, y1 = box(apply(device_matrix(parents, stub), pts))
    assert x1 - x0 == pytest.approx(y1 - y0, abs=EPS)
    return min(x1 - x0, y1 - y0)


@EACH_SEAT
def test_the_stub_is_the_default_cable_od(seated, seat):
    ref = seat[0]
    parents, host, occ, _ = _seat(seated, seat)
    stub = _nodes(occ, ref)["stub"]
    assert _stub_diameter(parents, stub) == pytest.approx(FIGURES[ref][4], abs=EPS)
    # and it is centred on the seat
    cx, cy = device_point(parents, stub, (float(stub.get("cx")), float(stub.get("cy"))))
    assert (cx, cy) == pytest.approx(device_point(parents, host, cage_mate(host)), abs=EPS)


# A placement's attrs set the field (an occupant carries only a ref): each
# plug placed directly, `mate-to` a real receptacle, with a cable-od of its
# own. One device carries two of the three.
OVERRIDES = [
    (A, "ufispace/s9500-30xs", "base", "front", "usb", 3.5),
    (MICRO, "ufispace/s9500-30xs", "base", "front", "console-usb", 3.0),
    (C, "readylinks/gl-8xep", "base", "front", "usb2", 3.8),
]


@pytest.fixture(scope="module")
def overridden(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("usbplugod")
    jobs = {}
    for case in OVERRIDES:
        jobs.setdefault((case[1], case[2], case[3]), []).append(case)
    out = {}
    for (device, config, view), cases in jobs.items():
        def edit(d, view=view, cases=cases):
            places = d["views"][view]["components"]["placements"]
            for ref, _device, _config, _view, host, od in cases:
                hits = [p for p in places if p.get("id") == host]
                assert len(hits) == 1 and hits[0]["ref"] == JACK_OF[ref], hits
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
    assert _stub_diameter(parents, el["stub"]) == pytest.approx(od, abs=EPS)
    # only the stub follows the cable: the strain relief keeps its drawn size
    boot = el["relief-boot"]
    assert boot.tag.endswith("circle")
    assert float(boot.get("r")) * 2 != pytest.approx(od, abs=0.01)
