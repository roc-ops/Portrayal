"""`chassis.ears` positions and `chassis.kits` on a device (roc-ops/Portrayal#906).

A device says where its ears can put the faceplate (named positions, `at` only
when a source gives it) and which rail kits it takes, each a `kind: kit` from
#905 (docs/rack-mounting-design.md sections 3 and 5). The schema holds the
words; lint L160-L163 hold what reads another entry or another file; L5, L10
and L101 refuse a kit anywhere but `chassis.kits`; devicelock files both keys
as chassis surface and follows a listed kit into `composed`.

No real kit or device states either key yet, so every test builds its own
library on tmp_path - a fake kit and a device listing it - and each rule is
tested both ways.
"""
import copy
import json
import pathlib
import shutil

import jsonschema
import pytest
import yaml

from portrayal import components_catalogue as cat
from portrayal import devicelock as dl
from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEVICE_SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
VALIDATOR = jsonschema.Draft202012Validator(DEVICE_SCHEMA)
KIT_REF = "acme/slide@1"

PART = {"format": 1, "kind": "component", "name": "inner", "version": "1.0.0",
        "class": "bracket", "size": {"w": 20, "h": 40},
        "description": "A rail member. Test part."}

KIT = {
    "format": 1, "kind": "kit", "name": "slide", "version": "1.0.0",
    "description": "A three-member slide. Test kit.",
    "motion": "sliding", "travel": "full", "install": "drop-in",
    "parts": [{"ref": "acme/inner@1", "id": "inner", "count": 2},
              {"ref": "acme/outer@1", "id": "outer", "count": 2},
              {"ref": "acme/mid@1", "id": "mid", "count": 2}],
    "configurations": [
        {"id": "four-post", "racks": ["4-post"], "parts": ["inner", "outer"],
         "depth": {"square": [631, 868], "round": [617, 861]}},
        {"id": "short", "racks": ["2-post"], "parts": ["mid"], "depth": [500, 600]}],
    "accessories": [{"kind": "cma", "ref": "acme/cma@1"}],
}

EARS = {"h": 43.5, "y": 0.15, "positions": [
    {"name": "flush", "at": 0, "default": True},
    {"name": "recessed", "at": -25.4, "label": "chassis recessed"},
    {"name": "mid", "at": 228, "racks": ["2-post"],
     "part": {"kit": KIT_REF, "part": "mid"}}]}

KITS = [{"ref": KIT_REF, "supply": "in-box",
         "depth": {"config": "four-post",
                   "range": {"square": [685, 868], "round": [671, 861]}}},
        {"ref": "acme/slide-rev@1", "supply": "optional", "variant": "reversed"}]


def _device(**chassis):
    return {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
            "manufacturer": "M", "model": "M", "maturity": "modelled",
            "profile": "networking",
            "chassis": {"width": 440.0, "height": 44.45, "depth": 500.0, "ru": 1,
                        **chassis},
            "views": {"front": {"size": {"w": 440.0, "h": 44.45}}}}


def _write(lib, ref, doc):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    d = lib / "components" / ns / name / f"v{major}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "contract.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    return d / "contract.yaml"


@pytest.fixture
def lib(tmp_path):
    """A library holding a kit, a reversed twin, their parts and accessory."""
    lib = tmp_path / "library"
    for ref in ("acme/inner@1", "acme/outer@1", "acme/mid@1", "acme/cma@1",
                "acme/plain@1"):
        _write(lib, ref, {**PART, "name": ref.split("/")[1].split("@")[0]})
    _write(lib, KIT_REF, KIT)
    _write(lib, "acme/slide-rev@1", {**KIT, "name": "slide-rev"})
    (lib / "devices").mkdir(parents=True)
    return lib


def _schema_errors(doc):
    return [f"{'/'.join(map(str, e.path))}: {e.message}" for e in VALIDATOR.iter_errors(doc)]


def _codes(findings):
    return sorted({f.split("[")[1].split("]")[0] for f in findings})


def _kit_findings(lib, doc):
    with lint.collecting() as found:
        lint.lint_device_kits(lib / "devices" / "d.yaml", doc, [str(lib)])
    return found.errors + found.warnings


