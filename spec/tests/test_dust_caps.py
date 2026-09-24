"""The four dust caps, seated as occupants (B3, docs/pluggables-caps-design.md,
"Parts" and "3D").

A dust cap is a connector: it mates the interface a plug mates, seats at the
plug's mate point, and occupies the plug's slot. Three of the four carry
figures that used to be drawn INTO an adapter - `common/lc-duplex-adapter@4`,
`common/lc-duplex-v-adapter@6` and `common/sc-duplex-adapter@5` each keep the
full reading under `provenance.dust-caps` - and the fourth, the MPO cap, is
read off FS's own renders and says so.

WHAT THE ARITHMETIC HERE IS ABOUT. An adapter's `out` is ABSOLUTE from the
panel; a cap's own relief is measured from ITS SEAT, and the seat already
carries the host's lift. So a cap's own `out` is the adapter's old absolute
figure less the lift the adapter presents, and the build puts that lift back on
the occupant's group as `data-z-lift` while offsetting the occupant's `out`
values by the same amount. Both halves are checked: the contract's own
subtraction, and what the build actually compiles.

Nothing in the library declares a cap as a `default:` yet - that is the
adapters' own step - so every seating here is a CONFIGURED occupant on a copy
of a real device.
"""
import shutil

import pytest
import yaml

from test_nested_occupants import (LIB, SPEC, by_path, device_point,
                                   effective_lift, is_inside)
from test_slot_defaults import _copy, build, face

from portrayal import lint
from portrayal.manifest import load_yaml, presented_interface

DCP = "smartoptics/dcp-r-34d-cs"
FHD = "fs/fhd-1ufce"
LC_CASSETTE = "fs/fhd-2mtp12-lc-os2-a@4"     # twelve lc-duplex-v-adapter@6
SC_CASSETTE = "fs/fhd-1mtp12-sc-os2-a@3"     # six sc-duplex-adapter@5

LC_CAP = "common/lc-dust-cap@1"
LC_DUPLEX_CAP = "common/lc-duplex-dust-cap@2"
SC_CAP = "common/sc-dust-cap@1"
MPO_CAP = "common/mpo-dust-cap@2"

# WHAT THE ADAPTERS READ, as an ABSOLUTE distance from the panel. These are the
# figures the three adapters' own `provenance.dust-caps` state, and
# `test_the_adapter_still_states_the_reading_these_figures_came_from` holds
# each one against the sentence it was taken from, so this table cannot drift
# away from its source in silence.
ABSOLUTE_OUT = {LC_CAP: 9.525, LC_DUPLEX_CAP: 5.5, SC_CAP: 3.3}
ADAPTER_OF = {LC_CAP: ("common/lc-duplex-adapter", 6),
              LC_DUPLEX_CAP: ("common/lc-duplex-v-adapter", 6),
              SC_CAP: ("common/sc-duplex-adapter", 5)}
MATES = {LC_CAP: "lc", LC_DUPLEX_CAP: "lc-duplex", SC_CAP: "sc", MPO_CAP: "mpo"}
# WHICH PART EACH CAP SEATS ON inside its adapter: a bore id, or None where the
# cap spans the adapter's own slot.
BORE_OF = {LC_CAP: "1", LC_DUPLEX_CAP: None, SC_CAP: "1"}


def contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return load_yaml(LIB / "components" / ns / name / f"v{major}" / "contract.yaml")


def feature(ref, node):
    c = contract(ref)
    return next(f for f in c["relief"]["features"] if f["node"] == node)


# --- what each part is -----------------------------------------------------------------

@pytest.mark.parametrize("ref", sorted(MATES))
def test_a_cap_is_an_occupying_cap_that_mates_one_interface(ref):
    c = contract(ref)
    assert c["class"] == "cap"
    assert c["behaviour"] == "occupies"
    assert c["mates"] == MATES[ref]
    # it mates, so it needs the point that aligns it to its host (L11)
    assert c["connection-points"]["mate"]["direction"] == "front"
    # a cap is not a receptacle: it presents nothing and accepts nothing
    assert "interface" not in c
    assert ref.startswith("common/"), "no standard governs a cap's shape"


