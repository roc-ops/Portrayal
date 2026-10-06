"""The four fibre plugs (B3, docs/pluggables-caps-design.md, "Parts").

A plug is the other occupant of a connector slot: it mates the interface a
dust cap mates, seats at the same point, and swaps for the cap without either
adapter being touched. Four arrive together - `generic/lc-duplex-plug@1`,
`generic/sc-plug@1`, `generic/mpo12-plug@1`, `generic/mpo24-plug@1` - beside
`generic/lc-plug@1`, which B2 already built. (Both are @2 since B3's Task 7c,
drawn seated and latch-first into the bore - spec/tests/test_lc_seated_orientation.py.)

WHAT THIS FILE IS ABOUT, BEYOND "IT RENDERS". Three things that could each go
wrong silently:

  - THE FIGURES ARE THE SOURCE'S. Every dimension on a new part came from a
    printed callout on a vendor drawing or is declared an estimate. A test
    cannot check a contract against a PDF, so what it checks instead is that
    the registry and the contract hold ONE copy of each figure between them
    (L9 does the comparing) and that the keys which say "this is an estimate"
    are still there to be read.
  - THE HALVES ARE REACHABLE. `generic/lc-duplex-plug` composes two whole
    plugs rather than redrawing a pair, and the point of that is a boot on one
    half. So the two halves' mate points are checked against the adapter's two
    bores IN THE DEVICE FRAME, and a boot is actually seated on one.
  - THE MPO PLUG FITS ITS HOLE. The MPO plug is 12.5 x 7.6 printed, and
    std/mpo@1's 7.8 x 5.6 estimated opening could not take it; std/mpo@2
    corrected the opening (12.9 x 8.0, still estimated). The plug is checked
    inside the opening twice - on the contracts and on a build, in the device
    frame - so a later edit to either side cannot reopen the gap in silence.

Nothing in the library places any of these, so every seating is a configured
occupant on a tmp_path copy of a real device, the idiom
spec/tests/test_dust_caps.py uses for the caps these replace.
"""
import shutil

import pytest
import yaml

from test_nested_occupants import (LIB, by_path, device_point, is_inside)
from test_slot_defaults import _copy, build, face, run
from test_connector_slots import comps                                # noqa: F401

from portrayal import lint
from portrayal.manifest import (load_yaml, nested_key_host,
                                presented_interface, seat_point)

SPEC = LIB.parent / "spec"

DUPLEX = "generic/lc-duplex-plug@2"
SC = "generic/sc-plug@1"
MPO12 = "generic/mpo12-plug@1"
MPO24 = "generic/mpo24-plug@1"
# the opening both MPO plugs enter, and the panel adapter that composes it
APERTURE = "std/mpo@2"
ADAPTER = "common/mpo-adapter@2"
LC = "generic/lc-plug@2"
BOOT = "common/lc-boot@1"

# the four this task builds, and what each one mates
MATES = {DUPLEX: "lc-duplex", SC: "sc", MPO12: "mpo", MPO24: "mpo"}
POSITIONS = {DUPLEX: 2, SC: 1, MPO12: 12, MPO24: 24}
# the standards entry each part's ENVELOPE is held to, or None where no entry
# describes its outline - which is a claim the contract has to defend in prose
CONFORMS = {DUPLEX: None, SC: "sc-plug", MPO12: "mpo-plug", MPO24: "mpo-plug"}

DCP = "smartoptics/dcp-r-34d-cs"      # places common/lc-duplex-adapter@6
FHD = "fs/fhd-1ufce"
LC_CASSETTE = "fs/fhd-2mtp12-lc-os2-a@4"     # twelve lc-duplex-v-adapter@6
SC_CASSETTE = "fs/fhd-1mtp12-sc-os2-a@3"     # six sc-duplex-adapter@5
H_ADAPTER = "common/lc-duplex-adapter@6"


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
    # generic/lc-plug@2's own provenance records the same decision.
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
        # the claim it makes instead: both halves are the simplex plug, whose
        # width is the registry's `lc-plug` width. Since @2 the halves are
        # drawn SEATED and carry no `conforms` of their own - the registry
        # entry is the free silhouette - so the width is what is held here.
        halves = {q["ref"] for q in c["parts"]}
        assert halves == {LC}
        assert contract(LC)["size"]["w"] == standards()["lc-plug"]["w"]
        assert "NO `conforms:`" in contract(LC)["provenance"]["standard"]