# --- the schema -----------------------------------------------------------------

def test_a_device_with_positions_and_kits_validates():
    assert _schema_errors(_device(ears=EARS, kits=KITS)) == []


@pytest.mark.parametrize("ears", ["behind", {"behind": True},
                                  {"positions": [{"name": "rear"}]}])
def test_both_spellings_of_ears_validate(ears):
    assert _schema_errors(_device(ears=ears)) == []


@pytest.mark.parametrize("ears", [
    "front", {}, {"positions": []}, {"positions": [{"at": 0}]},
    {"positions": [{"name": "sideways"}]},
    {"positions": [{"name": "flush", "racks": ["3-post"]}]},
    {"positions": [{"name": "flush", "racks": ["2-post", "2-post"]}]},
    {"positions": [{"name": "mid", "part": {"kit": KIT_REF}}]},
    {"positions": [{"name": "mid", "part": "mid"}]},
    {"positions": [{"name": "flush", "screws": 4}]},
    {"behind": "yes"}])
def test_a_malformed_ears_is_refused(ears):
    assert _schema_errors(_device(ears=ears))


@pytest.mark.parametrize("kit", [
    {"ref": KIT_REF},
    {"ref": KIT_REF, "supply": "bundled"},
    {"ref": KIT_REF, "supply": "in-box", "variant": "normal"},
    {"ref": "slide", "supply": "in-box"},
    {"ref": KIT_REF, "supply": "in-box", "depth": {"config": "four-post"}},
    {"ref": KIT_REF, "supply": "in-box", "depth": {"config": "x", "range": [600]}},
    {"ref": KIT_REF, "supply": "in-box", "depth": {"config": "x", "range": {"oval": [1, 2]}}},
    {"ref": KIT_REF, "supply": "in-box", "count": 2}])
def test_a_malformed_kit_entry_is_refused(kit):
    assert _schema_errors(_device(kits=[kit]))


def test_the_kit_shapes_are_the_component_schemas_own():
    """REUSED, NOT REWRITTEN. The schemas are loaded without a registry, so the
    device schema cannot `$ref` into component.schema.json; it carries copies,
    and this holds them to the originals so the override of a kit's depth and
    the depth it overrides cannot drift into two shapes."""
    dev, comp = DEVICE_SCHEMA["$defs"], COMPONENT_SCHEMA["$defs"]
    assert dev["kit-range"] == comp["kit-range"]
    assert dev["kit-depth"] == comp["kit-depth"]
    racks = COMPONENT_SCHEMA["properties"]["configurations"]["items"]["properties"]["racks"]
    assert dev["rack-type"]["enum"] == racks["items"]["enum"]


# --- devicelock -----------------------------------------------------------------

def test_kits_and_ears_are_chassis_surface():
    assert {"ears", "kits"} <= dl.CHASSIS_SURFACE


@pytest.mark.parametrize("key,value", [("ears", EARS), ("kits", KITS),
                                       ("ears", "behind")])
def test_stating_ears_or_kits_is_a_patch(key, value):
    before = dl.entry(_device())
    after = dl.entry(_device(**{key: value}))
    assert before["shape"] == after["shape"]
    assert before["surface"] != after["surface"]
    assert dl.required_bump(before, after) == "patch"


def test_a_listed_kit_and_what_it_holds_are_composed(lib):
    versions = dl.component_versions(lib)
    composed = dl.entry(_device(kits=KITS[:1]), versions)["composed-refs"]
    assert set(composed) == {KIT_REF, "acme/inner@1", "acme/outer@1", "acme/mid@1",
                             "acme/cma@1"}
    assert dl.entry(_device(), versions)["composed-refs"] == {}


@pytest.mark.parametrize("ref,edit", [
    (KIT_REF, {**KIT, "travel": 700}),
    ("acme/cma@1", {**PART, "name": "cma", "size": {"w": 30, "h": 40}})])
