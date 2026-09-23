"""A component's own `cages` in components.json (#484): cages ride on the card.

22 of the library's devices are modular chassis whose every port lives on a
card in a bay, and their `configs.json` lists no cage in any view - `cages[]`
is built from device-level placements only. So a card seated in a bay, or
swapped into one at runtime, offered no optic anywhere. The answer taken
(R1 of the #484 plan) is that a component publishes its OWN cages, in its own
frame, computed by the SAME core a device view's `cages[]` is
(`render.cage_entry`), so a host that seats a card into an empty slot learns
its cages from the card rather than from a configuration that never named it.

THESE RUN AGAINST THE REAL LIBRARY AND A REAL components.json, built here by
the indexer the build runs - never a fixture. The three named cards were
picked by reading their contracts:

  - casa/smm-300gm@1    ten `std/sfp-ganged@1` at rotate 90 with
                        `attrs.media: sfp-plus`, plus two QSFP28 cages;
  - cisco/a9k-40ge-b@1  a vertical card, forty SFP cages alternating rotate
                        270 / 90, declaring no media (no ceiling);
  - juniper/mic3-3d-10xge-sfpp@1  a MIC, ten SFP+ cages at rotate 0 / 180.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from portrayal import render as render_mod
from portrayal.manifest import load_yaml, presented_interface, seat_point

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
INDEXER = SPEC / "tools/portrayal/components_index.py"
RENDER = SPEC / "tools/portrayal/render.py"

NAMED = ["casa/smm-300gm@1", "cisco/a9k-40ge-b@1", "juniper/mic3-3d-10xge-sfpp@1"]


def _ref(entry):
    return f"{entry['ns']}/{entry['name']}@{entry['major'][1:]}"


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    out = tmp_path_factory.mktemp("components")
    r = subprocess.run([sys.executable, str(INDEXER), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads((out / "components.json").read_text())
    return {_ref(e): e for e in doc["components"]}


@pytest.fixture(scope="module")
def lib():
    return render_mod.Library([str(LIB)])


@pytest.fixture(scope="module")
def families():
    fams = render_mod._pluggable_families()
    assert fams, "spec/schemas/pluggables.yaml did not load"
    return fams


@pytest.fixture(scope="module")
def candidates():
    return render_mod._pluggable_candidates([str(LIB)])


def _contract(ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    return load_yaml(LIB / "components" / ns / name / f"v{major}" / "contract.yaml")


def _presents(lib, families, part):
    """(interface, mate_at, lift) when `part` is a cage or a connector slot
    (B3: spec/schemas/connectors.yaml), else None - the census's own reading,
    independent of the index."""
    def _res(ref):
        try:
            return lib.resolve(ref)[0]
        except Exception:
            return None
    c = _res(part["ref"])
    if not c:
        return None
    iface, mate_at, lift = presented_interface(c, _res)
    if not iface:
        return None
    if (render_mod._family_by_interface(families, iface) is None
            and iface not in render_mod._connector_registry()):
        return None
    return iface, mate_at, lift


def _faces(index):
    """Every ref some component names as one of its `faces:`, read off the
    contracts, not off the indexer's own helper."""
    return {((_contract(ref).get("faces") or {}).get(k) or {}).get("ref")
            for ref in index for k in ("plan", "rear")} - {None}


def _forwarded_connector(lib, contract, face=False):
    """The part id a contract presents as its OWN connector slot by
    forwarding (B3, P2) - published where the contract is placed, never on
    the contract itself - or None. Read off `presented_interface` here, not
    off render's helper: a contract without its own interface that presents
    a connector interface anyway got it from its one composed aperture.
    A FACE forwards nothing (B3, Task 7i): nothing places a cassette's back,
    so its one bulkhead is published on the back itself."""
    if face:
        return None
    def _res(ref):
        try:
            return lib.resolve(ref)[0]
        except Exception:
            return None
    own = contract.get("interface") and (contract.get("connection-points") or {}).get(
        contract.get("interface-at") or "mate")
    iface, _at, _lift = presented_interface(contract, _res)
    if own or iface not in render_mod._connector_registry():
        return None
    [pid] = [p["id"] for p in contract.get("parts") or []
             if (_res(p.get("ref")) or {}).get("interface") == iface]
    return pid


@pytest.mark.parametrize("ref", NAMED)
def test_a_card_publishes_one_cage_per_cage_presenting_part(index, lib, families, ref):
    parts = _contract(ref).get("parts") or []
    expected = [p for p in parts if _presents(lib, families, p)]
    assert expected, f"{ref} has no cage-presenting part - the pick is wrong"
    cages = index[ref].get("cages")
    assert cages, f"{ref}: components.json carries no cages"
    assert [c["id"] for c in cages] == [p["id"] for p in expected]


@pytest.mark.parametrize("ref", NAMED)
def test_a_card_cage_mates_in_the_card_frame(index, lib, families, ref):
    parts = {p["id"]: p for p in _contract(ref).get("parts") or []}
    for cage in index[ref]["cages"]:
        p = parts[cage["id"]]
        _iface, mate_at, _lift = _presents(lib, families, p)
        size = lib.resolve(p["ref"])[0]["size"]
        assert cage["at"] == p["at"]
        assert cage["rotate"] == p.get("rotate")
        assert cage["mate"] == seat_point(p["at"], size, p.get("rotate"), mate_at)


def test_the_vertical_card_carries_both_of_its_turns(index):
    """The a9k-40ge-b is the one whose cages are turned both ways: a mate
    point that ignored the rotation would land every 270 cage on the wrong
    side of its opening."""
    turns = {c["rotate"] for c in index["cisco/a9k-40ge-b@1"]["cages"]}
    assert turns == {90, 270}