def _ac_inlet_interfaces():
    """Every interface a `class: inlet` part presents, read off the library."""
    got = set()
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = load_yaml(f) or {}
        if c.get("class") == "inlet" and c.get("interface"):
            got.add(c["interface"])
    return got


def test_the_ac_inlet_interfaces_were_read():
    """The census's exclusion is keyed on these; an empty set would exclude
    nothing and say nothing."""
    assert {"iec-c14", "iec-c20", "saf-d-grid"} <= _ac_inlet_interfaces()


def _usb_receptacle_interfaces():
    """Every interface a part presents while stating a USB connector as its
    medium, read off the library."""
    got = set()
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = load_yaml(f) or {}
        if c.get("interface") and "usb" in str((c.get("attrs") or {}).get("media") or ""):
            got.add(c["interface"])
    return got


def test_the_usb_receptacle_interfaces_were_read():
    """The census's exclusion is keyed on these; an empty set would exclude
    nothing and say nothing."""
    assert _usb_receptacle_interfaces() == {"usb-a", "micro-usb-b", "usb-c"}


def _dsub_connector_interfaces():
    """Every interface a part presents while conforming to a D-subminiature
    shell in spec/schemas/standards.yaml, read off the library."""
    got = set()
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = load_yaml(f) or {}
        if c.get("interface") and c.get("conforms") in ("db9", "hd15", "da15", "db25"):
            got.add(c["interface"])
    return got


def test_the_dsub_connector_interfaces_were_read():
    """The census's exclusion is keyed on these; an empty set would exclude
    nothing and say nothing."""
    assert _dsub_connector_interfaces() == {"db9", "hd15", "da15", "db25"}


def _terminal_header_interfaces():
    """Every interface a part presents while stating a wire-terminal medium,
    or as a DC power inlet, read off the library: the pluggable terminal
    headers and the DC barrel jack."""
    got = set()
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = load_yaml(f) or {}
        media = str((c.get("attrs") or {}).get("media") or "")
        if c.get("interface") and media in ("dc-terminal", "terminal-block"):
            got.add(c["interface"])
        # and the DC barrel jack, a power inlet that states `input: dc`
        if c.get("interface") and c.get("class") == "inlet" \
                and (c.get("attrs") or {}).get("input") == "dc":
            got.add(c["interface"])
    return got


def _terminal_screw_interfaces():
    """Every interface a `class: screw` part presents, read off the library:
    the terminal screws of the barrier blocks, which a wire's lug lands on."""
    got = set()
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = load_yaml(f) or {}
        if c.get("interface") and c.get("class") == "screw":
            got.add(c["interface"])
    return got


def test_the_terminal_screw_interfaces_were_read():
    """The census's exclusion is keyed on these; an empty set would exclude
    nothing and say nothing."""
    assert _terminal_screw_interfaces() == {"terminal-stud"}


def test_the_terminal_header_interfaces_were_read():
    """The census's exclusion is keyed on these; an empty set would exclude
    nothing and say nothing."""
    assert _terminal_header_interfaces() == {"terminal-508-2", "terminal-508-5",
                                             "terminal-508-6", "dc-barrel"}