def test_the_four_caps_are_the_librarys_only_caps_and_there_are_four():
    """A census, and it asserts it measured something. `class: cap` is new with
    this work; if a fifth appears it needs its own paragraph here.

    KEYED FROM THE PATH, not from a guessed namespace: a cap added under
    `generic/` or a vendor would otherwise be reported as a missing `common/`
    one, which sends the reader to the wrong question."""
    found = {}
    for f in (LIB / "components").rglob("v*/contract.yaml"):
        c = load_yaml(f) or {}
        if c.get("class") == "cap":
            ns = f.parents[2].name
            found[f"{ns}/{c['name']}@{c['version'].split('.')[0]}"] = c
    assert len(found) == 4, sorted(found)
    assert set(found) == set(MATES), sorted(found)
    for ref, c in found.items():
        assert c.get("behaviour") == "occupies", ref
        assert c.get("mates"), ref


# --- the subtraction -------------------------------------------------------------------

def seat_lift(ref):
    """How far off the panel the build seats this cap, computed the way
    `solve_seat` computes it: the lift its host PRESENTS, plus whatever the
    host itself stands at.

    The two LC caps and the SC cap have different hosts, and the difference is
    the whole shape of the work. A simplex cap seats on a BORE, which presents
    0.0 - std/lc-bore@3 and std/sc-bore@1 both put `mate` on nothing - and
    stands at whatever `lift` its adapter's `parts:` entry gives it. A duplex
    cap seats on the ADAPTER, whose own `mate` sits `on:` its bezel and so
    presents that bezel's `out`. L116's depth arm is what keeps the two
    answers one number for a duplex adapter."""
    name, major = ADAPTER_OF[ref]
    adapter = contract(f"{name}@{major}")
    bore = BORE_OF[ref]
    if bore is None:
        _, _, lift = presented_interface(adapter, contract)
        return lift
    q = next(p for p in adapter["parts"] if p["id"] == bore)
    _, _, own = presented_interface(contract(q["ref"]), contract)
    assert own == 0.0, "the bore presents a lift of its own; this sum is wrong"
    return float(q.get("lift") or 0.0)


@pytest.mark.parametrize("ref", sorted(ABSOLUTE_OUT))
def test_a_caps_own_out_is_the_adapters_absolute_out_less_the_lift_it_presents(ref):
    """The rule the whole task turns on, computed rather than copied: the
    adapter's figure is absolute from the panel, the cap's is from its seat."""
    lift = seat_lift(ref)
    assert lift > 0, "nothing is seated off the panel, so there is nothing to subtract"
    assert feature(ref, "body")["out"] == pytest.approx(ABSOLUTE_OUT[ref] - lift)


@pytest.mark.parametrize("ref", sorted(ABSOLUTE_OUT))
def test_the_adapter_still_states_the_reading_these_figures_came_from(ref):
    """The figures above are the adapters', not this file's. Each adapter keeps
    the full cap reading under `provenance.dust-caps`; if that sentence loses
    the number, this table is stale and says so here rather than in a drawing."""
    name, major = ADAPTER_OF[ref]
    note = contract(f"{name}@{major}")["provenance"]["dust-caps"]
    assert f"out: {ABSOLUTE_OUT[ref]:g}" in note, note


