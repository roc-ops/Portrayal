"""The four fibre plugs (B3, docs/pluggables-caps-design.md, "Parts").

A plug is the other occupant of a connector slot: it mates the interface a
dust cap mates, seats at the same point, and swaps for the cap without either
adapter being touched. Four arrive together - `generic/lc-duplex-plug@1`,
`generic/sc-plug@1`, `generic/mpo12-plug@1`, `generic/mpo24-plug@1` - beside
`generic/lc-plug@1`, which B2 already built.

WHAT THIS FILE IS ABOUT, BEYOND "IT RENDERS". Three things that could each go
wrong silently:

  - THE FIGURES ARE THE SOURCE'S. Every dimension on a new part came from a
    printed callout on a vendor drawing or is declared an estimate. A test
    cannot check a contract against a PDF, so what it checks instead is that
    the registry and the contract hold ONE copy of each figure between them
    (L9 does the comparing) and that the keys which say "this is an estimate"
    are still there to be read.
  - THE HALVES ARE REACHABLE. `generic/lc-duplex-plug@1` composes two whole
    plugs rather than redrawing a pair, and the point of that is a boot on one
    half. So the two halves' mate points are checked against the adapter's two
    bores IN THE DEVICE FRAME, and a boot is actually seated on one.
  - THE MPO CONTRADICTION STAYS VISIBLE. The MPO plug is 12.5 x 7.6 printed
    and std/mpo@1's aperture is 7.8 x 5.6 estimated; the plug does not fit the
    hole. Nothing here fixes that - it is not this task's - but a test holds
    the contradiction to being STATED on both sides, so it cannot go quiet the
    next time somebody edits one of the three files.

Nothing in the library places any of these, so every seating is a configured
occupant on a tmp_path copy of a real device, the idiom
spec/tests/test_dust_caps.py uses for the caps these replace.
"""
import shutil

import pytest
import yaml

from test_nested_occupants import (LIB, by_path, device_point, is_inside)
from test_slot_defaults import _copy, build, face
from test_connector_slots import comps                                # noqa: F401

from portrayal.manifest import load_yaml, presented_interface, seat_point

SPEC = LIB.parent / "spec"

DUPLEX = "generic/lc-duplex-plug@1"
SC = "generic/sc-plug@1"
MPO12 = "generic/mpo12-plug@1"
MPO24 = "generic/mpo24-plug@1"
LC = "generic/lc-plug@1"
BOOT = "common/lc-boot@1"

# the four this task builds, and what each one mates
MATES = {DUPLEX: "lc-duplex", SC: "sc", MPO12: "mpo", MPO24: "mpo"}
POSITIONS = {DUPLEX: 2, SC: 1, MPO12: 12, MPO24: 24}
# the standards entry each part's ENVELOPE is held to, or None where no entry
# describes its outline - which is a claim the contract has to defend in prose
CONFORMS = {DUPLEX: None, SC: "sc-plug", MPO12: "mpo-plug", MPO24: "mpo-plug"}

DCP = "smartoptics/dcp-r-34d-cs"      # places common/lc-duplex-adapter@4
FHD = "fs/fhd-1ufce"
LC_CASSETTE = "fs/fhd-2mtp12-lc-os2-a@3"     # twelve lc-duplex-v-adapter@4
SC_CASSETTE = "fs/fhd-1mtp12-sc-os2-a@2"     # six sc-duplex-adapter@4
H_ADAPTER = "common/lc-duplex-adapter@4"


def contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return load_yaml(LIB / "components" / ns / name / f"v{major}" / "contract.yaml")


def standards():
    return yaml.safe_load((SPEC / "schemas/standards.yaml").read_text())["standards"]


# --- what each part is -------------------------------------------------------------

@pytest.mark.parametrize("ref", sorted(MATES))
def test_a_plug_is_an_unmoving_port_that_mates_one_interface(ref):
    c = contract(ref)
    assert c["class"] == "port"
    # NO `behaviour`, and it is not an oversight: test_behaviour.py asserts
    # `behaviour is None` for every `class: port` contract, and
    # generic/lc-plug@1's own provenance records the same decision.
    assert "behaviour" not in c
    assert c["mates"] == MATES[ref]
    assert c["connection-points"]["mate"]["direction"] == "front"
    assert (c.get("optical") or {}).get("positions") == POSITIONS[ref]
    assert ref.startswith("generic/")