def test_the_librarys_fibre_plugs_are_these_six_and_there_are_six():
    """A census, and it asserts it measured something.

    KEYED ON THE STRUCTURE, not on a namespace or a name: a part that MATES a
    connector interface and is not a `cap` is a plug, wherever it is filed.
    A sixth needs its own paragraph here, which is the point - the SC boot and
    the MPO boot the connectors design reserves will each trip this."""
    connectors = yaml.safe_load(
        (SPEC / "schemas/connectors.yaml").read_text())["interfaces"]
    # RJ45 IS A CONNECTOR SINCE #610 AND IT IS NOT FIBRE. generic/rj45-plug@1
    # mates `rj45`, which the registry now holds so a copper jack is a slot, and
    # without this line it would be the sixth plug here. It is left out by what
    # it IS - its own `attrs.media` is `rj45` - not by name, and its census is
    # spec/tests/test_rj45_slots.py.
    found = {}
    ac_inlets = _ac_inlet_interfaces()
    assert ac_inlets
    usb_receptacles = _usb_receptacle_interfaces()
    assert usb_receptacles
    dsub_connectors = _dsub_connector_interfaces()
    assert dsub_connectors
    terminal_headers = _terminal_header_interfaces()
    assert terminal_headers
    terminal_screws = _terminal_screw_interfaces()
    assert terminal_screws
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = load_yaml(f) or {}
        if (c.get("attrs") or {}).get("media") == "rj45":
            continue
        # NOR ARE THE COAX PLUGS (#650). generic/sma-plug@1, smb-plug@1 and
        # mcx-plug@1 mate `sma`, `smb` and `mcx`, which the registry holds so a
        # coax jack is a slot. Left out the same way: by what each IS - its
        # `attrs.media` is `coax-<family>` - and their census is
        # spec/tests/test_coax_plugs.py.
        if str((c.get("attrs") or {}).get("media") or "").startswith("coax-"):
            continue
        # NOR ARE THE AC CORD ENDS (#785). generic/c13-plug@1, c19-plug@1 and
        # saf-d-grid-plug@1 mate `iec-c14`, `iec-c20` and `saf-d-grid`, which
        # the registry holds so an AC inlet is a slot. Left out by what each
        # IS - it mates an interface a `class: inlet` part presents, and no
        # fibre runs through an appliance inlet - and their census is
        # spec/tests/test_ac_cord_ends.py.
        if c.get("mates") in ac_inlets:
            continue
        # NOR ARE THE USB CABLE PLUGS (#786). generic/usb-a-plug@1,
        # micro-usb-b-plug@1 and usb-c-plug@1 mate `usb-a`, `micro-usb-b` and
        # `usb-c`, which the registry holds so a USB receptacle is a slot.
        # Left out by what each IS - it mates an interface presented by a
        # part whose medium is a USB connector, and no fibre runs through
        # one - and their census is spec/tests/test_usb_plugs.py.
        if c.get("mates") in usb_receptacles:
            continue
        # NOR ARE THE D-SUB AND VGA CABLE PLUGS (#787). generic/db9-plug@1,
        # hd15-plug@1, da15-plug@1 and db25-plug@1 mate `db9`, `hd15`, `da15`
        # and `db25`, which the registry holds so a D-sub connector is a slot.
        # Left out by what each IS - it mates an interface presented by a
        # part that conforms to a D-subminiature shell, and no fibre runs
        # through one - and their census is spec/tests/test_dsub_plugs.py.
        if c.get("mates") in dsub_connectors:
            continue
        # NOR IS A COVER (#807). amphenol-ns/touch-guard-1ru@1 mates
        # `breaker-1ru-guard`, the face of a plug-in breaker, which the registry
        # holds so a guard that ships on a breaker can come off. Left out by what
        # the INTERFACE is - the registry marks it `cover: true` - not by name.
        if (connectors.get(c.get("mates")) or {}).get("cover"):
            continue
        # NOR ARE THE TERMINAL PLUGS (#789). generic/terminal-508-2-plug@1,
        # terminal-508-5-plug@1 and terminal-508-6-plug@1 mate the three
        # pluggable terminal header interfaces, which the registry holds so a
        # header is a slot. Left out by what each IS - it mates an interface
        # presented by a part whose medium is a wire terminal, and it carries
        # copper wires - and their census is
        # spec/tests/test_dc_terminal_plugs.py. generic/dc-barrel-plug@1 mates
        # `dc-barrel`, a power inlet's interface, and is left out with them;
        # its census is spec/tests/test_dc_barrel_plug.py.
        if c.get("mates") in terminal_headers:
            continue
        # NOR IS THE RING LUG (#789). generic/ring-lug@1 mates `terminal-stud`,
        # the interface a barrier block's terminal screw presents. Left out by
        # what it IS - it mates an interface presented by a screw, and it
        # carries one copper wire - and its census is
        # spec/tests/test_terminal_lugs.py.
        if c.get("mates") in terminal_screws:
            continue
        if c.get("mates") in connectors and c.get("class") != "cap":
            ns = f.parents[2].name
            found[f"{ns}/{c['name']}@{c['version'].split('.')[0]}"] = c
    # THE SIXTH, WITH ITS PARAGRAPH. generic/mpo16-plug@1 mates `mpo16`: the
    # MPO-12 housing with its key offset, so it is its own interface and its
    # own part (umbrella decision 10). Its tests are
    # spec/tests/test_mpo_bidi_pon_optics.py.
    assert len(found) == 6, sorted(found)
    assert set(found) == set(MATES) | {LC, "generic/mpo16-plug@1"}, sorted(found)


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
    for key in ("size", "connection-points", "conforms",
                "size-confidence", "mates", "attrs"):
        assert a[key] == b[key], key
    # THE ELEMENTS AGREE BUT FOR THE FIBRE POSITIONS, which ARE the count: one
    # node per position (L112), 12 on one and 24 on the other
    def outline(c):
        return {k: v for k, v in c["elements"].items() if v.get("class") != "fibre"}
    assert outline(a) == outline(b)
    for c in (a, b):
        fibres = [k for k, v in c["elements"].items() if v.get("class") == "fibre"]
        assert sorted(fibres, key=int) == [str(i) for i in range(1, c["optical"]["positions"] + 1)]
    # relief compared on the GEOMETRY, not the prose: each feature's `source`
    # names its own part, which is right and is not a figure
    def shape(c):
        return [(f["node"], f["out"], f["confidence"]) for f in c["relief"]["features"]]
    assert shape(a) == shape(b)
    assert a["optical"]["positions"] != b["optical"]["positions"]
    note = b["provenance"]["row-count"]
    assert "NO SOURCE HELD IN THIS CORPUS DIMENSIONS A TWO-ROW MT FERRULE" in note


