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
  - cisco/a9k-40ge-b@2  a vertical card, forty SFP cages alternating rotate
                        270 / 90, declaring no media (no ceiling);
  - juniper/mic3-3d-10xge-sfpp@1  a MIC, ten SFP+ cages at rotate 0 / 180.
"""
import json
import sys
from pathlib import Path

import pytest

import warmrender
from portrayal import libwalk
from portrayal import render as render_mod
from portrayal.manifest import load_yaml, presented_interface, seat_point

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
INDEXER = SPEC / "tools/portrayal/components_index.py"
RENDER = SPEC / "tools/portrayal/render.py"

NAMED = ["casa/smm-300gm@1", "cisco/a9k-40ge-b@2", "juniper/mic3-3d-10xge-sfpp@1"]


def _ref(entry):
    return f"{entry['ns']}/{entry['name']}@{entry['major'][1:]}"


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    out = tmp_path_factory.mktemp("components")
    r = warmrender.run([sys.executable, str(INDEXER), "--library", str(LIB),
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


def _bay_modules():
    """Every ref a bay can hold - a bay's `accepts` or `default`, or a
    configuration's `bays:` value - read off the device manifests and the
    contracts here, not off the indexer's own helper. A module in a bay
    forwards nothing (#610): the build never treats one as a placed slot."""
    found = set()

    def walk(o, key=None):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, k)
        elif isinstance(o, list):
            for v in o:
                if key == "bays" and isinstance(v, dict):
                    found.update(v.get("accepts") or [])
                    found.add(v.get("default"))
                walk(v, key)

    for f in libwalk.iter_devices(LIB) + libwalk.iter_components(LIB):
        doc = load_yaml(f) or {}
        walk(doc)
        for cfg in (doc.get("configurations") or {}).values():
            found.update(((cfg or {}).get("bays") or {}).values())
    return {r for r in found if isinstance(r, str)}


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
    turns = {c["rotate"] for c in index["cisco/a9k-40ge-b@2"]["cages"]}
    assert turns == {90, 270}


def test_a_card_cage_accepts_what_a_device_cage_of_its_media_accepts(index, tmp_path):
    """sfp-plus on the SMM-300GM and on the MIC takes exactly what a REAL
    device's sfp-plus cage takes - agr110's `port-0`, from a real build."""
    agr = LIB / "devices/edgecore/agr110/device.yaml"
    r = warmrender.run([sys.executable, str(RENDER), str(agr), "--library", str(LIB),
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
             "bores",
             # the facet the cage stands `on`, null where it stands on none
             # (P3 amended): a fact of the card's frame, so a card's alone
             "tilt"}


def shipped_default(ref, slot_id):
    """What test_shipped_caps.SHIPS says the slot `slot_id` of component `ref`
    ships: a composed adapter's own slot when that adapter ships at "self", an
    adapter's bore when it ships at "bores" - otherwise nothing."""
    from test_shipped_caps import SHIPS
    part = next((q for q in _contract(ref).get("parts") or []
                 if q.get("id") == slot_id), {})
    level, cap = SHIPS.get(part.get("ref", "").split(":")[0], (None, None))
    if level == "self":
        return cap
    level, cap = SHIPS.get(ref, (None, None))
    return cap if level == "bores" and slot_id in ("1", "2") else None


def test_a_card_cage_carries_exactly_the_r1_keys(index):
    """R1's list and nothing else: `occupant`, `group` and `rel-pos` are facts
    of a device frame, and a null there would read as an answer."""
    checked = 0
    for ref, entry in index.items():
        for c in entry.get("cages") or []:
            assert set(c) == CAGE_KEYS, (ref, c["id"], sorted(set(c) ^ CAGE_KEYS))
            # the only defaults are the caps the adapters ship (B3 task 8)
            assert c["default"] == shipped_default(ref, c["id"]), (ref, c["id"])
            # and only a duplex adapter's own slot spans anything
            assert c["bores"] == (["1", "2"] if c["interface"] == "lc-duplex"
                                  else []), (ref, c["id"])
            checked += 1
    assert checked > 0


def test_a_card_cage_on_a_facet_publishes_the_facet(index):
    """P3 amended: a cage whose part stands `on` a facet publishes that facet
    as `tilt` - the one _seat_nested_occupants tilts an optic seated there by
    - and every other cage publishes null. The FANT-H's two QSFP28 cages
    stand on its 36-degree `up` facet; that is the case that must not be
    vacuous."""
    tilted = set()
    for ref, entry in index.items():
        parts = {p["id"]: p for p in _contract(ref).get("parts") or []}
        for c in entry.get("cages") or []:
            p = parts[c["id"]]
            facet = render_mod._facets.facet_of(_contract(ref), p["on"]) if p.get("on") else None
            want = {"deg": facet["deg"], "facing": facet["facing"], "on": p["on"]} if facet else None
            assert c["tilt"] == want, (ref, c["id"])
            if want:
                tilted.add((ref, c["id"]))
    assert {("nokia/fant-h-bb@2", "qsfp-1"), ("nokia/fant-h-bb@2", "qsfp-2")} <= tilted, tilted


def test_a_card_cage_has_no_group_side_attrs(index):
    """R3, for a card that declares no `groups:` - the three named cards do
    not - the host side contributes nothing to a seated optic. A card that
    DOES declare groups (#511) is held to the other half below."""
    for ref in NAMED:
        assert not _contract(ref).get("groups"), f"{ref} now declares groups - repick"
        for c in index[ref]["cages"]:
            assert c["occupant-attrs"] == {}
            assert c["group-states"] is False


def test_a_grouped_card_cage_publishes_its_group_side(index):
    """#511: a cage on a card whose part joins one of the card's own groups
    publishes exactly group_side_attrs for that group as `occupant-attrs` -
    the map the build writes on an optic seated there. edgecore's AMX sled
    is the case: two CFP2 line ports and eight QSFP28 client ports, both
    groups `traffic`."""
    ref = "edgecore/amx-3200-sled400@1"
    contract = _contract(ref)
    groups = contract.get("groups") or {}
    parts = {p["id"]: p for p in contract.get("parts") or []}
    cages = index[ref]["cages"]
    assert cages and groups, "the sled publishes no cage or declares no group - vacuous"
    for c in cages:
        g = parts[c["id"]].get("group")
        assert g, (ref, c["id"])
        assert c["occupant-attrs"] == render_mod.group_side_attrs(g, groups[g])
        assert c["occupant-attrs"]["data-group-role"] == "traffic"
        assert c["media"] == groups[g]["attrs"]["media"]


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
            contract = _contract(ref)
            parts = {p["id"]: p for p in contract.get("parts") or []}
            p = parts[cage["id"]]
            # THE CARD'S OWN GROUPS STAND IN FOR A DEVICE'S (#511): the same
            # part, placed in a device that declares the card's groups, is
            # the same answer.
            device = {"groups": contract.get("groups") or {},
                      "views": {"front": {"components": {"placements": [p]}}}}
            [dev] = render_mod.cage_entries(device, "front", lib, families,
                                            candidates, {})
            assert cage["lift"] == dev["lift"] + float(p.get("lift") or 0.0), (ref, p["id"])
            assert {k: v for k, v in cage.items() if k not in ("lift", "tilt")} == \
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
    bays = _bay_modules()
    # the six single-MTP FHD backs, each ONE bulkhead a wrapper would forward
    assert sum(1 for r in faces if _forwarded_connector(lib, _contract(r))) == 6
    for ref, entry in index.items():
        skip = _forwarded_connector(lib, _contract(ref), face=ref in faces or ref in bays)
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