@pytest.mark.parametrize("ref", sorted(MATES))
def test_a_plugs_envelope_is_held_to_a_registry_entry_or_says_why_not(ref):
    """`generic/` means the envelope conforms to spec/schemas/standards.yaml.
    Three of the four do and L9 compares them. The duplex plug does not, and
    the rule is not waived for it: its halves carry the conforming envelopes
    and its own contract has to say so."""
    c, want = contract(ref), CONFORMS[ref]
    assert c.get("conforms") == want
    if want:
        std = standards()[want]
        assert sorted([c["size"]["w"], c["size"]["h"]]) == sorted([std["w"], std["h"]])
        assert std["confidence"] == "drawing"
    else:
        note = c["provenance"]["standard"]
        assert "NO `conforms:`" in note
        # the claim it makes instead: both halves are a conforming part
        halves = {q["ref"] for q in c["parts"]}
        assert halves == {LC}
        assert contract(LC)["conforms"] == "lc-plug"


def test_the_librarys_fibre_plugs_are_these_five_and_there_are_five():
    """A census, and it asserts it measured something.

    KEYED ON THE STRUCTURE, not on a namespace or a name: a part that MATES a
    connector interface and is not a `cap` is a plug, wherever it is filed.
    A sixth needs its own paragraph here, which is the point - the SC boot and
    the MPO boot the connectors design reserves will each trip this."""
    connectors = yaml.safe_load(
        (SPEC / "schemas/connectors.yaml").read_text())["interfaces"]
    found = {}
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = load_yaml(f) or {}
        if c.get("mates") in connectors and c.get("class") != "cap":
            ns = f.parents[2].name
            found[f"{ns}/{c['name']}@{c['version'].split('.')[0]}"] = c
    assert len(found) == 5, sorted(found)
    assert set(found) == set(MATES) | {LC}, sorted(found)


# --- the two new registry entries --------------------------------------------------

def test_the_sc_plug_entry_is_the_plug_and_not_the_hole_it_enters():
    """The SC intake's own COVERAGE.md ruled the plug front view NOT FOUND in
    2026-09-18 and the design planned for that: 'the front profile is the
    drawn opening less a stated clearance, marked estimated'. It was found, so
    that fallback is NOT what this part is - and the two entries now differ by
    the clearance, which is the reason for holding both."""
    std, hole = standards()["sc-plug"], standards()["sc-simplex-receptacle"]
    assert std["confidence"] == "drawing" and hole["confidence"] == "drawing"
    assert (std["w"], std["h"]) == (8.3, 9.0)
    assert (hole["w"], hole["h"]) == (8.39, 9.0)
    # the plug is SMALLER than the opening, by more than L9's 0.05 - which is
    # why `conforms: sc-simplex-receptacle` could not have been used
    assert 0.05 < hole["w"] - std["w"]
    body = next(t for t in std["tiers"] if t["name"] == "body")
    key = next(t for t in std["tiers"] if t["name"] == "key")
    assert (body["w"], body["h"]) == (7.4, 9.0) and (key["w"], key["h"]) == (0.9, 1.8)
    assert body["w"] + key["w"] == std["w"]
    # and nothing in the contract is an estimate dressed as a reading
    c = contract(SC)
    assert set(c["size-confidence"].values()) == {"drawing"}
    assert c["relief"]["features"][0]["confidence"] == "estimated"
    assert "ESTIMATED" in c["provenance"]["standoff"]


def test_the_mpo_plug_entry_names_the_variants_it_did_not_average():
    """`rj45-plug`'s rule: a generic must not average two real shapes. Three
    MPO shells were found and they disagree; the entry states one and records
    the other two rather than splitting the difference."""
    std = standards()["mpo-plug"]
    assert (std["w"], std["h"]) == (12.5, 7.6) and std["confidence"] == "drawing"
    for figure in ("12.8 x 8.0", "8.20"):
        assert figure in std["notes"], figure