@pytest.mark.parametrize("ref", [MPO12, MPO24])
def test_the_mpo_plug_envelope_fits_inside_the_opening(ref):
    """REPLACES THE TASK 6 TEST THAT PINNED THE CONTRADICTION. A 12.5 x 7.6
    connector (US Conec C20044 / C20851, printed) could not enter the 7.8 x 5.6
    opening std/mpo@1 drew; std/mpo@2 corrects the opening, and what a test
    can hold is the physical claim itself - on both axes the plug is smaller
    than the hole it seats in, and the opening is the registry's figure, so L9
    and this agree about which number is meant.

    The plug keeps its printed size: it is the aperture that moved, because it
    was the weaker reading (an estimate off a render) against two callouts."""
    plug, aperture = contract(ref), contract(APERTURE)
    std = standards()[aperture["conforms"]]
    assert (aperture["size"]["w"], aperture["size"]["h"]) == (std["w"], std["h"])
    assert (plug["size"]["w"], plug["size"]["h"]) == (12.5, 7.6)
    assert plug["size"]["w"] < aperture["size"]["w"], (plug["size"], aperture["size"])
    assert plug["size"]["h"] < aperture["size"]["h"], (plug["size"], aperture["size"])
    # the opening is still an ESTIMATE, and says so where L9 reads it
    assert std["confidence"] == "estimated"


def _corners(parents, el, w, h):
    xs, ys = zip(*(device_point(parents, el, p) for p in ((0, 0), (w, 0), (0, h), (w, h))))
    return min(xs), min(ys), max(xs), max(ys)