def test_a_card_cage_accepts_what_a_device_cage_of_its_media_accepts(index, tmp_path):
    """sfp-plus on the SMM-300GM and on the MIC takes exactly what a REAL
    device's sfp-plus cage takes - agr110's `port-0`, from a real build."""
    agr = LIB / "devices/edgecore/agr110/device.yaml"
    r = subprocess.run([sys.executable, str(RENDER), str(agr), "--library", str(LIB),
                        "--out", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    dev = json.loads((tmp_path / "agr110.configs.json").read_text())
    device_cage = next(c for c in dev["cages"]["front"] if c["id"] == "port-0")
    assert (device_cage["interface"], device_cage["media"]) == ("sfp", "sfp-plus")
    assert device_cage["accepts"], "the device cage accepts nothing - vacuous"
    for ref in ("casa/smm-300gm@1", "juniper/mic3-3d-10xge-sfpp@1"):
        sfpp = [c for c in index[ref]["cages"] if c["media"] == "sfp-plus"]
        assert sfpp, ref
        for c in sfpp:
            assert c["interface"] == "sfp"
            assert c["accepts"] == device_cage["accepts"], (ref, c["id"])


CAGE_KEYS = {"id", "at", "mate", "lift", "rotate", "interface", "media",
             "accepts", "occupant-attrs", "mirror", "group-states", "kind",
             # what this slot ships holding (B3), null where it ships empty -
             # a fact of the contract, so it is published here too
             "default",
             # the slots this one takes the place of (B3, "The duplex host"):
             # an LC duplex adapter's two bores, [] for a cage
             "bores"}


def test_a_card_cage_carries_exactly_the_r1_keys(index):
    """R1's list and nothing else: `occupant`, `group` and `rel-pos` are facts
    of a device frame, and a null there would read as an answer."""
    checked = 0
    for ref, entry in index.items():
        for c in entry.get("cages") or []:
            assert set(c) == CAGE_KEYS, (ref, c["id"], sorted(set(c) ^ CAGE_KEYS))
            # nothing in the library declares a default yet (B3 task 3)
            assert c["default"] is None, (ref, c["id"])
            # and only a duplex adapter's own slot spans anything
            assert c["bores"] == (["tx", "rx"] if c["interface"] == "lc-duplex"
                                  else []), (ref, c["id"])
            checked += 1
    assert checked > 0


def test_a_card_cage_has_no_group_side_attrs(index):
    """R3: a contract declares no `groups:`, so the host side contributes
    nothing to a seated optic."""
    for ref in NAMED:
        for c in index[ref]["cages"]:
            assert c["occupant-attrs"] == {}
            assert c["group-states"] is False


def test_every_component_cage_is_the_device_answer_for_the_same_placement(
        index, lib, families, candidates):
    """ONE CORE, HELD TO IT: every component cage equals the entry
    `cage_entries` - the device path - builds for the same part placed on a
    one-placement device, except `lift`, which on a card also carries the
    part's own `lift` (a composed part's lift is written as data-z-lift; a
    device placement's is not), and the device-frame keys a card drops."""
    checked = 0
    for ref, entry in index.items():
        for cage in entry.get("cages") or []:
            parts = {p["id"]: p for p in _contract(ref).get("parts") or []}
            p = parts[cage["id"]]
            device = {"views": {"front": {"components": {"placements": [p]}}}}
            [dev] = render_mod.cage_entries(device, "front", lib, families,
                                            candidates, {})
            assert cage["lift"] == dev["lift"] + float(p.get("lift") or 0.0), (ref, p["id"])
            assert {k: v for k, v in cage.items() if k != "lift"} == \
                {k: v for k, v in dev.items() if k != "lift"
                 and k not in render_mod.COMPONENT_CAGE_DROPS}, (ref, p["id"])
            checked += 1
    assert checked > 0


def test_the_census_every_cage_presenting_part_is_published(index, lib, families):
    """Across the whole library: the published cages are exactly the
    cage-presenting parts, counted independently of the indexer. 166
    components / 2171 cages when this was written; the live count is what is
    asserted, and that it is not zero."""
    want_components, want_cages, forwarded = 0, 0, 0
    faces = _faces(index)
    # the six single-MTP FHD backs, each ONE bulkhead a wrapper would forward
    assert sum(1 for r in faces if _forwarded_connector(lib, _contract(r))) == 6
    for ref, entry in index.items():
        skip = _forwarded_connector(lib, _contract(ref), face=ref in faces)
        forwarded += skip is not None
        n = sum(1 for p in _contract(ref).get("parts") or []
                if p["id"] != skip and _presents(lib, families, p))
        assert len(entry.get("cages") or []) == n, ref
        if n:
            want_components += 1
            want_cages += n
    got_components = sum(1 for e in index.values() if e.get("cages"))
    got_cages = sum(len(e.get("cages") or []) for e in index.values())
    assert want_components > 0 and want_cages > 0
    # P2 is exercised, not assumed: common/mpo-adapter@2 forwards its bore
    assert forwarded > 0
    assert (got_components, got_cages) == (want_components, want_cages)


def test_a_component_with_no_cage_carries_no_cages_key(index, lib, families):
    blanks = [ref for ref, e in index.items() if not e.get("parts")]
    assert blanks
    for ref in blanks:
        assert "cages" not in index[ref], ref


def test_a_composed_parts_own_lift_reaches_the_cage(index):
    """smartoptics/dcp-404 composes its QSFP cages at `lift: 44.0`, which the
    build writes as data-z-lift on each cage's group. An optic seated inside
    the card sits beside that group, not in it, so the published lift has to
    carry the 44 - and a consumer that refuses a lifted cage refuses it."""
    cages = index["smartoptics/dcp-404@1"]["cages"]
    assert cages
    assert {c["lift"] for c in cages} == {44.0}