def test_a_kit_edited_in_place_asks_the_device_for_a_patch(lib, ref, edit):
    doc = _device(kits=KITS[:1])
    old = dl.entry(doc, dl.component_versions(lib))
    _write(lib, ref, edit)
    new = dl.entry(doc, dl.component_versions(lib))
    assert old["composed"] != new["composed"]
    assert dl.required_bump(old, new) == "patch"


# --- L43 and L125 ---------------------------------------------------------------

def _wide(**chassis):
    doc = _device(**chassis)
    doc["chassis"]["width"] = 482.6
    doc["views"]["front"]["size"]["w"] = 482.6
    return doc


@pytest.mark.parametrize("ears,fires", [
    (None, True), ("behind", False), ({"behind": True}, False),
    ({"behind": False, "positions": [{"name": "flush"}]}, True),
    ({"positions": [{"name": "flush"}]}, True)])
def test_L43_stands_down_for_behind_in_either_spelling(tmp_path, ears, fires):
    doc = _wide(**({"ears": ears} if ears is not None else {}))
    with lint.collecting() as found:
        lint.lint_device_rack_ears(tmp_path / "d.yaml", doc)
    assert ("L43" in _codes(found.warnings)) is fires


@pytest.mark.parametrize("mount,fires", [("rack", False), ("din-rail", True),
                                         ("rack-face", True), ("wall", True)])
def test_L125_kits_only_on_a_rack_device(tmp_path, mount, fires):
    doc = _device(kits=KITS[:1], mount=mount)
    with lint.collecting() as found:
        lint.lint_device_mount(tmp_path / "d.yaml", doc)
    assert any("[L125]" in e and "chassis.kits" in e for e in found.errors) is fires


# --- L160 to L163 ---------------------------------------------------------------

def test_a_well_formed_device_is_clean(lib):
    assert _kit_findings(lib, _device(ears=EARS, kits=KITS)) == []


def test_L160_two_defaults(lib):
    ears = copy.deepcopy(EARS)
    ears["positions"][1]["default"] = True
    assert _codes(_kit_findings(lib, _device(ears=ears, kits=KITS))) == ["L160"]


def test_L160_one_default_false_is_not_a_second(lib):
    ears = copy.deepcopy(EARS)
    ears["positions"][1]["default"] = False
    assert _kit_findings(lib, _device(ears=ears, kits=KITS)) == []


@pytest.mark.parametrize("ref,words", [
    ("acme/plain@1", "not a kit"), ("acme/nothing@1", "not in the library")])
def test_L161_a_listed_ref_is_a_kit(lib, ref, words):
    found = _kit_findings(lib, _device(kits=[{"ref": ref, "supply": "optional"}]))
    assert _codes(found) == ["L161"] and words in found[0]


def test_L161_a_kit_listed_twice(lib):
    kits = [KITS[0], {"ref": KIT_REF, "supply": "optional"}]
    found = _kit_findings(lib, _device(kits=kits))
    assert _codes(found) == ["L161"] and "twice" in found[0]


def test_L162_a_position_names_an_unlisted_kit(lib):
    found = _kit_findings(lib, _device(ears=EARS, kits=KITS[1:]))
    assert _codes(found) == ["L162"] and "not listed" in found[0]


def test_L162_a_position_names_a_part_the_kit_lacks(lib):
    ears = copy.deepcopy(EARS)
    ears["positions"][2]["part"]["part"] = "bracket-225"
    found = _kit_findings(lib, _device(ears=ears, kits=KITS))
    assert _codes(found) == ["L162"] and "no part 'bracket-225'" in found[0]


def test_L162_stands_down_for_a_listed_kit_L161_refused(lib):
    """One finding for one fault: the listing is wrong, not the position."""
    ears = {"positions": [{"name": "mid", "part": {"kit": "acme/plain@1", "part": "x"}}]}
    found = _kit_findings(lib, _device(ears=ears, kits=[{"ref": "acme/plain@1",
                                                          "supply": "in-box"}]))
    assert _codes(found) == ["L161"]