def _within(inner, outer, tol=1e-6):
    return (inner[0] >= outer[0] - tol and inner[1] >= outer[1] - tol
            and inner[2] <= outer[2] + tol and inner[3] <= outer[3] + tol)


@pytest.mark.parametrize("ref", [MPO12, MPO24])
def test_a_seated_mpo_plug_lies_inside_its_opening_and_the_opening_inside_its_adapter(
        tmp_path, lib, ref):
    """The same claim ON A BUILD, in the device frame: seat the plug on the
    throwaway MTP cassette, map the plug's own outline, the aperture's and the
    adapter's through every transform above them, and check they nest. This is
    what a seated plug looks like to anyone reading the drawing, and a mate
    point that landed off-centre would fail it even with the sizes right."""
    dev = fhd(tmp_path, "test/mpo-cassette@1", {"bay-1/mtp1": ref})
    root, parents = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    occ = occupant(root, "bay-1/module/mtp1", ref)
    bore = by_path(root, "bay-1/module/mtp1/bore")
    adapter = by_path(root, "bay-1/module/mtp1")
    size = lambda r: (contract(r)["size"]["w"], contract(r)["size"]["h"])
    plug_box = _corners(parents, occ, *size(ref))
    hole_box = _corners(parents, bore, *size(APERTURE))
    wrap_box = _corners(parents, adapter, *size(ADAPTER))
    measured = [plug_box, hole_box, wrap_box]
    assert all(b[2] - b[0] > 0 and b[3] - b[1] > 0 for b in measured), measured
    assert _within(plug_box, hole_box), (plug_box, hole_box)
    assert _within(hole_box, wrap_box), (hole_box, wrap_box)


# --- the slots that offer them -----------------------------------------------------

def _accepts(comps, interface):
    """Every connector slot's accept list for one interface, across the whole
    published component index."""
    out = [c["accepts"] for comp in comps.values() for c in comp.get("cages") or []
           if c.get("kind") == "connector" and c.get("interface") == interface]
    assert out, f"no slot presents {interface!r}, so nothing accepts anything"
    return out


# ALL FOUR ARE CHECKED ACROSS THE LIBRARY. The MPO plugs were not, while no
# library part published an mpo slot (the FHD cassette rears' flanged
# bulkheads presented nothing); since common/mpo-flange-adapter@2 and
# common/mpo24-flange-adapter@2 present `mpo`, every FHD cassette back
# publishes one per bulkhead, and `_accepts` has real slots to ask.
@pytest.mark.parametrize("ref", sorted(MATES))
def test_a_plug_is_offered_by_every_slot_of_its_interface(comps, ref):
    for accepts in _accepts(comps, MATES[ref]):
        assert ref in accepts, (ref, accepts)


def test_an_mpo_slot_offers_both_mpo_plugs(comps):
    """The real wrapper, common/mpo-adapter@2, composed into a throwaway
    composer: its forwarded std/mpo@2 aperture is the slot, and the slot's
    accept list - built from `mates`, as every connector slot's is - offers
    both plugs. Any mpo slot the library does publish is held to the same."""
    from portrayal import render as render_mod
    lib = render_mod.Library([str(LIB)])
    composer = {"size": {"w": 80.0, "h": 30.0},
                "parts": [{"id": "mtp1", "ref": "common/mpo-adapter@2",
                           "at": [20.0, 12.0]}]}
    [slot] = render_mod.component_cages(composer, lib,
                                        render_mod._pluggable_families(),
                                        render_mod._pluggable_candidates([str(LIB)]),
                                        render_mod._connector_registry())
    assert slot["interface"] == "mpo"
    held = [slot["accepts"]] + [c["accepts"] for comp in comps.values()
                                for c in comp.get("cages") or []
                                if c.get("kind") == "connector"
                                and c.get("interface") == "mpo"]
    for accepts in held:
        assert MPO12 in accepts and MPO24 in accepts, accepts


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
        c["parts"] = [{"id": "mtp1", "ref": "common/mpo-adapter@2", "at": [20.0, 12.0]},
                      {"id": "mtp2", "ref": "common/mpo-adapter@2", "at": [60.0, 12.0]}]
        for k in ("optical", "faces"):
            c.pop(k, None)
    _copy(root, "fs/fhd-1mtp12-sc-os2-a", 3, "mpo-cassette", mpo_front)
    return root