def test_the_two_mpo_plugs_are_one_housing_with_two_ferrule_counts():
    """docs/pluggables-design.md decision 10: the fibre count is a property of
    the ferrule, so -12 and -24 are two parts with one outline. Everything
    outside the count must therefore agree, and the 24 has to say that nothing
    held here dimensions a two-row ferrule rather than drawing an invented
    one."""
    a, b = contract(MPO12), contract(MPO24)
    for key in ("size", "elements", "connection-points", "conforms",
                "size-confidence", "mates", "attrs"):
        assert a[key] == b[key], key
    # relief compared on the GEOMETRY, not the prose: each feature's `source`
    # names its own part, which is right and is not a figure
    def shape(c):
        return [(f["node"], f["out"], f["confidence"]) for f in c["relief"]["features"]]
    assert shape(a) == shape(b)
    assert a["optical"]["positions"] != b["optical"]["positions"]
    note = b["provenance"]["row-count"]
    assert "NO SOURCE HELD IN THIS CORPUS DIMENSIONS A TWO-ROW MT FERRULE" in note


def test_the_mpo_contradiction_is_stated_on_both_sides():
    """THE ONE FINDING OF THIS TASK'S INTAKE, and it is left standing rather
    than patched: a 12.5 x 7.6 connector cannot enter std/mpo@1's 7.8 x 5.6.

    The plug is NOT fitted to the aperture - that is the thing a test has to
    hold, because fitting it would make the library self-consistent and wrong.
    So: the plug keeps its printed size, the aperture keeps its estimated one,
    and all three files that know about the disagreement say so."""
    plug, aperture = contract(MPO12), contract("std/mpo@1")
    assert (aperture["size"]["w"], aperture["size"]["h"]) == (7.8, 5.6)
    assert plug["size"]["w"] > aperture["size"]["w"]
    assert plug["size"]["h"] > aperture["size"]["h"]
    assert "ESTIMATED" in aperture["provenance"]["size"]
    note = plug["provenance"]["aperture-contradiction"]
    assert "NOTHING, DELIBERATELY" in note
    # the cap that predicted it from the other direction still carries the
    # hypothesis, so the two can be read together
    assert "HYPOTHESIS" in contract("common/mpo-dust-cap@1")["provenance"]["aperture-doubt"]
    assert "7.8 x 5.6" in standards()["mpo-plug"]["notes"]


# --- the slots that offer them -----------------------------------------------------

def _accepts(comps, interface):
    """Every connector slot's accept list for one interface, across the whole
    published component index."""
    out = [c["accepts"] for comp in comps.values() for c in comp.get("cages") or []
           if c.get("kind") == "connector" and c.get("interface") == interface]
    assert out, f"no slot presents {interface!r}, so nothing accepts anything"
    return out


@pytest.mark.parametrize("ref", sorted(MATES))
def test_a_plug_is_offered_by_every_slot_of_its_interface(comps, ref):
    for accepts in _accepts(comps, MATES[ref]):
        assert ref in accepts, (ref, accepts)


def test_a_duplex_slot_offers_the_duplex_parts_and_not_the_simplex_ones(comps):
    """The spanning slot and its bores offer different parts, which is the
    whole of why `lc-duplex` is its own interface."""
    for accepts in _accepts(comps, "lc-duplex"):
        assert DUPLEX in accepts
        assert LC not in accepts and SC not in accepts
    for accepts in _accepts(comps, "lc"):
        assert LC in accepts and DUPLEX not in accepts


# --- seating -----------------------------------------------------------------------