def test_the_mpo_cap_marks_every_figure_it_carries_estimated():
    """The fourth cap has no adapter to take figures from, and neither of its
    two questions is settled by the renders it is read off: the pixel spans are
    measured but WHAT they measure is a reading, and no view along the depth
    axis can be unfolded at all. So every figure on it is `estimated`, and the
    contract has to say which reading each one assumes rather than dressing an
    interpretation as a measurement."""
    c = contract(MPO_CAP)
    assert set(c["size-confidence"].values()) == {"estimated"}
    assert feature(MPO_CAP, "body")["confidence"] == "estimated"
    assert feature(MPO_CAP, "grip")["confidence"] == "estimated"
    notes = c["size-notes"]
    # the check that makes the spans worth anything, and the two readings
    assert "ORTHOGRAPHIC FIRST" in notes and "quadratic" in notes
    assert "EXCLUDED" in notes and "NOT EXCLUDED" in notes
    depth = c["provenance"]["depth"]
    assert "ESTIMATED" in depth and "PERSPECTIVE" in depth
    assert "withdrawn" in depth, "the retracted derivation has to stay retracted"
    # @1 filed its doubt about std/mpo@1 as a hypothesis; @2 records what became
    # of it, and that the corrected figure did NOT come from this render
    aperture = c["provenance"]["aperture"]
    assert "hypothesis" in aperture and "did not come from here" in aperture


def test_the_mpo_caps_depth_figures_are_declared_choices_that_stack_right():
    """IMPORTANT 1 of the task 5 review, and what a test can and cannot do here.

    THERE IS NOTHING TO CHECK THE GRIP'S `out` AGAINST. No document held here
    dimensions an MTP cap and no render held here can be unfolded, so the height
    is a MODELLING CHOICE - and a test that compared it to another figure in the
    same file would be checking the contract against itself and would keep
    passing however wrong the figure was. This does not do that. It holds the
    two things that stay true whatever the number is, and it holds the contract
    to SAYING the number is a choice:

      - the ordering the drawing depends on - the saddle stands in front of the
        cap's face, and the cap's face in front of the adapter bezel it would
        otherwise be buried behind;
      - the arithmetic fault the first review caught - the seat is the panel
        (std/mpo@2 presents no lift), so the bezel is never added on top of a
        figure already measured from the panel.

    Whether the grip is the RIGHT height is open until something dimensions the
    part, and `provenance.depth` says so rather than this test pretending."""
    c = contract(MPO_CAP)
    grip = feature(MPO_CAP, "grip")
    body = feature(MPO_CAP, "body")
    bezel = feature("common/mpo-adapter@2", "bezel")["out"]
    assert body["out"] < grip["out"], "the saddle has to stand in front of the cap's face"
    assert body["out"] > bezel, "the cap's face would sit behind the adapter bezel"
    # the figure is declared a choice, in the key and on the feature itself
    assert "MODELLING CHOICE" in c["provenance"]["depth"]
    assert "MODELLING CHOICE" in grip["source"] and "NOT A READING" in grip["source"]
    # and nothing in the file quietly adds the bezel on top of a panel reading
    assert f"{grip['out'] + bezel:g}" not in c["provenance"]["depth"]


# THE FIGURE THE GRIP WAS BROUGHT DOWN FROM. Task 5 stood a 10.2 x 3.6 bar out to
# 8.0 from the panel as one solid - a plank - against FS's photographs of a thin,
# waisted saddle with a lip at its end.
PLANK_OUT = 8.0


def _skin_rect(ref, node_id):
    """(w, h) of a skin rect by id - the drawn outline a relief feature extrudes."""
    import xml.etree.ElementTree as ET
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    skin = LIB / "components" / ns / name / f"v{major}" / "skins" / "default.svg"
    hits = [e for e in ET.parse(skin).getroot().iter() if e.get("id") == node_id]
    assert len(hits) == 1, (ref, node_id, len(hits))
    return float(hits[0].get("width")), float(hits[0].get("height"))