@pytest.mark.parametrize("depth,words", [
    ({"config": "six-post", "range": [600, 900]}, "not a configuration"),
    ({"config": "four-post", "range": [600, 900]}, "same shape"),
    ({"config": "four-post", "range": {"square": [600, 900]}}, "same shape"),
    ({"config": "short", "range": {"square": [500, 600]}}, "same shape"),
    ({"config": "short", "range": [600, 500]}, "below the maximum"),
    ({"config": "four-post", "range": {"square": [700, 700], "round": [600, 800]}},
     "below the maximum")])
def test_L163_the_override_names_a_configuration_in_its_shape(lib, depth, words):
    kits = [{"ref": KIT_REF, "supply": "in-box", "depth": depth}]
    found = _kit_findings(lib, _device(kits=kits))
    assert _codes(found) == ["L163"] and words in found[0], found


def test_L163_a_single_range_override_is_clean(lib):
    kits = [{"ref": KIT_REF, "supply": "in-box",
             "depth": {"config": "short", "range": [520, 600]}}]
    assert _kit_findings(lib, _device(kits=kits)) == []


# --- a kit used where it cannot be: L5, L10, L101 -------------------------------

def _device_lint(lib, doc):
    path = lib / "devices" / "acme" / "d" / "device.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    with lint.collecting() as found:
        lint.lint_device(path, VALIDATOR, [str(lib)])
    # a schema fault stops the run before L5, and would pass the clean cases
    assert not [e for e in found.errors if "[L1]" in e], found.errors
    return found.errors


def _with_view(placements=(), bays=()):
    doc = _device()
    doc["views"]["front"]["components"] = {}
    if placements:
        doc["views"]["front"]["components"]["placements"] = list(placements)
    if bays:
        doc["views"]["front"]["components"]["bays"] = list(bays)
    return doc


@pytest.mark.parametrize("ref,fires", [(KIT_REF, True), ("acme/plain@1", False)])
def test_L5_refuses_a_placed_kit(lib, ref, fires):
    doc = _with_view(placements=[{"id": "rail", "ref": ref, "at": [10, 2]}])
    l5 = [e for e in _device_lint(lib, doc) if "[L5]" in e]
    assert bool(l5) is fires, l5
    if fires:
        assert "kind: kit" in l5[0]


@pytest.mark.parametrize("bay,fires", [
    ({"accepts": [KIT_REF], "default": KIT_REF}, True),
    ({"accepts": ["acme/plain@1", KIT_REF]}, True),
    ({"accepts": ["acme/plain@1"], "default": "acme/plain@1"}, False)])
def test_L5_refuses_a_kit_in_a_bay(lib, bay, fires):
    doc = _with_view(bays=[{"id": "slot", "at": [10, 2], "size": {"w": 20, "h": 40}, **bay}])
    l5 = [e for e in _device_lint(lib, doc) if "[L5]" in e]
    assert bool(l5) is fires, l5


def test_L5_a_bay_default_outside_accepts_is_still_refused_as_a_kit(lib):
    doc = _with_view(bays=[{"id": "slot", "at": [10, 2], "size": {"w": 20, "h": 40},
                            "accepts": ["acme/plain@1"], "default": KIT_REF}])
    errs = _device_lint(lib, doc)
    assert any("[L5]" in e and "kind: kit" in e for e in errs)
    assert any("[L6]" in e for e in errs)


@pytest.mark.parametrize("ref,fires", [(KIT_REF, True), ("acme/plain@1", False)])
def test_L10_refuses_a_composed_kit(lib, ref, fires):
    doc = {**PART, "name": "carrier",
           "parts": [{"ref": ref, "id": "p", "at": [0, 0]}]}
    path = _write(lib, "acme/carrier@1", doc)
    with lint.collecting() as found:
        lint.lint_component_parts(path, doc, [str(lib)])
    assert ("L10" in _codes(found.errors)) is fires, found.errors


@pytest.mark.parametrize("bay,fires", [
    ({"default": KIT_REF, "accepts": [KIT_REF]}, True),
    ({"accepts": [KIT_REF]}, True),
    ({"default": "acme/plain@1", "accepts": ["acme/plain@1"]}, False)])