def dcp(tmp_path, occupants):
    dev = shutil.copytree(LIB / "devices" / DCP, tmp_path / "dcp") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    assert not d.get("configurations"), "the device now ships its own; rewrite this"
    d["configurations"] = {"default": {"kind": "base", "default": True,
                                       "occupants": occupants}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def fhd(tmp_path, cassette, occupants):
    dev = shutil.copytree(LIB / "devices" / FHD, tmp_path / "fhd") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"]["base"]
    cfg["bays"] = {**(cfg.get("bays") or {}), "bay-1": cassette}
    cfg["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


@pytest.fixture
def lib(tmp_path):
    """A throwaway library holding a cassette whose FRONT carries MTP adapters.
    Every MPO aperture in the library is on a cassette's rear face, and this
    file's business is the plug, not the addressing of a rear - the same
    fixture spec/tests/test_dust_caps.py builds for the MPO cap."""
    root = tmp_path / "lib"

    def mpo_front(c):
        c["parts"] = [{"id": "mtp1", "ref": "common/mpo-adapter@1", "at": [20.0, 12.0]},
                      {"id": "mtp2", "ref": "common/mpo-adapter@1", "at": [60.0, 12.0]}]
        for k in ("optical", "faces"):
            c.pop(k, None)
    _copy(root, "fs/fhd-1mtp12-sc-os2-a", 2, "mpo-cassette", mpo_front)
    return root


def occupant(root, path, ref):
    occ = by_path(root, f"{path}-occupant")
    assert occ.get("data-ref").rsplit(":", 1)[0] == ref
    assert occ.get("data-for") == path
    return occ


def test_the_duplex_plugs_halves_land_on_the_adapters_two_bores(tmp_path):
    """THE ASSERTION THE COMPOSITION EXISTS FOR, and it is made in the DEVICE
    frame rather than on the contract's own arithmetic.

    `common/lc-duplex-adapter@4` composes two std/lc-bore@3 at `rotate: 180`,
    6.25 apart. The plug composes two generic/lc-plug@1 6.25 apart, unrotated.
    Neither contract knows about the other; what has to be true is that once
    the plug's own `mate` is seated on the adapter's, each half's `mate` lands
    on a bore's - because that is what makes a boot chained on a half land
    behind the fibre it belongs to, not 6.25 away from it."""
    dev = dcp(tmp_path, {"port-1510": DUPLEX})
    root, parents = face(build(dev, tmp_path / "o", LIB), "dcp-r-34d-cs", "default")
    occ = occupant(root, "port-1510", DUPLEX)
    adapter = by_path(root, "port-1510")
    assert is_inside(parents, occ, parents[adapter]) or occ is not None

    plug, bore = contract(DUPLEX), contract("std/lc-bore@3")
    half = contract(LC)
    bores = {q["id"]: q for q in contract(H_ADAPTER)["parts"]}
    pairs = [("a", "tx"), ("b", "rx")]
    for half_id, bore_id in pairs:
        q = next(p for p in plug["parts"] if p["id"] == half_id)
        # the half's mate in the PLUG's frame, through its own placement
        hp = seat_point(q["at"], half["size"], q.get("rotate"),
                        half["connection-points"]["mate"]["at"])
        hx, hy = device_point(parents, occ, hp)
        # the bore's mate in the ADAPTER's frame, through the bore's rotation
        b = bores[bore_id]
        bp = seat_point(b["at"], bore["size"], b.get("rotate"),
                        bore["connection-points"]["mate"]["at"])
        bx, by = device_point(parents, by_path(root, "port-1510"), bp)
        assert abs(hx - bx) < 1e-6 and abs(hy - by) < 1e-6, (half_id, bore_id)


def test_the_duplex_plug_seats_three_levels_down_on_an_fhd_cassette(tmp_path):
    """Deep addressing: `bay-1/lc01` is the duplex slot of the adapter `lc01`
    in the cassette in `bay-1`, and the plug is drawn inside the innermost
    group that holds it.

    IT LANDS ITS OWN MATE ON THE ADAPTER'S AND NOT ITS HALVES ON THE BORES,
    and that is not an oversight: `common/lc-duplex-v-adapter@4` stacks its
    pair where this plug's is side by side, and an occupant cannot be turned
    relative to its host. `provenance.orientation` records the gap - it is the
    one common/lc-duplex-dust-cap@1 already has in the other direction - so
    what is checked here is the seat, which IS right."""
    dev = fhd(tmp_path, LC_CASSETTE, {"bay-1/lc01": DUPLEX})
    root, parents = face(build(dev, tmp_path / "o", LIB), "fhd-1ufce", "base")
    occ = occupant(root, "bay-1/module/lc01", DUPLEX)
    host = by_path(root, "bay-1/module/lc01")
    assert is_inside(parents, occ, parents[host])
    adapter = contract("common/lc-duplex-v-adapter@4")
    _, at, lift = presented_interface(adapter, contract)
    hx, hy = device_point(parents, host, at)
    ox, oy = device_point(parents, occ,
                          contract(DUPLEX)["connection-points"]["mate"]["at"])
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6
    # seated ON the bezel the adapter presents, not at the plate behind it
    assert lift > 0
    assert float(occ.get("data-z-lift")) == pytest.approx(lift, abs=1e-6)


def test_a_boot_seats_on_one_half_of_the_duplex_plug(tmp_path):
    """HOW A BOOT ADDRESSES ONE HALF, which the brief left to be decided.

    Not `<plug key>-occupant`: the plug as a whole presents no interface - it
    composes two parts that do, and manifest.presented_interface declines to
    pick between them - so a boot keyed there has nothing to mate to and the
    build says so. The half is a composed part with an id, and the build seats
    occupants keyed under the instance that holds them at any depth, so the
    key is the half's part id under the plug's own seat:
    `port-1510-occupant/a`. Both halves take one, independently."""
    dev = dcp(tmp_path, {"port-1510": DUPLEX,
                         "port-1510-occupant/a": BOOT,
                         "port-1510-occupant/b": BOOT})
    root, parents = face(build(dev, tmp_path / "o", LIB), "dcp-r-34d-cs", "default")
    plug = occupant(root, "port-1510", DUPLEX)
    half_c, boot_c = contract(LC), contract(BOOT)
    _, bpt, blift = presented_interface(half_c, contract)
    assert blift > 0, "the plug presents no standoff, so this checks nothing"
    for half_id in ("a", "b"):
        boot = occupant(root, f"port-1510-occupant/{half_id}", BOOT)
        assert is_inside(parents, boot, plug)
        q = next(p for p in contract(DUPLEX)["parts"] if p["id"] == half_id)
        hx, hy = device_point(parents, by_path(root, f"port-1510-occupant/{half_id}"),
                              bpt)
        ox, oy = device_point(parents, boot,
                              boot_c["connection-points"]["mate"]["at"])
        assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, half_id
        # and it stands off by the plug body's own `out`, not at the plug face
        assert float(boot.get("data-z-lift")) == pytest.approx(blift, abs=1e-6)


def test_the_sc_plug_seats_in_an_fhd_sc_cassette_bore(tmp_path):
    """`bay-1/sc1/tx` is the TX bore of the adapter `sc1` in the cassette -
    the seat common/sc-dust-cap@1 already takes, with the plug in its place."""
    dev = fhd(tmp_path, SC_CASSETTE, {"bay-1/sc1/tx": SC})
    root, parents = face(build(dev, tmp_path / "o", LIB), "fhd-1ufce", "base")
    occ = occupant(root, "bay-1/module/sc1/tx", SC)
    host = by_path(root, "bay-1/module/sc1/tx")
    hx, hy = device_point(parents, host,
                          contract("std/sc-bore@1")["connection-points"]["mate"]["at"])
    ox, oy = device_point(parents, occ,
                          contract(SC)["connection-points"]["mate"]["at"])
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6
    # `out` IS ABSOLUTE AND THE SEAT'S LIFT IS ADDED TO IT by the build - the
    # rule common/sc-dust-cap@1's own provenance records from the other end.
    # The SC cassette's adapter lifts its bores onto a 1.0 frame, so the plug's
    # own 13.0 is written here as 14.0, and checking the raw 13.0 would be
    # checking that the lift had been forgotten.
    seat = float(occ.get("data-z-lift") or 0.0)
    own = next(f for f in contract(SC)["relief"]["features"] if f["node"] == "body")["out"]
    assert seat > 0
    body = next(n for n in occ.iter() if (n.get("id") or "").endswith("--body"))
    assert float(body.get("data-z-out")) == pytest.approx(own + seat, abs=1e-6)


def test_the_mpo_plug_seats_at_the_panel_because_its_aperture_presents_no_lift(
        tmp_path, lib):
    """std/mpo@1 puts its `mate` on nothing, so it presents 0.0 and an
    occupant is seated at the panel plane - the same reason
    common/mpo-dust-cap@1's figures are absolute from the panel."""
    dev = fhd(tmp_path, "test/mpo-cassette@1", {"bay-1/mtp1/bore": MPO12})
    root, parents = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    occ = occupant(root, "bay-1/module/mtp1/bore", MPO12)
    _, _, presented = presented_interface(contract("std/mpo@1"), contract)
    assert presented == 0.0
    assert float(occ.get("data-z-lift") or 0.0) == pytest.approx(0.0, abs=1e-6)
    body = next(n for n in occ.iter() if (n.get("id") or "").endswith("--body"))
    assert float(body.get("data-z-out")) == pytest.approx(15.2, abs=1e-6)
    # and it stands in front of the adapter bezel rather than inside it
    bezel = next(f for f in contract("common/mpo-adapter@1")["relief"]["features"]
                 if f["node"] == "bezel")["out"]
    assert float(body.get("data-z-out")) > bezel