def test_the_mpo_caps_grip_is_a_thin_waisted_saddle_not_a_plank():
    """The Task 7 review: the grip rendered as a plank. What FS draws is a web
    rising off the cap's face and a thin plate across its end, the plate
    overhanging the web's waist so a fingertip goes under it. So the grip is
    two named features, stacked:

      - `saddle`, the web, standing on the cap's face (its lift is the body's
        `out`) and NARROWER along the long axis than the plate it carries;
      - `grip`, the plate, standing on the saddle (its lift is the saddle's
        `out`), THINNER than the saddle's rise;

    and the plate's front is brought down from the plank's 8.0. The heights
    stay declared modelling choices - this holds the shape they have to make,
    not the numbers."""
    body, saddle, grip = (feature(MPO_CAP, n) for n in ("body", "saddle", "grip"))
    assert saddle["lift"] == pytest.approx(body["out"]), "the web stands on the cap's face"
    assert grip["lift"] == pytest.approx(saddle["out"]), "the plate stands on the web"
    rise, plate = saddle["out"] - saddle["lift"], grip["out"] - grip["lift"]
    assert 0 < plate < rise, (plate, rise)
    assert grip["out"] < PLANK_OUT, grip["out"]
    (ww, wh), (pw, ph) = _skin_rect(MPO_CAP, "saddle"), _skin_rect(MPO_CAP, "grip")
    assert ww < pw, "no waist: the plate would have nothing to get a fingertip under"
    assert wh <= ph
    for f in (saddle, grip):
        assert f["confidence"] == "estimated" and "MODELLING CHOICE" in f["source"]


def test_a_seated_mpo_caps_plate_stands_on_its_saddle(tmp_path, lib):
    """The same stack ON A BUILD: the plate's back (its summed lift) is the
    saddle's front, and the saddle's back is the cap's face. Lifts are summed
    down the tree and `out` is absolute, so a plate nested wrongly would build
    inside out or float, and 2D would not show it."""
    dev = fhd(tmp_path, "test/mpo-cassette@1", {"bay-1/mtp1": MPO_CAP})
    root, parents = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    occ = occupant(root, parents, "bay-1/module/mtp1", MPO_CAP)
    body, saddle, grip = (inside(occ, n) for n in ("body", "saddle", "grip"))
    stack = [(float(n.get("data-z-out")), effective_lift(parents, n))
             for n in (body, saddle, grip)]
    assert len(stack) == 3
    (b_out, _b), (s_out, s_back), (g_out, g_back) = stack
    assert s_back == pytest.approx(b_out, abs=1e-6)
    assert g_back == pytest.approx(s_out, abs=1e-6)
    assert b_out < s_out < g_out < PLANK_OUT


@pytest.mark.parametrize("ref,node,inner", [(LC_CAP, "inset", "pocket"),
                                            (LC_DUPLEX_CAP, "inset-tx", "pocket"),
                                            (LC_DUPLEX_CAP, "inset-rx", "pocket"),
                                            (SC_CAP, "grip", "out"),
                                            (MPO_CAP, "saddle", "out")])
def test_a_feature_inside_a_cap_is_lifted_onto_the_caps_own_front(ref, node, inner):
    """A child of the cap carries a lift RELATIVE to the cap, because lifts are
    summed down the tree. Each of these sits on the cap's face, so its lift is
    the cap's own `out`; a pocket then cuts back from there and a grip stands
    out from it."""
    body, feat = feature(ref, "body"), feature(ref, node)
    assert feat["lift"] == pytest.approx(body["out"])
    if inner == "pocket":
        assert feat["pocket"] > 0 and "out" not in feat
    else:
        assert feat["out"] > body["out"]


# --- the devices the caps are seated on ------------------------------------------------