def occupant(root, path, ref):
    occ = by_path(root, f"{path}-occupant")
    assert occ.get("data-ref").rsplit(":", 1)[0] == ref
    assert occ.get("data-for") == path
    return occ


def test_the_duplex_plugs_halves_land_on_the_adapters_two_bores(tmp_path):
    """THE ASSERTION THE COMPOSITION EXISTS FOR, and it is made in the DEVICE
    frame rather than on the contract's own arithmetic.

    `common/lc-duplex-adapter@6` composes two std/lc-bulkhead-bore@1 at `rotate: 180`,
    6.25 apart. The plug composes two generic/lc-plug@2 6.25 apart, each turned
    180 so its latch stands up (the canonical axis).
    Neither contract knows about the other; what has to be true is that once
    the plug's own `mate` is seated on the adapter's, each half's `mate` lands
    on a bore's - because that is what makes a boot chained on a half land
    behind the fibre it belongs to, not 6.25 away from it."""
    # the Smartoptics adapter ships a cap in each bore, emptied first
    dev = dcp(tmp_path, {"port-1510": DUPLEX, "port-1510/1": "", "port-1510/2": ""})
    root, parents = face(build(dev, tmp_path / "o", LIB), "dcp-r-34d-cs", "default")
    occ = occupant(root, "port-1510", DUPLEX)
    adapter = by_path(root, "port-1510")
    # A DEVICE-LEVEL OCCUPANT IS A TOP-LEVEL SIBLING OF ITS HOST, not a
    # descendant - docs/pluggables-connectors-design.md says so outright, and
    # it is why the seat's whole stack of lift has to be written onto the
    # occupant's own group rather than inherited. Asserted rather than assumed
    # because the numbers below are computed through each one's own ancestors,
    # and they would be wrong in a different way if the two were nested.
    assert not is_inside(parents, occ, adapter)
    assert parents[occ] is parents[adapter]

    plug, bore = contract(DUPLEX), contract("std/lc-bulkhead-bore@1")
    half = contract(LC)
    bores = {q["id"]: q for q in contract(H_ADAPTER)["parts"]}
    pairs = [("a", "1"), ("b", "2")]
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

    AND ITS HALVES LAND ON THE STACKED BORES, which they did not when this
    plug was first drawn. `common/lc-duplex-v-adapter@6` stacks its pair where
    this plug's is side by side, and an occupant cannot turn itself - so the
    ADAPTER says which way round its pair runs: its spanning slot publishes
    the turn that carries the canonical across axis onto its own bores, and
    the seat draws the plug at it. Half `a` therefore lands on the adapter's
    first bore here exactly as it does on the side-by-side Smartoptics adapter
    above, from the same drawing."""
    dev = fhd(tmp_path, LC_CASSETTE, {"bay-1/lc01": DUPLEX})
    root, parents = face(build(dev, tmp_path / "o", LIB), "fhd-1ufce", "base")
    occ = occupant(root, "bay-1/module/lc01", DUPLEX)
    host = by_path(root, "bay-1/module/lc01")
    assert is_inside(parents, occ, parents[host])
    adapter = contract("common/lc-duplex-v-adapter@6")
    _, at, lift = presented_interface(adapter, contract)
    hx, hy = device_point(parents, host, at)
    ox, oy = device_point(parents, occ,
                          contract(DUPLEX)["connection-points"]["mate"]["at"])
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6
    # seated ON the bezel the adapter presents, not at the plate behind it
    assert lift > 0
    assert float(occ.get("data-z-lift")) == pytest.approx(lift, abs=1e-6)
    # and each half on the bore it fills, through the turn the seat applied
    plug, bore, half = contract(DUPLEX), contract("std/lc-bulkhead-bore@1"), contract(LC)
    bores = {q["id"]: q for q in adapter["parts"]}
    for half_id, bore_id in (("a", "1"), ("b", "2")):
        q = next(p for p in plug["parts"] if p["id"] == half_id)
        hp = seat_point(q["at"], half["size"], q.get("rotate"),
                        half["connection-points"]["mate"]["at"])
        px, py = device_point(parents, occ, hp)
        b = bores[bore_id]
        bp = seat_point(b["at"], bore["size"], b.get("rotate"),
                        bore["connection-points"]["mate"]["at"])
        bx, by = device_point(parents, host, bp)
        assert abs(px - bx) < 1e-6 and abs(py - by) < 1e-6, (half_id, bore_id)


def test_a_boot_seats_on_one_half_of_the_duplex_plug(tmp_path):
    """HOW A BOOT ADDRESSES ONE HALF, which the brief left to be decided.

    Not `<plug key>-occupant`: the plug as a whole presents no interface - it
    composes two parts that do, and manifest.presented_interface declines to
    pick between them - so a boot keyed there has nothing to mate to and the
    build says so. The half is a composed part with an id, and the build seats
    occupants keyed under the instance that holds them at any depth, so the
    key is the half's part id under the plug's own seat:
    `port-1510-occupant/a`. Both halves take one, independently."""
    dev = dcp(tmp_path, {"port-1510": DUPLEX, "port-1510/1": "", "port-1510/2": "",
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
        hx, hy = device_point(parents, by_path(root, f"port-1510-occupant/{half_id}"),
                              bpt)
        ox, oy = device_point(parents, boot,
                              boot_c["connection-points"]["mate"]["at"])
        assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, half_id
        # and it stands off by the plug body's own `out`, not at the plug face
        assert float(boot.get("data-z-lift")) == pytest.approx(blift, abs=1e-6)


def l12(dev):
    """L12 on one device, the idiom spec/tests/test_deep_slots.py uses. Every
    key containing a slash goes through manifest.nested_key_host from here."""
    data = yaml.safe_load(dev.read_text())
    with lint.collecting() as got:
        lint.lint_device_occupants(dev, data, [str(LIB)])
    return [e for e in got.errors if "[L12]" in e]


def test_a_boot_on_a_half_seated_in_a_bay_builds_and_lints(tmp_path):
    """THE SEAT THIS TASK WAS ASKED FOR, and the one the review page will show:
    a duplex plug on the adapter `lc01` in the cassette in `bay-1`, with a boot
    on half `a`. The key is `bay-1/lc01-occupant/a`.

    IT IS A DIFFERENT CASE FROM THE DCP ONE ABOVE, and the difference is where
    the chained occupant sits in the key: at the HEAD when the plug is seated
    on a device placement (`port-1510-occupant/a`), and MID-WALK here, after a
    bay. `nested_key_host` resolved a chained occupant only at the head in the
    first cut of this work, so this key BUILT and FAILED L12 - lint refusing a
    seat that rendered, which is the one thing a resolver shared by both sides
    exists to prevent. Both halves of it are checked here, in one test, so
    neither can go green alone.

    The build: the boot is drawn inside the plug's own group at
    `bay-1/module/lc01-occupant/a-occupant`, lands its mate on the half's
    presented point, and stands off by the plug body's own `out`.
    The resolver: it answers the half's ref, the plug's ref, and the drawing
    path the build actually used.
    L12: clean."""
    occupants = {"bay-1/lc01": DUPLEX, "bay-1/lc01-occupant/a": BOOT}
    dev = fhd(tmp_path, LC_CASSETTE, occupants)

    # 1. the resolver, and it answers the path the build draws at
    data = yaml.safe_load(dev.read_text())

    def _res(r):
        try:
            return contract(r)
        except Exception:
            return None
    host_ref, module_ref, module_path = nested_key_host(
        "bay-1/lc01-occupant/a", data, data["configurations"]["base"], _res)
    assert (host_ref, module_ref) == (LC, DUPLEX)
    assert module_path == "bay-1/module/lc01-occupant"

    # 2. L12 over the same key
    assert l12(dev) == []

    # 3. the build
    root, parents = face(build(dev, tmp_path / "o", LIB), "fhd-1ufce", "base")
    plug = occupant(root, "bay-1/module/lc01", DUPLEX)
    boot = occupant(root, "bay-1/module/lc01-occupant/a", BOOT)
    assert is_inside(parents, boot, plug)
    _, bpt, blift = presented_interface(contract(LC), contract)
    assert blift > 0, "the plug presents no standoff, so this checks nothing"
    hx, hy = device_point(parents, by_path(root, "bay-1/module/lc01-occupant/a"), bpt)
    ox, oy = device_point(parents, boot,
                          contract(BOOT)["connection-points"]["mate"]["at"])
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6
    assert float(boot.get("data-z-lift")) == pytest.approx(blift, abs=1e-6)
    # half `b` was not keyed, so nothing is seated on it - a default nobody
    # declared must not appear, and this is the guard that says so
    drawn = {n.get("data-path") for n in root.iter()}
    assert "bay-1/module/lc01-occupant/a-occupant" in drawn, "nothing was seated"
    assert "bay-1/module/lc01-occupant/b-occupant" not in drawn


def test_a_key_under_a_seated_occupant_that_reaches_nothing_is_still_an_error(tmp_path):
    """The widening must not turn a typo into silence. `bay-1/lc01-occupant/zz`
    names no part of the plug and no occupant seated on it, in a position the
    resolver now walks rather than refusing outright - so the refusal has to
    come from the right place and name the right thing."""
    dev = fhd(tmp_path, LC_CASSETTE, {"bay-1/lc01": DUPLEX,
                                      "bay-1/lc01-occupant/zz": BOOT})
    errs = l12(dev)
    assert len(errs) == 1 and "occupants/bay-1/lc01-occupant/zz" in errs[0], errs
    r = run(dev, tmp_path / "o", LIB)
    assert r.returncode != 0
    assert "occupants/bay-1/lc01-occupant/zz" in r.stderr, r.stderr[-600:]


def test_the_sc_plug_seats_in_an_fhd_sc_cassette_bore(tmp_path):
    """`bay-1/sc1/1` is bore 1 of the adapter `sc1` in the cassette -
    the seat common/sc-dust-cap@1 already takes, with the plug in its place."""
    dev = fhd(tmp_path, SC_CASSETTE, {"bay-1/sc1/1": SC})
    root, parents = face(build(dev, tmp_path / "o", LIB), "fhd-1ufce", "base")
    occ = occupant(root, "bay-1/module/sc1/1", SC)
    host = by_path(root, "bay-1/module/sc1/1")
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
    """std/mpo@2 puts its `mate` on nothing, so it presents 0.0 and an
    occupant is seated at the panel plane - the same reason
    common/mpo-dust-cap@2's figures are absolute from the panel."""
    dev = fhd(tmp_path, "test/mpo-cassette@1", {"bay-1/mtp1": MPO12})
    root, parents = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    occ = occupant(root, "bay-1/module/mtp1", MPO12)
    _, _, presented = presented_interface(contract("std/mpo@2"), contract)
    assert presented == 0.0
    assert float(occ.get("data-z-lift") or 0.0) == pytest.approx(0.0, abs=1e-6)
    body = next(n for n in occ.iter() if (n.get("id") or "").endswith("--body"))
    assert float(body.get("data-z-out")) == pytest.approx(15.2, abs=1e-6)
    # and it stands in front of the adapter bezel rather than inside it
    bezel = next(f for f in contract("common/mpo-adapter@2")["relief"]["features"]
                 if f["node"] == "bezel")["out"]
    assert float(body.get("data-z-out")) > bezel