def test_L10_refuses_a_kit_in_a_components_bay(lib, bay, fires):
    doc = {**PART, "name": "carrier", "bays": {"slot": bay}}
    path = _write(lib, "acme/carrier@1", doc)
    with lint.collecting() as found:
        lint.lint_component_bay_kits(path, doc, [str(lib)])
    assert ("L10" in _codes(found.errors)) is fires, found.errors


@pytest.mark.parametrize("own,successor,fires", [
    (KIT, KIT_REF, False), (KIT, "acme/plain@1", True),
    (PART, KIT_REF, True), (PART, "acme/plain@1", False)])
def test_L101_a_kits_successor_is_a_kit(lib, own, successor, fires):
    doc = {**own, "name": "old", "superseded-by": successor}
    path = _write(lib, "acme/old@1", doc)
    with lint.collecting() as found:
        lint.lint_component_superseded_by(path, doc, [str(lib)])
    assert ("L101" in _codes(found.errors)) is fires, found.errors


# --- L89: a listed kit is reached, and so are its parts ------------------------

def _l89(lib, kits):
    # enough directly placed parts that the rule's non-vacuity guard (half the
    # library reachable) holds with the kit unlisted too
    placed = [f"acme/p{i}@1" for i in range(8)]
    for ref in placed:
        _write(lib, ref, {**PART, "name": ref.split("/")[1].split("@")[0]})
    doc = _with_view(placements=[{"id": f"p{i}", "ref": r, "at": [i, 0]}
                                 for i, r in enumerate(placed)])
    if kits:
        doc["chassis"]["kits"] = kits
    path = lib / "devices" / "acme" / "d" / "device.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    # the reversed twin would reach the same parts from its `unplaced:`, so it
    # goes; the plain part is reached from nowhere either way and says so
    shutil.rmtree(lib / "components/acme/slide-rev")
    p = lib / "components/acme/plain/v1/contract.yaml"
    p.write_text(yaml.safe_dump({**yaml.safe_load(p.read_text()),
                                 "unplaced": "a test part nothing names"}, sort_keys=False))
    with lint.collecting() as found:
        lint.lint_unplaced_majors(lib)
    return {e.split(" ")[2] for e in found.errors if "[L89]" in e and "reachable from no device" in e}


def test_L89_a_kit_listed_by_a_device_reaches_its_parts(lib):
    assert _l89(lib, KITS[:1]) == set()


def test_L89_an_unlisted_kit_and_its_parts_are_unreached(lib):
    assert _l89(lib, None) == {KIT_REF, "acme/inner@1", "acme/outer@1", "acme/mid@1",
                               "acme/cma@1"}


# --- the catalogue and the dependency walk -------------------------------------

def test_a_kit_composes_nothing_in_the_catalogue(lib):
    _write(lib, "acme/carrier@1", {**PART, "name": "carrier",
                                   "parts": [{"ref": "acme/inner@1", "id": "a", "at": [0, 0]}]})
    counts = cat.composer_counts(lib)
    assert counts.get("acme/inner@1") == 1          # the carrier, not the two kits
    assert "acme/cma@1" not in counts


def test_a_devices_dependencies_include_its_kits(lib):
    path = lib / "devices" / "acme" / "d" / "device.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(_device(kits=KITS[:1]), sort_keys=False))
    names = {f"{p.parts[-4]}/{p.parts[-3]}" for p in lint.device_dependencies(path, [str(lib)])
             if p.name == "contract.yaml"}
    assert names == {"acme/slide", "acme/inner", "acme/outer", "acme/mid", "acme/cma"}


# --- the one device that states ears today -------------------------------------

def test_the_bare_behind_device_is_unchanged_and_clean():
    path = ROOT / "library/devices/fs/uscmh-sfdabsb2u/device.yaml"
    assert yaml.safe_load(path.read_text())["chassis"]["ears"] == "behind"
    with lint.collecting() as found:
        lint.lint_device(path, VALIDATOR, [str(ROOT / "library")])
    assert found.errors == []
    codes = set(_codes(found.warnings))
    assert not codes & {"L43", "L125", "L160", "L161", "L162", "L163"}