def dcp(tmp_path, occupants):
    """smartoptics/dcp-r-34d-cs, which PLACES common/lc-duplex-adapter@6 as
    port-1510, with a configuration seating caps in its bores."""
    dev = shutil.copytree(LIB / "devices" / DCP, tmp_path / "dcp") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    assert not d.get("configurations"), "the device now ships its own; rewrite this"
    d["configurations"] = {"default": {"kind": "base", "default": True,
                                       "occupants": occupants}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def fhd(tmp_path, cassette, occupants):
    """fs/fhd-1ufce with `cassette` in bay-1 of its base configuration."""
    dev = shutil.copytree(LIB / "devices" / FHD, tmp_path / "fhd") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"]["base"]
    cfg["bays"] = {**(cfg.get("bays") or {}), "bay-1": cassette}
    cfg["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


@pytest.fixture
def lib(tmp_path):
    """A throwaway library holding one part the real one has no equivalent of:
    a cassette whose front carries MTP adapters. Every MPO aperture in the
    library today is on a cassette's REAR face, and this file's business is the
    cap, not the addressing of a rear."""
    root = tmp_path / "lib"

    def mpo_front(c):
        c["parts"] = [{"id": "mtp1", "ref": "common/mpo-adapter@2", "at": [20.0, 12.0]},
                      {"id": "mtp2", "ref": "common/mpo-adapter@2", "at": [60.0, 12.0]}]
        for k in ("optical", "faces"):
            c.pop(k, None)
    _copy(root, "fs/fhd-1mtp12-sc-os2-a", 3, "mpo-cassette", mpo_front)
    return root


# --- what the build compiles ------------------------------------------------------------

def occupant(root, parents, path, ref):
    occ = by_path(root, f"{path}-occupant")
    assert occ.get("data-ref").rsplit(":", 1)[0] == ref
    assert occ.get("data-for") == path
    return occ


def inside(occ, suffix):
    """The compiled node a relief feature was written onto: render.py names it
    `<instance>--<node>`, so the suffix is what identifies it inside the
    occupant's own group."""
    hits = [n for n in occ.iter() if (n.get("id") or "").endswith(f"--{suffix}")]
    assert len(hits) == 1, (suffix, [n.get("id") for n in occ.iter()])
    return hits[0]


def front_of(parents, occ, node):
    """Where a raised node's front face is, absolutely from the panel:
    `data-z-out` as the build wrote it. The summed `data-z-lift` is its BACK,
    and the two together are what relief.js builds the body between."""
    return float(node.get("data-z-out")), effective_lift(parents, occ)


def test_the_lc_cap_stands_where_the_adapter_drew_it(tmp_path):
    """Both bores of the Smartoptics adapter, at the lift the bezel presents,
    with the cap's front back at the adapter's old absolute 9.525."""
    dev = dcp(tmp_path, {"port-1510/1": LC_CAP, "port-1510/2": LC_CAP})
    root, parents = face(build(dev, tmp_path / "o", LIB), "dcp-r-34d-cs", "default")
    want = seat_lift(LC_CAP)
    for bore in ("1", "2"):
        occ = occupant(root, parents, f"port-1510/{bore}", LC_CAP)
        out, lift = front_of(parents, occ, inside(occ, "body"))
        assert lift == pytest.approx(want, abs=1e-6)
        assert out == pytest.approx(ABSOLUTE_OUT[LC_CAP], abs=1e-6)
        # and it lands its own mate on the bore's, turned with it
        host = by_path(root, f"port-1510/{bore}")
        assert is_inside(parents, occ, parents[host])
        hx, hy = device_point(parents, host,
                              contract("std/lc-bore@3")["connection-points"]["mate"]["at"])
        ox, oy = device_point(parents, occ,
                              contract(LC_CAP)["connection-points"]["mate"]["at"])
        assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6


def test_the_duplex_cap_stands_where_the_fhd_adapter_drew_it(tmp_path):
    """The FS cap spans BOTH stacked bores, so it seats on the adapter's own
    slot - one key, one occupant - at the bezel's 1.2."""
    dev = fhd(tmp_path, LC_CASSETTE, {"bay-1/lc01": LC_DUPLEX_CAP})
    root, parents = face(build(dev, tmp_path / "o", LIB), "fhd-1ufce", "base")
    occ = occupant(root, parents, "bay-1/module/lc01", LC_DUPLEX_CAP)
    out, lift = front_of(parents, occ, inside(occ, "body"))
    assert lift == pytest.approx(seat_lift(LC_DUPLEX_CAP), abs=1e-6)
    assert out == pytest.approx(ABSOLUTE_OUT[LC_DUPLEX_CAP], abs=1e-6)


def test_the_sc_cap_and_its_grip_stand_where_the_adapter_drew_them(tmp_path):
    """The SC cap's raised grip is the one feature of the four that stands in
    FRONT of its cap rather than cutting into it: 3.8 against the cap's 3.3."""
    dev = fhd(tmp_path, SC_CASSETTE, {"bay-1/sc1/1": SC_CAP})
    root, parents = face(build(dev, tmp_path / "o", LIB), "fhd-1ufce", "base")
    occ = occupant(root, parents, "bay-1/module/sc1/1", SC_CAP)
    out, lift = front_of(parents, occ, inside(occ, "body"))
    assert lift == pytest.approx(seat_lift(SC_CAP), abs=1e-6)
    assert out == pytest.approx(ABSOLUTE_OUT[SC_CAP], abs=1e-6)
    grip = inside(occ, "grip")
    assert float(grip.get("data-z-out")) == pytest.approx(3.8, abs=1e-6)
    # the grip's own back is the cap's front: lifts are summed down the tree
    assert lift + float(grip.get("data-z-lift")) == pytest.approx(out, abs=1e-6)


def test_the_mpo_cap_seats_at_the_panel_because_its_aperture_presents_no_lift(tmp_path, lib):
    """std/mpo@2's `mate` sits `on:` nothing, so it presents 0.0 and its
    occupant is seated at the panel plane - which is why this cap's figures are
    absolute from the panel and have to clear common/mpo-adapter@2's own bezel
    by hand."""
    dev = fhd(tmp_path, "test/mpo-cassette@1", {"bay-1/mtp1": MPO_CAP})
    root, parents = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    occ = occupant(root, parents, "bay-1/module/mtp1", MPO_CAP)
    out, lift = front_of(parents, occ, inside(occ, "body"))
    _, _, presented = presented_interface(contract("std/mpo@2"), contract)
    assert presented == 0.0
    assert lift == pytest.approx(0.0, abs=1e-6)
    assert out == pytest.approx(feature(MPO_CAP, "body")["out"], abs=1e-6)
    bezel = feature("common/mpo-adapter@2", "bezel")["out"]
    assert out > bezel, "the cap would be buried in the adapter it plugs"
    assert float(inside(occ, "grip").get("data-z-out")) == pytest.approx(
        feature(MPO_CAP, "grip")["out"], abs=1e-6)


# --- the 3D rule the spec asks for ------------------------------------------------------

SEATINGS = [
    (LC_CAP, DCP, "dcp-r-34d-cs", "default", "port-1510/1", "port-1510/1"),
    (LC_DUPLEX_CAP, FHD, "fhd-1ufce", "base", "bay-1/lc01", "bay-1/module/lc01"),
    (SC_CAP, FHD, "fhd-1ufce", "base", "bay-1/sc1/1", "bay-1/module/sc1/1"),
    (MPO_CAP, FHD, "fhd-1ufce", "base", "bay-1/mtp1", "bay-1/module/mtp1"),
]
CASSETTE_FOR = {LC_DUPLEX_CAP: LC_CASSETTE, SC_CAP: SC_CASSETTE,
                MPO_CAP: "test/mpo-cassette@1"}


def seat(tmp_path, root_lib, ref):
    _, _, name, config, key, path = next(s for s in SEATINGS if s[0] == ref)
    if ref == LC_CAP:
        dev = dcp(tmp_path, {key: ref})
    else:
        dev = fhd(tmp_path, CASSETTE_FOR[ref], {key: ref})
    root, parents = face(build(dev, tmp_path / "o", root_lib), name, config)
    return root, parents, occupant(root, parents, path, ref)


@pytest.mark.parametrize("ref", [LC_CAP, LC_DUPLEX_CAP, SC_CAP, MPO_CAP])
def test_a_pocket_inside_a_cap_never_stands_in_front_of_the_cap_face(tmp_path, lib, ref):
    """docs/pluggables-caps-design.md, "3D": a cap's inset or grip is a child of
    the cap and its lift is relative to the cap, not summed a second time - and
    a POCKET inside a cap must sit AT or BEHIND the cap's own front, because a
    recess in front of the face it is cut into is a recess in nothing.

    Written to MEASURE, not to assume: it counts the pockets it found and fails
    if a cap it was handed has none to check and none expected."""
    root, parents, occ = seat(tmp_path, lib, ref)
    body = inside(occ, "body")
    front = float(body.get("data-z-out"))
    base = effective_lift(parents, occ)
    pockets = [n for n in occ.iter() if n.get("data-depth") is not None]
    raised = [n for n in occ.iter()
              if n.get("data-z-out") is not None and n is not body]
    want = sum(1 for f in contract(ref)["relief"]["features"] if f.get("pocket"))
    assert len(pockets) == want, [n.get("id") for n in pockets]
    for n in pockets:
        mouth = effective_lift(parents, n)
        assert mouth <= front + 1e-6, (n.get("id"), mouth, front)
        assert mouth - float(n.get("data-depth")) >= base - 1e-6, \
            "the pocket cuts out through the back of the cap"
    # A RAISED FEATURE STANDS ON SOMETHING: its back (the summed lift) is the
    # cap's own front or the front of another raised feature of the same cap -
    # the MPO cap's plate stands on its saddle, which stands on the face. A
    # lift summed a second time lands on neither, which is the fault this holds.
    surfaces = [front] + [float(n.get("data-z-out")) for n in raised]
    for n in raised:
        assert float(n.get("data-z-out")) > front, (n.get("id"), front)
        back = effective_lift(parents, n)
        assert back < float(n.get("data-z-out")), (n.get("id"), "built inside out")
        assert any(back == pytest.approx(s, abs=1e-6) for s in surfaces), \
            (n.get("id"), back, surfaces)
    assert pockets or raised, "this cap compiled no inner feature at all"


# --- L116's fourth arm ------------------------------------------------------------------

def l112(ref, root=None):
    """L116 over one contract, found in `root` if given and in the real library
    otherwise. STANDARDS is filled the way main() fills it - lint.py loads it
    inside main, so a rule called directly finds an empty registry and the
    pitch arm passes VACUOUSLY."""
    lint.STANDARDS.update(
        lint.load_yaml(SPEC / "schemas/standards.yaml")["standards"])
    assert lint.STANDARDS.get("lc-duplex-receptacle", {}).get("pitch")
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    base = root if root is not None else LIB
    f = base / "components" / ns / name / f"v{major}" / "contract.yaml"
    data = yaml.safe_load(f.read_text())
    roots = [str(root), str(LIB)] if root is not None else [str(LIB)]
    with lint.collecting() as got:
        lint.lint_component_spanned_geometry(f, data, roots)
    return [e for e in got.errors if "[L116]" in e]


@pytest.mark.parametrize("name,major", [("common/lc-duplex-adapter", 6),
                                        ("common/lc-duplex-v-adapter", 6)])
def test_both_library_adapters_lift_their_bores_to_the_depth_they_present(name, major):
    """What a test used to say about these two by name, now asked by the rule -
    and still asserted here, because the rule is only as good as the corpus it
    is pointed at."""
    c = contract(f"{name}@{major}")
    _, _, presented = presented_interface(c, contract)
    assert presented > 0 and {q.get("lift") for q in c["parts"]} == {presented}
    assert l112(f"{name}@{major}") == []


@pytest.mark.parametrize("name,major", [("common/lc-duplex-adapter", 6),
                                        ("common/lc-duplex-v-adapter", 6)])
def test_lint_refuses_a_bore_at_a_different_depth_from_the_slot(tmp_path, name, major):
    """The fault the rule exists for: the bores drop to the panel while the
    adapter still presents its slot on the raised bezel, so a duplex cap would
    stand proud of the simplex cap it replaces by the bezel's own height."""
    root = tmp_path / "lib"

    def sunk(c):
        for q in c["parts"]:
            q.pop("lift", None)
    _copy(root, name, major, "flat-adapter", sunk)
    got = l112("test/flat-adapter@1", root)
    assert got and "lift" in got[0] and "same face" in got[0], got
    assert any("'1'" in e for e in got) and any("'2'" in e for e in got), got
